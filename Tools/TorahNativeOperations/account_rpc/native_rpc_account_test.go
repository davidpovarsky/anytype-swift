package service

import (
	"context"
	"testing"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

// Compiled only into the explicitly generated-RPC account binary. These helpers
// call the generated gomobile byte entry points with real protobuf bytes; they
// never substitute a client handler or call the typed native method directly.
var t2RPCAccountSchemaSHA = "UNSET"

func t2NativeRPCRequests(state *t2AccountState) (*pb.RpcPinkhaTorahOperationsAppendRequest, *pb.RpcPinkhaTorahOperationsReadTargetRequest) {
	appendRequest := &pb.RpcPinkhaTorahOperationsAppendRequest{
		ProtocolVersion: 1, SpaceId: state.SpaceID, OperationId: state.OperationID,
		Kind:    pb.RpcPinkhaTorahOperations_ADD,
		Target:  &pb.RpcPinkhaTorahOperationsTarget{ObjectId: state.DocumentID, BlockId: state.BlockID},
		Source:  &pb.RpcPinkhaTorahOperationsSource{ProviderId: "fixture", CanonicalRef: "fixture:t2-account:1"},
		Payload: []byte(t2PrivatePayload),
	}
	return appendRequest, &pb.RpcPinkhaTorahOperationsReadTargetRequest{
		ProtocolVersion: 1, SpaceId: state.SpaceID, Target: appendRequest.Target, Limit: 100,
	}
}

func t2WireAppend(t *testing.T, request *pb.RpcPinkhaTorahOperationsAppendRequest) *pb.RpcPinkhaTorahOperationsAppendResponse {
	t.Helper()
	raw, err := proto.Marshal(request)
	require.NoError(t, err)
	response := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	require.NoError(t, proto.Unmarshal(PinkhaTorahOperationsAppend(raw), response))
	require.Equal(t, uint32(1), response.ProtocolVersion)
	require.NotNil(t, response.Error)
	return response
}

func t2WireRead(t *testing.T, request *pb.RpcPinkhaTorahOperationsReadTargetRequest) *pb.RpcPinkhaTorahOperationsReadTargetResponse {
	t.Helper()
	raw, err := proto.Marshal(request)
	require.NoError(t, err)
	response := &pb.RpcPinkhaTorahOperationsReadTargetResponse{}
	require.NoError(t, proto.Unmarshal(PinkhaTorahOperationsReadTarget(raw), response))
	require.Equal(t, uint32(1), response.ProtocolVersion)
	require.NotNil(t, response.Error)
	return response
}

func t2CreateNativeRPCOperation(t *testing.T, ctx context.Context, state *t2AccountState) {
	t.Helper()
	spc := t2Space(t, state.SpaceID)
	absent := func() {
		exists, err := spc.Storage().HasTree(ctx, state.RootID)
		require.NoError(t, err)
		require.False(t, exists, "each rejected/read wire call must leave the private root absent")
	}
	absent()
	appendRequest, readRequest := t2NativeRPCRequests(state)
	read := t2WireRead(t, readRequest)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_HISTORY_UNAVAILABLE, read.Error.Code)
	require.Nil(t, read.Snapshot)
	absent()

	for _, version := range []uint32{0, 2} {
		request := proto.Clone(appendRequest).(*pb.RpcPinkhaTorahOperationsAppendRequest)
		request.ProtocolVersion = version
		result := t2WireAppend(t, request)
		require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_UNSUPPORTED_VERSION, result.Error.Code)
		require.Nil(t, result.Receipt)
		absent()
	}
	for _, kind := range []pb.RpcPinkhaTorahOperationsKind{pb.RpcPinkhaTorahOperations_KIND_UNSPECIFIED, 99} {
		request := proto.Clone(appendRequest).(*pb.RpcPinkhaTorahOperationsAppendRequest)
		request.Kind = kind
		result := t2WireAppend(t, request)
		require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_BAD_INPUT, result.Error.Code)
		require.Nil(t, result.Receipt)
		absent()
	}
	missing := proto.Clone(appendRequest).(*pb.RpcPinkhaTorahOperationsAppendRequest)
	missing.Target.BlockId = "fixture-missing-block"
	result := t2WireAppend(t, missing)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_TARGET_UNAVAILABLE, result.Error.Code)
	require.Nil(t, result.Receipt)
	absent()
	empty := proto.Clone(appendRequest).(*pb.RpcPinkhaTorahOperationsAppendRequest)
	empty.Payload = nil
	result = t2WireAppend(t, empty)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_BAD_INPUT, result.Error.Code)
	require.Nil(t, result.Receipt)
	absent()

	created := t2WireAppend(t, appendRequest)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, created.Error.Code)
	require.Empty(t, created.Error.Issues)
	require.NotNil(t, created.Receipt)
	require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, created.Receipt.Disposition)
	require.NotEmpty(t, created.Receipt.ClaimId)
	require.NotEmpty(t, created.Receipt.ChangeId)
	require.NotNil(t, created.Receipt.Resolution)
	require.False(t, created.Receipt.Resolution.Conflict)
	require.Len(t, created.Receipt.Resolution.Claims, 1)
	require.Equal(t, created.Receipt.ClaimId, created.Receipt.Resolution.Claims[0].ClaimId)
	state.ClaimID, state.ChangeID = created.Receipt.ClaimId, created.Receipt.ChangeId
	exists, err := spc.Storage().HasTree(ctx, state.RootID)
	require.NoError(t, err)
	require.True(t, exists)
}

