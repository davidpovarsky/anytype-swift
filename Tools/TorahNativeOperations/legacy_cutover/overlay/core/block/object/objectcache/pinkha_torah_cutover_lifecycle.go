package objectcache

import (
	"context"
	"github.com/anyproto/any-sync/commonspace"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
)

// The separate metadata root has a distinct one-shot native creation guard.
// Its durable storage transaction alone holds the current account/source/ACL
// authority. Constructing the registered object follows after ACL unlock.
func (c *objectCache) createPinkhaTorahCutoverRoot(ctx context.Context, payload treestorage.TreeStorageCreatePayload, initFunc InitFunc) (smartblock.SmartBlock, error) {
	provider, ok := c.space.(interface{ CommonSpace() commonspace.Space })
	if !ok || provider.CommonSpace() == nil || provider.CommonSpace().Id() != c.space.Id() {
		return nil, torahcutoverroot.ErrPrivateOperation
	}
	spc := provider.CommonSpace()
	err := torahcutoverroot.CreateRootWithGuard(ctx, c.space.Id(), payload.RootRawChange.Id, func() error {
		_, err := spc.Storage().CreateTreeStorage(ctx, payload)
		return err
	})
	if err != nil {
		return nil, err
	}
	return c.GetObject(ContextWithCreateOption(ctx, initFunc), payload.RootRawChange.Id)
}
