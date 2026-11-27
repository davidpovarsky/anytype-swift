package readguard

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/internal/fanout"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/stretchr/testify/require"
)

// These controls use the existing, fully verified fresh signed ACL fixture.
// Only the new materialized-value and status-event boundaries are selected.
type privateFileMetadata struct {
	Name string
	Mime string
}

func TestMetadataValueGuardAdmitsCurrentReaderAndGuest(t *testing.T) {
	for _, role := range []struct {
		name       string
		permission list.AclPermissions
	}{{"reader", list.AclPermissionsReader}, {"guest", list.AclPermissionsGuest}} {
		t.Run(role.name, func(t *testing.T) {
			f := newSignedFixture(t, role.permission)
			want := privateFileMetadata{Name: "current-member.txt", Mime: "text/plain"}
			got, err := Value(context.Background(), f.load, func() (privateFileMetadata, error) { return want, nil })
			require.NoError(t, err)
			require.Equal(t, want, got)
		})
	}
}

func TestMetadataValueGuardRefusesRemovedLookupAndMasksFailedRead(t *testing.T) {
	t.Run("removed-before-lookup", func(t *testing.T) {
		f := newSignedFixture(t, list.AclPermissionsReader)
		require.NoError(t, f.revoke())
		called := false
		got, err := Value(context.Background(), f.load, func() (privateFileMetadata, error) {
			called = true
			return privateFileMetadata{Name: "must not be looked up"}, nil
		})
		require.ErrorIs(t, err, list.ErrInsufficientPermissions)
		require.Zero(t, got)
		require.False(t, called)
	})
	t.Run("removed-during-failed-read", func(t *testing.T) {
		f := newSignedFixture(t, list.AclPermissionsReader)
		lookupErr := errors.New("private lookup diagnostic")
		got, err := Value(context.Background(), f.load, func() (privateFileMetadata, error) {
			require.NoError(t, f.revoke())
			return privateFileMetadata{Name: "partial private result"}, lookupErr
		})
		require.ErrorIs(t, err, list.ErrInsufficientPermissions)
		require.NotErrorIs(t, err, lookupErr)
		require.Zero(t, got)
	})
}

func TestMetadataValueGuardDiscardsAwaitedResultWithoutHoldingACL(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	ctx, cancel := context.WithCancel(context.Background())
	entered, release := make(chan struct{}), make(chan struct{})
	var releaseOnce sync.Once
	unblock := func() { releaseOnce.Do(func() { close(release) }) }
	type outcome struct {
		value privateFileMetadata
		err   error
	}
	done := make(chan outcome, 1)
	finished := make(chan struct{})
	t.Cleanup(func() {
		cancel()
		unblock()
		select {
		case <-finished:
		case <-time.After(time.Second):
			t.Error("owned metadata read did not finish")
		}
	})
	go func() {
		defer close(finished)
		value, err := Value(ctx, f.load, func() (privateFileMetadata, error) {
			close(entered)
			select {
			case <-release:
			case <-ctx.Done():
				return privateFileMetadata{}, ctx.Err()
			}
			return privateFileMetadata{Name: "private metadata fetched while awaiting"}, nil
		})
		done <- outcome{value, err}
	}()
	select {
	case <-entered:
	case <-time.After(time.Second):
		t.Fatal("metadata read did not reach its barrier")
	}
	revoked := make(chan error, 1)
	go func() { revoked <- f.revoke() }()
	select {
	case err := <-revoked:
		require.NoError(t, err)
	case <-time.After(time.Second):
		unblock()
		t.Fatal("the awaited read blocked the signed ACL writer")
	}
	unblock()
	select {
	case got := <-done:
		require.ErrorIs(t, got.err, list.ErrInsufficientPermissions)
		require.Zero(t, got.value)
	case <-time.After(time.Second):
		t.Fatal("metadata read did not return after release")
	}
}

func TestMetadataValueGuardRejectsSignedABAAndAccountRetirement(t *testing.T) {
	for _, transition := range []string{"signed-remove-restore", "account-retired"} {
		t.Run(transition, func(t *testing.T) {
			f := newSignedFixture(t, list.AclPermissionsReader)
			got, err := Value(context.Background(), f.load, func() (privateFileMetadata, error) {
				if transition == "signed-remove-restore" {
					require.NoError(t, f.revoke())
					require.NoError(t, f.restore())
				} else {
					f.accountLifetime.Retire()
				}
				return privateFileMetadata{Name: "cross-generation metadata"}, nil
			})
			require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			require.Zero(t, got)
		})
	}
}

