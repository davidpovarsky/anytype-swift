// Package localstorewitness captures a bounded, private decoded-value witness
// from one already initialized native SpaceStorage. It admits no semantic
// migration, file payload completeness, production authorization, or writes.
package localstorewitness

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"sort"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
)

const FixtureOnlyAuthority = "owned-fixture-only-v1"

var (
	ErrLimit             = errors.New("local witness capture limit exceeded")
	ErrOwnership         = errors.New("current owned Space capability required")
	ErrIncompleteBinding = errors.New("native Space state/root binding incomplete")
	ErrIncompleteScan    = errors.New("native collection inventory incomplete")
)

// Binding is issued by the trusted capability owner, not an external request.
// This initial candidate deliberately accepts fixture-only authority. A real
// account/lifetime adapter and production authority admission are not supplied.
type Binding struct {
	Authority  string
	OwnerNonce [32]byte
	Generation uint64
	SpaceID    string
}

// Capability is a concrete carrier whose acquisition closure is unexported.
// There is no public or production issuer. Only the build-tagged owned fixture
// initializes it in this candidate. A zero value grants nothing. Embedding or
// overriding methods cannot substitute this private closure; forwarding a real
// Capability is ordinary delegation and still uses its original current owner.
type Capability struct {
	acquire func(context.Context) (Lease, error)
}

// Lease is returned only by a capability's trusted private acquisition closure.
// Its marker is not an unforgeability claim and grants no authority by itself.
type Lease interface {
	localStoreWitnessLease()
	Binding() Binding
	Storage() spacestorage.SpaceStorage
	CheckCurrent(context.Context) error
	Close() error
}

type Limits struct {
	MaxCollections int
	MaxRows        int
	MaxRowBytes    int64
	MaxTotalBytes  int64
	MaxDepth       int
	MaxValueNodes  int
}

func DefaultLimits() Limits {
	return Limits{MaxCollections: 64, MaxRows: 10000, MaxRowBytes: 1 << 20, MaxTotalBytes: 16 << 20, MaxDepth: 64, MaxValueNodes: 100000}
}

func (l Limits) valid() bool {
	max := DefaultLimits()
	return l.MaxCollections > 0 && l.MaxCollections <= max.MaxCollections &&
		l.MaxRows > 0 && l.MaxRows <= max.MaxRows &&
		l.MaxRowBytes > 0 && l.MaxRowBytes <= max.MaxRowBytes &&
		l.MaxTotalBytes > 0 && l.MaxTotalBytes <= max.MaxTotalBytes &&
		l.MaxDepth > 0 && l.MaxDepth <= max.MaxDepth &&
		l.MaxValueNodes > 0 && l.MaxValueNodes <= max.MaxValueNodes
}

type row struct{ id, value []byte }
type collection struct {
	name       string
	rows       []row
	bytes      int64
	unresolved bool
}

type Witness struct {
	binding      Binding
	collections  []collection
	rows         int
	valueBytes   int64
	headerDigest string
	digest       string
	complete     bool
}

type CollectionReceipt struct {
	NameSHA256           string
	Rows                 int
	EncodedValueBytes    int64
	UnresolvedCollection bool
}

type Receipt struct {
	Version                      string
	Encoding                     string
	Authority                    string
	OwnerSHA256                  string
	SpaceSHA256                  string
	Generation                   uint64
	SpaceHeaderSHA256            string
	WitnessSHA256                string
	Collections                  int
	Rows                         int
	EncodedValueBytes            int64
	CollectionCoverage           []CollectionReceipt
	LocalDecodedRowsComplete     bool
	InventoryScope               string
	NativeBindingScope           string
	NativeSnapshotProofRequired  bool
	NativeIdentityCensusRequired bool
	HasNativeSourceAdmission     bool
	PermitsDestinationWrites     bool
}

