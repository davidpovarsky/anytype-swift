package migrationnative

import (
	"context"
	"strings"
	"sync"
	"testing"
	"time"

	anysyncsdk "github.com/anyproto/any-sync-sdk"
	"github.com/anyproto/any-sync-sdk/space"
	"github.com/stretchr/testify/require"
)

func definitionInput(t *testing.T, sp space.Space, key string, spec space.MigrationDefinitionSpec) space.MigrationInput {
	t.Helper()
	cap, err := sp.Objects().(space.PreparedMigrationService).MigrationCapabilities(context.Background())
	require.NoError(t, err)
	in := nativeInput(t, cap, key, spec)
	in.Contract = space.PreparedDefinitionContract
	return in
}
func finishDefinition(t *testing.T, ctx context.Context, n space.PreparedDefinitionService, in space.MigrationInput, prepared space.MigrationReceipt) space.MigrationReceipt {
	t.Helper()
	r := prepared
	for i := 0; i < 4 && r.Stage != "complete"; i++ {
		var err error
		r, err = n.CommitMigrationDefinition(ctx, commitOf(in, prepared))
		require.NoError(t, err)
		require.NotEqual(t, "obsolete", r.Outcome)
	}
	require.Equal(t, "complete", r.Stage)
	require.Equal(t, "committed", r.Outcome)
	return r
}

