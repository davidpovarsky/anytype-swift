package torahops

import (
	"bytes"
	"context"
	"errors"
	"github.com/anyproto/anytype-heart/util/pinkhat2spaceclosetest"
	"slices"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/util/crypto"
)

var (
	ErrNativeCommitGuard = errors.New("private local append requires its native commit guard")
	ErrNativeACLChanged  = errors.New("signed ACL head changed before native commit")
)

// nativeCommitTree rejects every local AddContent entry without the private,
// one-call token issued by NativeHost. Incoming AddRawChanges keeps AnySync's
// historical signature/ACL validation; it is not a new local mutation request.
type nativeCommitTree struct {
	objecttree.ObjectTree
	storage *nativeCommitStorage
}

type nativeCommitStorage struct {
	objecttree.Storage
	acl    list.AclList
	header *treechangeproto.RawTreeChangeWithId
}

type nativeCommitContextKey struct{}

// All fields belong to one synchronous append while its tree lock is held.
// No token, author, ACL head or guard callback is accepted from an RPC request.
type nativeCommitGuard struct {
	storage       *nativeCommitStorage
	author        crypto.PubKey
	used          bool
	active        bool
	attempted     bool
	prepared      *objecttree.StorageChange
	committed     *objecttree.StorageChange
	releaseTarget func()
}

func bindNativeCommitStorage(storage objecttree.Storage, acl list.AclList, header *treechangeproto.RawTreeChangeWithId) (*nativeCommitStorage, error) {
	if existing, ok := storage.(*nativeCommitStorage); ok {
		if existing == nil || existing.Storage == nil || existing.acl != acl || existing.header == nil ||
			existing.Id() != header.Id || existing.header.Id != header.Id ||
			!bytes.Equal(existing.header.RawChange, header.RawChange) {
			return nil, ErrNativeCommitGuard
		}
		if _, nested := existing.Storage.(*nativeCommitStorage); nested {
			return nil, ErrNativeCommitGuard
		}
		return existing, nil
	}
	return &nativeCommitStorage{Storage: storage, acl: acl, header: header}, nil
}

func boundNativeCommitStorage(tree objecttree.ObjectTree) (*nativeCommitStorage, error) {
	if tree == nil {
		return nil, ErrNativeCommitGuard
	}
	storage, ok := tree.Storage().(*nativeCommitStorage)
	if !ok || storage == nil || storage.acl == nil || storage.header == nil ||
		storage.Id() != tree.Id() || storage.acl != tree.AclList() ||
		storage.header.Id != tree.Header().Id || !bytes.Equal(storage.header.RawChange, tree.Header().RawChange) {
		return nil, ErrNativeCommitGuard
	}
	return storage, nil
}

func nativeCommitContext(ctx context.Context, tree objecttree.ObjectTree, author crypto.PubKey, releaseTarget func()) (context.Context, *nativeCommitGuard, error) {
	storage, err := boundNativeCommitStorage(tree)
	if ctx == nil || err != nil || author == nil || releaseTarget == nil {
		return nil, nil, ErrNativeCommitGuard
	}
	guard := &nativeCommitGuard{storage: storage, author: author, releaseTarget: releaseTarget}
	return context.WithValue(ctx, nativeCommitContextKey{}, guard), guard, nil
}

func nativeGuard(ctx context.Context) *nativeCommitGuard {
	if ctx == nil {
		return nil
	}
	guard, _ := ctx.Value(nativeCommitContextKey{}).(*nativeCommitGuard)
	return guard
}

func copyNativeStorageChange(change objecttree.StorageChange) *objecttree.StorageChange {
	change.RawChange = bytes.Clone(change.RawChange)
	change.PrevIds = slices.Clone(change.PrevIds)
	return &change
}

func (t *nativeCommitTree) AddContent(ctx context.Context, content objecttree.SignableChangeContent) (objecttree.AddResult, error) {
	return t.AddContentWithValidator(ctx, content, nil)
}

func (t *nativeCommitTree) AddContentWithValidator(ctx context.Context, content objecttree.SignableChangeContent, validate objecttree.ChangeValidator) (objecttree.AddResult, error) {
	guard := nativeGuard(ctx)
	if guard == nil || guard.storage != t.storage || guard.used || content.Key == nil ||
		!content.Key.GetPublic().Equals(guard.author) {
		return objecttree.AddResult{}, ErrNativeCommitGuard
	}
	if err := ctx.Err(); err != nil {
		return objecttree.AddResult{}, err
	}
	guard.used, guard.active = true, true
	defer func() { guard.active = false }()
	return t.ObjectTree.AddContentWithValidator(ctx, content, func(change objecttree.StorageChange) error {
		if guard.prepared != nil {
			return ErrNativeCommitGuard
		}
		guard.prepared = copyNativeStorageChange(change)
		if validate != nil {
			return validate(change)
		}
		return nil
	})
}

