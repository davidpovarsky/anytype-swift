package service

import (
	"context"
	"encoding/json"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/syncacl"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/net/peerservice"
	"github.com/anyproto/any-sync/net/pool"
	"github.com/anyproto/any-sync/util/cidutil"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/spacecore/clientserver"
	"github.com/anyproto/anytype-heart/space/spacecore/peerstore"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

const memberACLProtocol = "pinkha-independent-member-acl-transport-v1"

type memberACLIdentity struct {
	AccountID string `json:"account_id"`
	PeerID    string `json:"peer_id"`
	IP        string `json:"ip"`
	Port      int    `json:"port"`
	Namespace string `json:"network_namespace"`
}

type memberACLCommand struct {
	Protocol string             `json:"protocol"`
	Nonce    string             `json:"nonce"`
	Phase    string             `json:"phase"`
	Peer     *memberACLIdentity `json:"peer,omitempty"`
	State    *t2AccountState    `json:"state,omitempty"`
	Head     string             `json:"head,omitempty"`
}

func memberACLCommandRead(t *testing.T, phase, nonce string, limit time.Duration) memberACLCommand {
	t.Helper()
	var command memberACLCommand
	t2NativeClientWait(t, "owned member ACL "+phase, limit, func(time.Duration) bool {
		raw, err := os.ReadFile(filepath.Join("/private", phase+".command.json"))
		if os.IsNotExist(err) {
			return false
		}
		require.NoError(t, err)
		require.LessOrEqual(t, len(raw), 64*1024)
		require.NoError(t, json.Unmarshal(raw, &command))
		require.Equal(t, memberACLProtocol, command.Protocol)
		require.Equal(t, nonce, command.Nonce)
		require.Equal(t, phase, command.Phase)
		return true
	})
	return command
}

func memberACLRoute(t *testing.T, remote memberACLIdentity, spaceID string) {
	t.Helper()
	require.NotEmpty(t, remote.PeerID)
	require.NotNil(t, net.ParseIP(remote.IP))
	require.Greater(t, remote.Port, 0)
	require.LessOrEqual(t, remote.Port, 65535)
	// Explicit owned fixture routing, not a claim about invite or mDNS UX.
	// Native peer handshake, SpacePull and ACL signature validation remain live.
	app.MustComponent[peerservice.PeerService](mw.GetApp()).SetPeerAddrs(
		remote.PeerID, []string{"yamux://" + net.JoinHostPort(remote.IP, strconv.Itoa(remote.Port))})
	app.MustComponent[peerstore.PeerStore](mw.GetApp()).UpdateLocalPeer(remote.PeerID, []string{spaceID})
}

func memberACLApply(t *testing.T, acl syncacl.SyncAcl, build func(list.AclRecordBuilder) (*consensusproto.RawRecord, error)) string {
	t.Helper()
	acl.Lock()
	defer acl.Unlock()
	rec, err := build(acl.RecordBuilder())
	require.NoError(t, err)
	require.NoError(t, acl.ValidateRawRecord(rec, nil))
	raw, err := rec.MarshalVT()
	require.NoError(t, err)
	id, err := cidutil.NewCidFromBytes(raw)
	require.NoError(t, err)
	// SyncAcl persists the signed record and invokes its unmodified network
	// broadcast and native ACL updater. No mutation is injected into member B.
	require.NoError(t, acl.AddRawRecord(&consensusproto.RawRecordWithId{Id: id, Payload: raw}))
	require.Equal(t, id, acl.Head().Id)
	return id
}

func memberACLState(t *testing.T, acl syncacl.SyncAcl, member crypto.PubKey) map[string]any {
	t.Helper()
	acl.RLock()
	defer acl.RUnlock()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	records, err := acl.RecordsAfter(ctx, "")
	require.NoError(t, err)
	hashes := map[string]string{}
	for _, rec := range records {
		hashes[rec.Id] = t2Hash(rec.Payload)
	}
	require.NotEmpty(t, hashes)
	return map[string]any{
		"acl_head":           acl.Head().Id,
		"member_permissions": int32(acl.AclState().Permissions(member)),
		"read_key_id":        acl.AclState().CurrentReadKeyId(),
		"acl_records_sha256": hashes,
	}
}

func memberACLWait(t *testing.T, acl syncacl.SyncAcl, member crypto.PubKey, head string, permissions list.AclPermissions) {
	t.Helper()
	require.NotEmpty(t, head)
	t2NativeClientWait(t, "native signed ACL delivery", 120*time.Second, func(time.Duration) bool {
		acl.RLock()
		defer acl.RUnlock()
		if acl.Head().Id != head {
			return false
		}
		require.Equal(t, permissions, acl.AclState().Permissions(member))
		return true
	})
}

func memberACLPositive(t *testing.T, state *t2AccountState, reader string, reply *pb.PinkhaTorahAuthorizedOperationReadResponse) string {
	t.Helper()
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NULL, reply.Error.Code)
	require.Empty(t, reply.Error.Description)
	require.NotNil(t, reply.Snapshot)
	snapshot := reply.Snapshot
	require.Equal(t, torahops.AuthorizedOperationReadContract, snapshot.Contract)
	require.Equal(t, reader, snapshot.AccountId)
	require.Equal(t, state.SpaceID, snapshot.SpaceId)
	require.Equal(t, state.OperationID, snapshot.OperationId)
	require.True(t, snapshot.Complete)
	require.Len(t, snapshot.NativeSnapshotToken, 64)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_FOUND, snapshot.Outcome)
	require.Len(t, snapshot.Variants, 1)
	value := snapshot.Variants[0]
	require.Equal(t, state.ClaimID, value.ClaimId)
	require.Equal(t, state.OperationID, value.OperationId)
	require.Equal(t, state.SpaceID, value.SpaceId)
	require.Equal(t, state.AccountID, value.AuthorId)
	require.NotNil(t, value.Target)
	require.Equal(t, state.DocumentID, value.Target.ObjectId)
	require.Equal(t, state.BlockID, value.Target.BlockId)
	require.Equal(t, state.OperationSHA256, t2Hash(value.CanonicalBytes))
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_LIVE_BLOCK, value.Reachability)
	require.Len(t, value.Provenance, 1)
	require.Equal(t, state.AccountID, value.Provenance[0].Creator)
	require.Equal(t, state.ChangeID, value.Provenance[0].NativeChangeId)
	require.NotEmpty(t, value.Provenance[0].NativeAclHeadId)
	raw, err := proto.Marshal(value)
	require.NoError(t, err)
	return t2Hash(raw)
}

