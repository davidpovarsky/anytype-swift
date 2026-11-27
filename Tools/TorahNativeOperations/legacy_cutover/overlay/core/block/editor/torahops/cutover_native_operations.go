package torahops

import (
	"bytes"
	"context"
	"slices"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
)

// AppendImport persists an ordinary v1 Add through the original signed storage
// guard. The metadata tree records provenance in a later explicit phase. These
// two trees are never reported as one atomic transaction.
func (h *CutoverNativeHost) AppendImport(ctx context.Context, v1 *NativeHost, planID, factID string, op Operation) (NativeAppendResult, error) {
	return h.appendOriginal(ctx, v1, planID, factID, op, true)
}

// AppendAssociation is the production post-cutover write gate. A Swift-side
// read followed by an unguarded v1 append cannot substitute for this operation:
// source bytes, signed metadata and current native authority stay locked through
// the actual durable v1 write.
func (h *CutoverNativeHost) AppendAssociation(ctx context.Context, v1 *NativeHost, planID string, op Operation) (NativeAppendResult, error) {
	return h.appendOriginal(ctx, v1, planID, "", op, false)
}
func (h *CutoverNativeHost) appendOriginal(ctx context.Context, v1 *NativeHost, planID, factID string, op Operation, importing bool) (NativeAppendResult, error) {
	if err := h.validatePair(v1); err != nil {
		return NativeAppendResult{}, err
	}
	if !cutover.Hex(planID, 32) || (importing && !cutover.Hex(factID, 32)) {
		return NativeAppendResult{}, cutover.ErrInvalid
	}
	claim, wire, err := makeClaim(op)
	if err != nil {
		return NativeAppendResult{}, err
	}
	op = claim.Operation
	if op.SpaceID != h.store.spaceID || op.AuthorID != h.key.GetPublic().Account() {
		return NativeAppendResult{}, cutover.ErrInvalid
	}
	if err = AuthorizeCurrentACL(h.tree.AclList(), h.key, true); err != nil {
		return NativeAppendResult{}, err
	}
	h.tree.Lock()
	key, err := h.candidatePropertyLocked(ctx, op.Target.ObjectID, planID)
	h.tree.Unlock()
	if err != nil {
		return NativeAppendResult{}, err
	}
	lease, err := h.acquireSource(ctx, op.Target.ObjectID, key, true)
	if err != nil {
		return NativeAppendResult{}, err
	}
	defer lease.Release()
	h.tree.Lock()
	defer h.tree.Unlock()
	v1.tree.Lock()
	defer v1.tree.Unlock()
	acl := h.tree.AclList()
	acl.RLock()
	if !acl.AclState().Permissions(h.key.GetPublic()).CanWrite() {
		acl.RUnlock()
		return NativeAppendResult{}, list.ErrInsufficientPermissions
	}
	snapshot, err := h.readLocked(ctx, v1, op.Target.ObjectID, lease)
	if err == nil {
		err = lease.Validate(ctx)
	}
	if err == nil {
		err = lease.ValidateTarget(ctx, op.Target)
	}
	if err == nil {
		err = requireCurrentCutoverSource(snapshot.State)
	}
	if err != nil {
		acl.RUnlock()
		return NativeAppendResult{}, err
	}
	// A lost ACK reuses the original immutable bytes and every original receipt.
	// Current source/ACL/target authority was rechecked above. A valid Seal may
	// follow the original commit without invalidating that exact frozen retry.
	existing, err := v1.store.checkLocal(ctx, claim)
	if err != nil || existing.Disposition != Created {
		acl.RUnlock()
		return NativeAppendResult{AppendResult: existing}, err
	}
	err = validateCutoverOriginalAppend(snapshot, planID, factID, op, importing)
	acl.RUnlock()
	if err != nil {
		return NativeAppendResult{}, err
	}
	if err = lease.Validate(ctx); err != nil {
		return NativeAppendResult{}, err
	}
	return v1.appendLocked(ctx, op, claim, wire, lease.Release, func() error {
		if err := lease.Validate(ctx); err != nil {
			return err
		}
		return lease.ValidateTarget(ctx, op.Target)
	})
}
func validateCutoverOriginalAppend(s CutoverNativeSnapshot, planID, factID string, op Operation, importing bool) error {
	if err := requireCurrentCutoverSource(s.State); err != nil {
		return err
	}
	if s.State.Plan == nil || s.State.PlanID != planID {
		return cutover.ErrIncomplete
	}
	plan := s.State.Plan
	if plan.SpaceID != op.SpaceID || plan.ObjectID != op.Target.ObjectID {
		return cutover.ErrInvalid
	}
	if importing {
		if len(s.State.Seals) > 0 {
			return cutover.ErrAlreadySealed
		}
		expectedID, err := cutover.ImportOperationID(planID, factID, op.AuthorID)
		if err != nil {
			return err
		}
		if op.OperationID != expectedID || op.Kind != Add || len(op.Observed) != 0 {
			return cutover.ErrInvalid
		}
		for _, fact := range plan.Facts {
			id, err := fact.ID(plan.SpaceID, plan.ObjectID)
			if err != nil {
				return err
			}
			if id != factID {
				continue
			}
			if op.Target.BlockID != fact.BlockID || op.Source != (Source{ProviderID: fact.ProviderID, CanonicalRef: fact.CanonicalRef}) ||
				!bytes.Equal(op.Payload, fact.Payload) {
				return cutover.ErrInvalid
			}
			return nil
		}
		return cutover.ErrInvalid
	}
	if s.State.Status != CutoverSealed {
		return cutover.ErrIncomplete
	}
	// A new ordinary mutation may not impersonate the reserved deterministic
	// import identity. Exact retries were handled above without a new write.
	for _, fact := range plan.Facts {
		id, err := fact.ID(plan.SpaceID, plan.ObjectID)
		if err != nil {
			return err
		}
		reserved, err := cutover.ImportOperationID(planID, id, op.AuthorID)
		if err != nil {
			return err
		}
		if reserved == op.OperationID {
			return cutover.ErrInvalid
		}
	}
	// Original v1 requires real observed claim IDs. This new gate additionally
	// refuses references absent from the fully verified current object history.
	// Concurrent new claims remain visible under the original CRDT policy.
	known := map[string]Target{}
	for _, claim := range s.OriginalClaims {
		known[claim.ID] = claim.Operation.Target
	}
	for _, id := range slices.Compact(slices.Sorted(slices.Values(op.Observed))) {
		target, exists := known[id]
		if !exists || target != op.Target {
			return cutover.ErrIncomplete
		}
	}
	return nil
}
