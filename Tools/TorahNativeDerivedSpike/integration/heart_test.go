package heartprobe

import (
	"context"
	"encoding/json"
	"reflect"
	"sort"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	derived "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

const sources domain.RelationKey = "pinkhaTorahSources"
const ready domain.RelationKey = "_pinkhaTorahReady"

// Two metadata rows, never an Object per association. The native production
// hook discovers this binding exactly as it discovers the application's manifest.
func installNativeBinding(t testing.TB, store spaceindex.Store, active bool) *domain.Details {
	t.Helper()
	ctx := context.Background()
	property := domain.NewDetails().SetString(bundle.RelationKeyRelationKey, "fixtureCanonical").
		SetInt64(bundle.RelationKeyRelationFormat, 0).SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_relation))
	if err := store.UpdateObjectDetails(ctx, "fixture-property", property); err != nil { t.Fatal(err) }
	raw, err := json.Marshal(map[string]any{
		"schemaVersion": 1, "spaceId": "test", "manifestObjectId": "fixture-manifest", "provisioningState": "complete",
		"documentAssociationsPropertyId": "fixture-property", "documentAssociationsPropertyKey": "fixtureCanonical",
		"registeredDocumentTypes": map[string]string{"chiddush":"chiddush", "article":"article", "research":"research"},
		"defaultTemplateIds": map[string]string{"chiddush":"th", "article":"ta", "research":"tr"},
		"parentPropertyId":"parent", "parentPropertyKey":"parentKey", "orderPropertyId":"order", "orderPropertyKey":"orderKey",
		"folderTypeId":"folder", "bookFolderTypeId":"book",
	})
	if err != nil { t.Fatal(err) }
	name := derived.ManifestUniqueKey
	if !active { name = "inactive synthetic metadata" }
	manifest := domain.NewDetails().SetString(bundle.RelationKeyName, name).SetString(bundle.RelationKeyDescription, string(raw))
	if err := store.UpdateObjectDetails(ctx, "fixture-manifest", manifest); err != nil { t.Fatal(err) }
	return manifest
}

func nativeFixtureDocument(raw string) *domain.Details {
	return domain.NewDetails().SetString(bundle.RelationKeyName, "synthetic").
		SetString(bundle.RelationKeySpaceId, "test").SetString(bundle.RelationKeyType, "chiddush").SetString("fixtureCanonical", raw)
}

// This exercises Heart's real SQLite-backed ObjectStore and query compiler.
// It is not an ObjectSetDetails/Set UI end-to-end acceptance test.
func TestNativeMembershipAndCommittedNotifications(t *testing.T) {
	store := spaceindex.NewStoreFixture(t)
	installNativeBinding(t, store, true)
	ctx := context.Background()
	put := func(id string, values []string, valid bool) {
		t.Helper()
		details := nativeFixtureDocument(`{"version":999}`)
		if valid {
			items := []map[string]string{}
			for _, value := range values {
				items = append(items, map[string]string{"id": value, "kind": "ref", "role": "context", "providerID": "sefaria", "canonicalKey": value, "externalID": value, "labelHe": "מקור בדיקה"})
			}
			raw, err := json.Marshal(map[string]any{"version": 1, "items": items})
			if err != nil {
				t.Fatal(err)
			}
			details.SetString("fixtureCanonical", string(raw))
		}
		if err := store.UpdateObjectDetails(ctx, id, details); err != nil {
			t.Fatal(err)
		}
	}
	put("empty", nil, true)
	put("a", []string{"ref-a"}, true)
	put("ab", []string{"ref-a", "ref-b"}, true)
	put("substring", []string{"ref-ab"}, true)
	put("corrupt", nil, false)
	refA := derived.Identity(derived.Ref, "sefaria", "ref-a", "")
	refB := derived.Identity(derived.Ref, "sefaria", "ref-b", "")
	in := database.FilterIn{Key: sources, Value: []domain.Value{domain.String(refA)}}
	gate := database.FilterIn{Key: ready, Value: []domain.Value{domain.Bool(true)}}
	check := func(filter database.Filter, want ...string) {
		t.Helper()
		records, err := store.QueryRaw(&database.Filters{FilterObj: database.FiltersAnd{gate, filter}}, 0, 0)
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
			t.Fatalf("%T want %v, got %v", filter, want, got)
		}
	}
	check(in, "a", "ab")
	check(database.FilterAllIn{Key: sources, Strings: []string{refA, refB}}, "ab")
	check(database.FilterNot{Filter: in}, "empty", "substring")
	check(database.FilterEmpty{Key: sources}, "empty")
	check(database.FilterNot{Filter: database.FilterEmpty{Key: sources}}, "a", "ab", "substring")
	check(database.FiltersOr{in, database.FilterEmpty{Key: sources}}, "a", "ab", "empty")
	check(database.FiltersAnd{in, database.FilterAllIn{Key: sources, Strings: []string{refB}}}, "ab")
	recordsCh := make(chan *domain.Details, 4)
	subscription := database.NewSubscription(nil, recordsCh)
	_, closeSubscription, err := store.QueryByIdsAndSubscribeForChanges([]string{"a"}, subscription)
	if err != nil {
		t.Fatal(err)
	}
	defer closeSubscription()
	notifications := 0
	store.SubscribeForAll(func(record database.Record) {
		notifications++
		committed, err := store.GetDetails(record.Details.GetString(bundle.RelationKeyId))
		if err != nil {
			t.Error(err)
			return
		}
		if !reflect.DeepEqual(committed, record.Details) {
			t.Error("notification did not describe committed state")
		}
	})
	tx, err := store.WriteTx(ctx)
	if err != nil {
		t.Fatal(err)
	}
	details := nativeFixtureDocument(`{"version":2,"records":[]}`)
	if err := store.UpdateObjectDetails(tx.Context(), "a", details); err != nil {
		t.Fatal(err)
	}
	if notifications != 0 {
		t.Fatal("notification before commit")
	}
	if err := tx.Commit(); err != nil {
		t.Fatal(err)
	}
	if notifications != 1 {
		t.Fatalf("want one committed notification, got %d", notifications)
	}
	select {
	case update := <-recordsCh:
		if len(update.GetStringList(sources)) != 0 {
			t.Fatal("subscription retained last removed source")
		}
	case <-time.After(5 * time.Second):
		t.Fatal("native subscription did not receive committed removal")
	}
	check(in, "ab")
	check(database.FilterEmpty{Key: sources}, "a", "empty")
	tx, err = store.WriteTx(ctx)
	if err != nil {
		t.Fatal(err)
	}
	details.SetString("fixtureCanonical", `{"version":1,"items":[{"id":"retry","kind":"ref","role":"context","providerID":"sefaria","canonicalKey":"ref-a","externalID":"ref-a","labelHe":"מקור בדיקה"}]}`)
	if err := store.UpdateObjectDetails(tx.Context(), "a", details); err != nil {
		t.Fatal(err)
	}
	if err := tx.Rollback(); err != nil {
		t.Fatal(err)
	}
	if notifications != 1 {
		t.Fatal("rolled back update notified")
	}
	select {
	case <-recordsCh:
		t.Fatal("native subscription received rolled-back state")
	case <-time.After(20 * time.Millisecond):
	}
	check(in, "ab")
}
