//go:build pinkha_localstore_witness

package localstorewitness

import (
	"context"
	crand "crypto/rand"
	"errors"
	"os"
	"path/filepath"
	"sync/atomic"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/spacepayloads"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	nativecrypto "github.com/anyproto/any-sync/util/crypto"
)

const probeCollection = "witness-owned-probe"

var injectedFailure = errors.New("owned witness injected boundary failure")

type fixture struct {
	db      anystore.DB
	storage spacestorage.SpaceStorage
	root    string
	owner   *fixtureOwner
}
type fixtureOwner struct {
	nonce      [32]byte
	generation atomic.Uint64
	live       atomic.Bool
	acquired   atomic.Int32
	closed     atomic.Int32
}
type fixtureCapability struct {
	owner    *fixtureOwner
	storage  spacestorage.SpaceStorage
	binding  Binding
	closeErr error
}
type fixtureLease struct {
	cap    *fixtureCapability
	closed bool
}

func (*fixtureLease) localStoreWitnessLease() {}
func (c *fixtureCapability) Acquire(ctx context.Context) (Lease, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	l := &fixtureLease{cap: c}
	if err := l.CheckCurrent(ctx); err != nil {
		return nil, err
	}
	c.owner.acquired.Add(1)
	return l, nil
}
func (l *fixtureLease) Binding() Binding                   { return l.cap.binding }
func (l *fixtureLease) Storage() spacestorage.SpaceStorage { return l.cap.storage }
func (l *fixtureLease) CheckCurrent(ctx context.Context) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	if l.closed || !l.cap.owner.live.Load() || l.cap.owner.generation.Load() != l.cap.binding.Generation || l.cap.owner.nonce != l.cap.binding.OwnerNonce {
		return ErrOwnership
	}
	return nil
}
func (l *fixtureLease) Close() error {
	if l.closed {
		return errors.New("fixture lease closed twice")
	}
	l.closed = true
	l.cap.owner.closed.Add(1)
	return l.cap.closeErr
}
func (f *fixture) issuer(db anystore.DB) *fixtureCapability {
	st := f.storage
	if db != nil {
		st = &wrappedStorage{SpaceStorage: st, db: db}
	}
	return &fixtureCapability{owner: f.owner, storage: st, binding: Binding{
		Authority: FixtureOnlyAuthority, OwnerNonce: f.owner.nonce, Generation: f.owner.generation.Load(), SpaceID: f.storage.Id()}}
}

func (c *fixtureCapability) capability() *Capability {
	return &Capability{acquire: c.Acquire}
}

func (f *fixture) capability(db anystore.DB) *Capability {
	return f.issuer(db).capability()
}

type wrappedStorage struct {
	spacestorage.SpaceStorage
	db anystore.DB
}

func (s *wrappedStorage) AnyStore() anystore.DB { return s.db }

