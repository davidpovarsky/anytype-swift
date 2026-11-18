package service

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/anytype-heart/core/anytype/config"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/datastore/anystoreprovider"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/jsonpb"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

// These markers are linked into separately source-verified test binaries. They
// are fixture identities, not a new public App RPC or an enabled capability.
var t2AccountFixtureSHA = "UNSET"
var t2AccountRuntimeRole = "UNSET"
var t2AccountRegistrationSHA = "UNSET"

const t2AccountProtocol = "pinkha-t2-account-lifecycle-v1"
const t2HeartPin = "d98420b1113536afd08cde6de9a5816f6d27ffff"
const t2LegacyPatch = "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077"
const t2VisibleToken = "t2visiblejournalcontrolc729"
const t2PrivateToken = "t2privatejournalcontentc729"
const t2PrivatePayload = `{"fixture":"t2privatejournalcontentc729","unknown":{"keep":true}}`

type t2AccountState struct {
	AccountID       string
	SpaceID         string
	DocumentID      string
	BlockID         string
	RootID          string
	OperationID     string
	OperationSHA256 string
	ClaimID         string
	ChangeID        string
	RawChanges      map[string]string
	Heads           []string
}

type t2AccountRPC struct {
	t     *testing.T
	calls map[string]int
}

func (r *t2AccountRPC) raw(call func([]byte) []byte, request, response proto.Message) {
	r.t.Helper()
	name := strings.TrimSuffix(strings.TrimPrefix(reflect.TypeOf(request).Elem().Name(), "Rpc"), "Request")
	r.calls[name]++
	data, err := proto.Marshal(request)
	require.NoError(r.t, err, "marshal native request")
	require.NoError(r.t, proto.Unmarshal(call(data), response), "decode native response")
}

func (r *t2AccountRPC) check(response proto.Message) {
	r.t.Helper()
	field := reflect.ValueOf(response).Elem().FieldByName("Error")
	if field.IsValid() && !field.IsNil() && field.Elem().FieldByName("Code").Int() != 0 {
		// Never print wallet request/response values or a recovered secret.
		r.t.Fatalf("%T returned native error code %d", response, field.Elem().FieldByName("Code").Int())
	}
}

func (r *t2AccountRPC) invoke(call func([]byte) []byte, request, response proto.Message) {
	r.raw(call, request, response)
	r.check(response)
}

func t2Hash(data []byte) string {
	value := sha256.Sum256(data)
	return hex.EncodeToString(value[:])
}

func t2WriteFresh(t *testing.T, path string, data []byte) {
	t.Helper()
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	require.NoError(t, err, "fresh controller-owned output required")
	_, err = file.Write(data)
	require.NoError(t, err)
	require.NoError(t, file.Sync())
	require.NoError(t, file.Close())
}

func (r *t2AccountRPC) wait(label string, predicate func() bool) {
	r.t.Helper()
	deadline := time.Now().Add(45 * time.Second)
	for time.Now().Before(deadline) {
		if predicate() {
			return
		}
		time.Sleep(100 * time.Millisecond)
	}
	r.t.Fatal("native account lifecycle timeout: " + label)
}

func t2Space(t *testing.T, id string) clientspace.Space {
	t.Helper()
	require.NotNil(t, mw.GetApp(), "real native account must be running")
	spc, err := app.MustComponent[space.Service](mw.GetApp()).Get(context.Background(), id)
	require.NoError(t, err)
	require.Equal(t, id, spc.Id())
	return spc
}

func (r *t2AccountRPC) show(spaceID, id string) *pb.RpcObjectShowResponse {
	r.t.Helper()
	response := &pb.RpcObjectShowResponse{}
	r.invoke(ObjectShow, &pb.RpcObjectShowRequest{SpaceId: spaceID, ObjectId: id, ContextId: id}, response)
	require.NotNil(r.t, response.ObjectView)
	require.Equal(r.t, id, response.ObjectView.RootId)
	return response
}

