package storeresolver

import (
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/relationutils"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// readIndex is the complete read surface used by the resolver. New continues to
// accept spaceindex.Store; narrowing this private field adds no live behavior.
type readIndex interface {
	SpaceId() string
	ListAllRelations() (relationutils.Relations, error)
	GetRelationByKey(string) (*model.Relation, error)
	GetRelationById(string) (*model.Relation, error)
	ListRelationOptions(domain.RelationKey) ([]*model.RelationOption, error)
	GetDetails(string) (*domain.Details, error)
	Query(database.Query) ([]database.Record, error)
}
