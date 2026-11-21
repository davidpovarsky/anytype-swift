package service

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/util/pinkhat2test"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

var t2LifecycleFixtureSHA = "UNSET"

const t2LifecycleProtocol = "pinkha-t2-generated-byte-lifecycle-races-v1"

func t2RaceWait[T any](t *testing.T, ch <-chan T) T {
	t.Helper()
	timer := time.NewTimer(15 * time.Second)
	defer timer.Stop()
	select {
	case value := <-ch:
		return value
	case <-timer.C:
		t.Fatal("bounded native lifecycle event was not observed")
		var zero T
		return zero
	}
}

// Marshal once on the owner goroutine. The goroutine forwards those exact bytes
// exactly once to the original generated entry and returns its unmodified bytes.
// It does not use testing.Fatal, a shared RPC-count map, a proxy, or a retry.
func t2RaceCall(t *testing.T, call func([]byte) []byte, request proto.Message) (<-chan []byte, string) {
	t.Helper()
	raw, err := proto.Marshal(request)
	require.NoError(t, err)
	result := make(chan []byte, 1)
	go func() { result <- call(raw) }()
	return result, t2Hash(raw)
}

func t2RaceAppendResult(t *testing.T, ch <-chan []byte) *pb.RpcPinkhaTorahOperationsAppendResponse {
	t.Helper()
	response := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	require.NoError(t, proto.Unmarshal(t2RaceWait(t, ch), response))
	require.Equal(t, uint32(1), response.ProtocolVersion)
	require.NotNil(t, response.Error)
	return response
}

func t2RaceDeleteResult(t *testing.T, ch <-chan []byte) {
	t.Helper()
	response := &pb.RpcBlockListDeleteResponse{}
	require.NoError(t, proto.Unmarshal(t2RaceWait(t, ch), response))
	require.NotNil(t, response.Error)
	require.Equal(t, pb.RpcBlockListDeleteResponseError_NULL, response.Error.Code)
}

func t2RaceRawHistory(t *testing.T, spc clientspace.Space, rootID string) (map[string]string, []string) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	storage, err := spc.Storage().TreeStorage(ctx, rootID)
	require.NoError(t, err)
	root, err := storage.Root(ctx)
	require.NoError(t, err)
	require.Equal(t, rootID, root.Id)
	values := map[string]string{root.Id: t2Hash(root.RawChange)}
	require.NoError(t, storage.GetAfterAddSeq(ctx, 0, func(_ context.Context, change objecttree.StorageChange) (bool, error) {
		require.NotContains(t, values, change.Id)
		values[change.Id] = t2Hash(change.RawChange)
		return true, nil
	}))
	heads, err := storage.Heads(ctx)
	require.NoError(t, err)
	sort.Strings(heads)
	return values, heads
}

func t2RaceCapture(t *testing.T, filters []pinkhat2test.Filter) *pinkhat2test.Capture {
	t.Helper()
	capture, err := pinkhat2test.Begin(filters)
	require.NoError(t, err)
	t.Cleanup(capture.Close)
	return capture
}

func t2RaceTrace(t *testing.T, capture *pinkhat2test.Capture, expected []string) map[string]any {
	t.Helper()
	report := capture.Report()
	require.Empty(t, report["gate_timeouts"])
	events := report["events"].([]pinkhat2test.Event)
	require.Len(t, events, len(expected))
	for index, stage := range expected {
		require.Equal(t, index+1, events[index].Sequence)
		require.Equal(t, stage, events[index].Stage)
	}
	for _, count := range report["counts"].(map[string]int) {
		require.Equal(t, 1, count)
	}
	return report
}

func t2RacePrepare(t *testing.T, rpc *t2AccountRPC, accountID string, seed bool) (*t2AccountState, clientspace.Space, smartblock.SmartBlock) {
	t.Helper()
	state := &t2AccountState{AccountID: accountID, OperationID: fmt.Sprintf("%032x", 1)}
	rpc.createTarget(state)
	root, err := torahopscontract.Root(state.SpaceID)
	require.NoError(t, err)
	state.RootID = root.Id
	spc := t2Space(t, state.SpaceID)
	target, err := spc.GetObject(context.Background(), state.DocumentID)
	require.NoError(t, err)
	if seed {
		t2CreateNativeRPCOperation(t, context.Background(), state)
	}
	return state, spc, target
}

func t2RaceDeniedAfterDelete(t *testing.T, state *t2AccountState, request *pb.RpcPinkhaTorahOperationsAppendRequest) {
	t.Helper()
	_, readRequest := t2NativeRPCRequests(state)
	read, retry := t2WireRead(t, readRequest), t2WireAppend(t, request)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_TARGET_UNAVAILABLE, read.Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_TARGET_UNAVAILABLE, retry.Error.Code)
	require.Nil(t, read.Snapshot)
	require.Nil(t, retry.Receipt)
}

