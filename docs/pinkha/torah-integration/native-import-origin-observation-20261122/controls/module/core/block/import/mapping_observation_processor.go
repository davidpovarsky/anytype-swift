package importer

import (
	"context"

	"github.com/anyproto/anytype-heart/core/block/import/common"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// Clear only diagnostic state, including on an early failed reuse of a processor.
// Legacy response/error and native side-effect semantics are unchanged.
func (p *importProcessor) resetNativeMappingObservation() {
	p.nativeMapping = nil
	p.nativeMappingTraceID, p.nativeMappingSpaceID = "", ""
	p.nativeMappingAssignmentsFinished, p.nativeMappingCreationReturned = false, false
	p.nativeMappingBatchesStarted, p.nativeMappingBatchesDrained = 0, 0
	p.response.nativeMapping, p.response.nativeMappingProblems = nil, nil
}

func (p *importProcessor) initializeNativeMappingObservation(response *common.Response) {
	if !p.request.CaptureMappingObservation || p.request.Type != model.Import_Pb {
		return
	}
	sources := make([]nativeProtobufSourceRecord, 0, min(len(response.ProtobufSources), nativeMappingFactLimit+1))
	for i, source := range response.ProtobufSources {
		if i > nativeMappingFactLimit {
			break
		}
		sources = append(sources, nativeProtobufSourceRecord{archivePath: source.ArchivePath, memberPath: source.MemberPath,
			sourceSpaceID: source.SourceSpaceID, sourceObjectID: source.SourceObjectID, converterID: source.ConverterID,
			encoding: source.Encoding, selected: source.Selected})
	}
	ids := make([]string, 0, min(len(response.Snapshots), nativeMappingFactLimit+1))
	for i, snapshot := range response.Snapshots {
		if i > nativeMappingFactLimit {
			break
		}
		if snapshot == nil {
			ids = append(ids, "")
		} else {
			ids = append(ids, snapshot.Id)
		}
	}
	p.nativeMapping = newNativeMappingBuilder(sources, response.ProtobufGeneratedIDs, response.KeptIDs, ids,
		response.ProtobufSourceObservationIncomplete)
}

func (p *importProcessor) retainNativeMappingObservation(ctx context.Context) {
	if p.nativeMapping == nil {
		return
	}
	// Assignment success, successful return through all creation batches and
	// exact successful worker drains are independent prerequisites. A nil legacy
	// error/count alone is insufficient. Finalize's other effects remain outside
	// this observation's selected-snapshot assignment scope.
	eligible := p.nativeMappingAssignmentsFinished && p.nativeMappingCreationReturned &&
		p.nativeMappingBatchesStarted > 0 && p.nativeMappingBatchesDrained == p.nativeMappingBatchesStarted &&
		p.response.Err == nil && p.errors != nil && p.errors.IsEmpty() && ctx.Err() == nil &&
		p.request.SpaceId == p.nativeMappingSpaceID
	observation, problems := p.nativeMapping.finish(p.nativeMappingTraceID, p.response.ProcessId, p.nativeMappingSpaceID, eligible)
	p.response.nativeMappingProblems = append([]string(nil), problems...)
	if observation.complete {
		p.response.nativeMapping = &observation
	}
}
