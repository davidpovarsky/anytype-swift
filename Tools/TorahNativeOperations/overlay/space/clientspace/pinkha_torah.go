package clientspace

import (
	"context"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

func (s *space) PinkhaTorahSettingsTree(ctx context.Context) (objecttree.ObjectTree, error) {
	if s.common == nil {
		return nil, torahopscontract.ErrPrivateOperation
	}
	provider, ok := s.common.TreeSyncer().(interface {
		PinkhaTorahSettingsTree(context.Context) (objecttree.ObjectTree, error)
	})
	if !ok {
		return nil, torahopscontract.ErrPrivateOperation
	}
	tree, err := provider.PinkhaTorahSettingsTree(ctx)
	if err != nil {
		return nil, err
	}
	if tree == nil || tree.Id() != s.common.Storage().StateStorage().SettingsId() {
		return nil, torahopscontract.ErrPrivateOperation
	}
	return tree, nil
}

func (s *space) PinkhaTorahTargetIsCurrent(sb smartblock.SmartBlock) bool {
	cache, ok := s.Cache.(interface {
		PinkhaTorahTargetIsCurrent(smartblock.SmartBlock) bool
	})
	return ok && cache.PinkhaTorahTargetIsCurrent(sb)
}
