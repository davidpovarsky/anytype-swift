package objectcreator

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"slices"
	"strings"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-store/query"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/any-sync/commonspace/headsync/statestorage"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
)

// This owns only tx. OpenCollection and original NewStorage borrow collections;
// neither a collection nor a native storage handle is retained after finish.
// No ACL lock or ACL-dependent builder may run while this read transaction lives.
type fixedSchemaSnapshot struct {
	ctx     context.Context
	tx      anystore.ReadTx
	scope   fixedSchemaScope
	changes anystore.Collection
	heads   anystore.Collection
}

func openFixedSchemaSnapshot(ctx context.Context, scope fixedSchemaScope) (_ *fixedSchemaSnapshot, err error) {
	tx, err := scope.storage.AnyStore().ReadTx(ctx)
	if err != nil {
		return nil, err
	}
	snapshot := &fixedSchemaSnapshot{ctx: tx.Context(), tx: tx, scope: scope}
	defer func() {
		if err != nil {
			err = errors.Join(err, snapshot.finish())
		}
	}()
	snapshot.changes, err = scope.storage.AnyStore().OpenCollection(snapshot.ctx, objecttree.CollName)
	if err != nil {
		return nil, err
	}
	snapshot.heads, err = scope.storage.AnyStore().OpenCollection(snapshot.ctx, headstorage.HeadsCollectionName)
	if err != nil {
		return nil, err
	}
	return snapshot, nil
}

func (s *fixedSchemaSnapshot) finish() error {
	if s.tx == nil {
		return nil
	}
	tx := s.tx
	s.tx = nil
	s.changes, s.heads = nil, nil
	return tx.Commit()
}

// The state decoder and full encoded row are read from the same real ReadTx.
// The settings ID comes from the retained original StateStorage, not the row
// being compared. Its actual persisted root is additionally bound to the signed
// Space header by the original payload validator, after releasing this reader.
type fixedSchemaStoredSpace struct {
	state             statestorage.State
	stateBytes        []byte
	settingsRoot      *treechangeproto.RawTreeChangeWithId
	settingsRootBytes []byte
}

func (s fixedSchemaStoredSpace) same(other fixedSchemaStoredSpace) bool {
	return bytes.Equal(s.stateBytes, other.stateBytes) &&
		bytes.Equal(s.settingsRootBytes, other.settingsRootBytes)
}

func (s *fixedSchemaSnapshot) readSpace() (result fixedSchemaStoredSpace, err error) {
	if err = s.ctx.Err(); err != nil {
		return result, err
	}
	// Do not construct statestorage.New: that path can create a collection.
	state, err := s.scope.stateStorage.GetState(s.ctx)
	if err != nil {
		return result, err
	}
	if state.SpaceId != s.scope.spaceID || state.AclId != s.scope.aclID ||
		state.SettingsId != s.scope.settingsID || len(state.SpaceHeader) == 0 {
		return result, fmt.Errorf("%w: persisted native Space metadata", ErrFixedSchemaStorage)
	}
	state.SpaceId, state.AclId, state.SettingsId = strings.Clone(state.SpaceId), strings.Clone(state.AclId), strings.Clone(state.SettingsId)
	state.NewHash, state.SpaceHeader = strings.Clone(state.NewHash), slices.Clone(state.SpaceHeader)
	// These are the exact original private statestorage field names. Require
	// their native types as well as the original decoder's values; absent/wrong
	// fields must not be accepted through GetString/GetBytes defaulting.
	coll, err := s.scope.storage.AnyStore().OpenCollection(s.ctx, "state")
	if err != nil {
		return result, err
	}
	doc, err := coll.FindId(s.ctx, s.scope.spaceID)
	if err != nil {
		return result, err
	}
	value := doc.Value()
	if value.Get("id").Type() != anyenc.TypeString || value.GetString("id") != state.SpaceId ||
		value.Get("a").Type() != anyenc.TypeString || value.GetString("a") != state.AclId ||
		value.Get("s").Type() != anyenc.TypeString || value.GetString("s") != state.SettingsId ||
		value.Get("e").Type() != anyenc.TypeBinary || !bytes.Equal(value.GetBytes("e"), state.SpaceHeader) {
		return result, fmt.Errorf("%w: native state row types or projection", ErrFixedSchemaStorage)
	}
	result.state, result.stateBytes = state, value.MarshalTo(nil)
	root, err := s.scope.storage.TreeRoot(s.ctx, s.scope.settingsID)
	if err != nil {
		return result, err
	}
	if root == nil || root.Id != s.scope.settingsID || len(root.RawChange) == 0 {
		return result, fmt.Errorf("%w: original settings root identity", ErrFixedSchemaStorage)
	}
	result.settingsRoot = &treechangeproto.RawTreeChangeWithId{Id: strings.Clone(root.Id), RawChange: slices.Clone(root.RawChange)}
	doc, err = s.changes.FindId(s.ctx, s.scope.settingsID)
	if err != nil {
		return result, err
	}
	value = doc.Value()
	if value.GetString("id") != s.scope.settingsID || value.GetString(objecttree.TreeKey) != s.scope.settingsID {
		return result, fmt.Errorf("%w: original settings root row", ErrFixedSchemaStorage)
	}
	result.settingsRootBytes = value.MarshalTo(nil)
	return result, nil
}