func (t *nativeCommitTree) AddRawChanges(ctx context.Context, changes objecttree.RawChangesPayload) (objecttree.AddResult, error) {
	if nativeGuard(ctx) != nil {
		return objecttree.AddResult{}, ErrNativeCommitGuard
	}
	return t.ObjectTree.AddRawChanges(ctx, changes)
}

func (t *nativeCommitTree) AddRawChangesWithUpdater(ctx context.Context, changes objecttree.RawChangesPayload, update objecttree.Updater) (objecttree.AddResult, error) {
	if nativeGuard(ctx) != nil {
		return objecttree.AddResult{}, ErrNativeCommitGuard
	}
	return t.ObjectTree.AddRawChangesWithUpdater(ctx, changes, update)
}

func (s *nativeCommitStorage) AddAll(ctx context.Context, changes []objecttree.StorageChange, heads []string, snapshot string) error {
	guard := nativeGuard(ctx)
	if guard == nil {
		// Remote/deferred-storage replay has already passed the unchanged native
		// historical verifier. A later revocation must not erase valid history.
		return s.Storage.AddAll(ctx, changes, heads, snapshot)
	}
	if guard.storage != s || !guard.active || guard.attempted || guard.prepared == nil ||
		len(changes) != 1 || len(heads) != 1 || heads[0] != guard.prepared.Id || snapshot != s.header.Id {
		return ErrNativeCommitGuard
	}
	expected, actual := guard.prepared, changes[0]
	if actual.Id != expected.Id || actual.OrderId != expected.OrderId ||
		actual.SnapshotId != expected.SnapshotId || actual.SnapshotCounter != expected.SnapshotCounter ||
		actual.ChangeSize != expected.ChangeSize || !bytes.Equal(actual.RawChange, expected.RawChange) ||
		!slices.Equal(actual.PrevIds, expected.PrevIds) {
		return ErrNativeCommitGuard
	}
	guard.attempted = true
	if err := ctx.Err(); err != nil {
		return err
	}
	change, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), s.header).Unmarshall(actual.RawTreeChangeWithId(), true)
	if err != nil {
		return err
	}
	if change.Identity == nil || !change.Identity.Equals(guard.author) || change.IsSnapshot || change.ReadKeyId == "" {
		return ErrNativeCommitGuard
	}

	// prepareBuilderContent and validateTree have released their own ACL locks.
	// Hold this final read lock only across the real native storage transaction,
	// never across SyncTree head-update construction, broadcast or projection.
	err = func() error {
		s.acl.RLock()
		defer s.acl.RUnlock()
		if err := ctx.Err(); err != nil {
			return err
		}
		if !s.acl.AclState().Permissions(guard.author).CanWrite() {
			return list.ErrInsufficientPermissions
		}
		head := s.acl.Head()
		if head == nil || change.AclHeadId != head.Id {
			return errors.Join(ErrNativeACLChanged, list.ErrInsufficientPermissions)
		}
		pinkhat2spaceclosetest.Point(ctx, "commit-before-storage", s.header.Id, "", s)
		err := s.Storage.AddAll(ctx, changes, heads, snapshot)
		pinkhat2spaceclosetest.Return(ctx, "commit-after-storage", s.header.Id, s, err)
		return err
	}()
	if err != nil {
		return err
	}
	// AddAll returns only after its deferred tx.Commit succeeds. The underlying
	// store has also assigned AddSeq in this slice. This is the durable witness
	// even if SyncTree later returns an error while creating its head update.
	guard.committed = copyNativeStorageChange(changes[0])
	// Release target/settings only after durable commit and the ACL unlock,
	// before SyncTree creates/broadcasts a head update or projection commits.
	guard.releaseTarget()
	return nil
}

func (s *nativeCommitStorage) AddAllNoError(ctx context.Context, changes []objecttree.StorageChange, heads []string, snapshot string) error {
	if nativeGuard(ctx) != nil {
		return ErrNativeCommitGuard
	}
	return s.Storage.AddAllNoError(ctx, changes, heads, snapshot)
}
