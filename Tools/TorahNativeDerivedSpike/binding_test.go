package torahderived

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
)

type memoryManifestSource struct {
	manifests  map[string][]ManifestCandidate
	properties map[string]PropertyDescriptor
}

func (s memoryManifestSource) Manifests(_ context.Context, space string) ([]ManifestCandidate, error) {
	return s.manifests[space], nil
}
func (s memoryManifestSource) CanonicalProperty(_ context.Context, space, key string) (PropertyDescriptor, error) {
	return s.properties[space+":"+key], nil
}

func TestManifestBindingExactKeysIsolationInvalidationAndNoCleanup(t *testing.T) {
	source := memoryManifestSource{manifests: map[string][]ManifestCandidate{}, properties: map[string]PropertyDescriptor{}}
	for _, space := range []string{"a", "b"} {
		raw, err := json.Marshal(map[string]any{"schemaVersion": 1, "spaceId": space, "manifestObjectId": "manifest-" + space, "provisioningState": "complete", "documentAssociationsPropertyId": "id-" + space, "documentAssociationsPropertyKey": "key-" + space, "registeredDocumentTypes": map[string]string{"chiddush": "c", "article": "a", "research": "r"}, "defaultTemplateIds": map[string]string{"chiddush": "tc", "article": "ta", "research": "tr"}, "parentPropertyId": "p", "parentPropertyKey": "pk", "orderPropertyId": "o", "orderPropertyKey": "ok", "folderTypeId": "f", "bookFolderTypeId": "bf"})
		if err != nil {
			t.Fatal(err)
		}
		source.manifests[space] = []ManifestCandidate{{ObjectID: "manifest-" + space, Raw: raw}}
		source.properties[space+":key-"+space] = PropertyDescriptor{ID: "id-" + space, Key: "key-" + space, Format: 0}
	}
	a, err := ResolveBinding(context.Background(), source, "a")
	if err != nil {
		t.Fatal(err)
	}
	b, err := ResolveBinding(context.Background(), source, "b")
	if err != nil {
		t.Fatal(err)
	}
	if a.CanonicalKey == b.CanonicalKey || a.Generation == b.Generation {
		t.Fatal("cross-Space binding reuse")
	}
	source.manifests["a"][0].Raw = append([]byte(" \n"), source.manifests["a"][0].Raw...)
	updated, err := ResolveBinding(context.Background(), source, "a")
	if err != nil {
		t.Fatal(err)
	}
	if updated.Generation == a.Generation {
		t.Fatal("manifest revision did not invalidate generation")
	}
	source.properties["a:key-a"] = PropertyDescriptor{ID: "id-a", Key: "key-a", Format: 11}
	if _, err := ResolveBinding(context.Background(), source, "a"); !errors.Is(err, ErrBinding) {
		t.Fatal("wrong native format accepted")
	}
	source.manifests["b"] = append(source.manifests["b"], source.manifests["b"][0])
	if _, err := ResolveBinding(context.Background(), source, "b"); !errors.Is(err, ErrBinding) {
		t.Fatal("ambiguous manifest accepted")
	}
	if len(source.manifests["b"]) != 2 {
		t.Fatal("discovery deleted user data")
	}
	if _, err := ResolveBinding(context.Background(), source, "other"); !errors.Is(err, ErrBinding) {
		t.Fatal("unknown Space accepted")
	}
}
