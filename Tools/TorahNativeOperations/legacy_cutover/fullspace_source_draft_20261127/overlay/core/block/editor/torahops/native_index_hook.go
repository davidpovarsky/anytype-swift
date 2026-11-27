package torahops

import (
	"context"
	"errors"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
)

var ErrNativeIndexBehind = errors.New("native signed history is committed but its local index admission is behind")

// NativeIndexHook receives this exact locked native tree only after the signed
// store projection transaction has committed. It must not acquire another tree
// or resolve a current global account. It may return an index error; callers
// retain the original committed ChangeID/disposition/receipt alongside it.
type NativeIndexHook func(context.Context, objecttree.ObjectTree) error

func runNativeIndexHook(ctx context.Context, tree objecttree.ObjectTree, hook NativeIndexHook) error {
	if hook == nil {
		return nil
	}
	if err := hook(ctx, tree); err != nil {
		return errors.Join(ErrNativeIndexBehind, err)
	}
	return nil
}

// These binders are called once by the real adapter after Open returns and its
// ACL lock has been released. The original factory still holds this tree lock.
// Independent original host fixtures may leave the optional adapter hook nil.
func (h *NativeHost) BindNativeIndexHookLocked(ctx context.Context, hook NativeIndexHook) error {
	if h == nil || hook == nil || h.indexCommitted != nil {
		return ErrInvalid
	}
	h.indexCommitted = hook
	return runNativeIndexHook(ctx, h.tree, h.indexCommitted)
}

func (h *CutoverNativeHost) BindNativeIndexHookLocked(ctx context.Context, hook NativeIndexHook) error {
	if h == nil || hook == nil || h.indexCommitted != nil {
		return ErrInvalid
	}
	h.indexCommitted = hook
	return runNativeIndexHook(ctx, h.tree, h.indexCommitted)
}
