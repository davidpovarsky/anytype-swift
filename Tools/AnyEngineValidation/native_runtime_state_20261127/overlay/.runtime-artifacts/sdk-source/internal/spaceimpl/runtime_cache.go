package spaceimpl

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"sync"
	"time"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any-sync/coordinator/coordinatorproto"
)

const (
	runtimeCoordinatorFresh = 3 * time.Minute
	runtimeCoordinatorWait  = 5 * time.Second
	runtimeCoordinatorFetch = 30 * time.Second
	runtimeCoordinatorRetry = 30 * time.Second
	maxRuntimeStoredBytes   = 16 * 1024
)

// This is a device-local successful-answer cache, not replicated settings or
// an ACL authority. Keys and stored envelopes both bind all three identities.
type runtimeCoordinatorKey struct {
	AccountID string `json:"accountId"`
	NetworkID string `json:"networkId"`
	SpaceID   string `json:"spaceId"`
}

type runtimeCoordinatorKV interface {
	GetKV(context.Context, string) (string, bool, error)
	SetKV(context.Context, string, string) error
}

type runtimeCoordinatorStored struct {
	Version  int                                 `json:"version"`
	Scope    runtimeCoordinatorKey               `json:"scope"`
	Snapshot space.RuntimeCoordinatorObservation `json:"snapshot"`
}

type runtimeCoordinatorRun struct {
	available chan struct{}
	once      sync.Once
}

func (r *runtimeCoordinatorRun) answer() { r.once.Do(func() { close(r.available) }) }

type runtimeCoordinatorEntry struct {
	current *space.RuntimeCoordinatorObservation
	loaded  bool
	dirty   bool
	run     *runtimeCoordinatorRun
	retryAt time.Time
}

// One run per scoped Space coalesces disk load, network refresh and persistence.
// The owner closes admission before cancelling and draining every owned run.
// No cache lock, ACL lock or lifetime lock is held during network or store I/O.
type runtimeCoordinatorCache struct {
	mu      sync.Mutex
	entries map[runtimeCoordinatorKey]*runtimeCoordinatorEntry
	kv      runtimeCoordinatorKV
	closed  bool
	ctx     context.Context
	cancel  context.CancelFunc
	wg      sync.WaitGroup
	scope   func() (accountID, networkID string, err error)
	fetch   func(context.Context, []string) ([]*coordinatorproto.SpaceStatusPayload, error)
}

func newRuntimeCoordinatorCache(scope func() (string, string, error), fetch func(context.Context, []string) ([]*coordinatorproto.SpaceStatusPayload, error)) *runtimeCoordinatorCache {
	ctx, cancel := context.WithCancel(context.Background())
	return &runtimeCoordinatorCache{
		entries: make(map[runtimeCoordinatorKey]*runtimeCoordinatorEntry),
		ctx:     ctx, cancel: cancel, scope: scope, fetch: fetch,
	}
}

func (c *runtimeCoordinatorCache) setKV(kv runtimeCoordinatorKV) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.closed {
		c.kv = kv
	}
}

func (c *runtimeCoordinatorCache) close() {
	c.mu.Lock()
	c.closed = true
	c.mu.Unlock()
	c.cancel()
	c.wg.Wait()
}

func (c *runtimeCoordinatorCache) matches(key runtimeCoordinatorKey) bool {
	accountID, networkID, err := c.scope()
	return err == nil && accountID != "" && networkID != "" && key.SpaceID != "" &&
		key.AccountID == accountID && key.NetworkID == networkID
}

func runtimeCoordinatorCopy(in *space.RuntimeCoordinatorObservation) *space.RuntimeCoordinatorObservation {
	if in == nil {
		return nil
	}
	out := *in
	if in.Limits != nil {
		limits := *in.Limits
		out.Limits = &limits
	}
	return &out
}

func runtimeCoordinatorSnapshot(payload *coordinatorproto.SpaceStatusPayload, fetchedAt time.Time) *space.RuntimeCoordinatorObservation {
	if payload == nil || fetchedAt.IsZero() {
		return nil
	}
	status, known := coordinatorproto.SpaceStatus_name[int32(payload.Status)]
	if !known {
		return nil
	}
	out := &space.RuntimeCoordinatorObservation{FetchedAt: fetchedAt.UTC(), Status: status, IsShared: payload.IsShared}
	if payload.Limits != nil {
		out.Limits = &space.RuntimeMemberLimits{
			ReadersLimit: payload.Limits.ReadMembers, WritersLimit: payload.Limits.WriteMembers,
		}
	}
	return out
}

