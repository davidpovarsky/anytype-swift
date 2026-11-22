package application

import (
	"sync"

	"github.com/anyproto/any-sync/app"
)

// AcquireCurrentAppRead leases only the final publication of an already-built
// response. AccountStop/Select use the same native lifecycle lock, so a response
// from another application instance cannot be published after replacement.
//
// Never wait for a Space or an object while holding this lease. Its holder must
// not call GetApp, account lifecycle methods, or any callback that does so: a
// waiting lifecycle writer makes recursive RLock acquisition unsafe.
func (s *Service) AcquireCurrentAppRead(expected *app.App) (release func(), current bool) {
	if s == nil || expected == nil {
		return nil, false
	}
	s.lock.RLock()
	if s.app != expected {
		s.lock.RUnlock()
		return nil, false
	}
	var once sync.Once
	return func() { once.Do(s.lock.RUnlock) }, true
}
