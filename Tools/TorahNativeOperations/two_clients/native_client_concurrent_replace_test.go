package service

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"slices"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/space/spacecore/clientserver"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

const t2ConcurrentReplaceProtocol = "pinkha-t2-native-concurrent-replace-v1"

// Commands contain only a phase and expected signed IDs/hashes. Each request
// is constructed inside its own original native account, from its own read.
type t2ConcurrentReplaceCommand struct {
	Protocol string           `json:"protocol"`
	Nonce    string           `json:"nonce"`
	Role     string           `json:"role"`
	Phase    string           `json:"phase"`
	History  t2OfflineHistory `json:"expected_history"`
}

type t2ConcurrentReplaceSession struct {
	c                  *t2NativeClientCaller
	state              *t2AccountState
	baseline           t2CrashBaseline
	baselineSHA        string
	stateSHA           string
	peerID             string
	author             string
	version            string
	serverPort         int
	deadline           time.Time
	networkState       string
	predecessor        *pb.RpcPinkhaTorahOperationsClaim
	baselineRead       *pb.RpcPinkhaTorahOperationsReadTargetResponse
	predecessorReadSHA string
}

func (s *t2ConcurrentReplaceSession) budget(maximum time.Duration) time.Duration {
	left := time.Until(s.deadline)
	require.Greater(s.c.t, left, time.Duration(0), "one fixed concurrent-replace process deadline")
	return min(left, maximum)
}

func (s *t2ConcurrentReplaceSession) close() {
	c := s.c
	if c.startRequested && !c.stopAttempted {
		c.stopAttempted = true
		c.invoke("AccountStop", AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{}, 30*time.Second)
		require.Nil(c.t, mw.GetApp())
		c.invoke("AppShutdown", AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{}, 15*time.Second)
		c.closed = true
	}
}

