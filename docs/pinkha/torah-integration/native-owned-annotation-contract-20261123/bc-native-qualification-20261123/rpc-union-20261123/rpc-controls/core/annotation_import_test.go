package core

import (
	"bytes"
	"errors"
	"strings"
	"testing"

	importer "github.com/anyproto/anytype-heart/core/block/import"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/proto"
)

// These are protobuf/request-copy controls only. Fabricated data below does
// not represent an original import, Done, body match, native ACL or Host ACK.
func annotationTransportFixtureRequest() *pb.RpcAnnotationImportRequest {
	return &pb.RpcAnnotationImportRequest{
		ImportProtocol: annotationImportProtocol, ExpectedAccountId: "account",
		SourceSpaceId: "source-space", SourceRootId: "source-root", TargetSpaceId: "target-space",
		Archive: []byte("data-only-not-a-native-archive"), ArchiveSHA256: make([]byte, 32),
		AttemptSecret: append([]byte{1}, make([]byte, 31)...),
	}
}

func annotationTransportFixtureResponse() *pb.RpcAnnotationImportResponse {
	return &pb.RpcAnnotationImportResponse{
		Error: &pb.RpcAnnotationImportResponseError{
			Code: pb.RpcAnnotationImportResponseError_UNKNOWN_ERROR, Description: "finite test category",
		},
		ImportProtocol: annotationImportProtocol, Registered: true, OperationDone: true,
		CopyDisposition:     pb.RpcAnnotationImportResponse_COMPLETE,
		NativeErrorCategory: pb.RpcAnnotationImport_NATIVE_FAILURE,
		NativeErrorPresent:  true, CancellationRequested: true,
	}
}

func TestAnnotationImportTransportRequestBoundaries(t *testing.T) {
	req := annotationTransportFixtureRequest()
	req.Archive = make([]byte, annotationImportArchiveMaximum)
	req.SourceRootId = strings.Repeat("r", annotationImportStringMaximum)
	if !annotationImportRequestOK(req) {
		t.Fatal("exact independent archive/string limits refused")
	}
	req.Archive = append(req.Archive, 0)
	if annotationImportRequestOK(req) {
		t.Fatal("archive one byte over admitted")
	}
	req = annotationTransportFixtureRequest()
	req.SourceRootId = strings.Repeat("r", annotationImportStringMaximum+1)
	if annotationImportRequestOK(req) {
		t.Fatal("identity one byte over admitted")
	}
	for _, invalid := range []string{"", "a\x00b", string([]byte{0xff})} {
		req = annotationTransportFixtureRequest()
		req.ExpectedAccountId = invalid
		if annotationImportRequestOK(req) {
			t.Fatal("invalid identity admitted")
		}
	}
	req = annotationTransportFixtureRequest()
	req.AttemptSecret = make([]byte, 32)
	if annotationImportRequestOK(req) {
		t.Fatal("all-zero cancellation secret admitted")
	}
	req.AttemptSecret = make([]byte, 31)
	if annotationImportRequestOK(req) {
		t.Fatal("wrong secret length admitted")
	}
	cancel := &pb.RpcAnnotationImportCancelRequest{
		ImportProtocol: annotationImportProtocol, ExpectedAccountId: "account", SourceSpaceId: "source-space",
		SourceRootId: "source-root", TargetSpaceId: "target-space",
		ArchiveSHA256: make([]byte, 32), AttemptSecret: append([]byte{1}, make([]byte, 31)...),
	}
	if !annotationImportCancelRequestOK(cancel) {
		t.Fatal("complete comparison-only cancellation tuple refused")
	}
	cancel.ImportProtocol = "unknown"
	if annotationImportCancelRequestOK(cancel) {
		t.Fatal("unknown protocol admitted")
	}
}

func TestAnnotationImportTransportExactGeneratedEncoding(t *testing.T) {
	privatePath := "/private/owned/native-staging"
	privateError := "do not transport an arbitrary native error description"
	view := annotationImportCopyView{
		targetSpaceID: "target", processID: "", rootID: "root", objectsCount: -1,
		files: []importer.OwnedImportFileObservation{{
			Kind: "file", ObjectID: "object", BlockID: "block", FileObjectID: "file-object", Err: errors.New(privateError),
		}},
		sources: []importer.NativeProtobufSourceAssignment{{
			ArchivePath: privatePath, MemberPath: "objects/a.pb", SourceSpaceID: "source",
			SourceObjectID: "object", ConverterID: "converter", NativeID: "native",
		}},
		filtered: []importer.NativeProtobufFilteredSource{{
			ArchivePath: privatePath, MemberPath: "objects/b.pb", SourceSpaceID: "source",
			SourceObjectID: "filtered", ConverterID: "converter-filtered",
		}},
		generated: []importer.NativeProtobufGeneratedAssignment{{ConverterID: "generated", NativeID: "native-generated"}},
		aliases:   []importer.NativeProtobufInternalKeyAlias{{ConverterID: "converter", SourceKey: "old", NativeKey: "new"}},
		kept:      []string{"kept", ""}, problems: []string{"problem", ""},
		readbackObserved: true, nativeArchive: []byte("owned-wire-fixture"),
		exportReport: &model.ExportReport{Status: model.ExportReport_PARTIAL, Succeed: 1, ObjectErrors: 2, FileErrors: 3,
			Issues: []*model.ExportReportIssue{{ObjectId: "object", Severity: model.ExportReportIssue_ERROR,
				Code: "code", Path: "relative/path", Message: "preserve the complete original report field"}}},
	}
	view.sourceDigest[0] = 7
	response := annotationTransportFixtureResponse()
	expected, accepted := annotationImportCopySize(response, view)
	if !accepted {
		t.Fatal("bounded data-only wire fixture refused")
	}
	installAnnotationImportCopy(response, view)
	raw, err := proto.Marshal(response)
	if err != nil || len(raw) != expected || proto.Size(response) != expected {
		t.Fatalf("original generated protobuf differs from nonallocating preflight: bytes=%d expected=%d err=%v", len(raw), expected, err)
	}
	if bytes.Contains(raw, []byte(privatePath)) || bytes.Contains(raw, []byte(privateError)) {
		t.Fatal("private stage path or unbounded error description escaped")
	}
	if response.Outcome.ProcessId != "" || len(response.Mapping.KeptReferenceIds) != 2 ||
		response.Mapping.KeptReferenceIds[1] != "" || !proto.Equal(response.Readback.ExportReport, view.exportReport) {
		t.Fatal("empty progress identity, repeated empty field or complete report changed")
	}
	if !bytes.Equal(response.Mapping.SourceAssignments[0].SourceArchiveSHA256, view.sourceDigest[:]) {
		t.Fatal("exact input digest was not copied")
	}
}

