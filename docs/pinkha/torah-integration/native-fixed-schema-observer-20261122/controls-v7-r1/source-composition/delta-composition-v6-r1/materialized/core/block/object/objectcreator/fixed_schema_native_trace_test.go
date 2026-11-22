package objectcreator_test

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store"

	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage"
)

// Deterministic test instrumentation only. All Space/ACL authority, DB state,
// native transactions, queries and returned data come from the actual runtime.
// Embedded methods delegate unchanged. No production hook or fake Space is added.
type tracedSchemaSpace struct {
	clientspace.Space
	storage anystorage.ClientSpaceStorage
}

func (s *tracedSchemaSpace) Storage() anystorage.ClientSpaceStorage { return s.storage }

type tracedSchemaStorage struct {
	anystorage.ClientSpaceStorage
	db anystore.DB
}

func (s *tracedSchemaStorage) AnyStore() anystore.DB { return s.db }

type nativeSchemaTraceDB struct {
	anystore.DB
	sequence  atomic.Int32
	begin     func(context.Context, int, anystore.ReadTx) error
	committed func(int, bool) error
	faults    *nativeSchemaFaults
}
type nativeSchemaTraceTx struct {
	anystore.ReadTx
	index int
	owner *nativeSchemaTraceDB
}

func (d *nativeSchemaTraceDB) ReadTx(ctx context.Context) (anystore.ReadTx, error) {
	tx, err := d.DB.ReadTx(ctx)
	if err != nil {
		return nil, err
	}
	index := int(d.sequence.Add(1))
	if d.begin != nil {
		if err = d.begin(ctx, index, tx); err != nil {
			return nil, errors.Join(err, tx.Commit())
		}
	}
	return &nativeSchemaTraceTx{ReadTx: tx, index: index, owner: d}, nil
}
func (t *nativeSchemaTraceTx) Commit() error {
	// The notification is strictly after the genuine native Commit returns and
	// releases its reader; it cannot promise scheduling order on another goroutine.
	err := t.ReadTx.Commit()
	if t.owner.committed != nil {
		err = errors.Join(err, t.owner.committed(t.index, t.ReadTx.Done()))
	}
	if t.owner.faults != nil {
		err = errors.Join(err, t.owner.faults.commit)
	}
	return err
}
func (d *nativeSchemaTraceDB) OpenCollection(ctx context.Context, name string) (anystore.Collection, error) {
	collection, err := d.DB.OpenCollection(ctx, name)
	if err != nil {
		return nil, err
	}
	if d.faults != nil && d.faults.open != nil {
		return nil, d.faults.open
	}
	if d.faults == nil {
		return collection, nil
	}
	return &nativeSchemaTraceCollection{Collection: collection, faults: d.faults}, nil
}
func nativeSchemaTracedSpace(spc clientspace.Space, db *nativeSchemaTraceDB) clientspace.Space {
	return &tracedSchemaSpace{Space: spc, storage: &tracedSchemaStorage{ClientSpaceStorage: spc.Storage(), db: db}}
}

// These are deliberately synthetic failure signals AFTER real native operations.
// They prove caller error propagation, not that original SQLite failed in this run.
type nativeSchemaFaults struct {
	open, iteration, close, commit error
}
type nativeSchemaTraceCollection struct {
	anystore.Collection
	faults *nativeSchemaFaults
}

func (c *nativeSchemaTraceCollection) Find(filter any) anystore.Query {
	return &nativeSchemaTraceQuery{Query: c.Collection.Find(filter), faults: c.faults}
}

type nativeSchemaTraceQuery struct {
	anystore.Query
	faults *nativeSchemaFaults
}

func (q *nativeSchemaTraceQuery) Sort(fields ...any) anystore.Query {
	return &nativeSchemaTraceQuery{Query: q.Query.Sort(fields...), faults: q.faults}
}
func (q *nativeSchemaTraceQuery) Iter(ctx context.Context) (anystore.Iterator, error) {
	iter, err := q.Query.Iter(ctx)
	if err != nil {
		return nil, err
	}
	return &nativeSchemaTraceIterator{Iterator: iter, faults: q.faults}, nil
}

type nativeSchemaTraceIterator struct {
	anystore.Iterator
	faults *nativeSchemaFaults
}

func (i *nativeSchemaTraceIterator) Err() error {
	return errors.Join(i.Iterator.Err(), i.faults.iteration)
}
func (i *nativeSchemaTraceIterator) Close() error {
	return errors.Join(i.Iterator.Close(), i.faults.close)
}

type nativeSchemaEventLog struct {
	mu    sync.Mutex
	items []string
}

func (l *nativeSchemaEventLog) add(event string) {
	l.mu.Lock()
	l.items = append(l.items, event)
	l.mu.Unlock()
}
func (l *nativeSchemaEventLog) snapshot() []string {
	l.mu.Lock()
	defer l.mu.Unlock()
	return append([]string(nil), l.items...)
}

