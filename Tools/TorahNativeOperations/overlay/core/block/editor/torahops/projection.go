package torahops

import (
	"context"
	"errors"
	"sort"
)

type Projection struct {
	Live            []Claim
	Conflicts       []Resolution
	PendingObserved []string
}

// ReadTarget folds a bounded, consistent native SQLite snapshot. There is no
// pagination/watermark RPC yet: exceeding the bound is an explicit error, never a
// truncated success. Conflicted logical operations have NO projection effect;
// their complete variant set is returned separately and no winner is selected.
// Removes and replacements suppress only explicitly observed physical claims.
// Tombstones are never erased, including when another operation references one.
func (s *Store) ReadTarget(ctx context.Context, target Target, limit uint) (projection Projection, err error) {
	if !validText(target.ObjectID, true, 1024) || !validText(target.BlockID, false, 1024) || limit == 0 || limit > 10000 {
		return Projection{}, ErrInvalid
	}
	tx, err := s.claims.ReadTx(ctx)
	if err != nil {
		return Projection{}, err
	}
	defer func() { err = errors.Join(err, tx.Commit()) }()
	ctx = tx.Context()
	candidates, err := readClaims(ctx, s.claims.Find(map[string]any{
		"operation.target.objectId": target.ObjectID,
		"operation.target.blockId":  target.BlockID,
	}), limit)
	if err != nil {
		return Projection{}, err
	}
	seen := map[string]bool{}
	claims := map[string]Claim{}
	for _, candidate := range candidates {
		opID := candidate.Operation.OperationID
		if seen[opID] {
			continue
		}
		seen[opID] = true
		// A conflicting variant may name a different target. The target index
		// must not hide that variant and accidentally turn the first into a winner.
		resolution, readErr := s.ReadOperation(ctx, opID)
		if readErr != nil {
			return Projection{}, readErr
		}
		if resolution.Conflict {
			projection.Conflicts = append(projection.Conflicts, resolution)
			continue
		}
		claims[candidate.ID] = candidate
	}
	removed := map[string]bool{}
	pending := map[string]bool{}
	for _, claim := range claims {
		for _, observed := range claim.Operation.Observed {
			if observedClaim, ok := claims[observed]; ok && observedClaim.Operation.Target == target {
				removed[observed] = true
			} else {
				pending[observed] = true
			}
		}
	}
	for _, claim := range claims {
		if claim.Operation.Kind != Remove && !removed[claim.ID] {
			projection.Live = append(projection.Live, claim)
		}
	}
	for id := range pending {
		projection.PendingObserved = append(projection.PendingObserved, id)
	}
	// This is the bytewise display tie-break, not a native causal clock. Claim
	// identity starts with a hash and does not preserve OperationID order.
	sort.Slice(projection.Live, func(i, j int) bool {
		left, right := projection.Live[i], projection.Live[j]
		if left.Operation.OperationID != right.Operation.OperationID {
			return left.Operation.OperationID < right.Operation.OperationID
		}
		return left.ID < right.ID
	})
	sort.Slice(projection.Conflicts, func(i, j int) bool { return projection.Conflicts[i].OperationID < projection.Conflicts[j].OperationID })
	sort.Strings(projection.PendingObserved)
	return projection, nil
}
