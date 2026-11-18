package service

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"slices"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

const t2CrashProtocol = "pinkha-t2-native-process-crash-after-commit-v1"

type t2CrashByteObservation struct {
	RequestSHA   string
	RequestBytes int
	ReplyBytes   int
}

// This is a client-side byte gate, after the real generated entry returned.
// No response is decoded and no testing.T operation runs on the worker. Only
// failure cancellation releases the gate; a successful armed phase is killed.
func t2CrashHoldReply(ctx context.Context, entry func([]byte) []byte,
	observed chan<- t2CrashByteObservation) func([]byte) []byte {
	return func(data []byte) []byte {
		requestSHA, requestBytes := t2Hash(data), len(data)
		reply := entry(data)
		value := t2CrashByteObservation{requestSHA, requestBytes, len(reply)}
		select {
		case observed <- value:
		case <-ctx.Done():
			return nil
		}
		<-ctx.Done()
		return nil
	}
}

// testing.T.Fatal uses runtime.Goexit. The join must be a defer so a failed
// native Stop/Shutdown cannot skip the bounded append-worker join.
func t2CrashCleanup(cancel context.CancelFunc, closeAccount, join func()) {
	cancel()
	defer join()
	closeAccount()
}

func t2CrashCommittedChange(before, after t2OfflineHistory) (string, error) {
	if len(before.Changes) != 8 || len(before.Parents) != 7 || len(before.Heads) != 2 ||
		before.Heads[0] == before.Heads[1] || len(after.Changes) != 9 || len(after.Parents) != 8 || len(after.Heads) != 1 {
		return "", fmt.Errorf("unexpected crash history shape")
	}
	for id, digest := range before.Changes {
		if after.Changes[id] != digest {
			return "", fmt.Errorf("original signed bytes changed")
		}
	}
	for id, parents := range before.Parents {
		if !slices.Equal(after.Parents[id], parents) {
			return "", fmt.Errorf("original parents changed")
		}
	}
	newID := ""
	for id, digest := range after.Changes {
		if _, existed := before.Changes[id]; !existed {
			if newID != "" || id == "" || len(digest) != 64 {
				return "", fmt.Errorf("extra or invalid new signed change")
			}
			newID = id
		}
	}
	wantedParents := slices.Clone(before.Heads)
	slices.Sort(wantedParents)
	if newID == "" || !slices.Equal(after.Heads, []string{newID}) || !slices.Equal(after.Parents[newID], wantedParents) {
		return "", fmt.Errorf("new change does not join both original heads")
	}
	return newID, nil
}

func t2CrashOperation(state *t2AccountState, author string) torahops.Operation {
	return torahops.Operation{Version: 1, SpaceID: state.SpaceID, OperationID: fmt.Sprintf("%032x", 7),
		AuthorID: author, Kind: torahops.Add, Target: torahops.Target{ObjectID: state.DocumentID, BlockID: state.BlockID},
		Source:  torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:t2-process-crash:1"},
		Payload: []byte("t2-private-process-crash-add-c729")}
}

type t2CrashBaseline struct {
	Protocol       string           `json:"protocol"`
	Phase          string           `json:"phase"`
	Role           string           `json:"role"`
	Nonce          string           `json:"nonce"`
	PeerID         string           `json:"peer_id"`
	FixtureSHA     string           `json:"client_fixture_sha256"`
	StateSHA       string           `json:"state_sha256"`
	History        t2OfflineHistory `json:"history"`
	SnapshotSHA    string           `json:"snapshot_sha256_without_local_sequence"`
	Closed         bool             `json:"closed"`
	AccountStopped bool             `json:"account_stop_verified"`
	Passed         bool             `json:"test_passed"`
	PostStop       string           `json:"post_stop_rpc"`
}

type t2CrashSession struct {
	c           *t2NativeClientCaller
	state       *t2AccountState
	baseline    t2CrashBaseline
	baselineSHA string
	stateSHA    string
	peerID      string
	author      string
	version     string
}

