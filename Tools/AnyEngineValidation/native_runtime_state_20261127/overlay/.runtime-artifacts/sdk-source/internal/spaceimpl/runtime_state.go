package spaceimpl

import (
	"context"
	"errors"
	"time"

	"github.com/anyproto/any-sync-sdk/internal/files/readguard"
	"github.com/anyproto/any-sync-sdk/space"
)

var _ space.RuntimeStateProvider = (*spaceImpl)(nil)

// runtimeAccountScope reads the existing captured App, never a global active
// account or a caller-supplied identity. It copies only public identifiers.
func (s *Service) runtimeAccountScope() (accountID, networkID string, err error) {
	if s.app == nil {
		return "", "", errors.New("runtime state: account unavailable")
	}
	keys := s.app.AccountKeys()
	if keys == nil || keys.SignKey == nil {
		return "", "", errors.New("runtime state: account identity unavailable")
	}
	accountID = keys.SignKey.GetPublic().Account()
	networkID = s.app.NetworkId()
	if accountID == "" || networkID == "" {
		return "", "", errors.New("runtime state: account/network scope unavailable")
	}
	return accountID, networkID, nil
}

func (s *spaceImpl) runtimeScope(observed readguard.Observation) (space.RuntimeScope, error) {
	if s.parent == nil {
		return space.RuntimeScope{}, errors.New("runtime state: service unavailable")
	}
	accountID, networkID, err := s.parent.runtimeAccountScope()
	if err != nil {
		return space.RuntimeScope{}, err
	}
	return space.RuntimeScope{
		AccountID: accountID, NetworkID: networkID, SpaceID: s.id,
		AuthorityIdentity: observed.Identity, ACLHeadID: observed.HeadID,
	}, nil
}

func (s *spaceImpl) runtimeScopeUnchanged(scope space.RuntimeScope) error {
	accountID, networkID, err := s.parent.runtimeAccountScope()
	if err != nil {
		return err
	}
	if accountID != scope.AccountID || networkID != scope.NetworkID || s.id != scope.SpaceID {
		return errors.New("runtime state: account/network/Space scope changed")
	}
	return nil
}

func (s *spaceImpl) RuntimeState(ctx context.Context) (space.RuntimeState, error) {
	return readguard.ObserveValue(ctx, s.fileReadACL, func(observed readguard.Observation) (space.RuntimeState, error) {
		scope, err := s.runtimeScope(observed)
		if err != nil {
			return space.RuntimeState{}, err
		}
		var coordinator *space.RuntimeCoordinatorObservation
		if s.parent.runtimeCoordinator != nil {
			coordinator, err = s.parent.runtimeCoordinator.get(ctx, runtimeCoordinatorKey{
				AccountID: scope.AccountID, NetworkID: scope.NetworkID, SpaceID: scope.SpaceID,
			})
			if err != nil {
				return space.RuntimeState{}, err
			}
		}
		if err := s.runtimeScopeUnchanged(scope); err != nil {
			return space.RuntimeState{}, err
		}
		return space.RuntimeState{
			Contract: space.RuntimeStateContract, Scope: scope, CapturedAt: time.Now().UTC(),
			Coordinator: coordinator,
			// The present native producer has no positive original Personal
			// provenance. Generic Derived/owner/member counts cannot fill it.
			Access: runtimeAccessEvidence(s.id, observed.ACLIsEmpty, nil, coordinator),
		}, nil
	})
}

// runtimeAccessEvidence follows original Personal-first classification only
// after that account's actual native Personal identity is positively known.
// The current production call deliberately passes nil; no external setter or
// caller hint can inject the missing provenance.
func runtimeAccessEvidence(spaceID string, aclIsEmpty bool, personalSpaceID *string, coordinator *space.RuntimeCoordinatorObservation) space.RuntimeAccessEvidence {
	out := space.RuntimeAccessEvidence{ACLIsEmpty: aclIsEmpty, Reason: "personal_provenance_unavailable"}
	if personalSpaceID == nil || *personalSpaceID == "" {
		return out
	}
	personal := *personalSpaceID
	out.PersonalSpaceID = &personal
	var value space.RuntimeAccessType
	switch {
	case spaceID == personal:
		value, out.Reason = space.RuntimeAccessPersonal, "native_personal"
	case !aclIsEmpty:
		value, out.Reason = space.RuntimeAccessShared, "native_acl_shared"
	case coordinator == nil:
		out.Reason = "coordinator_unavailable"
		return out
	case coordinator.IsShared:
		value, out.Reason = space.RuntimeAccessShared, "coordinator_shared"
	default:
		value, out.Reason = space.RuntimeAccessPrivate, "native_private"
	}
	out.Value = &value
	return out
}

func (s *spaceImpl) RuntimeObjectState(ctx context.Context, objectID string) (space.RuntimeObjectState, error) {
	return readguard.ObserveValue(ctx, s.fileReadACL, func(observed readguard.Observation) (space.RuntimeObjectState, error) {
		if objectID == "" {
			return space.RuntimeObjectState{}, space.ErrRuntimeObjectIDRequired
		}
		scope, err := s.runtimeScope(observed)
		if err != nil {
			return space.RuntimeObjectState{}, err
		}
		object := space.RuntimeObjectSyncObservation{State: space.SyncStateUnknown, Basis: space.RuntimeSyncUnobserved}
		status := space.RuntimeSpaceSyncObservation{SpaceID: s.id, State: space.SyncStateUnknown, P2P: space.P2PStateUnknown}
		if service := s.app.SyncStatus(); service != nil {
			object, status = service.RuntimeObservation(s.id, objectID)
		}
		if err := s.runtimeScopeUnchanged(scope); err != nil {
			return space.RuntimeObjectState{}, err
		}
		return space.RuntimeObjectState{
			Contract: space.RuntimeObjectStateContract, Scope: scope, ObjectID: objectID,
			CapturedAt: time.Now().UTC(), ObjectSync: object, SpaceSync: status,
		}, nil
	})
}
