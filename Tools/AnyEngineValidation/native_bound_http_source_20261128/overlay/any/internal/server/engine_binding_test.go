package server

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	anysyncsdk "github.com/anyproto/any-sync-sdk"
	"github.com/labstack/echo/v4"

	"github.com/anyproto/any/internal/api"
	"github.com/anyproto/any/internal/config"
	"github.com/anyproto/any/internal/push"
)

func newBoundGateTestEngine(t *testing.T, account string) *engine {
	t.Helper()
	e := newEngine()
	e.account = account
	e.networkID = "bound-test-network"
	var err error
	e.runID, err = mintControlToken()
	if err != nil {
		t.Fatal(err)
	}
	if !validExpectedRun(e.runID) {
		t.Fatal("fresh native token is not the declared lower-case 32-byte hex")
	}
	t.Cleanup(e.cancel)
	return e
}

func boundGateTestContext(method, path string, account, run string) (echo.Context, *httptest.ResponseRecorder) {
	e := echo.New()
	r := httptest.NewRequest(method, "/v1/pinkha/bound/spaces/space/settings", strings.NewReader("{}"))
	r.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	if account != "" {
		r.Header.Set(api.ExpectedAccountHeader, account)
	}
	if run != "" {
		r.Header.Set(api.ExpectedRunHeader, run)
	}
	w := httptest.NewRecorder()
	c := e.NewContext(r, w)
	c.SetPath(path)
	c.SetParamNames("spaceId")
	c.SetParamValues("space")
	return c, w
}

func boundTestErrorCode(t testing.TB, body []byte) string {
	t.Helper()
	var envelope api.ErrorEnvelope
	if err := json.Unmarshal(body, &envelope); err != nil {
		t.Fatalf("invalid native error envelope: %v", err)
	}
	return envelope.Error.Code
}

func requireBoundTestClosed(t *testing.T, closed <-chan struct{}) {
	t.Helper()
	select {
	case <-closed:
	case <-time.After(time.Second):
		t.Fatal("owned generation did not drain")
	}
}

func TestBoundEngineGateRejectsABAAndDrainsOriginalGeneration(t *testing.T) {
	var gate engineGate
	first := newBoundGateTestEngine(t, "AAAA")
	middle := newBoundGateTestEngine(t, "BBBB")
	last := newBoundGateTestEngine(t, "AAAA")
	if first.runID == last.runID || first.runID == middle.runID {
		t.Fatal("fresh boots must not reuse a run token")
	}
	if holder, err := gate.enterEngineBinding("", "", false); holder != nil || err != nil {
		t.Fatal("a gate without a published engine admitted a binding")
	}
	gate.resetForEngine(first)
	old, err := gate.enterEngineBinding(first.account, first.runID, true)
	if err != nil || old == nil || old.engine != first {
		t.Fatalf("first capture: holder=%p err=%v", old, err)
	}
	var oldOnce sync.Once
	leaveOld := func() { oldOnce.Do(func() { gate.leave(old) }) }
	t.Cleanup(leaveOld)
	firstDrain := gate.close()
	select {
	case <-firstDrain:
		t.Fatal("original holder was not retained across its close")
	default:
	}
	gate.resetForEngine(middle)
	active, err := gate.enterEngineBinding(middle.account, middle.runID, true)
	if err != nil || active == nil || active.engine != middle {
		t.Fatalf("second capture: holder=%p err=%v", active, err)
	}
	secondDrain := gate.close()
	gate.leave(active)
	requireBoundTestClosed(t, secondDrain)
	select {
	case <-firstDrain:
		t.Fatal("the later generation released the earlier holder")
	default:
	}
	gate.resetForEngine(last)
	if holder, err := gate.enterEngineBinding(first.account, first.runID, true); holder != nil || !errors.Is(err, errEngineBindingMismatch) {
		t.Fatalf("A-B-A reused stale authority: holder=%p err=%v", holder, err)
	}
	lastHolder, err := gate.enterEngineBinding(last.account, last.runID, true)
	if err != nil || lastHolder == nil || lastHolder.engine != last {
		t.Fatalf("new A binding refused: holder=%p err=%v", lastHolder, err)
	}
	gate.leave(lastHolder)
	leaveOld()
	requireBoundTestClosed(t, firstDrain)
	requireBoundTestClosed(t, gate.close())
	if old.engine != first || first.ctx.Err() != nil {
		t.Fatal("a later publication changed the original captured owner")
	}
}