type fixedSchemaStoredTree struct {
	head        headstorage.HeadsEntry
	headPresent bool
	headBytes   []byte
	rootPresent bool
	root        *treechangeproto.RawTreeChangeWithId
	rootBytes   []byte
	rows        map[string][]byte
	changes     []objecttree.StorageChange
}

func (t fixedSchemaStoredTree) same(other fixedSchemaStoredTree) bool {
	return t.headPresent == other.headPresent && t.rootPresent == other.rootPresent &&
		bytes.Equal(t.headBytes, other.headBytes) && bytes.Equal(t.rootBytes, other.rootBytes) &&
		equalFixedSchemaRows(t.rows, other.rows)
}

type fixedSchemaStoredACL struct {
	headBytes []byte
	root      []byte
	rows      map[string][]byte
	records   []list.StorageRecord
}

func (a fixedSchemaStoredACL) same(other fixedSchemaStoredACL) bool {
	return bytes.Equal(a.headBytes, other.headBytes) && bytes.Equal(a.root, other.root) &&
		equalFixedSchemaRows(a.rows, other.rows)
}

func (s *fixedSchemaSnapshot) readACL() (result fixedSchemaStoredACL, err error) {
	if err = s.ctx.Err(); err != nil {
		return result, err
	}
	// AclStorage returns the retained native handle. Do not call list.NewStorage:
	// its original implementation can create a collection/index.
	native, err := s.scope.storage.AclStorage()
	if err != nil {
		return result, err
	}
	if native == nil || native.Id() != s.scope.aclID {
		return result, fmt.Errorf("%w: persisted ACL scope", ErrFixedSchemaStorage)
	}
	entry, err := s.scope.storage.HeadStorage().GetEntry(s.ctx, s.scope.aclID)
	if err != nil {
		return result, err
	}
	if entry.Id != s.scope.aclID || len(entry.Heads) != 1 || entry.Heads[0] != s.scope.aclHead ||
		entry.DeletedStatus != headstorage.DeletedStatusNotDeleted {
		return result, ErrFixedSchemaChanged
	}
	doc, err := s.heads.FindId(s.ctx, s.scope.aclID)
	if err != nil {
		return result, err
	}
	result.headBytes = doc.Value().MarshalTo(nil)
	records, err := s.scope.storage.AnyStore().OpenCollection(s.ctx, s.scope.aclID)
	if err != nil {
		return result, err
	}
	result.rows = make(map[string][]byte)
	// Full enumeration has no o>=1 predicate: extra/malformed rows must remain
	// visible. Use original Storage.Get decoding and check every iterator error.
	err = scanFixedSchemaRows(s.ctx, records.Find(nil).Sort("o"), func(doc anystore.Doc) error {
		value := doc.Value()
		id := value.GetString("id")
		if id == "" {
			return fmt.Errorf("%w: ACL row identity", ErrFixedSchemaStorage)
		}
		if _, duplicate := result.rows[id]; duplicate {
			return fmt.Errorf("%w: duplicate ACL row", ErrFixedSchemaStorage)
		}
		record, readErr := native.Get(s.ctx, id)
		if readErr != nil {
			return readErr
		}
		index := len(result.records)
		if index >= len(s.scope.aclRecords) || record.Id != id ||
			record.Id != s.scope.aclRecords[index].id || record.PrevId != s.scope.aclRecords[index].previousID ||
			record.Order != index+1 || len(record.RawRecord) == 0 || record.ChangeSize != len(record.RawRecord) ||
			value.Get("p").Type() != anyenc.TypeString {
			return fmt.Errorf("%w: complete persisted ACL chain", ErrFixedSchemaStorage)
		}
		if err := requireFixedSchemaInteger(value, "o", record.Order); err != nil {
			return err
		}
		if err := requireFixedSchemaInteger(value, "sz", record.ChangeSize); err != nil {
			return err
		}
		record.Id, record.PrevId = strings.Clone(record.Id), strings.Clone(record.PrevId)
		record.RawRecord = slices.Clone(record.RawRecord)
		result.rows[record.Id] = value.MarshalTo(nil)
		result.records = append(result.records, record)
		return nil
	})
	if err != nil {
		return result, err
	}
	if len(result.records) == 0 || len(result.records) != len(s.scope.aclRecords) ||
		result.records[0].Id != s.scope.aclID || !bytes.Equal(result.records[0].RawRecord, s.scope.aclRoot) {
		return result, fmt.Errorf("%w: missing persisted ACL record or root", ErrFixedSchemaStorage)
	}
	result.root = slices.Clone(result.records[0].RawRecord)
	return result, nil
}

