package service

import (
	"strings"
	"testing"

	"github.com/anyproto/anytype-heart/pb"
	"github.com/stretchr/testify/require"
)

// Calls the actual generated gomobile byte entry, never a replaced fixture
// handler. The positive account boundary has its own candidate fixture.
func TestPinkhaAuthorizedOperationGeneratedByteBoundaryWithoutAccount(t *testing.T) {
	require.Nil(t, mw.GetApp())
	for _, version := range []uint32{0, 1, 2} {
		t.Run(string(rune('0'+version)), func(t *testing.T) {
			req := &pb.PinkhaTorahAuthorizedOperationReadRequest{
				ProtocolVersion: version, SpaceId: "fixture-space", OperationId: strings.Repeat("1", 32),
			}
			raw, err := req.Marshal()
			require.NoError(t, err)
			var reply pb.PinkhaTorahAuthorizedOperationReadResponse
			require.NoError(t, reply.Unmarshal(PinkhaTorahAuthorizedOperationRead(raw)))
			require.Equal(t, uint32(1), reply.ProtocolVersion)
			require.NotNil(t, reply.Error)
			require.Nil(t, reply.Snapshot)
			if version == 1 {
				require.Equal(t, int32(5), int32(reply.Error.Code))
			} else {
				require.Equal(t, int32(3), int32(reply.Error.Code))
			}
		})
	}
	var malformed pb.PinkhaTorahAuthorizedOperationReadResponse
	require.NoError(t, malformed.Unmarshal(PinkhaTorahAuthorizedOperationRead([]byte{0xff})))
	require.NotNil(t, malformed.Error)
	require.Equal(t, int32(2), int32(malformed.Error.Code))
	require.Zero(t, malformed.ProtocolVersion)
	require.Nil(t, malformed.Snapshot)
	require.Nil(t, mw.GetApp())
}
