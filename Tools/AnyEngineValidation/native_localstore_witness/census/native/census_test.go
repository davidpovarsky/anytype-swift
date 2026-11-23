//go:build pinkha_localstore_witness

package localstorewitness

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"testing"

	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
)

func TestLocalTreeCensusNativeStorageRelationships(t *testing.T) {
	f := newFixture(t)
	alpha := newCensusNativeTree(t, f, "alpha", "")
	head := appendCensusNativeChange(t, alpha, "opaque signed storage change")
	beta := newCensusNativeTree(t, f, "beta", alpha.root.Id)
	queued, deleted := headstorage.DeletedStatusQueued, headstorage.DeletedStatusDeleted
	must(t, f.storage.HeadStorage().UpdateEntry(context.Background(), headstorage.HeadsUpdate{Id: alpha.root.Id, DeletedStatus: &queued}))
	must(t, f.storage.HeadStorage().UpdateEntry(context.Background(), headstorage.HeadsUpdate{Id: beta.root.Id, DeletedStatus: &deleted}))
	censusModify(t, f, "changes", alpha.root.Id, func(a *anyenc.Arena, v *anyenc.Value) {
		v.Set("future-census-field", a.NewBinary([]byte{0, 255, 1}))
	})
	active := map[string]bool{}
	must(t, f.storage.HeadStorage().IterateEntries(context.Background(), headstorage.IterOpts{}, func(entry headstorage.HeadsEntry) (bool, error) {
		active[entry.Id] = true
		return true, nil
	}))
	if active[alpha.root.Id] || active[beta.root.Id] {
		t.Fatal("native normal iterator unexpectedly included deleted registry rows")
	}
	w, c := censusCapture(t, f, nil)
	r, err := c.Receipt()
	must(t, err)
	if r.Rows != 12 || r.Collections != 5 || !r.AllCapturedRowsAccounted || r.ResolvedReferences != r.References {
		t.Fatal("real native structural inventory or reference resolution differs")
	}
	a := censusRowFor(t, c, "heads", alpha.root.Id)
	b := censusRowFor(t, c, "heads", beta.root.Id)
	if a.kind != "tree_head" || a.deleted != 1 || a.derived != 0 || b.deleted != 2 || b.derived != 1 {
		t.Fatal("deleted or derived native registry state was filtered or coerced")
	}
	if !censusReferenceOutcome(c, "head", head, "resolved_identity_only") ||
		!censusReferenceOutcome(c, "parent_tree", alpha.root.Id, "resolved_identity_only") ||
		censusIssueCount(c, "unknown_field") != 1 {
		t.Fatal("native head/parent or unknown source field was lost")
	}
	state, err := f.storage.StateStorage().GetState(context.Background())
	must(t, err)
	if censusRowFor(t, c, "heads", state.AclId).kind != "acl_head" ||
		censusRowFor(t, c, state.AclId, state.AclId).kind != "acl_root" ||
		censusRowFor(t, c, "changes", state.SettingsId).kind != "tree_root" {
		t.Fatal("Space ACL/settings storage domains were merged")
	}
	retainCensusPrivate(t, f, "native", w, c)
}

