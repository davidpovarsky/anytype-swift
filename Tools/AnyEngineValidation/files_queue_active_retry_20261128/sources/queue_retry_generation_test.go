package status

import (
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store/v2"
	"github.com/stretchr/testify/require"
)

// These controls use the original Queue API and a real isolated AnyStore DB.
// Each fake runner stays blocked until explicitly released, even after its
// attempt context is cancelled. Cleanup releases every such gate before
// joining Queue.Close; there is no native, account, network, or upload action.
type retryQueueInvocation struct {
	ctx      context.Context
	job      Job
	release  chan error
	returned chan struct{}
}

type retryQueueHarness struct {
	q       *Queue
	db      anystore.DB
	path    string
	entered chan *retryQueueInvocation
	stop    chan struct{}

	mu        sync.Mutex
	calls     int
	active    int
	maxActive int
	closeOnce sync.Once
	closeErr  error
}

func newRetryQueueHarness(t *testing.T, path string) *retryQueueHarness {
	t.Helper()
	if path == "" {
		path = filepath.Join(t.TempDir(), "retry-queue.db")
	}
	db, err := anystore.Open(context.Background(), path, nil)
	require.NoError(t, err)
	h := &retryQueueHarness{
		db:      db,
		path:    path,
		entered: make(chan *retryQueueInvocation, 8),
		stop:    make(chan struct{}),
	}
	h.q, err = NewQueue(context.Background(), db, h.run, nil)
	if err != nil {
		_ = db.Close()
		require.NoError(t, err)
	}
	t.Cleanup(func() {
		if err := h.close(); err != nil {
			t.Errorf("close isolated retry DB: %v", err)
		}
	})
	return h
}

func (h *retryQueueHarness) run(ctx context.Context, job Job) error {
	call := &retryQueueInvocation{
		ctx:      ctx,
		job:      job,
		release:  make(chan error, 1),
		returned: make(chan struct{}),
	}
	h.mu.Lock()
	h.calls++
	h.active++
	if h.active > h.maxActive {
		h.maxActive = h.active
	}
	h.mu.Unlock()
	defer func() {
		h.mu.Lock()
		h.active--
		h.mu.Unlock()
		close(call.returned)
	}()
	select {
	case h.entered <- call:
	case <-h.stop:
		return context.Canceled
	}
	// Deliberately do not select ctx.Done: Remove must retain ownership even
	// when a callback observes cancellation but does not return immediately.
	select {
	case err := <-call.release:
		return err
	case <-h.stop:
		return context.Canceled
	}
}

func (h *retryQueueHarness) close() error {
	h.closeOnce.Do(func() {
		h.q.cancel()
		close(h.stop)
		h.q.Close()
		h.closeErr = h.db.Close()
	})
	return h.closeErr
}

func (h *retryQueueHarness) next(t *testing.T) *retryQueueInvocation {
	t.Helper()
	select {
	case call := <-h.entered:
		return call
	case <-time.After(5 * time.Second):
		job, pending, err := h.q.Get(context.Background(), KindDurable, "sp", "file")
		t.Fatalf("next controlled attempt did not enter; pending=%v job=%+v err=%v", pending, job, err)
		return nil
	}
}

func requireRetryQueueRow(t *testing.T, h *retryQueueHarness, attempts int, limited bool) Job {
	t.Helper()
	job, ok, err := h.q.Get(context.Background(), KindDurable, "sp", "file")
	require.NoError(t, err)
	require.True(t, ok)
	require.Equal(t, int64(0), job.NextAt.Unix(), "acknowledged retry stays persistently due")
	require.Equal(t, attempts, job.Attempts)
	require.Equal(t, limited, job.Limited, "failure classification is independent of the due schedule")
	return job
}

func requireRetryQueueDone(t *testing.T, h *retryQueueHarness, calls int) {
	t.Helper()
	waitFor(t, func() bool {
		_, ok, err := h.q.Get(context.Background(), KindDurable, "sp", "file")
		return err == nil && !ok
	})
	require.NoError(t, h.close())
	h.mu.Lock()
	defer h.mu.Unlock()
	require.Equal(t, calls, h.calls)
	require.Equal(t, 0, h.active, "all actual callbacks returned before DB closure")
	require.Equal(t, 1, h.maxActive, "the same job never runs concurrently")
}

func TestQueueKickDuringLimitedAttemptKeepsRetryDue(t *testing.T) {
	ctx := context.Background()
	h := newRetryQueueHarness(t, "")
	h.q.Run()
	require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
	first := h.next(t)

	kicked, err := h.q.KickJob(ctx, KindDurable, "sp", "file")
	require.NoError(t, err)
	require.True(t, kicked)
	requireRetryQueueRow(t, h, 0, false)
	first.release <- ErrLimited

	second := h.next(t)
	row := requireRetryQueueRow(t, h, 1, true)
	require.Equal(t, ErrLimited.Error(), row.LastErr)
	require.Equal(t, 1, second.job.Attempts)
	require.True(t, second.job.Limited)
	require.Equal(t, int64(0), second.job.NextAt.Unix())
	second.release <- nil
	requireRetryQueueDone(t, h, 2)
}