func t2RaceVerifyCreated(t *testing.T, response *pb.RpcPinkhaTorahOperationsAppendResponse, request *pb.RpcPinkhaTorahOperationsAppendRequest, author string) {
	t.Helper()
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, response.Error.Code)
	require.Empty(t, response.Error.Issues)
	require.NotNil(t, response.Receipt)
	require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, response.Receipt.Disposition)
	require.NotEmpty(t, response.Receipt.ChangeId)
	require.NotNil(t, response.Receipt.Resolution)
	found := false
	for _, claim := range response.Receipt.Resolution.Claims {
		if claim.ClaimId != response.Receipt.ClaimId {
			continue
		}
		found = true
		require.NotNil(t, claim.Operation)
		op := claim.Operation
		require.Equal(t, uint32(1), op.Version)
		require.Equal(t, pb.RpcPinkhaTorahOperations_ADD, op.Kind)
		require.Empty(t, op.ObservedClaimIds)
		require.Equal(t, author, op.AuthorId)
		require.Equal(t, request.OperationId, op.OperationId)
		require.Equal(t, request.SpaceId, op.SpaceId)
		require.True(t, proto.Equal(request.Target, op.Target))
		require.True(t, proto.Equal(request.Source, op.Source))
		require.Equal(t, request.Payload, op.Payload)
		canonical, err := (torahops.Operation{Version: op.Version, SpaceID: op.SpaceId, OperationID: op.OperationId,
			AuthorID: op.AuthorId, Kind: torahops.Add,
			Target:  torahops.Target{ObjectID: op.Target.ObjectId, BlockID: op.Target.BlockId},
			Source:  torahops.Source{ProviderID: op.Source.ProviderId, CanonicalRef: op.Source.CanonicalRef},
			Payload: op.Payload, Observed: op.ObservedClaimIds}).CanonicalBytes()
		require.NoError(t, err)
		require.NotEmpty(t, canonical)
	}
	require.True(t, found, "actual created claim must be retained in the unchanged wire receipt")
}

