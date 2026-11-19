// Package pinkhat2test supplies disposable, signed native storage for registry
// adapter tests. It has no network peers, production account or user data.
package pinkhat2test

import (
	"context"
	"errors"
	"path/filepath"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/objecttreebuilder"
	"github.com/anyproto/any-sync/commonspace/spacepayloads"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/commonspace/sync/objectsync/objectmessages"
	"github.com/anyproto/any-sync/commonspace/sync/syncdeps"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
)

type Fixture struct {
	Dir        string
	NativePath string
	DB         anystore.DB
	Space      spacestorage.SpaceStorage
	ACL        list.AclList
	Keys       *accountdata.AccountKeys
	RootID     string
	Builder    *Builder
	Settings   synctree.SyncTree
	trees      []objecttree.ObjectTree
}

func New(t *testing.T) *Fixture {
	return newFixture(t, true)
}

// NewWithoutPrivateRoot retains the real native Space/ACL/settings fixture but
// leaves the private namespace absent for first-installation boundary tests.
func NewWithoutPrivateRoot(t *testing.T) *Fixture {
	return newFixture(t, false)
}

func newFixture(t *testing.T, createPrivateRoot bool) *Fixture {
	t.Helper()
	ctx := context.Background()
	keys, err := accountdata.NewRandom()
	require.NoError(t, err)
	master, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	metadata, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	payload, err := spacepayloads.StoragePayloadForSpaceCreate(spacepayloads.SpaceCreatePayload{
		SigningKey: keys.SignKey, SpaceType: "space", ReplicationKey: 10, MasterKey: master,
		ReadKey: crypto.NewAES(), MetadataKey: metadata, Metadata: []byte("disposable private registry fixture"),
	})
	require.NoError(t, err)
	f := &Fixture{Dir: t.TempDir(), Keys: keys}
	f.NativePath = filepath.Join(f.Dir, "store.db")
	f.DB, err = anystore.Open(ctx, f.NativePath, &anystore.Config{ReadConnections: 1})
	require.NoError(t, err)
	t.Cleanup(func() {
		for _, tree := range f.trees {
			_ = tree.Close()
		}
		require.NoError(t, f.DB.Close())
	})
	f.Space, err = spacestorage.Create(ctx, f.DB, payload)
	require.NoError(t, err)
	aclStorage, err := f.Space.AclStorage()
	require.NoError(t, err)
	f.ACL, err = list.BuildAclListWithIdentity(keys, aclStorage, recordverifier.NewValidateFull())
	require.NoError(t, err)
	root, err := torahopscontract.Root(f.Space.Id())
	require.NoError(t, err)
	f.RootID = root.Id
	if createPrivateRoot {
		_, err = f.Space.CreateTreeStorage(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}})
		require.NoError(t, err)
	}
	f.Builder = &Builder{Fixture: f}
	settings, err := f.Builder.BuildTree(ctx, f.Space.StateStorage().SettingsId(), objecttreebuilder.BuildTreeOpts{TreeBuilder: objecttree.BuildObjectTree})
	require.NoError(t, err)
	f.Settings = settings.(synctree.SyncTree)
	return f
}

// The boundary adapter delegates local tree construction to the actual native
// SyncTree implementation, including caller-selected content and ACL validation.
// Unsupported service methods panic; a network request is always an error.
type Builder struct {
	objecttreebuilder.TreeBuilder
	Fixture *Fixture
	Builds  int
}

func (b *Builder) BuildTree(ctx context.Context, id string, opts objecttreebuilder.BuildTreeOpts) (objecttree.ObjectTree, error) {
	b.Builds++
	f := b.Fixture
	if opts.TreeBuilder == nil {
		return nil, errors.New("registry test requires explicit source tree builder")
	}
	tree, err := synctree.BuildSyncTreeOrGetRemote(ctx, id, synctree.BuildDeps{
		SpaceId: f.Space.Id(), SpaceStorage: f.Space, AclList: f.ACL, BuildObjectTree: opts.TreeBuilder,
		ValidateObjectTree: opts.TreeValidator, Listener: opts.Listener, OnClose: func(string) {},
		SyncClient: &localClient{RequestFactory: synctree.NewRequestFactory(f.Space.Id())}, SyncStatus: status{},
	})
	if err == nil {
		f.trees = append(f.trees, tree)
	}
	return tree, err
}

type localClient struct{ synctree.RequestFactory }

func (*localClient) Broadcast(context.Context, *objectmessages.HeadUpdate) error { return nil }
func (*localClient) QueueRequest(context.Context, syncdeps.Request) error {
	return errors.New("no network in registry fixture")
}
func (*localClient) SendTreeRequest(context.Context, syncdeps.Request, syncdeps.ResponseCollector) error {
	return errors.New("no network in registry fixture")
}

type status struct{}

func (status) Init(*app.App) error                       { return nil }
func (status) Name() string                              { return "pinkha.t2.registry-test" }
func (status) HeadsChange(string, []string)              {}
func (status) HeadsReceive(string, string, []string)     {}
func (status) ObjectReceive(string, string, []string)    {}
func (status) HeadsApply(string, string, []string, bool) {}
func (status) UpdateQueueSize(uint64, int, bool)         {}