func runtimeCoordinatorStorageKey(key runtimeCoordinatorKey) string {
	raw, _ := json.Marshal(key) // a fixed struct of strings; no custom marshaler
	digest := sha256.Sum256(raw)
	return "pinkha/runtime-space-coordinator/v1/" + hex.EncodeToString(digest[:])
}

func decodeRuntimeCoordinator(raw string, key runtimeCoordinatorKey) *space.RuntimeCoordinatorObservation {
	if len(raw) == 0 || len(raw) > maxRuntimeStoredBytes {
		return nil
	}
	// Presence is checked independently of numeric value: a malformed local
	// object with missing booleans/limit members must not manufacture zeros.
	var stored struct {
		Version  int
		Scope    runtimeCoordinatorKey
		Snapshot *struct {
			FetchedAt *time.Time
			Status    *string
			IsShared  *bool
			Limits    json.RawMessage
		}
	}
	if json.Unmarshal([]byte(raw), &stored) != nil || stored.Version != 1 || stored.Scope != key || stored.Snapshot == nil {
		return nil
	}
	snapshot := stored.Snapshot
	if snapshot.FetchedAt == nil || snapshot.FetchedAt.IsZero() || snapshot.Status == nil || snapshot.IsShared == nil || len(snapshot.Limits) == 0 {
		return nil
	}
	if _, known := coordinatorproto.SpaceStatus_value[*snapshot.Status]; !known {
		return nil
	}
	var limits *struct {
		ReadersLimit *uint32
		WritersLimit *uint32
	}
	if json.Unmarshal(snapshot.Limits, &limits) != nil {
		return nil
	}
	out := &space.RuntimeCoordinatorObservation{
		FetchedAt: snapshot.FetchedAt.UTC(), Status: *snapshot.Status, IsShared: *snapshot.IsShared,
	}
	if limits != nil {
		if limits.ReadersLimit == nil || limits.WritersLimit == nil {
			return nil
		}
		out.Limits = &space.RuntimeMemberLimits{ReadersLimit: *limits.ReadersLimit, WritersLimit: *limits.WritersLimit}
	}
	return out
}

func runtimeCoordinatorNeedsRefresh(current *space.RuntimeCoordinatorObservation, now time.Time) bool {
	return current == nil || now.Before(current.FetchedAt) || now.Sub(current.FetchedAt) >= runtimeCoordinatorFresh
}

// get returns a cached answer immediately. With no answer it waits at most
// five seconds for the one owner-bound run. Offline/failure without a previous
// answer is nil, never a fabricated zero limit. Caller cancellation is an error.
func (c *runtimeCoordinatorCache) get(ctx context.Context, key runtimeCoordinatorKey) (*space.RuntimeCoordinatorObservation, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if !c.matches(key) {
		return nil, errors.New("runtime state: coordinator scope changed")
	}
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return nil, context.Canceled
	}
	entry := c.entries[key]
	if entry == nil {
		entry = &runtimeCoordinatorEntry{}
		c.entries[key] = entry
	}
	now := time.Now()
	if entry.run == nil && (!entry.loaded || entry.dirty ||
		(runtimeCoordinatorNeedsRefresh(entry.current, now) && !now.Before(entry.retryAt))) {
		run := &runtimeCoordinatorRun{available: make(chan struct{})}
		entry.run = run
		c.wg.Add(1)
		go c.run(key, entry, run)
	}
	current, run := runtimeCoordinatorCopy(entry.current), entry.run
	c.mu.Unlock()
	if current != nil || run == nil {
		return current, nil
	}
	timer := time.NewTimer(runtimeCoordinatorWait)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-c.ctx.Done():
		return nil, context.Canceled
	case <-run.available:
	case <-timer.C:
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.closed {
		return nil, context.Canceled
	}
	return runtimeCoordinatorCopy(entry.current), nil
}

