package service

import (
	"fmt"
	"strings"
	"testing"

	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pb/cutoverpb"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/stretchr/testify/require"
)

// Real generated gomobile byte entry points, never a replacement handler.
// Positive native-account dispatch is qualified separately through generated gRPC.
func TestPinkhaTorahCutoverGeneratedByteBoundary(t *testing.T) {
	require.Nil(t, mw.GetApp())
	for _, version := range []uint32{0, 1, 2} {
		scope := &cutoverpb.PinkhaTorahCutoverScope{ProtocolVersion: version, SpaceId: "space", ObjectId: "object", PropertyKey: "property"}
		raw, err := scope.Marshal()
		require.NoError(t, err)
		var source cutoverpb.PinkhaTorahCutoverSourceReadResponse
		require.NoError(t, source.Unmarshal(PinkhaTorahCutoverSourceRead(raw)))
		require.NotNil(t, source.Error)
		require.Nil(t, source.Snapshot)
		require.Equal(t, uint32(1), source.ProtocolVersion)
		var read cutoverpb.PinkhaTorahCutoverReadResponse
		require.NoError(t, read.Unmarshal(PinkhaTorahCutoverRead(raw)))
		require.NotNil(t, read.Error)
		require.Nil(t, read.Snapshot)
		require.Equal(t, uint32(1), read.ProtocolVersion)
		expected := cutoverpb.PinkhaTorahCutoverError_UNSUPPORTED_VERSION
		if version == 1 {
			expected = cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN
		}
		require.Equal(t, expected, source.Error.Code)
		require.Equal(t, expected, read.Error.Code)
	}
	scope := &cutoverpb.PinkhaTorahCutoverScope{ProtocolVersion: 1, SpaceId: "space", ObjectId: "object", PropertyKey: "property"}
	plan := cutover.Plan{Version: 1, SpaceID: "space", ObjectID: "object", PropertyKey: "property", Facts: []cutover.Fact{}}
	planID, err := plan.ID()
	require.NoError(t, err)
	record := &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, RecordId: fmt.Sprintf("%032x", 1), Kind: cutoverpb.PinkhaTorahCutover_BEGIN,
		PlanId: planID, Plan: &cutoverpb.PinkhaTorahCutoverPlan{Version: 1, SpaceId: "space", ObjectId: "object", PropertyKey: "property"}, SourceHeads: []string{"source-head"}}
	raw, err := record.Marshal()
	require.NoError(t, err)
	var appended cutoverpb.PinkhaTorahCutoverAppendResponse
	require.NoError(t, appended.Unmarshal(PinkhaTorahCutoverAppend(raw)))
	require.NotNil(t, appended.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, appended.Error.Code)
	require.Nil(t, appended.Receipt)
	operation := &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: scope, PlanId: planID, FactId: strings.Repeat("1", 64),
		OperationId: fmt.Sprintf("%032x", 2), Kind: pb.RpcPinkhaTorahOperations_ADD}
	raw, err = operation.Marshal()
	require.NoError(t, err)
	var imported cutoverpb.PinkhaTorahCutoverOperationResponse
	require.NoError(t, imported.Unmarshal(PinkhaTorahCutoverImport(raw)))
	require.NotNil(t, imported.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, imported.Error.Code)
	require.Nil(t, imported.Receipt)
	operation.FactId = ""
	raw, err = operation.Marshal()
	require.NoError(t, err)
	var association cutoverpb.PinkhaTorahCutoverOperationResponse
	require.NoError(t, association.Unmarshal(PinkhaTorahCutoverAssociationAppend(raw)))
	require.NotNil(t, association.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, association.Error.Code)
	require.Nil(t, association.Receipt)
	// The generator owns malformed-protobuf rejection. Its absent version can
	// never be mistaken for a successful native-v1 result.
	malformed := []byte{0xff}
	appended = cutoverpb.PinkhaTorahCutoverAppendResponse{}
	imported = cutoverpb.PinkhaTorahCutoverOperationResponse{}
	association = cutoverpb.PinkhaTorahCutoverOperationResponse{}
	require.NoError(t, cutoverByteMalformedReads(malformed, t))
	require.NoError(t, appended.Unmarshal(PinkhaTorahCutoverAppend(malformed)))
	require.NotNil(t, appended.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_BAD_INPUT, appended.Error.Code)
	require.Zero(t, appended.ProtocolVersion)
	require.Nil(t, appended.Receipt)
	require.NoError(t, imported.Unmarshal(PinkhaTorahCutoverImport(malformed)))
	require.NotNil(t, imported.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_BAD_INPUT, imported.Error.Code)
	require.Zero(t, imported.ProtocolVersion)
	require.Nil(t, imported.Receipt)
	require.NoError(t, association.Unmarshal(PinkhaTorahCutoverAssociationAppend(malformed)))
	require.NotNil(t, association.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_BAD_INPUT, association.Error.Code)
	require.Zero(t, association.ProtocolVersion)
	require.Nil(t, association.Receipt)
	require.Nil(t, mw.GetApp())
}
func cutoverByteMalformedReads(raw []byte, t *testing.T) error {
	t.Helper()
	var source cutoverpb.PinkhaTorahCutoverSourceReadResponse
	if err := source.Unmarshal(PinkhaTorahCutoverSourceRead(raw)); err != nil {
		return err
	}
	require.NotNil(t, source.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_BAD_INPUT, source.Error.Code)
	require.Zero(t, source.ProtocolVersion)
	require.Nil(t, source.Snapshot)
	var read cutoverpb.PinkhaTorahCutoverReadResponse
	if err := read.Unmarshal(PinkhaTorahCutoverRead(raw)); err != nil {
		return err
	}
	require.NotNil(t, read.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_BAD_INPUT, read.Error.Code)
	require.Zero(t, read.ProtocolVersion)
	require.Nil(t, read.Snapshot)
	return nil
}