func (s *fixedSchemaSnapshot) readTree(id string) (tree fixedSchemaStoredTree, err error) {
	tree.rows = make(map[string][]byte)
	if err = s.ctx.Err(); err != nil {
		return tree, err
	}
	tree.head, err = s.scope.storage.HeadStorage().GetEntry(s.ctx, id)
	switch {
	case err == nil:
		tree.headPresent = true
		tree.head.Id, tree.head.CommonSnapshot, tree.head.ParentId = strings.Clone(tree.head.Id), strings.Clone(tree.head.CommonSnapshot), strings.Clone(tree.head.ParentId)
		tree.head.Heads = slices.Clone(tree.head.Heads)
		for i := range tree.head.Heads {
			tree.head.Heads[i] = strings.Clone(tree.head.Heads[i])
		}
		doc, readErr := s.heads.FindId(s.ctx, id)
		if readErr != nil {
			return tree, readErr
		}
		tree.headBytes = doc.Value().MarshalTo(nil)
	case errors.Is(err, anystore.ErrDocNotFound):
		err = nil
	default:
		return tree, err
	}
	tree.root, err = s.scope.storage.TreeRoot(s.ctx, id)
	switch {
	case err == nil:
		if tree.root == nil {
			return tree, fmt.Errorf("%w: nil original root on successful read", ErrFixedSchemaStorage)
		}
		tree.rootPresent = true
		tree.root = &treechangeproto.RawTreeChangeWithId{Id: strings.Clone(tree.root.Id), RawChange: slices.Clone(tree.root.RawChange)}
		doc, readErr := s.changes.FindId(s.ctx, id)
		if readErr != nil {
			return tree, readErr
		}
		tree.rootBytes = doc.Value().MarshalTo(nil)
	case errors.Is(err, anystore.ErrDocNotFound):
		err = nil
	default:
		return tree, err
	}
	var native objecttree.Storage
	if tree.headPresent && tree.rootPresent {
		// The original NewStorage uses OpenCollection and reads its root. It does
		// not create/initialize the tree. Never call Close on its borrowed handle.
		native, err = objecttree.NewStorage(s.ctx, id, s.scope.storage.HeadStorage(), s.scope.storage.AnyStore())
		if err != nil {
			return tree, err
		}
	}
	filter := query.Key{Path: []string{objecttree.TreeKey}, Filter: query.NewComp(query.CompOpEq, id)}
	err = scanFixedSchemaRows(s.ctx, s.changes.Find(filter).Sort(objecttree.OrderKey), func(doc anystore.Doc) error {
		value := doc.Value()
		recordID := value.GetString("id")
		if recordID == "" || value.GetString(objecttree.TreeKey) != id {
			return fmt.Errorf("%w: persisted row identity", ErrFixedSchemaStorage)
		}
		if _, duplicate := tree.rows[recordID]; duplicate {
			return fmt.Errorf("%w: duplicate persisted row", ErrFixedSchemaStorage)
		}
		tree.rows[strings.Clone(recordID)] = value.MarshalTo(nil)
		if native == nil {
			return nil // Complete raw rows still disprove absence/root-only.
		}
		change, readErr := native.Get(s.ctx, recordID)
		if readErr != nil {
			return readErr
		}
		if change.Id != recordID || change.OrderId == "" || len(change.RawChange) == 0 ||
			change.ChangeSize != len(change.RawChange) || value.Get("i").Type() != anyenc.TypeString {
			return fmt.Errorf("%w: incomplete native change row", ErrFixedSchemaStorage)
		}
		if err := requireFixedSchemaInteger(value, objecttree.ChangeSizeKey, change.ChangeSize); err != nil {
			return err
		}
		// Native local AddContent persists zero for ordinary non-snapshots.
		// Actual counter/graph consistency is checked after original reconstruction.
		if err := requireFixedSchemaInteger(value, objecttree.SnapshotCounterKey, change.SnapshotCounter); err != nil {
			return err
		}
		if value.Get(objecttree.AddSeqKey) != nil {
			if err := requireFixedSchemaInteger(value, objecttree.AddSeqKey, value.GetInt(objecttree.AddSeqKey)); err != nil {
				return err
			}
		}
		if previous := value.Get("p"); previous != nil {
			items, readErr := previous.Array()
			if readErr != nil {
				return readErr
			}
			for _, item := range items {
				if item.Type() != anyenc.TypeString {
					return fmt.Errorf("%w: non-string previous change", ErrFixedSchemaStorage)
				}
			}
		}
		tree.changes = append(tree.changes, cloneFixedSchemaStorageChange(change))
		return nil
	})
	return tree, err
}

