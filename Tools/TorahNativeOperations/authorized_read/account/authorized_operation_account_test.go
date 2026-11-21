package service

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/anytype/config"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/datastore/anystoreprovider"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

// Linked into this test-only binary, never a product capability advertisement.
var t2ReadFixtureSHA = "UNSET"
var t2ReadCandidateSHA = "UNSET"

const t2ReadAccountProtocol = "pinkha-authorized-read-account-v1"

func t2AuthorizedReadBytes(t *testing.T, state *t2AccountState, operationID string) (*pb.PinkhaTorahAuthorizedOperationReadResponse, []byte) {
	t.Helper()
	request := &pb.PinkhaTorahAuthorizedOperationReadRequest{ProtocolVersion: 1, SpaceId: state.SpaceID, OperationId: operationID}
	encoded, err := proto.Marshal(request)
	require.NoError(t, err)
	// This is the actual generated gomobile byte entry, not the typed handler.
	raw := PinkhaTorahAuthorizedOperationRead(encoded)
	require.LessOrEqual(t, len(raw), torahops.MaxAuthorizedOperationReadBytes)
	response := &pb.PinkhaTorahAuthorizedOperationReadResponse{}
	require.NoError(t, proto.Unmarshal(raw, response))
	require.Equal(t, uint32(1), response.ProtocolVersion)
	require.NotNil(t, response.Error)
	return response, raw
}

func t2AuthorizedReadExpected(t *testing.T, state *t2AccountState) []byte {
	t.Helper()
	keys := app.MustComponent[accountservice.Service](mw.GetApp()).Account()
	canonical, err := (torahops.Operation{Version: 1, SpaceID: state.SpaceID, OperationID: state.OperationID,
		AuthorID: keys.SignKey.GetPublic().Account(), Kind: torahops.Add,
		Target:  torahops.Target{ObjectID: state.DocumentID, BlockID: state.BlockID},
		Source:  torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:authorized-read:1"},
		Payload: []byte(t2PrivatePayload)}).CanonicalBytes()
	require.NoError(t, err)
	return canonical
}

func t2AuthorizedReadCheck(t *testing.T, state *t2AccountState, canonical []byte,
	reachability pb.PinkhaTorahAuthorizedOperationReadReachability) (*pb.PinkhaTorahAuthorizedOperationReadSnapshot, []byte) {
	t.Helper()
	response, raw := t2AuthorizedReadBytes(t, state, state.OperationID)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NULL, response.Error.Code)
	require.Empty(t, response.Error.Description)
	require.NotNil(t, response.Snapshot)
	value := response.Snapshot
	require.Equal(t, torahops.AuthorizedOperationReadContract, value.Contract)
	require.Equal(t, state.AccountID, value.AccountId)
	require.Equal(t, state.SpaceID, value.SpaceId)
	require.Equal(t, state.OperationID, value.OperationId)
	require.True(t, value.Complete)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_FOUND, value.Outcome)
	token, err := hex.DecodeString(value.NativeSnapshotToken)
	require.NoError(t, err)
	require.Len(t, token, 32)
	require.Equal(t, hex.EncodeToString(token), value.NativeSnapshotToken)
	require.Len(t, value.Variants, 1)
	variant := value.Variants[0]
	require.Equal(t, state.ClaimID, variant.ClaimId)
	require.Equal(t, state.OperationID, variant.OperationId)
	require.Equal(t, state.SpaceID, variant.SpaceId)
	require.Equal(t, state.AccountID, variant.AuthorId)
	require.NotNil(t, variant.Target)
	require.Equal(t, state.DocumentID, variant.Target.ObjectId)
	require.Equal(t, state.BlockID, variant.Target.BlockId)
	require.Equal(t, canonical, variant.CanonicalBytes)
	require.Equal(t, reachability, variant.Reachability)
	require.Len(t, variant.Provenance, 1)
	require.Equal(t, state.AccountID, variant.Provenance[0].Creator)
	require.Equal(t, state.ChangeID, variant.Provenance[0].NativeChangeId)
	require.NotEmpty(t, variant.Provenance[0].NativeAclHeadId)
	return value, raw
}

