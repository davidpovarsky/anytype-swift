package torahindex

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"reflect"
	"testing"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

func relatedCacheDocument(raw string) *domain.Details {
	return domain.NewDetails().SetString(bundle.RelationKeyId, "A").
		SetString(bundle.RelationKeySpaceId, "S").SetString(bundle.RelationKeyType, "page").
		SetInt64(bundle.RelationKeyLayout, 0).SetString("canonical", raw)
}

func legacyRelatedCacheProof(binding torah.Binding, details *domain.Details) string {
	keys := []domain.RelationKey{}
	for _, key := range cacheInputKeys {
		if key != torah.RelatedSourcesKey && key != torah.RelatedVersionKey {
			keys = append(keys, key)
		}
	}
	keys = append(keys, domain.RelationKey(binding.CanonicalKey))
	data, _ := json.Marshal(details.CopyOnlyKeys(keys...).ToProto())
	h := sha256.New()
	h.Write([]byte("pinkha-torah-cache-v1\x00" + binding.Generation + "\x00" + binding.CanonicalKey + "\x00"))
	h.Write(data)
	h.Write([]byte{0})
	h.Write([]byte(details.GetString(domain.RelationKey(binding.CanonicalKey))))
	return hex.EncodeToString(h.Sum(nil))
}

func TestRelatedCacheInvalidatesR14AndSealsNewOutputs(t *testing.T) {
	b := torah.Binding{SpaceID: "S", CanonicalKey: "canonical", Generation: "g"}
	i := &Index{space: "S"}
	raw := `{"version":2,"records":[{"spaceId":"S","objectId":"A","blockId":"K","item":{"id":"q","kind":"ref","role":"sourceQuote","providerID":"sefaria","canonicalKey":"Genesis 3:3","externalID":"Genesis 3:3","labelHe":"quote"}}]}`
	d := relatedCacheDocument(raw)
	i.project(b, d)
	if !reusableCache(b, d) || d.GetInt64(torah.RelatedVersionKey) != 1 || len(d.GetStringList(torah.RelatedSourcesKey)) != 1 {
		t.Fatal("new related cache unavailable")
	}
	old := d.Copy()
	old.Delete(torah.RelatedSourcesKey)
	old.Delete(torah.RelatedVersionKey)
	old.SetString(torah.CacheIntegrityKey, legacyRelatedCacheProof(b, old))
	if reusableCache(b, old) {
		t.Fatal("r14 cache reused without private coverage")
	}
	rebuilt := clear(old)
	i.project(b, rebuilt)
	if !reusableCache(b, rebuilt) || rebuilt.GetString("canonical") != raw {
		t.Fatal("rebuild lost canonical bytes")
	}
	if !reflect.DeepEqual(d.GetStringList(torah.SourcesKey), rebuilt.GetStringList(torah.SourcesKey)) || d.GetString(torah.LabelsKey) != rebuilt.GetString(torah.LabelsKey) {
		t.Fatal("public projection changed during cache recovery")
	}
	rebuilt.SetStringList(torah.RelatedSourcesKey, []string{"forged"})
	if reusableCache(b, rebuilt) {
		t.Fatal("private output tampering accepted")
	}
	rebuilt.Delete(torah.RelatedVersionKey)
	sealCache(b, rebuilt)
	if reusableCache(b, rebuilt) {
		t.Fatal("fresh proof without expected private version accepted")
	}
}

func TestRelatedInvalidPrivateTargetPreservesPublicReadiness(t *testing.T) {
	b := torah.Binding{SpaceID: "S", CanonicalKey: "canonical", Generation: "g"}
	i := &Index{space: "S"}
	d := relatedCacheDocument(`{"version":2,"records":[{"spaceId":"S","objectId":"A","item":{"id":"a","kind":"ref","role":"context","providerID":"sefaria","canonicalKey":"Genesis 3:3","externalID":"Genesis 3:3","labelHe":"document"}},{"spaceId":"S","objectId":"A","blockId":"","item":{"id":"b","kind":"ref","role":"context","providerID":"sefaria","canonicalKey":"Genesis 3:4","externalID":"Genesis 3:4","labelHe":"invalid"}}]}`)
	i.project(b, d)
	if !d.GetBool(torah.ReadyKey) || d.GetInt64(torah.VersionKey) != 1 || len(d.GetStringList(torah.SourcesKey)) != 1 {
		t.Fatal("valid public Property disabled")
	}
	if d.Has(torah.RelatedVersionKey) || d.Has(torah.RelatedSourcesKey) {
		t.Fatal("invalid block advertised private capability")
	}
	for _, mutation := range []func(*domain.Details){
		func(d *domain.Details) { d.SetBool(bundle.RelationKeyIsDeleted, true) },
		func(d *domain.Details) { d.SetBool(bundle.RelationKeyIsArchived, true) },
		func(d *domain.Details) { d.SetBool(bundle.RelationKeyIsHidden, true) },
	} {
		copy := clear(d)
		mutation(copy)
		i.project(b, copy)
		if copy.Has(torah.RelatedVersionKey) || copy.Has(torah.RelatedSourcesKey) || copy.GetBool(torah.ReadyKey) {
			t.Fatal("ineligible row retained private fields")
		}
	}
}

func TestRelatedManifestCapabilityAndMalformedCleanup(t *testing.T) {
	b := torah.Binding{SpaceID: "S", CanonicalKey: "canonical", Generation: "g", ManifestObjectID: "manifest"}
	i := &Index{space: "S"}
	manifest := domain.NewDetails().SetString(bundle.RelationKeyId, "manifest").SetString(bundle.RelationKeySpaceId, "S").SetString(bundle.RelationKeyName, torah.ManifestUniqueKey)
	i.project(b, manifest)
	if manifest.GetInt64(torah.VersionKey) != 1 || manifest.GetInt64(torah.RelatedVersionKey) != 1 || !reusableCache(b, manifest) {
		t.Fatal("validated manifest capability/cache missing")
	}
	for _, mutate := range []func(*domain.Details){
		func(d *domain.Details) { d.SetString(bundle.RelationKeyId, "not-selected") },
		func(d *domain.Details) { d.SetString(bundle.RelationKeySpaceId, "foreign") },
		func(d *domain.Details) { d.Delete(bundle.RelationKeySpaceId) },
		func(d *domain.Details) { d.SetBool(bundle.RelationKeyIsDeleted, true) },
		func(d *domain.Details) { d.SetBool(bundle.RelationKeyIsArchived, true) },
	} {
		invalid := clear(manifest)
		mutate(invalid)
		i.project(b, invalid)
		if invalid.Has(torah.RelatedVersionKey) {
			t.Fatal("nonselected/foreign/deleted manifest advertised expanded capability")
		}
		if invalid.GetInt64(torah.VersionKey) != 1 {
			t.Fatal("legacy public manifest Version behavior changed")
		}
	}
	d := relatedCacheDocument(`{"version":999}`)
	i.project(b, d)
	if d.GetString(torah.StatusKey) != "UNSUPPORTED" || d.Has(torah.RelatedVersionKey) || d.Has(torah.RelatedSourcesKey) {
		t.Fatal("future payload advertised private coverage")
	}
	cleared := clear(manifest)
	for _, key := range torah.LocalKeys() {
		if cleared.Has(domain.RelationKey(key)) {
			t.Fatalf("local key survived clear: %s", key)
		}
	}
}
