package fileuploader

import (
	"context"
	"errors"

	"github.com/anyproto/anytype-heart/core/block/cache"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/domain"
)

var ErrOwnedUploadUnavailable = errors.New("owned original uploader is unavailable")
var ErrOwnedUploadCompletion = errors.New("owned original uploader returned an invalid completion")

// OwnedUploadOutcome is a historical result of one original upload attempt. It
// does not prove that the final block reference was applied: the original
// updateBlock logs that error, and full native semantic readback is still needed.
// No mutable details or encryption-key maps are exposed by this value.
type OwnedUploadOutcome struct {
	FileObjectID          string
	Name                  string
	MIME                  string
	Size                  int64
	CancellationRequested bool
	Err                   error
}

// OwnedUpload can only be initialized by StartOwnedUpload with the original
// concrete uploader. Its zero value is not a completed native operation.
type OwnedUpload struct {
	done    chan struct{}
	cancel  context.CancelFunc
	outcome OwnedUploadOutcome
}

// StartOwnedUpload retains the real original asynchronous completion channel.
// The caller must exclusively own the prepared uploader and register a returned
// handle even if a later containing operation fails. It never cancels the global
// uploader service or consumes a shared preload owned by a different operation.
func StartOwnedUpload(ctx context.Context, prepared Uploader) (*OwnedUpload, error) {
	if ctx == nil {
		return nil, ErrOwnedUploadUnavailable
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	native, ok := prepared.(*uploader)
	if !ok || native == nil || native.serviceCtx == nil || native.serviceCtx.Err() != nil || native.preloadId != "" {
		return nil, ErrOwnedUploadUnavailable
	}
	ownedCtx, cancel := context.WithCancel(ctx)
	stopServiceCancellation := context.AfterFunc(native.serviceCtx, cancel)
	owned := &OwnedUpload{done: make(chan struct{}), cancel: cancel}
	// The original asynchronous final block update uses cache.Do, whose generic
	// context must also be bound to this operation's cancellation. The original
	// prepared uploader itself is not changed or reused by another operation.
	ownedNative := *native
	ownedNative.picker = ownedUploadObjectGetter{original: native.picker, ctx: ownedCtx}
	actual := ownedNative.uploadAsync(ownedCtx)
	go func() {
		var result UploadResult
		count := 0
		for value := range actual {
			count++
			if count == 1 {
				result = value
			}
		}
		owned.outcome = OwnedUploadOutcome{
			FileObjectID:          result.FileObjectId,
			Name:                  result.Name,
			MIME:                  result.MIME,
			Size:                  result.Size,
			CancellationRequested: ownedCtx.Err() != nil,
			Err:                   result.Err,
		}
		if count != 1 {
			owned.outcome.Err = errors.Join(owned.outcome.Err, ErrOwnedUploadCompletion)
		}
		stopServiceCancellation()
		cancel()
		// Only exhaustion of the actual native result channel publishes drain.
		close(owned.done)
	}()
	return owned, nil
}

type ownedUploadObjectGetter struct {
	original cache.ObjectGetter
	ctx      context.Context
}

func (g ownedUploadObjectGetter) GetObject(_ context.Context, objectID string) (smartblock.SmartBlock, error) {
	return g.original.GetObject(g.ctx, objectID)
}

func (g ownedUploadObjectGetter) GetObjectByFullID(_ context.Context, id domain.FullID) (smartblock.SmartBlock, error) {
	return g.original.GetObjectByFullID(g.ctx, id)
}

// RequestCancel requests cancellation; it never publishes a drained result.
func (u *OwnedUpload) RequestCancel() {
	if u != nil && u.cancel != nil {
		u.cancel()
	}
}

// Done closes only after the original upload result channel has closed. For a
// nil or zero handle it returns nil, which cannot manufacture completion.
func (u *OwnedUpload) Done() <-chan struct{} {
	if u == nil {
		return nil
	}
	return u.done
}

// Result reports a copied result only after actual completion. It does not wait.
func (u *OwnedUpload) Result() (OwnedUploadOutcome, bool) {
	if u == nil || u.done == nil {
		return OwnedUploadOutcome{}, false
	}
	select {
	case <-u.done:
		return u.outcome, true
	default:
		return OwnedUploadOutcome{}, false
	}
}
