package spaceindex

import (
	"context"
	"encoding/hex"
	"encoding/json"

	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-store/query"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
)

const pinkhaNativeAdmissionField = "_pinkhaTorahNativeAdmissionV1"
const pinkhaDeletionAdmissionField = "_pinkhaTorahDeletionAdmissionV1"

// PinkhaMetadataKind is the original explicit non-indexable allowlist. Missing
// objects and inferred/unknown ID types are intentionally absent.
func PinkhaMetadataKind(kind uint64) bool {
	return coresb.SmartBlockType(kind).IsOneOf(coresb.SmartBlockTypeDate,
		coresb.SmartBlockTypeAccountOld, coresb.SmartBlockTypeNotificationObject,
		coresb.SmartBlockTypeDevicesObject, coresb.SmartBlockTypePinkhaTorahOperations,
		coresb.SmartBlockTypePinkhaTorahCutover)
}

// SavePinkhaNativeAdmission must receive the original indexer's root WriteTx
// context and a header validated before queue admission. Head hash and exclusion
// witness become visible in the same original headsState write. No new store.
func SavePinkhaNativeAdmission(ctx context.Context, store Store, admission contract.NativeAdmission) error {
	s, ok := store.(*dsObjectStore)
	if !ok || s.spaceId != admission.SpaceID || admission.RootID == "" || admission.Version != contract.Version ||
		!PinkhaMetadataKind(admission.NativeType) || len(admission.HeaderSHA256) != 64 || len(admission.HeadsHash) != 64 {
		return contract.ErrInvalidWitness
	}
	if _, err := hex.DecodeString(admission.HeaderSHA256); err != nil {
		return contract.ErrInvalidWitness
	}
	if _, err := hex.DecodeString(admission.HeadsHash); err != nil {
		return contract.ErrInvalidWitness
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	encoded, err := json.Marshal(admission)
	if err != nil {
		return err
	}
	_, err = s.headsState.UpsertId(ctx, admission.RootID, query.ModifyFunc(func(arena *anyenc.Arena, value *anyenc.Value) (*anyenc.Value, bool, error) {
		value.Set(headsStateField, arena.NewString(admission.HeadsHash))
		value.Set(pinkhaNativeAdmissionField, arena.NewString(string(encoded)))
		value.Del(pinkhaDeletionAdmissionField)
		return value, true, nil
	}))
	return err
}

// PinkhaDeleteObject binds a supplied native tuple to the same original index
// deletion transaction. Callers capture it before entering the index database.
func PinkhaDeleteObject(store Store, id string, admission contract.DeletionAdmission) error {
	s, ok := store.(*dsObjectStore)
	if !ok || s.spaceId != admission.SpaceID || id == "" || admission.Terminal.ID != id ||
		admission.Version != contract.Version || admission.Terminal.DeletedStatus != headstorage.DeletedStatusDeleted ||
		(admission.Provenance != "captured-before-native-delete" && admission.Provenance != "retained-terminal-and-original-tombstone") {
		return contract.ErrInvalidWitness
	}
	return s.deleteObject(id, &admission)
}

func (s *dsObjectStore) savePinkhaDeletionAdmission(ctx context.Context, admission contract.DeletionAdmission) error {
	encoded, err := json.Marshal(admission)
	if err != nil {
		return err
	}
	_, err = s.headsState.UpsertId(ctx, admission.Terminal.ID, query.ModifyFunc(func(arena *anyenc.Arena, value *anyenc.Value) (*anyenc.Value, bool, error) {
		value.Del(headsStateField)
		value.Del(pinkhaNativeAdmissionField)
		value.Del(lastReconciledLinksField)
		value.Set(pinkhaDeletionAdmissionField, arena.NewString(string(encoded)))
		return value, true, nil
	}))
	return err
}
