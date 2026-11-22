package importer
import (
 "fmt"
 "github.com/anyproto/anytype-heart/core/block/import/common"
 creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
 "github.com/anyproto/anytype-heart/core/block/import/common/workerpool"
 "github.com/anyproto/anytype-heart/core/domain"
 "github.com/anyproto/anytype-heart/pb"
)
// Explicit processor dependency fixture. All executed diagnostic methods and
// readResults below are byte-exact extracted production source, not reimplemented.
type importProcessor struct {
 request *ImportRequest
 response *ImportResponse
 errors *common.ConvertError
 nativeMapping *nativeMappingBuilder
 nativeMappingTraceID, nativeMappingSpaceID string
 nativeMappingAssignmentsFinished, nativeMappingCreationReturned bool
 nativeMappingBatchesStarted, nativeMappingBatchesDrained int
}
func (p *importProcessor) readResults(pool *workerpool.WorkerPool) map[string]*domain.Details {
	details := make(map[string]*domain.Details)

	for r := range pool.Results() {
		if err := p.request.Progress.TryStep(1); err != nil {
			p.errors.Add(fmt.Errorf("%w: %s", common.ErrCancel, err.Error()))
			pool.Stop()
			return nil
		}

		result := r.(*creator.Result)
		if result.Err != nil {
			p.errors.Add(result.Err)
			if p.request.Mode == pb.RpcObjectImportRequest_ALL_OR_NOTHING {
				pool.Stop()
				return nil
			}
		}

		details[result.NewID] = result.Details
	}

	// Reaching this point follows result-channel closure after the original
	// worker wait group drains. Stop/error early returns never mark a drain.
	if p.nativeMapping != nil {
		p.nativeMappingBatchesDrained++
	}
	return details
}
