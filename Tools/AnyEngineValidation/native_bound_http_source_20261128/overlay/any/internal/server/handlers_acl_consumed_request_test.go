package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/labstack/echo/v4"

	"github.com/anyproto/any/internal/api"
)

// Approval addresses a pending request record; decline resolves the current
// pending record for an identity. Once consumed, either typed native absence
// must remain an ordinary not-found response, including through wrappers.
// This test does not add an expected-request-record fence to decline.
func TestACLConsumedRecordErrorsKeepTypedContract(t *testing.T) {
	const private = "private-consumed-request-diagnostic"
	for _, test := range []struct {
		name    string
		inputs  []error
		status  int
		code    string
		message string
	}{
		{"missing_request", []error{list.ErrNoSuchRequest}, http.StatusNotFound, "acl.record_not_found", "ACL request or record is not present"},
		{"consumed_request_wrapped", []error{fmt.Errorf("%s: %w", private, list.ErrNoSuchRequest)}, http.StatusNotFound, "acl.record_not_found", "ACL request or record is not present"},
		{"missing_record", []error{list.ErrNoSuchRecord}, http.StatusNotFound, "acl.record_not_found", "ACL request or record is not present"},
		{"consumed_record_wrapped", []error{fmt.Errorf("%s: %w", private, list.ErrNoSuchRecord)}, http.StatusNotFound, "acl.record_not_found", "ACL request or record is not present"},
		{"cancelled_or_deadline", []error{errors.Join(context.Canceled, list.ErrNoSuchRequest), errors.Join(context.DeadlineExceeded, list.ErrNoSuchRecord)}, http.StatusServiceUnavailable, "server.unavailable", "request cancelled"},
		{"untyped_lookalike", []error{errors.New("no such request: " + private)}, http.StatusInternalServerError, "internal", "internal error"},
	} {
		t.Run(test.name, func(t *testing.T) {
			for _, input := range test.inputs {
				e := echo.New()
				recorder := httptest.NewRecorder()
				c := e.NewContext(httptest.NewRequest(http.MethodPost, "/v1/spaces/requested-space/acl/accept", nil), recorder)
				details := map[string]any{"spaceId": "requested-space", "requestRecordId": "requested-record"}
				if err := aclOpError(c, input, details); err != nil {
					t.Fatal(err)
				}
				if recorder.Code != test.status {
					t.Fatalf("status = %d, want %d; body = %s", recorder.Code, test.status, recorder.Body.String())
				}
				var envelope api.ErrorEnvelope
				if err := json.Unmarshal(recorder.Body.Bytes(), &envelope); err != nil {
					t.Fatal(err)
				}
				if envelope.Error.Code != test.code || envelope.Error.Message != test.message {
					t.Fatalf("error = %#v, want %s / %q", envelope.Error, test.code, test.message)
				}
				if strings.Contains(recorder.Body.String(), private) {
					t.Fatal("wrapped native diagnostic escaped the static response")
				}
				if test.status == http.StatusNotFound {
					if envelope.Error.Details["spaceId"] != "requested-space" || envelope.Error.Details["requestRecordId"] != "requested-record" {
						t.Fatal("known caller scope was lost")
					}
				} else if test.status == http.StatusServiceUnavailable && len(envelope.Error.Details) != 0 {
					t.Fatal("cancellation precedence must retain its original empty details")
				}
			}
		})
	}
}
