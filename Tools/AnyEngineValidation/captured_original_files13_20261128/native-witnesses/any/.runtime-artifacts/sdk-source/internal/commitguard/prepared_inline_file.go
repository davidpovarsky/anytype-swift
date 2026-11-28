package commitguard

import (
	"bytes"
	"context"
	"crypto/sha256"
	"math"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/payloads"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/util/crypto"
)

// InlineFileEnvelope is private SDK preparation metadata. It is never an
// HTTP input. The exact payload bytes come from the native immutable ledger.
type InlineFileEnvelope struct {
	SpaceID, OwnerID, ReadKeyID string
	Payload                     []byte
	Timestamp                   int64
}

func InlineFileRoot(spaceID, ownerID string) (*treechangeproto.RawTreeChangeWithId, error) {
	if spaceID == "" || ownerID == "" {
		return nil, ErrNativeCommitGuard
	}
	return objecttree.DeriveObjectTreeRoot(objecttree.ObjectTreeDerivePayload{
		SpaceId: spaceID, ParentId: ownerID, ChangeType: payloads.ChangeType,
		ChangePayload: []byte(payloads.WellKnownDeriveSeed), IsEncrypted: false,
	}, nil)
}

func inlineEnvelope(root, raw *treechangeproto.RawTreeChangeWithId, author crypto.PubKey, proof InlineFileEnvelope) (*objecttree.Change, error) {
	if root == nil || raw == nil || author == nil || proof.ReadKeyID == "" || proof.Timestamp <= 0 || len(proof.Payload) == 0 || len(proof.Payload) > 24<<10 {
		return nil, ErrNativeCommitGuard
	}
	expected, err := InlineFileRoot(proof.SpaceID, proof.OwnerID)
	if err != nil || root.Id != expected.Id || !bytes.Equal(root.RawChange, expected.RawChange) {
		return nil, ErrNativeCommitGuard
	}
	ch, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), root).Unmarshall(raw, true)
	if err != nil {
		return nil, err
	}
	if ch.Identity == nil || !ch.Identity.Equals(author) || ch.IsDerived || ch.IsSnapshot || ch.ReadKeyId != "" ||
		ch.SnapshotId != root.Id || ch.DataType != payloads.Dataset || ch.Timestamp != proof.Timestamp || !bytes.Equal(ch.Data, proof.Payload) {
		return nil, ErrNativeCommitGuard
	}
	return ch, nil
}

func exactInlineFields(v *anyenc.Value, keys ...string) bool {
	if v == nil || v.Type() != anyenc.TypeObject {
		return false
	}
	obj, err := v.Object()
	if err != nil {
		return false
	}
	count, good := 0, true
	obj.Visit(func(k []byte, _ *anyenc.Value) {
		count++
		found := false
		for _, key := range keys {
			if string(k) == key {
				found = true
			}
		}
		good = good && found
	})
	if !good || count != len(keys) {
		return false
	}
	for _, key := range keys {
		if v.Get(key) == nil {
			return false
		}
	}
	return true
}

// This dedicated strict parser follows the pinned SDK object/wire.go keys.
// It is not a general plaintext bypass: one original inline payloads create,
// one sealed enc field, no extra row/wire fields, no full-tier network values.
// The caller holds the ACL lock through this check and the final native tx.
func inlinePayloadLocked(acl list.AclList, proof InlineFileEnvelope) (payloads.EncPayload, error) {
	bad := func() (payloads.EncPayload, error) { return payloads.EncPayload{}, ErrNativeCommitGuard }
	v, err := anyenc.Parse(proof.Payload)
	if err != nil || !exactInlineFields(v, "d", "v", "r") || v.GetString("d") != payloads.Dataset || v.GetString("v") != payloads.HandlerVersion {
		return bad()
	}
	records := v.GetArray("r")
	if len(records) != 1 || !exactInlineFields(records[0], "u", "o") || !records[0].GetBool("u") {
		return bad()
	}
	ops := records[0].GetArray("o")
	if len(ops) != 1 || !exactInlineFields(ops[0], "t", "v") || ops[0].GetString("t") != string(crdt.OpSet) {
		return bad()
	}
	row := ops[0].Get("v")
	if !exactInlineFields(row, payloads.FieldSize, payloads.FieldObjectId, payloads.FieldEnc) || row.GetString(payloads.FieldObjectId) != proof.OwnerID {
		return bad()
	}
	size := row.Get(payloads.FieldSize)
	if size.Type() != anyenc.TypeNumber || size.GetFloat64() < 0 || size.GetFloat64() >= payloads.InlineMaxSize || math.Trunc(size.GetFloat64()) != size.GetFloat64() {
		return bad()
	}
	enc := row.Get(payloads.FieldEnc)
	if !exactInlineFields(enc, payloads.EncKeyId, payloads.EncKeyCiphertext) || enc.GetString(payloads.EncKeyId) != proof.ReadKeyID || enc.Get(payloads.EncKeyCiphertext).Type() != anyenc.TypeBinary {
		return bad()
	}
	keys, ok := acl.AclState().Keys()[proof.ReadKeyID]
	if !ok || keys.ReadKey == nil {
		return payloads.EncPayload{}, list.ErrNoReadKey
	}
	key, err := payloads.DeriveEncKey(keys.ReadKey)
	if err != nil {
		return payloads.EncPayload{}, err
	}
	plain, err := payloads.UnsealEnc(key, enc.GetBytes(payloads.EncKeyCiphertext))
	if err != nil {
		return payloads.EncPayload{}, err
	}
	hash := sha256.Sum256(plain.Inline)
	if len(plain.Key) != 0 || plain.Variant != "" || plain.VariantOf != "" || len(plain.Inline) >= payloads.InlineMaxSize ||
		float64(len(plain.Inline)) != size.GetFloat64() || !bytes.Equal(plain.SHA256, hash[:]) {
		return bad()
	}
	return plain, nil
}