func (f *nativeSchemaFixture) pooledReaderACLControl(t *testing.T, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition) {
	t.Helper()
	ctx, cancel := context.WithTimeout(f.ctx, 12*time.Second)
	defer cancel()
	db := spc.Storage().AnyStore()
	// Exact original Heart storageservice.anyStoreConfig sets ReadConnections=4.
	// These are actual native leases, not counters or a fixture semaphore.
	var held []anystore.ReadTx
	var observerWait, aclWait <-chan struct{}
	defer func() {
		cancel()
		for _, tx := range held {
			if err := tx.Commit(); err != nil {
				t.Errorf("release owned native reader: %v", err)
			}
		}
		// Release only owned native leases, then join the two owned goroutines.
		for _, wait := range []<-chan struct{}{observerWait, aclWait} {
			if wait == nil {
				continue
			}
			select {
			case <-wait:
			case <-time.After(2 * time.Second):
				t.Error("owned native fixture goroutine did not drain after cancellation")
			}
		}
	}()
	for n := 0; n < 3; n++ {
		tx, err := db.ReadTx(ctx)
		nativeSchemaNoError(t, err)
		held = append(held, tx)
	}
	readOpened, allowRead := make(chan struct{}), make(chan struct{})
	var allowOnce sync.Once
	allow := func() { allowOnce.Do(func() { close(allowRead) }) }
	defer allow()
	log := &nativeSchemaEventLog{}
	trace := &nativeSchemaTraceDB{DB: db}
	trace.begin = func(ctx context.Context, index int, tx anystore.ReadTx) error {
		if index != 1 {
			return nil
		}
		if tx.Done() {
			return errors.New("genuine observer read lease already closed")
		}
		log.add("observer-reader-four-acquired-after-scope")
		close(readOpened)
		select {
		case <-allowRead:
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	trace.committed = func(index int, done bool) error {
		if !done {
			return errors.New("genuine reader not released before Commit notification")
		}
		if index == 1 {
			log.add("first-genuine-commit-returned")
		}
		return nil
	}
	type observed struct {
		value objectcreator.FixedSchemaObservation
		err   error
	}
	observeDone := make(chan observed, 1)
	observerJoined := make(chan struct{})
	observerWait = observerJoined
	go func() {
		defer close(observerJoined)
		result, err := f.observer.ObserveFixedSchema(ctx, nativeSchemaTracedSpace(spc, trace), definition)
		log.add("full-observer-returned")
		observeDone <- observed{result, err}
	}()
	select {
	case <-readOpened:
	case <-ctx.Done():
		t.Fatal("full observer never acquired its actual fourth reader")
	}
	aclStarted := make(chan struct{})
	aclDone := make(chan error, 1)
	aclJoined := make(chan struct{})
	aclWait = aclJoined
	go func() {
		defer close(aclJoined)
		acl := spc.CommonSpace().Acl()
		acl.Lock()
		defer acl.Unlock()
		log.add("actual-acl-exclusive-lock-held")
		log.add("actual-records-after-started")
		close(aclStarted)
		records, err := acl.RecordsAfter(ctx, "")
		if err == nil && len(records) == 0 {
			err = errors.New("actual ACL read returned no original records")
		}
		log.add("actual-records-after-returned")
		aclDone <- err
	}()
	select {
	case <-aclStarted:
	case <-ctx.Done():
		t.Fatal("actual ACL holder did not start")
	}
	// With three held native leases plus the observer's fourth, this real ACL
	// storage query cannot acquire a reader until the observer releases its lease.
	select {
	case err := <-aclDone:
		t.Fatalf("actual ACL reader bypassed the full native reader pool: %v", err)
	default:
	}
	allow()
	var result observed
	select {
	case result = <-observeDone:
	case <-ctx.Done():
		t.Fatal("observer/ACL native lock ordering did not drain before deadline")
	}
	nativeSchemaNoError(t, result.err)
	if result.value.Disposition != objectcreator.FixedSchemaPersistedMatch {
		t.Fatalf("full instrumented observer failed to match: %d", result.value.Disposition)
	}
	select {
	case err := <-aclDone:
		nativeSchemaNoError(t, err)
	case <-ctx.Done():
		t.Fatal("actual native ACL reader did not drain")
	}
	events := log.snapshot()
	position := func(wanted string) int {
		for i, got := range events {
			if got == wanted {
				return i
			}
		}
		t.Fatalf("missing real concurrency event %s", wanted)
		return -1
	}
	start := position("observer-reader-four-acquired-after-scope")
	locked := position("actual-acl-exclusive-lock-held")
	requested := position("actual-records-after-started")
	committed := position("first-genuine-commit-returned")
	readFinished := position("actual-records-after-returned")
	finished := position("full-observer-returned")
	if !(start < locked && locked < requested && requested < committed && requested < readFinished &&
		committed < finished && readFinished < finished) {
		t.Fatalf("unexpected original concurrency boundaries: %v", events)
	}
	t.Logf("native pool/ACL events: %v", events)
}
