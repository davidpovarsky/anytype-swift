package torahops

import (
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/util/crypto"
)

// AuthorizeHeldCurrentReadACL reuses the original closed native read policy.
// The caller must already hold the ACL read lock and retain it through the
// protected read. This avoids a nested RLock when an ACL writer is waiting.
// Unknown permission values remain refused by requireCurrentReadAccess.
func AuthorizeHeldCurrentReadACL(acl list.AclList, key crypto.PrivKey) error {
	if acl == nil || key == nil {
		return list.ErrInsufficientPermissions
	}
	return requireCurrentReadAccess(acl, key)
}
