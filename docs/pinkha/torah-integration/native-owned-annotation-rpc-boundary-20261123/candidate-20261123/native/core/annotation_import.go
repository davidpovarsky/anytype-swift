package core

import (
	"context"
	"errors"
	"strings"
	"unicode/utf8"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"

	"github.com/anyproto/anytype-heart/core/application"
	importer "github.com/anyproto/anytype-heart/core/block/import"
	"github.com/anyproto/anytype-heart/core/block/restriction"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/proto"
)

// These are explicit annotation RPC transport policies, not Host action-wire
// limits, native account authority or proof that an original body is accepted.
const (
	annotationImportProtocol             = "pinkha.annotation.import.v1"
	annotationImportArchiveMaximum       = 1 << 20
	annotationImportResponseMaximum      = 2 << 20
	annotationImportStringMaximum        = 1 << 14
	annotationImportMappingMaximum       = 512
	annotationImportProblemMaximum       = 16
	annotationImportMetadataMaximum      = 4096
	annotationImportAdditionalContextMax = 3
)

// AnnotationImport keeps one original invocation alive through actual native
// completion. The generated C route's Background context is not Swift Task
// cancellation; the separate command below only requests cancellation.
func (mw *Middleware) AnnotationImport(ctx context.Context, req *pb.RpcAnnotationImportRequest) *pb.RpcAnnotationImportResponse {
	response := &pb.RpcAnnotationImportResponse{
		Error:          &pb.RpcAnnotationImportResponseError{},
		ImportProtocol: annotationImportProtocol,
	}
	if ctx == nil || !annotationImportRequestOK(req) {
		response.Error.Code = pb.RpcAnnotationImportResponseError_BAD_INPUT
		response.Error.Description = "invalid bounded original annotation import request"
		return response
	}
	if mw == nil || mw.applicationService == nil {
		response.Error.Code = pb.RpcAnnotationImportResponseError_RUNTIME_UNAVAILABLE
		response.Error.Description = "original annotation application is unavailable"
		return response
	}
	var digest, secret [32]byte
	copy(digest[:], req.ArchiveSHA256)
	copy(secret[:], req.AttemptSecret)
	completion, err := mw.applicationService.ImportOwnedAnnotation(ctx, req.ExpectedAccountId,
		req.Archive, digest, req.SourceRootId, req.SourceSpaceId, req.TargetSpaceId, secret)
	response.Registered = completion.Registered()
	response.OperationDone = completion.Done()
	if err != nil {
		response.Error.Code = annotationImportErrorCode(err)
		response.Error.Description = annotationImportErrorDescription(response.Error.Code)
	}
	outcome, observed := completion.Outcome()
	if !observed {
		return response
	}
	// These finite scalar facts survive a refused complete-body copy. They
	// originate in the actual Done/Result, never in a caller-owned completion.
	response.NativeErrorPresent = outcome.Err() != nil
	response.NativeErrorCategory = annotationImportNativeErrorCategory(outcome.Err())
	response.CancellationRequested = outcome.CancellationRequested()
	view := captureAnnotationImportCopy(outcome, digest)
	response.CopyDisposition = pb.RpcAnnotationImportResponse_COMPLETE
	expectedSize, accepted := annotationImportCopySize(response, view)
	if !accepted {
		return refuseAnnotationImportCopy(response)
	}
	installAnnotationImportCopy(response, view)
	// The original generator remains mandatory. This exact size comparison
	// checks its real protobuf representation before the external marshal.
	if proto.Size(response) != expectedSize || proto.Size(response) > annotationImportResponseMaximum {
		return refuseAnnotationImportCopy(response)
	}
	return response
}

