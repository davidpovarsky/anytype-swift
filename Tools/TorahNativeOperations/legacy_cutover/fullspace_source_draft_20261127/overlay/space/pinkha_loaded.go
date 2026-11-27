package space

import (
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/internal/spaceprocess/loader"
	"github.com/anyproto/anytype-heart/space/internal/spaceprocess/mode"
)

// PinkhaLoadedSpace is deliberately narrower than Service.Get: it never calls
// ensureSpaceStarted or waits for the deferred-loading queue. No Service/mock
// interface changes are needed. The caller holds the existing account app lease.
func PinkhaLoadedSpace(component Service, id string) (clientspace.Space, func() error, torahindexcontract.DeliveryFence, error) {
	s, ok := component.(*service)
	if !ok || id == "" {
		return nil, nil, nil, torahindexcontract.ErrNotLoaded
	}
	s.mu.Lock()
	ctrl := s.spaceControllers[id]
	if s.isClosing.Load() || s.ctx == nil || s.ctx.Err() != nil || ctrl == nil || ctrl.Mode() != mode.ModeLoading {
		s.mu.Unlock()
		return nil, nil, nil, torahindexcontract.ErrNotLoaded
	}
	current, lifecycle := ctrl.Current(), s.ctx
	s.mu.Unlock()
	sp, loaded, same, loadedDelivery, err := loader.PinkhaLoaded(current)
	if err != nil {
		return nil, nil, nil, err
	}
	if sp == nil || sp.Id() != id {
		return nil, nil, nil, torahindexcontract.ErrScopeChanged
	}
	validate := func() error {
		s.mu.Lock()
		registered := s.spaceControllers[id]
		valid := !s.isClosing.Load() && lifecycle.Err() == nil && s.ctx == lifecycle && registered == ctrl && ctrl.Mode() == mode.ModeLoading && same(ctrl.Current())
		s.mu.Unlock()
		if !valid {
			return torahindexcontract.ErrScopeChanged
		}
		return loaded()
	}
	if err = validate(); err != nil {
		return nil, nil, nil, err
	}
	deliver := func(visit func() error) error {
		if visit == nil {
			return torahindexcontract.ErrInvalidWitness
		}
		if !s.mu.TryLock() {
			return torahindexcontract.ErrSnapshotBusy
		}
		defer s.mu.Unlock()
		if s.isClosing.Load() || lifecycle.Err() != nil || s.ctx != lifecycle || s.spaceControllers[id] != ctrl {
			return torahindexcontract.ErrScopeChanged
		}
		// Do not call Mode/Current under the ACL fence: they acquire the state
		// machine lock. Its original loop closes the old loader BEFORE it
		// publishes any replacement process. The captured loaded-owner fence
		// checks that exact original component while preventing its cancel.
		return loadedDelivery(visit)
	}
	return sp, validate, deliver, nil
}
