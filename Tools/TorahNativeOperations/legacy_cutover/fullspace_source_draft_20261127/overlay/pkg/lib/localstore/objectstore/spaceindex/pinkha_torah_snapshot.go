package spaceindex

import (
	"context"
	"encoding/json"
	"errors"
	"slices"
	"strings"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/anytype-heart/core/domain"
	torahindex "github.com/anyproto/anytype-heart/core/pinkha/torahindex"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
)

type pinkhaIndexedHead struct {
	hash     string
	marker   string
	native   *contract.NativeAdmission
	deletion *contract.DeletionAdmission
	invalid  bool
}

func pinkhaReadCollection(ctx context.Context, collection anystore.Collection, budget *contract.Budget, visit func(*anyenc.Value) error) (err error) {
	iterator, err := collection.Find(nil).Iter(ctx)
	if err != nil {
		return err
	}
	defer func() { err = errors.Join(err, iterator.Err(), iterator.Close()) }()
	count := 0
	for iterator.Next() {
		if err = ctx.Err(); err != nil {
			return err
		}
		count++
		if count > contract.MaxObjects {
			return contract.ErrBound
		}
		document, readErr := iterator.Doc()
		if readErr != nil {
			return readErr
		}
		if err = budget.Value(document.Value()); err != nil {
			return err
		}
		if err = visit(document.Value()); err != nil {
			return err
		}
	}
	return iterator.Err()
}