func t2OpenConcurrentReplaceSession(t *testing.T, role string) *t2ConcurrentReplaceSession {
	t.Helper()
	require.Contains(t, []string{"creator", "recovered"}, role)
	require.Equal(t, role, os.Getenv("PINKHA_T2_CLIENT_ROLE"))
	require.Equal(t, t2ConcurrentReplaceProtocol, os.Getenv("PINKHA_T2_CONCURRENT_REPLACE_PHASE"))
	require.Empty(t, os.Getenv("PINKHA_T2_CRASH_PHASE"))
	require.Empty(t, os.Getenv("PINKHA_T2_OBSERVED_REMOVE_PHASE"))
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
	require.Equal(t, role, owner.Role)
	require.NotEmpty(t, owner.Nonce)
	require.Equal(t, owner.Nonce, os.Getenv("PINKHA_T2_CLIENT_NONCE"))
	require.True(t, owner.SyntheticOnly)
	entries, err := os.ReadDir(root)
	require.NoError(t, err)
	require.NotEmpty(t, entries, "the tail must retain each original account store")
	require.Len(t, t2OfflineIPs(t), 1, "the tail requires its actual owned LAN interface")
	stateBytes, err := os.ReadFile(filepath.Join(parent, "state.json"))
	require.NoError(t, err)
	s := &t2ConcurrentReplaceSession{state: &t2AccountState{}, stateSHA: t2Hash(stateBytes), deadline: time.Now().Add(600 * time.Second)}
	require.NoError(t, json.Unmarshal(stateBytes, s.state))
	baselineBytes, err := os.ReadFile(filepath.Join(parent, "reopened.json"))
	require.NoError(t, err)
	require.NoError(t, json.Unmarshal(baselineBytes, &s.baseline))
	s.baselineSHA = t2Hash(baselineBytes)
	require.Equal(t, t2OfflineProtocol, s.baseline.Protocol)
	require.Equal(t, "reopened", s.baseline.Phase)
	require.Equal(t, role, s.baseline.Role)
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
	s.c = &t2NativeClientCaller{t: t, rpc: rpc, role: role, nonce: owner.Nonce, returnedCalls: map[string]int{}}
	c := s.c
	SetEventHandler(func(*pb.Event) {})
	c.invoke("InitialSetParameters", InitialSetParameters, &pb.RpcInitialSetParametersRequest{
		Platform: "ios", Version: "0.51.0", Workdir: root, DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true},
		&pb.RpcInitialSetParametersResponse{}, s.budget(30*time.Second))
	version := &pb.RpcAppGetVersionResponse{}
	c.invoke("AppGetVersion", AppGetVersion, &pb.RpcAppGetVersionRequest{}, version, s.budget(10*time.Second))
	s.version = version.Version
	require.Equal(t, "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-"+t2LegacyPatch+
		"-pinkha-t2-registry-v1-"+t2AccountRegistrationSHA, s.version)
	t.Cleanup(s.close)
	key, err := os.ReadFile(filepath.Join(parent, "account-key.private"))
	require.NoError(t, err)
	require.NotEmpty(t, key)
	c.invoke("WalletRecover", WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)},
		&pb.RpcWalletRecoverResponse{}, s.budget(30*time.Second))
	c.startRequested = true
	selected := &pb.RpcAccountSelectResponse{}
	c.invoke("AccountSelect", AccountSelect, &pb.RpcAccountSelectRequest{Id: s.state.AccountID, RootPath: root,
		NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false, PreferredSpaceId: s.state.SpaceID},
		selected, s.budget(120*time.Second))
	require.NotNil(t, selected.Account)
	require.Equal(t, s.state.AccountID, selected.Account.Id)
	c.invoke("WorkspaceOpen", WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: s.state.SpaceID},
		&pb.RpcWorkspaceOpenResponse{}, s.budget(30*time.Second))
	t2OfflineNetwork(c, true)
	s.networkState = "WIFI"
	wallet := app.MustComponent[wallet.Wallet](mw.GetApp())
	s.peerID, s.author = wallet.Account().PeerId, wallet.Account().SignKey.GetPublic().Account()
	require.Equal(t, s.baseline.PeerID, s.peerID)
	require.Equal(t, filepath.Join(root, s.state.AccountID), wallet.RepoPath())
	server := app.MustComponent[clientserver.ClientServer](mw.GetApp())
	t2NativeClientWait(t, "native LAN server after original-store reopen", s.budget(30*time.Second),
		func(time.Duration) bool { return server.ServerStarted() })
	s.serverPort = int(server.Port())
	require.Greater(t, s.serverPort, 0)
	// The native handler derives AuthorID from SignKey, not the device PeerID.
	// Prove it against the original real claim on BOTH accounts before writing.
	original := torahops.Operation{Version: 1, SpaceID: s.state.SpaceID, OperationID: fmt.Sprintf("%032x", 1),
		AuthorID: s.author, Kind: torahops.Add, Target: torahops.Target{ObjectID: s.state.DocumentID, BlockID: s.state.BlockID},
		Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:t2-account:1"}, Payload: []byte(t2PrivatePayload)}
	originalID, originalSHA, err := t2OfflineClaim(original)
	require.NoError(t, err)
	require.Equal(t, s.state.OperationID, original.OperationID)
	require.Equal(t, s.state.ClaimID, originalID)
	require.Equal(t, s.state.OperationSHA256, originalSHA)
	return s
}

