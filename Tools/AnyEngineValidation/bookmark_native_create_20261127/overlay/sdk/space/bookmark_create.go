package space

import (
	"context"

	"github.com/anyproto/any-sync-sdk/internal/bookmarkcreate"
)

const BookmarkCreateContract = bookmarkcreate.Contract
const BookmarkCreateMaxFrameBytes = bookmarkcreate.MaxFrameBytes
const BookmarkCreateMaxEncodedFrameBytes = bookmarkcreate.MaxFrameEncodedBytes

var ErrBookmarkCreateInvalid = bookmarkcreate.ErrInvalid
var ErrBookmarkCreateChanged = bookmarkcreate.ErrChanged
var ErrBookmarkCreateIneligible = bookmarkcreate.ErrIneligible

type BookmarkCreateFrame = bookmarkcreate.Response

// ReadBookmarkCreateFrame is an opt-in read of the complete current descriptor
// dependency set. A frame is not a write grant: the subsequent create uses the
// original current-writer storage fence independently.
func ReadBookmarkCreateFrame(ctx context.Context, sp Space, typeID string, collections []string) (BookmarkCreateFrame, error) {
	type reader interface {
		ReadBookmarkCreateFrame(context.Context, string, []string) (BookmarkCreateFrame, error)
	}
	if sp == nil {
		return BookmarkCreateFrame{}, ErrCurrentWriterUnavailable
	}
	implementation, ok := sp.Objects().(reader)
	if !ok {
		return BookmarkCreateFrame{}, ErrCurrentWriterUnavailable
	}
	return implementation.ReadBookmarkCreateFrame(ctx, typeID, collections)
}

// CreateCurrentWriterWithBookmarkFrame retains the ordinary root/bootstrap
// outcome carrier. An accepted frame does not make these two stores atomic,
// and any post-root refusal still carries its original known object ID.
func CreateCurrentWriterWithBookmarkFrame(ctx context.Context, sp Space, opts CreateObjectOpts, frame string) (CurrentWriterCreateResult, error) {
	type creator interface {
		CreateCurrentWriterWithBookmarkFrame(context.Context, CreateObjectOpts, string) (CurrentWriterCreateResult, error)
	}
	if sp == nil {
		return CurrentWriterCreateResult{}, ErrCurrentWriterUnavailable
	}
	implementation, ok := sp.Objects().(creator)
	if !ok {
		return CurrentWriterCreateResult{}, ErrCurrentWriterUnavailable
	}
	return implementation.CreateCurrentWriterWithBookmarkFrame(ctx, opts, frame)
}
