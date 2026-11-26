package torahcutovercontract

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func planFixture() Plan {
	return Plan{Version: Version, SpaceID: "space", ObjectID: "object", PropertyKey: "native-property",
		ValuePresent: true, LegacyValue: []byte("{\"version\":2,\"records\":[]}"),
		Facts: []Fact{{ProviderID: "sefaria", CanonicalRef: "Genesis.1.1", Payload: []byte("{\"record\":\"first\"}")}}}
}
func recordFixture(kind Kind) Record {
	p := planFixture()
	id, _ := p.ID()
	fact, _ := p.Facts[0].ID(p.SpaceID, p.ObjectID)
	r := Record{Version: Version, SpaceID: p.SpaceID, ObjectID: p.ObjectID, RecordID: strings.Repeat("a", 32),
		AuthorID: "native-author", Kind: kind, PlanID: id}
	switch kind {
	case Begin:
		r.Plan = &p
		r.SourceHeads = []string{"native-target-head"}
	case Import:
		r.FactID = fact
		r.ImportClaimID = strings.Repeat("b", 64) + "/" + strings.Repeat("c", 64)
		r.NativeChanges = []NativeWitness{{ChangeID: "native-change", Creator: r.AuthorID, ACLHeadID: "native-acl"}}
	case Seal:
		r.Imported = []Binding{{FactID: fact, ClaimID: strings.Repeat("b", 64) + "/" + strings.Repeat("c", 64)}}
		r.ImportRecords = []string{strings.Repeat("1", 64) + "/" + strings.Repeat("2", 64)}
	}
	return r
}
func mustPlanID(t *testing.T, p Plan) string {
	t.Helper()
	id, e := p.ID()
	if e != nil {
		t.Fatal(e)
	}
	return id
}

func TestExactPropertyPresenceAndBytesArePartOfIdentity(t *testing.T) {
	absent := planFixture()
	absent.ValuePresent = false
	absent.LegacyValue = nil
	empty := absent
	empty.ValuePresent = true
	if mustPlanID(t, absent) == mustPlanID(t, empty) {
		t.Fatal("missing and empty collapsed")
	}
	p := planFixture()
	formatted := p
	formatted.LegacyValue = []byte("{ \"version\":2,\"records\":[] }")
	if mustPlanID(t, p) == mustPlanID(t, formatted) {
		t.Fatal("legacy bytes were normalized")
	}
	if p.MatchesProperty(false, p.LegacyValue) || p.MatchesProperty(true, formatted.LegacyValue) {
		t.Fatal("changed source admitted")
	}
	if !p.MatchesProperty(true, append([]byte{}, p.LegacyValue...)) {
		t.Fatal("exact original refused")
	}
}

func TestPlanIdentityDoesNotDependOnWriterOrFactOrder(t *testing.T) {
	p := planFixture()
	p.Facts = append(p.Facts, Fact{BlockID: "block", ProviderID: "sefaria", CanonicalRef: "Exodus.1.1", Payload: []byte("{\"record\":\"second\"}")})
	q := p
	q.Facts = []Fact{p.Facts[1], p.Facts[0]}
	if mustPlanID(t, p) != mustPlanID(t, q) {
		t.Fatal("plan depends on scheduling/order")
	}
	a := recordFixture(Begin)
	a.Plan = &p
	a.PlanID = mustPlanID(t, p)
	b := a
	b.AuthorID = "independent-writer"
	b.RecordID = strings.Repeat("d", 32)
	ca, wa, e := Encode(a)
	if e != nil {
		t.Fatal(e)
	}
	cb, wb, e := Encode(b)
	if e != nil {
		t.Fatal(e)
	}
	if ca.ID == cb.ID || bytes.Equal(wa, wb) || ca.Record.PlanID != cb.Record.PlanID {
		t.Fatal("writer provenance or shared plan identity lost")
	}
}

func TestRecordIdentityBindsAuthorTargetPlanAndImportSet(t *testing.T) {
	a := recordFixture(Seal)
	ca, _, e := Encode(a)
	if e != nil {
		t.Fatal(e)
	}
	mutations := []func(*Record){
		func(r *Record) { r.AuthorID = "other-author" },
		func(r *Record) { r.ObjectID = "other-object" },
		func(r *Record) { r.PlanID = strings.Repeat("d", 64) },
		func(r *Record) {
			r.Imported = []Binding{{FactID: r.Imported[0].FactID, ClaimID: strings.Repeat("e", 64) + "/" + strings.Repeat("f", 64)}}
		},
	}
	for _, m := range mutations {
		b := a
		b.Imported = append([]Binding{}, a.Imported...)
		m(&b)
		cb, _, e := Encode(b)
		if e != nil {
			t.Fatal(e)
		}
		if cb.ID == ca.ID || cb.Digest == ca.Digest {
			t.Fatal("changed immutable content retained identity")
		}
		if strings.Split(cb.ID, "/")[0] != strings.Split(ca.ID, "/")[0] {
			t.Fatal("logical collision was hidden")
		}
	}
}

