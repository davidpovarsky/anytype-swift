package spaceobjects

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	nativeStore "github.com/anyproto/any-store"
	projectionStore "github.com/anyproto/any-store/v2"
	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/bookmarkcreate"
	"github.com/anyproto/any-sync-sdk/internal/commitguard"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/object"
	"github.com/anyproto/any-sync-sdk/internal/schema"
	"github.com/anyproto/any-sync-sdk/internal/types"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree/updatelistener"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/spacepayloads"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/cidutil"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/stretchr/testify/require"
)

// The fixture uses fresh actual signed trees and actual native AddAll storage,
// following the original definition-fence fixture. It supplies no historical
// account, source capture, replacement ACL verifier, or synthetic write result.
type bookmarkLockTree struct {
	objecttree.ObjectTree
	held         atomic.Int32
	beforeLock   atomic.Pointer[func()]
	beforeAppend func(objecttree.StorageChange) error
}

func (t *bookmarkLockTree) Lock() {
	if hook := t.beforeLock.Load(); hook != nil {
		(*hook)()
	}
	t.ObjectTree.Lock()
	t.held.Add(1)
}
func (t *bookmarkLockTree) Unlock() { t.held.Add(-1); t.ObjectTree.Unlock() }
func (t *bookmarkLockTree) AddContent(ctx context.Context, content objecttree.SignableChangeContent) (objecttree.AddResult, error) {
	if t.beforeAppend != nil {
		return t.ObjectTree.AddContentWithValidator(ctx, content, t.beforeAppend)
	}
	return t.ObjectTree.AddContent(ctx, content)
}

type bookmarkStorage struct {
	objecttree.Storage
	before func()
}

func (s *bookmarkStorage) AddAll(ctx context.Context, changes []objecttree.StorageChange, heads []string, snapshot string) error {
	if s.before != nil {
		s.before()
	}
	return s.Storage.AddAll(ctx, changes, heads, snapshot)
}

type bookmarkFixture struct {
	store                             *Store
	objects                           map[string]*object.Object
	trees                             map[string]*bookmarkLockTree
	typeObject, propertyOwner, target *object.Object
	beforeTargetStorage               func()
	acl                               list.AclList
	account                           *accountdata.AccountKeys
	authorACL                         func(*accountdata.AccountKeys) list.AclList
	cleanupAllowed                    *atomic.Bool
}

