//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance

package application

import (
	"errors"
	"testing"

	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"

	"github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
)

// Use the actual loaded Space's native signing/encryption service. This
// fixture setup adds a real stored row, not a constructed successful receipt.
func loadedSpaceFixtureKeyValue(t *testing.T, f *loadedAccountFixture) {
	t.Helper()
	store := f.space.KeyValue().DefaultStore()
	if err := store.Set(f.ctx, "pinkha-native-source-inventory",
		[]byte("native signed key-value source state remains private")); err != nil {
		t.Fatal("actual native key-value write:", err)
	}
	entry, err := f.space.Storage().HeadStorage().GetEntry(f.ctx, store.Id())
	if err != nil || len(entry.Heads) != 1 || entry.Heads[0] != store.InnerStorage().Diff().Hash() {
		t.Fatal("actual native key-value head differs:", err)
	}
	inventory := loadedObjectFixtureInventory(t, f)
	receipt, err := inventory.Receipt()
	if err != nil || receipt.Version != "native-tree-identity-inventory-v2" ||
		receipt.KeyValueStores != 1 || receipt.KeyValueRows < 1 ||
		!receipt.AllHeadRowsAccounted || receipt.SemanticCompleteness ||
		receipt.HistorySemanticsValidated || receipt.HasNativeSourceAdmission ||
		receipt.PermitsDestinationWrites {
		t.Fatal("native key-value source identity was dropped or promoted:", err)
	}
	for _, id := range inventory.TreeIDs() {
		if id == store.Id() {
			t.Fatal("native key-value identity was classified as a document tree")
		}
	}
	f.privateNote(t, "whole-source-native-keyvalue", map[string]any{
		"receipt": receipt, "actualSignedNativeSet": true,
		"nativeDiffHeadMatched": true, "documentTreeExcluded": true,
	})
}

// Mutate only the disposable fixture's system head. Every failed parse still
// reads the actual native store; no successful parser return is injected.
func loadedSpaceFixtureRefuseKeyValueHeads(t *testing.T, f *loadedAccountFixture) {
	t.Helper()
	store := f.space.KeyValue().DefaultStore()
	heads := f.space.Storage().HeadStorage()
	original, err := heads.GetEntry(f.ctx, store.Id())
	if err != nil || len(original.Heads) != 1 {
		t.Fatal("actual native key-value head missing:", err)
	}
	for _, mode := range []string{"head-mismatch", "duplicate-head", "missing-head"} {
		t.Run("native-key-value-"+mode+"-refused", func(t *testing.T) {
			defer func() {
				if err := heads.UpdateEntry(f.ctx, headstorage.HeadsUpdate{
					Id: store.Id(), Heads: append([]string(nil), original.Heads...),
				}); err != nil {
					t.Error("restore disposable original native key-value head:", err)
				}
			}()
			if mode == "missing-head" {
				err = heads.DeleteEntry(f.ctx, store.Id())
			} else {
				bad := []string{"not-the-native-ldiff-head"}
				if mode == "duplicate-head" {
					bad = []string{original.Heads[0], original.Heads[0]}
				}
				err = heads.UpdateEntry(f.ctx, headstorage.HeadsUpdate{Id: store.Id(), Heads: bad})
			}
			if err != nil {
				t.Fatal("native fixture head mutation:", err)
			}
			captured, err := f.service.CaptureLoadedAccountWitness(f.ctx, f.token, f.request())
			if err != nil {
				t.Fatal("actual native rows capture after head mutation:", err)
			}
			inventory, err := captured.PrivateWitness().NativeTreeIdentities(f.ctx)
			if inventory != nil || !errors.Is(err, localstorewitness.ErrNativeTreeInventory) {
				t.Fatal("inconsistent native key-value head was admitted:", err)
			}
		})
	}
	// Successful read after restoring the original head also proves the
	// negative cases did not replace or drop the private key-value rows.
	receipt, err := loadedObjectFixtureInventory(t, f).Receipt()
	if err != nil || receipt.KeyValueStores != 1 || receipt.KeyValueRows < 1 {
		t.Fatal("restored native key-value inventory differs:", err)
	}
	f.privateNote(t, "whole-source-native-keyvalue-refusals", map[string]any{
		"wrongHeadRefused": true, "duplicateHeadRefused": true,
		"missingHeadRefused": true, "originalRowsRetainedAfterRestore": true,
	})
}
