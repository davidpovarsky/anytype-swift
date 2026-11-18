package service

import (
	"bytes"
	"encoding/json"
	"fmt"
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

const t2ObservedRemoveProtocol = "pinkha-t2-native-observed-remove-readd-v1"

// Commands contain only a phase and expected signed IDs/hashes. Each request
// is constructed inside its own original native account, from its own read.
type t2ObservedRemoveCommand struct {
	Protocol string           `json:"protocol"`
	Nonce    string           `json:"nonce"`
	Role     string           `json:"role"`
	Phase    string           `json:"phase"`
	History  t2OfflineHistory `json:"expected_history"`
}

type t2ObservedRemoveSession struct {
	c           *t2NativeClientCaller
	state       *t2AccountState
	baseline    t2CrashBaseline
	baselineSHA string
	stateSHA    string
	peerID      string
	author      string
	version     string
	serverPort  int
	deadline    time.Time
}

func (s *t2ObservedRemoveSession) budget(maximum time.Duration) time.Duration {
	left := time.Until(s.deadline)
	require.Greater(s.c.t, left, time.Duration(0), "one fixed observed-remove process deadline")
	return min(left, maximum)
}

func (s *t2ObservedRemoveSession) close() {
	c := s.c
	if c.startRequested && !c.stopAttempted {
		c.stopAttempted = true
		c.invoke("AccountStop", AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{}, 30*time.Second)
		require.Nil(c.t, mw.GetApp())
		c.invoke("AppShutdown", AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{}, 15*time.Second)
		c.closed = true
	}
}

func t2OpenObservedRemoveSession(t *testing.T, role string) *t2ObservedRemoveSession {
	t.Helper()
	require.Contains(t, []string{"creator", "recovered"}, role)
	require.Equal(t, role, os.Getenv("PINKHA_T2_CLIENT_ROLE"))
	require.Equal(t, t2ObservedRemoveProtocol, os.Getenv("PINKHA_T2_OBSERVED_REMOVE_PHASE"))
	require.Empty(t, os.Getenv("PINKHA_T2_CRASH_PHASE"))
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
	s := &t2ObservedRemoveSession{state: &t2AccountState{}, stateSHA: t2Hash(stateBytes), deadline: time.Now().Add(600 * time.Second)}
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
	original := s.operation(1, "")
	originalID, originalSHA, err := t2OfflineClaim(original)
	require.NoError(t, err)
	require.Equal(t, s.state.OperationID, original.OperationID)
	require.Equal(t, s.state.ClaimID, originalID)
	require.Equal(t, s.state.OperationSHA256, originalSHA)
	return s
}

func (s *t2ObservedRemoveSession) operation(number int, observed string) torahops.Operation {
	op := torahops.Operation{Version: 1, SpaceID: s.state.SpaceID, OperationID: fmt.Sprintf("%032x", number),
		AuthorID: s.author, Kind: torahops.Add, Target: torahops.Target{ObjectID: s.state.DocumentID, BlockID: s.state.BlockID},
		Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:t2-account:1"}, Payload: []byte(t2PrivatePayload)}
	if number == 9 {
		op.Kind, op.Source, op.Payload, op.Observed = torahops.Remove, torahops.Source{}, nil, []string{observed}
	}
	return op
}

func t2ObservedHistoryChild(before, after t2OfflineHistory) (string, error) {
	if len(before.Changes) < 8 || len(before.Changes) > 10 || len(before.Parents) != len(before.Changes)-1 ||
		len(after.Changes) != len(before.Changes)+1 || len(after.Parents) != len(before.Parents)+1 || len(after.Heads) != 1 {
		return "", fmt.Errorf("observed-remove requires exactly one new signed child")
	}
	for id, hash := range before.Changes {
		if after.Changes[id] != hash {
			return "", fmt.Errorf("original signed bytes changed")
		}
	}
	for id, parents := range before.Parents {
		if !slices.Equal(after.Parents[id], parents) {
			return "", fmt.Errorf("original signed parents changed")
		}
	}
	id := after.Heads[0]
	if _, exists := before.Changes[id]; exists || id == "" || len(after.Changes[id]) != 64 ||
		!slices.Equal(after.Parents[id], before.Heads) {
		return "", fmt.Errorf("new signed change must extend all previously observed heads")
	}
	return id, nil
}

// A validation copy removes only the one fully verified new ADD, leaving all
// original claims/conflicts to the existing strict offline snapshot validator.
// No returned snapshot or native state is changed.
func (s *t2ObservedRemoveSession) verifySnapshot(response *pb.RpcPinkhaTorahOperationsReadTargetResponse,
	step int, history t2OfflineHistory) (*pb.RpcPinkhaTorahOperationsClaim, error) {
	if response == nil || response.Error == nil || response.ProtocolVersion != 1 || response.Snapshot == nil ||
		response.Error.Code != pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL || len(response.Error.Issues) != 0 {
		return nil, fmt.Errorf("invalid causal snapshot envelope")
	}
	copy := proto.Clone(response).(*pb.RpcPinkhaTorahOperationsReadTargetResponse)
	var found *pb.RpcPinkhaTorahOperationsClaim
	if step == 1 || step == 3 {
		number := 8
		if step == 3 {
			number = 10
		}
		op := s.operation(number, "")
		id, _, err := t2OfflineClaim(op)
		if err != nil {
			return nil, err
		}
		copy.Snapshot.Live = nil
		for _, claim := range response.Snapshot.Live {
			if claim != nil && claim.ClaimId == id {
				if found != nil || !t2OfflineClaimMatches(claim, op) {
					return nil, fmt.Errorf("new association is duplicated or rewritten")
				}
				found = claim
			} else {
				copy.Snapshot.Live = append(copy.Snapshot.Live, claim)
			}
		}
		if found == nil {
			return nil, fmt.Errorf("same-association fresh claim is absent")
		}
	} else if step != 0 && step != 2 {
		return nil, fmt.Errorf("unknown causal snapshot step")
	}
	ready, err := t2OfflineSnapshotReady(s.state, s.author, copy, history.Heads)
	if err != nil {
		return nil, err
	}
	if !ready {
		return nil, fmt.Errorf("original independent claims or conflict variants changed")
	}
	return found, nil
}

func (s *t2ObservedRemoveSession) waitSnapshot(beforeStep int, before t2OfflineHistory, step int, history t2OfflineHistory) *pb.RpcPinkhaTorahOperationsReadTargetResponse {
	var result *pb.RpcPinkhaTorahOperationsReadTargetResponse
	t2NativeClientWait(s.c.t, "causal native transport observation", s.budget(90*time.Second), func(remaining time.Duration) bool {
		result = t2OfflineRead(s.c, s.state, min(remaining, s.budget(20*time.Second)))
		if result.Error != nil && result.Error.Code != pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL {
			// Reuse the established strict catch-up policy. Every other error,
			// failed snapshot or joined denial fails; no account/root repair.
			_, err := t2OfflineSnapshotReady(s.state, s.author, result, history.Heads)
			require.NoError(s.c.t, err)
			return false
		}
		require.NotNil(s.c.t, result.Snapshot)
		heads := slices.Clone(result.Snapshot.VerifiedLocalHeads)
		slices.Sort(heads)
		if slices.Equal(heads, history.Heads) {
			_, err := s.verifySnapshot(result, step, history)
			require.NoError(s.c.t, err)
			require.Equal(s.c.t, history, t2OfflineHistoryRead(s.c.t, s.state, min(remaining, s.budget(20*time.Second))))
			return true
		}
		// Only the immediately preceding fully verified state can wait while
		// this one native change travels over the LAN. No arbitrary prefix.
		require.Equal(s.c.t, before.Heads, heads)
		_, err := s.verifySnapshot(result, beforeStep, before)
		require.NoError(s.c.t, err)
		return false
	})
	return result
}

func (s *t2ObservedRemoveSession) command(phase string) t2ObservedRemoveCommand {
	var command t2ObservedRemoveCommand
	t2NativeClientWait(s.c.t, "fixed observed-remove phase", s.budget(240*time.Second), func(time.Duration) bool {
		path := filepath.Join("/private", "observed-"+phase+".command.json")
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
		require.Equal(s.c.t, t2ObservedRemoveProtocol, command.Protocol)
		require.Equal(s.c.t, s.c.nonce, command.Nonce)
		require.Equal(s.c.t, s.c.role, command.Role)
		require.Equal(s.c.t, phase, command.Phase)
		return true
	})
	return command
}

func t2ObservedRemoveClaimMatches(claim *pb.RpcPinkhaTorahOperationsClaim, expected torahops.Operation) bool {
	if claim == nil || claim.Operation == nil || claim.Operation.Target == nil || claim.Operation.Source == nil {
		return false
	}
	op := claim.Operation
	if op.Kind != pb.RpcPinkhaTorahOperations_REMOVE {
		return false
	}
	actual := torahops.Operation{Version: op.Version, SpaceID: op.SpaceId, OperationID: op.OperationId,
		AuthorID: op.AuthorId, Kind: torahops.Remove, Target: torahops.Target{ObjectID: op.Target.ObjectId, BlockID: op.Target.BlockId},
		Source:  torahops.Source{ProviderID: op.Source.ProviderId, CanonicalRef: op.Source.CanonicalRef},
		Payload: op.Payload, Observed: op.ObservedClaimIds}
	id, hash, err := t2OfflineClaim(expected)
	if err != nil || claim.ClaimId != id || claim.Digest != hash {
		return false
	}
	canonical, err := actual.CanonicalBytes()
	return err == nil && t2Hash(canonical) == hash
}

// The observation is captured immediately before the genuine generated byte
// entry, after protobuf encoding. The worker never asserts or publishes data.
func (s *t2ObservedRemoveSession) append(op torahops.Operation, retry bool) (*pb.RpcPinkhaTorahOperationsAppendResponse, map[string]any) {
	request := t2OfflineRequest(op)
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
	if op.Kind == torahops.Remove {
		require.True(s.c.t, t2ObservedRemoveClaimMatches(receipt.Resolution.Claims[0], op))
	} else {
		require.True(s.c.t, t2OfflineClaimMatches(receipt.Resolution.Claims[0], op))
	}
	disposition := "CREATED"
	if retry {
		disposition = "ALREADY_EXISTS_SAME_PAYLOAD"
		require.Equal(s.c.t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, receipt.Disposition)
		require.Empty(s.c.t, receipt.ChangeId)
	} else {
		require.Equal(s.c.t, pb.RpcPinkhaTorahOperations_CREATED, receipt.Disposition)
		require.NotEmpty(s.c.t, receipt.ChangeId)
	}
	return response, map[string]any{"operation_id": op.OperationID, "claim_id": id, "disposition": disposition,
		"change_id": receipt.ChangeId, "request_sha256": actualSHA, "request_bytes": actualBytes}
}

func (s *t2ObservedRemoveSession) create(op torahops.Operation, before t2OfflineHistory) (t2OfflineHistory, map[string]any) {
	response, observation := s.append(op, false)
	history := t2OfflineHistoryRead(s.c.t, s.state, s.budget(20*time.Second))
	id, err := t2ObservedHistoryChild(before, history)
	require.NoError(s.c.t, err)
	require.Equal(s.c.t, response.Receipt.ChangeId, id)
	return history, observation
}

func (s *t2ObservedRemoveSession) retry(op torahops.Operation, read *pb.RpcPinkhaTorahOperationsReadTargetResponse,
	history t2OfflineHistory) map[string]any {
	before := t2OfflineRead(s.c, s.state, s.budget(20*time.Second))
	require.True(s.c.t, proto.Equal(read, before))
	require.Equal(s.c.t, history, t2OfflineHistoryRead(s.c.t, s.state, s.budget(20*time.Second)))
	_, observation := s.append(op, true)
	after := t2OfflineRead(s.c, s.state, s.budget(20*time.Second))
	require.True(s.c.t, proto.Equal(before, after), "REMOVE retry must preserve all local response fields and sequence")
	afterHistory := t2OfflineHistoryRead(s.c.t, s.state, s.budget(20*time.Second))
	require.Equal(s.c.t, history, afterHistory)
	beforeBytes, err := proto.Marshal(before)
	require.NoError(s.c.t, err)
	afterBytes, err := proto.Marshal(after)
	require.NoError(s.c.t, err)
	observation["before_response_sha256"], observation["after_response_sha256"] = t2Hash(beforeBytes), t2Hash(afterBytes)
	observation["before_local_sequence"], observation["after_local_sequence"] = before.Snapshot.LocalAppliedSeq, after.Snapshot.LocalAppliedSeq
	observation["history_before"], observation["history_after"] = history, afterHistory
	return observation
}

func (s *t2ObservedRemoveSession) report(phase string, read *pb.RpcPinkhaTorahOperationsReadTargetResponse,
	history t2OfflineHistory, extra map[string]any) map[string]any {
	namespace, err := os.Readlink("/proc/self/ns/net")
	require.NoError(s.c.t, err)
	encodedRead, err := proto.Marshal(read)
	require.NoError(s.c.t, err)
	live, conflict := []string{}, []string{}
	for _, claim := range read.Snapshot.Live {
		live = append(live, claim.ClaimId)
	}
	for _, claim := range read.Snapshot.Conflicts[0].Claims {
		conflict = append(conflict, claim.ClaimId)
	}
	slices.Sort(live)
	slices.Sort(conflict)
	report := map[string]any{"protocol": t2ObservedRemoveProtocol, "phase": phase, "role": s.c.role, "nonce": s.c.nonce,
		"pid": os.Getpid(), "network_namespace": namespace, "actual_ipv4": t2OfflineIPs(s.c.t),
		"native_network_mode": "NATIVE_LOCAL_ONLY_LAN_ORIGINAL_STORES", "native_server_port": s.serverPort,
		"peer_id": s.peerID, "account_author_id": s.author, "heart_sha": vcs.GitCommit, "runtime_version": s.version,
		"client_fixture_sha256": t2NativeClientFixtureSHA, "rpc_manifest_sha256": t2RPCAccountSchemaSHA,
		"registration_patch_sha256": t2AccountRegistrationSHA, "state_sha256": s.stateSHA,
		"clean_reopen_receipt_sha256": s.baselineSHA, "original_operation_sha256": s.state.OperationSHA256,
		"original_claim_id": s.state.ClaimID, "history": history, "read_response_sha256": t2Hash(encodedRead),
		"snapshot_sha256_without_local_sequence": t2OfflineSnapshotHash(s.c.t, read.Snapshot),
		"local_applied_sequence":                 read.Snapshot.LocalAppliedSeq, "live_claim_ids": live,
		"conflict_operation_id": fmt.Sprintf("%032x", 4), "conflict_claim_ids": conflict,
		"app_capability": "OFF", "power_loss": "NOT_RUN", "disconnected_reopen_after_tail": "NOT_RUN",
		"two_ios_apps": "NOT_RUN", "full_t2_acceptance": "NOT_RUN", "test_passed": false}
	for key, value := range extra {
		report[key] = value
	}
	encoded, err := json.MarshalIndent(report, "", "  ")
	require.NoError(s.c.t, err)
	t2NativeClientReport(s.c.t, filepath.Join("/private", "observed-"+phase+".json"), encoded)
	return report
}

func t2NativeObservedRemoveRun(t *testing.T, role string) {
	s := t2OpenObservedRemoveSession(t, role)
	c := s.c
	baseline := s.baseline.History
	read := s.waitSnapshot(0, baseline, 0, baseline)
	require.Equal(t, s.baseline.SnapshotSHA, t2OfflineSnapshotHash(t, read.Snapshot))
	s.report("ready", read, baseline, nil)
	var added, removed, readded t2OfflineHistory
	var mutation, retry map[string]any
	if role == "creator" {
		command := s.command("start-add")
		require.Equal(t, baseline, command.History)
		added, mutation = s.create(s.operation(8, ""), baseline)
	} else {
		added = s.command("read-add").History
		_, err := t2ObservedHistoryChild(baseline, added)
		require.NoError(t, err)
	}
	read = s.waitSnapshot(0, baseline, 1, added)
	observed, err := s.verifySnapshot(read, 1, added)
	require.NoError(t, err)
	require.NotNil(t, observed)
	// Each side captures its own actual Native read, not a claim from a command.
	observed = proto.Clone(observed).(*pb.RpcPinkhaTorahOperationsClaim)
	addedReadBytes, err := proto.Marshal(read)
	require.NoError(t, err)
	addedReport := s.report("added", read, added, map[string]any{"mutation": mutation, "observed_add_claim_id": observed.ClaimId})
	remove := s.operation(9, observed.ClaimId)
	if role == "recovered" {
		command := s.command("start-remove")
		require.Equal(t, added, command.History)
		removed, mutation = s.create(remove, added)
	} else {
		removed = s.command("read-remove").History
		_, err := t2ObservedHistoryChild(added, removed)
		require.NoError(t, err)
		mutation = nil
	}
	read = s.waitSnapshot(1, added, 2, removed)
	retry = s.retry(remove, read, removed)
	if mutation != nil {
		require.Equal(t, mutation["request_sha256"], retry["request_sha256"])
		require.Equal(t, mutation["request_bytes"], retry["request_bytes"])
	}
	removedReport := s.report("removed", read, removed, map[string]any{"mutation": mutation, "remove_retry": retry,
		"observed_add_claim_id": observed.ClaimId, "observation_before_remove_sha256": t2Hash(addedReadBytes)})
	if role == "creator" {
		command := s.command("start-readd")
		require.Equal(t, removed, command.History)
		readded, mutation = s.create(s.operation(10, ""), removed)
	} else {
		readded = s.command("read-readd").History
		_, err := t2ObservedHistoryChild(removed, readded)
		require.NoError(t, err)
		mutation = nil
	}
	read = s.waitSnapshot(2, removed, 3, readded)
	newClaim, err := s.verifySnapshot(read, 3, readded)
	require.NoError(t, err)
	require.NotNil(t, newClaim)
	require.NotEqual(t, observed.ClaimId, newClaim.ClaimId)
	require.Len(t, readded.Changes, 11)
	require.Len(t, readded.Parents, 10)
	require.Len(t, readded.Heads, 1)
	s.report("readded", read, readded, map[string]any{"mutation": mutation, "fresh_claim_id": newClaim.ClaimId,
		"removed_claim_ids_verified": []string{s.state.ClaimID, observed.ClaimId}})
	command := s.command("stop")
	require.Equal(t, readded, command.History)
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
	// Preserve metadata from the completed native observations after closure;
	// no closed-account read is used to repair or synthesize the final state.
	s.report("final", read, readded, map[string]any{"fresh_claim_id": newClaim.ClaimId,
		"removed_claim_ids_verified": []string{s.state.ClaimID, observed.ClaimId},
		"added_receipt_sha256":       t2ObservedReportHash(t, addedReport),
		"removed_receipt_sha256":     t2ObservedReportHash(t, removedReport),
		"rpc_calls":                  c.rpc.calls, "returned_byte_calls": c.returnedCalls,
		"closed": true, "account_stop_verified": true, "post_stop_rpc": "READ_AND_APPEND_NOT_LOGGED_IN", "test_passed": true})
	t.Log("PASS original-store causal same-association add/remove/re-add and exact REMOVE retry through native bytes and transport")
}

func t2ObservedReportHash(t *testing.T, report map[string]any) string {
	t.Helper()
	encoded, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	return t2Hash(encoded)
}

func TestT2NativeClientObservedRemoveCreatorPhase(t *testing.T) {
	t2NativeObservedRemoveRun(t, "creator")
}
func TestT2NativeClientObservedRemoveRecoveredPhase(t *testing.T) {
	t2NativeObservedRemoveRun(t, "recovered")
}