func TestAnnotationImportTransportCompleteResponseLimit(t *testing.T) {
	view := annotationImportCopyView{readbackObserved: true, nativeArchive: make([]byte, annotationImportArchiveMaximum)}
	for i := 0; i < 63; i++ {
		view.files = append(view.files, importer.OwnedImportFileObservation{Kind: strings.Repeat("k", annotationImportStringMaximum)})
	}
	view.files = append(view.files, importer.OwnedImportFileObservation{})
	// The original generated encoder locates the actual boundary; this test
	// does not reuse the handwritten preflight to manufacture its own oracle.
	low, high, exact := 0, annotationImportStringMaximum, -1
	for low <= high {
		mid := low + (high-low)/2
		view.files[len(view.files)-1].Kind = strings.Repeat("k", mid)
		probe := annotationTransportFixtureResponse()
		installAnnotationImportCopy(probe, view)
		actual := proto.Size(probe)
		switch {
		case actual == annotationImportResponseMaximum:
			exact = mid
			low = high + 1
		case actual < annotationImportResponseMaximum:
			low = mid + 1
		default:
			high = mid - 1
		}
	}
	if exact < 0 || exact >= annotationImportStringMaximum {
		t.Fatal("generated complete-message exact boundary was not found")
	}
	view.files[len(view.files)-1].Kind = strings.Repeat("k", exact)
	response := annotationTransportFixtureResponse()
	expected, accepted := annotationImportCopySize(response, view)
	if !accepted || expected != annotationImportResponseMaximum {
		t.Fatal("exact complete encoded bound refused")
	}
	installAnnotationImportCopy(response, view)
	raw, err := proto.Marshal(response)
	if err != nil || len(raw) != annotationImportResponseMaximum {
		t.Fatal("exact accepted result did not encode at the real bound")
	}
	view.files[len(view.files)-1].Kind += "k"
	if _, accepted := annotationImportCopySize(annotationTransportFixtureResponse(), view); accepted {
		t.Fatal("complete encoded result one byte over admitted")
	}
	refused := refuseAnnotationImportCopy(response)
	if !refused.Registered || !refused.OperationDone || !refused.NativeErrorPresent || !refused.CancellationRequested ||
		refused.NativeErrorCategory != pb.RpcAnnotationImport_NATIVE_FAILURE ||
		refused.CopyDisposition != pb.RpcAnnotationImportResponse_COPY_REFUSED ||
		refused.Error.Code != pb.RpcAnnotationImportResponseError_COPY_REFUSED ||
		refused.Outcome != nil || refused.Mapping != nil || refused.Readback != nil {
		t.Fatal("whole-copy refusal changed finite history or retained a partial body")
	}
}

func TestAnnotationImportTransportContainerAndReportLimits(t *testing.T) {
	view := annotationImportCopyView{files: make([]importer.OwnedImportFileObservation, annotationImportMetadataMaximum)}
	if _, accepted := annotationImportCopySize(annotationTransportFixtureResponse(), view); !accepted {
		t.Fatal("exact new file-container policy refused")
	}
	view.files = append(view.files, importer.OwnedImportFileObservation{})
	if _, accepted := annotationImportCopySize(annotationTransportFixtureResponse(), view); accepted {
		t.Fatal("over-limit file containers admitted despite small encoded bytes")
	}
	view = annotationImportCopyView{readbackObserved: true, exportReport: &model.ExportReport{
		Issues: []*model.ExportReportIssue{{Message: strings.Repeat("m", annotationImportStringMaximum+1)}},
	}}
	if _, accepted := annotationImportCopySize(annotationTransportFixtureResponse(), view); accepted {
		t.Fatal("oversized original report field was truncated or admitted")
	}
	view.exportReport.Issues = []*model.ExportReportIssue{nil}
	if _, accepted := annotationImportCopySize(annotationTransportFixtureResponse(), view); accepted {
		t.Fatal("nil native report issue was treated as a complete copied report")
	}
}
