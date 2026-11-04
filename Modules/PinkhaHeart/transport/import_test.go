package torahtransport

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

func TestNativeImportPreservesAllOtherCanonicalBytes(t *testing.T) {
	raw := `{ "version":2, "unknown": {"objectId":"old-doc","spaceId":"old-space"}, "records": [ { "spaceId" : "old-space", "objectId":"old-doc", "blockId":"block-7", "item":{"id":"item-1","providerID":"sefaria","canonicalKey":"Genesis 1:1","kind":"ref","role":"context"}, "future":{"raw":"\\u05d0"} }, {"spaceId":"foreign","objectId":"old-doc","item":{"id":"foreign-item"}} ] }`
	got, err := remapCanonical([]byte(raw), "old-space", "old-doc", "new-space", "new-doc")
	if err != nil {
		t.Fatal(err)
	}
	// The expected bytes are deliberately literal: nested unknown fields and
	// foreign records containing the same identifiers must not be rewritten.
	want := `{ "version":2, "unknown": {"objectId":"old-doc","spaceId":"old-space"}, "records": [ { "spaceId" : "new-space", "objectId":"new-doc", "blockId":"block-7", "item":{"id":"item-1","providerID":"sefaria","canonicalKey":"Genesis 1:1","kind":"ref","role":"context"}, "future":{"raw":"\\u05d0"} }, {"spaceId":"foreign","objectId":"old-doc","item":{"id":"foreign-item"}} ] }`
	if string(got) != want {
		t.Fatalf("unrelated canonical bytes changed: %s", got)
	}
	for _, raw := range []string{`{"version":9,"records":[]}`, `{"version":1,"items":[]}`, `{"version":2`, `{"version":2,"records":[],"records":[]}`} {
		got, err := remapCanonical([]byte(raw), "s", "d", "next-s", "next-d")
		if err != nil || string(got) != raw {
			t.Fatalf("malformed/legacy/future payload rewritten: %s %v", got, err)
		}
	}
}

func importFixture() ([]Object, map[string]string) {
	manifest := `{ "schemaVersion":1, "spaceId":"old-space", "manifestObjectId":"manifest", "provisioningState":"complete", "documentAssociationsPropertyId":"property", "documentAssociationsPropertyKey":"canonical", "registeredDocumentTypes":{"chiddush":"type-a","article":"type-b","research":"type-c"}, "defaultTemplateIds":{"chiddush":"template-a"}, "unknown":{"spaceId":"old-space"} }`
	return []Object{
		{ID: "manifest", Details: domain.NewDetails().SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).SetString(bundle.RelationKeyDescription, manifest)},
		{ID: "property", Details: domain.NewDetails().SetString(bundle.RelationKeyRelationKey, "canonical").SetInt64(bundle.RelationKeyRelationFormat, 0)},
		{ID: "document", Details: domain.NewDetails().SetString("canonical", `{"version":2,"records":[{"spaceId":"old-space","objectId":"document","item":{"id":"stable"}}]}`)},
	}, map[string]string{"manifest": "new-manifest", "property": "new-property", "document": "new-document", "rel-canonical": "rel-new-canonical", "type-a": "new-a", "type-b": "new-b", "type-c": "new-c", "template-a": "new-template-a"}
}

func TestNativeImportUsesAllocatedSchemaAndContextIdentities(t *testing.T) {
	objects, ids := importFixture()
	if err := RemapObjects("new-space", objects, ids); err != nil {
		t.Fatal(err)
	}
	var got map[string]json.RawMessage
	if err := json.Unmarshal([]byte(objects[0].Details.GetString(bundle.RelationKeyDescription)), &got); err != nil {
		t.Fatal(err)
	}
	for key, want := range map[string]string{"spaceId": `"new-space"`, "manifestObjectId": `"new-manifest"`, "documentAssociationsPropertyId": `"new-property"`, "documentAssociationsPropertyKey": `"new-canonical"`, "unknown": `{"spaceId":"old-space"}`, "registeredDocumentTypes": `{"chiddush":"new-a","article":"new-b","research":"new-c"}`} {
		if string(got[key]) != want {
			t.Fatalf("%s = %s, want %s", key, got[key], want)
		}
	}
	if raw := objects[2].Details.GetString("canonical"); raw != `{"version":2,"records":[{"spaceId":"new-space","objectId":"new-document","item":{"id":"stable"}}]}` {
		t.Fatal(raw)
	}
	if objects[2].Details.Has("new-canonical") {
		t.Fatal("transport must leave relation-key remapping to the original importer")
	}
}

