package core

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"net"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pb/cutoverpb"
	pbservice "github.com/anyproto/anytype-heart/pb/service"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
)

func newCutoverGeneratedRPCClient(t *testing.T, mw *Middleware) pbservice.ClientCommandsClient {
	t.Helper()
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	server := grpc.NewServer()
	pbservice.RegisterClientCommandsServer(server, mw)
	done := make(chan error, 1)
	go func() { done <- server.Serve(listener) }()
	t.Cleanup(func() {
		server.Stop()
		_ = listener.Close()
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			t.Error("generated RPC server did not stop")
		}
	})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	connection, err := grpc.DialContext(ctx, listener.Addr().String(), grpc.WithTransportCredentials(insecure.NewCredentials()), grpc.WithBlock())
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, connection.Close()) })
	return pbservice.NewClientCommandsClient(connection)
}

func cutoverWirePlan() cutover.Plan {
	return cutover.Plan{Version: cutover.Version, SpaceID: "space", ObjectID: "object", PropertyKey: "property", ValuePresent: true,
		LegacyValue: []byte("  {\"retained\":\"אבג 👩🏽‍💻\",\"largeInteger\":9007199254740993}  "),
		Facts:       []cutover.Fact{{BlockID: "block", ProviderID: "test", CanonicalRef: "Ref 1", Payload: []byte("{\"unknown\":9007199254740993,\"text\":\"אבג 👩🏽‍💻\"}")}}}
}
func cutoverWireClaim(t *testing.T, plan cutover.Plan, record uint64) cutover.Claim {
	t.Helper()
	id, err := plan.ID()
	require.NoError(t, err)
	claim, _, err := cutover.Encode(cutover.Record{Version: cutover.Version, SpaceID: plan.SpaceID, ObjectID: plan.ObjectID,
		RecordID: fmt.Sprintf("%032x", record), AuthorID: "native-author", Kind: cutover.Begin, PlanID: id, Plan: &plan, SourceHeads: []string{"native-source-head"}})
	require.NoError(t, err)
	return claim
}

func TestPinkhaTorahCutoverWirePreservesFrozenIdentityAndCopies(t *testing.T) {
	plan := cutoverWirePlan()
	planID, err := plan.ID()
	require.NoError(t, err)
	factID, err := plan.Facts[0].ID(plan.SpaceID, plan.ObjectID)
	require.NoError(t, err)
	req := &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: &cutoverpb.PinkhaTorahCutoverScope{ProtocolVersion: 1, SpaceId: plan.SpaceID, ObjectId: plan.ObjectID, PropertyKey: plan.PropertyKey},
		RecordId: fmt.Sprintf("%032x", 1), Kind: cutoverpb.PinkhaTorahCutover_BEGIN, PlanId: planID, Plan: pinkhaCutoverPlanToWire(&plan), SourceHeads: []string{"native-source-head"}}
	encoded, err := proto.Marshal(req)
	require.NoError(t, err)
	var received cutoverpb.PinkhaTorahCutoverRecordRequest
	require.NoError(t, proto.Unmarshal(encoded, &received))
	native, err := pinkhaCutoverRecordFromWire(&received)
	require.NoError(t, err)
	require.Equal(t, plan, *native.Plan)
	actualID, err := native.Plan.ID()
	require.NoError(t, err)
	require.Equal(t, planID, actualID)
	actualFactID, err := native.Plan.Facts[0].ID(plan.SpaceID, plan.ObjectID)
	require.NoError(t, err)
	require.Equal(t, factID, actualFactID)
	// No caller-owned mutable buffer may change the frozen input after mapping.
	received.Plan.LegacyValue[0] = 'X'
	received.Plan.Facts[0].Payload[0] = 'X'
	received.SourceHeads[0] = "different-head"
	received.Scope.SpaceId = "foreign-space"
	require.Equal(t, plan, *native.Plan)
	require.Equal(t, []string{"native-source-head"}, native.SourceHeads)
	require.Equal(t, "space", native.SpaceID)
	operation := &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: req.Scope, PlanId: planID, FactId: factID, OperationId: fmt.Sprintf("%032x", 2),
		Kind: pb.RpcPinkhaTorahOperations_ADD, BlockId: "block", Source: &pb.RpcPinkhaTorahOperationsSource{ProviderId: "test", CanonicalRef: "Ref 1"},
		Payload: bytes.Clone(plan.Facts[0].Payload), ObservedClaimIds: []string{"immutable-observed"}}
	copied, err := pinkhaCutoverOperationFromWire(operation)
	require.NoError(t, err)
	operation.Payload[0] = 'X'
	operation.ObservedClaimIds[0] = "mutated"
	require.Equal(t, plan.Facts[0].Payload, copied.Payload)
	require.Equal(t, []string{"immutable-observed"}, copied.Observed)
}

