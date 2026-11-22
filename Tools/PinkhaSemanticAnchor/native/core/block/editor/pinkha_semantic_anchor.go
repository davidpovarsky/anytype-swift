package editor

import (
	"context"

	"github.com/anyproto/anytype-heart/core/block/editor/stext"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
)

func (p *Page) CaptureSemanticAnchor(ctx context.Context, sessionCtx session.Context,
	request semanticanchor.CaptureRequest) (semanticanchor.Receipt, error) {
	component, ok := p.Text.(stext.SemanticAnchors)
	if !ok || p.Id() != request.ObjectID || p.SpaceID() != request.SpaceID {
		return semanticanchor.Receipt{}, semanticanchor.ErrUnavailable
	}
	return component.CaptureSemanticAnchor(ctx, sessionCtx, request)
}