func TestPreparedDefinitionsNativeRestartIdentityAndUse(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	cfg, seeds := nativeConfig(t.TempDir(), localNetwork(t)), newSeeds(t)
	var sdk *anysyncsdk.SDK
	var sp space.Space
	var native space.PreparedDefinitionService
	var spaceID string
	open := func() {
		var err error
		sdk, err = anysyncsdk.Open(ctx, cfg, seeds)
		require.NoError(t, err)
		if spaceID == "" {
			sp, err = sdk.Spaces().Create(ctx, space.CreateRequest{Name: "prepared definitions"})
			if err == nil {
				spaceID = sp.Id()
			}
		} else {
			sp, err = sdk.Spaces().Get(ctx, spaceID)
		}
		require.NoError(t, err)
		native = sp.Objects().(space.PreparedDefinitionService)
	}
	closeSDK := func() { require.NoError(t, sdk.Close()); sdk = nil }
	t.Cleanup(func() {
		if sdk != nil {
			_ = sdk.Close()
		}
	})
	open()
	caps, err := native.MigrationDefinitionCapabilities(ctx)
	require.NoError(t, err)
	require.Equal(t, space.PreparedDefinitionContract, caps.Contract)
	require.Equal(t, 1, caps.TypeDefinition)
	require.False(t, caps.NetworkVerified)
	specs := []space.MigrationDefinitionSpec{
		{Kind: space.MigrationTypeDefinition, Type: &space.TypeCreateParams{Name: "סוג מקור", Description: "exact seed", XKey: "source-type", Meta: map[string]any{"z": true, "n": 7}, Layout: map[string]any{"sort": []any{"b", "a"}, "nested": map[string]any{"z": 2, "a": 1}}}},
		{Kind: space.MigrationCollectionDefinition, Collection: &space.CollectionCreateParams{Name: "אוסף מקור", XKey: "source-collection", Hidden: true, Meta: map[string]any{"flag": true}}},
	}
	inputs := make([]space.MigrationInput, len(specs))
	roots := make([]space.MigrationReceipt, len(specs))
	for i, spec := range specs {
		inputs[i] = definitionInput(t, sp, "definition/"+spec.Kind, spec)
		roots[i], err = native.PrepareMigrationDefinition(ctx, inputs[i], spec)
		require.NoError(t, err)
		require.Equal(t, "definition-root-prepared", roots[i].Stage)
		_, err = sp.Objects().Get(ctx, roots[i].ObjectID)
		require.Error(t, err)
	}
	closeSDK()
	open()
	for i, spec := range specs {
		r, err := native.PrepareMigrationDefinition(ctx, inputs[i], spec)
		require.NoError(t, err)
		require.Equal(t, roots[i], r)
		r, err = native.CommitMigrationDefinition(ctx, commitOf(inputs[i], roots[i]))
		require.NoError(t, err)
		require.Equal(t, "definition-root-committed", r.Stage)
		require.Equal(t, roots[i].ObjectID, r.ObjectID)
	}
	closeSDK()
	open()
	bootstraps := make([]space.MigrationReceipt, len(specs))
	for i := range specs {
		bootstraps[i], err = native.CommitMigrationDefinition(ctx, commitOf(inputs[i], roots[i]))
		require.NoError(t, err)
		require.Equal(t, "definition-bootstrap-prepared", bootstraps[i].Stage)
	}
	closeSDK()
	open()
	for i := range specs {
		r, err := native.MigrationDefinitionStatus(ctx, inputs[i].IntentID)
		require.NoError(t, err)
		require.Equal(t, bootstraps[i], r)
		done := finishDefinition(t, ctx, native, inputs[i], roots[i])
		require.Equal(t, bootstraps[i].ChangeID, done.ChangeID)
		require.Equal(t, roots[i].ObjectID, done.ObjectID)
	}
	props := make([]space.MigrationReceipt, 2)
	propInputs := make([]space.MigrationInput, 2)
	for i, root := range roots {
		spec := space.MigrationDefinitionSpec{Kind: space.MigrationPropertyDefinition, OwnerObjectID: root.ObjectID, Property: &space.PropertyDraft{Name: "שדה", Kind: space.PropertyKindString, XKey: "source-property", Meta: map[string]string{"z": "last", "a": "first"}, XFormat: map[string]any{"options": map[string]any{"z": "Z", "a": "A"}}}}
		propInputs[i] = definitionInput(t, sp, "property/"+root.ObjectID, spec)
		props[i], err = native.PrepareMigrationDefinition(ctx, propInputs[i], spec)
		require.NoError(t, err)
		require.Equal(t, "definition-property-prepared", props[i].Stage)
	}
	closeSDK()
	open()
	for i := range props {
		r, err := native.MigrationDefinitionStatus(ctx, propInputs[i].IntentID)
		require.NoError(t, err)
		require.Equal(t, props[i], r)
		var wg sync.WaitGroup
		results := make(chan space.MigrationReceipt, 4)
		errs := make(chan error, 4)
		for range 4 {
			wg.Add(1)
			go func() {
				defer wg.Done()
				r, e := native.CommitMigrationDefinition(ctx, commitOf(propInputs[i], props[i]))
				results <- r
				errs <- e
			}()
		}
		wg.Wait()
		close(results)
		close(errs)
		for e := range errs {
			require.NoError(t, e)
		}
		for r := range results {
			require.Equal(t, "complete", r.Stage)
			require.Equal(t, "committed", r.Outcome)
			require.Equal(t, props[i].RecordIDs, r.RecordIDs)
			require.Equal(t, props[i].ChangeID, r.ChangeID)
		}
	}
	// Actual ordinary object creation resolves the migrated type, collection and
	// both property definitions; this is stronger than receipt-only assertions.
	obj, err := space.CreateCurrentWriter(ctx, sp, space.CreateObjectOpts{Type: roots[0].ObjectID, Collections: []string{roots[1].ObjectID}, InitialProperties: map[string]map[string]any{"any": {"name": "migrated page"}, roots[0].ObjectID: {props[0].RecordIDs[0]: "type value"}, roots[1].ObjectID: {props[1].RecordIDs[0]: "collection value"}}})
	require.NoError(t, err)
	row, err := sp.Objects().Get(ctx, obj.ObjectID)
	require.NoError(t, err)
	require.Equal(t, "type value", row.GetString(roots[0].ObjectID, props[0].RecordIDs[0]))
	require.Equal(t, "collection value", row.GetString(roots[1].ObjectID, props[1].RecordIDs[0]))
	closeSDK()
	open()
	for i := range props {
		r := finishDefinition(t, ctx, native, propInputs[i], props[i])
		require.Equal(t, props[i].RecordIDs, r.RecordIDs)
	}
	for i, root := range roots {
		row, err := sp.Objects().Get(ctx, root.ObjectID)
		require.NoError(t, err)
		require.NotEmpty(t, row.GetString("any", "name"))
		_, err = native.PrepareMigrationDefinition(ctx, inputs[i], specs[i])
		require.NoError(t, err)
	}
	t.Log("definition_native exact_type_collection_property_ids=true real_sdk_reopens=5 concurrent_commit_callers=4 migrated_definition_object_use=true network_verified=false")
}

