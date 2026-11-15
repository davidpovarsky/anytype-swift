package spaceindex

import (
	"context"
	"encoding/json"
	"reflect"
	"sort"
	"testing"

	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

func TestTorahRelatedNativeIndexFilterCommitAndRecovery(t *testing.T) {
	store := NewStoreFixture(t)
	ctx := context.Background()
	put := func(id string, d *domain.Details) {
		t.Helper()
		if err := store.UpdateObjectDetails(ctx, id, d); err != nil {
			t.Fatal(err)
		}
	}
	put("related-canonical-property", domain.NewDetails().SetString(bundle.RelationKeyRelationKey, "relatedCanonical").SetInt64(bundle.RelationKeyRelationFormat, 0).SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_relation)))
	m, _ := json.Marshal(map[string]any{
		"schemaVersion": 1, "spaceId": "test", "manifestObjectId": "related-manifest", "provisioningState": "complete",
		"documentAssociationsPropertyId": "related-canonical-property", "documentAssociationsPropertyKey": "relatedCanonical",
		"registeredDocumentTypes": map[string]string{"chiddush": "h", "article": "a", "research": "r"},
		"defaultTemplateIds":      map[string]string{"chiddush": "th", "article": "ta", "research": "tr"},
		"parentPropertyId":        "p", "parentPropertyKey": "pk", "orderPropertyId": "o", "orderPropertyKey": "ok", "folderTypeId": "f", "bookFolderTypeId": "b",
	})
	put("related-manifest", domain.NewDetails().SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).SetString(bundle.RelationKeyDescription, string(m)))
	identity := torah.Identity(torah.Ref, "sefaria", "Genesis 3:3", "")
	rawByID := map[string]string{}
	for _, f := range []struct{ id, block, role string }{{"A", "", "context"}, {"B", "K", "context"}, {"C", "Q", "sourceQuote"}, {"D", "Q", "source_quote"}} {
		r := map[string]any{"spaceId": "test", "objectId": f.id, "item": map[string]string{"id": "same-id", "kind": "ref", "role": f.role, "providerID": "sefaria", "canonicalKey": "Genesis 3:3", "externalID": "Genesis 3:3", "labelHe": "source"}}
		if f.block != "" {
			r["blockId"] = f.block
		}
		raw, _ := json.Marshal(map[string]any{"version": 2, "records": []any{r}})
		rawByID[f.id] = string(raw)
		put(f.id, domain.NewDetails().SetString(bundle.RelationKeySpaceId, "test").SetString(bundle.RelationKeyType, "page").SetInt64(bundle.RelationKeyLayout, 0).SetString("relatedCanonical", string(raw)))
	}
	private, err := database.MakeFilter("test", database.FilterRequest{RelationKey: torah.RelatedSourcesKey, Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList([]string{identity})}, store)
	if err != nil {
		t.Fatal(err)
	}
	check := func(want ...string) {
		t.Helper()
		records, err := store.QueryRaw(&database.Filters{FilterObj: private}, 0, 0)
		if err != nil {
			t.Fatal(err)
		}
		got := []string{}
		for _, r := range records {
			got = append(got, r.Details.GetString(bundle.RelationKeyId))
		}
		sort.Strings(got)
		sort.Strings(want)
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("private native membership want%v got%v", want, got)
		}
	}
	check("A", "B", "C", "D")
	public, err := database.MakeFilter("test", database.FilterRequest{RelationKey: torah.SourcesKey, Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList([]string{identity})}, store)
	if err != nil {
		t.Fatal(err)
	}
	rows, err := store.QueryRaw(&database.Filters{FilterObj: public}, 0, 0)
	if err != nil || len(rows) != 1 || rows[0].Details.GetString(bundle.RelationKeyId) != "A" {
		t.Fatal("public membership widened", err)
	}
	plan, err := store.objects.Find(private.AnystoreFilter()).Explain(ctx)
	if err != nil {
		t.Fatal(err)
	}
	indexed := false
	for _, index := range plan.Indexes {
		indexed = indexed || (index.Name == torah.RelatedSourcesKey && index.Used)
	}
	if !indexed {
		t.Fatalf("private sparse membership index unused: %+v", plan)
	}
	for _, condition := range []model.BlockContentDataviewFilterCondition{model.BlockContentDataviewFilter_Equal, model.BlockContentDataviewFilter_NotIn, model.BlockContentDataviewFilter_Empty} {
		if _, err := database.MakeFilter("test", database.FilterRequest{RelationKey: torah.RelatedSourcesKey, Condition: condition, Value: domain.StringList([]string{identity})}, store); err == nil {
			t.Fatalf("unsupported private predicate accepted: %v", condition)
		}
	}
	d, err := store.GetDetails("B")
	if err != nil {
		t.Fatal(err)
	}
	tx, err := store.WriteTx(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if err = store.UpdateObjectDetails(tx.Context(), "B", d.Copy().SetString("relatedCanonical", `{"version":2,"records":[]}`)); err != nil {
		t.Fatal(err)
	}
	if err = tx.Rollback(); err != nil {
		t.Fatal(err)
	}
	check("A", "B", "C", "D")
	put("B", d.Copy().SetString("relatedCanonical", `{"version":2,"records":[]}`))
	check("A", "C", "D")
	put("B", d)
	check("A", "B", "C", "D")
	if err = store.nativeTorah().Recover(ctx); err != nil {
		t.Fatal(err)
	}
	check("A", "B", "C", "D")
	for id, raw := range rawByID {
		d, err = store.GetDetails(id)
		if err != nil || d.GetString("relatedCanonical") != raw || d.GetInt64(torah.RelatedVersionKey) != 1 {
			t.Fatalf("recovery changed canonical/capability for %s: %v", id, err)
		}
	}
	metadata, err := bundle.GetRelation(domain.RelationKey(torah.RelatedSourcesKey))
	if err != nil {
		t.Fatal(err)
	}
	if !metadata.Hidden || !metadata.ReadOnly || metadata.Format != model.RelationFormat_tag {
		t.Fatal("private list metadata is visible/editable/wrong format")
	}
	versionMetadata, err := bundle.GetRelation(domain.RelationKey(torah.RelatedVersionKey))
	if err != nil {
		t.Fatal(err)
	}
	if !versionMetadata.Hidden || versionMetadata.Format != model.RelationFormat_number {
		t.Fatal("private version metadata mismatch")
	}
	t.Logf("real native private compiler/membership/EXPLAIN/rollback/recovery verified; plan=%+v", plan)
}
