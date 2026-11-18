package core

import (
	"context"
	"errors"
	"fmt"
	"reflect"
	"strings"
	"testing"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

func t2WireAppendRoundTrip(t *testing.T, in *pb.RpcPinkhaTorahOperationsAppendResponse) *pb.RpcPinkhaTorahOperationsAppendResponse {
	t.Helper()
	raw, err := in.Marshal()
	require.NoError(t, err)
	var out pb.RpcPinkhaTorahOperationsAppendResponse
	require.NoError(t, out.Unmarshal(raw))
	require.True(t, proto.Equal(in, &out))
	return &out
}

func t2WireReadRoundTrip(t *testing.T, in *pb.RpcPinkhaTorahOperationsReadTargetResponse) *pb.RpcPinkhaTorahOperationsReadTargetResponse {
	t.Helper()
	raw, err := in.Marshal()
	require.NoError(t, err)
	var out pb.RpcPinkhaTorahOperationsReadTargetResponse
	require.NoError(t, out.Unmarshal(raw))
	require.True(t, proto.Equal(in, &out))
	return &out
}

func t2WireClaim(id, payload string) torahops.Claim {
	return torahops.Claim{ID: id, Digest: "fixture-digest-" + id,
		Operation: torahops.Operation{Version: 1, SpaceID: "fixture-space", OperationID: "00000000000000000000000000000001",
			AuthorID: "native-derived-author", Kind: torahops.Add,
			Target: torahops.Target{ObjectID: "fixture-target", BlockID: "fixture-block"},
			Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte(payload)}}
}

func TestPinkhaTorahRPCSchemaAndOpaqueRequestRoundTrip(t *testing.T) {
	fields := func(value any) []string {
		var names []string
		typ := reflect.TypeOf(value)
		for i := 0; i < typ.NumField(); i++ {
			f := typ.Field(i)
			if f.Tag.Get("protobuf") != "" {
				names = append(names, f.Name)
			}
		}
		return names
	}
	// The actual generated request schema cannot carry client-supplied native
	// author/root/key/ACL authority, including via a nested returned Operation.
	require.Equal(t, []string{"ProtocolVersion", "SpaceId", "OperationId", "Kind", "Target", "Source", "Payload", "ObservedClaimIds"}, fields(pb.RpcPinkhaTorahOperationsAppendRequest{}))
	require.Equal(t, []string{"ProtocolVersion", "SpaceId", "Target", "Limit"}, fields(pb.RpcPinkhaTorahOperationsReadTargetRequest{}))
	in := &pb.RpcPinkhaTorahOperationsAppendRequest{ProtocolVersion: 1, SpaceId: "fixture-space", OperationId: "00000000000000000000000000000001",
		Kind: pb.RpcPinkhaTorahOperations_REPLACE, Target: &pb.RpcPinkhaTorahOperationsTarget{ObjectId: "fixture-target", BlockId: "fixture-block"},
		Source: &pb.RpcPinkhaTorahOperationsSource{ProviderId: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte{0, 255, 0xc3, 0xa9}, ObservedClaimIds: []string{"claim-B", "claim-A"}}
	raw, err := in.Marshal()
	require.NoError(t, err)
	var decoded pb.RpcPinkhaTorahOperationsAppendRequest
	require.NoError(t, decoded.Unmarshal(raw))
	require.Equal(t, "anytype.Rpc.Pinkha.TorahOperations.Append.Request", proto.MessageName(&decoded))
	native, err := pinkhaTorahAppendFromWire(&decoded)
	require.NoError(t, err)
	require.Equal(t, in.Payload, native.Payload)
	require.Equal(t, in.ObservedClaimIds, native.Observed)
	require.Equal(t, torahops.Replace, native.Kind)
	decoded.Payload[0] = 7
	decoded.ObservedClaimIds[0] = "changed"
	require.Equal(t, byte(0), native.Payload[0])
	require.Equal(t, "claim-B", native.Observed[0])
}

func TestPinkhaTorahRPCRejectsUnknownContractBeforeNativeAuthority(t *testing.T) {
	// A nil Middleware makes accidental account/Space/root access fail the test.
	var mw *Middleware
	for _, version := range []uint32{0, 2, ^uint32(0)} {
		t.Run(fmt.Sprint("version-", version), func(t *testing.T) {
			a := t2WireAppendRoundTrip(t, mw.PinkhaTorahOperationsAppend(context.Background(), &pb.RpcPinkhaTorahOperationsAppendRequest{ProtocolVersion: version}))
			r := t2WireReadRoundTrip(t, mw.PinkhaTorahOperationsReadTarget(context.Background(), &pb.RpcPinkhaTorahOperationsReadTargetRequest{ProtocolVersion: version}))
			require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_UNSUPPORTED_VERSION, a.Error.Code)
			require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_UNSUPPORTED_VERSION, r.Error.Code)
			require.Nil(t, a.Receipt)
			require.Nil(t, r.Snapshot)
		})
	}
	for _, kind := range []pb.RpcPinkhaTorahOperationsKind{0, 99, -1} {
		t.Run(fmt.Sprint("kind-", kind), func(t *testing.T) {
			a := mw.PinkhaTorahOperationsAppend(context.Background(), &pb.RpcPinkhaTorahOperationsAppendRequest{ProtocolVersion: 1, Kind: kind, Target: &pb.RpcPinkhaTorahOperationsTarget{ObjectId: "fixture-target"}})
			require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_BAD_INPUT, a.Error.Code)
			require.Nil(t, a.Receipt)
		})
	}
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_BAD_INPUT, mw.PinkhaTorahOperationsAppend(context.Background(), nil).Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_BAD_INPUT, mw.PinkhaTorahOperationsReadTarget(context.Background(), nil).Error.Code)
	for _, limit := range []uint32{0, 10001, ^uint32(0)} {
		req := &pb.RpcPinkhaTorahOperationsReadTargetRequest{ProtocolVersion: 1, Target: &pb.RpcPinkhaTorahOperationsTarget{ObjectId: "fixture-target"}, Limit: limit}
		require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_BAD_INPUT, mw.PinkhaTorahOperationsReadTarget(context.Background(), req).Error.Code)
	}
}