// These conversions are local assertions/re-encoding of an actual native
// response. Neither a host command nor a fixture file provides an operation.
func t2ConcurrentReplaceOperation(claim *pb.RpcPinkhaTorahOperationsClaim) (torahops.Operation, error) {
	if claim == nil || claim.Operation == nil || claim.Operation.Target == nil || claim.Operation.Source == nil {
		return torahops.Operation{}, fmt.Errorf("missing complete native claim")
	}
	wire := claim.Operation
	kind := torahops.Add
	if wire.Kind == pb.RpcPinkhaTorahOperations_REPLACE {
		kind = torahops.Replace
	} else if wire.Kind != pb.RpcPinkhaTorahOperations_ADD {
		return torahops.Operation{}, fmt.Errorf("unexpected native claim kind")
	}
	op := torahops.Operation{Version: wire.Version, SpaceID: wire.SpaceId, OperationID: wire.OperationId,
		AuthorID: wire.AuthorId, Kind: kind, Target: torahops.Target{ObjectID: wire.Target.ObjectId, BlockID: wire.Target.BlockId},
		Source:  torahops.Source{ProviderID: wire.Source.ProviderId, CanonicalRef: wire.Source.CanonicalRef},
		Payload: slices.Clone(wire.Payload), Observed: slices.Clone(wire.ObservedClaimIds)}
	id, digest, err := t2OfflineClaim(op)
	if err != nil || id != claim.ClaimId || digest != claim.Digest {
		return torahops.Operation{}, fmt.Errorf("native claim content identity mismatch")
	}
	return op, nil
}

func t2ConcurrentReplaceMatches(claim *pb.RpcPinkhaTorahOperationsClaim, expected torahops.Operation) bool {
	actual, err := t2ConcurrentReplaceOperation(claim)
	if err != nil || !slices.Equal(actual.Observed, expected.Observed) {
		return false
	}
	a, errA := actual.CanonicalBytes()
	b, errB := expected.CanonicalBytes()
	return errA == nil && errB == nil && bytes.Equal(a, b)
}

func (s *t2ConcurrentReplaceSession) replacement(role string) torahops.Operation {
	require.Contains(s.c.t, []string{"creator", "recovered"}, role)
	op, err := t2ConcurrentReplaceOperation(s.predecessor)
	require.NoError(s.c.t, err)
	require.Equal(s.c.t, s.author, op.AuthorID)
	require.Equal(s.c.t, fmt.Sprintf("%032x", 2), op.OperationID)
	require.Equal(s.c.t, torahops.Add, op.Kind)
	number := 8
	if role == "recovered" {
		number = 9
	}
	op.OperationID, op.Kind = fmt.Sprintf("%032x", number), torahops.Replace
	op.Payload, op.Observed = []byte("t2-concurrent-replace-"+role), []string{s.predecessor.ClaimId}
	return op
}

func t2ConcurrentReplaceHash(t *testing.T, message proto.Message) string {
	t.Helper()
	raw, err := proto.Marshal(message)
	require.NoError(t, err)
	return t2Hash(raw)
}

func t2ConcurrentReplaceClaimEvidence(t *testing.T, claim *pb.RpcPinkhaTorahOperationsClaim) map[string]any {
	t.Helper()
	op, err := t2ConcurrentReplaceOperation(claim)
	require.NoError(t, err)
	return map[string]any{"operation_id": op.OperationID, "claim_id": claim.ClaimId, "digest": claim.Digest,
		"author_id": op.AuthorID, "kind": claim.Operation.Kind.String(),
		"target_sha256": t2ConcurrentReplaceHash(t, claim.Operation.Target),
		"source_sha256": t2ConcurrentReplaceHash(t, claim.Operation.Source), "payload_sha256": t2Hash(op.Payload),
		"observed_claim_ids": append([]string{}, op.Observed...), "claim_response_sha256": t2ConcurrentReplaceHash(t, claim)}
}

