package object

import (
	"bytes"
	"context"
	"slices"
	"strings"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-store/v2/anyenc/anyencutil"
	"github.com/anyproto/any-sync-sdk/internal/commitguard"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
)

type migrationContextKey struct{}
type preparedOperation struct {
	entry          *migrationintent.Prepared
	journal        *migrationintent.Store
	commit         bool
	definition     bool
	propertyUpdate bool
	outcome        string
}

func migrationOperation(ctx context.Context) *preparedOperation {
	op, _ := ctx.Value(migrationContextKey{}).(*preparedOperation)
	return op
}

func (o *Object) PrepareMigration(ctx context.Context, change crdt.Change, entry *migrationintent.Prepared, journal *migrationintent.Store) (*migrationintent.Prepared, error) {
	if entry == nil || journal == nil || !change.NativeObjectPolicy || change.NativeDefinitionPolicy != "" || len(change.Records) != 1 || !change.Records[0].Upsert {
		return nil, crdt.ErrValidation
	}
	op := &preparedOperation{entry: entry, journal: journal}
	_, err := o.localWriteIf(context.WithValue(ctx, migrationContextKey{}, op), change, nil, nil, true)
	if err != nil {
		return nil, err
	}
	if op.entry.ChangeID == "" || len(op.entry.Raw) == 0 {
		return nil, migrationintent.ErrCorrupt
	}
	return op.entry, nil
}

func (o *Object) CommitMigration(ctx context.Context, change crdt.Change, entry *migrationintent.Prepared) (WriteResult, string, error) {
	if entry == nil || !change.NativeObjectPolicy || change.NativeDefinitionPolicy != "" || len(change.Records) != 1 {
		return WriteResult{}, "", crdt.ErrValidation
	}
	op := &preparedOperation{entry: entry, commit: true}
	change.Timestamp = entry.Timestamp
	result, err := o.localWriteIf(context.WithValue(ctx, migrationContextKey{}, op), change, nil, nil, true)
	return result, op.outcome, err
}

type preparedDependencyView interface{ PreparedHeads() map[string][]string }

