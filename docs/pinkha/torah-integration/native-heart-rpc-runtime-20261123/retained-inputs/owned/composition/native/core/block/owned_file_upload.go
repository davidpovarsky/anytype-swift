package block

import (
	"context"

	"github.com/anyproto/anytype-heart/core/block/cache"
	"github.com/anyproto/anytype-heart/core/block/editor/file"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/files/fileuploader"
	"github.com/anyproto/anytype-heart/core/session"
)

// StartOwnedBlockFile retains the completion of the original file editor upload.
// It is an internal building block, not a production import route or authority.
// Always retain a nonnil returned handle, including when err is nonnil.
func (s *Service) StartOwnedBlockFile(
	operationCtx context.Context, eventCtx session.Context, req UploadRequest, groupID string,
) (owned *fileuploader.OwnedUpload, err error) {
	if operationCtx == nil {
		return nil, fileuploader.ErrOwnedUploadUnavailable
	}
	if err = operationCtx.Err(); err != nil {
		return nil, err
	}
	err = cache.DoContext(s, operationCtx, req.ContextId, func(sb smartblock.SmartBlock) error {
		createdInContextRef := req.CreatedInContextRef
		if createdInContextRef == "" {
			createdInContextRef = req.BlockId
		}
		owned, err = file.StartOwnedUpload(operationCtx, sb, s, s.fileUploaderService, eventCtx, req.BlockId, file.FileSource{
			Path:                req.FilePath,
			Url:                 req.Url,
			Bytes:               req.Bytes,
			GroupID:             groupID,
			Origin:              req.ObjectOrigin,
			ImageKind:           req.ImageKind,
			CreatedInContext:    req.ContextId,
			CreatedInContextRef: createdInContextRef,
		})
		return err
	})
	return owned, err
}