func TestBoundEngineAdmissionPreservesOriginalOutcomeAfterRetirement(t *testing.T) {
	for _, status := range []int{http.StatusNoContent, http.StatusConflict} {
		t.Run(http.StatusText(status), func(t *testing.T) {
			first := newBoundGateTestEngine(t, "AAAA")
			next := newBoundGateTestEngine(t, "BBBB")
			first.sdk, next.sdk = &anysyncsdk.SDK{}, &anysyncsdk.SDK{}
			first.push, next.push = &push.Service{}, &push.Service{}
			d := &deps{sdk: first.sdk, push: first.push, shutdownCtx: first.ctx}
			d.gate.resetForEngine(first)
			c, recorder := boundGateTestContext(http.MethodPatch,
				"/v1/pinkha/bound/spaces/:spaceId/settings", first.account, first.runID)
			var admittedEffects int
			var firstDrain <-chan struct{}
			err := d.admitEngineBinding(c, func(c echo.Context) error {
				if boundRequestEngine(c) != first || d.requestPush(c) != first.push {
					return errors.New("request did not capture its original owner")
				}
				admittedEffects++
				firstDrain = d.gate.close()
				first.done.Store(true)
				first.cancel()
				d.sdk, d.push, d.shutdownCtx = next.sdk, next.push, next.ctx
				d.gate.resetForEngine(next)
				if boundRequestEngine(c).sdk != first.sdk || d.requestPush(c) != first.push {
					return errors.New("retired request followed replacement global fields")
				}
				if status == http.StatusNoContent {
					return c.NoContent(status)
				}
				return writeError(c, status, "bound.fixture_original_error", "original effect result", nil)
			})
			if err != nil {
				t.Fatal(err)
			}
			if admittedEffects != 1 || recorder.Code != status {
				t.Fatalf("original result changed: effects=%d code=%d body=%s", admittedEffects, recorder.Code, recorder.Body.String())
			}
			if recorder.Header().Get(api.BindingContractHeader) != api.EngineBindingContract ||
				recorder.Header().Get(api.BoundAccountHeader) != first.account ||
				recorder.Header().Get(api.BoundRunHeader) != first.runID {
				t.Fatal("acknowledgement did not retain the original admitted binding")
			}
			if status == http.StatusConflict && boundTestErrorCode(t, recorder.Body.Bytes()) != "bound.fixture_original_error" {
				t.Fatal("post-effect retirement replaced the original error")
			}
			requireBoundTestClosed(t, firstDrain)
			requireBoundTestClosed(t, d.gate.close())
		})
	}
}

