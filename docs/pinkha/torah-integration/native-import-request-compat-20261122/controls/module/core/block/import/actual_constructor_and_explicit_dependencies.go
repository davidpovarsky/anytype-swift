package importer
import (
 "context"
 "github.com/anyproto/anytype-heart/core/block/import/common"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)
// These dependencies and the narrowed interface are explicit unit fixtures.
// Actual constructor and conversion-context statements below are extracted.
type Dependencies struct{}
type ImportProcessor interface{}
type importProcessor struct {
 deps *Dependencies
 request *ImportRequest
 response *ImportResponse
 errors *common.ConvertError
 captureMappingObservation bool
 nativeMapping *nativeMappingBuilder
 nativeMappingTraceID, nativeMappingSpaceID string
 nativeMappingAssignmentsFinished, nativeMappingCreationReturned bool
 nativeMappingBatchesStarted, nativeMappingBatchesDrained int
}
func NewProcessor(deps *Dependencies, req *ImportRequest) ImportProcessor {
	return &importProcessor{
		deps:     deps,
		request:  req,
		response: &ImportResponse{},
	}
}

func actualConversionContext(p *importProcessor, ctx context.Context) context.Context {
	conversionContext := ctx
	if p.captureMappingObservation && p.request.Type == model.Import_Pb {
		conversionContext = common.WithProtobufSourceObservation(ctx)
	}
	return conversionContext
}
