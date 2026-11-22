package core

import (
	"context"
	"testing"

	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
	"github.com/stretchr/testify/require"
)

func TestPinkhaSemanticAnchorNativeEntryRejectsInvalidOrCancelledBeforeAccount(t *testing.T) {
	// No application service is installed. Input failure must happen before the
	// real writer lifetime is requested; this is not a live-account acceptance.
	middleware := &Middleware{}
	request := semanticanchor.CaptureRequest{Version: 1, SpaceID: "space", ObjectID: "document", BlockID: "paragraph",
		AnchorID: "00112233-4455-6677-8899-aabbccddeeff", From: 0, To: 3, Expected: semanticanchor.Snapshot{Text: "abc"}}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	value, err := middleware.NativeSemanticAnchorCapture(ctx, session.NewContext(), request)
	require.ErrorIs(t, err, context.Canceled)
	require.Equal(t, semanticanchor.Receipt{}, value)
	value, err = middleware.NativeSemanticAnchorCapture(nil, session.NewContext(), request)
	require.ErrorIs(t, err, semanticanchor.ErrInvalid)
	require.Equal(t, semanticanchor.Receipt{}, value)
	request.From = 2
	request.To = 1
	value, err = middleware.NativeSemanticAnchorCapture(context.Background(), session.NewContext(), request)
	require.ErrorIs(t, err, semanticanchor.ErrInvalid)
	require.Equal(t, semanticanchor.Receipt{}, value)
}
