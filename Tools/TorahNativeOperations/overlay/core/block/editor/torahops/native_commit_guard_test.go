package torahops

import (
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/commonspace/sync/objectsync/objectmessages"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/stretchr/testify/require"
)

// This decorator uses the real native preparation/validation/storage path.
// Its callback changes only the disposable signed ACL or request cancellation;
// it neither replaces authorization results nor writes operation history.
type nativePreparedBoundaryTree struct {
	synctree.SyncTree
	afterPrepared func(objecttree.StorageChange) error
}

func (t *nativePreparedBoundaryTree) AddContentWithValidator(ctx context.Context, content objecttree.SignableChangeContent, validate objecttree.ChangeValidator) (objecttree.AddResult, error) {
	return t.SyncTree.AddContentWithValidator(ctx, content, func(change objecttree.StorageChange) error {
		if validate != nil {
			if err := validate(change); err != nil {
				return err
			}
		}
		return t.afterPrepared(change)
	})
}

type nativeUnboundStorageTree struct {
	synctree.SyncTree
	unbound objecttree.Storage
}

func (t *nativeUnboundStorageTree) Storage() objecttree.Storage { return t.unbound }

func TestNativeLocalAppendRequiresCommitGuard(t *testing.T) {
	for _, test := range []string{
		"unguarded AddContent",
		"unguarded AddContentWithValidator",
		"foreign guard cannot authorize local append",
		"unbound host constructor fails before replay",
	} {
		t.Run(test, func(t *testing.T) {
			f, op := nativeFixtureWithPopulatedProjection(t)
			ctx := context.Background()
			before, err := f.host.ReadTarget(ctx, op.Target, 10)
			require.NoError(t, err)
			storage, err := boundNativeCommitStorage(f.tree)
			require.NoError(t, err)
			content := objecttree.SignableChangeContent{Key: f.keys.SignKey, ShouldBeEncrypted: true, Data: []byte("must be rejected before preparation")}
			f.tree.Lock()
			func() {
				defer f.tree.Unlock()
				switch test {
				case "unguarded AddContent":
					_, err = f.tree.AddContent(ctx, content)
				case "unguarded AddContentWithValidator":
					_, err = f.tree.AddContentWithValidator(ctx, content, nil)
				case "foreign guard cannot authorize local append":
					foreign := &nativeCommitStorage{Storage: storage.Storage, acl: storage.acl, header: storage.header}
					guard := &nativeCommitGuard{storage: foreign, author: f.keys.SignKey.GetPublic()}
					_, err = f.tree.AddContent(context.WithValue(ctx, nativeCommitContextKey{}, guard), content)
				case "unbound host constructor fails before replay":
					unbound := &nativeUnboundStorageTree{SyncTree: f.tree, unbound: storage.Storage}
					var host *NativeHost
					host, err = OpenNativeHostLocked(ctx, f.projectionDB, f.space.Id(), unbound, f.keys.SignKey, f.acquireTarget)
					require.Nil(t, host)
				}
			}()
			require.ErrorIs(t, err, ErrNativeCommitGuard)
			after, err := f.host.ReadTarget(ctx, op.Target, 10)
			require.NoError(t, err)
			require.Equal(t, before, after)
		})
	}
}

