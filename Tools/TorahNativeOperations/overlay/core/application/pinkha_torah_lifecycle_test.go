package application

import (
	"context"
	"testing"

	"github.com/anyproto/any-sync/app"
	"github.com/stretchr/testify/require"
)

func TestPinkhaAppLeaseExcludesStopAndReleasesOnce(t *testing.T) {
	s := &Service{app: &app.App{}}
	current, release, err := s.LeasePinkhaTorahApp(context.Background())
	require.NoError(t, err)
	require.Same(t, s.app, current)
	available := s.lock.TryLock()
	if available {
		s.lock.Unlock()
	}
	require.False(t, available, "Stop must wait before closing any leased account component")
	release()
	release()
	require.True(t, s.lock.TryLock(), "application lease must be released exactly once")
	s.app = nil
	s.lock.Unlock()
	current, release, err = s.LeasePinkhaTorahApp(context.Background())
	require.NoError(t, err)
	require.Nil(t, current)
	require.Nil(t, release)
	require.True(t, s.lock.TryLock(), "no-app result must not retain the application lock")
	s.lock.Unlock()
}

func TestPinkhaAppLeaseRejectsCancelledContextWithoutLock(t *testing.T) {
	s := &Service{app: &app.App{}}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	current, release, err := s.LeasePinkhaTorahApp(ctx)
	require.ErrorIs(t, err, context.Canceled)
	require.Nil(t, current)
	require.Nil(t, release)
	require.True(t, s.lock.TryLock())
	s.lock.Unlock()
}