func (s *t2ConcurrentReplaceSession) verifySnapshot(read *pb.RpcPinkhaTorahOperationsReadTargetResponse,
	mode string, history t2OfflineHistory) error {
	if read == nil || read.ProtocolVersion != 1 || read.Error == nil ||
		read.Error.Code != pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL || len(read.Error.Issues) != 0 ||
		read.Snapshot == nil || read.Snapshot.Scope != pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE ||
		len(read.Snapshot.PendingObservedClaimIds) != 0 || read.Snapshot.LocalAppliedSeq == 0 {
		return fmt.Errorf("invalid native replacement snapshot")
	}
	heads := slices.Clone(read.Snapshot.VerifiedLocalHeads)
	slices.Sort(heads)
	if !slices.Equal(heads, history.Heads) {
		return fmt.Errorf("unexpected native signed heads")
	}
	previousOperation, previousClaim := "", ""
	for index, claim := range read.Snapshot.Live {
		op, err := t2ConcurrentReplaceOperation(claim)
		if err != nil {
			return err
		}
		if index > 0 && (op.OperationID < previousOperation ||
			(op.OperationID == previousOperation && claim.ClaimId <= previousClaim)) {
			return fmt.Errorf("live claims must retain actual bytewise OperationID/ClaimID order")
		}
		previousOperation, previousClaim = op.OperationID, claim.ClaimId
	}
	if mode == "baseline" {
		ready, err := t2OfflineSnapshotReady(s.state, s.author, read, history.Heads)
		if err != nil || !ready || t2OfflineSnapshotHash(s.c.t, read.Snapshot) != s.baseline.SnapshotSHA {
			return fmt.Errorf("original exact baseline projection changed")
		}
		return nil
	}
	if mode != "local" && mode != "merged" {
		return fmt.Errorf("unknown fixed native replacement phase")
	}
	if s.predecessor == nil || s.baselineRead == nil ||
		len(read.Snapshot.Conflicts) != 1 || !proto.Equal(read.Snapshot.Conflicts[0], s.baselineRead.Snapshot.Conflicts[0]) {
		return fmt.Errorf("original conflict provenance changed")
	}
	expected := map[string]torahops.Operation{}
	other := t2OfflineExpected(s.state, s.author, "recovered")[0]
	otherID, _, err := t2OfflineClaim(other)
	if err != nil {
		return err
	}
	expected[otherID] = other
	roles := []string{s.c.role}
	if mode == "merged" {
		roles = []string{"creator", "recovered"}
	}
	for _, role := range roles {
		op := s.replacement(role)
		id, _, err := t2OfflineClaim(op)
		if err != nil || expected[id].OperationID != "" {
			return fmt.Errorf("replacement identity is not independent")
		}
		expected[id] = op
	}
	if len(read.Snapshot.Live) != len(expected) {
		return fmt.Errorf("a live successor or unrelated baseline claim was lost")
	}
	for _, claim := range read.Snapshot.Live {
		op, ok := expected[claim.ClaimId]
		if !ok || !t2ConcurrentReplaceMatches(claim, op) {
			return fmt.Errorf("unexpected, revived or altered native claim")
		}
	}
	return nil
}

func (s *t2ConcurrentReplaceSession) read(mode string, history t2OfflineHistory,
	previousMode string, previousHistory t2OfflineHistory) *pb.RpcPinkhaTorahOperationsReadTargetResponse {
	var result *pb.RpcPinkhaTorahOperationsReadTargetResponse
	t2NativeClientWait(s.c.t, "native replacement observation", s.budget(90*time.Second), func(remaining time.Duration) bool {
		result = t2OfflineRead(s.c, s.state, min(remaining, s.budget(20*time.Second)))
		if result.Error != nil && result.Error.Code != pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL {
			// Only the pre-existing explicit projection-behind category can wait.
			_, err := t2OfflineSnapshotReady(s.state, s.author, result, history.Heads)
			require.NoError(s.c.t, err)
			return false
		}
		require.NotNil(s.c.t, result.Snapshot)
		heads := slices.Clone(result.Snapshot.VerifiedLocalHeads)
		slices.Sort(heads)
		if slices.Equal(heads, history.Heads) {
			require.NoError(s.c.t, s.verifySnapshot(result, mode, history))
			require.Equal(s.c.t, history, t2OfflineHistoryRead(s.c.t, s.state, min(remaining, s.budget(20*time.Second))))
			return true
		}
		require.Equal(s.c.t, previousHistory.Heads, heads)
		require.NoError(s.c.t, s.verifySnapshot(result, previousMode, previousHistory))
		return false
	})
	return result
}

