package core

import (
	"context"
	"errors"
	"strings"
	"sync/atomic"
	"unicode/utf8"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
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
	application *app.App
	spaces      space.Service
	key         crypto.PrivKey
	releaseApp  func()
	leaseActive atomic.Bool
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

func (mw *Middleware) pinkhaTorahScope(ctx context.Context) (*pinkhaTorahScope, error) {
	a, release, err := mw.applicationService.LeasePinkhaTorahApp(ctx)
	if err != nil {
		return nil, err
	}
	if a == nil {
		return nil, ErrNotLoggedIn
	}
	keepLease := false
	defer func() {
		if !keepLease {
			release()
		}
	}()
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
	scope := &pinkhaTorahScope{application: a, spaces: spaces, key: keys.SignKey, releaseApp: release}
	scope.leaseActive.Store(true)
	keepLease = true
	return scope, nil
}

func (s *pinkhaTorahScope) current(ctx context.Context) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	// The outer application RLock prevents Stop/AccountSelect from changing
	// this app. Never call GetApp here: a waiting writer makes nested RLock
	// deadlock while shutdown waits for the target/settings locks we own.
	if !s.leaseActive.Load() {
		return ErrPinkhaTorahAccountChanged
	}
	return nil
}

func (s *pinkhaTorahScope) close() {
	if s.leaseActive.CompareAndSwap(true, false) {
		s.releaseApp()
	}
}

func (s *pinkhaTorahScope) host(ctx context.Context, spaceID string, target torahops.Target, write, create bool) (torahopsobject.StoreObject, context.Context, func(), error) {
	if err := s.current(ctx); err != nil {
		return nil, nil, nil, err
	}
	spc, err := s.spaces.Get(ctx, spaceID)
	if err != nil {
		return nil, nil, nil, err
	}
	if spc == nil || spc.Id() != spaceID || spc.CommonSpace() == nil {
		return nil, nil, nil, torahopscontract.ErrPrivateRoot
	}
	if err = torahops.AuthorizeCurrentACL(spc.CommonSpace().Acl(), s.key, write); err != nil {
		return nil, nil, nil, err
	}
	root, err := torahopscontract.Root(spaceID)
	if err != nil {
		return nil, nil, nil, err
	}
	// Bound remote loading before taking lifecycle locks. The later native
	// lease validates the current target and settings through durable commit.
	if err = validatePinkhaTorahTargetBeforeHost(ctx, spc, root.Id, target); err != nil {
		return nil, nil, nil, err
	}
	if err = s.current(ctx); err != nil {
		return nil, nil, nil, err
	}
	leaseCtx, release, err := torahopsobject.AcquireNativeTargetLease(ctx, spc, root.Id, target)
	if err != nil {
		return nil, nil, nil, err
	}
	keepLease := false
	defer func() {
		if !keepLease {
			release()
		}
	}()
	ctx = leaseCtx
	if create {
		ctx = torahopscontract.WithRootCreationGuard(ctx, spaceID, root.Id, func(install func() error) error {
			if err := s.current(leaseCtx); err != nil {
				return err
			}
			if err := torahopsobject.CheckNativeTargetLease(leaseCtx, spc, root.Id, target); err != nil {
				return err
			}
			acl := spc.CommonSpace().Acl()
			acl.RLock()
			defer acl.RUnlock()
			if !acl.AclState().Permissions(s.key.GetPublic()).CanWrite() {
				return list.ErrInsufficientPermissions
			}
			if err := s.current(leaseCtx); err != nil {
				return err
			}
			// Only the durable root storage transaction runs inside this ACL
			// hold. Registry construction follows after it has been released.
			return install()
		})
	}
	exists, err := spc.Storage().HasTree(ctx, root.Id)
	if err != nil {
		return nil, nil, nil, err
	}
	if !exists && !create {
		// Absence locally is not a proof that a remote client has no history.
		// Never report an empty synchronized snapshot or create a root on read.
		// Remove/Replace require observed predecessors and cannot be the first
		// local operation; an absent history must not create an empty journal.
		return nil, nil, nil, ErrPinkhaTorahHistoryUnavailable
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
		return nil, nil, nil, err
	}
	host, ok := object.(torahopsobject.StoreObject)
	if !ok || host.Id() != root.Id || host.SpaceID() != spaceID || host.Type() != coresb.SmartBlockTypePinkhaTorahOperations {
		return nil, nil, nil, torahopscontract.ErrPrivateRoot
	}
	if err = s.current(ctx); err != nil {
		return nil, nil, nil, err
	}
	keepLease = true
	return host, ctx, release, nil
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
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return torahops.NativeAppendResult{}, err
	}
	defer scope.close()
	op := torahops.Operation{Version: torahops.Version, SpaceID: req.SpaceID, OperationID: req.OperationID,
		AuthorID: scope.key.GetPublic().Account(), Kind: req.Kind, Target: req.Target, Source: req.Source,
		Payload: append([]byte{}, req.Payload...), Observed: append([]string{}, req.Observed...)}
	if _, err = op.CanonicalBytes(); err != nil {
		return torahops.NativeAppendResult{}, err
	}
	host, hostCtx, release, err := scope.host(ctx, req.SpaceID, req.Target, true, req.Kind == torahops.Add)
	if err != nil {
		return torahops.NativeAppendResult{}, err
	}
	defer release()
	result, appendErr := host.AppendTorahOperation(hostCtx, op)
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
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return torahops.NativeSnapshot{}, err
	}
	defer scope.close()
	host, hostCtx, release, err := scope.host(ctx, req.SpaceID, req.Target, false, false)
	if err != nil {
		return torahops.NativeSnapshot{}, err
	}
	defer release()
	result, readErr := host.ReadTorahTarget(hostCtx, req.Target, req.Limit)
	if err = errors.Join(readErr, scope.current(ctx)); err != nil {
		return torahops.NativeSnapshot{}, err
	}
	return result, nil
}