func TestStatusEventGuardRefusesQueuedRemovedOrCancelledEvents(t *testing.T) {
	for _, transition := range []string{"signed-removal", "unsubscribe"} {
		t.Run(transition, func(t *testing.T) {
			f := newSignedFixture(t, list.AclPermissionsReader)
			entered, release := make(chan struct{}), make(chan struct{})
			var releaseOnce sync.Once
			unblock := func() { releaseOnce.Do(func() { close(release) }) }
			var calls atomic.Int32
			load := func(ctx context.Context) (Scope, error) {
				if calls.Add(1) == 2 {
					close(entered)
					select {
					case <-release:
					case <-ctx.Done():
						return Scope{}, ctx.Err()
					}
				}
				return f.load(ctx)
			}
			gate, err := NewEventGate(context.Background(), load)
			require.NoError(t, err)
			registry := fanout.New[privateFileMetadata]()
			var delivered atomic.Int32
			unsub := registry.Add(func(value privateFileMetadata) {
				if gate.Admit() {
					delivered.Add(1)
				}
			})
			finished := make(chan struct{})
			t.Cleanup(func() {
				gate.Cancel()
				unsub()
				unblock()
				select {
				case <-finished:
				case <-time.After(time.Second):
					t.Error("owned queued status dispatch did not finish")
				}
			})
			go func() {
				defer close(finished)
				registry.Dispatch(privateFileMetadata{Name: "queued local diagnostics"})
			}()
			select {
			case <-entered:
			case <-time.After(time.Second):
				t.Fatal("real fanout dispatch did not reach admission")
			}
			if transition == "signed-removal" {
				require.NoError(t, f.revoke())
			} else {
				gate.Cancel()
				unsub()
			}
			unblock()
			select {
			case <-finished:
			case <-time.After(time.Second):
				t.Fatal("status dispatch did not finish after release")
			}
			require.Zero(t, delivered.Load(), "a snapshotted callback must not admit a queued stale value")
			registry.Dispatch(privateFileMetadata{Name: "later event"})
			require.Zero(t, delivered.Load())
		})
	}
}

func TestStatusEventGuardAlreadyAdmittedCallbackMayFinish(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	gate, err := NewEventGate(context.Background(), f.load)
	require.NoError(t, err)
	entered, release := make(chan struct{}), make(chan struct{})
	var releaseOnce sync.Once
	unblock := func() { releaseOnce.Do(func() { close(release) }) }
	var delivered atomic.Int32
	registry := fanout.New[privateFileMetadata]()
	unsub := registry.Add(func(privateFileMetadata) {
		if gate.Admit() {
			close(entered)
			<-release // External code is deliberately still running.
			delivered.Add(1)
		}
	})
	finished := make(chan struct{})
	t.Cleanup(func() {
		gate.Cancel()
		unsub()
		unblock()
		select {
		case <-finished:
		case <-time.After(time.Second):
			t.Error("owned admitted callback did not finish")
		}
	})
	go func() { defer close(finished); registry.Dispatch(privateFileMetadata{Name: "already admitted event"}) }()
	select {
	case <-entered:
	case <-time.After(time.Second):
		t.Fatal("callback was not admitted")
	}
	retired := make(chan error, 1)
	go func() { err := f.revoke(); gate.Cancel(); unsub(); retired <- err }()
	select {
	case err := <-retired:
		require.NoError(t, err)
	case <-time.After(time.Second):
		t.Fatal("external callback retained an ACL/lifetime/gate lock")
	}
	require.Zero(t, delivered.Load(), "Cancel is not a callback-drain claim")
	unblock()
	select {
	case <-finished:
	case <-time.After(time.Second):
		t.Fatal("admitted callback did not finish")
	}
	require.Equal(t, int32(1), delivered.Load())
	registry.Dispatch(privateFileMetadata{Name: "not admitted after retirement"})
	require.Equal(t, int32(1), delivered.Load())
}

func TestStatusEventGuardQuiescesWithoutWaitingAndPreservesDeclinedClose(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	gate, err := NewEventGate(context.Background(), f.load)
	require.NoError(t, err)
	defer gate.Cancel()
	f.spaceLifetime.BeginCloseAttempt()
	finished := make(chan bool, 1)
	go func() { finished <- gate.Admit() }()
	select {
	case admitted := <-finished:
		require.False(t, admitted)
	case <-time.After(time.Second):
		f.spaceLifetime.FinishCloseAttempt(false)
		t.Fatal("a best-effort status event waited on TryClose")
	}
	f.spaceLifetime.FinishCloseAttempt(false)
	require.True(t, gate.Admit(), "the same subscription remains valid after a declined close")
	f.spaceLifetime.Retire()
	require.False(t, gate.Admit())
}
