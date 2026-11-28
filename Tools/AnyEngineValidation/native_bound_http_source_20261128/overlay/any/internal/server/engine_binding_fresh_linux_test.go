//go:build linux

package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"

	anysyncsdk "github.com/anyproto/any-sync-sdk"
	sdkauth "github.com/anyproto/any-sync-sdk/auth"
	sdkconfig "github.com/anyproto/any-sync-sdk/config"
	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any-sync/app/logger"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/require"
	"github.com/valyala/fastjson"

	"github.com/anyproto/any/internal/api"
	"github.com/anyproto/any/internal/config"
)

// This is a new in-process HTTP-handler fixture over one real headless SDK.
// All identities and databases are new. It uses no retained account, upload,
// access-code or existing test method. The qualifier supplies OS network denial.
func newBoundHTTPNativeFixture(t *testing.T) (*deps, context.Context) {
	t.Helper()
	raw := os.Getenv("PINKHA_FRESH_FILES_FIXTURE_ROOT")
	require.NotEmpty(t, raw)
	require.Equal(t, filepath.Clean(raw), raw)
	require.True(t, filepath.IsAbs(raw))
	relative, err := filepath.Rel("/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127", raw)
	require.NoError(t, err)
	parts := strings.Split(relative, string(filepath.Separator))
	require.Len(t, parts, 2)
	require.Regexp(t, regexp.MustCompile("^attempt[1-9][0-9]{0,2}$"), parts[0])
	require.Equal(t, "fixtures", parts[1])
	physical, err := filepath.EvalSymlinks(raw)
	require.NoError(t, err)
	require.Equal(t, raw, physical)
	info, err := os.Lstat(raw)
	require.NoError(t, err)
	require.True(t, info.IsDir())
	require.Equal(t, os.FileMode(0700), info.Mode().Perm())
	require.NotContains(t, t.Name(), "/")
	root := filepath.Join(raw, t.Name())
	require.NoError(t, os.Mkdir(root, 0700), "exclusive new retained fixture")
	require.NoError(t, os.Chmod(root, 0700))

	status, err := os.ReadFile("/proc/self/status")
	require.NoError(t, err)
	require.Contains(t, string(status), "NoNewPrivs:\t1")
	require.Contains(t, string(status), "Seccomp:\t2")
	socket, err := syscall.Socket(syscall.AF_INET, syscall.SOCK_STREAM, 0)
	require.NoError(t, err)
	connectErr := syscall.Connect(socket, &syscall.SockaddrInet4{Port: 9, Addr: [4]byte{127, 0, 0, 1}})
	require.NoError(t, syscall.Close(socket))
	require.ErrorIs(t, connectErr, syscall.EPERM)

	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	t.Cleanup(cancel)
	accountKey, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	deviceKey, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	networkKey, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	node, err := accountdata.NewRandom()
	require.NoError(t, err)
	accountRaw, err := accountKey.Raw()
	require.NoError(t, err)
	deviceRaw, err := deviceKey.Raw()
	require.NoError(t, err)
	provider, err := sdkauth.NewKeyProvider(sdkauth.KeyConfig{AccountKey: accountRaw, DeviceKey: deviceRaw})
	clear(accountRaw)
	clear(deviceRaw)
	require.NoError(t, err)
	configuration := fmt.Sprintf("id: fresh-bound-http\nnetworkId: %s\nfileNetworkId: %s\nnodes:\n- peerId: %s\n  addresses: [127.0.0.1:1]\n  types: [coordinator, tree, consensus]\ncreationTime: '2026-11-28T00:00:00Z'\n",
		networkKey.GetPublic().Network(), networkKey.GetPublic().Network(), node.PeerId)
	disabled := false
	sdk, err := anysyncsdk.Open(ctx, sdkconfig.Config{
		Storage:  sdkconfig.Storage{DataDir: filepath.Join(root, "new-sdk"), Topology: sdkconfig.StorageShared},
		Network:  sdkconfig.Network{NodeConfYAML: []byte(configuration)},
		Headless: true,
		P2P:      sdkconfig.P2P{Enabled: &disabled, LocalDiscovery: &disabled, Global: sdkconfig.GlobalP2P{Enabled: &disabled}},
		Types:    serverTypes(), Collections: serverCollections(), Modules: serverModules(),
	}, provider)
	require.NoError(t, err)
	eng := newEngine()
	eng.sdk = sdk
	var d *deps
	t.Cleanup(func() {
		closed := make(chan struct{})
		go func() {
			if d == nil {
				eng.closeResources(logger.NewNamed("bound-http-setup-test"))
			} else {
				d.teardownEngine(logger.NewNamed("bound-http-test"), api.SubscribeClosedServerShutdown)
			}
			close(closed)
		}()
		select {
		case <-closed:
		case <-time.After(10 * time.Second):
			t.Fatal("fresh captured engine did not drain and close")
		}
	})
	eng.account = sdk.Account().Id()
	eng.networkID = networkKey.GetPublic().Network()
	eng.runID, err = mintControlToken()
	require.NoError(t, err)
	eng.dir = filepath.Join(root, "new-sdk")
	require.Equal(t, accountKey.GetPublic().Account(), eng.account)
	cfg := config.Defaults()
	cfg.DataDir = root
	cfg.Index.Enabled = false
	d = &deps{
		eng: eng, sdk: sdk, account: eng.account, networkId: eng.networkID,
		root: root, cfg: cfg, runCtx: ctx, shutdownCtx: eng.ctx,
		startedAt: time.Now().UTC(), shutdown: make(chan struct{}, 1),
	}
	d.gate.resetForEngine(eng)
	d.ready.Store(true)

	return d, ctx
}

