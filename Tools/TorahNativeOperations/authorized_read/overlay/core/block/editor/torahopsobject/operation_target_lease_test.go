package torahopsobject

import (
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/objecttreebuilder"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/internal/pinkhat2test"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
)

// Actual signed native settings/target trees and mutexes; document State and
// cache membership are controlled boundaries. This is not account/UI acceptance.
type operationLeaseBlock struct {
	smartblock.SmartBlock
	doc     *state.State
	tree    objecttree.ObjectTree
	spaceID string
	deleted bool
	kind    coresb.SmartBlockType
	details *domain.Details
	locks   *[]string
}

func (b *operationLeaseBlock) Lock() {
	b.tree.Lock()
	if b.locks != nil {
		*b.locks = append(*b.locks, b.Id())
	}
}
func (b *operationLeaseBlock) Unlock()                     { b.tree.Unlock() }
func (b *operationLeaseBlock) Id() string                  { return b.doc.RootId() }
func (b *operationLeaseBlock) RootId() string              { return b.doc.RootId() }
func (b *operationLeaseBlock) SpaceID() string             { return b.spaceID }
func (b *operationLeaseBlock) Type() coresb.SmartBlockType { return b.kind }
func (b *operationLeaseBlock) IsDeleted() bool             { return b.deleted }
func (b *operationLeaseBlock) Details() *domain.Details {
	if b.details != nil {
		return b.details
	}
	return b.doc.Details()
}
func (b *operationLeaseBlock) Pick(id string) simple.Block { return b.doc.Pick(id) }
func (b *operationLeaseBlock) Tree() objecttree.ObjectTree { return b.tree }

type operationLeaseSettings struct {
	objecttree.ObjectTree
	locks        *[]string
	acquisitions int
}

func (s *operationLeaseSettings) Lock() {
	s.ObjectTree.Lock()
	s.acquisitions++
	*s.locks = append(*s.locks, "settings")
}

type operationLeaseSpace struct {
	smartblock.Space
	id         string
	objects    map[string]smartblock.SmartBlock
	settings   *operationLeaseSettings
	loads      []string
	onLoad     func(context.Context, string) error
	onSettings func()
}

func (s *operationLeaseSpace) Id() string { return s.id }
func (s *operationLeaseSpace) GetObject(ctx context.Context, id string) (smartblock.SmartBlock, error) {
	s.loads = append(s.loads, id)
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if s.onLoad != nil {
		if err := s.onLoad(ctx, id); err != nil {
			return nil, err
		}
	}
	object := s.objects[id]
	if object == nil {
		return nil, ErrTargetUnavailable
	}
	return object, nil
}
func (s *operationLeaseSpace) PinkhaTorahSettingsTree(ctx context.Context) (objecttree.ObjectTree, error) {
	if s.onSettings != nil {
		s.onSettings()
	}
	return s.settings, ctx.Err()
}
func (s *operationLeaseSpace) PinkhaTorahTargetIsCurrent(sb smartblock.SmartBlock) bool {
	return sb != nil && s.objects[sb.Id()] == sb
}

func newOperationLeaseFixture(t *testing.T, count int) (*pinkhat2test.Fixture, *operationLeaseSpace, []*operationLeaseBlock, *[]string) {
	t.Helper()
	f := pinkhat2test.New(t)
	locks := &[]string{}
	sp := &operationLeaseSpace{id: f.Space.Id(), objects: map[string]smartblock.SmartBlock{}, settings: &operationLeaseSettings{ObjectTree: f.Settings, locks: locks}}
	var blocks []*operationLeaseBlock
	for index := 0; index < count; index++ {
		_, root, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), nil).BuildRoot(objecttree.InitialContent{
			PrivKey: f.Keys.SignKey, AclHeadId: f.ACL.Head().Id, SpaceId: sp.Id(),
			ChangeType: "pinkha.disposable.read-target", Seed: []byte(fmt.Sprintf("target-%d", index)),
		})
		require.NoError(t, err)
		_, err = f.Space.CreateTreeStorage(context.Background(), treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}})
		require.NoError(t, err)
		tree, err := f.Builder.BuildTree(context.Background(), root.Id, objecttreebuilder.BuildTreeOpts{TreeBuilder: objecttree.BuildObjectTree})
		require.NoError(t, err)
		doc := state.NewDoc(root.Id, map[string]simple.Block{
			root.Id:  simple.New(&model.Block{Id: root.Id, ChildrenIds: []string{"live"}}),
			"live":   simple.New(&model.Block{Id: "live"}),
			"orphan": simple.New(&model.Block{Id: "orphan"}),
		}).(*state.State)
		block := &operationLeaseBlock{doc: doc, tree: tree, spaceID: sp.Id(), kind: coresb.SmartBlockTypePage, locks: locks}
		sp.objects[block.Id()] = block
		blocks = append(blocks, block)
	}
	return f, sp, blocks, locks
}

