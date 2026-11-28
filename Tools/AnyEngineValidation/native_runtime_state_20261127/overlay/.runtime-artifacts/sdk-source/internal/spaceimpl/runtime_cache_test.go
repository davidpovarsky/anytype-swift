package spaceimpl

import (
	"context"
	"encoding/json"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any-sync/coordinator/coordinatorproto"
	"github.com/stretchr/testify/require"
)

type runtimeMemoryKV struct {
	mu   sync.Mutex
	data map[string]string
}

func (k *runtimeMemoryKV) GetKV(ctx context.Context, key string) (string, bool, error) {
	if err := ctx.Err(); err != nil {
		return "", false, err
	}
	k.mu.Lock()
	defer k.mu.Unlock()
	value, ok := k.data[key]
	return value, ok, nil
}

func (k *runtimeMemoryKV) SetKV(ctx context.Context, key, value string) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	k.mu.Lock()
	defer k.mu.Unlock()
	k.data[key] = value
	return nil
}

func runtimeTestScope() (string, string, error) { return "new-account", "new-network", nil }

func runtimeTestKey() runtimeCoordinatorKey {
	return runtimeCoordinatorKey{AccountID: "new-account", NetworkID: "new-network", SpaceID: "new-space"}
}

func TestRuntimeCoordinatorMissingLimitsAndExplicitZeroStayDistinct(t *testing.T) {
	key := runtimeTestKey()
	at := time.Date(2026, 11, 27, 5, 42, 46, 340108716, time.UTC)
	missing := runtimeCoordinatorSnapshot(&coordinatorproto.SpaceStatusPayload{Status: coordinatorproto.SpaceStatus(0)}, at)
	require.NotNil(t, missing)
	require.Equal(t, coordinatorproto.SpaceStatus(0).String(), missing.Status)
	require.Nil(t, missing.Limits)
	zero := runtimeCoordinatorSnapshot(&coordinatorproto.SpaceStatusPayload{
		Status: coordinatorproto.SpaceStatus(0), Limits: &coordinatorproto.SpaceLimits{ReadMembers: 0, WriteMembers: 0},
	}, at)
	require.NotNil(t, zero.Limits)
	require.EqualValues(t, 0, zero.Limits.ReadersLimit)
	require.EqualValues(t, 0, zero.Limits.WritersLimit)
	for _, snapshot := range []*space.RuntimeCoordinatorObservation{missing, zero} {
		raw, err := json.Marshal(runtimeCoordinatorStored{Version: 1, Scope: key, Snapshot: *snapshot})
		require.NoError(t, err)
		got := decodeRuntimeCoordinator(string(raw), key)
		require.Equal(t, snapshot, got)
		require.Equal(t, at, got.FetchedAt)
	}
	copy := runtimeCoordinatorCopy(zero)
	copy.Limits.ReadersLimit = 99
	require.Zero(t, zero.Limits.ReadersLimit, "callers never mutate the cached answer")
}

func TestRuntimeCoordinatorRejectsMalformedAndForeignCachedAnswers(t *testing.T) {
	key := runtimeTestKey()
	snapshot := runtimeCoordinatorSnapshot(&coordinatorproto.SpaceStatusPayload{
		Status: coordinatorproto.SpaceStatus(0), Limits: &coordinatorproto.SpaceLimits{ReadMembers: 3, WriteMembers: 2},
	}, time.Now())
	raw, err := json.Marshal(runtimeCoordinatorStored{Version: 1, Scope: key, Snapshot: *snapshot})
	require.NoError(t, err)
	for _, change := range []func(*runtimeCoordinatorKey){
		func(k *runtimeCoordinatorKey) { k.AccountID += "-other" },
		func(k *runtimeCoordinatorKey) { k.NetworkID += "-other" },
		func(k *runtimeCoordinatorKey) { k.SpaceID += "-other" },
	} {
		foreign := key
		change(&foreign)
		require.Nil(t, decodeRuntimeCoordinator(string(raw), foreign))
		require.NotEqual(t, runtimeCoordinatorStorageKey(key), runtimeCoordinatorStorageKey(foreign))
	}
	var stored map[string]any
	require.NoError(t, json.Unmarshal(raw, &stored))
	for _, field := range []string{"FetchedAt", "Status", "IsShared", "Limits"} {
		var malformed map[string]any
		require.NoError(t, json.Unmarshal(raw, &malformed))
		delete(malformed["snapshot"].(map[string]any), field)
		encoded, err := json.Marshal(malformed)
		require.NoError(t, err)
		require.Nil(t, decodeRuntimeCoordinator(string(encoded), key), field)
	}
	stored["snapshot"].(map[string]any)["Limits"] = map[string]any{"ReadersLimit": 0}
	malformed, err := json.Marshal(stored)
	require.NoError(t, err)
	require.Nil(t, decodeRuntimeCoordinator(string(malformed), key))
	require.Nil(t, runtimeCoordinatorSnapshot(nil, time.Now()))
	require.Nil(t, runtimeCoordinatorSnapshot(&coordinatorproto.SpaceStatusPayload{Status: coordinatorproto.SpaceStatus(-99)}, time.Now()))
	cache := newRuntimeCoordinatorCache(runtimeTestScope, nil)
	t.Cleanup(cache.close)
	cache.remember([]string{key.SpaceID, "other-space"}, []*coordinatorproto.SpaceStatusPayload{{Status: coordinatorproto.SpaceStatus(0)}}, time.Now())
	require.Empty(t, cache.entries, "a response count mismatch publishes no positional cache rows")
}