// Receipt contains safe hashes, counts and explicit scope. It contains no native
// IDs, collection names, header bytes, row values, keys, or raw owner nonce.
func (w *Witness) Receipt() (Receipt, error) {
	if w == nil || !w.complete {
		return Receipt{}, ErrIncompleteScan
	}
	r := Receipt{Version: "native-localstore-witness-v1", Encoding: Encoding,
		Authority: w.binding.Authority, OwnerSHA256: sum(w.binding.OwnerNonce[:]),
		SpaceSHA256: sum([]byte(w.binding.SpaceID)), Generation: w.binding.Generation,
		SpaceHeaderSHA256: w.headerDigest, WitnessSHA256: w.digest,
		Collections: len(w.collections), Rows: w.rows, EncodedValueBytes: w.valueBytes,
		LocalDecodedRowsComplete: true, InventoryScope: "registered-native-collections-only", NativeBindingScope: "space-state-acl-settings-roots-only",
		NativeSnapshotProofRequired: true, NativeIdentityCensusRequired: true}
	for _, c := range w.collections {
		r.CollectionCoverage = append(r.CollectionCoverage, CollectionReceipt{
			NameSHA256: sum([]byte(c.name)), Rows: len(c.rows), EncodedValueBytes: c.bytes, UnresolvedCollection: c.unresolved})
	}
	return r, nil
}

func sum(raw []byte) string { s := sha256.Sum256(raw); return hex.EncodeToString(s[:]) }

// WritePrivate emits a deterministic, length-framed private witness. Callers
// must use private storage; raw witness bytes must not enter logs/artifacts.
// Row payloads are decoded-value re-encodings, never original SQLite bytes.
func (w *Witness) WritePrivate(dst io.Writer) error {
	if w == nil || !w.complete || dst == nil {
		return ErrIncompleteScan
	}
	return w.writePrivate(dst)
}

func (w *Witness) writePrivate(dst io.Writer) error {
	put := func(raw []byte) error {
		var n [8]byte
		binary.BigEndian.PutUint64(n[:], uint64(len(raw)))
		written, err := dst.Write(n[:])
		if err != nil {
			return err
		}
		if written != len(n) {
			return io.ErrShortWrite
		}
		written, err = dst.Write(raw)
		if err != nil {
			return err
		}
		if written != len(raw) {
			return io.ErrShortWrite
		}
		return nil
	}
	for _, raw := range [][]byte{[]byte("pinkha-localstore-witness-v1"), []byte(Encoding), []byte(w.binding.Authority), w.binding.OwnerNonce[:], []byte(w.binding.SpaceID)} {
		if err := put(raw); err != nil {
			return err
		}
	}
	var n [8]byte
	binary.BigEndian.PutUint64(n[:], w.binding.Generation)
	if err := put(n[:]); err != nil {
		return err
	}
	binary.BigEndian.PutUint64(n[:], uint64(len(w.collections)))
	if err := put(n[:]); err != nil {
		return err
	}
	for _, c := range w.collections {
		if err := put([]byte(c.name)); err != nil {
			return err
		}
		binary.BigEndian.PutUint64(n[:], uint64(len(c.rows)))
		if err := put(n[:]); err != nil {
			return err
		}
		for _, r := range c.rows {
			if err := put(r.id); err != nil {
				return err
			}
			if err := put(r.value); err != nil {
				return err
			}
		}
	}
	return nil
}

// Capture makes no database-path entry, creates no collections, and never
// invokes live document/export/index/file services. On any error it returns no
// witness, including failures during iterator, transaction or lease cleanup.
func Capture(ctx context.Context, capability *Capability, limits Limits) (w *Witness, err error) {
	if ctx == nil || capability == nil || capability.acquire == nil || !limits.valid() {
		return nil, ErrOwnership
	}
	if err = ctx.Err(); err != nil {
		return nil, err
	}
	lease, err := capability.acquire(ctx)
	if err != nil {
		return nil, err
	}
	return captureLease(ctx, lease, limits, FixtureOnlyAuthority)
}

