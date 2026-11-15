package torahderived

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"reflect"
	"strings"
	"testing"
)

func relatedInput(raw string) (Binding, Input) {
	b := Binding{SpaceID: "S", CanonicalKey: "canonical", Generation: "g"}
	return b, Input{SpaceID: "S", ObjectID: "A", TypeID: "page", IsDocument: true, Raw: []byte(raw)}
}

func relatedRecord(id, block, role, provider, canonical string) map[string]any {
	r := map[string]any{"spaceId": "S", "objectId": "A", "item": map[string]any{
		"id": id, "kind": "ref", "role": role, "providerID": provider,
		"canonicalKey": canonical, "externalID": canonical, "labelHe": "source",
	}}
	if block != "" {
		r["blockId"] = block
	}
	return r
}

func relatedProject(t *testing.T, records ...map[string]any) Projection {
	t.Helper()
	raw, err := json.Marshal(map[string]any{"version": 2, "records": records})
	if err != nil {
		t.Fatal(err)
	}
	before := bytes.Clone(raw)
	b, in := relatedInput(string(raw))
	p, err := Project(b, in)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(raw, before) {
		t.Fatal("canonical bytes changed")
	}
	return p
}

func TestRelatedUnionIndependentOfPublicLocationRoleAndIDDedup(t *testing.T) {
	p := relatedProject(t,
		relatedRecord("same-id", "K", "context", "sefaria", "Genesis 3:3"),
		relatedRecord("same-id", "Q", "sourceQuote", "sefaria", "Genesis 3:4"),
		relatedRecord("legacy", "Q", "source_quote", "sefaria", "Genesis 3:4"),
		relatedRecord("doc-quote", "", "sourceQuote", "sefaria", "Genesis 3:5"),
		relatedRecord("doc-context", "", "context", "sefaria", "Genesis 3:6"))
	want := []string{}
	for _, ref := range []string{"Genesis 3:3", "Genesis 3:4", "Genesis 3:5", "Genesis 3:6"} {
		want = append(want, Identity(Ref, "sefaria", ref, ""))
	}
	if p.RelatedError != nil || !reflect.DeepEqual(p.RelatedSources, want) {
		t.Fatalf("private union: %#v", p)
	}
	if !reflect.DeepEqual(p.Sources, want[3:]) || len(p.Labels) != 1 {
		t.Fatalf("public semantics widened: %#v", p)
	}
}

func TestRelatedExactIdentityAndForeignInternalExclusion(t *testing.T) {
	foreign := relatedRecord("foreign", "K", "context", "sefaria", "foreign")
	foreign["spaceId"] = "S2"
	otherObject := relatedRecord("object", "K", "context", "sefaria", "other-object")
	otherObject["objectId"] = "B"
	fallback := relatedRecord("fallback", "K", "context", "sefaria", "")
	fallback["item"].(map[string]any)["externalID"] = "Genesis 3:3"
	internal := relatedRecord("internal", "K", "context", "sefaria", "")
	internal["item"].(map[string]any)["externalID"] = "anytype-note:note-id"
	topic := relatedRecord("topic", "K", "context", "sefaria", "topic")
	topic["item"].(map[string]any)["kind"] = "topic"
	p := relatedProject(t, foreign, otherObject, fallback, internal, topic,
		relatedRecord("alias-a", "K", "context", "e\u0301", "Genesis 3:3"),
		relatedRecord("alias-b", "K", "sourceQuote", "é", "Genesis 3:3"))
	if len(p.RelatedSources) != 2 {
		t.Fatalf("foreign/internal/kind/alias mismatch: %v", p.RelatedSources)
	}
	for _, id := range p.RelatedSources {
		if strings.Contains(id, "anytype-note:") || strings.Contains(id, "foreign") {
			t.Fatal(id)
		}
	}
}

func TestRelatedInvalidTargetWithholdsOnlyPrivateProjection(t *testing.T) {
	invalid := relatedRecord("invalid", "K", "sourceQuote", "sefaria", "Genesis 3:3")
	invalid["blockId"] = ""
	p := relatedProject(t, relatedRecord("valid", "", "context", "sefaria", "Genesis 3:3"), invalid)
	if !errors.Is(p.RelatedError, ErrMalformed) || p.RelatedSources != nil {
		t.Fatalf("private target did not fail closed: %#v", p)
	}
	if len(p.Sources) != 1 || len(p.Labels) != 1 {
		t.Fatalf("valid public projection was disabled: %#v", p)
	}
}

func TestRelatedMalformedFutureAndEmptyPayload(t *testing.T) {
	for _, raw := range []string{`{"version":999}`, `{"version":2,"records":[{}]}`, `{"version":2,"records":null}`, `invalid`} {
		b, in := relatedInput(raw)
		p, err := Project(b, in)
		if err == nil || !reflect.DeepEqual(p, Projection{}) {
			t.Fatalf("valid-looking malformed private projection: %q %#v %v", raw, p, err)
		}
	}
	b, in := relatedInput("")
	p, err := Project(b, in)
	if err != nil || p.RelatedError != nil || len(p.RelatedSources) != 0 {
		t.Fatalf("eligible empty: %#v %v", p, err)
	}
}

func TestRelatedKeysRemainPrivateAndPublicVersionUnchanged(t *testing.T) {
	if Version != 1 || RelatedVersion != 1 || len(Definitions) != 3 {
		t.Fatal("public schema/version changed")
	}
	for _, key := range []string{RelatedSourcesKey, RelatedVersionKey} {
		if IsProperty(key) || !IsLocalKey(key) || !IsPrivateKey(key) {
			t.Fatalf("private key leaked into Properties: %s", key)
		}
	}
	if IsPrivateKey(SourcesKey) || IsPrivateKey("ordinaryUserProperty") {
		t.Fatal("private guard changed public/user Property classification")
	}
}

func TestRelatedPreservesExistingSwiftPublicGoldenFixtures(t *testing.T) {
	data, err := os.ReadFile("../../PinkhaKit/Tests/PinkhaKitTests/Torah/Fixtures/derived-query-golden.json")
	if os.IsNotExist(err) {
		data, err = os.ReadFile("testdata/derived-query-golden.json")
	}
	if err != nil {
		t.Fatal(err)
	}
	var fixtures []struct {
		Name, Space, Object, Raw, Error string
		Expected                        *Projection
	}
	if err := json.Unmarshal(data, &fixtures); err != nil {
		t.Fatal(err)
	}
	for _, f := range fixtures {
		t.Run(f.Name, func(t *testing.T) {
			p, err := Project(Binding{SpaceID: "test-space", CanonicalKey: "key", Generation: "g"}, Input{
				SpaceID: f.Space, ObjectID: f.Object, TypeID: "page", IsDocument: true, Raw: []byte(f.Raw),
			})
			if f.Error != "" {
				if err == nil || !reflect.DeepEqual(p, Projection{}) {
					t.Fatal("malformed golden became valid")
				}
				return
			}
			if err != nil || !reflect.DeepEqual(p.Sources, f.Expected.Sources) || !reflect.DeepEqual(p.Topics, f.Expected.Topics) || !reflect.DeepEqual(p.Words, f.Expected.Words) {
				t.Fatalf("public golden changed: %#v %v", p, err)
			}
		})
	}
}
