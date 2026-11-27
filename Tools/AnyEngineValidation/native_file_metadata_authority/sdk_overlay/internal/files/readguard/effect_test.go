package readguard

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/stretchr/testify/require"
)

func TestCacheEffectAdmitsCurrentReaderAndGuest(t *testing.T) {
	for _, role := range []struct {
		name       string
		permission list.AclPermissions
	}{{"reader", list.AclPermissionsReader}, {"guest", list.AclPermissionsGuest}} {
		t.Run(role.name, func(t *testing.T) {
			f := newSignedFixture(t, role.permission)
			prepared, invoked := 0, 0
			err := Effect(context.Background(), f.load, func() (func() error, error) {
				prepared++
				return func() error { invoked++; return nil }, nil
			})
			require.NoError(t, err)
			require.Equal(t, 1, prepared)
			require.Equal(t, 1, invoked)
		})
	}
}

func TestCacheEffectRefusesRemovedBeforePreparation(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	require.NoError(t, f.revoke())
	prepared, invoked := 0, 0
	err := Effect(context.Background(), f.load, func() (func() error, error) {
		prepared++
		return func() error { invoked++; return nil }, nil
	})
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, prepared)
	require.Zero(t, invoked)
}

func TestCacheEffectDiscardsChangedPreparation(t *testing.T) {
	for _, changed := range []string{"signed-removal-and-read-error", "account-retired", "space-retired", "cancelled"} {
		t.Run(changed, func(t *testing.T) {
			f := newSignedFixture(t, list.AclPermissionsReader)
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			prepared, invoked := 0, 0
			originalReadError := errors.New("original synthetic row lookup error")
			err := Effect(ctx, f.load, func() (func() error, error) {
				prepared++
				// These operations take ACL/lifetime writer locks. Preparation
				// must not retain the guard's reader locks around a row lookup.
				switch changed {
				case "signed-removal-and-read-error":
					require.NoError(t, f.revoke())
				case "account-retired":
					f.accountLifetime.Retire()
				case "space-retired":
					f.spaceLifetime.Retire()
				case "cancelled":
					cancel()
				}
				return func() error { invoked++; return nil }, originalReadError
			})
			if changed == "cancelled" {
				require.ErrorIs(t, err, context.Canceled)
			} else {
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			}
			require.NotErrorIs(t, err, originalReadError)
			require.Equal(t, 1, prepared)
			require.Zero(t, invoked)
		})
	}
}

func TestCacheEffectPreservesAdmittedOutcome(t *testing.T) {
	for _, outcome := range []string{"success", "original-error-after-effect"} {
		t.Run(outcome, func(t *testing.T) {
			f := newSignedFixture(t, list.AclPermissionsReader)
			originalError := errors.New("original synthetic second-stage failure")
			prepared, effects, callbacks := 0, 0, 0
			err := Effect(context.Background(), f.load, func() (func() error, error) {
				prepared++
				return func() error {
					effects++
					// A queue/store may synchronously call other code. The action
					// is outside all guard locks, so signed removal and retirement
					// can complete without waiting for this action to return.
					if revokeErr := f.revoke(); revokeErr != nil {
						return revokeErr
					}
					f.accountLifetime.Retire()
					f.spaceLifetime.Retire()
					callbacks++
					if outcome == "original-error-after-effect" {
						return originalError
					}
					return nil
				}, nil
			})
			if outcome == "success" {
				require.NoError(t, err)
			} else {
				require.ErrorIs(t, err, originalError)
			}
			require.NotErrorIs(t, err, list.ErrInsufficientPermissions)
			require.Equal(t, 1, prepared)
			require.Equal(t, 1, effects)
			require.Equal(t, 1, callbacks)
		})
	}
}

func TestCacheEffectInlineNoopRequiresCurrentAuthority(t *testing.T) {
	for _, state := range []string{"current", "removed-during-preparation"} {
		t.Run(state, func(t *testing.T) {
			f := newSignedFixture(t, list.AclPermissionsReader)
			prepared := 0
			err := Effect(context.Background(), f.load, func() (func() error, error) {
				prepared++
				if state == "removed-during-preparation" {
					require.NoError(t, f.revoke())
				}
				return nil, nil
			})
			if state == "current" {
				require.NoError(t, err)
			} else {
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			}
			require.Equal(t, 1, prepared)
		})
	}
}

func TestCacheEffectPreservesUnchangedPreparationError(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	originalError := errors.New("original synthetic row failure before any effect")
	invoked := 0
	err := Effect(context.Background(), f.load, func() (func() error, error) {
		return func() error { invoked++; return nil }, originalError
	})
	require.ErrorIs(t, err, originalError)
	require.Zero(t, invoked)
}
