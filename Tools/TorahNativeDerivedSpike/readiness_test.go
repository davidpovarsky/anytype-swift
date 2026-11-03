package torahderived

import (
	"errors"
	"testing"
)

func TestReadinessRejectsStaleCompletionAndOtherSpaces(t *testing.T) {
	var state Readiness
	if !errors.Is(state.RequireReady("a"), ErrNotReady) {
		t.Fatal("unknown Space exposed results")
	}
	first := state.Begin("a")
	if !errors.Is(state.RequireReady("a"), ErrNotReady) {
		t.Fatal("partial rebuild exposed results")
	}
	second := state.Begin("a")
	if !errors.Is(state.Finish("a", first, true), ErrStaleGeneration) {
		t.Fatal("stale rebuild was accepted")
	}
	if err := state.Finish("a", second, true); err != nil {
		t.Fatal(err)
	}
	if err := state.RequireReady("a"); err != nil {
		t.Fatal(err)
	}
	if !errors.Is(state.RequireReady("b"), ErrNotReady) {
		t.Fatal("Space readiness leaked")
	}
	state.Invalidate("a")
	if !errors.Is(state.Finish("a", second, true), ErrStaleGeneration) {
		t.Fatal("invalidated generation became ready")
	}
	third := state.Begin("a")
	if err := state.Finish("a", third, false); err != nil {
		t.Fatal(err)
	}
	if state.Status("a") != Error {
		t.Fatal("failed rebuild exposed empty results")
	}
	// A fresh process starts unready; no implicit persisted READY after a crash.
	var restarted Readiness
	if restarted.Status("a") != NotInitialized {
		t.Fatal("restart falsely ready")
	}
}