// captureLease is the exact bounded reader shared by the two fixed authorities.
// Neither authority nor acquisition is supplied by an external caller.
func captureLease(ctx context.Context, lease Lease, limits Limits, authority string) (w *Witness, err error) {
	if lease == nil {
		return nil, ErrOwnership
	}
	defer func() {
		err = errors.Join(err, lease.Close())
		if err != nil {
			w = nil
		} else if w != nil {
			w.complete = true
		}
	}()
	binding := lease.Binding()
	storage := lease.Storage()
	if binding.Authority != authority || binding.OwnerNonce == ([32]byte{}) || binding.Generation == 0 || binding.SpaceID == "" || storage == nil || storage.Id() != binding.SpaceID {
		return nil, ErrOwnership
	}
	check := func() error {
		if err := ctx.Err(); err != nil {
			return err
		}
		if lease.Binding() != binding {
			return ErrOwnership
		}
		if err := lease.CheckCurrent(ctx); err != nil {
			return errors.Join(ErrOwnership, err)
		}
		return nil
	}
	if err = check(); err != nil {
		return nil, err
	}
	db := storage.AnyStore()
	if db == nil {
		return nil, ErrOwnership
	}
	tx, err := db.ReadTx(ctx)
	if err != nil {
		return nil, err
	}
	if tx == nil {
		return nil, ErrIncompleteScan
	}
	defer func() {
		err = errors.Join(err, tx.Commit(), check())
		if err != nil {
			w = nil
		}
	}()
	txctx := tx.Context()
	if txctx == nil || tx.Done() {
		return nil, ErrIncompleteScan
	}
	names, err := db.GetCollectionNames(txctx)
	if err != nil {
		return nil, err
	}
	if len(names) == 0 {
		return nil, ErrIncompleteScan
	}
	if len(names) > limits.MaxCollections {
		return nil, ErrLimit
	}
	names = append([]string(nil), names...)
	sort.Strings(names)
	w = &Witness{binding: binding}
	for i, name := range names {
		if len(name) == 0 || len(name) > 4096 || (i > 0 && name == names[i-1]) {
			return nil, ErrIncompleteScan
		}
		if err = check(); err != nil {
			return nil, err
		}
		c, openErr := db.OpenCollection(txctx, name)
		if openErr != nil {
			return nil, openErr
		}
		count, countErr := c.Find(nil).Count(txctx)
		if countErr != nil {
			return nil, countErr
		}
		if count < 0 || count > limits.MaxRows-w.rows {
			return nil, ErrLimit
		}
		col, scanErr := scan(ctx, txctx, c, name, count, limits, limits.MaxRows-w.rows, limits.MaxTotalBytes-w.valueBytes, check)
		if scanErr != nil {
			return nil, scanErr
		}
		w.rows += len(col.rows)
		w.valueBytes += col.bytes
		w.collections = append(w.collections, col)
	}
	if err = w.bindState(); err != nil {
		return nil, err
	}
	if err = check(); err != nil {
		return nil, err
	}
	h := sha256.New()
	if err = w.writePrivate(h); err != nil {
		return nil, err
	}
	w.digest = hex.EncodeToString(h.Sum(nil))
	return w, nil
}

