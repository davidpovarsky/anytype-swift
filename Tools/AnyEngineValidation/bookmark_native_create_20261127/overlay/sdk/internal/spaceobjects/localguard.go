package spaceobjects

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"sort"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/commitguard"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/object"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/util/crypto"
)

type lockedReadView struct {
	ctx     context.Context
	objects map[string]*object.Object
	store   *Store
	carrier *object.Object
}

func (v lockedReadView) Lookup(objectId, dataset, id string) (*anyenc.Value, error) {
	o := v.objects[objectId]
	if o == nil {
		return nil, errors.New("native guard: undeclared object dependency")
	}
	if o.Controller().IsShared(dataset) && id != objectId {
		return nil, errors.New("native guard: foreign shared row")
	}
	return o.Controller().GuardLookup(v.ctx, dataset, id)
}

// PreparedHeads snapshots the exact carrier/definition envelope while every
// member tree is locked. This is private SDK state, never a replicated field.
func (v lockedReadView) PreparedHeads() map[string][]string {
	heads := make(map[string][]string, len(v.objects))
	for id, obj := range v.objects {
		heads[id] = append([]string(nil), obj.Tree().Heads()...)
		sort.Strings(heads[id])
	}
	return heads
}

func (v lockedReadView) Query(objectId, dataset string, filter any, limit int) ([]*anyenc.Value, error) {
	o := v.objects[objectId]
	if o == nil {
		return nil, errors.New("native guard: undeclared object dependency")
	}
	return o.Controller().GuardQuery(v.ctx, dataset, filter, limit)
}

func (s *Store) lockLocalWrite(ctx context.Context, carrier *object.Object, ch *crdt.Change) (crdt.LocalReadView, func(), error) {
	g := carrier.Controller().LocalGuard(ch.Dataset)
	if g == nil && !ch.NativeObjectPolicy && ch.NativeDefinitionPolicy == "" {
		return nil, nil, errors.New("native guard: no handler")
	}
	var ids []string
	var err error
	if g != nil {
		ids, err = g.LocalTargets(ch)
		if err != nil {
			return nil, nil, err
		}
	}
	if len(ids) > 256 {
		return nil, nil, errors.New("native guard: dependency limit")
	}
	objects := map[string]*object.Object{carrier.Id(): carrier}
	for _, id := range ids {
		if id == "" {
			return nil, nil, errors.New("native guard: empty target")
		}
		if objects[id] != nil {
			continue
		}
		o, err := s.Get(ctx, id)
		if err != nil {
			return nil, nil, err
		}
		objects[id] = o
	}
	if err := s.preloadNativeDefinitions(ctx, objects, carrier, ch); err != nil {
		return nil, nil, err
	}
	return s.lockPreparedNativeObjects(ctx, objects, carrier)
}

func (s *Store) lockPreparedNativeObjects(ctx context.Context, objects map[string]*object.Object, carrier *object.Object) (crdt.LocalReadView, func(), error) {
	order := make([]string, 0, len(objects))
	for id := range objects {
		order = append(order, id)
	}
	sort.Strings(order)
	locked := make([]*object.Object, 0, len(order))
	unlock := func() {
		for i := len(locked) - 1; i >= 0; i-- {
			locked[i].Tree().Unlock()
		}
	}
	for _, id := range order {
		o := objects[id]
		if err := ctx.Err(); err != nil {
			unlock()
			return nil, nil, err
		}
		if o.Tree() == nil {
			unlock()
			return nil, nil, object.ErrTreeNotSet
		}
		o.Tree().Lock()
		locked = append(locked, o)
		if err := o.GuardReadyLocked(ctx); err != nil {
			unlock()
			return nil, nil, err
		}
	}
	return lockedReadView{ctx: ctx, objects: objects, store: s, carrier: carrier}, unlock, nil
}