func boundHTTPNativeRequest(t *testing.T, h http.Handler, eng *engine, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	request := httptest.NewRequest(method, path, strings.NewReader(body))
	request.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	request.Header.Set(api.ExpectedAccountHeader, eng.account)
	request.Header.Set(api.ExpectedRunHeader, eng.runID)
	recorder := httptest.NewRecorder()
	h.ServeHTTP(recorder, request)
	return recorder
}

func requireBoundHTTPNativeACK(t *testing.T, recorder *httptest.ResponseRecorder, eng *engine) {
	t.Helper()
	require.Equal(t, api.EngineBindingContract, recorder.Header().Get(api.BindingContractHeader))
	require.Equal(t, eng.account, recorder.Header().Get(api.BoundAccountHeader))
	require.Equal(t, eng.runID, recorder.Header().Get(api.BoundRunHeader))
}

func TestBoundHTTPFreshOwnerSettingsAndDeclaredLocalBuiltin(t *testing.T) {
	d, ctx := newBoundHTTPNativeFixture(t)
	eng := d.eng
	sp, err := eng.sdk.Spaces().Create(ctx, space.CreateRequest{Name: "new bound HTTP fixture"})
	require.NoError(t, err)
	router := buildEcho(d)
	catalog := doJSON(t, router, http.MethodGet, "/v1/spaces/"+sp.Id()+"/types/any/properties", "")
	require.Equal(t, http.StatusOK, catalog.Code, catalog.Body.String())
	var definitions api.PropertiesListResponse
	require.NoError(t, json.Unmarshal(catalog.Body.Bytes(), &definitions))
	found := 0
	for _, def := range definitions.Properties {
		if def.Id != "pinkhaLastOpenedV1" {
			continue
		}
		found++
		require.Equal(t, "datetime", def.Kind)
		require.Equal(t, "local", def.Scope)
		require.JSONEq(t, `{"type":"datetime","contract":"pinkha-last-opened-local-v1","precision":"seconds"}`, string(def.XFormat))
	}
	require.Equal(t, 1, found, "one explicit native builtin, without a definition write")

	// This builtin's declaration cannot be removed or re-scoped by the
	// ordinary mutable definition API, even by the current Space owner.
	_, addErr := sp.Types().AddProperty(ctx, "any", space.PropertyDraft{Name: "cannot shadow compiled schema",
		Kind: space.PropertyKindDatetime, Scope: space.ScopeLocal})
	require.ErrorIs(t, addErr, space.ErrTypeRegistered)
	require.ErrorIs(t, sp.Types().RemoveProperty(ctx, "any", "pinkhaLastOpenedV1"), space.ErrTypeRegistered)
	require.ErrorIs(t, sp.Types().PatchProperty(ctx, "any", "pinkhaLastOpenedV1",
		space.PropertyPatch{Set: map[string]any{"scope": "synced"}}), space.ErrTypeRegistered)
	afterDeclarationAttempt := doJSON(t, router, http.MethodGet,
		"/v1/spaces/"+sp.Id()+"/types/any/properties", "")
	require.Equal(t, http.StatusOK, afterDeclarationAttempt.Code)
	require.JSONEq(t, catalog.Body.String(), afterDeclarationAttempt.Body.String())

	target := sp.SpaceIndexObjectId()
	require.NotEmpty(t, target)
	navigationValue := fmt.Sprintf("{\"objectId\":%q,\"spaceId\":%q}", target, sp.Id())
	settingsBody, err := json.Marshal(map[string]any{"set": map[string]any{"pinkhaHomeV1": navigationValue}})
	require.NoError(t, err)
	settings := boundHTTPNativeRequest(t, router, eng, http.MethodPatch,
		"/v1/pinkha/bound/spaces/"+sp.Id()+"/settings", string(settingsBody))
	require.Equal(t, http.StatusNoContent, settings.Code, settings.Body.String())
	require.Empty(t, settings.Body.Bytes(), "preserve the original empty 204")
	requireBoundHTTPNativeACK(t, settings, eng)
	info := getSpaceInfo(t, router, sp.Id())
	require.Equal(t, navigationValue, info.Settings["pinkhaHomeV1"])

	property := boundHTTPNativeRequest(t, router, eng, http.MethodPost,
		"/v1/pinkha/bound/spaces/"+sp.Id()+"/properties/"+target+"/set/any",
		`{"patch":{"pinkhaLastOpenedV1":{"$date":1760000123000}}}`)
	require.Equal(t, http.StatusOK, property.Code, property.Body.String())
	var acknowledgement api.ModifyResult
	require.NoError(t, json.Unmarshal(property.Body.Bytes(), &acknowledgement))
	var acknowledgementFields map[string]json.RawMessage
	require.NoError(t, json.Unmarshal(property.Body.Bytes(), &acknowledgementFields))
	require.Len(t, acknowledgementFields, 3)
	for _, key := range []string{"versionId", "changeId", "recordIds"} {
		require.Contains(t, acknowledgementFields, key)
	}
	require.NotEmpty(t, acknowledgement.VersionId)
	require.Empty(t, acknowledgement.ChangeId)
	require.Equal(t, []string{target}, acknowledgement.RecordIds, "LOCAL result retains this one explicit target")
	require.Empty(t, acknowledgement.Rejections)
	requireBoundHTTPNativeACK(t, property, eng)
	row, err := sp.Properties().Get(ctx, target)
	require.NoError(t, err)
	require.NotNil(t, row)
	value := row.Get("any", "pinkhaLastOpenedV1")
	require.NotNil(t, value)
	arena := &fastjson.Arena{}
	milliseconds, err := value.DateTimeMillis()
	require.NoError(t, err)
	require.Equal(t, int64(1760000123000), milliseconds)
	require.JSONEq(t, `{"$date":"2025-10-09T08:55:23.000Z"}`, string(value.FastJson(arena).MarshalTo(nil)))

	objectsRead := doJSON(t, router, http.MethodGet, "/v1/spaces/"+sp.Id()+"/objects/"+target, "")
	propertiesRead := doJSON(t, router, http.MethodGet, "/v1/spaces/"+sp.Id()+"/properties/"+target, "")
	require.Equal(t, http.StatusOK, objectsRead.Code, objectsRead.Body.String())
	require.Equal(t, http.StatusOK, propertiesRead.Code, propertiesRead.Body.String())
	var objectResponse api.ObjectGetResponse
	var propertyResponse api.PropertiesGetResponse
	require.NoError(t, json.Unmarshal(objectsRead.Body.Bytes(), &objectResponse))
	require.NoError(t, json.Unmarshal(propertiesRead.Body.Bytes(), &propertyResponse))
	require.Equal(t, target, objectResponse.ObjectId)
	require.JSONEq(t, string(objectResponse.Record), string(propertyResponse.Record))
	require.JSONEq(t, string(row.FastJson(&fastjson.Arena{}).MarshalTo(nil)), string(objectResponse.Record))

	// This route cannot silently fall back to the old synced route.
	before := string(row.FastJson(&fastjson.Arena{}).MarshalTo(nil))
	refused := boundHTTPNativeRequest(t, router, eng, http.MethodPost,
		"/v1/pinkha/bound/spaces/"+sp.Id()+"/properties/"+target+"/set/any",
		`{"patch":{"name":"must not become a synced write"}}`)
	require.Equal(t, http.StatusBadRequest, refused.Code, refused.Body.String())
	requireBoundHTTPNativeACK(t, refused, eng)
	after, err := sp.Properties().Get(ctx, target)
	require.NoError(t, err)
	require.Equal(t, before, string(after.FastJson(&fastjson.Arena{}).MarshalTo(nil)))
	// A real freshly defined LOCAL property remains outside this narrow new
	// contract. Both API layers refuse it before an effect, even though the
	// target actually carries its declared mutable owner.
	mutableOwner, err := sp.Types().Create(ctx, space.TypeCreateParams{Name: "new mutable local owner"})
	require.NoError(t, err)
	mutableProp, err := sp.Types().AddProperty(ctx, mutableOwner,
		space.PropertyDraft{Name: "new local instant", Kind: space.PropertyKindDatetime, Scope: space.ScopeLocal})
	require.NoError(t, err)
	mutableTarget, err := sp.Objects().Create(ctx, space.CreateObjectOpts{Type: mutableOwner})
	require.NoError(t, err)
	mutableRow, err := sp.Properties().Get(ctx, mutableTarget)
	require.NoError(t, err)
	require.NotNil(t, mutableRow)
	mutableBefore := string(mutableRow.FastJson(&fastjson.Arena{}).MarshalTo(nil))
	mutableBody := fmt.Sprintf("{\"patch\":{%q:{\"$date\":1760000123000}}}", mutableProp)
	unsupported := boundHTTPNativeRequest(t, router, eng, http.MethodPost,
		"/v1/pinkha/bound/spaces/"+sp.Id()+"/properties/"+mutableTarget+"/set/"+mutableOwner, mutableBody)
	require.Equal(t, http.StatusNotImplemented, unsupported.Code, unsupported.Body.String())
	require.Equal(t, "auth.binding_unsupported", boundTestErrorCode(t, unsupported.Body.Bytes()))
	requireBoundHTTPNativeACK(t, unsupported, eng)
	direct, ok := sp.Properties().(space.CurrentReaderLocalProperties)
	require.True(t, ok)
	zero, directErr := direct.SetLocalCurrentReader(ctx, mutableTarget, mutableOwner,
		map[string]any{mutableProp: time.Unix(1760000123, 0).UTC()})
	require.ErrorIs(t, directErr, space.ErrUnsupported)
	require.Zero(t, zero)
	mutableAfter, err := sp.Properties().Get(ctx, mutableTarget)
	require.NoError(t, err)
	require.Equal(t, mutableBefore, string(mutableAfter.FastJson(&fastjson.Arena{}).MarshalTo(nil)))
	// The original private Space deletion is real and belongs solely to this
	// fresh fixture. A known historical index row must not authorize a later
	// bound home update once its current native status is deleted.
	require.NoError(t, eng.sdk.Spaces().Delete(ctx, sp.Id()))
	deletedReply := boundHTTPNativeRequest(t, router, eng, http.MethodPatch,
		"/v1/pinkha/bound/spaces/"+sp.Id()+"/settings", `{"set":{"pinkhaHomeV1":"must not replace a deleted Space"}}`)
	require.Equal(t, http.StatusConflict, deletedReply.Code, deletedReply.Body.String())
	require.Equal(t, "space.deleted", boundTestErrorCode(t, deletedReply.Body.Bytes()))
	requireBoundHTTPNativeACK(t, deletedReply, eng)
	rows, err := eng.sdk.Spaces().List(ctx)
	require.NoError(t, err)
	matched := 0
	for _, current := range rows {
		if current.Id == sp.Id() {
			matched++
			require.Equal(t, navigationValue, current.Settings["pinkhaHomeV1"])
		}
	}
	require.Equal(t, 1, matched, "the private historical row is retained without the refused effect")
}

