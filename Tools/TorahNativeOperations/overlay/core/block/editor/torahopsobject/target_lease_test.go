package torahopsobject

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/settings/settingsstate"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/internal/pinkhat2test"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/stretchr/testify/require"
)

// Target lookup is a controlled native State boundary; settings storage,
// signed changes, full-history reconstruction and the lease implementation are
// real. This does not replace the native account/two-client acceptance lanes.
type leaseTargetBlock struct {
	smartblock.SmartBlock
	mu      sync.Mutex
	doc     *state.State
	spaceID string
	deleted bool
}

func (b *leaseTargetBlock) Lock()                       { b.mu.Lock() }
func (b *leaseTargetBlock) Unlock()                     { b.mu.Unlock() }
func (b *leaseTargetBlock) Id() string                  { return b.doc.RootId() }
func (b *leaseTargetBlock) SpaceID() string             { return b.spaceID }
func (b *leaseTargetBlock) Type() coresb.SmartBlockType { return coresb.SmartBlockTypePage }
func (b *leaseTargetBlock) IsDeleted() bool             { return b.deleted }
func (b *leaseTargetBlock) Details() *domain.Details    { return b.doc.Details() }
func (b *leaseTargetBlock) Pick(id string) simple.Block { return b.doc.Pick(id) }

type leaseSpace struct {
	smartblock.Space
	id         string
	target     *leaseTargetBlock
	settings   objecttree.ObjectTree
	current    bool
	loadErr    error
	onSettings func()
}

func (s *leaseSpace) Id() string { return s.id }
func (s *leaseSpace) GetObject(ctx context.Context, id string) (smartblock.SmartBlock, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if s.loadErr != nil {
		return nil, s.loadErr
	}
	if id != s.target.Id() {
		return nil, ErrTargetUnavailable
	}
	return s.target, nil
}
func (s *leaseSpace) PinkhaTorahSettingsTree(context.Context) (objecttree.ObjectTree, error) {
	if s.onSettings != nil {
		s.onSettings()
	}
	return s.settings, nil
}
func (s *leaseSpace) PinkhaTorahTargetIsCurrent(sb smartblock.SmartBlock) bool {
	return s.current && sb == s.target
}

func newLeaseSpace(t *testing.T) (*pinkhat2test.Fixture, *leaseSpace, torahops.Target) {
	t.Helper()
	f := pinkhat2test.New(t)
	target := &leaseTargetBlock{doc: state.NewDoc("lease-target", nil).(*state.State), spaceID: f.Space.Id()}
	sp := &leaseSpace{id: f.Space.Id(), target: target, settings: f.Settings, current: true}
	return f, sp, torahops.Target{ObjectID: target.Id()}
}

func requireLeaseUnlocked(t *testing.T, sp *leaseSpace) {
	t.Helper()
	require.True(t, sp.target.mu.TryLock(), "target must be released on this path")
	sp.target.mu.Unlock()
	require.True(t, sp.settings.TryLock(), "settings must be released on this path")
	sp.settings.Unlock()
}

func TestPinkhaNativeTargetLeaseHoldsBothLocksAndReleasesOnce(t *testing.T) {
	f, sp, target := newLeaseSpace(t)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	leased, release, err := AcquireNativeTargetLease(ctx, sp, f.RootID, target)
	require.NoError(t, err)
	require.False(t, sp.settings.TryLock(), "settings deletion must wait for the lease")
	require.False(t, sp.target.mu.TryLock(), "block mutation/uninstall must wait for the lease")
	require.NoError(t, CheckNativeTargetLease(leased, sp, f.RootID, target))
	require.ErrorIs(t, CheckNativeTargetLease(leased, sp, "different-root", target), ErrTargetUnavailable)
	other := target
	other.BlockID = "different-block"
	require.ErrorIs(t, CheckNativeTargetLease(leased, sp, f.RootID, other), ErrTargetUnavailable)
	cancel()
	require.ErrorIs(t, CheckNativeTargetLease(leased, sp, f.RootID, target), context.Canceled)
	release()
	release()
	requireLeaseUnlocked(t, sp)
}

func TestPinkhaNativeTargetLeaseCancellationAndUnavailableRelease(t *testing.T) {
	for _, scenario := range []string{"cancelled_while_waiting_for_settings", "stale_cache_instance", "deleted_target", "missing_block", "original_loader_error"} {
		t.Run(scenario, func(t *testing.T) {
			f, sp, target := newLeaseSpace(t)
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			want := ErrTargetUnavailable
			switch scenario {
			case "cancelled_while_waiting_for_settings":
				sp.settings.Lock()
				entered := make(chan struct{})
				sp.onSettings = func() { close(entered) }
				done := make(chan error, 1)
				go func() {
					_, release, err := AcquireNativeTargetLease(ctx, sp, f.RootID, target)
					if release != nil {
						release()
					}
					done <- err
				}()
				select {
				case <-entered:
				case <-time.After(time.Second):
					t.Fatal("settings lookup not entered")
				}
				cancel()
				sp.settings.Unlock()
				select {
				case err := <-done:
					require.ErrorIs(t, err, context.Canceled)
				case <-time.After(time.Second):
					t.Fatal("cancelled lease did not return after native unlock")
				}
				requireLeaseUnlocked(t, sp)
				return
			case "stale_cache_instance":
				sp.current = false
			case "deleted_target":
				sp.target.deleted = true
			case "missing_block":
				target.BlockID = "deleted-block"
			case "original_loader_error":
				sp.loadErr = errors.New("native load failed")
				want = sp.loadErr
			}
			leased, release, err := AcquireNativeTargetLease(ctx, sp, f.RootID, target)
			require.ErrorIs(t, err, want)
			require.Nil(t, leased)
			require.Nil(t, release)
			requireLeaseUnlocked(t, sp)
		})
	}
}

