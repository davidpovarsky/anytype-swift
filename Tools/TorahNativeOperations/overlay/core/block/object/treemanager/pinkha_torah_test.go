package treemanager

import (
	"context"
	"errors"
	"path/filepath"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree/updatelistener"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/objecttreebuilder"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/internal/pinkhat2test"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/spacedomain"
	"github.com/stretchr/testify/require"
)

// These service-boundary adapters deliberately expose only the existing generic
// PutTree route. Any call is observable before a production builder could write.
type privatePutBuilder struct {
	objecttreebuilder.TreeBuilder
	puts    int
	payload treestorage.TreeStorageCreatePayload
	err     error
}

func (b *privatePutBuilder) PutTree(_ context.Context, payload treestorage.TreeStorageCreatePayload, _ updatelistener.UpdateListener) (objecttree.ObjectTree, error) {
	b.puts++
	b.payload = payload
	return nil, b.err
}

type privatePutSpace struct {
	clientspace.Space
	b *privatePutBuilder
}

func (s privatePutSpace) TreeBuilder() objecttreebuilder.TreeBuilder { return s.b }

type privatePutSpaces struct {
	space.Service
	gets int
	b    *privatePutBuilder
}

func (s *privatePutSpaces) Get(context.Context, string) (clientspace.Space, error) {
	s.gets++
	return privatePutSpace{b: s.b}, nil
}

func TestPinkhaPrivateTreeManagerRejectsGenericImportBeforeStorage(t *testing.T) {
	ctx := context.Background()
	f := pinkhat2test.New(t)
	spaceID := f.Space.Id()
	ot, err := f.Builder.BuildTree(ctx, f.RootID, objecttreebuilder.BuildTreeOpts{
		TreeBuilder: torahops.NativeTreeBuilder(spaceID), TreeValidator: torahops.NativeTreeValidator(spaceID),
	})
	require.NoError(t, err)
	tree := ot.(synctree.SyncTree)
	db, err := anystore.Open(ctx, filepath.Join(f.Dir, "projection.db"), &anystore.Config{ReadConnections: 1})
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	host, err := torahops.OpenNativeHost(ctx, db, spaceID, tree, f.Keys.SignKey, func(context.Context, torahops.Target) (func(), error) { return func() {}, nil })
	require.NoError(t, err)
	op := torahops.Operation{Version: torahops.Version, SpaceID: spaceID, OperationID: "000000000000000000000000000000c1",
		AuthorID: f.Keys.SignKey.GetPublic().Account(), Kind: torahops.Add, Target: torahops.Target{ObjectID: "fixture-target"},
		Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:import-boundary"}, Payload: []byte("signed private import boundary")}
	appended, err := host.Append(ctx, op)
	require.NoError(t, err)
	stored, err := tree.Storage().Get(ctx, appended.ChangeID)
	require.NoError(t, err)
	change := stored.RawTreeChangeWithId()
	root := tree.Header()
	forgedBytes, err := (&model.ObjectChangePayload{
		SmartBlockType: model.SmartBlockType(coresb.SmartBlockTypePinkhaTorahOperations), Key: "v1",
	}).Marshal()
	require.NoError(t, err)
	forged, err := objecttree.DeriveObjectTreeRoot(objecttree.ObjectTreeDerivePayload{
		SpaceId: spaceID, ChangeType: spacedomain.ChangeType, ChangePayload: forgedBytes, IsEncrypted: true,
	}, nil)
	require.NoError(t, err)
	malformed, err := objecttree.DeriveObjectTreeRoot(objecttree.ObjectTreeDerivePayload{
		SpaceId: spaceID, ChangeType: torahopscontract.ChangeType, ChangePayload: []byte("unexpected-contract"), IsEncrypted: true,
	}, nil)
	require.NoError(t, err)
	for _, test := range []struct {
		name    string
		spaceID string
		payload treestorage.TreeStorageCreatePayload
		want    error
	}{
		{"canonical empty", spaceID, treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}}, torahopscontract.ErrPrivateOperation},
		{"signed populated", spaceID, treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{change.Id}, Changes: []*treechangeproto.RawTreeChangeWithId{change}}, torahopscontract.ErrPrivateOperation},
		{"foreign receiving Space", "foreign-space", treestorage.TreeStorageCreatePayload{RootRawChange: root}, torahopscontract.ErrPrivateRoot},
		{"missing receiving Space", "", treestorage.TreeStorageCreatePayload{RootRawChange: root}, torahopscontract.ErrPrivateRoot},
		{"forged generic enum", spaceID, treestorage.TreeStorageCreatePayload{RootRawChange: forged}, torahopscontract.ErrPrivateRoot},
		{"noncanonical private contract", spaceID, treestorage.TreeStorageCreatePayload{RootRawChange: malformed}, torahopscontract.ErrPrivateRoot},
	} {
		t.Run(test.name, func(t *testing.T) {
			builder := &privatePutBuilder{}
			spaces := &privatePutSpaces{b: builder}
			manager := &treeManager{spaceService: spaces}
			require.ErrorIs(t, manager.ValidateAndPutTree(ctx, test.spaceID, test.payload), test.want)
			require.Zero(t, spaces.gets, "reject before opening a Space or constructing a writable backend")
			require.Zero(t, builder.puts, "private history must never reach the generic PutTree writer")
		})
	}
	stillStored, err := tree.Storage().Get(ctx, appended.ChangeID)
	require.NoError(t, err)
	require.Equal(t, change, stillStored.RawTreeChangeWithId(), "rejection preserves existing native history bytes")
	snapshot, err := host.ReadTarget(ctx, op.Target, 100)
	require.NoError(t, err)
	require.Len(t, snapshot.Projection.Live, 1)
	require.Equal(t, op.Payload, snapshot.Projection.Live[0].Operation.Payload)
}

func TestPinkhaPrivateTreeManagerPreservesLegacyPutTreeBoundary(t *testing.T) {
	pageBytes, err := (&model.ObjectChangePayload{SmartBlockType: model.SmartBlockType_Page}).Marshal()
	require.NoError(t, err)
	for _, test := range []struct {
		name        string
		changeType  string
		changeBytes []byte
	}{
		{"existing Page", spacedomain.ChangeType, pageBytes},
		{"opaque unknown type", "fixture.unknown.future.type", []byte("preserve upstream generic behavior")},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, err := objecttree.DeriveObjectTreeRoot(objecttree.ObjectTreeDerivePayload{
				SpaceId: "legacy-space", ChangeType: test.changeType, ChangePayload: test.changeBytes, IsEncrypted: true,
			}, nil)
			require.NoError(t, err)
			payload := treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}}
			upstreamResult := errors.New("observable upstream generic PutTree result")
			builder := &privatePutBuilder{err: upstreamResult}
			spaces := &privatePutSpaces{b: builder}
			manager := &treeManager{spaceService: spaces}
			require.ErrorIs(t, manager.ValidateAndPutTree(context.Background(), "legacy-space", payload), upstreamResult)
			require.Equal(t, 1, spaces.gets)
			require.Equal(t, 1, builder.puts)
			require.Equal(t, payload, builder.payload, "non-private payload and backend result remain unchanged")
		})
	}
}
