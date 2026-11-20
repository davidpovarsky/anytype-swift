package server

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"time"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any/internal/api"
	"github.com/labstack/echo/v4"
	"github.com/valyala/fastjson"
)

// This route is separate because stock propertiesSet ignores unknown fields.
// A native client must never send conditional guards to that stock route.
func (d *deps) pinkhaPropertiesSet(c echo.Context) error {
	return d.propertiesSetWithCondition(c, true)
}

func (d *deps) pinkhaPropertyPrecondition(c echo.Context, sp space.Space,
	objectID string, body *fastjson.Value) (uint64, error, bool) {
	if response, done := checkUnknownFields(c, body, "use patch, ifVersion, ifApplySeq and ifStartedAt",
		"patch", "ifVersion", "ifApplySeq", "ifStartedAt"); done {
		return 0, response, true
	}
	seen := map[string]bool{}
	duplicate := false
	body.GetObject().Visit(func(key []byte, _ *fastjson.Value) {
		name := string(key)
		if seen[name] {
			duplicate = true
		}
		seen[name] = true
	})
	if duplicate {
		return 0, writeError(c, http.StatusBadRequest, "pinkha.properties.precondition_required", "duplicate property precondition fields", nil), true
	}
	expected := body.Get("ifVersion")
	started := body.Get("ifStartedAt")
	capturedSequence := body.Get("ifApplySeq")
	nodes := 0
	if expected == nil || expected.Type() != fastjson.TypeObject ||
		!pinkhaValidVersion(expected, 0, &nodes) ||
		capturedSequence == nil || capturedSequence.Type() != fastjson.TypeNumber ||
		started == nil || started.Type() != fastjson.TypeString ||
		len(started.GetStringBytes()) == 0 || len(started.GetStringBytes()) > 128 {
		return 0, writeError(c, http.StatusBadRequest, "pinkha.properties.precondition_required",
			"full native ifVersion, positive integer ifApplySeq and ifStartedAt are required", nil), true
	}
	expectedSequence, parseErr := strconv.ParseUint(string(capturedSequence.MarshalTo(nil)), 10, 64)
	if parseErr != nil || expectedSequence == 0 {
		return 0, writeError(c, http.StatusBadRequest, "pinkha.properties.precondition_required",
			"ifApplySeq must be a positive integer from the original native read", nil), true
	}
	if string(started.GetStringBytes()) != d.startedAt.Format(time.RFC3339Nano) {
		return 0, writeError(c, http.StatusConflict, "pinkha.properties.engine_restarted",
			"re-read after the engine restarted", nil), true
	}
	record, err := sp.Properties().Get(c.Request().Context(), objectID)
	if err != nil {
		return 0, sdkOpError(c, err, map[string]any{"spaceId": sp.Id(), "objectId": objectID}), true
	}
	if record == nil {
		return 0, sdkOpError(c, space.ErrNotFound, nil), true
	}
	arena := getFastjsonArena()
	defer putFastjsonArena(arena)
	current := record.FastJson(arena)
	if !pinkhaVersionEqual(expected, current.Get("_ver")) {
		return 0, writeError(c, http.StatusConflict, "pinkha.properties.conflict",
			"properties changed", nil), true
	}
	seq := current.Get("_applySeq")
	if seq == nil || seq.Type() != fastjson.TypeNumber {
		return 0, writeError(c, http.StatusConflict, "pinkha.properties.version_unavailable",
			"native property sequence is unavailable", nil), true
	}
	value, err := strconv.ParseUint(string(seq.MarshalTo(nil)), 10, 64)
	if err != nil || value == 0 {
		return 0, writeError(c, http.StatusConflict, "pinkha.properties.version_unavailable",
			"native property sequence is unavailable", nil), true
	}
	if value != expectedSequence {
		return 0, writeError(c, http.StatusConflict, "pinkha.properties.conflict", "properties changed", nil), true
	}
	// Pass the caller capture unchanged. Never replace it with a fresh token
	// after an equal _ver map: late commutative operations may leave _ver equal.
	return expectedSequence, nil, false
}

// Native version metadata is a bounded map tree with string leaves, including
// nested style/property stamps and "*" ancestors. Numbers are never coerced.
func pinkhaValidVersion(value *fastjson.Value, depth int, nodes *int) bool {
	if value == nil || depth > 32 {
		return false
	}
	*nodes++
	if *nodes > 10000 {
		return false
	}
	if value.Type() == fastjson.TypeString {
		b := value.GetStringBytes()
		return len(b) > 0 && len(b) <= 1024
	}
	if value.Type() != fastjson.TypeObject {
		return false
	}
	object := value.GetObject()
	if object == nil || object.Len() == 0 || object.Len() > 1024 {
		return false
	}
	seen := make(map[string]bool, object.Len())
	valid := true
	object.Visit(func(key []byte, child *fastjson.Value) {
		name := string(key)
		if len(key) == 0 || len(key) > 1024 || seen[name] ||
			!pinkhaValidVersion(child, depth+1, nodes) {
			valid = false
		}
		seen[name] = true
	})
	return valid
}

func pinkhaVersionEqual(expected, current *fastjson.Value) bool {
	if expected == nil || current == nil || expected.Type() != current.Type() {
		return false
	}
	if expected.Type() == fastjson.TypeString {
		return string(expected.GetStringBytes()) == string(current.GetStringBytes())
	}
	if expected.Type() != fastjson.TypeObject {
		return false
	}
	a, b := expected.GetObject(), current.GetObject()
	if a == nil || b == nil || a.Len() != b.Len() {
		return false
	}
	same := true
	a.Visit(func(key []byte, child *fastjson.Value) {
		if !pinkhaVersionEqual(child, current.Get(string(key))) {
			same = false
		}
	})
	return same
}

func (d *deps) pinkhaPropertyResult(c echo.Context, sp space.Space, objectID string,
	result space.ModifyResult, err error) error {
	if errors.Is(err, space.ErrPreconditionFailed) {
		return writeError(c, http.StatusConflict, "pinkha.properties.conflict", "properties changed", nil)
	}
	if err != nil {
		return sdkOpError(c, err, map[string]any{"spaceId": sp.Id(), "objectId": objectID})
	}
	var next json.RawMessage
	if record, readErr := sp.Properties().Get(c.Request().Context(), objectID); readErr == nil && record != nil {
		arena := getFastjsonArena()
		current := record.FastJson(arena)
		sequence := current.Get("_applySeq")
		if sequence != nil {
			applied, parseErr := strconv.ParseUint(string(sequence.MarshalTo(nil)), 10, 64)
			if parseErr == nil && result.ApplySeq != 0 && applied == result.ApplySeq {
				if version := current.Get("_ver"); version != nil {
					next = append(next, version.MarshalTo(nil)...)
				}
			}
		}
		putFastjsonArena(arena)
	}
	return c.JSON(http.StatusOK, api.PinkhaPropertiesSetResponse{
		ModifyResult: modifyResultToAPI(result), PropertiesVersion: next,
		EngineStartedAt: d.startedAt.Format(time.RFC3339Nano),
	})
}