func t2ShownDetails(t *testing.T, shown *pb.RpcObjectShowResponse, state *t2AccountState) *domain.Details {
	t.Helper()
	for _, row := range shown.ObjectView.Details {
		if row.Id == state.DocumentID {
			details := domain.NewDetailsFromProto(row.Details)
			require.Equal(t, state.DocumentID, details.GetString(bundle.RelationKeyId))
			require.Equal(t, state.SpaceID, details.GetString(bundle.RelationKeySpaceId))
			return details
		}
	}
	t.Fatal("ordinary target details missing from actual ObjectShow")
	return nil
}

func (r *t2AccountRPC) search(state *t2AccountState, fulltext, id string) []string {
	r.t.Helper()
	request := &pb.RpcObjectSearchRequest{SpaceId: state.SpaceID, FullText: fulltext, Keys: []string{"id"}, Limit: 100}
	if id != "" {
		request.Filters = []*model.BlockContentDataviewFilter{{RelationKey: "id",
			Condition: model.BlockContentDataviewFilter_Equal, Value: domain.String(id).ToProto()}}
	}
	response := &pb.RpcObjectSearchResponse{}
	r.invoke(ObjectSearch, request, response)
	ids := []string{}
	for _, record := range response.Records {
		value := domain.NewDetailsFromProto(record).GetString(bundle.RelationKeyId)
		require.NotEmpty(r.t, value)
		ids = append(ids, value)
	}
	sort.Strings(ids)
	return ids
}

func (r *t2AccountRPC) createTarget(state *t2AccountState) {
	createdSpace := &pb.RpcWorkspaceCreateResponse{}
	r.invoke(WorkspaceCreate, &pb.RpcWorkspaceCreateRequest{Details: domain.NewDetails().
		SetString(bundle.RelationKeyName, "T2 disposable native lifecycle").ToProto()}, createdSpace)
	state.SpaceID = createdSpace.SpaceId
	require.NotEmpty(r.t, state.SpaceID)
	r.invoke(WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{})
	// Readiness is a read-only precondition. Never retry object creation after
	// an ambiguous native response. Wait for Page in the actual native index.
	r.wait("indexed native Page type", func() bool {
		response := &pb.RpcObjectSearchResponse{}
		r.invoke(ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: state.SpaceID,
			Filters: []*model.BlockContentDataviewFilter{{RelationKey: "uniqueKey",
				Condition: model.BlockContentDataviewFilter_Equal, Value: domain.String("ot-page").ToProto()}},
			Keys: []string{"id", "spaceId", "uniqueKey"}, Limit: 2}, response)
		if len(response.Records) == 0 {
			return false
		}
		require.Len(r.t, response.Records, 1, "unambiguous native Page type required")
		d := domain.NewDetailsFromProto(response.Records[0])
		require.Equal(r.t, state.SpaceID, d.GetString(bundle.RelationKeySpaceId))
		require.Equal(r.t, "ot-page", d.GetString(bundle.RelationKeyUniqueKey))
		require.NotEmpty(r.t, d.GetString(bundle.RelationKeyId))
		return true
	})
	created := &pb.RpcObjectCreateResponse{}
	r.invoke(ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: state.SpaceID, ObjectTypeUniqueKey: "ot-page",
		Details: domain.NewDetails().SetString(bundle.RelationKeyName, t2VisibleToken).ToProto()}, created)
	state.DocumentID = created.ObjectId
	require.NotEmpty(r.t, state.DocumentID)
	block := &pb.RpcBlockCreateResponse{}
	r.invoke(BlockCreate, &pb.RpcBlockCreateRequest{ContextId: state.DocumentID, TargetId: state.DocumentID,
		Position: model.Block_Inner, Block: &model.Block{Content: &model.BlockContentOfText{
			Text: &model.BlockContentText{Text: t2VisibleToken}}}}, block)
	state.BlockID = block.BlockId
	require.NotEmpty(r.t, state.BlockID)
}

