package anystorage

import (
	"context"

	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
)

// PinkhaDeletionAdmission captures the original persisted tuple BEFORE any
// index transaction. Deleted native rows intentionally retain this tuple after
// raw changes/header removal. No lost header or deletion timestamp is invented.
func PinkhaDeletionAdmission(ctx context.Context, storage ClientSpaceStorage, spaceID, objectID string) (contract.DeletionAdmission, error) {
	if storage == nil || storage.Id() != spaceID || spaceID == "" || objectID == "" {
		return contract.DeletionAdmission{}, contract.ErrInvalidWitness
	}
	entry, err := storage.HeadStorage().GetEntry(ctx, objectID)
	if err != nil {
		return contract.DeletionAdmission{}, err
	}
	if entry.Id != objectID || entry.DeletedStatus < headstorage.DeletedStatusNotDeleted || entry.DeletedStatus > headstorage.DeletedStatusDeleted {
		return contract.DeletionAdmission{}, contract.ErrInvalidWitness
	}
	if len(entry.Heads) > contract.MaxObjects {
		return contract.DeletionAdmission{}, contract.ErrBound
	}
	budget := &contract.Budget{}
	if err = budget.Add(len(spaceID) + len(entry.Id) + len(entry.CommonSnapshot) + len(entry.ParentId)); err != nil {
		return contract.DeletionAdmission{}, err
	}
	for _, head := range entry.Heads {
		if err = budget.Add(len(head)); err != nil {
			return contract.DeletionAdmission{}, err
		}
	}
	provenance := "captured-before-native-delete"
	if entry.DeletedStatus == headstorage.DeletedStatusDeleted {
		provenance = "retained-terminal-and-original-tombstone"
	}
	terminal := contract.CopyHead(entry)
	terminal.DeletedStatus = headstorage.DeletedStatusDeleted
	return contract.DeletionAdmission{Version: contract.Version, SpaceID: spaceID, Provenance: provenance, Terminal: terminal}, nil
}
