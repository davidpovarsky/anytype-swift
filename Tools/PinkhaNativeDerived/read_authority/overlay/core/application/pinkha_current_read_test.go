package application

import (
	"testing"

	"github.com/anyproto/any-sync/app"
	"github.com/stretchr/testify/require"
)

// This is a native lifecycle-lock component check, not an account/RPC journey.
func TestCurrentAppReadPublicationLease(t *testing.T) {
	original, replacement := &app.App{}, &app.App{}
	s := &Service{app: original}
	release, current := s.AcquireCurrentAppRead(nil)
	require.False(t, current)
	require.Nil(t, release)
	release, current = s.AcquireCurrentAppRead(replacement)
	require.False(t, current)
	require.Nil(t, release)

	release, current = s.AcquireCurrentAppRead(original)
	require.True(t, current)
	require.NotNil(t, release)
	// AccountStop/Select acquire this same lock exclusively. TryLock makes the
	// exclusion assertion deterministic; no scheduler delay or sleep is used.
	require.False(t, s.lock.TryLock())
	release()
	release() // the owner can safely retire a completed lease more than once
	require.True(t, s.lock.TryLock())
	s.app = replacement
	s.lock.Unlock()
	release, current = s.AcquireCurrentAppRead(original)
	require.False(t, current)
	require.Nil(t, release)
	release, current = s.AcquireCurrentAppRead(replacement)
	require.True(t, current)
	release()
	require.True(t, s.lock.TryLock())
	s.app = nil
	s.lock.Unlock()
	release, current = s.AcquireCurrentAppRead(replacement)
	require.False(t, current)
	require.Nil(t, release)
}
