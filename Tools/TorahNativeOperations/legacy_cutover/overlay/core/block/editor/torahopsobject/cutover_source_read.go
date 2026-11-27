package torahopsobject

import (
	"bytes"
	"context"
	"slices"

	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
)

// ReadNativeCutoverSource returns only the exact held live source. The native
// application entry independently holds current read ACL authority. It does not
// install either private root or assert that a remote operation history is empty.
func ReadNativeCutoverSource(ctx context.Context, space smartblock.Space, objectID, propertyKey string) (torahops.CutoverLegacyValue, []string, error) {
	if ctx == nil || space == nil {
		return torahops.CutoverLegacyValue{}, nil, cutover.ErrInvalid
	}
	root, err := torahcutoverroot.Root(space.Id())
	if err != nil {
		return torahops.CutoverLegacyValue{}, nil, err
	}
	if err = CheckNativeCutoverSourceLease(ctx, space, root.Id, objectID, propertyKey, false); err != nil {
		return torahops.CutoverLegacyValue{}, nil, err
	}
	lease := ctx.Value(cutoverSourceLeaseKey{}).(*cutoverSourceLease)
	return torahops.CutoverLegacyValue{Key: lease.value.Key, Present: lease.value.Present, Bytes: bytes.Clone(lease.value.Bytes)}, slices.Clone(lease.heads), nil
}