func t2CheckNativeRPCOperation(t *testing.T, state *t2AccountState, create bool) map[string]any {
	t.Helper()
	require.NotEqual(t, "UNSET", t2RPCAccountSchemaSHA)
	appendRequest, readRequest := t2NativeRPCRequests(state)
	for _, version := range []uint32{0, 2} {
		invalid := proto.Clone(readRequest).(*pb.RpcPinkhaTorahOperationsReadTargetRequest)
		invalid.ProtocolVersion = version
		denied := t2WireRead(t, invalid)
		require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_UNSUPPORTED_VERSION, denied.Error.Code)
		require.Nil(t, denied.Snapshot)
	}
	invalid := proto.Clone(readRequest).(*pb.RpcPinkhaTorahOperationsReadTargetRequest)
	invalid.Limit = 0
	denied := t2WireRead(t, invalid)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_BAD_INPUT, denied.Error.Code)
	require.Nil(t, denied.Snapshot)

	// Reading precedes any replay through this endpoint. The existing signed
	// history must already be present after account reopen and legacy use.
	before := t2WireRead(t, readRequest)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, before.Error.Code)
	require.Empty(t, before.Error.Issues)
	require.NotNil(t, before.Snapshot)
	require.Equal(t, pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE, before.Snapshot.Scope)
	require.Equal(t, []string{state.ChangeID}, before.Snapshot.VerifiedLocalHeads)
	require.Len(t, before.Snapshot.Live, 1)
	require.Empty(t, before.Snapshot.Conflicts)
	require.Empty(t, before.Snapshot.PendingObservedClaimIds)
	claim := before.Snapshot.Live[0]
	require.Equal(t, state.ClaimID, claim.ClaimId)
	require.NotNil(t, claim.Operation)
	op := claim.Operation
	require.NotNil(t, op.Target)
	require.NotNil(t, op.Source)
	require.Equal(t, pb.RpcPinkhaTorahOperations_ADD, op.Kind)
	canonical, err := (torahops.Operation{Version: op.Version, SpaceID: op.SpaceId, OperationID: op.OperationId,
		AuthorID: op.AuthorId, Kind: torahops.Add,
		Target:  torahops.Target{ObjectID: op.Target.ObjectId, BlockID: op.Target.BlockId},
		Source:  torahops.Source{ProviderID: op.Source.ProviderId, CanonicalRef: op.Source.CanonicalRef},
		Payload: op.Payload, Observed: op.ObservedClaimIds}).CanonicalBytes()
	require.NoError(t, err)
	require.Equal(t, state.OperationSHA256, t2Hash(canonical), "wire output must retain the actual account-derived author and exact payload")

	retried := t2WireAppend(t, appendRequest)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, retried.Error.Code)
	require.Empty(t, retried.Error.Issues)
	require.NotNil(t, retried.Receipt)
	require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, retried.Receipt.Disposition)
	require.Equal(t, state.ClaimID, retried.Receipt.ClaimId)
	require.Empty(t, retried.Receipt.ChangeId)
	require.NotNil(t, retried.Receipt.Resolution)
	require.Len(t, retried.Receipt.Resolution.Claims, 1)
	require.True(t, proto.Equal(claim, retried.Receipt.Resolution.Claims[0]))

	different := proto.Clone(appendRequest).(*pb.RpcPinkhaTorahOperationsAppendRequest)
	different.Payload = []byte("different wire bytes must not replace the committed claim")
	collision := t2WireAppend(t, different)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_COLLISION, collision.Error.Code)
	require.Equal(t, []pb.RpcPinkhaTorahOperationsIssue{pb.RpcPinkhaTorahOperations_ISSUE_COLLISION}, collision.Error.Issues)
	require.NotNil(t, collision.Receipt, "non-NULL wire error must not discard the native receipt")
	require.Equal(t, pb.RpcPinkhaTorahOperations_COLLISION_DIFFERENT_PAYLOAD, collision.Receipt.Disposition)
	require.NotEmpty(t, collision.Receipt.ClaimId)
	require.Empty(t, collision.Receipt.ChangeId)
	require.NotNil(t, collision.Receipt.Resolution)
	require.Len(t, collision.Receipt.Resolution.Claims, 1)
	require.True(t, proto.Equal(claim, collision.Receipt.Resolution.Claims[0]))
	after := t2WireRead(t, readRequest)
	require.True(t, proto.Equal(before, after), "wire retry/collision must preserve signed heads, claims and local watermark")

	creation := "EXISTING_HISTORY_REOPENED_THROUGH_GENERATED_RPC"
	if create {
		creation = "REJECTED_WIRE_CALLS_NO_ROOT_THEN_VALID_WIRE_APPEND_CREATED_ROOT"
	}
	return map[string]any{"scope": "ACCOUNT_SCOPED_GENERATED_BYTE_RPC_NOT_TWO_CLIENTS",
		"schema_inventory_sha256": t2RPCAccountSchemaSHA,
		"creation":                creation, "read": "EXACT_PERSISTED_CLAIM_NATIVE_AUTHOR",
		"read_guards": "VERSION_AND_LIMIT_REJECTED", "retry": "ALREADY_EXISTS_SAME_PAYLOAD",
		"collision": "NON_NULL_COLLISION_WITH_COMPLETE_RECEIPT", "snapshot_scope": "LOCAL_VERIFIED_TREE",
		"after_stop": "NOT_RUN"}
}

