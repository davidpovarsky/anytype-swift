// This file is compiled only by the separate Space.Close test overlay. It adds
// no product command, source replacement, status mutation, or substitute Space.
package space

import (
	"context"
	"errors"
	"sync/atomic"

	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/internal/spaceprocess/loader"
)

// PinkhaT2OwnedSpaceCloser selects the already loaded controller before any
// append barrier is armed. The returned closure forwards its original Close
// exactly once; later ordinary account cleanup uses the controller normally.
func PinkhaT2OwnedSpaceCloser(ctx context.Context, spaces Service, expected clientspace.Space) (func(context.Context) error, error) {
	s, ok := spaces.(*service)
	if !ok || s == nil || expected == nil || ctx == nil {
		return nil, errors.New("actual owned Space service required")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	s.mu.Lock()
	ctrl := s.spaceControllers[expected.Id()]
	s.mu.Unlock()
	if ctrl == nil || ctrl.SpaceId() != expected.Id() {
		return nil, errors.New("actual owned Space controller required")
	}
	load, ok := ctrl.Current().(loader.LoadWaiter)
	if !ok {
		return nil, errors.New("already loaded Space controller required")
	}
	actual, err := load.WaitLoad(ctx)
	if err != nil {
		return nil, err
	}
	if actual != expected {
		return nil, errors.New("controller belongs to another Space instance")
	}
	var called atomic.Bool
	return func(closeCtx context.Context) error {
		if !called.CompareAndSwap(false, true) {
			return errors.New("test controller Close was already forwarded")
		}
		return ctrl.Close(closeCtx)
	}, nil
}