func newBookmarkFixture(t *testing.T) *bookmarkFixture {
	t.Helper()
	ctx := context.Background()
	cleanupAllowed := &atomic.Bool{}
	cleanupAllowed.Store(true)
	// The qualifier directs TMPDIR to its owned evidence volume. Keep the
	// fresh stores on failure as well; no automatic TempDir removal may race
	// a writer whose bounded cleanup join failed.
	fixtureRoot, err := os.MkdirTemp("", "pinkha-bookmark-fixture-")
	require.NoError(t, err)
	keys, err := accountdata.NewRandom()
	require.NoError(t, err)
	master, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	metadata, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	payload, err := spacepayloads.StoragePayloadForSpaceCreate(spacepayloads.SpaceCreatePayload{SigningKey: keys.SignKey, SpaceType: "space", ReplicationKey: 10, MasterKey: master, ReadKey: crypto.NewAES(), MetadataKey: metadata, Metadata: []byte("fresh Bookmark condition fixture")})
	require.NoError(t, err)
	native, err := nativeStore.Open(ctx, filepath.Join(fixtureRoot, "native.db"), &nativeStore.Config{ReadConnections: 2})
	require.NoError(t, err)
	t.Cleanup(func() {
		if cleanupAllowed.Load() {
			require.NoError(t, native.Close())
		}
	})
	storage, err := spacestorage.Create(ctx, native, payload)
	require.NoError(t, err)
	aclStorage, err := storage.AclStorage()
	require.NoError(t, err)
	acl, err := list.BuildAclListWithIdentity(keys, aclStorage, recordverifier.NewValidateFull())
	require.NoError(t, err)
	db, err := projectionStore.Open(ctx, filepath.Join(fixtureRoot, "projection.db"), nil)
	require.NoError(t, err)
	t.Cleanup(func() {
		if cleanupAllowed.Load() {
			require.NoError(t, db.Close())
		}
	})
	shared, err := db.Collection(ctx, "objects")
	require.NoError(t, err)
	meta, err := db.Collection(ctx, crdt.MetaCollectionName)
	require.NoError(t, err)
	_, err = crdt.LoadOrInitGeneration(ctx, meta, storage.Id())
	require.NoError(t, err)
	f := &bookmarkFixture{store: &Store{spaceId: storage.Id(), db: db, signKey: keys.SignKey,
		moduleInfos: types.NewModules(types.ModuleInfo{Name: "editor", Canonical: "editor_blocks"})},
		objects: map[string]*object.Object{}, trees: map[string]*bookmarkLockTree{}, acl: acl, account: keys, cleanupAllowed: cleanupAllowed}
	f.authorACL = func(author *accountdata.AccountKeys) list.AclList {
		loaded, err := list.BuildAclListWithIdentity(author, aclStorage, recordverifier.NewValidateFull())
		require.NoError(t, err)
		return loaded
	}
	makeObject := func(seed string) *object.Object {
		_, root, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), nil).BuildRoot(objecttree.InitialContent{PrivKey: keys.SignKey, AclHeadId: payload.AclWithId.Id, SpaceId: storage.Id(), ChangeType: "object", Seed: []byte(seed)})
		require.NoError(t, err)
		ts, err := storage.CreateTreeStorage(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}})
		require.NoError(t, err)
		observed := &bookmarkStorage{Storage: ts, before: func() {
			if f.target != nil && root.Id == f.target.Id() && f.beforeTargetStorage != nil {
				f.beforeTargetStorage()
			}
		}}
		tree, err := commitguard.Builder(nil)(observed, acl)
		require.NoError(t, err)
		tracked := &bookmarkLockTree{ObjectTree: tree}
		f.trees[root.Id] = tracked
		controller, err := crdt.NewControllerWithShared(ctx, root.Id, db, crdt.SharedCollections{"objects": shared},
			crdt.HandlerReg{Name: "objects", Handler: crdt.DefaultHandler{}, Schema: schema.Dataset{Dynamic: true}},
			crdt.HandlerReg{Name: "datasets", Handler: crdt.DefaultHandler{}, Schema: schema.Dataset{Dynamic: true}},
			crdt.HandlerReg{Name: "properties", Handler: crdt.DefaultHandler{}, Schema: schema.Dataset{Dynamic: true}},
			crdt.HandlerReg{Name: "editor_blocks", Handler: crdt.DefaultHandler{}, Schema: schema.Dataset{Dynamic: true}})
		require.NoError(t, err)
		controller.SetApplySeqAllocator(crdt.NewApplySeqAllocator(nil))
		obj, err := object.New(object.Config{SpaceId: storage.Id(), SignKey: keys.SignKey, Controller: controller,
			LockLocalWrite: func(ctx context.Context, carrier *object.Object, _ *crdt.Change) (crdt.LocalReadView, func(), error) {
				return f.store.lockPreparedNativeObjects(ctx, f.objects, carrier)
			}}, func(updatelistener.UpdateListener) (objecttree.ObjectTree, error) { return tracked, nil })
		require.NoError(t, err)
		f.objects[obj.Id()] = obj
		t.Cleanup(func() {
			if cleanupAllowed.Load() {
				require.NoError(t, tree.Close())
			}
		})
		return obj
	}
	f.typeObject, f.propertyOwner, f.target = makeObject("Bookmark Type"), makeObject("Bookmark URL owner"), makeObject("ordinary new Bookmark")
	seed := func(obj *object.Object, dataset, id string, value any) {
		raw, err := json.Marshal(value)
		require.NoError(t, err)
		_, err = obj.LocalWrite(ctx, crdt.Change{Dataset: dataset, DataVersion: "fixture-v1", Records: []crdt.RecordChange{{Id: id, Upsert: true, Ops: []crdt.Op{{Type: crdt.OpSet, Payload: anyenc.MustParseJson(string(raw))}}}}})
		require.NoError(t, err)
	}
	address := map[string]any{"ownerId": f.propertyOwner.Id(), "propertyId": "url"}
	seed(f.typeObject, "objects", f.typeObject.Id(), map[string]any{"spaceId": storage.Id(), "any": map[string]any{"type": "__type__"},
		"type": map[string]any{"layout": map[string]any{"type": "bookmark", "config": map[string]any{"pinkhaHeart": map[string]any{
			"contract": bookmarkcreate.PresentationContract, "sourceRecommendedLayout": 11, "propertyOwnerId": f.propertyOwner.Id(),
			"sourceURL": address, "recommended": []any{address}, "featured": []any{}, "hidden": []any{}, "files": []any{}}}}}})
	seed(f.propertyOwner, "objects", f.propertyOwner.Id(), map[string]any{"spaceId": storage.Id(), "any": map[string]any{"type": "__collection__"}, "collection": map[string]any{"meta": map[string]any{"unknown": "must stay exact"}}})
	seed(f.propertyOwner, "properties", "url", map[string]any{"name": "Source", "kind": "string", "scope": "synced", "x-format": map[string]any{"type": "url", "pinkhaHeart": map[string]any{"sourceUniqueKey": "rel-source", "relationKey": "source", "sourceObjectID": "original-source-definition"}}})
	seed(f.typeObject, "datasets", "body", map[string]any{"def": "part", "key": "body"})
	seed(f.typeObject, "datasets", "editor", map[string]any{"def": "dataset", "key": "editor_blocks", "module": "editor", "shared": true, "part": "body"})
	return f
}

