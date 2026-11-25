//go:build pinkha_loaded_account_witness

package export

import (
	"context"
	"encoding/json"
	"errors"
	"sort"

	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/block/cache"
	sb "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
	"github.com/anyproto/anytype-heart/pkg/lib/anyblockjson"
	"github.com/anyproto/anytype-heart/pkg/lib/anyblockjson/storeresolver"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
)

// NativeRawObject is a private detached native snapshot, captured before any
// export resolver runs. Only the real concrete export component can issue it.
type NativeRawObject struct {
	spaceID, objectID, uniqueKey string
	nativeType                   model.SmartBlockType
	heads                        []string
	root, snapshot               []byte
	storeBacked                  bool
	complete                     bool
}

type NativeRawObjectReceipt struct {
	Version, ObjectSHA256, HeadsSHA256, RootSHA256, SnapshotSHA256 string
	SmartBlockType                                                 int32
	SnapshotBytes                                                  int
	StoreBacked, NativeIdentityBoundUnderTreeLock                  bool
	HistorySemanticsValidated, FilePayloadCompleteness             bool
	HasNativeSourceAdmission, PermitsDestinationWrites             bool
}

func CaptureNativeRawObject(ctx context.Context, component app.Component,
	inventory *localstorewitness.NativeTreeInventory, objectID string, maxBytes int,
) (*NativeRawObject, error) {
	service, ok := component.(*export)
	if ctx == nil || !ok || service == nil || service.picker == nil || inventory == nil ||
		inventory.SpaceID() == "" || objectID == "" || maxBytes < 1 || maxBytes > 8<<20 {
		return nil, ErrNativeObjectWitness
	}
	identity, err := inventory.Tree(objectID)
	if err != nil || identity.DeletedStatus() != 0 {
		return nil, errors.Join(ErrNativeObjectWitness, err)
	}
	var result *NativeRawObject
	err = cache.DoContextFullID(service.picker, ctx,
		domain.FullID{SpaceID: inventory.SpaceID(), ObjectID: objectID},
		func(object sb.SmartBlock) error {
			if err := ctx.Err(); err != nil {
				return err
			}
			tree := object.Tree()
			if tree == nil || tree.Id() != objectID || object.Id() != objectID || object.SpaceID() != inventory.SpaceID() {
				return ErrNativeObjectWitness
			}
			root := tree.Header()
			if root == nil {
				return ErrNativeObjectWitness
			}
			if err := inventory.MatchObject(object.SpaceID(), object.Id(), root.Id, root.RawChange, tree.Heads()); err != nil {
				return err
			}
			nativeType, internalKey, err := typeprovider.GetTypeAndKeyFromRoot(root)
			if err != nil || nativeType.Valid() != nil || nativeType != object.Type() {
				return errors.Join(ErrNativeObjectWitness, err)
			}
			// DetailsStoreOwned views (participants) are not native tree-state
			// authority. Such an entry must be mapped from its real owner later.
			if nativeType.DetailsStoreOwned() {
				return ErrNativeObjectWitness
			}
			st := object.NewState()
			if st == nil || st.RootId() != objectID || st.UniqueKeyInternal() != internalKey {
				return ErrNativeObjectWitness
			}
			uniqueKey := ""
			if key := object.UniqueKey(); key != nil {
				if key.SmartblockType() != nativeType || key.InternalKey() != internalKey {
					return ErrNativeObjectWitness
				}
				uniqueKey = key.Marshal()
			}
			removed := make([]string, 0, len(st.StoreKeysRemoved()))
			for key := range st.StoreKeysRemoved() {
				removed = append(removed, key)
			}
			sort.Strings(removed)
			base := &model.SmartBlockSnapshotBase{
				Blocks: st.BlocksToSave(), Details: st.Details().ToProto(),
				ObjectTypes: domain.MarshalTypeKeys(st.ObjectTypeKeys()), Collections: st.Store(),
				RemovedCollectionKeys: removed, RelationLinks: st.PickRelationLinks(),
				Key: st.UniqueKeyInternal(), OriginalCreatedTimestamp: st.OriginalCreatedTimestamp(),
				FileInfo: st.GetFileInfo().ToModel(),
			}
			if proto.Size(base) < 1 || proto.Size(base) > maxBytes {
				return ErrNativeObjectWitness
			}
			raw, err := proto.Marshal(base)
			if err != nil {
				return err
			}
			if err := ctx.Err(); err != nil {
				return err
			}
			root = tree.Header()
			if root == nil {
				return ErrNativeObjectWitness
			}
			if err := inventory.MatchObject(object.SpaceID(), object.Id(), root.Id, root.RawChange, tree.Heads()); err != nil {
				return err
			}
			result = &NativeRawObject{spaceID: object.SpaceID(), objectID: object.Id(), uniqueKey: uniqueKey,
				nativeType: nativeType.ToProto(), heads: identity.Heads(), root: identity.RootRawChange(),
				snapshot: append([]byte(nil), raw...), storeBacked: nativeType.IsStoreBacked(), complete: true}
			return nil
		})
	if err != nil {
		return nil, err
	}
	if result == nil || !result.complete {
		return nil, ErrNativeObjectWitness
	}
	return result, nil
}
func (w *NativeRawObject) ObjectID() string {
	if w == nil || !w.complete {
		return ""
	}
	return w.objectID
}
func (w *NativeRawObject) UniqueKey() string {
	if w == nil || !w.complete {
		return ""
	}
	return w.uniqueKey
}
func (w *NativeRawObject) Type() model.SmartBlockType {
	if w == nil || !w.complete {
		return model.SmartBlockType_MissingObject
	}
	return w.nativeType
}
func (w *NativeRawObject) SnapshotBase() []byte {
	if w == nil || !w.complete {
		return nil
	}
	return append([]byte(nil), w.snapshot...)
}
func (w *NativeRawObject) MatchInventory(inventory *localstorewitness.NativeTreeInventory) error {
	if w == nil || !w.complete {
		return ErrNativeObjectWitness
	}
	return inventory.MatchObject(w.spaceID, w.objectID, w.objectID, w.root, w.heads)
}
func (w *NativeRawObject) capturedRow() (storeresolver.CapturedRow, error) {
	if w == nil || !w.complete {
		return storeresolver.CapturedRow{}, ErrNativeObjectWitness
	}
	base := new(model.SmartBlockSnapshotBase)
	if err := proto.Unmarshal(w.snapshot, base); err != nil {
		return storeresolver.CapturedRow{}, err
	}
	return storeresolver.CapturedRow{ID: w.objectID, Type: w.nativeType, UniqueKey: w.uniqueKey, Snapshot: base}, nil
}
func (w *NativeRawObject) Receipt() (NativeRawObjectReceipt, error) {
	if w == nil || !w.complete {
		return NativeRawObjectReceipt{}, ErrNativeObjectWitness
	}
	heads, err := json.Marshal(w.heads)
	if err != nil {
		return NativeRawObjectReceipt{}, err
	}
	return NativeRawObjectReceipt{Version: "native-raw-object-snapshot-v1",
		ObjectSHA256: nativeObjectWitnessHash([]byte(w.objectID)), HeadsSHA256: nativeObjectWitnessHash(heads),
		RootSHA256: nativeObjectWitnessHash(w.root), SnapshotSHA256: nativeObjectWitnessHash(w.snapshot),
		SmartBlockType: int32(w.nativeType), SnapshotBytes: len(w.snapshot), StoreBacked: w.storeBacked,
		NativeIdentityBoundUnderTreeLock: true}, nil
}