func requireOperationLeaseUnlocked(t *testing.T, sp *operationLeaseSpace, blocks []*operationLeaseBlock) {
	t.Helper()
	require.True(t, sp.settings.TryLock())
	sp.settings.Unlock()
	for _, block := range blocks {
		require.True(t, block.tree.TryLock())
		block.tree.Unlock()
	}
}

func TestPinkhaAuthorizedOperationTargetsAcquireOnceAndInStableOrder(t *testing.T) {
	f, sp, blocks, locks := newOperationLeaseFixture(t, 2)
	ids := []string{blocks[0].Id(), blocks[1].Id()}
	slices.Sort(ids)
	targets := []torahops.Target{{ObjectID: ids[1]}, {ObjectID: ids[0], BlockID: "live"}, {ObjectID: ids[0], BlockID: "absent"}, {ObjectID: ids[0], BlockID: "orphan"}}
	sp.onLoad = func(context.Context, string) error {
		require.True(t, sp.settings.TryLock(), "preload must precede settings lock")
		sp.settings.Unlock()
		return nil
	}
	lease, err := AcquireNativeOperationTargetsLease(context.Background(), sp, f.RootID, targets)
	require.NoError(t, err)
	require.Equal(t, append([]string{"settings"}, ids...), *locks)
	require.Equal(t, ids, sp.loads)
	require.Equal(t, 1, sp.settings.acquisitions)
	require.False(t, sp.settings.TryLock())
	for _, block := range blocks {
		require.False(t, block.tree.TryLock())
	}
	require.Equal(t, torahops.OperationLiveDocument, lease.Reachability[targets[0]])
	require.Equal(t, torahops.OperationLiveBlock, lease.Reachability[targets[1]])
	require.Equal(t, torahops.OperationUnreachableBlock, lease.Reachability[targets[2]])
	require.Equal(t, torahops.OperationUnreachableBlock, lease.Reachability[targets[3]])
	require.NoError(t, lease.Validate(context.Background()))
	require.Len(t, lease.SnapshotToken, 64)
	lease.Release()
	lease.Release()
	requireOperationLeaseUnlocked(t, sp, blocks)
	require.ErrorIs(t, lease.Validate(context.Background()), ErrTargetUnavailable)
}

func TestPinkhaAuthorizedOperationTargetsRejectChangedEligibility(t *testing.T) {
	for _, scenario := range []string{"replaced-cache", "deleted", "uninstalled", "foreign-space", "wrong-native-type"} {
		t.Run(scenario, func(t *testing.T) {
			f, sp, blocks, _ := newOperationLeaseFixture(t, 2)
			victim := blocks[1]
			sp.onSettings = func() {
				switch scenario {
				case "replaced-cache":
					clone := *victim
					sp.objects[victim.Id()] = &clone
				case "deleted":
					victim.deleted = true
				case "uninstalled":
					victim.details = domain.NewDetailsFromMap(map[domain.RelationKey]domain.Value{bundle.RelationKeyIsUninstalled: domain.Bool(true)})
				case "foreign-space":
					victim.spaceID = "foreign-space"
				case "wrong-native-type":
					victim.kind = coresb.SmartBlockTypeFile
				}
			}
			lease, err := AcquireNativeOperationTargetsLease(context.Background(), sp, f.RootID, []torahops.Target{{ObjectID: blocks[0].Id()}, {ObjectID: victim.Id()}})
			require.ErrorIs(t, err, ErrTargetUnavailable)
			require.Nil(t, lease.Release)
			require.Nil(t, lease.Reachability)
			requireOperationLeaseUnlocked(t, sp, blocks)
		})
	}
}