func (f *bookmarkFixture) capture(t *testing.T) bookmarkcreate.Frame {
	t.Helper()
	view, unlock, err := f.store.lockPreparedNativeObjects(context.Background(), f.objects, f.target)
	require.NoError(t, err)
	defer unlock()
	frame, err := view.(lockedReadView).bookmarkFrame(f.typeObject.Id(), []string{f.propertyOwner.Id()})
	require.NoError(t, err)
	return frame
}

func (f *bookmarkFixture) change(t *testing.T, frame bookmarkcreate.Frame) crdt.Change {
	t.Helper()
	raw, err := json.Marshal(map[string]any{"any.type": f.typeObject.Id(), "any.collections": []string{f.propertyOwner.Id()}, f.propertyOwner.Id() + ".url": "https://example.test/cafe\u0301"})
	require.NoError(t, err)
	return crdt.Change{Dataset: "objects", DataVersion: "fixture-v1", NativeObjectPolicy: true, NativeBookmarkCreateFrame: &frame,
		NativeDefinitionOwners: []string{f.typeObject.Id(), f.propertyOwner.Id()}, NativeTypeDatasets: []crdt.NativeTypeDatasetRequirement{{Module: "editor", Dataset: "editor_blocks", Canonical: true}},
		Records: []crdt.RecordChange{{Id: f.target.Id(), Upsert: true, Ops: []crdt.Op{{Type: crdt.OpSet, Payload: anyenc.MustParseJson(string(raw))}}}}}
}

