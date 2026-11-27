package server

import (
	"errors"
	"net/http"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/labstack/echo/v4"
)

// The details carry identifiers and outcome metadata only. A known native ID
// must survive an unsuccessful response; it is not evidence that the bootstrap
// completed. The host journals this ID before reconciling the original intent.
func pinkhaObjectCreateError(c echo.Context, err error, spaceID string, result space.CurrentWriterCreateResult) error {
	details := map[string]any{"spaceId": spaceID, "creationStage": result.CreationStage, "cleanup": result.Cleanup, "outcome": result.Outcome}
	if result.ObjectID != "" {
		details["objectId"] = result.ObjectID
	}
	if result.Outcome == "uncertain" && result.ObjectID != "" {
		return writeError(c, http.StatusServiceUnavailable, "pinkha.object_create_uncertain", "native object creation needs reconciliation of its known ID", details)
	}
	if response, handled := pinkhaBookmarkError(c, err); handled {
		return response
	}
	if errors.Is(err, space.ErrCurrentWriterUnavailable) {
		return writeError(c, http.StatusServiceUnavailable, "pinkha.current_writer_unavailable", "native creation authority is unavailable", nil)
	}
	return sdkOpError(c, err, details)
}
