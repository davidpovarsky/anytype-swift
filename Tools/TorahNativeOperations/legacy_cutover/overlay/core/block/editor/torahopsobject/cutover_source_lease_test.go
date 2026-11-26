package torahopsobject

import (
	"bytes"
	"context"
	"errors"
	"slices"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/objecttreebuilder"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/internal/pinkhat2test"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
	"github.com/stretchr/testify/require"
)

const sourceLeasePropertyKey = "pinkha-disposable-canonical-associations"

// Native signed settings, object trees, ACLs and mutexes are real. The loaded
// SmartBlock/cache is the existing controlled adapter. This is lease/authority
// component qualification, not application registry, RPC or peer acceptance.
func cutoverLeaseMetadata(t *testing.T, f *pinkhat2test.Fixture) objecttree.ObjectTree {
	t.Helper()
	root, err := torahcutoverroot.Root(f.Space.Id())
	require.NoError(t, err)
	_, err = f.Space.CreateTreeStorage(context.Background(), treestorage.TreeStorageCreatePayload{
		RootRawChange: root, Heads: []string{root.Id}})
	require.NoError(t, err)
	tree, err := f.Builder.BuildTree(context.Background(), root.Id,
		objecttreebuilder.BuildTreeOpts{TreeBuilder: torahops.CutoverNativeTreeBuilder(f.Space.Id())})
	require.NoError(t, err)
	return tree
}
func setCutoverLeaseProperty(t *testing.T, space *semanticLeaseSpace, value domain.Value) {
	t.Helper()
	require.NoError(t, space.target.SetDetails(nil, []domain.Detail{{Key: domain.RelationKey(sourceLeasePropertyKey), Value: value}}, false))
}

func TestCutoverSourceLeasePreservesExactNativePropertyAndOneBorrow(t *testing.T) {
	for _, scenario := range []string{"missing", "present-empty", "exact-unicode-bytes"} {
		t.Run(scenario, func(t *testing.T) {
			f, space, request := newSemanticLeaseFixture(t)
			native := cutoverLeaseMetadata(t, f)
			text := "  {\"preserved\":\"אבג 😀\"}\n"
			if scenario == "present-empty" {
				text = ""
			}
			if scenario != "missing" {
				setCutoverLeaseProperty(t, space, domain.String(text))
			}
			before := slices.Clone(space.target.tree.Heads())
			ctx, release, err := AcquireNativeCutoverSourceLease(context.Background(), space, request.ObjectID,
				sourceLeasePropertyKey, true, f.ACL, func(ctx context.Context) error { return ctx.Err() })
			require.NoError(t, err)
			defer release()
			require.False(t, space.settings.TryLock())
			require.False(t, space.target.tree.TryLock())
			lease, err := BorrowNativeCutoverSourceLease(ctx, space, native, request.ObjectID, sourceLeasePropertyKey, true)
			require.NoError(t, err)
			require.Equal(t, scenario != "missing", lease.Value.Present)
			require.Equal(t, sourceLeasePropertyKey, lease.Value.Key)
			if scenario == "missing" {
				require.Empty(t, lease.Value.Bytes)
			} else {
				require.Equal(t, []byte(text), lease.Value.Bytes)
			}
			require.ElementsMatch(t, before, lease.Heads)
			require.NoError(t, lease.Validate(ctx))
			require.NoError(t, lease.ValidateTarget(ctx, torahops.Target{ObjectID: request.ObjectID, BlockID: request.BlockID}))
			require.ErrorIs(t, lease.ValidateTarget(ctx, torahops.Target{ObjectID: "other", BlockID: request.BlockID}), ErrTargetUnavailable)
			require.ErrorIs(t, lease.ValidateTarget(ctx, torahops.Target{ObjectID: request.ObjectID, BlockID: "missing"}), ErrTargetUnavailable)
			_, err = BorrowNativeCutoverSourceLease(ctx, space, native, request.ObjectID, sourceLeasePropertyKey, true)
			require.ErrorIs(t, err, ErrTargetUnavailable)
			// Published value buffers are copies, not a writable route into the
			// held native property or its source-head authority.
			if len(lease.Value.Bytes) > 0 {
				lease.Value.Bytes[0] ^= 1
			}
			lease.Heads[0] = "changed-copy"
			require.NoError(t, lease.Validate(ctx))
			require.Equal(t, before, space.target.tree.Heads())
			lease.Release()
			release()
			assertSemanticLeaseUnlocked(t, space)
			require.ErrorIs(t, lease.Validate(ctx), ErrTargetUnavailable)
		})
	}
}