func TestBookmarkLockedConditionRefusesForeignEpochAndDependencyFrames(t *testing.T) {
	f := newBookmarkFixture(t)
	original := f.capture(t)
	before := append([]string{}, f.target.Tree().Heads()...)
	for _, mutate := range []func(*bookmarkcreate.Frame){
		func(frame *bookmarkcreate.Frame) { frame.AccountID = "another-account" },
		func(frame *bookmarkcreate.Frame) { frame.SpaceID = "another-space" },
		func(frame *bookmarkcreate.Frame) { frame.StoreGeneration += "-different" },
		func(frame *bookmarkcreate.Frame) { frame.TypeSHA256 = strings.Repeat("a", 64) },
		func(frame *bookmarkcreate.Frame) { frame.OwnerSHA256 = strings.Repeat("b", 64) },
		func(frame *bookmarkcreate.Frame) { frame.PropertySHA256 = strings.Repeat("c", 64) },
		func(frame *bookmarkcreate.Frame) { frame.Dependencies = frame.Dependencies[:1] },
	} {
		encoded, err := bookmarkcreate.Encode(original)
		require.NoError(t, err)
		frame, err := bookmarkcreate.Decode(encoded)
		require.NoError(t, err)
		mutate(&frame)
		_, err = f.target.LocalWriteCurrentWriter(context.Background(), f.change(t, frame))
		require.Error(t, err)
		require.Equal(t, before, f.target.Tree().Heads(), "refused condition never appends bootstrap")
	}
	result, err := f.target.LocalWriteCurrentWriter(context.Background(), f.change(t, original))
	require.NoError(t, err)
	require.NotEmpty(t, result.ChangeId)
	row, err := f.target.Controller().GuardLookup(context.Background(), "objects", f.target.Id())
	require.NoError(t, err)
	require.Equal(t, []byte("https://example.test/cafe\u0301"), []byte(row.GetString(f.propertyOwner.Id(), "url")))
	blocks, err := f.target.Controller().GuardQuery(context.Background(), "editor_blocks", nil, 2)
	require.NoError(t, err)
	require.Empty(t, blocks, "a valid Bookmark bootstrap does not create a dummy editor block")
}

func TestBookmarkLockedConditionFencesConcurrentDefinitionWrite(t *testing.T) {
	f := newBookmarkFixture(t)
	frame := f.capture(t)
	started, attempted, finished := make(chan struct{}), make(chan struct{}), make(chan error, 1)
	var once sync.Once
	lockHook := func() {
		select {
		case <-started:
			once.Do(func() { close(attempted) })
		default:
		}
	}
	f.trees[f.propertyOwner.Id()].beforeLock.Store(&lockHook)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	done := make(chan struct{})
	// Registered after fixture cleanup: LIFO joins this worker before any
	// tree or database can close, including an assertion/timeout failure.
	t.Cleanup(func() {
		cancel()
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			f.cleanupAllowed.Store(false)
			t.Error("competing definition worker did not stop; native tree/database cleanup withheld")
		}
	})
	go func() {
		defer close(done)
		select {
		case <-started:
		case <-ctx.Done():
			finished <- ctx.Err()
			return
		}
		_, err := f.propertyOwner.LocalWrite(ctx, crdt.Change{Dataset: "properties", DataVersion: "fixture-v1", Records: []crdt.RecordChange{{Id: "url", Ops: []crdt.Op{{Type: crdt.OpSet, Path: []string{"description"}, Payload: anyenc.MustParseJson(`"changed after accepted bootstrap"`)}}}}})
		finished <- err
	}()
	f.beforeTargetStorage = func() {
		for id, tracker := range f.trees {
			require.Equal(t, int32(1), tracker.held.Load(), "dependency lock %s held at actual storage", id)
		}
		close(started)
		select {
		case <-attempted:
		case <-ctx.Done():
			t.Fatal(ctx.Err())
		}
		select {
		case err := <-finished:
			t.Fatalf("competing definition passed held lock: %v", err)
		default:
		}
	}
	result, err := f.target.LocalWriteCurrentWriter(ctx, f.change(t, frame))
	require.NoError(t, err)
	f.beforeTargetStorage = nil
	select {
	case err := <-finished:
		require.NoError(t, err)
	case <-ctx.Done():
		t.Fatal(ctx.Err())
	}
	require.NotEmpty(t, result.ChangeId)
	after := append([]string{}, f.target.Tree().Heads()...)
	_, err = f.target.LocalWriteCurrentWriter(ctx, f.change(t, frame))
	require.ErrorIs(t, err, bookmarkcreate.ErrChanged)
	require.Equal(t, after, f.target.Tree().Heads(), "the same stale condition cannot append after the competing definition")
	fresh := f.capture(t)
	require.False(t, slices.Equal(frame.Dependencies[0].Heads, fresh.Dependencies[0].Heads) && slices.Equal(frame.Dependencies[1].Heads, fresh.Dependencies[1].Heads))
}

