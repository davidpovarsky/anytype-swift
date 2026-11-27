// Package readguard fences plaintext readers with the loaded space's current
// signed ACL. It does not fetch or fabricate ACL records.
package readguard

import (
	"context"
	"errors"
	"io"
	"sync"
	"sync/atomic"

	"github.com/anyproto/any-sync-sdk/internal/readlifetime"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
)

// Reader is the existing file reader contract, without a dependency on the
// fetching implementation or a particular storage tier.
type Reader interface {
	io.Reader
	io.Seeker
	io.Closer
	Size() int64
}

// Scope binds the ACL to one captured account run and loaded Space generation.
// Tokens are immutable identities: retirement never reactivates an old token.
type Scope struct {
	ACL     list.AclList
	Account *readlifetime.Token
	Space   *readlifetime.Token
}

// LoadACL must resolve the captured account's exact space. It must not consult
// a later globally active account or reuse an ACL after that space is retired.
// Loading and all file I/O take place outside the ACL read lock.
type LoadACL func(context.Context) (Scope, error)

const maxReadChunk = 64 * 1024

// Open checks authority before opening content and again after opening returns.
// A held reader repeats the check at every read and seek boundary. Authority
// failure or any signed ACL generation change invalidates that reader: a later
// grant requires a fresh Open even when removal and restoration both happened
// while the caller was awaiting I/O. No old plaintext reader crosses that fence.
func Open(ctx context.Context, load LoadACL, open func() (Reader, error)) (Reader, error) {
	var admitted authority
	if err := withAuthority(ctx, load, nil, func(current authority) error {
		admitted = current
		return nil
	}); err != nil {
		return nil, err
	}
	inner, err := open()
	if err != nil {
		return nil, err
	}
	if err = withAuthority(ctx, load, &admitted, nil); err != nil {
		_ = inner.Close()
		return nil, err
	}
	// The reader owns cancellation for lifecycle waits even when Open's caller
	// supplied context.Background. Close must wake a pending TryClose wait.
	readCtx, cancel := context.WithCancel(ctx)
	return &reader{ctx: readCtx, cancel: cancel, load: load, inner: inner, admitted: admitted}, nil
}

// authority names one actual signed generation of the loaded ACL. Only public
// identifiers are retained; no private key or payload is copied into this fence.
type authority struct {
	aclID    string
	identity string
	headID   string
	account  *readlifetime.Token
	space    *readlifetime.Token
}

func withAuthority(ctx context.Context, load LoadACL, expected *authority, deliver func(authority) error) error {
	for {
		err := withAuthorityOnce(ctx, load, expected, deliver)
		var pending *readlifetime.Pending
		if !errors.As(err, &pending) {
			return err
		}
		// withAuthorityOnce has released every lock. Never wait for a close
		// decision (which may need the ACL lock) while holding the ACL lock.
		if err := pending.Wait(ctx); err != nil {
			return err
		}
	}
}

func withAuthorityOnce(ctx context.Context, load LoadACL, expected *authority, deliver func(authority) error) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	scope, err := load(ctx)
	if err != nil {
		return err
	}
	acl := scope.ACL
	if acl == nil || scope.Account == nil || scope.Space == nil {
		return list.ErrInsufficientPermissions
	}
	acl.RLock()
	defer acl.RUnlock()
	if err := ctx.Err(); err != nil {
		return err
	}
	state := acl.AclState()
	if state == nil || state.Identity() == nil || state.Permissions(state.Identity()).NoPermissions() {
		return list.ErrInsufficientPermissions
	}
	head := acl.Head()
	if head == nil {
		return list.ErrInsufficientPermissions
	}
	current := authority{aclID: acl.Id(), identity: state.Identity().Account(), headID: head.Id,
		account: scope.Account, space: scope.Space}
	if current.aclID == "" || current.identity == "" || current.headID == "" || (expected != nil && current != *expected) {
		return list.ErrInsufficientPermissions
	}
	// GetSpace may have returned before retirement while this goroutine waited
	// for the ACL lock. Check both captured lifecycle tokens now, atomically
	// with the final bounded memory copy. Retirement releases its token lock
	// before closing the cache/Space, so it never waits on ACL while holding it.
	err = scope.Account.WithActive(func() error {
		return scope.Space.WithActive(func() error {
			if err := ctx.Err(); err != nil {
				return err
			}
			if deliver != nil {
				return deliver(current)
			}
			return nil
		})
	})
	if errors.Is(err, readlifetime.ErrRetired) {
		return list.ErrInsufficientPermissions
	}
	return err
}

type reader struct {
	ctx      context.Context
	cancel   context.CancelFunc
	load     LoadACL
	inner    Reader
	admitted authority

	// Serializes stream position, not ACL updates or Close. In particular, a
	// network read never prevents the signed ACL from observing a removal.
	mu       sync.Mutex
	terminal error
	closed   atomic.Bool
	close    sync.Once
	closeErr error
}

func (r *reader) check(deliver func() error) error {
	if r.terminal != nil {
		return r.terminal
	}
	if r.closed.Load() {
		return io.ErrClosedPipe
	}
	err := withAuthority(r.ctx, r.load, &r.admitted, func(authority) error {
		if r.closed.Load() {
			return io.ErrClosedPipe
		}
		if deliver != nil {
			return deliver()
		}
		return nil
	})
	if err != nil && r.closed.Load() {
		err = io.ErrClosedPipe
	}
	if err != nil {
		r.terminal = err
	}
	return err
}

func (r *reader) Read(p []byte) (int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if err := r.check(nil); err != nil {
		return 0, err
	}
	if len(p) == 0 {
		return 0, nil
	}
	// Never let an awaited fetch write directly into caller-owned memory.
	// Data fetched after the initial check stays private until current signed
	// authority is checked again. Already released plaintext cannot be recalled.
	private := make([]byte, min(len(p), maxReadChunk))
	defer clear(private)
	n, readErr := r.inner.Read(private)
	if n < 0 || n > len(private) {
		return 0, io.ErrUnexpectedEOF
	}
	if err := r.check(func() error { copy(p, private[:n]); return nil }); err != nil {
		return 0, err
	}
	return n, readErr
}

func (r *reader) Seek(offset int64, whence int) (int64, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if err := r.check(nil); err != nil {
		return 0, err
	}
	position, seekErr := r.inner.Seek(offset, whence)
	if err := r.check(nil); err != nil {
		return 0, err
	}
	return position, seekErr
}

// Size is the existing metadata-only method and cannot return an authority
// error. All operations that deliver or position plaintext remain guarded.
func (r *reader) Size() int64 { return r.inner.Size() }

// Close may interrupt an awaited underlying read; it never waits for the
// position mutex or requires permission that may already have been revoked.
func (r *reader) Close() error {
	r.closed.Store(true)
	r.cancel()
	r.close.Do(func() { r.closeErr = r.inner.Close() })
	return r.closeErr
}
