package object

import (
	"bytes"
	"context"
	"encoding/hex"
	"encoding/json"
	"errors"
	"slices"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/commitguard"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
	"github.com/anyproto/any-sync-sdk/internal/payloads"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/util/crypto"
)

// BuildMigrationInlinePayload uses the ordinary native payloads seal/handler
// and native wire codec, without creating a tree or publishing a row.
func BuildMigrationInlinePayload(spec migrationintent.InlineFileSpec, kid string, key crypto.SymKey) ([]byte, error) {
	if err := spec.Validate(); err != nil {
		return nil, err
	}
	if kid == "" || key == nil {
		return nil, commitguard.ErrNativeCommitGuard
	}
	hash, err := hex.DecodeString(spec.ContentSHA256)
	if err != nil {
		return nil, err
	}
	sealed, err := payloads.SealEnc(key, payloads.EncPayload{Name: spec.Name, Mime: spec.Mime, SHA256: hash, Inline: spec.Content})
	if err != nil {
		return nil, err
	}
	a := &anyenc.Arena{}
	enc := a.NewObject()
	enc.Set(payloads.EncKeyId, a.NewString(kid))
	enc.Set(payloads.EncKeyCiphertext, a.NewBinary(sealed))
	row := a.NewObject()
	row.Set(payloads.FieldSize, a.NewNumberFloat64(float64(len(spec.Content))))
	row.Set(payloads.FieldObjectId, a.NewString(spec.OwnerObjectID))
	row.Set(payloads.FieldEnc, enc)
	ch := crdt.Change{Dataset: payloads.Dataset, DataVersion: payloads.HandlerVersion, Records: []crdt.RecordChange{{Upsert: true, Ops: []crdt.Op{{Type: crdt.OpSet, Payload: row}}}}}
	if err = (payloads.Handler{}).PreValidateMulti(&ch, nil); err != nil {
		return nil, err
	}
	return NewCodec().Encode(&ch)
}

func MigrationInlineProof(e *migrationintent.InlineFile) commitguard.InlineFileEnvelope {
	return commitguard.InlineFileEnvelope{SpaceID: e.Binding.SpaceID, OwnerID: e.OwnerObjectID, ReadKeyID: e.ReadKeyID, Payload: e.Payload, Timestamp: e.Timestamp}
}

// CheckMigrationInlineFile binds actual sealed content, exact raw native CID
// and exact native record ID back to the immutable normalized operation.
func CheckMigrationInlineFile(ctx context.Context, acl list.AclList, author crypto.PubKey, e *migrationintent.InlineFile, current bool) (crdt.Change, error) {
	if e == nil {
		return crdt.Change{}, migrationintent.ErrCorrupt
	}
	var spec migrationintent.InlineFileSpec
	if json.Unmarshal(e.Spec, &spec) != nil || spec.Validate() != nil || spec.OwnerObjectID != e.OwnerObjectID ||
		spec.ContentSHA256 != e.ContentSHA256 || int64(len(spec.Content)) != e.Size {
		return crdt.Change{}, migrationintent.ErrCorrupt
	}
	root := &treechangeproto.RawTreeChangeWithId{Id: e.ObjectID, RawChange: e.RootRaw}
	raw := &treechangeproto.RawTreeChangeWithId{Id: e.ChangeID, RawChange: e.Raw}
	plain, err := commitguard.CheckPreparedInlineFile(ctx, acl, author, root, raw, MigrationInlineProof(e), current)
	if err != nil {
		return crdt.Change{}, err
	}
	envelope, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), root).Unmarshall(raw, true)
	if err != nil {
		return crdt.Change{}, err
	}
	if envelope.AclHeadId != e.ACLHeadID || !sameDependencyHeads(map[string][]string{e.ObjectID: envelope.PreviousIds}, map[string][]string{e.ObjectID: e.Dependencies[e.ObjectID]}) {
		return crdt.Change{}, migrationintent.ErrCorrupt
	}
	if plain.Name != spec.Name || plain.Mime != spec.Mime || !bytes.Equal(plain.Inline, spec.Content) || hex.EncodeToString(plain.SHA256) != spec.ContentSHA256 {
		return crdt.Change{}, migrationintent.ErrCorrupt
	}
	ch, err := NewCodec().Decode(e.Payload)
	if err != nil {
		return crdt.Change{}, err
	}
	ch.ChangeId, ch.Timestamp = e.ChangeID, e.Timestamp
	ids, err := crdt.ResolveRecordIds(ch)
	if err != nil || len(ids) != 1 || !slices.Equal(ids, e.RecordIDs) {
		return crdt.Change{}, migrationintent.ErrCorrupt
	}
	return ch, nil
}

