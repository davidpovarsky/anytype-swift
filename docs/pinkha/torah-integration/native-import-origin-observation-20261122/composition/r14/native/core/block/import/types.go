package importer

import (
	"context"

	"github.com/anyproto/any-sync/app"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/import/common/objectid"
	_ "github.com/anyproto/anytype-heart/core/block/import/markdown"
	_ "github.com/anyproto/anytype-heart/core/block/import/pb"
	_ "github.com/anyproto/anytype-heart/core/block/import/web"
	"github.com/anyproto/anytype-heart/core/block/process"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/files/filesync"
	"github.com/anyproto/anytype-heart/core/notifications"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
)

type ImportRequest struct {
	*pb.RpcObjectImportRequest
	Origin           objectorigin.ObjectOrigin
	Progress         process.Progress
	SendNotification bool
	IsSync           bool
	// Internal opt-in diagnostic only. No wire RPC or production caller enables
	// it here; ordinary imports retain their existing outputs and side effects.
	CaptureMappingObservation bool `json:"-"`
}

type ImportResponse struct {
	RootCollectionId      string
	RootWidgetLayout      model.BlockContentWidgetLayout
	ProcessId             string
	ObjectsCount          int64
	Err                   error
	nativeMapping         *NativeProtobufImportMappingObservation
	nativeMappingProblems []string
}

// NativeMappingObservation describes actual selected-snapshot ID choices only.
// It is unavailable for incomplete/failed/undrained observations, even if callers
// fill the public legacy response fields themselves. It grants no body/ACK right.
func (r *ImportResponse) NativeMappingObservation() (NativeProtobufImportMappingObservation, bool) {
	if r == nil || r.nativeMapping == nil || !r.nativeMapping.complete {
		return NativeProtobufImportMappingObservation{}, false
	}
	return r.nativeMapping.copy(), true
}

func (r *ImportResponse) NativeMappingProblems() []string {
	if r == nil {
		return nil
	}
	return append([]string(nil), r.nativeMappingProblems...)
}

type Dependencies struct {
	converters          map[string]common.Converter
	blockService        *block.Service
	objectCreator       creator.Service
	idProvider          objectid.IdAndKeyProvider
	fileSync            filesync.FileSync
	notificationService notifications.Notifications
	eventSender         event.Sender
	objectStore         objectstore.ObjectStore
	spaceService        space.Service
}

// Importer encapsulate logic with import
type Importer interface {
	app.Component
	Import(ctx context.Context, importRequest *ImportRequest) *ImportResponse

	ListImports(req *pb.RpcObjectImportListRequest) ([]*pb.RpcObjectImportListImportResponse, error)
	ImportWeb(ctx context.Context, req *ImportRequest) (string, *domain.Details, error)
	// nolint: lll
	ValidateNotionToken(ctx context.Context, req *pb.RpcObjectImportNotionValidateTokenRequest) (pb.RpcObjectImportNotionValidateTokenResponseErrorCode, error)
}
