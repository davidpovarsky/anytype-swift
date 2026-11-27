package anysyncx

import "github.com/anyproto/any-sync-sdk/internal/readlifetime"

// FileReadLifetimes captures this exact App run and loaded Space instance.
// It does not load/wait on the cache and is called before the ACL lock. The
// returned tokens are checked again inside the final bounded plaintext copy.
func (a *App) FileReadLifetimes(handle SpaceHandle) (account, loadedSpace *readlifetime.Token, err error) {
	wrapped, ok := handle.(*spaceWrapper)
	if a == nil || !ok || wrapped == nil || wrapped.app != a {
		return nil, nil, readlifetime.ErrRetired
	}
	return &a.fileReadLifetime, &wrapped.fileReadLifetime, nil
}