// guardedTreeBuilder keeps AnySync's cryptographic/historical ACL verifier and
// adds the compiled module's intrinsic validator BEFORE native tree storage.
// It never evaluates mutable targets or predecessor arrival order on replay.
func (s *Store) guardedTreeBuilder(guards map[string]crdt.GuardedHandler) objecttree.BuildObjectTreeFunc {
	return func(storage objecttree.Storage, acl list.AclList) (objecttree.ObjectTree, error) {
		header, err := storage.Root(context.Background())
		if err != nil {
			return nil, err
		}
		rawRoot := header.RawTreeChangeWithId()
		root, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), rawRoot).Unmarshall(rawRoot, true)
		if err != nil {
			return nil, err
		}
		info, _ := root.Model.(*treechangeproto.TreeChangeInfo)
		var seed []byte
		if info != nil {
			seed = info.ChangePayload
		}
		isCarrier := false
		for _, g := range guards {
			isCarrier = isCarrier || (root.IsDerived && bytes.Equal(seed, g.GuardRootSeed()))
		}
		validate := func(raw *objecttree.Change, acl list.AclList) error {
			if raw.Id == rawRoot.Id {
				return nil
			}
			_, namedGuard := guards[raw.DataType]
			// A bounded read of other SDK changes also detects a forged outer
			// DataType that attempts to hide a guarded inner dataset.
			if len(raw.Data) > 2*1024*1024 {
				if isCarrier || namedGuard {
					return errors.New("native guard: change exceeds wire bound")
				}
				return nil
			}
			data := raw.Data
			if raw.ReadKeyId != "" {
				keys, ok := acl.AclState().Keys()[raw.ReadKeyId]
				if !ok || keys.ReadKey == nil {
					return list.ErrNoReadKey
				}
				rawKey, err := keys.ReadKey.Raw()
				if err != nil {
					return err
				}
				key, err := crypto.NewKeyDeriver(fmt.Sprintf(crypto.AnysyncTreePath, storage.Id())).DeriveKey(rawKey)
				if err != nil {
					return err
				}
				data, err = key.Decrypt(raw.Data)
				if err != nil {
					return err
				}
			}
			decoded, err := object.NewCodec().Decode(data)
			if err != nil {
				if isCarrier || namedGuard {
					return err
				}
				return nil
			}
			g := guards[decoded.Dataset]
			if g == nil {
				return nil
			}
			if raw.ReadKeyId == "" || raw.Identity == nil || raw.IsSnapshot {
				return errors.New("native guard: signed encrypted operation required")
			}
			decoded.SpaceId, decoded.ObjectId = s.spaceId, storage.Id()
			decoded.ChangeId, decoded.Creator, decoded.ACLHeadId = raw.Id, raw.Identity.Account(), raw.AclHeadId
			decoded.ObjectDerived, decoded.ObjectRootPayload = root.IsDerived, append([]byte(nil), seed...)
			return g.ValidateNative(&decoded)
		}
		return commitguard.Builder(validate)(storage, acl)
	}
}

// NativeReadSnapshot holds all declared native objects, then current ACL, then
// a single projection transaction. The callback receives only already-loaded
// controller reads: it cannot reenter object loading or acquire locks in the
// opposite order. The order matches native writes (trees -> ACL -> storage).
func (s *Store) NativeReadSnapshot(ctx context.Context, ids []string, read func(crdt.NativeReadView) error) (err error) {
	return s.nativeReadSnapshot(ctx, ids, read, s.Generation)
}

