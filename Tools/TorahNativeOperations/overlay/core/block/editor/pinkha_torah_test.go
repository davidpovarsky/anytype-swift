package editor

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/core/block/restriction"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/block/source"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/internal/pinkhat2test"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/datastore/anystoreprovider"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
)

// Source and target lookup boundaries are explicit test adapters. The tested
// factory, base SmartBlock init, native tree/signatures/ACL, operations and CRDT
// databases are real. This is not a full middleware/production-account fixture.
type privateFactoryAccount struct {
	accountService
	keys *accountdata.AccountKeys
}

func (a privateFactoryAccount) Keys() *accountdata.AccountKeys { return a.keys }
func (a privateFactoryAccount) MyParticipantId(space string) string {
	return domain.NewParticipantId(space, a.keys.SignKey.GetPublic().Account())
}

type privateFactoryObjects struct{ objectstore.ObjectStore }

func (privateFactoryObjects) SpaceIndex(string) spaceindex.Store { return nil }

type privateFactorySources struct {
	source.Service
	fixture *pinkhat2test.Fixture
}

func (s privateFactorySources) NewSource(ctx context.Context, space source.Space, id string, opts source.BuildOptions) (source.Source, error) {
	tree, err := s.fixture.Builder.BuildTree(ctx, id, opts.BuildTreeOptsForSpace(space.Id()))
	if err != nil {
		return nil, err
	}
	return &privateFactorySource{tree: tree.(synctree.SyncTree), spaceID: space.Id()}, nil
}

type privateFactorySource struct {
	source.Source
	tree    synctree.SyncTree
	spaceID string
}

func (s *privateFactorySource) Id() string      { return s.tree.Id() }
func (s *privateFactorySource) SpaceID() string { return s.spaceID }
func (*privateFactorySource) Type() coresb.SmartBlockType {
	return coresb.SmartBlockTypePinkhaTorahOperations
}
func (s *privateFactorySource) Tree() objecttree.ObjectTree { return s.tree }
func (s *privateFactorySource) Close() error                { return s.tree.Close() }
func (s *privateFactorySource) ReadDoc(context.Context, source.ChangeReceiver, bool) (state.Doc, error) {
	doc := state.NewDocWithInternalKey(s.Id(), nil, "v1").(*state.State)
	doc.SetDetailAndBundledRelation(bundle.RelationKeyId, domain.String(s.Id()))
	doc.SetDetailAndBundledRelation(bundle.RelationKeySpaceId, domain.String(s.SpaceID()))
	doc.SetDetailAndBundledRelation(bundle.RelationKeyIsHidden, domain.Bool(true))
	return doc, nil
}

type privateFactorySpace struct {
	smartblock.Space
	id      string
	targets map[string]*privateTarget
}

func (s *privateFactorySpace) Id() string         { return s.id }
func (*privateFactorySpace) CanManageSpace() bool { return true }
func (s *privateFactorySpace) Do(id string, fn func(smartblock.SmartBlock) error) error {
	target := s.targets[id]
	if target == nil {
		return torahopsobject.ErrTargetUnavailable
	}
	return fn(target)
}

type privateTarget struct {
	smartblock.SmartBlock
	doc     *state.State
	spaceID string
	deleted bool
}

func (t *privateTarget) Id() string                  { return t.doc.RootId() }
func (t *privateTarget) SpaceID() string             { return t.spaceID }
func (*privateTarget) Type() coresb.SmartBlockType   { return coresb.SmartBlockTypePage }
func (t *privateTarget) IsDeleted() bool             { return t.deleted }
func (t *privateTarget) Details() *domain.Details    { return t.doc.Details() }
func (t *privateTarget) Pick(id string) simple.Block { return t.doc.Pick(id) }

