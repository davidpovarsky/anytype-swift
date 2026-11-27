package objectstore

import (
	"reflect"
	"sync"
	"sync/atomic"

	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
)

// AcquirePinkhaLoadedSpaceIndex borrows an existing native index and the original
// deletion drain counter. It never calls SpaceIndex/Init or creates a database.
// The caller validates after reading and releases exactly once, including errors.
func AcquirePinkhaLoadedSpaceIndex(component ObjectStore, id string) (spaceindex.Store, func() error, torahindexcontract.DeliveryFence, func(), error) {
	s, ok := component.(*dsObjectStore)
	if !ok || id == "" {
		return nil, nil, nil, nil, torahindexcontract.ErrNotLoaded
	}
	s.lock.Lock()
	store := s.spaceIndexes[id]
	_, deleted := s.deletedSpaceIds[id]
	if deleted || s.componentCtx == nil || s.componentCtx.Err() != nil || store == nil || reflect.TypeOf(store).Kind() != reflect.Pointer || s.crossSpaceDrained == nil {
		s.lock.Unlock()
		return nil, nil, nil, nil, torahindexcontract.ErrNotLoaded
	}
	lifecycle := s.componentCtx
	s.crossSpaceInflight++
	s.lock.Unlock()
	var released atomic.Bool
	var once sync.Once
	release := func() { once.Do(func() { released.Store(true); s.endCrossSpaceIteration() }) }
	currentLocked := func() error {
		_, deleted := s.deletedSpaceIds[id]
		if released.Load() || deleted || lifecycle.Err() != nil || s.componentCtx != lifecycle || s.spaceIndexes[id] != store {
			return torahindexcontract.ErrScopeChanged
		}
		return nil
	}
	validate := func() error {
		s.lock.Lock()
		defer s.lock.Unlock()
		return currentLocked()
	}
	deliver := func(visit func() error) error {
		if visit == nil {
			return torahindexcontract.ErrInvalidWitness
		}
		if !s.lock.TryLock() {
			return torahindexcontract.ErrSnapshotBusy
		}
		defer s.lock.Unlock()
		if err := currentLocked(); err != nil {
			return err
		}
		return visit()
	}
	return store, validate, deliver, release, nil
}