func (mw *Middleware) AnnotationImportCancel(ctx context.Context, req *pb.RpcAnnotationImportCancelRequest) *pb.RpcAnnotationImportCancelResponse {
	response := &pb.RpcAnnotationImportCancelResponse{
		Error:          &pb.RpcAnnotationImportCancelResponseError{},
		ImportProtocol: annotationImportProtocol,
	}
	if ctx == nil || !annotationImportCancelRequestOK(req) {
		response.Error.Code = pb.RpcAnnotationImportCancelResponseError_BAD_INPUT
		response.Error.Description = "invalid original annotation cancellation comparison"
		return response
	}
	if mw == nil || mw.applicationService == nil {
		response.Error.Code = pb.RpcAnnotationImportCancelResponseError_RUNTIME_UNAVAILABLE
		response.Error.Description = "original annotation application is unavailable"
		return response
	}
	var digest, secret [32]byte
	copy(digest[:], req.ArchiveSHA256)
	copy(secret[:], req.AttemptSecret)
	actual := mw.applicationService.CancelOwnedAnnotationImport(req.ExpectedAccountId,
		req.SourceRootId, req.SourceSpaceId, req.TargetSpaceId, digest, secret)
	switch actual {
	case application.OwnedAnnotationCancelRequested:
		response.Disposition = pb.RpcAnnotationImportCancelResponse_REQUESTED
	case application.OwnedAnnotationCancelDoneObserved:
		response.Disposition = pb.RpcAnnotationImportCancelResponse_DONE_OBSERVED
	default:
		response.Disposition = pb.RpcAnnotationImportCancelResponse_NOT_OBSERVED
	}
	// No current-write admission is renewed and no operation is released.
	// Even DONE_OBSERVED does not replace the retained Import response/drain.
	return response
}

func annotationImportTextOK(value string) bool {
	return len(value) <= annotationImportStringMaximum && utf8.ValidString(value)
}

func annotationImportIdentityOK(value string) bool {
	return value != "" && annotationImportTextOK(value) && !strings.ContainsRune(value, '\x00')
}

func annotationImportSecretOK(value []byte) bool {
	if len(value) != 32 {
		return false
	}
	var present byte
	for _, b := range value {
		present |= b
	}
	return present != 0
}

func annotationImportRequestOK(req *pb.RpcAnnotationImportRequest) bool {
	return req != nil && req.ImportProtocol == annotationImportProtocol &&
		annotationImportIdentityOK(req.ExpectedAccountId) && annotationImportIdentityOK(req.SourceSpaceId) &&
		annotationImportIdentityOK(req.SourceRootId) && annotationImportIdentityOK(req.TargetSpaceId) &&
		len(req.Archive) > 0 && len(req.Archive) <= annotationImportArchiveMaximum &&
		len(req.ArchiveSHA256) == 32 && annotationImportSecretOK(req.AttemptSecret)
}

func annotationImportCancelRequestOK(req *pb.RpcAnnotationImportCancelRequest) bool {
	return req != nil && req.ImportProtocol == annotationImportProtocol &&
		annotationImportIdentityOK(req.ExpectedAccountId) && annotationImportIdentityOK(req.SourceSpaceId) &&
		annotationImportIdentityOK(req.SourceRootId) && annotationImportIdentityOK(req.TargetSpaceId) &&
		len(req.ArchiveSHA256) == 32 && annotationImportSecretOK(req.AttemptSecret)
}

func annotationImportErrorCode(err error) pb.RpcAnnotationImportResponseErrorCode {
	switch {
	case errors.Is(err, context.Canceled), errors.Is(err, context.DeadlineExceeded):
		return pb.RpcAnnotationImportResponseError_CANCELED
	case errors.Is(err, list.ErrInsufficientPermissions), errors.Is(err, restriction.ErrRestricted):
		return pb.RpcAnnotationImportResponseError_PERMISSION_DENIED
	case errors.Is(err, application.ErrOwnedAnnotationAttemptInvalid):
		return pb.RpcAnnotationImportResponseError_BAD_INPUT
	case errors.Is(err, application.ErrOwnedAnnotationAttemptConflict):
		return pb.RpcAnnotationImportResponseError_ATTEMPT_CONFLICT
	case errors.Is(err, application.ErrOwnedImportAdmissionUnavailable),
		errors.Is(err, importer.ErrOwnedImportOperationUnavailable):
		return pb.RpcAnnotationImportResponseError_RUNTIME_UNAVAILABLE
	default:
		return pb.RpcAnnotationImportResponseError_UNKNOWN_ERROR
	}
}

