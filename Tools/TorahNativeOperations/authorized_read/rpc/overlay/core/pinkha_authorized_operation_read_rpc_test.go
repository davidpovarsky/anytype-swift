package core

import (
	"bytes"
	"context"
	"errors"
	"reflect"
	"slices"
	"strings"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/stretchr/testify/require"
)

// Mapping fixture, not a native-signature or account proof. Signed history,
// current ACL and target leases are exercised by the separate native slice.
func authorizedRPCSnapshot(t *testing.T) torahops.AuthorizedOperationSnapshot {
	t.Helper()
	op := torahops.Operation{Version: 1, SpaceID: "fixture-space", OperationID: strings.Repeat("1", 32),
		AuthorID: "native-author", Kind: torahops.Add, Target: torahops.Target{ObjectID: "live-document", BlockID: "old-block"},
		Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte{0xff, 0x00, 'x'}}
	canonical, err := op.CanonicalBytes()
	require.NoError(t, err)
	id, _, err := torahops.EncodeClaim(op)
	require.NoError(t, err)
	return torahops.AuthorizedOperationSnapshot{Contract: torahops.AuthorizedOperationReadContract,
		AccountID: "native-reader", SpaceID: op.SpaceID, OperationID: op.OperationID, Outcome: torahops.OperationFound,
		Complete: true, NativeSnapshotToken: strings.Repeat("a", 64), Variants: []torahops.AuthorizedOperationVariant{{
			ClaimID: id, OperationID: op.OperationID, SpaceID: op.SpaceID, AuthorID: op.AuthorID, Target: op.Target,
			CanonicalBytes: canonical, Reachability: torahops.OperationUnreachableBlock,
			Provenance: []torahops.AuthorizedOperationProvenance{{Creator: op.AuthorID, NativeChangeID: "native-change", NativeACLHeadID: "native-acl-head"}},
		}}}
}

func TestPinkhaAuthorizedOperationRPCSchemaAndExactOpaqueRoundTrip(t *testing.T) {
	requestType := reflect.TypeOf(pb.PinkhaTorahAuthorizedOperationReadRequest{})
	fields := []string{}
	for i := 0; i < requestType.NumField(); i++ {
		field := requestType.Field(i)
		if field.Tag.Get("protobuf") != "" {
			fields = append(fields, field.Name)
		}
	}
	require.Equal(t, []string{"ProtocolVersion", "SpaceId", "OperationId"}, fields, "caller cannot assert author, targets, ACL or root")
	value := authorizedRPCSnapshot(t)
	reply := pinkhaAuthorizedOperationReadToWire(value, nil)
	require.Equal(t, int32(0), int32(reply.Error.Code))
	require.NotNil(t, reply.Snapshot)
	raw, err := reply.Marshal()
	require.NoError(t, err)
	var decoded pb.PinkhaTorahAuthorizedOperationReadResponse
	require.NoError(t, decoded.Unmarshal(raw))
	require.Equal(t, reply, &decoded)
	require.Equal(t, value.Variants[0].CanonicalBytes, decoded.Snapshot.Variants[0].CanonicalBytes)
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_UNREACHABLE_BLOCK, decoded.Snapshot.Variants[0].Reachability)
	require.True(t, decoded.Snapshot.Complete)
	value.Variants = nil
	value.Outcome = torahops.OperationAbsentInVerifiedLocalSnapshot
	absent := pinkhaAuthorizedOperationReadToWire(value, nil)
	require.Equal(t, int32(0), int32(absent.Error.Code))
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_ABSENT_IN_VERIFIED_LOCAL_SNAPSHOT, absent.Snapshot.Outcome)
	require.Empty(t, absent.Snapshot.Variants)
}