func TestBoundHTTPTechSpaceRefusalUsesCapturedSDK(t *testing.T) {
	d, _ := newBoundHTTPNativeFixture(t)
	captured := d.eng
	techID := captured.sdk.TechSpaceId()
	require.NotEmpty(t, techID)
	require.Equal(t, captured.account, captured.sdk.Account().Id())
	router := buildEcho(d)
	// Deliberately poison only the mutable global alias. The captured engine
	// still owns the actual SDK; cleanup closes that engine, not this alias.
	d.sdk = &anysyncsdk.SDK{}
	for _, request := range []struct{ method, suffix, body string }{
		{http.MethodPatch, "/settings", `{"set":{"pinkhaHomeV1":"must not write"}}`},
		{http.MethodPost, "/properties/unused/set/any", `{"patch":{"pinkhaLastOpenedV1":{"$date":1760000123000}}}`},
	} {
		recorder := boundHTTPNativeRequest(t, router, captured, request.method,
			"/v1/pinkha/bound/spaces/"+techID+request.suffix, request.body)
		require.Equal(t, http.StatusMethodNotAllowed, recorder.Code, recorder.Body.String())
		require.Equal(t, codeSpaceUnsupported, boundTestErrorCode(t, recorder.Body.Bytes()))
		requireBoundHTTPNativeACK(t, recorder, captured)
	}
}

