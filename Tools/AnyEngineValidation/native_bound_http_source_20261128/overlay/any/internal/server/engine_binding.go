package server

import (
	"context"
	"errors"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/labstack/echo/v4"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any/internal/api"
	"github.com/anyproto/any/internal/push"
)

var errEngineBindingMismatch = errors.New("engine binding mismatch")

type engineBindingContextKey struct{}
type engineBindingSpaceContextKey struct{}

// resetForEngine publishes the immutable engine pointer with its admission
// generation. Lifecycle callers already serialize publication with authMu;
// request admission itself only takes the gate mutex.
func (g *engineGate) resetForEngine(eng *engine) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.cur = &gateGen{engine: eng}
}

// enterEngineBinding compares the complete requested tuple and increments
// its generation in one transaction. A later close or replacement cannot
// retarget this holder, including after a timed-out old-generation drain.
func (g *engineGate) enterEngineBinding(account, run string, expected bool) (*gateGen, error) {
	g.mu.Lock()
	defer g.mu.Unlock()
	gen := g.cur
	if gen == nil || gen.closed || gen.engine == nil {
		return nil, nil
	}
	eng := gen.engine
	if eng.account == "" || eng.runID == "" || eng.networkID == "" ||
		eng.ctx == nil || eng.ctx.Err() != nil || eng.done.Load() {
		return nil, nil
	}
	if expected && (eng.account != account || eng.runID != run) {
		return nil, errEngineBindingMismatch
	}
	gen.n++
	return gen, nil
}

func engineBindingRoute(path string) bool {
	switch path {
	case "/v1/auth/engine-binding",
		"/v1/pinkha/bound/spaces/:spaceId/settings",
		"/v1/pinkha/bound/spaces/:spaceId/properties/:objectId/set/:typeId":
		return true
	}
	return false
}

func boundRequestEngine(c echo.Context) *engine {
	eng, _ := c.Request().Context().Value(engineBindingContextKey{}).(*engine)
	return eng
}

func boundRequestSpace(c echo.Context) space.Space {
	sp, _ := c.Request().Context().Value(engineBindingSpaceContextKey{}).(space.Space)
	return sp
}

func oneBindingHeader(header http.Header, name string) (string, bool) {
	var values []string
	for key, current := range header {
		if strings.EqualFold(key, name) {
			values = append(values, current...)
		}
	}
	if len(values) != 1 || values[0] == "" {
		return "", false
	}
	return values[0], true
}

func validExpectedAccount(value string) bool {
	if len(value) == 0 || len(value) > 128 {
		return false
	}
	const alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
	for _, ch := range value {
		if !strings.ContainsRune(alphabet, ch) {
			return false
		}
	}
	return true
}

func validExpectedRun(value string) bool {
	if len(value) != 64 {
		return false
	}
	for _, ch := range value {
		if !(ch >= '0' && ch <= '9') && !(ch >= 'a' && ch <= 'f') {
			return false
		}
	}
	return true
}

func (d *deps) admitEngineBinding(c echo.Context, next echo.HandlerFunc) error {
	expected := c.Path() != "/v1/auth/engine-binding"
	var account, run string
	if expected {
		var accountOK, runOK bool
		account, accountOK = oneBindingHeader(c.Request().Header, api.ExpectedAccountHeader)
		run, runOK = oneBindingHeader(c.Request().Header, api.ExpectedRunHeader)
		if !accountOK || !runOK || !validExpectedAccount(account) || !validExpectedRun(run) {
			return writeError(c, http.StatusBadRequest, "request.invalid_binding",
				"exactly one valid expected account and run header is required", nil)
		}
	}
	holder, err := d.gate.enterEngineBinding(account, run, expected)
	if errors.Is(err, errEngineBindingMismatch) {
		return writeError(c, http.StatusConflict, "auth.binding_mismatch",
			"the requested engine binding is no longer current", nil)
	}
	if holder == nil {
		return writeError(c, http.StatusUnauthorized, "auth.required",
			"no account engine is admitting bound requests", nil)
	}
	defer d.gate.leave(holder)
	eng := holder.engine
	header := c.Response().Header()
	header.Set(api.BindingContractHeader, api.EngineBindingContract)
	header.Set(api.BoundAccountHeader, eng.account)
	header.Set(api.BoundRunHeader, eng.runID)

	// Cancellation belongs to the captured engine, never the next d.sdk or
	// shutdownCtx. The response carries this binding even on an original
	// operation error; an admitted effect is not reclassified after a switch.
	ctx, cancel := context.WithCancel(c.Request().Context())
	defer cancel()
	ctx = context.WithValue(ctx, engineBindingContextKey{}, eng)
	resp := c.Response()
	var mu sync.Mutex
	finished := false
	stop := context.AfterFunc(eng.ctx, func() {
		cancel()
		mu.Lock()
		defer mu.Unlock()
		if !finished {
			_ = http.NewResponseController(resp).SetWriteDeadline(time.Now().Add(teardownWriteGrace))
		}
	})
	defer func() {
		stop()
		mu.Lock()
		finished = true
		mu.Unlock()
	}()
	c.SetRequest(c.Request().WithContext(ctx))
	return next(c)
}

