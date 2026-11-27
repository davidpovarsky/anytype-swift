package torahops

import (
	"context"
	"errors"
	"slices"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/stretchr/testify/require"
)

// The actual signed SyncTree/ACL/SQLite fixture is unchanged. Only the later
// index-admission callback is injected. These controls do not claim that the
// fixture callback is a real full-Space index; its transaction is covered by
// the indexer failure controls and the native Space transition acceptance.
func TestCutoverNativeCommittedBeginRetainsReceiptAfterIndexFailure(t *testing.T) {
	f := newCutoverSignedFixture(t)
	ctx := context.Background()
	key := f.native.keys.SignKey
	begin := f.begin(t, key, 1)
	failure := errors.New("owned metadata index transaction rejected after native commit")
	var unavailable atomic.Bool
	unavailable.Store(true)
	f.tree.Lock()
	beforeHeads := slices.Clone(f.tree.Heads())
	err := f.host.BindNativeIndexHookLocked(ctx, func(_ context.Context, tree objecttree.ObjectTree) error {
		require.Equal(t, f.tree, tree)
		if unavailable.Load() && !slices.Equal(beforeHeads, tree.Heads()) {
			return failure
		}
		return nil
	})
	f.tree.Unlock()
	require.NoError(t, err)
	result, err := f.host.Append(ctx, f.native.host, begin)
	require.ErrorIs(t, err, ErrNativeIndexBehind)
	require.ErrorIs(t, err, failure)
	require.Equal(t, Created, result.Disposition)
	require.NotEmpty(t, result.ChangeID)
	require.NotEmpty(t, result.ClaimID)
	exists, readErr := f.tree.Storage().Has(ctx, result.ChangeID)
	require.NoError(t, readErr)
	require.True(t, exists)
	unavailable.Store(false)
	snapshot := f.read(t)
	require.Len(t, snapshot.MetadataHistory.Claims, 1)
	receipts := snapshot.MetadataReceipts[result.ClaimID]
	require.Len(t, receipts, 1)
	require.Equal(t, result.ChangeID, receipts[0].ChangeID)
	require.Equal(t, begin.AuthorID, receipts[0].Creator)
	retry, err := f.host.Append(ctx, f.native.host, begin)
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.Equal(t, snapshot, f.read(t))
	require.Equal(t, f.acquired.Load(), f.released.Load())
}

func TestCutoverNativeCommittedImportRetainsReceiptAfterIndexFailure(t *testing.T) {
	f := newCutoverSignedFixture(t)
	ctx := context.Background()
	key := f.native.keys.SignKey
	begin := f.begin(t, key, 1)
	_, err := f.host.Append(ctx, f.native.host, begin)
	require.NoError(t, err)
	factID, operation := f.importOperation(t, key, 0)
	failure := errors.New("owned operation index transaction rejected after native commit")
	var unavailable atomic.Bool
	unavailable.Store(true)
	f.native.tree.Lock()
	beforeHeads := slices.Clone(f.native.tree.Heads())
	err = f.native.host.BindNativeIndexHookLocked(ctx, func(_ context.Context, tree objecttree.ObjectTree) error {
		require.Equal(t, f.native.tree, tree)
		if unavailable.Load() && !slices.Equal(beforeHeads, tree.Heads()) {
			return failure
		}
		return nil
	})
	f.native.tree.Unlock()
	require.NoError(t, err)
	result, err := f.host.AppendImport(ctx, f.native.host, begin.PlanID, factID, operation)
	require.ErrorIs(t, err, ErrNativeIndexBehind)
	require.ErrorIs(t, err, failure)
	require.Equal(t, Created, result.Disposition)
	require.NotEmpty(t, result.ChangeID)
	require.NotEmpty(t, result.ClaimID)
	exists, readErr := f.native.tree.Storage().Has(ctx, result.ChangeID)
	require.NoError(t, readErr)
	require.True(t, exists)
	unavailable.Store(false)
	snapshot := f.read(t)
	require.Equal(t, CutoverPending, snapshot.State.Status)
	require.Len(t, snapshot.OriginalClaims, 1)
	receipts := snapshot.OriginalReceipts[result.ClaimID]
	require.Len(t, receipts, 1)
	require.Equal(t, result.ChangeID, receipts[0].ChangeID)
	require.Equal(t, operation.AuthorID, receipts[0].Creator)
	retry, err := f.host.AppendImport(ctx, f.native.host, begin.PlanID, factID, operation)
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.Equal(t, snapshot, f.read(t))
	require.Equal(t, f.acquired.Load(), f.released.Load())
}

