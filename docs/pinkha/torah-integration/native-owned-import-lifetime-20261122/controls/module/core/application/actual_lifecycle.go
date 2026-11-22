package application
import "context"
import "errors"
import "runtime"
import "github.com/anyproto/any-sync/app"
import "github.com/anyproto/anytype-heart/core/pushnotification"
import "github.com/anyproto/anytype-heart/pb"
import "github.com/anyproto/anytype-heart/util/anyerror"
func (s *Service) GetApp() *app.App {
	s.lock.RLock()
	defer s.lock.RUnlock()
	return s.app
}

func (s *Service) Stop() error {
	releaseOwnedRetirement, ownedErr := s.beginOwnedImportRetirement()
	if ownedErr != nil {
		return ownedErr
	}
	defer releaseOwnedRetirement()

	s.cancelStart()
	s.lock.Lock()
	defer s.lock.Unlock()
	return s.stop()
}

func (s *Service) stop() error {
	return errors.Join(s.closeApp(), s.releaseAccountLease())
}

func (s *Service) AccountStop(req *pb.RpcAccountStopRequest) error {
	releaseOwnedRetirement, ownedErr := s.beginOwnedImportRetirement()
	if ownedErr != nil {
		return ownedErr
	}
	defer releaseOwnedRetirement()

	cancelled := s.cancelStart()
	if cancelled && !req.RemoveData {
		return nil
	}
	s.lock.Lock()
	defer s.lock.Unlock()

	if s.app == nil {
		if cancelled {
			// The stop happened; the removal did not.
			return ErrFailedToRemoveAccountData
		}
		return ErrApplicationIsNotRunning
	}

	// try to revoke push notification token for mobile clients
	if runtime.GOOS == "android" || runtime.GOOS == "ios" {
		if pushService := s.app.Component(pushnotification.CName).(pushnotification.Service); pushService != nil {
			go func() {
				_ = pushService.RevokeToken(context.Background())
			}()
		}
	}

	if req.RemoveData {
		err := s.accountRemoveLocalData()
		if err != nil {
			return errors.Join(ErrFailedToRemoveAccountData, anyerror.CleanupError(err))
		}
	} else {
		err := s.stop()
		if err != nil {
			return ErrFailedToStopApplication
		}
	}
	return nil
}

type startRun struct {
	ctx    context.Context
	cancel context.CancelFunc
}

// beginStart publishes a start as the in-flight one, superseding any start
// published before it, and returns the context it runs under and the end to
// defer. end must run under s.lock: defer it after s.lock.Unlock.
func (s *Service) beginStart(ctx context.Context) (context.Context, func()) {
	ctx, cancel := context.WithCancel(ctx)
	run := &startRun{ctx: ctx, cancel: cancel}
	s.startMu.Lock()
	prev := s.starting
	s.starting = run
	s.startMu.Unlock()
	if prev != nil {
		log.Info("cancelling the account start in flight: superseded by a newer start")
		prev.cancel()
	}
	end := func() {
		s.startMu.Lock()
		if s.starting == run {
			s.starting = nil
		}
		s.startMu.Unlock()
		if ctx.Err() != nil {
			// told to stop — by AccountStop, by a newer start or by the
			// caller — and the stop has already returned: nothing this start
			// published may outlive it
			if s.app != nil {
				log.Info("closing the app of a cancelled account start")
				_ = s.stop()
			}
			return
		}
		if s.app == nil {
			cancel()
		}
		// a running app keeps its context: any-sync handed it to every Run
		// and objectgc holds it for the app's lifetime, so only the caller's
		// context ends it — as it did before this protocol existed
	}
	return ctx, end
}

// cancelStart cancels the in-flight start, if there is one, and takes it, so
// a second caller finds nothing. It reports whether there was one: that is
// how AccountStop tells "I stopped a pending start" from "nothing to stop".
func (s *Service) cancelStart() bool {
	s.startMu.Lock()
	run := s.starting
	s.starting = nil
	s.startMu.Unlock()
	if run == nil {
		return false
	}
	log.Info("cancelling the account start in flight: stop requested")
	run.cancel()
	return true
}

func (s *Service) releaseAccountLease() error {
	if s.accountLease == nil {
		return nil
	}
	lease := s.accountLease
	if err := lease.Release(); err != nil {
		return err
	}
	s.accountLease = nil
	return nil
}