func TestNativeACLCommitFence(t *testing.T) {
	for _, test := range []string{
		"revocation after preparation denies before durable write",
		"ACL head advance while still writer requires fresh preparation",
		"cancellation after preparation denies before durable write",
	} {
		t.Run(test, func(t *testing.T) {
			f, op := nativeFixtureWithPopulatedProjection(t)
			key := addNativeWriter(t, f)
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			before, err := f.host.ReadTarget(context.Background(), op.Target, 10)
			require.NoError(t, err)
			var preparedID, signedHead string
			wrapped := &nativePreparedBoundaryTree{SyncTree: f.tree, afterPrepared: func(raw objecttree.StorageChange) error {
				change, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), f.tree.Header()).Unmarshall(raw.RawTreeChangeWithId(), true)
				require.NoError(t, err)
				preparedID, signedHead = change.Id, change.AclHeadId
				f.acl.RLock()
				current := f.acl.Head().Id
				f.acl.RUnlock()
				require.Equal(t, current, signedHead)
				switch test {
				case "revocation after preparation denies before durable write":
					removeNativeMember(t, f, key)
				case "ACL head advance while still writer requires fresh preparation":
					_ = addNativeWriter(t, f)
				case "cancellation after preparation denies before durable write":
					cancel()
				}
				return nil
			}}
			writer, err := OpenNativeHost(ctx, f.projectionDB, f.space.Id(), wrapped, key, f.acquireTarget)
			require.NoError(t, err)
			op.OperationID, op.AuthorID = fmt.Sprintf("%032x", 2), key.GetPublic().Account()
			result, err := writer.Append(ctx, op)
			switch test {
			case "cancellation after preparation denies before durable write":
				require.ErrorIs(t, err, context.Canceled)
			case "ACL head advance while still writer requires fresh preparation":
				require.ErrorIs(t, err, ErrNativeACLChanged)
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			default:
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			}
			require.Equal(t, NativeAppendResult{}, result)
			require.NotEmpty(t, preparedID)
			require.NotEmpty(t, signedHead)
			stored, err := f.tree.Storage().Has(context.Background(), preparedID)
			require.NoError(t, err)
			require.False(t, stored, "the prepared signed change must not become durable after failed final authority")
			after, err := f.host.ReadTarget(context.Background(), op.Target, 10)
			require.NoError(t, err)
			require.Equal(t, before, after)
			resolution, err := f.host.store.ReadOperation(context.Background(), op.OperationID)
			require.NoError(t, err)
			require.Empty(t, resolution.Claims)
		})
	}
}

type nativeCommitStorageObserver struct {
	objecttree.Storage
	before, after func()
}

func (s *nativeCommitStorageObserver) AddAll(ctx context.Context, changes []objecttree.StorageChange, heads []string, snapshot string) error {
	s.before()
	err := s.Storage.AddAll(ctx, changes, heads, snapshot)
	s.after()
	return err
}

type nativeFailingHeadUpdate struct {
	synctree.RequestFactory
	observe func()
	failure error
}

func (f *nativeFailingHeadUpdate) CreateHeadUpdate(objecttree.ObjectTree, string, []*treechangeproto.RawTreeChangeWithId) (*objectmessages.HeadUpdate, error) {
	f.observe()
	return nil, f.failure
}

func nativeACLWriteLockAvailable(t *testing.T, acl list.AclList) bool {
	t.Helper()
	try, ok := acl.(interface{ TryLock() bool })
	require.True(t, ok, "the actual native ACL embeds sync.RWMutex")
	locked := try.TryLock()
	if locked {
		acl.Unlock()
	}
	return locked
}

