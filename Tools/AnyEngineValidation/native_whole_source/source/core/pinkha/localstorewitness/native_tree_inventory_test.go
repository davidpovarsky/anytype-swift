//go:build pinkha_localstore_witness && pinkha_loaded_account_witness

package localstorewitness

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
)

// These tests create real native SpaceStorage and signed opaque tree records.
// They qualify the structural join, not Heart object semantics or migration.
func TestNativeTreeInventoryBindsDetachedNativeHeads(t *testing.T) {
	ctx := nativeOwnedContext(t)
	f := newNativeOwnedFixture(t, ctx)
	tree := newCensusNativeTree(t, &fixture{storage: f.storage}, "inventory-original", "")
	firstHead := appendCensusNativeChange(t, tree, "original native change")
	w, err := CaptureNativeOwned(ctx, nativeOwnedCapability(t, f.storage), DefaultLimits())
	must(t, err)
	inventory, err := w.NativeTreeIdentities(ctx)
	must(t, err)
	entry, err := inventory.Tree(tree.root.Id)
	must(t, err)
	if entry.ID() != tree.root.Id || entry.DeletedStatus() != 0 ||
		!bytes.Equal(entry.RootRawChange(), tree.root.RawChange) ||
		len(entry.Heads()) != 1 || entry.Heads()[0] != firstHead {
		t.Fatal("exact native tree root/head join changed")
	}
	must(t, inventory.MatchObject(f.storage.Id(), tree.root.Id, tree.root.Id, tree.root.RawChange, []string{firstHead}))
	copiedHeads, copiedRoot := entry.Heads(), entry.RootRawChange()
	copiedHeads[0] = "not-a-native-head"
	copiedRoot[0] ^= 1
	ids := inventory.TreeIDs()
	ids[0] = "not-a-native-tree"
	must(t, inventory.MatchObject(f.storage.Id(), tree.root.Id, tree.root.Id, tree.root.RawChange, []string{firstHead}))
	for _, mismatch := range []struct {
		name, space, object, root string
		raw                       []byte
		heads                     []string
	}{
		{"space", "another-space", tree.root.Id, tree.root.Id, tree.root.RawChange, []string{firstHead}},
		{"object", f.storage.Id(), "another-object", tree.root.Id, tree.root.RawChange, []string{firstHead}},
		{"root", f.storage.Id(), tree.root.Id, "another-root", tree.root.RawChange, []string{firstHead}},
		{"raw-root", f.storage.Id(), tree.root.Id, tree.root.Id, copiedRoot, []string{firstHead}},
		{"head", f.storage.Id(), tree.root.Id, tree.root.Id, tree.root.RawChange, []string{"another-head"}},
		{"duplicate-head", f.storage.Id(), tree.root.Id, tree.root.Id, tree.root.RawChange, []string{firstHead, firstHead}},
	} {
		t.Run(mismatch.name, func(t *testing.T) {
			if err := inventory.MatchObject(mismatch.space, mismatch.object, mismatch.root, mismatch.raw, mismatch.heads); !errors.Is(err, ErrNativeTreeInventory) {
				t.Fatal("different native source identity was admitted")
			}
		})
	}
	same, err := CaptureNativeOwned(ctx, nativeOwnedCapability(t, f.storage), DefaultLimits())
	must(t, err)
	sameInventory, err := same.NativeTreeIdentities(ctx)
	must(t, err)
	must(t, inventory.SameCheckpoint(sameInventory))
	secondHead := appendCensusNativeChange(t, tree, "later native change")
	later, err := CaptureNativeOwned(ctx, nativeOwnedCapability(t, f.storage), DefaultLimits())
	must(t, err)
	laterInventory, err := later.NativeTreeIdentities(ctx)
	must(t, err)
	if !errors.Is(inventory.SameCheckpoint(laterInventory), ErrNativeTreeInventory) {
		t.Fatal("native source changed without invalidating the checkpoint")
	}
	must(t, inventory.MatchObject(f.storage.Id(), tree.root.Id, tree.root.Id, tree.root.RawChange, []string{firstHead}))
	must(t, laterInventory.MatchObject(f.storage.Id(), tree.root.Id, tree.root.Id, tree.root.RawChange, []string{secondHead}))
	if _, err = w.LocalTreeCensus(ctx, DefaultCensusLimits()); !errors.Is(err, ErrOwnership) {
		t.Fatal("old fixture-only census authority changed")
	}
	receipt, err := inventory.Receipt()
	must(t, err)
	if receipt.SourceWitnessSHA256 != w.digest || !receipt.AllHeadRowsAccounted ||
		receipt.OtherCollections < 2 || receipt.OtherCollectionRows < 1 ||
		receipt.AccountSessionAuthorized || receipt.HistorySemanticsValidated ||
		receipt.SemanticCompleteness || receipt.FilePayloadCompleteness ||
		receipt.HasNativeSourceAdmission || receipt.PermitsDestinationWrites {
		t.Fatal("structural inventory overclaimed source authority or completeness")
	}
	raw, err := json.Marshal(receipt)
	must(t, err)
	if bytes.Contains(raw, []byte(tree.root.Id)) || bytes.Contains(raw, []byte(f.storage.Id())) {
		t.Fatal("public receipt exposed native identifiers")
	}
	t.Logf("NATIVE_TREE_INVENTORY %s", raw)
}

