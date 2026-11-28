package server

import (
	"net/http"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/labstack/echo/v4"

	"github.com/anyproto/any/internal/api"
)

func registerRuntimeStateRoutes(g *echo.Group, d *deps) {
	g.GET("/spaces/:spaceId/runtime-state", d.spaceRuntimeState)
	g.GET("/spaces/:spaceId/objects/:objectId/runtime-state", d.objectRuntimeState)
}

// The optional SDK interface plus a successful versioned contract response is
// the capability boundary. Unsupported implementations never fall back to a
// cached SpaceInfo role or to unguarded legacy sync status.
func runtimeStateUnsupported(c echo.Context) error {
	return writeError(c, http.StatusNotImplemented, "runtime_state.unsupported",
		"this Space does not provide current-authority runtime observations", nil)
}

func (d *deps) spaceRuntimeState(c echo.Context) error {
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	provider, ok := sp.(space.RuntimeStateProvider)
	if !ok {
		return runtimeStateUnsupported(c)
	}
	state, err := provider.RuntimeState(c.Request().Context())
	if err != nil {
		return sdkOpError(c, err, map[string]any{"spaceId": sp.Id()})
	}
	return c.JSON(http.StatusOK, runtimeStateToAPI(state))
}

func (d *deps) objectRuntimeState(c echo.Context) error {
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	provider, ok := sp.(space.RuntimeStateProvider)
	if !ok {
		return runtimeStateUnsupported(c)
	}
	objectID := c.Param("objectId")
	if objectID == "" {
		return writeError(c, http.StatusBadRequest, "request.missing_field", "objectId required", nil)
	}
	if isSerializedNil(objectID) {
		return serializedNilIdError(c, "objectId", objectID)
	}
	// This new route takes the exact native ID. It performs no short-ID or
	// metadata lookup before the provider's current-authority admission.
	state, err := provider.RuntimeObjectState(c.Request().Context(), objectID)
	if err != nil {
		return sdkOpError(c, err, map[string]any{"spaceId": sp.Id(), "objectId": objectID})
	}
	return c.JSON(http.StatusOK, runtimeObjectStateToAPI(state))
}

func runtimeScopeToAPI(scope space.RuntimeScope) api.RuntimeScope {
	return api.RuntimeScope{
		AccountID: scope.AccountID, NetworkID: scope.NetworkID, SpaceID: scope.SpaceID,
		AuthorityIdentity: scope.AuthorityIdentity, ACLHeadID: scope.ACLHeadID,
	}
}

func runtimeStateToAPI(state space.RuntimeState) api.RuntimeStateResponse {
	out := api.RuntimeStateResponse{
		Contract: state.Contract, Scope: runtimeScopeToAPI(state.Scope), CapturedAt: state.CapturedAt,
		Access: api.RuntimeAccessEvidence{
			ACLIsEmpty: state.Access.ACLIsEmpty, PersonalSpaceID: state.Access.PersonalSpaceID, Reason: state.Access.Reason,
		},
	}
	if state.Access.Value != nil {
		value := uint8(*state.Access.Value) // the explicit original access domain, not a sync enum cast
		out.Access.Value = &value
	}
	if state.Coordinator != nil {
		out.Coordinator = &api.RuntimeCoordinatorObservation{
			FetchedAt: state.Coordinator.FetchedAt, Status: state.Coordinator.Status, IsShared: state.Coordinator.IsShared,
		}
		if state.Coordinator.Limits != nil {
			out.Coordinator.Limits = &api.RuntimeMemberLimits{
				ReadersLimit: state.Coordinator.Limits.ReadersLimit, WritersLimit: state.Coordinator.Limits.WritersLimit,
			}
		}
	}
	return out
}

func runtimeObjectStateToAPI(state space.RuntimeObjectState) api.RuntimeObjectStateResponse {
	return api.RuntimeObjectStateResponse{
		Contract: state.Contract, Scope: runtimeScopeToAPI(state.Scope), ObjectID: state.ObjectID, CapturedAt: state.CapturedAt,
		ObjectSync: api.RuntimeObjectSyncObservation{
			State: state.ObjectSync.State.String(), Basis: string(state.ObjectSync.Basis), LastSyncAt: state.ObjectSync.LastSyncAt,
		},
		SpaceSync: api.RuntimeSpaceSyncObservation{
			SpaceID: state.SpaceSync.SpaceID, State: state.SpaceSync.State.String(),
			Synced: state.SpaceSync.Synced, Total: state.SpaceSync.Total,
			NetworkPeers: state.SpaceSync.NetworkPeers, LocalPeers: state.SpaceSync.LocalPeers, GlobalPeers: state.SpaceSync.GlobalPeers,
			P2P: state.SpaceSync.P2P.String(), LastSyncedAt: state.SpaceSync.LastSyncedAt,
			NetworkProtocolIncompatible: state.SpaceSync.NetworkProtocolIncompatible,
		},
	}
}
