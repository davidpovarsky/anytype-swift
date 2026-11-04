package heartprobe

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/clientlibrary/service"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/gogo/protobuf/jsonpb"
	"github.com/gogo/protobuf/proto"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-store/query"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	engine "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/engine"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

// This crosses the SAME generated protobuf command entry points used by the
// mobile library, with the real core, account, object editor, indexer, Type and
// subscription services. No ObjectStore fixture or mock backend is used here.
func TestRealNativeMiddlewareDerivedProperties(t *testing.T) {
	if os.Getenv("PINKHA_NATIVE_WIRE_ACCEPTANCE") != "1" {
		t.Skip("explicit disposable native wallet opt-in required")
	}
	events := make(chan string, 16)
	// Mobile installs its event bridge before account startup. Register the real
	// callback component at the same point; replacing it later misses the app's
	// already-registered sender.
	service.SetEventHandler(func(event *pb.Event) {
		for _, msg := range event.Messages {
			if add := msg.GetSubscriptionAdd(); add != nil && add.SubId == "torah-native-wire" {
				select {
				case events <- "add":
				default:
				}
			}
			if remove := msg.GetSubscriptionRemove(); remove != nil && remove.SubId == "torah-native-wire" {
				select {
				case events <- "remove":
				default:
				}
			}
		}
	})
	invoke := func(call func([]byte) []byte, req, resp proto.Message) {
		t.Helper()
		data, err := proto.Marshal(req)
		if err != nil {
			t.Fatal(err)
		}
		if err = proto.Unmarshal(call(data), resp); err != nil {
			t.Fatal(err)
		}
		field := reflect.ValueOf(resp).Elem().FieldByName("Error")
		if field.IsValid() && !field.IsNil() && field.Elem().FieldByName("Code").Int() != 0 {
			t.Fatalf("%T error %d: %s", req, field.Elem().FieldByName("Code").Int(), field.Elem().FieldByName("Description").String())
		}
	}
	root := t.TempDir()
	invoke(service.InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root, DoNotSendLogs: true, DoNotSaveLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	wallet := &pb.RpcWalletCreateResponse{}
	invoke(service.WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, wallet)
	// Never print or persist the synthetic wallet's mnemonic in evidence.
	invoke(service.AccountCreate, &pb.RpcAccountCreateRequest{Name: "Disposable native Torah API test", NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true}, &pb.RpcAccountCreateResponse{})
	t.Cleanup(func() { invoke(service.AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{}) })
	space := &pb.RpcWorkspaceCreateResponse{}
	invoke(service.WorkspaceCreate, &pb.RpcWorkspaceCreateRequest{Details: domain.NewDetails().SetString(bundle.RelationKeyName, "Native derived disposable Space").ToProto()}, space)
	invoke(service.WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: space.SpaceId}, &pb.RpcWorkspaceOpenResponse{})
	// Match the application's incremental bootstrap: discover a hidden manifest
	// before its Property/Type/template IDs exist, then complete the same Object.
	manifest := &pb.RpcObjectCreateResponse{}
	initial, _ := json.Marshal(map[string]any{"schemaVersion": 1, "spaceId": space.SpaceId, "provisioningState": "inProgress"})
	invoke(service.ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: space.SpaceId, ObjectTypeUniqueKey: "ot-page", Details: domain.NewDetails().SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).SetString(bundle.RelationKeyUniqueKey, torah.ManifestUniqueKey).SetString(bundle.RelationKeyDescription, string(initial)).SetBool(bundle.RelationKeyIsHidden, true).ToProto()}, manifest)
	canonical := &pb.RpcObjectCreateRelationResponse{}
	invoke(service.ObjectCreateRelation, &pb.RpcObjectCreateRelationRequest{SpaceId: space.SpaceId, Details: domain.NewDetails().SetString(bundle.RelationKeyName, "הקשר תורני").SetInt64(bundle.RelationKeyRelationFormat, 0).ToProto()}, canonical)
	canonicalKey := domain.NewDetailsFromProto(canonical.Details).GetString(bundle.RelationKeyRelationKey)
	if canonicalKey == "" {
		t.Fatal("native Property creation did not return its generated key")
	}
	typeIDs := map[string]string{}
	typeKeys := map[string]string{}
	for _, role := range []string{"chiddush", "article", "research"} {
		created := &pb.RpcObjectCreateObjectTypeResponse{}
		invoke(service.ObjectCreateObjectType, &pb.RpcObjectCreateObjectTypeRequest{SpaceId: space.SpaceId, Details: domain.NewDetails().SetString(bundle.RelationKeyName, role).SetInt64(bundle.RelationKeyRecommendedLayout, int64(model.ObjectType_basic)).ToProto()}, created)
		typeIDs[role] = created.ObjectId
		typeKeys[role] = domain.NewDetailsFromProto(created.Details).GetString(bundle.RelationKeyUniqueKey)
	}
	// Auxiliary manifest roles are not exercised here; the iOS suite runs the
	// existing complete bootstrap/migration. Native writing Types/property IDs
	// below are all real Objects created through the production RPCs.
	manifestData := map[string]any{"schemaVersion": 1, "spaceId": space.SpaceId, "provisioningState": "complete",
		"manifestObjectId": manifest.ObjectId, "documentAssociationsPropertyId": canonical.ObjectId, "documentAssociationsPropertyKey": canonicalKey,
		"registeredDocumentTypes": typeIDs, "defaultTemplateIds": map[string]string{"chiddush": "unused-template-h", "article": "unused-template-a", "research": "unused-template-r"},
		"parentPropertyId": "unused-parent", "parentPropertyKey": "unusedParent", "orderPropertyId": "unused-order", "orderPropertyKey": "unusedOrder", "folderTypeId": "unused-folder", "bookFolderTypeId": "unused-book"}
	manifestRaw, _ := json.MarshalIndent(manifestData, "", "  ")
	invoke(service.ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: manifest.ObjectId, Details: []*model.Detail{{Key: "description", Value: domain.String(string(manifestRaw)).ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
	show := func(id string) *domain.Details {
		t.Helper()
		response := &pb.RpcObjectShowResponse{}
		invoke(service.ObjectShow, &pb.RpcObjectShowRequest{SpaceId: space.SpaceId, ObjectId: id, ContextId: id}, response)
		for _, entry := range response.ObjectView.Details {
			if entry.Id == id {
				return domain.NewDetailsFromProto(entry.Details)
			}
		}
		t.Fatalf("ObjectShow omitted requested object")
		return nil
	}
	wait := func(label string, predicate func() bool) {
		t.Helper()
		deadline := time.Now().Add(45 * time.Second)
		for time.Now().Before(deadline) {
			if predicate() {
				return
			}
			time.Sleep(100 * time.Millisecond)
		}
		t.Fatal("native API timeout: " + label)
	}
	t.Cleanup(func() {
		if t.Failed() {
			m, p := show(manifest.ObjectId), show(canonical.ObjectId)
			t.Logf("actual bootstrap binding: manifest name=%q uniqueKey=%q descriptionBytes=%d exactDescription=%v canonical id=%q key=%q format=%d hasFormat=%v layout=%d space=%q", m.GetString(bundle.RelationKeyName), m.GetString(bundle.RelationKeyUniqueKey), len(m.GetString(bundle.RelationKeyDescription)), m.GetString(bundle.RelationKeyDescription) == string(manifestRaw), p.GetString(bundle.RelationKeyId), p.GetString(bundle.RelationKeyRelationKey), p.GetInt64(bundle.RelationKeyRelationFormat), p.Has(bundle.RelationKeyRelationFormat), p.GetInt64(bundle.RelationKeyLayout), p.GetString(bundle.RelationKeySpaceId))
		}
	})
	wait("engine capability", func() bool { return show(manifest.ObjectId).GetInt64(torah.VersionKey) == 1 })
	nativeIDs := []string{}
	for _, definition := range torah.Definitions {
		property := &pb.RpcObjectCreateRelationResponse{}
		invoke(service.ObjectCreateRelation, &pb.RpcObjectCreateRelationRequest{SpaceId: space.SpaceId, Details: domain.NewDetails().SetString(bundle.RelationKeyName, definition.Name).SetString(bundle.RelationKeyRelationKey, definition.Key).SetInt64(bundle.RelationKeyRelationFormat, 11).SetBool(bundle.RelationKeyRelationReadonlyValue, true).ToProto()}, property)
		nativeIDs = append(nativeIDs, property.ObjectId)
		metadata := show(property.ObjectId)
		if metadata.GetString(bundle.RelationKeySourceObject) != "_br"+definition.Key {
			t.Fatal("not a genuine installed bundled Property")
		}
		for _, id := range typeIDs {
			invoke(service.ObjectTypePropertyAdd, &pb.RpcObjectTypePropertyAddRequest{ObjectTypeId: id, Key: definition.Key, Section: pb.RpcObjectTypePropertyAddRequest_Recommended, EnableInViews: true}, &pb.RpcObjectTypePropertyAddResponse{})
		}
	}
	document := &pb.RpcObjectCreateResponse{}
	invoke(service.ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: space.SpaceId, ObjectTypeUniqueKey: typeKeys["chiddush"], Details: domain.NewDetails().SetString(bundle.RelationKeyName, "Real native document").ToProto()}, document)
	identity := torah.Identity(torah.Ref, "sefaria", "Genesis 1:1", "")
	item := map[string]string{"id": "wire-source", "kind": "ref", "role": "context", "providerID": "sefaria", "canonicalKey": "Genesis 1:1", "externalID": "Genesis 1:1", "labelHe": "בראשית א:א"}
	topic := map[string]string{"id": "wire-topic", "kind": "topic", "role": "context", "providerID": "sefaria", "canonicalKey": "creation", "externalID": "creation", "labelHe": "בריאה"}
	word := map[string]string{"id": "wire-word", "kind": "word", "role": "context", "providerID": "sefaria", "canonicalKey": "בראשית", "externalID": "בראשית", "labelHe": "בראשית"}
	records := []any{}
	for _, value := range []map[string]string{item, topic, word} {
		records = append(records, map[string]any{"spaceId": space.SpaceId, "objectId": document.ObjectId, "item": value})
	}
	payload, _ := json.Marshal(map[string]any{"version": 2, "records": records, "unknownFields": map[string]any{"preserve": "unchanged"}})
	write := func(raw string) {
		t.Helper()
		invoke(service.ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: document.ObjectId, Details: []*model.Detail{{Key: canonicalKey, Value: domain.String(raw).ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
	}
	write(string(payload))
	t.Cleanup(func() {
		d := show(document.ObjectId)
		t.Logf("disposable document native diagnostics: scalarType=%q legacyTypes=%v expected=%v target=%v ready=%v status=%s sources=%v", d.GetString(bundle.RelationKeyType), d.GetStringList(bundle.RelationKeyType), typeIDs, d.Has(bundle.RelationKeyTargetObjectType), d.GetBool(torah.ReadyKey), d.GetString(torah.StatusKey), d.GetStringList(torah.SourcesKey))
		if t.Failed() {
			response := &pb.RpcObjectSearchResponse{}
			invoke(service.ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: space.SpaceId, Filters: []*model.BlockContentDataviewFilter{{RelationKey: "id", Condition: model.BlockContentDataviewFilter_Equal, Value: domain.String(document.ObjectId).ToProto()}}, Keys: []string{"id", "type", torah.ReadyKey, torah.StatusKey, torah.SourcesKey}}, response)
			for _, record := range response.Records {
				indexed := domain.NewDetailsFromProto(record)
				t.Logf("actual indexed document: scalarType=%q ready=%v status=%s sources=%v", indexed.GetString(bundle.RelationKeyType), indexed.GetBool(torah.ReadyKey), indexed.GetString(torah.StatusKey), indexed.GetStringList(torah.SourcesKey))
			}
		}
	})
	wait("canonical to native ObjectShow", func() bool {
		values := show(document.ObjectId).GetStringList(torah.SourcesKey)
		return len(values) == 1 && values[0] == identity
	})
	for _, key := range []string{torah.TopicsKey, torah.WordsKey} {
		if len(show(document.ObjectId).GetStringList(domain.RelationKey(key))) != 1 {
			t.Fatal("native kind projection missing: " + key)
		}
	}
	if show(document.ObjectId).GetString(domain.RelationKey(canonicalKey)) != string(payload) {
		t.Fatal("canonical payload bytes were rewritten")
	}
	filter := &model.BlockContentDataviewFilter{RelationKey: torah.SourcesKey, Format: model.RelationFormat_tag, Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList([]string{identity}).ToProto()}
	search := &pb.RpcObjectSearchResponse{}
	invoke(service.ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: space.SpaceId, Filters: []*model.BlockContentDataviewFilter{filter}, Keys: []string{"id", torah.SourcesKey, torah.LabelsKey}, NeedTotal: true}, search)
	if len(search.Records) != 1 || domain.NewDetailsFromProto(search.Records[0]).GetString(bundle.RelationKeyId) != document.ObjectId {
		t.Fatal("actual native ObjectSearch membership mismatch")
	}
	// The original Details APIs must reject direct value and deletion writes,
	// including the hidden readiness/label capability metadata.
	for _, key := range torah.LocalKeys() {
		if !show(document.ObjectId).Has(domain.RelationKey(key)) {
			t.Fatal("direct mutation fixture must contain the tested derived key: " + key)
		}
		for _, value := range []domain.Value{domain.StringList([]string{"forged"}), domain.Null()} {
			request := &pb.RpcObjectSetDetailsRequest{ContextId: document.ObjectId, Details: []*model.Detail{{Key: key, Value: value.ToProto()}}}
			data, _ := proto.Marshal(request)
			response := &pb.RpcObjectSetDetailsResponse{}
			if err := proto.Unmarshal(service.ObjectSetDetails(data), response); err != nil {
				t.Fatal(err)
			}
			if response.Error == nil || response.Error.Code == 0 {
				t.Fatalf("native API accepted direct derived write: %s null=%v", key, value.IsNull())
			}
		}
	}
	nativeSet := &pb.RpcObjectCreateSetResponse{}
	invoke(service.ObjectCreateSet, &pb.RpcObjectCreateSetRequest{SpaceId: space.SpaceId, Source: []string{typeIDs["chiddush"]}, Details: domain.NewDetails().SetString(bundle.RelationKeyName, "Real native Torah Set").ToProto()}, nativeSet)
	setView := &pb.RpcObjectShowResponse{}
	invoke(service.ObjectShow, &pb.RpcObjectShowRequest{SpaceId: space.SpaceId, ObjectId: nativeSet.ObjectId, ContextId: nativeSet.ObjectId}, setView)
	foundView := false
	for _, block := range setView.ObjectView.Blocks {
		if dv := block.GetDataview(); dv != nil && len(dv.Views) > 0 {
			invoke(service.BlockDataviewFilterAdd, &pb.RpcBlockDataviewFilterAddRequest{ContextId: nativeSet.ObjectId, BlockId: block.Id, ViewId: dv.Views[0].Id, Filter: filter}, &pb.RpcBlockDataviewFilterAddResponse{})
			foundView = true
			break
		}
	}
	if !foundView {
		t.Fatal("native Set had no Dataview")
	}
	subscribed := &pb.RpcObjectSearchSubscribeResponse{}
	invoke(service.ObjectSearchSubscribe, &pb.RpcObjectSearchSubscribeRequest{SpaceId: space.SpaceId, SubId: "torah-native-wire", Filters: []*model.BlockContentDataviewFilter{filter}, Keys: []string{"id", torah.SourcesKey, torah.LabelsKey}, Limit: 100}, subscribed)
	if len(subscribed.Records) != 1 {
		t.Fatal("native subscription initial membership mismatch")
	}
	waitEvent := func(want string) {
		t.Helper()
		deadline := time.After(45 * time.Second)
		for {
			select {
			case value := <-events:
				if value == want {
					return
				}
			case <-deadline:
				t.Fatal("missing actual subscription event: " + want)
			}
		}
	}
	write("")
	waitEvent("remove")
	wait("ObjectShow removed native value", func() bool { return len(show(document.ObjectId).GetStringList(torah.SourcesKey)) == 0 })
	write(string(payload))
	waitEvent("add")
	wait("ObjectShow restored native value", func() bool {
		values := show(document.ObjectId).GetStringList(torah.SourcesKey)
		return len(values) == 1 && values[0] == identity
	})
	// A derived Property must never offer an alternative per-source option store,
	// including when an older/unadapted client calls the original option API.
	optionRequest := &pb.RpcObjectCreateRelationOptionRequest{SpaceId: space.SpaceId, Details: domain.NewDetails().SetString(bundle.RelationKeyName, "must not exist").SetString(bundle.RelationKeyRelationKey, torah.SourcesKey).ToProto()}
	optionData, _ := proto.Marshal(optionRequest)
	option := &pb.RpcObjectCreateRelationOptionResponse{}
	if err := proto.Unmarshal(service.ObjectCreateRelationOption(optionData), option); err != nil {
		t.Fatal(err)
	}
	if option.Error == nil || option.Error.Code == 0 {
		t.Fatal("derived canonical Property accepted a forbidden Tag option Object")
	}
	// Exercise actual native export boundaries rather than inferring compatibility
	// from the projector's read-only behavior. Local derived values must not become
	// an additional payload that an unmodified importer could treat as synced data.
	for _, format := range []model.ExportFormat{model.Export_Protobuf, model.Export_JSON} {
		exported := &pb.RpcObjectExportResponse{}
		invoke(service.ObjectExport, &pb.RpcObjectExportRequest{SpaceId: space.SpaceId, ObjectId: document.ObjectId, Format: format}, exported)
		snapshot := &pb.SnapshotWithType{}
		if format == model.Export_Protobuf {
			data, err := base64.StdEncoding.DecodeString(exported.Result)
			if err != nil {
				t.Fatal(err)
			}
			if err = proto.Unmarshal(data, snapshot); err != nil {
				t.Fatal(err)
			}
		} else if err := jsonpb.UnmarshalString(exported.Result, snapshot); err != nil {
			t.Fatal(err)
		}
		details := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
		if details.GetString(domain.RelationKey(canonicalKey)) != string(payload) {
			t.Error("native export rewrote canonical bytes/unknown fields")
		}
		for _, key := range torah.LocalKeys() {
			if details.Has(domain.RelationKey(key)) {
				t.Errorf("native export persisted computed local value: format=%v key=%s", format, key)
			}
		}
	}
	for _, id := range show(document.ObjectId).GetStringList(bundle.RelationKeyLinks) {
		if strings.HasPrefix(id, "torah1|") {
			t.Error("canonical identity became a graph Object link")
		}
	}
	for _, id := range show(nativeSet.ObjectId).GetStringList(bundle.RelationKeyLinks) {
		if strings.HasPrefix(id, "torah1|") {
			t.Error("Set predicate identity became a graph Object link")
		}
	}
	wait("native human-label full-text search", func() bool {
		// ObjectSearch is the name-prefix API. Use the same WithMeta full-text
		// command as the original application's global search and inspect its UI text.
		response := &pb.RpcObjectSearchWithMetaResponse{}
		invoke(service.ObjectSearchWithMeta, &pb.RpcObjectSearchWithMetaRequest{SpaceId: space.SpaceId, FullText: "בריאה", Keys: []string{"id"}, ReturnMeta: true, ReturnMetaRelationDetails: true}, response)
		for _, result := range response.Results {
			if result.ObjectId == document.ObjectId {
				for _, meta := range result.Meta {
					if strings.Contains(meta.Highlight, "providerID") || strings.Contains(meta.Highlight, "canonicalKey") {
						t.Error("native search exposed canonical JSON")
					}
					if meta.RelationKey == torah.TopicsKey && strings.Contains(meta.Highlight, "בריאה") {
						return true
					}
				}
			}
		}
		return false
	})
	exportIDs := []string{document.ObjectId, canonical.ObjectId, manifest.ObjectId, nativeSet.ObjectId}
	for _, role := range []string{"chiddush", "article", "research"} {
		exportIDs = append(exportIDs, typeIDs[role])
	}
	exportIDs = append(exportIDs, nativeIDs...)
	emitCompatibilityExports(t, space.SpaceId, exportIDs, "Real native document", string(payload))
	t.Log("PASS real generated middleware APIs: Property registry, Type recommendation, canonical writes, native search/Set/live Details, mutation rejection and native export; zero alternative option Objects")
}

// This verifies the actual production index lifecycle against native SQLite.
// Product API/Set acceptance must additionally run against the approved patched
// Heart. Do not promote this component result to D01-D34 product acceptance.
func TestProductionEngineLifecycleAndRecovery(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "native.db")
	var db anystore.DB
	var objects anystore.Collection
	var index *engine.Index
	var raw engine.Writer
	open := func() {
		var err error
		db, err = anystore.Open(ctx, path, nil)
		if err != nil {
			t.Fatal(err)
		}
		objects, err = db.Collection(ctx, "objects")
		if err != nil {
			t.Fatal(err)
		}
		raw = func(ctx context.Context, id string, d *domain.Details) error {
			d = d.Copy().SetString(bundle.RelationKeyId, id)
			_, err := objects.UpsertId(ctx, id, query.ModifyFunc(func(a *anyenc.Arena, _ *anyenc.Value) (*anyenc.Value, bool, error) { return d.ToAnyEnc(a), true, nil }))
			return err
		}
		index = engine.New("s", objects, db.WriteTx, raw, db.ReadTx)
		if err = index.Recover(ctx); err != nil {
			t.Fatal(err)
		}
	}
	open()
	defer func() { db.Close() }()
	put := func(id string, d *domain.Details) {
		t.Helper()
		if err := index.Update(ctx, id, d); err != nil {
			t.Fatal(err)
		}
	}
	get := func(id string) *domain.Details {
		t.Helper()
		doc, err := objects.FindId(ctx, id)
		if err != nil {
			t.Fatal(err)
		}
		d, err := domain.NewDetailsFromAnyEnc(doc.Value())
		if err != nil {
			t.Fatal(err)
		}
		return d
	}
	manifest := map[string]any{
		"schemaVersion": 1, "spaceId": "s", "manifestObjectId": "manifest", "provisioningState": "complete",
		"documentAssociationsPropertyId": "canonical-property", "documentAssociationsPropertyKey": "customCanonical",
		"registeredDocumentTypes": map[string]string{"chiddush": "h", "article": "a", "research": "r"},
		"defaultTemplateIds":      map[string]string{"chiddush": "th", "article": "ta", "research": "tr"},
		"parentPropertyId":        "parent", "parentPropertyKey": "parentKey", "orderPropertyId": "order", "orderPropertyKey": "orderKey",
		"folderTypeId": "folder", "bookFolderTypeId": "book",
	}
	putManifest := func() {
		payload, _ := json.Marshal(manifest)
		put("manifest", domain.NewDetails().SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).SetString(bundle.RelationKeySpaceId, "s").SetString(bundle.RelationKeyDescription, string(payload)))
	}
	put("canonical-property", domain.NewDetails().SetString(bundle.RelationKeyRelationKey, "customCanonical").SetInt64(bundle.RelationKeyRelationFormat, 0).SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_relation)))
	document := func(raw string) *domain.Details {
		return domain.NewDetails().SetString(bundle.RelationKeySpaceId, "s").SetStringList(bundle.RelationKeyType, []string{"h"}).SetString("customCanonical", raw)
	}
	payload := `{"version":1,"items":[{"id":"source","kind":"ref","role":"context","providerID":"sefaria","canonicalKey":"Genesis 1:1","externalID":"Genesis 1:1","labelHe":"בראשית א:א"}]}`
	put("doc", document(payload))
	if get("doc").Has(torah.SourcesKey) {
		t.Fatal("unbound document was projected")
	}
	putManifest()
	// The real pinned mobile engine uses a scalar Type; retain legacy-list parity.
	put("native-scalar", document(payload).SetString(bundle.RelationKeyType, "h"))
	if len(get("native-scalar").GetStringList(torah.SourcesKey)) != 1 {
		t.Fatal("native scalar Type was not projected")
	}
	identity := torah.Identity(torah.Ref, "sefaria", "Genesis 1:1", "")
	if got := get("doc").GetStringList(torah.SourcesKey); len(got) != 1 || got[0] != identity {
		t.Fatalf("manifest upgrade failed: %v", got)
	}
	if get("manifest").GetInt64(torah.VersionKey) != 1 {
		t.Fatal("no native capability")
	}
	if get("doc").GetString("customCanonical") != payload {
		t.Fatal("canonical bytes changed")
	}
	if !get("doc").GetBool(torah.ReadyKey) {
		t.Fatal("eligible document not ready")
	}
	live, err := index.LocalDetails(ctx, document("").SetString(bundle.RelationKeyId, "doc"))
	if err != nil {
		t.Fatal(err)
	}
	if !live.GetBool(torah.ReadyKey) || live.Has(torah.SourcesKey) {
		t.Fatal("editor projection reused stale indexed canonical data")
	}
	if get("doc").GetStringList(torah.SourcesKey)[0] != identity {
		t.Fatal("read-only editor projection changed the native index")
	}
	if err = index.Recover(ctx); err != nil {
		t.Fatal(err)
	}
	if stats := index.LastRecoveryStats(); !stats.Complete || stats.Reused < 3 {
		t.Fatalf("unchanged persisted projections were decoded again: %+v", stats)
	}
	// An old client can retain the old canonical hash while changing a cached
	// list. Recovery must validate cached outputs as well as the input payload.
	if err = raw(ctx, "doc", get("doc").SetStringList(torah.SourcesKey, []string{"older-client-forged"})); err != nil {
		t.Fatal(err)
	}
	if err = index.Recover(ctx); err != nil {
		t.Fatal(err)
	}
	if got := get("doc").GetStringList(torah.SourcesKey); len(got) != 1 || got[0] != identity {
		t.Fatal("recovery trusted a forged cache with an unchanged canonical hash")
	}
	if stats := index.LastRecoveryStats(); stats.Recomputed < 1 || stats.Reused < 1 {
		t.Fatalf("cache repair/reuse not measured: %+v", stats)
	}
	if err = raw(ctx, "doc", get("doc").SetString("customCanonical", "")); err != nil {
		t.Fatal(err)
	}
	if err = index.Recover(ctx); err != nil {
		t.Fatal(err)
	}
	if !get("doc").GetBool(torah.ReadyKey) || get("doc").Has(torah.SourcesKey) {
		t.Fatal("recovery reused a cache after canonical bytes changed")
	}
	forged := document(payload).SetStringList(torah.SourcesKey, []string{"forged"})
	put("doc", forged)
	if get("doc").GetStringList(torah.SourcesKey)[0] != identity {
		t.Fatal("forged derived value accepted")
	}
	tx, err := db.WriteTx(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if err = index.Update(tx.Context(), "doc", document("")); err != nil {
		t.Fatal(err)
	}
	if err = tx.Rollback(); err != nil {
		t.Fatal(err)
	}
	if get("doc").GetString("customCanonical") != payload {
		t.Fatal("nested rollback changed canonical")
	}
	// A candidate-ID hint introduced by an outer tx is not binding state. Once
	// rolled back, it must not poison future resolution or Space readiness.
	tx, err = db.WriteTx(ctx)
	if err != nil {
		t.Fatal(err)
	}
	duplicate := map[string]any{}
	for key, value := range manifest {
		duplicate[key] = value
	}
	duplicate["manifestObjectId"] = "rolled-back-manifest"
	duplicateRaw, _ := json.Marshal(duplicate)
	if err = index.Update(tx.Context(), "rolled-back-manifest", domain.NewDetails().SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).SetString(bundle.RelationKeyDescription, string(duplicateRaw))); err != nil {
		t.Fatal(err)
	}
	if err = tx.Rollback(); err != nil {
		t.Fatal(err)
	}
	put("doc", document(payload))
	if !get("doc").GetBool(torah.ReadyKey) {
		t.Fatal("rolled-back candidate poisoned binding cache")
	}
	put("doc", document(payload).SetBool(bundle.RelationKeyIsArchived, true))
	if get("doc").GetBool(torah.ReadyKey) || get("doc").Has(torah.SourcesKey) {
		t.Fatal("archived membership retained")
	}
	put("doc", document(payload))
	if !get("doc").GetBool(torah.ReadyKey) {
		t.Fatal("unarchive did not restore canonical membership")
	}
	put("malformed", document(`{"version":900}`))
	if get("malformed").GetBool(torah.ReadyKey) || get("malformed").Has(torah.SourcesKey) {
		t.Fatal("future payload matched empty/negative predicates")
	}
	put("foreign", document(payload).SetString(bundle.RelationKeySpaceId, "foreign"))
	if get("foreign").GetBool(torah.ReadyKey) {
		t.Fatal("foreign Space indexed")
	}
	// Simulate a missing/stale local index, retaining the only canonical source.
	if err = raw(ctx, "doc", document(payload)); err != nil {
		t.Fatal(err)
	}
	if err = db.Close(); err != nil {
		t.Fatal(err)
	}
	open()
	if get("doc").GetStringList(torah.SourcesKey)[0] != identity {
		t.Fatal("relaunch recovery failed")
	}
	if get("doc").GetString(torah.LabelsKey) == "" {
		t.Fatal("labels not rebuilt")
	}
	plan, err := objects.Find(map[string]any{torah.SourcesKey: identity}).Explain(ctx)
	if err != nil {
		t.Fatal(err)
	}
	indexed := false
	for _, idx := range plan.Indexes {
		indexed = indexed || (idx.Name == torah.SourcesKey && idx.Used)
	}
	if !indexed {
		t.Fatalf("native membership index not used: %+v", plan)
	}
	manifest["registeredDocumentTypes"] = map[string]string{"chiddush": "new-h", "article": "a", "research": "r"}
	putManifest()
	if get("doc").GetBool(torah.ReadyKey) || get("doc").Has(torah.SourcesKey) {
		t.Fatal("old Type membership survived manifest change")
	}
	if get("doc").GetString("customCanonical") != payload {
		t.Fatal("rebind rewrote associations")
	}
	manifest["registeredDocumentTypes"] = map[string]string{"chiddush": "h", "article": "a", "research": "r"}
	putManifest()
	if err = index.Delete(ctx, []string{"canonical-property"}, func(ctx context.Context) error { return objects.DeleteId(ctx, "canonical-property") }); err != nil {
		t.Fatal(err)
	}
	if get("doc").GetBool(torah.ReadyKey) || get("manifest").Has(torah.VersionKey) {
		t.Fatal("deleted canonical property left ready state")
	}
	count, err := objects.Count(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if count != 5 {
		t.Fatalf("unexpected generated objects/options: %d", count)
	}
}
