package bookmarkcreate

import (
	"encoding/base64"
	"fmt"
	"reflect"
	"strings"
	"testing"
)

func validFixtureFrame() Frame {
	return Frame{Contract: Contract, Version: 1, AccountID: "account-A", SpaceID: "space-A", StoreGeneration: "existing-store-epoch",
		TypeID: "type-A", Collections: []string{"owner-A"}, PropertyOwnerID: "owner-A", PropertyID: "source-url-A",
		TypeSHA256: strings.Repeat("1", 64), OwnerSHA256: strings.Repeat("2", 64), PropertySHA256: strings.Repeat("3", 64),
		Dependencies: []Dependency{{ObjectID: "owner-A", Heads: []string{"owner-head-A"}}, {ObjectID: "type-A", Heads: []string{"type-head-A"}}},
		StaticOwners: []StaticOwner{}}
}

func TestBookmarkFrameCanonicalClosedEncoding(t *testing.T) {
	f := validFixtureFrame()
	token, err := Encode(f)
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := Decode(token)
	if err != nil || !reflect.DeepEqual(f, decoded) {
		t.Fatalf("canonical roundtrip: %v", err)
	}
	raw, err := base64.RawURLEncoding.DecodeString(token)
	if err != nil {
		t.Fatal(err)
	}
	mutations := []string{
		strings.Replace(string(raw), `"version":1`, `"version":2`, 1),
		strings.Replace(string(raw), `"version":1`, `"version":1,"version":1`, 1),
		strings.Replace(string(raw), `"version":1`, `"Version":1`, 1),
		strings.Replace(string(raw), `"version":1`, `"version":1.0`, 1),
		strings.Replace(string(raw), `"version":1`, `"version":1,"futureAuthority":true`, 1),
		strings.Replace(string(raw), `"accountId":"account-A"`, `"accountId":"account-\u0041"`, 1),
		strings.Replace(string(raw), `"staticOwners":[]`, `"staticOwners":null`, 1),
		" " + string(raw), string(raw) + "\n", string(raw) + `{}`,
	}
	for i, mutation := range mutations {
		if mutation == string(raw) {
			t.Fatalf("negative mutation %d did not change bytes", i)
		}
		_, err := Decode(base64.RawURLEncoding.EncodeToString([]byte(mutation)))
		if err == nil {
			t.Fatalf("accepted noncanonical/unknown/duplicate frame %d", i)
		}
	}
	for _, bad := range []string{token + "=", token + "\n", "", strings.Repeat("A", MaxFrameEncodedBytes+1)} {
		if _, err := Decode(bad); err == nil {
			t.Fatal("accepted invalid base64 frame")
		}
	}
}

func TestBookmarkFrameRequiresCompleteUniqueDependencySet(t *testing.T) {
	changes := []func(*Frame){
		func(f *Frame) { f.Collections = nil },
		func(f *Frame) { f.Collections = []string{"owner-A", "owner-A"} },
		func(f *Frame) { f.Collections = []string{"bin", "owner-A"} },
		func(f *Frame) { f.Collections = []string{"owner-A", "template"} },
		func(f *Frame) { f.Collections = []string{"owner-A", "type-A"} },
		func(f *Frame) { f.Dependencies = f.Dependencies[1:] },
		func(f *Frame) { f.Dependencies[0].ObjectID = "foreign-owner" },
		func(f *Frame) { f.Dependencies[0].Heads = []string{} },
		func(f *Frame) { f.Dependencies[0].Heads = []string{"same", "same"} },
		func(f *Frame) { f.Dependencies[0].Heads = []string{"z", "a"} },
		func(f *Frame) { f.StaticOwners = []StaticOwner{{ObjectID: "owner-A", SHA256: strings.Repeat("4", 64)}} },
		func(f *Frame) { f.StaticOwners = []StaticOwner{{ObjectID: "foreign", SHA256: strings.Repeat("4", 64)}} },
		func(f *Frame) { f.PropertyOwnerID = "type-A" },
		func(f *Frame) { f.TypeSHA256 = strings.Repeat("A", 64) },
		func(f *Frame) { f.StoreGeneration = "" },
		func(f *Frame) { f.AccountID = "account\x00foreign" },
	}
	for i, change := range changes {
		f := validFixtureFrame()
		change(&f)
		if _, err := Encode(f); err == nil {
			t.Fatalf("accepted incomplete/aliased dependency set %d", i)
		}
	}
	f := validFixtureFrame()
	f.Collections = []string{"owner-A", "registered-B"}
	f.StaticOwners = []StaticOwner{{ObjectID: "registered-B", SHA256: strings.Repeat("4", 64)}}
	if _, err := Encode(f); err != nil {
		t.Fatalf("complete mixed immutable/dynamic dependencies: %v", err)
	}
}

func TestBookmarkFrameBoundsAndExactUTF8Identity(t *testing.T) {
	f := validFixtureFrame()
	f.PropertyID = "caf\u00e9"
	one, err := Encode(f)
	if err != nil {
		t.Fatal(err)
	}
	f.PropertyID = "cafe\u0301"
	two, err := Encode(f)
	if err != nil {
		t.Fatal(err)
	}
	if one == two {
		t.Fatal("distinct UTF8 identifiers collapsed")
	}
	for _, mutation := range []func(*Frame){
		func(f *Frame) { f.AccountID = strings.Repeat("x", MaxIDBytes+1) },
		func(f *Frame) { f.StoreGeneration = strings.Repeat("g", MaxGenerationBytes+1) },
		func(f *Frame) { f.TypeID = string([]byte{0xff}) },
		func(f *Frame) { f.Dependencies[0].Heads = make([]string, MaxHeadsPerDependency+1) },
	} {
		f := validFixtureFrame()
		mutation(&f)
		if _, err := Encode(f); err == nil {
			t.Fatal("accepted an out-of-bound frame")
		}
	}
	// Every individual head and per-dependency count can be valid while the
	// complete canonical token exceeds its byte bound. The raw bound is real.
	f = validFixtureFrame()
	for i := range f.Dependencies {
		f.Dependencies[i].Heads = nil
		for n := 0; n < MaxHeadsPerDependency; n++ {
			f.Dependencies[i].Heads = append(f.Dependencies[i].Heads, fmt.Sprintf("%02x", n)+strings.Repeat("x", 1000))
		}
	}
	if err := f.Validate(); err != nil {
		t.Fatalf("individual bounded head shape: %v", err)
	}
	if _, err := Encode(f); err == nil {
		t.Fatal("raw canonical byte cap was not enforced")
	}
}

func TestBookmarkFrameCollectionUnionIsReadOnlyNormalization(t *testing.T) {
	requested := []string{"z", "a", "z"}
	before := append([]string{}, requested...)
	got, err := NormalizeCollections(requested, "m")
	if err != nil || !reflect.DeepEqual(got, []string{"a", "m", "z"}) || !reflect.DeepEqual(requested, before) {
		t.Fatal("collection union changed input or output", err)
	}
	for _, values := range [][]string{{"bin"}, {"template"}, {""}, {"bad\x00id"}, make([]string, MaxCollections+1)} {
		if _, err := NormalizeCollections(values, "owner"); err == nil {
			t.Fatal("accepted invalid read membership")
		}
	}
}
