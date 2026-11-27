package server

import (
	"errors"
	"net/http"
	"strconv"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/labstack/echo/v4"

	"github.com/anyproto/any/internal/pinkha/claims"
)

// A native contract is advertised separately from the stock records module.
// Clients must explicitly migrate to this versioned bundle; a stock server's
// generic schema never implies these native write and replay checks.
func registerPinkhaRoutes(v1 *echo.Group, d *deps) {
	registerPinkhaMigrationRoutes(v1, d)
	v1.GET("/pinkha/capabilities", d.pinkhaCapabilities)
	v1.POST("/spaces/:spaceId/pinkha/install", d.pinkhaInstall)
	v1.POST("/spaces/:spaceId/pinkha/bookmark-create-frame", d.pinkhaBookmarkCreateFrame)
	v1.POST("/spaces/:spaceId/pinkha/objects", d.pinkhaObjectCreate)
	v1.POST("/spaces/:spaceId/pinkha/objects/:objectId/editor/:collection/blocks", d.pinkhaBlocksCreate)
	v1.GET("/spaces/:spaceId/pinkha/targets/:objectId", d.pinkhaTarget)
	v1.GET("/spaces/:spaceId/pinkha/document-types/:typeId", d.pinkhaDocumentType)
	v1.GET("/spaces/:spaceId/pinkha/document-targets/:objectId", d.pinkhaDocumentTarget)
	v1.GET("/spaces/:spaceId/pinkha/sources", d.pinkhaSource)
	v1.GET("/spaces/:spaceId/pinkha/related", d.pinkhaRelated)
	v1.GET("/spaces/:spaceId/pinkha/operations/:operationId", d.pinkhaAuthorizedOperation)
	v1.GET("/spaces/:spaceId/pinkha/claims", d.pinkhaClaimsSnapshot)
	v1.GET("/spaces/:spaceId/pinkha/claims/subscribe", d.pinkhaClaimsWatch)
	v1.GET("/spaces/:spaceId/pinkha/objects/:objectId/claims", d.pinkhaObjectClaimsSnapshot)
	v1.GET("/spaces/:spaceId/pinkha/objects/:objectId/claims/subscribe", d.pinkhaObjectClaimsWatch)
	v1.POST("/spaces/:spaceId/pinkha/properties/:objectId/set/:typeId", d.pinkhaPropertiesSet)
}

func (d *deps) pinkhaCapabilities(c echo.Context) error {
	return c.JSON(http.StatusOK, map[string]any{
		"contract":                           claims.ContractID,
		"bundleId":                           claims.BundleID,
		"module":                             claims.ModuleName,
		"dataset":                            claims.Dataset,
		"dataVersion":                        claims.DataVersion,
		"allowedTargetTypes":                 []string{"page"},
		"associationBlockDataset":            "editor_blocks",
		"nativeSignedClaims":                 1,
		"spaceWideOperationConflictDomain":   1,
		"nativeOrderedOperationCollision":    1,
		"currentACLCommitFence":              1,
		"targetTreeCommitFence":              1,
		"nativeDocumentProperties":           1,
		"nativeIndexedSourceQuery":           1,
		"nativeRelatedVersion":               1,
		"nativeClaimsSnapshot":               1,
		"nativeClaimsWatch":                  1,
		"nativeObjectClaimsSnapshot":         1,
		"nativeObjectClaimsWatch":            1,
		"nativeClaimsMaxRecords":             claims.MaxSnapshotRecords,
		"nativeClaimsMaxBytes":               claims.MaxSnapshotBytes,
		"conditionalBlockPatch":              1,
		"conditionalBlockCurrentWriterFence": 1,
		"currentWriterObjectCreate":          1,
		"nativeBookmarkObjectCreate":         1,
		"currentWriterBlockCreate":           1,
		"mobileManagedTokenGateway":          d.pinkhaMobileManagedGatewayVersion(),
		"conditionalPropertiesSet":           1,
		"conditionalPropertiesNoop":          1,
		"conditionalPropertiesApplySeq":      1,
		"conditionalMembershipSet":           1,
		"nativeDocumentTypePolicy":           1,
		"nativeDocumentMembership":           1,
		"documentTypePolicy":                 claims.DocumentPolicy,
		"nativePropertyPresentation":         1,
		"propertyPresentationCollection":     claims.PropertyPresentationCollection,
		"propertyPresentationHiddenProperty": claims.PropertyPresentationHiddenProperty,
		"propertyPresentationMaxKeys":        claims.PropertyPresentationMaxKeys,
		"propertyPresentationMaxKeyBytes":    claims.PropertyPresentationMaxKeyBytes,
		"nativeSemanticPayload":              "canonical-associations-v2-single-record",
		// Qualification candidate only; default v9 does not advertise this contract.
		"nativeAuthorizedOperationRead":      1,
		"authorizedOperationReadContract":    claims.AuthorizedOperationReadContract,
		"authorizedOperationReadMaxVariants": claims.MaxVariants,
		"authorizedOperationReadMaxBytes":    claims.MaxAuthorizedOperationReadBytes,
	})
}

