package readguard

import (
	"bytes"
	"context"
	"io"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/internal/readlifetime"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/stretchr/testify/require"
)

// These barriers decorate the real signed ACL mutex, never its permissions,
// identity or signed head. They locate the post-fetch delivery boundary.
type observedACL struct {
	list.AclList
	locks       atomic.Int32
	unlocks     atomic.Int32
	beforeLock  func(int32)
	afterUnlock func(int32)
}

func (a *observedACL) RLock() {
	n := a.locks.Add(1)
	if a.beforeLock != nil {
		a.beforeLock(n)
	}
	a.AclList.RLock()
}

func (a *observedACL) RUnlock() {
	a.AclList.RUnlock()
	n := a.unlocks.Add(1)
	if a.afterUnlock != nil {
		a.afterUnlock(n)
	}
}

type readOutcome struct {
	n   int
	err error
}

func awaitRead(t *testing.T, done <-chan readOutcome) readOutcome {
	t.Helper()
	select {
	case got := <-done:
		return got
	case <-time.After(2 * time.Second):
		t.Fatal("held reader did not settle")
		return readOutcome{}
	}
}

func TestReadGuardRetirementAfterLoadBeforeFinalACLLock(t *testing.T) {
	for _, target := range []string{"account", "space"} {
		t.Run(target, func(t *testing.T) {
			f := newSignedFixture(t, list.AclPermissionsReader)
			originalHead := f.local.Head().Id
			atFinalLock := make(chan struct{})
			acl := &observedACL{AclList: f.local, beforeLock: func(n int32) {
				if n == 4 {
					close(atFinalLock)
				}
			}}
			load := func(ctx context.Context) (Scope, error) { scope, _ := f.load(ctx); scope.ACL = acl; return scope, nil }
			var release sync.Once
			source := &trackedReader{Reader: bytes.NewReader(nil), readFn: func(p []byte) (int, error) {
				f.local.Lock()
				return copy(p, "private bytes fetched before retirement"), nil
			}}
			r, err := Open(context.Background(), load, func() (Reader, error) { return source, nil })
			require.NoError(t, err)
			defer r.Close()
			buffer := bytes.Repeat([]byte{0xa5}, 64)
			done := make(chan readOutcome, 1)
			go func() { n, err := r.Read(buffer); done <- readOutcome{n, err} }()
			select {
			case <-atFinalLock:
			case <-time.After(2 * time.Second):
				t.Fatal("final read did not reach the captured ACL lock")
			}
			defer release.Do(f.local.Unlock)
			retired := make(chan struct{})
			go func() {
				if target == "account" {
					f.accountLifetime.Retire()
				} else {
					f.spaceLifetime.Retire()
				}
				close(retired)
			}()
			select {
			case <-retired:
			case <-time.After(2 * time.Second):
				t.Fatal("retirement waited for the ACL lock")
			}
			release.Do(f.local.Unlock)
			got := awaitRead(t, done)
			require.ErrorIs(t, got.err, list.ErrInsufficientPermissions)
			require.Zero(t, got.n)
			require.Equal(t, bytes.Repeat([]byte{0xa5}, 64), buffer)
			require.Equal(t, originalHead, f.local.Head().Id, "retirement test must keep the signed generation unchanged")
			require.Equal(t, int32(1), source.reads.Load())
		})
	}
}

