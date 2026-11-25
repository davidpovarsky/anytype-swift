//go:build pinkha_loaded_account_witness

package export

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
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
)

var ErrNativeObjectWitness = errors.New("native object identity and warning-free snapshot join required")

// NativeObjectWitness contains private copies produced while the actual object
// tree was locked. The export component does not grant account authorization.
type NativeObjectWitness struct {
	spaceID, objectID, exportID, exportPath string
	heads                                   []string
	root, snapshot, document                []byte
	smartBlockType                          model.SmartBlockType
	complete                                bool
}

type NativeObjectWitnessReceipt struct {
	Version, SpaceSHA256, ObjectSHA256, ExportIDSHA256 string
	ExportPath, HeadsSHA256, RootSHA256                string
	SnapshotBaseSHA256, AnyBlockSHA256                 string
	SnapshotBaseBytes, AnyBlockBytes                   int
	SmartBlockType                                     int32
	NativeIdentityBoundUnderTreeLock                   bool
	AccountSessionAuthorized                           bool
	IndexResolverSnapshotBound                         bool
	HistorySemanticsValidated                          bool
	SemanticCompleteness                               bool
	FilePayloadCompleteness                            bool
	HasNativeSourceAdmission                           bool
	PermitsDestinationWrites                           bool
}

func nativeObjectWitnessHash(data []byte) string {
	digest := sha256.Sum256(data)
	return hex.EncodeToString(digest[:])
}