func TestNativeCommitReceiptAfterHeadUpdateFailure(t *testing.T) {
	f, op := nativeFixtureWithPopulatedProjection(t)
	ctx := context.Background()
	storage, err := boundNativeCommitStorage(f.tree)
	require.NoError(t, err)
	originalStorage, originalFactory := storage.Storage, f.client.RequestFactory
	t.Cleanup(func() { storage.Storage, f.client.RequestFactory = originalStorage, originalFactory })
	var beforeCommit, afterCommit, afterRelease bool
	storage.Storage = &nativeCommitStorageObserver{Storage: originalStorage, before: func() {
		beforeCommit = true
		require.False(t, nativeACLWriteLockAvailable(t, f.acl), "ACL writer must be excluded before the real DB write")
	}, after: func() {
		afterCommit = true
		require.False(t, nativeACLWriteLockAvailable(t, f.acl), "ACL writer must remain excluded through the real DB commit")
	}}
	postCommitError := errors.New("fixture head-update encoding failure after native commit")
	f.client.RequestFactory = &nativeFailingHeadUpdate{RequestFactory: originalFactory, failure: postCommitError, observe: func() {
		afterRelease = true
		require.True(t, nativeACLWriteLockAvailable(t, f.acl), "ACL lock must be released before CreateHeadUpdate and Broadcast")
	}}
	op.OperationID = fmt.Sprintf("%032x", 2)
	result, err := f.host.Append(ctx, op)
	require.ErrorIs(t, err, postCommitError)
	require.False(t, errors.Is(err, ErrProjectionBehind))
	require.Equal(t, Created, result.Disposition)
	require.NotEmpty(t, result.ChangeID)
	require.NotEmpty(t, result.ClaimID)
	require.True(t, beforeCommit && afterCommit && afterRelease)
	raw, err := f.tree.Storage().Get(ctx, result.ChangeID)
	require.NoError(t, err)
	change, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), f.tree.Header()).Unmarshall(raw.RawTreeChangeWithId(), true)
	require.NoError(t, err)
	f.acl.RLock()
	currentHead := f.acl.Head().Id
	f.acl.RUnlock()
	require.Equal(t, currentHead, change.AclHeadId)
	require.Equal(t, op.AuthorID, change.Identity.Account())
	read, err := f.host.ReadTarget(ctx, op.Target, 10)
	require.NoError(t, err)
	require.Len(t, read.Projection.Live, 2)
	receipts, err := f.host.store.Receipts(ctx, result.ClaimID)
	require.NoError(t, err)
	require.Len(t, receipts, 1)
	require.Equal(t, change.AclHeadId, receipts[0].ACLHeadID)
	f.client.RequestFactory = originalFactory
	retry, err := f.host.Append(ctx, op)
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.Empty(t, retry.ChangeID)
	after, err := f.host.ReadTarget(ctx, op.Target, 10)
	require.NoError(t, err)
	require.Equal(t, read, after)
}

func TestNativeCommitGuardKeepsHistoricalReplay(t *testing.T) {
	ctx := context.Background()
	config, _, _ := makeNativeConfigs(t)
	f, err := openNativeFixture(ctx, config)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, f.Close()) })
	key := addNativeWriter(t, f)
	writer, err := OpenNativeHost(ctx, f.projectionDB, f.space.Id(), f.tree, key, f.acquireTarget)
	require.NoError(t, err)
	op := Operation{Version: Version, SpaceID: f.space.Id(), OperationID: fmt.Sprintf("%032x", 1),
		AuthorID: key.GetPublic().Account(), Kind: Add, Target: Target{ObjectID: config.TargetRoots[0].Id},
		Source: Source{ProviderID: "fixture", CanonicalRef: "fixture:historical"}, Payload: []byte("authorized before native revocation")}
	created, err := writer.Append(ctx, op)
	require.NoError(t, err)
	raw, err := f.tree.Storage().Get(ctx, created.ChangeID)
	require.NoError(t, err)
	change, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), f.tree.Header()).Unmarshall(raw.RawTreeChangeWithId(), true)
	require.NoError(t, err)
	removeNativeMember(t, f, key)
	f.acl.RLock()
	currentHead, currentWrite := f.acl.Head().Id, f.acl.AclState().Permissions(key.GetPublic()).CanWrite()
	f.acl.RUnlock()
	require.False(t, currentWrite)
	require.NotEqual(t, currentHead, change.AclHeadId)
	db, err := anystore.Open(ctx, filepath.Join(t.TempDir(), "historical-native.db"), &anystore.Config{ReadConnections: 1})
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	receiver, err := spacestorage.Create(ctx, db, config.Space)
	require.NoError(t, err)
	payload := treestorage.TreeStorageCreatePayload{RootRawChange: f.tree.Header(), Heads: []string{created.ChangeID},
		Changes: []*treechangeproto.RawTreeChangeWithId{raw.RawTreeChangeWithId()}}
	tree, err := NativeTreeValidator(f.space.Id())(payload, receiver, f.acl)
	require.NoError(t, err, "remote history is judged at its signed historical ACL head, not current write authority")
	t.Cleanup(func() { require.NoError(t, tree.Close()) })
	require.Equal(t, 2, tree.Len())
	require.Equal(t, payload.Heads, tree.Heads())
	stored, err := tree.Storage().Get(ctx, created.ChangeID)
	require.NoError(t, err)
	require.Equal(t, raw.RawChange, stored.RawChange)
}
