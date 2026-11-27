package anystorage

import (
	"bytes"
	"cmp"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"slices"
	"strings"

	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
)

type PinkhaNativeTypeResolver func(string, *treechangeproto.RawTreeChangeWithId) (smartblock.SmartBlockType, string, error)

// PinkhaNativeRoot validates the existing immutable native header before the
// caller opens an index transaction or enqueues its metadata-only admission.
// It reuses native CID decoding and the original type provider at its caller.
// Non-derived roots require their original signature. Derived roots have no
// author signature: their exact canonical native derivation bytes are checked.
// The type provider additionally validates both deterministic private roots.
func PinkhaNativeRoot(spaceID string, head contract.Head, raw *treechangeproto.RawTreeChangeWithId, resolve PinkhaNativeTypeResolver) (contract.NativeRoot, error) {
	result := contract.NativeRoot{Head: head}
	if resolve == nil || spaceID == "" || head.ID == "" || raw == nil || raw.Id != head.ID || len(raw.RawChange) == 0 || len(raw.RawChange) > contract.MaxWitnessBytes {
		return result, contract.ErrInvalidWitness
	}
	root, err := objecttree.UnmarshallRoot(raw)
	if err != nil {
		return result, err
	}
	if root.SpaceId != spaceID || root.IsDerived != head.IsDerived || root.ParentId != head.ParentID {
		return result, contract.ErrInvalidWitness
	}
	if _, err = objecttree.NewChangeBuilder(crypto.NewKeyStorage(), raw).Unmarshall(raw, true); err != nil {
		return result, err
	}
	if root.IsDerived {
		_, canonical, deriveErr := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), nil).BuildDerivedRoot(objecttree.InitialDerivedContent{SpaceId: spaceID, ChangeType: root.ChangeType, ChangePayload: root.ChangePayload, ParentId: root.ParentId})
		if deriveErr != nil {
			return result, deriveErr
		}
		if canonical == nil || canonical.Id != raw.Id || !bytes.Equal(canonical.RawChange, raw.RawChange) {
			return result, contract.ErrInvalidWitness
		}
	}
	nativeType, _, err := resolve(spaceID, raw)
	if err != nil {
		return result, err
	}
	if err = nativeType.Valid(); err != nil {
		return result, err
	}
	sum := sha256.Sum256(raw.RawChange)
	result.HeaderSHA256 = hex.EncodeToString(sum[:])
	result.NativeType = uint64(nativeType)
	result.HeaderVerified = true
	return result, nil
}

// PinkhaNativeAdmissionFromTree is called only while the original tree owner
// holds its tree lock, before entering the index queue. The signed immutable
// header supplies native kind/scope; the actual current tree supplies heads.
func PinkhaNativeAdmissionFromTree(spaceID string, tree objecttree.ObjectTree, resolve PinkhaNativeTypeResolver) (contract.NativeAdmission, error) {
	if tree == nil || tree.Header() == nil {
		return contract.NativeAdmission{}, contract.ErrInvalidWitness
	}
	header := tree.Header()
	root, err := objecttree.UnmarshallRoot(header)
	if err != nil {
		return contract.NativeAdmission{}, err
	}
	head := contract.Head{ID: tree.Id(), Heads: slices.Clone(tree.Heads()), IsDerived: root.IsDerived, ParentID: root.ParentId}
	verified, err := PinkhaNativeRoot(spaceID, head, header, resolve)
	if err != nil {
		return contract.NativeAdmission{}, err
	}
	hash := contract.HeadsHash(head.Heads)
	if hash == "" {
		return contract.NativeAdmission{}, contract.ErrInvalidWitness
	}
	return contract.NativeAdmission{Version: contract.Version, SpaceID: spaceID, RootID: head.ID,
		HeaderSHA256: verified.HeaderSHA256, NativeType: verified.NativeType, HeadsHash: hash}, nil
}

// PinkhaHeadsSnapshot is read-only even when a Space is partial. It opens only
// original existing collections, includes live/queued/deleted heads together,
// and checks native cursor, close and transaction errors. No prefix is success.
func PinkhaHeadsSnapshot(ctx context.Context, storage ClientSpaceStorage, budget *contract.Budget, resolve PinkhaNativeTypeResolver) (result contract.NativeSnapshot, err error) {
	if ctx == nil || resolve == nil || storage == nil || storage.AnyStore() == nil {
		return result, contract.ErrNotLoaded
	}
	if err = ctx.Err(); err != nil {
		return result, err
	}
	tx, err := storage.AnyStore().ReadTx(ctx)
	if err != nil {
		return result, err
	}
	defer func() {
		err = errors.Join(err, tx.Commit())
		if err != nil {
			result = contract.NativeSnapshot{}
		}
	}()
	state, err := storage.StateStorage().GetState(tx.Context())
	if err != nil {
		return result, err
	}
	if state.SpaceId != storage.Id() || state.AclId == "" || state.SettingsId == "" {
		return result, contract.ErrInvalidWitness
	}
	if err = budget.Add(len(state.SpaceId) + len(state.AclId) + len(state.SettingsId)); err != nil {
		return result, err
	}
	result.SpaceID, result.ACLID, result.SettingsID = state.SpaceId, state.AclId, state.SettingsId
	collection, err := storage.AnyStore().OpenCollection(tx.Context(), headstorage.HeadsCollectionName)
	if err != nil {
		return result, err
	}
	iterator, err := collection.Find(nil).Iter(tx.Context())
	if err != nil {
		return result, err
	}
	defer func() { err = errors.Join(err, iterator.Err(), iterator.Close()) }()
	seen := make(map[string]bool)
	for iterator.Next() {
		if err = ctx.Err(); err != nil {
			return result, err
		}
		if len(result.Roots) >= contract.MaxObjects {
			return result, contract.ErrBound
		}
		document, readErr := iterator.Doc()
		if readErr != nil {
			return result, readErr
		}
		if err = budget.Value(document.Value()); err != nil {
			return result, err
		}
		id := strings.Clone(document.Value().GetString("id"))
		if id == "" || seen[id] {
			return result, contract.ErrInvalidWitness
		}
		seen[id] = true
		entry, readErr := storage.HeadStorage().GetEntry(tx.Context(), id)
		if readErr != nil {
			return result, readErr
		}
		if entry.Id != id || entry.DeletedStatus < headstorage.DeletedStatusNotDeleted || entry.DeletedStatus > headstorage.DeletedStatusDeleted {
			return result, contract.ErrInvalidWitness
		}
		head := contract.CopyHead(entry)
		root := contract.NativeRoot{Head: head, Protocol: id == state.AclId || id == state.SettingsId}
		if !root.Protocol && head.DeletedStatus == headstorage.DeletedStatusNotDeleted {
			raw, readErr := storage.TreeRoot(tx.Context(), id)
			if readErr != nil {
				// An unavailable accepted head cannot be silently excluded. The
				// complete handler returns incomplete after its final ACL fence.
				root.RootFailure = contract.MissingNativeRoot
			} else {
				if err = budget.Add(len(raw.RawChange)); err != nil {
					return result, err
				}
				root, readErr = PinkhaNativeRoot(result.SpaceID, head, raw, resolve)
				if readErr != nil {
					root = contract.NativeRoot{Head: head, RootFailure: contract.UnknownNativeRoot}
				}
			}
		}
		result.Roots = append(result.Roots, root)
	}
	if err = iterator.Err(); err != nil {
		return result, err
	}
	slices.SortFunc(result.Roots, func(a, b contract.NativeRoot) int { return cmp.Compare(a.Head.ID, b.Head.ID) })
	return result, nil
}
