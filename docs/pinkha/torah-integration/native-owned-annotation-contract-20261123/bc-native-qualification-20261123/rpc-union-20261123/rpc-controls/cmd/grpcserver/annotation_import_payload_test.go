//go:build !nogrpcserver && !_test

package main

import (
	"bytes"
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/golang/protobuf/ptypes/wrappers"
	grpc_zap "github.com/grpc-ecosystem/go-grpc-middleware/logging/zap"
	"github.com/grpc-ecosystem/grpc-opentracing/go/otgrpc"
	"github.com/opentracing/opentracing-go"
	"github.com/opentracing/opentracing-go/mocktracer"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"google.golang.org/grpc"
)

// These are interceptor controls with explicit synthetic messages and a test
// tracer. They never invoke an annotation import, account, Space, or native SDK.
func TestAnnotationImportPayloadPolicyExactMethods(t *testing.T) {
	for _, item := range []struct {
		method string
		allow  bool
	}{
		{"/anytype.ClientCommands/AnnotationImport", false},
		{"/anytype.ClientCommands/AnnotationImportCancel", false},
		{"/anytype.ClientCommands/AnnotationSchemaRegister", true},
		{"/anytype.ClientCommands/ObjectImport", true},
		{"/anytype.ClientCommands/AnnotationImportOther", true},
		{"/another.Service/AnnotationImport", true},
		{"/anytype.ClientCommands/AnnotationImport/", true},
		{"AnnotationImport", true},
	} {
		if got := annotationImportPayloadsAllowed(item.method); got != item.allow {
			t.Fatalf("full-method policy differs for %q", item.method)
		}
	}
}

func TestAnnotationImportPayloadLoggerSuppressesBothDirections(t *testing.T) {
	for _, method := range []string{
		"/anytype.ClientCommands/AnnotationImport",
		"/anytype.ClientCommands/AnnotationImportCancel",
		"/anytype.ClientCommands/AnnotationSchemaRegister",
	} {
		t.Run(method, func(t *testing.T) {
			var output bytes.Buffer
			logger := zap.New(zapcore.NewCore(
				zapcore.NewJSONEncoder(zap.NewProductionEncoderConfig()),
				zapcore.AddSync(&output), zapcore.DebugLevel))
			interceptor := grpc_zap.PayloadUnaryServerInterceptor(logger,
				func(_ context.Context, fullMethod string, _ interface{}) bool {
					return annotationImportPayloadsAllowed(fullMethod)
				})
			request := &wrappers.StringValue{Value: "synthetic-request-payload"}
			response := &wrappers.StringValue{Value: "synthetic-response-payload"}
			calls := 0
			ctx := context.Background()
			got, err := interceptor(ctx, request, &grpc.UnaryServerInfo{FullMethod: method},
				func(actual context.Context, value interface{}) (interface{}, error) {
					calls++
					if actual != ctx || value != request {
						t.Fatal("payload policy changed original context or request identity")
					}
					return response, nil
				})
			if err != nil || got != response || calls != 1 {
				t.Fatal("payload policy changed original handler outcome")
			}
			if !annotationImportPayloadsAllowed(method) {
				if output.Len() != 0 {
					t.Fatal("excluded method emitted request or response payload")
				}
			} else {
				for _, expected := range []string{
					"grpc.request.content", "grpc.response.content",
					request.Value, response.Value,
				} {
					if !strings.Contains(output.String(), expected) {
						t.Fatalf("unrelated method lost its original payload log: %q", expected)
					}
				}
			}
		})
	}
}

func TestAnnotationImportTracingKeepsOriginalSpanAndErrorWithoutPayloads(t *testing.T) {
	for _, method := range []string{
		"/anytype.ClientCommands/AnnotationImport",
		"/anytype.ClientCommands/AnnotationImportCancel",
		"/anytype.ClientCommands/AnnotationSchemaRegister",
	} {
		for _, configured := range []bool{false, true} {
			for _, failure := range []bool{false, true} {
				name := method
				if configured {
					name += "/payloads-enabled"
				} else {
					name += "/payloads-disabled"
				}
				if failure {
					name += "/error"
				} else {
					name += "/success"
				}
				t.Run(name, func(t *testing.T) {
					tracer := mocktracer.New()
					var options []otgrpc.Option
					if configured {
						options = append(options, otgrpc.LogPayloads())
					}
					interceptor := annotationImportTraceBoundary(
						otgrpc.OpenTracingServerInterceptor(tracer, options...),
						otgrpc.OpenTracingServerInterceptor(tracer))
					request := &wrappers.StringValue{Value: "synthetic-request-payload"}
					response := &wrappers.StringValue{Value: "synthetic-response-payload"}
					var originalError error
					if failure {
						originalError = errors.New("fixed synthetic interceptor error")
					}
					calls := 0
					got, err := interceptor(context.Background(), request,
						&grpc.UnaryServerInfo{FullMethod: method},
						func(actual context.Context, value interface{}) (interface{}, error) {
							calls++
							if value != request || opentracing.SpanFromContext(actual) == nil {
								t.Fatal("trace boundary lost original request or actual server span")
							}
							return response, originalError
						})
					if got != response || err != originalError || calls != 1 {
						t.Fatal("trace boundary changed original handler outcome")
					}
					spans := tracer.FinishedSpans()
					if len(spans) != 1 || spans[0].OperationName != method {
						t.Fatal("excluded method must still retain its original completed span")
					}
					requestFields, responseFields, errorFields := 0, 0, 0
					for _, entry := range spans[0].Logs() {
						for _, field := range entry.Fields {
							switch field.Key {
							case "gRPC request":
								requestFields++
							case "gRPC response":
								responseFields++
							case "message":
								if failure && field.ValueString == originalError.Error() {
									errorFields++
								}
							}
							if !annotationImportPayloadsAllowed(method) &&
								(strings.Contains(field.ValueString, request.Value) ||
									strings.Contains(field.ValueString, response.Value)) {
								t.Fatal("excluded trace retained a synthetic payload")
							}
						}
					}
					wantRequest, wantResponse, wantError := 0, 0, 0
					if configured && annotationImportPayloadsAllowed(method) {
						wantRequest = 1
						if !failure {
							wantResponse = 1
						}
					}
					if failure {
						wantError = 1
					}
					if requestFields != wantRequest || responseFields != wantResponse || errorFields != wantError {
						t.Fatal("trace payload/error observations differ from the original configured semantics")
					}
				})
			}
		}
	}
}
