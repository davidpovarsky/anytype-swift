package torahops

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
)

// These are disk-backed StoreState regressions using the existing component
// fixture. Explicit Replay is not evidence of two syncing Native clients, and
// OperationID order is not evidence of signed-event causal ordering.
func projectionOrderClaims(t *testing.T, operations ...Operation) []Claim {
	t.Helper()
	claims := make([]Claim, 0, len(operations))
	for _, operation := range operations {
		claim, _, err := makeClaim(operation)
		require.NoError(t, err)
		claims = append(claims, claim)
	}
	return claims
}

func replayProjectionOrder(t *testing.T, fx *fixture, operations []Operation, order []int) {
	t.Helper()
	for _, index := range order {
		require.NoError(t, fx.store.Replay(testContext, operations[index], native(fmt.Sprintf("display-order-%02d", index))))
	}
}

type projectionOrderEvidence struct {
	Operations map[string]Resolution
	Receipts   map[string][]Receipt
}

func readProjectionOrderEvidence(t *testing.T, fx *fixture, operations []Operation) projectionOrderEvidence {
	t.Helper()
	evidence := projectionOrderEvidence{Operations: map[string]Resolution{}, Receipts: map[string][]Receipt{}}
	for index, operation := range operations {
		claim := projectionOrderClaims(t, operation)[0]
		resolution, err := fx.store.ReadOperation(testContext, operation.OperationID)
		require.NoError(t, err)
		require.Contains(t, resolution.Claims, claim, "canonical identity and complete content must remain readable")
		evidence.Operations[operation.OperationID] = resolution
		receipts, err := fx.store.Receipts(testContext, claim.ID)
		require.NoError(t, err)
		require.Len(t, receipts, 1)
		require.Equal(t, claim.ID, receipts[0].ClaimID)
		require.Equal(t, fmt.Sprintf("display-order-%02d", index), receipts[0].ChangeID)
		require.Equal(t, operation.AuthorID, receipts[0].Creator)
		require.Equal(t, "verified-native-acl-head", receipts[0].ACLHeadID)
		evidence.Receipts[claim.ID] = receipts
	}
	return evidence
}

func TestLiveOperationIDOrderAcrossReplayAndDiskReopen(t *testing.T) {
	operations := []Operation{add(1, "first operation bytes"), add(2, "second operation bytes"), add(3, "third operation bytes")}
	expected := projectionOrderClaims(t, operations...)
	// This fixed Space/ID pair reverses physical-hash order. The old comparator
	// therefore cannot accidentally pass the expected 01,02,03 display order.
	require.Less(t, expected[1].ID, expected[0].ID)
	require.Less(t, operations[0].OperationID, operations[1].OperationID)
	for _, order := range [][]int{{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}} {
		t.Run(fmt.Sprint(order), func(t *testing.T) {
			fx := openFixture(t, "")
			replayProjectionOrder(t, fx, operations, order)
			before := readProjectionOrderEvidence(t, fx, operations)
			view := projection(t, fx)
			require.Equal(t, expected, view.Live)
			require.Empty(t, view.Conflicts)
			require.Empty(t, view.PendingObserved)
			require.Equal(t, before, readProjectionOrderEvidence(t, fx, operations))
			counts(t, fx, 3, 3)
			fx.reopen(t)
			require.Equal(t, view, projection(t, fx))
			require.Equal(t, before, readProjectionOrderEvidence(t, fx, operations))
			counts(t, fx, 3, 3)
		})
	}
}

func TestLiveOperationIDOrderRetainsConcurrentReplacements(t *testing.T) {
	old, first, second, unrelated := add(9, "old predecessor"), add(1, "successor one"), add(2, "successor two"), add(3, "unrelated live claim")
	first.Kind, second.Kind = Replace, Replace
	first.Observed, second.Observed = []string{claimID(t, old)}, []string{claimID(t, old)}
	operations := []Operation{old, first, second, unrelated}
	expected := projectionOrderClaims(t, first, second, unrelated)
	require.Less(t, expected[1].ID, expected[0].ID)
	for _, order := range [][]int{{0, 1, 2, 3}, {2, 3, 0, 1}, {3, 1, 2, 0}} {
		t.Run(fmt.Sprint(order), func(t *testing.T) {
			fx := openFixture(t, "")
			replayProjectionOrder(t, fx, operations, order)
			before := readProjectionOrderEvidence(t, fx, operations)
			view := projection(t, fx)
			require.Equal(t, expected, view.Live, "both successors retain their full provenance and exact predecessor reference")
			require.Empty(t, view.Conflicts)
			require.Empty(t, view.PendingObserved)
			counts(t, fx, 4, 4)
			fx.reopen(t)
			require.Equal(t, view, projection(t, fx))
			require.Equal(t, before, readProjectionOrderEvidence(t, fx, operations))
			counts(t, fx, 4, 4)
		})
	}
}

func TestLiveOperationIDOrderPreservesNonLiveProvenance(t *testing.T) {
	first, second := add(1, "first live"), add(2, "second live")
	variantA, variantB := add(4, "conflicting A"), add(4, "conflicting B")
	missing := add(6, "predecessor not received")
	remove := add(5, "")
	remove.Kind, remove.Source, remove.Observed = Remove, Source{}, []string{claimID(t, missing)}
	operations := []Operation{first, second, variantA, variantB, remove}
	fx := openFixture(t, "")
	replayProjectionOrder(t, fx, operations, []int{4, 3, 1, 2, 0})
	before := readProjectionOrderEvidence(t, fx, operations)
	conflict := before.Operations[variantA.OperationID]
	require.True(t, conflict.Conflict)
	require.Len(t, conflict.Claims, 2)
	require.ElementsMatch(t, projectionOrderClaims(t, variantA, variantB), conflict.Claims)
	view := projection(t, fx)
	require.Equal(t, projectionOrderClaims(t, first, second), view.Live)
	require.Equal(t, []Resolution{conflict}, view.Conflicts)
	require.Equal(t, []string{claimID(t, missing)}, view.PendingObserved)
	require.Equal(t, before, readProjectionOrderEvidence(t, fx, operations))
	counts(t, fx, 5, 5)
	fx.reopen(t)
	require.Equal(t, view, projection(t, fx))
	require.Equal(t, before, readProjectionOrderEvidence(t, fx, operations))
	counts(t, fx, 5, 5)
}
