package service

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/jsonpb"
	"github.com/gogo/protobuf/proto"
)

// Linked separately into each exact native revision; not a production capability.
var accountPairFixtureSHA = "UNSET"

type t5AccountPairDocument struct {
	ID        string
	BlockID   string
	Role      string
	Name      string
	Canonical string
}

type t5AccountPairState struct {
	AccountID    string
	SpaceID      string
	ManifestID   string
	ManifestRaw  string
	CanonicalKey string
	Documents    []t5AccountPairDocument
}

type t5AccountPairRPC struct {
	t     *testing.T
	calls map[string]int
}

func (r *t5AccountPairRPC) raw(call func([]byte) []byte, request, response proto.Message) {
	r.t.Helper()
	name := strings.TrimSuffix(strings.TrimPrefix(reflect.TypeOf(request).Elem().Name(), "Rpc"), "Request")
	r.calls[name]++
	data, err := proto.Marshal(request)
	if err != nil {
		r.t.Fatal("could not marshal native request")
	}
	if err = proto.Unmarshal(call(data), response); err != nil {
		r.t.Fatal("could not decode native response")
	}
}

func (r *t5AccountPairRPC) check(response proto.Message) {
	r.t.Helper()
	field := reflect.ValueOf(response).Elem().FieldByName("Error")
	if field.IsValid() && !field.IsNil() && field.Elem().FieldByName("Code").Int() != 0 {
		// Never print request/response values: a wallet response contains a key.
		r.t.Fatalf("%T returned native error code %d", response, field.Elem().FieldByName("Code").Int())
	}
}

func (r *t5AccountPairRPC) invoke(call func([]byte) []byte, request, response proto.Message) {
	r.t.Helper()
	r.raw(call, request, response)
	r.check(response)
}

func (r *t5AccountPairRPC) show(space, id string) (*pb.RpcObjectShowResponse, *domain.Details) {
	r.t.Helper()
	shown := &pb.RpcObjectShowResponse{}
	r.invoke(ObjectShow, &pb.RpcObjectShowRequest{SpaceId: space, ObjectId: id, ContextId: id}, shown)
	if shown.ObjectView == nil || shown.ObjectView.RootId != id {
		r.t.Fatal("ObjectShow did not return the exact requested root")
	}
	for _, row := range shown.ObjectView.Details {
		if row.Id == id {
			details := domain.NewDetailsFromProto(row.Details)
			if details.GetString(bundle.RelationKeyId) != id || details.GetString(bundle.RelationKeySpaceId) != space {
				r.t.Fatal("ObjectShow identity or Space changed")
			}
			return shown, details
		}
	}
	r.t.Fatal("ObjectShow omitted the requested object")
	return nil, nil
}

func (r *t5AccountPairRPC) wait(label string, predicate func() bool) {
	r.t.Helper()
	deadline := time.Now().Add(45 * time.Second)
	for time.Now().Before(deadline) {
		if predicate() {
			return
		}
		time.Sleep(100 * time.Millisecond)
	}
	r.t.Fatal("native account-pair timeout: " + label)
}

func t5PairHash(data []byte) string {
	result := sha256.Sum256(data)
	return hex.EncodeToString(result[:])
}

func t5PairWrite(t *testing.T, path string, data []byte) {
	t.Helper()
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		t.Fatal("fresh controller-owned output required")
	}
	if _, err = file.Write(data); err != nil {
		file.Close()
		t.Fatal("could not preserve native evidence")
	}
	if err = file.Close(); err != nil {
		t.Fatal("could not close native evidence")
	}
}

