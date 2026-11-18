package core

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	"github.com/anyproto/any-sync/net/peer"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/stretchr/testify/require"
)

// This probe observes the real ValidateNativeTarget -> DoCtx boundary. It does
// not provide a document, ACL, private tree or synthetic network transport.
type pinkhaTargetFetchProbe struct {
	smartblock.Space
	load func(context.Context, string, func(smartblock.SmartBlock) error) error
}

func (*pinkhaTargetFetchProbe) Id() string { return "fixture-space" }
func (*pinkhaTargetFetchProbe) Do(string, func(smartblock.SmartBlock) error) error {
	panic("target lookup must retain the caller context through DoCtx")
}
func (s *pinkhaTargetFetchProbe) DoCtx(ctx context.Context, id string, apply func(smartblock.SmartBlock) error) error {
	return s.load(ctx, id, apply)
}

func TestPinkhaTargetLookupUsesResponsiblePeersBeforeHost(t *testing.T) {
	type contextKey struct{}
	parent := context.WithValue(context.Background(), contextKey{}, "caller-value")
	original := errors.New("native target load result")
	started := time.Now()
	var received context.Context
	space := &pinkhaTargetFetchProbe{load: func(ctx context.Context, id string, _ func(smartblock.SmartBlock) error) error {
		received = ctx
		require.Equal(t, "ordinary-target", id)
		peerID, err := peer.CtxPeerId(ctx)
		require.NoError(t, err)
		require.Equal(t, peer.CtxResponsiblePeers, peerID)
		require.Equal(t, "caller-value", ctx.Value(contextKey{}))
		deadline, ok := ctx.Deadline()
		require.True(t, ok, "background byte-entry calls must have a bounded native lookup")
		require.False(t, deadline.Before(started.Add(pinkhaTorahTargetLookupTimeout)))
		require.False(t, deadline.After(time.Now().Add(pinkhaTorahTargetLookupTimeout)))
		return original
	}}
	err := validatePinkhaTorahTargetBeforeHost(parent, space, "private-root", torahops.Target{ObjectID: "ordinary-target"})
	require.Same(t, original, err, "native lookup errors must remain unchanged")
	require.ErrorIs(t, received.Err(), context.Canceled, "the lookup timer must be released on return")
	_, err = peer.CtxPeerId(parent)
	require.ErrorIs(t, err, peer.ErrPeerIdNotFoundInContext, "the caller context must not be modified")
	require.NoError(t, parent.Err())
}

func TestPinkhaTargetLookupPreservesPeerAndEarlierDeadline(t *testing.T) {
	for _, item := range []struct{ name, peerID string }{
		{"explicit_peer", "caller-selected-peer"},
		{"responsible_peers", peer.CtxResponsiblePeers},
		{"explicit_empty_peer", ""},
	} {
		t.Run(item.name, func(t *testing.T) {
			deadline := time.Now().Add(5 * time.Second)
			parent, cancel := context.WithDeadline(peer.CtxWithPeerId(context.Background(), item.peerID), deadline)
			defer cancel()
			original := errors.New("native lookup error is not an availability classification")
			space := &pinkhaTargetFetchProbe{load: func(ctx context.Context, _ string, _ func(smartblock.SmartBlock) error) error {
				peerID, err := peer.CtxPeerId(ctx)
				require.NoError(t, err)
				require.Equal(t, item.peerID, peerID)
				actual, ok := ctx.Deadline()
				require.True(t, ok)
				require.Equal(t, deadline, actual)
				return original
			}}
			err := validatePinkhaTorahTargetBeforeHost(parent, space, "private-root", torahops.Target{ObjectID: "ordinary-target"})
			require.Same(t, original, err)
			require.NoError(t, parent.Err(), "releasing the child must not cancel the caller")
		})
	}
}

func TestPinkhaTargetLookupPropagatesCancellationDuringLoad(t *testing.T) {
	parent, cancel := context.WithCancel(context.Background())
	defer cancel()
	entered := make(chan context.Context, 1)
	finished := make(chan error, 1)
	original := fmt.Errorf("native target load: %w", context.Canceled)
	space := &pinkhaTargetFetchProbe{load: func(ctx context.Context, _ string, _ func(smartblock.SmartBlock) error) error {
		entered <- ctx
		<-ctx.Done()
		return original
	}}
	go func() {
		finished <- validatePinkhaTorahTargetBeforeHost(parent, space, "private-root", torahops.Target{ObjectID: "ordinary-target"})
	}()
	select {
	case ctx := <-entered:
		peerID, err := peer.CtxPeerId(ctx)
		require.NoError(t, err)
		require.Equal(t, peer.CtxResponsiblePeers, peerID)
	case <-time.After(time.Second):
		t.Fatal("native context-aware loading was not entered")
	}
	cancel()
	select {
	case err := <-finished:
		require.Same(t, original, err)
		require.ErrorIs(t, err, context.Canceled)
	case <-time.After(time.Second):
		t.Fatal("caller cancellation did not reach the native target loader")
	}
}

func TestPinkhaTargetLookupRejectsEndedContextBeforeAccess(t *testing.T) {
	for _, item := range []struct {
		name string
		ctx  func() (context.Context, context.CancelFunc)
		want error
	}{
		{"cancelled", func() (context.Context, context.CancelFunc) {
			ctx, cancel := context.WithCancel(context.Background())
			cancel()
			return ctx, cancel
		}, context.Canceled},
		{"deadline", func() (context.Context, context.CancelFunc) {
			return context.WithDeadline(context.Background(), time.Now().Add(-time.Second))
		}, context.DeadlineExceeded},
	} {
		t.Run(item.name, func(t *testing.T) {
			ctx, cancel := item.ctx()
			defer cancel()
			// A nil native Space would reject the target if the context fence
			// were missing. No storage, root or object access is needed here.
			err := validatePinkhaTorahTargetBeforeHost(ctx, nil, "private-root", torahops.Target{ObjectID: "ordinary-target"})
			require.ErrorIs(t, err, item.want)
		})
	}
}
