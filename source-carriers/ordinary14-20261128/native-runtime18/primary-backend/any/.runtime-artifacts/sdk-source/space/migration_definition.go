package space

import (
	"context"
	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
)

const PreparedDefinitionContract = migrationintent.DefinitionContract
const (
	MigrationTypeDefinition       = migrationintent.TypeDefinition
	MigrationCollectionDefinition = migrationintent.CollectionDefinition
	MigrationPropertyDefinition   = migrationintent.PropertyDefinition
	MigrationPartDefinition       = migrationintent.PartDefinition
)

// A definition seed uses the same public creation parameters and native
// validators as ordinary definitions. It never accepts caller DAG bytes,
// replacement IDs, template copies, arbitrary batches or metatype overrides.
type MigrationDefinitionSpec struct {
	Kind          string                  `json:"kind"`
	OwnerObjectID string                  `json:"ownerObjectId,omitempty"`
	Type          *TypeCreateParams       `json:"type,omitempty"`
	Collection    *CollectionCreateParams `json:"collection,omitempty"`
	Property      *PropertyDraft          `json:"property,omitempty"`
	Part          *PartDraft              `json:"part,omitempty"`
}
type MigrationDefinitionCapabilities struct {
	Contract             string `json:"contract"`
	StoreID              string `json:"storeId"`
	AccountID            string `json:"accountId"`
	SpaceID              string `json:"spaceId"`
	TypeDefinition       int    `json:"typeDefinition"`
	CollectionDefinition int    `json:"collectionDefinition"`
	PropertyDefinition   int    `json:"propertyDefinition"`
	PartDefinition       int    `json:"partDefinition"`
	NetworkVerified      bool   `json:"networkVerified"`
}
type PreparedDefinitionService interface {
	MigrationDefinitionCapabilities(context.Context) (MigrationDefinitionCapabilities, error)
	PrepareMigrationDefinition(context.Context, MigrationInput, MigrationDefinitionSpec) (MigrationReceipt, error)
	CommitMigrationDefinition(context.Context, MigrationCommit) (MigrationReceipt, error)
	MigrationDefinitionStatus(context.Context, string) (MigrationReceipt, error)
}
