package torahops

import (
	"bytes"
	"fmt"
	"sort"

	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
)

type CutoverStatus string

const (
	CutoverLegacy     CutoverStatus = "legacy"
	CutoverPending    CutoverStatus = "pending"
	CutoverSealed     CutoverStatus = "sealed"
	CutoverDiverged   CutoverStatus = "diverged"
	CutoverConflicted CutoverStatus = "conflicted"
)

type CutoverIssue struct {
	Reason    string `json:"reason"`
	Reference string `json:"reference"`
}
type CutoverImport struct {
	FactID         string   `json:"factId"`
	ClaimID        string   `json:"claimId"`
	MetadataClaims []string `json:"metadataClaims"`
}
type CutoverState struct {
	Status    CutoverStatus   `json:"status"`
	PlanID    string          `json:"planId,omitempty"`
	Plan      *cutover.Plan   `json:"plan,omitempty"`
	Imports   []CutoverImport `json:"imports"`
	Seals     []string        `json:"seals"`
	Pending   []CutoverIssue  `json:"pending"`
	Conflicts []CutoverIssue  `json:"conflicts"`
}
type CutoverLegacyValue struct {
	Key     string
	Present bool
	Bytes   []byte
}

// projectCutover consumes only native-host-verified histories. Shape/receipt
// fields supplied by an RPC must never be passed to this internal function.
// No source or claims are written; multiple facts/claims are not coalesced here.
func projectCutover(history CutoverHistory, originals []Claim, receipts map[string][]Receipt,
	current CutoverLegacyValue) (state CutoverState, err error) {
	state = CutoverState{Status: CutoverLegacy, Imports: []CutoverImport{}, Seals: []string{}, Pending: []CutoverIssue{}, Conflicts: []CutoverIssue{}}
	if len(history.Claims) == 0 {
		return state, nil
	}
	state.Status = CutoverPending
	addConflict := func(reason, reference string) {
		state.Conflicts = append(state.Conflicts, CutoverIssue{reason, reference})
	}
	addPending := func(reason, reference string) { state.Pending = append(state.Pending, CutoverIssue{reason, reference}) }
	defer func() {
		sort.Slice(state.Imports, func(i, j int) bool {
			a, b := state.Imports[i], state.Imports[j]
			if a.FactID != b.FactID {
				return a.FactID < b.FactID
			}
			return a.ClaimID < b.ClaimID
		})
		for i := range state.Imports {
			sort.Strings(state.Imports[i].MetadataClaims)
		}
		sort.Strings(state.Seals)
		less := func(a, b CutoverIssue) bool {
			if a.Reason != b.Reason {
				return a.Reason < b.Reason
			}
			return a.Reference < b.Reference
		}
		sort.Slice(state.Pending, func(i, j int) bool { return less(state.Pending[i], state.Pending[j]) })
		sort.Slice(state.Conflicts, func(i, j int) bool { return less(state.Conflicts[i], state.Conflicts[j]) })
		if len(state.Conflicts) > 0 && state.Status != CutoverDiverged {
			state.Status = CutoverConflicted
		}
	}()
	for _, resolution := range history.Conflicts {
		addConflict("metadataRecordCollision", resolution.RecordID)
	}
	plans := map[string]cutover.Plan{}
	metadata := map[string]cutover.Claim{}
	for _, claim := range history.Claims {
		if _, duplicate := metadata[claim.ID]; duplicate {
			return state, cutover.ErrInvalid
		}
		metadata[claim.ID] = claim
		r := claim.Record
		if r.Kind != cutover.Begin {
			continue
		}
		if r.Plan == nil {
			return state, cutover.ErrInvalid
		}
		id, e := r.Plan.ID()
		if e != nil || id != r.PlanID {
			return state, cutover.ErrInvalid
		}
		if e = cutover.ValidateSourceCoverage(*r.Plan); e != nil {
			return state, e
		}
		if old, exists := plans[id]; exists {
			a, _ := old.CanonicalBytes()
			b, _ := r.Plan.CanonicalBytes()
			if !bytes.Equal(a, b) {
				return state, cutover.ErrConflict
			}
		}
		plans[id] = *r.Plan
	}
	if len(plans) != 1 {
		for id := range plans {
			addConflict("differentRetainedSourcePlan", id)
		}
		if len(plans) == 0 {
			addConflict("missingBegin", "")
		}
		state.Status = CutoverDiverged
		return state, nil
	}
	for id, plan := range plans {
		copy := plan
		state.PlanID = id
		state.Plan = &copy
	}
	plan := *state.Plan
	if current.Key != plan.PropertyKey || current.Present != plan.ValuePresent || !bytes.Equal(current.Bytes, plan.LegacyValue) {
		state.Status = CutoverDiverged
		addConflict("retainedLegacyPropertyChanged", plan.PropertyKey)
	}
	facts := map[string]cutover.Fact{}
	for _, fact := range plan.Facts {
		id, e := fact.ID(plan.SpaceID, plan.ObjectID)
		if e != nil {
			return state, e
		}
		facts[id] = fact
	}
	byID := map[string]Claim{}
	byOperation := map[string][]Claim{}
	for _, claim := range originals {
		if claim.Operation.SpaceID != plan.SpaceID || claim.Operation.Target.ObjectID != plan.ObjectID {
			return state, cutover.ErrInvalid
		}
		if _, exists := byID[claim.ID]; exists {
			return state, cutover.ErrInvalid
		}
		byID[claim.ID] = claim
		byOperation[claim.Operation.OperationID] = append(byOperation[claim.Operation.OperationID], claim)
	}
	eligible := map[string]Claim{}
	for operationID, variants := range byOperation {
		if len(variants) > 1 {
			addConflict("originalOperationCollision", operationID)
			continue
		}
		eligible[variants[0].ID] = variants[0]
	}
	removed := map[string]bool{}
	for _, claim := range eligible {
		for _, observed := range claim.Operation.Observed {
			old, exists := eligible[observed]
			if !exists || old.Operation.Target != claim.Operation.Target {
				addPending("originalObservedClaimUnavailable", observed)
			} else {
				removed[observed] = true
			}
		}
	}
	// Derive every genuine import from its actual v1 native author's operation
	// identity, even when its second metadata phase has not arrived yet.
	imports := map[string]*CutoverImport{}
	byFact := map[string][]string{}
	for _, claim := range originals {
		for factID, fact := range facts {
			operationID, e := cutover.ImportOperationID(state.PlanID, factID, claim.Operation.AuthorID)
			if e != nil {
				return state, e
			}
			if claim.Operation.OperationID != operationID {
				continue
			}
			op := claim.Operation
			if len(byOperation[op.OperationID]) != 1 || op.Kind != Add || len(op.Observed) != 0 ||
				op.Target != (Target{ObjectID: plan.ObjectID, BlockID: fact.BlockID}) || op.Source.ProviderID != fact.ProviderID ||
				op.Source.CanonicalRef != fact.CanonicalRef || !bytes.Equal(op.Payload, fact.Payload) {
				addConflict("differentPhysicalImport", claim.ID)
				continue
			}
			imports[claim.ID] = &CutoverImport{FactID: factID, ClaimID: claim.ID, MetadataClaims: []string{}}
			byFact[factID] = append(byFact[factID], claim.ID)
		}
	}
	importMetadata := map[string]cutover.Binding{}
	for _, claim := range history.Claims {
		r := claim.Record
		if r.PlanID != state.PlanID {
			addConflict("metadataNamesDifferentPlan", claim.ID)
			continue
		}
		if r.Kind != cutover.Import {
			continue
		}
		fact, exists := facts[r.FactID]
		if !exists {
			addConflict("unknownSourceFact", claim.ID)
			continue
		}
		_ = fact
		native, known := byID[r.ImportClaimID]
		if !known {
			addPending("v1ImportHistoryUnavailable", r.ImportClaimID)
			continue
		}
		binding, valid := imports[r.ImportClaimID]
		if !valid || binding.FactID != r.FactID {
			addConflict("metadataDoesNotNameExactNativeImport", claim.ID)
			continue
		}
		actual := receipts[native.ID]
		if len(actual) == 0 {
			addPending("v1ImportReceiptUnavailable", native.ID)
			continue
		}
		for _, witness := range r.NativeChanges {
			found := false
			for _, receipt := range actual {
				if receipt.ChangeID == witness.ChangeID && receipt.Creator == witness.Creator && receipt.ACLHeadID == witness.ACLHeadID &&
					receipt.ClaimID == native.ID && receipt.Creator == native.Operation.AuthorID {
					found = true
					break
				}
			}
			if !found {
				valid = false
				break
			}
		}
		if !valid {
			addConflict("importSignedReceiptMismatch", claim.ID)
			continue
		}
		binding.MetadataClaims = append(binding.MetadataClaims, claim.ID)
		importMetadata[claim.ID] = cutover.Binding{FactID: r.FactID, ClaimID: r.ImportClaimID}
	}
	for factID := range facts {
		group := byFact[factID]
		if len(group) == 0 {
			addPending("sourceFactNotImported", factID)
			continue
		}
		hasRemoved, hasLive := false, false
		for _, id := range group {
			hasRemoved = hasRemoved || removed[id]
			hasLive = hasLive || !removed[id]
			if len(imports[id].MetadataClaims) == 0 {
				addPending("importMetadataNotCommitted", id)
			}
		}
		// An offline writer that did not observe a removal may later publish a
		// canonically equal Add. It must not resurrect the removed fact silently.
		if hasRemoved && hasLive {
			addConflict("lateImportAfterObservedRemoval", factID)
		}
	}
	for _, claim := range history.Claims {
		r := claim.Record
		if r.Kind != cutover.Seal || r.PlanID != state.PlanID {
			continue
		}
		bindings := map[string]cutover.Binding{}
		valid := true
		for _, id := range r.ImportRecords {
			binding, exists := importMetadata[id]
			if !exists {
				if _, known := metadata[id]; known {
					addConflict("sealReferencesInvalidImport", claim.ID)
				} else {
					addConflict("sealReferencesMissingMetadata", claim.ID)
				}
				valid = false
				break
			}
			bindings[binding.ClaimID] = binding
		}
		if !valid {
			continue
		}
		if len(bindings) != len(r.Imported) {
			addConflict("sealBindingSetMismatch", claim.ID)
			continue
		}
		covered := map[string]bool{}
		for _, binding := range r.Imported {
			if actual, ok := bindings[binding.ClaimID]; !ok || actual != binding {
				valid = false
				break
			}
			covered[binding.FactID] = true
		}
		if !valid || len(covered) != len(facts) {
			addConflict("sealIncompleteSourceCoverage", claim.ID)
			continue
		}
		for factID := range facts {
			if !covered[factID] {
				valid = false
			}
		}
		if !valid {
			addConflict("sealIncompleteSourceCoverage", claim.ID)
			continue
		}
		state.Seals = append(state.Seals, claim.ID)
	}
	for _, entry := range imports {
		state.Imports = append(state.Imports, *entry)
	}
	if state.Status != CutoverDiverged && len(state.Conflicts) == 0 && len(state.Pending) == 0 && len(state.Seals) > 0 {
		state.Status = CutoverSealed
	}
	return state, nil
}

