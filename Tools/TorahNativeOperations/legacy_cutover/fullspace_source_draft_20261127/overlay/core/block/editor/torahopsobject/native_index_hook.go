package torahopsobject

import (
	"context"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
)

func bindNativeIndexHook(ctx context.Context, sb smartblock.SmartBlock, host interface {
	BindNativeIndexHookLocked(context.Context, torahops.NativeIndexHook) error
}) error {
	registration, ok := sb.(interface {
		PinkhaNativeIndexHook() (func(context.Context, objecttree.ObjectTree) error, error)
	})
	if !ok {
		return contract.ErrNotLoaded
	}
	hook, err := registration.PinkhaNativeIndexHook()
	if err != nil {
		return err
	}
	return host.BindNativeIndexHookLocked(ctx, torahops.NativeIndexHook(hook))
}