// Enumerate raw native storage without teaching the legacy client's registry
// the private type. No history decoder, replay helper or write is used here.
func t2RawHistory(t *testing.T, state *t2AccountState) (map[string]string, []string) {
	t.Helper()
	ctx := context.Background()
	spc := t2Space(t, state.SpaceID)
	storage, err := spc.Storage().TreeStorage(ctx, state.RootID)
	require.NoError(t, err)
	require.Equal(t, state.RootID, storage.Id())
	root, err := storage.Root(ctx)
	require.NoError(t, err)
	require.Equal(t, state.RootID, root.Id)
	entry, err := spc.Storage().HeadStorage().GetEntry(ctx, state.RootID)
	require.NoError(t, err)
	require.Equal(t, headstorage.DeletedStatusNotDeleted, entry.DeletedStatus)
	require.True(t, entry.IsDerived)
	require.Empty(t, entry.ParentId)
	// Upstream genesis has AddSeq zero; GetAfterAddSeq is strictly greater.
	// Hash the root directly, then enumerate every appended native change.
	values := map[string]string{root.Id: t2Hash(root.RawChange)}
	err = storage.GetAfterAddSeq(ctx, 0, func(_ context.Context, change objecttree.StorageChange) (bool, error) {
		// GetAfterAddSeq is filtered by this storage ID. Upstream
		// changeFromDoc does not populate TreeId; verify the actual
		// acknowledged change and its parent in the retained history.
		require.Equal(t, state.ChangeID, change.Id)
		require.Equal(t, []string{state.RootID}, change.PrevIds)
		require.NotContains(t, values, change.Id)
		values[change.Id] = t2Hash(change.RawChange)
		return true, nil
	})
	require.NoError(t, err)
	require.Len(t, values, 2, "exactly one immutable operation plus its root must remain")
	require.Equal(t, t2Hash(root.RawChange), values[state.RootID])
	require.NotEmpty(t, values[state.ChangeID])
	heads, err := storage.Heads(ctx)
	require.NoError(t, err)
	sort.Strings(heads)
	require.Equal(t, []string{state.ChangeID}, heads)
	require.Equal(t, heads, entry.Heads)
	return values, heads
}

