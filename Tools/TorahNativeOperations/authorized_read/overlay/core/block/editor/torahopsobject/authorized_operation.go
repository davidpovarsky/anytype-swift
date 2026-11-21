package torahopsobject

import (
	"context"
	"errors"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// Separate extension preserves existing StoreObject implementers and write/read
// semantics. Only an actual private object with its owned NativeHost implements it.
type AuthorizedOperationStoreObject interface {
	StoreObject
	ReadAuthorizedTorahOperation(context.Context, string) (torahops.AuthorizedOperationSnapshot, error)
}

func (o *object) ReadAuthorizedTorahOperation(ctx context.Context, operationID string) (torahops.AuthorizedOperationSnapshot, error) {
	if o.host == nil {
		return torahops.AuthorizedOperationSnapshot{}, torahopscontract.ErrPrivateOperation
	}
	loader, ok := o.space.(nativeTargetSpace)
	if !ok {
		return torahops.AuthorizedOperationSnapshot{}, ErrTargetUnavailable
	}
	current := func(check context.Context) error {
		if check == nil {
			return torahops.ErrInvalid
		}
		if err := check.Err(); err != nil {
			return err
		}
		// The cache owns this wrapper, not the embedded generic SmartBlock.
		// Peek is nonblocking and excludes closing/replaced native instances.
		if !loader.PinkhaTorahTargetIsCurrent(o) {
			return torahopscontract.ErrPrivateOperation
		}
		return nil
	}
	lease := func(check context.Context, targets []torahops.Target) (torahops.OperationTargetLease, error) {
		if err := current(check); err != nil {
			return torahops.OperationTargetLease{}, err
		}
		result, err := AcquireNativeOperationTargetsLease(check, o.space, o.Id(), targets)
		if errors.Is(err, ErrTargetUnavailable) {
			err = errors.Join(torahops.ErrOperationTargetUnavailable, err)
		}
		return result, err
	}
	return o.host.ReadAuthorizedOperation(ctx, operationID, lease, current)
}