func TestPinkhaNativeTargetLeaseCanBeBorrowedOnce(t *testing.T) {
	f, sp, target := newLeaseSpace(t)
	leased, release, err := AcquireNativeTargetLease(context.Background(), sp, f.RootID, target)
	require.NoError(t, err)
	defer release()
	private := &leaseTargetBlock{doc: state.NewDoc(f.RootID, nil).(*state.State), spaceID: sp.Id()}
	otherSpace := *sp
	foreign := &object{SmartBlock: private, space: &otherSpace}
	borrowed, err := foreign.leaseTarget(leased, target)
	require.ErrorIs(t, err, ErrTargetUnavailable, "equal Space ID cannot substitute a different live Space instance")
	require.Nil(t, borrowed)
	o := &object{SmartBlock: private, space: sp}
	borrowed, err = o.leaseTarget(leased, target)
	require.NoError(t, err)
	require.NotNil(t, borrowed)
	second, err := o.leaseTarget(leased, target)
	require.ErrorIs(t, err, ErrTargetUnavailable)
	require.Nil(t, second)
	require.False(t, sp.settings.TryLock())
	require.False(t, sp.target.mu.TryLock())
	borrowed()
	release()
	borrowed()
	requireLeaseUnlocked(t, sp)
	require.ErrorIs(t, CheckNativeTargetLease(leased, sp, f.RootID, target), ErrTargetUnavailable)
	second, err = o.leaseTarget(leased, target)
	require.ErrorIs(t, err, ErrTargetUnavailable)
	require.Nil(t, second)
}

func TestPinkhaNativeTargetLeaseRechecksStateAfterPreload(t *testing.T) {
	for _, scenario := range []string{"target_deleted_after_preload", "cache_replaced_after_preload"} {
		t.Run(scenario, func(t *testing.T) {
			f, sp, target := newLeaseSpace(t)
			preloaded := sp.target
			sp.onSettings = func() {
				preloaded.Lock()
				defer preloaded.Unlock()
				if scenario == "target_deleted_after_preload" {
					preloaded.deleted = true
				} else {
					sp.target = &leaseTargetBlock{doc: state.NewDoc(target.ObjectID, nil).(*state.State), spaceID: sp.Id()}
				}
			}
			leased, release, err := AcquireNativeTargetLease(context.Background(), sp, f.RootID, target)
			require.ErrorIs(t, err, ErrTargetUnavailable)
			require.Nil(t, leased)
			require.Nil(t, release)
			require.True(t, preloaded.mu.TryLock(), "the originally loaded instance must be unlocked on rejection")
			preloaded.mu.Unlock()
			requireLeaseUnlocked(t, sp)
		})
	}
}

func TestPinkhaNativeTargetLeaseReadsGenesisBeforeSnapshot(t *testing.T) {
	f, sp, target := newLeaseSpace(t)
	ctx := context.Background()
	appendSettings := func(data *spacesyncproto.SettingsData, snapshot bool) {
		wire, err := data.MarshalVT()
		require.NoError(t, err)
		f.Settings.Lock()
		_, err = f.Settings.AddContent(ctx, objecttree.SignableChangeContent{Data: wire, Key: f.Keys.SignKey, IsSnapshot: snapshot})
		f.Settings.Unlock()
		require.NoError(t, err)
	}
	deleted := func(id string) *spacesyncproto.SpaceSettingsContent {
		return &spacesyncproto.SpaceSettingsContent{Value: &spacesyncproto.SpaceSettingsContent_ObjectDelete{ObjectDelete: &spacesyncproto.ObjectDelete{Id: id}}}
	}
	appendSettings(&spacesyncproto.SettingsData{Content: []*spacesyncproto.SpaceSettingsContent{deleted(target.ObjectID)}}, false)
	// A locally verified snapshot can omit a deletion from earlier history.
	// BuildFull must still find that durable ObjectDelete, even while the
	// asynchronous target deleter has not yet marked this cached SmartBlock.
	appendSettings(&spacesyncproto.SettingsData{Snapshot: &spacesyncproto.SpaceSettingsSnapshot{DeletedIds: []string{"another-target"}}, Content: []*spacesyncproto.SpaceSettingsContent{deleted("another-target")}}, true)
	f.Settings.Lock()
	visible, err := settingsstate.NewStateBuilder().Build(f.Settings, nil)
	f.Settings.Unlock()
	require.NoError(t, err)
	require.False(t, visible.Exists(target.ObjectID), "fixture must expose the snapshot-only blind spot")
	require.False(t, sp.target.IsDeleted(), "cached target has not yet received asynchronous deletion")
	leased, release, err := AcquireNativeTargetLease(ctx, sp, f.RootID, target)
	require.ErrorIs(t, err, ErrTargetUnavailable)
	require.Nil(t, leased)
	require.Nil(t, release)
	requireLeaseUnlocked(t, sp)
}
