package core

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/stretchr/testify/require"
)

func TestPinkhaAuthorizedOperationReadRejectsVersionBeforeAccount(t *testing.T) {
	var mw *Middleware
	for _, version := range []uint32{0, 2, ^uint32(0)} {
		result, err := mw.NativeTorahAuthorizedOperationRead(context.Background(), PinkhaTorahAuthorizedOperationReadRequest{Version: version})
		require.ErrorIs(t, err, torahops.ErrUnsupportedVersion)
		require.Equal(t, torahops.AuthorizedOperationSnapshot{}, result)
	}
}

func TestPinkhaAuthorizedOperationReadShapeAndCancellationBeforeAccount(t *testing.T) {
	var mw *Middleware
	base := PinkhaTorahAuthorizedOperationReadRequest{Version: torahops.AuthorizedOperationReadVersion, SpaceID: "space", OperationID: strings.Repeat("1", 32)}
	for _, mutate := range []func(*PinkhaTorahAuthorizedOperationReadRequest){
		func(value *PinkhaTorahAuthorizedOperationReadRequest) { value.SpaceID = "" },
		func(value *PinkhaTorahAuthorizedOperationReadRequest) { value.SpaceID = "space\x00tail" },
		func(value *PinkhaTorahAuthorizedOperationReadRequest) { value.SpaceID = string([]byte{0xff}) },
		func(value *PinkhaTorahAuthorizedOperationReadRequest) { value.OperationID = "" },
		func(value *PinkhaTorahAuthorizedOperationReadRequest) { value.OperationID = strings.Repeat("A", 32) },
		func(value *PinkhaTorahAuthorizedOperationReadRequest) { value.OperationID = strings.Repeat("x", 32) },
	} {
		request := base
		mutate(&request)
		result, err := mw.NativeTorahAuthorizedOperationRead(context.Background(), request)
		require.ErrorIs(t, err, torahops.ErrInvalid)
		require.Equal(t, torahops.AuthorizedOperationSnapshot{}, result)
	}
	result, err := mw.NativeTorahAuthorizedOperationRead(nil, base)
	require.ErrorIs(t, err, torahops.ErrInvalid)
	require.Equal(t, torahops.AuthorizedOperationSnapshot{}, result)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	result, err = mw.NativeTorahAuthorizedOperationRead(ctx, base)
	require.ErrorIs(t, err, context.Canceled)
	require.Equal(t, torahops.AuthorizedOperationSnapshot{}, result)
	ctx, cancel = context.WithDeadline(context.Background(), time.Unix(1, 0))
	defer cancel()
	result, err = mw.NativeTorahAuthorizedOperationRead(ctx, base)
	require.ErrorIs(t, err, context.DeadlineExceeded)
	require.Equal(t, torahops.AuthorizedOperationSnapshot{}, result)
}

func TestPinkhaAuthorizedOperationReadRequiresRunningAccount(t *testing.T) {
	mw := New()
	result, err := mw.NativeTorahAuthorizedOperationRead(context.Background(), PinkhaTorahAuthorizedOperationReadRequest{
		Version: torahops.AuthorizedOperationReadVersion, SpaceID: "disposable-space", OperationID: strings.Repeat("1", 32)})
	require.ErrorIs(t, err, ErrNotLoggedIn)
	require.Equal(t, torahops.AuthorizedOperationSnapshot{}, result)
}
