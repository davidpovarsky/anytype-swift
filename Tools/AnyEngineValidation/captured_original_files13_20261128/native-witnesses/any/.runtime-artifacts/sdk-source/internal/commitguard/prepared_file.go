package commitguard

import (
	"bytes"
	"context"
	"encoding/hex"
	"github.com/ipfs/go-cid"
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

// FileEnvelope is private SDK preparation metadata. It is never an
// HTTP input. The exact payload bytes come from the native immutable ledger.
type FileEnvelope struct {
	InlineFileEnvelope
	RootCID, ContentSHA256 string
	Key                    []byte
	Size                   int64
}

// This strict full-tier parser admits one original payload row with one
// immutable staged content root and sealed key/hash. Inline/variant/network
// fields cannot enter the initial prepared append through this boundary.
// The caller holds the ACL lock through this check and the final native tx.
func filePayloadLocked(acl list.AclList, proof FileEnvelope) (payloads.EncPayload, error) {
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
	if !exactInlineFields(row, payloads.FieldSize, payloads.FieldObjectId, payloads.FieldEnc, payloads.FieldRootCid) || row.GetString(payloads.FieldObjectId) != proof.OwnerID {
		return bad()
	}
	size := row.Get(payloads.FieldSize)
	if size.Type() != anyenc.TypeNumber || size.GetFloat64() < payloads.InlineMaxSize || size.GetFloat64() > 512<<20 || int64(size.GetFloat64()) != proof.Size || math.Trunc(size.GetFloat64()) != size.GetFloat64() {
		return bad()
	}
	root, rootErr := cid.Decode(row.GetString(payloads.FieldRootCid))
	if rootErr != nil || !root.Defined() || root.String() != proof.RootCID || row.GetString(payloads.FieldRootCid) != proof.RootCID || len(proof.Key) != 32 {
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
	if len(plain.Key) != 32 || !bytes.Equal(plain.Key, proof.Key) || plain.Variant != "" || plain.VariantOf != "" || len(plain.Inline) != 0 ||
		len(plain.SHA256) != 32 || hex.EncodeToString(plain.SHA256) != proof.ContentSHA256 {
		return bad()
	}
	return plain, nil
}

// CheckPreparedFile checks the signed envelope against reserved bytes
// and the native sealed member-only content. Current authority is always
// required. Only an already committed known CID may use a historical key.
func CheckPreparedFile(ctx context.Context, acl list.AclList, author crypto.PubKey, root, raw *treechangeproto.RawTreeChangeWithId, proof FileEnvelope, current bool) (payloads.EncPayload, error) {
	if ctx == nil || acl == nil {
		return payloads.EncPayload{}, ErrNativeCommitGuard
	}
	ch, err := inlineEnvelope(root, raw, author, proof.InlineFileEnvelope)
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
	return filePayloadLocked(acl, proof)
}

func PreparedFileContext(ctx context.Context, tree objecttree.ObjectTree, author crypto.PubKey, raw *treechangeproto.RawTreeChangeWithId, proof FileEnvelope) (context.Context, *Guard, error) {
	appendCtx, guard, err := Context(ctx, tree, author)
	if err != nil {
		return nil, nil, err
	}
	if _, err = CheckPreparedFile(ctx, tree.AclList(), author, tree.Header(), raw, proof, true); err != nil {
		return nil, nil, err
	}
	ch, err := inlineEnvelope(tree.Header(), raw, author, proof.InlineFileEnvelope)
	if err != nil {
		return nil, nil, err
	}
	if !sameHeads(ch.PreviousIds, tree.Heads()) {
		return nil, nil, ErrNativeCommitGuard
	}
	proof.Payload = bytes.Clone(proof.Payload)
	proof.Key = bytes.Clone(proof.Key)
	guard.file = &proof
	guard.preparedRaw = &treechangeproto.RawTreeChangeWithId{Id: raw.Id, RawChange: bytes.Clone(raw.RawChange)}
	return appendCtx, guard, nil
}

// StorePreparedFileRoot only registers the already reserved deterministic
// payloads root. Its owner must be locked/live by the native Store caller.
// ACL/key validity is held through the real root storage transaction.
func StorePreparedFileRoot(ctx context.Context, storage spacestorage.SpaceStorage, acl list.AclList, author crypto.PubKey, root, raw *treechangeproto.RawTreeChangeWithId, proof FileEnvelope) error {
	if ctx == nil || storage == nil || acl == nil || storage.Id() != proof.SpaceID {
		return ErrNativeCommitGuard
	}
	ch, err := inlineEnvelope(root, raw, author, proof.InlineFileEnvelope)
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
	if _, err = filePayloadLocked(acl, proof); err != nil {
		return err
	}
	_, err = storage.CreateTreeStorage(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root, Changes: []*treechangeproto.RawTreeChangeWithId{root}, Heads: []string{root.Id}})
	return err
}
