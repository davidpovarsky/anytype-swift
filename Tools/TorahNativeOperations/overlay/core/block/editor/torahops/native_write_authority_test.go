package torahops

import (
	"context"
	"fmt"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/stretchr/testify/require"
)

func addNativeWriter(t *testing.T, f *nativeFixture) crypto.PrivKey {
	t.Helper()
	member, err := accountdata.NewRandom()
	require.NoError(t, err)
	applyNativeACLRecord(t, f.acl, func() (*consensusproto.RawRecord, error) {
		return f.acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{
			{Identity: member.SignKey.GetPublic(), Permissions: list.AclPermissionsWriter, Metadata: []byte("disposable write member")},
		}})
	})
	return member.SignKey
}

func removeNativeMember(t *testing.T, f *nativeFixture, key crypto.PrivKey) {
	t.Helper()
	metadata, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	applyNativeACLRecord(t, f.acl, func() (*consensusproto.RawRecord, error) {
		return f.acl.RecordBuilder().BuildAccountRemove(list.AccountRemovePayload{
			Identities: []crypto.PubKey{key.GetPublic()},
			Change:     list.ReadKeyChangePayload{MetadataKey: metadata, ReadKey: crypto.NewAES()},
		})
	})
}

func TestNativeCurrentWriteAuthority(t *testing.T) {
	t.Run("locally removed writer cannot append or replay an acknowledged operation", func(t *testing.T) {
		f, op := nativeFixtureWithPopulatedProjection(t)
		key := addNativeWriter(t, f)
		member, err := OpenNativeHost(context.Background(), f.projectionDB, f.space.Id(), f.tree, key, f.acquireTarget)
		require.NoError(t, err)
		op.OperationID = fmt.Sprintf("%032x", 2)
		op.AuthorID = key.GetPublic().Account()
		written, err := member.Append(context.Background(), op)
		require.NoError(t, err)
		require.Equal(t, Created, written.Disposition)
		require.NotEmpty(t, written.ChangeID)
		before, err := f.host.ReadTarget(context.Background(), op.Target, 10)
		require.NoError(t, err)
		require.Len(t, before.Projection.Live, 2)

		removeNativeMember(t, f, key)
		for _, operationID := range []string{op.OperationID, fmt.Sprintf("%032x", 3)} {
			attempt := op
			attempt.OperationID = operationID
			result, err := member.Append(context.Background(), attempt)
			require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			require.Equal(t, NativeAppendResult{}, result)
		}
		after, err := f.host.ReadTarget(context.Background(), op.Target, 10)
		require.NoError(t, err)
		require.Equal(t, before, after, "known local removal must not create another native change or modify the projection")
		receipts, err := f.host.store.Receipts(context.Background(), written.ClaimID)
		require.NoError(t, err)
		require.Len(t, receipts, 1)
	})

	t.Run("native preparation rechecks removal after host preflight", func(t *testing.T) {
		f, op := nativeFixtureWithPopulatedProjection(t)
		key := addNativeWriter(t, f)
		called := 0
		validate := func(ctx context.Context, target Target) (func(), error) {
			if err := f.validateTarget(ctx, target); err != nil {
				return nil, err
			}
			called++
			// This callback runs after NativeHost's preflight permission check,
			// but before the real ObjectTree.prepareBuilderContent. Applying a
			// signed native removal here deterministically exercises that gap.
			removeNativeMember(t, f, key)
			return func() {}, nil
		}
		member, err := OpenNativeHost(context.Background(), f.projectionDB, f.space.Id(), f.tree, key, validate)
		require.NoError(t, err)
		before, err := f.host.ReadTarget(context.Background(), op.Target, 10)
		require.NoError(t, err)
		op.OperationID = fmt.Sprintf("%032x", 2)
		op.AuthorID = key.GetPublic().Account()
		result, err := member.Append(context.Background(), op)
		require.ErrorIs(t, err, list.ErrInsufficientPermissions)
		require.Equal(t, NativeAppendResult{}, result)
		require.Equal(t, 1, called)
		after, err := f.host.ReadTarget(context.Background(), op.Target, 10)
		require.NoError(t, err)
		require.Equal(t, before, after)
		resolution, err := f.host.store.ReadOperation(context.Background(), op.OperationID)
		require.NoError(t, err)
		require.Empty(t, resolution.Claims)
	})
}
