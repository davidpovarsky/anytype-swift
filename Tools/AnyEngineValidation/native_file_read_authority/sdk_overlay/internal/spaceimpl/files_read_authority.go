package spaceimpl

import (
	"context"
	"fmt"

	"github.com/anyproto/any-sync-sdk/internal/files/readguard"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
)

// fileReadACL resolves the same captured account and space for every delivery
// boundary. The current loaded signed ACL is authoritative; the cached members
// table and a later globally active account are not used here. GetSpace also
// refuses an account whose space cache has closed. No network refresh is added
// to offline reads, and a loaded Guest identity keeps its original permission.
func (s *spaceImpl) fileReadACL(ctx context.Context) (readguard.Scope, error) {
	handle, err := s.app.GetSpace(ctx, s.id)
	if err != nil {
		return readguard.Scope{}, fmt.Errorf("files: load space authority: %w", err)
	}
	if handle.Id() != s.id {
		return readguard.Scope{}, list.ErrInsufficientPermissions
	}
	account, loadedSpace, err := s.app.FileReadLifetimes(handle)
	if err != nil {
		return readguard.Scope{}, list.ErrInsufficientPermissions
	}
	return readguard.Scope{ACL: handle.Inner().Acl(), Account: account, Space: loadedSpace}, nil
}
