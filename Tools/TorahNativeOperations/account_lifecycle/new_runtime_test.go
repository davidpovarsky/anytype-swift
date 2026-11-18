package service

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/core/block/object/objectcache"
	"github.com/anyproto/anytype-heart/core/domain"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
)

// Only the new binary compiles this file. It exercises the account's real
// Space/cache/factory and provider-owned CRDT database, without adding an RPC.
func t2ExerciseRuntime(t *testing.T, state *t2AccountState, create bool) (map[string]any, func(), func()) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	spc := t2Space(t, state.SpaceID)
	root, err := torahopscontract.Root(state.SpaceID)
	require.NoError(t, err)
	var object smartblock.SmartBlock
	if create {
		exists, err := spc.Storage().HasTree(ctx, root.Id)
		require.NoError(t, err)
		require.False(t, exists, "normal account/Space startup must not create a private host")
		state.RootID, state.OperationID = root.Id, fmt.Sprintf("%032x", 1)
		object, err = spc.DeriveTreeObject(ctx, objectcache.TreeDerivationParams{
			Key: domain.MustUniqueKey(coresb.SmartBlockTypePinkhaTorahOperations, torahopscontract.UniqueKeyVersion),
		})
		require.NoError(t, err)
	} else {
		require.Equal(t, root.Id, state.RootID)
		object, err = spc.GetObject(ctx, state.RootID)
		require.NoError(t, err, "existing root must reopen through the native registry/factory")
	}
	host, ok := object.(torahopsobject.StoreObject)
	require.True(t, ok, "actual native factory must produce the private host adapter")
	require.Equal(t, coresb.SmartBlockTypePinkhaTorahOperations, host.Type())
	require.Equal(t, state.SpaceID, host.SpaceID())
	require.Equal(t, state.RootID, host.Id())
	require.Equal(t, "pinkhaTorahOps-v1", host.UniqueKey().Marshal())
	require.Empty(t, host.Blocks(), "private operation tree must never become a block document")
	keys := app.MustComponent[accountservice.Service](mw.GetApp()).Account()
	op := torahops.Operation{Version: torahops.Version, SpaceID: state.SpaceID, OperationID: state.OperationID,
		AuthorID: keys.SignKey.GetPublic().Account(), Kind: torahops.Add,
		Target: torahops.Target{ObjectID: state.DocumentID, BlockID: state.BlockID},
		Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:t2-account:1"}, Payload: []byte(t2PrivatePayload)}
	canonical, err := op.CanonicalBytes()
	require.NoError(t, err)
	if create {
		state.OperationSHA256 = t2Hash(canonical)
		created, err := host.AppendTorahOperation(ctx, op)
		require.NoError(t, err)
		require.Equal(t, torahops.Created, created.Disposition)
		require.NotEmpty(t, created.ClaimID)
		require.NotEmpty(t, created.ChangeID)
		state.ClaimID, state.ChangeID = created.ClaimID, created.ChangeID
	} else {
		require.Equal(t, state.OperationSHA256, t2Hash(canonical))
	}
	// Read before retry: a reopened process must recover existing signed history,
	// not recreate a missing projection by accidentally adding another operation.
	snapshot, err := host.ReadTorahTarget(ctx, op.Target, 100)
	require.NoError(t, err)
	require.Len(t, snapshot.Projection.Live, 1)
	require.Empty(t, snapshot.Projection.Conflicts)
	require.Empty(t, snapshot.Projection.PendingObserved)
	require.Equal(t, state.ClaimID, snapshot.Projection.Live[0].ID)
	readCanonical, err := snapshot.Projection.Live[0].Operation.CanonicalBytes()
	require.NoError(t, err)
	require.Equal(t, canonical, readCanonical)
	require.Equal(t, []string{state.ChangeID}, snapshot.Heads)
	retried, err := host.AppendTorahOperation(ctx, op)
	require.NoError(t, err)
	require.Equal(t, torahops.AlreadyExistsSamePayload, retried.Disposition)
	require.Equal(t, state.ClaimID, retried.ClaimID)
	require.Empty(t, retried.ChangeID, "idempotent replay must not create a native change")
	require.Equal(t, 2, host.Tree().Len())
	assertRemoved := func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		_, err := host.ReadTorahTarget(ctx, op.Target, 100)
		require.ErrorIs(t, err, torahopsobject.ErrTargetUnavailable)
		_, err = host.AppendTorahOperation(ctx, op)
		require.ErrorIs(t, err, torahopsobject.ErrTargetUnavailable)
	}
	assertDeleted := func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		_, err := host.ReadTorahTarget(ctx, op.Target, 100)
		require.Error(t, err, "closed/deleted Space must not serve a cached private projection")
		_, err = host.AppendTorahOperation(ctx, op)
		require.Error(t, err, "closed/deleted Space must not accept an operation")
	}
	return map[string]any{"private_registry": "ACTUAL_NATIVE_FACTORY", "private_read": "EXACT_PERSISTED_CLAIM",
		"idempotent_retry": string(retried.Disposition), "operation_sha256": state.OperationSHA256,
		"claim_id": state.ClaimID, "signed_change_id": state.ChangeID,
		"private_type": uint32(coresb.SmartBlockTypePinkhaTorahOperations)}, assertRemoved, assertDeleted
}
