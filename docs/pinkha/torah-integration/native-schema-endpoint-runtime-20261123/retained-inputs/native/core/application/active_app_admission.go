package application

import (
	"context"
	"errors"

	"github.com/anyproto/any-sync/app"
)

var ErrActiveAppChanged = errors.New("active native application changed before admission")

// WithActiveApp retains the existing application lifetime for one synchronous
// operation. The expected pointer must have come from this Service's GetApp.
// Account replacement/close that requires the original write lock waits for
// already admitted work. AccountStop can still acknowledge cancellation of an
// in-flight Select before taking that lock; such an acknowledgement is not a
// drain and does not close/replace the retained application.
//
// The callback must use retained components directly, never GetApp, account
// lifecycle methods, detached work, or work whose cancellation requires Stop.
// Even a nested RLock can deadlock when an account lifecycle writer is queued.
// entered distinguishes rejection before the callback from an error after it
// ran. An error after entry is not evidence that native writes were rolled back.
func (s *Service) WithActiveApp(ctx context.Context, expected *app.App, operation func(*app.App) error) (entered bool, err error) {
	if s == nil || ctx == nil || expected == nil || operation == nil {
		return false, ErrActiveAppChanged
	}
	if err = ctx.Err(); err != nil {
		return false, err
	}
	s.lock.RLock()
	defer s.lock.RUnlock()
	if err = ctx.Err(); err != nil {
		return false, err
	}
	if s.app == nil || s.app != expected {
		return false, ErrActiveAppChanged
	}
	err = operation(s.app)
	return true, errors.Join(err, ctx.Err())
}
