//go:build pinkha_localstore_witness

package localstorewitness_test

import (
	"context"
	"errors"
	"testing"

	witness "github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
)

// This is the old interface-embedding attack shape. Its public Acquire method
// cannot replace the concrete Capability's private acquisition closure.
type externalEmbedding struct {
	*witness.Capability
	called bool
}

func (e *externalEmbedding) Acquire(context.Context) (witness.Lease, error) {
	e.called = true
	return nil, errors.New("external acquisition override must never be called")
}

func TestLocalStoreWitnessConcreteCapabilityRejectsExternalEmbeddingAndZero(t *testing.T) {
	ctx := context.Background()
	refused := func(cap *witness.Capability) {
		t.Helper()
		w, err := witness.Capture(ctx, cap, witness.DefaultLimits())
		if w != nil || !errors.Is(err, witness.ErrOwnership) {
			t.Fatalf("unissued or retired concrete capability accepted: witness=%v err=%v", w != nil, err)
		}
	}
	refused(nil)
	refused(new(witness.Capability))
	for _, cap := range []*witness.Capability{nil, new(witness.Capability)} {
		attack := &externalEmbedding{Capability: cap}
		if _, ok := any(attack).(*witness.Capability); ok {
			t.Fatal("foreign embedding became the concrete issued carrier")
		}
		refused(attack.Capability)
		if attack.called {
			t.Fatal("external public override substituted an issuer")
		}
	}

	// Forwarding a genuinely issued capability is delegation. The caller
	// cannot change its issuer or bypass current generation after retirement.
	cap, retire := witness.LocalWitnessFixtureCapabilityForExternalTest(t)
	delegate := &externalEmbedding{Capability: cap}
	w, err := witness.Capture(ctx, delegate.Capability, witness.DefaultLimits())
	if err != nil {
		t.Fatal(err)
	}
	receipt, err := w.Receipt()
	if err != nil || !receipt.LocalDecodedRowsComplete || receipt.HasNativeSourceAdmission || receipt.PermitsDestinationWrites || delegate.called {
		t.Fatal("delegated fixture capability changed scope or invoked override")
	}
	retire()
	refused(delegate.Capability)
	if delegate.called {
		t.Fatal("external override bypassed retired original issuer")
	}
}
