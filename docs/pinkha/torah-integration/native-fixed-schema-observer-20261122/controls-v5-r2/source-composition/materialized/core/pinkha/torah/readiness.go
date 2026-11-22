package torahderived

import (
	"errors"
	"sync"
)

type State string

const (
	NotInitialized State = "NOT_INITIALIZED"
	Discovering    State = "DISCOVERING"
	Rebuilding     State = "REBUILDING"
	Ready          State = "READY"
	Outdated       State = "OUTDATED"
	Error          State = "ERROR"
	Unsupported    State = "UNSUPPORTED"
)

var ErrNotReady = errors.New("Space derived index is not ready")
var ErrStaleGeneration = errors.New("stale rebuild generation")

// Readiness is a guard for a caller-owned native index, not a second database.
// A production integration must durably checkpoint its generation and recovery
// status in the engine's own local store before using this guard.
type Readiness struct {
	mu       sync.RWMutex
	spaces   map[string]readinessEntry
	sequence uint64
}

type readinessEntry struct {
	state State
	epoch uint64
}

func (r *Readiness) Begin(space string) uint64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.spaces == nil {
		r.spaces = map[string]readinessEntry{}
	}
	r.sequence++
	r.spaces[space] = readinessEntry{state: Rebuilding, epoch: r.sequence}
	return r.sequence
}

func (r *Readiness) Finish(space string, epoch uint64, success bool) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	entry, ok := r.spaces[space]
	if !ok || entry.epoch != epoch || entry.state != Rebuilding {
		return ErrStaleGeneration
	}
	entry.state = Error
	if success {
		entry.state = Ready
	}
	r.spaces[space] = entry
	return nil
}

func (r *Readiness) Invalidate(space string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.spaces == nil {
		r.spaces = map[string]readinessEntry{}
	}
	r.sequence++
	r.spaces[space] = readinessEntry{state: Outdated, epoch: r.sequence}
}

func (r *Readiness) RequireReady(space string) error {
	if r.Status(space) != Ready {
		return ErrNotReady
	}
	return nil
}

func (r *Readiness) Status(space string) State {
	r.mu.RLock()
	defer r.mu.RUnlock()
	if entry, ok := r.spaces[space]; ok {
		return entry.state
	}
	return NotInitialized
}
