package clientspace

import (
	"context"
	"testing"

	"github.com/anyproto/anytype-heart/core/block/object/objectcache"
	"github.com/stretchr/testify/require"
)

type currentReadCloseObserver struct {
	objectcache.Cache
	onClose func()
}

func (c *currentReadCloseObserver) Close(context.Context) error {
	c.onClose()
	return nil
}

// Uses the actual native space.Close entry. Only unrelated cache/common cleanup
// is inert; the native retirement gate and lifetime exclusion are unmodified.
func TestCurrentSpaceReadPublicationLease(t *testing.T) {
	s := &space{common: newVirtualCommonSpace("publication-component")}
	closed := 0
	s.Cache = &currentReadCloseObserver{onClose: func() {
		closed++
		// Close must retire before cleanup and release its writer before calling
		// cleanup. Otherwise this actual acquisition either succeeds or deadlocks.
		release, current := s.AcquireCurrentReadPublication()
		require.False(t, current)
		require.Nil(t, release)
	}}
	release, current := s.AcquireCurrentReadPublication()
	require.True(t, current)
	require.NotNil(t, release)
	// Deterministically prove that the exact writer used by native Close cannot
	// retire while a completed publication is still leased; no sleep is used.
	require.False(t, s.currentRead.mu.TryLock())
	release()
	release()
	require.NoError(t, s.Close(context.Background()))
	require.Equal(t, 1, closed)
	release, current = s.AcquireCurrentReadPublication()
	require.False(t, current)
	require.Nil(t, release)
}