func TestPinkhaAuthorizedOperationRPCFailedFencesReleaseNoPayload(t *testing.T) {
	for _, item := range []struct {
		name string
		err  error
		code int32
	}{
		{"account-changed", ErrPinkhaTorahAccountChanged, 6},
		{"denied", list.ErrInsufficientPermissions, 4},
		{"missing-key", list.ErrNoReadKey, 4},
		{"no-account", ErrNotLoggedIn, 5},
		{"unsupported-version", torahops.ErrUnsupportedVersion, 3},
		{"invalid", torahops.ErrInvalid, 2},
		{"target-unavailable", torahops.ErrOperationTargetUnavailable, 7},
		{"history-unavailable", ErrPinkhaTorahHistoryUnavailable, 8},
		{"snapshot-changed", torahops.ErrOperationSnapshotChanged, 9},
		{"projection-behind", torahops.ErrProjectionBehind, 10},
		{"read-limit", torahops.ErrReadLimit, 11},
		{"cancelled", context.Canceled, 12},
		{"deadline", context.DeadlineExceeded, 13},
	} {
		t.Run(item.name, func(t *testing.T) {
			value := authorizedRPCSnapshot(t)
			reply := pinkhaAuthorizedOperationReadToWire(value, errors.Join(item.err, errors.New("private secret identifier")))
			require.Equal(t, item.code, int32(reply.Error.Code))
			require.Nil(t, reply.Snapshot)
			raw, err := reply.Marshal()
			require.NoError(t, err)
			require.False(t, bytes.Contains(raw, []byte("private secret")))
			require.False(t, bytes.Contains(raw, []byte(value.Variants[0].ClaimID)))
		})
	}
}

func TestPinkhaAuthorizedOperationRPCBoundsAndInvalidShape(t *testing.T) {
	for _, scenario := range []string{"variant-count", "encoded-response", "incomplete", "wrong-outcome", "wrong-reachability", "duplicate-claim"} {
		t.Run(scenario, func(t *testing.T) {
			value := authorizedRPCSnapshot(t)
			expected := int32(2)
			switch scenario {
			case "variant-count":
				value.Variants = slices.Repeat(value.Variants, torahops.MaxVariants+1)
				expected = 11
			case "encoded-response":
				value.Variants[0].CanonicalBytes = bytes.Repeat([]byte{0xff}, torahops.MaxAuthorizedOperationReadBytes)
				expected = 11
			case "incomplete":
				value.Complete = false
			case "wrong-outcome":
				value.Outcome = torahops.OperationAbsentInVerifiedLocalSnapshot
			case "wrong-reachability":
				value.Variants[0].Reachability = torahops.OperationLiveDocument
			case "duplicate-claim":
				value.Variants = append(value.Variants, value.Variants[0])
			}
			reply := pinkhaAuthorizedOperationReadToWire(value, nil)
			require.Equal(t, expected, int32(reply.Error.Code))
			require.Nil(t, reply.Snapshot)
			require.Less(t, reply.Size(), 1024)
		})
	}
}

func TestPinkhaAuthorizedOperationRPCRejectsBeforeAccount(t *testing.T) {
	mw := &Middleware{}
	for _, version := range []uint32{0, 2} {
		reply := mw.PinkhaTorahAuthorizedOperationRead(context.Background(), &pb.PinkhaTorahAuthorizedOperationReadRequest{ProtocolVersion: version})
		require.Equal(t, int32(3), int32(reply.Error.Code))
		require.Nil(t, reply.Snapshot)
	}
	invalid := mw.PinkhaTorahAuthorizedOperationRead(context.Background(), nil)
	require.Equal(t, int32(2), int32(invalid.Error.Code))
	require.Nil(t, invalid.Snapshot)
	value := authorizedRPCSnapshot(t)
	missing := mw.PinkhaTorahAuthorizedOperationRead(context.Background(), &pb.PinkhaTorahAuthorizedOperationReadRequest{
		ProtocolVersion: 1, SpaceId: value.SpaceID, OperationId: value.OperationID,
	})
	require.Equal(t, int32(5), int32(missing.Error.Code))
	require.Nil(t, missing.Snapshot)
}
