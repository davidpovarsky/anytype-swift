package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/device"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

const t2OfflineProtocol = "pinkha-t2-native-offline-conflict-reopen-v1"

// History contains only original change IDs, parent IDs and SHA256 digests.
// It is an assertion input, never signed history or a native storage overlay.
type t2OfflineHistory struct {
	Changes map[string]string   `json:"changes_sha256"`
	Parents map[string][]string `json:"parents"`
	Heads   []string            `json:"heads"`
}

type t2OfflineCommand struct {
	Protocol string           `json:"protocol"`
	Nonce    string           `json:"nonce"`
	Role     string           `json:"role"`
	Phase    string           `json:"phase"`
	History  t2OfflineHistory `json:"expected_history"`
}

func t2OfflineExpected(state *t2AccountState, author, role string) []torahops.Operation {
	unique, remove := 2, 5
	if role == "recovered" {
		unique, remove = 3, 6
	}
	target := torahops.Target{ObjectID: state.DocumentID, BlockID: state.BlockID}
	base := torahops.Operation{Version: 1, SpaceID: state.SpaceID, AuthorID: author, Target: target,
		Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:t2-offline:1"}, Kind: torahops.Add}
	one, shared, tombstone := base, base, base
	one.OperationID, one.Payload = fmt.Sprintf("%032x", unique), []byte("t2-offline-unique-"+role)
	shared.OperationID, shared.Payload = fmt.Sprintf("%032x", 4), []byte("t2-offline-collision-"+role)
	tombstone.OperationID, tombstone.Kind = fmt.Sprintf("%032x", remove), torahops.Remove
	tombstone.Source, tombstone.Payload, tombstone.Observed = torahops.Source{}, nil, []string{state.ClaimID}
	return []torahops.Operation{one, shared, tombstone}
}

func t2OfflineRequest(op torahops.Operation) *pb.RpcPinkhaTorahOperationsAppendRequest {
	request := &pb.RpcPinkhaTorahOperationsAppendRequest{ProtocolVersion: 1, SpaceId: op.SpaceID,
		OperationId: op.OperationID, Kind: pb.RpcPinkhaTorahOperations_ADD,
		Target:  &pb.RpcPinkhaTorahOperationsTarget{ObjectId: op.Target.ObjectID, BlockId: op.Target.BlockID},
		Payload: slices.Clone(op.Payload), ObservedClaimIds: slices.Clone(op.Observed)}
	if op.Kind == torahops.Remove {
		request.Kind = pb.RpcPinkhaTorahOperations_REMOVE
	} else {
		request.Source = &pb.RpcPinkhaTorahOperationsSource{ProviderId: op.Source.ProviderID, CanonicalRef: op.Source.CanonicalRef}
	}
	// There is deliberately no request author, root ID, signed change or key.
	return request
}

func t2OfflineClaim(op torahops.Operation) (id, digest string, err error) {
	id, _, err = torahops.EncodeClaim(op)
	if err != nil {
		return
	}
	canonical, err := op.CanonicalBytes()
	return id, t2Hash(canonical), err
}

func t2OfflineClaimMatches(claim *pb.RpcPinkhaTorahOperationsClaim, expected torahops.Operation) bool {
	if claim == nil || claim.Operation == nil || claim.Operation.Target == nil || claim.Operation.Source == nil {
		return false
	}
	id, digest, err := t2OfflineClaim(expected)
	if err != nil || claim.ClaimId != id || claim.Digest != digest {
		return false
	}
	op := claim.Operation
	if op.Kind != pb.RpcPinkhaTorahOperations_ADD {
		return false
	}
	actual := torahops.Operation{Version: op.Version, SpaceID: op.SpaceId, OperationID: op.OperationId,
		AuthorID: op.AuthorId, Kind: torahops.Add, Target: torahops.Target{ObjectID: op.Target.ObjectId, BlockID: op.Target.BlockId},
		Source:  torahops.Source{ProviderID: op.Source.ProviderId, CanonicalRef: op.Source.CanonicalRef},
		Payload: op.Payload, Observed: op.ObservedClaimIds}
	canonical, err := actual.CanonicalBytes()
	return err == nil && t2Hash(canonical) == digest
}

func t2OfflineSnapshotReady(state *t2AccountState, author string, response *pb.RpcPinkhaTorahOperationsReadTargetResponse,
	wantedHeads []string) (bool, error) {
	if response == nil || response.ProtocolVersion != 1 || response.Error == nil {
		return false, fmt.Errorf("invalid offline read envelope")
	}
	if response.Error.Code != pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL {
		if response.Snapshot != nil {
			return false, fmt.Errorf("failed offline read exposed a snapshot")
		}
		// A previously established local account/target/root must not disappear
		// merely because its peer was disconnected. Only a projection catch-up
		// can be retried in this later phase; every other issue fails closed.
		if response.Error.Code != pb.RpcPinkhaTorahOperationsReadTargetResponseError_PROJECTION_BEHIND {
			return false, fmt.Errorf("unexpected offline read error: %d", response.Error.Code)
		}
		for _, issue := range response.Error.Issues {
			if issue != pb.RpcPinkhaTorahOperations_ISSUE_PROJECTION_BEHIND {
				return false, fmt.Errorf("nontransient issue joined with offline projection catch-up")
			}
		}
		return false, nil
	}
	view := response.Snapshot
	if len(response.Error.Issues) != 0 || view == nil || view.Scope != pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE ||
		len(view.PendingObservedClaimIds) != 0 {
		return false, fmt.Errorf("invalid offline projection state")
	}
	unique, variants := map[string]torahops.Operation{}, map[string]torahops.Operation{}
	for _, role := range []string{"creator", "recovered"} {
		operations := t2OfflineExpected(state, author, role)
		id, _, err := t2OfflineClaim(operations[0])
		if err != nil {
			return false, err
		}
		unique[id] = operations[0]
		id, _, err = t2OfflineClaim(operations[1])
		if err != nil {
			return false, err
		}
		variants[id] = operations[1]
	}
	seen := map[string]bool{}
	liveUnique, liveVariant := 0, 0
	for _, claim := range view.Live {
		if claim == nil || seen[claim.ClaimId] {
			return false, fmt.Errorf("duplicate or nil live claim")
		}
		seen[claim.ClaimId] = true
		if operation, ok := unique[claim.ClaimId]; ok && t2OfflineClaimMatches(claim, operation) {
			liveUnique++
		} else if operation, ok := variants[claim.ClaimId]; ok && t2OfflineClaimMatches(claim, operation) {
			liveVariant++
		} else {
			return false, fmt.Errorf("unknown claim or removed original claim became live")
		}
	}
	if liveVariant > 1 || len(view.Conflicts) > 1 {
		return false, fmt.Errorf("conflicting operations selected as live")
	}
	if len(view.Conflicts) == 1 {
		conflict := view.Conflicts[0]
		if conflict == nil || !conflict.Conflict || conflict.OperationId != fmt.Sprintf("%032x", 4) || len(conflict.Claims) != 2 || liveVariant != 0 {
			return false, fmt.Errorf("conflict must expose both variants without a winner")
		}
		for _, claim := range conflict.Claims {
			if claim == nil || seen[claim.ClaimId] {
				return false, fmt.Errorf("duplicate or nil conflict claim")
			}
			seen[claim.ClaimId] = true
			operation, ok := variants[claim.ClaimId]
			if !ok || !t2OfflineClaimMatches(claim, operation) {
				return false, fmt.Errorf("unknown conflict variant")
			}
		}
	}
	actualHeads, expectedHeads := slices.Clone(view.VerifiedLocalHeads), slices.Clone(wantedHeads)
	sort.Strings(actualHeads)
	sort.Strings(expectedHeads)
	return liveUnique == 2 && liveVariant == 0 && len(view.Conflicts) == 1 && slices.Equal(actualHeads, expectedHeads), nil
}

func t2OfflineSnapshotHash(t *testing.T, snapshot *pb.RpcPinkhaTorahOperationsSnapshot) string {
	t.Helper()
	copy := proto.Clone(snapshot).(*pb.RpcPinkhaTorahOperationsSnapshot)
	// The storage sequence is expressly local; it is not a cross-client clock.
	copy.LocalAppliedSeq = 0
	sort.Strings(copy.VerifiedLocalHeads)
	raw, err := proto.Marshal(copy)
	require.NoError(t, err)
	return t2Hash(raw)
}

func t2OfflineHistoryRead(t *testing.T, state *t2AccountState, limits ...time.Duration) t2OfflineHistory {
	t.Helper()
	limit := 20 * time.Second
	if len(limits) > 0 {
		require.Len(t, limits, 1)
		require.Greater(t, limits[0], time.Duration(0))
		limit = min(limit, limits[0])
	}
	ctx, cancel := context.WithTimeout(context.Background(), limit)
	defer cancel()
	spc, err := app.MustComponent[space.Service](mw.GetApp()).Get(ctx, state.SpaceID)
	require.NoError(t, err)
	require.Equal(t, state.SpaceID, spc.Id())
	storage, err := spc.Storage().TreeStorage(ctx, state.RootID)
	require.NoError(t, err)
	require.Equal(t, state.RootID, storage.Id())
	root, err := storage.Root(ctx)
	require.NoError(t, err)
	require.Equal(t, state.RootID, root.Id)
	require.Equal(t, state.RawChanges[state.RootID], t2Hash(root.RawChange))
	result := t2OfflineHistory{Changes: map[string]string{root.Id: t2Hash(root.RawChange)}, Parents: map[string][]string{}}
	err = storage.GetAfterAddSeq(ctx, 0, func(_ context.Context, change objecttree.StorageChange) (bool, error) {
		require.NotContains(t, result.Changes, change.Id)
		require.NotEmpty(t, change.PrevIds)
		result.Changes[change.Id] = t2Hash(change.RawChange)
		result.Parents[change.Id] = slices.Clone(change.PrevIds)
		sort.Strings(result.Parents[change.Id])
		return true, nil
	})
	require.NoError(t, err)
	require.Equal(t, state.RawChanges[state.ChangeID], result.Changes[state.ChangeID])
	require.Equal(t, []string{state.RootID}, result.Parents[state.ChangeID])
	result.Heads, err = storage.Heads(ctx)
	require.NoError(t, err)
	sort.Strings(result.Heads)
	entry, err := spc.Storage().HeadStorage().GetEntry(ctx, state.RootID)
	require.NoError(t, err)
	require.True(t, entry.IsDerived)
	require.Empty(t, entry.ParentId)
	require.Equal(t, headstorage.DeletedStatusNotDeleted, entry.DeletedStatus)
	sort.Strings(entry.Heads)
	require.Equal(t, result.Heads, entry.Heads)
	return result
}

func t2OfflineIPs(t *testing.T) []string {
	t.Helper()
	addresses, err := net.InterfaceAddrs()
	require.NoError(t, err)
	result := []string{}
	for _, address := range addresses {
		ip, _, err := net.ParseCIDR(address.String())
		if err == nil && ip.To4() != nil && !ip.IsLoopback() {
			result = append(result, ip.String())
		}
	}
	sort.Strings(result)
	return result
}

func t2OfflineNetwork(c *t2NativeClientCaller, connected bool) []string {
	c.t.Helper()
	addresses := t2OfflineIPs(c.t)
	kind := model.DeviceNetworkType_NOT_CONNECTED
	if connected {
		require.Len(c.t, addresses, 1)
		kind = model.DeviceNetworkType_WIFI
	} else {
		require.Empty(c.t, addresses, "native notification cannot substitute for an actual network detach")
	}
	c.invoke("DeviceNetworkStateSet", DeviceNetworkStateSet, &pb.RpcDeviceNetworkStateSetRequest{
		DeviceNetworkType: kind, NetworkId: "pinkha-t2-owned-internal-bridge"}, &pb.RpcDeviceNetworkStateSetResponse{}, 20*time.Second)
	require.Equal(c.t, kind, app.MustComponent[device.NetworkState](mw.GetApp()).GetNetworkState())
	return addresses
}

func t2OfflineWaitCommand(c *t2NativeClientCaller, parent, phase string, limit time.Duration) t2OfflineCommand {
	c.t.Helper()
	var command t2OfflineCommand
	t2NativeClientWait(c.t, "fixed offline phase "+phase, limit, func(time.Duration) bool {
		data, err := os.ReadFile(filepath.Join(parent, phase+".command.json"))
		if os.IsNotExist(err) {
			return false
		}
		require.NoError(c.t, err)
		require.LessOrEqual(c.t, len(data), 64*1024)
		require.NoError(c.t, json.Unmarshal(data, &command))
		require.Equal(c.t, t2OfflineProtocol, command.Protocol)
		require.Equal(c.t, c.nonce, command.Nonce)
		require.Equal(c.t, c.role, command.Role)
		require.Equal(c.t, phase, command.Phase)
		return true
	})
	return command
}

func t2OfflineReport(c *t2NativeClientCaller, parent, phase string, extra map[string]any) {
	c.t.Helper()
	report := map[string]any{"protocol": t2OfflineProtocol, "nonce": c.nonce, "role": c.role, "phase": phase,
		"pid": os.Getpid(), "client_fixture_sha256": t2NativeClientFixtureSHA,
		"peer_id":              app.MustComponent[wallet.Wallet](mw.GetApp()).Account().PeerId,
		"native_network_state": app.MustComponent[device.NetworkState](mw.GetApp()).GetNetworkState().String(),
		"actual_ipv4":          t2OfflineIPs(c.t), "app_capability": "OFF", "full_t2_acceptance": "NOT_RUN"}
	for key, value := range extra {
		report[key] = value
	}
	raw, err := json.MarshalIndent(report, "", "  ")
	require.NoError(c.t, err)
	t2NativeClientReport(c.t, filepath.Join(parent, phase+".json"), raw)
}

func t2OfflineRead(c *t2NativeClientCaller, state *t2AccountState, limit time.Duration) *pb.RpcPinkhaTorahOperationsReadTargetResponse {
	_, request := t2NativeRPCRequests(state)
	response := &pb.RpcPinkhaTorahOperationsReadTargetResponse{}
	c.raw("PinkhaTorahOperationsReadTarget", PinkhaTorahOperationsReadTarget, request, response, limit)
	return response
}

func t2OfflineAppend(c *t2NativeClientCaller, request *pb.RpcPinkhaTorahOperationsAppendRequest) *pb.RpcPinkhaTorahOperationsAppendResponse {
	response := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	c.raw("PinkhaTorahOperationsAppend", PinkhaTorahOperationsAppend, request, response, 20*time.Second)
	require.Equal(c.t, uint32(1), response.ProtocolVersion)
	require.NotNil(c.t, response.Error)
	require.NotNil(c.t, response.Receipt)
	return response
}

func t2OfflineRetryCollision(c *t2NativeClientCaller, state *t2AccountState, operation torahops.Operation, wantConflict bool) {
	c.t.Helper()
	before := t2OfflineRead(c, state, 20*time.Second)
	require.NotNil(c.t, before.Error)
	require.Equal(c.t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, before.Error.Code)
	require.NotNil(c.t, before.Snapshot)
	request := t2OfflineRequest(operation)
	expectedID, _, err := t2OfflineClaim(operation)
	require.NoError(c.t, err)
	identical := t2OfflineAppend(c, request)
	require.Equal(c.t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, identical.Error.Code)
	require.Empty(c.t, identical.Error.Issues)
	require.Equal(c.t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, identical.Receipt.Disposition)
	require.Equal(c.t, expectedID, identical.Receipt.ClaimId)
	require.Empty(c.t, identical.Receipt.ChangeId)
	require.NotNil(c.t, identical.Receipt.Resolution)
	require.Equal(c.t, operation.OperationID, identical.Receipt.Resolution.OperationId)
	require.Equal(c.t, wantConflict, identical.Receipt.Resolution.Conflict)
	wantedVariants := 1
	if wantConflict {
		wantedVariants = 2
	}
	require.Len(c.t, identical.Receipt.Resolution.Claims, wantedVariants)
	if wantConflict {
		require.Len(c.t, before.Snapshot.Conflicts, 1)
		require.True(c.t, proto.Equal(before.Snapshot.Conflicts[0], identical.Receipt.Resolution))
	} else {
		require.True(c.t, t2OfflineClaimMatches(identical.Receipt.Resolution.Claims[0], operation))
	}
	request.Payload = []byte("uncommitted-third-collision-payload")
	different := t2OfflineAppend(c, request)
	require.Equal(c.t, pb.RpcPinkhaTorahOperationsAppendResponseError_COLLISION, different.Error.Code)
	require.Equal(c.t, []pb.RpcPinkhaTorahOperationsIssue{pb.RpcPinkhaTorahOperations_ISSUE_COLLISION}, different.Error.Issues)
	require.Equal(c.t, pb.RpcPinkhaTorahOperations_COLLISION_DIFFERENT_PAYLOAD, different.Receipt.Disposition)
	rejected := operation
	rejected.Payload = slices.Clone(request.Payload)
	rejectedID, _, err := t2OfflineClaim(rejected)
	require.NoError(c.t, err)
	require.Equal(c.t, rejectedID, different.Receipt.ClaimId)
	require.Empty(c.t, different.Receipt.ChangeId)
	require.True(c.t, proto.Equal(identical.Receipt.Resolution, different.Receipt.Resolution))
	after := t2OfflineRead(c, state, 20*time.Second)
	require.True(c.t, proto.Equal(before, after), "retry and rejected collision must preserve every local field and signed head")
}

type t2DroppedClientReply struct {
	requestSHA string
	calls      int
	replyBytes int
	returned   bool
}

// The fault is at the client byte-return boundary. Invoke the real generated
// entry, but never decode, replace or expose its first reply to the caller.
// This is not a network packet loss or a process/power failure simulation.
func t2DropClientReply(entry func([]byte) []byte, observed *t2DroppedClientReply) func([]byte) []byte {
	return func(request []byte) []byte {
		observed.calls++
		observed.requestSHA = t2Hash(request)
		reply := entry(request)
		observed.replyBytes = len(reply)
		observed.returned = true
		return nil
	}
}

func t2LostReplyCommittedChange(before, after t2OfflineHistory) (string, error) {
	if len(before.Changes) != 2 || len(before.Parents) != 1 || len(before.Heads) != 1 ||
		len(after.Changes) != 3 || len(after.Parents) != 2 || len(after.Heads) != 1 {
		return "", fmt.Errorf("lost-reply proof requires the original history plus exactly one signed commit")
	}
	for id, hash := range before.Changes {
		if after.Changes[id] != hash {
			return "", fmt.Errorf("original signed change changed during lost-reply append")
		}
	}
	for id, parents := range before.Parents {
		if !slices.Equal(after.Parents[id], parents) {
			return "", fmt.Errorf("original signed parentage changed during lost-reply append")
		}
	}
	changeID := ""
	for id := range after.Changes {
		if _, existed := before.Changes[id]; !existed {
			changeID = id
		}
	}
	if changeID == "" || !slices.Equal(after.Heads, []string{changeID}) ||
		!slices.Equal(after.Parents[changeID], before.Heads) {
		return "", fmt.Errorf("lost-reply append is not one new signed child of the original head")
	}
	return changeID, nil
}

func t2OfflineAppendLostReply(c *t2NativeClientCaller, state *t2AccountState, operation torahops.Operation) (string, string, map[string]any) {
	c.t.Helper()
	deadline := time.Now().Add(60 * time.Second)
	remaining := func() time.Duration {
		left := time.Until(deadline)
		require.Greater(c.t, left, time.Duration(0), "one fixed lost-reply proof deadline")
		return min(20*time.Second, left)
	}
	require.Equal(c.t, torahops.Add, operation.Kind)
	beforeHistory := t2OfflineHistoryRead(c.t, state, remaining())
	beforeRead := t2OfflineRead(c, state, remaining())
	require.NotNil(c.t, beforeRead.Error)
	require.Equal(c.t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, beforeRead.Error.Code)
	require.Empty(c.t, beforeRead.Error.Issues)
	t2NativeClientBaseline(c.t, state, beforeRead.Snapshot)
	require.Equal(c.t, beforeHistory, t2OfflineHistoryRead(c.t, state, remaining()), "pre-write read must not add signed state")
	encoded, err := proto.Marshal(t2OfflineRequest(operation))
	require.NoError(c.t, err)
	original := slices.Clone(encoded)
	const method = "PinkhaTorahOperationsAppend"
	initialCalls := c.returnedCalls[method]
	dropped := &t2DroppedClientReply{}
	c.rpc.calls[method]++
	returned := c.callBytes(method, t2DropClientReply(PinkhaTorahOperationsAppend, dropped), encoded, remaining())
	require.Nil(c.t, returned)
	require.True(c.t, dropped.returned)
	require.Equal(c.t, 1, dropped.calls)
	require.Greater(c.t, dropped.replyBytes, 0)
	require.Equal(c.t, t2Hash(original), dropped.requestSHA)
	require.True(c.t, bytes.Equal(original, encoded))

	// Inspect native signed storage before ReadTarget. A read cannot create the
	// evidence used to declare this write committed. Any failed assertion ends
	// this test before a second mutation request can be issued.
	committedHistory := t2OfflineHistoryRead(c.t, state, remaining())
	changeID, err := t2LostReplyCommittedChange(beforeHistory, committedHistory)
	require.NoError(c.t, err)
	committed := t2OfflineRead(c, state, remaining())
	require.NotNil(c.t, committed.Error)
	require.Equal(c.t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, committed.Error.Code)
	require.Empty(c.t, committed.Error.Issues)
	require.NotNil(c.t, committed.Snapshot)
	require.Equal(c.t, pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE, committed.Snapshot.Scope)
	require.Empty(c.t, committed.Snapshot.Conflicts)
	require.Empty(c.t, committed.Snapshot.PendingObservedClaimIds)
	require.Len(c.t, committed.Snapshot.Live, 2)
	require.Equal(c.t, []string{changeID}, committed.Snapshot.VerifiedLocalHeads)
	require.Greater(c.t, committed.Snapshot.LocalAppliedSeq, beforeRead.Snapshot.LocalAppliedSeq)
	claimID, _, err := t2OfflineClaim(operation)
	require.NoError(c.t, err)
	seenOriginal, seenNew := 0, 0
	for _, claim := range committed.Snapshot.Live {
		require.NotNil(c.t, claim)
		if claim.ClaimId == state.ClaimID {
			require.True(c.t, proto.Equal(beforeRead.Snapshot.Live[0], claim))
			seenOriginal++
		} else {
			require.True(c.t, t2OfflineClaimMatches(claim, operation))
			seenNew++
		}
	}
	require.Equal(c.t, 1, seenOriginal)
	require.Equal(c.t, 1, seenNew)
	afterReadHistory := t2OfflineHistoryRead(c.t, state, remaining())
	require.Equal(c.t, committedHistory, afterReadHistory, "ReadTarget must not manufacture the committed history")
	beforeRetryBytes, err := proto.Marshal(committed)
	require.NoError(c.t, err)

	// Reuse the exact original encoded bytes, not a request reconstructed from
	// the read or the dropped response. Observe the actual second entry input.
	retrySHA, retryCalls := "", 0
	c.rpc.calls[method]++
	reply := c.callBytes(method, func(data []byte) []byte {
		retrySHA, retryCalls = t2Hash(data), retryCalls+1
		return PinkhaTorahOperationsAppend(data)
	}, encoded, remaining())
	require.Equal(c.t, 1, retryCalls)
	require.Equal(c.t, dropped.requestSHA, retrySHA)
	require.True(c.t, bytes.Equal(original, encoded))
	retry := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	require.NoError(c.t, proto.Unmarshal(reply, retry))
	require.Equal(c.t, uint32(1), retry.ProtocolVersion)
	require.NotNil(c.t, retry.Error)
	require.Equal(c.t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, retry.Error.Code)
	require.Empty(c.t, retry.Error.Issues)
	require.NotNil(c.t, retry.Receipt)
	require.Equal(c.t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, retry.Receipt.Disposition)
	require.Equal(c.t, claimID, retry.Receipt.ClaimId)
	require.Empty(c.t, retry.Receipt.ChangeId)
	require.NotNil(c.t, retry.Receipt.Resolution)
	require.Equal(c.t, operation.OperationID, retry.Receipt.Resolution.OperationId)
	require.False(c.t, retry.Receipt.Resolution.Conflict)
	require.Len(c.t, retry.Receipt.Resolution.Claims, 1)
	require.True(c.t, t2OfflineClaimMatches(retry.Receipt.Resolution.Claims[0], operation))
	afterRetry := t2OfflineRead(c, state, remaining())
	require.True(c.t, proto.Equal(committed, afterRetry), "lost-reply retry must preserve every snapshot field, including the local sequence")
	afterRetryHistory := t2OfflineHistoryRead(c.t, state, remaining())
	require.Equal(c.t, committedHistory, afterRetryHistory)
	afterRetryBytes, err := proto.Marshal(afterRetry)
	require.NoError(c.t, err)
	require.Equal(c.t, 2, c.returnedCalls[method]-initialCalls)
	_ = remaining()
	proof := map[string]any{"protocol": "pinkha-t2-lost-client-reply-v1",
		"scope": "DROPPED_CLIENT_BYTE_REPLY_NOT_PACKET_LOSS_OR_CRASH", "first_reply_decoded": false,
		"fixed_deadline_ms":   60000,
		"discarded_responses": 1, "discarded_response_bytes": dropped.replyBytes, "native_append_attempts": 2,
		"request_sha256": dropped.requestSHA, "retry_request_sha256": retrySHA, "request_bytes": len(original),
		"claim_id": claimID, "committed_change_id": changeID, "commit_observed_before_read": true,
		"history_before": beforeHistory, "history_committed": committedHistory,
		"history_after_read": afterReadHistory, "history_after_retry": afterRetryHistory,
		"retry_disposition": "ALREADY_EXISTS_SAME_PAYLOAD", "retry_change_id": retry.Receipt.ChangeId,
		"snapshot_before_retry_sha256": t2Hash(beforeRetryBytes), "snapshot_after_retry_sha256": t2Hash(afterRetryBytes),
		"local_sequence_before_retry": committed.Snapshot.LocalAppliedSeq, "local_sequence_after_retry": afterRetry.Snapshot.LocalAppliedSeq,
		"crash_after_commit": "NOT_RUN"}
	return claimID, changeID, proof
}

func TestT2NativeLostReplyControls(t *testing.T) {
	t.Run("exact_bytes_forwarded_once_reply_discarded", func(t *testing.T) {
		input := []byte("synthetic-exact-encoded-request")
		var received []byte
		observed := &t2DroppedClientReply{}
		result := t2AwaitClientBytes(context.Background(), t2DropClientReply(func(data []byte) []byte {
			received = slices.Clone(data)
			return []byte("opaque-invalid-protobuf-reply-must-not-be-decoded")
		}, observed), input, nil, nil, time.Second)
		require.Equal(t, input, received)
		require.Empty(t, result.failure)
		require.True(t, result.originalReturned)
		require.Nil(t, result.data)
		require.Equal(t, 1, observed.calls)
		require.True(t, observed.returned)
		require.Equal(t, t2Hash(input), observed.requestSHA)
		require.Greater(t, observed.replyBytes, 0)
	})
	t.Run("panic_is_not_a_dropped_reply", func(t *testing.T) {
		observed := &t2DroppedClientReply{}
		result := t2AwaitClientBytes(context.Background(), t2DropClientReply(func([]byte) []byte {
			panic("synthetic-private-call-failure")
		}, observed), []byte("synthetic-input"), nil, nil, time.Second)
		require.Equal(t, "CALL_PANIC", result.failure)
		require.False(t, observed.returned)
		require.Zero(t, observed.replyBytes)
		require.Nil(t, result.data)
	})
	before := t2OfflineHistory{Changes: map[string]string{"root": "root-hash", "original": "original-hash"},
		Parents: map[string][]string{"original": {"root"}}, Heads: []string{"original"}}
	valid := t2OfflineHistory{Changes: map[string]string{"root": "root-hash", "original": "original-hash", "new": "new-hash"},
		Parents: map[string][]string{"original": {"root"}, "new": {"original"}}, Heads: []string{"new"}}
	t.Run("single_signed_commit_is_observed", func(t *testing.T) {
		change, err := t2LostReplyCommittedChange(before, valid)
		require.NoError(t, err)
		require.Equal(t, "new", change)
	})
	for _, test := range []struct {
		name   string
		change func(*t2OfflineHistory)
	}{
		{"missing_commit_is_rejected", func(h *t2OfflineHistory) { *h = before }},
		{"additional_commit_is_rejected", func(h *t2OfflineHistory) { h.Changes["extra"] = "extra-hash" }},
		{"changed_original_is_rejected", func(h *t2OfflineHistory) { h.Changes["original"] = "changed-hash" }},
		{"wrong_parent_is_rejected", func(h *t2OfflineHistory) { h.Parents["new"] = []string{"root"} }},
		{"changed_original_parent_is_rejected", func(h *t2OfflineHistory) { h.Parents["original"] = []string{"new"} }},
		{"wrong_head_is_rejected", func(h *t2OfflineHistory) { h.Heads = []string{"original"} }},
	} {
		t.Run(test.name, func(t *testing.T) {
			encoded, err := json.Marshal(valid)
			require.NoError(t, err)
			var changed t2OfflineHistory
			require.NoError(t, json.Unmarshal(encoded, &changed))
			test.change(&changed)
			change, err := t2LostReplyCommittedChange(before, changed)
			require.Error(t, err)
			require.Empty(t, change)
		})
	}
}

func t2NativeOfflineRun(c *t2NativeClientCaller, state *t2AccountState, parent string) map[string]any {
	c.t.Helper()
	partitionWait := 60 * time.Second
	if c.role == "creator" {
		partitionWait = 600 * time.Second // B still has its bounded cold bootstrap to finish.
	}
	command := t2OfflineWaitCommand(c, parent, "partition", partitionWait)
	require.Empty(c.t, command.History.Changes)
	if c.role == "recovered" {
		t2OfflineNetwork(c, false)
	} else {
		require.Len(c.t, t2OfflineIPs(c.t), 1)
	}
	t2OfflineReport(c, parent, "partitioned", map[string]any{"network_detach_acknowledged": c.role == "recovered"})
	t2OfflineWaitCommand(c, parent, "write", 60*time.Second)
	author := app.MustComponent[wallet.Wallet](mw.GetApp()).Account().SignKey.GetPublic().Account()
	operations := t2OfflineExpected(state, author, c.role)
	changes := []string{}
	claims := []string{}
	var lostReply map[string]any
	for index, operation := range operations {
		if index == 0 {
			claimID, changeID, proof := t2OfflineAppendLostReply(c, state, operation)
			changes, claims = append(changes, changeID), append(claims, claimID)
			lostReply = proof
			continue
		}
		response := t2OfflineAppend(c, t2OfflineRequest(operation))
		require.Equal(c.t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, response.Error.Code)
		require.Empty(c.t, response.Error.Issues)
		require.Equal(c.t, pb.RpcPinkhaTorahOperations_CREATED, response.Receipt.Disposition)
		expected, _, err := t2OfflineClaim(operation)
		require.NoError(c.t, err)
		require.Equal(c.t, expected, response.Receipt.ClaimId)
		require.NotEmpty(c.t, response.Receipt.ChangeId)
		changes, claims = append(changes, response.Receipt.ChangeId), append(claims, response.Receipt.ClaimId)
	}
	t2OfflineRetryCollision(c, state, operations[0], false)
	local := t2OfflineRead(c, state, 20*time.Second)
	require.Equal(c.t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, local.Error.Code)
	require.NotNil(c.t, local.Snapshot)
	require.Empty(c.t, local.Snapshot.Conflicts)
	require.Empty(c.t, local.Snapshot.PendingObservedClaimIds)
	require.Len(c.t, local.Snapshot.Live, 2)
	actualClaimIDs := []string{}
	for _, claim := range local.Snapshot.Live {
		require.True(c.t, t2OfflineClaimMatches(claim, operations[0]) || t2OfflineClaimMatches(claim, operations[1]))
		actualClaimIDs = append(actualClaimIDs, claim.ClaimId)
	}
	require.ElementsMatch(c.t, []string{claims[0], claims[1]}, actualClaimIDs)
	history := t2OfflineHistoryRead(c.t, state)
	require.Len(c.t, history.Changes, 5)
	require.Equal(c.t, []string{state.ChangeID}, history.Parents[changes[0]])
	require.Equal(c.t, []string{changes[0]}, history.Parents[changes[1]])
	require.Equal(c.t, []string{changes[1]}, history.Parents[changes[2]])
	require.Equal(c.t, []string{changes[2]}, history.Heads)
	require.Equal(c.t, history.Heads, local.Snapshot.VerifiedLocalHeads)
	t2OfflineReport(c, parent, "diverged", map[string]any{"history": history, "created_claim_ids": claims,
		"created_change_ids": changes, "local_snapshot_sha256": t2OfflineSnapshotHash(c.t, local.Snapshot),
		"lost_client_reply":   lostReply,
		"retry_and_collision": "PASS_LOCAL_EXACT_RETRY_AND_REJECTED_DIFFERENT_BYTES", "removed_observed_original": true})
	command = t2OfflineWaitCommand(c, parent, "reconnect", 240*time.Second)
	require.Len(c.t, command.History.Changes, 8)
	require.Len(c.t, command.History.Parents, 7)
	require.Len(c.t, command.History.Heads, 2)
	if c.role == "recovered" {
		t2OfflineNetwork(c, true)
	} else {
		require.Len(c.t, t2OfflineIPs(c.t), 1)
	}
	t2OfflineReport(c, parent, "reconnected", map[string]any{"actual_reconnect_acknowledged": true})
	var converged *pb.RpcPinkhaTorahOperationsReadTargetResponse
	t2NativeClientWait(c.t, "native offline conflict convergence", 180*time.Second, func(remaining time.Duration) bool {
		converged = t2OfflineRead(c, state, min(20*time.Second, remaining))
		ready, err := t2OfflineSnapshotReady(state, author, converged, command.History.Heads)
		require.NoError(c.t, err)
		return ready
	})
	history = t2OfflineHistoryRead(c.t, state)
	require.Equal(c.t, command.History, history, "both original branch histories must arrive through native transport")
	t2OfflineRetryCollision(c, state, operations[1], true)
	semanticHash := t2OfflineSnapshotHash(c.t, converged.Snapshot)
	result := map[string]any{"history": history, "snapshot_sha256_without_local_sequence": semanticHash,
		"local_applied_sequence": converged.Snapshot.LocalAppliedSeq, "live_count": 2, "conflict_count": 1,
		"conflict_variants": 2, "retry_and_collision": "PASS_CONFLICT_VARIANTS_PRESERVED_IDEMPOTENT_REPLAY",
		"concurrent_remove_add_remove": "OBSERVED_ORIGINAL_REMOVED_CONCURRENT_UNIQUE_ADDS_RETAINED",
		"restart":                      "NOT_RUN", "crash_after_commit": "NOT_RUN", "full_t2_acceptance": "NOT_RUN"}
	t2OfflineReport(c, parent, "converged", result)
	return result
}

func TestT2OfflineSnapshotConvergenceControls(t *testing.T) {
	state := &t2AccountState{SpaceID: "synthetic-space", DocumentID: "synthetic-document", BlockID: "synthetic-block",
		ClaimID: strings.Repeat("a", 64) + "/" + strings.Repeat("b", 64)}
	const author = "synthetic-native-author"
	heads := []string{"synthetic-head-a", "synthetic-head-b"}
	claim := func(operation torahops.Operation) *pb.RpcPinkhaTorahOperationsClaim {
		id, digest, err := t2OfflineClaim(operation)
		require.NoError(t, err)
		return &pb.RpcPinkhaTorahOperationsClaim{ClaimId: id, Digest: digest, Operation: &pb.RpcPinkhaTorahOperationsOperation{
			Version: operation.Version, SpaceId: operation.SpaceID, OperationId: operation.OperationID,
			AuthorId: operation.AuthorID, Kind: pb.RpcPinkhaTorahOperations_ADD,
			Target:  &pb.RpcPinkhaTorahOperationsTarget{ObjectId: operation.Target.ObjectID, BlockId: operation.Target.BlockID},
			Source:  &pb.RpcPinkhaTorahOperationsSource{ProviderId: operation.Source.ProviderID, CanonicalRef: operation.Source.CanonicalRef},
			Payload: slices.Clone(operation.Payload), ObservedClaimIds: slices.Clone(operation.Observed)}}
	}
	a, b := t2OfflineExpected(state, author, "creator"), t2OfflineExpected(state, author, "recovered")
	complete := &pb.RpcPinkhaTorahOperationsReadTargetResponse{ProtocolVersion: 1,
		Error: &pb.RpcPinkhaTorahOperationsReadTargetResponseError{},
		Snapshot: &pb.RpcPinkhaTorahOperationsSnapshot{Scope: pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE,
			Live: []*pb.RpcPinkhaTorahOperationsClaim{claim(a[0]), claim(b[0])},
			Conflicts: []*pb.RpcPinkhaTorahOperationsResolution{{OperationId: fmt.Sprintf("%032x", 4), Conflict: true,
				Claims: []*pb.RpcPinkhaTorahOperationsClaim{claim(a[1]), claim(b[1])}}},
			VerifiedLocalHeads: heads, LocalAppliedSeq: 7}}
	t.Run("complete_variants_and_unique_adds_converge", func(t *testing.T) {
		ready, err := t2OfflineSnapshotReady(state, author, complete, heads)
		require.NoError(t, err)
		require.True(t, ready)
	})
	t.Run("local_sequence_is_not_a_cross_client_clock", func(t *testing.T) {
		other := proto.Clone(complete).(*pb.RpcPinkhaTorahOperationsReadTargetResponse)
		other.Snapshot.LocalAppliedSeq = 99
		ready, err := t2OfflineSnapshotReady(state, author, other, heads)
		require.NoError(t, err)
		require.True(t, ready)
		require.Equal(t, t2OfflineSnapshotHash(t, complete.Snapshot), t2OfflineSnapshotHash(t, other.Snapshot))
	})
	t.Run("known_local_prefix_waits_without_convergence", func(t *testing.T) {
		prefix := proto.Clone(complete).(*pb.RpcPinkhaTorahOperationsReadTargetResponse)
		prefix.Snapshot.Live = []*pb.RpcPinkhaTorahOperationsClaim{claim(a[0]), claim(a[1])}
		prefix.Snapshot.Conflicts = nil
		prefix.Snapshot.VerifiedLocalHeads = heads[:1]
		ready, err := t2OfflineSnapshotReady(state, author, prefix, heads)
		require.NoError(t, err)
		require.False(t, ready)
	})
	t.Run("projection_catchup_can_wait", func(t *testing.T) {
		response := &pb.RpcPinkhaTorahOperationsReadTargetResponse{ProtocolVersion: 1,
			Error: &pb.RpcPinkhaTorahOperationsReadTargetResponseError{Code: pb.RpcPinkhaTorahOperationsReadTargetResponseError_PROJECTION_BEHIND,
				Issues: []pb.RpcPinkhaTorahOperationsIssue{pb.RpcPinkhaTorahOperations_ISSUE_PROJECTION_BEHIND}}}
		ready, err := t2OfflineSnapshotReady(state, author, response, heads)
		require.NoError(t, err)
		require.False(t, ready)
	})
	for _, test := range []struct {
		name   string
		change func(*pb.RpcPinkhaTorahOperationsReadTargetResponse)
	}{
		{"known_account_history_cannot_disappear", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot = nil
			r.Error.Code = pb.RpcPinkhaTorahOperationsReadTargetResponseError_HISTORY_UNAVAILABLE
		}},
		{"joined_permission_denial_is_not_retryable", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot = nil
			r.Error.Code = pb.RpcPinkhaTorahOperationsReadTargetResponseError_PROJECTION_BEHIND
			r.Error.Issues = []pb.RpcPinkhaTorahOperationsIssue{pb.RpcPinkhaTorahOperations_ISSUE_PERMISSION_DENIED}
		}},
		{"failed_read_cannot_expose_snapshot", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Error.Code = pb.RpcPinkhaTorahOperationsReadTargetResponseError_PROJECTION_BEHIND
		}},
		{"author_cannot_be_substituted", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot.Live[0].Operation.AuthorId = "different-author"
		}},
		{"opaque_payload_cannot_be_replaced", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot.Conflicts[0].Claims[0].Operation.Payload = []byte("replaced-bytes")
		}},
		{"removed_original_cannot_reappear", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot.Live[0].ClaimId = state.ClaimID
		}},
		{"duplicate_live_claims_are_rejected", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot.Live[1] = proto.Clone(r.Snapshot.Live[0]).(*pb.RpcPinkhaTorahOperationsClaim)
		}},
		{"conflict_must_preserve_both_variants", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot.Conflicts[0].Claims = r.Snapshot.Conflicts[0].Claims[:1]
		}},
		{"duplicate_conflict_variant_is_rejected", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot.Conflicts[0].Claims[1] = proto.Clone(r.Snapshot.Conflicts[0].Claims[0]).(*pb.RpcPinkhaTorahOperationsClaim)
		}},
		{"conflict_has_no_live_winner", func(r *pb.RpcPinkhaTorahOperationsReadTargetResponse) {
			r.Snapshot.Live = append(r.Snapshot.Live, claim(a[1]))
		}},
	} {
		t.Run(test.name, func(t *testing.T) {
			mutated := proto.Clone(complete).(*pb.RpcPinkhaTorahOperationsReadTargetResponse)
			test.change(mutated)
			ready, err := t2OfflineSnapshotReady(state, author, mutated, heads)
			require.Error(t, err)
			require.False(t, ready)
		})
	}
}
