package fileuploader
import "context"
import "github.com/anyproto/anytype-heart/core/block/cache"
import "github.com/anyproto/anytype-heart/core/block/simple/file"
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
// Explicit ABI/callback fixture: no real filesystem, storage or native upload.
type Uploader interface {UploadAsync(context.Context) chan UploadResult}
type uploader struct {serviceCtx context.Context; preloadId string; picker cache.ObjectGetter; block file.Block; upload func(context.Context) UploadResult}
func (u *uploader) Upload(c context.Context) UploadResult {return u.upload(c)}
func FixturePrepared(c context.Context,g cache.ObjectGetter, f func(context.Context) UploadResult) Uploader {return &uploader{serviceCtx:c,picker:g,upload:f}}
type logger struct{}
func (logger) Errorf(string,...any){}
var log logger
type UploadResult struct {
	Name              string
	Type              model.BlockContentFileType
	FileObjectId      string
	FileObjectDetails *domain.Details
	EncryptionKeys    map[string]string
	MIME              string
	Size              int64
	Err               error
}

func (u *uploader) UploadAsync(ctx context.Context) (result chan UploadResult) {
	return u.uploadAsync(u.serviceCtx)
}

// uploadAsync retains the original asynchronous upload and completion channel.
// The legacy entry point keeps using serviceCtx. An explicitly owned upload can
// supply its own cancellation context without cancelling the global service.
func (u *uploader) uploadAsync(ctx context.Context) (result chan UploadResult) {
	result = make(chan UploadResult, 1)
	if u.block != nil {
		u.block.SetState(model.BlockContentFile_Uploading)
		u.block = u.block.Copy().(file.Block)
	}
	go func() {
		res := u.Upload(ctx)
		if res.Err != nil {
			log.Errorf("upload async: %v", res.Err)
		}
		result <- res
		close(result)
	}()
	return
}
