// Package torahtransport remaps only known context identities at native import.
// Normal projection/getters remain read-only and never rewrite canonical data.
package torahtransport

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

type Object struct {
	ID          string
	OriginalID  string
	PropertyKey string
	Details     *domain.Details
}

type manifest struct {
	SchemaVersion     int               `json:"schemaVersion"`
	SpaceID           string            `json:"spaceId"`
	ManifestID        string            `json:"manifestObjectId"`
	ProvisioningState string            `json:"provisioningState"`
	CanonicalID       string            `json:"documentAssociationsPropertyId"`
	CanonicalKey      string            `json:"documentAssociationsPropertyKey"`
	Types             map[string]string `json:"registeredDocumentTypes"`
}

func mapped(ids map[string]string, id string) string {
	if next := ids[id]; next != "" {
		return next
	}
	return id
}
func mappedProperty(ids map[string]string, key string) string {
	next := ids["rel-"+key]
	if next == "" {
		return key
	}
	return strings.TrimPrefix(next, "rel-")
}

// RemapObjects runs once after the native importer has assigned all IDs and
// before it creates any object. Ordinary exports are untouched. The caller owns
// the original import transaction and the authoritative old-to-new identity map.
func RemapObjects(targetSpace string, objects []Object, ids map[string]string) error {
	byID := map[string]Object{}
	// The original PB converter first maps exported IDs to temporary import
	// IDs. The processor then allocates final IDs. Compose those two stages;
	// neither stage knows the opaque JSON's internal identity fields.
	aliases := make(map[string]string, len(ids)+len(objects))
	for old, next := range ids {
		aliases[old] = next
	}
	for _, object := range objects {
		byID[object.ID] = object
		if object.OriginalID != "" {
			byID[object.OriginalID] = object
			aliases[object.OriginalID] = mapped(ids, object.ID)
		}
	}
	ids = aliases
	type update struct {
		details *domain.Details
		key     domain.RelationKey
		value   string
	}
	var updates []update
	origins := map[string]bool{}
	for _, object := range objects {
		details := object.Details
		if details == nil || (details.GetString(bundle.RelationKeyName) != torah.ManifestUniqueKey && details.GetString(bundle.RelationKeyUniqueKey) != torah.ManifestUniqueKey) {
			continue
		}
		raw := []byte(details.GetString(bundle.RelationKeyDescription))
		var source manifest
		if json.Unmarshal(raw, &source) != nil || source.SchemaVersion != 1 || source.SpaceID == "" || source.CanonicalID == "" || source.CanonicalKey == "" {
			continue
		}
		originalID := object.OriginalID
		if originalID == "" {
			originalID = object.ID
		}
		if source.ManifestID != "" && source.ManifestID != originalID {
			continue
		}
		if source.ProvisioningState != "" && source.ProvisioningState != "complete" {
			continue
		}
		binding := torah.Binding{SpaceID: source.SpaceID, CanonicalKey: source.CanonicalKey, Generation: "native-import"}
		if binding.Validate() != nil {
			continue
		}
		property := byID[source.CanonicalID]
		propertyKey := property.PropertyKey
		if propertyKey == "" && property.Details != nil {
			propertyKey = property.Details.GetString(bundle.RelationKeyRelationKey)
		}
		if property.Details == nil || propertyKey != source.CanonicalKey || !property.Details.Has(bundle.RelationKeyRelationFormat) || property.Details.GetInt64(bundle.RelationKeyRelationFormat) != 0 {
			continue
		}
		if targetSpace == "" {
			return fmt.Errorf("missing destination Space for imported Torah manifest")
		}
		if origins[source.SpaceID] {
			return fmt.Errorf("ambiguous imported Torah manifest")
		}
		origins[source.SpaceID] = true
		root, err := fields(raw)
		if err != nil {
			return err
		}
		var changes []replacement
		for _, member := range root {
			var value string
			switch member.name {
			case "spaceId":
				value = targetSpace
			case "manifestObjectId":
				value = mapped(ids, object.ID)
			case "parentPropertyId", "orderPropertyId", "documentAssociationsPropertyId", "folderTypeId", "bookFolderTypeId":
				var old string
				if json.Unmarshal(member.raw, &old) == nil {
					value = mapped(ids, old)
				}
			case "parentPropertyKey", "orderPropertyKey", "documentAssociationsPropertyKey":
				var old string
				if json.Unmarshal(member.raw, &old) == nil {
					value = mappedProperty(ids, old)
				}
			case "registeredDocumentTypes", "defaultTemplateIds":
				entries, err := fields(member.raw)
				if err != nil {
					return err
				}
				for _, entry := range entries {
					var old string
					if json.Unmarshal(entry.raw, &old) == nil {
						changes = append(changes, replacement{member.start + entry.start, member.start + entry.end, mapped(ids, old)})
					}
				}
			}
			if value != "" {
				changes = append(changes, replacement{member.start, member.end, value})
			}
		}
		rewritten, err := replace(raw, changes)
		if err != nil {
			return err
		}
		updates = append(updates, update{details, bundle.RelationKeyDescription, string(rewritten)})
		for _, document := range objects {
			if document.Details == nil || !document.Details.Has(domain.RelationKey(source.CanonicalKey)) {
				continue
			}
			canonical := []byte(document.Details.GetString(domain.RelationKey(source.CanonicalKey)))
			sourceID := document.OriginalID
			if sourceID == "" {
				sourceID = document.ID
			}
			rewritten, err := remapCanonical(canonical, source.SpaceID, sourceID, targetSpace, mapped(ids, document.ID))
			if err != nil {
				return err
			}
			updates = append(updates, update{document.Details, domain.RelationKey(source.CanonicalKey), string(rewritten)})
		}
	}
	for _, change := range updates {
		change.details.SetString(change.key, change.value)
	}
	return nil
}
