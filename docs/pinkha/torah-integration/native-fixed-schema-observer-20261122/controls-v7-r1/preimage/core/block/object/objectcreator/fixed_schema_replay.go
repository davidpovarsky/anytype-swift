package objectcreator

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"slices"

	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/util/crypto"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/block/source/sourceimpl"
	"github.com/anyproto/anytype-heart/pb"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
)

func observeFixedSchemaSnapshot(ctx context.Context, scope fixedSchemaScope, definition FixedSchemaDefinition, expected, archiveRoot *treechangeproto.RawTreeChangeWithId) (read fixedSchemaRead, disposition FixedSchemaDisposition, err error) {
	disposition = FixedSchemaUnavailable
	read, err = readFixedSchemaSnapshot(ctx, scope, expected.Id, archiveRoot.Id)
	if err != nil {
		return read, disposition, err
	}
	// The owned native read transaction is already committed/released here.
	// Original ACL users can hold the ACL lock while waiting for a DB reader;
	// retaining our reader across any ACL lock would invert that ordering.
	if err = validateFixedSchemaSpace(ctx, scope, read.space, read.acl); err != nil {
		return read, disposition, err
	}
	if err = validateFixedSchemaACL(ctx, scope, read.acl); err != nil {
		return read, disposition, err
	}
	archiveState, archiveCount, err := replayFixedSchemaTree(ctx, scope, read.archive, archiveRoot, coresb.SmartBlockTypeArchive, "")
	if err != nil {
		return read, disposition, fmt.Errorf("read original archive: %w", err)
	}
	if archiveCount < 2 {
		return read, disposition, fmt.Errorf("%w: archive has no persisted initialization", ErrFixedSchemaStorage)
	}
	var archived bool
	err = archiveState.Iterate(func(block simple.Block) bool {
		if link := block.Model().GetLink(); link != nil && link.TargetBlockId == expected.Id {
			archived = true
		}
		return true
	})
	if err != nil {
		return read, disposition, fmt.Errorf("iterate original archive state: %w", err)
	}
	if archived || (read.schema.headPresent && read.schema.head.DeletedStatus != headstorage.DeletedStatusNotDeleted) {
		return read, FixedSchemaPopulatedConflict, nil
	}
	if !read.schema.headPresent && !read.schema.rootPresent && len(read.schema.rows) == 0 {
		return read, FixedSchemaLocallyMissing, nil
	}
	st, count, err := replayFixedSchemaTree(ctx, scope, read.schema, expected, definition.Key.SmartblockType(), definition.Key.InternalKey())
	if err != nil {
		return read, disposition, err
	}
	if count == 1 {
		return read, FixedSchemaRootOnlyIncomplete, nil
	}
	if !fixedSchemaObjectTypeMatches(definition.Key.SmartblockType(), st.ObjectTypeKeys()) ||
		!fixedSchemaDetailsMatch(st.Details(), definition.Required) {
		return read, FixedSchemaPopulatedConflict, nil
	}
	return read, FixedSchemaPersistedMatch, nil
}

func rereadFixedSchemaSnapshot(ctx context.Context, scope fixedSchemaScope, schemaID, archiveID string) (fixedSchemaRead, error) {
	return readFixedSchemaSnapshot(ctx, scope, schemaID, archiveID)
}

// Every real DB read and original row decoder runs through this one actual
// ReadTx context. The returned data owns only copied native values/raw rows.
func readFixedSchemaSnapshot(ctx context.Context, scope fixedSchemaScope, schemaID, archiveID string) (read fixedSchemaRead, err error) {
	snapshot, err := openFixedSchemaSnapshot(ctx, scope)
	if err != nil {
		return read, err
	}
	defer func() { err = errors.Join(err, snapshot.finish()) }()
	read.space, err = snapshot.readSpace()
	if err != nil {
		return read, err
	}
	read.acl, err = snapshot.readACL()
	if err != nil {
		return read, err
	}
	read.schema, err = snapshot.readTree(schemaID)
	if err != nil {
		return read, err
	}
	read.archive, err = snapshot.readTree(archiveID)
	return read, err
}