func TestReadGuardPendingCloseWaitRevalidatesOrCancels(t *testing.T) {
	for _, outcome := range []string{"declined", "committed", "declined-then-close", "caller-cancel", "reader-close"} {
		t.Run(outcome, func(t *testing.T) {
			f := newSignedFixture(t, list.AclPermissionsReader)
			originalHead := f.local.Head().Id
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			pendingReached := make(chan struct{})
			acl := &observedACL{AclList: f.local, afterUnlock: func(n int32) {
				if n == 4 {
					close(pendingReached)
				}
			}}
			load := func(ctx context.Context) (Scope, error) { scope, _ := f.load(ctx); scope.ACL = acl; return scope, nil }
			source := &trackedReader{Reader: bytes.NewReader(nil), readFn: func(p []byte) (int, error) {
				f.spaceLifetime.BeginCloseAttempt()
				return copy(p, "fetched pending bytes"), nil
			}}
			// The reader-close case deliberately receives Background, so only
			// its own Close can wake the outstanding lifetime wait.
			openCtx := ctx
			if outcome == "reader-close" {
				openCtx = context.Background()
			}
			r, err := Open(openCtx, load, func() (Reader, error) { return source, nil })
			require.NoError(t, err)
			defer r.Close()
			buffer := bytes.Repeat([]byte{0xa5}, 64)
			done := make(chan readOutcome, 1)
			go func() { n, err := r.Read(buffer); done <- readOutcome{n, err} }()
			select {
			case <-pendingReached:
			case <-time.After(2 * time.Second):
				t.Fatal("post-fetch close barrier was not reached")
			}
			var settled sync.Once
			defer settled.Do(func() { f.spaceLifetime.FinishCloseAttempt(false) })
			// Taking the real ACL write lock while the reader waits proves the
			// pending wait dropped it. FinishCloseAttempt additionally takes the
			// token write gate; that must also complete while ACL is held here.
			aclHeld := make(chan struct{})
			releaseACL := make(chan struct{})
			aclReleased := make(chan struct{})
			var release sync.Once
			defer release.Do(func() { close(releaseACL) })
			go func() { f.local.Lock(); close(aclHeld); <-releaseACL; f.local.Unlock(); close(aclReleased) }()
			select {
			case <-aclHeld:
			case <-time.After(2 * time.Second):
				t.Fatal("pending reader retained the ACL lock")
			}
			var want error
			switch outcome {
			case "declined":
				settled.Do(func() { f.spaceLifetime.FinishCloseAttempt(false) })
			case "committed":
				settled.Do(func() { f.spaceLifetime.FinishCloseAttempt(true) })
				want = list.ErrInsufficientPermissions
			case "declined-then-close":
				settled.Do(func() { f.spaceLifetime.FinishCloseAttempt(false) })
				f.spaceLifetime.Retire()
				want = list.ErrInsufficientPermissions
			case "caller-cancel":
				cancel()
				want = context.Canceled
			case "reader-close":
				require.NoError(t, r.Close())
				want = io.ErrClosedPipe
			}
			if outcome == "caller-cancel" || outcome == "reader-close" {
				// Require cancellation before resolving the pending TryClose or
				// releasing ACL. Neither event is allowed to rescue a stuck wait.
				got := awaitRead(t, done)
				require.ErrorIs(t, got.err, want)
				require.Zero(t, got.n)
				require.Equal(t, bytes.Repeat([]byte{0xa5}, 64), buffer)
			} else {
				release.Do(func() { close(releaseACL) })
				got := awaitRead(t, done)
				if want == nil {
					require.NoError(t, got.err)
					require.Equal(t, "fetched pending bytes", string(buffer[:got.n]))
					require.Same(t, &f.spaceLifetime, r.(*reader).admitted.space, "declined TryClose must preserve the existing reader's exact token")
				} else {
					require.ErrorIs(t, got.err, want)
					require.Zero(t, got.n)
					require.Equal(t, bytes.Repeat([]byte{0xa5}, 64), buffer)
				}
			}
			release.Do(func() { close(releaseACL) })
			select {
			case <-aclReleased:
			case <-time.After(2 * time.Second):
				t.Fatal("ACL barrier did not close")
			}
			require.Equal(t, originalHead, f.local.Head().Id)
			require.Equal(t, int32(1), source.reads.Load())
		})
	}
}

func TestReadGuardSameSpaceReloadRequiresNewReaderWithUnchangedACL(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	originalHead := f.local.Head().Id
	current := &f.spaceLifetime
	load := func(ctx context.Context) (Scope, error) {
		scope, _ := f.load(ctx)
		scope.Space = current
		return scope, nil
	}
	source := &trackedReader{Reader: bytes.NewReader(nil), readFn: func(p []byte) (int, error) {
		current.Retire()
		current = &readlifetime.Token{}
		return copy(p, "prior loaded-space bytes"), nil
	}}
	r, err := Open(context.Background(), load, func() (Reader, error) { return source, nil })
	require.NoError(t, err)
	defer r.Close()
	buffer := bytes.Repeat([]byte{0xa5}, 64)
	n, err := r.Read(buffer)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, n)
	require.Equal(t, bytes.Repeat([]byte{0xa5}, 64), buffer)
	require.Equal(t, originalHead, f.local.Head().Id)
	require.NotSame(t, r.(*reader).admitted.space, current)
	fresh, err := Open(context.Background(), load, func() (Reader, error) {
		return &trackedReader{Reader: bytes.NewReader([]byte("current loaded-space bytes"))}, nil
	})
	require.NoError(t, err)
	defer fresh.Close()
	got, err := io.ReadAll(fresh)
	require.NoError(t, err)
	require.Equal(t, "current loaded-space bytes", string(got))
}
