package torahops

import (
	"bytes"
	"context"
	"fmt"
	"path/filepath"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/net/peer"
	"github.com/stretchr/testify/require"
)

func TestNativeRemoteFetchKeepsSingleCommitGuard(t *testing.T) {
	f, op := nativeFixtureWithPopulatedProjection(t)
	ctx := context.Background()
	db, err := anystore.Open(ctx, filepath.Join(t.TempDir(), "receiver-space.db"), &anystore.Config{ReadConnections: 1})
	require.NoError(t, err)
	var tree synctree.SyncTree
	var projection anystore.DB
	t.Cleanup(func() {
		if tree != nil {
			require.NoError(t, tree.Close())
		}
		if projection != nil {
			require.NoError(t, projection.Close())
		}
		require.NoError(t, db.Close())
	})
	receiver, err := spacestorage.Create(ctx, db, f.config.Space)
	require.NoError(t, err)
	for _, target := range f.config.TargetRoots {
		_, err = receiver.CreateTreeStorage(ctx, treestorage.TreeStorageCreatePayload{
			RootRawChange: target, Heads: []string{target.Id},
		})
		require.NoError(t, err)
	}
	aclStorage, err := receiver.AclStorage()
	require.NoError(t, err)
	acl, err := list.BuildAclListWithIdentity(f.keys, aclStorage, recordverifier.NewValidateFull())
	require.NoError(t, err)
	client := &fixtureSyncClient{
		RequestFactory: synctree.NewRequestFactory(receiver.Id()),
		address:        f.listener.Addr().String(), spaceID: receiver.Id(), stats: &protocolStats{},
	}
	var fetchedStorage objecttree.Storage
	validate := NativeTreeValidator(receiver.Id())
	deps := synctree.BuildDeps{
		SpaceId: receiver.Id(), SyncClient: client, AclList: acl, SpaceStorage: receiver,
		OnClose: func(string) {}, SyncStatus: fixtureStatus{}, BuildObjectTree: NativeTreeBuilder(receiver.Id()),
		ValidateObjectTree: func(payload treestorage.TreeStorageCreatePayload, creator objecttree.TreeStorageCreator, currentACL list.AclList) (objecttree.ObjectTree, error) {
			validated, validateErr := validate(payload, creator, currentACL)
			if validateErr == nil {
				fetchedStorage = validated.Storage()
			}
			return validated, validateErr
		},
	}
	tree, err = synctree.BuildSyncTreeOrGetRemote(peer.CtxWithPeerId(ctx, "loopback-fixture-peer"), f.tree.Id(), deps)
	require.NoError(t, err)
	require.NotNil(t, fetchedStorage)
	require.Positive(t, client.stats.Requests.Load())
	require.Positive(t, client.stats.Responses.Load())
	require.Positive(t, client.stats.Bytes.Load())
	tree.Lock()
	_, directErr := tree.AddContent(ctx, objecttree.SignableChangeContent{
		Key: f.keys.SignKey, ShouldBeEncrypted: true, Data: []byte("unguarded fetched-tree append"),
	})
	tree.Unlock()
	require.ErrorIs(t, directErr, ErrNativeCommitGuard)
	projection, err = anystore.Open(ctx, filepath.Join(t.TempDir(), "receiver-projection.db"), &anystore.Config{ReadConnections: 1})
	require.NoError(t, err)
	targets := &nativeFixture{config: f.config, space: receiver}
	host, err := OpenNativeHost(ctx, projection, receiver.Id(), tree, f.keys.SignKey, targets.validateTarget)
	require.NoError(t, err)
	before, err := host.ReadTarget(ctx, op.Target, 10)
	require.NoError(t, err)
	require.Len(t, before.Projection.Live, 1)
	op.OperationID = fmt.Sprintf("%032x", 2)
	created, err := host.Append(ctx, op)
	require.NoError(t, err)
	require.Same(t, fetchedStorage, tree.Storage())
	require.Equal(t, Created, created.Disposition)
	require.NotEmpty(t, created.ChangeID)
	stored, err := tree.Storage().Has(ctx, created.ChangeID)
	require.NoError(t, err)
	require.True(t, stored)
	after, err := host.ReadTarget(ctx, op.Target, 10)
	require.NoError(t, err)
	require.Len(t, after.Projection.Live, 2)
	retry, err := host.Append(ctx, op)
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.Empty(t, retry.ChangeID)
	afterRetry, err := host.ReadTarget(ctx, op.Target, 10)
	require.NoError(t, err)
	require.Equal(t, after, afterRetry)
}

func TestNativeRebuiltStorageRejectsForeignBinding(t *testing.T) {
	for _, name := range []string{"different ACL instance", "different root header", "nested guard"} {
		t.Run(name, func(t *testing.T) {
			f, op := nativeFixtureWithPopulatedProjection(t)
			ctx := context.Background()
			before, err := f.host.ReadTarget(ctx, op.Target, 10)
			require.NoError(t, err)
			storage, err := boundNativeCommitStorage(f.tree)
			require.NoError(t, err)
			candidate := *storage
			acl := f.acl
			switch name {
			case "different ACL instance":
				aclStorage, err := f.space.AclStorage()
				require.NoError(t, err)
				acl, err = list.BuildAclListWithIdentity(f.keys, aclStorage, recordverifier.NewValidateFull())
				require.NoError(t, err)
				require.NotSame(t, f.acl, acl)
			case "different root header":
				header := *storage.header
				header.RawChange = append(bytes.Clone(header.RawChange), 0)
				candidate.header = &header
			case "nested guard":
				candidate.Storage = storage
			}
			tree, err := NativeTreeBuilder(f.space.Id())(&candidate, acl)
			require.ErrorIs(t, err, ErrNativeCommitGuard)
			require.Nil(t, tree)
			after, err := f.host.ReadTarget(ctx, op.Target, 10)
			require.NoError(t, err)
			require.Equal(t, before, after)
		})
	}
}
