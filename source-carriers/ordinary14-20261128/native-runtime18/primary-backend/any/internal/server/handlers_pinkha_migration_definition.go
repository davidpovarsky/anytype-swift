package server

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any/internal/api"
	"github.com/labstack/echo/v4"
)

func registerPinkhaMigrationDefinitionRoutes(v1 *echo.Group, d *deps) {
	v1.GET("/spaces/:spaceId/pinkha/migration/definition/capabilities", d.pinkhaMigrationDefinitionCapabilities)
	v1.PUT("/spaces/:spaceId/pinkha/migration/intents/:intentId/definition/prepare", d.pinkhaMigrationDefinitionPrepare)
	v1.GET("/spaces/:spaceId/pinkha/migration/intents/:intentId/definition", d.pinkhaMigrationDefinitionStatus)
	v1.POST("/spaces/:spaceId/pinkha/migration/intents/:intentId/definition/commit", d.pinkhaMigrationDefinitionCommit)
}
func migrationDefinitionService(sp space.Space) (space.PreparedDefinitionService, error) {
	n, ok := sp.Objects().(space.PreparedDefinitionService)
	if !ok {
		return nil, space.ErrCurrentWriterUnavailable
	}
	return n, nil
}
func (d *deps) pinkhaMigrationDefinitionCapabilities(c echo.Context) error {
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	n, err := migrationDefinitionService(sp)
	if err != nil {
		return migrationError(c, err)
	}
	result, err := n.MigrationDefinitionCapabilities(c.Request().Context())
	if err != nil {
		return migrationError(c, err)
	}
	return c.JSON(http.StatusOK, result)
}
func migrationDefinitionInput(c echo.Context) (space.MigrationInput, space.MigrationDefinitionSpec, error) {
	var request api.MigrationPrepareRequest
	bad := func(reason string) (space.MigrationInput, space.MigrationDefinitionSpec, error) {
		return space.MigrationInput{}, space.MigrationDefinitionSpec{}, fmt.Errorf("%s", reason)
	}
	if err := readMigrationJSON(c, &request); err != nil {
		return bad(err.Error())
	}
	raw, err := base64.StdEncoding.Strict().DecodeString(request.SpecBase64)
	if err != nil || len(raw) == 0 || len(raw) > 256<<10 || base64.StdEncoding.EncodeToString(raw) != request.SpecBase64 {
		return bad("invalid definition specification encoding")
	}
	hash := sha256.Sum256(raw)
	if request.Contract != space.PreparedDefinitionContract || hex.EncodeToString(hash[:]) != request.SpecSHA256 {
		return bad("definition contract or digest differs")
	}
	var wire api.MigrationDefinitionSpec
	if err := strictMigrationJSON(raw, &wire); err != nil {
		return bad(err.Error())
	}
	// The exact-number and duplicate/unknown-field gates ran above. Normalize
	// map values to the same JSON scalar forms used by ordinary Any handlers.
	if err := json.Unmarshal(raw, &wire); err != nil {
		return bad(err.Error())
	}
	spec := space.MigrationDefinitionSpec{Kind: wire.Kind, OwnerObjectID: wire.OwnerObjectID}
	switch wire.Kind {
	case space.MigrationTypeDefinition:
		if wire.Type == nil || wire.Collection != nil || wire.Property != nil || wire.Part != nil || wire.OwnerObjectID != "" || wire.Type.XKey == "" {
			return bad("one type seed with xKey required")
		}
		p := wire.Type
		layout, code, reason := layoutFromWire(p.Layout)
		if code != "" {
			return bad(reason)
		}
		for k, v := range p.Meta {
			if code, reason := checkTypeMetaEntry(k, v, false); code != "" {
				return bad(reason)
			}
		}
		spec.Type = &space.TypeCreateParams{Name: p.Name, Description: p.Description, IconCID: p.IconCID, XKey: p.XKey, Layout: layout, Hidden: p.Hidden, Meta: p.Meta}
	case space.MigrationCollectionDefinition:
		if wire.Collection == nil || wire.Type != nil || wire.Property != nil || wire.Part != nil || wire.OwnerObjectID != "" || wire.Collection.XKey == "" {
			return bad("one collection seed with xKey required")
		}
		p := wire.Collection
		for k, v := range p.Meta {
			if code, reason := checkTypeMetaEntry(k, v, false); code != "" {
				return bad(reason)
			}
		}
		spec.Collection = &space.CollectionCreateParams{Name: p.Name, Description: p.Description, IconCID: p.IconCID, XKey: p.XKey, Hidden: p.Hidden, Meta: p.Meta}
	case space.MigrationPropertyDefinition:
		if wire.Property == nil || wire.Type != nil || wire.Collection != nil || wire.Part != nil || wire.OwnerObjectID == "" {
			return bad("one property seed with ownerObjectId required")
		}
		p, code, reason, _ := propertyDraftFromAPI(*wire.Property)
		if code != "" {
			return bad(reason)
		}
		spec.Property = &p
	case space.MigrationPartDefinition:
		if wire.Part == nil || wire.Type != nil || wire.Collection != nil || wire.Property != nil || wire.OwnerObjectID == "" {
			return bad("one atomic part seed with custom type owner required")
		}
		draft, code, reason, _ := partDraftFromAPI(*wire.Part)
		if code != "" {
			return bad(reason)
		}
		spec.Part = &draft
	default:
		return bad("unsupported prepared definition kind")
	}
	return space.MigrationInput{Contract: request.Contract, StoreID: request.StoreID, PlanID: request.PlanID, PlanSHA256: request.PlanSHA256, IntentID: c.Param("intentId"), SourceKey: request.SourceKey, SpecSHA256: request.SpecSHA256, SourceSpec: raw}, spec, nil
}
func (d *deps) pinkhaMigrationDefinitionPrepare(c echo.Context) error {
	input, spec, err := migrationDefinitionInput(c)
	if err != nil {
		return writeError(c, http.StatusBadRequest, "request.invalid_field", err.Error(), nil)
	}
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	n, err := migrationDefinitionService(sp)
	if err != nil {
		return migrationError(c, err)
	}
	// Repeat ordinary handle/owner preflights only for a new intent. A known
	// intent must reach the native ledger's complete binding comparison, even
	// after its own handle exists or the original row was modified/deleted.
	_, statusErr := n.MigrationDefinitionStatus(c.Request().Context(), input.IntentID)
	if errors.Is(statusErr, space.ErrMigrationNotFound) {
		switch spec.Kind {
		case space.MigrationTypeDefinition:
			if r, done := d.requireHandleFree(c, sp, spec.Type.XKey); done {
				return r
			}
		case space.MigrationCollectionDefinition:
			if r, done := d.requireHandleFree(c, sp, spec.Collection.XKey); done {
				return r
			}
		case space.MigrationPartDefinition:
			if r, done := requireType(c, sp, spec.OwnerObjectID); done {
				return r
			}
		case space.MigrationPropertyDefinition:
			// This generic route has no types/collections surface parameter.
			// Admit the closed native definition kind instead of defaulting to
			// the type-only ordinary-route helper. Unexpected lookup failures
			// remain failures; only an actual collection marker selects that API.
			if _, e := sp.Types().Get(c.Request().Context(), spec.OwnerObjectID); e != nil {
				if !errors.Is(e, space.ErrNotAType) {
					if r, done := typeLookupError(c, e, sp.Id(), spec.OwnerObjectID); done {
						return r
					}
					return migrationError(c, e)
				}
				if r, done := requireCollection(c, sp, spec.OwnerObjectID); done {
					return r
				}
			}
			if spec.Property.XKey != "" {
				defs, e := sp.Types().Properties(c.Request().Context(), spec.OwnerObjectID)
				if e != nil {
					return migrationError(c, e)
				}
				if r, done := requireXKeyFree(c, defs, spec.Property.XKey, ""); done {
					return r
				}
			}
		}
	} else if statusErr != nil {
		return migrationError(c, statusErr)
	}
	result, err := n.PrepareMigrationDefinition(c.Request().Context(), input, spec)
	if err != nil {
		return migrationError(c, err)
	}
	return c.JSON(http.StatusOK, result)
}
func (d *deps) pinkhaMigrationDefinitionStatus(c echo.Context) error {
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	n, err := migrationDefinitionService(sp)
	if err != nil {
		return migrationError(c, err)
	}
	result, err := n.MigrationDefinitionStatus(c.Request().Context(), c.Param("intentId"))
	if err != nil {
		return migrationError(c, err)
	}
	return c.JSON(http.StatusOK, result)
}
func (d *deps) pinkhaMigrationDefinitionCommit(c echo.Context) error {
	var request space.MigrationCommit
	if err := readMigrationJSON(c, &request); err != nil {
		return writeError(c, http.StatusBadRequest, "request.invalid_field", err.Error(), nil)
	}
	request.IntentID = c.Param("intentId")
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	n, err := migrationDefinitionService(sp)
	if err != nil {
		return migrationError(c, err)
	}
	result, err := n.CommitMigrationDefinition(c.Request().Context(), request)
	if err != nil {
		return migrationError(c, err)
	}
	return c.JSON(http.StatusOK, result)
}
