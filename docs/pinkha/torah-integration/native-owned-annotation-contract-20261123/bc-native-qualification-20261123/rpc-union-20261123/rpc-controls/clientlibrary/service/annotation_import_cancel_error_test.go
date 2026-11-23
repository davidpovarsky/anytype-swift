package service

import (
	"context"
	"testing"

	"github.com/anyproto/anytype-heart/pb"
)

type annotationCancelPanicHandler struct {
	ClientCommandsHandler
}

func (annotationCancelPanicHandler) AnnotationImportCancel(context.Context, *pb.RpcAnnotationImportCancelRequest) *pb.RpcAnnotationImportCancelResponse {
	panic("owned annotation cancel control")
}

func TestAnnotationImportCancelGeneratedPanicIsUnobservedFailure(t *testing.T) {
	// This is the real generated mobile wrapper. No parallel execution: both
	// original generated globals are restored after this one bounded control.
	oldHandler, oldPanic := clientCommandsHandler, PanicHandler
	t.Cleanup(func() {
		clientCommandsHandler, PanicHandler = oldHandler, oldPanic
	})
	clientCommandsHandler = annotationCancelPanicHandler{}
	panics := 0
	PanicHandler = func(value interface{}) {
		panics++
		if value != "owned annotation cancel control" {
			t.Fatalf("unexpected recovered value: %v", value)
		}
	}

	if pb.RpcAnnotationImportCancelResponseError_NULL != 0 ||
		pb.RpcAnnotationImportCancelResponseError_BAD_INPUT != 1 ||
		pb.RpcAnnotationImportCancelResponseError_RUNTIME_UNAVAILABLE != 2 ||
		pb.RpcAnnotationImportCancelResponseError_UNKNOWN_ERROR != 3 {
		t.Fatal("existing cancellation error wire values changed")
	}
	request, err := (&pb.RpcAnnotationImportCancelRequest{}).Marshal()
	if err != nil {
		t.Fatal(err)
	}
	var response pb.RpcAnnotationImportCancelResponse
	if err = response.Unmarshal(AnnotationImportCancel(request)); err != nil {
		t.Fatal(err)
	}
	if panics != 1 || response.Error == nil ||
		response.Error.Code != pb.RpcAnnotationImportCancelResponseError_UNKNOWN_ERROR ||
		response.Error.Description != "panic recovered" {
		t.Fatalf("generated panic recovery did not return explicit unknown error: panics=%d response=%v", panics, &response)
	}
	if response.Disposition != pb.RpcAnnotationImportCancelResponse_NOT_OBSERVED ||
		response.ImportProtocol != "" {
		t.Fatalf("panic recovery invented cancellation or drain observation: %v", &response)
	}

	// The existing malformed-input branch keeps BAD_INPUT=1 and must never
	// reach the handler or report native cancellation/drain.
	if err = response.Unmarshal(AnnotationImportCancel([]byte{0x0a, 0x80})); err != nil {
		t.Fatal(err)
	}
	if panics != 1 || response.Error == nil ||
		response.Error.Code != pb.RpcAnnotationImportCancelResponseError_BAD_INPUT ||
		response.Disposition != pb.RpcAnnotationImportCancelResponse_NOT_OBSERVED {
		t.Fatalf("malformed input changed original refusal semantics: panics=%d response=%v", panics, &response)
	}
}
