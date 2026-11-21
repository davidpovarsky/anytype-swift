package core

import (
	"context"
	"encoding/hex"
	"errors"
	"strings"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// Target, author, private root, signing keys and authorization are not request
// fields. The current owned account derives them from verified native history.
type PinkhaTorahAuthorizedOperationReadRequest struct {
	Version     uint32
	SpaceID     string
	OperationID string
}

func validatePinkhaTorahOperationRead(ctx context.Context, req PinkhaTorahAuthorizedOperationReadRequest) error {
	if req.Version != torahops.AuthorizedOperationReadVersion {
		return torahops.ErrUnsupportedVersion
	}
	if ctx == nil || !pinkhaTorahText(req.SpaceID, true) || len(req.OperationID) != 32 || req.OperationID != strings.ToLower(req.OperationID) {
		return torahops.ErrInvalid
	}
	if _, err := hex.DecodeString(req.OperationID); err != nil {
		return torahops.ErrInvalid
	}
	return ctx.Err()
}

// operationReadHost is existing-only and does not reuse host's live-target or
// root-creation path. Candidate targets are discovered under the private tree's
// current ACL first, then authorized together by the native object adapter.
func (s *pinkhaTorahScope) operationReadHost(ctx context.Context, spaceID string) (torahopsobject.AuthorizedOperationStoreObject, error) {
	if err := s.current(ctx); err != nil {
		return nil, err
	}
	spc, err := s.spaces.Get(ctx, spaceID)
	if err != nil {
		return nil, err
	}
	if spc == nil || spc.Id() != spaceID || spc.CommonSpace() == nil {
		return nil, torahopscontract.ErrPrivateRoot
	}
	if err = torahops.AuthorizeCurrentACL(spc.CommonSpace().Acl(), s.key, false); err != nil {
		return nil, err
	}
	root, err := torahopscontract.Root(spaceID)
	if err != nil {
		return nil, err
	}
	exists, err := spc.Storage().HasTree(ctx, root.Id)
	if err != nil {
		return nil, err
	}
	if !exists {
		return nil, ErrPinkhaTorahHistoryUnavailable
	}
	// Never derive a missing root or turn missing local history into absence.
	object, err := spc.GetObject(ctx, root.Id)
	if err != nil {
		return nil, err
	}
	host, ok := object.(torahopsobject.AuthorizedOperationStoreObject)
	if !ok || host.Id() != root.Id || host.SpaceID() != spaceID || host.Type() != coresb.SmartBlockTypePinkhaTorahOperations {
		return nil, torahopscontract.ErrPrivateRoot
	}
	if err = s.current(ctx); err != nil {
		return nil, err
	}
	return host, nil
}

func (mw *Middleware) NativeTorahAuthorizedOperationRead(ctx context.Context, req PinkhaTorahAuthorizedOperationReadRequest) (torahops.AuthorizedOperationSnapshot, error) {
	if err := validatePinkhaTorahOperationRead(ctx, req); err != nil {
		return torahops.AuthorizedOperationSnapshot{}, err
	}
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return torahops.AuthorizedOperationSnapshot{}, err
	}
	defer scope.close()
	host, err := scope.operationReadHost(ctx, req.SpaceID)
	if err != nil {
		return torahops.AuthorizedOperationSnapshot{}, err
	}
	result, err := host.ReadAuthorizedTorahOperation(ctx, req.OperationID)
	if err = errors.Join(err, scope.current(ctx), ctx.Err()); err != nil {
		return torahops.AuthorizedOperationSnapshot{}, err
	}
	if result.AccountID != scope.key.GetPublic().Account() || result.SpaceID != req.SpaceID || result.OperationID != req.OperationID {
		return torahops.AuthorizedOperationSnapshot{}, torahops.ErrInvalid
	}
	return result, nil
}
