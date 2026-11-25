//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance

package application

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/cache"
	sb "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	nativeexport "github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// The existing fixture creates a real LocalOnly account and native full session.
// These new methods execute native object creation/editing and the new capture
// entrypoint; no fake picker, signed tree or successful result is injected.
func loadedObjectFixturePage(t *testing.T, f *loadedAccountFixture, body string, archived bool) string {
	t.Helper()
	creator, ok := f.service.GetApp().Component(objectcreator.CName).(objectcreator.Service)
	if !ok {
		t.Fatal("actual object creator missing")
	}
	const root, child = "native-object-fixture-root", "native-object-fixture-body"
	st := state.NewDoc(root, map[string]simple.Block{
		root: simple.New(&model.Block{Id: root, ChildrenIds: []string{child},
			Content: &model.BlockContentOfSmartblock{Smartblock: &model.BlockContentSmartblock{}}}),
		child: simple.New(&model.Block{Id: child,
			Content: &model.BlockContentOfText{Text: &model.BlockContentText{
				Text: body, Style: model.BlockContentText_Paragraph,
			}}}),
	}).(*state.State)
	st.SetDetailAndBundledRelation(bundle.RelationKeyName, domain.String("צילום מקור — עברית"))
	if archived {
		st.SetDetailAndBundledRelation(bundle.RelationKeyIsArchived, domain.Bool(true))
	}
	id, _, err := creator.CreateSmartBlockFromState(f.ctx, f.space.Id(),
		[]domain.TypeKey{bundle.TypeKeyPage}, st)
	if err != nil || id == "" {
		t.Fatal("actual native object creation:", err)
	}
	return id
}

func loadedObjectFixtureEdit(t *testing.T, f *loadedAccountFixture, id, body string) {
	t.Helper()
	picker, ok := f.service.GetApp().Component(block.CName).(*block.Service)
	if !ok {
		t.Fatal("actual block service missing")
	}
	err := cache.DoContextFullID(picker, f.ctx,
		domain.FullID{SpaceID: f.space.Id(), ObjectID: id}, func(object sb.SmartBlock) error {
			st := object.NewState()
			text := st.Get("native-object-fixture-body")
			if text == nil || text.Model().GetText() == nil {
				t.Fatal("actual original native body block absent")
			}
			text.Model().GetText().Text = body
			return object.Apply(st)
		})
	if err != nil {
		t.Fatal("actual native edit:", err)
	}
}

func loadedObjectFixtureInventory(t *testing.T, f *loadedAccountFixture) *localstorewitness.NativeTreeInventory {
	t.Helper()
	source, err := f.service.CaptureLoadedAccountWitness(f.ctx, f.token, f.request())
	if err != nil {
		t.Fatal(err)
	}
	inventory, err := source.PrivateWitness().NativeTreeIdentities(f.ctx)
	if err != nil {
		t.Fatal(err)
	}
	return inventory
}

