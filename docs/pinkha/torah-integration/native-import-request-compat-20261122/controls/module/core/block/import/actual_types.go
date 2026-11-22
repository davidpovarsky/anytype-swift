package importer
import (
 "github.com/anyproto/anytype-heart/core/block/process"
 "github.com/anyproto/anytype-heart/core/domain/objectorigin"
 "github.com/anyproto/anytype-heart/pb"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)
type ImportRequest struct {
	*pb.RpcObjectImportRequest
	Origin           objectorigin.ObjectOrigin
	Progress         process.Progress
	SendNotification bool
	IsSync           bool
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

type originalFiveFieldRequest struct {
	*pb.RpcObjectImportRequest
	Origin           objectorigin.ObjectOrigin
	Progress         process.Progress
	SendNotification bool
	IsSync           bool
}