func memberACLDenied(t *testing.T, value *pb.PinkhaTorahAuthorizedOperationReadResponse) {
	t.Helper()
	require.Equal(t, uint32(1), value.ProtocolVersion)
	require.NotNil(t, value.Error)
	// The qualified native mapping: 4 permission denied, 9 invalidated closure.
	require.Contains(t, []int32{4, 9}, int32(value.Error.Code))
	require.Nil(t, value.Snapshot)
}

func TestIndependentMemberACLTransport(t *testing.T) {
	const parent, root = "/private", "/private/account-root"
	role, nonce := os.Getenv("PINKHA_MEMBER_ACL_ROLE"), os.Getenv("PINKHA_T2_CLIENT_NONCE")
	require.Contains(t, []string{"owner", "member"}, role)
	require.Len(t, nonce, 32)
	require.Len(t, coherentPeerFixtureSHA, 64)
	require.Equal(t, coherentPeerFixtureSHA, os.Getenv("PINKHA_T2_CLIENT_FIXTURE_SHA"))
	require.Len(t, coherentPeerSourceSHA, 40)
	require.Equal(t, t2HeartPin, vcs.GitCommit)
	var ownership map[string]any
	raw, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	require.NoError(t, err)
	require.NoError(t, json.Unmarshal(raw, &ownership))
	require.Equal(t, map[string]any{"protocol": memberACLProtocol, "nonce": nonce, "role": role, "synthetic_only": true}, ownership)
	entries, err := os.ReadDir(root)
	require.NoError(t, err)
	require.Empty(t, entries, "each independent identity starts with an empty private store")
	require.Len(t, t2OfflineIPs(t), 1)
	helperRole := "creator"
	if role == "member" {
		helperRole = "recovered"
	}
	calls := &t2AccountRPC{t: t, calls: map[string]int{}}
	c := &t2NativeClientCaller{t: t, rpc: calls, role: helperRole, nonce: nonce, returnedCalls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	c.invoke("InitialSetParameters", InitialSetParameters, &pb.RpcInitialSetParametersRequest{
		Platform: "ios", Version: "0.51.0", Workdir: root, DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true},
		&pb.RpcInitialSetParametersResponse{}, 30*time.Second)
	version := &pb.RpcAppGetVersionResponse{}
	c.invoke("AppGetVersion", AppGetVersion, &pb.RpcAppGetVersionRequest{}, version, 10*time.Second)
	require.Equal(t, vcs.GitSummary, version.Version)
	require.Equal(t, os.Getenv("PINKHA_COHERENT_RUNTIME_VERSION"), version.Version)
	createdWallet := &pb.RpcWalletCreateResponse{}
	c.invoke("WalletCreate", WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, createdWallet, 30*time.Second)
	require.NotEmpty(t, createdWallet.AccountKey)
	require.NotEmpty(t, createdWallet.Mnemonic)
	needles, err := json.Marshal([]string{createdWallet.AccountKey, createdWallet.Mnemonic})
	require.NoError(t, err)
	t2WriteFresh(t, filepath.Join(parent, "sensitive-needles.private"), needles)
	c.startRequested = true
	created := &pb.RpcAccountCreateResponse{}
	c.invoke("AccountCreate", AccountCreate, &pb.RpcAccountCreateRequest{
		Name: "Disposable independent member ACL " + role, NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false},
		created, 90*time.Second)
	require.NotNil(t, created.Account)
	accountID := created.Account.Id
	require.NotEmpty(t, accountID)
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
	keys := app.MustComponent[accountservice.Service](mw.GetApp()).Account()
	require.Equal(t, accountID, keys.SignKey.GetPublic().Account())
	ownedWallet := app.MustComponent[wallet.Wallet](mw.GetApp())
	require.Equal(t, filepath.Join(root, accountID), ownedWallet.RepoPath())
	c.invoke("DeviceNetworkStateSet", DeviceNetworkStateSet, &pb.RpcDeviceNetworkStateSetRequest{
		DeviceNetworkType: model.DeviceNetworkType_WIFI, NetworkId: "pinkha-independent-member-owned-bridge"},
		&pb.RpcDeviceNetworkStateSetResponse{}, 30*time.Second)
	server := app.MustComponent[clientserver.ClientServer](mw.GetApp())
	t2NativeClientWait(t, "native member server", 30*time.Second, func(time.Duration) bool { return server.ServerStarted() })
	namespace, err := os.Readlink("/proc/self/ns/net")
	require.NoError(t, err)
	own := memberACLIdentity{AccountID: accountID, PeerID: keys.PeerId, IP: t2OfflineIPs(t)[0], Port: server.Port(), Namespace: namespace}
	state := &t2AccountState{}
	if role == "owner" {
		state.AccountID = accountID
		t2NativeClientCreateTarget(c, state)
		t2NativeClientCreateOperation(c, state)
		state.RawChanges, state.Heads = t2RawHistory(t, state)
		data, err := json.Marshal(state)
		require.NoError(t, err)
		t2WriteFresh(t, filepath.Join(parent, "state.json"), data)
	}
	write := func(phase string, value map[string]any, wire []byte) {
		value["protocol"], value["phase"], value["role"], value["nonce"] = memberACLProtocol, phase, role, nonce
		value["source_sha"], value["heart_sha"], value["runtime_version"] = coherentPeerSourceSHA, vcs.GitCommit, version.Version
		value["fixture_sha256"], value["account_id"], value["peer_id"] = coherentPeerFixtureSHA, accountID, own.PeerID
		value["network_namespace"], value["actual_ipv4"], value["pid"] = namespace, t2OfflineIPs(t), os.Getpid()
		value["rpc_calls"], value["wallet_create_count"], value["wallet_recover_count"] = calls.calls, calls.calls["WalletCreate"], calls.calls["WalletRecover"]
		value["full_t2_acceptance"], value["ios_acceptance"], value["app_capability"] = "NOT_RUN", "NOT_RUN", "OFF"
		if wire != nil {
			value["wire_sha256"] = t2Hash(wire)
			t2WriteFresh(t, filepath.Join(parent, phase+".pb"), wire)
		}
		coherentPeerWrite(t, parent, phase+".json", value)
	}
	write("identity", map[string]any{"identity": own}, nil)
	command := memberACLCommandRead(t, "grant", nonce, 480*time.Second)
	require.NotNil(t, command.Peer)
	require.NotEqual(t, accountID, command.Peer.AccountID)
	require.NotEqual(t, own.PeerID, command.Peer.PeerID)
	require.NotEqual(t, namespace, command.Peer.Namespace)
	memberID := accountID
	if role == "owner" {
		memberID = command.Peer.AccountID
	}
	memberKey, err := crypto.DecodeAccountAddress(memberID)
	require.NoError(t, err)
	spaces := app.MustComponent[space.Service](mw.GetApp())
	ctx, cancel := context.WithTimeout(context.Background(), 180*time.Second)
	defer cancel()
	var acl syncacl.SyncAcl
	grantHead := ""
	if role == "owner" {
		sp, err := spaces.Get(ctx, state.SpaceID)
		require.NoError(t, err)
		require.True(t, sp.GetAclIdentity().Equals(keys.SignKey.GetPublic()))
		acl = sp.CommonSpace().Acl()
		acl.RLock()
		require.Equal(t, list.AclPermissionsOwner, acl.AclState().Permissions(keys.SignKey.GetPublic()))
		require.Equal(t, list.AclPermissionsNone, acl.AclState().Permissions(memberKey))
		acl.RUnlock()
		memberACLRoute(t, *command.Peer, state.SpaceID)
		grantHead = memberACLApply(t, acl, func(builder list.AclRecordBuilder) (*consensusproto.RawRecord, error) {
			return builder.BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{
				{Identity: memberKey, Permissions: list.AclPermissionsWriter, Metadata: nil},
			}})
		})
	} else {
		require.NotNil(t, command.State)
		state = command.State
		require.Equal(t, command.Peer.AccountID, state.AccountID)
		require.NotEqual(t, accountID, state.AccountID)
		grantHead = command.Head
		require.NotEmpty(t, grantHead)
		memberACLRoute(t, *command.Peer, state.SpaceID)
		// Only public identifiers and a signed-head reference cross the fixture
		// boundary. Native SpacePull fetches every ACL, key envelope and tree.
		require.NoError(t, spaces.InviteJoin(ctx, state.SpaceID, grantHead))
		sp, err := spaces.Get(ctx, state.SpaceID)
		require.NoError(t, err)
		require.True(t, sp.GetAclIdentity().Equals(keys.SignKey.GetPublic()))
		acl = sp.CommonSpace().Acl()
		require.NoError(t, sp.WaitMandatoryObjects(ctx))
		c.invoke("WorkspaceOpen", WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{}, 30*time.Second)
	}
	memberACLWait(t, acl, memberKey, grantHead, list.AclPermissionsWriter)
	var wire []byte
	variantSHA := ""
	t2NativeClientWait(t, "independent member original authorized bytes", 150*time.Second, func(remaining time.Duration) bool {
		response, raw := coherentPeerRead(c, state, min(20*time.Second, remaining))
		if response.Error.Code != 0 {
			require.Nil(t, response.Snapshot)
			require.Contains(t, []int32{7, 8, 10}, int32(response.Error.Code))
			return false
		}
		require.NotNil(t, response.Snapshot)
		if response.Snapshot.Outcome == pb.PinkhaTorahAuthorizedOperationRead_ABSENT_IN_VERIFIED_LOCAL_SNAPSHOT {
			require.True(t, response.Snapshot.Complete)
			require.Empty(t, response.Snapshot.Variants)
			return false
		}
		variantSHA = memberACLPositive(t, state, accountID, response)
		wire = raw
		return true
	})
	receipt := func() map[string]any {
		value := memberACLState(t, acl, memberKey)
		value["member_account_id"], value["owner_account_id"], value["space_id"] = memberID, state.AccountID, state.SpaceID
		value["operation_id"], value["canonical_sha256"], value["variant_sha256"] = state.OperationID, state.OperationSHA256, variantSHA
		require.Zero(t, calls.calls["PinkhaTorahOperationsReadTarget"])
		require.Equal(t, 1, calls.calls["WalletCreate"])
		require.Zero(t, calls.calls["WalletRecover"])
		expectedAppends := 0
		if role == "owner" {
			expectedAppends = 1
		}
		require.Equal(t, expectedAppends, calls.calls["PinkhaTorahOperationsAppend"])
		value["append_count"], value["read_target_count"] = expectedAppends, 0
		return value
	}
	write("grant", receipt(), wire)
	roleCommand := memberACLCommandRead(t, "reader", nonce, 360*time.Second)
	readerHead := roleCommand.Head
	if role == "owner" {
		readerHead = memberACLApply(t, acl, func(builder list.AclRecordBuilder) (*consensusproto.RawRecord, error) {
			return builder.BuildPermissionChanges(list.PermissionChangesPayload{Changes: []list.PermissionChangePayload{
				{Identity: memberKey, Permissions: list.AclPermissionsReader},
			}})
		})
	}
	memberACLWait(t, acl, memberKey, readerHead, list.AclPermissionsReader)
	response, raw := coherentPeerRead(c, state, 20*time.Second)
	require.Equal(t, variantSHA, memberACLPositive(t, state, accountID, response))
	write("reader", receipt(), raw)
	if role == "owner" {
		memberACLCommandRead(t, "revoke", nonce, 180*time.Second)
		prior := memberACLState(t, acl, memberKey)
		metadata, _, err := crypto.GenerateRandomEd25519KeyPair()
		require.NoError(t, err)
		memberACLApply(t, acl, func(builder list.AclRecordBuilder) (*consensusproto.RawRecord, error) {
			return builder.BuildAccountRemove(list.AccountRemovePayload{
				Identities: []crypto.PubKey{memberKey},
				Change:     list.ReadKeyChangePayload{MetadataKey: metadata, ReadKey: crypto.NewAES()},
			})
		})
		current := receipt()
		require.NotEqual(t, prior["read_key_id"], current["read_key_id"])
		require.Equal(t, int32(list.AclPermissionsNone), current["member_permissions"])
		write("revoke", current, nil)
	} else {
		memberACLCommandRead(t, "offline", nonce, 120*time.Second)
		require.Empty(t, t2OfflineIPs(t), "actual Docker interface detach precedes cached read")
		t2OfflineNetwork(c, false)
		memberACLWait(t, acl, memberKey, readerHead, list.AclPermissionsReader)
		response, raw = coherentPeerRead(c, state, 20*time.Second)
		require.Equal(t, variantSHA, memberACLPositive(t, state, accountID, response))
		// Hold only a prepared immutable value. The production preparation
		// releases all App/private/object leases before this function returns.
		fenceCtx, fenceCancel := context.WithTimeout(context.Background(), 360*time.Second)
		defer fenceCancel()
		finalize, err := mw.PinkhaMemberACLFixturePrepare(fenceCtx, state.SpaceID, state.OperationID)
		require.NoError(t, err)
		require.NotNil(t, finalize)
		prepared := receipt()
		prepared["real_native_preparation_captured"] = true
		write("offline", prepared, raw)
		unknown := memberACLCommandRead(t, "unknown-revocation", nonce, 120*time.Second)
		require.Empty(t, t2OfflineIPs(t))
		require.NotEqual(t, readerHead, unknown.Head)
		memberACLWait(t, acl, memberKey, readerHead, list.AclPermissionsReader)
		response, raw = coherentPeerRead(c, state, 20*time.Second)
		require.Equal(t, variantSHA, memberACLPositive(t, state, accountID, response))
		lastKnown := receipt()
		lastKnown["unseen_owner_head"] = unknown.Head
		lastKnown["policy"] = "last-known-local-authority-before-native-revocation-observation"
		write("unknown-revocation", lastKnown, raw)
		reconnect := memberACLCommandRead(t, "reconnect", nonce, 120*time.Second)
		require.Equal(t, unknown.Head, reconnect.Head)
		require.Len(t, t2OfflineIPs(t), 1)
		require.NotNil(t, reconnect.Peer)
		memberACLRoute(t, *reconnect.Peer, state.SpaceID)
		c.invoke("DeviceNetworkStateSet", DeviceNetworkStateSet, &pb.RpcDeviceNetworkStateSetRequest{
			DeviceNetworkType: model.DeviceNetworkType_WIFI, NetworkId: "pinkha-independent-member-owned-bridge"},
			&pb.RpcDeviceNetworkStateSetResponse{}, 30*time.Second)
		syncCtx, syncCancel := context.WithTimeout(context.Background(), 30*time.Second)
		peer, err := app.MustComponent[pool.Service](mw.GetApp()).Get(syncCtx, reconnect.Peer.PeerID)
		require.NoError(t, err)
		require.NoError(t, acl.SyncWithPeer(syncCtx, peer))
		syncCancel()
		memberACLWait(t, acl, memberKey, reconnect.Head, list.AclPermissionsNone)
		denied := finalize()
		memberACLDenied(t, denied)
		deniedWire, err := proto.Marshal(denied)
		require.NoError(t, err)
		fenced := receipt()
		fenced["prepared_before_revocation"] = true
		fenced["finalized_after_observed_revocation"] = true
		fenced["error_code"], fenced["snapshot_present"] = int32(denied.Error.Code), denied.Snapshot != nil
		write("publication-fence", fenced, deniedWire)
		denied, deniedWire = coherentPeerRead(c, state, 20*time.Second)
		memberACLDenied(t, denied)
		current := receipt()
		current["error_code"], current["snapshot_present"] = int32(denied.Error.Code), denied.Snapshot != nil
		write("revoked", current, deniedWire)
	}
	memberACLCommandRead(t, "stop", nonce, 180*time.Second)
	final := receipt()
	shutdown()
	require.True(t, c.closed)
	stopped, stoppedWire := coherentPeerRead(c, state, 10*time.Second)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NOT_LOGGED_IN, stopped.Error.Code)
	require.Nil(t, stopped.Snapshot)
	final["account_stop_verified"], final["test_passed"], final["stopped_error_code"], final["snapshot_present"] = true, true, int32(stopped.Error.Code), false
	final["returned_byte_calls"] = c.returnedCalls
	write("final", final, stoppedWire)
}
