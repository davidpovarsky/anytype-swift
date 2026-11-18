package service

import (
	"testing"

	"github.com/anyproto/anytype-heart/pb"
	"github.com/stretchr/testify/require"
)

// This is the real generated gomobile byte entry point. It does not substitute
// a fixture handler or call the typed core method directly. Account-backed
// positive acceptance remains a separate lifecycle fixture stage.
func TestPinkhaTorahGeneratedByteBoundaryRejectsWithoutAccount(t *testing.T) {
	require.Nil(t, mw.GetApp())
	for _, version := range []uint32{0, 1, 2} {
		t.Run(string(rune('0'+version)), func(t *testing.T) {
			request := &pb.RpcPinkhaTorahOperationsAppendRequest{ProtocolVersion: version, SpaceId: "fixture-space", OperationId: "00000000000000000000000000000001",
				Kind: pb.RpcPinkhaTorahOperations_ADD, Target: &pb.RpcPinkhaTorahOperationsTarget{ObjectId: "fixture-target"},
				Source: &pb.RpcPinkhaTorahOperationsSource{ProviderId: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte("test")}
			raw, err := request.Marshal()
			require.NoError(t, err)
			var appendReply pb.RpcPinkhaTorahOperationsAppendResponse
			require.NoError(t, appendReply.Unmarshal(PinkhaTorahOperationsAppend(raw)))
			require.Equal(t, uint32(1), appendReply.ProtocolVersion)
			require.NotNil(t, appendReply.Error)
			require.Nil(t, appendReply.Receipt)
			read := &pb.RpcPinkhaTorahOperationsReadTargetRequest{ProtocolVersion: version, SpaceId: request.SpaceId, Target: request.Target, Limit: 10}
			raw, err = read.Marshal()
			require.NoError(t, err)
			var readReply pb.RpcPinkhaTorahOperationsReadTargetResponse
			require.NoError(t, readReply.Unmarshal(PinkhaTorahOperationsReadTarget(raw)))
			require.Equal(t, uint32(1), readReply.ProtocolVersion)
			require.NotNil(t, readReply.Error)
			require.Nil(t, readReply.Snapshot)
			if version == 1 {
				require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NOT_LOGGED_IN, appendReply.Error.Code)
				require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NOT_LOGGED_IN, readReply.Error.Code)
			} else {
				require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_UNSUPPORTED_VERSION, appendReply.Error.Code)
				require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_UNSUPPORTED_VERSION, readReply.Error.Code)
			}
		})
	}
	var malformed pb.RpcPinkhaTorahOperationsAppendResponse
	require.NoError(t, malformed.Unmarshal(PinkhaTorahOperationsAppend([]byte{0xff})))
	require.NotNil(t, malformed.Error)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_BAD_INPUT, malformed.Error.Code)
	require.Nil(t, malformed.Receipt)
	require.Zero(t, malformed.ProtocolVersion, "generated parser errors cannot look like a native v1 receipt")
	require.Nil(t, mw.GetApp())
}