func TestPinkhaAuthorizedOperationAccountByteLifecycle(t *testing.T) {
	phase, root := os.Getenv("PINKHA_T2_READ_PHASE"), os.Getenv("PINKHA_T2_READ_ROOT")
	reportPath, nonce := os.Getenv("PINKHA_T2_READ_REPORT"), os.Getenv("PINKHA_T2_READ_NONCE")
	require.Contains(t, []string{"create", "reopen"}, phase)
	require.True(t, filepath.IsAbs(root))
	require.Equal(t, "account-root", filepath.Base(root))
	parent := filepath.Dir(root)
	require.Equal(t, parent, filepath.Dir(reportPath))
	require.Equal(t, phase+".json", filepath.Base(reportPath))
	require.NotEmpty(t, nonce)
	for _, marker := range []string{t2ReadFixtureSHA, t2ReadCandidateSHA} {
		require.Len(t, marker, 64)
		require.Equal(t, strings.ToLower(marker), marker)
		_, err := hex.DecodeString(marker)
		require.NoError(t, err)
	}
	require.Equal(t, os.Getenv("PINKHA_T2_READ_FIXTURE_SHA"), t2ReadFixtureSHA)
	require.Equal(t, os.Getenv("PINKHA_T2_READ_CANDIDATE_SHA"), t2ReadCandidateSHA)
	require.Equal(t, t2HeartPin, vcs.GitCommit)
	owner, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	require.NoError(t, err)
	require.Equal(t, string(owner), os.Getenv("PINKHA_T2_READ_OWNER_TOKEN"))
	var ownership struct {
		Protocol      string `json:"protocol"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	require.NoError(t, json.Unmarshal(owner, &ownership))
	require.Equal(t, t2ReadAccountProtocol, ownership.Protocol)
	require.True(t, ownership.SyntheticOnly)
	statePath, keyPath := filepath.Join(parent, "state.json"), filepath.Join(parent, "account-key.private")
	state := &t2AccountState{}
	if phase == "create" {
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
		require.NotEmpty(t, entries, "reopen must use the existing account")
	}
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	rpc.invoke(InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	version := &pb.RpcAppGetVersionResponse{}
	rpc.invoke(AppGetVersion, &pb.RpcAppGetVersionRequest{}, version)
	wantVersion := "v0.51.7-nightly.20261014.1-pinkha-authorized-read-v1-" + t2ReadCandidateSHA
	require.Equal(t, wantVersion, vcs.GitSummary)
	require.Equal(t, wantVersion, version.Version)
	started, closed := false, false
	shutdown := func() {
		if started && !closed {
			rpc.invoke(AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{})
			require.Nil(t, mw.GetApp())
			rpc.invoke(AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{})
			closed = true
		}
	}
	t.Cleanup(shutdown)
	if phase == "create" {
		walletResponse := &pb.RpcWalletCreateResponse{}
		rpc.invoke(WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, walletResponse)
		require.NotEmpty(t, walletResponse.AccountKey)
		require.NotEmpty(t, walletResponse.Mnemonic)
		t2WriteFresh(t, keyPath, []byte(walletResponse.AccountKey))
		needles, err := json.Marshal([]string{walletResponse.AccountKey, walletResponse.Mnemonic})
		require.NoError(t, err)
		t2WriteFresh(t, filepath.Join(parent, "sensitive-needles.private"), needles)
		created := &pb.RpcAccountCreateResponse{}
		rpc.invoke(AccountCreate, &pb.RpcAccountCreateRequest{Name: "T2 authorized read disposable fixture",
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
	spc := t2Space(t, state.SpaceID)
	privateRoot, err := torahopscontract.Root(state.SpaceID)
	require.NoError(t, err)
	if phase == "create" {
		state.RootID, state.OperationID = privateRoot.Id, strings.Repeat("1", 32)
		absent, _ := t2AuthorizedReadBytes(t, state, state.OperationID)
		require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_HISTORY_UNAVAILABLE, absent.Error.Code)
		require.Nil(t, absent.Snapshot)
		exists, err := spc.Storage().HasTree(context.Background(), state.RootID)
		require.NoError(t, err)
		require.False(t, exists, "read cannot create missing private history")
		appendRequest := &pb.RpcPinkhaTorahOperationsAppendRequest{ProtocolVersion: 1, SpaceId: state.SpaceID,
			OperationId: state.OperationID, Kind: pb.RpcPinkhaTorahOperations_ADD,
			Target:  &pb.RpcPinkhaTorahOperationsTarget{ObjectId: state.DocumentID, BlockId: state.BlockID},
			Source:  &pb.RpcPinkhaTorahOperationsSource{ProviderId: "fixture", CanonicalRef: "fixture:authorized-read:1"},
			Payload: []byte(t2PrivatePayload)}
		created := &pb.RpcPinkhaTorahOperationsAppendResponse{}
		rpc.invoke(PinkhaTorahOperationsAppend, appendRequest, created)
		require.NotNil(t, created.Receipt)
		require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, created.Receipt.Disposition)
		state.ClaimID, state.ChangeID = created.Receipt.ClaimId, created.Receipt.ChangeId
		require.NotEmpty(t, state.ClaimID)
		require.NotEmpty(t, state.ChangeID)
	} else {
		require.Equal(t, privateRoot.Id, state.RootID)
	}
	canonical := t2AuthorizedReadExpected(t, state)
	if phase == "create" {
		state.OperationSHA256 = t2Hash(canonical)
	}
	require.Equal(t, state.OperationSHA256, t2Hash(canonical))
	// On reopen this read occurs before any append or replay of this operation.
	live, raw := t2AuthorizedReadCheck(t, state, canonical, pb.PinkhaTorahAuthorizedOperationRead_LIVE_BLOCK)
	goldenName := phase + "-live.pb"
	t2WriteFresh(t, filepath.Join(parent, goldenName), raw)
	absent, _ := t2AuthorizedReadBytes(t, state, strings.Repeat("2", 32))
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NULL, absent.Error.Code)
	require.NotNil(t, absent.Snapshot)
	require.True(t, absent.Snapshot.Complete)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_ABSENT_IN_VERIFIED_LOCAL_SNAPSHOT, absent.Snapshot.Outcome)
	require.Empty(t, absent.Snapshot.Variants)
	history, heads := t2RawHistory(t, state)
	if phase == "create" {
		state.RawChanges, state.Heads = history, heads
		data, err := json.Marshal(state)
		require.NoError(t, err)
		t2WriteFresh(t, statePath, data)
	} else {
		require.Equal(t, state.RawChanges, history)
		require.Equal(t, state.Heads, heads)
	}
	orphaned, deletedSpace := false, false
	if phase == "reopen" {
		rpc.invoke(BlockListDelete, &pb.RpcBlockListDeleteRequest{ContextId: state.DocumentID, BlockIds: []string{state.BlockID}}, &pb.RpcBlockListDeleteResponse{})
		unreachable, orphanBytes := t2AuthorizedReadCheck(t, state, canonical, pb.PinkhaTorahAuthorizedOperationRead_UNREACHABLE_BLOCK)
		require.True(t, proto.Equal(live.Variants[0].Provenance[0], unreachable.Variants[0].Provenance[0]))
		t2WriteFresh(t, filepath.Join(parent, "reopen-unreachable.pb"), orphanBytes)
		after, afterHeads := t2RawHistory(t, state)
		require.Equal(t, history, after)
		require.Equal(t, heads, afterHeads)
		orphaned = true
		provider := app.MustComponent[anystoreprovider.Provider](mw.GetApp())
		getter := provider.GetCrdtDb(state.SpaceID)
		_, err := getter.Wait()
		require.NoError(t, err)
		repo := app.MustComponent[wallet.Wallet](mw.GetApp()).RepoPath()
		require.Equal(t, filepath.Join(root, state.AccountID), repo)
		nativeRoot := app.MustComponent[*config.Config](mw.GetApp()).GetNewSpaceStorePath()
		projectionPath, nativePath := filepath.Join(repo, "objectstore", state.SpaceID), filepath.Join(nativeRoot, state.SpaceID)
		require.FileExists(t, filepath.Join(projectionPath, "crdt.db"))
		require.FileExists(t, filepath.Join(nativePath, "store.db"))
		rpc.invoke(SpaceDelete, &pb.RpcSpaceDeleteRequest{SpaceId: state.SpaceID}, &pb.RpcSpaceDeleteResponse{})
		rpc.wait("existing cleanup removes disposable Space", func() bool {
			_, projectionErr := os.Stat(projectionPath)
			_, nativeErr := os.Stat(nativePath)
			_, getterErr := getter.Wait()
			return os.IsNotExist(projectionErr) && os.IsNotExist(nativeErr) && errors.Is(getterErr, anystoreprovider.ErrSpaceDeleted)
		})
		denied, _ := t2AuthorizedReadBytes(t, state, state.OperationID)
		require.NotEqual(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NULL, denied.Error.Code)
		require.Nil(t, denied.Snapshot)
		deletedSpace = true
	}
	shutdown()
	require.True(t, closed)
	stopped, _ := t2AuthorizedReadBytes(t, state, state.OperationID)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NOT_LOGGED_IN, stopped.Error.Code)
	require.Nil(t, stopped.Snapshot)
	stateBytes, err := os.ReadFile(statePath)
	require.NoError(t, err)
	report := map[string]any{"protocol": t2ReadAccountProtocol, "phase": phase, "pid": os.Getpid(), "nonce": nonce,
		"heart_sha": vcs.GitCommit, "candidate_sha256": t2ReadCandidateSHA, "fixture_sha256": t2ReadFixtureSHA,
		"runtime_version": version.Version, "account_root": root, "account_id": state.AccountID, "space_id": state.SpaceID,
		"document_id": state.DocumentID, "block_id": state.BlockID, "private_root_id": state.RootID,
		"state_sha256": t2Hash(stateBytes), "raw_changes_sha256": history, "heads": heads,
		"canonical_sha256": t2Hash(canonical), "golden_file": goldenName, "golden_sha256": t2Hash(raw),
		"exact_signed_provenance": true, "read_before_replay": true, "verified_local_absence": true,
		"orphan_history_preserved": orphaned, "space_cleanup_verified": deletedSpace,
		"account_stop_verified": true, "closed": true, "test_passed": true, "rpc_calls": rpc.calls,
		"app_capability": "OFF", "two_app_clients": "NOT_RUN", "ios_acceptance": "NOT_RUN"}
	data, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	t2WriteFresh(t, reportPath, data)
	t.Log("PASS generated operation-ID read on the same disposable native account")
}