func TestPinkhaTorahRPCPreservesCommittedReceiptAndJoinedIssues(t *testing.T) {
	claim := t2WireClaim("claim-one", "private payload must not become an error label")
	result := torahops.NativeAppendResult{AppendResult: torahops.AppendResult{Disposition: torahops.Created, ClaimID: claim.ID,
		Resolution: torahops.Resolution{OperationID: claim.Operation.OperationID, Claims: []torahops.Claim{claim}}}, ChangeID: "signed-native-change"}
	completed := t2WireAppendRoundTrip(t, pinkhaTorahAppendToWire(result, nil))
	require.Equal(t, "native-derived-author", completed.Receipt.Resolution.Claims[0].Operation.AuthorId)
	err := errors.Join(fmt.Errorf("sensitive native path: %w", torahops.ErrProjectionBehind), ErrPinkhaTorahAccountChanged, errors.New("private-payload-or-key-sentinel"))
	out := t2WireAppendRoundTrip(t, pinkhaTorahAppendToWire(result, err))
	require.Equal(t, uint32(1), out.ProtocolVersion)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_ACCOUNT_CHANGED, out.Error.Code)
	require.Equal(t, []pb.RpcPinkhaTorahOperationsIssue{pb.RpcPinkhaTorahOperations_ISSUE_ACCOUNT_CHANGED, pb.RpcPinkhaTorahOperations_ISSUE_PROJECTION_BEHIND, pb.RpcPinkhaTorahOperations_ISSUE_UNKNOWN_INTERNAL}, out.Error.Issues)
	require.Equal(t, "signed-native-change", out.Receipt.ChangeId)
	require.Equal(t, claim.ID, out.Receipt.ClaimId)
	require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, out.Receipt.Disposition)
	require.Nil(t, out.Receipt.Resolution, "partial receipt must not release cached payload after failed native authority/lifecycle fence")
	require.NotContains(t, out.Error.Description, "private")
	require.NotContains(t, out.Error.Description, "sensitive")
	claim.Operation.Payload[0] = 'X'
	require.Equal(t, byte('p'), completed.Receipt.Resolution.Claims[0].Operation.Payload[0])
}

