package objectcache

import (
	"context"

	"github.com/anyproto/any-sync/app/ocache"
	"github.com/anyproto/any-sync/commonspace"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// Called while the target's own mutex is held. Peek never loads or waits for a
// close, avoiding the cache-close -> SmartBlock lock inversion. A closing or
// replaced object cannot authorize a private write using its stale State.
func (c *objectCache) PinkhaTorahTargetIsCurrent(sb smartblock.SmartBlock) bool {
	if sb == nil || c.cache == nil {
		return false
	}
	select {
	case <-c.closing:
		return false
	default:
	}
	peeker, ok := c.cache.(ocache.Peeker)
	if !ok {
		return false
	}
	current, state := peeker.Peek(sb.Id(), true)
	return state == ocache.PeekHit && current == sb
}

// A private empty root is installed under the account/target/ACL creation
// guard. Do not wrap generic PutTree in an ACL lock: its subsequent tree build
// takes the ACL lock again. Open through the private source registry only after
// the actual CreateTreeStorage transaction and its guard have returned.
func (c *objectCache) createPinkhaTorahRoot(ctx context.Context, payload treestorage.TreeStorageCreatePayload, initFunc InitFunc) (smartblock.SmartBlock, error) {
	provider, ok := c.space.(interface{ CommonSpace() commonspace.Space })
	if !ok || provider.CommonSpace() == nil || provider.CommonSpace().Id() != c.space.Id() {
		return nil, torahopscontract.ErrPrivateOperation
	}
	spc := provider.CommonSpace()
	err := torahopscontract.CreateRootWithGuard(ctx, c.space.Id(), payload.RootRawChange.Id, func() error {
		_, err := spc.Storage().CreateTreeStorage(ctx, payload)
		return err
	})
	if err != nil {
		return nil, err
	}
	return c.GetObject(ContextWithCreateOption(ctx, initFunc), payload.RootRawChange.Id)
}
