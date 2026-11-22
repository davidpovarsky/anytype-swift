package core

import (
	"context"
	"errors"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pb"
)

// The coherent candidate uses the same native publication fence as
// ObjectSearch/ObjectShow. No owner, ACL verdict, or callback is caller supplied.
type pinkhaOperationReadPublication interface {
	acquirePublication(context.Context) (func(), error)
}

type pinkhaPreparedOperationRead struct {
	value       torahops.AuthorizedOperationSnapshot
	readOwner   *pinkhaTorahScope
	publication pinkhaOperationReadPublication
}

// The existing App lease protects native target/private-history preparation.
// It is released before this function returns, along with every object/settings
// lease owned by the read. Final publication must never recursively acquire the
// App RLock: an AccountStop/Select writer may already be waiting for it.
func (mw *Middleware) preparePinkhaAuthorizedOperationRead(ctx context.Context, req PinkhaTorahAuthorizedOperationReadRequest) (pinkhaPreparedOperationRead, error) {
	if err := validatePinkhaTorahOperationRead(ctx, req); err != nil {
		return pinkhaPreparedOperationRead{}, err
	}
	owner, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return pinkhaPreparedOperationRead{}, err
	}
	defer owner.close()
	publication, err := mw.pinkhaBeginCurrentSpaceRead(ctx, owner.application, req.SpaceID, "")
	if err != nil {
		return pinkhaPreparedOperationRead{}, pinkhaOperationPublicationError(err)
	}
	host, err := owner.operationReadHost(ctx, req.SpaceID)
	if err != nil {
		return pinkhaPreparedOperationRead{}, err
	}
	result, err := host.ReadAuthorizedTorahOperation(ctx, req.OperationID)
	if err = errors.Join(err, owner.current(ctx), ctx.Err()); err != nil {
		return pinkhaPreparedOperationRead{}, err
	}
	if result.AccountID != owner.key.GetPublic().Account() || result.SpaceID != req.SpaceID || result.OperationID != req.OperationID {
		return pinkhaPreparedOperationRead{}, torahops.ErrInvalid
	}
	return pinkhaPreparedOperationRead{value: result, readOwner: owner, publication: publication}, nil
}

// Only the native fence's exact typed errors gain the existing T2 wire meanings.
// Transient errors and arbitrary descriptions never become authority denials.
func pinkhaOperationPublicationError(err error) error {
	switch {
	case errors.Is(err, errPinkhaCurrentReadDenied):
		return errors.Join(list.ErrInsufficientPermissions, err)
	case errors.Is(err, errPinkhaCurrentReadInvalidated):
		return errors.Join(torahops.ErrOperationSnapshotChanged, err)
	default:
		return err
	}
}

func (p pinkhaPreparedOperationRead) acquirePublication(ctx context.Context) (func(), error) {
	if ctx == nil {
		return nil, torahops.ErrInvalid
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	// This explicit ownership barrier also fails closed if a future caller moves
	// finalization inside the old read lease. It cannot hang on a nested RLock.
	if p.readOwner == nil || p.readOwner.leaseActive.Load() || p.publication == nil {
		return nil, torahops.ErrOperationSnapshotChanged
	}
	release, err := p.publication.acquirePublication(ctx)
	if err != nil {
		return nil, pinkhaOperationPublicationError(err)
	}
	if release == nil {
		return nil, torahops.ErrOperationSnapshotChanged
	}
	if err := ctx.Err(); err != nil {
		release()
		return nil, err
	}
	return release, nil
}

func (p pinkhaPreparedOperationRead) snapshot(ctx context.Context) (torahops.AuthorizedOperationSnapshot, error) {
	release, err := p.acquirePublication(ctx)
	if err != nil {
		return torahops.AuthorizedOperationSnapshot{}, err
	}
	defer release()
	return p.value, nil
}

func (p pinkhaPreparedOperationRead) wire(ctx context.Context) *pb.PinkhaTorahAuthorizedOperationReadResponse {
	// Complete copying, validation, and size checks before acquiring final
	// App->Space-publication->ACL leases. No native service is called while held.
	response := pinkhaAuthorizedOperationReadToWire(p.value, nil)
	if response.Error.Code != pb.PinkhaTorahAuthorizedOperationReadResponseError_NULL {
		return response
	}
	release, err := p.acquirePublication(ctx)
	if err != nil {
		return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, err)
	}
	defer release()
	return response
}
