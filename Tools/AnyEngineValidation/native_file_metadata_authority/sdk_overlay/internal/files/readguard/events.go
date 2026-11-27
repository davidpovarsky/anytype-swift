package readguard

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"

	"github.com/anyproto/any-sync-sdk/internal/readlifetime"
)

// EventGate binds one local status subscription to its original signed ACL
// generation and account/Space lifetimes. Its loader must only peek an already
// loaded Space: event delivery must not load a cache or wait for a network.
type EventGate struct {
	ctx      context.Context
	cancel   context.CancelFunc
	load     LoadACL
	admitted authority
	closed   atomic.Bool
	mu       sync.Mutex
}

// NewEventGate refuses unavailable or quiescing authority. Status subscriptions
// are a best-effort local stream; Status remains the point-in-time truth.
func NewEventGate(ctx context.Context, load LoadACL) (*EventGate, error) {
	ctx, cancel := context.WithCancel(ctx)
	g := &EventGate{ctx: ctx, cancel: cancel, load: load}
	err := withAuthorityOnce(ctx, load, nil, func(current authority) error {
		g.admitted = current
		return nil
	})
	if err != nil {
		cancel()
		return nil, err
	}
	return g, nil
}

// Admit linearizes one event before invocation of external user code. It never
// calls that code or waits for TryClose. A queued event rejected after removal,
// cancellation or lifetime retirement is not delivered. An event already
// admitted may finish after Cancel/retirement; neither drains user callbacks.
func (g *EventGate) Admit() bool {
	if g == nil || g.closed.Load() {
		return false
	}
	accepted := false
	err := withAuthorityOnce(g.ctx, g.load, &g.admitted, func(authority) error {
		g.mu.Lock()
		defer g.mu.Unlock()
		if !g.closed.Load() && g.ctx.Err() == nil {
			accepted = true
		}
		return nil
	})
	if err != nil {
		var pending *readlifetime.Pending
		if !errors.As(err, &pending) {
			g.Cancel()
		}
		return false
	}
	return accepted
}

// Cancel prevents later admission without acquiring an ACL or cache lock. The
// short gate lock is never retained while unregistering or running user code.
func (g *EventGate) Cancel() {
	if g == nil {
		return
	}
	g.mu.Lock()
	g.closed.Store(true)
	g.cancel()
	g.mu.Unlock()
}