func annotationImportErrorDescription(code pb.RpcAnnotationImportResponseErrorCode) string {
	switch code {
	case pb.RpcAnnotationImportResponseError_CANCELED:
		return "original annotation import observed cancellation"
	case pb.RpcAnnotationImportResponseError_PERMISSION_DENIED:
		return "original annotation import writer admission was refused"
	case pb.RpcAnnotationImportResponseError_BAD_INPUT:
		return "invalid original annotation import attempt"
	case pb.RpcAnnotationImportResponseError_ATTEMPT_CONFLICT:
		return "original annotation attempt is already registered"
	case pb.RpcAnnotationImportResponseError_RUNTIME_UNAVAILABLE:
		return "original annotation import application is unavailable"
	default:
		return "original annotation import returned a native failure"
	}
}

func annotationImportNativeErrorCategory(err error) pb.RpcAnnotationImportNativeErrorCategory {
	switch {
	case err == nil:
		return pb.RpcAnnotationImport_NONE
	case errors.Is(err, context.Canceled), errors.Is(err, context.DeadlineExceeded):
		return pb.RpcAnnotationImport_CANCELED
	case errors.Is(err, list.ErrInsufficientPermissions), errors.Is(err, restriction.ErrRestricted):
		return pb.RpcAnnotationImport_PERMISSION_DENIED
	case errors.Is(err, application.ErrOwnedImportAdmissionUnavailable),
		errors.Is(err, importer.ErrOwnedImportOperationUnavailable):
		return pb.RpcAnnotationImport_RUNTIME_UNAVAILABLE
	default:
		return pb.RpcAnnotationImport_NATIVE_FAILURE
	}
}

func refuseAnnotationImportCopy(response *pb.RpcAnnotationImportResponse) *pb.RpcAnnotationImportResponse {
	// Refuse the entire body, never a truncated graph/report. The actual
	// registration, Done, native-error and cancellation facts remain intact.
	response.CopyDisposition = pb.RpcAnnotationImportResponse_COPY_REFUSED
	response.Outcome, response.Mapping, response.Readback = nil, nil, nil
	response.Error.Code = pb.RpcAnnotationImportResponseError_COPY_REFUSED
	response.Error.Description = "complete original annotation result exceeds transport policy"
	return response
}

// Original immutable getters perform their existing owned copies. This route
// does not change the native engine's Result/copy semantics. It validates all
// finite counts, strings and the exact encoded size BEFORE constructing any
// new protobuf row arrays. The accepted native archive remains bounded at 1MiB.
type annotationImportCopyView struct {
	sourceDigest                     [32]byte
	targetSpaceID, processID, rootID string
	objectsCount                     int64
	files                            []importer.OwnedImportFileObservation
	mapping                          importer.NativeProtobufImportMappingObservation
	mappingObserved                  bool
	sources                          []importer.NativeProtobufSourceAssignment
	filtered                         []importer.NativeProtobufFilteredSource
	generated                        []importer.NativeProtobufGeneratedAssignment
	aliases                          []importer.NativeProtobufInternalKeyAlias
	kept, problems                   []string
	readback                         importer.OwnedAnnotationReadbackObservation
	readbackObserved                 bool
	nativeArchive                    []byte
	exportReport                     *model.ExportReport
}

func captureAnnotationImportCopy(outcome importer.OwnedImportOutcome, digest [32]byte) annotationImportCopyView {
	view := annotationImportCopyView{
		sourceDigest: digest, targetSpaceID: outcome.TargetSpaceID(),
		processID: outcome.ProcessID(), rootID: outcome.RootCollectionID(),
		objectsCount: outcome.ObjectsCount(), files: outcome.Files(),
		problems: outcome.NativeMappingProblems(),
	}
	view.mapping, view.mappingObserved = outcome.NativeMappingObservation()
	view.sources, view.filtered = view.mapping.SourceAssignments(), view.mapping.FilteredSources()
	view.generated, view.aliases = view.mapping.GeneratedAssignments(), view.mapping.InternalKeyAliases()
	view.kept = view.mapping.KeptReferenceIDs()
	view.readback, view.readbackObserved = outcome.OriginalAnnotationReadback()
	if view.readbackObserved {
		view.nativeArchive = view.readback.CopyNativeArchive()
		view.exportReport = view.readback.CopyExportReport()
	}
	return view
}