func (r *t2AccountRPC) visibleAndHiddenEvidence(state *t2AccountState, phase, parent string) map[string]any {
	shown := r.show(state.SpaceID, state.DocumentID)
	details := t2ShownDetails(r.t, shown, state)
	wantName := t2VisibleToken
	if phase == "legacy-edit" || phase == "new-recover" {
		wantName += " edited by legacy"
	}
	require.Equal(r.t, wantName, details.GetString(bundle.RelationKeyName))
	foundBlock := false
	for _, block := range shown.ObjectView.Blocks {
		if block.Id == state.BlockID {
			require.NotNil(r.t, block.GetText())
			require.Equal(r.t, t2VisibleToken, block.GetText().Text)
			foundBlock = true
		}
	}
	require.True(r.t, foundBlock, "original actual block must survive every process")
	r.wait("positive ordinary fulltext control", func() bool {
		return reflect.DeepEqual(r.search(state, t2VisibleToken, ""), []string{state.DocumentID})
	})
	require.Equal(r.t, []string{state.DocumentID}, r.search(state, "", state.DocumentID))
	require.Empty(r.t, r.search(state, "", state.RootID), "private host cannot appear even in an exact-ID indexed query")
	require.Empty(r.t, r.search(state, t2PrivateToken, ""), "encrypted private payload must not enter ordinary fulltext")
	privateShow := &pb.RpcObjectShowResponse{}
	r.raw(ObjectShow, &pb.RpcObjectShowRequest{SpaceId: state.SpaceID, ObjectId: state.RootID, ContextId: state.RootID}, privateShow)
	require.NotNil(r.t, privateShow.Error)
	require.NotZero(r.t, privateShow.Error.Code, "normal ObjectShow cannot mount the private host")
	exports := map[string]string{}
	directory := filepath.Join(parent, "exports", phase)
	require.NoError(r.t, os.MkdirAll(directory, 0700))
	for _, format := range []model.ExportFormat{model.Export_Protobuf, model.Export_JSON} {
		response := &pb.RpcObjectExportResponse{}
		r.invoke(ObjectExport, &pb.RpcObjectExportRequest{SpaceId: state.SpaceID, ObjectId: state.DocumentID, Format: format}, response)
		raw, name := []byte(response.Result), "document.json"
		snapshot := &pb.SnapshotWithType{}
		if format == model.Export_Protobuf {
			name = "document.pbc"
			var err error
			raw, err = base64.StdEncoding.DecodeString(response.Result)
			require.NoError(r.t, err)
			require.NoError(r.t, proto.Unmarshal(raw, snapshot))
		} else {
			require.NoError(r.t, jsonpb.UnmarshalString(response.Result, snapshot))
		}
		require.NotNil(r.t, snapshot.Snapshot)
		require.NotNil(r.t, snapshot.Snapshot.Data)
		d := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
		require.Equal(r.t, wantName, d.GetString(bundle.RelationKeyName))
		containsBlock := false
		for _, block := range snapshot.Snapshot.Data.Blocks {
			if block.Id == state.BlockID && block.GetText() != nil && block.GetText().Text == t2VisibleToken {
				containsBlock = true
			}
		}
		require.True(r.t, containsBlock, "native export must preserve the original real block")
		for _, forbidden := range []string{t2PrivateToken, state.RootID, state.OperationID, state.ClaimID} {
			require.NotEmpty(r.t, forbidden)
			require.False(r.t, bytes.Contains(raw, []byte(forbidden)), "ordinary export leaked private journal content/identity")
		}
		t2WriteFresh(r.t, filepath.Join(directory, name), raw)
		exports[name] = t2Hash(raw)
		denied := &pb.RpcObjectExportResponse{}
		r.raw(ObjectExport, &pb.RpcObjectExportRequest{SpaceId: state.SpaceID, ObjectId: state.RootID, Format: format}, denied)
		r.t.Logf("T2_PRIVATE_EXPORT format=%s result_bytes=%d result_sha256=%s", format.String(), len(denied.Result), t2Hash([]byte(denied.Result)))
		if denied.Error != nil {
			r.t.Logf("T2_PRIVATE_EXPORT rpc_code=%d", denied.Error.Code)
		}
		if denied.Report != nil {
			r.t.Logf("T2_PRIVATE_EXPORT report_status=%s succeed=%d object_errors=%d file_errors=%d issues=%d", denied.Report.Status.String(), denied.Report.Succeed, denied.Report.ObjectErrors, denied.Report.FileErrors, len(denied.Report.Issues))
		}
		require.NotNil(r.t, denied.Error)
		require.NotZero(r.t, denied.Error.Code, "normal export must reject a private journal host")
		require.Empty(r.t, denied.Result)
	}
	return map[string]any{"ordinary_name": wantName, "block_sha256": t2Hash([]byte(state.BlockID + "\x00" + t2VisibleToken)),
		"exports": exports, "ordinary_fulltext_control": "PASS", "private_search": "ABSENT",
		"private_show": "REJECTED", "private_export": "REJECTED_JSON_AND_PROTOBUF"}
}