// The original row decoder uses GetInt (which can default/truncate). Require
// presence, exact number type, and a nonnegative exact integer projection.
func requireFixedSchemaInteger(value *anyenc.Value, key string, decoded int) error {
	number, err := value.Get(key).Float64()
	if err != nil {
		return fmt.Errorf("%w: numeric native field %s: %w", ErrFixedSchemaStorage, key, err)
	}
	if decoded < 0 || number != float64(decoded) {
		return fmt.Errorf("%w: non-integral native field %s", ErrFixedSchemaStorage, key)
	}
	return nil
}

func scanFixedSchemaRows(ctx context.Context, qry anystore.Query, visit func(anystore.Doc) error) (err error) {
	iter, err := qry.Iter(ctx)
	if err != nil {
		return err
	}
	defer func() { err = errors.Join(err, iter.Err(), iter.Close()) }()
	for iter.Next() {
		if err = ctx.Err(); err != nil {
			return err
		}
		doc, readErr := iter.Doc()
		if readErr != nil {
			return readErr
		}
		if err = visit(doc); err != nil {
			return err
		}
	}
	return nil
}

func cloneFixedSchemaStorageChange(change objecttree.StorageChange) objecttree.StorageChange {
	change.Id, change.OrderId, change.SnapshotId = strings.Clone(change.Id), strings.Clone(change.OrderId), strings.Clone(change.SnapshotId)
	change.RawChange = slices.Clone(change.RawChange)
	change.PrevIds = slices.Clone(change.PrevIds)
	for i := range change.PrevIds {
		change.PrevIds[i] = strings.Clone(change.PrevIds[i])
	}
	return change
}