func TestT2GeneratedByteLifecycleRaces(t *testing.T) {
	root, reportPath := os.Getenv("PINKHA_T2_LIFECYCLE_ROOT"), os.Getenv("PINKHA_T2_LIFECYCLE_REPORT")
	nonce := os.Getenv("PINKHA_T2_LIFECYCLE_NONCE")
	require.Equal(t, "new", t2AccountRuntimeRole)
	require.Equal(t, t2HeartPin, vcs.GitCommit)
	require.NotEqual(t, "UNSET", t2LifecycleFixtureSHA)
	require.Equal(t, t2LifecycleFixtureSHA, os.Getenv("PINKHA_T2_LIFECYCLE_FIXTURE_SHA"))
	require.NotEmpty(t, nonce)
	require.True(t, filepath.IsAbs(root))
	require.Equal(t, "account-root", filepath.Base(root))
	require.Equal(t, filepath.Dir(root), filepath.Dir(reportPath))
	require.Equal(t, "lifecycle.json", filepath.Base(reportPath))
	owner, err := os.ReadFile(filepath.Join(filepath.Dir(root), "ownership.json"))
	require.NoError(t, err)
	require.Equal(t, string(owner), os.Getenv("PINKHA_T2_LIFECYCLE_OWNER_TOKEN"))
	var ownership struct {
		Protocol      string `json:"protocol"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	require.NoError(t, json.Unmarshal(owner, &ownership))
	require.Equal(t, t2LifecycleProtocol, ownership.Protocol)
	require.True(t, ownership.SyntheticOnly)
	entries, err := os.ReadDir(root)
	require.NoError(t, err)
	require.Empty(t, entries, "fixture must never attach to existing user data")
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	rpc.invoke(InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	wallet := &pb.RpcWalletCreateResponse{}
	rpc.invoke(WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, wallet)
	require.NotEmpty(t, wallet.AccountKey)
	require.NotEmpty(t, wallet.Mnemonic)
	needles, err := json.Marshal([]string{wallet.AccountKey, wallet.Mnemonic})
	require.NoError(t, err)
	t2WriteFresh(t, filepath.Join(filepath.Dir(root), "sensitive-needles.private"), needles)
	created := &pb.RpcAccountCreateResponse{}
	rpc.invoke(AccountCreate, &pb.RpcAccountCreateRequest{Name: "T2 disposable lifecycle races",
		NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true}, created)
	require.NotNil(t, created.Account)
	require.NotEmpty(t, created.Account.Id)
	stopped := false
	t.Cleanup(func() {
		if !stopped {
			rpc.invoke(AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{})
		}
		rpc.invoke(AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{})
	})
	author := app.MustComponent[accountservice.Service](mw.GetApp()).Account().SignKey.GetPublic().Account()
	results := map[string]any{}

	// 1: A real block deletion after target preload wins before target leasing.
	state, spc, _ := t2RacePrepare(t, rpc, created.Account.Id, false)
	request, _ := t2NativeRPCRequests(state)
	capture := t2RaceCapture(t, []pinkhat2test.Filter{{Stage: "prelease", ID: state.DocumentID, Qualifier: "write", Pause: true}})
	appendDone, requestHash := t2RaceCall(t, PinkhaTorahOperationsAppend, request)
	t2RaceWait(t, capture.Arrival("prelease"))
	deleteDone, _ := t2RaceCall(t, BlockListDelete, &pb.RpcBlockListDeleteRequest{ContextId: state.DocumentID, BlockIds: []string{state.BlockID}})
	t2RaceDeleteResult(t, deleteDone)
	capture.Release("prelease")
	denied := t2RaceAppendResult(t, appendDone)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_TARGET_UNAVAILABLE, denied.Error.Code)
	require.Nil(t, denied.Receipt)
	storage, err := spc.Storage().TreeStorage(context.Background(), state.RootID)
	require.ErrorIs(t, err, treestorage.ErrUnknownTreeId)
	require.Nil(t, storage)
	results["delete_wins_first_add"] = map[string]any{"trace": t2RaceTrace(t, capture, []string{"prelease"}),
		"request_sha256": requestHash, "response": "TARGET_UNAVAILABLE_NO_RECEIPT", "private_root": "ABSENT"}
	capture.Close()

	// 2: The same live target lock keeps deletion behind the original DB commit.
	state, spc, target := t2RacePrepare(t, rpc, created.Account.Id, true)
	before, beforeHeads := t2RaceRawHistory(t, spc, state.RootID)
	require.Len(t, before, 2)
	request, _ = t2NativeRPCRequests(state)
	request.OperationId = fmt.Sprintf("%032x", 2)
	capture = t2RaceCapture(t, []pinkhat2test.Filter{
		{Stage: "commit-before-storage", ID: state.RootID, Pause: true},
		{Stage: "commit-after-storage", ID: state.RootID, Pause: true},
		{Stage: "delete-lock-attempt", ID: state.DocumentID, Qualifier: "basic.Unlinkable", Identity: target},
		{Stage: "delete-lock-acquired", ID: state.DocumentID, Qualifier: "basic.Unlinkable", Identity: target}})
	appendDone, requestHash = t2RaceCall(t, PinkhaTorahOperationsAppend, request)
	t2RaceWait(t, capture.Arrival("commit-before-storage"))
	deleteDone, _ = t2RaceCall(t, BlockListDelete, &pb.RpcBlockListDeleteRequest{ContextId: state.DocumentID, BlockIds: []string{state.BlockID}})
	t2RaceWait(t, capture.Arrival("delete-lock-attempt"))
	require.False(t, capture.Seen("delete-lock-acquired"))
	stillBefore, stillHeads := t2RaceRawHistory(t, spc, state.RootID)
	require.Equal(t, before, stillBefore)
	require.Equal(t, beforeHeads, stillHeads)
	capture.Release("commit-before-storage")
	t2RaceWait(t, capture.Arrival("commit-after-storage"))
	require.False(t, capture.Seen("delete-lock-acquired"))
	durable, durableHeads := t2RaceRawHistory(t, spc, state.RootID)
	require.Len(t, durable, 3)
	for id, hash := range before {
		require.Equal(t, hash, durable[id])
	}
	capture.Release("commit-after-storage")
	appended := t2RaceAppendResult(t, appendDone)
	t2RaceVerifyCreated(t, appended, request, author)
	t2RaceDeleteResult(t, deleteDone)
	require.Equal(t, []string{appended.Receipt.ChangeId}, durableHeads)
	require.NotEmpty(t, durable[appended.Receipt.ChangeId])
	trace := t2RaceTrace(t, capture, []string{"commit-before-storage", "delete-lock-attempt", "commit-after-storage", "delete-lock-acquired"})
	require.True(t, capture.SameIdentity("delete-lock-attempt", "delete-lock-acquired"))
	require.True(t, capture.SameIdentity("commit-before-storage", "commit-after-storage"))
	capture.Close()
	t2RaceDeniedAfterDelete(t, state, request)
	after, afterHeads := t2RaceRawHistory(t, spc, state.RootID)
	require.Equal(t, durable, after)
	require.Equal(t, durableHeads, afterHeads)
	results["commit_wins_block_delete"] = map[string]any{"trace": trace, "request_sha256": requestHash,
		"raw_changes_sha256": after, "heads": afterHeads, "private_history_count": len(after),
		"target_pointer_identity": "EXACT_SAME_LIVE_SMARTBLOCK", "post_delete_read_and_retry": "TARGET_UNAVAILABLE_NO_RESULT"}

	// 3: Stop uses the real writer lock. No GetApp or cache helper is called by
	// the controller while that writer is queued behind the append's app lease.
	state, spc, _ = t2RacePrepare(t, rpc, created.Account.Id, true)
	before, beforeHeads = t2RaceRawHistory(t, spc, state.RootID)
	require.Len(t, before, 2)
	require.Equal(t, []string{state.ChangeID}, beforeHeads)
	request, _ = t2NativeRPCRequests(state)
	request.OperationId = fmt.Sprintf("%032x", 2)
	capture = t2RaceCapture(t, []pinkhat2test.Filter{
		{Stage: "app-lease-held"},
		{Stage: "commit-before-storage", ID: state.RootID, Pause: true},
		{Stage: "commit-after-storage", ID: state.RootID, Pause: true},
		{Stage: "append-native-return", ID: state.DocumentID, Qualifier: "write"},
		{Stage: "stop-lock-attempt"}, {Stage: "stop-lock-acquired"}})
	appendDone, requestHash = t2RaceCall(t, PinkhaTorahOperationsAppend, request)
	t2RaceWait(t, capture.Arrival("commit-before-storage"))
	stopDone, _ := t2RaceCall(t, AccountStop, &pb.RpcAccountStopRequest{RemoveData: false})
	t2RaceWait(t, capture.Arrival("stop-lock-attempt"))
	require.False(t, capture.Seen("stop-lock-acquired"))
	require.True(t, capture.SameIdentity("app-lease-held", "stop-lock-attempt"))
	capture.Release("commit-before-storage")
	t2RaceWait(t, capture.Arrival("commit-after-storage"))
	require.False(t, capture.Seen("stop-lock-acquired"))
	durable, durableHeads = t2RaceRawHistory(t, spc, state.RootID)
	require.Len(t, durable, 3)
	for id, hash := range before {
		require.Equal(t, hash, durable[id])
	}
	capture.Release("commit-after-storage")
	appended = t2RaceAppendResult(t, appendDone)
	t2RaceVerifyCreated(t, appended, request, author)
	stopResponse := &pb.RpcAccountStopResponse{}
	require.NoError(t, proto.Unmarshal(t2RaceWait(t, stopDone), stopResponse))
	require.NotNil(t, stopResponse.Error)
	require.Equal(t, pb.RpcAccountStopResponseError_NULL, stopResponse.Error.Code)
	stopped = true
	require.Nil(t, mw.GetApp())
	require.Equal(t, []string{appended.Receipt.ChangeId}, durableHeads)
	require.NotEmpty(t, durable[appended.Receipt.ChangeId])
	trace = t2RaceTrace(t, capture, []string{"app-lease-held", "commit-before-storage", "stop-lock-attempt",
		"commit-after-storage", "append-native-return", "stop-lock-acquired"})
	require.True(t, capture.SameIdentity("app-lease-held", "stop-lock-acquired"))
	capture.Close()
	_, readRequest := t2NativeRPCRequests(state)
	read, retry := t2WireRead(t, readRequest), t2WireAppend(t, request)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NOT_LOGGED_IN, read.Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NOT_LOGGED_IN, retry.Error.Code)
	require.Nil(t, read.Snapshot)
	require.Nil(t, retry.Receipt)
	results["commit_wins_account_stop"] = map[string]any{"trace": trace, "request_sha256": requestHash,
		"raw_changes_sha256_before_append": before, "heads_before_append": beforeHeads,
		"raw_changes_sha256_at_durable_boundary": durable, "heads_at_durable_boundary": durableHeads,
		"application_service_identity": "EXACT_SAME_LIVE_INSTANCE", "account_stop": "PASS_ORIGINAL_STOP",
		"after_stop_read_and_retry": "NOT_LOGGED_IN_NO_RESULT"}
	data, err := json.MarshalIndent(map[string]any{"protocol": t2LifecycleProtocol, "nonce": nonce, "pid": os.Getpid(),
		"heart_sha": vcs.GitCommit, "fixture_sha256": t2LifecycleFixtureSHA, "status": "PASS_THREE_REAL_ACCOUNT_BYTE_LIFECYCLE_CASES",
		"cases": results, "account_stop_verified": stopped, "app_capability": "OFF",
		"instrumentation":             "SEPARATE_PINNED_TEST_COMPILE_OVERLAY_NOT_SHIPPED_PRODUCT",
		"generated_byte_cancellation": "NOT_EXPOSED_NOT_CLAIMED", "settings_delete": "NOT_RUN",
		"standalone_space_close": "NOT_RUN", "account_switch": "NOT_RUN", "new_engine_parity": "NOT_PROVEN"}, "", "  ")
	require.NoError(t, err)
	t2WriteFresh(t, reportPath, data)
}