func TestT2AccountLifecyclePhase(t *testing.T) {
	phase, role := os.Getenv("PINKHA_T2_ACCOUNT_PHASE"), os.Getenv("PINKHA_T2_ACCOUNT_ROLE")
	root, reportPath := os.Getenv("PINKHA_T2_ACCOUNT_ROOT"), os.Getenv("PINKHA_T2_ACCOUNT_REPORT")
	nonce := os.Getenv("PINKHA_T2_ACCOUNT_NONCE")
	roles := map[string]string{"new-create": "new", "new-reopen": "new", "legacy-edit": "legacy", "new-recover": "new"}
	require.Equal(t, roles[phase], role)
	require.NotEmpty(t, role)
	require.Equal(t, role, t2AccountRuntimeRole)
	require.NotEqual(t, "UNSET", t2AccountFixtureSHA)
	require.Equal(t, t2AccountFixtureSHA, os.Getenv("PINKHA_T2_ACCOUNT_FIXTURE_SHA"))
	require.Equal(t, t2AccountRegistrationSHA, os.Getenv("PINKHA_T2_ACCOUNT_REGISTRATION_SHA"))
	require.Equal(t, t2HeartPin, vcs.GitCommit)
	require.NotEmpty(t, nonce)
	require.True(t, filepath.IsAbs(root))
	require.Equal(t, "account-root", filepath.Base(root))
	parent := filepath.Dir(root)
	require.Equal(t, parent, filepath.Dir(reportPath))
	require.Equal(t, phase+".json", filepath.Base(reportPath))
	owner, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	require.NoError(t, err)
	require.Equal(t, string(owner), os.Getenv("PINKHA_T2_ACCOUNT_OWNER_TOKEN"))
	var ownership struct {
		Protocol      string `json:"protocol"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	require.NoError(t, json.Unmarshal(owner, &ownership))
	require.Equal(t, t2AccountProtocol, ownership.Protocol)
	require.True(t, ownership.SyntheticOnly)
	statePath, keyPath := filepath.Join(parent, "state.json"), filepath.Join(parent, "account-key.private")
	state := &t2AccountState{}
	if phase == "new-create" {
		entries, err := os.ReadDir(root)
		require.NoError(t, err)
		require.Empty(t, entries, "never attach the fixture to existing user data")
	} else {
		data, err := os.ReadFile(statePath)
		require.NoError(t, err)
		require.NoError(t, json.Unmarshal(data, state))
		require.NotEmpty(t, state.AccountID)
		require.Equal(t, filepath.Base(state.AccountID), state.AccountID)
		entries, err := os.ReadDir(filepath.Join(root, state.AccountID))
		require.NoError(t, err)
		require.NotEmpty(t, entries, "later processes must reopen the exact existing native account")
	}
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	rpc.invoke(InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	version := &pb.RpcAppGetVersionResponse{}
	rpc.invoke(AppGetVersion, &pb.RpcAppGetVersionRequest{}, version)
	wantVersion := "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + t2LegacyPatch
	if role == "new" {
		wantVersion += "-pinkha-t2-registry-v1-" + t2AccountRegistrationSHA
	}
	require.Equal(t, wantVersion, vcs.GitSummary)
	require.Equal(t, wantVersion, version.Version)
	started, closed := false, false
	shutdown := func() {
		if started && !closed {
			// AppShutdown alone intentionally hides native Stop errors. AccountStop
			// reports them and must clear the actual running application first.
			rpc.invoke(AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{})
			require.Nil(t, mw.GetApp(), "AccountStop must close the real native application")
			rpc.invoke(AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{})
			closed = true
		}
	}
	t.Cleanup(shutdown)
	if phase == "new-create" {
		walletResponse := &pb.RpcWalletCreateResponse{}
		rpc.invoke(WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, walletResponse)
		require.NotEmpty(t, walletResponse.AccountKey)
		require.NotEmpty(t, walletResponse.Mnemonic)
		t2WriteFresh(t, keyPath, []byte(walletResponse.AccountKey))
		needles, err := json.Marshal([]string{walletResponse.AccountKey, walletResponse.Mnemonic})
		require.NoError(t, err)
		t2WriteFresh(t, filepath.Join(parent, "sensitive-needles.private"), needles)
		created := &pb.RpcAccountCreateResponse{}
		rpc.invoke(AccountCreate, &pb.RpcAccountCreateRequest{Name: "T2 disposable native lifecycle",
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true}, created)
		started = true
		require.NotNil(t, created.Account)
		require.NotEmpty(t, created.Account.Id)
		state.AccountID = created.Account.Id
		rpc.createTarget(state)
	} else {
		key, err := os.ReadFile(keyPath)
		require.NoError(t, err)
		require.NotEmpty(t, key)
		rpc.invoke(WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)}, &pb.RpcWalletRecoverResponse{})
		request := &pb.RpcAccountSelectRequest{Id: state.AccountID, RootPath: root, NetworkMode: pb.RpcAccount_LocalOnly,
			DisableLocalNetworkSync: true, PreferredSpaceId: state.SpaceID}
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
		require.NotNil(t, selected.Account)
		require.Equal(t, state.AccountID, selected.Account.Id)
		rpc.invoke(WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{})
	}
	observation, assertRemovedTarget, assertDeletedSpace := t2ExerciseRuntime(t, state, phase == "new-create")
	if phase == "legacy-edit" {
		rpc.invoke(ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: state.DocumentID,
			Details: []*model.Detail{{Key: "name", Value: domain.String(t2VisibleToken + " edited by legacy").ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
	}
	raw, heads := t2RawHistory(t, state)
	if phase == "new-create" {
		state.RawChanges, state.Heads = raw, heads
		data, err := json.Marshal(state)
		require.NoError(t, err)
		t2WriteFresh(t, statePath, data)
	} else {
		require.Equal(t, state.RawChanges, raw, "old/native app must preserve all signed private history bytes")
		require.Equal(t, state.Heads, heads)
	}
	visible := rpc.visibleAndHiddenEvidence(state, phase, parent)
	cleanup := "NOT_REQUESTED_IN_THIS_PHASE"
	if phase == "new-recover" {
		// A real target block deletion must orphan, not erase, private history.
		rpc.invoke(BlockListDelete, &pb.RpcBlockListDeleteRequest{ContextId: state.DocumentID, BlockIds: []string{state.BlockID}}, &pb.RpcBlockListDeleteResponse{})
		assertRemovedTarget()
		after, afterHeads := t2RawHistory(t, state)
		require.Equal(t, state.RawChanges, after)
		require.Equal(t, state.Heads, afterHeads)
		provider := app.MustComponent[anystoreprovider.Provider](mw.GetApp())
		getter := provider.GetCrdtDb(state.SpaceID)
		_, err := getter.Wait()
		require.NoError(t, err)
		repo := app.MustComponent[wallet.Wallet](mw.GetApp()).RepoPath()
		require.Equal(t, filepath.Join(root, state.AccountID), repo)
		nativeRoot := app.MustComponent[*config.Config](mw.GetApp()).GetNewSpaceStorePath()
		projectionPath := filepath.Join(repo, "objectstore", state.SpaceID)
		nativePath := filepath.Join(nativeRoot, state.SpaceID)
		require.FileExists(t, filepath.Join(projectionPath, "crdt.db"))
		require.FileExists(t, filepath.Join(nativePath, "store.db"))
		rpc.invoke(SpaceDelete, &pb.RpcSpaceDeleteRequest{SpaceId: state.SpaceID}, &pb.RpcSpaceDeleteResponse{})
		rpc.wait("existing cleanup services remove this disposable Space", func() bool {
			_, projectionError := os.Stat(projectionPath)
			_, nativeError := os.Stat(nativePath)
			_, getterError := getter.Wait()
			return os.IsNotExist(projectionError) && os.IsNotExist(nativeError) && errors.Is(getterError, anystoreprovider.ErrSpaceDeleted)
		})
		assertDeletedSpace()
		cleanup = "TARGET_ORPHAN_PRESERVED_THEN_SPACE_AND_PROJECTION_REMOVED"
	}
	shutdown()
	require.True(t, closed)
	stateBytes, err := os.ReadFile(statePath)
	require.NoError(t, err)
	report := map[string]any{"protocol": t2AccountProtocol, "phase": phase, "role": role, "pid": os.Getpid(), "nonce": nonce,
		"heart_sha": vcs.GitCommit, "legacy_patch_sha256": t2LegacyPatch, "registration_patch_sha256": t2AccountRegistrationSHA,
		"fixture_sha256": t2AccountFixtureSHA, "runtime_version": version.Version, "account_root": root,
		"account_id": state.AccountID, "space_id": state.SpaceID, "document_id": state.DocumentID, "block_id": state.BlockID,
		"private_root_id": state.RootID, "state_sha256": t2Hash(stateBytes), "raw_changes_sha256": raw, "heads": heads,
		"runtime_observation": observation, "visibility": visible, "cleanup": cleanup,
		"account_stop_verified": true, "closed": true, "test_passed": true, "rpc_calls": rpc.calls,
		"app_capability": "OFF", "two_app_clients": "NOT_RUN", "ios_acceptance": "NOT_RUN"}
	data, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	t2WriteFresh(t, reportPath, data)
	t.Log("PASS actual disposable account/Space lifecycle; source-bound private history and normal RPC evidence")
}
