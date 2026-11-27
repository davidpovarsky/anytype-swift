package indexer

import (
	"context"
	"errors"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/cheggaaa/mb/v3"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/space/clientspace/mock_clientspace"
)

type pinkhaFailureTx struct {
	anystore.WriteTx
	commitErr error
}

func (t pinkhaFailureTx) Commit() error {
	if t.commitErr != nil {
		return t.commitErr
	}
	return t.WriteTx.Commit()
}

type pinkhaFailureSpaceStore struct {
	spaceindex.Store
	beginErr, commitErr error
	entered             chan struct{}
	release             chan struct{}
}

func (s *pinkhaFailureSpaceStore) WriteTx(ctx context.Context) (anystore.WriteTx, error) {
	if s.entered != nil {
		close(s.entered)
		<-s.release
	}
	if s.beginErr != nil {
		return nil, s.beginErr
	}
	tx, err := s.Store.WriteTx(ctx)
	if err != nil {
		return nil, err
	}
	return pinkhaFailureTx{WriteTx: tx, commitErr: s.commitErr}, nil
}

type pinkhaFailureCommonStore struct {
	objectstore.ObjectStore
	beginErr, bindErr, commitErr error
	fulltextQueueErr             error
	fulltextQueueCalls           [][]domain.FullID
}

func (s *pinkhaFailureCommonStore) WriteTx(ctx context.Context) (anystore.WriteTx, error) {
	if s.beginErr != nil {
		return nil, s.beginErr
	}
	tx, err := s.ObjectStore.WriteTx(ctx)
	if err != nil {
		return nil, err
	}
	return pinkhaFailureTx{WriteTx: tx, commitErr: s.commitErr}, nil
}
func (s *pinkhaFailureCommonStore) BindSpaceId(ctx context.Context, spaceID, id string) error {
	if s.bindErr != nil {
		return s.bindErr
	}
	return s.ObjectStore.BindSpaceId(ctx, spaceID, id)
}
func (s *pinkhaFailureCommonStore) AddToIndexQueueWithCounter(ctx context.Context, counter uint64, ids ...domain.FullID) (int, error) {
	s.fulltextQueueCalls = append(s.fulltextQueueCalls, append([]domain.FullID(nil), ids...))
	if s.fulltextQueueErr != nil {
		return 0, s.fulltextQueueErr
	}
	return s.ObjectStore.AddToIndexQueueWithCounter(ctx, counter, ids...)
}

func pinkhaCompletionInfo(t *testing.T, id string) smartblock.DocInfo {
	t.Helper()
	space := mock_clientspace.NewMockSpace(t)
	space.EXPECT().Id().Return("spaceId1").Maybe()
	return smartblock.DocInfo{Id: id, Space: space, Heads: []string{"retained-head-" + id}, SmartblockType: coresb.SmartBlockTypeWorkspace,
		Details: domain.NewDetailsFromMap(map[domain.RelationKey]domain.Value{bundle.RelationKeyName: domain.String("completion fixture")})}
}

// These are failures of actual native index transactions/queue completions,
// not source-shape checks. The common-commit case deliberately observes the
// already committed Space write while retaining an error for its caller.
func TestPinkhaIndexerEveryTransactionFailureSettlesAcceptedTasks(t *testing.T) {
	for _, stage := range []string{"space-begin", "common-begin", "bind", "space-commit", "common-commit", "fulltext-queue"} {
		t.Run(stage, func(t *testing.T) {
			fx := newFixture(t)
			underlying := fx.store.SpaceIndex("spaceId1")
			space := &pinkhaFailureSpaceStore{Store: underlying}
			common := &pinkhaFailureCommonStore{ObjectStore: fx.store}
			failure := errors.New("injected " + stage)
			switch stage {
			case "space-begin":
				space.beginErr = failure
			case "common-begin":
				common.beginErr = failure
			case "bind":
				common.bindErr = failure
			case "space-commit":
				space.commitErr = failure
			case "common-commit":
				common.commitErr = failure
			case "fulltext-queue":
				common.fulltextQueueErr = failure
			}
			runCtx, cancel := context.WithCancel(context.Background())
			defer cancel()
			if stage == "fulltext-queue" {
				pinkhaAssertFulltextQueueFailure(t, runCtx, space, common, underlying, failure)
				return
			}
			worker := newSpaceIndexer(runCtx, space, common, false)
			defer worker.close()
			info := pinkhaCompletionInfo(t, "object-"+stage)
			finished := make(chan error, 1)
			go func() { finished <- worker.Index(info) }()
			select {
			case err := <-finished:
				require.ErrorIs(t, err, failure)
			case <-time.After(5 * time.Second):
				t.Fatal("accepted task never completed")
			}
			hash, err := underlying.GetLastIndexedHeadsHash(context.Background(), info.Id)
			require.NoError(t, err)
			if stage == "common-commit" {
				require.Equal(t, headsHash(info.Heads), hash)
			} else {
				require.Empty(t, hash, "failed uncommitted Space tx must roll back")
			}
		})
	}
}

