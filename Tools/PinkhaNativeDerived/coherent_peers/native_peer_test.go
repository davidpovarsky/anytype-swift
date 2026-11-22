package service

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/spacecore/clientserver"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

// This separate test binary retains the original account/peer helpers but never
// selects their old tests. Its first private read on B is the new authorized
// byte entry. No ReadTarget, append retry or database copy may prime that read.
var coherentPeerFixtureSHA = "UNSET"
var coherentPeerSourceSHA = "UNSET"

const coherentPeerProtocol = "pinkha-coherent-authorized-read-peers-v1"

func coherentPeerWrite(t *testing.T, parent, name string, value any) {
	t.Helper()
	raw, err := json.MarshalIndent(value, "", "  ")
	require.NoError(t, err)
	t2NativeClientReport(t, filepath.Join(parent, name), raw)
}

func coherentPeerCommand(t *testing.T, parent, name, nonce string, limit time.Duration) {
	t.Helper()
	t2NativeClientWait(t, "owned "+name+" command", limit, func(time.Duration) bool {
		raw, err := os.ReadFile(filepath.Join(parent, name+".command.json"))
		if os.IsNotExist(err) {
			return false
		}
		require.NoError(t, err)
		var command map[string]string
		require.NoError(t, json.Unmarshal(raw, &command))
		require.Equal(t, map[string]string{"protocol": coherentPeerProtocol, "nonce": nonce, "phase": name}, command)
		return true
	})
}

func coherentPeerRead(c *t2NativeClientCaller, state *t2AccountState, limit time.Duration) (*pb.PinkhaTorahAuthorizedOperationReadResponse, []byte) {
	c.t.Helper()
	request := &pb.PinkhaTorahAuthorizedOperationReadRequest{ProtocolVersion: 1, SpaceId: state.SpaceID, OperationId: state.OperationID}
	input, err := proto.Marshal(request)
	require.NoError(c.t, err)
	c.rpc.calls["PinkhaTorahAuthorizedOperationRead"]++
	raw := c.callBytes("PinkhaTorahAuthorizedOperationRead", PinkhaTorahAuthorizedOperationRead, input, limit)
	require.LessOrEqual(c.t, len(raw), torahops.MaxAuthorizedOperationReadBytes)
	response := &pb.PinkhaTorahAuthorizedOperationReadResponse{}
	require.NoError(c.t, proto.Unmarshal(raw, response))
	require.Equal(c.t, uint32(1), response.ProtocolVersion)
	require.NotNil(c.t, response.Error)
	return response, raw
}

func coherentPeerPositive(t *testing.T, state *t2AccountState, reply *pb.PinkhaTorahAuthorizedOperationReadResponse) string {
	t.Helper()
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NULL, reply.Error.Code)
	require.Empty(t, reply.Error.Description)
	require.NotNil(t, reply.Snapshot)
	snapshot := reply.Snapshot
	require.Equal(t, torahops.AuthorizedOperationReadContract, snapshot.Contract)
	require.Equal(t, state.AccountID, snapshot.AccountId)
	require.Equal(t, state.SpaceID, snapshot.SpaceId)
	require.Equal(t, state.OperationID, snapshot.OperationId)
	require.True(t, snapshot.Complete)
	require.Len(t, snapshot.NativeSnapshotToken, 64)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_FOUND, snapshot.Outcome)
	require.Len(t, snapshot.Variants, 1)
	variant := snapshot.Variants[0]
	require.Equal(t, state.ClaimID, variant.ClaimId)
	require.Equal(t, state.OperationID, variant.OperationId)
	require.Equal(t, state.SpaceID, variant.SpaceId)
	require.Equal(t, state.AccountID, variant.AuthorId)
	require.NotNil(t, variant.Target)
	require.Equal(t, state.DocumentID, variant.Target.ObjectId)
	require.Equal(t, state.BlockID, variant.Target.BlockId)
	require.Equal(t, state.OperationSHA256, t2Hash(variant.CanonicalBytes))
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_LIVE_BLOCK, variant.Reachability)
	require.Len(t, variant.Provenance, 1)
	require.Equal(t, state.AccountID, variant.Provenance[0].Creator)
	require.Equal(t, state.ChangeID, variant.Provenance[0].NativeChangeId)
	require.NotEmpty(t, variant.Provenance[0].NativeAclHeadId)
	raw, err := proto.Marshal(variant)
	require.NoError(t, err)
	return t2Hash(raw)
}