func TestClosedCanonicalWireRefusesUnknownDuplicateAndWhitespace(t *testing.T) {
	c, wire, e := Encode(recordFixture(Begin))
	if e != nil {
		t.Fatal(e)
	}
	if _, e = Decode(c.ID, wire); e != nil {
		t.Fatal(e)
	}
	variants := [][]byte{
		append(append([]byte{}, wire...), byte(' ')),
		bytes.Replace(wire, []byte("{\"record\":"), []byte("{\"unknown\":1,\"record\":"), 1),
		bytes.Replace(wire, []byte("\"version\":1"), []byte("\"version\":1,\"version\":1"), 1),
		bytes.Replace(wire, []byte("\"native-author\""), []byte("\"another-native-author\""), 1),
	}
	for _, v := range variants {
		if _, e := Decode(c.ID, v); e == nil {
			t.Fatal("noncanonical or changed record accepted")
		}
	}
	if _, e := Decode(strings.Repeat("0", 64)+"/"+c.Digest, wire); e == nil {
		t.Fatal("foreign physical identity accepted")
	}
}

func TestEncodedClaimOwnsAllCallerSlices(t *testing.T) {
	r := recordFixture(Begin)
	c, wire, e := Encode(r)
	if e != nil {
		t.Fatal(e)
	}
	r.Plan.LegacyValue[0] = '!'
	r.Plan.Facts[0].Payload[0] = '!'
	r.Plan.Facts[0].ProviderID = "changed"
	again, encoded, e := Encode(c.Record)
	if e != nil {
		t.Fatal(e)
	}
	if again.ID != c.ID || !bytes.Equal(wire, encoded) {
		t.Fatal("claim aliases mutable request data")
	}
	s := recordFixture(Seal)
	claim, wire, e := Encode(s)
	if e != nil {
		t.Fatal(e)
	}
	s.Imported[0].ClaimID = strings.Repeat("d", 64) + "/" + strings.Repeat("e", 64)
	_, againWire, e := Encode(claim.Record)
	if e != nil || !bytes.Equal(wire, againWire) {
		t.Fatal("seal aliases request bindings")
	}
}

func TestMetadataKindsHaveDisjointClosedShapes(t *testing.T) {
	for _, kind := range []Kind{Begin, Import, Seal} {
		r := recordFixture(kind)
		if _, _, e := Encode(r); e != nil {
			t.Fatal(e)
		}
		switch kind {
		case Begin:
			r.FactID = strings.Repeat("f", 64)
		case Import:
			r.Plan = recordFixture(Begin).Plan
		case Seal:
			r.ImportClaimID = recordFixture(Import).ImportClaimID
		}
		if _, _, e := Encode(r); e == nil {
			t.Fatal("mixed metadata kind shape")
		}
	}
	r := recordFixture(Seal)
	r.Kind = "add"
	if _, _, e := Encode(r); e == nil {
		t.Fatal("source operation confused with cutover metadata")
	}
}

func TestBoundsAndDuplicateFactsRefuseWithoutTruncation(t *testing.T) {
	cases := []Plan{}
	p := planFixture()
	p.ValuePresent = false
	cases = append(cases, p)
	p = planFixture()
	p.LegacyValue = bytes.Repeat([]byte("x"), MaxLegacyBytes+1)
	cases = append(cases, p)
	p = planFixture()
	p.Facts = append(p.Facts, p.Facts[0])
	cases = append(cases, p)
	p = planFixture()
	p.PropertyKey = "native\x00property"
	cases = append(cases, p)
	p = planFixture()
	p.Facts[0].Payload = append([]byte("\""), bytes.Repeat([]byte("x"), MaxFactPayloadBytes)...)
	p.Facts[0].Payload = append(p.Facts[0].Payload, '"')
	cases = append(cases, p)
	p = planFixture()
	p.Facts[0].Payload = []byte("{invalid")
	cases = append(cases, p)
	for _, p := range cases {
		if _, e := p.CanonicalBytes(); e == nil {
			t.Fatal("invalid bounded plan accepted")
		}
	}
}