// The generation reader is supplied only by compiled SDK routes. Ordinary
// snapshots retain their original initialization; a precreate descriptor read
// can require already-present metadata without minting a new epoch.
func (s *Store) nativeReadSnapshot(ctx context.Context, ids []string, read func(crdt.NativeReadView) error, readGeneration func(context.Context) (string, error)) (err error) {
	if read == nil || len(ids) > 1001 || s.signKey == nil {
		return errors.New("native snapshot: invalid dependencies")
	}
	generation, err := readGeneration(ctx)
	if err != nil {
		return err
	}
	handle, err := s.app.GetSpace(ctx, s.spaceId)
	if err != nil {
		return err
	}
	acl := handle.Inner().Acl()
	if acl == nil {
		return list.ErrInsufficientPermissions
	}
	objects := make(map[string]*object.Object)
	for _, id := range ids {
		if id == "" {
			return errors.New("native snapshot: empty dependency")
		}
		if objects[id] != nil {
			continue
		}
		o, err := s.Get(ctx, id)
		if err != nil {
			return err
		}
		objects[id] = o
	}
	if err := s.preloadNativeDefinitions(ctx, objects, nil, nil); err != nil {
		return err
	}
	order := make([]string, 0, len(objects))
	for id := range objects {
		order = append(order, id)
	}
	sort.Strings(order)
	locked := make([]*object.Object, 0, len(order))
	defer func() {
		for i := len(locked) - 1; i >= 0; i-- {
			locked[i].Tree().Unlock()
		}
	}()
	for _, id := range order {
		if err := ctx.Err(); err != nil {
			return err
		}
		o := objects[id]
		if o.Tree() == nil {
			return object.ErrTreeNotSet
		}
		o.Tree().Lock()
		locked = append(locked, o)
		if err := o.GuardReadyLocked(ctx); err != nil {
			return err
		}
	}
	acl.RLock()
	defer acl.RUnlock()
	permission := acl.AclState().Permissions(s.signKey.GetPublic())
	switch permission {
	case list.AclPermissionsReader, list.AclPermissionsWriter, list.AclPermissionsAdmin, list.AclPermissionsOwner:
	default:
		return list.ErrInsufficientPermissions
	}
	tx, err := s.db.ReadTx(ctx)
	if err != nil {
		return err
	}
	defer func() { err = errors.Join(err, tx.Commit()) }()
	stamp := crdt.NativeReadStamp{StoreGeneration: generation, TreeHeads: map[string][]string{}}
	if head := acl.Head(); head != nil {
		stamp.ACLHeadID = head.Id
	}
	for id, o := range objects {
		stamp.TreeHeads[id] = append([]string(nil), o.Tree().Heads()...)
		sort.Strings(stamp.TreeHeads[id])
	}
	// Immutable compiled-Type metadata needs only current Space ACL, not an
	// unrelated carrier tree. An empty dependency set cannot read object rows.
	var controller *crdt.Controller
	if len(order) > 0 {
		controller = objects[order[0]].Controller()
	}
	return read(snapshotReadView{lockedReadView: lockedReadView{ctx: tx.Context(), objects: objects, store: s}, controller: controller, canWrite: permission.CanWrite() && s.CheckWrite() == nil, stamp: stamp})
}

// Only the native read scope can see arbitrary object rows, all from the same
// transaction and Space. It cannot materialize a tree or mutate its projection.
type snapshotReadView struct {
	lockedReadView
	controller *crdt.Controller
	canWrite   bool
	stamp      crdt.NativeReadStamp
}

func (v snapshotReadView) SpaceObjects(filter any, limit int) ([]*anyenc.Value, error) {
	if v.controller == nil {
		return nil, crdt.ErrValidation
	}
	return v.controller.GuardSpaceObjects(v.ctx, filter, limit)
}
func (v snapshotReadView) CanWrite() bool                  { return v.canWrite }
func (v snapshotReadView) ReadStamp() crdt.NativeReadStamp { return v.stamp }

// Guarded canonical datasets are served only through NativeReadSnapshot.
// Generic queries, subscriptions and history cannot preserve current authority
// after returning an unrestricted collection, iterator or historical view.
func (s *Store) RequiresNativeDatasetRead(dataset string) bool {
	if s == nil {
		return false
	}
	for _, reg := range s.canonicalRegs {
		if reg.Name == dataset {
			_, guarded := reg.Handler.(crdt.GuardedHandler)
			return guarded
		}
	}
	return false
}

func (s *Store) RefuseNativeCarrierHistory(ctx context.Context, objectID string) error {
	if s == nil {
		return nil
	}
	var guards []crdt.GuardedHandler
	for _, reg := range s.canonicalRegs {
		if g, ok := reg.Handler.(crdt.GuardedHandler); ok {
			guards = append(guards, g)
		}
	}
	if len(guards) == 0 {
		return nil
	}
	obj, err := s.Get(ctx, objectID)
	if err != nil {
		return err
	}
	if obj.Tree() == nil {
		return object.ErrTreeNotSet
	}
	obj.Tree().Lock()
	defer obj.Tree().Unlock()
	if err := obj.GuardReadyLocked(ctx); err != nil {
		return err
	}
	if !obj.Tree().IsDerived() {
		return nil
	}
	info := obj.Tree().ChangeInfo()
	if info == nil {
		return nil
	}
	for _, g := range guards {
		if bytes.Equal(info.ChangePayload, g.GuardRootSeed()) {
			return crdt.ErrNativeReadRequired
		}
	}
	return nil
}
