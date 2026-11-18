package smartblock

import (
	"testing"

	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/stretchr/testify/require"
)

func TestPinkhaPrivateTypeAllocationAndIndexPolicy(t *testing.T) {
	_, collision := model.SmartBlockType_name[int32(SmartBlockTypePinkhaTorahOperations)]
	require.False(t, collision, "fork-local allocation collides with a generated upstream enum; review the pin before use")
	require.Equal(t, uint64(1347092481), uint64(SmartBlockTypePinkhaTorahOperations))
	require.Equal(t, "PinkhaTorahOperations", SmartBlockTypePinkhaTorahOperations.String())
	require.NoError(t, SmartBlockTypePinkhaTorahOperations.Valid())
	require.True(t, SmartBlockTypePinkhaTorahOperations.IsStoreBacked())
	fulltext, details, outgoing := SmartBlockTypePinkhaTorahOperations.Indexable()
	require.False(t, fulltext)
	require.False(t, details)
	require.False(t, outgoing)
	require.Error(t, SmartBlockType(0x504B0002).Valid(), "adjacent unknown versions must not become valid")
	fulltext, details, outgoing = SmartBlockTypePage.Indexable()
	require.True(t, fulltext && details && outgoing, "existing page indexing is unchanged")
}
