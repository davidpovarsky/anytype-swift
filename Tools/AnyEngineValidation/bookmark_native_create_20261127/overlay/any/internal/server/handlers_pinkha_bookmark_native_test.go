package server

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any/internal/api"
	"github.com/anyproto/any/internal/config"
	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/require"
)

type bookmarkRouteFixture struct {
	e                                    http.Handler
	spaceID, typeID, ownerID, propertyID string
	layout                               map[string]any
}

func newBookmarkRouteFixture(t *testing.T) bookmarkRouteFixture {
	t.Helper()
	// Original handler fixtures skip when their public nodeconf is absent.
	// This new qualification must fail closed instead of accepting a skip.
	_, configErr := config.LoadNodeconf(config.Network{NodeconfPath: stagingPath})
	require.NoError(t, configErr, "the qualifier must bind the original public nodeconf before this native method")
	d, teardown := newTestDeps(t)
	t.Cleanup(teardown)
	e := buildEcho(d)
	sp := createSpaceInfo(t, e, "FreshConditionalBookmark")
	base := "/v1/spaces/" + sp.Id
	typeID := installModuleType(t, e, sp.Id, "editor")
	ownerID := mustCreateCollection(t, e, sp.Id, `{"name":"Fresh imported URL namespace","xKey":"fresh_bookmark_url"}`)
	property := doJSON(t, e, http.MethodPost, base+"/collections/"+ownerID+"/properties",
		`{"name":"Source","kind":"string","scope":"synced","xFormat":{"type":"url","pinkhaHeart":{"sourceObjectID":"original-source-definition","sourceUniqueKey":"rel-source","relationKey":"source"}}}`)
	require.Equal(t, http.StatusCreated, property.Code, property.Body.String())
	var added api.AddPropertyResponse
	require.NoError(t, json.Unmarshal(property.Body.Bytes(), &added))
	require.NotEmpty(t, added.PropId)
	address := map[string]any{"ownerId": ownerID, "propertyId": added.PropId}
	layout := map[string]any{"type": "bookmark", "config": map[string]any{"pinkhaHeart": map[string]any{
		"contract": "pinkha-heart-native-bookmark-presentation-v1", "sourceRecommendedLayout": 11,
		"propertyOwnerId": ownerID, "sourceURL": address, "recommended": []any{address},
		"featured": []any{}, "hidden": []any{}, "files": []any{}}}}
	raw, err := json.Marshal(map[string]any{"layout": layout})
	require.NoError(t, err)
	updated := doJSON(t, e, http.MethodPatch, base+"/types/"+typeID, string(raw))
	require.Equal(t, http.StatusNoContent, updated.Code, updated.Body.String())
	return bookmarkRouteFixture{e: e, spaceID: sp.Id, typeID: typeID, ownerID: ownerID, propertyID: added.PropId, layout: layout}
}

func (f bookmarkRouteFixture) frame(t *testing.T) space.BookmarkCreateFrame {
	t.Helper()
	body, err := json.Marshal(map[string]any{"typeId": f.typeID, "collections": []string{}})
	require.NoError(t, err)
	response := doJSON(t, f.e, http.MethodPost, "/v1/spaces/"+f.spaceID+"/pinkha/bookmark-create-frame", string(body))
	require.Equal(t, http.StatusOK, response.Code, response.Body.String())
	var proof space.BookmarkCreateFrame
	require.NoError(t, json.Unmarshal(response.Body.Bytes(), &proof))
	require.Equal(t, space.BookmarkCreateContract, proof.Contract)
	require.Equal(t, f.spaceID, proof.SpaceID)
	require.Equal(t, f.typeID, proof.TypeID)
	require.Equal(t, []string{f.ownerID}, proof.Collections)
	require.Equal(t, f.ownerID, proof.PropertyOwnerID)
	require.Equal(t, f.propertyID, proof.PropertyID)
	require.NotEmpty(t, proof.AccountID)
	require.True(t, proof.CanWrite)
	require.NotEmpty(t, proof.Frame)
	return proof
}

func (f bookmarkRouteFixture) body(t *testing.T, frame string) string {
	t.Helper()
	raw, err := json.Marshal(map[string]any{"type": f.typeID, "collections": []string{f.ownerID},
		"initialProperties":       map[string]any{"any": map[string]any{"name": "Bodyless Bookmark"}, f.ownerID: map[string]any{f.propertyID: "https://example.test/cafe\u0301"}},
		"bookmarkDefinitionFrame": frame})
	require.NoError(t, err)
	return string(raw)
}

