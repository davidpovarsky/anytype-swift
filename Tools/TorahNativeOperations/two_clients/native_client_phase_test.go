package service

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/spacecore/clientserver"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/stretchr/testify/require"
)

// This fixture uses the complete native application and its ordinary LAN
// discovery/peer transport. The second container starts with an empty account
// root and receives only the recovery account key and public expected IDs. It
// does not receive databases, device keys, signed changes, or a transport shim.
var t2NativeClientFixtureSHA = "UNSET"

const t2NativeClientProtocol = "pinkha-t2-two-native-clients-bootstrap-v1"

func t2NativeClientReport(t *testing.T, path string, data []byte) {
	t.Helper()
	_, err := os.Lstat(path)
	require.True(t, os.IsNotExist(err), "each client receipt must be new")
	t2WriteFresh(t, path+".partial", data)
	require.NoError(t, os.Rename(path+".partial", path))
}

func t2NativeClientWait(t *testing.T, label string, limit time.Duration, condition func(time.Duration) bool) {
	t.Helper()
	deadline := time.Now().Add(limit)
	for {
		remaining := time.Until(deadline)
		if remaining <= 0 {
			t.Fatal("native two-client bootstrap timeout: " + label)
		}
		if condition(remaining) {
			return
		}
		time.Sleep(min(200*time.Millisecond, max(0, time.Until(deadline))))
	}
}

func t2NativeClientCreateTarget(c *t2NativeClientCaller, state *t2AccountState) {
	c.t.Helper()
	createdSpace := &pb.RpcWorkspaceCreateResponse{}
	c.invoke("WorkspaceCreate", WorkspaceCreate, &pb.RpcWorkspaceCreateRequest{Details: domain.NewDetails().
		SetString(bundle.RelationKeyName, "T2 isolated native LAN bootstrap").ToProto()}, createdSpace, 30*time.Second)
	state.SpaceID = createdSpace.SpaceId
	require.NotEmpty(c.t, state.SpaceID)
	c.invoke("WorkspaceOpen", WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{}, 30*time.Second)
	t2NativeClientWait(c.t, "indexed native Page type", 60*time.Second, func(remaining time.Duration) bool {
		response := &pb.RpcObjectSearchResponse{}
		c.invoke("ObjectSearch", ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: state.SpaceID,
			Filters: []*model.BlockContentDataviewFilter{{RelationKey: "uniqueKey", Condition: model.BlockContentDataviewFilter_Equal,
				Value: domain.String("ot-page").ToProto()}}, Keys: []string{"id", "spaceId", "uniqueKey"}, Limit: 2}, response, min(20*time.Second, remaining))
		if len(response.Records) == 0 {
			return false
		}
		require.Len(c.t, response.Records, 1)
		details := domain.NewDetailsFromProto(response.Records[0])
		require.Equal(c.t, state.SpaceID, details.GetString(bundle.RelationKeySpaceId))
		require.Equal(c.t, "ot-page", details.GetString(bundle.RelationKeyUniqueKey))
		require.NotEmpty(c.t, details.GetString(bundle.RelationKeyId))
		return true
	})
	created := &pb.RpcObjectCreateResponse{}
	c.invoke("ObjectCreate", ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: state.SpaceID, ObjectTypeUniqueKey: "ot-page",
		Details: domain.NewDetails().SetString(bundle.RelationKeyName, t2VisibleToken).ToProto()}, created, 30*time.Second)
	state.DocumentID = created.ObjectId
	require.NotEmpty(c.t, state.DocumentID)
	block := &pb.RpcBlockCreateResponse{}
	c.invoke("BlockCreate", BlockCreate, &pb.RpcBlockCreateRequest{ContextId: state.DocumentID, TargetId: state.DocumentID,
		Position: model.Block_Inner, Block: &model.Block{Content: &model.BlockContentOfText{
			Text: &model.BlockContentText{Text: t2VisibleToken}}}}, block, 30*time.Second)
	state.BlockID = block.BlockId
	require.NotEmpty(c.t, state.BlockID)
}

