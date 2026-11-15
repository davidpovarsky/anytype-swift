package torahderived

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"testing"
)

type relatedBindingSource struct{ candidates []ManifestCandidate }

func (s relatedBindingSource) Manifests(context.Context, string) ([]ManifestCandidate, error) {
	return s.candidates, nil
}
func (s relatedBindingSource) CanonicalProperty(context.Context, string, string) (PropertyDescriptor, error) {
	return PropertyDescriptor{ID: "p", Key: "canonical", Format: 0}, nil
}

func TestRelatedBindingCarriesSelectedIdentityWithoutChangingPublicGeneration(t *testing.T) {
	raw, _ := json.Marshal(map[string]any{
		"schemaVersion": 1, "spaceId": "S", "manifestObjectId": "selected", "provisioningState": "complete",
		"documentAssociationsPropertyId": "p", "documentAssociationsPropertyKey": "canonical",
		"registeredDocumentTypes": map[string]string{"chiddush": "h", "article": "a", "research": "r"},
		"defaultTemplateIds":      map[string]string{"chiddush": "th", "article": "ta", "research": "tr"},
		"parentPropertyId":        "parent", "parentPropertyKey": "parentKey", "orderPropertyId": "o", "orderPropertyKey": "ok", "folderTypeId": "f", "bookFolderTypeId": "b",
	})
	source := relatedBindingSource{[]ManifestCandidate{{ObjectID: "selected", Raw: raw}}}
	b, err := ResolveBinding(context.Background(), source, "S")
	if err != nil || b.ManifestObjectID != "selected" || b.CanonicalKey != "canonical" {
		t.Fatalf("selected binding lost: %#v %v", b, err)
	}
	h := sha256.New()
	h.Write(raw)
	fmt.Fprintf(h, "|%d:%s|%d:%s|%d", len("selected"), "selected", len("p"), "p", 0)
	if b.Generation != hex.EncodeToString(h.Sum(nil)) {
		t.Fatal("legacy public generation changed")
	}
	if err := (Binding{SpaceID: "S", CanonicalKey: "canonical", Generation: "legacy"}).Validate(); err != nil {
		t.Fatal("old public Binding validation now requires private capability")
	}
	for _, candidates := range [][]ManifestCandidate{
		{{ObjectID: "other", Raw: raw}},
		{{ObjectID: "selected", Raw: raw}, {ObjectID: "selected", Raw: raw}},
	} {
		b, err = ResolveBinding(context.Background(), relatedBindingSource{candidates}, "S")
		if err == nil || b.ManifestObjectID != "" {
			t.Fatal("unvalidated/nonselected binding advertised manifest identity")
		}
	}
	b, err = ResolveBinding(context.Background(), source, "foreign")
	if err == nil || b.ManifestObjectID != "" {
		t.Fatal("foreign manifest identity accepted")
	}
}
