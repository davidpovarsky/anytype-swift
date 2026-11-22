package clientspace

import "sync"

type currentReadPublicationGate struct {
	mu      sync.RWMutex
	retired bool
}

// AcquireCurrentReadPublication is implemented by real native Spaces (including
// their TechSpace/VirtualSpace wrappers), without widening the public Space
// interface or granting authority to a mock/foreign cache. It leases only a
// finished response publication, never a Space/object load or a network call.
func (s *space) AcquireCurrentReadPublication() (release func(), current bool) {
	if s == nil {
		return nil, false
	}
	s.currentRead.mu.RLock()
	if s.currentRead.retired {
		s.currentRead.mu.RUnlock()
		return nil, false
	}
	var once sync.Once
	return func() { once.Do(s.currentRead.mu.RUnlock) }, true
}

// Close retires this exact native instance before any cache/common cleanup.
// The write lease drains existing publications, then is released before cleanup
// can acquire object or ACL locks. A failed cleanup cannot reactivate the Space.
func (s *space) retireCurrentReadPublications() {
	s.currentRead.mu.Lock()
	s.currentRead.retired = true
	s.currentRead.mu.Unlock()
}
