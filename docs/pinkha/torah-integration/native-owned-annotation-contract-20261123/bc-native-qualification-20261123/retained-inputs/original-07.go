package file

import (
	"context"

	"github.com/globalsign/mgo/bson"

	"github.com/anyproto/anytype-heart/core/block/cache"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/files/fileuploader"
	"github.com/anyproto/anytype-heart/core/session"
)

// StartOwnedUpload uses the original file editor under its caller's existing
// SmartBlock lock. Never wait for its completion under that lock: the actual
// asynchronous uploader will acquire the same object for its final update.
// A started handle is returned even when the initial Apply fails, so its native
// work remains owned and must drain before its containing operation can finish.
func StartOwnedUpload(
	operationCtx context.Context,
	sb smartblock.SmartBlock,
	picker cache.ObjectGetter,
	factory fileuploader.Service,
	eventCtx session.Context,
	blockID string,
	source FileSource,
) (*fileuploader.OwnedUpload, error) {
	if operationCtx == nil {
		return nil, fileuploader.ErrOwnedUploadUnavailable
	}
	if err := operationCtx.Err(); err != nil {
		return nil, err
	}
	if source.GroupID == "" {
		source.GroupID = bson.NewObjectId().Hex()
	}
	// The native byte reader must not retain caller-owned mutable input.
	source.Bytes = append([]byte(nil), source.Bytes...)
	sf := &sfile{SmartBlock: sb, picker: picker, fileUploaderFactory: factory}
	st := sf.NewStateCtx(eventCtx).SetGroupId(source.GroupID)
	upl, err := sf.prepareUploader(st, blockID, source)
	if err != nil {
		return nil, err
	}
	upl.SetGroupId(st.GroupId()).AsyncUpdates(sf.Id())
	owned, err := fileuploader.StartOwnedUpload(operationCtx, upl)
	if err != nil {
		return nil, err
	}
	if err = sf.Apply(st); err != nil {
		owned.RequestCancel()
		return owned, err
	}
	return owned, nil
}
