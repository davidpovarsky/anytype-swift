package importer

import (
	"context"
	"errors"
	"sync"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	"github.com/anyproto/anytype-heart/core/files/fileuploader"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

var errOwnedImportSealed = errors.New("owned native import file admission is sealed")
var errOwnedImportPreload = errors.New("owned native import does not admit shared preloads")
var errOwnedImportBookmark = errors.New("owned native import has no joined bookmark fetch")

type ownedImportFileResult struct {
	Kind, ObjectID, BlockID, FileObjectID string
	Err                                   error
}

// A slot is registered before native upload admission, including its initial
// object-lock/Apply phase. Cancelling a context never closes ready or Done.
type ownedImportFileSlot struct {
	ready  chan struct{}
	async  *fileuploader.OwnedUpload
	result ownedImportFileResult
}

type ownedImportExecution struct {
	ctx         context.Context
	cancel      context.CancelFunc
	mu          sync.Mutex
	started     bool
	sealed      bool
	files       []*ownedImportFileSlot
	fileResults []ownedImportFileResult
}

func (o *ownedImportExecution) beginRun() error {
	o.mu.Lock()
	defer o.mu.Unlock()
	if o.started || o.sealed {
		return errOwnedImportSealed
	}
	if err := o.ctx.Err(); err != nil {
		return err
	}
	o.started = true
	return nil
}

func newOwnedImportExecution(ctx context.Context) *ownedImportExecution {
	ownedCtx, cancel := context.WithCancel(ctx)
	return &ownedImportExecution{ctx: ownedCtx, cancel: cancel}
}

func (o *ownedImportExecution) beginFile(kind, objectID, blockID string) (*ownedImportFileSlot, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if o.sealed {
		return nil, errOwnedImportSealed
	}
	if err := o.ctx.Err(); err != nil {
		return nil, err
	}
	slot := &ownedImportFileSlot{ready: make(chan struct{}), result: ownedImportFileResult{
		Kind: kind, ObjectID: objectID, BlockID: blockID,
	}}
	o.files = append(o.files, slot)
	return slot, nil
}

// sealAndDrain is called only by the owning import goroutine, after its actual
// native workers and submitters have drained. Existing initial upload calls and
// real asynchronous upload channels must finish even if cancellation was asked.
// It does not wait for component-wide remote backup synchronization.
func (o *ownedImportExecution) sealAndDrain() ([]ownedImportFileResult, error) {
	o.mu.Lock()
	o.sealed = true
	slots := append([]*ownedImportFileSlot(nil), o.files...)
	o.mu.Unlock()
	results := make([]ownedImportFileResult, 0, len(slots))
	var outcome error
	for _, slot := range slots {
		<-slot.ready
		result := slot.result
		if slot.async != nil {
			// The concrete original hook returns an initialized channel. A
			// zero handle cannot manufacture completed native work.
			<-slot.async.Done()
			actual, completed := slot.async.Result()
			if !completed {
				result.Err = errors.Join(result.Err, fileuploader.ErrOwnedUploadCompletion)
			} else {
				result.FileObjectID = actual.FileObjectID
				result.Err = errors.Join(result.Err, actual.Err)
			}
		}
		results = append(results, result)
		outcome = errors.Join(outcome, result.Err)
	}
	return results, errors.Join(outcome, o.ctx.Err())
}

// The retained concrete block service remains the native implementation. Only
// this operation's context replaces the syncers' Background/nil cancellation.
type ownedImportBlockService struct {
	*block.Service
	owned *ownedImportExecution
}

func (s ownedImportBlockService) GetObject(_ context.Context, id string) (smartblock.SmartBlock, error) {
	return s.Service.GetObject(s.owned.ctx, id)
}

func (s ownedImportBlockService) GetObjectByFullID(_ context.Context, id domain.FullID) (smartblock.SmartBlock, error) {
	return s.Service.GetObjectByFullID(s.owned.ctx, id)
}

func (s ownedImportBlockService) UploadFile(_ context.Context, spaceID string, req block.FileUploadRequest) (id string, kind model.BlockContentFileType, details *domain.Details, err error) {
	if req.PreloadOnly {
		return "", 0, nil, errOwnedImportPreload
	}
	slot, err := s.owned.beginFile("synchronous-file", req.CreatedInContext, "")
	if err != nil {
		return "", 0, nil, err
	}
	defer close(slot.ready)
	id, kind, details, err = s.Service.UploadFile(s.owned.ctx, spaceID, req)
	slot.result.FileObjectID, slot.result.Err = id, err
	return id, kind, details, err
}

func (s ownedImportBlockService) UploadBlockFile(eventCtx session.Context, req block.UploadRequest, groupID string, isSync bool) (string, error) {
	// Existing FileSyncer explicitly requests async. An unreviewed synchronous
	// editor route is rejected instead of silently losing its completion.
	if isSync {
		return "", fileuploader.ErrOwnedUploadUnavailable
	}
	slot, err := s.owned.beginFile("asynchronous-block-file", req.ContextId, req.BlockId)
	if err != nil {
		return "", err
	}
	defer close(slot.ready)
	started, err := s.Service.StartOwnedBlockFile(s.owned.ctx, eventCtx, req, groupID)
	if started == nil && err == nil {
		err = fileuploader.ErrOwnedUploadCompletion
	}
	// Keep a started handle even if the initial native Apply also failed.
	slot.async, slot.result.Err = started, err
	return "", err
}

// Check the actual block handed to the syncer, not just the parsed archive:
// original object creation can observe a live block changed after preflight.
type ownedImportBookmarkSyncer struct{}

func (ownedImportBookmarkSyncer) Sync(_ domain.FullID, _ map[string]struct{}, b simple.Block, _ objectorigin.ObjectOrigin) error {
	bookmark := b.Model().GetBookmark()
	if bookmark != nil && bookmark.TargetObjectId == "" && bookmark.Url != "" {
		return errors.Join(common.ErrFileLoad, errOwnedImportBookmark)
	}
	return nil
}