// NativeCapturedResolver can only be constructed from real detached captures
// joined to the same native inventory. The generic pure resolver grants no
// account authority; application ownership/final-checkpoint checks remain above.
type NativeCapturedResolver struct {
	inventory *localstorewitness.NativeTreeInventory
	objects   map[string]*NativeRawObject
	resolver  *storeresolver.CapturedResolver
}

func NewNativeCapturedResolver(inventory *localstorewitness.NativeTreeInventory, objects []*NativeRawObject) (*NativeCapturedResolver, error) {
	if inventory == nil || len(objects) == 0 {
		return nil, ErrNativeObjectWitness
	}
	result := &NativeCapturedResolver{inventory: inventory, objects: map[string]*NativeRawObject{}}
	rows := make([]storeresolver.CapturedRow, 0, len(objects))
	for _, object := range objects {
		if err := object.MatchInventory(inventory); err != nil {
			return nil, err
		}
		if result.objects[object.objectID] != nil {
			return nil, ErrNativeObjectWitness
		}
		row, err := object.capturedRow()
		if err != nil {
			return nil, err
		}
		rows = append(rows, row)
		result.objects[object.objectID] = object
	}
	resolver, err := storeresolver.NewCaptured(inventory.SpaceID(), rows)
	if err != nil {
		return nil, err
	}
	result.resolver = resolver
	return result, nil
}
func (r *NativeCapturedResolver) Unmapped() []storeresolver.UnmappedReference {
	if r == nil || r.resolver == nil {
		return nil
	}
	return r.resolver.Unmapped()
}
func (r *NativeCapturedResolver) BundledDefinitionsUsed() []string {
	if r == nil || r.resolver == nil {
		return nil
	}
	return r.resolver.BundledDefinitionsUsed()
}
func (r *NativeCapturedResolver) Render(ctx context.Context, objectID string, maxBytes int) ([]byte, error) {
	if r == nil || r.resolver == nil || ctx == nil || maxBytes < 1 || maxBytes > 8<<20 {
		return nil, ErrNativeObjectWitness
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	object := r.objects[objectID]
	if object == nil {
		return nil, ErrNativeObjectWitness
	}
	if err := object.MatchInventory(r.inventory); err != nil {
		return nil, err
	}
	row, err := object.capturedRow()
	if err != nil {
		return nil, err
	}
	details := domain.NewDetailsFromProto(row.Snapshot.Details)
	details.Set(bundle.RelationKeyId, domain.String(objectID))
	details.Set(bundle.RelationKeySpaceId, domain.String(r.inventory.SpaceID()))
	if row.UniqueKey != "" {
		details.Set(bundle.RelationKeyUniqueKey, domain.String(row.UniqueKey))
	}
	row.Snapshot.Details = details.ToProto()
	opts, err := r.resolver.OptionsForObject(objectID)
	if err != nil {
		return nil, err
	}
	warnings := 0
	opts.OnWarning = func(anyblockjson.Issue) { warnings++ }
	raw, err := anyblockjson.Marshal(row.Type, row.Snapshot, opts)
	if err != nil || warnings != 0 || len(raw) == 0 || len(raw) > maxBytes {
		return nil, errors.Join(ErrNativeObjectWitness, err)
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	return raw, nil
}