func TestPinkhaBookmarkReadAndBodylessConditionalCreate(t *testing.T) {
	f := newBookmarkRouteFixture(t)
	base := "/v1/spaces/" + f.spaceID
	proof := f.frame(t)
	stock := doJSON(t, f.e, http.MethodPost, base+"/objects", f.body(t, proof.Frame))
	require.Equal(t, http.StatusBadRequest, stock.Code, "stock route still refuses the optional Pinkha-only field")
	created := doJSON(t, f.e, http.MethodPost, base+"/pinkha/objects", f.body(t, proof.Frame))
	require.Equal(t, http.StatusCreated, created.Code, created.Body.String())
	var object api.ObjectsCreateResponse
	require.NoError(t, json.Unmarshal(created.Body.Bytes(), &object))
	require.NotEmpty(t, object.ObjectId)
	_, properties := pinkhaPropertiesSnapshot(t, f.e, f.spaceID, object.ObjectId)
	require.Equal(t, []byte("https://example.test/cafe\u0301"), []byte(properties[f.ownerID].(map[string]any)[f.propertyID].(string)))
	require.Empty(t, blocksList(t, f.e, base+"/objects/"+object.ObjectId).Records)
	target := doJSON(t, f.e, http.MethodGet, base+"/pinkha/document-targets/"+object.ObjectId, "")
	require.Equal(t, http.StatusOK, target.Code, target.Body.String())
	require.Contains(t, target.Body.String(), `"eligible":true`)
	var first, second struct {
		Content string `json:"content"`
		Version string `json:"version"`
	}
	path := base + "/objects/" + object.ObjectId + "/editor/editor_blocks/markdown"
	decodeGet(t, f.e, path, &first)
	decodeGet(t, f.e, path, &second)
	require.Empty(t, first.Content)
	require.NotEmpty(t, first.Version)
	require.Equal(t, first, second)
	// The frame conditions definitions, not an object-create idempotency key.
	// This test performs exactly one successful conditional creation.
}

func TestPinkhaBookmarkFrameRefusesForeignIdentityAndDefinitionDrift(t *testing.T) {
	f := newBookmarkRouteFixture(t)
	base := "/v1/spaces/" + f.spaceID
	proof := f.frame(t)
	raw, err := base64.RawURLEncoding.DecodeString(proof.Frame)
	require.NoError(t, err)
	for _, pair := range [][2]string{{`"accountId":"` + proof.AccountID + `"`, `"accountId":"another-account"`}, {`"spaceId":"` + proof.SpaceID + `"`, `"spaceId":"another-space"`}} {
		changed := strings.Replace(string(raw), pair[0], pair[1], 1)
		require.NotEqual(t, string(raw), changed)
		refused := doJSON(t, f.e, http.MethodPost, base+"/pinkha/objects", f.body(t, base64.RawURLEncoding.EncodeToString([]byte(changed))))
		require.Equal(t, http.StatusConflict, refused.Code, refused.Body.String())
		require.Contains(t, refused.Body.String(), "pinkha.bookmark_definition_changed")
		require.NotContains(t, refused.Body.String(), `"objectId"`)
	}
	// A harmless-looking metadata mutation still advances the complete selected
	// definition state. Generic object eligibility alone must not accept it.
	changed := doJSON(t, f.e, http.MethodPatch, base+"/types/"+f.typeID, `{"description":"new current descriptor"}`)
	require.Equal(t, http.StatusNoContent, changed.Code, changed.Body.String())
	refused := doJSON(t, f.e, http.MethodPost, base+"/pinkha/objects", f.body(t, proof.Frame))
	require.Equal(t, http.StatusConflict, refused.Code, refused.Body.String())
	require.Contains(t, refused.Body.String(), "pinkha.bookmark_definition_changed")
	proof = f.frame(t)
	changed = doJSON(t, f.e, http.MethodPatch, base+"/collections/"+f.ownerID+"/properties/"+f.propertyID, `{"set":{"xFormat.type":"text"}}`)
	require.Equal(t, http.StatusNoContent, changed.Code, changed.Body.String())
	refused = doJSON(t, f.e, http.MethodPost, base+"/pinkha/objects", f.body(t, proof.Frame))
	require.Equal(t, http.StatusConflict, refused.Code, refused.Body.String())
	require.Contains(t, refused.Body.String(), "pinkha.bookmark_definition_ineligible")
	require.NotContains(t, refused.Body.String(), `"objectId"`)
}

func TestPinkhaBookmarkKnownRootConditionErrorRetainsOriginalIdentity(t *testing.T) {
	e := echo.New()
	recorder := httptest.NewRecorder()
	context := e.NewContext(httptest.NewRequest(http.MethodPost, "/", nil), recorder)
	err := pinkhaObjectCreateError(context, space.ErrBookmarkCreateChanged, "original-space",
		space.CurrentWriterCreateResult{ObjectID: "original-root", CreationStage: "root-stored", Cleanup: "not-attempted", Outcome: "uncertain"})
	require.NoError(t, err)
	require.Equal(t, http.StatusServiceUnavailable, recorder.Code)
	require.Contains(t, recorder.Body.String(), "pinkha.object_create_uncertain")
	require.Contains(t, recorder.Body.String(), `"objectId":"original-root"`)
	require.Contains(t, recorder.Body.String(), `"spaceId":"original-space"`)
	require.Contains(t, recorder.Body.String(), `"creationStage":"root-stored"`)
	require.Contains(t, recorder.Body.String(), `"cleanup":"not-attempted"`)
	require.NotContains(t, recorder.Body.String(), "pinkha.bookmark_definition_changed")
}