func TestSealPreservesEveryImportAndRefusesRepeatedClaimIdentity(t *testing.T) {
	a := recordFixture(Seal)
	a.Imported = append(a.Imported, Binding{FactID: a.Imported[0].FactID, ClaimID: strings.Repeat("d", 64) + "/" + strings.Repeat("e", 64)})
	b := a
	b.Imported = []Binding{a.Imported[1], a.Imported[0]}
	ca, wa, e := Encode(a)
	if e != nil {
		t.Fatal(e)
	}
	cb, wb, e := Encode(b)
	if e != nil {
		t.Fatal(e)
	}
	if ca.ID != cb.ID || !bytes.Equal(wa, wb) || len(ca.Record.Imported) != 2 {
		t.Fatal("set identity or complete import retention failed")
	}
	a.Imported = append(a.Imported, a.Imported[0])
	if _, _, e = Encode(a); e == nil {
		t.Fatal("duplicate import claim admitted")
	}
	a = recordFixture(Seal)
	a.Imported = append(a.Imported, Binding{FactID: strings.Repeat("f", 64), ClaimID: a.Imported[0].ClaimID})
	if _, _, e = Encode(a); e == nil {
		t.Fatal("one claim reassigned to another fact")
	}
}

func TestFactIdentityKeepsScopeAndOpaquePayloadExact(t *testing.T) {
	p := planFixture()
	f := p.Facts[0]
	a, e := f.ID(p.SpaceID, p.ObjectID)
	if e != nil {
		t.Fatal(e)
	}
	b, _ := f.ID("other-space", p.ObjectID)
	c, _ := f.ID(p.SpaceID, "other-object")
	g := f
	g.BlockID = "block"
	d, _ := g.ID(p.SpaceID, p.ObjectID)
	g = f
	g.Payload = []byte("{ \"record\":\"first\" }")
	eID, _ := g.ID(p.SpaceID, p.ObjectID)
	seen := map[string]bool{}
	for _, id := range []string{a, b, c, d, eID} {
		if seen[id] {
			t.Fatal("different fact collapsed")
		}
		seen[id] = true
	}
	// Native retains opaque source bytes; the shared Swift codec separately
	// validates complete canonical facts against the retained legacy property.
	if !json.Valid(g.Payload) {
		t.Fatal("fixture invalid")
	}
}

func TestBeginCannotRebindPlanScopeOrIdentity(t *testing.T) {
	for _, mutate := range []func(*Record){
		func(r *Record) { r.SpaceID = "foreign" }, func(r *Record) { r.ObjectID = "foreign" },
		func(r *Record) { r.PlanID = strings.Repeat("0", 64) }, func(r *Record) { r.Version = 2 },
	} {
		r := recordFixture(Begin)
		mutate(&r)
		if _, _, e := Encode(r); e == nil {
			t.Fatal("foreign begin plan admitted")
		}
	}
}

func TestSourceHeadsBindSignedBeginButNotDeterministicPlan(t *testing.T) {
	a := recordFixture(Begin)
	b := a
	b.SourceHeads = []string{"other-native-target-head"}
	ca, _, err := Encode(a)
	if err != nil {
		t.Fatal(err)
	}
	cb, _, err := Encode(b)
	if err != nil {
		t.Fatal(err)
	}
	if ca.ID == cb.ID || ca.Record.PlanID != cb.Record.PlanID {
		t.Fatal("native witness or stable source plan lost")
	}
	a.SourceHeads = []string{"head-b", "head-a"}
	b.SourceHeads = []string{"head-a", "head-b"}
	ca, wa, err := Encode(a)
	if err != nil {
		t.Fatal(err)
	}
	cb, wb, err := Encode(b)
	if err != nil || ca.ID != cb.ID || !bytes.Equal(wa, wb) {
		t.Fatal("head set not canonical")
	}
	a.SourceHeads = nil
	if _, _, err := Encode(a); err == nil {
		t.Fatal("missing source head witness accepted")
	}
	a.SourceHeads = []string{"same", "same"}
	if _, _, err := Encode(a); err == nil {
		t.Fatal("duplicate source head accepted")
	}
}

func TestImportRetainsIndependentNativeAuthorChangeAndACL(t *testing.T) {
	a := recordFixture(Import)
	a.NativeChanges[0].Creator = "original-native-author"
	ca, wa, err := Encode(a)
	if err != nil {
		t.Fatal(err)
	}
	if ca.Record.NativeChanges[0].Creator == ca.Record.AuthorID {
		t.Fatal("fixture must have independent metadata author")
	}
	mutations := []func(*NativeWitness){
		func(w *NativeWitness) { w.ChangeID = "other-change" },
		func(w *NativeWitness) { w.Creator = "other-native-author" },
		func(w *NativeWitness) { w.ACLHeadID = "other-acl-head" },
	}
	for _, mutate := range mutations {
		b := a
		b.NativeChanges = append([]NativeWitness{}, a.NativeChanges...)
		mutate(&b.NativeChanges[0])
		cb, wb, err := Encode(b)
		if err != nil {
			t.Fatal(err)
		}
		if ca.ID == cb.ID || bytes.Equal(wa, wb) {
			t.Fatal("source native provenance not immutable")
		}
	}
	a.NativeChanges = append(a.NativeChanges, a.NativeChanges[0])
	if _, _, err := Encode(a); err == nil {
		t.Fatal("duplicate native change accepted")
	}
}

