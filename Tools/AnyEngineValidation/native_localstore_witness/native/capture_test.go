//go:build pinkha_localstore_witness

package localstorewitness

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"math"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/anyproto/any-store/anyenc"
)

func assertRefused(t *testing.T, w *Witness, err error, want error) {
	t.Helper()
	if w != nil || err == nil || (want != nil && !errors.Is(err, want)) {
		t.Fatalf("capture refusal mismatch: witness_present=%v error=%v", w != nil, err)
	}
}
func savePrivate(t *testing.T, root, name string, w *Witness) {
	t.Helper()
	f, err := os.OpenFile(filepath.Join(root, name), os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	must(t, err)
	writeErr := w.WritePrivate(f)
	syncErr := f.Sync()
	closeErr := f.Close()
	must(t, errors.Join(writeErr, syncErr, closeErr))
	r, err := w.Receipt()
	must(t, err)
	body, err := json.Marshal(r)
	must(t, err)
	t.Log("WITNESS_SAFE_RECEIPT " + string(body))
}

func TestLocalStoreWitnessNativeConcurrentTransaction(t *testing.T) {
	f := newFixture(t)
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	start := make(chan struct{})
	done := make(chan error, 1)
	finished := make(chan struct{})
	defer func() {
		cancel()
		select {
		case <-finished:
		case <-time.After(5 * time.Second):
			t.Error("owned writer failed to finish")
		}
	}()
	go func() {
		defer close(finished)
		select {
		case <-start:
		case <-ctx.Done():
			done <- ctx.Err()
			return
		}
		tx, err := f.db.WriteTx(ctx)
		if err != nil {
			done <- err
			return
		}
		work := func() error {
			if err := f.storage.StateStorage().SetHash(tx.Context(), "after"); err != nil {
				return err
			}
			c, err := f.db.OpenCollection(tx.Context(), probeCollection)
			if err != nil {
				return err
			}
			if err = c.UpdateOne(tx.Context(), probe("a", []byte{4, 5, 6, 255})); err != nil {
				return err
			}
			if err = c.Insert(tx.Context(), probe("c", []byte{7, 0, 7})); err != nil {
				return err
			}
			added, err := f.db.CreateCollection(tx.Context(), "witness-created-after-first-read")
			if err != nil {
				return err
			}
			return added.Insert(tx.Context(), probe("new", []byte{33, 0, 44}))
		}
		if err = work(); err != nil {
			done <- errors.Join(err, tx.Rollback())
			return
		}
		done <- tx.Commit()
	}()
	audit := &auditDB{DB: f.db}
	audit.afterInventory = func(context.Context) error {
		close(start)
		select {
		case err := <-done:
			return err
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	w, err := Capture(ctx, f.capability(audit), DefaultLimits())
	must(t, err)
	if audit.txCalls != 1 || audit.inventories != 1 || audit.badContext ||
		audit.opens != len(w.collections) || audit.counts != len(w.collections) ||
		audit.iterators != len(w.collections) || audit.iteratorCloses != len(w.collections) || audit.txCloses != 1 {
		t.Fatalf("native transaction/context coverage mismatch: tx=%d inventory=%d opens=%d counts=%d iterators=%d closes=%d tx_closes=%d bad_context=%v", audit.txCalls, audit.inventories, audit.opens, audit.counts, audit.iterators, audit.iteratorCloses, audit.txCloses, audit.badContext)
	}
	state, err := w.collection("state").stringID(f.storage.Id())
	must(t, err)
	if state.GetString("nh") != "before" {
		t.Fatal("capture crossed native transaction state")
	}
	if w.collection("witness-created-after-first-read") != nil || len(w.collection(probeCollection).rows) != 2 {
		t.Fatal("capture crossed native collection inventory or row boundary")
	}
	a, err := w.collection(probeCollection).stringID("a")
	must(t, err)
	b, err := w.collection(probeCollection).stringID("b")
	must(t, err)
	if !bytes.Equal(a.GetBytes("payload"), []byte{0, 1, 2, 255}) || !bytes.Equal(b.GetBytes("payload"), []byte{9, 0, 8, 255}) {
		t.Fatal("iterator-backed values were not detached")
	}
	live, err := f.storage.StateStorage().GetState(ctx)
	must(t, err)
	if live.NewHash != "after" {
		t.Fatal("independent native writer did not commit")
	}
	later, err := Capture(ctx, f.capability(nil), DefaultLimits())
	must(t, err)
	if later.collection("witness-created-after-first-read") == nil || len(later.collection(probeCollection).rows) != 3 {
		t.Fatal("later transaction did not see committed native inventory")
	}
	laterState, err := later.collection("state").stringID(f.storage.Id())
	must(t, err)
	if laterState.GetString("nh") != "after" || later.digest == w.digest {
		t.Fatal("later native witness did not advance")
	}
	r, err := w.Receipt()
	must(t, err)
	if r.HasNativeSourceAdmission || r.PermitsDestinationWrites || !r.NativeIdentityCensusRequired || !r.NativeSnapshotProofRequired || !r.LocalDecodedRowsComplete {
		t.Fatal("migration scope overclaim")
	}
	if !w.collection(probeCollection).unresolved {
		t.Fatal("unknown collection was silently classified")
	}
	savePrivate(t, f.root, "first-transaction.private.bin", w)
	savePrivate(t, f.root, "later-transaction.private.bin", later)
	t.Logf("NATIVE_INTERLEAVING one_read_transaction=1 exact_context=1 writer_committed_after_inventory=1 later_transaction_sees_commit=1 iterator_detachment=1 collections=%d rows=%d later_collections=%d later_rows=%d", len(w.collections), w.rows, len(later.collections), later.rows)
}

func TestLocalStoreWitnessOwnershipAndCancellation(t *testing.T) {
	for _, mode := range []string{"retired-before", "retired-after-inventory", "wrong-space", "unsupported-authority", "cancel-after-inventory", "lease-close"} {
		t.Run(mode, func(t *testing.T) {
			f := newFixture(t)
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			audit := &auditDB{DB: f.db}
			cap := f.capability(audit)
			want := ErrOwnership
			switch mode {
			case "retired-before":
				f.owner.generation.Add(1)
			case "retired-after-inventory":
				audit.afterInventory = func(context.Context) error { f.owner.generation.Add(1); return nil }
			case "wrong-space":
				cap.binding.SpaceID = "wrong-owned-space"
			case "unsupported-authority":
				cap.binding.Authority = "production-not-admitted"
			case "cancel-after-inventory":
				audit.afterInventory = func(context.Context) error { cancel(); return nil }
				want = context.Canceled
			case "lease-close":
				cap.closeErr = injectedFailure
				want = injectedFailure
			}
			w, err := Capture(ctx, cap, DefaultLimits())
			assertRefused(t, w, err, want)
			if audit.iterators != audit.iteratorCloses {
				t.Fatal("iterator leaked on ownership/cancellation failure")
			}
		})
	}
}

func TestLocalStoreWitnessLimitsAndNativeBinding(t *testing.T) {
	for _, mode := range []string{"collections", "rows", "row-bytes", "total-bytes", "wrong-native-state", "missing-native-header"} {
		t.Run(mode, func(t *testing.T) {
			f := newFixture(t)
			limits := DefaultLimits()
			want := ErrLimit
			switch mode {
			case "collections":
				limits.MaxCollections = 1
			case "rows":
				limits.MaxRows = 1
			case "row-bytes":
				limits.MaxRowBytes = 1
			case "total-bytes":
				limits.MaxTotalBytes = 1
			case "wrong-native-state":
				c, err := f.db.OpenCollection(context.Background(), "state")
				must(t, err)
				a := &anyenc.Arena{}
				v := a.NewObject()
				v.Set("id", a.NewString("second-space"))
				must(t, c.Insert(context.Background(), v))
				want = ErrIncompleteBinding
			case "missing-native-header":
				c, err := f.db.OpenCollection(context.Background(), "state")
				must(t, err)
				doc, err := c.FindId(context.Background(), f.storage.Id())
				must(t, err)
				copy, err := anyenc.Parse(doc.Value().MarshalTo(nil))
				must(t, err)
				copy.Del("e")
				must(t, c.UpdateOne(context.Background(), copy))
				want = ErrIncompleteBinding
			}
			w, err := Capture(context.Background(), f.capability(nil), limits)
			assertRefused(t, w, err, want)
		})
	}
}

func TestLocalStoreWitnessIteratorAndTransactionFailures(t *testing.T) {
	for _, mode := range []string{"iterator-terminal", "iterator-close", "transaction-close"} {
		t.Run(mode, func(t *testing.T) {
			f := newFixture(t)
			audit := &auditDB{DB: f.db, mode: mode}
			w, err := Capture(context.Background(), f.capability(audit), DefaultLimits())
			assertRefused(t, w, err, injectedFailure)
			if audit.iterators != audit.iteratorCloses || audit.txCloses != 1 {
				t.Fatal("native resources were not closed after injected failure")
			}
		})
	}
}

func TestLocalStoreWitnessDecodedEncodingRoundTrip(t *testing.T) {
	ctx := context.Background()
	limits := DefaultLimits()
	a := &anyenc.Arena{}
	v := a.NewObject()
	v.Set("binary", a.NewBinary([]byte{0, 255, 65, 0}))
	v.Set("text", a.NewStringBytes([]byte{255, 65}))
	v.Set("negative-zero", a.NewNumberFloat64(math.Float64frombits(1<<63)))
	v.Set("nan", a.NewNumberFloat64(math.Float64frombits(0x7ff8000000000042)))
	v.Set("unicode", a.NewString("\u05e9\u05dc\u05d5\u05dd e\u0301 \u00e9"))
	arr := a.NewArray()
	arr.SetArrayItem(0, a.NewString("x"))
	arr.SetArrayItem(1, a.NewBinary([]byte("x")))
	v.Set("ordered", arr)
	encoded, err := detachValue(ctx, v, limits)
	must(t, err)
	again, err := anyenc.Parse(encoded)
	must(t, err)
	if !equalDecoded(v, again) {
		t.Fatal("decoded type/bit/byte/order mismatch")
	}
	a.Reset()
	if !bytes.Equal(again.GetBytes("binary"), []byte{0, 255, 65, 0}) {
		t.Fatal("encoded bytes retained arena storage")
	}

	// The native parser retains duplicate ordered entries. The capture codec
	// preserves them; required identity/binding fields reject ambiguous copies.
	duplicate := []byte{byte(anyenc.TypeObject), 'k', 0, byte(anyenc.TypeTrue), 'k', 0, byte(anyenc.TypeFalse), 0}
	dup, err := anyenc.Parse(duplicate)
	must(t, err)
	copy, err := detachValue(ctx, dup, limits)
	must(t, err)
	if !bytes.Equal(copy, duplicate) {
		t.Fatal("duplicate ordered entries lost")
	}

	unsupported := a.NewStringBytes([]byte{'a', 0, 'b'})
	if _, err = detachValue(ctx, unsupported, limits); !errors.Is(err, ErrUnsupportedValue) {
		t.Fatal("lossy native string encoding accepted")
	}
	deep := a.NewArray()
	at := deep
	for i := 0; i < limits.MaxDepth+1; i++ {
		child := a.NewArray()
		at.SetArrayItem(0, child)
		at = child
	}
	if _, err = detachValue(ctx, deep, limits); err == nil {
		t.Fatal("unbounded depth accepted")
	}
	nodeLimit := limits
	nodeLimit.MaxValueNodes = 1
	if _, err = detachValue(ctx, dup, nodeLimit); !errors.Is(err, ErrLimit) {
		t.Fatal("node limit not applied")
	}
}

type shortWriter struct{}

func (shortWriter) Write(p []byte) (int, error) { return len(p) - 1, nil }

func TestLocalStoreWitnessUnqualifiedAndPrivateOutput(t *testing.T) {
	var zero Witness
	if _, err := zero.Receipt(); !errors.Is(err, ErrIncompleteScan) {
		t.Fatal("zero witness produced complete receipt")
	}
	if err := zero.WritePrivate(io.Discard); !errors.Is(err, ErrIncompleteScan) {
		t.Fatal("zero witness emitted private payload")
	}
	f := newFixture(t)
	w, err := Capture(context.Background(), f.capability(nil), DefaultLimits())
	must(t, err)
	if err = w.WritePrivate(shortWriter{}); !errors.Is(err, io.ErrShortWrite) {
		t.Fatal("short private writer accepted")
	}
	r, err := w.Receipt()
	must(t, err)
	safe, err := json.Marshal(r)
	must(t, err)
	if bytes.Contains(safe, []byte(f.storage.Id())) || bytes.Contains(safe, []byte(probeCollection)) || bytes.Contains(safe, f.owner.nonce[:]) {
		t.Fatal("safe receipt leaked native identity")
	}
}