func t2NativeClientCreateOperation(c *t2NativeClientCaller, state *t2AccountState) {
	c.t.Helper()
	root, err := torahopscontract.Root(state.SpaceID)
	require.NoError(c.t, err)
	state.RootID, state.OperationID = root.Id, fmt.Sprintf("%032x", 1)
	request, _ := t2NativeRPCRequests(state)
	response := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	c.invoke("PinkhaTorahOperationsAppend", PinkhaTorahOperationsAppend, request, response, 30*time.Second)
	require.Equal(c.t, uint32(1), response.ProtocolVersion)
	require.NotNil(c.t, response.Error)
	require.Equal(c.t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, response.Error.Code)
	require.Empty(c.t, response.Error.Issues)
	require.NotNil(c.t, response.Receipt)
	require.Equal(c.t, pb.RpcPinkhaTorahOperations_CREATED, response.Receipt.Disposition)
	require.NotEmpty(c.t, response.Receipt.ClaimId)
	require.NotEmpty(c.t, response.Receipt.ChangeId)
	require.NotNil(c.t, response.Receipt.Resolution)
	require.False(c.t, response.Receipt.Resolution.Conflict)
	require.Len(c.t, response.Receipt.Resolution.Claims, 1)
	state.ClaimID, state.ChangeID = response.Receipt.ClaimId, response.Receipt.ChangeId
	keys := app.MustComponent[wallet.Wallet](mw.GetApp()).Account()
	canonical, err := (torahops.Operation{Version: torahops.Version, SpaceID: state.SpaceID, OperationID: state.OperationID,
		AuthorID: keys.SignKey.GetPublic().Account(), Kind: torahops.Add,
		Target: torahops.Target{ObjectID: state.DocumentID, BlockID: state.BlockID},
		Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:t2-account:1"}, Payload: []byte(t2PrivatePayload)}).CanonicalBytes()
	require.NoError(c.t, err)
	state.OperationSHA256 = t2Hash(canonical)
}

// This failure-only trace never authorizes a retry or changes signed history.
// Wire issues are enum labels; native error strings and request/response bytes
// are deliberately absent. Storage presence is a later diagnostic observation,
// not proof of the state at the original failed call.
func t2NativeClientTraceReadFailure(t *testing.T, state *t2AccountState, read *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
	t.Helper()
	if read != nil && read.Error != nil {
		t.Logf("T2_READ_FAILURE wire_code=%d wire_issues=%v snapshot_present=%t", read.Error.Code, read.Error.Issues, read.Snapshot != nil)
	}
	application := mw.GetApp()
	if application == nil {
		t.Log("T2_READ_FAILURE current_account=false")
		return
	}
	spaces, err := app.GetComponent[space.Service](application)
	if err != nil {
		t.Logf("T2_READ_FAILURE space_service=false error_type=%T", err)
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	spc, err := spaces.Get(ctx, state.SpaceID)
	if err != nil || spc == nil {
		t.Logf("T2_READ_FAILURE space_lookup=false error_type=%T", err)
		return
	}
	targetPresent, targetErr := spc.Storage().HasTree(ctx, state.DocumentID)
	rootPresent, rootErr := spc.Storage().HasTree(ctx, state.RootID)
	t.Logf("T2_READ_FAILURE later_storage_presence target=%t target_error_type=%T private_root=%t root_error_type=%T", targetPresent, targetErr, rootPresent, rootErr)
}

func t2NativeClientReadReady(state *t2AccountState, read *pb.RpcPinkhaTorahOperationsReadTargetResponse) (bool, error) {
	if read == nil || read.ProtocolVersion != 1 || read.Error == nil {
		return false, fmt.Errorf("invalid native read envelope")
	}
	if read.Error.Code != pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL {
		if read.Snapshot != nil {
			return false, fmt.Errorf("failed native read returned a snapshot")
		}
		switch read.Error.Code {
		case pb.RpcPinkhaTorahOperationsReadTargetResponseError_HISTORY_UNAVAILABLE,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_TARGET_UNAVAILABLE,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_PROJECTION_BEHIND:
			for _, issue := range read.Error.Issues {
				if !slices.Contains([]pb.RpcPinkhaTorahOperationsIssue{pb.RpcPinkhaTorahOperations_ISSUE_HISTORY_UNAVAILABLE,
					pb.RpcPinkhaTorahOperations_ISSUE_TARGET_UNAVAILABLE, pb.RpcPinkhaTorahOperations_ISSUE_PROJECTION_BEHIND}, issue) {
					return false, fmt.Errorf("nontransient issue joined with native read readiness")
				}
			}
			return false, nil
		default:
			return false, fmt.Errorf("unexpected native read error during LAN bootstrap: code=%d", read.Error.Code)
		}
	}
	if len(read.Error.Issues) != 0 || read.Snapshot == nil {
		return false, fmt.Errorf("incomplete native read success")
	}
	snapshot := read.Snapshot
	if snapshot.Scope != pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE || len(snapshot.Conflicts) != 0 || len(snapshot.PendingObservedClaimIds) != 0 {
		return false, fmt.Errorf("unexpected native snapshot scope or extra history")
	}
	if len(snapshot.Live) == 0 {
		// A valid root-only local prefix can arrive before its operation. Wait
		// for that precise missing history, never count it as convergence.
		if len(snapshot.VerifiedLocalHeads) > 1 || (len(snapshot.VerifiedLocalHeads) == 1 && snapshot.VerifiedLocalHeads[0] != state.RootID) {
			return false, fmt.Errorf("unexpected native prefix head")
		}
		return false, nil
	}
	if len(snapshot.Live) != 1 || snapshot.Live[0] == nil || snapshot.Live[0].ClaimId != state.ClaimID || !slices.Equal(state.Heads, snapshot.VerifiedLocalHeads) {
		return false, fmt.Errorf("unexpected native claim or head")
	}
	return true, nil
}

// Observe only the response and readiness decision that already occurred.
// Descriptions, payloads, IDs and the error text never enter this fixed record.
func t2NativeClientReadObservation(read *pb.RpcPinkhaTorahOperationsReadTargetResponse, ready bool, err error) string {
	code := "INVALID_ENVELOPE"
	if read != nil && read.ProtocolVersion == 1 && read.Error != nil {
		code = "UNRECOGNIZED_CODE"
		switch read.Error.Code {
		case pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_UNKNOWN_ERROR,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_BAD_INPUT,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_UNSUPPORTED_VERSION,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_PERMISSION_DENIED,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_NOT_LOGGED_IN,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_ACCOUNT_CHANGED,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_TARGET_UNAVAILABLE,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_HISTORY_UNAVAILABLE,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_PROJECTION_BEHIND,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_READ_LIMIT,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_CANCELLED,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_DEADLINE_EXCEEDED,
			pb.RpcPinkhaTorahOperationsReadTargetResponseError_COLLISION:
			code = read.Error.Code.String()
		}
	}
	readiness := "WAIT"
	if err != nil {
		readiness = "REJECTED"
	} else if ready {
		readiness = "READY"
	}
	return fmt.Sprintf("T2_READ_OBSERVATION code=%s snapshot_present=%t readiness=%s", code, read != nil && read.Snapshot != nil, readiness)
}

func t2NativeClientBaseline(t *testing.T, state *t2AccountState, snapshot *pb.RpcPinkhaTorahOperationsSnapshot) {
	t.Helper()
	require.NotNil(t, snapshot)
	require.Equal(t, pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE, snapshot.Scope)
	require.Equal(t, state.Heads, snapshot.VerifiedLocalHeads)
	require.Len(t, snapshot.Live, 1)
	require.Empty(t, snapshot.Conflicts)
	require.Empty(t, snapshot.PendingObservedClaimIds)
	claim := snapshot.Live[0]
	require.Equal(t, state.ClaimID, claim.ClaimId)
	require.NotNil(t, claim.Operation)
	op := claim.Operation
	require.NotNil(t, op.Target)
	require.NotNil(t, op.Source)
	require.Equal(t, pb.RpcPinkhaTorahOperations_ADD, op.Kind)
	canonical, err := (torahops.Operation{Version: op.Version, SpaceID: op.SpaceId,
		OperationID: op.OperationId, AuthorID: op.AuthorId, Kind: torahops.Add,
		Target:  torahops.Target{ObjectID: op.Target.ObjectId, BlockID: op.Target.BlockId},
		Source:  torahops.Source{ProviderID: op.Source.ProviderId, CanonicalRef: op.Source.CanonicalRef},
		Payload: op.Payload, Observed: op.ObservedClaimIds}).CanonicalBytes()
	require.NoError(t, err)
	require.Equal(t, state.OperationSHA256, t2Hash(canonical))
}

func TestT2NativeClientBootstrapPhase(t *testing.T) {
	role, nonce := os.Getenv("PINKHA_T2_CLIENT_ROLE"), os.Getenv("PINKHA_T2_CLIENT_NONCE")
	require.Contains(t, []string{"creator", "recovered"}, role)
	require.NotEmpty(t, nonce)
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
		Role          string `json:"role"`
		Nonce         string `json:"nonce"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	require.NoError(t, json.Unmarshal(ownerBytes, &owner))
	require.Equal(t, t2NativeClientProtocol, owner.Protocol)
	require.Equal(t, role, owner.Role)
	require.Equal(t, nonce, owner.Nonce)
	require.True(t, owner.SyntheticOnly)
	entries, err := os.ReadDir(root)
	require.NoError(t, err)
	require.Empty(t, entries, "each native client must begin with an empty, independent account root")
	netNS, err := os.Readlink("/proc/self/ns/net")
	require.NoError(t, err)
	require.True(t, strings.HasPrefix(netNS, "net:["))
	addresses, err := net.InterfaceAddrs()
	require.NoError(t, err)
	var ipv4 []string
	for _, address := range addresses {
		ip, _, parseErr := net.ParseCIDR(address.String())
		if parseErr == nil && ip.To4() != nil && !ip.IsLoopback() {
			ipv4 = append(ipv4, ip.String())
		}
	}
	require.Len(t, ipv4, 1, "one isolated bridge interface required")
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	c := &t2NativeClientCaller{t: t, rpc: rpc, role: role, nonce: nonce, returnedCalls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	c.invoke("InitialSetParameters", InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{}, 30*time.Second)
	version := &pb.RpcAppGetVersionResponse{}
	c.invoke("AppGetVersion", AppGetVersion, &pb.RpcAppGetVersionRequest{}, version, 10*time.Second)
	require.Equal(t, "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-"+t2LegacyPatch+
		"-pinkha-t2-registry-v1-"+t2AccountRegistrationSHA, version.Version)
	state := &t2AccountState{}
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
		c.invoke("AccountCreate", AccountCreate, &pb.RpcAccountCreateRequest{Name: "T2 isolated LAN bootstrap",
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false}, created, 60*time.Second)
		require.NotNil(t, created.Account)
		state.AccountID = created.Account.Id
		t2NativeClientCreateTarget(c, state)
		t2NativeClientCreateOperation(c, state)
		state.RawChanges, state.Heads = t2RawHistory(t, state)
		stateBytes, err := json.Marshal(state)
		require.NoError(t, err)
		t2WriteFresh(t, filepath.Join(parent, "state.json"), stateBytes)
	} else {
		stateBytes, err := os.ReadFile(filepath.Join(parent, "state.json"))
		require.NoError(t, err)
		require.NoError(t, json.Unmarshal(stateBytes, state))
		require.NotEmpty(t, state.AccountID)
		key, err := os.ReadFile(filepath.Join(parent, "account-key.private"))
		require.NoError(t, err)
		require.NotEmpty(t, key)
		c.invoke("WalletRecover", WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)}, &pb.RpcWalletRecoverResponse{}, 30*time.Second)
		request := &pb.RpcAccountSelectRequest{Id: state.AccountID, RootPath: root,
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false, PreferredSpaceId: state.SpaceID}
		selected := &pb.RpcAccountSelectResponse{}
		// This is a genuinely empty B root, so native cold recovery initializes
		// its own repo. Do not replace an unexpected error with AccountCreate,
		// migration of nonexistent data, or a copy of A's database/device key.
		c.startRequested = true
		c.invoke("AccountSelect", AccountSelect, request, selected, 180*time.Second)
		require.NotNil(t, selected.Account)
		require.Equal(t, state.AccountID, selected.Account.Id)
		c.invoke("WorkspaceOpen", WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{}, 30*time.Second)
	}
	// Explicit native network state, after real account startup. The enclosing
	// Docker bridge is internal, and neither client has an external route.
	c.invoke("DeviceNetworkStateSet", DeviceNetworkStateSet, &pb.RpcDeviceNetworkStateSetRequest{
		DeviceNetworkType: model.DeviceNetworkType_WIFI, NetworkId: "pinkha-t2-owned-internal-bridge"},
		&pb.RpcDeviceNetworkStateSetResponse{}, 30*time.Second)
	nativeWallet := app.MustComponent[wallet.Wallet](mw.GetApp())
	peerID := nativeWallet.Account().PeerId
	require.NotEmpty(t, peerID)
	require.Equal(t, filepath.Join(root, state.AccountID), nativeWallet.RepoPath())
	server := app.MustComponent[clientserver.ClientServer](mw.GetApp())
	t2NativeClientWait(t, "native LAN server", 30*time.Second, func(time.Duration) bool { return server.ServerStarted() })
	require.Greater(t, server.Port(), 0)
	_, readRequest := t2NativeRPCRequests(state)
	var read *pb.RpcPinkhaTorahOperationsReadTargetResponse
	t2NativeClientWait(t, "private history received through ordinary native transport", 150*time.Second, func(remaining time.Duration) bool {
		read = &pb.RpcPinkhaTorahOperationsReadTargetResponse{}
		c.raw("PinkhaTorahOperationsReadTarget", PinkhaTorahOperationsReadTarget, readRequest, read, min(20*time.Second, remaining))
		ready, err := t2NativeClientReadReady(state, read)
		t.Log(t2NativeClientReadObservation(read, ready, err))
		if err != nil {
			t2NativeClientTraceReadFailure(t, state, read)
		}
		require.NoError(t, err)
		return ready
	})
	t2NativeClientBaseline(t, state, read.Snapshot)
	raw, heads := t2RawHistory(t, state)
	require.Equal(t, state.RawChanges, raw, "recovered native store must contain original signed bytes, received without file seeding")
	require.Equal(t, state.Heads, heads)
	shown := &pb.RpcObjectShowResponse{}
	c.invoke("ObjectShow", ObjectShow, &pb.RpcObjectShowRequest{SpaceId: state.SpaceID, ObjectId: state.DocumentID, ContextId: state.DocumentID}, shown, 30*time.Second)
	require.NotNil(t, shown.ObjectView)
	require.Equal(t, state.DocumentID, shown.ObjectView.RootId)
	details := t2ShownDetails(t, shown, state)
	require.Equal(t, t2VisibleToken, details.GetString("name"))
	stateBytes, err := os.ReadFile(filepath.Join(parent, "state.json"))
	require.NoError(t, err)
	report := map[string]any{"protocol": t2NativeClientProtocol, "role": role, "nonce": nonce, "pid": os.Getpid(),
		"network_namespace": netNS, "bridge_ipv4": ipv4[0], "peer_id": peerID, "native_server_port": server.Port(),
		"heart_sha": vcs.GitCommit, "runtime_version": version.Version, "client_fixture_sha256": t2NativeClientFixtureSHA,
		"account_fixture_sha256": t2AccountFixtureSHA, "rpc_manifest_sha256": t2RPCAccountSchemaSHA,
		"registration_patch_sha256": t2AccountRegistrationSHA, "state_sha256": t2Hash(stateBytes),
		"account_id": state.AccountID, "space_id": state.SpaceID, "document_id": state.DocumentID,
		"block_id": state.BlockID, "private_root_id": state.RootID, "raw_changes_sha256": raw, "heads": heads,
		"native_local_only_requested": true, "native_lan_enabled_requested": true,
		"initial_account_root": "OBSERVED_EMPTY", "ordinary_document": "PASS_NATIVE_OBJECT_SHOW",
		"private_read":   "PASS_GENERATED_RPC_ORIGINAL_SIGNED_HISTORY",
		"app_capability": "OFF", "two_ios_apps": "NOT_RUN", "offline_conflict_merge": "NOT_RUN"}
	if role == "recovered" {
		report["active_private_append"] = "NONE_RECOVERED_CLIENT_READ_ONLY"
	} else {
		report["active_private_append"] = "ONE_CREATOR_GENERATED_RPC_APPEND"
	}
	readyBytes, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	t2NativeClientReport(t, filepath.Join(parent, "ready.json"), readyBytes)
	// B's wallet (30s), cold AccountSelect (180s), workspace/network/server
	// readiness (90s), private read (150s), Show (30s), and owner bookkeeping
	// fit inside A's 600s peer wait. The host controller uses a 540s B bound.
	peerWait := 60 * time.Second
	if role == "creator" {
		peerWait = 600 * time.Second
	}
	t2NativeClientWait(t, "owner-controlled stop after both native clients are ready", peerWait, func(time.Duration) bool {
		data, readErr := os.ReadFile(filepath.Join(parent, "stop.json"))
		if os.IsNotExist(readErr) {
			return false
		}
		require.NoError(t, readErr)
		var command struct {
			Protocol string `json:"protocol"`
			Nonce    string `json:"nonce"`
		}
		require.NoError(t, json.Unmarshal(data, &command))
		require.Equal(t, t2NativeClientProtocol, command.Protocol)
		require.Equal(t, nonce, command.Nonce)
		return true
	})
	shutdown()
	require.True(t, c.closed)
	appendRequest, readRequest := t2NativeRPCRequests(state)
	deniedRead, deniedAppend := &pb.RpcPinkhaTorahOperationsReadTargetResponse{}, &pb.RpcPinkhaTorahOperationsAppendResponse{}
	c.raw("PinkhaTorahOperationsReadTarget", PinkhaTorahOperationsReadTarget, readRequest, deniedRead, 10*time.Second)
	c.raw("PinkhaTorahOperationsAppend", PinkhaTorahOperationsAppend, appendRequest, deniedAppend, 10*time.Second)
	require.Equal(t, uint32(1), deniedRead.ProtocolVersion)
	require.Equal(t, uint32(1), deniedAppend.ProtocolVersion)
	require.NotNil(t, deniedRead.Error)
	require.NotNil(t, deniedAppend.Error)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NOT_LOGGED_IN, deniedRead.Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NOT_LOGGED_IN, deniedAppend.Error.Code)
	require.Nil(t, deniedRead.Snapshot)
	require.Nil(t, deniedAppend.Receipt)
	report["closed"] = true
	report["account_stop_verified"] = true
	report["post_stop_rpc"] = "READ_AND_APPEND_NOT_LOGGED_IN"
	report["rpc_calls"] = rpc.calls
	report["returned_byte_calls"] = c.returnedCalls
	report["test_passed"] = true
	finalBytes, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	t2NativeClientReport(t, filepath.Join(parent, "final.json"), finalBytes)
	t.Log(fmt.Sprintf("PASS native LAN bootstrap role=%s; ordinary and private data verified; no database/device-key seeding", role))
}
