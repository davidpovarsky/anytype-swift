package blockjournalprobe

import (
	"testing"

	"github.com/gogo/protobuf/types"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/simple"
	_ "github.com/anyproto/anytype-heart/core/block/simple/text"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/util/pbtypes"
)

const (
	rootID   = "root"
	anchorID = "anchor"
)

func baseState(withAnchor bool) *state.State {
	children := []string(nil)
	blocks := map[string]simple.Block{
		rootID: simple.New(&model.Block{
			Id: rootID,
			Content: &model.BlockContentOfSmartblock{
				Smartblock: &model.BlockContentSmartblock{},
			},
		}),
	}
	if withAnchor {
		children = []string{anchorID, "sibling"}
		blocks[anchorID] = operationBlock(anchorID, "anchor")
		blocks["sibling"] = operationBlock("sibling", "sibling")
	}
	blocks[rootID].Model().ChildrenIds = children
	return state.NewDoc(rootID, blocks).(*state.State)
}

func operationBlock(id, payload string) simple.Block {
	return simple.New(&model.Block{
		Id: id,
		Content: &model.BlockContentOfText{Text: &model.BlockContentText{
			Text:  payload,
			Style: model.BlockContentText_Paragraph,
		}},
		Fields: &types.Struct{Fields: map[string]*types.Value{
			"pinkhaPayloadHash": pbtypes.String("sha256:" + payload),
		}},
	})
}

func createChanges(t *testing.T, original *state.State, id, payload, target string, position model.BlockPosition) []*pb.ChangeContent {
	t.Helper()
	branch := original.Copy()
	edit := branch.NewState()
	if !edit.Add(operationBlock(id, payload)) {
		t.Fatalf("Add(%q) unexpectedly rejected", id)
	}
	if err := edit.InsertTo(target, position, id); err != nil {
		t.Fatalf("InsertTo(%q): %v", target, err)
	}
	if _, _, err := state.ApplyState("probe-space", edit, true); err != nil {
		t.Fatalf("ApplyState create %q: %v", id, err)
	}
	changes := edit.GetChanges()
	if len(changes) != 1 || changes[0].GetBlockCreate() == nil {
		t.Fatalf("expected one BlockCreate change, got %#v", changes)
	}
	return changes
}

func applyChanges(t *testing.T, original *state.State, changes ...[]*pb.ChangeContent) *state.State {
	t.Helper()
	doc := original.Copy()
	for _, batch := range changes {
		edit := doc.NewState()
		if err := edit.ApplyChange(batch...); err != nil {
			t.Fatalf("ApplyChange: %v", err)
		}
		if _, _, err := state.ApplyState("probe-space", edit, true); err != nil {
			t.Fatalf("ApplyState replay: %v", err)
		}
	}
	return doc
}

func childCount(doc *state.State, id string) int {
	count := 0
	for _, childID := range doc.Pick(rootID).Model().ChildrenIds {
		if childID == id {
			count++
		}
	}
	return count
}

func textPayload(t *testing.T, doc *state.State, id string) string {
	t.Helper()
	b := doc.Pick(id)
	if b == nil || b.Model().GetText() == nil {
		t.Fatalf("block %q or text payload missing", id)
	}
	return b.Model().GetText().Text
}

func snapshotRoundTrip(t *testing.T, doc *state.State) *state.State {
	t.Helper()
	rebuilt, err := state.NewDocFromSnapshot(rootID, &pb.ChangeSnapshot{
		Data: &model.SmartBlockSnapshotBase{Blocks: doc.Blocks()},
	})
	if err != nil {
		t.Fatalf("NewDocFromSnapshot: %v", err)
	}
	return rebuilt
}

func TestInitialCreateRetainsCallerIDAndPayloadAcrossSnapshot(t *testing.T) {
	original := baseState(true)
	changes := createChanges(t, original, "op-deterministic-001", "payload-v1", rootID, model.Block_Inner)
	created := changes[0].GetBlockCreate().Blocks[0]
	if created.Id != "op-deterministic-001" {
		t.Fatalf("caller ID changed in create: %q", created.Id)
	}
	if got := created.GetText().Text; got != "payload-v1" {
		t.Fatalf("initial content missing from create: %q", got)
	}
	if got := pbtypes.GetString(created.Fields, "pinkhaPayloadHash"); got != "sha256:payload-v1" {
		t.Fatalf("initial fields missing from create: %q", got)
	}

	rebuilt := snapshotRoundTrip(t, applyChanges(t, original, changes))
	if got := textPayload(t, rebuilt, "op-deterministic-001"); got != "payload-v1" {
		t.Fatalf("payload changed after snapshot rebuild: %q", got)
	}
	if got := pbtypes.GetString(rebuilt.Pick("op-deterministic-001").Model().Fields, "pinkhaPayloadHash"); got != "sha256:payload-v1" {
		t.Fatalf("fields changed after snapshot rebuild: %q", got)
	}
	if got := pbtypes.GetString(rebuilt.Pick(anchorID).Model().Fields, "pinkhaPayloadHash"); got != "sha256:anchor" {
		t.Fatalf("unrelated existing block fields changed: %q", got)
	}
	t.Log("caller ID, initial payload and fields survived BlockCreate replay plus snapshot rebuild; unrelated fields stayed intact")
}

