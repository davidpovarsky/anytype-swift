package torahops

import (
	"bytes"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestCanonicalEncodingGoldenVector(t *testing.T) {
	// Independently calculated using Python struct.pack('>I', length) and SHA-256.
	op := add(1, "א<>&\n")
	id, wire, err := EncodeClaim(op)
	require.NoError(t, err)
	require.Equal(t, "89344c7ac74f7d5df8ef2a94f9592a7ed86a9dccc47084f8ce27d98080c29263/3652b732b88752a35184fcf1af80f8d3e499fb5e5e4132a8064e6236a54cd589", id)
	canonical, err := op.CanonicalBytes()
	require.NoError(t, err)
	require.Len(t, canonical, 188)
	claim, err := DecodeClaim(id, wire)
	require.NoError(t, err)
	require.Equal(t, []byte("א<>&\n"), claim.Operation.Payload)
	op.Payload = []byte("א<>&")
	require.NotEqual(t, id, claimID(t, op), "payload bytes are not trimmed or normalized")
}

func TestObservedSetCanonicalizationAndInputOwnership(t *testing.T) {
	a, b := claimID(t, add(1, "A")), claimID(t, add(2, "B"))
	op := add(3, "replacement")
	op.Kind, op.Observed = Replace, []string{b, a, b}
	id, wire, err := EncodeClaim(op)
	require.NoError(t, err)
	op.Observed = []string{a, b}
	id2, wire2, err := EncodeClaim(op)
	require.NoError(t, err)
	require.Equal(t, id, id2)
	require.Equal(t, wire, wire2)
	claim, _, err := makeClaim(op)
	require.NoError(t, err)
	op.Payload[0] = 'X'
	op.Observed[0] = "mutated"
	require.Equal(t, "replacement", string(claim.Operation.Payload))
	require.NotContains(t, claim.Operation.Observed, "mutated")
}

func TestEnvelopeBoundsAndVersionFailClosed(t *testing.T) {
	cases := map[string]func(*Operation){
		"future":              func(op *Operation) { op.Version = 2 },
		"unknown-kind":        func(op *Operation) { op.Kind = "update" },
		"empty-id":            func(op *Operation) { op.OperationID = "" },
		"noncanonical-id":     func(op *Operation) { op.OperationID = strings.Repeat("A", 32) },
		"payload-limit":       func(op *Operation) { op.Payload = bytes.Repeat([]byte{1}, MaxPayloadBytes+1) },
		"invalid-utf8":        func(op *Operation) { op.Target.ObjectID = string([]byte{0xff}) },
		"nul-space":           func(op *Operation) { op.SpaceID = "space\x00other" },
		"empty-add":           func(op *Operation) { op.Payload = nil },
		"invalid-observed":    func(op *Operation) { op.Kind = Replace; op.Observed = []string{"not-a-claim"} },
		"remove-with-payload": func(op *Operation) { op.Kind = Remove; op.Observed = []string{claimID(t, add(2, "old"))} },
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			op := add(1, "value")
			mutate(&op)
			_, _, err := EncodeClaim(op)
			require.Error(t, err)
		})
	}
	op := add(1, "")
	op.Payload = bytes.Repeat([]byte{0xff}, MaxPayloadBytes)
	id, wire, err := EncodeClaim(op)
	require.NoError(t, err, "opaque payload bytes need not be UTF-8")
	_, err = DecodeClaim(id, wire)
	require.NoError(t, err)
}

func TestRemoveBeforeObservedClaimAndNoTombstoneErasure(t *testing.T) {
	fx := openFixture(t, "")
	old := add(1, "old")
	remove := add(2, "")
	remove.Kind, remove.Source, remove.Observed = Remove, Source{}, []string{claimID(t, old)}
	require.NoError(t, fx.store.Replay(testContext, remove, native("remove-first")))
	require.Equal(t, []string{claimID(t, old)}, projection(t, fx).PendingObserved)
	require.NoError(t, fx.store.Replay(testContext, old, native("old-later")))
	require.Empty(t, projection(t, fx).Live)
	removeTombstone := add(3, "")
	removeTombstone.Kind, removeTombstone.Source, removeTombstone.Observed = Remove, Source{}, []string{claimID(t, remove)}
	require.NoError(t, fx.store.Replay(testContext, removeTombstone, native("remove-tombstone")))
	require.Empty(t, projection(t, fx).Live, "referencing a tombstone must never resurrect old content")
	counts(t, fx, 3, 3)
	fx.reopen(t)
	require.Empty(t, projection(t, fx).Live)
}
