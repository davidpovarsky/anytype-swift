package spaceindex

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"

	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/datastore/anystoreprovider"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// This supplemental same-runtime proof is overlaid by validate_t5_coverage.py;
// it does not change the frozen production patch or prove old/new binary pairing.
func TestTorahRelatedNativeOnDiskCloseAndReopen(t *testing.T) {
	ctx := context.Background()
	deps := NewStoreFixture(t)
	root := t.TempDir()
	var provider anystoreprovider.Provider
	var store *dsObjectStore
	open := func() {
		t.Helper()
		var err error
		provider, err = anystoreprovider.NewInPath(root)
		if err != nil {
			t.Fatal(err)
		}
		store = New(ctx, "test", Deps{DbProvider: provider, Fts: deps.fts,
			SourceService: deps.sourceService, SubManager: &SubscriptionManager{},
			FulltextQueue: deps.fulltextQueue}).(*dsObjectStore)
		if err = store.Init(); err != nil {
			t.Fatal(err)
		}
	}
	close := func() {
		t.Helper()
		var closeErr error
		if store != nil {
			closeErr = errors.Join(closeErr, store.Close())
			store = nil
		}
		if provider != nil {
			closeErr = errors.Join(closeErr, provider.Close(ctx))
			provider = nil
		}
		if closeErr != nil {
			t.Fatal(closeErr)
		}
	}
	t.Cleanup(close)
	open()
	put := func(id string, details *domain.Details) {
		t.Helper()
		if err := store.UpdateObjectDetails(ctx, id, details); err != nil {
			t.Fatal(err)
		}
	}
	put("reopen-property", domain.NewDetails().SetString(bundle.RelationKeyRelationKey, "reopenCanonical").
		SetInt64(bundle.RelationKeyRelationFormat, 0).SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_relation)))
	manifest, err := json.Marshal(map[string]any{
		"schemaVersion": 1, "spaceId": "test", "manifestObjectId": "reopen-manifest", "provisioningState": "complete",
		"documentAssociationsPropertyId": "reopen-property", "documentAssociationsPropertyKey": "reopenCanonical",
		"registeredDocumentTypes": map[string]string{"chiddush": "h", "article": "a", "research": "r"},
		"defaultTemplateIds":      map[string]string{"chiddush": "th", "article": "ta", "research": "tr"},
		"parentPropertyId":        "p", "parentPropertyKey": "pk", "orderPropertyId": "o", "orderPropertyKey": "ok", "folderTypeId": "f", "bookFolderTypeId": "b",
	})
	if err != nil {
		t.Fatal(err)
	}
	put("reopen-manifest", domain.NewDetails().SetString(bundle.RelationKeySpaceId, "test").
		SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).SetString(bundle.RelationKeyDescription, string(manifest)))
	identity := torah.Identity(torah.Ref, "sefaria", "Genesis 3:3", "")
	for _, entry := range []struct{ id, block, role string }{{"reopen-document", "", "context"}, {"reopen-block", "K", "sourceQuote"}} {
		record := map[string]any{"spaceId": "test", "objectId": entry.id, "item": map[string]string{
			"id": entry.id + "-association", "kind": "ref", "role": entry.role,
			"providerID": "sefaria", "canonicalKey": "Genesis 3:3", "externalID": "Genesis 3:3", "labelHe": "source"}}
		if entry.block != "" {
			record["blockId"] = entry.block
		}
		raw, err := json.Marshal(map[string]any{"version": 2, "records": []any{record}})
		if err != nil {
			t.Fatal(err)
		}
		put(entry.id, domain.NewDetails().SetString(bundle.RelationKeySpaceId, "test").
			SetString(bundle.RelationKeyType, "page").SetInt64(bundle.RelationKeyLayout, 0).
			SetString(bundle.RelationKeyName, entry.id).SetString("reopenCanonical", string(raw)))
	}
	keys := []domain.RelationKey{bundle.RelationKeyId, bundle.RelationKeySpaceId, bundle.RelationKeyType,
		bundle.RelationKeyLayout, bundle.RelationKeyName, bundle.RelationKeyDescription, "reopenCanonical"}
	for _, key := range torah.LocalKeys() {
		keys = append(keys, domain.RelationKey(key))
	}
	sentinels := map[string]*domain.Details{}
	for _, id := range []string{"reopen-manifest", "reopen-document", "reopen-block"} {
		details, err := store.GetDetails(id)
		if err != nil {
			t.Fatal(err)
		}
		if details.GetInt64(torah.RelatedVersionKey) != 1 || details.GetString(torah.CacheIntegrityKey) == "" {
			t.Fatalf("pre-close private capability/cache missing for %s", id)
		}
		if id != "reopen-manifest" && !details.GetBool(torah.ReadyKey) {
			t.Fatalf("pre-close row not ready: %s", id)
		}
		sentinels[id] = details.CopyOnlyKeys(keys...)
	}
	close() // Closes store workers/collections AND provider-owned SQLite DB handles.
	dbPath := filepath.Join(root, "objectstore", "test", "objects.db")
	info, err := os.Stat(dbPath)
	if err != nil || !info.Mode().IsRegular() || info.Size() == 0 {
		t.Fatalf("closed on-disk Space DB missing/empty: %v", err)
	}
	open() // Fresh provider and fresh store, same existing on-disk root; Init recovers.
	stats := store.nativeTorah().LastRecoveryStats()
	if !stats.Complete || stats.Reused < len(sentinels) {
		t.Fatalf("reopen did not reuse sealed private caches: %+v", stats)
	}
	for id, before := range sentinels {
		after, err := store.GetDetails(id)
		if err != nil || !before.Equal(after.CopyOnlyKeys(keys...)) {
			t.Fatalf("reopen changed canonical/public/private/cache sentinel %s: %v", id, err)
		}
	}
	membership := func(key domain.RelationKey, want []string) database.Filter {
		t.Helper()
		filter, err := database.MakeFilter("test", database.FilterRequest{RelationKey: key,
			Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList([]string{identity})}, store)
		if err != nil {
			t.Fatal(err)
		}
		rows, err := store.QueryRaw(&database.Filters{FilterObj: filter}, 0, 0)
		if err != nil {
			t.Fatal(err)
		}
		got := []string{}
		for _, row := range rows {
			got = append(got, row.Details.GetString(bundle.RelationKeyId))
		}
		sort.Strings(got)
		sort.Strings(want)
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("reopen %s membership want %v got %v", key, want, got)
		}
		return filter
	}
	private := membership(torah.RelatedSourcesKey, []string{"reopen-document", "reopen-block"})
	membership(torah.SourcesKey, []string{"reopen-document"})
	plan, err := store.objects.Find(private.AnystoreFilter()).Explain(ctx)
	if err != nil {
		t.Fatal(err)
	}
	indexed := false
	for _, index := range plan.Indexes {
		indexed = indexed || (index.Name == torah.RelatedSourcesKey && index.Used)
	}
	if !indexed {
		t.Fatalf("reopened private sparse index unused: %+v", plan)
	}
	t.Logf("PASS T5 actual on-disk store/provider close/reopen: canonical/public/private/cache/readiness/index preserved; recovery=%+v", stats)
}
