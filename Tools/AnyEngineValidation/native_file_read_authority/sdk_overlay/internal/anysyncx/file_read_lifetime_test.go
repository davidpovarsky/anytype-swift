package anysyncx

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/internal/readlifetime"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace"
	"github.com/stretchr/testify/require"
)

// Only the teardown boundary is replaced. These tests call the real App.Close
// and spaceWrapper Close/TryClose methods and inspect their real lifetime gate.
type lifetimeCloseCache struct {
	spaceCache
	closeFn func() error
}

func (c *lifetimeCloseCache) Close() error { return c.closeFn() }

type lifetimeCloseSpace struct {
	commonspace.Space
	closeFn    func() error
	tryCloseFn func(time.Duration) (bool, error)
}

func (s *lifetimeCloseSpace) Close() error                             { return s.closeFn() }
func (s *lifetimeCloseSpace) TryClose(ttl time.Duration) (bool, error) { return s.tryCloseFn(ttl) }

func TestFileReadLifetimeAppCloseRetiresBeforeCacheTeardown(t *testing.T) {
	a := &App{a: &app.App{}}
	wrapper := &spaceWrapper{id: "same-space", app: a}
	account, _, err := a.FileReadLifetimes(wrapper)
	require.NoError(t, err)
	require.NoError(t, account.WithActive(nil))
	calls := 0
	a.spaceCache = &lifetimeCloseCache{closeFn: func() error {
		calls++
		// This read gate must return, not deadlock behind a write gate held
		// over cache teardown; retirement is already permanent here.
		require.ErrorIs(t, account.WithActive(nil), readlifetime.ErrRetired)
		return nil
	}}
	require.NoError(t, a.Close(context.Background()))
	require.Equal(t, 1, calls)
	require.ErrorIs(t, account.WithActive(nil), readlifetime.ErrRetired)
}

func TestFileReadLifetimeWrapperCloseAndTryCloseBoundaries(t *testing.T) {
	for _, operation := range []string{"close", "try-declined", "try-committed"} {
		t.Run(operation, func(t *testing.T) {
			a := &App{sync: newSpaceSyncHandler()}
			wrapper := &spaceWrapper{id: "same-space", app: a}
			account, space, err := a.FileReadLifetimes(wrapper)
			require.NoError(t, err)
			calls := 0
			errSentinel := errors.New("original underlying close result")
			wrapper.cs = &lifetimeCloseSpace{
				closeFn: func() error {
					calls++
					require.ErrorIs(t, space.WithActive(nil), readlifetime.ErrRetired)
					return errSentinel
				},
				tryCloseFn: func(ttl time.Duration) (bool, error) {
					calls++
					require.Equal(t, time.Minute, ttl)
					var pending *readlifetime.Pending
					called := false
					require.ErrorAs(t, space.WithActive(func() error { called = true; return nil }), &pending)
					require.False(t, called, "no plaintext callback may run inside underlying TryClose's decision/teardown interval")
					return operation == "try-committed", errSentinel
				},
			}
			if operation == "close" {
				require.ErrorIs(t, wrapper.Close(), errSentinel)
			} else {
				closed, err := wrapper.TryClose(time.Minute)
				require.Equal(t, operation == "try-committed", closed)
				require.ErrorIs(t, err, errSentinel)
			}
			require.Equal(t, 1, calls)
			currentAccount, currentSpace, err := a.FileReadLifetimes(wrapper)
			require.NoError(t, err)
			require.Same(t, account, currentAccount)
			require.Same(t, space, currentSpace)
			require.NoError(t, account.WithActive(nil))
			if operation == "try-declined" {
				require.NoError(t, space.WithActive(nil), "failed TryClose must resume the SAME token")
			} else {
				require.ErrorIs(t, space.WithActive(nil), readlifetime.ErrRetired)
			}
			// A loaded wrapper for the same account and exact space ID owns a
			// distinct token even though both public identities are unchanged.
			reloaded := &spaceWrapper{id: wrapper.id, app: a}
			reloadedAccount, reloadedSpace, err := a.FileReadLifetimes(reloaded)
			require.NoError(t, err)
			require.Same(t, account, reloadedAccount)
			require.NotSame(t, space, reloadedSpace)
			require.NoError(t, reloadedSpace.WithActive(nil))
		})
	}
}