func TestPinkhaTorahRPCSeparatesRetryCollisionAndRemoteVariants(t *testing.T) {
	a, b := t2WireClaim("variant-A", "A"), t2WireClaim("variant-B", "B")
	resolution := torahops.Resolution{OperationID: a.Operation.OperationID, Conflict: true, Claims: []torahops.Claim{a, b}}
	for _, disposition := range []torahops.Disposition{torahops.AlreadyExistsSamePayload, torahops.CollisionDifferentPayload} {
		t.Run(string(disposition), func(t *testing.T) {
			out := t2WireAppendRoundTrip(t, pinkhaTorahAppendToWire(torahops.NativeAppendResult{AppendResult: torahops.AppendResult{Disposition: disposition, ClaimID: a.ID, Resolution: resolution}}, nil))
			require.Empty(t, out.Receipt.ChangeId)
			require.True(t, out.Receipt.Resolution.Conflict)
			require.Len(t, out.Receipt.Resolution.Claims, 2)
			require.Equal(t, []byte("A"), out.Receipt.Resolution.Claims[0].Operation.Payload)
			require.Equal(t, []byte("B"), out.Receipt.Resolution.Claims[1].Operation.Payload)
			if disposition == torahops.AlreadyExistsSamePayload {
				require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, out.Error.Code)
				require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, out.Receipt.Disposition)
			} else {
				require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_COLLISION, out.Error.Code)
				require.Equal(t, pb.RpcPinkhaTorahOperations_COLLISION_DIFFERENT_PAYLOAD, out.Receipt.Disposition)
			}
		})
	}
	snapshot := torahops.NativeSnapshot{Projection: torahops.Projection{Live: []torahops.Claim{a}, Conflicts: []torahops.Resolution{resolution}, PendingObserved: []string{"unreceived-claim"}}, Heads: []string{"head-B", "head-A"}, AppliedSeq: 27}
	read := t2WireReadRoundTrip(t, pinkhaTorahReadToWire(snapshot, nil))
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, read.Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE, read.Snapshot.Scope)
	require.Equal(t, snapshot.Heads, read.Snapshot.VerifiedLocalHeads)
	require.Equal(t, uint64(27), read.Snapshot.LocalAppliedSeq)
	require.Len(t, read.Snapshot.Conflicts[0].Claims, 2)
	for _, err := range []error{ErrPinkhaTorahAccountChanged, torahops.ErrProjectionBehind, context.Canceled, errors.New("unknown")} {
		failed := t2WireReadRoundTrip(t, pinkhaTorahReadToWire(snapshot, err))
		require.NotEqual(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, failed.Error.Code)
		require.Nil(t, failed.Snapshot)
	}
}

type t2EmptyJoinedError struct{}

func (t2EmptyJoinedError) Error() string   { return "unknown native error" }
func (t2EmptyJoinedError) Unwrap() []error { return nil }

func TestPinkhaTorahRPCBoundsNeverTruncateSuccessfulHistory(t *testing.T) {
	var claims []torahops.Claim
	for i := 0; i < 70; i++ {
		claims = append(claims, t2WireClaim(fmt.Sprint("claim-", i), strings.Repeat("x", torahops.MaxPayloadBytes)))
	}
	result := torahops.NativeAppendResult{AppendResult: torahops.AppendResult{Disposition: torahops.Created, ClaimID: "durable-claim",
		Resolution: torahops.Resolution{OperationID: "operation", Claims: claims}}, ChangeID: "durable-change"}
	appendReply := t2WireAppendRoundTrip(t, pinkhaTorahAppendToWire(result, nil))
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_READ_LIMIT, appendReply.Error.Code)
	require.Equal(t, "durable-claim", appendReply.Receipt.ClaimId)
	require.Equal(t, "durable-change", appendReply.Receipt.ChangeId)
	require.Nil(t, appendReply.Receipt.Resolution)
	read := t2WireReadRoundTrip(t, pinkhaTorahReadToWire(torahops.NativeSnapshot{Projection: torahops.Projection{Live: claims}, Heads: []string{"head"}}, nil))
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_READ_LIMIT, read.Error.Code)
	require.Nil(t, read.Snapshot)
	for _, err := range []error{t2EmptyJoinedError{}, errors.New("unknown")} {
		reply := pinkhaTorahAppendToWire(torahops.NativeAppendResult{}, err)
		require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_UNKNOWN_ERROR, reply.Error.Code)
		require.Nil(t, reply.Receipt)
	}
	invalid := pinkhaTorahAppendToWire(torahops.NativeAppendResult{AppendResult: torahops.AppendResult{Disposition: torahops.Created, ClaimID: "partial-receipt"}}, nil)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_UNKNOWN_ERROR, invalid.Error.Code)
	require.Equal(t, "partial-receipt", invalid.Receipt.ClaimId)
	require.NotEqual(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, pinkhaTorahReadToWire(torahops.NativeSnapshot{}, nil).Error.Code)
}

func TestPinkhaTorahRPCDoesNotExpandExternalScope(t *testing.T) {
	for _, method := range []string{"PinkhaTorahOperationsAppend", "PinkhaTorahOperationsReadTarget"} {
		_, anonymous := noAuthMethods[method]
		_, limited := limitedScopeMethods[method]
		require.False(t, anonymous)
		require.False(t, limited)
		for _, scope := range []model.AccountAuthLocalApiScope{model.AccountAuth_Limited, model.AccountAuth_JsonAPI, 99} {
			require.Error(t, checkScopeAllowsMethod(scope, "/anytype.ClientCommands/"+method))
		}
		require.NoError(t, checkScopeAllowsMethod(model.AccountAuth_Full, "/anytype.ClientCommands/"+method))
	}
}