func TestPinkhaPrivateFactoryNativeStorageAndTargetLifecycle(t *testing.T) {
	ctx := context.Background()
	native := pinkhat2test.New(t)
	sp := &privateFactorySpace{id: native.Space.Id(), targets: map[string]*privateTarget{}}
	doc := state.NewDoc("disposable-target", map[string]simple.Block{"block-a": simple.New(&model.Block{Id: "block-a", Content: &model.BlockContentOfText{Text: &model.BlockContentText{Text: "disposable block", Style: model.BlockContentText_Paragraph}}})}).(*state.State)
	target := &privateTarget{doc: doc, spaceID: sp.id}
	sp.targets[target.Id()] = target
	accountPath := t.TempDir()
	provider, err := anystoreprovider.NewInPath(accountPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, provider.Close(ctx)) })
	factory := &ObjectFactory{objectStore: privateFactoryObjects{}, accountService: privateFactoryAccount{keys: native.Keys}, sourceService: privateFactorySources{fixture: native}, dbProvider: provider}
	init := &smartblock.InitContext{Ctx: ctx, SpaceID: sp.id, IsNewObject: true}
	block, err := factory.InitObject(sp, native.RootID, init)
	require.NoError(t, err, "factory must not re-enter the tree lock or run document migrations")
	host, ok := block.(torahopsobject.StoreObject)
	require.True(t, ok)
	require.Equal(t, coresb.SmartBlockTypePinkhaTorahOperations, host.Type())
	require.Equal(t, "pinkhaTorahOps-v1", host.UniqueKey().Marshal())
	require.Equal(t, 1, host.Tree().Len(), "initialization must preserve the genesis-only native tree")
	require.Empty(t, host.Blocks())
	require.ErrorIs(t, restriction.CheckRestrictions(host, model.Restrictions_Delete), restriction.ErrRestricted)
	_, err = host.Show()
	require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	require.ErrorIs(t, host.Apply(host.NewState()), torahopscontract.ErrPrivateOperation)
	operation := torahops.Operation{Version: torahops.Version, SpaceID: sp.id, OperationID: fmt.Sprintf("%032x", 1), AuthorID: native.Keys.SignKey.GetPublic().Account(), Kind: torahops.Add,
		Target: torahops.Target{ObjectID: target.Id(), BlockID: "block-a"}, Source: torahops.Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte("retained native claim")}
	_, err = host.AppendTorahOperation(ctx, operation)
	require.NoError(t, err)
	snapshot, err := host.ReadTorahTarget(ctx, operation.Target, 100)
	require.NoError(t, err)
	require.Len(t, snapshot.Projection.Live, 1)
	count := host.Tree().Len()
	require.Equal(t, 2, count)
	projectionPath := filepath.Join(accountPath, "objectstore", sp.id, "crdt.db")
	nativeFile, err := os.Stat(native.NativePath)
	require.NoError(t, err)
	projectionFile, err := os.Stat(projectionPath)
	require.NoError(t, err)
	require.False(t, os.SameFile(nativeFile, projectionFile), "projection/native writes must use different SQLite files")
	for i, test := range []string{"missing object", "foreign Space", "deleted object", "uninstalled object", "deleted block", "self target"} {
		t.Run(test, func(t *testing.T) {
			invalid := operation
			invalid.OperationID = fmt.Sprintf("%032x", i+2)
			switch test {
			case "missing object":
				delete(sp.targets, target.Id())
				defer func() { sp.targets[target.Id()] = target }()
			case "foreign Space":
				target.spaceID = "foreign"
				defer func() { target.spaceID = sp.id }()
			case "deleted object":
				target.deleted = true
				defer func() { target.deleted = false }()
			case "uninstalled object":
				target.doc.SetDetail(bundle.RelationKeyIsUninstalled, domain.Bool(true))
				defer target.doc.SetDetail(bundle.RelationKeyIsUninstalled, domain.Bool(false))
			case "deleted block":
				target.doc = state.NewDoc(target.Id(), nil).(*state.State)
				defer func() { target.doc = doc }()
			case "self target":
				invalid.Target.ObjectID = host.Id()
			}
			_, err := host.AppendTorahOperation(ctx, invalid)
			require.ErrorIs(t, err, torahopsobject.ErrTargetUnavailable)
			_, err = host.ReadTorahTarget(ctx, invalid.Target, 100)
			require.ErrorIs(t, err, torahopsobject.ErrTargetUnavailable)
			require.Equal(t, count, host.Tree().Len(), "unavailable target never deletes or retargets the journal")
		})
	}
	restored, err := host.ReadTorahTarget(ctx, operation.Target, 100)
	require.NoError(t, err)
	require.Equal(t, snapshot.Projection, restored.Projection)
	require.NoError(t, host.Close())
	// Reopen the same native history through the factory into a fresh projection DB.
	freshAccount := t.TempDir()
	freshProvider, err := anystoreprovider.NewInPath(freshAccount)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, freshProvider.Close(ctx)) })
	factory.dbProvider = freshProvider
	reopened, err := factory.InitObject(sp, native.RootID, &smartblock.InitContext{Ctx: ctx, SpaceID: sp.id})
	require.NoError(t, err)
	rebuilt, err := reopened.(torahopsobject.StoreObject).ReadTorahTarget(ctx, operation.Target, 100)
	require.NoError(t, err)
	require.Equal(t, snapshot.Projection, rebuilt.Projection)
	require.Equal(t, count, reopened.Tree().Len())
	require.NoError(t, reopened.Close())
	getter := freshProvider.GetCrdtDb(sp.id)
	require.NoError(t, freshProvider.DeleteSpaceData(sp.id))
	_, err = getter.Wait()
	require.ErrorIs(t, err, anystoreprovider.ErrSpaceDeleted)
	_, err = os.Stat(filepath.Join(freshAccount, "objectstore", sp.id))
	require.True(t, os.IsNotExist(err))
	_, err = os.Stat(native.NativePath)
	require.NoError(t, err, "projection cleanup cannot remove the separately owned native journal")
	t.Log("factory/source boundary fixture: real native signed tree + provider-owned CRDT DB; target lookup is controlled real State; no App/RPC or atomic two-tree lifecycle claim")
}
