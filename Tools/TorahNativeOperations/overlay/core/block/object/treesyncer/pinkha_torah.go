package treesyncer

import (
	"context"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/settings"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// PinkhaTorahSettingsTree exposes the already registered reserved settings
// object. Building another SyncTree over its storage would not share the mutex
// used by DeleteObject and incoming settings changes, and cannot be a lease.
func (t *treeSyncer) PinkhaTorahSettingsTree(ctx context.Context) (objecttree.ObjectTree, error) {
	if ctx == nil || t.mainCtx == nil || t.treeManager == nil || t.spaceSettingsId == "" {
		return nil, torahopscontract.ErrPrivateOperation
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if err := t.mainCtx.Err(); err != nil {
		return nil, err
	}
	tree, err := t.treeManager.GetTree(ctx, t.spaceId, t.spaceSettingsId)
	if err != nil {
		return nil, err
	}
	reserved, ok := tree.(settings.SettingsObject)
	if !ok || reserved == nil || reserved.Id() != t.spaceSettingsId {
		return nil, torahopscontract.ErrPrivateOperation
	}
	return reserved, nil
}
