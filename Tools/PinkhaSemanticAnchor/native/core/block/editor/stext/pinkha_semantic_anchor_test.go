package stext

import (
	"context"
	"errors"
	"slices"
	"strings"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock/smarttest"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/block/simple/text"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
	"github.com/stretchr/testify/require"
)

// These component controls use the real text/state diff and SmartTest Apply,
// with explicit fault injection at Apply and the native storage witness. They
// are not evidence of a signed native commit or an account lifecycle journey.
type semanticComponentTree struct {
	objecttree.ObjectTree
	heads []string
}

func (tree *semanticComponentTree) Heads() []string { return slices.Clone(tree.heads) }

type semanticComponentBlock struct {
	*smarttest.SmartTest
	tree               *semanticComponentTree
	newStates, applies int
	mode               string
	flags              []smartblock.ApplyFlag
	onNewState         func()
}

func (block *semanticComponentBlock) NewStateCtx(ctx session.Context) *state.State {
	block.newStates++
	child := block.SmartTest.NewStateCtx(ctx)
	if block.onNewState != nil {
		block.onNewState()
	}
	return child
}

func (block *semanticComponentBlock) Apply(child *state.State, flags ...smartblock.ApplyFlag) error {
	block.applies++
	block.flags = slices.Clone(flags)
	if block.mode == "silent-noop" {
		return nil
	}
	if block.mode == "error-before-mutation" {
		return errors.New("controlled pre-mutation Apply failure")
	}
	if err := block.SmartTest.Apply(child, flags...); err != nil {
		return err
	}
	if block.mode != "missing-change-id" {
		block.Doc.(*state.State).SetChangeId("native-change-after")
		block.tree.heads = []string{"native-change-after"}
	}
	if block.mode == "post-mark-mutation" {
		block.Pick("paragraph").Model().GetText().Marks.Marks[0].Param = "changed-by-post-hook"
	}
	if block.mode == "error-after-mutation" {
		return errors.New("controlled post-mutation Apply failure")
	}
	return nil
}

func semanticTextFixture(t *testing.T) (*textImpl, *semanticComponentBlock, semanticanchor.CaptureRequest) {
	t.Helper()
	tree := &semanticComponentTree{heads: []string{"native-change-before"}}
	sb := smarttest.NewWithTree("document", tree)
	sb.SetSpaceId("space")
	sb.Doc.(*state.State).SetChangeId("native-change-before")
	sb.AddBlock(simple.New(&model.Block{Id: "document", ChildrenIds: []string{"paragraph"}}))
	sb.AddBlock(text.NewText(&model.Block{Id: "paragraph", Content: &model.BlockContentOfText{Text: &model.BlockContentText{
		Text: "אבג 😀 text", Style: model.BlockContentText_Paragraph,
		Marks: &model.BlockContentTextMarks{Marks: []*model.BlockContentTextMark{
			{Range: &model.Range{From: 0, To: 3}, Type: model.BlockContentTextMark_Bold},
			{Range: &model.Range{From: 7, To: 11}, Type: model.BlockContentTextMark_TextColor, Param: "red"},
		}},
	}}}))
	block := &semanticComponentBlock{SmartTest: sb, tree: tree}
	component := NewText(block, nil, nil).(*textImpl)
	snapshot, err := semanticSnapshot(block.Pick("paragraph").Model().GetText())
	require.NoError(t, err)
	request := semanticanchor.CaptureRequest{Version: 1, SpaceID: "space", ObjectID: "document", BlockID: "paragraph",
		AnchorID: "00112233-4455-6677-8899-aabbccddeeff", From: 4, To: 6, Expected: snapshot}
	return component, block, request
}

func TestPinkhaSemanticAnchorTextCASRefusesPendingAndAllMarkConflicts(t *testing.T) {
	for _, scenario := range []string{"pending-text", "changed-text", "changed-unselected-mark", "added-mark", "new-state-hook-changes-text"} {
		t.Run(scenario, func(t *testing.T) {
			component, block, request := semanticTextFixture(t)
			want := semanticanchor.ErrConflict
			var pending *state.State
			switch scenario {
			case "pending-text":
				pending = block.SmartTest.NewStateCtx(session.NewContext())
				pending.Get(request.BlockID).Model().GetText().Text = "unflushed native text"
				component.lastSetTextState, component.lastSetTextId = pending, request.BlockID
				want = semanticanchor.ErrPendingEdit
			case "changed-text":
				block.Pick(request.BlockID).Model().GetText().Text = "different native text"
			case "changed-unselected-mark":
				block.Pick(request.BlockID).Model().GetText().Marks.Marks[0].Type = model.BlockContentTextMark_Italic
			case "added-mark":
				block.Pick(request.BlockID).Model().GetText().Marks.Marks = append(
					block.Pick(request.BlockID).Model().GetText().Marks.Marks,
					&model.BlockContentTextMark{Range: &model.Range{From: 0, To: 1}, Type: model.BlockContentTextMark_Strikethrough})
			case "new-state-hook-changes-text":
				block.onNewState = func() { block.Pick(request.BlockID).Model().GetText().Text = "changed during native hook" }
			}
			witnessCalls := 0
			receipt, err := component.captureSemanticAnchorLocked(context.Background(), session.NewContext(), request,
				func() error { return nil }, func(string, string, []string) (string, error) { witnessCalls++; return strings.Repeat("a", 64), nil })
			require.ErrorIs(t, err, want)
			require.Equal(t, semanticanchor.Receipt{}, receipt)
			require.Zero(t, block.applies)
			require.Zero(t, witnessCalls)
			if pending != nil {
				require.Same(t, pending, component.lastSetTextState)
				require.Equal(t, request.BlockID, component.lastSetTextId)
				require.Zero(t, block.newStates, "pending batch must not invoke NewState's lossy flush hook")
				require.Equal(t, "unflushed native text", pending.Pick(request.BlockID).Model().GetText().Text)
				require.Equal(t, request.Expected.Text, block.Pick(request.BlockID).Model().GetText().Text)
			}
		})
	}
}

