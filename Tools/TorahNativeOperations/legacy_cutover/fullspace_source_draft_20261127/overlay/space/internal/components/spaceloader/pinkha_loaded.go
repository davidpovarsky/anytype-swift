package spaceloader

import (
	"reflect"

	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

// PinkhaLoaded snapshots only a finished original loader. In particular it does
// not call WaitLoad, start a load, or turn a persisted optimistic status into a
// native readiness claim. The returned validator must run after the read.
func PinkhaLoaded(component SpaceLoader) (clientspace.Space, func() error, torahindexcontract.DeliveryFence, error) {
	s, ok := component.(*spaceLoader)
	if !ok {
		return nil, nil, nil, torahindexcontract.ErrNotLoaded
	}
	s.mx.Lock()
	if s.ctx == nil || s.ctx.Err() != nil || s.loading == nil || s.space == nil || reflect.TypeOf(s.space).Kind() != reflect.Pointer {
		s.mx.Unlock()
		return nil, nil, nil, torahindexcontract.ErrNotLoaded
	}
	sp, loading, lifecycle := s.space, s.loading, s.ctx
	s.mx.Unlock()
	currentLocked := func() error {
		if lifecycle.Err() != nil || s.ctx != lifecycle || s.loading != loading || s.space != sp {
			return torahindexcontract.ErrScopeChanged
		}
		return nil
	}
	validate := func() error {
		s.mx.Lock()
		defer s.mx.Unlock()
		return currentLocked()
	}
	deliver := func(visit func() error) error {
		if visit == nil {
			return torahindexcontract.ErrInvalidWitness
		}
		if !s.mx.TryLock() {
			return torahindexcontract.ErrSnapshotBusy
		}
		defer s.mx.Unlock()
		if err := currentLocked(); err != nil {
			return err
		}
		return visit()
	}
	return sp, validate, deliver, nil
}
