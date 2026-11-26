package torahops

import (
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"testing"

	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/stretchr/testify/require"
)

type cutoverProjectionFixture struct {
	plan      cutover.Plan
	begin     cutover.Claim
	current   CutoverLegacyValue
	history   CutoverHistory
	originals []Claim
	receipts  map[string][]Receipt
	next      uint
}

func newCutoverProjectionFixture(t *testing.T) *cutoverProjectionFixture {
	t.Helper()
	data, err := os.ReadFile(os.Getenv("PINKHA_CUTOVER_VECTORS"))
	require.NoError(t, err)
	require.Less(t, len(data), 2*1024*1024)
	var vectors []struct {
		Name     string `json:"name"`
		WireData string `json:"wire"`
	}
	require.NoError(t, json.Unmarshal(data, &vectors))
	var plan cutover.Plan
	found := false
	for _, v := range vectors {
		if v.Name == "document-unknown" {
			raw, e := base64.StdEncoding.DecodeString(v.WireData)
			require.NoError(t, e)
			require.NoError(t, json.Unmarshal(raw, &plan))
			found = true
		}
	}
	require.True(t, found)
	require.NoError(t, cutover.ValidateSourceCoverage(plan))
	planID, err := plan.ID()
	require.NoError(t, err)
	begin, _, err := cutover.Encode(cutover.Record{Version: cutover.Version, SpaceID: plan.SpaceID, ObjectID: plan.ObjectID,
		RecordID: fmt.Sprintf("%032x", 1), AuthorID: "component-author-a", Kind: cutover.Begin, PlanID: planID, Plan: &plan, SourceHeads: []string{"component-native-head"}})
	require.NoError(t, err)
	return &cutoverProjectionFixture{plan: plan, begin: begin, current: CutoverLegacyValue{Key: plan.PropertyKey, Present: plan.ValuePresent, Bytes: plan.LegacyValue},
		history: CutoverHistory{Claims: []cutover.Claim{begin}}, receipts: map[string][]Receipt{}, next: 2}
}
func (f *cutoverProjectionFixture) record(t *testing.T, r cutover.Record) cutover.Claim {
	t.Helper()
	r.Version = cutover.Version
	r.SpaceID = f.plan.SpaceID
	r.ObjectID = f.plan.ObjectID
	r.RecordID = fmt.Sprintf("%032x", f.next)
	f.next++
	if r.AuthorID == "" {
		r.AuthorID = "component-author-a"
	}
	r.PlanID = f.begin.Record.PlanID
	claim, _, err := cutover.Encode(r)
	require.NoError(t, err)
	f.history.Claims = append(f.history.Claims, claim)
	return claim
}
func (f *cutoverProjectionFixture) importFact(t *testing.T, fact cutover.Fact, author string, metadata bool) Claim {
	t.Helper()
	factID, err := fact.ID(f.plan.SpaceID, f.plan.ObjectID)
	require.NoError(t, err)
	operationID, err := cutover.ImportOperationID(f.begin.Record.PlanID, factID, author)
	require.NoError(t, err)
	op := Operation{Version: Version, SpaceID: f.plan.SpaceID, OperationID: operationID, AuthorID: author, Kind: Add,
		Target: Target{ObjectID: f.plan.ObjectID, BlockID: fact.BlockID}, Source: Source{ProviderID: fact.ProviderID, CanonicalRef: fact.CanonicalRef}, Payload: fact.Payload}
	claim, _, err := makeClaim(op)
	require.NoError(t, err)
	f.originals = append(f.originals, claim)
	receipt := Receipt{ID: "component-only-not-native-authority", ClaimID: claim.ID, ChangeID: "component-change-" + claim.ID, Creator: author, ACLHeadID: "component-acl"}
	f.receipts[claim.ID] = []Receipt{receipt}
	if metadata {
		f.record(t, cutover.Record{AuthorID: author, Kind: cutover.Import, FactID: factID, ImportClaimID: claim.ID,
			NativeChanges: []cutover.NativeWitness{{ChangeID: receipt.ChangeID, Creator: author, ACLHeadID: receipt.ACLHeadID}}})
	}
	return claim
}
func (f *cutoverProjectionFixture) state(t *testing.T) CutoverState {
	t.Helper()
	state, err := projectCutover(f.history, f.originals, f.receipts, f.current)
	require.NoError(t, err)
	return state
}
func (f *cutoverProjectionFixture) seal(t *testing.T) cutover.Claim {
	t.Helper()
	state := f.state(t)
	record := cutover.Record{Kind: cutover.Seal, PlanID: f.begin.Record.PlanID}
	for _, entry := range state.Imports {
		record.Imported = append(record.Imported, cutover.Binding{FactID: entry.FactID, ClaimID: entry.ClaimID})
		record.ImportRecords = append(record.ImportRecords, entry.MetadataClaims...)
	}
	require.NoError(t, requireCompleteSeal(state, record))
	return f.record(t, record)
}
func TestCutoverProjectionRequiresAllSourceFactsAndSecondPhase(t *testing.T) {
	f := newCutoverProjectionFixture(t)
	state := f.state(t)
	require.Equal(t, CutoverPending, state.Status)
	require.NotEmpty(t, state.Pending)
	require.ErrorIs(t, requireCompleteSeal(state, cutover.Record{Kind: cutover.Seal, PlanID: state.PlanID}), cutover.ErrIncomplete)
	for _, fact := range f.plan.Facts {
		f.importFact(t, fact, "component-author-a", false)
	}
	state = f.state(t)
	require.Equal(t, CutoverPending, state.Status)
	require.NotEmpty(t, state.Pending)
	for _, entry := range state.Imports {
		r := f.receipts[entry.ClaimID][0]
		f.record(t, cutover.Record{Kind: cutover.Import, FactID: entry.FactID, ImportClaimID: entry.ClaimID, NativeChanges: []cutover.NativeWitness{{ChangeID: r.ChangeID, Creator: r.Creator, ACLHeadID: r.ACLHeadID}}})
	}
	f.seal(t)
	require.Equal(t, CutoverSealed, f.state(t).Status)
}
func TestCutoverProjectionTwoAuthorsRetainEveryPhysicalBinding(t *testing.T) {
	f := newCutoverProjectionFixture(t)
	for _, fact := range f.plan.Facts {
		a := f.importFact(t, fact, "component-author-a", true)
		b := f.importFact(t, fact, "component-author-b", true)
		require.NotEqual(t, a.ID, b.ID)
	}
	state := f.state(t)
	require.Len(t, state.Imports, len(f.plan.Facts)*2)
	require.Empty(t, state.Conflicts)
	first := f.seal(t)
	second := f.seal(t)
	require.NotEqual(t, first.ID, second.ID)
	require.Equal(t, CutoverSealed, f.state(t).Status)
	incomplete := first.Record
	incomplete.Imported = incomplete.Imported[1:]
	require.ErrorIs(t, requireCompleteSeal(f.state(t), incomplete), cutover.ErrIncomplete)
}
func TestCutoverProjectionDurableSealSurvivesUnlinkWithoutLegacyResurrection(t *testing.T) {
	f := newCutoverProjectionFixture(t)
	var observed []string
	for _, fact := range f.plan.Facts {
		claim := f.importFact(t, fact, "component-author-a", true)
		observed = append(observed, claim.ID)
	}
	f.seal(t)
	// This vector has exactly one document-level fact. The actual v1 tombstone
	// remains in history; it does not erase the independent metadata seal.
	require.Len(t, observed, 1)
	tombstone, _, err := makeClaim(Operation{Version: Version, SpaceID: f.plan.SpaceID, OperationID: fmt.Sprintf("%032x", 500), AuthorID: "component-author-a",
		Kind: Remove, Target: f.originals[0].Operation.Target, Observed: observed})
	require.NoError(t, err)
	f.originals = append(f.originals, tombstone)
	state := f.state(t)
	require.Equal(t, CutoverSealed, state.Status)
	require.Len(t, state.Seals, 1)
	require.Empty(t, state.Pending)
	require.Equal(t, f.plan.LegacyValue, f.current.Bytes)
}
func TestCutoverProjectionLateOfflineImportAfterRemovalIsVisibleConflict(t *testing.T) {
	f := newCutoverProjectionFixture(t)
	claim := f.importFact(t, f.plan.Facts[0], "component-author-a", true)
	f.seal(t)
	tombstone, _, err := makeClaim(Operation{Version: Version, SpaceID: f.plan.SpaceID, OperationID: fmt.Sprintf("%032x", 501), AuthorID: "component-author-a",
		Kind: Remove, Target: claim.Operation.Target, Observed: []string{claim.ID}})
	require.NoError(t, err)
	f.originals = append(f.originals, tombstone)
	f.importFact(t, f.plan.Facts[0], "component-author-b", true)
	state := f.state(t)
	require.Equal(t, CutoverConflicted, state.Status)
	require.Contains(t, state.Conflicts, CutoverIssue{Reason: "lateImportAfterObservedRemoval", Reference: state.Imports[0].FactID})
	require.ErrorIs(t, requireCompleteSeal(state, cutover.Record{Kind: cutover.Seal, PlanID: state.PlanID}), cutover.ErrConflict)
}
func TestCutoverProjectionOlderWriterDivergenceDoesNotUnionOrDelete(t *testing.T) {
	f := newCutoverProjectionFixture(t)
	for _, fact := range f.plan.Facts {
		f.importFact(t, fact, "component-author-a", true)
	}
	f.seal(t)
	original := append([]byte{}, f.current.Bytes...)
	f.current.Bytes = append(f.current.Bytes, ' ')
	state := f.state(t)
	require.Equal(t, CutoverDiverged, state.Status)
	require.Equal(t, original, state.Plan.LegacyValue)
	require.ErrorIs(t, requireCompleteSeal(state, cutover.Record{Kind: cutover.Seal, PlanID: state.PlanID}), cutover.ErrLegacyChanged)
}
func TestCutoverProjectionInvalidNativeReceiptCannotSeal(t *testing.T) {
	f := newCutoverProjectionFixture(t)
	claim := f.importFact(t, f.plan.Facts[0], "component-author-a", true)
	f.receipts[claim.ID][0].Creator = "different-native-author"
	state := f.state(t)
	require.Equal(t, CutoverConflicted, state.Status)
	require.NotEmpty(t, state.Conflicts)
	require.ErrorIs(t, requireCompleteSeal(state, cutover.Record{Kind: cutover.Seal, PlanID: state.PlanID}), cutover.ErrConflict)
}
func TestCutoverProjectionSameAuthorChangedRetryIsExplicitConflict(t *testing.T) {
	f := newCutoverProjectionFixture(t)
	claim := f.importFact(t, f.plan.Facts[0], "component-author-a", true)
	op := claim.Operation
	op.Payload = append(append([]byte{}, op.Payload...), '\n')
	variant, _, err := makeClaim(op)
	require.NoError(t, err)
	f.originals = append(f.originals, variant)
	state := f.state(t)
	require.Equal(t, CutoverConflicted, state.Status)
	require.Contains(t, state.Conflicts, CutoverIssue{Reason: "originalOperationCollision", Reference: op.OperationID})
}
func TestCutoverOriginalWriteGateRequiresSealAndRealObservedHistory(t *testing.T) {
	f := newCutoverProjectionFixture(t)
	op := Operation{Version: Version, SpaceID: f.plan.SpaceID, OperationID: fmt.Sprintf("%032x", 700),
		AuthorID: "component-author-a", Kind: Add, Target: Target{ObjectID: f.plan.ObjectID}, Source: Source{ProviderID: "other", CanonicalRef: "ref"}, Payload: []byte("new explicit content")}
	s := CutoverNativeSnapshot{State: f.state(t), OriginalClaims: f.originals}
	require.ErrorIs(t, validateCutoverOriginalAppend(s, f.begin.Record.PlanID, "", op, false), cutover.ErrIncomplete)
	claim := f.importFact(t, f.plan.Facts[0], "component-author-a", true)
	f.seal(t)
	s.State = f.state(t)
	s.OriginalClaims = f.originals
	require.NoError(t, validateCutoverOriginalAppend(s, f.begin.Record.PlanID, "", op, false))
	factID, err := f.plan.Facts[0].ID(f.plan.SpaceID, f.plan.ObjectID)
	require.NoError(t, err)
	require.ErrorIs(t, validateCutoverOriginalAppend(s, f.begin.Record.PlanID, factID, claim.Operation, true), cutover.ErrAlreadySealed)
	op.Kind = Remove
	op.Source = Source{}
	op.Payload = nil
	op.Observed = []string{"unknown"}
	require.True(t, errors.Is(validateCutoverOriginalAppend(s, f.begin.Record.PlanID, "", op, false), cutover.ErrIncomplete))
	op.Observed = []string{claim.ID}
	require.NoError(t, validateCutoverOriginalAppend(s, f.begin.Record.PlanID, "", op, false))
}