func TestNativeTreeInventoryRefusesMalformedNativeHeads(t *testing.T) {
	for _, mode := range []string{"unknown-head", "duplicate-head", "unknown-deletion", "deleted-tree-retained"} {
		t.Run(mode, func(t *testing.T) {
			ctx := nativeOwnedContext(t)
			f := newNativeOwnedFixture(t, ctx)
			tree := newCensusNativeTree(t, &fixture{storage: f.storage}, "inventory-invalid-"+mode, "")
			head := appendCensusNativeChange(t, tree, "native fixture before mutation")
			update := headstorage.HeadsUpdate{Id: tree.root.Id}
			switch mode {
			case "unknown-head":
				update.Heads = []string{"not-a-stored-native-change"}
			case "duplicate-head":
				update.Heads = []string{head, head}
			case "unknown-deletion":
				status := headstorage.DeletedStatus(99)
				update.DeletedStatus = &status
			case "deleted-tree-retained":
				status := headstorage.DeletedStatusQueued
				update.DeletedStatus = &status
			}
			must(t, f.storage.HeadStorage().UpdateEntry(ctx, update))
			w, err := CaptureNativeOwned(ctx, nativeOwnedCapability(t, f.storage), DefaultLimits())
			must(t, err)
			inventory, err := w.NativeTreeIdentities(ctx)
			if mode == "deleted-tree-retained" {
				must(t, err)
				entry, err := inventory.Tree(tree.root.Id)
				must(t, err)
				if entry.DeletedStatus() != int(headstorage.DeletedStatusQueued) ||
					!bytes.Equal(entry.RootRawChange(), tree.root.RawChange) {
					t.Fatal("deleted native identity or original bytes were dropped")
				}
				if !errors.Is(inventory.MatchObject(f.storage.Id(), tree.root.Id, tree.root.Id, tree.root.RawChange, []string{head}), ErrNativeTreeInventory) {
					t.Fatal("deleted native tree was admitted as a live document")
				}
			} else if inventory != nil || !errors.Is(err, ErrNativeTreeInventory) {
				t.Fatal("malformed real native head row was accepted")
			}
		})
	}
}

func TestNativeTreeInventoryRefusesUnownedOrCorruptCapture(t *testing.T) {
	ctx := nativeOwnedContext(t)
	f := newNativeOwnedFixture(t, ctx)
	w, err := CaptureNativeOwned(ctx, nativeOwnedCapability(t, f.storage), DefaultLimits())
	must(t, err)
	var zero Witness
	for _, invalid := range []*Witness{nil, &zero} {
		if got, err := invalid.NativeTreeIdentities(ctx); got != nil || !errors.Is(err, ErrOwnership) {
			t.Fatal("unowned witness issued native identities")
		}
	}
	fixtureOnly := *w
	fixtureOnly.binding.Authority = FixtureOnlyAuthority
	if got, err := fixtureOnly.NativeTreeIdentities(ctx); got != nil || !errors.Is(err, ErrOwnership) {
		t.Fatal("fixture authority was promoted to native ownership")
	}
	corrupt := *w
	corrupt.digest = strings.Repeat("0", 64)
	if got, err := corrupt.NativeTreeIdentities(ctx); got != nil || !errors.Is(err, ErrNativeTreeInventory) {
		t.Fatal("altered captured witness digest was accepted")
	}
	cancelled, cancel := context.WithCancel(ctx)
	cancel()
	if got, err := w.NativeTreeIdentities(cancelled); got != nil || !errors.Is(err, context.Canceled) {
		t.Fatal("cancelled census continued")
	}
	if got, err := w.NativeTreeIdentities(nil); got != nil || !errors.Is(err, ErrOwnership) {
		t.Fatal("missing source context was accepted")
	}
}