// Exact proto3 wire accounting over the immutable native copies. Each local
// budget can only grow to the total response maximum; no integer wrap or
// unbounded protobuf construction is used to discover a refused result.
type annotationImportWireSize struct {
	bytes int
	ok    bool
}

func newAnnotationImportWireSize() annotationImportWireSize {
	return annotationImportWireSize{ok: true}
}

func annotationImportVarintSize(value uint64) int {
	size := 1
	for value >= 128 {
		value >>= 7
		size++
	}
	return size
}

func (size *annotationImportWireSize) add(amount int) {
	if !size.ok || amount < 0 || amount > annotationImportResponseMaximum-size.bytes {
		size.ok = false
		return
	}
	size.bytes += amount
}

func (size *annotationImportWireSize) number(field int, value uint64) {
	if value != 0 {
		size.add(annotationImportVarintSize(uint64(field<<3)) + annotationImportVarintSize(value))
	}
}

func (size *annotationImportWireSize) boolean(field int, value bool) {
	if value {
		size.number(field, 1)
	}
}

func (size *annotationImportWireSize) data(field, length int, present bool) {
	if present {
		size.add(annotationImportVarintSize(uint64(field<<3|2)) +
			annotationImportVarintSize(uint64(length)) + length)
	}
}

func (size *annotationImportWireSize) text(field int, value string) {
	if !annotationImportTextOK(value) {
		size.ok = false
		return
	}
	size.data(field, len(value), value != "")
}

func (size *annotationImportWireSize) message(field int, child annotationImportWireSize) {
	if !child.ok {
		size.ok = false
		return
	}
	size.data(field, child.bytes, true)
}

func annotationImportResponseBaseSize(response *pb.RpcAnnotationImportResponse) annotationImportWireSize {
	size := newAnnotationImportWireSize()
	if response.Error == nil {
		size.ok = false
		return size
	}
	errorSize := newAnnotationImportWireSize()
	errorSize.number(1, uint64(response.Error.Code))
	errorSize.text(2, response.Error.Description)
	size.message(1, errorSize)
	size.text(2, response.ImportProtocol)
	size.boolean(3, response.Registered)
	size.boolean(4, response.OperationDone)
	size.number(5, uint64(response.CopyDisposition))
	size.number(6, uint64(response.NativeErrorCategory))
	size.boolean(7, response.NativeErrorPresent)
	size.boolean(8, response.CancellationRequested)
	return size
}

