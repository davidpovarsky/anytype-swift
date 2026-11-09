package torahderived

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"reflect"
	"testing"
)

type fixture struct {
	Name     string      `json:"name"`
	Space    string      `json:"space"`
	Object   string      `json:"object"`
	Raw      string      `json:"raw"`
	Error    string      `json:"error"`
	Expected *Projection `json:"expected"`
}

func fixtures(t testing.TB) []fixture {
	t.Helper()
	data, err := os.ReadFile("../../Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Fixtures/derived-query-golden.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []fixture
	if err := json.Unmarshal(data, &cases); err != nil {
		t.Fatal(err)
	}
	return cases
}

func binding() Binding {
	return Binding{SpaceID: "test-space", CanonicalKey: "native-test-key", Generation: "test-generation-1"}
}

func TestSharedSwiftGoldenFixtures(t *testing.T) {
	for _, f := range fixtures(t) {
		t.Run(f.Name, func(t *testing.T) {
			raw := []byte(f.Raw)
			before := append([]byte(nil), raw...)
			got, err := Project(binding(), Input{SpaceID: f.Space, ObjectID: f.Object, TypeID: "chiddush-id", IsDocument: true, Raw: raw})
			if !bytes.Equal(raw, before) {
				t.Fatal("canonical bytes mutated")
			}
			if f.Error != "" {
				want := ErrMalformed
				if f.Error == "unsupported" {
					want = ErrUnsupported
				}
				if !errors.Is(err, want) {
					t.Fatalf("want %v, got %v", want, err)
				}
				if !reflect.DeepEqual(got, Projection{}) {
					t.Fatal("error exposed a valid-looking partial projection")
				}
				return
			}
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(got.Sources, f.Expected.Sources) || !reflect.DeepEqual(got.Topics, f.Expected.Topics) || !reflect.DeepEqual(got.Words, f.Expected.Words) {
				t.Fatalf("projection mismatch: %#v", got)
			}
		})
	}
}

func TestBindingSpaceTypeTemplateLifecycle(t *testing.T) {
	b := binding()
	for _, id := range []string{"chiddush-id", "article-id", "research-id", "page", "note", "custom-random-id"} {
		got, err := Project(b, Input{SpaceID: b.SpaceID, ObjectID: "doc", TypeID: id, IsDocument: true})
		if err != nil || len(got.Sources) != 0 {
			t.Fatalf("empty eligible document: %v", err)
		}
	}
	for _, in := range []Input{
		{SpaceID: "wrong-space", ObjectID: "doc", TypeID: "chiddush-id"},
		{SpaceID: b.SpaceID, ObjectID: "doc", TypeID: "system-record"},
		{SpaceID: b.SpaceID, TypeID: "page", IsDocument: true},
		{SpaceID: b.SpaceID, ObjectID: "doc", IsDocument: true},
		{SpaceID: b.SpaceID, ObjectID: "doc", TypeID: "chiddush-id", IsDocument: true, IsTemplate: true},
		{SpaceID: b.SpaceID, ObjectID: "doc", TypeID: "chiddush-id", IsDocument: true, IsDeleted: true},
		{SpaceID: b.SpaceID, ObjectID: "doc", TypeID: "chiddush-id", IsDocument: true, IsArchived: true},
	} {
		if _, err := Project(b, in); !errors.Is(err, ErrIneligible) {
			t.Fatalf("ineligible input was accepted: %v", err)
		}
	}
	b.CanonicalKey = ""
	if !errors.Is(b.Validate(), ErrBinding) {
		t.Fatal("missing canonical binding was accepted")
	}
}

func TestIdentityIsTypedNormalizedAndUnambiguous(t *testing.T) {
	if Identity(Ref, "sefaria", "café", "") != Identity(Ref, "sefaria", "cafe\u0301", "") {
		t.Fatal("NFC parity")
	}
	if Identity(Ref, "x|1:y", "z", "") == Identity(Ref, "x", "1:y|z", "") {
		t.Fatal("delimiter collision")
	}
	if Identity(Ref, "sefaria", "a", "") == Identity(Topic, "sefaria", "a", "") {
		t.Fatal("kind collision")
	}
	if Identity(Ref, "sefaria", "a", "") == Identity(Ref, "otzaria", "a", "") {
		t.Fatal("provider collision")
	}
	if Identity(Ref, "sefaria", "", "a") != "torah1|3:ref|7:sefaria|1:a" {
		t.Fatal("external fallback")
	}
}

func FuzzProjectNeverMutatesOrReturnsPartialOnError(f *testing.F) {
	for _, sample := range fixtures(f) {
		f.Add([]byte(sample.Raw))
	}
	f.Fuzz(func(t *testing.T, raw []byte) {
		before := append([]byte(nil), raw...)
		got, err := Project(binding(), Input{SpaceID: "test-space", ObjectID: "test-object", TypeID: "chiddush-id", IsDocument: true, Raw: raw})
		if !bytes.Equal(before, raw) {
			t.Fatal("mutated input")
		}
		if err != nil && !reflect.DeepEqual(got, Projection{}) {
			t.Fatal("partial result on error")
		}
	})
}
