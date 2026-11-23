package service

import (
	"context"
	"errors"
	"time"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
)

// PinkhaSemanticAnchorCapture is an additive gomobile byte entry. It does not
// register a generated RPC, select an account or enable an app capability. The
// native typed entry supplies the same current writer lifetime, ACL and text /
// all-mark CAS as the non-wire path; no caller authority flags are accepted.
func PinkhaSemanticAnchorCapture(raw []byte) (response []byte) {
	defer func() {
		if value := recover(); value != nil {
			response = semanticanchor.CaptureWireFailure("uncertain")
			if PanicHandler != nil {
				PanicHandler(value)
			}
		}
	}()
	request, err := semanticanchor.CaptureFromWire(raw)
	if err != nil {
		return semanticCaptureError(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	sessionCtx := session.NewContext()
	receipt, err := mw.NativeSemanticAnchorCapture(ctx, sessionCtx, request)
	if err != nil {
		return semanticCaptureError(err)
	}
	event := sessionCtx.GetResponseEvent()
	if event == nil || event.ContextId != request.ObjectID || len(event.Messages) == 0 || event.Size() > semanticanchor.MaxCaptureNativeEventBytes {
		return semanticanchor.CaptureWireFailure("uncertain")
	}
	rawEvent, err := event.Marshal()
	if err != nil {
		return semanticanchor.CaptureWireFailure("uncertain")
	}
	return semanticanchor.CaptureWireSuccess(receipt, rawEvent)
}

func semanticCaptureError(err error) []byte {
	outcome := "unavailable"
	switch {
	case errors.Is(err, semanticanchor.ErrUncertain):
		outcome = "uncertain"
	case errors.Is(err, semanticanchor.ErrUnsupportedVersion):
		outcome = "unsupportedVersion"
	case errors.Is(err, semanticanchor.ErrLimit):
		outcome = "limit"
	case errors.Is(err, semanticanchor.ErrInvalid):
		outcome = "invalid"
	case errors.Is(err, list.ErrInsufficientPermissions):
		outcome = "permissionDenied"
	case errors.Is(err, semanticanchor.ErrConflict):
		outcome = "changed"
	case errors.Is(err, semanticanchor.ErrAlreadyLinked), errors.Is(err, semanticanchor.ErrDuplicate):
		outcome = "alreadyLinked"
	case errors.Is(err, semanticanchor.ErrPendingEdit):
		outcome = "pendingEdit"
	}
	return semanticanchor.CaptureWireFailure(outcome)
}