func (d *deps) pinkhaInstall(c echo.Context) error {
	// No caller-provided module, root, identity or authority policy. The route
	// installs exactly the compiled contract on its canonical derived root.
	if hasBody(c.Request()) {
		return writeError(c, http.StatusBadRequest, "request.invalid_field", "native install takes no request body", nil)
	}
	sp, errResp, done := d.resolveSpace(c)
	if done {
		return errResp
	}
	b, _, err := sp.Bundles().Ensure(c.Request().Context(), space.EnsureBundleRequest{
		Id: claims.BundleID, Name: "Pinkha native Torah operations", DerivedRoot: true, Hidden: true,
		XKey: claims.ContractID,
		Parts: []space.PartDraft{{Key: "claims", Name: "Torah operations", Hidden: true,
			Datasets: []space.DatasetDraft{{Key: claims.Dataset, Module: claims.ModuleName}}}},
	}, space.SystemInstall())
	if err != nil {
		return bundleError(c, err, sp.Id(), claims.BundleID)
	}
	if !b.Derived {
		return writeError(c, http.StatusConflict, "pinkha.invalid_install", "native contract requires its canonical derived root", nil)
	}
	return c.JSON(http.StatusOK, map[string]any{
		"contract": claims.ContractID, "bundleId": claims.BundleID,
		"rootObjectId": b.RootId, "dataset": claims.Dataset, "module": claims.ModuleName,
	})
}

func pinkhaRoot(c echo.Context, sp space.Space) (string, error) {
	b, err := sp.Bundles().Get(c.Request().Context(), claims.BundleID)
	if err != nil {
		return "", err
	}
	expected, err := sp.Bundles().DerivedRootId(c.Request().Context(), claims.BundleID)
	if err != nil {
		return "", err
	}
	if !b.Derived || b.RootId != expected {
		return "", claims.ErrInvalid
	}
	return b.RootId, nil
}

func pinkhaLimit(c echo.Context, fallback, max int) (int, error) {
	value := c.QueryParam("limit")
	if value == "" {
		return fallback, nil
	}
	n, err := strconv.Atoi(value)
	if err != nil || n < 1 || n > max {
		return 0, claims.ErrInvalid
	}
	return n, nil
}

func pinkhaReadError(c echo.Context, err error, spaceID string) error {
	if errors.Is(err, space.ErrPreconditionFailed) {
		return writeError(c, http.StatusConflict, "pinkha.snapshot_changed", "native definition dependencies changed; repeat the read", nil)
	}
	if errors.Is(err, claims.ErrReadLimit) {
		return writeError(c, http.StatusConflict, "pinkha.read_limit", "native indexed result exceeds the explicit bound", nil)
	}
	if errors.Is(err, claims.ErrSnapshotChanged) {
		return writeError(c, http.StatusConflict, "pinkha.snapshot_changed", "native related dependencies changed; repeat the read", nil)
	}
	if errors.Is(err, claims.ErrInvalid) {
		return writeError(c, http.StatusBadRequest, "pinkha.invalid_request", "invalid native contract request", nil)
	}
	return bundleError(c, err, spaceID, claims.BundleID)
}

func (d *deps) pinkhaTarget(c echo.Context) error {
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	limit, err := pinkhaLimit(c, 10000, 10000)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	root, err := pinkhaRoot(c, sp)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	result, err := claims.ReadTarget(c.Request().Context(), sp, root, claims.Target{ObjectID: c.Param("objectId"), BlockID: c.QueryParam("blockId")}, limit)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	return c.JSON(http.StatusOK, result)
}

func (d *deps) pinkhaSource(c echo.Context) error {
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	limit, err := pinkhaLimit(c, 1000, 1000)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	root, err := pinkhaRoot(c, sp)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	result, err := claims.FindSource(c.Request().Context(), sp, root, c.QueryParam("field"), c.QueryParam("identity"), limit)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	return c.JSON(http.StatusOK, result)
}

func (d *deps) pinkhaRelated(c echo.Context) error {
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	limit, err := pinkhaLimit(c, 1000, 1000)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	root, err := pinkhaRoot(c, sp)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	result, err := claims.FindRelated(c.Request().Context(), sp, root, c.QueryParam("identity"), limit)
	if err != nil {
		return pinkhaReadError(c, err, sp.Id())
	}
	return c.JSON(http.StatusOK, result)
}
