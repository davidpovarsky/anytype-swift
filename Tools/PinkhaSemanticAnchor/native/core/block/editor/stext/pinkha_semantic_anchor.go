package stext

import (
	"context"
	"errors"
	"slices"

	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/core/block/simple/text"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
)

// SemanticAnchors is additive. Existing Text methods, buffered typing, legacy
// offsets, normal Undo history and the generated RPC surface are unchanged.
type SemanticAnchors interface {
	CaptureSemanticAnchor(context.Context, session.Context, semanticanchor.CaptureRequest) (semanticanchor.Receipt, error)
}

func semanticSnapshot(content *model.BlockContentText) (semanticanchor.Snapshot, error) {
	if content == nil {
		return semanticanchor.Snapshot{}, semanticanchor.ErrUnavailable
	}
	snapshot := semanticanchor.Snapshot{Text: content.Text}
	if len(content.GetMarks().GetMarks()) > semanticanchor.MaxMarks {
		return snapshot, semanticanchor.ErrLimit
	}
	for _, mark := range content.GetMarks().GetMarks() {
		if mark == nil || mark.Range == nil {
			return semanticanchor.Snapshot{}, semanticanchor.ErrInvalid
		}
		snapshot.Marks = append(snapshot.Marks, semanticanchor.Mark{
			From: mark.Range.From, To: mark.Range.To, Kind: int32(mark.Type), Param: mark.Param})
	}
	return snapshot, snapshot.Validate()
}

func semanticNativeMarks(snapshot semanticanchor.Snapshot) *model.BlockContentTextMarks {
	marks := &model.BlockContentTextMarks{}
	for _, mark := range snapshot.Marks {
		marks.Marks = append(marks.Marks, &model.BlockContentTextMark{Range: &model.Range{From: mark.From, To: mark.To},
			Type: model.BlockContentTextMarkType(mark.Kind), Param: mark.Param})
	}
	return marks
}

func (t *textImpl) CaptureSemanticAnchor(ctx context.Context, sessionCtx session.Context,
	request semanticanchor.CaptureRequest) (semanticanchor.Receipt, error) {
	if _, err := request.Validate(); err != nil {
		return semanticanchor.Receipt{}, err
	}
	validate, err := torahopsobject.BorrowNativeSemanticAnchorLease(ctx, t.Tree(), request)
	if err != nil {
		return semanticanchor.Receipt{}, err
	}
	return t.captureSemanticAnchorLocked(ctx, sessionCtx, request, validate,
		func(before, after string, heads []string) (string, error) {
			return torahopsobject.VerifySemanticAnchorNativeChange(ctx, t.Tree(), before, after, heads)
		})
}

// The private helper permits focused fault injection of Apply/readback while
// the exported entry always requires the real native lease and storage witness.
func (t *textImpl) captureSemanticAnchorLocked(ctx context.Context, sessionCtx session.Context,
	request semanticanchor.CaptureRequest, validate func() error,
	witness func(string, string, []string) (string, error)) (semanticanchor.Receipt, error) {
	empty := semanticanchor.Receipt{}
	if ctx == nil || sessionCtx == nil || validate == nil || witness == nil {
		return empty, semanticanchor.ErrInvalid
	}
	if err := validate(); err != nil {
		return empty, err
	}
	// NewStateCtx's current flush hook discards Apply errors. Refuse before
	// invoking it, leaving the existing delayed text batch entirely untouched.
	if t.lastSetTextState != nil {
		return empty, semanticanchor.ErrPendingEdit
	}
	block, ok := t.Pick(request.BlockID).(text.Block)
	if !ok || block == nil || block.Model() == nil {
		return empty, semanticanchor.ErrUnavailable
	}
	if _, details := block.(text.DetailsBlock); details {
		return empty, semanticanchor.ErrUnavailable
	}
	before, err := semanticSnapshot(block.Model().GetText())
	if err != nil {
		return empty, err
	}
	after, err := request.Plan(before)
	if err != nil {
		return empty, err
	}
	if t.Tree() == nil {
		return empty, semanticanchor.ErrUnavailable
	}
	s := t.NewStateCtx(sessionCtx)
	// An unrelated native NewState hook is allowed to run. It cannot make the
	// previously captured text/marks comparison silently become stale.
	currentBlock := t.Pick(request.BlockID)
	if currentBlock == nil || currentBlock.Model() == nil {
		return empty, semanticanchor.ErrConflict
	}
	current, err := semanticSnapshot(currentBlock.Model().GetText())
	if err != nil || !before.Exact(current) {
		return empty, errors.Join(semanticanchor.ErrConflict, err)
	}
	child := s.Get(request.BlockID)
	if child == nil || child.Model() == nil || child.Model().GetText() == nil {
		return empty, semanticanchor.ErrUnavailable
	}
	childBefore, err := semanticSnapshot(child.Model().GetText())
	if err != nil || !before.Exact(childBefore) {
		return empty, errors.Join(semanticanchor.ErrConflict, err)
	}
	// Append only the planned markup. Do not call SetText, normalize existing
	// links, overwrite style or toggle every link mark via the legacy SetMark.
	child.Model().GetText().Marks = semanticNativeMarks(after)
	if err = validate(); err != nil {
		return empty, err
	}
	beforeChangeID := t.ChangeId()
	beforeHeads := slices.Clone(t.Tree().Heads())
	if len(beforeHeads) == 0 {
		return empty, semanticanchor.ErrUnavailable
	}
	if err = t.Apply(s); err != nil {
		// Normal Apply can mutate memory before PushChange fails, or the native
		// tree can commit before a later head-update error. No blind rollback or
		// synthetic success is safe; callers must re-read current native state.
		return empty, errors.Join(semanticanchor.ErrUncertain, err)
	}
	if err = validate(); err != nil {
		return empty, errors.Join(semanticanchor.ErrUncertain, err)
	}
	actualBlock := t.Pick(request.BlockID)
	if actualBlock == nil || actualBlock.Model() == nil {
		return empty, semanticanchor.ErrUncertain
	}
	actual, err := semanticSnapshot(actualBlock.Model().GetText())
	if err != nil || !after.SameMarks(actual) {
		return empty, errors.Join(semanticanchor.ErrUncertain, err)
	}
	changeID := t.ChangeId()
	if changeID == "" || changeID == beforeChangeID {
		return empty, semanticanchor.ErrUncertain
	}
	nativeSHA, err := witness(beforeChangeID, changeID, beforeHeads)
	if err != nil || len(nativeSHA) != 64 {
		return empty, errors.Join(semanticanchor.ErrUncertain, err)
	}
	if err = validate(); err != nil {
		return empty, errors.Join(semanticanchor.ErrUncertain, err)
	}
	marker, _ := request.Validate()
	return semanticanchor.Receipt{Version: semanticanchor.Version, SpaceID: request.SpaceID, ObjectID: request.ObjectID,
		BlockID: request.BlockID, AnchorID: request.AnchorID, Marker: marker, ChangeID: changeID,
		NativeChangeSHA256: nativeSHA, BeforeTextMarksSHA256: before.Digest(), AfterTextMarksSHA256: actual.Digest()}, nil
}