func TestLocalTreeCensusUsesCapturedCheckpointWithoutLiveReads(t *testing.T) {
	f := newFixture(t)
	tree := newCensusNativeTree(t, f, "checkpoint", "")
	oldHead := appendCensusNativeChange(t, tree, "before checkpoint")
	audit := &auditDB{DB: f.db}
	oldWitness, oldCensus := censusCapture(t, f, audit)
	readCounts := [5]int{audit.txCalls, audit.inventories, audit.opens, audit.counts, audit.iterators}
	oldAcquire := f.owner.acquired.Load()
	oldReceipt, err := oldCensus.Receipt()
	must(t, err)
	var original bytes.Buffer
	must(t, oldWitness.WritePrivate(&original))
	newHead := appendCensusNativeChange(t, tree, "after checkpoint")
	_, err = f.db.CreateCollection(context.Background(), "late-empty-census")
	must(t, err)
	repeated, err := oldWitness.LocalTreeCensus(context.Background(), DefaultCensusLimits())
	must(t, err)
	repeatedReceipt, err := repeated.Receipt()
	must(t, err)
	if readCounts != [5]int{audit.txCalls, audit.inventories, audit.opens, audit.counts, audit.iterators} ||
		oldAcquire != f.owner.acquired.Load() {
		t.Fatal("census reacquired authority or read a live database")
	}
	if oldReceipt.CensusSHA256 != repeatedReceipt.CensusSHA256 ||
		!censusReferenceOutcome(repeated, "head", oldHead, "resolved_identity_only") ||
		censusReferenceOutcome(repeated, "head", newHead, "resolved_identity_only") {
		t.Fatal("old captured census was replaced by a live storage view")
	}
	var after bytes.Buffer
	must(t, oldWitness.WritePrivate(&after))
	if !bytes.Equal(original.Bytes(), after.Bytes()) {
		t.Fatal("census changed its completed source witness")
	}
	newWitness, newCensus := censusCapture(t, f, nil)
	newReceipt, err := newCensus.Receipt()
	must(t, err)
	if newReceipt.SourceWitnessSHA256 == oldReceipt.SourceWitnessSHA256 ||
		newReceipt.CensusSHA256 == oldReceipt.CensusSHA256 ||
		newReceipt.Rows != oldReceipt.Rows+1 || newReceipt.Collections != oldReceipt.Collections+1 ||
		!censusReferenceOutcome(newCensus, "head", newHead, "resolved_identity_only") {
		t.Fatal("later native capture did not retain its own changed rows and inventory")
	}
	// Retirement cannot turn the historical captured report into current authority.
	f.owner.live.Store(false)
	f.owner.generation.Add(1)
	historical, err := oldCensus.Receipt()
	must(t, err)
	if historical.Generation != oldReceipt.Generation || historical.HasNativeSourceAdmission ||
		historical.PermitsDestinationWrites {
		t.Fatal("historical census minted a current generation or migration authority")
	}
	retainCensusPrivate(t, f, "captured-old", oldWitness, oldCensus)
	retainCensusPrivate(t, f, "captured-new", newWitness, newCensus)
}

func TestLocalTreeCensusRetainsUnknownRowsAndExactTypedIdentities(t *testing.T) {
	f := newFixture(t)
	ctx := context.Background()
	a := &anyenc.Arena{}
	names := []string{"census-\u00e9", "census-e\u0301", "empty-census"}
	first, err := f.db.CreateCollection(ctx, names[0])
	must(t, err)
	second, err := f.db.CreateCollection(ctx, names[1])
	must(t, err)
	_, err = f.db.CreateCollection(ctx, names[2])
	must(t, err)
	ids := []*anyenc.Value{a.NewString("1"), a.NewNumberInt(1), a.NewBinary([]byte("1")),
		a.NewString("\u00e9"), a.NewString("e\u0301")}
	expected := map[string]bool{}
	for _, id := range ids {
		v := a.NewObject()
		v.Set("id", id)
		v.Set("future", a.NewBinary([]byte{0, 255, 3}))
		v = censusDuplicateField(t, v, "future", a.NewString("retained duplicate"))
		expected[string(id.MarshalTo(nil))] = true
		must(t, first.Insert(ctx, v))
	}
	v := a.NewObject()
	v.Set("id", a.NewString("1"))
	v.Set("private", a.NewString("private-census-marker"))
	must(t, second.Insert(ctx, v))
	invalidHead := a.NewObject()
	invalidHead.Set("id", a.NewNumberInt(7))
	invalidHead.Set("h", a.NewArray())
	censusInsert(t, f, "heads", invalidHead)
	w, c := censusCapture(t, f, nil)
	r, err := c.Receipt()
	must(t, err)
	if r.Collections != 8 || r.Rows != 14 || r.EmptyCollections != 1 ||
		r.UnknownCollections != 4 || !r.AllCapturedRowsAccounted ||
		censusIssueCount(c, "unsupported_native_identity") != 1 {
		t.Fatal("unknown or invalid native row accounting differs")
	}
	actual := map[string]bool{}
	foundSecond, invalidTypedID := false, false
	for _, row := range c.rows {
		col := w.collections[row.collection]
		if !bytes.Equal(row.nativeID, col.rows[row.ordinal].id) {
			t.Fatal("census changed the exact typed native row identity")
		}
		if col.name == names[0] {
			if row.kind != "unknown_collection_row" || !row.unresolved {
				t.Fatal("opaque collection gained semantic interpretation")
			}
			actual[string(row.nativeID)] = true
		}
		if col.name == names[1] && bytes.Equal(row.nativeID, a.NewString("1").MarshalTo(nil)) {
			foundSecond = true
		}
		if col.name == "heads" && bytes.Equal(row.nativeID, a.NewNumberInt(7).MarshalTo(nil)) {
			invalidTypedID = row.kind == "unresolved_row" && len(row.id) == 0
		}
	}
	if len(actual) != len(expected) || !foundSecond || !invalidTypedID {
		t.Fatal("typed, Unicode, or collection-scoped identities were merged")
	}
	for id := range expected {
		if !actual[id] {
			t.Fatal("an exact original typed identity was dropped")
		}
	}
	retainCensusPrivate(t, f, "unknowns", w, c)
}

