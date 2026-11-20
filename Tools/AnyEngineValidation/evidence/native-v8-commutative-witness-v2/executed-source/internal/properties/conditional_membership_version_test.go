package properties_test

import (
	"context"
	"testing"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/properties"
	"github.com/anyproto/any-sync-sdk/internal/schema"
	"github.com/stretchr/testify/require"
)

// This is the actual native properties handler and apply-sequence allocator.
// It composes the existing commutative-set and modified-stamp behaviors into
// the exact stale-read case that a full _ver-only HTTP guard cannot observe.
func TestNativeConditionalMembershipLateOperationLeavesFullVersionUnchanged(t *testing.T) {
	ctx := context.Background()
	registry := defaultRegistry()
	registry.Set(typeAny, "collections", schema.KindArray)
	controller := newPropsController(t, registry)
	controller.SetApplySeqAllocator(crdt.NewApplySeqAllocator(nil))
	require.NoError(t, controller.ApplyChange(ctx, makeChangeBy("v1", 100, creatorAlice, testObjectId, true,
		crdt.Op{Type: crdt.OpSet, Path: []string{typeAny, "collections"}, Payload: anyenc.MustParseJson(`["base-collection"]`)})))
	require.NoError(t, controller.ApplyChange(ctx, makeChangeBy("v3", 300, creatorCarol, testObjectId, false,
		crdt.Op{Type: crdt.OpSet, Path: []string{typeAny, propName}, Payload: anyenc.MustParseJson(`"newer unrelated edit"`)})))
	before := controller.Get(ctx, properties.Dataset, testObjectId)
	require.NotNil(t, before)
	fullVersion := before.Get("_ver").String()
	sequence := before.GetInt(crdt.ApplySeqField)
	require.Positive(t, sequence)
	oldMemberships := before.Get(typeAny, "collections").String()
	modifiedBefore := before.Get(typeAny, "modifiedAt").String()
	require.NoError(t, controller.ApplyChange(ctx, makeChangeBy("v2", 200, creatorBob, testObjectId, false,
		crdt.Op{Type: crdt.OpAddToSet, Path: []string{typeAny, "collections"}, Payload: anyenc.MustParseJson(`"late-collection"`)})))
	after := controller.Get(ctx, properties.Dataset, testObjectId)
	require.Equal(t, fullVersion, after.Get("_ver").String(), "complete version map cannot detect this late commutative operation")
	require.NotEqual(t, oldMemberships, after.Get(typeAny, "collections").String())
	require.Equal(t, modifiedBefore, after.Get(typeAny, "modifiedAt").String())
	require.Greater(t, after.GetInt(crdt.ApplySeqField), sequence)
}
