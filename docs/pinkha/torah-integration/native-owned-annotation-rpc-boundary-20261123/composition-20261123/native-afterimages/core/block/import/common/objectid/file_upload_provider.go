package objectid

import (
	"context"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/files/fileobject"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
)

// FileUploader is the original synchronous upload dependency. The ordinary
// NewIDProvider still receives the same concrete block service. An explicitly
// owned importer may pass its operation-scoped adapter to retain upload errors
// that the original file providers intentionally log and fall back from.
type FileUploader interface {
	UploadFile(context.Context, string, block.FileUploadRequest) (string, model.BlockContentFileType, *domain.Details, error)
}

// NewIDProviderWithFileUploader changes only upload observation/context. The
// original ID assignment, fallback, file-key and object-creation semantics are
// shared with NewIDProvider; a nil final provider error is not a body proof.
func NewIDProviderWithFileUploader(
	objectStore objectstore.ObjectStore,
	spaceService space.Service,
	fileUploader FileUploader,
	fileObjectService fileobject.Service,
) IdAndKeyProvider {
	return newIDProvider(objectStore, spaceService, fileUploader, fileObjectService)
}
