package syncstatus

import (
	"testing"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/stretchr/testify/require"
)

func TestRuntimeSyncObservationPreservesOriginalDomainsAndPrecedence(t *testing.T) {
	// The SDK's sync domain is not Heart's historical relation domain.
	require.EqualValues(t, 0, space.SyncStateUnknown)
	require.EqualValues(t, 1, space.SyncStateOffline)
	require.EqualValues(t, 2, space.SyncStateSyncing)
	require.EqualValues(t, 3, space.SyncStateSynced)
	require.EqualValues(t, 4, space.SyncStateError)
	service := NewService()
	t.Cleanup(service.Close)
	connected, incompatible := true, false
	service.SetNodeIdsFn(func(string) []string { return []string{"responsible-peer"} })
	service.SetPeerCountsFn(func(string) (int, int, int) {
		if connected {
			return 1, 0, 0
		}
		return 0, 0, 0
	})
	service.SetNetworkIncompatibleFn(func() bool { return incompatible })
	service.SetTotalFn(func(string) int { return 1 })
	tracker := service.For("scope-space")
	tracker.HeadsChange("object", []string{"head"})
	before, status := service.RuntimeObservation("scope-space", "object")
	require.Equal(t, space.RuntimeSyncPerObjectHooks, before.Basis)
	require.Equal(t, space.SyncStateSyncing, before.State)
	require.Nil(t, before.LastSyncAt)
	require.Equal(t, space.SyncStateSyncing, status.State)
	tracker.HeadsApply("responsible-peer", "object", []string{"head"}, true)
	confirmed := tracker.Object("object")
	object, status := service.RuntimeObservation("scope-space", "object")
	require.Equal(t, space.SyncStateSynced, object.State)
	require.Equal(t, confirmed.LastSyncAt.UTC(), *object.LastSyncAt)
	require.Equal(t, space.SyncStateSynced, status.State)
	connected = false
	object, status = service.RuntimeObservation("scope-space", "object")
	require.Equal(t, space.SyncStateSynced, object.State, "retained object confirmation is not a claim of current connectivity")
	require.Equal(t, confirmed.LastSyncAt.UTC(), *object.LastSyncAt)
	require.Equal(t, space.SyncStateOffline, status.State)
	incompatible = true
	_, status = service.RuntimeObservation("scope-space", "object")
	require.Equal(t, space.SyncStateError, status.State, "protocol error retains the original precedence over offline")
	require.True(t, status.NetworkProtocolIncompatible)
}

func TestRuntimeSyncObservationDistinguishesInheritedAndUnobserved(t *testing.T) {
	service := NewService()
	t.Cleanup(service.Close)
	service.SetNodeIdsFn(func(string) []string { return []string{"responsible-peer"} })
	service.SetHasTreeFn(func(spaceID, objectID string) bool { return spaceID == "scope-space" && objectID == "stored-object" })
	service.SetPeerCountsFn(func(string) (int, int, int) { return 1, 0, 0 })
	object, status := service.RuntimeObservation("untracked-space", "unknown-object")
	require.Nil(t, service.trackerNoCreate("untracked-space"), "a runtime read creates no tracking state")
	require.Equal(t, space.SyncStateUnknown, status.State)
	require.Equal(t, space.RuntimeSyncUnobserved, object.Basis)
	require.Nil(t, object.LastSyncAt)
	tracker := service.For("scope-space")
	tracker.BulkSyncedFromPeer("responsible-peer")
	object, _ = service.RuntimeObservation("scope-space", "stored-object")
	state, pending, at, known := tracker.Detail("stored-object")
	require.False(t, known)
	require.Empty(t, pending)
	require.Equal(t, state, object.State)
	require.Equal(t, space.RuntimeSyncResponsibleSpaceRound, object.Basis)
	require.Equal(t, at.UTC(), *object.LastSyncAt)
	foreign, _ := service.RuntimeObservation("scope-space", "not-stored-here")
	require.Equal(t, space.RuntimeSyncUnobserved, foreign.Basis)
	require.Equal(t, space.SyncStateUnknown, foreign.State)
	require.Nil(t, foreign.LastSyncAt)
}
