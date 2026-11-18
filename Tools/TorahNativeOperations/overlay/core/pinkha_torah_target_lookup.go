package core

import (
	"context"
	"errors"
	"time"

	"github.com/anyproto/any-sync/net/peer"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
)

// Bound native peer discovery and target loading before opening the private
// host. An earlier caller deadline and its cancellation remain authoritative.
// This does not make the subsequent native SmartBlock lock cancellable.
const pinkhaTorahTargetLookupTimeout = 15 * time.Second

func validatePinkhaTorahTargetBeforeHost(ctx context.Context, space smartblock.Space, privateID string, target torahops.Target) error {
	loadCtx, cancel := context.WithTimeout(ctx, pinkhaTorahTargetLookupTimeout)
	defer cancel()
	if _, err := peer.CtxPeerId(loadCtx); errors.Is(err, peer.ErrPeerIdNotFoundInContext) {
		// This is the native routing hint used by Heart's ordinary remote tree
		// loader. It grants no account, Space, target or private-root authority.
		loadCtx = peer.CtxWithPeerId(loadCtx, peer.CtxResponsiblePeers)
	}
	return torahopsobject.ValidateNativeTarget(loadCtx, space, privateID, target)
}
