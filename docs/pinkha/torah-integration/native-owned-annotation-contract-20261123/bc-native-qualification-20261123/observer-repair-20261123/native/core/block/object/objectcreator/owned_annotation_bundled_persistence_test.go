package objectcreator

import (
	"context"
	"slices"
	"testing"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/source/sourceimpl"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
)

// This is a new semantic control over the original compiled bundled sources and
// native State. It does not manufacture persisted rows or grant schema readiness.
func TestOwnedAnnotationBundledPersistedDefinitionContract(t *testing.T) {
	keys := []domain.UniqueKey{
		domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, bundle.TypeKeyObjectType.String()),
		domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, bundle.TypeKeyParticipant.String()),
		domain.MustUniqueKey(coresb.SmartBlockTypeRelation, bundle.RelationKeyName.String()),
		domain.MustUniqueKey(coresb.SmartBlockTypeRelation, bundle.RelationKeySourceObject.String()),
		domain.MustUniqueKey(coresb.SmartBlockTypeRelation, bundle.RelationKeyRevision.String()),
	}
	for _, key := range keys {
		t.Run(key.Marshal(), func(t *testing.T) {
			var (
				document state.Doc
				err      error
				bundled  string
			)
			switch key.SmartblockType() {
			case coresb.SmartBlockTypeObjectType:
				bundled = domain.TypeKey(key.InternalKey()).BundledURL()
				document, err = sourceimpl.NewBundledObjectType(bundled).ReadDoc(context.Background(), nil, false)
			case coresb.SmartBlockTypeRelation:
				bundled = domain.RelationKey(key.InternalKey()).BundledURL()
				document, err = sourceimpl.NewBundledRelation(bundled).ReadDoc(context.Background(), nil, false)
			}
			if err != nil {
				t.Fatal(err)
			}
			native, ok := document.(*state.State)
			if !ok || native == nil || native.UniqueKeyInternal() != key.InternalKey() {
				t.Fatal("original bundled source lost its native header key")
			}
			if native.Details().Has(bundle.RelationKeyUniqueKey) ||
				native.LocalDetails().GetString(bundle.RelationKeyUniqueKey) != key.Marshal() {
				t.Fatal("original derived unique key must be local, not a persisted detail")
			}

			definition, err := originalOwnedAnnotationBundledDefinition(key)
			if err != nil {
				t.Fatal(err)
			}
			for field := range definition.Required.IterateKeys() {
				if slices.Contains(bundle.LocalAndDerivedRelationKeys, field) {
					t.Fatalf("raw persisted definition contains local/derived field %q", field)
				}
			}
			// The actual original installer adds this one persisted provenance
			// field after reading the original marketplace object. Keep that
			// expected transform explicit; no derived value is copied into Details.
			native.SetDetailAndBundledRelation(bundle.RelationKeySourceObject, domain.String(bundled))
			if !fixedSchemaObjectTypeMatches(key.SmartblockType(), native.ObjectTypeKeys()) ||
				!fixedSchemaDetailsMatch(native.Details(), definition.Required) {
				t.Fatal("original installed persisted fields do not match the bundled definition")
			}

			// The former raw-details predicate must fail on original native State.
			// This demonstrates the defect without populating a false raw uniqueKey.
			former := definition.Required.Copy()
			former.SetString(bundle.RelationKeyUniqueKey, key.Marshal())
			if fixedSchemaDetailsMatch(native.Details(), former) {
				t.Fatal("derived unique key unexpectedly became persisted evidence")
			}
			for field := range definition.Required.IterateKeys() {
				corrupt := native.Details().Copy()
				corrupt.Set(field, domain.Bool(true))
				if fixedSchemaDetailsMatch(corrupt, definition.Required) {
					t.Fatalf("wrong persisted field %q was accepted", field)
				}
			}
			if fixedSchemaObjectTypeMatches(key.SmartblockType(), []domain.TypeKey{bundle.TypeKeyPage}) {
				t.Fatal("wrong original object type was accepted")
			}
		})
	}
	t.Run("unsupported-bundled-key", func(t *testing.T) {
		key := domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "otzariaUnsupportedNativeSchema")
		if _, err := originalOwnedAnnotationBundledDefinition(key); err == nil {
			t.Fatal("unsupported original bundled key was accepted")
		}
	})
}