func t5PairBlock(t *testing.T, root, target string, blocks []*model.Block) string {
	t.Helper()
	byID := map[string]*model.Block{}
	for _, block := range blocks {
		if block == nil || block.Id == "" || byID[block.Id] != nil {
			t.Fatal("invalid or duplicate block graph node")
		}
		byID[block.Id] = block
	}
	if target == "" || target == root || byID[root] == nil {
		t.Fatal("real reachable leaf block required")
	}
	queue, seen := []string{root}, map[string]bool{}
	for len(queue) > 0 {
		id := queue[0]
		queue = queue[1:]
		if seen[id] {
			continue
		}
		seen[id] = true
		block := byID[id]
		if block == nil {
			t.Fatal("block graph contains a missing child")
		}
		if id == target {
			text := block.GetText()
			if text == nil || text.Text != "T5 preserved real block sentinel" {
				t.Fatal("real block text or identity changed")
			}
			raw, _ := json.Marshal(map[string]string{"id": id, "text": text.Text})
			return t5PairHash(raw)
		}
		queue = append(queue, block.ChildrenIds...)
		if len(seen) > 10000 {
			t.Fatal("unexpectedly large disposable block graph")
		}
	}
	t.Fatal("canonical leaf target is unreachable from the actual root")
	return ""
}