func pinkhaAssertFulltextQueueFailure(t *testing.T, runCtx context.Context, space *pinkhaFailureSpaceStore, common *pinkhaFailureCommonStore, underlying spaceindex.Store, failure error) {
	t.Helper()
	// Both original queue admissions must be in the same real transaction. The
	// task barrier controls batching without replacing either native DB or the
	// production indexBatch/completion path.
	worker := &spaceIndexer{runCtx: runCtx, spaceIndex: space, objectStore: common, fulltextEnabled: true, batcher: mb.New[indexTask](1000)}
	defer worker.close()
	infos := []smartblock.DocInfo{pinkhaCompletionInfo(t, "fulltext-first"), pinkhaCompletionInfo(t, "fulltext-second")}
	callers := make([]chan error, len(infos))
	wantIDs := make([]domain.FullID, len(infos))
	for n := range infos {
		infos[n].SmartblockType = coresb.SmartBlockTypePage
		fulltext, details, _ := infos[n].SmartblockType.Indexable()
		require.True(t, fulltext && details, "fixture must reach the native fulltext queue")
		callers[n] = make(chan error, 1)
		wantIDs[n] = domain.FullID{SpaceID: infos[n].Space.Id(), ObjectID: infos[n].Id}
		go func(n int) { callers[n] <- worker.Index(infos[n]) }(n)
	}
	ctx, stop := context.WithTimeout(context.Background(), 5*time.Second)
	defer stop()
	var tasks []indexTask
	for len(tasks) < len(infos) {
		batch, err := worker.batcher.Wait(ctx)
		require.NoError(t, err, "every caller must be accepted before injecting failure")
		tasks = append(tasks, batch...)
	}
	require.Len(t, tasks, 2)
	require.ErrorIs(t, worker.indexBatch(tasks), failure)
	require.Len(t, common.fulltextQueueCalls, 1)
	require.ElementsMatch(t, wantIDs, common.fulltextQueueCalls[0])
	for n, caller := range callers {
		select {
		case err := <-caller:
			require.ErrorIs(t, err, failure)
		case <-ctx.Done():
			t.Fatal("fulltext insertion failure stranded an accepted caller")
		}
		hash, err := underlying.GetLastIndexedHeadsHash(context.Background(), infos[n].Id)
		require.NoError(t, err)
		require.Empty(t, hash, "failed queue insertion must roll back Space heads/projection")
	}
	for _, task := range tasks {
		_, open := <-task.completion.done
		require.False(t, open, "each affected task must settle exactly once")
	}
	queued, err := common.ObjectStore.ListIdsFromFullTextQueue([]string{"spaceId1"}, 10)
	require.NoError(t, err)
	require.Empty(t, queued, "failed common transaction must leave no fulltext entries")
}

func TestPinkhaIndexerPerTaskFailureDoesNotPoisonCommittedNeighbor(t *testing.T) {
	fx := newFixture(t)
	store := fx.store.SpaceIndex("spaceId1")
	worker := &spaceIndexer{runCtx: context.Background(), spaceIndex: store, objectStore: fx.store}
	failure := errors.New("prevalidated native metadata rejected")
	bad, good := pinkhaCompletionInfo(t, "bad"), pinkhaCompletionInfo(t, "good")
	bad.PinkhaNativeAdmissionError = failure
	tasks := []indexTask{{info: bad, completion: &indexCompletion{done: make(chan error, 1)}}, {info: good, completion: &indexCompletion{done: make(chan error, 1)}}}
	require.ErrorIs(t, worker.indexBatch(tasks), failure)
	require.ErrorIs(t, <-tasks[0].completion.done, failure)
	require.NoError(t, <-tasks[1].completion.done)
	for _, task := range tasks {
		_, open := <-task.completion.done
		require.False(t, open, "one completion only")
	}
	hash, err := store.GetLastIndexedHeadsHash(context.Background(), good.Id)
	require.NoError(t, err)
	require.Equal(t, headsHash(good.Heads), hash)
	hash, err = store.GetLastIndexedHeadsHash(context.Background(), bad.Id)
	require.NoError(t, err)
	require.Empty(t, hash)
}

func TestPinkhaIndexerCanceledCallerCannotBlockTransactionWorker(t *testing.T) {
	fx := newFixture(t)
	failure := errors.New("begin failed after owner cancellation")
	space := &pinkhaFailureSpaceStore{Store: fx.store.SpaceIndex("spaceId1"), beginErr: failure, entered: make(chan struct{}), release: make(chan struct{})}
	runCtx, cancel := context.WithCancel(context.Background())
	defer cancel()
	// Drive the SAME queue and worker boundary explicitly so cancellation occurs
	// after acceptance and while the actual transaction acquisition is blocked.
	worker := &spaceIndexer{runCtx: runCtx, spaceIndex: space, objectStore: fx.store, batcher: mb.New[indexTask](1000)}
	defer worker.close()
	caller := make(chan error, 1)
	info := pinkhaCompletionInfo(t, "canceled")
	go func() { caller <- worker.Index(info) }()
	tasks, err := worker.batcher.Wait(context.Background())
	require.NoError(t, err)
	require.Len(t, tasks, 1)
	finished := make(chan error, 1)
	go func() { finished <- worker.indexBatch(tasks) }()
	select {
	case <-space.entered:
	case <-time.After(5 * time.Second):
		t.Fatal("worker never acquired accepted task")
	}
	cancel()
	select {
	case err = <-caller:
		require.ErrorIs(t, err, context.Canceled)
	case <-time.After(5 * time.Second):
		t.Fatal("caller cancellation did not settle")
	}
	close(space.release)
	select {
	case err = <-finished:
		require.ErrorIs(t, err, failure)
	case <-time.After(5 * time.Second):
		t.Fatal("canceled caller stranded index worker")
	}
	_, open := <-tasks[0].completion.done
	require.False(t, open, "late transaction outcome must not send a second completion")
}
