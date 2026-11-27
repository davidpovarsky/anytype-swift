package torahops

import (
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/util/crypto"
)

// WithCurrentReadACL snapshots the same current-membership predicate used by
// native signed-history reads. The callback may copy the immutable ACL identity
// and head or release a completed result; it must not wait for a tree, owner or
// database lock. Callers must not already hold the ACL lock.
func WithCurrentReadACL(acl list.AclList, key crypto.PrivKey, visit func(id, head string) error) error {
	if acl == nil || key == nil || visit == nil {
		return list.ErrInsufficientPermissions
	}
	acl.RLock()
	defer acl.RUnlock()
	if err := requireCurrentReadAccess(acl, key); err != nil {
		return err
	}
	head := acl.Head()
	if acl.Id() == "" || head == nil || head.Id == "" {
		return list.ErrInsufficientPermissions
	}
	return visit(acl.Id(), head.Id)
}