func t2AssertNativeRPCUnavailable(t *testing.T, state *t2AccountState, targetRemoved bool) {
	t.Helper()
	appendRequest, readRequest := t2NativeRPCRequests(state)
	read, write := t2WireRead(t, readRequest), t2WireAppend(t, appendRequest)
	require.NotEqual(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, read.Error.Code)
	require.NotEqual(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, write.Error.Code)
	if targetRemoved {
		require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_TARGET_UNAVAILABLE, read.Error.Code)
		require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_TARGET_UNAVAILABLE, write.Error.Code)
	}
	require.Nil(t, read.Snapshot)
	require.Nil(t, write.Receipt)
}

func t2RecordStoppedRPC(t *testing.T, state *t2AccountState, observation map[string]any) {
	t.Helper()
	appendRequest, readRequest := t2NativeRPCRequests(state)
	read, write := t2WireRead(t, readRequest), t2WireAppend(t, appendRequest)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NOT_LOGGED_IN, read.Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NOT_LOGGED_IN, write.Error.Code)
	require.Nil(t, read.Snapshot)
	require.Nil(t, write.Receipt)
	boundary, ok := observation["wire_boundary"].(map[string]any)
	require.True(t, ok)
	boundary["after_stop"] = "GENERATED_READ_AND_APPEND_NOT_LOGGED_IN"
}