func (o *Object) preparedWriteLocked(ctx context.Context, ch crdt.Change, payload []byte, view crdt.LocalReadView, op *preparedOperation) (WriteResult, error) {
	if op.definition && op.entry.Kind == migrationintent.PartDefinition {
		return o.preparedPartWriteLocked(ctx, ch, payload, view, op)
	}
	if o.signKey == nil || o.plaintextSpecFor(o.tree) != nil {
		return WriteResult{}, commitguard.ErrNativeCommitGuard
	}
	fence, ok := view.(preparedDependencyView)
	if !ok {
		return WriteResult{}, commitguard.ErrNativeCommitGuard
	}
	heads := fence.PreparedHeads()
	if err := o.checkPreparedParent(ctx, ch); err != nil {
		return WriteResult{}, err
	}
	if op.commit {
		if !sameDependencyHeads(heads, op.entry.Dependencies) || !bytes.Equal(payload, op.entry.Payload) {
			op.outcome = "obsolete"
			return WriteResult{}, migrationintent.ErrObsolete
		}
		raw := &treechangeproto.RawTreeChangeWithId{Id: op.entry.ChangeID, RawChange: bytes.Clone(op.entry.Raw)}
		appendCtx, _, err := commitguard.PreparedContext(ctx, o.tree, o.signKey.GetPublic(), raw)
		if err != nil {
			op.outcome = "obsolete"
			return WriteResult{}, err
		}
		_, err = o.tree.AddRawChanges(appendCtx, objecttree.RawChangesPayload{NewHeads: []string{raw.Id}, RawChanges: []*treechangeproto.RawTreeChangeWithId{raw}})
		if err != nil {
			// Native append may have committed before a later callback failed.
			// Mark the gap and reconcile the same CID on the next request.
			o.setApplyGap(true)
			return WriteResult{}, err
		}
		// Production SyncTree's deferred listener normally already replayed.
		// A direct wrapped native tree has no listener, so explicitly catch up
		// from durable storage. The max AddSeq makes this idempotent.
		if err := o.replayLocked(context.WithoutCancel(ctx), o.tree); err != nil {
			o.setApplyGap(true)
			return WriteResult{}, err
		}
		result, found, err := o.reconcilePreparedLocked(ctx, op)
		if !found && err == nil {
			err = migrationintent.ErrCorrupt
		}
		return result, err
	}
	if err := commitguard.CheckCurrentWrite(ctx, o.tree, o.signKey.GetPublic()); err != nil {
		return WriteResult{}, err
	}
	if op.entry.Stage == "bootstrap" {
		for id, original := range op.entry.Dependencies {
			if !slices.Equal(original, heads[id]) {
				return WriteResult{}, migrationintent.ErrObsolete
			}
		}
	}
	raw, err := o.tree.PrepareChange(objecttree.SignableChangeContent{Data: payload, Key: o.signKey, ShouldBeEncrypted: true, DataType: ch.Dataset, Timestamp: ch.Timestamp})
	if err != nil {
		return WriteResult{}, err
	}
	if err := commitguard.CheckPreparedPayload(ctx, o.tree, o.signKey.GetPublic(), raw, payload, ch.Dataset, ch.Timestamp); err != nil {
		return WriteResult{}, err
	}
	ch.ChangeId = raw.Id
	ids, err := crdt.ResolveRecordIds(ch)
	if err != nil || len(ids) != 1 {
		return WriteResult{}, crdt.ErrValidation
	}
	// The route only creates records. Even a pre-existing auto-ID collision
	// refuses; it never turns a migration create into an overwrite.
	row, err := o.ctrl.GuardLookup(ctx, ch.Dataset, ids[0])
	if err != nil {
		return WriteResult{}, err
	}
	if op.propertyUpdate {
		if row == nil || row.Get(crdt.DeletedAtField) != nil {
			return WriteResult{}, crdt.ErrPreconditionFailed
		}
	} else if row != nil {
		return WriteResult{}, migrationintent.ErrCollision
	}
	entry := *op.entry
	entry.ObjectID, entry.ChangeID, entry.Raw = o.tree.Id(), raw.Id, bytes.Clone(raw.RawChange)
	entry.Payload, entry.Timestamp, entry.RecordIDs, entry.Dependencies = bytes.Clone(payload), ch.Timestamp, ids, heads
	var reserved *migrationintent.Prepared
	if op.propertyUpdate {
		reserved, err = op.journal.ReservePropertyUpdate(ctx, &entry)
	} else if op.definition {
		reserved, err = op.journal.ReserveDefinition(ctx, &entry)
	} else {
		reserved, err = op.journal.Reserve(ctx, &entry)
	}
	if err != nil {
		return WriteResult{}, err
	}
	op.entry = reserved
	return WriteResult{ChangeId: reserved.ChangeID, RecordIds: slices.Clone(reserved.RecordIDs)}, nil
}

func (o *Object) preparedFenceLocked(ctx context.Context, view crdt.LocalReadView, op *preparedOperation) error {
	fence, ok := view.(preparedDependencyView)
	if !ok {
		return commitguard.ErrNativeCommitGuard
	}
	if !sameDependencyHeads(fence.PreparedHeads(), op.entry.Dependencies) {
		op.outcome = "obsolete"
		return migrationintent.ErrObsolete
	}
	_, _, err := commitguard.PreparedContext(ctx, o.tree, o.signKey.GetPublic(), &treechangeproto.RawTreeChangeWithId{Id: op.entry.ChangeID, RawChange: op.entry.Raw})
	if err != nil {
		op.outcome = "obsolete"
		return err
	}
	return nil
}