func TestBoundEngineHeadersFailBeforeDispatchAndBindingIsExplicit(t *testing.T) {
	first := newBoundGateTestEngine(t, "AAAA")
	d := &deps{cfg: config.Defaults()}
	d.gate.resetForEngine(first)
	staleRun := "0" + first.runID[1:]
	if staleRun == first.runID {
		staleRun = "1" + first.runID[1:]
	}
	for _, tc := range []struct {
		name    string
		account []string
		run     []string
		status  int
		code    string
	}{
		{"missing", nil, nil, http.StatusBadRequest, "request.invalid_binding"},
		{"duplicate-account", []string{first.account, first.account}, []string{first.runID}, http.StatusBadRequest, "request.invalid_binding"},
		{"duplicate-run", []string{first.account}, []string{first.runID, first.runID}, http.StatusBadRequest, "request.invalid_binding"},
		{"combined-run", []string{first.account}, []string{first.runID + "," + first.runID}, http.StatusBadRequest, "request.invalid_binding"},
		{"upper-run", []string{first.account}, []string{strings.Repeat("A", 64)}, http.StatusBadRequest, "request.invalid_binding"},
		{"foreign-account", []string{"BBBB"}, []string{first.runID}, http.StatusConflict, "auth.binding_mismatch"},
		{"stale-run", []string{first.account}, []string{staleRun}, http.StatusConflict, "auth.binding_mismatch"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			c, recorder := boundGateTestContext(http.MethodPatch, "/v1/pinkha/bound/spaces/:spaceId/settings", "", "")
			c.Request().Header[api.ExpectedAccountHeader] = tc.account
			c.Request().Header[api.ExpectedRunHeader] = tc.run
			invoked := false
			err := d.admitEngineBinding(c, func(echo.Context) error { invoked = true; return nil })
			if err != nil || invoked || recorder.Code != tc.status {
				t.Fatalf("bad tuple dispatched or wrong refusal: invoked=%v err=%v status=%d", invoked, err, recorder.Code)
			}
			if boundTestErrorCode(t, recorder.Body.Bytes()) != tc.code ||
				recorder.Header().Get(api.BoundRunHeader) != "" {
				t.Fatal("pre-admission refusal published a bound acknowledgement")
			}
		})
	}
	// Exercise route registration and middleware, with no SDK or account I/O.
	router := buildEcho(d)
	got := doJSON(t, router, http.MethodGet, "/v1/auth/engine-binding", "")
	if got.Code != http.StatusOK {
		t.Fatalf("explicit binding GET: %d %s", got.Code, got.Body.String())
	}
	var binding api.EngineBindingResponse
	if err := json.Unmarshal(got.Body.Bytes(), &binding); err != nil {
		t.Fatal(err)
	}
	if binding.Contract != api.EngineBindingContract || binding.AccountId != first.account ||
		binding.RunId != first.runID || binding.NetworkId != first.networkID {
		t.Fatalf("binding GET did not report the captured engine: %+v", binding)
	}
	requireBoundTestClosed(t, d.gate.close())
	if got = doJSON(t, router, http.MethodGet, "/v1/auth/engine-binding", ""); got.Code != http.StatusUnauthorized || boundTestErrorCode(t, got.Body.Bytes()) != "auth.required" {
		t.Fatalf("closed binding GET: %d %s", got.Code, got.Body.String())
	}
	if got = doJSON(t, router, http.MethodPost, "/v1/pinkha/bound/unsupported", "{}"); got.Code != http.StatusNotFound {
		t.Fatalf("unsupported bound route must remain 404: %d", got.Code)
	}
}

func TestBoundEngineRequestAvoidsAuthMutexAndUsesCapturedCancellation(t *testing.T) {
	first := newBoundGateTestEngine(t, "AAAA")
	unrelated := newBoundGateTestEngine(t, "BBBB")
	d := &deps{shutdownCtx: unrelated.ctx}
	d.gate.resetForEngine(first)
	c, recorder := boundGateTestContext(http.MethodPatch, "/v1/pinkha/bound/spaces/:spaceId/settings", first.account, first.runID)
	entered := make(chan context.Context, 1)
	finish := make(chan struct{})
	var finishOnce sync.Once
	release := func() { finishOnce.Do(func() { close(finish) }) }
	t.Cleanup(release)
	done := make(chan error, 1)
	d.authMu.Lock()
	go func() {
		done <- d.admitEngineBinding(c, func(c echo.Context) error {
			entered <- c.Request().Context()
			select {
			case <-finish:
				return c.NoContent(http.StatusNoContent)
			case <-time.After(3 * time.Second):
				return errors.New("bounded fixture handler did not receive release")
			}
		})
	}()
	var captured context.Context
	select {
	case captured = <-entered:
		d.authMu.Unlock()
	case <-time.After(time.Second):
		d.authMu.Unlock()
		release()
		select {
		case <-done:
		case <-time.After(4 * time.Second):
			t.Fatal("request did not join after auth-mutex test release")
		}
		t.Fatal("bound request tried to acquire authMu")
	}
	unrelated.cancel()
	if captured.Err() != nil {
		release()
		select {
		case <-done:
		case <-time.After(4 * time.Second):
			t.Fatal("owned request did not join after release")
		}
		t.Fatal("request used the mutable global shutdown context")
	}
	first.cancel()
	select {
	case <-captured.Done():
	case <-time.After(time.Second):
		release()
		select {
		case <-done:
		case <-time.After(4 * time.Second):
			t.Fatal("owned request did not join after release")
		}
		t.Fatal("captured engine retirement did not cancel the request")
	}
	release()
	select {
	case err := <-done:
		if err != nil || recorder.Code != http.StatusNoContent {
			t.Fatalf("joined request: %v, status=%d", err, recorder.Code)
		}
	case <-time.After(4 * time.Second):
		t.Fatal("owned request failed to join")
	}
	requireBoundTestClosed(t, d.gate.close())
}
