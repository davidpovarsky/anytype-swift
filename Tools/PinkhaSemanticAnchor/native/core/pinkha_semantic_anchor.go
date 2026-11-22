package core

import (
	"context"
	"errors"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
)

type nativeSemanticAnchorEditor interface {
	CaptureSemanticAnchor(context.Context, session.Context, semanticanchor.CaptureRequest) (semanticanchor.Receipt, error)
}

// NativeSemanticAnchorCapture is a typed native seam only. There is no generated
// command registration or runtime/App capability in this change. Shipping stays
// unavailable until native, complete wire and mounted Apple acceptance pass.
// The request cannot select an account, signer, ACL verdict or native pointer.
func (mw *Middleware) NativeSemanticAnchorCapture(ctx context.Context, sessionCtx session.Context,
	request semanticanchor.CaptureRequest) (semanticanchor.Receipt, error) {
	empty := semanticanchor.Receipt{}
	if ctx == nil || sessionCtx == nil {
		return empty, semanticanchor.ErrInvalid
	}
	if _, err := request.Validate(); err != nil {
		return empty, err
	}
	if err := ctx.Err(); err != nil {
		return empty, err
	}
	// This is the previously qualified writer lifetime, acquired before any
	// native preload or object lock. No GetApp or read-publication lease is used
	// from inside this scope; AccountStop/AccountSelect wait on its writer side.
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return empty, err
	}
	defer scope.close()
	space, err := scope.spaces.Get(ctx, request.SpaceID)
	if err != nil {
		return empty, err
	}
	if space == nil || space.Id() != request.SpaceID || space.CommonSpace() == nil {
		return empty, semanticanchor.ErrUnavailable
	}
	if err = torahops.AuthorizeCurrentACL(space.CommonSpace().Acl(), scope.key, true); err != nil {
		return empty, err
	}
	leaseCtx, object, release, err := torahopsobject.AcquireNativeSemanticAnchorLease(ctx, space, scope.key.GetPublic(), request)
	if err != nil {
		return empty, err
	}
	defer release()
	if err = scope.current(ctx); err != nil {
		return empty, err
	}
	editor, ok := object.(nativeSemanticAnchorEditor)
	if !ok {
		return empty, semanticanchor.ErrUnavailable
	}
	result, err := editor.CaptureSemanticAnchor(leaseCtx, sessionCtx, request)
	if err != nil {
		return empty, err
	}
	if err = scope.current(ctx); err != nil {
		return empty, errors.Join(semanticanchor.ErrUncertain, err)
	}
	if err = torahops.AuthorizeCurrentACL(space.CommonSpace().Acl(), scope.key, true); err != nil {
		return empty, errors.Join(semanticanchor.ErrUncertain, err)
	}
	return result, nil
}
