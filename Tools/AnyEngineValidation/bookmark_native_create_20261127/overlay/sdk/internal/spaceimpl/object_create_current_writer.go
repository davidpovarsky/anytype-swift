package spaceimpl

import (
	"context"
	"fmt"

	"github.com/anyproto/any-sync-sdk/internal/bookmarkcreate"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/properties"
	"github.com/anyproto/any-sync-sdk/internal/spaceobjects"
	"github.com/anyproto/any-sync-sdk/space"
)

func (o *objectService) CreateCurrentWriter(ctx context.Context, opts space.CreateObjectOpts) (space.CurrentWriterCreateResult, error) {
	return o.createCurrentWriter(ctx, opts, nil)
}

func (o *objectService) createCurrentWriter(ctx context.Context, opts space.CreateObjectOpts, bookmarkFrame *bookmarkcreate.Frame) (space.CurrentWriterCreateResult, error) {
	result := space.CurrentWriterCreateResult{CreationStage: "validation", Cleanup: "not-needed", Outcome: "refused"}
	if opts.From != "" {
		return result, fmt.Errorf("%w: current-writer creation does not copy templates or objects", crdt.ErrValidation)
	}
	if opts.Type == "" {
		return result, space.ErrTypeRequired
	}
	if properties.IsMetaType(opts.Type) {
		return result, space.ErrMetaType
	}
	if bookmarkFrame != nil {
		if err := o.parent.store.CheckBookmarkCreateFrame(ctx, *bookmarkFrame); err != nil {
			return result, err
		}
	}
	_, state, err := o.parent.store.CreateCurrentWriter(ctx, spaceobjects.CreateOpts{ChangeType: objectChangeType})
	result.ObjectID = state.ObjectID
	if state.ObjectID != "" {
		result.CreationStage = "root-prepared"
	}
	if state.StorageAttempted {
		result.Outcome = "uncertain"
		result.Cleanup = "not-attempted"
	}
	if state.RootStored {
		result.CreationStage = "root-stored"
	}
	if err != nil {
		return result, err
	}
	receipt, err := o.bootstrapWithWriterAndBookmark(ctx, state.ObjectID, opts, true, bookmarkFrame)
	if err != nil {
		return result, err
	}
	if len(receipt.Rejections) > 0 {
		result.CreationStage = "bootstrap-stored"
		return result, fmt.Errorf("%w: native object bootstrap contains rejections", crdt.ErrValidation)
	}
	result.CreationStage = "complete"
	result.Outcome = "created"
	result.Cleanup = "not-needed"
	return result, nil
}

// A post-root failure retains its known ID and uncertain state. In particular,
// an AddContent error may follow durable storage. No best-effort delete here
// can race a stored successful bootstrap and erase the caller's new object.
// Reconciliation uses this explicit ID; this API does not promise exactly-once
// creation after a response is lost.
