package core

import (
	"context"
	"errors"
	"strings"
	"unicode/utf8"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/core/block/object/objectcache"
	"github.com/anyproto/anytype-heart/core/domain"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

// These typed native handlers are deliberately not registered in ClientCommands.
// The later generated protobuf endpoints must map their complete result/error
// contract. No App capability or startup creation is enabled by this file.
const PinkhaTorahOperationsVersion uint32 = 1

var (
	ErrPinkhaTorahAccountChanged     = errors.New("native Torah operation account changed")
	ErrPinkhaTorahHistoryUnavailable = errors.New("native Torah history is not materialized locally")
)

// Neither request accepts an author, private root ID, signing key or ACL verdict.
// Payload bytes must be reused exactly on retry; operation IDs are stable 16-byte
// lowercase hex values as defined by the native immutable operation contract.
type PinkhaTorahAppendRequest struct {
	Version     uint32
	SpaceID     string
	OperationID string
	Kind        torahops.Kind
	Target      torahops.Target
	Source      torahops.Source
	Payload     []byte
	Observed    []string
}

type PinkhaTorahReadRequest struct {
	Version uint32
	SpaceID string
	Target  torahops.Target
	Limit   uint
}

type pinkhaTorahScope struct {
	mw          *Middleware
	application *app.App
	spaces      space.Service
	key         crypto.PrivKey
}

func pinkhaTorahText(value string, required bool) bool {
	return (!required || value != "") && len(value) <= 1024 && utf8.ValidString(value) && !strings.ContainsRune(value, 0)
}

func validatePinkhaTorahRequest(ctx context.Context, version uint32, spaceID string, target torahops.Target) error {
	if version != PinkhaTorahOperationsVersion {
		return torahops.ErrUnsupportedVersion
	}
	if ctx == nil || !pinkhaTorahText(spaceID, true) || !pinkhaTorahText(target.ObjectID, true) || !pinkhaTorahText(target.BlockID, false) {
		return torahops.ErrInvalid
	}
	return ctx.Err()
}

func (mw *Middleware) pinkhaTorahScope() (*pinkhaTorahScope, error) {
	a := mw.GetApp()
	if a == nil {
		return nil, ErrNotLoggedIn
	}
	accounts, err := app.GetComponent[accountservice.Service](a)
	if err != nil {
		return nil, err
	}
	keys := accounts.Account()
	if keys == nil || keys.SignKey == nil {
		return nil, ErrNotLoggedIn
	}
	spaces, err := app.GetComponent[space.Service](a)
	if err != nil {
		return nil, err
	}
	return &pinkhaTorahScope{mw: mw, application: a, spaces: spaces, key: keys.SignKey}, nil
}

func (s *pinkhaTorahScope) current(ctx context.Context) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	if s.mw.GetApp() != s.application {
		return ErrPinkhaTorahAccountChanged
	}
	return nil
}

func (s *pinkhaTorahScope) host(ctx context.Context, spaceID string, target torahops.Target, create bool) (torahopsobject.StoreObject, error) {
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
	if err = torahops.AuthorizeCurrentACL(spc.CommonSpace().Acl(), s.key, create); err != nil {
		return nil, err
	}
	root, err := torahopscontract.Root(spaceID)
	if err != nil {
		return nil, err
	}
	// Resolve the actual native Page/Template and live block before an append
	// can create an empty root. The host checks the target again before writing.
	if err = torahopsobject.ValidateNativeTarget(ctx, spc, root.Id, target); err != nil {
		return nil, err
	}
	if err = s.current(ctx); err != nil {
		return nil, err
	}
	exists, err := spc.Storage().HasTree(ctx, root.Id)
	if err != nil {
		return nil, err
	}
	if !exists && !create {
		// Absence locally is not a proof that a remote client has no history.
		// Never report an empty synchronized snapshot or create a root on read.
		return nil, ErrPinkhaTorahHistoryUnavailable
	}
	var object smartblock.SmartBlock
	if exists {
		object, err = spc.GetObject(ctx, root.Id)
	} else {
		object, err = derivePinkhaTorahHost(ctx, spc)
		if errors.Is(err, treestorage.ErrTreeExists) {
			// Another authorized append may have created the same deterministic
			// root. Never replace its history or retry arbitrary creation errors.
			object, err = spc.GetObject(ctx, root.Id)
		}
	}
	if err != nil {
		return nil, err
	}
	host, ok := object.(torahopsobject.StoreObject)
	if !ok || host.Id() != root.Id || host.SpaceID() != spaceID || host.Type() != coresb.SmartBlockTypePinkhaTorahOperations {
		return nil, torahopscontract.ErrPrivateRoot
	}
	if err = s.current(ctx); err != nil {
		return nil, err
	}
	return host, nil
}

