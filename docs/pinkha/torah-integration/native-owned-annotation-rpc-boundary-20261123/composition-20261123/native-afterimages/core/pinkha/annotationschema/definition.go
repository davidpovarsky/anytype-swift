// Package annotationschema observes the original fixed annotation schema.
// Its results are historical native observations, never permission to create,
// an annotation identity/body receipt, or a delivery acknowledgement.
package annotationschema

import (
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema/definition"
)

const Protocol = definition.Protocol
const TypeUniqueKey = definition.TypeUniqueKey

// Retain the original private array and field shape for every unchanged sibling.
// The leaf accessor returns a new array value; no mutable storage is shared.
var relationNames = func() [17]struct{ key, name string } {
	var result [17]struct{ key, name string }
	for i, relation := range definition.RelationNames() {
		result[i].key, result[i].name = relation.Key, relation.Name
	}
	return result
}()

func Definitions() ([]objectcreator.FixedSchemaDefinition, error) {
	return definition.Definitions()
}