func registerEngineBindingRoutes(g *echo.Group, d *deps) {
	g.GET("/auth/engine-binding", d.engineBindingStatus)
	g.PATCH("/pinkha/bound/spaces/:spaceId/settings", d.boundSpaceSettingsPatch)
	g.POST("/pinkha/bound/spaces/:spaceId/properties/:objectId/set/:typeId", d.boundLocalPropertiesSet)
}

func (d *deps) engineBindingStatus(c echo.Context) error {
	eng := boundRequestEngine(c)
	if eng == nil || c.Request().Context().Err() != nil {
		return writeError(c, http.StatusUnauthorized, "auth.required",
			"no account engine is admitting bound requests", nil)
	}
	return c.JSON(http.StatusOK, api.EngineBindingResponse{
		Contract: api.EngineBindingContract, NetworkId: eng.networkID,
		AccountId: eng.account, RunId: eng.runID,
	})
}

// prepareBoundSpace resolves only through the captured SDK. The current signed
// READ check precedes native object/type/property metadata inspection. The
// mutation provider repeats its final current-head/lifetime admission.
func (d *deps) prepareBoundSpace(c echo.Context) (space.Space, error, bool) {
	eng := boundRequestEngine(c)
	if eng == nil || eng.sdk == nil {
		return nil, writeError(c, http.StatusUnauthorized, "auth.required",
			"bound request has no captured account engine", nil), true
	}
	id := c.Param("spaceId")
	if id == "" {
		return nil, writeError(c, http.StatusBadRequest, "request.missing_field",
			"spaceId required", nil), true
	}
	// Preserve the original account-private tech-space route fence using
	// this holder's SDK, even if the next engine has replaced d.sdk.
	if id == eng.sdk.TechSpaceId() {
		return nil, unsupportedOnTechSpace(c, id), true
	}
	sp, err := eng.sdk.Spaces().Get(c.Request().Context(), id)
	if err != nil {
		return nil, boundSpaceError(c, err, id), true
	}
	current, ok := sp.(space.CurrentReaderAuthority)
	if !ok {
		return nil, writeError(c, http.StatusNotImplemented, "auth.binding_unsupported",
			"this space does not support bound current-reader operations", nil), true
	}
	if err := current.CheckCurrentReader(c.Request().Context()); err != nil {
		return nil, sdkOpError(c, err, map[string]any{"spaceId": id}), true
	}
	c.SetRequest(c.Request().WithContext(context.WithValue(
		c.Request().Context(), engineBindingSpaceContextKey{}, sp)))
	return sp, nil, false
}

func (d *deps) boundSpaceSettingsPatch(c echo.Context) error {
	if _, response, done := d.prepareBoundSpace(c); done {
		return response
	}
	return d.spaceSettingsPatch(c)
}

func (d *deps) boundLocalPropertiesSet(c echo.Context) error {
	if _, response, done := d.prepareBoundSpace(c); done {
		return response
	}
	// Only the compiled immutable native any schema is supported. Mutable
	// definition owners need a separately qualified owner+target lock; a
	// preflight registry read alone cannot make their local apply atomic.
	if c.Param("typeId") != "any" {
		return writeError(c, http.StatusNotImplemented, "auth.binding_unsupported",
			"bound local-property updates require immutable native any properties", nil)
	}
	return d.propertiesSetWithCondition(c, false)
}

// requestPush retains the original push owner for an already-admitted effect.
func (d *deps) requestPush(c echo.Context) *push.Service {
	if eng := boundRequestEngine(c); eng != nil {
		return eng.push
	}
	return d.push
}

// finishBoundPreparationError is only for refusal before dispatch. It withholds
// native validation details if current read membership was lost during
// preparation. It is never called after a local or synced effect was attempted.
func finishBoundPreparationError(c echo.Context, original func() error) error {
	if sp := boundRequestSpace(c); sp != nil {
		current, ok := sp.(space.CurrentReaderAuthority)
		if !ok {
			return writeError(c, http.StatusNotImplemented, "auth.binding_unsupported",
				"current-reader preparation is unavailable", nil)
		}
		if err := current.CheckCurrentReader(c.Request().Context()); err != nil {
			return sdkOpError(c, err, map[string]any{"spaceId": sp.Id()})
		}
	}
	return original()
}

// boundSpaceError retains the original Space-state errors and the native
// current-ACL refusal. Legacy spaceError is unchanged for unbound callers.
func boundSpaceError(c echo.Context, err error, id string) error {
	if errors.Is(err, space.ErrSpaceUnknown) || errors.Is(err, space.ErrSpaceDeleted) ||
		errors.Is(err, space.ErrSpaceNotAccepted) {
		return spaceError(c, err, id)
	}
	return sdkOpError(c, err, map[string]any{"spaceId": id})
}
