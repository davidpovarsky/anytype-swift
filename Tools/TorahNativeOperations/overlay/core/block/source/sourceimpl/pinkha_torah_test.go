package sourceimpl

import (
	"context"
	"path/filepath"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/commonspace/objecttreebuilder"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/source"
	"github.com/anyproto/anytype-heart/internal/pinkhat2test"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
)

type privateSourceSpace struct {
	source.Space
	f              *pinkhat2test.Fixture
	receivingSpace string
}

func (s privateSourceSpace) Id() string {
	if s.receivingSpace != "" {
		return s.receivingSpace
	}
	return s.f.Space.Id()
}
func (s privateSourceSpace) TreeBuilder() objecttreebuilder.TreeBuilder { return s.f.Builder }

type privateSourceObjects struct {
	objectstore.ObjectStore
	binds int
}

func (*privateSourceObjects) SpaceIndex(string) spaceindex.Store { return nil }
func (o *privateSourceObjects) BindSpaceId(context.Context, string, string) error {
	o.binds++
	return nil
}

func TestPinkhaPrivateSourceOwnsNoGenericBlockOrStorePath(t *testing.T) {
	f := pinkhat2test.New(t)
	ctx := context.Background()
	objects := &privateSourceObjects{}
	svc := &service{objectStore: objects}
	sp := privateSourceSpace{f: f}
	sc, err := svc.NewSource(ctx, sp, f.RootID, source.BuildOptions{})
	require.NoError(t, err)
	require.IsType(t, &torahOperationsSource{}, sc)
	_, genericStore := sc.(source.Store)
	require.False(t, genericStore, "private operations cannot use the generic store listener")
	tree := sc.(source.ObjectTreeProvider).Tree().(synctree.SyncTree)
	projection, err := anystore.Open(ctx, filepath.Join(f.Dir, "projection.db"), &anystore.Config{ReadConnections: 1})
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, projection.Close()) })
	host, err := torahops.OpenNativeHost(ctx, projection, f.Space.Id(), tree, f.Keys.SignKey, func(context.Context, torahops.Target) (func(), error) { return func() {}, nil })
	require.NoError(t, err)
	op := torahops.Operation{Version: torahops.Version, SpaceID: f.Space.Id(), OperationID: "00000000000000000000000000000001", AuthorID: f.Keys.SignKey.GetPublic().Account(), Kind: torahops.Add,
		Target: torahops.Target{ObjectID: "fixture-target"}, Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte("PRIVATE_OPERATION_SENTINEL")}
	_, err = host.Append(ctx, op)
	require.NoError(t, err)
	before := tree.Len()
	doc, err := sc.ReadDoc(ctx, nil, false)
	require.NoError(t, err)
	require.Equal(t, f.RootID, doc.RootId())
	require.True(t, doc.Details().GetBool(bundle.RelationKeyIsHidden))
	require.Empty(t, doc.Blocks())
	require.True(t, sc.ReadOnly())
	_, err = sc.PushChange(source.PushChangeParams{})
	require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	tree.Lock()
	_, _, _, err = BuildState(f.Space.Id(), nil, tree, true)
	tree.Unlock()
	require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	require.Equal(t, before, tree.Len(), "generic document access must not append migrations or delete operation history")
	snapshot, err := host.ReadTarget(ctx, op.Target, 100)
	require.NoError(t, err)
	require.Len(t, snapshot.Projection.Live, 1)
	require.Equal(t, op.Payload, snapshot.Projection.Live[0].Operation.Payload)
	require.Equal(t, 1, objects.binds)
	cancelled, cancel := context.WithCancel(ctx)
	cancel()
	_, err = sc.ReadDoc(cancelled, nil, false)
	require.ErrorIs(t, err, context.Canceled)
}

func TestPinkhaPrivateSourceRejectsForeignReceivingSpace(t *testing.T) {
	f := pinkhat2test.New(t)
	svc := &service{objectStore: &privateSourceObjects{}}
	_, err := svc.NewSource(context.Background(), privateSourceSpace{f: f, receivingSpace: "foreign-space"}, f.RootID, source.BuildOptions{})
	require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
}
