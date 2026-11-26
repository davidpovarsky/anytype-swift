package torahcutoverroot

import (
	"context"
	"errors"
	"sync/atomic"
)

var ErrPrivateOperation = errors.New("private Torah cutover operation requires its native versioned boundary")

type rootCreationKey struct{}
type rootCreationGuard struct {
	spaceID string
	rootID  string
	used    atomic.Bool
	commit  func(func() error) error
}

// WithRootCreationGuard carries one account-scoped local installation authority.
// No caller RPC field is used as a permit. Its callback owns current account,
// target lease, and ACL checks immediately around the native storage operation.
func WithRootCreationGuard(ctx context.Context, spaceID, rootID string, commit func(func() error) error) context.Context {
	return context.WithValue(ctx, rootCreationKey{}, &rootCreationGuard{spaceID: spaceID, rootID: rootID, commit: commit})
}

func CreateRootWithGuard(ctx context.Context, spaceID, rootID string, create func() error) error {
	if ctx == nil {
		return ErrPrivateOperation
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	guard, _ := ctx.Value(rootCreationKey{}).(*rootCreationGuard)
	if guard == nil || guard.spaceID != spaceID || guard.rootID != rootID || guard.commit == nil || create == nil ||
		!guard.used.CompareAndSwap(false, true) {
		return ErrPrivateOperation
	}
	return guard.commit(create)
}