// CaptureNativeObjectWitness is intentionally tied to the application's actual
// concrete export service. A caller-supplied picker or exported Exporter wrapper
// cannot replace it. The caller must separately authorize the account/session
// and recheck the complete native checkpoint after all selected captures.
//
// cache.DoContextFullID already acquires the SmartBlock's native tree locker
// (set by editor/factory.go). Acquiring tree.Lock again would deadlock. Object
// loading can perform native normalization, so a changed final checkpoint must
// be refused rather than silently accepted or retried.
func CaptureNativeObjectWitness(ctx context.Context, component app.Component,
	inventory *localstorewitness.NativeTreeInventory, objectID string, maxBytes int,
) (*NativeObjectWitness, error) {
	service, ok := component.(*export)
	if ctx == nil || !ok || service == nil || service.picker == nil || service.objectStore == nil ||
		inventory == nil || inventory.SpaceID() == "" || objectID == "" || maxBytes <= 0 || maxBytes > 8<<20 {
		return nil, ErrNativeObjectWitness
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	identity, err := inventory.Tree(objectID)
	if err != nil || identity.DeletedStatus() != 0 {
		return nil, errors.Join(ErrNativeObjectWitness, err)
	}
	spaceID := inventory.SpaceID()
	var captured *NativeObjectWitness
	err = cache.DoContextFullID(service.picker, ctx,
		domain.FullID{SpaceID: spaceID, ObjectID: objectID},
		func(block sb.SmartBlock) error {
			if err := ctx.Err(); err != nil {
				return err
			}
			tree := block.Tree()
			if block.Id() != objectID || block.SpaceID() != spaceID || tree == nil || tree.Id() != objectID {
				return ErrNativeObjectWitness
			}
			header := tree.Header()
			if header == nil {
				return ErrNativeObjectWitness
			}
			if err := inventory.MatchObject(spaceID, objectID, header.Id, header.RawChange, tree.Heads()); err != nil {
				return errors.Join(ErrNativeObjectWitness, err)
			}
			st := block.NewState()
			if st == nil || st.RootId() != objectID ||
				(st.CombinedDetails().GetBool(bundle.RelationKeyIsDeleted) &&
					!st.CombinedDetails().GetBool(bundle.RelationKeyIsUninstalled)) {
				return ErrNativeObjectWitness
			}
			// Preserve the fields used by native sourceimpl.buildChange, plus
			// removed collection keys. This is a current snapshot base, not a
			// replacement for the original raw change history or file keys.
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
			if proto.Size(base) <= 0 || proto.Size(base) > maxBytes {
				return ErrNativeObjectWitness
			}
			// Use the native generated protobuf marshaler. This exact returned
			// byte string is retained; protobuf map order is not advertised as
			// canonical across separate captures.
			snapshot, err := proto.Marshal(base)
			if err != nil {
				return errors.Join(ErrNativeObjectWitness, err)
			}
			// Standalone AnyBlock export uses combined details. Its index
			// resolvers are real, but do not share the native witness read tx;
			// the receipt therefore does not claim resolver/schema completeness.
			base.Details = st.CombinedDetails().ToProto()
			opts := storeresolver.New(service.objectStore.SpaceIndex(spaceID)).Options()
			warned := false
			opts.OnWarning = func(anyblockjson.Issue) { warned = true }
			document, err := anyblockjson.Marshal(block.Type().ToProto(), base, opts)
			if err != nil || warned || len(document) == 0 || len(document) > maxBytes {
				return errors.Join(ErrNativeObjectWitness, err)
			}
			var envelope struct {
				ID string `json:"id"`
			}
			if err := json.Unmarshal(document, &envelope); err != nil || envelope.ID == "" {
				return errors.Join(ErrNativeObjectWitness, err)
			}
			if err := ctx.Err(); err != nil {
				return err
			}
			// Check the actual tree again before returning copies. This does
			// not use GetDocInfo, whose heads have a separate fallback path.
			header = tree.Header()
			if header == nil {
				return ErrNativeObjectWitness
			}
			if err := inventory.MatchObject(spaceID, objectID, header.Id, header.RawChange, tree.Heads()); err != nil {
				return errors.Join(ErrNativeObjectWitness, err)
			}
			captured = &NativeObjectWitness{
				spaceID: spaceID, objectID: objectID, exportID: envelope.ID,
				exportPath: "objects/" + nativeObjectWitnessHash([]byte(objectID)) + ".json",
				heads:      identity.Heads(), root: identity.RootRawChange(),
				snapshot: snapshot, document: append([]byte(nil), document...),
				smartBlockType: block.Type().ToProto(), complete: true,
			}
			return nil
		})
	if err != nil {
		return nil, err
	}
	if captured == nil || !captured.complete {
		return nil, ErrNativeObjectWitness
	}
	return captured, nil
}

func (w *NativeObjectWitness) ObjectID() string {
	if w == nil || !w.complete {
		return ""
	}
	return w.objectID
}
func (w *NativeObjectWitness) ExportID() string {
	if w == nil || !w.complete {
		return ""
	}
	return w.exportID
}
func (w *NativeObjectWitness) ExportPath() string {
	if w == nil || !w.complete {
		return ""
	}
	return w.exportPath
}
func (w *NativeObjectWitness) SnapshotBase() []byte {
	if w == nil || !w.complete {
		return nil
	}
	return append([]byte(nil), w.snapshot...)
}
func (w *NativeObjectWitness) AnyBlock() []byte {
	if w == nil || !w.complete {
		return nil
	}
	return append([]byte(nil), w.document...)
}
func (w *NativeObjectWitness) Heads() []string {
	if w == nil || !w.complete {
		return nil
	}
	return append([]string(nil), w.heads...)
}
func (w *NativeObjectWitness) MatchInventory(inventory *localstorewitness.NativeTreeInventory) error {
	if w == nil || !w.complete {
		return ErrNativeObjectWitness
	}
	return inventory.MatchObject(w.spaceID, w.objectID, w.objectID, w.root, w.heads)
}
func (w *NativeObjectWitness) Receipt() (NativeObjectWitnessReceipt, error) {
	if w == nil || !w.complete {
		return NativeObjectWitnessReceipt{}, ErrNativeObjectWitness
	}
	heads, err := json.Marshal(w.heads)
	if err != nil {
		return NativeObjectWitnessReceipt{}, err
	}
	return NativeObjectWitnessReceipt{
		Version:        "native-object-snapshot-join-v1",
		SpaceSHA256:    nativeObjectWitnessHash([]byte(w.spaceID)),
		ObjectSHA256:   nativeObjectWitnessHash([]byte(w.objectID)),
		ExportIDSHA256: nativeObjectWitnessHash([]byte(w.exportID)), ExportPath: w.exportPath,
		HeadsSHA256: nativeObjectWitnessHash(heads), RootSHA256: nativeObjectWitnessHash(w.root),
		SnapshotBaseSHA256: nativeObjectWitnessHash(w.snapshot), AnyBlockSHA256: nativeObjectWitnessHash(w.document),
		SnapshotBaseBytes: len(w.snapshot), AnyBlockBytes: len(w.document),
		SmartBlockType: int32(w.smartBlockType), NativeIdentityBoundUnderTreeLock: true,
	}, nil
}
