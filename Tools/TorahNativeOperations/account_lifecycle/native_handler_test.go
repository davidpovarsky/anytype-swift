package service

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
)

// This file is compiled into the new binary only. The legacy binary never
// receives these symbols and keeps its explicit unsupported-handler evidence.
func t2NativeHandlerRequests(state *t2AccountState) (core.PinkhaTorahAppendRequest, core.PinkhaTorahReadRequest) {
	appendRequest := core.PinkhaTorahAppendRequest{
		Version: core.PinkhaTorahOperationsVersion, SpaceID: state.SpaceID,
		OperationID: state.OperationID, Kind: torahops.Add,
		Target:  torahops.Target{ObjectID: state.DocumentID, BlockID: state.BlockID},
		Source:  torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:t2-account:1"},
		Payload: []byte(t2PrivatePayload),
	}
	readRequest := core.PinkhaTorahReadRequest{
		Version: core.PinkhaTorahOperationsVersion, SpaceID: state.SpaceID,
		Target: appendRequest.Target, Limit: 100,
	}
	return appendRequest, readRequest
}

// The first valid append must create the canonical root through the actual
// account boundary. Failed requests and a read must leave it unmaterialized.
func t2CreateNativeHandlerOperation(t *testing.T, ctx context.Context, state *t2AccountState) {
	t.Helper()
	spc := t2Space(t, state.SpaceID)
	assertAbsent := func() {
		exists, err := spc.Storage().HasTree(ctx, state.RootID)
		require.NoError(t, err)
		require.False(t, exists, "read or rejected handler call must not create a private root")
	}
	assertAbsent()
	appendRequest, readRequest := t2NativeHandlerRequests(state)
	read, err := mw.NativeTorahTargetRead(ctx, readRequest)
	require.ErrorIs(t, err, core.ErrPinkhaTorahHistoryUnavailable)
	require.Equal(t, torahops.NativeSnapshot{}, read)
	assertAbsent()

	wrongVersion := appendRequest
	wrongVersion.Version++
	write, err := mw.NativeTorahOperationAppend(ctx, wrongVersion)
	require.ErrorIs(t, err, torahops.ErrUnsupportedVersion)
	require.Equal(t, torahops.NativeAppendResult{}, write)
	assertAbsent()
	missingBlock := appendRequest
	missingBlock.Target.BlockID = "fixture-missing-block"
	write, err = mw.NativeTorahOperationAppend(ctx, missingBlock)
	require.ErrorIs(t, err, torahopsobject.ErrTargetUnavailable)
	require.Equal(t, torahops.NativeAppendResult{}, write)
	assertAbsent()
	invalidPayload := appendRequest
	invalidPayload.Payload = nil
	write, err = mw.NativeTorahOperationAppend(ctx, invalidPayload)
	require.ErrorIs(t, err, torahops.ErrInvalid)
	require.Equal(t, torahops.NativeAppendResult{}, write)
	assertAbsent()

	for _, kind := range []torahops.Kind{torahops.Remove, torahops.Replace} {
		unobserved := appendRequest
		unobserved.Kind = kind
		unobserved.Observed = []string{strings.Repeat("1", 64) + "/" + strings.Repeat("2", 64)}
		if kind == torahops.Remove {
			unobserved.Source = torahops.Source{}
			unobserved.Payload = nil
		}
		write, err = mw.NativeTorahOperationAppend(ctx, unobserved)
		require.ErrorIs(t, err, core.ErrPinkhaTorahHistoryUnavailable, "an observed operation cannot initialize absent history")
		require.Equal(t, torahops.NativeAppendResult{}, write)
		assertAbsent()
	}
	cancelled, cancel := context.WithCancel(ctx)
	cancel()
	write, err = mw.NativeTorahOperationAppend(cancelled, appendRequest)
	require.ErrorIs(t, err, context.Canceled)
	require.Equal(t, torahops.NativeAppendResult{}, write)
	assertAbsent()

	created, err := mw.NativeTorahOperationAppend(ctx, appendRequest)
	require.NoError(t, err)
	require.Equal(t, torahops.Created, created.Disposition)
	require.NotEmpty(t, created.ClaimID)
	require.NotEmpty(t, created.ChangeID)
	state.ClaimID, state.ChangeID = created.ClaimID, created.ChangeID
	exists, err := spc.Storage().HasTree(ctx, state.RootID)
	require.NoError(t, err)
	require.True(t, exists)
}