// replayFixedSchemaTree builds only private in-memory original native views.
// It never calls InitObject, migrations, cache.GetObject, AddContent, or Close on
// borrowed storage. The owned ReadTx has already closed; only copied original
// rows remain behind the immutable Storage adapter.
func replayFixedSchemaTree(ctx context.Context, scope fixedSchemaScope, stored fixedSchemaStoredTree, expected *treechangeproto.RawTreeChangeWithId, kind coresb.SmartBlockType, internalKey string) (*state.State, int, error) {
	if !stored.headPresent || !stored.rootPresent || len(stored.changes) == 0 || len(stored.changes) != len(stored.rows) {
		return nil, 0, fmt.Errorf("%w: root, heads, and full membership are required", ErrFixedSchemaStorage)
	}
	if stored.head.Id != expected.Id || stored.head.DeletedStatus != headstorage.DeletedStatusNotDeleted ||
		!stored.head.IsDerived || stored.head.ParentId != "" || stored.head.CommonSnapshot == "" ||
		!equalFixedSchemaHeads(stored.head.Heads, stored.head.Heads) {
		return nil, 0, fmt.Errorf("%w: malformed/deleted native head entry", ErrFixedSchemaStorage)
	}
	if stored.root.Id != expected.Id || !bytes.Equal(stored.root.RawChange, expected.RawChange) {
		return nil, 0, fmt.Errorf("%w: original derived header mismatch", ErrFixedSchemaStorage)
	}
	if _, exists := stored.rows[expected.Id]; !exists || stored.changes[0].Id != expected.Id {
		return nil, 0, fmt.Errorf("%w: root missing from complete tree membership", ErrFixedSchemaStorage)
	}
	actualKind, actualKey, err := typeprovider.GetTypeAndKeyFromRoot(stored.root)
	if err != nil {
		return nil, 0, err
	}
	if actualKind != kind || actualKey != internalKey {
		return nil, 0, fmt.Errorf("%w: native header kind/key", ErrFixedSchemaStorage)
	}
	storage := newFixedSchemaTreeStorage(ctx, stored)
	builder := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), stored.root)
	changes := make([]*objecttree.Change, 0, len(stored.changes))
	previousOrder := ""
	for _, persisted := range stored.changes {
		if err := ctx.Err(); err != nil {
			return nil, 0, err
		}
		change, err := builder.Unmarshall(persisted.RawTreeChangeWithId(), true)
		if err != nil {
			return nil, 0, fmt.Errorf("verify original persisted change: %w", err)
		}
		if persisted.OrderId <= previousOrder || change.Id != persisted.Id ||
			change.SnapshotId != persisted.SnapshotId || !sameFixedSchemaIDs(change.PreviousIds, persisted.PrevIds) ||
			(change.Id != expected.Id && (change.IsDerived || len(change.PreviousIds) == 0)) {
			return nil, 0, fmt.Errorf("%w: inconsistent original change metadata", ErrFixedSchemaStorage)
		}
		// Reconstruct through the original Tree with no persisted order/counter
		// supplied. Original CreateStorageTx seeds the native root counter at 1.
		if change.Id == expected.Id {
			change.SnapshotCounter = 1
		}
		previousOrder = persisted.OrderId
		changes = append(changes, change)
	}
	full := &objecttree.Tree{}
	full.AddFast(changes...)
	if full.RootId() != expected.Id || full.Len() != len(stored.rows) ||
		!equalFixedSchemaHeads(full.Heads(), stored.head.Heads) {
		return nil, 0, fmt.Errorf("%w: unattached, extra, or mismatched native membership", ErrFixedSchemaStorage)
	}
	for index, change := range changes {
		if full.Get(change.Id) != change {
			return nil, 0, fmt.Errorf("%w: discarded original change", ErrFixedSchemaStorage)
		}
		persisted := stored.changes[index]
		if change.Id == expected.Id {
			if persisted.SnapshotCounter != 1 {
				return nil, 0, fmt.Errorf("%w: original root snapshot counter", ErrFixedSchemaStorage)
			}
			continue
		}
		snapshot := full.Get(change.SnapshotId)
		if snapshot == nil || !snapshot.IsSnapshot ||
			(persisted.SnapshotCounter != change.SnapshotCounter && (change.IsSnapshot || persisted.SnapshotCounter != 0)) {
			return nil, 0, fmt.Errorf("%w: native snapshot reference/counter", ErrFixedSchemaStorage)
		}
	}
	// Native traversal establishes order. Absolute lex IDs can legitimately
	// differ after prior insertions; only the stored ordering must agree.
	orderIndex := 0
	var orderErr error
	full.IterateBranching(expected.Id, func(change *objecttree.Change, _ int) bool {
		if orderIndex >= len(stored.changes) || stored.changes[orderIndex].Id != change.Id {
			orderErr = fmt.Errorf("%w: stored order differs from original traversal", ErrFixedSchemaStorage)
			return false
		}
		orderIndex++
		return true
	})
	if orderErr != nil {
		return nil, 0, orderErr
	}
	if orderIndex != len(stored.changes) {
		return nil, 0, fmt.Errorf("%w: incomplete original traversal", ErrFixedSchemaStorage)
	}
	// Original validator's explicit contract requires its own ACL read lock.
	// Do not hold this lock around BuildObjectTree, which acquires it itself.
	err = validateFixedSchemaFullTree(scope.acl, full)
	if err != nil {
		return nil, 0, err
	}
	if err = validateFixedSchemaStoredContent(ctx, scope.acl, expected.Id, changes); err != nil {
		return nil, 0, err
	}
	if err = validateFixedSchemaCommonSnapshot(ctx, scope.acl, full, storage); err != nil {
		return nil, 0, err
	}
	original, err := objecttree.BuildObjectTree(storage, scope.acl)
	if err != nil {
		return nil, 0, fmt.Errorf("build original persisted tree: %w", err)
	}
	if original.Id() != expected.Id || !bytes.Equal(original.Header().RawChange, expected.RawChange) ||
		!equalFixedSchemaHeads(original.Heads(), stored.head.Heads) {
		return nil, 0, fmt.Errorf("%w: original replay view disagrees", ErrFixedSchemaStorage)
	}
	if len(stored.rows) == 1 && (stored.head.CommonSnapshot != expected.Id ||
		!equalFixedSchemaHeads(stored.head.Heads, []string{expected.Id}) || original.Len() != 1) {
		return nil, 0, fmt.Errorf("%w: not an exact root-only tree", ErrFixedSchemaStorage)
	}
	st, _, _, err := sourceimpl.BuildStateStrict(scope.spaceID, original)
	if err != nil {
		return nil, 0, fmt.Errorf("replay original persisted state: %w", err)
	}
	if st == nil || st.RootId() != expected.Id {
		return nil, 0, fmt.Errorf("%w: original state is unavailable", ErrFixedSchemaStorage)
	}
	if len(stored.rows) > 1 && (st.Pick(st.RootId()) == nil || st.Pick(st.RootId()).Model() == nil) {
		return nil, 0, fmt.Errorf("%w: populated original state has no root block", ErrFixedSchemaStorage)
	}
	return st, len(stored.rows), nil
}

