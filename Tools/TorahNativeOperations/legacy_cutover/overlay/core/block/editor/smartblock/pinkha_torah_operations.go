package smartblock

import (
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/restriction"
	"github.com/anyproto/anytype-heart/core/block/source"
	"github.com/anyproto/anytype-heart/core/block/undo"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// InitTorahOperations initializes cache/lifecycle plumbing only. It intentionally
// does not call document Init, relation injection, block migrations, layout
// conversion, indexing or Apply. NativeHost owns the private durable state.
// The factory already holds the source tree lock.
func (sb *smartBlock) InitTorahOperations(ctx *InitContext) error {
	return sb.initPrivateTorah(ctx, coresb.SmartBlockTypePinkhaTorahOperations)
}

func (sb *smartBlock) InitTorahCutover(ctx *InitContext) error {
	return sb.initPrivateTorah(ctx, coresb.SmartBlockTypePinkhaTorahCutover)
}

func (sb *smartBlock) initPrivateTorah(ctx *InitContext, expected coresb.SmartBlockType) error {
	if ctx == nil || sb.space == nil || ctx.Source == nil || ctx.Source.Type() != expected ||
		ctx.Doc == nil || ctx.Doc.RootId() != ctx.Source.Id() || ctx.SpaceID != sb.space.Id() ||
		ctx.Source.SpaceID() != sb.space.Id() {
		return torahopscontract.ErrPrivateRoot
	}
	if ctx.State != nil && !ctx.State.IsEmpty(true) {
		return torahopscontract.ErrPrivateOperation
	}
	provider, ok := ctx.Source.(source.ObjectTreeProvider)
	if !ok {
		return torahopscontract.ErrPrivateRoot
	}
	doc, ok := ctx.Doc.(*state.State)
	if !ok {
		return torahopscontract.ErrPrivateRoot
	}
	sb.Doc, sb.source, sb.ObjectTree = doc, ctx.Source, provider.Tree()
	sb.undo = undo.NewHistory(0)
	sb.Doc.BlocksInit(doc)
	sb.restrictions = restriction.GetRestrictions(sb)
	ctx.State = sb.NewState()
	return nil
}
