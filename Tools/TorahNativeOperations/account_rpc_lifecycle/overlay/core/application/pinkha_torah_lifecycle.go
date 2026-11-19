package application

import (
	"context"
	"sync"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/util/pinkhat2test"
)

// LeasePinkhaTorahApp holds the application lifetime lock outside all native
// object locks. Stop/AccountSelect hold the writer side while closing the app;
// reentering GetApp from inside a target/settings lease would invert that order.
// Callers must release once finished and must not call GetApp while leased.
func (s *Service) LeasePinkhaTorahApp(ctx context.Context) (*app.App, func(), error) {
	if err := ctx.Err(); err != nil {
		return nil, nil, err
	}
	s.lock.RLock()
	if err := ctx.Err(); err != nil {
		s.lock.RUnlock()
		return nil, nil, err
	}
	if s.app == nil {
		s.lock.RUnlock()
		return nil, nil, nil
	}
	pinkhat2test.Point(ctx, "app-lease-held", "", "", s)
	var once sync.Once
	return s.app, func() { once.Do(s.lock.RUnlock) }, nil
}