func TestDuplicateSameIDIdenticalPayloadCollapsesToOneReachableBlock(t *testing.T) {
	original := baseState(false)
	a := createChanges(t, original, "op-same", "identical", rootID, model.Block_Inner)
	b := createChanges(t, original, "op-same", "identical", rootID, model.Block_Inner)

	for name, batches := range map[string][][]*pb.ChangeContent{
		"A-then-B": {a, b},
		"B-then-A": {b, a},
	} {
		t.Run(name, func(t *testing.T) {
			doc := snapshotRoundTrip(t, applyChanges(t, original, batches...))
			if got := childCount(doc, "op-same"); got != 1 {
				t.Fatalf("reachable occurrences = %d, want 1", got)
			}
			if got := textPayload(t, doc, "op-same"); got != "identical" {
				t.Fatalf("payload = %q", got)
			}
		})
	}
	t.Log("state replay collapses identical duplicate IDs to one reachable block in either order")
}

func TestDuplicateSameIDDifferentPayloadSilentlyLastReplayWins(t *testing.T) {
	original := baseState(false)
	a := createChanges(t, original, "op-collision", "payload-A", rootID, model.Block_Inner)
	b := createChanges(t, original, "op-collision", "payload-B", rootID, model.Block_Inner)

	ab := snapshotRoundTrip(t, applyChanges(t, original, a, b))
	ba := snapshotRoundTrip(t, applyChanges(t, original, b, a))
	if got := textPayload(t, ab, "op-collision"); got != "payload-B" {
		t.Fatalf("A->B payload = %q, want last replay payload-B", got)
	}
	if got := textPayload(t, ba, "op-collision"); got != "payload-A" {
		t.Fatalf("B->A payload = %q, want last replay payload-A", got)
	}
	if childCount(ab, "op-collision") != 1 || childCount(ba, "op-collision") != 1 {
		t.Fatal("collision should leave exactly one reachable ID in each order")
	}
	t.Log("no conflict/error was returned; differing payload is silently replaced and final content depends on replay order")
}

func TestDistinctIDsAtSameAnchorBothSurviveButSiblingOrderFollowsReplay(t *testing.T) {
	original := baseState(false)
	a := createChanges(t, original, "op-A", "payload-A", rootID, model.Block_Inner)
	b := createChanges(t, original, "op-B", "payload-B", rootID, model.Block_Inner)

	ab := snapshotRoundTrip(t, applyChanges(t, original, a, b))
	ba := snapshotRoundTrip(t, applyChanges(t, original, b, a))
	for _, doc := range []*state.State{ab, ba} {
		if childCount(doc, "op-A") != 1 || childCount(doc, "op-B") != 1 {
			t.Fatalf("both IDs did not survive: %v", doc.Pick(rootID).Model().ChildrenIds)
		}
	}
	if got := ab.Pick(rootID).Model().ChildrenIds; len(got) != 2 || got[0] != "op-A" || got[1] != "op-B" {
		t.Fatalf("A->B order = %v", got)
	}
	if got := ba.Pick(rootID).Model().ChildrenIds; len(got) != 2 || got[0] != "op-B" || got[1] != "op-A" {
		t.Fatalf("B->A order = %v", got)
	}
	t.Log("both distinct IDs survive; raw state replay order controls sibling order")
}

func TestRemovedAnchorMakesCreateUnreachableWhenReplayErrorIsIgnored(t *testing.T) {
	original := baseState(true)
	create := createChanges(t, original, "op-after-anchor", "payload", anchorID, model.Block_Bottom)
	remove := &pb.ChangeContent{Value: &pb.ChangeContentValueOfBlockRemove{
		BlockRemove: &pb.ChangeBlockRemove{Ids: []string{anchorID}},
	}}

	doc := original.Copy()
	removeEdit := doc.NewState()
	if err := removeEdit.ApplyChange(remove); err != nil {
		t.Fatalf("remove anchor: %v", err)
	}
	if _, _, err := state.ApplyState("probe-space", removeEdit, true); err != nil {
		t.Fatalf("apply removed anchor: %v", err)
	}

	createEdit := doc.NewState()
	createEdit.ApplyChangeIgnoreErr(create...)
	if childCount(createEdit, "op-after-anchor") != 0 {
		t.Fatalf("operation unexpectedly reachable: %v", createEdit.Pick(rootID).Model().ChildrenIds)
	}
	if createEdit.Pick("op-after-anchor") == nil {
		t.Fatal("expected replay to Set the block before target insertion failed")
	}
	if _, _, err := state.ApplyState("probe-space", createEdit, true); err != nil {
		t.Fatalf("normalizing ignored replay: %v", err)
	}
	if childCount(doc, "op-after-anchor") != 0 {
		t.Fatalf("operation became reachable after apply: %v", doc.Pick(rootID).Model().ChildrenIds)
	}
	t.Log("production-style ApplyChangeIgnoreErr silently leaves/drops a create whose positional anchor was removed")
}
