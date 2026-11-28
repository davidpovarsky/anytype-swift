package syncstatus

import (
	"time"

	"github.com/anyproto/any-sync-sdk/space"
)

// RuntimeObservation samples existing tracker and presence facts without
// creating a tracker or changing its state. It is not a cross-service atomic
// consensus snapshot. The SDK caller supplies the current authority fence.
func (s *Service) RuntimeObservation(spaceID, objectID string) (space.RuntimeObjectSyncObservation, space.RuntimeSpaceSyncObservation) {
	object := space.RuntimeObjectSyncObservation{
		State: space.SyncStateUnknown, Basis: space.RuntimeSyncUnobserved,
	}
	if tracker := s.trackerNoCreate(spaceID); tracker != nil {
		row, known, inherited := tracker.lookup(objectID, false)
		switch {
		case known:
			object.State = row.state
			object.Basis = space.RuntimeSyncPerObjectHooks
			object.LastSyncAt = runtimeTimestamp(row.lastApplied)
		case !inherited.IsZero():
			object.State = space.SyncStateSynced
			object.Basis = space.RuntimeSyncResponsibleSpaceRound
			object.LastSyncAt = runtimeTimestamp(inherited)
		}
	}
	status := s.Status(spaceID)
	return object, space.RuntimeSpaceSyncObservation{
		SpaceID: status.SpaceId, State: status.State, Synced: status.Synced, Total: status.Total,
		NetworkPeers: status.NetworkPeers, LocalPeers: status.LocalPeers, GlobalPeers: status.GlobalPeers,
		P2P: status.P2P, LastSyncedAt: runtimeTimestamp(status.LastSyncedAt),
		NetworkProtocolIncompatible: s.incompatible(),
	}
}

func runtimeTimestamp(value time.Time) *time.Time {
	if value.IsZero() {
		return nil
	}
	value = value.UTC()
	return &value
}