func scan(ctx, txctx context.Context, c anystore.Collection, name string, expected int, limits Limits, remainingRows int, remainingBytes int64, check func() error) (out collection, err error) {
	out.name = name
	iter, err := c.Find(nil).Iter(txctx)
	if err != nil {
		return out, err
	}
	if iter == nil {
		return out, ErrIncompleteScan
	}
	defer func() { err = errors.Join(err, iter.Close()) }()
	ids := map[string]bool{}
	for iter.Next() {
		if err = check(); err != nil {
			return out, err
		}
		if len(out.rows) >= remainingRows {
			return out, ErrLimit
		}
		doc, docErr := iter.Doc()
		if docErr != nil {
			return out, docErr
		}
		if doc == nil {
			return out, ErrUnsupportedValue
		}
		value := doc.Value()
		id, idErr := uniqueField(value, "id")
		if idErr != nil {
			return out, idErr
		}
		raw, encodeErr := detachValue(ctx, value, limits)
		if encodeErr != nil {
			return out, encodeErr
		}
		rawID, encodeErr := detachValue(ctx, id, limits)
		if encodeErr != nil {
			return out, encodeErr
		}
		if out.bytes+int64(len(raw)) > remainingBytes {
			return out, ErrLimit
		}
		if ids[string(rawID)] {
			return out, ErrIncompleteScan
		}
		ids[string(rawID)] = true
		out.rows = append(out.rows, row{id: rawID, value: raw})
		out.bytes += int64(len(raw))
	}
	if err = iter.Err(); err != nil {
		return out, err
	}
	if err = check(); err != nil {
		return out, err
	}
	if len(out.rows) != expected {
		return out, ErrIncompleteScan
	}
	sort.Slice(out.rows, func(i, j int) bool { return bytes.Compare(out.rows[i].id, out.rows[j].id) < 0 })
	return out, nil
}

func (w *Witness) collection(name string) *collection {
	for i := range w.collections {
		if w.collections[i].name == name {
			return &w.collections[i]
		}
	}
	return nil
}
func (c *collection) stringID(id string) (*anyenc.Value, error) {
	if c == nil {
		return nil, ErrIncompleteBinding
	}
	var a anyenc.Arena
	encoded := a.NewString(id).MarshalTo(nil)
	for _, r := range c.rows {
		if bytes.Equal(r.id, encoded) {
			return anyenc.Parse(r.value)
		}
	}
	return nil, ErrIncompleteBinding
}
func requiredString(v *anyenc.Value, key string) (string, error) {
	f, err := uniqueField(v, key)
	if err != nil {
		return "", ErrIncompleteBinding
	}
	raw, err := f.StringBytes()
	if err != nil || len(raw) == 0 {
		return "", ErrIncompleteBinding
	}
	return string(raw), nil
}

func (w *Witness) bindState() error {
	state := w.collection("state")
	if state == nil || len(state.rows) != 1 {
		return ErrIncompleteBinding
	}
	v, err := state.stringID(w.binding.SpaceID)
	if err != nil {
		return ErrIncompleteBinding
	}
	header, err := uniqueField(v, "e")
	if err != nil {
		return ErrIncompleteBinding
	}
	raw, err := header.Bytes()
	if err != nil || len(raw) == 0 {
		return ErrIncompleteBinding
	}
	w.headerDigest = sum(raw)
	acl, err := requiredString(v, "a")
	if err != nil {
		return err
	}
	settings, err := requiredString(v, "s")
	if err != nil {
		return err
	}
	if acl == settings || acl == w.binding.SpaceID {
		return ErrIncompleteBinding
	}
	if _, err = w.collection("heads").stringID(acl); err != nil {
		return ErrIncompleteBinding
	}
	if _, err = w.collection("heads").stringID(settings); err != nil {
		return ErrIncompleteBinding
	}
	if _, err = w.collection(acl).stringID(acl); err != nil {
		return ErrIncompleteBinding
	}
	root, err := w.collection("changes").stringID(settings)
	if err != nil {
		return ErrIncompleteBinding
	}
	tree, err := requiredString(root, "t")
	if err != nil || tree != settings {
		return ErrIncompleteBinding
	}
	for i := range w.collections {
		switch w.collections[i].name {
		case "state", "heads", "changes", "_client", acl:
		default:
			w.collections[i].unresolved = true
		}
	}
	return nil
}

func (w *Witness) String() string {
	if w == nil {
		return "LocalStoreWitness{nil}"
	}
	return fmt.Sprintf("LocalStoreWitness{collections:%d rows:%d sha256:%s}", len(w.collections), w.rows, w.digest)
}
