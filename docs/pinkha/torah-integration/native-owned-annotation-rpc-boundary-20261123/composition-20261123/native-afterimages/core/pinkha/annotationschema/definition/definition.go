// Package definition owns the immutable original annotation schema values.
// Every call returns owned data. No application, registrar, permission, mutable
// native object or completion capability is imported or returned here.
package definition

import (
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

const Protocol = "pinkha.torah.annotation/1"
const TypeUniqueKey = "ot-pinkhatorahannotationv1"

var relationNames = [...]struct{ key, name string }{
	{"pinkhaTorahAnnotationProtocol", "Torah annotation protocol"},
	{"pinkhaTorahAnnotationClassification", "Torah annotation classification"},
	{"pinkhaTorahAnnotationNamespace", "Torah annotation namespace"},
	{"pinkhaTorahAnnotationUUID", "Torah annotation UUID"},
	{"pinkhaTorahAnnotationCreationDestination", "Torah annotation creation destination"},
	{"pinkhaTorahAnnotationCreationAccount", "Torah annotation creation account"},
	{"pinkhaTorahAnnotationCreationSpace", "Torah annotation creation Space"},
	{"pinkhaTorahAnnotationCreationMessageID", "Torah annotation creation message ID"},
	{"pinkhaTorahAnnotationCreationMutationID", "Torah annotation creation mutation ID"},
	{"pinkhaTorahAnnotationCreationRevision", "Torah annotation creation revision"},
	{"pinkhaTorahAnnotationCreationSourceDigest", "Torah annotation creation source digest"},
	{"pinkhaTorahAnnotationCreationPayloadDigest", "Torah annotation creation payload digest"},
	{"pinkhaTorahAnnotationAppliedMessageID", "Torah annotation applied message ID"},
	{"pinkhaTorahAnnotationAppliedMutationID", "Torah annotation applied mutation ID"},
	{"pinkhaTorahAnnotationAppliedRevision", "Torah annotation applied revision"},
	{"pinkhaTorahAnnotationAppliedSourceDigest", "Torah annotation applied source digest"},
	{"pinkhaTorahAnnotationAppliedPayloadDigest", "Torah annotation applied payload digest"},
}

// Definitions supplies new owned values on every call. Fixed native keys, not
// display names, determine identity. A renamed definition is conservatively a
// structural mismatch; this read-only component never renames or repairs it.
func Definitions() ([]objectcreator.FixedSchemaDefinition, error) {
	result := make([]objectcreator.FixedSchemaDefinition, 0, len(relationNames)+1)
	key, err := domain.UnmarshalUniqueKey(TypeUniqueKey)
	if err != nil {
		return nil, err
	}
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, "Torah annotation")
	details.SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_objectType))
	details.SetInt64(bundle.RelationKeyRecommendedLayout, int64(model.ObjectType_basic))
	result = append(result, objectcreator.FixedSchemaDefinition{Key: key, Required: details})
	for _, relation := range relationNames {
		key, err := domain.NewUniqueKey(coresb.SmartBlockTypeRelation, relation.key)
		if err != nil {
			return nil, err
		}
		details := domain.NewDetails()
		details.SetString(bundle.RelationKeyName, relation.name)
		details.SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_relation))
		// Longtext is numeric zero. Its explicit presence is mandatory.
		details.SetInt64(bundle.RelationKeyRelationFormat, int64(model.RelationFormat_longtext))
		result = append(result, objectcreator.FixedSchemaDefinition{Key: key, Required: details})
	}
	return result, nil
}

// RelationNames returns an array value, never the private original storage.
// The parent package uses its owned copy to preserve the existing private shape.
func RelationNames() [len(relationNames)]struct{ Key, Name string } {
	var result [len(relationNames)]struct{ Key, Name string }
	for i, relation := range relationNames {
		result[i].Key, result[i].Name = relation.key, relation.name
	}
	return result
}