func annotationImportCopySize(response *pb.RpcAnnotationImportResponse, view annotationImportCopyView) (int, bool) {
	if len(view.sources) > annotationImportMappingMaximum || len(view.filtered) > annotationImportMappingMaximum ||
		len(view.generated) > annotationImportMappingMaximum || len(view.aliases) > annotationImportMappingMaximum ||
		len(view.kept) > annotationImportMappingMaximum || len(view.problems) > annotationImportProblemMaximum ||
		len(view.files) > annotationImportMetadataMaximum || len(view.nativeArchive) > annotationImportArchiveMaximum {
		return 0, false
	}
	size := annotationImportResponseBaseSize(response)
	outcome := newAnnotationImportWireSize()
	outcome.text(1, view.targetSpaceID)
	outcome.text(2, view.processID)
	outcome.text(3, view.rootID)
	outcome.number(4, uint64(view.objectsCount))
	for _, file := range view.files {
		row := newAnnotationImportWireSize()
		row.text(1, file.Kind)
		row.text(2, file.ObjectID)
		row.text(3, file.BlockID)
		row.text(4, file.FileObjectID)
		row.boolean(5, file.Err != nil)
		row.number(6, uint64(annotationImportNativeErrorCategory(file.Err)))
		outcome.message(5, row)
		if !outcome.ok {
			return 0, false
		}
	}
	size.message(9, outcome)
	mapping := newAnnotationImportWireSize()
	mapping.boolean(1, view.mappingObserved)
	mapping.boolean(2, view.mapping.CompleteForSelectedSnapshots())
	mapping.text(3, view.mapping.TraceID())
	mapping.text(4, view.mapping.ProcessID())
	mapping.text(5, view.mapping.TargetSpaceID())
	for _, source := range view.sources {
		row := newAnnotationImportWireSize()
		row.data(1, len(view.sourceDigest), true)
		row.text(2, source.MemberPath)
		row.text(3, source.SourceSpaceID)
		row.text(4, source.SourceObjectID)
		row.text(5, source.ConverterID)
		row.text(6, source.NativeID)
		mapping.message(6, row)
	}
	for _, source := range view.filtered {
		row := newAnnotationImportWireSize()
		row.data(1, len(view.sourceDigest), true)
		row.text(2, source.MemberPath)
		row.text(3, source.SourceSpaceID)
		row.text(4, source.SourceObjectID)
		row.text(5, source.ConverterID)
		mapping.message(7, row)
	}
	for _, assignment := range view.generated {
		row := newAnnotationImportWireSize()
		row.text(1, assignment.ConverterID)
		row.text(2, assignment.NativeID)
		mapping.message(8, row)
	}
	for _, alias := range view.aliases {
		row := newAnnotationImportWireSize()
		row.text(1, alias.ConverterID)
		row.text(2, alias.SourceKey)
		row.text(3, alias.NativeKey)
		mapping.message(9, row)
	}
	for _, id := range view.kept {
		// Repeated scalar strings preserve even empty entries on the wire.
		if !annotationImportTextOK(id) {
			return 0, false
		}
		mapping.data(10, len(id), true)
	}
	mapping.boolean(11, view.mapping.NonInjectiveDestinations())
	for _, problem := range view.problems {
		if !annotationImportTextOK(problem) {
			return 0, false
		}
		mapping.data(12, len(problem), true)
	}
	size.message(10, mapping)
	if view.readbackObserved {
		readback, accepted := annotationImportReadbackSize(view)
		if !accepted {
			return 0, false
		}
		size.message(11, readback)
	}
	return size.bytes, size.ok
}

func annotationImportReadbackSize(view annotationImportCopyView) (annotationImportWireSize, bool) {
	actual := view.readback
	size := newAnnotationImportWireSize()
	if actual.Stage() > importer.OwnedAnnotationBodyMatched ||
		actual.SourceSnapshots() < 0 || actual.SourceSnapshots() > annotationImportMappingMaximum ||
		actual.AnnotationPages() < 0 || actual.AnnotationPages() > annotationImportMappingMaximum ||
		actual.FileObjects() < 0 || actual.FileObjects() > annotationImportMappingMaximum ||
		actual.ReadOnlyContexts() < 0 || actual.ReadOnlyContexts() > annotationImportMappingMaximum ||
		actual.AdditionalImportContexts() < 0 || actual.AdditionalImportContexts() > annotationImportAdditionalContextMax {
		return size, false
	}
	size.boolean(1, true)
	size.number(2, uint64(actual.Stage()))
	size.text(3, actual.AccountID())
	size.text(4, actual.SpaceID())
	size.text(5, actual.RootID())
	size.data(6, 32, true)
	size.data(7, 32, true)
	size.data(8, len(view.nativeArchive), len(view.nativeArchive) != 0)
	if report := view.exportReport; report != nil {
		if len(report.Issues) > annotationImportMetadataMaximum {
			return size, false
		}
		for _, issue := range report.Issues {
			if issue == nil || !annotationImportTextOK(issue.ObjectId) || !annotationImportTextOK(issue.Code) ||
				!annotationImportTextOK(issue.Path) || !annotationImportTextOK(issue.Message) {
				return size, false
			}
		}
		reportBytes := proto.Size(report)
		if reportBytes > annotationImportResponseMaximum {
			return size, false
		}
		size.data(9, reportBytes, true)
	}
	size.number(10, uint64(actual.SourceSnapshots()))
	size.number(11, uint64(actual.AnnotationPages()))
	size.number(12, uint64(actual.FileObjects()))
	size.number(13, uint64(actual.ReadOnlyContexts()))
	size.number(14, uint64(actual.AdditionalImportContexts()))
	return size, size.ok
}