// The normal teardown deadline is exercised once against a new real SDK.
// The successor generation below has no SDK or background resources: it exists
// only to detect an old deferred close overwriting the new published identity.
func TestBoundHTTPDrainTimeoutKeepsCapturedSDKUntilHolderLeaves(t *testing.T) {
	d, ctx := newBoundHTTPNativeFixture(t)
	original := d.eng
	sp, err := original.sdk.Spaces().Create(ctx, space.CreateRequest{Name: "new retained engine holder"})
	require.NoError(t, err)
	holder, err := d.gate.enterEngineBinding(original.account, original.runID, true)
	require.NoError(t, err)
	require.NotNil(t, holder)
	var once sync.Once
	leave := func() { once.Do(func() { d.gate.leave(holder) }) }
	teardownDone := make(chan struct{})
	t.Cleanup(func() {
		leave()
		select {
		case <-teardownDone:
		case <-time.After(gracefulShutdownDeadline + 2*time.Second):
			t.Error("original teardown goroutine did not join after holder release")
		}
		closeDeadline := time.Now().Add(10 * time.Second)
		for dirHeld(original.dir) {
			if time.Now().After(closeDeadline) {
				t.Error("deferred original resources did not close after cleanup released the holder")
				break
			}
			time.Sleep(10 * time.Millisecond)
		}
	})
	go func() {
		d.teardownEngine(logger.NewNamed("bound-http-drain-test"), api.SubscribeClosedDeauthorized)
		close(teardownDone)
	}()
	select {
	case <-teardownDone:
	case <-time.After(gracefulShutdownDeadline + 2*time.Second):
		t.Fatal("bounded original teardown did not return")
	}
	require.ErrorIs(t, original.ctx.Err(), context.Canceled)
	require.Nil(t, d.eng)
	require.True(t, dirHeld(original.dir), "timed-out holder keeps its original SDK directory owned")
	require.Same(t, original, holder.engine)
	require.Same(t, original.sdk, holder.engine.sdk)
	retainedRow, err := holder.engine.sdk.Spaces().List(ctx)
	require.NoError(t, err, "captured SDK must remain open until the holder drains")
	hasOriginalSpace := false
	for _, row := range retainedRow {
		hasOriginalSpace = hasOriginalSpace || row.Id == sp.Id()
	}
	require.True(t, hasOriginalSpace)

	next := newBoundGateTestEngine(t, "BBBB")
	d.eng, d.sdk, d.account, d.shutdownCtx = next, nil, next.account, next.ctx
	d.gate.resetForEngine(next)
	d.ready.Store(true)
	if stale, refusal := d.gate.enterEngineBinding(original.account, original.runID, true); stale != nil || !errors.Is(refusal, errEngineBindingMismatch) {
		t.Fatalf("retired holder's binding reached successor: %p %v", stale, refusal)
	}
	leave()
	deadline := time.Now().Add(10 * time.Second)
	for dirHeld(original.dir) {
		if time.Now().After(deadline) {
			t.Fatal("original resources were not released after the captured holder drained")
		}
		time.Sleep(10 * time.Millisecond)
	}
	require.Same(t, next, d.eng)
	require.Equal(t, next.account, d.account)
	require.Nil(t, d.sdk, "deferred old close must not overwrite the successor aliases")
	current, err := d.gate.enterEngineBinding(next.account, next.runID, true)
	require.NoError(t, err)
	require.NotNil(t, current)
	require.Same(t, next, current.engine)
	d.gate.leave(current)
}
