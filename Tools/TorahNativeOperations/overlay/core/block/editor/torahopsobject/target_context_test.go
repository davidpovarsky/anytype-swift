package torahopsobject

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/stretchr/testify/require"
)

// The embedded native interface is deliberately incomplete. These tests cover
// the target loader boundary; they do not simulate a document, ACL or sync tree.
type contextlessTargetSpace struct {
	smartblock.Space
	doCalls int
}

func (*contextlessTargetSpace) Id() string { return "fixture-space" }
func (s *contextlessTargetSpace) Do(string, func(smartblock.SmartBlock) error) error {
	s.doCalls++
	return errors.New("contextless loading must not be called")
}

type contextTargetProbe struct {
	contextlessTargetSpace
	load func(context.Context, string, func(smartblock.SmartBlock) error) error
}

func (s *contextTargetProbe) DoCtx(ctx context.Context, id string, apply func(smartblock.SmartBlock) error) error {
	return s.load(ctx, id, apply)
}

func TestPinkhaNativeTargetLoadReceivesCancellationContext(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	type observedCall struct {
		ctx context.Context
		id  string
	}
	entered := make(chan observedCall, 1)
	finished := make(chan error, 1)
	loadError := fmt.Errorf("native target load: %w", context.Canceled)
	space := &contextTargetProbe{load: func(received context.Context, id string, _ func(smartblock.SmartBlock) error) error {
		entered <- observedCall{received, id}
		<-received.Done()
		return loadError
	}}
	go func() {
		finished <- ValidateNativeTarget(ctx, space, "private-root", torahops.Target{ObjectID: "ordinary-target"})
	}()
	select {
	case observed := <-entered:
		require.Same(t, ctx, observed.ctx)
		require.Equal(t, "ordinary-target", observed.id)
	case <-time.After(time.Second):
		t.Fatal("native context-aware target loader was not entered")
	}
	cancel()
	select {
	case err := <-finished:
		require.Same(t, loadError, err, "native lookup error must remain unchanged")
		require.ErrorIs(t, err, context.Canceled)
	case <-time.After(time.Second):
		t.Fatal("cancelled target loading did not return")
	}
	require.Zero(t, space.doCalls)
}

func TestPinkhaNativeTargetRejectsContextlessLoader(t *testing.T) {
	space := &contextlessTargetSpace{}
	err := ValidateNativeTarget(context.Background(), space, "private-root", torahops.Target{ObjectID: "ordinary-target"})
	require.ErrorIs(t, err, ErrTargetUnavailable)
	require.Zero(t, space.doCalls, "missing DoCtx must not fall back to context.Background loading")
}

func TestPinkhaNativeTargetPreservesErrorsAndChecksCancelledCallback(t *testing.T) {
	t.Run("original_load_error_is_not_reclassified_as_missing", func(t *testing.T) {
		original := errors.New("synthetic native storage failure")
		space := &contextTargetProbe{load: func(context.Context, string, func(smartblock.SmartBlock) error) error {
			return original
		}}
		err := ValidateNativeTarget(context.Background(), space, "private-root", torahops.Target{ObjectID: "ordinary-target"})
		require.Same(t, original, err)
		require.NotErrorIs(t, err, ErrTargetUnavailable)
		require.Zero(t, space.doCalls)
	})
	t.Run("cancelled_callback_does_not_inspect_native_target", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()
		space := &contextTargetProbe{load: func(_ context.Context, _ string, apply func(smartblock.SmartBlock) error) error {
			cancel()
			// A nil test object makes any access before the context fence fail.
			// This does not assert that the native SmartBlock lock is cancellable.
			return apply(nil)
		}}
		err := ValidateNativeTarget(ctx, space, "private-root", torahops.Target{ObjectID: "ordinary-target"})
		require.ErrorIs(t, err, context.Canceled)
		require.Zero(t, space.doCalls)
	})
}