func TestQueueEnqueueDuringFailureKeepsRetryDue(t *testing.T) {
	ctx := context.Background()
	h := newRetryQueueHarness(t, "")
	h.q.Run()
	require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
	first := h.next(t)

	require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
	requireRetryQueueRow(t, h, 0, false)
	first.release <- errors.New("transient controlled failure")

	second := h.next(t)
	row := requireRetryQueueRow(t, h, 1, false)
	require.Equal(t, "transient controlled failure", row.LastErr)
	require.Equal(t, 1, second.job.Attempts)
	second.release <- nil
	requireRetryQueueDone(t, h, 2)
}

func TestQueueActiveRetryRequestsCoalesce(t *testing.T) {
	ctx := context.Background()
	h := newRetryQueueHarness(t, "")
	h.q.Run()
	require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
	first := h.next(t)

	for i := 0; i < 3; i++ {
		kicked, err := h.q.KickJob(ctx, KindDurable, "sp", "file")
		require.NoError(t, err)
		require.True(t, kicked)
		require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
		requireRetryQueueRow(t, h, 0, false)
	}
	first.release <- ErrLimited
	second := h.next(t)
	requireRetryQueueRow(t, h, 1, true)
	second.release <- nil
	requireRetryQueueDone(t, h, 2)
}

func TestQueueRemovedAttemptCannotSettleReplacement(t *testing.T) {
	ctx := context.Background()
	h := newRetryQueueHarness(t, "")
	h.q.Run()
	require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
	first := h.next(t)

	require.NoError(t, h.q.Remove(ctx, KindDurable, "sp", "file"))
	select {
	case <-first.ctx.Done():
	case <-time.After(5 * time.Second):
		t.Fatal("Remove did not cancel the owned attempt")
	}
	require.ErrorIs(t, first.ctx.Err(), context.Canceled)
	require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
	requireRetryQueueRow(t, h, 0, false)

	// The old callback is still blocked. Retain its running-ID fence; a
	// newly inserted row is not permission to overlap the old operation.
	h.q.mu.Lock()
	stillRunning := h.q.running[Job{Kind: KindDurable, SpaceId: "sp", FileId: "file"}.id()] != nil
	h.q.mu.Unlock()
	require.True(t, stillRunning)
	h.mu.Lock()
	callsBeforeReturn, activeBeforeReturn := h.calls, h.active
	h.mu.Unlock()
	require.Equal(t, 1, callsBeforeReturn)
	require.Equal(t, 1, activeBeforeReturn)
	first.release <- ErrLimited

	second := h.next(t)
	select {
	case <-first.returned:
	default:
		t.Fatal("replacement entered before the old callback returned")
	}
	row := requireRetryQueueRow(t, h, 0, false)
	require.Empty(t, row.LastErr, "removed attempt must not overwrite the replacement")
	require.Equal(t, 0, second.job.Attempts)
	require.False(t, second.job.Limited)
	second.release <- nil
	requireRetryQueueDone(t, h, 2)
}

func TestQueueAcknowledgedRetrySurvivesReopen(t *testing.T) {
	ctx := context.Background()
	h := newRetryQueueHarness(t, "")
	h.q.Run()
	require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
	first := h.next(t)
	kicked, err := h.q.KickJob(ctx, KindDurable, "sp", "file")
	require.NoError(t, err)
	require.True(t, kicked)
	requireRetryQueueRow(t, h, 0, false)
	path := h.path

	// Stop while the acknowledged retry's older callback is still active.
	// Queue.Close cancels and joins it; the next=0 write predates shutdown.
	require.NoError(t, h.close())
	select {
	case <-first.returned:
	default:
		t.Fatal("old callback not joined before reopening the durable DB")
	}
	reopened := newRetryQueueHarness(t, path)
	requireRetryQueueRow(t, reopened, 0, false) // before Run can reset anything
	reopened.q.Run()
	resumed := reopened.next(t)
	require.Equal(t, int64(0), resumed.job.NextAt.Unix())
	resumed.release <- nil
	requireRetryQueueDone(t, reopened, 1)
	h.mu.Lock()
	defer h.mu.Unlock()
	require.Equal(t, 1, h.calls)
	require.Equal(t, 0, h.active)
}

func TestQueueRetryDuringSuccessCompletesOnce(t *testing.T) {
	ctx := context.Background()
	h := newRetryQueueHarness(t, "")
	h.q.Run()
	require.NoError(t, h.q.Enqueue(ctx, KindDurable, "sp", "file"))
	first := h.next(t)
	kicked, err := h.q.KickJob(ctx, KindDurable, "sp", "file")
	require.NoError(t, err)
	require.True(t, kicked)
	requireRetryQueueRow(t, h, 0, false)
	first.release <- nil
	waitFor(t, func() bool {
		_, ok, err := h.q.Get(ctx, KindDurable, "sp", "file")
		return err == nil && !ok
	})
	kicked, err = h.q.KickJob(ctx, KindDurable, "sp", "file")
	require.NoError(t, err)
	require.False(t, kicked, "successful work is terminal, not a blind duplicate upload")
	requireRetryQueueDone(t, h, 1)
}
