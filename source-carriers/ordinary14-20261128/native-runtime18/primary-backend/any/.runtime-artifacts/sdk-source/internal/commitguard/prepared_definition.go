package commitguard

import (
	"context"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/util/crypto"
)

func CheckPreparedDefinitionRoot(ctx context.Context, storage spacestorage.SpaceStorage, acl list.AclList, author crypto.PubKey, raw *treechangeproto.RawTreeChangeWithId, kind string) error {
	if kind != "type" && kind != "collection" {
		return ErrNativeCommitGuard
	}
	if ctx == nil || storage == nil || acl == nil || author == nil || raw == nil {
		return ErrNativeCommitGuard
	}
	root, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), raw).Unmarshall(raw, true)
	if err != nil {
		return err
	}
	envelope := &treechangeproto.RawTreeChange{}
	if envelope.UnmarshalVT(raw.RawChange) != nil {
		return ErrNativeCommitGuard
	}
	info := &treechangeproto.RootChange{}
	if info.UnmarshalVT(envelope.Payload) != nil || info.SpaceId != storage.Id() || info.IsDerived || info.ParentId != "" || info.ChangeType != kind || root.Identity == nil || !root.Identity.Equals(author) {
		return ErrNativeCommitGuard
	}
	acl.RLock()
	defer acl.RUnlock()
	if err := ctx.Err(); err != nil {
		return err
	}
	if !acl.AclState().Permissions(author).CanWrite() {
		return list.ErrInsufficientPermissions
	}
	if acl.Head() == nil || root.AclHeadId != acl.Head().Id {
		return ErrNativeACLChanged
	}
	return nil
}