func TestCutoverSourceLeaseRefusesNonStringNativeProperties(t *testing.T) {
	for _, value := range []domain.Value{domain.Null(), domain.Int64(7), domain.Bool(true), domain.StringList([]string{"[]"})} {
		f, space, request := newSemanticLeaseFixture(t)
		setCutoverLeaseProperty(t, space, value)
		ctx, release, err := AcquireNativeCutoverSourceLease(context.Background(), space, request.ObjectID,
			sourceLeasePropertyKey, false, f.ACL, func(ctx context.Context) error { return ctx.Err() })
		require.ErrorIs(t, err, cutover.ErrInvalid)
		require.Nil(t, ctx)
		require.Nil(t, release)
		assertSemanticLeaseUnlocked(t, space)
	}
}

func TestCutoverSourceLeaseRechecksHeldAccountDocumentAndExactSource(t *testing.T) {
	for _, scenario := range []string{"account-retired", "cache-retired", "native-property-changed", "native-head-changed", "cancelled", "orphan-target"} {
		t.Run(scenario, func(t *testing.T) {
			f, space, request := newSemanticLeaseFixture(t)
			native := cutoverLeaseMetadata(t, f)
			setCutoverLeaseProperty(t, space, domain.String("exact source"))
			parent, cancel := context.WithCancel(context.Background())
			defer cancel()
			retired := errors.New("actual held account scope retired")
			active := true
			ctx, release, err := AcquireNativeCutoverSourceLease(parent, space, request.ObjectID,
				sourceLeasePropertyKey, true, f.ACL, func(ctx context.Context) error {
					if !active {
						return retired
					}
					return ctx.Err()
				})
			require.NoError(t, err)
			defer release()
			lease, err := BorrowNativeCutoverSourceLease(ctx, space, native, request.ObjectID, sourceLeasePropertyKey, true)
			require.NoError(t, err)
			want := ErrTargetUnavailable
			switch scenario {
			case "account-retired":
				active = false
				want = retired
			case "cache-retired":
				space.current = false
			case "native-property-changed":
				setCutoverLeaseProperty(t, space, domain.String("different source"))
				want = cutover.ErrLegacyChanged
			case "native-head-changed":
				semanticStoredChange(t, f, space)
				want = cutover.ErrLegacyChanged
			case "cancelled":
				cancel()
				want = context.Canceled
			case "orphan-target":
				space.target.Pick(request.ObjectID).Model().ChildrenIds = nil
			}
			if scenario == "orphan-target" {
				require.NoError(t, lease.Validate(ctx))
				require.ErrorIs(t, lease.ValidateTarget(ctx, torahops.Target{ObjectID: request.ObjectID, BlockID: request.BlockID}), want)
			} else {
				require.ErrorIs(t, lease.Validate(ctx), want)
			}
			release()
			assertSemanticLeaseUnlocked(t, space)
		})
	}
}

func TestCutoverSourceLeaseRefusesForeignACLAndBorrowScope(t *testing.T) {
	f, space, request := newSemanticLeaseFixture(t)
	other, _, _ := newSemanticLeaseFixture(t)
	metadata := cutoverLeaseMetadata(t, f)
	current := func(ctx context.Context) error { return ctx.Err() }
	_, release, err := AcquireNativeCutoverSourceLease(context.Background(), space, request.ObjectID,
		sourceLeasePropertyKey, false, other.ACL, current)
	require.ErrorIs(t, err, ErrTargetUnavailable)
	require.Nil(t, release)
	assertSemanticLeaseUnlocked(t, space)
	ctx, release, err := AcquireNativeCutoverSourceLease(context.Background(), space, request.ObjectID,
		sourceLeasePropertyKey, false, f.ACL, current)
	require.NoError(t, err)
	defer release()
	for _, scope := range []struct {
		object, key string
		write       bool
	}{
		{request.ObjectID, sourceLeasePropertyKey, true}, {"foreign", sourceLeasePropertyKey, false}, {request.ObjectID, "other-key", false},
	} {
		_, err = BorrowNativeCutoverSourceLease(ctx, space, metadata, scope.object, scope.key, scope.write)
		require.ErrorIs(t, err, ErrTargetUnavailable)
	}
	_, err = BorrowNativeCutoverSourceLease(ctx, space, space.target.tree, request.ObjectID, sourceLeasePropertyKey, false)
	require.ErrorIs(t, err, ErrTargetUnavailable)
	lease, err := BorrowNativeCutoverSourceLease(ctx, space, metadata, request.ObjectID, sourceLeasePropertyKey, false)
	require.NoError(t, err)
	require.False(t, lease.Value.Present)
	require.True(t, bytes.Equal(nil, lease.Value.Bytes))
}
