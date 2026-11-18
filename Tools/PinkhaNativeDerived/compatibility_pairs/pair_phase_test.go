package spaceindex

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"

	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/datastore/anystoreprovider"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/util/vcs"
)

// Set by the external exact-source build recipe, checked again before opening DBs.
var pairFixtureSHA = "UNSET"

func TestTorahCompatibilityPairPhase(t *testing.T) {
	const protocol = "pinkha-t5-pair-store-v1"
	root, reportPath := os.Getenv("PINKHA_PAIR_ROOT"), os.Getenv("PINKHA_PAIR_REPORT")
	phase, role, nonce := os.Getenv("PINKHA_PAIR_PHASE"), os.Getenv("PINKHA_PAIR_ROLE"), os.Getenv("PINKHA_PAIR_NONCE")
	patch := os.Getenv("PINKHA_PAIR_PATCH_SHA")
	if root == "" || reportPath == "" || nonce == "" || len(patch) != 64 || pairFixtureSHA == "UNSET" ||
		pairFixtureSHA != os.Getenv("PINKHA_PAIR_FIXTURE_SHA") || vcs.GitCommit != "d98420b1113536afd08cde6de9a5816f6d27ffff" {
		t.Fatal("exact controller/build identities required; no skip or ad-hoc database permitted")
	}
	roles := map[string]string{"old-create": "old", "new-upgrade": "new", "old-edit": "old", "new-recover": "new"}
	if roles[phase] != role || (role != "old" && role != "new") || !strings.Contains(vcs.GitSummary, "pinkha-native-derived-v1-"+patch) {
		t.Fatal("wrong phase or linked native revision")
	}
	capability := 0
	if role == "new" {
		if !strings.Contains(vcs.GitSummary, "pinkha-native-t5-lookup-v1-"+patch) {
			t.Fatal("new runtime lacks separate linked T5 capability")
		}
		capability = 1
	} else if strings.Contains(vcs.GitSummary, "pinkha-native-t5-lookup-v1-") {
		t.Fatal("old runtime unexpectedly advertises new capability")
	}
	root, err := filepath.Abs(root)
	if err != nil {
		t.Fatal(err)
	}
	parent := filepath.Dir(root)
	if filepath.Base(root) != "database" || filepath.Dir(reportPath) != parent || filepath.Base(reportPath) != phase+".json" {
		t.Fatal("controller-owned database/report paths required")
	}
	owner, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	var ownership struct {
		Protocol      string `json:"protocol"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	if err != nil || string(owner) != os.Getenv("PINKHA_PAIR_OWNER_TOKEN") || json.Unmarshal(owner, &ownership) != nil ||
		ownership.Protocol != protocol || !ownership.SyntheticOnly {
		t.Fatal("fresh synthetic controller ownership required")
	}
	if phase == "old-create" {
		entries, err := os.ReadDir(root)
		if err != nil || len(entries) != 0 {
			t.Fatal("initial disposable database directory must be empty")
		}
	} else if info, err := os.Stat(filepath.Join(root, "objectstore", "test", "objects.db")); err != nil || info.Size() == 0 {
		t.Fatal("prior phase's same on-disk database required")
	}
	ctx := context.Background()
	deps := NewStoreFixture(t)
	provider, err := anystoreprovider.NewInPath(root)
	if err != nil {
		t.Fatal(err)
	}
	store := New(ctx, "test", Deps{DbProvider: provider, Fts: deps.fts, SourceService: deps.sourceService,
		SubManager: &SubscriptionManager{}, FulltextQueue: deps.fulltextQueue}).(*dsObjectStore)
	closed := false
	closeStore := func() error {
		if closed {
			return nil
		}
		closed = true
		return errors.Join(store.Close(), provider.Close(ctx))
	}
	t.Cleanup(func() {
		if err := closeStore(); err != nil {
			t.Error(err)
		}
	})
	if err = store.Init(); err != nil {
		t.Fatal(err)
	}
	stats := store.nativeTorah().LastRecoveryStats()
	put := func(id string, details *domain.Details) {
		t.Helper()
		if err := store.UpdateObjectDetails(ctx, id, details); err != nil {
			t.Fatal(err)
		}
	}
	if phase == "old-create" {
		put("pair-property", domain.NewDetails().SetString(bundle.RelationKeyRelationKey, "pairCanonical").
			SetInt64(bundle.RelationKeyRelationFormat, 0).SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_relation)))
		manifest, err := json.Marshal(map[string]any{
			"schemaVersion": 1, "spaceId": "test", "manifestObjectId": "pair-manifest", "provisioningState": "complete",
			"documentAssociationsPropertyId": "pair-property", "documentAssociationsPropertyKey": "pairCanonical",
			"registeredDocumentTypes": map[string]string{"chiddush": "h", "article": "a", "research": "r"},
			"defaultTemplateIds":      map[string]string{"chiddush": "th", "article": "ta", "research": "tr"},
			"parentPropertyId":        "p", "parentPropertyKey": "pk", "orderPropertyId": "o", "orderPropertyKey": "ok", "folderTypeId": "f", "bookFolderTypeId": "b",
		})
		if err != nil {
			t.Fatal(err)
		}
		put("pair-manifest", domain.NewDetails().SetString(bundle.RelationKeySpaceId, "test").
			SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).SetString(bundle.RelationKeyDescription, string(manifest)))
		for _, entry := range []struct{ id, block, role string }{{"pair-document", "", "context"}, {"pair-block", "K", "sourceQuote"}} {
			record := map[string]any{"spaceId": "test", "objectId": entry.id, "unknownRecord": "preserve",
				"item": map[string]string{"id": entry.id + "-ref", "kind": "ref", "role": entry.role, "providerID": "sefaria",
					"canonicalKey": "Genesis 3:3", "externalID": "Genesis 3:3", "labelHe": "source", "unknownItem": "preserve"}}
			if entry.block != "" {
				record["blockId"] = entry.block
			}
			raw, err := json.Marshal(map[string]any{"version": 2, "unknownRoot": "preserve", "records": []any{record}})
			if err != nil {
				t.Fatal(err)
			}
			put(entry.id, domain.NewDetails().SetString(bundle.RelationKeySpaceId, "test").SetString(bundle.RelationKeyType, "page").
				SetInt64(bundle.RelationKeyLayout, 0).SetString(bundle.RelationKeyName, entry.id).SetString("pairCanonical", string(raw)))
		}
	} else if phase == "old-edit" {
		d, err := store.GetDetails("pair-document")
		if err != nil {
			t.Fatal(err)
		}
		put("pair-document", d.Copy().SetString(bundle.RelationKeyName, "Synthetic ordinary edit by r14"))
	}
	hash := func(value []byte) string { result := sha256.Sum256(value); return hex.EncodeToString(result[:]) }
	canonical, public, caches := map[string]string{}, map[string]string{}, map[string]string{}
	ready, versions := map[string]bool{}, map[string]int64{}
	publicKeys := []domain.RelationKey{torah.SourcesKey, torah.TopicsKey, torah.WordsKey, torah.LabelsKey,
		torah.ReadyKey, torah.VersionKey, torah.CanonicalHashKey, torah.StatusKey, torah.CanonicalKeyKey}
	for _, id := range []string{"pair-manifest", "pair-document", "pair-block"} {
		d, err := store.GetDetails(id)
		if err != nil {
			t.Fatal(err)
		}
		if id == "pair-manifest" {
			if d.GetString(bundle.RelationKeyDescription) == "" {
				t.Fatal("canonical manifest missing")
			}
			canonical[id] = hash([]byte(d.GetString(bundle.RelationKeyDescription)))
			continue
		}
		if d.GetString("pairCanonical") == "" {
			t.Fatal("canonical document payload missing")
		}
		canonical[id] = hash([]byte(d.GetString("pairCanonical")))
		data, err := json.Marshal(d.CopyOnlyKeys(publicKeys...).ToProto())
		if err != nil {
			t.Fatal(err)
		}
		public[id] = hash(data)
		caches[id] = d.GetString(torah.CacheIntegrityKey)
		ready[id] = d.GetBool(torah.ReadyKey)
		versions[id] = d.GetInt64("_pinkhaTorahRelatedVersion")
	}
	identity := torah.Identity(torah.Ref, "sefaria", "Genesis 3:3", "")
	query := func(key domain.RelationKey, want []string) database.Filter {
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
		ids := []string{}
		for _, row := range rows {
			ids = append(ids, row.Details.GetString(bundle.RelationKeyId))
		}
		sort.Strings(ids)
		if !reflect.DeepEqual(ids, want) {
			t.Fatalf("%s membership want %v got %v", key, want, ids)
		}
		return filter
	}
	query(torah.SourcesKey, []string{"pair-document"})
	privateMembers := []string{}
	privateIndex, privateStatus := false, "NOT_ATTEMPTED_RUNTIME_UNAVAILABLE"
	if role == "new" {
		filter := query("_pinkhaTorahRelatedSources", []string{"pair-block", "pair-document"})
		plan, err := store.objects.Find(filter.AnystoreFilter()).Explain(ctx)
		if err != nil {
			t.Fatal(err)
		}
		for _, index := range plan.Indexes {
			privateIndex = privateIndex || (index.Name == "_pinkhaTorahRelatedSources" && index.Used)
		}
		if !privateIndex {
			t.Fatal("new runtime private index unused")
		}
		privateMembers, privateStatus = []string{"pair-block", "pair-document"}, "EXECUTED"
	}
	if err = closeStore(); err != nil {
		t.Fatal(err)
	}
	report := map[string]any{"protocol": protocol, "phase": phase, "nonce": nonce, "pid": os.Getpid(),
		"heart_sha": vcs.GitCommit, "patch_sha256": patch, "fixture_sha256": pairFixtureSHA, "runtime_capability": capability,
		"database_path": root, "space_id": "test", "closed": true, "test_passed": true,
		"canonical_sha256": canonical, "public_sha256": public, "cache_sha256": caches, "ready": ready,
		"private_versions": versions, "public_members": []string{"pair-document"}, "private_members": privateMembers,
		"private_index_used": privateIndex, "private_query_status": privateStatus,
		"recovery_complete": stats.Complete, "recomputed": stats.Recomputed,
		"export_status": "NOT_RUN_COMPONENT_NO_RPC", "swift_pairing_status": "NOT_RUN",
		"required_swift_fallback": "UNAVAILABLE_FROM_RUNTIME_CAPABILITY"}
	output, err := os.OpenFile(reportPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		t.Fatal(err)
	}
	err = json.NewEncoder(output).Encode(report)
	err = errors.Join(err, output.Close())
	if err != nil {
		t.Fatal(err)
	}
	t.Logf("%s: closed synthetic component DB after %s; export/Swift pairing NOT_RUN", protocol, phase)
}
