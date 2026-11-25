//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance

package application

import (
	"testing"

	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/anyblockjson/storeresolver"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

func TestLoadedAccountCapturedTypeNamespaces(t *testing.T) {
	f := newLoadedAccountFixture(t)
	_ = loadedObjectFixturePage(t, f, "native type namespace", false)
	loadedSpaceFixtureWarm(t, f)
	var receipt LoadedAccountSpaceWitnessReceipt
	nativeURLs, nativeTypeRows := 0, 0

	t.Run("actual-native-snapshot-closure", func(t *testing.T) {
		captured, err := f.service.CaptureLoadedAccountSpaceWitness(f.ctx, f.token, loadedSpaceRequest(f))
		if err != nil {
			t.Fatal(err)
		}
		receipt, err = captured.Receipt()
		if err != nil {
			t.Fatal(err)
		}
		if receipt.ClosedResolverUnmapped != 0 || !receipt.AllNativeHeadRowsAccounted ||
			!receipt.AllCurrentObjectsCaptured || !receipt.CapturedSnapshotsBoundToUnchangedCheckpoint ||
			!receipt.AccountSessionAuthorizedAtFinalCapture || !receipt.IndexResolverSnapshotBound {
			t.Fatal("actual captured native type URLs did not close", receipt.ClosedResolverUnmapped)
		}
		if receipt.HasNativeSourceAdmission || receipt.SemanticCompleteness ||
			receipt.HistorySemanticsValidated || receipt.PermitsDestinationWrites {
			t.Fatal("type lookup conferred migration authority")
		}
		for _, object := range captured.objects {
			raw := object.SnapshotBase()
			original, err := object.Receipt()
			if err != nil || loadedFixtureHash(raw) != original.SnapshotSHA256 {
				t.Fatal("native snapshot changed during resolver construction", err)
			}
			base := new(model.SmartBlockSnapshotBase)
			if err := proto.Unmarshal(raw, base); err != nil {
				t.Fatal(err)
			}
			for _, value := range base.ObjectTypes {
				key, err := bundle.TypeKeyFromUrl(value)
				if err != nil || key == "" || value != key.URL() {
					t.Fatal("actual native serializer did not supply canonical type URL")
				}
				nativeURLs++
			}
			if object.Type() == model.SmartBlockType_STType {
				nativeTypeRows++
			}
		}
		if nativeURLs == 0 || nativeTypeRows == 0 {
			t.Fatal("native namespace fixture did not capture type references and definitions")
		}
	})

	typeRow := func(id, key string) storeresolver.CapturedRow {
		row := loadedCapturedRow(id, model.SmartBlockType_STType, nil)
		row.UniqueKey = domain.TypeKey(key).URL()
		return row
	}
	resolve := func(t *testing.T, values []string, definitions ...storeresolver.CapturedRow) *storeresolver.CapturedResolver {
		t.Helper()
		source := loadedCapturedRow("captured-source", model.SmartBlockType_Page, nil)
		source.Snapshot.ObjectTypes = append([]string(nil), values...)
		rows := append([]storeresolver.CapturedRow{source}, definitions...)
		resolver, err := storeresolver.NewCaptured("captured-space", rows)
		if err != nil {
			t.Fatal(err)
		}
		return resolver
	}
	hasGap := func(resolver *storeresolver.CapturedResolver, target, reason string) bool {
		for _, gap := range resolver.Unmapped() {
			if gap.SourceID == "captured-source" && gap.Field == "objectTypes" &&
				gap.Target == target && gap.Reason == reason {
				return true
			}
		}
		return false
	}
	key := domain.TypeKey("capturedtype")
	t.Run("native-and-legacy-urls-join-captured-key", func(t *testing.T) {
		for _, value := range []string{key.URL(), key.BundledURL()} {
			resolver := resolve(t, []string{value}, typeRow("native-type-id", key.String()))
			if len(resolver.Unmapped()) != 0 {
				t.Fatal("native URL did not join its captured definition")
			}
			if len(resolver.BundledDefinitionsUsed()) != 0 {
				t.Fatal("custom captured identity fell through to bundled data")
			}
		}
	})
	t.Run("native-id-is-not-snapshot-type-key", func(t *testing.T) {
		resolver := resolve(t, []string{"native-type-id"}, typeRow("native-type-id", key.String()))
		if !hasGap(resolver, "native-type-id", "type-object-id-in-key-slot") {
			t.Fatal("native object ID was accepted as a serialized type key")
		}
	})
	t.Run("missing-type-url-remains-explicit", func(t *testing.T) {
		missing := domain.TypeKey("unavailabletype").URL()
		resolver := resolve(t, []string{missing}, typeRow("native-type-id", key.String()))
		if !hasGap(resolver, missing, "missing-type-key") {
			t.Fatal("missing parsed type key disappeared from accounting")
		}
	})
	t.Run("duplicate-type-aliases-remain-explicit", func(t *testing.T) {
		resolver := resolve(t, []string{key.URL(), key.BundledURL()}, typeRow("native-type-id", key.String()))
		if !hasGap(resolver, key.URL(), "duplicate-type-alias") ||
			!hasGap(resolver, key.BundledURL(), "duplicate-type-alias") {
			t.Fatal("duplicate native/legacy type aliases were silently collapsed")
		}
	})
	t.Run("colliding-key-blocks-bundled-fallback", func(t *testing.T) {
		value := bundle.TypeKeyPage.URL()
		resolver := resolve(t, []string{value},
			typeRow("native-type-a", bundle.TypeKeyPage.String()),
			typeRow("native-type-b", bundle.TypeKeyPage.String()))
		collisions := 0
		for _, gap := range resolver.Unmapped() {
			if gap.Reason == "colliding-type-key" {
				collisions++
			}
		}
		if collisions != 2 || !hasGap(resolver, value, "missing-type-key") ||
			len(resolver.BundledDefinitionsUsed()) != 0 {
			t.Fatal("ambiguous captured type identity escaped through bundled fallback")
		}
	})
	t.Run("type-url-object-id-alias-refused", func(t *testing.T) {
		resolver := resolve(t, []string{key.URL()}, typeRow(key.URL(), key.String()))
		if !hasGap(resolver, key.URL(), "type-object-id-in-key-slot") {
			t.Fatal("same spelling in object-ID and type-key namespaces was guessed")
		}
	})
	t.Run("empty-and-foreign-prefixes-refused", func(t *testing.T) {
		for _, value := range []string{"", "ot-", "rel-capturedtype", key.String()} {
			resolver := resolve(t, []string{value}, typeRow("native-type-id", key.String()))
			if !hasGap(resolver, value, "invalid-type-url") {
				t.Fatal("invalid serialized type namespace was admitted")
			}
		}
	})
	if t.Failed() {
		return
	}
	f.privateNote(t, "captured-type-namespaces", map[string]any{
		"receipt": receipt, "actualNativeTypeURLs": nativeURLs, "actualNativeTypeRows": nativeTypeRows,
		"rawSnapshotsUnchanged": true, "boundarySubtests": 8,
		"nativeIDRefusedInTypeKeySlot": true, "missingTypeRetained": true,
		"duplicateAliasesRetained": true, "capturedCollisionBlocksBundledFallback": true,
	})
	t.Logf("NATIVE_CAPTURED_TYPE_NAMESPACE_OBSERVATION native_urls=%d native_type_rows=%d boundary_subtests=8", nativeURLs, nativeTypeRows)
}