func TestCoherentAuthorizedReadNativePeer(t *testing.T) {
	const parent, root = "/private", "/private/account-root"
	role, nonce, phase := os.Getenv("PINKHA_T2_CLIENT_ROLE"), os.Getenv("PINKHA_T2_CLIENT_NONCE"), os.Getenv("PINKHA_COHERENT_PEER_PHASE")
	require.Contains(t, []string{"creator", "recovered"}, role)
	require.Contains(t, []string{"online", "reopen"}, phase)
	require.False(t, phase == "reopen" && role != "recovered")
	require.Len(t, nonce, 32)
	require.NotEqual(t, "UNSET", coherentPeerFixtureSHA)
	require.Equal(t, coherentPeerFixtureSHA, os.Getenv("PINKHA_T2_CLIENT_FIXTURE_SHA"))
	require.Len(t, coherentPeerSourceSHA, 40)
	require.Equal(t, t2HeartPin, vcs.GitCommit)
	owned, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	require.NoError(t, err)
	var ownership map[string]any
	require.NoError(t, json.Unmarshal(owned, &ownership))
	require.Equal(t, map[string]any{"protocol": coherentPeerProtocol, "nonce": nonce, "role": role, "synthetic_only": true}, ownership)
	entries, err := os.ReadDir(root)
	require.NoError(t, err)
	if phase == "reopen" {
		require.NotEmpty(t, entries)
		require.Empty(t, t2OfflineIPs(t))
	} else {
		require.Empty(t, entries, "both first processes start with independent empty native stores")
		require.Len(t, t2OfflineIPs(t), 1)
	}
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	c := &t2NativeClientCaller{t: t, rpc: rpc, role: role, nonce: nonce, returnedCalls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	c.invoke("InitialSetParameters", InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{}, 30*time.Second)
	version := &pb.RpcAppGetVersionResponse{}
	c.invoke("AppGetVersion", AppGetVersion, &pb.RpcAppGetVersionRequest{}, version, 10*time.Second)
	require.Equal(t, os.Getenv("PINKHA_COHERENT_RUNTIME_VERSION"), version.Version)
	require.Equal(t, vcs.GitSummary, version.Version)
	shutdown := func() {
		if c.startRequested && !c.stopAttempted {
			c.stopAttempted = true
			c.invoke("AccountStop", AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{}, 30*time.Second)
			require.Nil(t, mw.GetApp())
			c.invoke("AppShutdown", AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{}, 15*time.Second)
			c.closed = true
		}
	}
	t.Cleanup(shutdown)
	state := &t2AccountState{}
	if role == "creator" {
		createdWallet := &pb.RpcWalletCreateResponse{}
		c.invoke("WalletCreate", WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, createdWallet, 30*time.Second)
		require.NotEmpty(t, createdWallet.AccountKey)
		require.NotEmpty(t, createdWallet.Mnemonic)
		t2WriteFresh(t, filepath.Join(parent, "account-key.private"), []byte(createdWallet.AccountKey))
		needles, err := json.Marshal([]string{createdWallet.AccountKey, createdWallet.Mnemonic})
		require.NoError(t, err)
		t2WriteFresh(t, filepath.Join(parent, "sensitive-needles.private"), needles)
		created := &pb.RpcAccountCreateResponse{}
		c.startRequested = true
		c.invoke("AccountCreate", AccountCreate, &pb.RpcAccountCreateRequest{Name: "Coherent authorized-read disposable peers",
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false}, created, 60*time.Second)
		require.NotNil(t, created.Account)
		state.AccountID = created.Account.Id
		t2NativeClientCreateTarget(c, state)
		t2NativeClientCreateOperation(c, state)
		state.RawChanges, state.Heads = t2RawHistory(t, state)
		raw, err := json.Marshal(state)
		require.NoError(t, err)
		t2WriteFresh(t, filepath.Join(parent, "state.json"), raw)
	} else {
		raw, err := os.ReadFile(filepath.Join(parent, "state.json"))
		require.NoError(t, err)
		require.NoError(t, json.Unmarshal(raw, state))
		key, err := os.ReadFile(filepath.Join(parent, "account-key.private"))
		require.NoError(t, err)
		require.NotEmpty(t, key)
		c.invoke("WalletRecover", WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)}, &pb.RpcWalletRecoverResponse{}, 30*time.Second)
		c.startRequested = true
		selected := &pb.RpcAccountSelectResponse{}
		c.invoke("AccountSelect", AccountSelect, &pb.RpcAccountSelectRequest{Id: state.AccountID, RootPath: root,
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false, PreferredSpaceId: state.SpaceID}, selected, 180*time.Second)
		require.NotNil(t, selected.Account)
		require.Equal(t, state.AccountID, selected.Account.Id)
		c.invoke("WorkspaceOpen", WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{}, 30*time.Second)
	}
	if phase == "reopen" {
		t2OfflineNetwork(c, false)
	} else {
		c.invoke("DeviceNetworkStateSet", DeviceNetworkStateSet, &pb.RpcDeviceNetworkStateSetRequest{
			DeviceNetworkType: model.DeviceNetworkType_WIFI, NetworkId: "pinkha-coherent-owned-internal-bridge"}, &pb.RpcDeviceNetworkStateSetResponse{}, 30*time.Second)
		server := app.MustComponent[clientserver.ClientServer](mw.GetApp())
		t2NativeClientWait(t, "native LAN server", 30*time.Second, func(time.Duration) bool { return server.ServerStarted() })
	}
	identity := app.MustComponent[wallet.Wallet](mw.GetApp())
	peerID := identity.Account().PeerId
	require.NotEmpty(t, peerID)
	require.Equal(t, filepath.Join(root, state.AccountID), identity.RepoPath())
	namespace, err := os.Readlink("/proc/self/ns/net")
	require.NoError(t, err)
	stateBytes, err := os.ReadFile(filepath.Join(parent, "state.json"))
	require.NoError(t, err)
	var reply *pb.PinkhaTorahAuthorizedOperationReadResponse
	var wire []byte
	readOnce := func(remaining time.Duration) bool {
		reply, wire = coherentPeerRead(c, state, min(20*time.Second, remaining))
		if reply.Error.Code == pb.PinkhaTorahAuthorizedOperationReadResponseError_NULL {
			require.NotNil(t, reply.Snapshot)
			if reply.Snapshot.Outcome == pb.PinkhaTorahAuthorizedOperationRead_ABSENT_IN_VERIFIED_LOCAL_SNAPSHOT {
				require.True(t, reply.Snapshot.Complete)
				require.Empty(t, reply.Snapshot.Variants)
				return false // A complete local prefix is not peer convergence.
			}
			return true
		}
		require.Nil(t, reply.Snapshot)
		require.Contains(t, []pb.PinkhaTorahAuthorizedOperationReadResponseErrorCode{
			pb.PinkhaTorahAuthorizedOperationReadResponseError_HISTORY_UNAVAILABLE,
			pb.PinkhaTorahAuthorizedOperationReadResponseError_TARGET_STATE_UNAVAILABLE,
			pb.PinkhaTorahAuthorizedOperationReadResponseError_PROJECTION_BEHIND}, reply.Error.Code)
		return false
	}
	if phase == "reopen" {
		require.True(t, readOnce(20*time.Second), "cold offline read must succeed without a retry or peer repair")
	} else {
		t2NativeClientWait(t, "authorized first private read over native transport", 150*time.Second, readOnce)
	}
	variantSHA := coherentPeerPositive(t, state, reply)
	report := func(stage string, raw []byte) map[string]any {
		history, heads := t2RawHistory(t, state)
		require.Equal(t, state.RawChanges, history)
		require.Equal(t, state.Heads, heads)
		require.Zero(t, rpc.calls["PinkhaTorahOperationsReadTarget"])
		appendCount := 0
		if role == "creator" {
			appendCount = 1
		}
		require.Equal(t, appendCount, rpc.calls["PinkhaTorahOperationsAppend"])
		return map[string]any{"protocol": coherentPeerProtocol, "phase": stage, "role": role, "nonce": nonce, "pid": os.Getpid(),
			"source_sha": coherentPeerSourceSHA, "heart_sha": vcs.GitCommit, "runtime_version": version.Version, "fixture_sha256": coherentPeerFixtureSHA,
			"peer_id": peerID, "network_namespace": namespace, "actual_ipv4": t2OfflineIPs(t), "state_sha256": t2Hash(stateBytes),
			"account_id": state.AccountID, "space_id": state.SpaceID, "object_id": state.DocumentID, "block_id": state.BlockID,
			"operation_id": state.OperationID, "claim_id": state.ClaimID, "change_id": state.ChangeID,
			"canonical_sha256": state.OperationSHA256, "variant_sha256": variantSHA, "wire_sha256": t2Hash(raw),
			"raw_changes_sha256": history, "heads": heads, "first_private_read": "PinkhaTorahAuthorizedOperationRead",
			"active_append_count": appendCount, "read_target_count": 0, "rpc_calls": rpc.calls,
			"network_acl_transport": "NOT_RUN", "mixed_versions": "NOT_RUN", "offline_unknown_revocation": "NOT_PROVEN",
			"full_t2_acceptance": "NOT_RUN", "ios_acceptance": "NOT_RUN", "app_capability": "OFF"}
	}
	initial := "ready"
	if phase == "reopen" {
		initial = "reopen"
		originalBytes, err := os.ReadFile(filepath.Join(parent, "ready.json"))
		require.NoError(t, err)
		var original map[string]any
		require.NoError(t, json.Unmarshal(originalBytes, &original))
		require.Equal(t, peerID, original["peer_id"])
		require.Equal(t, variantSHA, original["variant_sha256"])
	}
	t2WriteFresh(t, filepath.Join(parent, initial+".pb"), wire)
	coherentPeerWrite(t, parent, initial+".json", report(initial, wire))
	if role == "recovered" && phase == "online" {
		coherentPeerCommand(t, parent, "offline", nonce, 120*time.Second)
		require.Empty(t, t2OfflineIPs(t), "the real network must be detached before the cached read")
		t2OfflineNetwork(c, false)
		reply, wire = coherentPeerRead(c, state, 20*time.Second)
		require.Equal(t, variantSHA, coherentPeerPositive(t, state, reply))
		t2WriteFresh(t, filepath.Join(parent, "offline.pb"), wire)
		coherentPeerWrite(t, parent, "offline.json", report("offline", wire))
	}
	stop := "stop"
	if phase == "reopen" {
		stop = "reopen-stop"
	}
	coherentPeerCommand(t, parent, stop, nonce, 600*time.Second)
	final := report("final", wire)
	shutdown()
	require.True(t, c.closed)
	denied, deniedWire := coherentPeerRead(c, state, 10*time.Second)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NOT_LOGGED_IN, denied.Error.Code)
	require.Nil(t, denied.Snapshot)
	final["account_stop_verified"], final["test_passed"], final["stopped_error_code"], final["stopped_payload"] = true, true, int32(denied.Error.Code), false
	final["rpc_calls"] = rpc.calls
	final["returned_byte_calls"] = c.returnedCalls
	final["stopped_wire_sha256"] = t2Hash(deniedWire)
	prefix := ""
	if phase == "reopen" {
		prefix = "reopen-"
		final["phase"] = "reopen-final"
	}
	t2WriteFresh(t, filepath.Join(parent, prefix+"stopped.pb"), deniedWire)
	coherentPeerWrite(t, parent, prefix+"final.json", final)
}