func TestCutoverNativeCommittedAssociationRetainsReceiptAfterIndexFailure(t *testing.T) {
	f := newCutoverSignedFixture(t)
	ctx := context.Background()
	sealed := f.finishOwner(t)
	operation := Operation{Version: Version, SpaceID: f.plan.SpaceID, OperationID: strings.Repeat("a", 32),
		AuthorID: f.native.keys.SignKey.GetPublic().Account(), Kind: Remove, Target: Target{ObjectID: f.plan.ObjectID}}
	for _, item := range sealed.State.Imports {
		operation.Observed = append(operation.Observed, item.ClaimID)
	}
	failure := errors.New("owned post-append association index admission rejected")
	var unavailable atomic.Bool
	unavailable.Store(true)
	f.native.tree.Lock()
	beforeHeads := slices.Clone(f.native.tree.Heads())
	err := f.native.host.BindNativeIndexHookLocked(ctx, func(_ context.Context, tree objecttree.ObjectTree) error {
		require.Equal(t, f.native.tree, tree)
		if unavailable.Load() && !slices.Equal(beforeHeads, tree.Heads()) {
			return failure
		}
		return nil
	})
	f.native.tree.Unlock()
	require.NoError(t, err)
	result, err := f.host.AppendAssociation(ctx, f.native.host, sealed.State.PlanID, operation)
	require.ErrorIs(t, err, ErrNativeIndexBehind)
	require.ErrorIs(t, err, failure)
	require.Equal(t, Created, result.Disposition)
	require.NotEmpty(t, result.ChangeID)
	require.NotEmpty(t, result.ClaimID)
	exists, readErr := f.native.tree.Storage().Has(ctx, result.ChangeID)
	require.NoError(t, readErr)
	require.True(t, exists)
	unavailable.Store(false)
	snapshot := f.read(t)
	require.Equal(t, CutoverSealed, snapshot.State.Status)
	receipts := snapshot.OriginalReceipts[result.ClaimID]
	require.Len(t, receipts, 1)
	require.Equal(t, result.ChangeID, receipts[0].ChangeID)
	require.Equal(t, operation.AuthorID, receipts[0].Creator)
	view, err := f.native.host.ReadTarget(ctx, operation.Target, 10)
	require.NoError(t, err)
	require.Empty(t, view.Projection.Live)
	retry, err := f.host.AppendAssociation(ctx, f.native.host, sealed.State.PlanID, operation)
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.Equal(t, snapshot, f.read(t))
	require.Equal(t, f.acquired.Load(), f.released.Load())
}

func TestNativeReadinessCurrentACLWithholdsCallbackAfterRealRevocation(t *testing.T) {
	f := newCutoverSignedFixture(t)
	writer := addNativeWriter(t, f.native)
	var calls int
	var capturedHead string
	err := WithCurrentReadACL(f.native.acl, writer, func(id, head string) error {
		calls++
		require.Equal(t, f.native.acl.Id(), id)
		require.NotEmpty(t, head)
		capturedHead = head
		return nil
	})
	require.NoError(t, err)
	require.Equal(t, 1, calls)
	removeNativeMember(t, f.native, writer)
	err = WithCurrentReadACL(f.native.acl, writer, func(string, string) error { calls++; return nil })
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Equal(t, 1, calls)
	err = WithCurrentReadACL(f.native.acl, f.native.keys.SignKey, func(_ string, head string) error {
		calls++
		require.NotEqual(t, capturedHead, head)
		return nil
	})
	require.NoError(t, err)
	require.Equal(t, 2, calls)
	// Existing source/property contents are not inspected by this ACL fence.
	require.Equal(t, f.acquired.Load(), f.released.Load())
}