func TestPinkhaAuthorizedOperationTargetsRejectMalformedRequestedGraph(t *testing.T) {
	for _, scenario := range []string{"cycle", "duplicate-parent", "missing-child", "wrong-row-id", "missing-root", "orphan-cycle", "orphan-links-live-graph"} {
		t.Run(scenario, func(t *testing.T) {
			f, sp, blocks, _ := newOperationLeaseFixture(t, 1)
			block := blocks[0]
			target := torahops.Target{ObjectID: block.Id(), BlockID: "live"}
			switch scenario {
			case "cycle":
				block.Pick("live").Model().ChildrenIds = []string{block.Id()}
			case "duplicate-parent":
				block.Pick(block.Id()).Model().ChildrenIds = []string{"live", "live"}
			case "missing-child":
				block.Pick("live").Model().ChildrenIds = []string{"missing"}
			case "wrong-row-id":
				block.Pick("live").Model().Id = "other-id"
			case "missing-root":
				block.doc = state.NewDoc(block.Id(), nil).(*state.State)
			case "orphan-cycle":
				target.BlockID = "orphan"
				block.Pick("orphan").Model().ChildrenIds = []string{"orphan"}
			case "orphan-links-live-graph":
				target.BlockID = "orphan"
				block.Pick("orphan").Model().ChildrenIds = []string{"live"}
			}
			lease, err := AcquireNativeOperationTargetsLease(context.Background(), sp, f.RootID, []torahops.Target{target})
			require.ErrorIs(t, err, ErrTargetUnavailable)
			require.Nil(t, lease.Reachability)
			requireOperationLeaseUnlocked(t, sp, blocks)
		})
	}
}

func TestPinkhaAuthorizedOperationTargetsIgnoreUnrelatedOrphanHistory(t *testing.T) {
	f, sp, blocks, _ := newOperationLeaseFixture(t, 1)
	blocks[0].Pick("orphan").Model().ChildrenIds = []string{"orphan"}
	target := torahops.Target{ObjectID: blocks[0].Id(), BlockID: "missing"}
	lease, err := AcquireNativeOperationTargetsLease(context.Background(), sp, f.RootID, []torahops.Target{target})
	require.NoError(t, err)
	defer lease.Release()
	require.Equal(t, torahops.OperationUnreachableBlock, lease.Reachability[target])
}

func TestPinkhaAuthorizedOperationTargetsRetainGenesisDeletionAuthority(t *testing.T) {
	for _, scenario := range []string{"deleted-object-before-snapshot", "deleted-space-empty-closure"} {
		t.Run(scenario, func(t *testing.T) {
			f, sp, blocks, _ := newOperationLeaseFixture(t, 2)
			appendSettings := func(data *spacesyncproto.SettingsData, snapshot bool) {
				wire, err := data.MarshalVT()
				require.NoError(t, err)
				f.Settings.Lock()
				_, err = f.Settings.AddContent(context.Background(), objecttree.SignableChangeContent{Data: wire, Key: f.Keys.SignKey, IsSnapshot: snapshot})
				f.Settings.Unlock()
				require.NoError(t, err)
			}
			targets := []torahops.Target{{ObjectID: blocks[0].Id()}, {ObjectID: blocks[1].Id()}}
			if scenario == "deleted-space-empty-closure" {
				targets = nil
				appendSettings(&spacesyncproto.SettingsData{Content: []*spacesyncproto.SpaceSettingsContent{{Value: &spacesyncproto.SpaceSettingsContent_SpaceDelete{SpaceDelete: &spacesyncproto.SpaceDelete{}}}}}, false)
			} else {
				deleted := &spacesyncproto.SpaceSettingsContent{Value: &spacesyncproto.SpaceSettingsContent_ObjectDelete{ObjectDelete: &spacesyncproto.ObjectDelete{Id: blocks[1].Id()}}}
				appendSettings(&spacesyncproto.SettingsData{Content: []*spacesyncproto.SpaceSettingsContent{deleted}}, false)
				appendSettings(&spacesyncproto.SettingsData{Snapshot: &spacesyncproto.SpaceSettingsSnapshot{DeletedIds: []string{"unrelated"}}}, true)
			}
			lease, err := AcquireNativeOperationTargetsLease(context.Background(), sp, f.RootID, targets)
			require.ErrorIs(t, err, ErrTargetUnavailable)
			require.Nil(t, lease.Reachability)
			require.False(t, blocks[1].IsDeleted(), "cached state still precedes asynchronous deletion")
			requireOperationLeaseUnlocked(t, sp, blocks)
		})
	}
}

