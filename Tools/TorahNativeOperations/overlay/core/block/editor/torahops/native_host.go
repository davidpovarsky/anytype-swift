package torahops

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"slices"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/golang/snappy"

	"github.com/anyproto/anytype-heart/core/block/editor/storestate"
	"github.com/anyproto/anytype-heart/pb"
)

// This independent AnySync namespace is experimental. It is not a registered
// SmartBlockType, an application RPC, or evidence of hidden-object lifecycle.
const NativeChangeType = "pinkha.torah.operations.v1"
const nativePayload = "store-change/immutable-claims-v1"
const nativeSnappy = "1/s" // Heart sourceimpl's StoreChange wire format.
const maxNativeBytes = MaxWireBytes + 4096

var ErrProjectionBehind = errors.New("signed native change persisted; projection must recover")

// TargetValidator is an internal native-service dependency, never an RPC field.
// App binding must supply real object/block validation with an agreed concurrent
// deletion contract. The transport fixture validates disposable object roots;
// it does not prove cross-object atomicity or a block lifecycle.
type TargetValidator func(context.Context, Target) error

// NativeRoot derives exactly one separate operation tree per Space. Its root is
// deterministic; every operation after that root must be signed and encrypted.
// There is no parent binding to a user page or to T5's manifest.
func NativeRoot(spaceID string) (*treechangeproto.RawTreeChangeWithId, error) {
	if !validText(spaceID, true, 1024) {
		return nil, ErrInvalid
	}
	return objecttree.DeriveObjectTreeRoot(objecttree.ObjectTreeDerivePayload{
		SpaceId: spaceID, ChangeType: NativeChangeType, ChangePayload: []byte(nativePayload),
		IsEncrypted: true,
	}, nil)
}

// NativeTreeBuilder keeps AnySync's CID, signature and historical ACL checks.
// The added content check rejects malformed/foreign/plaintext operations before
// they become durable native history. No mock verifier or global override is used.
func NativeTreeBuilder(spaceID string) objecttree.BuildObjectTreeFunc {
	return func(storage objecttree.Storage, acl list.AclList) (objecttree.ObjectTree, error) {
		root, err := NativeRoot(spaceID)
		if err != nil || storage.Id() != root.Id {
			return nil, errors.Join(ErrInvalid, err)
		}
		build := objecttree.BuildObjectTreeWithContentValidator(func(ch *objecttree.Change, acl list.AclList) error {
			if ch.IsSnapshot || ch.ReadKeyId == "" || ch.Identity == nil {
				return ErrInvalid
			}
			if cached, ok := ch.Model.(*pb.StoreChange); ok {
				return validateNativeStoreChange(spaceID, ch, cached)
			}
			// The upstream validator already holds the ACL read lock here.
			keys, exists := acl.AclState().Keys()[ch.ReadKeyId]
			if !exists || keys.ReadKey == nil {
				return list.ErrNoReadKey
			}
			rawKey, err := keys.ReadKey.Raw()
			if err != nil {
				return err
			}
			key, err := crypto.NewKeyDeriver(fmt.Sprintf(crypto.AnysyncTreePath, root.Id)).DeriveKey(rawKey)
			if err != nil {
				return err
			}
			if len(ch.Data) > snappy.MaxEncodedLen(maxNativeBytes)+128 {
				return ErrReadLimit
			}
			data, err := key.Decrypt(ch.Data)
			if err != nil {
				return err
			}
			change, err := decodeNativeStoreChange(ch, data)
			if err != nil {
				return err
			}
			return validateNativeStoreChange(spaceID, ch, change)
		})
		tree, err := build(storage, acl)
		if err == nil {
			tree.SetFlusher(objecttree.MarkNewChangeFlusher())
		}
		return tree, err
	}
}

func decodeNativeStoreChange(ch *objecttree.Change, data []byte) (*pb.StoreChange, error) {
	if ch.DataType == nativeSnappy {
		size, err := snappy.DecodedLen(data)
		if err != nil || size > maxNativeBytes {
			return nil, errors.Join(ErrInvalid, err)
		}
		data, err = snappy.Decode(nil, data)
		if err != nil {
			return nil, err
		}
	} else if ch.DataType != "" {
		return nil, ErrUnsupportedVersion
	}
	if len(data) == 0 || len(data) > maxNativeBytes {
		return nil, ErrInvalid
	}
	change := &pb.StoreChange{}
	if err := change.Unmarshal(data); err != nil {
		return nil, err
	}
	return change, nil
}

func validateNativeStoreChange(spaceID string, ch *objecttree.Change, change *pb.StoreChange) error {
	if ch.Identity == nil || ch.ReadKeyId == "" || ch.IsSnapshot || len(change.ChangeSet) != 1 {
		return ErrInvalid
	}
	create := change.ChangeSet[0].GetCreate()
	if create == nil || create.Collection != CollectionName {
		return ErrInvalid
	}
	claim, err := DecodeClaim(create.DocumentId, create.Value)
	if err != nil {
		return err
	}
	if claim.Operation.SpaceID != spaceID || claim.Operation.AuthorID != ch.Identity.Account() {
		return ErrInvalid
	}
	return nil
}

