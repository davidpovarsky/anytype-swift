package core

import (
	"context"
	"errors"
	"slices"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/core/block/object/objectcache"
	"github.com/anyproto/anytype-heart/core/domain"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

// A separate versioned native capability; existing v1 Append/Read endpoints and
// their signed tree never receive incompatible cutover metadata. Registration
// and generated wire mapping are qualified separately from these typed handlers.
const PinkhaTorahCutoverVersion uint32 = 1

type PinkhaTorahCutoverReadRequest struct {
	Version     uint32
	SpaceID     string
	ObjectID    string
	PropertyKey string
}
type PinkhaTorahCutoverSourceSnapshot struct {
	Source      torahops.CutoverLegacyValue
	SourceHeads []string
}

// No author/key/root/permission field is accepted from callers. Native derives
// the current signer and validates complete frozen source coverage and receipts.
type PinkhaTorahCutoverRecordRequest struct {
	PinkhaTorahCutoverReadRequest
	RecordID      string
	Kind          cutover.Kind
	PlanID        string
	Plan          *cutover.Plan
	FactID        string
	ImportClaimID string
	Imported      []cutover.Binding
	SourceHeads   []string
	NativeChanges []cutover.NativeWitness
	ImportRecords []string
}
type PinkhaTorahCutoverOperationRequest struct {
	PinkhaTorahCutoverReadRequest
	PlanID      string
	FactID      string
	OperationID string
	Kind        torahops.Kind
	BlockID     string
	Source      torahops.Source
	Payload     []byte
	Observed    []string
}

func validatePinkhaTorahCutoverRequest(ctx context.Context, req PinkhaTorahCutoverReadRequest) error {
	if req.Version != PinkhaTorahCutoverVersion {
		return torahops.ErrUnsupportedVersion
	}
	if ctx == nil || !pinkhaTorahText(req.SpaceID, true) || !pinkhaTorahText(req.ObjectID, true) || !pinkhaTorahText(req.PropertyKey, true) {
		return cutover.ErrInvalid
	}
	return ctx.Err()
}

func (scope *pinkhaTorahScope) cutoverSource(ctx context.Context, req PinkhaTorahCutoverReadRequest, write bool) (clientspace.Space, context.Context, func(), error) {
	if err := scope.current(ctx); err != nil {
		return nil, nil, nil, err
	}
	spc, err := scope.spaces.Get(ctx, req.SpaceID)
	if err != nil {
		return nil, nil, nil, err
	}
	if spc == nil || spc.Id() != req.SpaceID || spc.CommonSpace() == nil {
		return nil, nil, nil, torahcutoverroot.ErrPrivateRoot
	}
	if err = torahops.AuthorizeCurrentACL(spc.CommonSpace().Acl(), scope.key, write); err != nil {
		return nil, nil, nil, err
	}
	root, err := torahcutoverroot.Root(req.SpaceID)
	if err != nil {
		return nil, nil, nil, err
	}
	if err = validatePinkhaTorahTargetBeforeHost(ctx, spc, root.Id, torahops.Target{ObjectID: req.ObjectID}); err != nil {
		return nil, nil, nil, err
	}
	leaseCtx, release, err := torahopsobject.AcquireNativeCutoverSourceLease(ctx, spc, req.ObjectID, req.PropertyKey, write, spc.CommonSpace().Acl(), scope.current)
	if err != nil {
		return nil, nil, nil, err
	}
	if err = scope.current(leaseCtx); err != nil {
		release()
		return nil, nil, nil, err
	}
	return spc, leaseCtx, release, nil
}

// This read is available before explicit cutover. It leaves both native private
// roots and the exact legacy property untouched, even when either is absent.
func (mw *Middleware) NativeTorahCutoverSourceRead(ctx context.Context, req PinkhaTorahCutoverReadRequest) (PinkhaTorahCutoverSourceSnapshot, error) {
	if err := validatePinkhaTorahCutoverRequest(ctx, req); err != nil {
		return PinkhaTorahCutoverSourceSnapshot{}, err
	}
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return PinkhaTorahCutoverSourceSnapshot{}, err
	}
	defer scope.close()
	spc, held, release, err := scope.cutoverSource(ctx, req, false)
	if err != nil {
		return PinkhaTorahCutoverSourceSnapshot{}, err
	}
	defer release()
	acl := spc.CommonSpace().Acl()
	acl.RLock()
	defer acl.RUnlock()
	if err := torahops.AuthorizeHeldCurrentReadACL(acl, scope.key); err != nil {
		return PinkhaTorahCutoverSourceSnapshot{}, err
	}
	value, heads, err := torahopsobject.ReadNativeCutoverSource(held, spc, req.ObjectID, req.PropertyKey)
	if err = errors.Join(err, scope.current(held)); err != nil {
		return PinkhaTorahCutoverSourceSnapshot{}, err
	}
	return PinkhaTorahCutoverSourceSnapshot{Source: value, SourceHeads: heads}, nil
}

