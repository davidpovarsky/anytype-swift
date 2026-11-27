// Package readlifetime linearizes bounded plaintext delivery with retirement.
// It contains no cache, storage, network or ACL operations.
package readlifetime

import (
	"context"
	"errors"
	"sync"
)

var ErrRetired = errors.New("plaintext read lifetime retired")

// Token is one account run or one loaded-space generation. Its zero value is
// active. A retired token is never reactivated and must not be copied after use.
type Token struct {
	mu      sync.RWMutex
	retired bool
	closing int
	settled chan struct{}
}

// Pending means a TryClose decision is in flight. A caller must release its
// ACL lock before waiting. A declined close resumes this very token.
type Pending struct{ done <-chan struct{} }

func (p *Pending) Error() string { return "plaintext read lifetime close pending" }

func (p *Pending) Wait(ctx context.Context) error {
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-p.done:
		return nil
	}
}

// WithActive protects only a bounded synchronous validation/memory-copy step.
// The callback must not load a cache entry, wait on I/O, or acquire an ACL lock.
// Callers acquire their ACL lock before entering this method. Retirement drops
// its write lock before beginning any teardown that might acquire an ACL lock.
func (t *Token) WithActive(deliver func() error) error {
	if t == nil {
		return ErrRetired
	}
	t.mu.RLock()
	defer t.mu.RUnlock()
	if t.retired {
		return ErrRetired
	}
	if t.closing != 0 {
		return &Pending{done: t.settled}
	}
	if deliver != nil {
		return deliver()
	}
	return nil
}

// Retire is the linearization point, before cache/component teardown. It waits
// only for bounded copies already admitted by this token, never for file I/O.
func (t *Token) Retire() {
	if t == nil {
		return
	}
	t.mu.Lock()
	t.retired = true
	if t.settled != nil {
		close(t.settled)
		t.settled = nil
	}
	t.mu.Unlock()
}

// BeginCloseAttempt quiesces delivery before TryClose's private committed-close
// decision. It does not retire the token. No lock remains held during TryClose.
func (t *Token) BeginCloseAttempt() {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.closing == 0 && !t.retired {
		t.settled = make(chan struct{})
	}
	t.closing++
}

func (t *Token) FinishCloseAttempt(closed bool) {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.closing == 0 {
		panic("readlifetime: close attempt was not begun")
	}
	t.closing--
	if closed {
		t.retired = true
	}
	if (t.closing == 0 || t.retired) && t.settled != nil {
		close(t.settled)
		t.settled = nil
	}
}
