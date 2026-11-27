package smartblock

import (
	"context"
	"errors"
	"slices"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
)

type pinkhaNativeIndexer interface {
	IndexPinkhaNative(context.Context, DocInfo, spaceindex.Store) error
}

func (sb *smartBlock) pinkhaNativeAdmission(tree objecttree.ObjectTree) (*contract.NativeAdmission, error) {
	admission, err := anystorage.PinkhaNativeAdmissionFromTree(sb.space.Id(), tree, typeprovider.GetTypeAndKeyFromRootForSpace)
	if err != nil {
		return nil, err
	}
	if admission.RootID != sb.Id() || admission.NativeType != uint64(sb.Type()) || !spaceindex.PinkhaMetadataKind(admission.NativeType) {
		return nil, contract.ErrInvalidWitness
	}
	return &admission, nil
}

// PinkhaNativeIndexHook captures this exact account component, Space and index
// instance at private-host registration. It never resolves a future global
// current owner. Each invocation borrows the existing deletion-drain lease; a
// retired/replaced owner cannot admit into a replacement index with the same ID.
// The host invokes it under its tree lock, only AFTER its projection commit.
func (sb *smartBlock) PinkhaNativeIndexHook() (func(context.Context, objecttree.ObjectTree) error, error) {
	indexer, ok := sb.indexer.(pinkhaNativeIndexer)
	if !ok || sb.space == nil || sb.spaceIndex == nil || sb.objectStore == nil || sb.ObjectTree == nil {
		return nil, contract.ErrNotLoaded
	}
	spaceID, rootID, kind := sb.space.Id(), sb.Id(), sb.Type()
	spaceOwner, indexOwner, accountOwner, treeOwner := sb.space, sb.spaceIndex, sb.objectStore, sb.ObjectTree
	hook := func(ctx context.Context, tree objecttree.ObjectTree) error {
		if ctx == nil {
			return contract.ErrInvalidWitness
		}
		if err := ctx.Err(); err != nil {
			return err
		}
		if tree != treeOwner || tree.Id() != rootID || sb.space != spaceOwner || sb.spaceIndex != indexOwner || sb.objectStore != accountOwner || sb.isDeleted {
			return contract.ErrScopeChanged
		}
		index, current, _, release, err := objectstore.AcquirePinkhaLoadedSpaceIndex(accountOwner, spaceID)
		if err != nil {
			return err
		}
		defer release()
		if index != indexOwner {
			return contract.ErrScopeChanged
		}
		admission, err := sb.pinkhaNativeAdmission(tree)
		if err != nil {
			return err
		}
		info := DocInfo{Id: rootID, Space: spaceOwner, Heads: slices.Clone(tree.Heads()), SmartblockType: kind,
			PinkhaNativeAdmission: admission, PinkhaIndexOwner: indexOwner}
		if err = current(); err != nil {
			return err
		}
		// Queue admission is not success: this call waits for the original index
		// transaction result. Its error cannot undo the prior native commit.
		err = indexer.IndexPinkhaNative(ctx, info, indexOwner)
		return errors.Join(err, current())
	}
	return hook, nil
}
