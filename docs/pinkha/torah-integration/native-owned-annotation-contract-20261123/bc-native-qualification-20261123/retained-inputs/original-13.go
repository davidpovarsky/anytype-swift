package importer

import (
	"errors"

	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/anytype/account"
	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/collection"
	"github.com/anyproto/anytype-heart/core/block/detailservice"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/import/common/objectid"
	"github.com/anyproto/anytype-heart/core/block/import/common/syncer"
	pbc "github.com/anyproto/anytype-heart/core/block/import/pb"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/process"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/files/fileobject"
	"github.com/anyproto/anytype-heart/core/files/filesync"
	"github.com/anyproto/anytype-heart/core/notifications"
	"github.com/anyproto/anytype-heart/core/relationutils"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/core"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
)

// This constructor is deliberately package-private and has no production
// caller. Exact archive/account/Space admission must be bound before enabling a
// route. The original public NewProcessor and five-field ImportRequest stay
// unchanged. Neither caller-owned progress nor mutable RPC data is retained.
func newOwnedImportProcessor(a *app.App, owned *ownedImportExecution, request *ImportRequest) (*importProcessor, error) {
	if a == nil || owned == nil || owned.ctx == nil || request == nil || request.RpcObjectImportRequest == nil {
		return nil, errors.New("owned native import is not initialized")
	}
	if err := owned.ctx.Err(); err != nil {
		return nil, err
	}
	if request.Type != model.Import_Pb || request.Mode != pb.RpcObjectImportRequest_ALL_OR_NOTHING ||
		!request.IsSync || !request.GetNoProgress() || request.SendNotification || request.Progress != nil ||
		request.IsMigration || request.IsNewSpace || request.SpaceId == "" {
		return nil, errors.New("unsupported owned native import request")
	}
	cloned := *request
	cloned.RpcObjectImportRequest = proto.Clone(request.RpcObjectImportRequest).(*pb.RpcObjectImportRequest)
	cloned.Progress = process.NewNoOp()
	return &importProcessor{
		deps: newOwnedImportDependencies(a, owned), request: &cloned,
		response: &ImportResponse{}, captureMappingObservation: true, owned: owned,
	}, nil
}

// newOwnedImportDependencies constructs fresh original converter/provider state
// for one operation. Its caller must retain the exact native app's lifetime;
// a copied app pointer alone is not admission. No production caller is enabled.
func newOwnedImportDependencies(a *app.App, owned *ownedImportExecution) *Dependencies {
	blocks := app.MustComponent[*block.Service](a)
	spaces := app.MustComponent[space.Service](a)
	store := app.MustComponent[objectstore.ObjectStore](a)
	fileObjects := app.MustComponent[fileobject.Service](a)
	scoped := ownedImportBlockService{Service: blocks, owned: owned}
	deps := &Dependencies{
		converters: map[string]common.Converter{
			model.Import_Pb.String(): pbc.New(
				app.MustComponent[*collection.Service](a),
				app.MustComponent[account.Service](a),
				app.MustComponent[core.TempDirProvider](a),
			),
		},
		blockService:        blocks,
		spaceService:        spaces,
		objectStore:         store,
		fileSync:            app.MustComponent[filesync.FileSync](a),
		notificationService: app.MustComponent[notifications.Notifications](a),
		eventSender:         app.MustComponent[event.Sender](a),
	}
	// The original provider's synchronous uploads remain on this Execute path.
	// Its original log-and-fallback behavior is unchanged, while scoped slots
	// retain the actual upload error for the owning import's final result.
	deps.idProvider = objectid.NewIDProviderWithFileUploader(store, spaces, scoped, fileObjects)
	factory := syncer.NewWithBookmarkSyncer(
		syncer.NewFileSyncer(scoped, fileObjects),
		ownedImportBookmarkSyncer{},
		syncer.NewIconSyncer(scoped, fileObjects),
	)
	deps.objectCreator = creator.New(
		app.MustComponent[detailservice.Service](a),
		factory, store, syncer.NewFileRelationSyncer(scoped, fileObjects), spaces,
		app.MustComponent[objectcreator.Service](a), scoped,
		app.MustComponent[relationutils.RelationFormatFetcher](a),
	)
	return deps
}