func (s *t2ConcurrentReplaceSession) capturePredecessor(read *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
	expected := t2OfflineExpected(s.state, s.author, "creator")[0]
	id, _, err := t2OfflineClaim(expected)
	require.NoError(s.c.t, err)
	var found *pb.RpcPinkhaTorahOperationsClaim
	for _, claim := range read.Snapshot.Live {
		if claim.ClaimId == id {
			require.Nil(s.c.t, found)
			require.True(s.c.t, t2ConcurrentReplaceMatches(claim, expected))
			found = claim
		}
	}
	require.NotNil(s.c.t, found)
	if s.predecessor != nil {
		require.True(s.c.t, proto.Equal(s.predecessor, found))
	}
	s.predecessor = proto.Clone(found).(*pb.RpcPinkhaTorahOperationsClaim)
	s.predecessorReadSHA = t2ConcurrentReplaceHash(s.c.t, read)
}

func (s *t2ConcurrentReplaceSession) command(phase string) t2ConcurrentReplaceCommand {
	var command t2ConcurrentReplaceCommand
	t2NativeClientWait(s.c.t, "fixed concurrent-replace command", s.budget(240*time.Second), func(time.Duration) bool {
		path := filepath.Join("/private", "replace-"+phase+".command.json")
		info, err := os.Lstat(path)
		if os.IsNotExist(err) {
			return false
		}
		require.NoError(s.c.t, err)
		require.True(s.c.t, info.Mode().IsRegular())
		require.LessOrEqual(s.c.t, info.Size(), int64(64*1024))
		data, err := os.ReadFile(path)
		require.NoError(s.c.t, err)
		decoder := json.NewDecoder(bytes.NewReader(data))
		decoder.DisallowUnknownFields()
		require.NoError(s.c.t, decoder.Decode(&command))
		require.Equal(s.c.t, io.EOF, decoder.Decode(new(any)))
		require.Equal(s.c.t, t2ConcurrentReplaceProtocol, command.Protocol)
		require.Equal(s.c.t, s.c.nonce, command.Nonce)
		require.Equal(s.c.t, s.c.role, command.Role)
		require.Equal(s.c.t, phase, command.Phase)
		return true
	})
	return command
}

func (s *t2ConcurrentReplaceSession) append(op torahops.Operation, retry bool) map[string]any {
	require.Contains(s.c.t, []torahops.Kind{torahops.Add, torahops.Replace}, op.Kind)
	request := t2OfflineRequest(op)
	if op.Kind == torahops.Replace {
		// The accepted ADD/REMOVE helper is unchanged. Select the generated
		// REPLACE enum explicitly here, without adding any authority field.
		request.Kind = pb.RpcPinkhaTorahOperations_REPLACE
	}
	encoded, err := proto.Marshal(request)
	require.NoError(s.c.t, err)
	var actualSHA string
	var actualBytes, calls int
	entry := func(data []byte) []byte {
		actualSHA, actualBytes = t2Hash(data), len(data)
		calls++
		return PinkhaTorahOperationsAppend(data)
	}
	response := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	s.c.raw("PinkhaTorahOperationsAppend", entry, request, response, s.budget(20*time.Second))
	require.Equal(s.c.t, 1, calls)
	require.Equal(s.c.t, t2Hash(encoded), actualSHA)
	require.Equal(s.c.t, len(encoded), actualBytes)
	require.Equal(s.c.t, uint32(1), response.ProtocolVersion)
	require.NotNil(s.c.t, response.Error)
	require.Equal(s.c.t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, response.Error.Code)
	require.Empty(s.c.t, response.Error.Issues)
	receipt := response.Receipt
	require.NotNil(s.c.t, receipt)
	id, _, err := t2OfflineClaim(op)
	require.NoError(s.c.t, err)
	require.Equal(s.c.t, id, receipt.ClaimId)
	require.NotNil(s.c.t, receipt.Resolution)
	require.Equal(s.c.t, op.OperationID, receipt.Resolution.OperationId)
	require.False(s.c.t, receipt.Resolution.Conflict)
	require.Len(s.c.t, receipt.Resolution.Claims, 1)
	require.True(s.c.t, t2ConcurrentReplaceMatches(receipt.Resolution.Claims[0], op))
	disposition := "CREATED"
	if retry {
		disposition = "ALREADY_EXISTS_SAME_PAYLOAD"
		require.Equal(s.c.t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, receipt.Disposition)
		require.Empty(s.c.t, receipt.ChangeId)
	} else {
		require.Equal(s.c.t, pb.RpcPinkhaTorahOperations_CREATED, receipt.Disposition)
		require.NotEmpty(s.c.t, receipt.ChangeId)
	}
	return map[string]any{"operation_id": op.OperationID, "claim_id": id, "disposition": disposition,
		"change_id": receipt.ChangeId, "request_sha256": actualSHA, "request_bytes": actualBytes,
		"returned_claim_sha256": t2ConcurrentReplaceHash(s.c.t, receipt.Resolution.Claims[0])}
}