func (o *Object) checkPreparedPayloadLocked(ctx context.Context, entry *migrationintent.Prepared) error {
	decoded, err := NewCodec().Decode(entry.Payload)
	if err != nil {
		return migrationintent.ErrCorrupt
	}
	return commitguard.CheckPreparedPayload(ctx, o.tree, o.signKey.GetPublic(), &treechangeproto.RawTreeChangeWithId{Id: entry.ChangeID, RawChange: entry.Raw}, entry.Payload, decoded.Dataset, entry.Timestamp)
}

func (o *Object) checkPreparedParent(ctx context.Context, ch crdt.Change) error {
	if ch.Dataset != "editor_blocks" {
		return nil
	}
	if len(ch.Records) != 1 || len(ch.Records[0].Ops) != 1 {
		return crdt.ErrValidation
	}
	op := ch.Records[0].Ops[0]
	if op.Type != crdt.OpSet || len(op.Path) != 0 || op.Payload == nil {
		return crdt.ErrValidation
	}
	parent := op.Payload.GetString("nav", "parentId")
	if parent == "" {
		return nil
	}
	row, err := o.ctrl.GuardLookup(ctx, ch.Dataset, parent)
	if err != nil {
		return err
	}
	if row == nil || row.Get(crdt.DeletedAtField) != nil {
		return crdt.ErrPreconditionFailed
	}
	return nil
}

func sameDependencyHeads(a, b map[string][]string) bool {
	if len(a) != len(b) {
		return false
	}
	for id, heads := range a {
		other, ok := b[id]
		if !ok {
			return false
		}
		left, right := slices.Clone(heads), slices.Clone(other)
		slices.Sort(left)
		slices.Sort(right)
		if !slices.Equal(left, right) {
			return false
		}
	}
	return true
}

func (o *Object) reconcilePreparedLocked(ctx context.Context, op *preparedOperation) (WriteResult, bool, error) {
	if op.entry.Kind == migrationintent.PropertyUpdate {
		return o.reconcilePreparedPropertyUpdateLocked(ctx, op)
	}
	if op.entry.Kind == migrationintent.PartDefinition {
		return o.reconcilePreparedPartLocked(ctx, op)
	}
	entry := op.entry
	if entry.ObjectID != o.tree.Id() || o.signKey == nil {
		return WriteResult{}, false, migrationintent.ErrScope
	}
	if err := commitguard.CheckCurrentWrite(ctx, o.tree, o.signKey.GetPublic()); err != nil {
		return WriteResult{}, false, err
	}
	if err := o.checkPreparedPayloadLocked(ctx, entry); err != nil {
		return WriteResult{}, false, err
	}
	found, err := o.tree.Storage().Has(ctx, entry.ChangeID)
	if err != nil || !found {
		return WriteResult{}, false, err
	}
	stored, err := o.tree.Storage().Get(ctx, entry.ChangeID)
	if err != nil {
		return WriteResult{}, true, err
	}
	if stored.Id != entry.ChangeID || !bytes.Equal(stored.RawChange, entry.Raw) || stored.AddSeq == 0 {
		return WriteResult{}, true, migrationintent.ErrCorrupt
	}
	decoded, err := o.codec.Decode(entry.Payload)
	if err != nil {
		return WriteResult{}, true, err
	}
	decoded.ChangeId = stored.Id
	ids, err := crdt.ResolveRecordIds(decoded)
	if err != nil || len(ids) != 1 || !slices.Equal(ids, entry.RecordIDs) {
		return WriteResult{}, true, migrationintent.ErrCorrupt
	}
	row, err := o.ctrl.GuardLookup(ctx, decoded.Dataset, ids[0])
	if err != nil {
		return WriteResult{}, true, err
	}
	op.outcome = "committed"
	if row == nil || row.Get(crdt.DeletedAtField) != nil {
		op.outcome = "committed_deleted"
	} else if crdt.GetRecordVersion(row, "id") != crdt.VersionId(stored.OrderId) || !preparedSetsMatch(row, decoded.Records[0].Ops) ||
		(decoded.Dataset == "objects" && !preparedSetVersionsMatch(row, decoded.Records[0].Ops, crdt.VersionId(stored.OrderId))) ||
		(decoded.Dataset != "objects" && (row.GetInt(crdt.AddSeqField) <= 0 || uint64(row.GetInt(crdt.AddSeqField)) != stored.AddSeq)) {
		// AddSeq is actual local native-delivery metadata, not a host receipt.
		// It advances for commutative edits too, whose _ver need not change.
		op.outcome = "committed_modified"
	}
	if op.outcome == "committed" && o.checkPreparedParent(ctx, decoded) != nil {
		op.outcome = "committed_modified"
	}
	return WriteResult{ChangeId: stored.Id, VersionId: crdt.VersionId(stored.OrderId), RecordIds: ids}, true, nil
}

