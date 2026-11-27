package core

import (
	"context"
	"errors"
	"slices"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
)

// This typed native boundary is additive. A generated wire endpoint may expose
// it only after qualifying this complete result/error contract. Neither a row
// readiness bit nor a successful asynchronous reindex request enables it.
type PinkhaTorahSpaceIndexRequest struct {
	Version             uint32
	NativeSchemaVersion uint32
	SpaceID             string
	CanonicalKey        string
}

// NativeTorahSpaceIndexReadiness proves a bounded CURRENT LOCAL native snapshot.
// It does not prove remote convergence or query result coverage. Consumers need
// complete before/after results with equal generation and the same owner/scope,
// plus a separate nontruncation proof for their intervening related query.
//
// This call never starts a Space, creates a root/index, queues a write or repairs
// an index. Unloaded/oversized/failed snapshots return typed errors and no prefix
// result. A fully captured but stale/unsupported projection returns incomplete.
func (mw *Middleware) NativeTorahSpaceIndexReadiness(ctx context.Context, req PinkhaTorahSpaceIndexRequest) (result contract.Result, err error) {
	if ctx == nil || req.Version != contract.Version || req.NativeSchemaVersion != contract.Version ||
		!pinkhaTorahText(req.SpaceID, true) || !pinkhaTorahText(req.CanonicalKey, true) {
		return result, torahops.ErrInvalid
	}
	if err = ctx.Err(); err != nil {
		return result, err
	}
	scope, err := mw.pinkhaTorahScope(ctx)
	if err != nil {
		return result, err
	}
	defer scope.close()
	spc, spaceCurrent, spaceDelivery, err := space.PinkhaLoadedSpace(scope.spaces, req.SpaceID)
	if err != nil {
		return result, err
	}
	if spc == nil || spc.CommonSpace() == nil || spc.Storage() == nil {
		return result, contract.ErrNotLoaded
	}
	store, err := app.GetComponent[objectstore.ObjectStore](scope.application)
	if err != nil {
		return result, err
	}
	index, indexCurrent, indexDelivery, releaseIndex, err := objectstore.AcquirePinkhaLoadedSpaceIndex(store, req.SpaceID)
	if err != nil {
		return result, err
	}
	defer releaseIndex()
	current := func() error {
		return errors.Join(scope.current(ctx), spaceCurrent(), indexCurrent())
	}
	if err = current(); err != nil {
		return result, err
	}
	acl := spc.CommonSpace().Acl()
	var aclID, aclHead string
	err = torahops.WithCurrentReadACL(acl, scope.key, func(id, head string) error { aclID, aclHead = id, head; return scope.current(ctx) })
	if err != nil {
		return result, err
	}

	// All native and index DB transactions are disjoint. Header validation and
	// ACL/tree waits never occur while the index ReadTx is held.
	budget := &contract.Budget{}
	before, err := anystorage.PinkhaHeadsSnapshot(ctx, spc.Storage(), budget, typeprovider.GetTypeAndKeyFromRootForSpace)
	if err != nil {
		return result, err
	}
	if before.SpaceID != req.SpaceID || before.ACLID != aclID {
		return result, contract.ErrScopeChanged
	}
	indexed, err := spaceindex.PinkhaTorahSnapshot(ctx, index, before, req.CanonicalKey, budget)
	if err != nil {
		return result, err
	}
	after, err := anystorage.PinkhaHeadsSnapshot(ctx, spc.Storage(), budget, typeprovider.GetTypeAndKeyFromRootForSpace)
	if err != nil {
		return result, err
	}
	if !before.Equal(after) {
		indexed.Reasons = contract.AddReason(indexed.Reasons, contract.HeadSetChanged)
	}
	slices.Sort(indexed.Reasons)
	generation, err := contract.Generation(scope.key.GetPublic().Account(), aclHead, before, indexed)
	if err != nil {
		return result, err
	}
	result = contract.Result{
		Contract: contract.Contract, Version: contract.Version, SpaceID: req.SpaceID, CanonicalKey: req.CanonicalKey,
		Readiness:          contract.Readiness{Version: contract.Version, State: "incomplete", Generation: generation},
		IndexedObjectCount: indexed.IndexedObjectCount, EligibleDocumentCount: indexed.EligibleDocumentCount,
		Reasons: indexed.Reasons,
	}
	for _, root := range before.Roots {
		if !root.Protocol {
			result.AuthoritativeObjectCount++
		}
	}
	result.Complete = len(result.Reasons) == 0 && result.IndexedObjectCount == result.AuthoritativeObjectCount
	if result.Complete {
		result.Readiness.State = "ready-local-snapshot"
	}

	// Validate outside the ACL lock, then use only nonblocking original owner
	// mutexes inside the final ACL fence. The completed tuple is checked while
	// the Space retirement and index tombstone points are excluded. There is no
	// tree/DB/owner wait, generation work or row copy in these tiny fences. A local
	// revocation/retirement/cancellation withholds even counts and generation.
	if err = current(); err != nil {
		return contract.Result{}, err
	}
	err = torahops.WithCurrentReadACL(acl, scope.key, func(id, head string) error {
		if id != aclID || head != aclHead {
			return contract.ErrScopeChanged
		}
		return spaceDelivery(func() error {
			return indexDelivery(func() error { return scope.current(ctx) })
		})
	})
	if err != nil {
		return contract.Result{}, err
	}
	return result, nil
}