func (s *t2ConcurrentReplaceSession) retry(claim *pb.RpcPinkhaTorahOperationsClaim,
	read *pb.RpcPinkhaTorahOperationsReadTargetResponse, history t2OfflineHistory) map[string]any {
	op, err := t2ConcurrentReplaceOperation(claim)
	require.NoError(s.c.t, err)
	require.Equal(s.c.t, s.author, op.AuthorID)
	before := t2OfflineRead(s.c, s.state, s.budget(20*time.Second))
	require.True(s.c.t, proto.Equal(read, before))
	require.Equal(s.c.t, history, t2OfflineHistoryRead(s.c.t, s.state, s.budget(20*time.Second)))
	observation := s.append(op, true)
	require.Equal(s.c.t, t2ConcurrentReplaceHash(s.c.t, claim), observation["returned_claim_sha256"])
	after := t2OfflineRead(s.c, s.state, s.budget(20*time.Second))
	require.True(s.c.t, proto.Equal(before, after), "retry cannot change any local response, sequence, head or materialized ordering")
	afterHistory := t2OfflineHistoryRead(s.c.t, s.state, s.budget(20*time.Second))
	require.Equal(s.c.t, history, afterHistory)
	observation["before_response_sha256"], observation["after_response_sha256"] = t2ConcurrentReplaceHash(s.c.t, before), t2ConcurrentReplaceHash(s.c.t, after)
	observation["before_local_sequence"], observation["after_local_sequence"] = before.Snapshot.LocalAppliedSeq, after.Snapshot.LocalAppliedSeq
	observation["history_before"], observation["history_after"] = history, afterHistory
	return observation
}

func t2ConcurrentReplaceBranch(t *testing.T, before, after t2OfflineHistory, change string) {
	t.Helper()
	require.Len(t, before.Changes, 8)
	require.Len(t, before.Parents, 7)
	require.Len(t, before.Heads, 2)
	require.Len(t, after.Changes, 9)
	require.Len(t, after.Parents, 8)
	require.Equal(t, []string{change}, after.Heads)
	require.NotContains(t, before.Changes, change)
	require.Len(t, after.Changes[change], 64)
	require.Equal(t, before.Heads, after.Parents[change])
	for id, digest := range before.Changes {
		require.Equal(t, digest, after.Changes[id])
	}
	for id, parents := range before.Parents {
		require.Equal(t, parents, after.Parents[id])
	}
}