// This is an immutable projection of original decoded rows, not another database,
// codec, or state engine. It retains no native store/collection/transaction handle.
// Original builders sometimes pass Background; every read still checks ctx.
type fixedSchemaTreeStorage struct {
	ctx            context.Context
	id             string
	heads          []string
	commonSnapshot string
	changes        []objecttree.StorageChange
	byID           map[string]objecttree.StorageChange
}

var _ objecttree.Storage = (*fixedSchemaTreeStorage)(nil)

func newFixedSchemaTreeStorage(ctx context.Context, stored fixedSchemaStoredTree) *fixedSchemaTreeStorage {
	storage := &fixedSchemaTreeStorage{ctx: ctx, id: stored.head.Id, heads: slices.Clone(stored.head.Heads),
		commonSnapshot: strings.Clone(stored.head.CommonSnapshot), byID: make(map[string]objecttree.StorageChange, len(stored.changes))}
	for _, change := range stored.changes {
		copy := cloneFixedSchemaStorageChange(change)
		storage.changes = append(storage.changes, copy)
		storage.byID[copy.Id] = copy
	}
	return storage
}

func (s *fixedSchemaTreeStorage) Id() string { return s.id }
func (s *fixedSchemaTreeStorage) Root(context.Context) (objecttree.StorageChange, error) {
	return s.Get(s.ctx, s.id)
}
func (s *fixedSchemaTreeStorage) Heads(context.Context) ([]string, error) {
	if err := s.ctx.Err(); err != nil {
		return nil, err
	}
	return slices.Clone(s.heads), nil
}
func (s *fixedSchemaTreeStorage) CommonSnapshot(context.Context) (string, error) {
	return s.commonSnapshot, s.ctx.Err()
}
func (s *fixedSchemaTreeStorage) Has(_ context.Context, id string) (bool, error) {
	_, err := s.Get(s.ctx, id)
	if errors.Is(err, anystore.ErrDocNotFound) {
		return false, nil
	}
	return err == nil, err
}
func (s *fixedSchemaTreeStorage) Get(_ context.Context, id string) (objecttree.StorageChange, error) {
	if err := s.ctx.Err(); err != nil {
		return objecttree.StorageChange{}, err
	}
	change, found := s.byID[id]
	if !found {
		return objecttree.StorageChange{}, anystore.ErrDocNotFound
	}
	return cloneFixedSchemaStorageChange(change), nil
}
func (s *fixedSchemaTreeStorage) iterate(selectRow func(objecttree.StorageChange) bool, visit objecttree.StorageIterator) error {
	for _, change := range s.changes {
		if err := s.ctx.Err(); err != nil {
			return err
		}
		if !selectRow(change) {
			continue
		}
		keepGoing, err := visit(s.ctx, cloneFixedSchemaStorageChange(change))
		if err != nil {
			return err
		}
		if !keepGoing {
			return nil
		}
	}
	return s.ctx.Err()
}
func (s *fixedSchemaTreeStorage) GetAfterOrder(_ context.Context, order string, visit objecttree.StorageIterator) error {
	return s.iterate(func(change objecttree.StorageChange) bool { return change.OrderId >= order }, visit)
}
func (s *fixedSchemaTreeStorage) GetAfterAddSeq(_ context.Context, seq uint64, visit objecttree.StorageIterator) error {
	// Original GetAfterAddSeq also sorts by OrderKey, not AddSeq.
	return s.iterate(func(change objecttree.StorageChange) bool { return change.AddSeq > seq }, visit)
}
func (*fixedSchemaTreeStorage) AddAll(context.Context, []objecttree.StorageChange, []string, string) error {
	return ErrFixedSchemaReadOnly
}
func (*fixedSchemaTreeStorage) AddAllNoError(context.Context, []objecttree.StorageChange, []string, string) error {
	return ErrFixedSchemaReadOnly
}
func (*fixedSchemaTreeStorage) Delete(context.Context) error { return ErrFixedSchemaReadOnly }
func (*fixedSchemaTreeStorage) Close() error                 { return ErrFixedSchemaReadOnly }
