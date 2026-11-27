package spaceloader

import (
	"context"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/spaceinfo"
	"github.com/stretchr/testify/require"
)

type pinkhaClosedSpace struct {
	clientspace.Space
	closes atomic.Int32
}

func (s *pinkhaClosedSpace) Close(context.Context) error { s.closes.Add(1); return nil }

type pinkhaContextBuilder struct{ entered chan struct{} }

func (b *pinkhaContextBuilder) Init(*app.App) error { return nil }
func (b *pinkhaContextBuilder) Name() string        { return "test.pinkha-context-builder" }
func (b *pinkhaContextBuilder) BuildSpace(ctx context.Context, _ bool) (clientspace.Space, error) {
	close(b.entered)
	<-ctx.Done()
	return nil, ctx.Err()
}

func TestPinkhaReadinessLoadedFenceDoesNotStartOrWait(t *testing.T) {
	s := &spaceLoader{}
	sp, current, deliver, err := PinkhaLoaded(s)
	require.ErrorIs(t, err, contract.ErrNotLoaded)
	require.Nil(t, sp)
	require.Nil(t, current)
	require.Nil(t, deliver)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	s.ctx, s.cancel = ctx, cancel
	s.loading = &loadingSpace{loadCh: make(chan struct{})}
	sp, _, _, err = PinkhaLoaded(s)
	require.ErrorIs(t, err, contract.ErrNotLoaded)
	require.Nil(t, sp)
	// A persisted optimistic status or an unfinished load is never readiness.
	require.Nil(t, s.space)
}

func TestPinkhaReadinessLoadedFenceBusyAndRetirement(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	sp := &pinkhaClosedSpace{}
	s := &spaceLoader{ctx: ctx, cancel: cancel, space: sp, loading: &loadingSpace{loadCh: make(chan struct{})}}
	close(s.loading.loadCh)
	_, current, deliver, err := PinkhaLoaded(s)
	require.NoError(t, err)
	require.NoError(t, current())
	var visited atomic.Int32
	s.mx.Lock()
	busy := make(chan error, 1)
	go func() { busy <- deliver(func() error { visited.Add(1); return nil }) }()
	var busyErr error
	select {
	case busyErr = <-busy:
	case <-time.After(time.Second):
		s.mx.Unlock()
		t.Fatal("delivery waited on an owner mutex")
	}
	s.mx.Unlock()
	require.ErrorIs(t, busyErr, contract.ErrSnapshotBusy)
	require.Zero(t, visited.Load())
	entered, release := make(chan struct{}), make(chan struct{})
	finished := make(chan error, 1)
	go func() { finished <- deliver(func() error { close(entered); <-release; visited.Add(1); return nil }) }()
	<-entered
	closed := make(chan error, 1)
	go func() { closed <- s.Close(context.Background()) }()
	select {
	case <-ctx.Done():
		close(release)
		t.Fatal("owner cancellation crossed a held delivery fence")
	case <-closed:
		close(release)
		t.Fatal("owner closed before delivery linearization")
	case <-time.After(20 * time.Millisecond):
	}
	require.Zero(t, sp.closes.Load())
	close(release)
	select {
	case err = <-finished:
		require.NoError(t, err)
	case <-time.After(time.Second):
		t.Fatal("delivery did not finish")
	}
	select {
	case err = <-closed:
		require.NoError(t, err)
	case <-time.After(time.Second):
		t.Fatal("close did not drain delivery")
	}
	require.EqualValues(t, 1, sp.closes.Load())
	require.EqualValues(t, 1, visited.Load())
	require.ErrorIs(t, current(), contract.ErrScopeChanged)
	require.ErrorIs(t, deliver(func() error { visited.Add(1); return nil }), contract.ErrScopeChanged)
	require.EqualValues(t, 1, visited.Load())
}

func TestPinkhaReadinessCloseDuringNativeLoading(t *testing.T) {
	f := newLoaderForTest(t, spaceinfo.LocalStatusOk, true)
	builder := &pinkhaContextBuilder{entered: make(chan struct{})}
	f.loader.builder = builder
	require.NoError(t, f.loader.startLoad(f.loader.ctx))
	select {
	case <-builder.entered:
	case <-time.After(time.Second):
		t.Fatal("original asynchronous load did not start")
	}
	deadline, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	closed := make(chan error, 1)
	go func() { closed <- f.loader.Close(deadline) }()
	select {
	case err := <-closed:
		require.ErrorIs(t, err, context.Canceled)
	case <-deadline.Done():
		t.Fatal("close could not cancel the original load worker")
	}
	select {
	case <-f.loader.loading.loadCh:
	case <-time.After(time.Second):
		t.Fatal("load worker did not finish")
	}
	require.Empty(t, f.recordedStatuses(), "shutdown must not persist Missing after optimistic native load")
	_, _, _, err := PinkhaLoaded(f.loader)
	require.ErrorIs(t, err, contract.ErrNotLoaded)
}