func preparedSetVersionsMatch(row *anyenc.Value, ops []crdt.Op, version crdt.VersionId) bool {
	for _, op := range ops {
		if len(op.Path) != 0 {
			if crdt.GetRecordVersion(row, op.Path...) != version {
				return false
			}
			continue
		}
		fields, err := op.Payload.Object()
		if err != nil {
			return false
		}
		ok := true
		fields.Visit(func(key []byte, _ *anyenc.Value) {
			if crdt.GetRecordVersion(row, strings.Split(string(key), ".")...) != version {
				ok = false
			}
		})
		if !ok {
			return false
		}
	}
	return true
}

func preparedSetsMatch(row *anyenc.Value, ops []crdt.Op) bool {
	for _, op := range ops {
		if op.Type != crdt.OpSet || op.Payload == nil {
			return false
		}
		if len(op.Path) != 0 {
			if !anyencutil.Equal(row.Get(op.Path...), op.Payload) {
				return false
			}
			continue
		}
		fields, err := op.Payload.Object()
		if err != nil {
			return false
		}
		ok := true
		fields.Visit(func(key []byte, value *anyenc.Value) {
			if !anyencutil.Equal(row.Get(strings.Split(string(key), ".")...), value) {
				ok = false
			}
		})
		if !ok {
			return false
		}
	}
	return true
}

// Status never appends. Its native read checks the same actual writer account
// as commit, and a materialization gap must be repaired before reporting state.
func (o *Object) MigrationStatus(ctx context.Context, entry *migrationintent.Prepared) (WriteResult, string, error) {
	return o.migrationStatus(ctx, entry, false)
}

func (o *Object) migrationStatus(ctx context.Context, entry *migrationintent.Prepared, definition bool) (WriteResult, string, error) {
	if o.tree == nil {
		return WriteResult{}, "", ErrTreeNotSet
	}
	change, err := NewCodec().Decode(entry.Payload)
	if err != nil {
		return WriteResult{}, "", err
	}
	if definition {
		change.NativeDefinitionPolicy = entry.Kind
	} else {
		change.NativeObjectPolicy = true
	}
	for id := range entry.Dependencies {
		if id != o.tree.Id() {
			change.NativeDefinitionOwners = append(change.NativeDefinitionOwners, id)
		}
	}
	if o.lockLocalWrite == nil {
		return WriteResult{}, "", commitguard.ErrNativeCommitGuard
	}
	view, unlock, err := o.lockLocalWrite(ctx, o, &change)
	if err != nil {
		return WriteResult{}, "", err
	}
	defer unlock()
	if err := o.GuardReadyLocked(ctx); err != nil {
		return WriteResult{}, "", err
	}
	op := &preparedOperation{entry: entry, commit: true}
	result, found, err := o.reconcilePreparedLocked(ctx, op)
	if err != nil {
		return result, "", err
	}
	if found {
		return result, op.outcome, nil
	}
	if err := o.preparedFenceLocked(ctx, view, op); err != nil {
		if op.outcome == "obsolete" {
			return result, "obsolete", nil
		}
		return result, "", err
	}
	return result, "prepared", nil
}