func t2CheckNativeHandlerOperation(t *testing.T, ctx context.Context, state *t2AccountState, create bool) map[string]any {
	t.Helper()
	appendRequest, readRequest := t2NativeHandlerRequests(state)
	badRead := readRequest
	badRead.Version++
	_, err := mw.NativeTorahTargetRead(ctx, badRead)
	require.ErrorIs(t, err, torahops.ErrUnsupportedVersion)
	badRead = readRequest
	badRead.Limit = 0
	_, err = mw.NativeTorahTargetRead(ctx, badRead)
	require.ErrorIs(t, err, torahops.ErrInvalid)

	// Read before retry, so a reopen cannot recreate missing history and pass.
	snapshot, err := mw.NativeTorahTargetRead(ctx, readRequest)
	require.NoError(t, err)
	require.Len(t, snapshot.Projection.Live, 1)
	require.Empty(t, snapshot.Projection.Conflicts)
	require.Empty(t, snapshot.Projection.PendingObserved)
	claim := snapshot.Projection.Live[0]
	require.Equal(t, state.ClaimID, claim.ID)
	canonical, err := claim.Operation.CanonicalBytes()
	require.NoError(t, err)
	// The parent fixture computes this digest from the actual native signing
	// identity. The request above has no author, root or permission fields.
	require.Equal(t, state.OperationSHA256, t2Hash(canonical))
	require.Equal(t, []string{state.ChangeID}, snapshot.Heads)
	retried, err := mw.NativeTorahOperationAppend(ctx, appendRequest)
	require.NoError(t, err)
	require.Equal(t, torahops.AlreadyExistsSamePayload, retried.Disposition)
	require.Equal(t, state.ClaimID, retried.ClaimID)
	require.Empty(t, retried.ChangeID)

	collisionRequest := appendRequest
	collisionRequest.Payload = []byte("different bytes must not replace the committed claim")
	collision, err := mw.NativeTorahOperationAppend(ctx, collisionRequest)
	require.NoError(t, err)
	require.Equal(t, torahops.CollisionDifferentPayload, collision.Disposition)
	require.Empty(t, collision.ChangeID)
	require.Len(t, collision.Resolution.Claims, 1)
	require.Equal(t, state.ClaimID, collision.Resolution.Claims[0].ID)
	after, err := mw.NativeTorahTargetRead(ctx, readRequest)
	require.NoError(t, err)
	require.Equal(t, snapshot, after, "retry/collision must preserve claims, signed heads and local watermark")
	creation := "EXISTING_HISTORY_REOPENED"
	if create {
		creation = "INVALID_CALLS_NO_ROOT_THEN_VALID_APPEND_CREATED_ROOT"
	}
	return map[string]any{
		"scope":    "ACCOUNT_SCOPED_TYPED_BOUNDARY_NOT_REGISTERED_RPC",
		"creation": creation, "read": "EXACT_PERSISTED_CLAIM_NATIVE_AUTHOR",
		"read_guards": "VERSION_AND_LIMIT_REJECTED",
		"retry":       string(retried.Disposition), "collision": string(collision.Disposition),
		"after_stop": "NOT_RUN",
	}
}

func t2AssertNativeHandlerUnavailable(t *testing.T, ctx context.Context, state *t2AccountState, targetRemoved bool) {
	t.Helper()
	appendRequest, readRequest := t2NativeHandlerRequests(state)
	read, readErr := mw.NativeTorahTargetRead(ctx, readRequest)
	write, writeErr := mw.NativeTorahOperationAppend(ctx, appendRequest)
	if targetRemoved {
		require.ErrorIs(t, readErr, torahopsobject.ErrTargetUnavailable)
		require.ErrorIs(t, writeErr, torahopsobject.ErrTargetUnavailable)
	} else {
		require.Error(t, readErr, "deleted Space must not yield a cached projection")
		require.Error(t, writeErr, "deleted Space must not accept an operation")
	}
	require.Equal(t, torahops.NativeSnapshot{}, read)
	require.Equal(t, torahops.NativeAppendResult{}, write)
}

func t2RecordStoppedRuntime(t *testing.T, state *t2AccountState, observation map[string]any) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	appendRequest, readRequest := t2NativeHandlerRequests(state)
	read, err := mw.NativeTorahTargetRead(ctx, readRequest)
	require.ErrorIs(t, err, core.ErrNotLoggedIn)
	require.Equal(t, torahops.NativeSnapshot{}, read)
	write, err := mw.NativeTorahOperationAppend(ctx, appendRequest)
	require.ErrorIs(t, err, core.ErrNotLoggedIn)
	require.Equal(t, torahops.NativeAppendResult{}, write)
	handler, ok := observation["handler_boundary"].(map[string]any)
	require.True(t, ok)
	handler["after_stop"] = "NATIVE_READ_AND_APPEND_NOT_LOGGED_IN"
}