func TestLoadedAccountObjectWitnessBindsRealSnapshotsAndHistoryRows(t *testing.T) {
	f := newLoadedAccountFixture(t)
	firstBody, laterBody := "גִּרְסָה ראשונה — מקור ①", "גִּרְסָה שנייה — מקור ②"
	id := loadedObjectFixturePage(t, f, firstBody, false)
	archivedID := loadedObjectFixturePage(t, f, "מסמך שמור בארכיון", true)
	before := loadedObjectFixtureInventory(t, f)
	exporter := f.service.GetApp().Component(nativeexport.CName)
	oldObject, err := nativeexport.CaptureNativeObjectWitness(f.ctx, exporter, before, id, 1<<20)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(oldObject.AnyBlock(), []byte(firstBody)) ||
		!bytes.Contains(oldObject.SnapshotBase(), []byte(firstBody)) {
		t.Fatal("first actual native text did not reach both snapshot formats")
	}
	loadedObjectFixtureEdit(t, f, id, laterBody)
	stale, err := nativeexport.CaptureNativeObjectWitness(f.ctx, exporter, before, id, 1<<20)
	if stale != nil || !errors.Is(err, nativeexport.ErrNativeObjectWitness) {
		t.Fatal("old captured heads admitted a later real native version")
	}
	captured, err := f.service.CaptureLoadedAccountObjectWitness(f.ctx, f.token,
		LoadedAccountObjectWitnessRequest{Source: f.request(), ObjectIDs: []string{archivedID, id}})
	if err != nil {
		t.Fatal(err)
	}
	receipt, err := captured.Receipt()
	if err != nil {
		t.Fatal(err)
	}
	if receipt.SelectedObjects != 2 || receipt.UnrepresentedNativeTrees == 0 ||
		!receipt.AccountSessionAuthorizedAtFinalCapture || !receipt.SelectedObjectsBoundToNativeCheckpoint ||
		!receipt.OriginalNativeRowsRetained || receipt.Inventory.ChangeRecords < 3 ||
		receipt.IndexResolverSnapshotBound || receipt.HistorySemanticsValidated ||
		receipt.SemanticCompleteness || receipt.FilePayloadCompleteness ||
		receipt.HasNativeSourceAdmission || receipt.PermitsDestinationWrites {
		t.Fatal("actual selected capture overclaimed broader migration scope")
	}
	objects := captured.Objects()
	var current *nativeexport.NativeObjectWitness
	for _, object := range objects {
		if object.ObjectID() == id {
			current = object
		}
		loadedFixtureWrite(t, filepath.Join(f.dir, loadedFixtureHash([]byte(object.ObjectID()))+".snapshot.pb"), object.SnapshotBase())
		loadedFixtureWrite(t, filepath.Join(f.dir, loadedFixtureHash([]byte(object.ObjectID()))+".anyblock.json"), object.AnyBlock())
	}
	if current == nil || !bytes.Contains(current.AnyBlock(), []byte(laterBody)) ||
		!bytes.Contains(current.SnapshotBase(), []byte(laterBody)) ||
		reflect.DeepEqual(current.Heads(), oldObject.Heads()) {
		t.Fatal("current native state was not joined to its changed actual heads")
	}
	// Mutating all exported slices must not alter the captured source bytes.
	snapshot, document, heads := current.SnapshotBase(), current.AnyBlock(), current.Heads()
	snapshot[0] ^= 1
	document[0] ^= 1
	heads[0] = "not-native"
	objects[0] = nil
	if !bytes.Contains(current.AnyBlock(), []byte(laterBody)) ||
		!bytes.Contains(current.SnapshotBase(), []byte(laterBody)) ||
		captured.Objects()[0] == nil {
		t.Fatal("detached native object capture was mutable through its accessors")
	}
	raw, err := json.Marshal(receipt)
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Contains(raw, []byte(id)) || bytes.Contains(raw, []byte(laterBody)) {
		t.Fatal("safe selected-capture receipt exposed private source data")
	}
	f.preserve(t, "selected-native-source", captured.source, map[string]any{
		"actualNativeObjectCreation": true, "actualNativeVersionChange": true,
		"oldHeadsRefused": true, "selectedObjects": 2, "archivedObjectSelected": true,
		"fullSpaceMigration": false,
	})
	loadedFixtureWrite(t, filepath.Join(f.dir, "selected-object-receipt.json"), raw)
	t.Logf("LOADED_OBJECT_WITNESS %s", raw)
}

type loadedObjectExportForwarder struct{ nativeexport.Export }

func TestLoadedAccountObjectWitnessRefusesInvalidSelectionAndSession(t *testing.T) {
	f := newLoadedAccountFixture(t)
	id := loadedObjectFixturePage(t, f, "מקור לבדיקת סירוב", false)
	request := LoadedAccountObjectWitnessRequest{Source: f.request(), ObjectIDs: []string{id}}
	for _, mode := range []string{"duplicate", "missing-object", "tiny-budget", "unbound-session", "cancelled"} {
		t.Run(mode, func(t *testing.T) {
			candidate, token, ctx := request, f.token, f.ctx
			switch mode {
			case "duplicate":
				candidate.ObjectIDs = []string{id, id}
			case "missing-object":
				candidate.ObjectIDs = []string{"absent-native-object"}
			case "tiny-budget":
				candidate.MaxObjectBytes = 1
			case "unbound-session":
				token = "unregistered-native-session"
			case "cancelled":
				var cancel context.CancelFunc
				ctx, cancel = context.WithCancel(f.ctx)
				cancel()
			}
			captured, err := f.service.CaptureLoadedAccountObjectWitness(ctx, token, candidate)
			if captured != nil || err == nil {
				t.Fatal("invalid selected capture admitted")
			}
		})
	}
	inventory := loadedObjectFixtureInventory(t, f)
	actual, ok := f.service.GetApp().Component(nativeexport.CName).(nativeexport.Export)
	if !ok {
		t.Fatal("actual export service absent")
	}
	forwarded, err := nativeexport.CaptureNativeObjectWitness(f.ctx,
		loadedObjectExportForwarder{actual}, inventory, id, 1<<20)
	if forwarded != nil || !errors.Is(err, nativeexport.ErrNativeObjectWitness) {
		t.Fatal("interface forwarder replaced concrete native export ownership")
	}
	if err := f.service.CloseSession(&pb.RpcWalletCloseSessionRequest{Token: f.token}); err != nil {
		t.Fatal(err)
	}
	closed, err := f.service.CaptureLoadedAccountObjectWitness(f.ctx, f.token, request)
	if closed != nil || !errors.Is(err, ErrLoadedAccountWitnessSession) {
		t.Fatal("actual closed session admitted a new object capture")
	}
	f.privateNote(t, "selected-object-refusals", map[string]any{
		"completed": true, "actualClosedSessionRefused": true,
		"concreteExportForwarderRefused": true, "productionDestinationCalls": 0,
	})
}
