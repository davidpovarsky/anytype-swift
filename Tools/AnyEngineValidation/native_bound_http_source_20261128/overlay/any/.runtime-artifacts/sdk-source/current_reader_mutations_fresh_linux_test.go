//go:build linux

package anysyncsdk

import (
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/stretchr/testify/require"
	"github.com/valyala/fastjson"
)

// The unchanged constructor creates new keys, a new SDK and a new Space. Its
// signed ownership transfer makes this SDK a Reader; removal is a subsequent
// signed ACL record verified by the production loaded ACL. No retained account
// or old test method is used. The encrypted fixture payload is incidental setup,
// not an additional transfer, durability or performance qualification.
func TestCurrentReaderLocalSettingsAndBuiltinStopAtSignedRemoval(t *testing.T) {
	var deletedObjectID string
	fixture := newFreshFilesFixtureWithPreparation(t, true, nil, func(f *freshFilesFixture) {
		owner, err := f.space.Types().Create(f.ctx, space.TypeCreateParams{Name: "new deleted-target fixture"})
		require.NoError(t, err)
		deletedObjectID, err = f.space.Objects().Create(f.ctx, space.CreateObjectOpts{Type: owner})
		require.NoError(t, err)
		require.NoError(t, f.space.Objects().Delete(f.ctx, deletedObjectID))
	})
	local, ok := fixture.space.Properties().(space.CurrentReaderLocalProperties)
	require.True(t, ok)
	settings, ok := fixture.sdk.Spaces().(space.CurrentReaderSettings)
	require.True(t, ok)
	authority, ok := fixture.space.(space.CurrentReaderAuthority)
	require.True(t, ok)
	require.NoError(t, authority.CheckCurrentReader(fixture.ctx))
	fixture.localACL.RLock()
	permission := fixture.localACL.AclState().Permissions(fixture.sdk.app.AccountKeys().SignKey.GetPublic())
	fixture.localACL.RUnlock()
	require.Equal(t, list.AclPermissionsReader, permission)

	// The catalog declares this exact immutable native LOCAL datetime without
	// a per-Space definition creation or shared-WRITE grant.
	defs, err := fixture.space.Types().Properties(fixture.ctx, "any")
	require.NoError(t, err)
	found := 0
	for _, def := range defs {
		if def.Id != "pinkhaLastOpenedV1" {
			continue
		}
		found++
		require.Equal(t, space.PropertyKindDatetime, def.Kind)
		require.Equal(t, space.ScopeLocal, def.Scope)
		require.Equal(t, "datetime", def.XFormat["type"])
		require.Equal(t, "pinkha-last-opened-local-v1", def.XFormat["contract"])
		require.Equal(t, "seconds", def.XFormat["precision"])
	}
	require.Equal(t, 1, found)
	require.ErrorIs(t, fixture.space.Types().RemoveProperty(fixture.ctx, "any", "pinkhaLastOpenedV1"), space.ErrTypeRegistered)
	stillDeclared, err := fixture.space.Types().Properties(fixture.ctx, "any")
	require.NoError(t, err)
	require.Equal(t, defs, stillDeclared)

	objectID := fixture.space.SpaceIndexObjectId()
	const field = "pinkhaLastOpenedV1"
	stamp := time.Unix(1760000123, 0).UTC()
	written, err := local.SetLocalCurrentReader(fixture.ctx, objectID, "any", map[string]any{field: stamp})
	require.NoError(t, err)
	require.NotEmpty(t, written.VersionId)
	require.Empty(t, written.ChangeId, "device-local value must not append a signed shared change")
	require.Empty(t, written.Rejections)
	require.Equal(t, []string{objectID}, written.RecordIds)
	// Repeating this exact local value still follows the native local route:
	// no DAG change and the same explicit result target, without a new upload.
	repeated, err := local.SetLocalCurrentReader(fixture.ctx, objectID, "any", map[string]any{field: stamp})
	require.NoError(t, err)
	require.NotEmpty(t, repeated.VersionId)
	require.Empty(t, repeated.ChangeId)
	require.Equal(t, []string{objectID}, repeated.RecordIds)
	require.Empty(t, repeated.Rejections)
	row, err := fixture.space.Properties().Get(fixture.ctx, objectID)
	require.NoError(t, err)
	require.NotNil(t, row)
	stored := row.Get("any", field)
	require.NotNil(t, stored)
	milliseconds, err := stored.DateTimeMillis()
	require.NoError(t, err)
	require.Equal(t, int64(1760000123000), milliseconds)
	require.JSONEq(t, "{\"$date\":\"2025-10-09T08:55:23.000Z\"}",
		string(stored.FastJson(&fastjson.Arena{}).MarshalTo(nil)))
	before := string(row.FastJson(&fastjson.Arena{}).MarshalTo(nil))

	// Both the original kind and scope are decisive, including a mixed patch.
	// Rejection must not mint a visible row version or return a success token.
	for _, patch := range []map[string]any{
		{field: "wrong-kind"},
		{"name": "must not become a synced write"},
		{field: stamp.Add(time.Second), "name": "mixed-scope"},
		{"notDeclared": stamp},
	} {
		got, refusal := local.SetLocalCurrentReader(fixture.ctx, objectID, "any", patch)
		require.Error(t, refusal)
		require.Zero(t, got)
		unchanged, readErr := fixture.space.Properties().Get(fixture.ctx, objectID)
		require.NoError(t, readErr)
		require.Equal(t, before, string(unchanged.FastJson(&fastjson.Arena{}).MarshalTo(nil)))
	}

	// The target was really deleted by its fresh owner before the signed
	// Reader transition. Current membership does not resurrect that tree.
	require.NoError(t, fixture.ctx.Err())
	_, deletedErr := fixture.space.Objects().Get(fixture.ctx, deletedObjectID)
	require.ErrorIs(t, deletedErr, space.ErrObjectDeleted)
	deletedResult, deletedWriteErr := local.SetLocalCurrentReader(fixture.ctx, deletedObjectID, "any",
		map[string]any{field: stamp})
	require.Error(t, deletedWriteErr)
	require.Zero(t, deletedResult)
	require.NoError(t, fixture.ctx.Err(), "a request timeout is not the target refusal being qualified")
	_, stillDeleted := fixture.space.Objects().Get(fixture.ctx, deletedObjectID)
	require.ErrorIs(t, stillDeleted, space.ErrObjectDeleted)
	deletedRow, err := fixture.space.Properties().Get(fixture.ctx, deletedObjectID)
	require.NoError(t, err)
	require.Nil(t, deletedRow, "the refused effect must not recreate a local row")

	home := "{\"objectId\":\"fresh-owned-target\"}"
	require.NoError(t, settings.SetSettingsCurrentReader(fixture.ctx, fixture.space.Id(),
		map[string]any{"pinkhaHomeV1": home}, nil))
	beforeRecord, exists := fixture.sdk.tsp.Get(fixture.ctx, fixture.space.Id())
	require.True(t, exists)
	require.Equal(t, home, beforeRecord.Settings["pinkhaHomeV1"])

	fixture.revoke(t)
	require.ErrorIs(t, authority.CheckCurrentReader(fixture.ctx), list.ErrInsufficientPermissions)
	got, err := local.SetLocalCurrentReader(fixture.ctx, objectID, "any", map[string]any{field: stamp.Add(time.Hour)})
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, got)
	require.ErrorIs(t, settings.SetSettingsCurrentReader(fixture.ctx, fixture.space.Id(),
		map[string]any{"pinkhaHomeV1": "must not replace after removal"}, nil), list.ErrInsufficientPermissions)

	// These are deliberate internal reads of this new fixture's own retained
	// rows solely to prove zero effect. They are not public read-authority
	// claims after removal and do not open an old account or private input.
	unchanged, err := fixture.space.Properties().Get(fixture.ctx, objectID)
	require.NoError(t, err)
	require.Equal(t, before, string(unchanged.FastJson(&fastjson.Arena{}).MarshalTo(nil)))
	afterRecord, exists := fixture.sdk.tsp.Get(fixture.ctx, fixture.space.Id())
	require.True(t, exists)
	require.Equal(t, home, afterRecord.Settings["pinkhaHomeV1"])
	require.Equal(t, beforeRecord.Settings, afterRecord.Settings)
}
