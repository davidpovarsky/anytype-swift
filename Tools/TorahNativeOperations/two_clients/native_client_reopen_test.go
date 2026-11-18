package service

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/stretchr/testify/require"
)

// This runs in a new OS process against one client's original data directory,
// with Docker network=none. No peer can repair missing persisted data here.
func TestT2NativeClientOfflineReopenPhase(t *testing.T) {
	role, nonce := os.Getenv("PINKHA_T2_CLIENT_ROLE"), os.Getenv("PINKHA_T2_CLIENT_NONCE")
	require.Contains(t, []string{"creator", "recovered"}, role)
	require.NotEmpty(t, nonce)
	require.Equal(t, t2OfflineProtocol, os.Getenv("PINKHA_T2_CLIENT_SCENARIO"))
	require.Equal(t, "new", t2AccountRuntimeRole)
	require.NotEqual(t, "UNSET", t2NativeClientFixtureSHA)
	require.Equal(t, t2NativeClientFixtureSHA, os.Getenv("PINKHA_T2_CLIENT_FIXTURE_SHA"))
	require.Equal(t, t2HeartPin, vcs.GitCommit)
	require.NotEqual(t, "UNSET", t2RPCAccountSchemaSHA)
	const parent = "/private"
	const root = "/private/account-root"
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
	require.Equal(t, nonce, owner.Nonce)
	require.Equal(t, role, owner.Role)
	require.True(t, owner.SyntheticOnly)
	entries, err := os.ReadDir(root)
	require.NoError(t, err)
	require.NotEmpty(t, entries, "reopen must retain the original native account store")
	require.Empty(t, t2OfflineIPs(t), "both reopen processes must have no peer network")
	stateBytes, err := os.ReadFile(filepath.Join(parent, "state.json"))
	require.NoError(t, err)
	state := &t2AccountState{}
	require.NoError(t, json.Unmarshal(stateBytes, state))
	convergedBytes, err := os.ReadFile(filepath.Join(parent, "converged.json"))
	require.NoError(t, err)
	var expected struct {
		Protocol    string           `json:"protocol"`
		Nonce       string           `json:"nonce"`
		Role        string           `json:"role"`
		Phase       string           `json:"phase"`
		PeerID      string           `json:"peer_id"`
		FixtureSHA  string           `json:"client_fixture_sha256"`
		History     t2OfflineHistory `json:"history"`
		SnapshotSHA string           `json:"snapshot_sha256_without_local_sequence"`
	}
	require.NoError(t, json.Unmarshal(convergedBytes, &expected))
	require.Equal(t, t2OfflineProtocol, expected.Protocol)
	require.Equal(t, nonce, expected.Nonce)
	require.Equal(t, role, expected.Role)
	require.Equal(t, "converged", expected.Phase)
	require.Equal(t, t2NativeClientFixtureSHA, expected.FixtureSHA)
	require.NotEmpty(t, expected.PeerID)
	require.Len(t, expected.SnapshotSHA, 64)
	require.Len(t, expected.History.Changes, 8)
	require.Len(t, expected.History.Parents, 7)
	require.Len(t, expected.History.Heads, 2)
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	c := &t2NativeClientCaller{t: t, rpc: rpc, role: role, nonce: nonce, returnedCalls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	c.invoke("InitialSetParameters", InitialSetParameters, &pb.RpcInitialSetParametersRequest{
		Platform: "ios", Version: "0.51.0", Workdir: root, DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true},
		&pb.RpcInitialSetParametersResponse{}, 30*time.Second)
	version := &pb.RpcAppGetVersionResponse{}
	c.invoke("AppGetVersion", AppGetVersion, &pb.RpcAppGetVersionRequest{}, version, 10*time.Second)
	require.Equal(t, "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-"+t2LegacyPatch+
		"-pinkha-t2-registry-v1-"+t2AccountRegistrationSHA, version.Version)
	closeAccount := func() {
		if c.startRequested && !c.stopAttempted {
			c.stopAttempted = true
			c.invoke("AccountStop", AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{}, 30*time.Second)
			require.Nil(t, mw.GetApp())
			c.invoke("AppShutdown", AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{}, 15*time.Second)
			c.closed = true
		}
	}
	t.Cleanup(closeAccount)
	key, err := os.ReadFile(filepath.Join(parent, "account-key.private"))
	require.NoError(t, err)
	require.NotEmpty(t, key)
	c.invoke("WalletRecover", WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)},
		&pb.RpcWalletRecoverResponse{}, 30*time.Second)
	c.startRequested = true
	selected := &pb.RpcAccountSelectResponse{}
	c.invoke("AccountSelect", AccountSelect, &pb.RpcAccountSelectRequest{Id: state.AccountID, RootPath: root,
		NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false, PreferredSpaceId: state.SpaceID}, selected, 120*time.Second)
	require.NotNil(t, selected.Account)
	require.Equal(t, state.AccountID, selected.Account.Id)
	c.invoke("WorkspaceOpen", WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{}, 30*time.Second)
	t2OfflineNetwork(c, false)
	wallet := app.MustComponent[wallet.Wallet](mw.GetApp())
	peerID := wallet.Account().PeerId
	require.Equal(t, expected.PeerID, peerID, "native reopen must retain its own device key and PeerID")
	require.Equal(t, filepath.Join(root, state.AccountID), wallet.RepoPath())
	read := t2OfflineRead(c, state, 30*time.Second)
	ready, err := t2OfflineSnapshotReady(state, wallet.Account().SignKey.GetPublic().Account(), read, expected.History.Heads)
	require.NoError(t, err)
	require.True(t, ready, "disconnected reopen must read the complete persisted conflict state without peer repair")
	require.Equal(t, expected.SnapshotSHA, t2OfflineSnapshotHash(t, read.Snapshot))
	history := t2OfflineHistoryRead(t, state)
	require.Equal(t, expected.History, history)
	namespace, err := os.Readlink("/proc/self/ns/net")
	require.NoError(t, err)
	localSequence := read.Snapshot.LocalAppliedSeq
	report := map[string]any{"protocol": t2OfflineProtocol, "phase": "reopened", "role": role, "nonce": nonce,
		"pid": os.Getpid(), "network_namespace": namespace, "actual_ipv4": t2OfflineIPs(t),
		"native_network_mode": "DISCONNECTED_REOPEN_NO_PEER_REPAIR", "peer_id": peerID,
		"heart_sha": vcs.GitCommit, "runtime_version": version.Version, "client_fixture_sha256": t2NativeClientFixtureSHA,
		"rpc_manifest_sha256": t2RPCAccountSchemaSHA, "registration_patch_sha256": t2AccountRegistrationSHA,
		"state_sha256": t2Hash(stateBytes), "convergence_receipt_sha256": t2Hash(convergedBytes),
		"history": history, "snapshot_sha256_without_local_sequence": expected.SnapshotSHA,
		"local_applied_sequence": localSequence, "app_capability": "OFF", "crash_after_commit": "NOT_RUN",
		"two_ios_apps": "NOT_RUN", "full_t2_acceptance": "NOT_RUN"}
	readyBytes, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	t2NativeClientReport(t, filepath.Join(parent, "reopen-ready.json"), readyBytes)
	t2OfflineWaitCommand(c, parent, "reopen-stop", 60*time.Second)
	closeAccount()
	require.True(t, c.closed)
	appendRequest, readRequest := t2NativeRPCRequests(state)
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
	report["rpc_calls"], report["returned_byte_calls"] = rpc.calls, c.returnedCalls
	report["account_stop_verified"], report["closed"], report["test_passed"] = true, true, true
	report["post_stop_rpc"] = "READ_AND_APPEND_NOT_LOGGED_IN"
	encoded, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	t2NativeClientReport(t, filepath.Join(parent, "reopened.json"), encoded)
	t.Log("PASS independent native data reopened without a peer network; both conflict variants and original history retained")
}