func TestBookmarkGenerationPeekCannotRecreateMissingEpoch(t *testing.T) {
	f := newBookmarkFixture(t)
	ctx := context.Background()
	collection, err := f.store.db.Collection(ctx, crdt.MetaCollectionName)
	require.NoError(t, err)
	before, err := collection.FindId(ctx, crdt.SpaceMetaKey(f.store.spaceId))
	require.NoError(t, err)
	require.NotEmpty(t, before.Value().GetString("gen"))
	err = collection.DeleteId(ctx, crdt.SpaceMetaKey(f.store.spaceId))
	require.NoError(t, err)
	_, err = f.store.bookmarkExistingGeneration(ctx)
	require.Error(t, err)
	_, err = collection.FindId(ctx, crdt.SpaceMetaKey(f.store.spaceId))
	require.ErrorIs(t, err, projectionStore.ErrDocNotFound)
}

func TestBookmarkConditionRechecksCurrentWriterAtDurableAppend(t *testing.T) {
	f := newBookmarkFixture(t)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	newOwner, err := accountdata.NewRandom()
	require.NoError(t, err)
	networkKey, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	apply := func(raw *consensusproto.RawRecord) {
		// The fresh fixture uses both the real acceptor verifier and the real
		// author/content verifier. This is not a copied original network record.
		raw.AcceptorIdentity, err = networkKey.GetPublic().Marshall()
		require.NoError(t, err)
		raw.AcceptorSignature, err = networkKey.Sign(raw.Payload)
		require.NoError(t, err)
		require.NoError(t, recordverifier.New(networkKey.GetPublic()).VerifyAcceptor(raw))
		encoded, err := raw.MarshalVT()
		require.NoError(t, err)
		id, err := cidutil.NewCidFromBytes(encoded)
		require.NoError(t, err)
		f.acl.Lock()
		addErr := f.acl.AddRawRecord(&consensusproto.RawRecordWithId{Id: id, Payload: encoded})
		f.acl.Unlock()
		require.NoError(t, addErr)
	}
	addition, err := f.acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{{
		Identity: newOwner.SignKey.GetPublic(), Permissions: list.AclPermissionsWriter, Metadata: []byte("fresh condition fixture owner"),
	}}})
	require.NoError(t, err)
	apply(addition)
	transfer, err := f.acl.RecordBuilder().BuildOwnershipChange(list.OwnershipChangePayload{
		NewOwner: newOwner.SignKey.GetPublic(), OldOwnerPermissions: list.AclPermissionsWriter,
	})
	require.NoError(t, err)
	apply(transfer)
	author := f.authorACL(newOwner)
	require.True(t, f.acl.AclState().Permissions(f.account.SignKey.GetPublic()).CanWrite())
	frame := f.capture(t)
	head := append([]string{}, f.target.Tree().Heads()...)
	require.Len(t, head, 1)
	prepared := ""
	storageCalls := 0
	f.beforeTargetStorage = func() { storageCalls++ }
	f.trees[f.target.Id()].beforeAppend = func(change objecttree.StorageChange) error {
		prepared = change.Id
		metadata, _, keyErr := crypto.GenerateRandomEd25519KeyPair()
		require.NoError(t, keyErr)
		removed, buildErr := author.RecordBuilder().BuildAccountRemove(list.AccountRemovePayload{
			Identities: []crypto.PubKey{f.account.SignKey.GetPublic()},
			Change:     list.ReadKeyChangePayload{MetadataKey: metadata, ReadKey: crypto.NewAES()},
		})
		require.NoError(t, buildErr)
		apply(removed)
		return nil
	}
	_, err = f.target.LocalWriteCurrentWriter(ctx, f.change(t, frame))
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.NotEmpty(t, prepared, "the frame passed before the actual current-writer retirement")
	require.Zero(t, storageCalls, "retired authority must fail before the actual AddAll call")
	require.Equal(t, head, f.target.Tree().Heads())
	stored, err := f.target.Tree().Storage().Has(ctx, prepared)
	require.NoError(t, err)
	require.False(t, stored)
	row, err := f.target.Controller().GuardLookup(ctx, "objects", f.target.Id())
	require.NoError(t, err)
	require.Nil(t, row)
	require.Equal(t, head[0], f.target.Id(), "the already-created native root is preserved, never replaced or deleted")
}
