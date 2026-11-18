package core

import (
	"context"
	"testing"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/stretchr/testify/require"
)

func TestPinkhaNativeHandlerRejectsVersionBeforeAccountAccess(t *testing.T) {
	// A nil Middleware would panic on account access: rejecting the unsupported
	// version must happen before resolving any account, Space or private tree.
	var mw *Middleware
	for _, version := range []uint32{0, 2, ^uint32(0)} {
		written, err := mw.NativeTorahOperationAppend(context.Background(), PinkhaTorahAppendRequest{Version: version})
		require.ErrorIs(t, err, torahops.ErrUnsupportedVersion)
		require.Equal(t, torahops.NativeAppendResult{}, written)
		read, err := mw.NativeTorahTargetRead(context.Background(), PinkhaTorahReadRequest{Version: version})
		require.ErrorIs(t, err, torahops.ErrUnsupportedVersion)
		require.Equal(t, torahops.NativeSnapshot{}, read)
	}
}

func TestPinkhaNativeHandlerRequiresRunningAccount(t *testing.T) {
	mw := New()
	target := torahops.Target{ObjectID: "disposable-target", BlockID: "disposable-block"}
	written, err := mw.NativeTorahOperationAppend(context.Background(), PinkhaTorahAppendRequest{
		Version: PinkhaTorahOperationsVersion, SpaceID: "disposable-space", OperationID: "00000000000000000000000000000001",
		Kind: torahops.Add, Target: target, Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte("test")})
	require.ErrorIs(t, err, ErrNotLoggedIn)
	require.Equal(t, torahops.NativeAppendResult{}, written)
	read, err := mw.NativeTorahTargetRead(context.Background(), PinkhaTorahReadRequest{
		Version: PinkhaTorahOperationsVersion, SpaceID: "disposable-space", Target: target, Limit: 10})
	require.ErrorIs(t, err, ErrNotLoggedIn)
	require.Equal(t, torahops.NativeSnapshot{}, read)
}

func TestPinkhaNativeReadShapeAndCancellationBeforeAccountAccess(t *testing.T) {
	var mw *Middleware
	base := PinkhaTorahReadRequest{Version: PinkhaTorahOperationsVersion, SpaceID: "space", Target: torahops.Target{ObjectID: "target"}, Limit: 10}
	for _, change := range []func(*PinkhaTorahReadRequest){
		func(r *PinkhaTorahReadRequest) { r.SpaceID = "" },
		func(r *PinkhaTorahReadRequest) { r.Target.ObjectID = "" },
		func(r *PinkhaTorahReadRequest) { r.Target.BlockID = "block\x00tail" },
		func(r *PinkhaTorahReadRequest) { r.Target.ObjectID = string([]byte{0xff}) },
		func(r *PinkhaTorahReadRequest) { r.Limit = 0 },
		func(r *PinkhaTorahReadRequest) { r.Limit = 10001 },
	} {
		req := base
		change(&req)
		read, err := mw.NativeTorahTargetRead(context.Background(), req)
		require.ErrorIs(t, err, torahops.ErrInvalid)
		require.Equal(t, torahops.NativeSnapshot{}, read)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	_, err := mw.NativeTorahTargetRead(ctx, base)
	require.ErrorIs(t, err, context.Canceled)
	_, err = mw.NativeTorahOperationAppend(ctx, PinkhaTorahAppendRequest{Version: PinkhaTorahOperationsVersion, SpaceID: base.SpaceID, Target: base.Target})
	require.ErrorIs(t, err, context.Canceled)
}