func (s *t2ConcurrentReplaceSession) report(phase string, read *pb.RpcPinkhaTorahOperationsReadTargetResponse,
	history t2OfflineHistory, extra map[string]any) map[string]any {
	namespace, err := os.Readlink("/proc/self/ns/net")
	require.NoError(s.c.t, err)
	live, conflict := []string{}, []string{}
	liveClaims := []map[string]any{}
	successors := map[string]any{}
	for _, claim := range read.Snapshot.Live {
		live = append(live, claim.ClaimId) // Keep the real returned order, never repair it here.
		evidence := t2ConcurrentReplaceClaimEvidence(s.c.t, claim)
		liveClaims = append(liveClaims, evidence) // OperationID is bound to the canonical native claim above.
		for index, role := range []string{"creator", "recovered"} {
			if evidence["operation_id"] == fmt.Sprintf("%032x", index+8) {
				successors[role] = evidence
			}
		}
	}
	for _, claim := range read.Snapshot.Conflicts[0].Claims {
		conflict = append(conflict, claim.ClaimId)
	}
	slices.Sort(conflict)
	report := map[string]any{"protocol": t2ConcurrentReplaceProtocol, "phase": phase, "role": s.c.role, "nonce": s.c.nonce,
		"pid": os.Getpid(), "network_namespace": namespace, "actual_ipv4": t2OfflineIPs(s.c.t),
		"native_network_mode": "NATIVE_LOCAL_ONLY_LAN_ORIGINAL_STORES", "native_network_state": s.networkState, "native_server_port": s.serverPort,
		"peer_id": s.peerID, "account_author_id": s.author, "heart_sha": vcs.GitCommit, "runtime_version": s.version,
		"client_fixture_sha256": t2NativeClientFixtureSHA, "rpc_manifest_sha256": t2RPCAccountSchemaSHA,
		"registration_patch_sha256": t2AccountRegistrationSHA, "state_sha256": s.stateSHA,
		"clean_reopen_receipt_sha256": s.baselineSHA, "original_operation_sha256": s.state.OperationSHA256,
		"original_claim_id": s.state.ClaimID, "history": history, "read_response_sha256": t2ConcurrentReplaceHash(s.c.t, read),
		"snapshot_sha256_without_local_sequence": t2OfflineSnapshotHash(s.c.t, read.Snapshot),
		"local_applied_sequence":                 read.Snapshot.LocalAppliedSeq, "live_claim_ids": live, "live_claims": liveClaims,
		"conflict_operation_id": fmt.Sprintf("%032x", 4), "conflict_claim_ids": conflict,
		"predecessor": t2ConcurrentReplaceClaimEvidence(s.c.t, s.predecessor), "predecessor_observation_sha256": s.predecessorReadSHA,
		"successors": successors, "materialized_order": "BYTEWISE_OPERATION_ID_CLAIM_ID_FALLBACK_BOTH_SUCCESSORS_RETAINED",
		"rfc_causal_operation_id_display_order": "NOT_PROVEN", "app_capability": "OFF",
		"process_crash": "NOT_RUN", "power_loss": "NOT_RUN", "disconnected_reopen_after_tail": "NOT_RUN",
		"two_ios_apps": "NOT_RUN", "full_t2_acceptance": "NOT_RUN", "test_passed": false}
	for key, value := range extra {
		report[key] = value
	}
	encoded, err := json.MarshalIndent(report, "", "  ")
	require.NoError(s.c.t, err)
	t2NativeClientReport(s.c.t, filepath.Join("/private", "replace-"+phase+".json"), encoded)
	return report
}

