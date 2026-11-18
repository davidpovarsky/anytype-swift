package torahops

import (
	"context"
	"fmt"
	"slices"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// NativeTreeValidator validates fetched private history before native storage
// accepts it. Unlike a generic block key filter, it must reject malformed claims
// rather than silently drop them or reinterpret StoreChange as block changes.
func NativeTreeValidator(spaceID string) objecttree.ValidatorFunc {
	return func(payload treestorage.TreeStorageCreatePayload, creator objecttree.TreeStorageCreator, acl list.AclList) (objecttree.ObjectTree, error) {
		if err := torahopscontract.ValidateRoot(spaceID, payload.RootRawChange); err != nil {
			return nil, err
		}
		storage, err := creator.CreateStorageWithDeferredCreation(context.Background(), treestorage.TreeStorageCreatePayload{
			RootRawChange: payload.RootRawChange, Heads: []string{payload.RootRawChange.Id},
		})
		if err != nil {
			return nil, err
		}
		tree, err := NativeTreeBuilder(spaceID)(storage, acl)
		if err != nil {
			return nil, err
		}
		tree.Lock()
		defer tree.Unlock()
		result, err := tree.AddRawChanges(context.Background(), objecttree.RawChangesPayload{
			NewHeads: payload.Heads, RawChanges: payload.Changes,
		})
		if err != nil {
			return nil, err
		}
		actual, expected := slices.Clone(result.Heads), slices.Clone(payload.Heads)
		slices.Sort(actual)
		slices.Sort(expected)
		if !slices.Equal(actual, expected) {
			return nil, fmt.Errorf("private native heads mismatch: %w", objecttree.ErrHasInvalidChanges)
		}
		if objecttree.IsEmptyDerivedTree(tree) {
			return nil, objecttree.ErrDerived
		}
		return tree, nil
	}
}