func TestPinkhaAuthorizedOperationTargetsCancellationAndLoadFailure(t *testing.T) {
	for _, scenario := range []string{"cancelled-before-load", "cancelled-during-load", "native-load-error", "cancelled-waiting-settings"} {
		t.Run(scenario, func(t *testing.T) {
			f, sp, blocks, _ := newOperationLeaseFixture(t, 1)
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			want := error(context.Canceled)
			if scenario == "cancelled-before-load" {
				cancel()
			}
			if scenario == "cancelled-during-load" {
				sp.onLoad = func(c context.Context, _ string) error { cancel(); return c.Err() }
			}
			if scenario == "native-load-error" {
				want = errors.New("original load failure")
				sp.onLoad = func(context.Context, string) error { return want }
			}
			if scenario == "cancelled-waiting-settings" {
				entered := make(chan struct{})
				sp.onSettings = func() { close(entered) }
				f.Settings.Lock()
				done := make(chan error, 1)
				go func() {
					value, err := AcquireNativeOperationTargetsLease(ctx, sp, f.RootID, []torahops.Target{{ObjectID: blocks[0].Id()}})
					if value.Release != nil {
						value.Release()
					}
					done <- err
				}()
				select {
				case <-entered:
				case <-time.After(time.Second):
					t.Fatal("settings not reached")
				}
				cancel()
				f.Settings.Unlock()
				select {
				case err := <-done:
					require.ErrorIs(t, err, want)
				case <-time.After(time.Second):
					t.Fatal("cancelled lock waiter did not return")
				}
			} else {
				lease, err := AcquireNativeOperationTargetsLease(ctx, sp, f.RootID, []torahops.Target{{ObjectID: blocks[0].Id()}})
				require.ErrorIs(t, err, want)
				require.Nil(t, lease.Reachability)
			}
			requireOperationLeaseUnlocked(t, sp, blocks)
		})
	}
}

func TestPinkhaAuthorizedOperationReadUsesCurrentPrivateWrapper(t *testing.T) {
	f, sp, _, _ := newOperationLeaseFixture(t, 0)
	tree, err := f.Builder.BuildTree(context.Background(), f.RootID, objecttreebuilder.BuildTreeOpts{TreeBuilder: torahops.NativeTreeBuilder(sp.Id())})
	require.NoError(t, err)
	db, err := anystore.Open(context.Background(), filepath.Join(t.TempDir(), "projection.db"), nil)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	inner := &operationLeaseBlock{doc: state.NewDoc(f.RootID, nil).(*state.State), tree: tree, spaceID: sp.Id(), kind: coresb.SmartBlockTypePinkhaTorahOperations}
	owned := &object{SmartBlock: inner, space: sp, projectionDB: db, key: f.Keys.SignKey}
	owned.host, err = torahops.OpenNativeHost(context.Background(), db, sp.Id(), tree.(synctree.SyncTree), f.Keys.SignKey, owned.leaseTarget)
	require.NoError(t, err)
	sp.objects[f.RootID] = owned
	result, err := owned.ReadAuthorizedTorahOperation(context.Background(), strings.Repeat("1", 32))
	require.NoError(t, err)
	require.Equal(t, torahops.OperationAbsentInVerifiedLocalSnapshot, result.Outcome)
	sp.objects[f.RootID] = inner
	result, err = owned.ReadAuthorizedTorahOperation(context.Background(), strings.Repeat("1", 32))
	require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	require.Equal(t, torahops.AuthorizedOperationSnapshot{}, result)
}