func TestRuntimeCoordinatorPersistsSuccessfulAnswerAcrossOfflineReopen(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	kv := &runtimeMemoryKV{data: map[string]string{}}
	var calls atomic.Int32
	cache := newRuntimeCoordinatorCache(runtimeTestScope, func(ctx context.Context, ids []string) ([]*coordinatorproto.SpaceStatusPayload, error) {
		calls.Add(1)
		if len(ids) != 1 || ids[0] != runtimeTestKey().SpaceID {
			return nil, errors.New("unexpected requested scope")
		}
		return []*coordinatorproto.SpaceStatusPayload{{Status: coordinatorproto.SpaceStatus(0), IsShared: true,
			Limits: &coordinatorproto.SpaceLimits{ReadMembers: 0, WriteMembers: 7}}}, nil
	})
	cache.setKV(kv)
	defer cache.close()
	got, err := cache.get(ctx, runtimeTestKey())
	require.NoError(t, err)
	require.NotNil(t, got)
	require.NotNil(t, got.Limits)
	require.Zero(t, got.Limits.ReadersLimit)
	require.EqualValues(t, 7, got.Limits.WritersLimit)
	// The cached value is persisted before this run's positive join. Waiting
	// here is test coordination; no production lock is held across I/O.
	cache.wg.Wait()
	require.EqualValues(t, 1, calls.Load())
	cache.close()
	offline := newRuntimeCoordinatorCache(runtimeTestScope, func(context.Context, []string) ([]*coordinatorproto.SpaceStatusPayload, error) {
		return nil, errors.New("new fixture is offline")
	})
	offline.setKV(kv)
	defer offline.close()
	reopened, err := offline.get(ctx, runtimeTestKey())
	require.NoError(t, err)
	require.Equal(t, got, reopened, "disk reopen retains the actual timestamp and zero limit")
	foreign := runtimeTestKey()
	foreign.SpaceID = "never-observed-space"
	absent, err := offline.get(ctx, foreign)
	require.NoError(t, err)
	require.Nil(t, absent, "offline absence remains distinct from the other Space's observed zero")
}

func TestRuntimeCoordinatorCoalescesFetchAndDrainsOwnerCancellation(t *testing.T) {
	entered := make(chan struct{}, 1)
	var calls atomic.Int32
	cache := newRuntimeCoordinatorCache(runtimeTestScope, func(ctx context.Context, ids []string) ([]*coordinatorproto.SpaceStatusPayload, error) {
		calls.Add(1)
		select {
		case entered <- struct{}{}:
		default:
		}
		<-ctx.Done()
		return nil, ctx.Err()
	})
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	defer cache.close()
	type outcome struct {
		value *space.RuntimeCoordinatorObservation
		err   error
	}
	results := make(chan outcome, 2)
	for i := 0; i < 2; i++ {
		go func() { value, err := cache.get(ctx, runtimeTestKey()); results <- outcome{value, err} }()
	}
	select {
	case <-entered:
	case <-ctx.Done():
		t.Fatal("coalesced worker did not reach its controlled fetch")
	}
	cache.close()
	for i := 0; i < 2; i++ {
		select {
		case result := <-results:
			require.Nil(t, result.value)
			require.ErrorIs(t, result.err, context.Canceled)
		case <-ctx.Done():
			t.Fatal("caller remained blocked after the cache owner drained")
		}
	}
	require.EqualValues(t, 1, calls.Load())
}

func TestRuntimeAccessNeedsPositiveOriginalPersonalProvenance(t *testing.T) {
	require.EqualValues(t, 0, space.RuntimeAccessPrivate)
	require.EqualValues(t, 1, space.RuntimeAccessPersonal)
	require.EqualValues(t, 2, space.RuntimeAccessShared)
	for _, empty := range []bool{false, true} {
		for _, coordinator := range []*space.RuntimeCoordinatorObservation{nil, {IsShared: false}, {IsShared: true}} {
			got := runtimeAccessEvidence("candidate", empty, nil, coordinator)
			require.Nil(t, got.Value)
			require.Nil(t, got.PersonalSpaceID)
			require.Equal(t, "personal_provenance_unavailable", got.Reason)
		}
	}
	personal := "original-native-personal"
	for _, shared := range []bool{false, true} {
		got := runtimeAccessEvidence(personal, !shared, &personal, &space.RuntimeCoordinatorObservation{IsShared: shared})
		require.Equal(t, space.RuntimeAccessPersonal, *got.Value, "original Personal classification is sticky")
		require.Equal(t, "native_personal", got.Reason)
	}
	shared := runtimeAccessEvidence("other", false, &personal, nil)
	require.Equal(t, space.RuntimeAccessShared, *shared.Value)
	require.Equal(t, "native_acl_shared", shared.Reason)
	shareable := runtimeAccessEvidence("other", true, &personal, &space.RuntimeCoordinatorObservation{IsShared: true})
	require.Equal(t, space.RuntimeAccessShared, *shareable.Value, "shareable need not have an additional member")
	unknown := runtimeAccessEvidence("other", true, &personal, nil)
	require.Nil(t, unknown.Value)
	require.Equal(t, "coordinator_unavailable", unknown.Reason)
	private := runtimeAccessEvidence("other", true, &personal, &space.RuntimeCoordinatorObservation{IsShared: false})
	require.Equal(t, space.RuntimeAccessPrivate, *private.Value)
}
