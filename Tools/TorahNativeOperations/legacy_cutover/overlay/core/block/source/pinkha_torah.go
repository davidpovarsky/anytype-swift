package source

import (
	"context"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/objecttreebuilder"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
)

// BuildTreeOptsForSpace selects private validation before interpreting history.
// A private root requires an independently known receiving Space. Legacy callers
// of BuildTreeOpts without that binding continue to handle legacy trees only.
func (b *BuildOptions) BuildTreeOptsForSpace(spaceID string) objecttreebuilder.BuildTreeOpts {
	return objecttreebuilder.BuildTreeOpts{
		Listener: b.Listener,
		TreeBuilder: func(storage objecttree.Storage, acl list.AclList) (objecttree.ObjectTree, error) {
			root, err := storage.Root(context.Background())
			if err != nil {
				return nil, err
			}
			tp, _, err := typeprovider.GetTypeAndKeyFromRootForSpace(spaceID, root.RawTreeChangeWithId())
			if err != nil {
				return nil, err
			}
			if tp == smartblock.SmartBlockTypePinkhaTorahOperations {
				return torahops.NativeTreeBuilder(spaceID)(storage, acl)
			}
			if tp == smartblock.SmartBlockTypePinkhaTorahCutover {
				return torahops.CutoverNativeTreeBuilder(spaceID)(storage, acl)
			}
			tree, err := objecttree.BuildKeyFilterableObjectTree(storage, acl)
			if err == nil && tp.IsStoreBacked() {
				tree.SetFlusher(objecttree.MarkNewChangeFlusher())
			}
			return tree, err
		},
		TreeValidator: func(payload treestorage.TreeStorageCreatePayload, creator objecttree.TreeStorageCreator, acl list.AclList) (objecttree.ObjectTree, error) {
			tp, _, err := typeprovider.GetTypeAndKeyFromRootForSpace(spaceID, payload.RootRawChange)
			if err != nil {
				return nil, err
			}
			if tp == smartblock.SmartBlockTypePinkhaTorahOperations {
				return torahops.NativeTreeValidator(spaceID)(payload, creator, acl)
			}
			if tp == smartblock.SmartBlockTypePinkhaTorahCutover {
				return torahops.CutoverNativeTreeValidator(spaceID)(payload, creator, acl)
			}
			return objecttree.ValidateFilterRawTree(payload, creator, acl)
		},
	}
}
