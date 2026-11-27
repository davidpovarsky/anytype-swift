package export

import (
	"context"

	"github.com/anyproto/anytype-heart/core/block/cache"
	editorsb "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// withPrivateTorahExportGuard scopes the getter to this export operation. The
// service's shared getter is unchanged; the struct contains service references,
// not locks or mutable per-export state. Collection and context copies retain
// this boundary before a converter can inspect the private object's envelope.
func withPrivateTorahExportGuard(e *export) *export {
	if _, guarded := e.picker.(privateTorahExportGetter); guarded {
		return e
	}
	scoped := *e
	scoped.picker = privateTorahExportGetter{CachedObjectGetter: e.picker}
	return &scoped
}

// Embed the complete cached getter so TryRemoveFromCache keeps its original
// lifecycle and errors. This wrapper neither closes objects nor adds a load.
type privateTorahExportGetter struct {
	cache.CachedObjectGetter
}

func (g privateTorahExportGetter) GetObject(ctx context.Context, objectID string) (editorsb.SmartBlock, error) {
	object, err := g.CachedObjectGetter.GetObject(ctx, objectID)
	return publicTorahExportObject(object, err)
}

func (g privateTorahExportGetter) GetObjectByFullID(ctx context.Context, id domain.FullID) (editorsb.SmartBlock, error) {
	object, err := g.CachedObjectGetter.GetObjectByFullID(ctx, id)
	return publicTorahExportObject(object, err)
}

func publicTorahExportObject(object editorsb.SmartBlock, err error) (editorsb.SmartBlock, error) {
	if err != nil || object == nil {
		return object, err
	}
	if object.Type().IsOneOf(smartblock.SmartBlockTypePinkhaTorahOperations, smartblock.SmartBlockTypePinkhaTorahCutover) {
		return nil, torahopscontract.ErrPrivateOperation
	}
	return object, nil
}

var _ cache.CachedObjectGetter = privateTorahExportGetter{}
