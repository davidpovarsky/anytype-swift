package server

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/require"
)

func TestRuntimeStateWirePreservesAbsenceZeroAndOriginalAccessDomain(t *testing.T) {
	at := time.Date(2026, 11, 27, 5, 42, 46, 340108716, time.UTC)
	state := space.RuntimeState{
		Contract: space.RuntimeStateContract,
		Scope: space.RuntimeScope{AccountID: "account", NetworkID: "network", SpaceID: "space",
			AuthorityIdentity: "loaded-guest", ACLHeadID: "signed-head"},
		CapturedAt: at,
		Access:     space.RuntimeAccessEvidence{ACLIsEmpty: false, Reason: "personal_provenance_unavailable"},
	}
	encode := func() map[string]json.RawMessage {
		raw, err := json.Marshal(runtimeStateToAPI(state))
		require.NoError(t, err)
		var fields map[string]json.RawMessage
		require.NoError(t, json.Unmarshal(raw, &fields))
		require.Len(t, fields, 5)
		return fields
	}
	fields := encode()
	require.JSONEq(t, `null`, string(fields["coordinator"]))
	require.JSONEq(t, `{"aclIsEmpty":false,"personalSpaceId":null,"value":null,"reason":"personal_provenance_unavailable"}`, string(fields["access"]))
	require.Equal(t, `"2026-11-27T05:42:46.340108716Z"`, string(fields["capturedAt"]))
	state.Coordinator = &space.RuntimeCoordinatorObservation{
		FetchedAt: at, Status: "original-coordinator-label", IsShared: false,
	}
	fields = encode()
	require.JSONEq(t, `{"fetchedAt":"2026-11-27T05:42:46.340108716Z","status":"original-coordinator-label","isShared":false,"limits":null}`, string(fields["coordinator"]))
	state.Coordinator.Limits = &space.RuntimeMemberLimits{ReadersLimit: 0, WritersLimit: 0}
	fields = encode()
	require.Contains(t, string(fields["coordinator"]), `"readersLimit":0`)
	require.Contains(t, string(fields["coordinator"]), `"writersLimit":0`)
	for _, value := range []space.RuntimeAccessType{space.RuntimeAccessPrivate, space.RuntimeAccessPersonal, space.RuntimeAccessShared} {
		state.Access.Value = &value
		converted := runtimeStateToAPI(state)
		require.Equal(t, uint8(value), *converted.Access.Value)
	}
}

func TestRuntimeObjectWireDoesNotCastSDKSyncIntoHeartDomain(t *testing.T) {
	at := time.Date(2026, 11, 27, 5, 42, 46, 340108716, time.UTC)
	state := space.RuntimeObjectState{
		Contract: space.RuntimeObjectStateContract, ObjectID: "exact-native-object", CapturedAt: at.Add(time.Second),
		Scope: space.RuntimeScope{AccountID: "account", NetworkID: "network", SpaceID: "space",
			AuthorityIdentity: "current-reader", ACLHeadID: "signed-head"},
		ObjectSync: space.RuntimeObjectSyncObservation{State: space.SyncStateSynced,
			Basis: space.RuntimeSyncResponsibleSpaceRound, LastSyncAt: &at},
		SpaceSync: space.RuntimeSpaceSyncObservation{SpaceID: "space", State: space.SyncStateOffline,
			P2P: space.P2PStateNotConnected, LastSyncedAt: &at},
	}
	converted := runtimeObjectStateToAPI(state)
	require.Equal(t, "synced", converted.ObjectSync.State)
	require.Equal(t, "responsible_space_round", converted.ObjectSync.Basis)
	require.Equal(t, "offline", converted.SpaceSync.State)
	require.Equal(t, "notconnected", converted.SpaceSync.P2P)
	require.Equal(t, at, *converted.ObjectSync.LastSyncAt)
	require.NotEqual(t, converted.CapturedAt, *converted.ObjectSync.LastSyncAt)
	raw, err := json.Marshal(converted)
	require.NoError(t, err)
	require.NotContains(t, string(raw), "syncDate")
	require.NotContains(t, string(raw), "queued")
	state.ObjectSync = space.RuntimeObjectSyncObservation{State: space.SyncStateUnknown, Basis: space.RuntimeSyncUnobserved}
	raw, err = json.Marshal(runtimeObjectStateToAPI(state))
	require.NoError(t, err)
	require.Contains(t, string(raw), `"lastSyncAt":null`)
	require.Contains(t, string(raw), `"state":"unknown"`)
}

func TestRuntimeStateRoutesAdvertiseOnlyVersionedOptionalReads(t *testing.T) {
	e := echo.New()
	registerRuntimeStateRoutes(e.Group("/v1"), &deps{})
	routes := e.Routes()
	require.Len(t, routes, 2)
	paths := make([]string, 0, 2)
	for _, route := range routes {
		require.Equal(t, http.MethodGet, route.Method)
		paths = append(paths, route.Path)
	}
	require.ElementsMatch(t, []string{"/v1/spaces/:spaceId/runtime-state", "/v1/spaces/:spaceId/objects/:objectId/runtime-state"}, paths)
	request := httptest.NewRequest(http.MethodGet, "/", nil)
	recorder := httptest.NewRecorder()
	err := runtimeStateUnsupported(e.NewContext(request, recorder))
	require.NoError(t, err)
	require.Equal(t, http.StatusNotImplemented, recorder.Code)
	require.Contains(t, recorder.Body.String(), `"code":"runtime_state.unsupported"`)
	require.NotContains(t, recorder.Body.String(), "ownRole")
}
