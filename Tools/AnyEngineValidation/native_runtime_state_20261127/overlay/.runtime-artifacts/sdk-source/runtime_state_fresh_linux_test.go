//go:build linux

package anysyncsdk

import (
	"testing"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/stretchr/testify/require"
)

// Only this new method is selected. The unchanged fresh-fixture constructor
// creates a new OS-isolated SDK/account/Space and verifies its own signed ACL
// transitions. No retained account, key, snapshot or old test method is used.
func TestRuntimeStateFreshScopeAndSyncStopAtSignedRemoval(t *testing.T) {
	fixture := newFreshFilesFixture(t, true)
	provider, ok := fixture.space.(space.RuntimeStateProvider)
	require.True(t, ok, "the actual regular SDK Space exposes the optional provider")
	fixture.localACL.RLock()
	head := fixture.localACL.Head().Id
	identity := fixture.localACL.AclState().Identity().Account()
	isEmpty := fixture.localACL.AclState().IsEmpty()
	fixture.localACL.RUnlock()
	state, err := provider.RuntimeState(fixture.ctx)
	require.NoError(t, err)
	require.Equal(t, space.RuntimeStateContract, state.Contract)
	require.Equal(t, fixture.localID, state.Scope.AccountID)
	require.Equal(t, fixture.sdk.app.NetworkId(), state.Scope.NetworkID)
	require.Equal(t, fixture.space.Id(), state.Scope.SpaceID)
	require.Equal(t, identity, state.Scope.AuthorityIdentity)
	require.Equal(t, head, state.Scope.ACLHeadID)
	require.Equal(t, isEmpty, state.Access.ACLIsEmpty)
	require.Nil(t, state.Coordinator, "new OS-offline fixture has no accepted coordinator answer")
	require.Nil(t, state.Access.Value)
	require.Nil(t, state.Access.PersonalSpaceID)
	require.Equal(t, "personal_provenance_unavailable", state.Access.Reason)
	require.False(t, state.CapturedAt.IsZero())
	objectID := fixture.space.SpaceIndexObjectId()
	object, err := provider.RuntimeObjectState(fixture.ctx, objectID)
	require.NoError(t, err)
	require.Equal(t, space.RuntimeObjectStateContract, object.Contract)
	require.Equal(t, state.Scope, object.Scope)
	require.Equal(t, objectID, object.ObjectID)
	require.Equal(t, fixture.space.Id(), object.SpaceSync.SpaceID)
	legacy := fixture.space.SyncStatus().Object(objectID)
	require.Equal(t, legacy.State, object.ObjectSync.State)
	if legacy.LastSyncAt.IsZero() {
		require.Nil(t, object.ObjectSync.LastSyncAt)
	} else {
		require.Equal(t, legacy.LastSyncAt.UTC(), *object.ObjectSync.LastSyncAt)
	}
	fixture.revoke(t)
	state, err = provider.RuntimeState(fixture.ctx)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, state)
	object, err = provider.RuntimeObjectState(fixture.ctx, objectID)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, object)
}
