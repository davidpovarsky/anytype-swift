package spaceimpl

import (
	"context"
	"slices"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/bookmarkcreate"
	"github.com/anyproto/any-sync-sdk/space"
)

func (o *objectService) ReadBookmarkCreateFrame(ctx context.Context, typeID string, collections []string) (space.BookmarkCreateFrame, error) {
	return o.parent.store.ReadBookmarkCreateFrame(ctx, typeID, collections)
}

func (o *objectService) CreateCurrentWriterWithBookmarkFrame(ctx context.Context, opts space.CreateObjectOpts, token string) (space.CurrentWriterCreateResult, error) {
	refused := space.CurrentWriterCreateResult{CreationStage: "validation", Cleanup: "not-needed", Outcome: "refused"}
	frame, err := bookmarkcreate.Decode(token)
	if err != nil {
		return refused, err
	}
	if opts.From != "" || opts.Type != frame.TypeID || !slices.Equal(opts.Collections, frame.Collections) {
		return refused, bookmarkcreate.ErrInvalid
	}
	for owner, properties := range opts.InitialProperties {
		if owner != "any" && owner != frame.TypeID && !slices.Contains(frame.Collections, owner) {
			return refused, bookmarkcreate.ErrInvalid
		}
		if owner == "any" {
			for _, key := range []string{"type", "collections", "template"} {
				if _, present := properties[key]; present {
					return refused, bookmarkcreate.ErrInvalid
				}
			}
		}
	}
	value, present := opts.InitialProperties[frame.PropertyOwnerID][frame.PropertyID]
	if !present {
		return refused, bookmarkcreate.ErrInvalid
	}
	arena := &anyenc.Arena{}
	nativeValue, err := goToAnyenc(arena, value)
	if err != nil || nativeValue == nil || nativeValue.Type() != anyenc.TypeString {
		return refused, bookmarkcreate.ErrInvalid
	}
	return o.createCurrentWriter(ctx, opts, &frame)
}