func TestMetadataWitnessArraysAreOwnedAndKindBound(t *testing.T) {
	for _, kind := range []Kind{Begin, Import, Seal} {
		r := recordFixture(kind)
		c, wire, err := Encode(r)
		if err != nil {
			t.Fatal(err)
		}
		switch kind {
		case Begin:
			r.SourceHeads[0] = "changed"
		case Import:
			r.NativeChanges[0].Creator = "changed"
		case Seal:
			r.ImportRecords[0] = strings.Repeat("e", 64) + "/" + strings.Repeat("f", 64)
		}
		_, again, err := Encode(c.Record)
		if err != nil || !bytes.Equal(wire, again) {
			t.Fatal("mutable witness alias")
		}
	}
	r := recordFixture(Import)
	r.NativeChanges = nil
	if _, _, err := Encode(r); err == nil {
		t.Fatal("missing native receipt accepted")
	}
	r = recordFixture(Seal)
	r.SourceHeads = []string{"source-head"}
	if _, _, err := Encode(r); err == nil {
		t.Fatal("begin witness mixed into seal")
	}
	r = recordFixture(Begin)
	r.ImportRecords = recordFixture(Seal).ImportRecords
	if _, _, err := Encode(r); err == nil {
		t.Fatal("seal imports mixed into begin")
	}
}

func TestSealRetainsAllMetadataClaimsWithNoSilentDeduplication(t *testing.T) {
	a := recordFixture(Seal)
	a.ImportRecords = append(a.ImportRecords, strings.Repeat("d", 64)+"/"+strings.Repeat("e", 64))
	b := a
	b.ImportRecords = []string{a.ImportRecords[1], a.ImportRecords[0]}
	ca, wa, err := Encode(a)
	if err != nil {
		t.Fatal(err)
	}
	cb, wb, err := Encode(b)
	if err != nil {
		t.Fatal(err)
	}
	if ca.ID != cb.ID || !bytes.Equal(wa, wb) || len(ca.Record.ImportRecords) != 2 {
		t.Fatal("metadata provenance lost")
	}
	a.ImportRecords = append(a.ImportRecords, a.ImportRecords[0])
	if _, _, err := Encode(a); err == nil {
		t.Fatal("duplicate metadata claim silently deduplicated")
	}
	a = recordFixture(Seal)
	a.ImportRecords = nil
	if _, _, err := Encode(a); err == nil {
		t.Fatal("bindings without metadata evidence accepted")
	}
	a = recordFixture(Seal)
	a.Imported = nil
	if _, _, err := Encode(a); err == nil {
		t.Fatal("metadata without import bindings accepted")
	}
}

func TestImportOperationIdentitySeparatesActualNativeAuthors(t *testing.T) {
	p := planFixture()
	pid := mustPlanID(t, p)
	fid, err := p.Facts[0].ID(p.SpaceID, p.ObjectID)
	if err != nil {
		t.Fatal(err)
	}
	a, err := ImportOperationID(pid, fid, "author-a")
	if err != nil {
		t.Fatal(err)
	}
	again, _ := ImportOperationID(pid, fid, "author-a")
	b, _ := ImportOperationID(pid, fid, "author-b")
	c, _ := ImportOperationID(strings.Repeat("a", 64), fid, "author-a")
	d, _ := ImportOperationID(pid, strings.Repeat("b", 64), "author-a")
	if a != again || !Hex(a, 16) {
		t.Fatal("stable import retry identity failed")
	}
	seen := map[string]bool{}
	for _, id := range []string{a, b, c, d} {
		if seen[id] {
			t.Fatal("different author or source conflated")
		}
		seen[id] = true
	}
	if _, err := ImportOperationID(pid, fid, ""); err == nil {
		t.Fatal("missing actual author accepted")
	}
}

func TestEmptyPlanCanSealOnlyWithoutPhantomImports(t *testing.T) {
	p := planFixture()
	p.Facts = nil
	r := recordFixture(Begin)
	r.Plan = &p
	r.PlanID = mustPlanID(t, p)
	if _, _, err := Encode(r); err != nil {
		t.Fatal(err)
	}
	seal := recordFixture(Seal)
	seal.PlanID = r.PlanID
	seal.Imported = nil
	seal.ImportRecords = nil
	if _, _, err := Encode(seal); err != nil {
		t.Fatal(err)
	}
	seal.ImportRecords = recordFixture(Seal).ImportRecords
	if _, _, err := Encode(seal); err == nil {
		t.Fatal("phantom import records accepted")
	}
}
