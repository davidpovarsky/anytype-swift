package domain

import (
	"testing"

	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/stretchr/testify/require"
)

func TestPinkhaTorahOperationsUniqueKeyIsDedicated(t *testing.T) {
	key, err := NewUniqueKey(smartblock.SmartBlockTypePinkhaTorahOperations, "v1")
	require.NoError(t, err)
	require.Equal(t, "pinkhaTorahOps-v1", key.Marshal())
	decoded, err := UnmarshalUniqueKey(key.Marshal())
	require.NoError(t, err)
	require.Equal(t, smartblock.SmartBlockTypePinkhaTorahOperations, decoded.SmartblockType())
	require.Equal(t, "v1", decoded.InternalKey())
	for tp, prefix := range smartBlockTypeToKey {
		if tp != smartblock.SmartBlockTypePinkhaTorahOperations {
			require.NotEqual(t, "pinkhaTorahOps", prefix)
		}
	}
}