func TestLocalTreeCensusReportsMissingCrossTreeAndACLReferences(t *testing.T) {
	f := newFixture(t)
	ctx := context.Background()
	alpha := newCensusNativeTree(t, f, "refs-alpha", "")
	beta := newCensusNativeTree(t, f, "refs-beta", "")
	foreign := appendCensusNativeChange(t, beta, "other tree signed bytes")
	state, err := f.storage.StateStorage().GetState(ctx)
	must(t, err)
	// These writes are explicit negative storage fixtures, not authorized Object operations.
	censusModify(t, f, "heads", alpha.root.Id, func(a *anyenc.Arena, v *anyenc.Value) {
		heads := a.NewArray()
		heads.SetArrayItem(0, a.NewString(foreign))
		v.Set("h", heads)
		v.Set("s", a.NewString("census-absent-snapshot"))
		v.Set("p", a.NewString(state.AclId))
	})
	a := &anyenc.Arena{}
	orphan := a.NewObject()
	orphan.Set("id", a.NewString("census-orphan-change"))
	orphan.Set("t", a.NewString("census-missing-tree"))
	orphan.Set("r", a.NewBinary([]byte("negative fixture opaque bytes")))
	orphan.Set("o", a.NewString("census-order-1"))
	predecessors := a.NewArray()
	predecessors.SetArrayItem(0, a.NewString("census-absent-predecessor"))
	orphan.Set("p", predecessors)
	censusInsert(t, f, "changes", orphan)
	ambiguous := a.NewObject()
	ambiguous.Set("id", a.NewString("census-ambiguous-owner"))
	ambiguous.Set("t", a.NewString(alpha.root.Id))
	ambiguous.Set("r", a.NewBinary([]byte("negative fixture")))
	ambiguous.Set("o", a.NewString("census-order-2"))
	ambiguous = censusDuplicateField(t, ambiguous, "t", a.NewString(beta.root.Id))
	censusInsert(t, f, "changes", ambiguous)
	ghost := a.NewObject()
	ghost.Set("id", a.NewString("census-head-without-root"))
	heads := a.NewArray()
	heads.SetArrayItem(0, a.NewString("census-ambiguous-owner"))
	heads.SetArrayItem(1, a.NewString("census-absent-head"))
	heads.SetArrayItem(2, a.NewString("census-absent-head"))
	ghost.Set("h", heads)
	ghost.Set("d", a.NewNumberInt(9))
	ghost.Set("r", a.NewString("unknown"))
	censusInsert(t, f, "heads", ghost)
	w, c := censusCapture(t, f, nil)
	r, err := c.Receipt()
	must(t, err)
	if !r.AllCapturedRowsAccounted || r.Rows != w.rows || r.AllRecognizedReferencesResolved ||
		r.ResolvedReferences == r.References || r.UnresolvedRows < 4 {
		t.Fatal("unresolved native records were discarded or admitted")
	}
	for _, check := range []struct{ kind, id, outcome string }{
		{"head", foreign, "cross_tree"},
		{"common_snapshot", "census-absent-snapshot", "not_in_capture"},
		{"parent_tree", state.AclId, "wrong_namespace"},
		{"change_tree_head", "census-missing-tree", "not_in_capture"},
		{"predecessor", "census-absent-predecessor", "not_in_capture"},
		{"tree_root", "census-head-without-root", "not_in_capture"},
		{"head", "census-ambiguous-owner", "target_unresolved"},
	} {
		if !censusReferenceOutcome(c, check.kind, check.id, check.outcome) {
			t.Fatal("required unresolved reference classification missing")
		}
	}
	for _, code := range []string{"ambiguous_field", "unknown_deletion_state", "unsupported_derived_state", "duplicate_reference"} {
		if censusIssueCount(c, code) != 1 {
			t.Fatal("required malformed source issue count differs")
		}
	}
	if censusRowFor(t, c, "changes", "census-ambiguous-owner").kind != "unresolved_row" {
		t.Fatal("ambiguous tree identity was guessed")
	}
	for _, ref := range c.references {
		if ref.outcome != "resolved_identity_only" && ref.target != -1 {
			t.Fatal("unresolved reference gained a destination edge")
		}
	}
	retainCensusPrivate(t, f, "references", w, c)
}

