package torahops

import (
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/util/crypto"
)

// AuthorizeCurrentACL checks the locally verified current membership before a
// host can exist. It acquires/releases the ACL lock itself; callers must not
// already hold it. NativeHost repeats authorization under its tree operation's
// locks. This is not knowledge of ACL updates an offline client has not received.
func AuthorizeCurrentACL(acl list.AclList, key crypto.PrivKey, write bool) error {
	if acl == nil || key == nil {
		return list.ErrInsufficientPermissions
	}
	acl.RLock()
	defer acl.RUnlock()
	if err := requireCurrentReadAccess(acl, key); err != nil {
		return err
	}
	if write && !acl.AclState().Permissions(key.GetPublic()).CanWrite() {
		return list.ErrInsufficientPermissions
	}
	return nil
}
