package torahderived

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
)

// ManifestSource must scope both calls to the supplied Space. Implementations
// may only read: discovery must not invoke the app's duplicate cleanup/bootstrap.
type ManifestSource interface {
	Manifests(context.Context, string) ([]ManifestCandidate, error)
	CanonicalProperty(context.Context, string, string) (PropertyDescriptor, error)
}

type ManifestCandidate struct {
	ObjectID string
	Raw      []byte
}
type PropertyDescriptor struct {
	ID     string
	Key    string
	Format int
}

// ResolveBinding deliberately has no cache. Each manifest/property revision
// changes Generation, forcing callers to invalidate/rebuild the local index.
func ResolveBinding(ctx context.Context, source ManifestSource, space string) (Binding, error) {
	candidates, err := source.Manifests(ctx, space)
	if err != nil {
		return Binding{}, err
	}
	// Fail closed on ambiguity. Never delete competing synced manifest objects.
	if len(candidates) != 1 {
		return Binding{}, ErrBinding
	}
	candidate := candidates[0]
	var manifest struct {
		SchemaVersion     int               `json:"schemaVersion"`
		SpaceID           string            `json:"spaceId"`
		ManifestObjectID  string            `json:"manifestObjectId"`
		ProvisioningState *string           `json:"provisioningState"`
		CanonicalID       string            `json:"documentAssociationsPropertyId"`
		CanonicalKey      string            `json:"documentAssociationsPropertyKey"`
		Types             map[string]string `json:"registeredDocumentTypes"`
		Templates         map[string]string `json:"defaultTemplateIds"`
		ParentID          string            `json:"parentPropertyId"`
		ParentKey         string            `json:"parentPropertyKey"`
		OrderID           string            `json:"orderPropertyId"`
		OrderKey          string            `json:"orderPropertyKey"`
		FolderTypeID      string            `json:"folderTypeId"`
		BookFolderTypeID  string            `json:"bookFolderTypeId"`
	}
	if err := json.Unmarshal(candidate.Raw, &manifest); err != nil {
		return Binding{}, ErrBinding
	}
	if manifest.SchemaVersion != 1 {
		return Binding{}, ErrUnsupported
	}
	if candidate.ObjectID == "" || !exact(manifest.SpaceID, space) || (manifest.ManifestObjectID != "" && manifest.ManifestObjectID != candidate.ObjectID) || (manifest.ProvisioningState != nil && *manifest.ProvisioningState != "complete") {
		return Binding{}, ErrBinding
	}
	if manifest.CanonicalID == "" || manifest.CanonicalKey == "" || manifest.ParentID == "" || manifest.ParentKey == "" || manifest.OrderID == "" || manifest.OrderKey == "" || manifest.FolderTypeID == "" || manifest.BookFolderTypeID == "" {
		return Binding{}, ErrBinding
	}
	for _, role := range []string{"chiddush", "article", "research"} {
		if manifest.Templates[role] == "" {
			return Binding{}, ErrBinding
		}
	}
	property, err := source.CanonicalProperty(ctx, space, manifest.CanonicalKey)
	if err != nil {
		return Binding{}, err
	}
	// Heart's existing RelationFormat_longtext is 0. No new wire format here.
	if property.ID != manifest.CanonicalID || property.Key != manifest.CanonicalKey || property.Format != 0 {
		return Binding{}, ErrBinding
	}
	hash := sha256.New()
	hash.Write(candidate.Raw)
	fmt.Fprintf(hash, "|%d:%s|%d:%s|%d", len(candidate.ObjectID), candidate.ObjectID, len(property.ID), property.ID, property.Format)
	binding := Binding{SpaceID: space, CanonicalKey: manifest.CanonicalKey, Generation: hex.EncodeToString(hash.Sum(nil))}
	return binding, binding.Validate()
}