// CheckPreparedInlineFile checks the signed envelope against reserved bytes
// and the native sealed member-only content. Current authority is always
// required. Only an already committed known CID may use a historical key.
func CheckPreparedInlineFile(ctx context.Context, acl list.AclList, author crypto.PubKey, root, raw *treechangeproto.RawTreeChangeWithId, proof InlineFileEnvelope, current bool) (payloads.EncPayload, error) {
	if ctx == nil || acl == nil {
		return payloads.EncPayload{}, ErrNativeCommitGuard
	}
	ch, err := inlineEnvelope(root, raw, author, proof)
	if err != nil {
		return payloads.EncPayload{}, err
	}
	acl.RLock()
	defer acl.RUnlock()
	if err = ctx.Err(); err != nil {
		return payloads.EncPayload{}, err
	}
	if !acl.AclState().Permissions(author).CanWrite() {
		return payloads.EncPayload{}, list.ErrInsufficientPermissions
	}
	if current && (acl.Head() == nil || ch.AclHeadId != acl.Head().Id || proof.ReadKeyID != acl.AclState().CurrentReadKeyId()) {
		return payloads.EncPayload{}, ErrNativeACLChanged
	}
	return inlinePayloadLocked(acl, proof)
}

func PreparedInlineFileContext(ctx context.Context, tree objecttree.ObjectTree, author crypto.PubKey, raw *treechangeproto.RawTreeChangeWithId, proof InlineFileEnvelope) (context.Context, *Guard, error) {
	appendCtx, guard, err := Context(ctx, tree, author)
	if err != nil {
		return nil, nil, err
	}
	if _, err = CheckPreparedInlineFile(ctx, tree.AclList(), author, tree.Header(), raw, proof, true); err != nil {
		return nil, nil, err
	}
	ch, err := inlineEnvelope(tree.Header(), raw, author, proof)
	if err != nil {
		return nil, nil, err
	}
	if !sameHeads(ch.PreviousIds, tree.Heads()) {
		return nil, nil, ErrNativeCommitGuard
	}
	proof.Payload = bytes.Clone(proof.Payload)
	guard.inlineFile = &proof
	guard.preparedRaw = &treechangeproto.RawTreeChangeWithId{Id: raw.Id, RawChange: bytes.Clone(raw.RawChange)}
	return appendCtx, guard, nil
}

// StorePreparedInlineRoot only registers the already reserved deterministic
// payloads root. Its owner must be locked/live by the native Store caller.
// ACL/key validity is held through the real root storage transaction.
func StorePreparedInlineRoot(ctx context.Context, storage spacestorage.SpaceStorage, acl list.AclList, author crypto.PubKey, root, raw *treechangeproto.RawTreeChangeWithId, proof InlineFileEnvelope) error {
	if ctx == nil || storage == nil || acl == nil || storage.Id() != proof.SpaceID {
		return ErrNativeCommitGuard
	}
	ch, err := inlineEnvelope(root, raw, author, proof)
	if err != nil {
		return err
	}
	acl.RLock()
	defer acl.RUnlock()
	if err = ctx.Err(); err != nil {
		return err
	}
	if !acl.AclState().Permissions(author).CanWrite() {
		return list.ErrInsufficientPermissions
	}
	if acl.Head() == nil || ch.AclHeadId != acl.Head().Id || proof.ReadKeyID != acl.AclState().CurrentReadKeyId() {
		return ErrNativeACLChanged
	}
	if _, err = inlinePayloadLocked(acl, proof); err != nil {
		return err
	}
	_, err = storage.CreateTreeStorage(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root, Changes: []*treechangeproto.RawTreeChangeWithId{root}, Heads: []string{root.Id}})
	return err
}
