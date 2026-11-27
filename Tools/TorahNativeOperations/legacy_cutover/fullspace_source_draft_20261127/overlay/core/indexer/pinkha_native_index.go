package indexer

import (
	"context"
	"errors"

	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
)

// IndexPinkhaNative uses the original queue and transaction worker, bound to the
// exact index instance captured by the original account's object adapter. It
// never calls SpaceIndex (which may create/rebind an index) or a global owner.
func (i *indexer) IndexPinkhaNative(ctx context.Context, info smartblock.DocInfo, expected spaceindex.Store) error {
	if ctx == nil || i.runCtx == nil || info.Space == nil || expected == nil || info.PinkhaIndexOwner != expected {
		return contract.ErrNotLoaded
	}
	if err := errors.Join(ctx.Err(), i.runCtx.Err()); err != nil {
		return err
	}
	if info.PinkhaNativeAdmissionError != nil {
		return info.PinkhaNativeAdmissionError
	}
	if info.PinkhaNativeAdmission == nil {
		return contract.ErrInvalidWitness
	}
	store, current, _, release, err := objectstore.AcquirePinkhaLoadedSpaceIndex(i.store, info.Space.Id())
	if err != nil {
		return err
	}
	defer release()
	if store != expected {
		return contract.ErrScopeChanged
	}
	i.lock.Lock()
	if err = i.runCtx.Err(); err != nil {
		i.lock.Unlock()
		return err
	}
	spaceInd := i.spaceIndexers[info.Space.Id()]
	if spaceInd == nil {
		spaceInd = newSpaceIndexer(i.runCtx, expected, i.store, i.isFulltextEnabled(info.Space))
		i.spaceIndexers[info.Space.Id()] = spaceInd
	}
	if spaceInd.spaceIndex != expected || spaceInd.objectStore != i.store {
		i.lock.Unlock()
		return contract.ErrScopeChanged
	}
	i.lock.Unlock()
	if err = errors.Join(current(), ctx.Err()); err != nil {
		return err
	}
	// Once accepted, the original queue owns its transaction; cancellation does
	// not invent a zero-effect result or move this task into a new account run.
	err = spaceInd.Index(info)
	return errors.Join(err, current(), ctx.Err())
}