type NativeHost struct {
	store          *Store
	tree           synctree.SyncTree
	key            crypto.PrivKey
	validateTarget TargetValidator
}

type NativeAppendResult struct {
	AppendResult
	ChangeID string
}

// NativeSnapshot is tied to the verified tree heads observed under its lock.
// AppliedSeq is a LOCAL storage watermark, never a cross-client causal version
// or a pagination cursor. No read succeeds while the projection is behind.
type NativeSnapshot struct {
	Projection Projection
	Heads      []string
	AppliedSeq uint64
}

// OpenNativeHost must receive a SyncTree built by NativeTreeBuilder and a
// separate projection DB. Using the tree's DB would nest independent write
// transactions. Caller owns DB/tree lifecycle; this function takes the tree lock.
func OpenNativeHost(ctx context.Context, db anystore.DB, spaceID string, tree synctree.SyncTree, key crypto.PrivKey, validate TargetValidator) (*NativeHost, error) {
	if tree == nil || key == nil || validate == nil {
		return nil, ErrInvalid
	}
	root, err := NativeRoot(spaceID)
	if err != nil {
		return nil, err
	}
	tree.Lock()
	defer tree.Unlock()
	if tree.Id() != root.Id || !bytes.Equal(root.RawChange, tree.Header().RawChange) {
		return nil, ErrInvalid
	}
	acl := tree.AclList()
	acl.RLock()
	defer acl.RUnlock()
	if err = requireCurrentReadAccess(acl, key); err != nil {
		return nil, err
	}
	store, err := New(ctx, db, spaceID)
	if err != nil {
		return nil, err
	}
	host := &NativeHost{store: store, tree: tree, key: key, validateTarget: validate}
	if _, err = host.recoverLocked(ctx, tree); err != nil {
		return nil, err
	}
	// Native storage commits first, then the replayable projection. This is the
	// same deferred-update ordering used by Heart's store-backed source.
	tree.SetDeferredUpdater(true)
	tree.SetListener(host)
	return host, nil
}

func (h *NativeHost) Append(ctx context.Context, op Operation) (NativeAppendResult, error) {
	claim, wire, err := makeClaim(op)
	if err != nil || op.SpaceID != h.store.spaceID || op.AuthorID != h.key.GetPublic().Account() {
		return NativeAppendResult{}, errors.Join(ErrInvalid, err)
	}
	if err = ctx.Err(); err != nil {
		return NativeAppendResult{}, err
	}
	h.tree.Lock()
	defer h.tree.Unlock()
	acl := h.tree.AclList()
	acl.RLock()
	allowed := acl.AclState().Permissions(h.key.GetPublic()).CanWrite()
	acl.RUnlock()
	if !allowed {
		return NativeAppendResult{}, list.ErrInsufficientPermissions
	}
	if _, err = h.recoverLocked(ctx, h.tree); err != nil {
		return NativeAppendResult{}, err
	}
	tx, err := h.store.state.NewTx(ctx)
	if err != nil {
		return NativeAppendResult{}, err
	}
	defer func() { _ = tx.Rollback() }()
	result, err := h.store.checkLocal(tx.Context(), claim)
	if err != nil || result.Disposition != Created {
		return NativeAppendResult{AppendResult: result}, err
	}
	// This callback reads native target authority, not projection caller fields.
	// Its eventual App implementation must define cross-object deletion races.
	if err = h.validateTarget(ctx, op.Target); err != nil {
		return NativeAppendResult{}, err
	}
	build := &storestate.Builder{}
	if err = build.Create(CollectionName, claim.ID, string(wire)); err != nil {
		return NativeAppendResult{}, err
	}
	data, err := build.StoreChange.Marshal()
	if err != nil {
		return NativeAppendResult{}, err
	}
	dataType := ""
	if len(data) > 64 {
		data, dataType = snappy.Encode(nil, data), nativeSnappy
	}
	added, err := h.tree.AddContentWithValidator(ctx, objecttree.SignableChangeContent{
		Data: data, DataType: dataType, Key: h.key, ShouldBeEncrypted: true, Timestamp: time.Now().Unix(),
	}, func(raw objecttree.StorageChange) error {
		// Read creator and captured ACL head from the signed bytes produced by
		// the native tree. Never substitute the current head or RPC author.
		ch, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), h.tree.Header()).Unmarshall(raw.RawTreeChangeWithId(), true)
		if err != nil {
			return err
		}
		if err = h.store.validateNative(op, NativeChange{ID: ch.Id, Order: raw.OrderId,
			Creator: ch.Identity.Account(), ACLHeadID: ch.AclHeadId}); err != nil {
			return err
		}
		return tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{
			Id: ch.Id, Order: raw.OrderId, Creator: ch.Identity.Account(), AclHeadId: ch.AclHeadId,
			Timestamp: ch.Timestamp, Changes: build.ChangeSet,
		})
	})
	if err != nil {
		return NativeAppendResult{}, err
	}
	if len(added.Added) != 1 {
		return NativeAppendResult{}, fmt.Errorf("unexpected native append result: %w", ErrProjectionBehind)
	}
	response := NativeAppendResult{AppendResult: result, ChangeID: added.Added[0].Id}
	tx.UpdateMaxAddSeq(added.Added[0].AddSeq)
	if err = tx.Commit(); err != nil {
		return response, errors.Join(ErrProjectionBehind, err)
	}
	return response, nil
}