func TestPinkhaTorahCutoverGeneratedRPCRefusesUnloadedAccountAndVersions(t *testing.T) {
	client := newCutoverGeneratedRPCClient(t, New())
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	scope := &cutoverpb.PinkhaTorahCutoverScope{ProtocolVersion: 1, SpaceId: "space", ObjectId: "object", PropertyKey: "property"}
	source, err := client.PinkhaTorahCutoverSourceRead(ctx, scope)
	require.NoError(t, err)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, source.Error.Code)
	require.Nil(t, source.Snapshot)
	read, err := client.PinkhaTorahCutoverRead(ctx, scope)
	require.NoError(t, err)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, read.Error.Code)
	require.Nil(t, read.Snapshot)
	plan := cutover.Plan{Version: 1, SpaceID: "space", ObjectID: "object", PropertyKey: "property", Facts: []cutover.Fact{}}
	id, err := plan.ID()
	require.NoError(t, err)
	record, err := client.PinkhaTorahCutoverAppend(ctx, &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, RecordId: fmt.Sprintf("%032x", 1), Kind: cutoverpb.PinkhaTorahCutover_BEGIN, PlanId: id, Plan: pinkhaCutoverPlanToWire(&plan), SourceHeads: []string{"source-head"}})
	require.NoError(t, err)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, record.Error.Code)
	require.Nil(t, record.Receipt)
	operation := &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: scope, PlanId: strings.Repeat("1", 64), FactId: strings.Repeat("2", 64), OperationId: fmt.Sprintf("%032x", 2), Kind: pb.RpcPinkhaTorahOperations_ADD}
	imported, err := client.PinkhaTorahCutoverImport(ctx, operation)
	require.NoError(t, err)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, imported.Error.Code)
	require.Nil(t, imported.Receipt)
	operation.FactId = ""
	appended, err := client.PinkhaTorahCutoverAssociationAppend(ctx, operation)
	require.NoError(t, err)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, appended.Error.Code)
	require.Nil(t, appended.Receipt)
	for _, version := range []uint32{0, 2} {
		invalid := *scope
		invalid.ProtocolVersion = version
		rejected, err := client.PinkhaTorahCutoverSourceRead(ctx, &invalid)
		require.NoError(t, err)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_UNSUPPORTED_VERSION, rejected.Error.Code)
		require.Nil(t, rejected.Snapshot)
	}
	malformed, err := client.PinkhaTorahCutoverAppend(ctx, &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, Kind: cutoverpb.PinkhaTorahCutover_KIND_UNSPECIFIED})
	require.NoError(t, err)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_BAD_INPUT, malformed.Error.Code)
	require.Nil(t, malformed.Receipt)
}