// MigrationInlineFileLocked requires the Store's stable owner/carrier native
// locks. The ordinary encrypted prepared route and its replay are untouched.
func (o *Object) MigrationInlineFileLocked(ctx context.Context, e *migrationintent.InlineFile, commit bool) (string, error) {
	if e == nil || o.tree == nil || o.tree.Id() != e.ObjectID || o.signKey == nil {
		return "", migrationintent.ErrScope
	}
	if o.writeGate != nil {
		if err := o.writeGate(); err != nil {
			return "", err
		}
	}
	if err := o.GuardReadyLocked(ctx); err != nil {
		return "", err
	}
	if o.tree.Header().Id != e.ObjectID || !bytes.Equal(o.tree.Header().RawChange, e.RootRaw) {
		return "", migrationintent.ErrCollision
	}
	if o.plaintextSpecFor(o.tree) == nil || checkPlaintextDataset(o.plaintextSpecFor(o.tree), payloads.Dataset) != nil {
		return "", commitguard.ErrNativeCommitGuard
	}
	found, err := o.tree.Storage().Has(ctx, e.ChangeID)
	if err != nil {
		return "", err
	}
	ch, err := CheckMigrationInlineFile(ctx, o.tree.AclList(), o.signKey.GetPublic(), e, !found)
	if errors.Is(err, commitguard.ErrNativeACLChanged) {
		return "obsolete", nil
	}
	if err != nil {
		return "", err
	}
	if found {
		stored, err := o.tree.Storage().Get(ctx, e.ChangeID)
		if err != nil {
			return "", err
		}
		if stored.Id != e.ChangeID || !bytes.Equal(stored.RawChange, e.Raw) || stored.AddSeq == 0 {
			return "", migrationintent.ErrCorrupt
		}
		row, err := o.ctrl.GuardLookup(ctx, payloads.Dataset, e.RecordIDs[0])
		if err != nil {
			return "", err
		}
		if row == nil || row.Get(crdt.DeletedAtField) != nil {
			return "committed_deleted", nil
		}
		if !preparedSetsMatch(row, ch.Records[0].Ops) || crdt.GetRecordVersion(row, "id") != crdt.VersionId(stored.OrderId) ||
			row.GetInt(crdt.AddSeqField) <= 0 || uint64(row.GetInt(crdt.AddSeqField)) != stored.AddSeq || row.GetString(payloads.FieldAuthor) != o.signKey.GetPublic().Account() {
			return "committed_modified", nil
		}
		return "committed", nil
	}
	if !sameDependencyHeads(map[string][]string{e.ObjectID: o.tree.Heads()}, map[string][]string{e.ObjectID: e.Dependencies[e.ObjectID]}) {
		return "obsolete", nil
	}
	if err = o.ctrl.ValidateChange(ch); err != nil {
		return "", err
	}
	if err = o.ctrl.PreValidateLocal(ctx, &ch); err != nil {
		return "", err
	}
	row, err := o.ctrl.GuardLookup(ctx, payloads.Dataset, e.RecordIDs[0])
	if err != nil {
		return "", err
	}
	if row != nil {
		return "", migrationintent.ErrCollision
	}
	if !commit {
		return "prepared", nil
	}
	raw := &treechangeproto.RawTreeChangeWithId{Id: e.ChangeID, RawChange: bytes.Clone(e.Raw)}
	appendCtx, _, err := commitguard.PreparedInlineFileContext(ctx, o.tree, o.signKey.GetPublic(), raw, MigrationInlineProof(e))
	if err != nil {
		return "", err
	}
	_, err = o.tree.AddRawChanges(appendCtx, objecttree.RawChangesPayload{NewHeads: []string{raw.Id}, RawChanges: []*treechangeproto.RawTreeChangeWithId{raw}})
	if err != nil {
		o.setApplyGap(true)
		return "", err
	}
	if err = o.replayLocked(context.WithoutCancel(ctx), o.tree); err != nil {
		o.setApplyGap(true)
		return "", err
	}
	return o.MigrationInlineFileLocked(ctx, e, false)
}