// Update/Rebuild are called by the actual SyncTree protocol while it holds the
// tree lock. No explicit component Replay() call is involved in this path.
func (h *NativeHost) Update(tree objecttree.ObjectTree) error {
	_, err := h.recoverLocked(context.Background(), tree)
	return err
}

func (h *NativeHost) Rebuild(tree objecttree.ObjectTree) error { return h.Update(tree) }

func (h *NativeHost) recoverLocked(ctx context.Context, tree objecttree.ObjectTree) (uint64, error) {
	if tree.Id() != h.tree.Id() || tree.Root().Id != tree.Id() || tree.Root().SnapshotCounter > 1 {
		return 0, fmt.Errorf("operation tree must retain genesis history: %w", ErrInvalid)
	}
	tx, err := h.store.state.NewTx(ctx)
	if err != nil {
		return 0, err
	}
	defer func() { _ = tx.Rollback() }()
	convert := func(ch *objecttree.Change, data []byte) (any, error) {
		change, err := decodeNativeStoreChange(ch, data)
		if err == nil {
			err = validateNativeStoreChange(h.store.spaceID, ch, change)
		}
		return change, err
	}
	var applyErr error
	iterate := func(ch *objecttree.Change) bool {
		if applyErr = ctx.Err(); applyErr != nil {
			return false
		}
		if ch.Id != tree.Id() {
			change, ok := ch.Model.(*pb.StoreChange)
			if !ok {
				applyErr = ErrInvalid
				return false
			}
			if applyErr = validateNativeStoreChange(h.store.spaceID, ch, change); applyErr != nil {
				return false
			}
			applyErr = tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{
				Id: ch.Id, Order: ch.OrderId, Creator: ch.Identity.Account(), AclHeadId: ch.AclHeadId,
				Timestamp: ch.Timestamp, Changes: change.ChangeSet,
			})
			if applyErr != nil {
				return false
			}
		}
		tx.UpdateMaxAddSeq(ch.AddSeq)
		return true
	}
	if tx.IsFullyReplayed() {
		err = tree.IterateAfterAddSeq(ctx, tx.GetMaxAddSeq(), convert, iterate)
	} else {
		err = tree.IterateRoot(convert, iterate)
	}
	if err = errors.Join(err, applyErr); err != nil {
		return 0, err
	}
	tx.MarkFullyReplayed()
	seq := tx.GetMaxAddSeq()
	return seq, tx.Commit()
}

func (h *NativeHost) ReadTarget(ctx context.Context, target Target, limit uint) (NativeSnapshot, error) {
	if err := ctx.Err(); err != nil {
		return NativeSnapshot{}, err
	}
	h.tree.Lock()
	defer h.tree.Unlock()
	acl := h.tree.AclList()
	acl.RLock()
	defer acl.RUnlock()
	if err := requireCurrentReadAccess(acl, h.key); err != nil {
		return NativeSnapshot{}, err
	}
	seq, err := h.recoverLocked(ctx, h.tree)
	if err != nil {
		return NativeSnapshot{}, err
	}
	projection, err := h.store.ReadTarget(ctx, target, limit)
	if err != nil {
		return NativeSnapshot{}, err
	}
	heads := slices.Clone(h.tree.Heads())
	slices.Sort(heads)
	return NativeSnapshot{Projection: projection, Heads: heads, AppliedSeq: seq}, nil
}

// Caller holds the ACL read lock through the complete open/read operation.
// Permissions is the CURRENT locally verified ACL state. HadReadPermissions is
// deliberately unsuitable: a removed member can retain historical decryption
// keys and a populated local projection. Known local removal must deny access.
// Holding the lock prevents a local revocation from completing between this
// authorization check and returning a cached/recovered snapshot. This does not
// claim knowledge of revocations that have not reached this offline client.
func requireCurrentReadAccess(acl list.AclList, key crypto.PrivKey) error {
	if key == nil {
		return list.ErrInsufficientPermissions
	}
	switch acl.AclState().Permissions(key.GetPublic()) {
	case list.AclPermissionsReader, list.AclPermissionsGuest, list.AclPermissionsWriter,
		list.AclPermissionsAdmin, list.AclPermissionsOwner:
		return nil
	default:
		return list.ErrInsufficientPermissions
	}
}