// Use the exported original history builder's native common-snapshot selection,
// after complete raw membership, signatures, counters and traversal were checked.
// An older persisted replay base is valid only along that native signed snapshot
// chain. This does not regenerate graph IDs or invent another ancestor engine.
func validateFixedSchemaCommonSnapshot(ctx context.Context, acl list.AclList, full *objecttree.Tree, storage *fixedSchemaTreeStorage) error {
	history, err := objecttree.BuildHistoryTree(objecttree.HistoryTreeParams{
		Storage: storage, AclList: acl, Heads: slices.Clone(storage.heads), IncludeBeforeId: true,
	})
	if err != nil {
		return fmt.Errorf("select original common snapshot: %w", err)
	}
	if history == nil || history.Root() == nil || !equalFixedSchemaHeads(history.Heads(), storage.heads) {
		return fmt.Errorf("%w: native history membership", ErrFixedSchemaStorage)
	}
	latest := history.Root().Id
	// Original Tree.reduceTree makes a sole snapshot head the root directly.
	// BuildHistoryTree starts from its predecessor SnapshotId, so preserve this
	// documented original native case before checking allowed older ancestry.
	if len(storage.heads) == 1 {
		if head := full.Get(storage.heads[0]); head != nil && head.IsSnapshot {
			latest = head.Id
		}
	}
	for remaining := full.Len(); remaining > 0; remaining-- {
		if err := ctx.Err(); err != nil {
			return err
		}
		snapshot := full.Get(latest)
		if snapshot == nil || !snapshot.IsSnapshot {
			return fmt.Errorf("%w: native common snapshot path", ErrFixedSchemaStorage)
		}
		if snapshot.Id == storage.commonSnapshot {
			return nil
		}
		if snapshot.Id == full.RootId() {
			break
		}
		previous := full.Get(snapshot.SnapshotId)
		if previous == nil || !previous.IsSnapshot || previous.SnapshotCounter >= snapshot.SnapshotCounter {
			return fmt.Errorf("%w: invalid native snapshot ancestry", ErrFixedSchemaStorage)
		}
		latest = previous.Id
	}
	return fmt.Errorf("%w: persisted common snapshot is not an allowed native ancestor", ErrFixedSchemaStorage)
}

func validateFixedSchemaFullTree(acl list.AclList, tree *objecttree.Tree) error {
	acl.RLock()
	defer acl.RUnlock()
	return objecttree.NewTreeValidatorWithContentCheck(true, false, nil).ValidateFullTree(tree, acl)
}

func sameFixedSchemaIDs(a, b []string) bool {
	a, b = slices.Clone(a), slices.Clone(b)
	slices.Sort(a)
	slices.Sort(b)
	return slices.Equal(a, b)
}

// Decode every persisted non-root record through the original strict companion,
// including records older than CommonSnapshot. Current-state replay alone does
// not visit those rows. Native keys and decryption are the same as IterateFrom;
// no replacement protobuf, compression, or state codec is used.
func validateFixedSchemaStoredContent(ctx context.Context, acl list.AclList, rootID string, changes []*objecttree.Change) error {
	for _, change := range changes {
		if err := ctx.Err(); err != nil {
			return err
		}
		if change.Id == rootID {
			continue
		}
		data := change.Data
		if change.ReadKeyId != "" {
			acl.RLock()
			keys, found := acl.AclState().Keys()[change.ReadKeyId]
			acl.RUnlock()
			if !found || keys.ReadKey == nil {
				return list.ErrNoReadKey
			}
			var err error
			data, err = keys.ReadKey.DecryptReuse(nil, data)
			if err != nil {
				return fmt.Errorf("decrypt original stored content: %w", err)
			}
		}
		decoded, err := sourceimpl.UnmarshalChangeStrict(change, data)
		if err != nil {
			return fmt.Errorf("decode original stored content: %w", err)
		}
		model, ok := decoded.(*pb.Change)
		if !ok || model == nil || change.IsSnapshot != (model.Snapshot != nil) {
			return fmt.Errorf("%w: original snapshot content marker", ErrFixedSchemaStorage)
		}
	}
	return nil
}