// PinkhaTorahSnapshot resolves nativeTorah before acquiring the index ReadTx.
// Every indexed head and projected object is then read in the SAME transaction;
// the original resolver/projector operate on that context without any writes.
func PinkhaTorahSnapshot(ctx context.Context, store Store, native contract.NativeSnapshot, canonicalKey string, budget *contract.Budget) (result contract.IndexSnapshot, err error) {
	s, ok := store.(*dsObjectStore)
	if !ok || s.spaceId != native.SpaceID || canonicalKey == "" {
		return result, contract.ErrNotLoaded
	}
	index := s.nativeTorah()
	if index == nil || index.ReadinessRunID() == "" {
		return result, contract.ErrNotLoaded
	}
	result = contract.IndexSnapshot{SpaceID: s.spaceId, RunID: index.ReadinessRunID(), CanonicalKey: canonicalKey, Reasons: []contract.Reason{}}
	tx, err := s.db.ReadTx(ctx)
	if err != nil {
		return result, err
	}
	defer func() {
		err = errors.Join(err, tx.Commit())
		if err != nil {
			result = contract.IndexSnapshot{}
		}
	}()
	rows := make(map[string]*domain.Details)
	err = pinkhaReadCollection(tx.Context(), s.objects, budget, func(value *anyenc.Value) error {
		details, decodeErr := domain.NewDetailsFromAnyEnc(value)
		if decodeErr != nil {
			return decodeErr
		}
		id := details.GetString(bundle.RelationKeyId)
		if id == "" || rows[id] != nil {
			return contract.ErrInvalidWitness
		}
		rows[id] = details
		return nil
	})
	if err != nil {
		return result, err
	}
	heads := make(map[string]pinkhaIndexedHead)
	err = pinkhaReadCollection(tx.Context(), s.headsState, budget, func(value *anyenc.Value) error {
		id := strings.Clone(value.GetString("id"))
		if _, duplicate := heads[id]; id == "" || duplicate {
			return contract.ErrInvalidWitness
		}
		row := pinkhaIndexedHead{hash: strings.Clone(value.GetString(headsStateField)), marker: strings.Clone(value.GetString(lastReconciledLinksField))}
		if field := value.Get(pinkhaNativeAdmissionField); field != nil {
			if field.Type() != anyenc.TypeString {
				row.invalid = true
			} else {
				var admission contract.NativeAdmission
				if json.Unmarshal(field.GetStringBytes(), &admission) != nil {
					row.invalid = true
				} else {
					row.native = &admission
				}
			}
		}
		if field := value.Get(pinkhaDeletionAdmissionField); field != nil {
			if field.Type() != anyenc.TypeString {
				row.invalid = true
			} else {
				var admission contract.DeletionAdmission
				if json.Unmarshal(field.GetStringBytes(), &admission) != nil {
					row.invalid = true
				} else {
					row.deletion = &admission
				}
			}
		}
		heads[id] = row
		return nil
	})
	if err != nil {
		return result, err
	}
	nativeIDs := make(map[string]bool, len(native.Roots))
	for _, root := range native.Roots {
		nativeIDs[root.Head.ID] = true
	}
	if !nativeIDs[native.ACLID] || !nativeIDs[native.SettingsID] {
		result.Reasons = contract.AddReason(result.Reasons, contract.MissingNativeRoot)
	}
	binding, propertyID, bindingErr := index.ReadinessBinding(tx.Context(), rows, canonicalKey)
	if bindingErr == nil && (!nativeIDs[binding.ManifestObjectID] || !nativeIDs[propertyID]) {
		bindingErr = contract.ErrInvalidWitness
	}
	if bindingErr != nil {
		result.Reasons = contract.AddReason(result.Reasons, contract.InvalidBinding)
	} else {
		result.BindingGeneration = binding.Generation
	}
	for _, root := range native.Roots {
		if err = ctx.Err(); err != nil {
			return result, err
		}
		id := root.Head.ID
		if root.Protocol {
			if root.Head.DeletedStatus != headstorage.DeletedStatusNotDeleted {
				result.Reasons = contract.AddReason(result.Reasons, contract.MissingNativeRoot)
			}
			continue
		}
		indexed, exists := heads[id]
		witness := contract.IndexedWitness{ID: id, HeadsHash: indexed.hash, Native: indexed.native, Deletion: indexed.deletion, ReconcileMarker: indexed.marker}
		appendWitness := func() { result.Witnesses = append(result.Witnesses, witness) }
		if root.Head.DeletedStatus == headstorage.DeletedStatusQueued {
			witness.Classification = "queued-native-deletion"
			result.Reasons = contract.AddReason(result.Reasons, contract.PendingDeletion)
			appendWitness()
			continue
		}
		if root.Head.DeletedStatus == headstorage.DeletedStatusDeleted {
			witness.Classification = "terminal-native-deletion"
			if !exists || indexed.deletion == nil {
				result.Reasons = contract.AddReason(result.Reasons, contract.MissingDeletionAdmission)
			} else if indexed.invalid || indexed.hash != "" || indexed.native != nil || !indexed.deletion.Matches(s.spaceId, root.Head) ||
				!torahindex.IsReadinessTombstone(rows[id], s.spaceId, id, canonicalKey) {
				result.Reasons = contract.AddReason(result.Reasons, contract.StaleDeletionAdmission)
			} else {
				result.IndexedObjectCount++
			}
			appendWitness()
			continue
		}
		// Match EVERY live native object before classification, including native
		// metadata. A stale type row cannot turn an unindexed new object invisible.
		if !exists || indexed.hash == "" {
			result.Reasons = contract.AddReason(result.Reasons, contract.MissingIndexedHeads)
			appendWitness()
			continue
		}
		if indexed.invalid || indexed.deletion != nil || indexed.hash != contract.HeadsHash(root.Head.Heads) {
			result.Reasons = contract.AddReason(result.Reasons, contract.IndexedHeadsChanged)
			appendWitness()
			continue
		}
		if !root.HeaderVerified {
			reason := root.RootFailure
			if reason == "" {
				reason = contract.UnknownNativeRoot
			}
			result.Reasons = contract.AddReason(result.Reasons, reason)
			appendWitness()
			continue
		}
		if PinkhaMetadataKind(root.NativeType) {
			witness.Classification = "validated-native-metadata"
			if indexed.native == nil || !indexed.native.Matches(s.spaceId, root) {
				result.Reasons = contract.AddReason(result.Reasons, contract.MissingNativeAdmission)
			} else if torahindex.CouldDeliverRelated(rows[id]) {
				result.Reasons = contract.AddReason(result.Reasons, contract.StaleProjection)
			} else {
				result.IndexedObjectCount++
			}
			appendWitness()
			continue
		}
		if rows[id] == nil {
			result.Reasons = contract.AddReason(result.Reasons, contract.MissingObject)
			appendWitness()
			continue
		}
		if coresb.SmartBlockType(root.NativeType).IsOneOf(coresb.SmartBlockTypeHome, coresb.SmartBlockTypeArchive) && indexed.marker != HashIds(root.Head.Heads) {
			result.Reasons = contract.AddReason(result.Reasons, contract.StaleReconciliation)
			appendWitness()
			continue
		}
		if bindingErr != nil {
			appendWitness()
			continue
		}
		projection := index.ReadinessProjection(binding, root, rows[id])
		witness.Classification, witness.ProjectionProof = projection.Classification, projection.Proof
		result.Reasons = contract.AddReason(result.Reasons, projection.Reason)
		if projection.Reason == "" {
			result.IndexedObjectCount++
			if projection.Eligible {
				result.EligibleDocumentCount++
			}
		}
		appendWitness()
	}
	for id, row := range rows {
		if !nativeIDs[id] && torahindex.CouldDeliverRelated(row) {
			result.Reasons = contract.AddReason(result.Reasons, contract.MissingNativeRoot)
		}
	}
	slices.Sort(result.Reasons)
	return result, nil
}