func TestNativeImportComposesConverterAndProcessorIDs(t *testing.T) {
	objects, oldIDs := importFixture()
	ids := map[string]string{"rel-canonical": "rel-new-canonical", "type-a": "new-a", "type-b": "new-b", "type-c": "new-c", "template-a": "new-template-a"}
	for index := range objects {
		old := objects[index].ID
		objects[index].OriginalID = old
		objects[index].ID = "temporary-" + old
		ids[objects[index].ID] = oldIDs[old]
	}
	// PB conversion strips derived relationKey Details but preserves Data.Key.
	objects[1].PropertyKey = "canonical"
	objects[1].Details.Delete(bundle.RelationKeyRelationKey)
	if err := RemapObjects("new-space", objects, ids); err != nil {
		t.Fatal(err)
	}
	if raw := objects[2].Details.GetString("canonical"); !strings.Contains(raw, `"objectId":"new-document"`) {
		t.Fatal(raw)
	}
	raw := objects[0].Details.GetString(bundle.RelationKeyDescription)
	if !strings.Contains(raw, `"manifestObjectId":"new-manifest"`) || !strings.Contains(raw, `"documentAssociationsPropertyId":"new-property"`) {
		t.Fatal(raw)
	}
}

func TestNativeImportFailsClosedWithoutPartialMutation(t *testing.T) {
	objects, ids := importFixture()
	before := objects[0].Details.GetString(bundle.RelationKeyDescription)
	duplicate := Object{ID: "manifest-2", Details: objects[0].Details.Copy()}
	duplicate.Details.SetString(bundle.RelationKeyDescription, strings.ReplaceAll(before, `"manifest"`, `"manifest-2"`))
	objects = append(objects, duplicate)
	if err := RemapObjects("new-space", objects, ids); err == nil {
		t.Fatal("ambiguous same-Space manifests were accepted")
	}
	if objects[0].Details.GetString(bundle.RelationKeyDescription) != before {
		t.Fatal("failed import partially mutated the manifest")
	}
	objects, ids = importFixture()
	objects[1].Details.SetInt64(bundle.RelationKeyRelationFormat, 11)
	before = objects[0].Details.GetString(bundle.RelationKeyDescription)
	if err := RemapObjects("new-space", objects, ids); err != nil {
		t.Fatal(err)
	}
	if objects[0].Details.GetString(bundle.RelationKeyDescription) != before {
		t.Fatal("unverified canonical property was adopted")
	}
}

func TestOrdinaryImportRetainsOriginalValidationContract(t *testing.T) {
	for _, objects := range [][]Object{nil, {{ID: "ordinary-web-object", Details: domain.NewDetails().SetString(bundle.RelationKeyName, "Ordinary web import")}}} {
		if err := RemapObjects("", objects, nil); err != nil {
			t.Fatalf("Torah adapter changed an ordinary import contract: %v", err)
		}
	}
	objects, ids := importFixture()
	before := objects[0].Details.GetString(bundle.RelationKeyDescription)
	if err := RemapObjects("", objects, ids); err == nil {
		t.Fatal("verified Torah import has no destination Space")
	}
	if objects[0].Details.GetString(bundle.RelationKeyDescription) != before {
		t.Fatal("invalid Torah destination partially mutated data")
	}
}
