package spaceimpl

import (
	"context"

	"github.com/anyproto/any-sync-sdk/internal/files/readguard"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
)

// fileStatusACL never loads a Space or waits on an in-flight cache load. A
// callback belongs to the exact originally loaded account/Space generation;
// a later reload or signed ACL change requires a new subscription.
func (s *spaceImpl) fileStatusACL(context.Context) (readguard.Scope, error) {
	handle, ok := s.app.PeekSpace(s.id)
	if !ok || handle.Id() != s.id {
		return readguard.Scope{}, list.ErrInsufficientPermissions
	}
	account, loadedSpace, err := s.app.FileReadLifetimes(handle)
	if err != nil {
		return readguard.Scope{}, list.ErrInsufficientPermissions
	}
	return readguard.Scope{ACL: handle.Inner().Acl(), Account: account, Space: loadedSpace}, nil
}