func derivePinkhaTorahHost(ctx context.Context, spc clientspace.Space) (smartblock.SmartBlock, error) {
	return spc.DeriveTreeObject(ctx, objectcache.TreeDerivationParams{
		Key:      domain.MustUniqueKey(coresb.SmartBlockTypePinkhaTorahOperations, torahopscontract.UniqueKeyVersion),
		InitFunc: func(string) *smartblock.InitContext { return &smartblock.InitContext{} },
	})
}

// NativeTorahOperationAppend preserves the receipt even when the signed change
// is durable but projection recovery fails. A non-nil error MUST be surfaced;
// Created with ErrProjectionBehind is not synchronized acceptance. An idempotent
// retry and an operation-ID collision retain their distinct native dispositions.
func (mw *Middleware) NativeTorahOperationAppend(ctx context.Context, req PinkhaTorahAppendRequest) (torahops.NativeAppendResult, error) {
	if err := validatePinkhaTorahRequest(ctx, req.Version, req.SpaceID, req.Target); err != nil {
		return torahops.NativeAppendResult{}, err
	}
	scope, err := mw.pinkhaTorahScope()
	if err != nil {
		return torahops.NativeAppendResult{}, err
	}
	op := torahops.Operation{Version: torahops.Version, SpaceID: req.SpaceID, OperationID: req.OperationID,
		AuthorID: scope.key.GetPublic().Account(), Kind: req.Kind, Target: req.Target, Source: req.Source,
		Payload: append([]byte{}, req.Payload...), Observed: append([]string{}, req.Observed...)}
	if _, err = op.CanonicalBytes(); err != nil {
		return torahops.NativeAppendResult{}, err
	}
	host, err := scope.host(ctx, req.SpaceID, req.Target, true)
	if err != nil {
		return torahops.NativeAppendResult{}, err
	}
	result, appendErr := host.AppendTorahOperation(ctx, op)
	return result, errors.Join(appendErr, scope.current(ctx))
}

// NativeTorahTargetRead never creates a root or changes signed history. Opening
// an existing host may rebuild its derived local projection from verified native
// changes. This is not a remote synchronization barrier. AppliedSeq is local,
// and exceeding Limit returns an error instead of a truncated successful view.
func (mw *Middleware) NativeTorahTargetRead(ctx context.Context, req PinkhaTorahReadRequest) (torahops.NativeSnapshot, error) {
	if err := validatePinkhaTorahRequest(ctx, req.Version, req.SpaceID, req.Target); err != nil {
		return torahops.NativeSnapshot{}, err
	}
	if req.Limit == 0 || req.Limit > 10000 {
		return torahops.NativeSnapshot{}, torahops.ErrInvalid
	}
	scope, err := mw.pinkhaTorahScope()
	if err != nil {
		return torahops.NativeSnapshot{}, err
	}
	host, err := scope.host(ctx, req.SpaceID, req.Target, false)
	if err != nil {
		return torahops.NativeSnapshot{}, err
	}
	result, readErr := host.ReadTorahTarget(ctx, req.Target, req.Limit)
	if err = errors.Join(readErr, scope.current(ctx)); err != nil {
		return torahops.NativeSnapshot{}, err
	}
	return result, nil
}