func (c *runtimeCoordinatorCache) run(key runtimeCoordinatorKey, entry *runtimeCoordinatorEntry, run *runtimeCoordinatorRun) {
	defer c.wg.Done()
	defer func() {
		c.mu.Lock()
		entry.run = nil
		c.mu.Unlock()
		run.answer()
	}()
	ctx, cancel := context.WithTimeout(c.ctx, runtimeCoordinatorFetch)
	defer cancel()
	c.mu.Lock()
	loaded, kv := entry.loaded, c.kv
	c.mu.Unlock()
	if !loaded {
		var stored *space.RuntimeCoordinatorObservation
		if kv != nil {
			raw, exists, err := kv.GetKV(ctx, runtimeCoordinatorStorageKey(key))
			if err == nil && exists {
				stored = decodeRuntimeCoordinator(raw, key)
			}
		}
		validScope := c.matches(key)
		c.mu.Lock()
		if !c.closed && validScope {
			entry.loaded = true
			if stored != nil && (entry.current == nil || stored.FetchedAt.After(entry.current.FetchedAt)) {
				entry.current = stored
			}
		}
		c.mu.Unlock()
	}
	c.mu.Lock()
	now := time.Now()
	hasAnswer := entry.current != nil
	refresh := !c.closed && runtimeCoordinatorNeedsRefresh(entry.current, now) && !now.Before(entry.retryAt)
	c.mu.Unlock()
	if hasAnswer {
		run.answer()
	}
	if refresh && c.matches(key) && ctx.Err() == nil {
		payloads, err := c.fetch(ctx, []string{key.SpaceID})
		var snapshot *space.RuntimeCoordinatorObservation
		if err == nil && len(payloads) == 1 && ctx.Err() == nil && c.matches(key) {
			snapshot = runtimeCoordinatorSnapshot(payloads[0], time.Now())
		}
		c.mu.Lock()
		if !c.closed {
			if snapshot != nil {
				if entry.current == nil || !entry.current.FetchedAt.After(snapshot.FetchedAt) {
					entry.current, entry.loaded, entry.dirty = snapshot, true, true
				}
				entry.retryAt = time.Time{}
			} else {
				entry.retryAt = time.Now().Add(runtimeCoordinatorRetry)
			}
		}
		c.mu.Unlock()
		run.answer()
	}
	// There is only one persistence writer for this exact key. If an existing
	// reconciler observation arrives during a disk write, persist that newer
	// value next. The fixed owner deadline bounds this loop as well as the RPC.
	for kv != nil && ctx.Err() == nil && c.matches(key) {
		c.mu.Lock()
		if c.closed || !entry.dirty || entry.current == nil {
			c.mu.Unlock()
			return
		}
		current := runtimeCoordinatorCopy(entry.current)
		entry.dirty = false
		c.mu.Unlock()
		raw, err := json.Marshal(runtimeCoordinatorStored{Version: 1, Scope: key, Snapshot: *current})
		if err == nil && len(raw) <= maxRuntimeStoredBytes {
			err = kv.SetKV(ctx, runtimeCoordinatorStorageKey(key), string(raw))
		} else if err == nil {
			err = errors.New("runtime state: cached answer too large")
		}
		if err != nil {
			c.mu.Lock()
			entry.dirty = true
			c.mu.Unlock()
			return
		}
	}
}

// remember records already successful, positionally aligned coordinator data.
// It never blocks the original deletion reconciler on extra I/O or launches a
// fetch. The next requested get persists a dirty answer in its owned run.
func (c *runtimeCoordinatorCache) remember(ids []string, payloads []*coordinatorproto.SpaceStatusPayload, fetchedAt time.Time) {
	if len(ids) != len(payloads) || fetchedAt.IsZero() {
		return
	}
	accountID, networkID, err := c.scope()
	if err != nil || accountID == "" || networkID == "" {
		return
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.closed {
		return
	}
	for i, id := range ids {
		if id == "" {
			continue
		}
		snapshot := runtimeCoordinatorSnapshot(payloads[i], fetchedAt)
		if snapshot == nil {
			continue
		}
		key := runtimeCoordinatorKey{AccountID: accountID, NetworkID: networkID, SpaceID: id}
		entry := c.entries[key]
		if entry == nil {
			entry = &runtimeCoordinatorEntry{}
			c.entries[key] = entry
		}
		if entry.current == nil || !entry.current.FetchedAt.After(snapshot.FetchedAt) {
			entry.current, entry.loaded, entry.dirty = snapshot, true, true
			entry.retryAt = time.Time{}
		}
	}
}