func t2NativeConcurrentReplaceRun(t *testing.T, role string) {
	s := t2OpenConcurrentReplaceSession(t, role)
	c, baseline := s.c, s.baseline.History
	read := s.read("baseline", baseline, "baseline", baseline)
	s.baselineRead = proto.Clone(read).(*pb.RpcPinkhaTorahOperationsReadTargetResponse)
	s.capturePredecessor(read)
	ready := s.report("ready", read, baseline, nil)
	require.Equal(t, baseline, s.command("partition").History)
	if role == "recovered" {
		t2OfflineNetwork(c, false)
		s.networkState = "NOT_CONNECTED"
	} else {
		require.Len(t, t2OfflineIPs(t), 1)
	}
	read = s.read("baseline", baseline, "baseline", baseline)
	s.capturePredecessor(read) // Observe the predecessor locally again after the real detach.
	partitioned := s.report("partitioned", read, baseline, nil)
	require.Equal(t, baseline, s.command("write").History)
	op := s.replacement(role)
	mutation := s.append(op, false)
	localHistory := t2OfflineHistoryRead(t, s.state, s.budget(20*time.Second))
	t2ConcurrentReplaceBranch(t, baseline, localHistory, mutation["change_id"].(string))
	read = s.read("local", localHistory, "baseline", baseline)
	diverged := s.report("diverged", read, localHistory, map[string]any{"mutation": mutation})
	merged := s.command("reconnect").History
	require.Len(t, merged.Changes, 10)
	require.Len(t, merged.Parents, 9)
	require.Len(t, merged.Heads, 2)
	for id, digest := range localHistory.Changes {
		require.Equal(t, digest, merged.Changes[id])
	}
	for id, parents := range localHistory.Parents {
		require.Equal(t, parents, merged.Parents[id])
	}
	otherChange := ""
	for id := range merged.Changes {
		if _, ok := localHistory.Changes[id]; !ok {
			require.Empty(t, otherChange)
			otherChange = id
			require.Len(t, merged.Changes[id], 64)
			require.Equal(t, baseline.Heads, merged.Parents[id])
		}
	}
	require.NotEmpty(t, otherChange)
	expectedHeads := []string{mutation["change_id"].(string), otherChange}
	slices.Sort(expectedHeads)
	require.Equal(t, expectedHeads, merged.Heads)
	if role == "recovered" {
		t2OfflineNetwork(c, true)
		s.networkState = "WIFI"
	} else {
		require.Len(t, t2OfflineIPs(t), 1)
	}
	read = s.read("merged", merged, "local", localHistory)
	retries := map[string]any{}
	for index, writer := range []string{"creator", "recovered"} {
		var observed *pb.RpcPinkhaTorahOperationsClaim
		for _, claim := range read.Snapshot.Live {
			if claim.Operation.OperationId == fmt.Sprintf("%032x", index+8) {
				observed = proto.Clone(claim).(*pb.RpcPinkhaTorahOperationsClaim)
			}
		}
		require.NotNil(t, observed)
		retries[writer] = s.retry(observed, read, merged)
	}
	retries["predecessor"] = s.retry(s.predecessor, read, merged)
	ownRetry := retries[role].(map[string]any)
	require.Equal(t, mutation["request_sha256"], ownRetry["request_sha256"])
	require.Equal(t, mutation["request_bytes"], ownRetry["request_bytes"])
	mergedReport := s.report("merged", read, merged, map[string]any{"mutation": mutation, "retries": retries})
	require.Equal(t, merged, s.command("stop").History)
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
	require.Equal(t, c.rpc.calls, c.returnedCalls)
	// Hash original receipts, and carry their already-observed metadata after
	// closure. No closed-session read is used to repair acceptance evidence.
	s.report("final", read, merged, map[string]any{"mutation": mutation, "retries": retries,
		"ready_receipt_sha256": t2ObservedReportHash(t, ready), "partitioned_receipt_sha256": t2ObservedReportHash(t, partitioned),
		"diverged_receipt_sha256": t2ObservedReportHash(t, diverged), "merged_receipt_sha256": t2ObservedReportHash(t, mergedReport),
		"rpc_calls": c.rpc.calls, "returned_byte_calls": c.returnedCalls, "closed": true,
		"account_stop_verified": true, "post_stop_rpc": "READ_AND_APPEND_NOT_LOGGED_IN", "test_passed": true})
	t.Log("PASS concurrent native REPLACE retains both successors and predecessor provenance with exact byte retries")
}

func TestT2NativeClientConcurrentReplaceCreatorPhase(t *testing.T) {
	t2NativeConcurrentReplaceRun(t, "creator")
}

func TestT2NativeClientConcurrentReplaceRecoveredPhase(t *testing.T) {
	t2NativeConcurrentReplaceRun(t, "recovered")
}
