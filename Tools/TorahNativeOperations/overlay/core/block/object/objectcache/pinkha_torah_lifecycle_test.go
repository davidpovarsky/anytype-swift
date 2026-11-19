package objectcache

import (
	"context"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app/ocache"
	"github.com/anyproto/any-sync/commonspace"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/internal/pinkhat2test"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
)

type pinkhaCacheTarget struct {
	smartblock.SmartBlock
	id              string
	closing, finish chan struct{}
}

func (b *pinkhaCacheTarget) Id() string { return b.id }
func (b *pinkhaCacheTarget) Close() error {
	if b.closing != nil {
		close(b.closing)
		<-b.finish
	}
	return nil
}
func (*pinkhaCacheTarget) TryClose(time.Duration) (bool, error) { return false, nil }

func TestPinkhaTargetCacheLeaseRejectsClosingAndReplacedInstances(t *testing.T) {
	ctx := context.Background()
	first := &pinkhaCacheTarget{id: "target", closing: make(chan struct{}), finish: make(chan struct{})}
	second := &pinkhaCacheTarget{id: "target"}
	var loaded ocache.Object = first
	c := &objectCache{closing: make(chan struct{}), cache: ocache.New(func(context.Context, string) (ocache.Object, error) { return loaded, nil }, ocache.WithGCPeriod(0))}
	t.Cleanup(func() { require.NoError(t, c.cache.Close()) })
	require.False(t, c.PinkhaTorahTargetIsCurrent(first))
	_, err := c.cache.Get(ctx, first.Id())
	require.NoError(t, err)
	require.True(t, c.PinkhaTorahTargetIsCurrent(first))
	require.False(t, c.PinkhaTorahTargetIsCurrent(second), "same ID is insufficient for native cache authority")
	done := make(chan error, 1)
	go func() { _, err := c.cache.Remove(ctx, first.Id()); done <- err }()
	select {
	case <-first.closing:
	case <-time.After(time.Second):
		t.Fatal("native cache did not start close")
	}
	checked := make(chan bool, 1)
	go func() { checked <- c.PinkhaTorahTargetIsCurrent(first) }()
	select {
	case current := <-checked:
		require.False(t, current)
	case <-time.After(time.Second):
		t.Fatal("cache identity check waited for close while target could be locked")
	}
	close(first.finish)
	select {
	case err := <-done:
		require.NoError(t, err)
	case <-time.After(time.Second):
		t.Fatal("native cache close did not finish")
	}
	loaded = second
	_, err = c.cache.Get(ctx, second.Id())
	require.NoError(t, err)
	require.False(t, c.PinkhaTorahTargetIsCurrent(first))
	require.True(t, c.PinkhaTorahTargetIsCurrent(second))
	close(c.closing)
	require.False(t, c.PinkhaTorahTargetIsCurrent(second))
}

type pinkhaRootCommonSpace struct {
	commonspace.Space
	storage spacestorage.SpaceStorage
}

func (s pinkhaRootCommonSpace) Id() string                         { return s.storage.Id() }
func (s pinkhaRootCommonSpace) Storage() spacestorage.SpaceStorage { return s.storage }

type pinkhaRootSpace struct {
	smartblock.Space
	common commonspace.Space
}

func (s pinkhaRootSpace) Id() string                     { return s.common.Id() }
func (s pinkhaRootSpace) CommonSpace() commonspace.Space { return s.common }

func TestPinkhaPrivateRootCannotBypassAccountCreationGuard(t *testing.T) {
	f := pinkhat2test.NewWithoutPrivateRoot(t)
	ctx := context.Background()
	c := &objectCache{space: pinkhaRootSpace{common: pinkhaRootCommonSpace{storage: f.Space}}}
	root, err := torahopscontract.Root(f.Space.Id())
	require.NoError(t, err)
	stored, err := f.Space.TreeStorage(ctx, root.Id)
	require.ErrorIs(t, err, treestorage.ErrUnknownTreeId)
	require.Nil(t, stored)
	_, err = c.CreateTreeObjectWithPayload(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}}, nil)
	require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	stored, err = f.Space.TreeStorage(ctx, root.Id)
	require.ErrorIs(t, err, treestorage.ErrUnknownTreeId, "the actual native root must remain absent after missing-guard rejection")
	require.Nil(t, stored)
}