func (scope *pinkhaTorahScope) cutoverHosts(ctx context.Context, req PinkhaTorahCutoverReadRequest, write, create bool) (torahopsobject.CutoverStoreObject, torahopsobject.StoreObject, clientspace.Space, context.Context, func(), error) {
	spc, held, release, err := scope.cutoverSource(ctx, req, write)
	if err != nil {
		return nil, nil, nil, nil, nil, err
	}
	keep := false
	defer func() {
		if !keep {
			release()
		}
	}()
	metadataRoot, err := torahcutoverroot.Root(req.SpaceID)
	if err != nil {
		return nil, nil, nil, nil, nil, err
	}
	originalRoot, err := torahopscontract.Root(req.SpaceID)
	if err != nil {
		return nil, nil, nil, nil, nil, err
	}
	installGuard := func(install func() error) error {
		if !write {
			return list.ErrInsufficientPermissions
		}
		if err := scope.current(held); err != nil {
			return err
		}
		if err := torahopsobject.CheckNativeCutoverSourceLease(held, spc, metadataRoot.Id, req.ObjectID, req.PropertyKey, true); err != nil {
			return err
		}
		acl := spc.CommonSpace().Acl()
		acl.RLock()
		defer acl.RUnlock()
		if !acl.AclState().Permissions(scope.key.GetPublic()).CanWrite() {
			return list.ErrInsufficientPermissions
		}
		if err := scope.current(held); err != nil {
			return err
		}
		return install()
	}
	creationCtx := held
	if create {
		creationCtx = torahopscontract.WithRootCreationGuard(creationCtx, req.SpaceID, originalRoot.Id, installGuard)
		creationCtx = torahcutoverroot.WithRootCreationGuard(creationCtx, req.SpaceID, metadataRoot.Id, installGuard)
	}
	load := func(id string, kind coresb.SmartBlockType, version string) (smartblock.SmartBlock, error) {
		exists, err := spc.Storage().HasTree(held, id)
		if err != nil {
			return nil, err
		}
		if !exists && !create {
			return nil, ErrPinkhaTorahHistoryUnavailable
		}
		if exists {
			return spc.GetObject(held, id)
		}
		value, err := spc.DeriveTreeObject(creationCtx, objectcache.TreeDerivationParams{
			Key: domain.MustUniqueKey(kind, version), InitFunc: func(string) *smartblock.InitContext { return &smartblock.InitContext{} },
		})
		if errors.Is(err, treestorage.ErrTreeExists) {
			return spc.GetObject(held, id)
		}
		return value, err
	}
	original, err := load(originalRoot.Id, coresb.SmartBlockTypePinkhaTorahOperations, torahopscontract.UniqueKeyVersion)
	if err != nil {
		return nil, nil, nil, nil, nil, err
	}
	metadata, err := load(metadataRoot.Id, coresb.SmartBlockTypePinkhaTorahCutover, torahcutoverroot.UniqueKeyVersion)
	if err != nil {
		return nil, nil, nil, nil, nil, err
	}
	v1, originalOK := original.(torahopsobject.StoreObject)
	v2, metadataOK := metadata.(torahopsobject.CutoverStoreObject)
	if !originalOK || !metadataOK || v1.Id() != originalRoot.Id || v2.Id() != metadataRoot.Id ||
		v1.SpaceID() != req.SpaceID || v2.SpaceID() != req.SpaceID ||
		v1.Type() != coresb.SmartBlockTypePinkhaTorahOperations || v2.Type() != coresb.SmartBlockTypePinkhaTorahCutover {
		return nil, nil, nil, nil, nil, torahcutoverroot.ErrPrivateRoot
	}
	if err = scope.current(held); err != nil {
		return nil, nil, nil, nil, nil, err
	}
	keep = true
	return v2, v1, spc, held, release, nil
}

func (scope *pinkhaTorahScope) cutoverPost(ctx context.Context, spc clientspace.Space, write bool) error {
	if err := scope.current(ctx); err != nil {
		return err
	}
	if spc == nil || spc.CommonSpace() == nil {
		return torahcutoverroot.ErrPrivateRoot
	}
	if err := torahops.AuthorizeCurrentACL(spc.CommonSpace().Acl(), scope.key, write); err != nil {
		return err
	}
	return scope.current(ctx)
}

func (mw *Middleware) NativeTorahCutoverRead(ctx context.Context, req PinkhaTorahCutoverReadRequest) (torahops.CutoverNativeSnapshot, error) {
	if err := validatePinkhaTorahCutoverRequest(ctx, req); err != nil {
		return torahops.CutoverNativeSnapshot{}, err
	}
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return torahops.CutoverNativeSnapshot{}, err
	}
	defer scope.close()
	metadata, original, spc, held, release, err := scope.cutoverHosts(ctx, req, false, false)
	if err != nil {
		return torahops.CutoverNativeSnapshot{}, err
	}
	defer release()
	result, readErr := metadata.ReadTorahCutover(held, original, req.ObjectID, req.PropertyKey)
	if err = errors.Join(readErr, scope.cutoverPost(ctx, spc, false)); err != nil {
		return torahops.CutoverNativeSnapshot{}, err
	}
	return result, nil
}

