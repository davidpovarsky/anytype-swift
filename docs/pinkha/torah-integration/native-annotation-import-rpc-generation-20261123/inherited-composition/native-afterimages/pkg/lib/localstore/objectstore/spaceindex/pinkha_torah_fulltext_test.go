package spaceindex

import (
	"context"
	"errors"
	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"sync/atomic"
	"testing"
	"time"
)

type torahFailingFTQueue struct {
	FulltextQueue
	fail    atomic.Bool
	calls   atomic.Int32
	blocked <-chan struct{}
	entered chan struct{}
}

func (q *torahFailingFTQueue) AddToIndexQueue(ctx context.Context, ids ...domain.FullID) (uint64, int, error) {
	q.calls.Add(1)
	if q.entered != nil {
		select {
		case q.entered <- struct{}{}:
		default:
		}
	}
	if q.blocked != nil {
		select {
		case <-q.blocked:
		case <-ctx.Done():
			return 0, 0, ctx.Err()
		}
	}
	if q.fail.Load() {
		return 0, 0, errors.New("injected common-DB queue failure")
	}
	return q.FulltextQueue.AddToIndexQueue(ctx, ids...)
}

func TestTorahFulltextOutboxCommitRollbackAndRetry(t *testing.T) {
	store := NewStoreFixture(t)
	store.stopTorahFulltext()
	queue := &torahFailingFTQueue{FulltextQueue: store.fulltextQueue}
	queue.fail.Store(true)
	store.fulltextQueue = queue
	store.prepareTorahFulltext()
	store.startTorahFulltext()
	ctx := context.Background()
	details := domain.NewDetails().SetString(domain.RelationKey(torah.CanonicalKeyKey), "actualCanonical")
	tx, err := store.WriteTx(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if err = store.recordTorahFulltext(tx.Context(), "disposable-doc", nil, details); err != nil {
		t.Fatal(err)
	}
	if queue.calls.Load() != 0 {
		t.Fatal("FT queue notified before commit")
	}
	if err = tx.Rollback(); err != nil {
		t.Fatal(err)
	}
	if count, err := store.torahOutbox.Count(ctx); err != nil || count != 0 {
		t.Fatal("rollback retained an outbox entry", err)
	}
	if queue.calls.Load() != 0 {
		t.Fatal("rolled-back projection escaped into FT queue")
	}
	tx, err = store.WriteTx(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if err = store.recordTorahFulltext(tx.Context(), "disposable-doc", nil, details); err != nil {
		t.Fatal(err)
	}
	if err = tx.Commit(); err != nil {
		t.Fatal(err)
	}
	waitTorahFT(t, func() bool { return queue.calls.Load() > 0 })
	if count, err := store.torahOutbox.Count(ctx); err != nil || count != 1 {
		t.Fatal("queue failure lost durable retry", err)
	}
	queue.fail.Store(false)
	// No new edit/wake: the running worker must retry a transient failure itself.
	waitTorahFT(t, func() bool { count, err := store.torahOutbox.Count(ctx); return err == nil && count == 0 })
	if queue.calls.Load() < 2 {
		t.Fatal("retry did not reach the original queue")
	}
}

func waitTorahFT(t *testing.T, condition func() bool) {
	t.Helper()
	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		if condition() {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatal("native full-text worker deadline exceeded")
}

func TestTorahFulltextOutboxCommitDoesNotWaitForCommonTransaction(t *testing.T) {
	store := NewStoreFixture(t)
	store.stopTorahFulltext()
	unblock := make(chan struct{})
	queue := &torahFailingFTQueue{FulltextQueue: store.fulltextQueue, blocked: unblock, entered: make(chan struct{}, 1)}
	store.fulltextQueue = queue
	store.prepareTorahFulltext()
	store.startTorahFulltext()
	tx, err := store.WriteTx(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()
	details := domain.NewDetails().SetString(domain.RelationKey(torah.CanonicalKeyKey), "actualCanonical")
	if err = store.recordTorahFulltext(tx.Context(), "blocked-common-db", nil, details); err != nil {
		t.Fatal(err)
	}
	committed := make(chan error, 1)
	go func() { committed <- tx.Commit() }()
	// Native indexBatch holds commonTx until this per-Space Commit returns.
	// The queue gate models that lock ordering; synchronous drain deadlocks here.
	select {
	case err = <-committed:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(3 * time.Second):
		close(unblock)
		t.Fatal("Space commit waited for the common DB transaction")
	}
	select {
	case <-queue.entered:
	case <-time.After(3 * time.Second):
		t.Fatal("worker did not enqueue committed update")
	}
	close(unblock)
	waitTorahFT(t, func() bool {
		count, err := store.torahOutbox.Count(context.Background())
		return err == nil && count == 0
	})
}

func TestTorahFulltextWorkerStopsWithOwningComponent(t *testing.T) {
	store := NewStoreFixture(t)
	store.stopTorahFulltext()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	store.componentCtx = ctx
	store.prepareTorahFulltext()
	store.startTorahFulltext()
	cancel()
	select {
	case <-store.torahFT.done:
	case <-time.After(3 * time.Second):
		t.Fatal("worker outlived the original ObjectStore component")
	}
}