func installAnnotationImportCopy(response *pb.RpcAnnotationImportResponse, view annotationImportCopyView) {
	outcome := &pb.RpcAnnotationImportOutcome{
		TargetSpaceId: view.targetSpaceID, ProcessId: view.processID,
		RootCollectionId: view.rootID, ObjectsCount: view.objectsCount,
	}
	for _, file := range view.files {
		outcome.Files = append(outcome.Files, &pb.RpcAnnotationImportFileObservation{
			Kind: file.Kind, ObjectId: file.ObjectID, BlockId: file.BlockID, FileObjectId: file.FileObjectID,
			NativeErrorPresent: file.Err != nil, NativeErrorCategory: annotationImportNativeErrorCategory(file.Err),
		})
	}
	mapping := &pb.RpcAnnotationImportMapping{
		Observed: view.mappingObserved, CompleteForSelectedSnapshots: view.mapping.CompleteForSelectedSnapshots(),
		TraceId: view.mapping.TraceID(), ProcessId: view.mapping.ProcessID(), TargetSpaceId: view.mapping.TargetSpaceID(),
		NonInjectiveDestinations: view.mapping.NonInjectiveDestinations(),
		KeptReferenceIds:         append([]string(nil), view.kept...), Problems: append([]string(nil), view.problems...),
	}
	for _, source := range view.sources {
		mapping.SourceAssignments = append(mapping.SourceAssignments, &pb.RpcAnnotationImportSourceAssignment{
			SourceArchiveSHA256: append([]byte(nil), view.sourceDigest[:]...),
			MemberPath:          source.MemberPath, SourceSpaceId: source.SourceSpaceID,
			SourceObjectId: source.SourceObjectID, ConverterId: source.ConverterID, NativeId: source.NativeID,
		})
	}
	for _, source := range view.filtered {
		mapping.FilteredSources = append(mapping.FilteredSources, &pb.RpcAnnotationImportFilteredSource{
			SourceArchiveSHA256: append([]byte(nil), view.sourceDigest[:]...),
			MemberPath:          source.MemberPath, SourceSpaceId: source.SourceSpaceID,
			SourceObjectId: source.SourceObjectID, ConverterId: source.ConverterID,
		})
	}
	for _, assignment := range view.generated {
		mapping.GeneratedAssignments = append(mapping.GeneratedAssignments, &pb.RpcAnnotationImportGeneratedAssignment{
			ConverterId: assignment.ConverterID, NativeId: assignment.NativeID,
		})
	}
	for _, alias := range view.aliases {
		mapping.InternalKeyAliases = append(mapping.InternalKeyAliases, &pb.RpcAnnotationImportInternalKeyAlias{
			ConverterId: alias.ConverterID, SourceKey: alias.SourceKey, NativeKey: alias.NativeKey,
		})
	}
	response.Outcome, response.Mapping = outcome, mapping
	if view.readbackObserved {
		actual := view.readback
		sourceDigest, nativeDigest := actual.SourceArchiveSHA256(), actual.NativeArchiveSHA256()
		response.Readback = &pb.RpcAnnotationImportReadback{
			Observed: true, Stage: uint32(actual.Stage()),
			AccountId: actual.AccountID(), SpaceId: actual.SpaceID(), RootId: actual.RootID(),
			SourceArchiveSHA256: append([]byte(nil), sourceDigest[:]...),
			NativeArchiveSHA256: append([]byte(nil), nativeDigest[:]...),
			NativeArchive:       view.nativeArchive, ExportReport: view.exportReport,
			SourceSnapshots: uint32(actual.SourceSnapshots()), AnnotationPages: uint32(actual.AnnotationPages()),
			FileObjects: uint32(actual.FileObjects()), ReadOnlyContexts: uint32(actual.ReadOnlyContexts()),
			AdditionalContexts: uint32(actual.AdditionalImportContexts()),
		}
	}
}