func must(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

func newFixture(t *testing.T) *fixture {
	t.Helper()
	root := os.Getenv("PINKHA_LOCAL_WITNESS_PRIVATE_ROOT")
	if root == "" {
		t.Fatal("explicit private fixture root required")
	}
	info, err := os.Lstat(root)
	must(t, err)
	if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 || info.Mode().Perm() != 0700 {
		t.Fatal("private root must be owned directory mode 0700")
	}
	dir, err := os.MkdirTemp(root, "case-")
	must(t, err)
	db, err := anystore.Open(context.Background(), filepath.Join(dir, "store.db"), &anystore.Config{
		ReadConnections: 2, SQLiteGlobalPageCachePreallocateSizeBytes: -1})
	must(t, err)
	f := &fixture{db: db, root: dir, owner: &fixtureOwner{}}
	f.owner.generation.Store(1)
	f.owner.live.Store(true)
	_, err = crand.Read(f.owner.nonce[:])
	must(t, err)
	t.Cleanup(func() {
		f.owner.live.Store(false)
		f.owner.generation.Add(1)
		if f.owner.acquired.Load() != f.owner.closed.Load() {
			t.Error("owned fixture lease leaked")
		}
		if err := db.Close(); err != nil {
			t.Errorf("owned native database close: %v", err)
		}
	})
	keys, err := accountdata.NewRandom()
	must(t, err)
	master, _, err := nativecrypto.GenerateRandomEd25519KeyPair()
	must(t, err)
	meta, _, err := nativecrypto.GenerateRandomEd25519KeyPair()
	must(t, err)
	payload, err := spacepayloads.StoragePayloadForSpaceCreate(spacepayloads.SpaceCreatePayload{
		SigningKey: keys.SignKey, SpaceType: "space", ReplicationKey: 10,
		MasterKey: master, ReadKey: nativecrypto.NewAES(), MetadataKey: meta, Metadata: []byte("owned-local-witness-fixture")})
	must(t, err)
	f.storage, err = spacestorage.Create(context.Background(), db, payload)
	must(t, err)
	if f.storage.Id() != payload.SpaceHeaderWithId.Id {
		t.Fatal("native initialized Space identity differs")
	}
	must(t, f.storage.StateStorage().SetHash(context.Background(), "before"))
	c, err := db.CreateCollection(context.Background(), probeCollection)
	must(t, err)
	must(t, c.Insert(context.Background(), probe("a", []byte{0, 1, 2, 255}), probe("b", []byte{9, 0, 8, 255})))
	return f
}
func probe(id string, raw []byte) *anyenc.Value {
	a := &anyenc.Arena{}
	v := a.NewObject()
	v.Set("id", a.NewString(id))
	v.Set("payload", a.NewBinary(raw))
	v.Set("unicode", a.NewString("\u05e9\u05dc\u05d5\u05dd e\u0301 \u00e9"))
	return v
}

// auditDB delegates every actual read to the native database. Its hooks exist
// only in this build-tagged owned fixture; no capture callback can write.
type auditDB struct {
	anystore.DB
	txctx                                                                    context.Context
	txCalls, inventories, opens, counts, iterators, iteratorCloses, txCloses int
	badContext                                                               bool
	afterInventory                                                           func(context.Context) error
	mode                                                                     string
}

func (d *auditDB) ReadTx(ctx context.Context) (anystore.ReadTx, error) {
	tx, err := d.DB.ReadTx(ctx)
	if err != nil {
		return nil, err
	}
	d.txCalls++
	d.txctx = tx.Context()
	return &auditTx{ReadTx: tx, audit: d}, nil
}
func (d *auditDB) same(ctx context.Context) {
	if ctx != d.txctx {
		d.badContext = true
	}
}
func (d *auditDB) GetCollectionNames(ctx context.Context) ([]string, error) {
	d.same(ctx)
	d.inventories++
	names, err := d.DB.GetCollectionNames(ctx)
	if err != nil {
		return nil, err
	}
	if d.afterInventory != nil {
		if err = d.afterInventory(ctx); err != nil {
			return nil, err
		}
	}
	return names, nil
}
func (d *auditDB) OpenCollection(ctx context.Context, name string) (anystore.Collection, error) {
	d.same(ctx)
	d.opens++
	c, err := d.DB.OpenCollection(ctx, name)
	if err != nil {
		return nil, err
	}
	return &auditCollection{Collection: c, audit: d, name: name}, nil
}

type auditTx struct {
	anystore.ReadTx
	audit *auditDB
}

func (t *auditTx) Commit() error {
	t.audit.txCloses++
	err := t.ReadTx.Commit()
	if t.audit.mode == "transaction-close" {
		return errors.Join(err, injectedFailure)
	}
	return err
}

type auditCollection struct {
	anystore.Collection
	audit *auditDB
	name  string
}

func (c *auditCollection) Find(filter any) anystore.Query {
	if filter != nil {
		c.audit.badContext = true
	}
	return &auditQuery{Query: c.Collection.Find(filter), audit: c.audit, name: c.name}
}

type auditQuery struct {
	anystore.Query
	audit *auditDB
	name  string
}

func (q *auditQuery) Count(ctx context.Context) (int, error) {
	q.audit.same(ctx)
	q.audit.counts++
	return q.Query.Count(ctx)
}
func (q *auditQuery) Iter(ctx context.Context) (anystore.Iterator, error) {
	q.audit.same(ctx)
	q.audit.iterators++
	it, err := q.Query.Iter(ctx)
	if err != nil {
		return nil, err
	}
	return &auditIterator{Iterator: it, audit: q.audit, name: q.name}, nil
}

type auditIterator struct {
	anystore.Iterator
	audit    *auditDB
	name     string
	rows     int
	terminal bool
}

func (i *auditIterator) Next() bool {
	if i.name == probeCollection && i.audit.mode == "iterator-terminal" && i.rows == 1 {
		i.terminal = true
		return false
	}
	next := i.Iterator.Next()
	if next {
		i.rows++
	}
	return next
}
func (i *auditIterator) Err() error {
	err := i.Iterator.Err()
	if i.terminal {
		return errors.Join(err, injectedFailure)
	}
	return err
}
func (i *auditIterator) Close() error {
	i.audit.iteratorCloses++
	err := i.Iterator.Close()
	if i.name == probeCollection && i.audit.mode == "iterator-close" {
		return errors.Join(err, injectedFailure)
	}
	return err
}