// requireCompleteSeal is the stricter local append fence: unlike a historical
// seal, a newly committed seal must include every import currently observed on
// both native trees. It makes no assertion about unseen offline peers.
func requireCompleteSeal(state CutoverState, record cutover.Record) error {
	if state.Status == CutoverDiverged {
		return cutover.ErrLegacyChanged
	}
	if len(state.Conflicts) > 0 {
		return cutover.ErrConflict
	}
	if len(state.Pending) > 0 || state.Plan == nil || record.Kind != cutover.Seal || record.PlanID != state.PlanID {
		return cutover.ErrIncomplete
	}
	bindings := map[string]cutover.Binding{}
	metadata := map[string]bool{}
	for _, entry := range state.Imports {
		bindings[entry.ClaimID] = cutover.Binding{FactID: entry.FactID, ClaimID: entry.ClaimID}
		for _, id := range entry.MetadataClaims {
			metadata[id] = true
		}
	}
	if len(bindings) != len(record.Imported) || len(metadata) != len(record.ImportRecords) {
		return cutover.ErrIncomplete
	}
	for _, binding := range record.Imported {
		if bindings[binding.ClaimID] != binding {
			return cutover.ErrIncomplete
		}
	}
	for _, id := range record.ImportRecords {
		if !metadata[id] {
			return cutover.ErrIncomplete
		}
	}
	if len(state.Plan.Facts) > 0 && len(bindings) == 0 {
		return fmt.Errorf("no native imports: %w", cutover.ErrIncomplete)
	}
	return nil
}