func TestLocalTreeCensusQualificationLimitsAndPrivateReceipt(t *testing.T) {
	f := newFixture(t)
	_, err := f.db.CreateCollection(context.Background(), "empty-boundary-census")
	must(t, err)
	w, c := censusCapture(t, f, nil)
	ctx := context.Background()
	for _, source := range []*Witness{nil, new(Witness)} {
		if result, err := source.LocalTreeCensus(ctx, DefaultCensusLimits()); result != nil || !errors.Is(err, ErrIncompleteCensus) {
			t.Fatal("unqualified witness created a census")
		}
	}
	if result, err := w.LocalTreeCensus(nil, DefaultCensusLimits()); result != nil || !errors.Is(err, ErrIncompleteCensus) {
		t.Fatal("nil context returned a qualified census")
	}
	cancelled, cancel := context.WithCancel(ctx)
	cancel()
	if result, err := w.LocalTreeCensus(cancelled, DefaultCensusLimits()); result != nil || !errors.Is(err, context.Canceled) {
		t.Fatal("cancelled census returned a qualified value")
	}
	for _, change := range []func(*CensusLimits){
		func(l *CensusLimits) { l.MaxRows = 1 },
		func(l *CensusLimits) { l.MaxReferences = 1 },
		func(l *CensusLimits) { l.MaxIssues = 1 },
		func(l *CensusLimits) { l.MaxPrivateBytes = 1 },
		func(l *CensusLimits) { l.MaxRows = DefaultCensusLimits().MaxRows + 1 },
	} {
		limit := DefaultCensusLimits()
		change(&limit)
		if result, err := w.LocalTreeCensus(ctx, limit); result != nil || !errors.Is(err, ErrLimit) {
			t.Fatal("bounded census returned partial or unbounded qualification")
		}
	}
	var zero LocalTreeCensus
	if _, err := zero.Receipt(); !errors.Is(err, ErrIncompleteCensus) {
		t.Fatal("zero census returned a qualified receipt")
	}
	if err := zero.WritePrivate(io.Discard); !errors.Is(err, ErrIncompleteCensus) {
		t.Fatal("zero census emitted private source material")
	}
	if err := c.WritePrivate(censusShortWriter{}); !errors.Is(err, io.ErrShortWrite) {
		t.Fatal("private census ignored original short-write failure")
	}
	receipt, err := c.Receipt()
	must(t, err)
	if receipt.HasNativeSourceAdmission || receipt.PermitsDestinationWrites ||
		receipt.SemanticIdentityCensusComplete || !receipt.NativeSnapshotProofRequired ||
		!receipt.NativeIdentityCensusRequired || receipt.Authority != FixtureOnlyAuthority {
		t.Fatal("local structural census upgraded source or destination authority")
	}
	public, err := json.Marshal(receipt)
	must(t, err)
	for _, private := range [][]byte{[]byte(w.binding.SpaceID), w.binding.OwnerNonce[:],
		[]byte("empty-boundary-census"), []byte(probeCollection)} {
		if bytes.Contains(public, private) || bytes.Contains([]byte(fmt.Sprint(c)), private) {
			t.Fatal("public census summary exposed private source identity")
		}
	}
	retainCensusPrivate(t, f, "boundary", w, c)
}