func (mw *Middleware) NativeTorahCutoverAppend(ctx context.Context, req PinkhaTorahCutoverRecordRequest) (torahops.CutoverNativeAppendResult, error) {
	if err := validatePinkhaTorahCutoverRequest(ctx, req.PinkhaTorahCutoverReadRequest); err != nil {
		return torahops.CutoverNativeAppendResult{}, err
	}
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return torahops.CutoverNativeAppendResult{}, err
	}
	defer scope.close()
	record := cutover.Record{Version: cutover.Version, SpaceID: req.SpaceID, ObjectID: req.ObjectID,
		RecordID: req.RecordID, AuthorID: scope.key.GetPublic().Account(), Kind: req.Kind, PlanID: req.PlanID, Plan: req.Plan,
		FactID: req.FactID, ImportClaimID: req.ImportClaimID, Imported: slices.Clone(req.Imported), SourceHeads: slices.Clone(req.SourceHeads),
		NativeChanges: slices.Clone(req.NativeChanges), ImportRecords: slices.Clone(req.ImportRecords)}
	claim, _, err := cutover.Encode(record)
	if err != nil {
		return torahops.CutoverNativeAppendResult{}, err
	}
	record = claim.Record // canonical deep copy before any awaited native load.
	if record.Plan != nil {
		if record.Plan.PropertyKey != req.PropertyKey {
			return torahops.CutoverNativeAppendResult{}, cutover.ErrInvalid
		}
		// Full shared-codec coverage is a prerequisite to even installing the
		// private roots. The host checks it again against the held native value.
		if err = cutover.ValidateSourceCoverage(*record.Plan); err != nil {
			return torahops.CutoverNativeAppendResult{}, err
		}
	}
	metadata, original, spc, held, release, err := scope.cutoverHosts(ctx, req.PinkhaTorahCutoverReadRequest, true, record.Kind == cutover.Begin)
	if err != nil {
		return torahops.CutoverNativeAppendResult{}, err
	}
	defer release()
	result, appendErr := metadata.AppendTorahCutover(held, original, record)
	return result, errors.Join(appendErr, scope.cutoverPost(ctx, spc, true))
}

func (mw *Middleware) nativeTorahCutoverOperation(ctx context.Context, req PinkhaTorahCutoverOperationRequest, importing bool) (torahops.NativeAppendResult, error) {
	if err := validatePinkhaTorahCutoverRequest(ctx, req.PinkhaTorahCutoverReadRequest); err != nil {
		return torahops.NativeAppendResult{}, err
	}
	if !cutover.Hex(req.PlanID, 32) || (importing && !cutover.Hex(req.FactID, 32)) || (!importing && req.FactID != "") {
		return torahops.NativeAppendResult{}, cutover.ErrInvalid
	}
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return torahops.NativeAppendResult{}, err
	}
	defer scope.close()
	op := torahops.Operation{Version: torahops.Version, SpaceID: req.SpaceID, OperationID: req.OperationID,
		AuthorID: scope.key.GetPublic().Account(), Kind: req.Kind, Target: torahops.Target{ObjectID: req.ObjectID, BlockID: req.BlockID},
		Source: req.Source, Payload: slices.Clone(req.Payload), Observed: slices.Clone(req.Observed)}
	if _, err = op.CanonicalBytes(); err != nil {
		return torahops.NativeAppendResult{}, err
	}
	metadata, original, spc, held, release, err := scope.cutoverHosts(ctx, req.PinkhaTorahCutoverReadRequest, true, false)
	if err != nil {
		return torahops.NativeAppendResult{}, err
	}
	defer release()
	var result torahops.NativeAppendResult
	if importing {
		result, err = metadata.ImportTorahCutoverFact(held, original, req.PlanID, req.FactID, op)
	} else {
		result, err = metadata.AppendTorahCutoverAssociation(held, original, req.PlanID, op)
	}
	return result, errors.Join(err, scope.cutoverPost(ctx, spc, true))
}
func (mw *Middleware) NativeTorahCutoverImport(ctx context.Context, req PinkhaTorahCutoverOperationRequest) (torahops.NativeAppendResult, error) {
	return mw.nativeTorahCutoverOperation(ctx, req, true)
}
func (mw *Middleware) NativeTorahCutoverAssociationAppend(ctx context.Context, req PinkhaTorahCutoverOperationRequest) (torahops.NativeAppendResult, error) {
	return mw.nativeTorahCutoverOperation(ctx, req, false)
}