func TestPinkhaSemanticAnchorTextCASRequiresPostApplyStateAndNativeWitness(t *testing.T) {
	for _, scenario := range []string{"silent-noop", "error-before-mutation", "error-after-mutation", "missing-change-id", "post-mark-mutation", "native-witness-error", "authority-lost-after-apply"} {
		t.Run(scenario, func(t *testing.T) {
			component, block, request := semanticTextFixture(t)
			block.mode = scenario
			validations, witnesses := 0, 0
			receipt, err := component.captureSemanticAnchorLocked(context.Background(), session.NewContext(), request,
				func() error {
					validations++
					if scenario == "authority-lost-after-apply" && validations == 3 {
						return semanticanchor.ErrUnavailable
					}
					return nil
				}, func(string, string, []string) (string, error) {
					witnesses++
					if scenario == "native-witness-error" {
						return "", semanticanchor.ErrUncertain
					}
					return strings.Repeat("a", 64), nil
				})
			require.ErrorIs(t, err, semanticanchor.ErrUncertain)
			require.Equal(t, semanticanchor.Receipt{}, receipt)
			require.Equal(t, 1, block.applies)
			if scenario == "native-witness-error" {
				require.Equal(t, 1, witnesses)
			} else {
				require.Zero(t, witnesses)
			}
			if scenario == "error-after-mutation" {
				actual, readErr := semanticSnapshot(block.Pick(request.BlockID).Model().GetText())
				require.NoError(t, readErr)
				planned, planErr := request.Plan(request.Expected)
				require.NoError(t, planErr)
				require.True(t, planned.SameMarks(actual), "uncertain outcome must not blindly roll back native state")
			}
		})
	}
}

func TestPinkhaSemanticAnchorTextCASPreservesMarksAndNormalApplyFlags(t *testing.T) {
	component, block, request := semanticTextFixture(t)
	witnesses := 0
	receipt, err := component.captureSemanticAnchorLocked(context.Background(), session.NewContext(), request,
		func() error { return nil }, func(before, after string, heads []string) (string, error) {
			witnesses++
			require.Equal(t, "native-change-before", before)
			require.Equal(t, "native-change-after", after)
			require.Equal(t, []string{before}, heads)
			return strings.Repeat("a", 64), nil // explicit controlled witness, never a native acceptance claim
		})
	require.NoError(t, err)
	require.Equal(t, 1, witnesses)
	require.Equal(t, 1, block.applies)
	require.Empty(t, block.flags, "normal restrictions/events/hooks/undo must stay enabled")
	actual, err := semanticSnapshot(block.Pick(request.BlockID).Model().GetText())
	require.NoError(t, err)
	planned, err := request.Plan(request.Expected)
	require.NoError(t, err)
	require.True(t, planned.SameMarks(actual))
	require.Equal(t, model.BlockContentText_Paragraph, block.Pick(request.BlockID).Model().GetText().Style)
	require.Equal(t, request.Expected.Digest(), receipt.BeforeTextMarksSHA256)
	require.Equal(t, actual.Digest(), receipt.AfterTextMarksSHA256)
	require.Equal(t, "native-change-after", receipt.ChangeID)
	require.Equal(t, request.AnchorID, receipt.AnchorID)
}

func TestPinkhaSemanticAnchorTextPublicEntryRequiresNativeLease(t *testing.T) {
	component, block, request := semanticTextFixture(t)
	receipt, err := component.CaptureSemanticAnchor(context.Background(), session.NewContext(), request)
	require.ErrorIs(t, err, semanticanchor.ErrUnavailable)
	require.Equal(t, semanticanchor.Receipt{}, receipt)
	require.Zero(t, block.newStates)
	require.Zero(t, block.applies)
	validations := 0
	receipt, err = component.captureSemanticAnchorLocked(context.Background(), session.NewContext(), request,
		func() error {
			validations++
			if validations == 2 {
				return semanticanchor.ErrUnavailable
			}
			return nil
		},
		func(string, string, []string) (string, error) {
			t.Fatal("witness after refused pre-write authority")
			return "", nil
		})
	require.ErrorIs(t, err, semanticanchor.ErrUnavailable)
	require.Equal(t, semanticanchor.Receipt{}, receipt)
	require.Zero(t, block.applies)
	require.Equal(t, request.Expected.Text, block.Pick(request.BlockID).Model().GetText().Text)
}