func TestPreparedDefinitionsNativeRefusesWrongScopeAndChangedHeads(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()
	sdk, err := anysyncsdk.Open(ctx, nativeConfig(t.TempDir(), localNetwork(t)), newSeeds(t))
	require.NoError(t, err)
	defer sdk.Close()
	sp, err := sdk.Spaces().Create(ctx, space.CreateRequest{Name: "definition refusal"})
	require.NoError(t, err)
	native := sp.Objects().(space.PreparedDefinitionService)
	spec := space.MigrationDefinitionSpec{Kind: space.MigrationTypeDefinition, Type: &space.TypeCreateParams{Name: "original"}}
	in := definitionInput(t, sp, "refusal/type", spec)
	root, err := native.PrepareMigrationDefinition(ctx, in, spec)
	require.NoError(t, err)
	changed := spec
	copy := *spec.Type
	copy.Name = "different"
	changed.Type = &copy
	_, err = native.PrepareMigrationDefinition(ctx, in, changed)
	require.ErrorIs(t, err, space.ErrMigrationCollision)
	wrong := in
	wrong.StoreID = strings.Repeat("0", 64)
	_, err = native.PrepareMigrationDefinition(ctx, wrong, spec)
	require.Error(t, err)
	duplicate := in
	duplicate.IntentID = strings.Repeat("1", 64)
	_, err = native.PrepareMigrationDefinition(ctx, duplicate, spec)
	require.ErrorIs(t, err, space.ErrMigrationCollision)
	bad := spec
	bad.OwnerObjectID = "page"
	_, err = native.PrepareMigrationDefinition(ctx, in, bad)
	require.Error(t, err)
	finishDefinition(t, ctx, native, in, root)
	prop := space.MigrationDefinitionSpec{Kind: space.MigrationPropertyDefinition, OwnerObjectID: "page", Property: &space.PropertyDraft{Name: "bad", Kind: space.PropertyKindString}}
	pi := definitionInput(t, sp, "refusal/static", prop)
	_, err = native.PrepareMigrationDefinition(ctx, pi, prop)
	require.Error(t, err)
	prop.OwnerObjectID = root.ObjectID
	pi = definitionInput(t, sp, "refusal/stale-heads", prop)
	p, err := native.PrepareMigrationDefinition(ctx, pi, prop)
	require.NoError(t, err)
	name := "concurrent edit"
	require.NoError(t, sp.Types().Patch(ctx, root.ObjectID, space.TypePatch{Name: &name}))
	stale, err := native.CommitMigrationDefinition(ctx, commitOf(pi, p))
	require.NoError(t, err)
	require.Equal(t, "obsolete", stale.Outcome)
	all, err := sp.Types().Properties(ctx, root.ObjectID)
	require.NoError(t, err)
	for _, v := range all {
		require.NotEqual(t, p.RecordIDs[0], v.Id)
	}
	ordinary := sp.Objects().(space.PreparedMigrationService)
	cap, err := ordinary.MigrationCapabilities(ctx)
	require.NoError(t, err)
	opts := space.CreateObjectOpts{Type: "__type__"}
	oi := nativeInput(t, cap, "refusal/ordinary-meta", opts)
	_, err = ordinary.PrepareMigrationObject(ctx, oi, opts)
	require.Error(t, err)
	cross := in
	cross.Contract = space.PreparedMigrationContract
	_, err = ordinary.PrepareMigrationObject(ctx, cross, space.CreateObjectOpts{Type: "page"})
	require.ErrorIs(t, err, space.ErrMigrationCollision)
	t.Log("definition_refusal static_owner=true changed_heads=true cross_kind_intent_collision=true ordinary_metatype_guard_preserved=true")
}

func TestPreparedDefinitionsNativeModifiedDeletedNeverReplaced(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()
	sdk, err := anysyncsdk.Open(ctx, nativeConfig(t.TempDir(), localNetwork(t)), newSeeds(t))
	require.NoError(t, err)
	defer sdk.Close()
	sp, err := sdk.Spaces().Create(ctx, space.CreateRequest{Name: "definition terminal"})
	require.NoError(t, err)
	native := sp.Objects().(space.PreparedDefinitionService)
	spec := space.MigrationDefinitionSpec{Kind: space.MigrationTypeDefinition, Type: &space.TypeCreateParams{Name: "before"}}
	in := definitionInput(t, sp, "terminal/type", spec)
	r, err := native.PrepareMigrationDefinition(ctx, in, spec)
	require.NoError(t, err)
	done := finishDefinition(t, ctx, native, in, r)
	name := "after"
	require.NoError(t, sp.Types().Patch(ctx, r.ObjectID, space.TypePatch{Name: &name}))
	modified, err := native.CommitMigrationDefinition(ctx, commitOf(in, r))
	require.NoError(t, err)
	require.Equal(t, "committed_modified", modified.Outcome)
	require.Equal(t, done.ChangeID, modified.ChangeID)
	prop := space.MigrationDefinitionSpec{Kind: space.MigrationPropertyDefinition, OwnerObjectID: r.ObjectID, Property: &space.PropertyDraft{Name: "delete", Kind: space.PropertyKindString}}
	pi := definitionInput(t, sp, "terminal/property", prop)
	p, err := native.PrepareMigrationDefinition(ctx, pi, prop)
	require.NoError(t, err)
	finishDefinition(t, ctx, native, pi, p)
	require.NoError(t, sp.Types().RemoveProperty(ctx, r.ObjectID, p.RecordIDs[0]))
	deleted, err := native.CommitMigrationDefinition(ctx, commitOf(pi, p))
	require.NoError(t, err)
	require.Equal(t, "committed_deleted", deleted.Outcome)
	require.Equal(t, p.RecordIDs, deleted.RecordIDs)
	require.NoError(t, sp.Types().Delete(ctx, r.ObjectID))
	ended, err := native.CommitMigrationDefinition(ctx, commitOf(in, r))
	require.NoError(t, err)
	require.Equal(t, "obsolete", ended.Outcome)
	_, err = sp.Objects().Get(ctx, r.ObjectID)
	require.Error(t, err)
}
