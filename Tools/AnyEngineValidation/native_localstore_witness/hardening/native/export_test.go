//go:build pinkha_localstore_witness

package localstorewitness

import "testing"

// LocalWitnessFixtureCapabilityForExternalTest exists only in the opt-in test
// package. It does not ship in the product package or issue production authority.
func LocalWitnessFixtureCapabilityForExternalTest(t *testing.T) (*Capability, func()) {
	f := newFixture(t)
	return f.capability(nil), func() { f.owner.generation.Add(1) }
}