func t2OpenCrashSession(t *testing.T, phase string) *t2CrashSession {
	t.Helper()
	require.Equal(t, "creator", os.Getenv("PINKHA_T2_CLIENT_ROLE"))
	require.Equal(t, phase, os.Getenv("PINKHA_T2_CRASH_PHASE"))
	require.Equal(t, t2OfflineProtocol, os.Getenv("PINKHA_T2_CLIENT_SCENARIO"))
	require.Equal(t, "new", t2AccountRuntimeRole)
	require.NotEqual(t, "UNSET", t2NativeClientFixtureSHA)
	require.Equal(t, t2NativeClientFixtureSHA, os.Getenv("PINKHA_T2_CLIENT_FIXTURE_SHA"))
	require.NotEqual(t, "UNSET", t2RPCAccountSchemaSHA)
	require.Equal(t, t2HeartPin, vcs.GitCommit)
	const parent, root = "/private", "/private/account-root"
	ownerBytes, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	require.NoError(t, err)
	var owner struct {
		Protocol      string `json:"protocol"`
		Nonce         string `json:"nonce"`
		Role          string `json:"role"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	require.NoError(t, json.Unmarshal(ownerBytes, &owner))
	require.Equal(t, t2NativeClientProtocol, owner.Protocol)
	require.Equal(t, "creator", owner.Role)
	require.NotEmpty(t, owner.Nonce)
	require.Equal(t, os.Getenv("PINKHA_T2_CLIENT_NONCE"), owner.Nonce)
	require.True(t, owner.SyntheticOnly)
	entries, err := os.ReadDir(root)
	require.NoError(t, err)
	require.NotEmpty(t, entries, "crash phases must retain the original account store")
	require.Empty(t, t2OfflineIPs(t), "no peer may repair the crashed store")
	stateBytes, err := os.ReadFile(filepath.Join(parent, "state.json"))
	require.NoError(t, err)
	s := &t2CrashSession{state: &t2AccountState{}, stateSHA: t2Hash(stateBytes)}
	require.NoError(t, json.Unmarshal(stateBytes, s.state))
	baselineBytes, err := os.ReadFile(filepath.Join(parent, "reopened.json"))
	require.NoError(t, err)
	require.NoError(t, json.Unmarshal(baselineBytes, &s.baseline))
	s.baselineSHA = t2Hash(baselineBytes)
	require.Equal(t, t2OfflineProtocol, s.baseline.Protocol)
	require.Equal(t, "reopened", s.baseline.Phase)
	require.Equal(t, "creator", s.baseline.Role)
	require.Equal(t, owner.Nonce, s.baseline.Nonce)
	require.Equal(t, t2NativeClientFixtureSHA, s.baseline.FixtureSHA)
	require.Equal(t, s.stateSHA, s.baseline.StateSHA)
	require.True(t, s.baseline.Closed && s.baseline.AccountStopped && s.baseline.Passed)
	require.Equal(t, "READ_AND_APPEND_NOT_LOGGED_IN", s.baseline.PostStop)
	require.Len(t, s.baseline.History.Changes, 8)
	require.Len(t, s.baseline.History.Parents, 7)
	require.Len(t, s.baseline.History.Heads, 2)
	require.Len(t, s.baseline.SnapshotSHA, 64)
	require.NotEmpty(t, s.baseline.PeerID)
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	s.c = &t2NativeClientCaller{t: t, rpc: rpc, role: "creator", nonce: owner.Nonce, returnedCalls: map[string]int{}}
	c := s.c
	SetEventHandler(func(*pb.Event) {})
	c.invoke("InitialSetParameters", InitialSetParameters, &pb.RpcInitialSetParametersRequest{
		Platform: "ios", Version: "0.51.0", Workdir: root, DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true},
		&pb.RpcInitialSetParametersResponse{}, 30*time.Second)
	version := &pb.RpcAppGetVersionResponse{}
	c.invoke("AppGetVersion", AppGetVersion, &pb.RpcAppGetVersionRequest{}, version, 10*time.Second)
	s.version = version.Version
	require.Equal(t, "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-"+t2LegacyPatch+
		"-pinkha-t2-registry-v1-"+t2AccountRegistrationSHA, s.version)
	t.Cleanup(s.close)
	key, err := os.ReadFile(filepath.Join(parent, "account-key.private"))
	require.NoError(t, err)
	require.NotEmpty(t, key)
	c.invoke("WalletRecover", WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)},
		&pb.RpcWalletRecoverResponse{}, 30*time.Second)
	c.startRequested = true
	selected := &pb.RpcAccountSelectResponse{}
	c.invoke("AccountSelect", AccountSelect, &pb.RpcAccountSelectRequest{Id: s.state.AccountID, RootPath: root,
		NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false, PreferredSpaceId: s.state.SpaceID}, selected, 120*time.Second)
	require.NotNil(t, selected.Account)
	require.Equal(t, s.state.AccountID, selected.Account.Id)
	c.invoke("WorkspaceOpen", WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: s.state.SpaceID}, &pb.RpcWorkspaceOpenResponse{}, 30*time.Second)
	t2OfflineNetwork(c, false)
	wallet := app.MustComponent[wallet.Wallet](mw.GetApp())
	s.peerID, s.author = wallet.Account().PeerId, wallet.Account().SignKey.GetPublic().Account()
	require.Equal(t, s.baseline.PeerID, s.peerID)
	require.Equal(t, filepath.Join(root, s.state.AccountID), wallet.RepoPath())
	return s
}

func (s *t2CrashSession) close() {
	c := s.c
	if c.startRequested && !c.stopAttempted {
		c.stopAttempted = true
		c.invoke("AccountStop", AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{}, 30*time.Second)
		require.Nil(c.t, mw.GetApp())
		c.invoke("AppShutdown", AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{}, 15*time.Second)
		c.closed = true
	}
}

func (s *t2CrashSession) report(phase string) map[string]any {
	namespace, err := os.Readlink("/proc/self/ns/net")
	require.NoError(s.c.t, err)
	return map[string]any{"protocol": t2CrashProtocol, "phase": phase, "role": "creator", "nonce": s.c.nonce,
		"pid": os.Getpid(), "network_namespace": namespace, "actual_ipv4": t2OfflineIPs(s.c.t),
		"native_network_mode": "DISCONNECTED_PROCESS_CRASH_NO_PEER_REPAIR", "peer_id": s.peerID,
		"heart_sha": vcs.GitCommit, "runtime_version": s.version, "client_fixture_sha256": t2NativeClientFixtureSHA,
		"rpc_manifest_sha256": t2RPCAccountSchemaSHA, "registration_patch_sha256": t2AccountRegistrationSHA,
		"state_sha256": s.stateSHA, "clean_reopen_receipt_sha256": s.baselineSHA,
		"app_capability": "OFF", "power_loss": "NOT_RUN", "two_ios_apps": "NOT_RUN", "full_t2_acceptance": "NOT_RUN"}
}

func t2WriteCrashReport(t *testing.T, name string, report map[string]any) {
	t.Helper()
	encoded, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	t2NativeClientReport(t, filepath.Join("/private", name), encoded)
}

// This test is expected to have no terminal PASS: the host kills its exact
// owned container after validating crash-armed.json. Timeout is a real failure.
func TestT2NativeClientCrashCommitPhase(t *testing.T) {
	s := t2OpenCrashSession(t, "commit")
	c := s.c
	beforeHistory := t2OfflineHistoryRead(t, s.state)
	require.Equal(t, s.baseline.History, beforeHistory)
	before := t2OfflineRead(c, s.state, 30*time.Second)
	ready, err := t2OfflineSnapshotReady(s.state, s.author, before, beforeHistory.Heads)
	require.NoError(t, err)
	require.True(t, ready)
	require.Equal(t, s.baseline.SnapshotSHA, t2OfflineSnapshotHash(t, before.Snapshot))
	operation := t2CrashOperation(s.state, s.author)
	claimID, _, err := t2OfflineClaim(operation)
	require.NoError(t, err)
	encoded, err := proto.Marshal(t2OfflineRequest(operation))
	require.NoError(t, err)
	// The original client request is retained outside the DB and never uploaded.
	requestPath := filepath.Join("/private", "crash-request.private")
	t2WriteFresh(t, requestPath, encoded)
	requestMetadata, err := os.Lstat(requestPath)
	require.NoError(t, err)
	require.True(t, requestMetadata.Mode().IsRegular())
	require.Equal(t, os.FileMode(0o600), requestMetadata.Mode().Perm())
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	observed := make(chan t2CrashByteObservation, 1)
	c.rpc.calls["PinkhaTorahOperationsAppend"]++
	done := t2ClientByteWorker(t2CrashHoldReply(ctx, PinkhaTorahOperationsAppend, observed), encoded)
	// Failure-only cleanup retains the native Stop and a bounded worker join.
	// SIGKILL executes neither this callback nor the session's graceful cleanup.
	t.Cleanup(func() {
		t2CrashCleanup(cancel, s.close, func() {
			select {
			case <-done:
			case <-time.After(15 * time.Second):
				t.Error("crash byte worker did not join after cancellation and native stop")
			}
		})
	})
	var observation t2CrashByteObservation
	select {
	case observation = <-observed:
	case reply := <-done:
		require.False(t, reply.panicked, "native append panicked before crash arming")
		t.Fatal("client byte call returned before crash arming")
	case <-ctx.Done():
		t.Fatal("native append did not reach the bounded crash gate")
	}
	require.Equal(t, t2Hash(encoded), observation.RequestSHA)
	require.Equal(t, len(encoded), observation.RequestBytes)
	require.Greater(t, observation.ReplyBytes, 0)
	committed := t2OfflineHistoryRead(t, s.state)
	changeID, err := t2CrashCommittedChange(beforeHistory, committed)
	require.NoError(t, err)
	require.NoError(t, ctx.Err())
	deadline, ok := ctx.Deadline()
	require.True(t, ok)
	require.Greater(t, time.Until(deadline), 45*time.Second)
	select {
	case <-done:
		t.Fatal("client byte boundary unexpectedly completed")
	default:
	}
	require.Zero(t, c.returnedCalls["PinkhaTorahOperationsAppend"])
	require.Equal(t, 1, c.rpc.calls["PinkhaTorahOperationsReadTarget"])
	require.Zero(t, c.rpc.calls["AccountStop"])
	require.Zero(t, c.rpc.calls["AppShutdown"])
	report := s.report("armed_after_signed_commit_before_client_ack")
	report["history_before"], report["history_committed"] = beforeHistory, committed
	report["baseline_snapshot_sha256"] = s.baseline.SnapshotSHA
	report["request_sha256"], report["request_bytes"] = observation.RequestSHA, observation.RequestBytes
	report["withheld_response_bytes"] = observation.ReplyBytes
	report["claim_id"], report["committed_change_id"] = claimID, changeID
	report["first_reply_decoded"], report["client_append_returned"] = false, false
	report["read_target_after_commit"], report["native_append_attempts"] = 0, 1
	report["rpc_calls"], report["returned_byte_calls"] = c.rpc.calls, c.returnedCalls
	report["kill_deadline_unix_ns"] = time.Now().Add(30 * time.Second).UnixNano()
	report["expected_termination"], report["test_passed"] = "OWNED_CONTAINER_SIGKILL", false
	t2WriteCrashReport(t, "crash-armed.json", report)
	select {
	case <-done:
		t.Fatal("armed client byte boundary completed without the required process kill")
	case <-ctx.Done():
		t.Fatal("owned process was not killed inside the bounded crash window")
	}
}

type t2CrashArm struct {
	Protocol        string           `json:"protocol"`
	Phase           string           `json:"phase"`
	Role            string           `json:"role"`
	Nonce           string           `json:"nonce"`
	PeerID          string           `json:"peer_id"`
	FixtureSHA      string           `json:"client_fixture_sha256"`
	StateSHA        string           `json:"state_sha256"`
	BaselineSHA     string           `json:"clean_reopen_receipt_sha256"`
	HistoryBefore   t2OfflineHistory `json:"history_before"`
	History         t2OfflineHistory `json:"history_committed"`
	BaselineViewSHA string           `json:"baseline_snapshot_sha256"`
	RequestSHA      string           `json:"request_sha256"`
	RequestBytes    int              `json:"request_bytes"`
	ClaimID         string           `json:"claim_id"`
	ChangeID        string           `json:"committed_change_id"`
	Decoded         bool             `json:"first_reply_decoded"`
	Returned        bool             `json:"client_append_returned"`
	ReadsAfter      int              `json:"read_target_after_commit"`
	Attempts        int              `json:"native_append_attempts"`
	ExpectedStop    string           `json:"expected_termination"`
	Passed          bool             `json:"test_passed"`
}

func t2CrashVerifySnapshot(t *testing.T, s *t2CrashSession, response *pb.RpcPinkhaTorahOperationsReadTargetResponse,
	operation torahops.Operation, heads []string) {
	t.Helper()
	require.NotNil(t, response)
	require.Equal(t, uint32(1), response.ProtocolVersion)
	require.NotNil(t, response.Error)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, response.Error.Code)
	require.Empty(t, response.Error.Issues)
	require.NotNil(t, response.Snapshot)
	require.Equal(t, pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE, response.Snapshot.Scope)
	require.Equal(t, heads, response.Snapshot.VerifiedLocalHeads)
	require.Len(t, response.Snapshot.Live, 3)
	base := proto.Clone(response).(*pb.RpcPinkhaTorahOperationsReadTargetResponse)
	base.Snapshot.Live = nil
	claimID, _, err := t2OfflineClaim(operation)
	require.NoError(t, err)
	newClaims := 0
	for _, claim := range response.Snapshot.Live {
		require.NotNil(t, claim)
		if claim.ClaimId == claimID {
			require.True(t, t2OfflineClaimMatches(claim, operation))
			newClaims++
		} else {
			base.Snapshot.Live = append(base.Snapshot.Live, proto.Clone(claim).(*pb.RpcPinkhaTorahOperationsClaim))
		}
	}
	require.Equal(t, 1, newClaims)
	base.Snapshot.VerifiedLocalHeads = slices.Clone(s.baseline.History.Heads)
	ready, err := t2OfflineSnapshotReady(s.state, s.author, base, s.baseline.History.Heads)
	require.NoError(t, err)
	require.True(t, ready)
	require.Equal(t, s.baseline.SnapshotSHA, t2OfflineSnapshotHash(t, base.Snapshot), "all baseline claims and conflict variants must remain exact")
}

func TestT2NativeClientCrashRecoverPhase(t *testing.T) {
	s := t2OpenCrashSession(t, "recover")
	c := s.c
	armBytes, err := os.ReadFile(filepath.Join("/private", "crash-armed.json"))
	require.NoError(t, err)
	arm := t2CrashArm{}
	require.NoError(t, json.Unmarshal(armBytes, &arm))
	require.Equal(t, t2CrashProtocol, arm.Protocol)
	require.Equal(t, "armed_after_signed_commit_before_client_ack", arm.Phase)
	require.Equal(t, "creator", arm.Role)
	require.Equal(t, c.nonce, arm.Nonce)
	require.Equal(t, s.peerID, arm.PeerID)
	require.Equal(t, t2NativeClientFixtureSHA, arm.FixtureSHA)
	require.Equal(t, s.stateSHA, arm.StateSHA)
	require.Equal(t, s.baselineSHA, arm.BaselineSHA)
	require.Equal(t, s.baseline.SnapshotSHA, arm.BaselineViewSHA)
	require.Equal(t, s.baseline.History, arm.HistoryBefore)
	require.Equal(t, "OWNED_CONTAINER_SIGKILL", arm.ExpectedStop)
	require.False(t, arm.Passed || arm.Decoded || arm.Returned)
	require.Zero(t, arm.ReadsAfter)
	require.Equal(t, 1, arm.Attempts)
	changeID, err := t2CrashCommittedChange(arm.HistoryBefore, arm.History)
	require.NoError(t, err)
	require.Equal(t, arm.ChangeID, changeID)
	operation := t2CrashOperation(s.state, s.author)
	claimID, _, err := t2OfflineClaim(operation)
	require.NoError(t, err)
	require.Equal(t, claimID, arm.ClaimID)
	// Signed disk history is observed before any post-crash ReadTarget or retry.
	beforeHistory := t2OfflineHistoryRead(t, s.state)
	require.Equal(t, arm.History, beforeHistory)
	before := t2OfflineRead(c, s.state, 30*time.Second)
	t2CrashVerifySnapshot(t, s, before, operation, arm.History.Heads)
	require.Equal(t, arm.History, t2OfflineHistoryRead(t, s.state))
	beforeBytes, err := proto.Marshal(before)
	require.NoError(t, err)
	requestPath := filepath.Join("/private", "crash-request.private")
	metadata, err := os.Lstat(requestPath)
	require.NoError(t, err)
	require.True(t, metadata.Mode().IsRegular())
	require.Equal(t, os.FileMode(0o600), metadata.Mode().Perm())
	encoded, err := os.ReadFile(requestPath)
	require.NoError(t, err)
	require.Equal(t, arm.RequestSHA, t2Hash(encoded))
	require.Equal(t, arm.RequestBytes, len(encoded))
	request := &pb.RpcPinkhaTorahOperationsAppendRequest{}
	require.NoError(t, proto.Unmarshal(encoded, request))
	require.True(t, proto.Equal(t2OfflineRequest(operation), request))
	actualRequestSHA, retryCalls := "", 0
	c.rpc.calls["PinkhaTorahOperationsAppend"]++
	reply := c.callBytes("PinkhaTorahOperationsAppend", func(data []byte) []byte {
		actualRequestSHA, retryCalls = t2Hash(data), retryCalls+1
		return PinkhaTorahOperationsAppend(data)
	}, encoded, 30*time.Second)
	require.Equal(t, 1, retryCalls)
	require.Equal(t, arm.RequestSHA, actualRequestSHA)
	retry := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	require.NoError(t, proto.Unmarshal(reply, retry))
	require.Equal(t, uint32(1), retry.ProtocolVersion)
	require.NotNil(t, retry.Error)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, retry.Error.Code)
	require.Empty(t, retry.Error.Issues)
	require.NotNil(t, retry.Receipt)
	require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, retry.Receipt.Disposition)
	require.Empty(t, retry.Receipt.ChangeId)
	require.Equal(t, claimID, retry.Receipt.ClaimId)
	require.NotNil(t, retry.Receipt.Resolution)
	require.Equal(t, operation.OperationID, retry.Receipt.Resolution.OperationId)
	require.False(t, retry.Receipt.Resolution.Conflict)
	require.Len(t, retry.Receipt.Resolution.Claims, 1)
	require.True(t, t2OfflineClaimMatches(retry.Receipt.Resolution.Claims[0], operation))
	after := t2OfflineRead(c, s.state, 30*time.Second)
	require.True(t, proto.Equal(before, after), "retry cannot change any snapshot field or local sequence")
	afterHistory := t2OfflineHistoryRead(t, s.state)
	require.Equal(t, beforeHistory, afterHistory)
	afterBytes, err := proto.Marshal(after)
	require.NoError(t, err)
	report := s.report("recovered_state_before_native_stop")
	report["armed_receipt_sha256"], report["request_sha256"], report["retry_request_sha256"] = t2Hash(armBytes), arm.RequestSHA, actualRequestSHA
	report["request_bytes"], report["claim_id"], report["committed_change_id"] = len(encoded), claimID, changeID
	report["history_before_read"], report["history_after_retry"] = beforeHistory, afterHistory
	report["snapshot_before_retry_sha256"], report["snapshot_after_retry_sha256"] = t2Hash(beforeBytes), t2Hash(afterBytes)
	report["local_sequence_before_retry"], report["local_sequence_after_retry"] = before.Snapshot.LocalAppliedSeq, after.Snapshot.LocalAppliedSeq
	report["retry_disposition"], report["retry_change_id"] = "ALREADY_EXISTS_SAME_PAYLOAD", retry.Receipt.ChangeId
	report["rpc_calls"], report["returned_byte_calls"] = c.rpc.calls, c.returnedCalls
	report["test_passed"] = false
	t2WriteCrashReport(t, "crash-recover-ready.json", report)
	command := t2OfflineWaitCommand(c, "/private", "crash-recover-stop", 60*time.Second)
	require.Empty(t, command.History.Changes)
	s.close()
	require.True(t, c.closed)
	appendRequest, readRequest := t2NativeRPCRequests(s.state)
	deniedRead, deniedWrite := &pb.RpcPinkhaTorahOperationsReadTargetResponse{}, &pb.RpcPinkhaTorahOperationsAppendResponse{}
	c.raw("PinkhaTorahOperationsReadTarget", PinkhaTorahOperationsReadTarget, readRequest, deniedRead, 10*time.Second)
	c.raw("PinkhaTorahOperationsAppend", PinkhaTorahOperationsAppend, appendRequest, deniedWrite, 10*time.Second)
	require.Equal(t, uint32(1), deniedRead.ProtocolVersion)
	require.Equal(t, uint32(1), deniedWrite.ProtocolVersion)
	require.NotNil(t, deniedRead.Error)
	require.NotNil(t, deniedWrite.Error)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NOT_LOGGED_IN, deniedRead.Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NOT_LOGGED_IN, deniedWrite.Error.Code)
	require.Nil(t, deniedRead.Snapshot)
	require.Nil(t, deniedWrite.Receipt)
	report["phase"] = "recovered_after_owned_sigkill"
	report["rpc_calls"], report["returned_byte_calls"] = c.rpc.calls, c.returnedCalls
	report["account_stop_verified"], report["closed"], report["test_passed"] = true, true, true
	report["post_stop_rpc"] = "READ_AND_APPEND_NOT_LOGGED_IN"
	t2WriteCrashReport(t, "crash-recovered.json", report)
	t.Log("PASS original native store recovered after owned process kill; exact request retry created no signed change")
}

func TestT2NativeCrashByteGateControls(t *testing.T) {
	t.Run("fatal_close_still_runs_bounded_join", func(t *testing.T) {
		events := make(chan string, 3)
		done := make(chan struct{})
		go func() {
			defer close(done)
			t2CrashCleanup(func() { events <- "cancel" }, func() {
				events <- "close"
				runtime.Goexit()
			}, func() { events <- "join" })
		}()
		select {
		case <-done:
		case <-time.After(time.Second):
			t.Fatal("Goexit cleanup did not complete")
		}
		require.Len(t, events, 3)
		require.Equal(t, []string{"cancel", "close", "join"}, []string{<-events, <-events, <-events})
	})
	t.Run("actual_reply_is_held_until_failure_cancellation", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()
		observed := make(chan t2CrashByteObservation, 1)
		done := t2ClientByteWorker(t2CrashHoldReply(ctx, func(data []byte) []byte {
			return []byte("opaque-not-protobuf-reply")
		}, observed), []byte("synthetic-encoded-request"))
		value := <-observed
		require.Equal(t, t2Hash([]byte("synthetic-encoded-request")), value.RequestSHA)
		require.Equal(t, len("synthetic-encoded-request"), value.RequestBytes)
		require.Greater(t, value.ReplyBytes, 0)
		select {
		case <-done:
			t.Fatal("client unexpectedly received the held response")
		default:
		}
		cancel()
		select {
		case value := <-done:
			require.Nil(t, value.data)
			require.False(t, value.panicked)
		case <-time.After(time.Second):
			t.Fatal("cancelled gate did not join")
		}
	})
	t.Run("native_panic_never_arms_a_committed_reply", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()
		observed := make(chan t2CrashByteObservation, 1)
		done := t2ClientByteWorker(t2CrashHoldReply(ctx, func([]byte) []byte { panic("synthetic") }, observed), nil)
		select {
		case reply := <-done:
			require.True(t, reply.panicked)
		case <-time.After(time.Second):
			t.Fatal("panic worker did not join")
		}
		require.Empty(t, observed)
	})
}

func TestT2NativeCrashHistoryControls(t *testing.T) {
	before := t2OfflineHistory{Changes: map[string]string{}, Parents: map[string][]string{}, Heads: []string{"old-6", "old-7"}}
	for index := 0; index < 8; index++ {
		id := fmt.Sprintf("old-%d", index)
		before.Changes[id] = fmt.Sprintf("%064x", index+1)
		if index > 0 {
			parent := index - 1
			if index == 7 {
				parent = 5
			}
			before.Parents[id] = []string{fmt.Sprintf("old-%d", parent)}
		}
	}
	encoded, err := json.Marshal(before)
	require.NoError(t, err)
	valid := t2OfflineHistory{}
	require.NoError(t, json.Unmarshal(encoded, &valid))
	valid.Changes["new"] = fmt.Sprintf("%064x", 9)
	valid.Parents["new"], valid.Heads = slices.Clone(before.Heads), []string{"new"}
	t.Run("one_signed_child_joins_both_existing_heads", func(t *testing.T) {
		id, err := t2CrashCommittedChange(before, valid)
		require.NoError(t, err)
		require.Equal(t, "new", id)
	})
	for _, test := range []struct {
		name   string
		change func(*t2OfflineHistory)
	}{
		{"missing_commit", func(h *t2OfflineHistory) { delete(h.Changes, "new") }},
		{"extra_commit", func(h *t2OfflineHistory) { h.Changes["extra"] = fmt.Sprintf("%064x", 10) }},
		{"changed_original_bytes", func(h *t2OfflineHistory) { h.Changes["old-0"] = fmt.Sprintf("%064x", 10) }},
		{"changed_original_parent", func(h *t2OfflineHistory) { h.Parents["old-7"] = []string{"old-4"} }},
		{"missing_second_parent", func(h *t2OfflineHistory) { h.Parents["new"] = []string{"old-6"} }},
		{"wrong_head", func(h *t2OfflineHistory) { h.Heads = []string{"old-6"} }},
	} {
		t.Run(test.name, func(t *testing.T) {
			encoded, err := json.Marshal(valid)
			require.NoError(t, err)
			changed := t2OfflineHistory{}
			require.NoError(t, json.Unmarshal(encoded, &changed))
			test.change(&changed)
			id, err := t2CrashCommittedChange(before, changed)
			require.Error(t, err)
			require.Empty(t, id)
		})
	}
}