func TestPinkhaTorahCutoverWireFailureRetainsReceiptWithoutPrivateHistory(t *testing.T) {
	plan := cutoverWirePlan()
	claim := cutoverWireClaim(t, plan, 1)
	result := torahops.CutoverNativeAppendResult{CutoverAppendResult: torahops.CutoverAppendResult{
		Disposition: torahops.Created, ClaimID: claim.ID, Resolution: torahops.CutoverResolution{RecordID: claim.Record.RecordID, Claims: []cutover.Claim{claim}}}, ChangeID: "signed-change"}
	joined := errors.Join(ErrPinkhaTorahAccountChanged, list.ErrInsufficientPermissions, cutover.ErrIncomplete, errors.New("private-account-secret"))
	wire := pinkhaCutoverAppendToWire(result, joined)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_ACCOUNT_CHANGED, wire.Error.Code)
	require.Equal(t, []cutoverpb.PinkhaTorahCutoverErrorCode{cutoverpb.PinkhaTorahCutoverError_ACCOUNT_CHANGED, cutoverpb.PinkhaTorahCutoverError_PERMISSION_DENIED, cutoverpb.PinkhaTorahCutoverError_INCOMPLETE, cutoverpb.PinkhaTorahCutoverError_UNKNOWN_ERROR}, wire.Error.Issues)
	require.NotNil(t, wire.Receipt)
	require.Equal(t, claim.ID, wire.Receipt.ClaimId)
	require.Equal(t, "signed-change", wire.Receipt.ChangeId)
	require.Nil(t, wire.Receipt.Resolution)
	encoded, err := proto.Marshal(wire)
	require.NoError(t, err)
	require.NotContains(t, string(encoded), "private-account-secret")
	require.NotContains(t, string(encoded), "largeInteger")
	source := pinkhaCutoverSourceToWire(PinkhaTorahCutoverSourceSnapshot{Source: torahops.CutoverLegacyValue{Key: "property", Present: true, Bytes: plan.LegacyValue}, SourceHeads: []string{"head"}}, joined)
	require.Nil(t, source.Snapshot)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_ACCOUNT_CHANGED, source.Error.Code)
	read := pinkhaCutoverReadToWire(torahops.CutoverNativeSnapshot{State: torahops.CutoverState{Status: torahops.CutoverSealed, Plan: &plan}, SourceHeads: []string{"source"}, MetadataHeads: []string{"metadata"}, OperationHeads: []string{"original"}}, joined)
	require.Nil(t, read.Snapshot)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_ACCOUNT_CHANGED, read.Error.Code)
	require.Equal(t, wire.Error.Issues, source.Error.Issues)
	require.Equal(t, wire.Error.Issues, read.Error.Issues)
	// Import and AssociationAppend share this exact result mapper. Their real
	// generated endpoint dispatch is separately exercised with a native account.
	// The native result must survive every joined post-authority failure, while
	// its private resolution is never released or rewritten as retry permission.
	for _, disposition := range []torahops.Disposition{torahops.Created, torahops.AlreadyExistsSamePayload, torahops.CollisionDifferentPayload} {
		t.Run(string(disposition), func(t *testing.T) {
			operation := torahops.NativeAppendResult{AppendResult: torahops.AppendResult{
				Disposition: disposition, ClaimID: claim.ID, Resolution: torahops.Resolution{OperationID: "private-operation-resolution"}}}
			if disposition == torahops.Created {
				operation.ChangeID = "signed-v1-change"
			}
			before := operation
			response := pinkhaCutoverOperationToWire(operation, joined)
			require.Equal(t, before, operation)
			require.Equal(t, cutoverpb.PinkhaTorahCutoverError_ACCOUNT_CHANGED, response.Error.Code)
			require.Contains(t, response.Error.Issues, cutoverpb.PinkhaTorahCutoverError_PERMISSION_DENIED)
			require.Contains(t, response.Error.Issues, cutoverpb.PinkhaTorahCutoverError_INCOMPLETE)
			require.Contains(t, response.Error.Issues, cutoverpb.PinkhaTorahCutoverError_UNKNOWN_ERROR)
			require.NotNil(t, response.Receipt)
			require.Equal(t, claim.ID, response.Receipt.ClaimId)
			require.Equal(t, operation.ChangeID, response.Receipt.ChangeId)
			require.Nil(t, response.Receipt.Resolution)
			if disposition == torahops.Created {
				require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, response.Receipt.Disposition)
			} else if disposition == torahops.AlreadyExistsSamePayload {
				require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, response.Receipt.Disposition)
			} else {
				require.Equal(t, pb.RpcPinkhaTorahOperations_COLLISION_DIFFERENT_PAYLOAD, response.Receipt.Disposition)
				require.Contains(t, response.Error.Issues, cutoverpb.PinkhaTorahCutoverError_COLLISION)
			}
			bytes, encodeErr := proto.Marshal(response)
			require.NoError(t, encodeErr)
			require.NotContains(t, string(bytes), "private-account-secret")
			require.NotContains(t, string(bytes), "private-operation-resolution")
		})
	}
}

func TestPinkhaTorahCutoverWireBoundRefusesWholeSnapshot(t *testing.T) {
	plan := cutoverWirePlan()
	plan.LegacyValue = []byte("\"" + strings.Repeat("x", cutover.MaxLegacyBytes-2) + "\"")
	first, second := cutoverWireClaim(t, plan, 1), cutoverWireClaim(t, plan, 2)
	native := torahops.CutoverNativeSnapshot{State: torahops.CutoverState{Status: torahops.CutoverPending, Plan: &plan},
		Source:      torahops.CutoverLegacyValue{Key: plan.PropertyKey, Present: true, Bytes: plan.LegacyValue},
		SourceHeads: []string{"source"}, MetadataHeads: []string{"metadata"}, OperationHeads: []string{"original"},
		MetadataHistory: torahops.CutoverHistory{Claims: []cutover.Claim{first, second}}}
	response := pinkhaCutoverReadToWire(native, nil)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_READ_LIMIT, response.Error.Code)
	require.Nil(t, response.Snapshot, "a bound is never a truncated successful local history")
	committed := torahops.CutoverNativeAppendResult{CutoverAppendResult: torahops.CutoverAppendResult{Disposition: torahops.Created, ClaimID: first.ID,
		Resolution: torahops.CutoverResolution{RecordID: first.Record.RecordID, Claims: []cutover.Claim{first, first, first, first, first}}}, ChangeID: "signed-change"}
	receipt := pinkhaCutoverAppendToWire(committed, nil)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_READ_LIMIT, receipt.Error.Code)
	require.NotNil(t, receipt.Receipt)
	require.Equal(t, first.ID, receipt.Receipt.ClaimId)
	require.Equal(t, "signed-change", receipt.Receipt.ChangeId)
	require.Nil(t, receipt.Receipt.Resolution)
}