func (r *t5AccountPairRPC) create(state *t5AccountPairState) {
	space := &pb.RpcWorkspaceCreateResponse{}
	r.invoke(WorkspaceCreate, &pb.RpcWorkspaceCreateRequest{Details: domain.NewDetails().
		SetString(bundle.RelationKeyName, "T5 disposable same-account pair").ToProto()}, space)
	state.SpaceID = space.SpaceId
	r.invoke(WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{})
	manifest := &pb.RpcObjectCreateResponse{}
	initial, _ := json.Marshal(map[string]any{"schemaVersion": 1, "spaceId": state.SpaceID, "provisioningState": "inProgress"})
	r.invoke(ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: state.SpaceID, ObjectTypeUniqueKey: "ot-page",
		Details: domain.NewDetails().SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).
			SetString(bundle.RelationKeyUniqueKey, torah.ManifestUniqueKey).
			SetString(bundle.RelationKeyDescription, string(initial)).SetBool(bundle.RelationKeyIsHidden, true).ToProto()}, manifest)
	state.ManifestID = manifest.ObjectId
	canonical := &pb.RpcObjectCreateRelationResponse{}
	r.invoke(ObjectCreateRelation, &pb.RpcObjectCreateRelationRequest{SpaceId: state.SpaceID,
		Details: domain.NewDetails().SetString(bundle.RelationKeyName, "T5 opaque canonical payload").
			SetInt64(bundle.RelationKeyRelationFormat, 0).ToProto()}, canonical)
	state.CanonicalKey = domain.NewDetailsFromProto(canonical.Details).GetString(bundle.RelationKeyRelationKey)
	if state.CanonicalKey == "" {
		r.t.Fatal("canonical native property key missing")
	}
	typeIDs, typeKeys := map[string]string{}, map[string]string{}
	for _, role := range []string{"chiddush", "article", "research"} {
		created := &pb.RpcObjectCreateObjectTypeResponse{}
		r.invoke(ObjectCreateObjectType, &pb.RpcObjectCreateObjectTypeRequest{SpaceId: state.SpaceID,
			Details: domain.NewDetails().SetString(bundle.RelationKeyName, role).
				SetInt64(bundle.RelationKeyRecommendedLayout, int64(model.ObjectType_basic)).ToProto()}, created)
		typeIDs[role] = created.ObjectId
		typeKeys[role] = domain.NewDetailsFromProto(created.Details).GetString(bundle.RelationKeyUniqueKey)
	}
	manifestRaw, _ := json.Marshal(map[string]any{"schemaVersion": 1, "spaceId": state.SpaceID,
		"manifestObjectId": state.ManifestID, "provisioningState": "complete",
		"documentAssociationsPropertyId": canonical.ObjectId, "documentAssociationsPropertyKey": state.CanonicalKey,
		"registeredDocumentTypes": typeIDs,
		"defaultTemplateIds":      map[string]string{"chiddush": "unused-th", "article": "unused-ta", "research": "unused-tr"},
		"parentPropertyId":        "unused-p", "parentPropertyKey": "unusedPk", "orderPropertyId": "unused-o",
		"orderPropertyKey": "unusedOk", "folderTypeId": "unused-f", "bookFolderTypeId": "unused-b",
		"unknownManifestField": map[string]string{"preserve": "unchanged"}})
	state.ManifestRaw = string(manifestRaw)
	r.invoke(ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: state.ManifestID,
		Details: []*model.Detail{{Key: "description", Value: domain.String(state.ManifestRaw).ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
	r.wait("native manifest binding", func() bool {
		_, d := r.show(state.SpaceID, state.ManifestID)
		return d.GetInt64(torah.VersionKey) == 1
	})
	for _, definition := range torah.Definitions {
		r.invoke(ObjectCreateRelation, &pb.RpcObjectCreateRelationRequest{SpaceId: state.SpaceID,
			Details: domain.NewDetails().SetString(bundle.RelationKeyName, definition.Name).
				SetString(bundle.RelationKeyRelationKey, definition.Key).SetInt64(bundle.RelationKeyRelationFormat, 11).
				SetBool(bundle.RelationKeyRelationReadonlyValue, true).ToProto()}, &pb.RpcObjectCreateRelationResponse{})
	}
	for index, typeKey := range []string{"ot-page", "ot-note", typeKeys["chiddush"]} {
		doc := t5AccountPairDocument{Name: "T5 preserved document", Role: "context"}
		created := &pb.RpcObjectCreateResponse{}
		r.invoke(ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: state.SpaceID, ObjectTypeUniqueKey: typeKey,
			Details: domain.NewDetails().SetString(bundle.RelationKeyName, doc.Name).ToProto()}, created)
		doc.ID = created.ObjectId
		if index > 0 {
			block := &pb.RpcBlockCreateResponse{}
			r.invoke(BlockCreate, &pb.RpcBlockCreateRequest{ContextId: doc.ID, TargetId: doc.ID, Position: model.Block_Inner,
				Block: &model.Block{Content: &model.BlockContentOfText{Text: &model.BlockContentText{
					Text: "T5 preserved real block sentinel"}}}}, block)
			doc.BlockID = block.BlockId
			if doc.BlockID == "" {
				r.t.Fatal("real BlockCreate returned no block identity")
			}
		}
		if index == 2 {
			doc.Role = "sourceQuote"
		}
		record := map[string]any{"spaceId": state.SpaceID, "objectId": doc.ID,
			"unknownRecord": map[string]string{"preserve": "unchanged"},
			"item": map[string]string{"id": "pair-ref", "kind": "ref", "role": doc.Role, "providerID": "sefaria",
				"canonicalKey": "Genesis 3:3", "externalID": "Genesis 3:3", "labelHe": "source",
				"unknownItem": "preserve"}}
		if doc.BlockID != "" {
			record["blockId"] = doc.BlockID
		}
		raw, _ := json.Marshal(map[string]any{"version": 2, "unknownRoot": "preserve", "records": []any{record}})
		doc.Canonical = string(raw)
		r.invoke(ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: doc.ID,
			Details: []*model.Detail{{Key: state.CanonicalKey, Value: domain.String(doc.Canonical).ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
		state.Documents = append(state.Documents, doc)
	}
}

// Four real application processes must reopen the same synthetic account and
// original object/block identities. No account is recreated in later phases.
func TestT5AccountCompatibilityPairPhase(t *testing.T) {
	const protocol = "pinkha-t5-account-pair-v1"
	phase, role := os.Getenv("PINKHA_ACCOUNT_PAIR_PHASE"), os.Getenv("PINKHA_ACCOUNT_PAIR_ROLE")
	root, reportPath := os.Getenv("PINKHA_ACCOUNT_PAIR_ROOT"), os.Getenv("PINKHA_ACCOUNT_PAIR_REPORT")
	nonce, patch := os.Getenv("PINKHA_ACCOUNT_PAIR_NONCE"), os.Getenv("PINKHA_ACCOUNT_PAIR_PATCH_SHA")
	roles := map[string]string{"old-create": "old", "new-upgrade": "new", "old-edit": "old", "new-recover": "new"}
	patches := map[string]string{"old": "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077",
		"new": "5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2"}
	if roles[phase] != role || patches[role] != patch || nonce == "" || root == "" || reportPath == "" ||
		accountPairFixtureSHA == "UNSET" || accountPairFixtureSHA != os.Getenv("PINKHA_ACCOUNT_PAIR_FIXTURE_SHA") ||
		vcs.GitCommit != "d98420b1113536afd08cde6de9a5816f6d27ffff" {
		t.Fatal("exact native phase/controller/build identities required")
	}
	root, err := filepath.Abs(root)
	if err != nil {
		t.Fatal(err)
	}
	parent := filepath.Dir(root)
	if filepath.Base(root) != "account-root" || filepath.Dir(reportPath) != parent ||
		filepath.Base(reportPath) != phase+".json" {
		t.Fatal("controller-owned account and report paths required")
	}
	owner, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	var ownership struct {
		Protocol      string `json:"protocol"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	if err != nil || string(owner) != os.Getenv("PINKHA_ACCOUNT_PAIR_OWNER_TOKEN") ||
		json.Unmarshal(owner, &ownership) != nil || ownership.Protocol != protocol || !ownership.SyntheticOnly {
		t.Fatal("fresh disposable account ownership required")
	}
	statePath, secretPath := filepath.Join(parent, "state.json"), filepath.Join(parent, "account-key.private")
	state := t5AccountPairState{}
	if phase == "old-create" {
		entries, err := os.ReadDir(root)
		if err != nil || len(entries) != 0 {
			t.Fatal("first process requires an empty fresh account root")
		}
	} else {
		data, err := os.ReadFile(statePath)
		if err != nil || json.Unmarshal(data, &state) != nil || state.AccountID == "" ||
			filepath.Base(state.AccountID) != state.AccountID || len(state.Documents) != 3 {
			t.Fatal("prior phase's exact account contract required")
		}
		entries, err := os.ReadDir(filepath.Join(root, state.AccountID))
		if err != nil || len(entries) == 0 {
			t.Fatal("existing nonempty account directory required; recreation is forbidden")
		}
	}
	rpc := &t5AccountPairRPC{t: t, calls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	rpc.invoke(InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0",
		Workdir: root, DoNotSendLogs: true, DoNotSaveLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	version := &pb.RpcAppGetVersionResponse{}
	rpc.invoke(AppGetVersion, &pb.RpcAppGetVersionRequest{}, version)
	expectedVersion := "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + patch
	if role == "new" {
		expectedVersion += "-pinkha-native-t5-lookup-v1-" + patch
	}
	if version.Version != expectedVersion || vcs.GitSummary != expectedVersion {
		t.Fatal("running native AppGetVersion and linked revision differ")
	}
	started, closed := false, false
	shutdown := func() {
		if started && !closed {
			rpc.invoke(AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{})
			closed = true
		}
	}
	t.Cleanup(shutdown)
	if phase == "old-create" {
		wallet := &pb.RpcWalletCreateResponse{}
		rpc.invoke(WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, wallet)
		if wallet.AccountKey == "" {
			t.Fatal("synthetic wallet key missing")
		}
		// This file is never copied to the evidence or binary artifacts.
		t5PairWrite(t, secretPath, []byte(wallet.AccountKey))
		secretNeedles, err := json.Marshal([]string{wallet.AccountKey, wallet.Mnemonic})
		if err != nil || wallet.Mnemonic == "" {
			t.Fatal("synthetic secret guard could not be initialized")
		}
		t5PairWrite(t, filepath.Join(parent, "sensitive-needles.private"), secretNeedles)
		account := &pb.RpcAccountCreateResponse{}
		rpc.invoke(AccountCreate, &pb.RpcAccountCreateRequest{Name: "T5 disposable account pairing",
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true}, account)
		started = true
		if account.Account == nil || account.Account.Id == "" {
			t.Fatal("real native account identity missing")
		}
		state.AccountID = account.Account.Id
		rpc.create(&state)
		data, err := json.Marshal(state)
		if err != nil {
			t.Fatal(err)
		}
		t5PairWrite(t, statePath, data)
	} else {
		key, err := os.ReadFile(secretPath)
		if err != nil || len(key) == 0 {
			t.Fatal("prior synthetic account key unavailable")
		}
		rpc.invoke(WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)}, &pb.RpcWalletRecoverResponse{})
		request := &pb.RpcAccountSelectRequest{Id: state.AccountID, RootPath: root,
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true, PreferredSpaceId: state.SpaceID}
		selected := &pb.RpcAccountSelectResponse{}
		rpc.raw(AccountSelect, request, selected)
		if selected.Error != nil && selected.Error.Code == pb.RpcAccountSelectResponseError_ACCOUNT_STORE_NOT_MIGRATED {
			rpc.invoke(AccountMigrate, &pb.RpcAccountMigrateRequest{Id: state.AccountID, RootPath: root}, &pb.RpcAccountMigrateResponse{})
			selected = &pb.RpcAccountSelectResponse{}
			rpc.invoke(AccountSelect, request, selected)
		} else {
			rpc.check(selected)
		}
		started = true
		if selected.Account == nil || selected.Account.Id != state.AccountID {
			t.Fatal("reopened a different native account")
		}
		rpc.invoke(WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{})
	}
	if phase == "old-edit" {
		rpc.invoke(ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: state.Documents[0].ID,
			Details: []*model.Detail{{Key: "name", Value: domain.String("T5 ordinary title edited by r14").ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
	}
	canonical, public, blockHashes := map[string]string{}, map[string]string{}, map[string]string{}
	versions := map[string]int64{}
	ordinaryNames := map[string]string{}
	_, manifest := rpc.show(state.SpaceID, state.ManifestID)
	if manifest.GetString(bundle.RelationKeyDescription) != state.ManifestRaw {
		t.Fatal("canonical manifest or unknown fields changed")
	}
	canonical[state.ManifestID] = t5PairHash([]byte(state.ManifestRaw))
	publicKeys := []domain.RelationKey{torah.SourcesKey, torah.TopicsKey, torah.WordsKey, torah.LabelsKey,
		torah.ReadyKey, torah.VersionKey, torah.CanonicalHashKey, torah.StatusKey, torah.CanonicalKeyKey}
	exportDir := filepath.Join(parent, "exports", phase)
	if err := os.MkdirAll(exportDir, 0700); err != nil {
		t.Fatal(err)
	}
	exports := map[string]string{}
	for index, doc := range state.Documents {
		rpc.wait("live canonical projection", func() bool {
			_, d := rpc.show(state.SpaceID, doc.ID)
			return d.GetBool(torah.ReadyKey) && d.GetString(domain.RelationKey(state.CanonicalKey)) == doc.Canonical
		})
		view, d := rpc.show(state.SpaceID, doc.ID)
		wantName := doc.Name
		if index == 0 && (phase == "old-edit" || phase == "new-recover") {
			wantName = "T5 ordinary title edited by r14"
		}
		if d.GetString(bundle.RelationKeyName) != wantName {
			t.Fatal("ordinary title edit was lost or changed at the wrong phase")
		}
		ordinaryNames[doc.ID] = d.GetString(bundle.RelationKeyName)
		canonical[doc.ID] = t5PairHash([]byte(d.GetString(domain.RelationKey(state.CanonicalKey))))
		rawPublic, _ := json.Marshal(d.CopyOnlyKeys(publicKeys...).ToProto())
		public[doc.ID] = t5PairHash(rawPublic)
		versions[doc.ID] = d.GetInt64("_pinkhaTorahRelatedVersion")
		if role == "new" && versions[doc.ID] != 1 {
			t.Fatal("new running runtime did not recover the private projection")
		}
		if doc.BlockID != "" {
			blockHashes[doc.ID] = t5PairBlock(t, doc.ID, doc.BlockID, view.ObjectView.Blocks)
		}
		for _, format := range []model.ExportFormat{model.Export_Protobuf, model.Export_JSON} {
			response := &pb.RpcObjectExportResponse{}
			rpc.invoke(ObjectExport, &pb.RpcObjectExportRequest{SpaceId: state.SpaceID, ObjectId: doc.ID, Format: format}, response)
			snapshot := &pb.SnapshotWithType{}
			raw, extension := []byte(response.Result), "json"
			if format == model.Export_Protobuf {
				extension = "pbc"
				raw, err = base64.StdEncoding.DecodeString(response.Result)
				if err != nil || proto.Unmarshal(raw, snapshot) != nil {
					t.Fatal("invalid actual Protobuf export")
				}
			} else if jsonpb.UnmarshalString(response.Result, snapshot) != nil {
				t.Fatal("invalid actual JSON export")
			}
			if snapshot.Snapshot == nil || snapshot.Snapshot.Data == nil {
				t.Fatal("native export snapshot data missing")
			}
			exported := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
			if exported.GetString(domain.RelationKey(state.CanonicalKey)) != doc.Canonical ||
				exported.GetString(bundle.RelationKeyName) != wantName {
				t.Fatal("native export changed canonical/unknown data or the ordinary edit")
			}
			keys := append(append([]string{}, torah.LocalKeys()...), "_pinkhaTorahRelatedSources", "_pinkhaTorahRelatedVersion")
			for _, key := range keys {
				if exported.Has(domain.RelationKey(key)) {
					t.Fatalf("actual export leaked local derived field %s", key)
				}
			}
			if doc.BlockID != "" {
				found := false
				for _, block := range snapshot.Snapshot.Data.Blocks {
					if block.Id == doc.BlockID && block.GetText() != nil &&
						block.GetText().Text == "T5 preserved real block sentinel" {
						found = true
					}
				}
				if !found {
					t.Fatal("actual native export lost real block identity or text")
				}
			}
			name := []string{"document", "block", "quote"}[index] + "." + extension
			t5PairWrite(t, filepath.Join(exportDir, name), raw)
			exports[name] = t5PairHash(raw)
		}
	}
	identity := torah.Identity(torah.Ref, "sefaria", "Genesis 3:3", "")
	query := func(key string, expected []string) []string {
		t.Helper()
		sort.Strings(expected)
		observed := []string{}
		rpc.wait("indexed native membership", func() bool {
			response := &pb.RpcObjectSearchResponse{}
			rpc.invoke(ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: state.SpaceID,
				Filters: []*model.BlockContentDataviewFilter{{RelationKey: key,
					Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList([]string{identity}).ToProto()}},
				Keys: []string{"id"}, Limit: 20}, response)
			ids := []string{}
			for _, row := range response.Records {
				ids = append(ids, domain.NewDetailsFromProto(row).GetString(bundle.RelationKeyId))
			}
			sort.Strings(ids)
			observed = ids
			return reflect.DeepEqual(ids, expected)
		})
		return observed
	}
	publicMembers := query(torah.SourcesKey, []string{state.Documents[0].ID})
	privateMembers := []string{}
	privateStatus := "NOT_ATTEMPTED_RUNTIME_UNAVAILABLE"
	if role == "new" {
		ids := []string{}
		for _, doc := range state.Documents {
			ids = append(ids, doc.ID)
		}
		privateMembers = query("_pinkhaTorahRelatedSources", ids)
		privateStatus = "EXECUTED"
	}
	shutdown()
	if !closed {
		t.Fatal("native application did not shut down")
	}
	stateBytes, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	report := map[string]any{"protocol": protocol, "phase": phase, "pid": os.Getpid(), "nonce": nonce,
		"heart_sha": vcs.GitCommit, "patch_sha256": patch, "fixture_sha256": accountPairFixtureSHA,
		"runtime_version": version.Version, "account_root": root, "account_id": state.AccountID,
		"space_id": state.SpaceID, "state_sha256": t5PairHash(stateBytes), "closed": true, "test_passed": true,
		"canonical_sha256": canonical, "public_sha256": public, "block_sha256": blockHashes,
		"private_versions": versions, "private_query_status": privateStatus, "exports": exports,
		"ordinary_names": ordinaryNames, "public_members": publicMembers, "private_members": privateMembers,
		"export_status": "ACTUAL_JSON_AND_PROTOBUF", "rpc_calls": rpc.calls,
		"client_enablement": "DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF", "swift_pairing_status": "NOT_RUN",
		"scope": "actual native RPC same-account processes; no Apple packaged app or physical UI proof"}
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	t5PairWrite(t, reportPath, data)
	t.Log("PASS same native account and exact object/block identities; actual JSON/Protobuf exports and closed app")
}
