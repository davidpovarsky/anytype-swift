package application
import "errors"
import "sync"
import "github.com/anyproto/any-sync/app"
import "github.com/anyproto/anytype-heart/core/application/accountdirlock"
// Minimal Service storage ABI plus explicit close/remove dispatch fixtures.
// They do not close a real application, release an OS lock or delete files.
type Service struct {
 lock sync.RWMutex
 ownedImports ownedImportRegistry
 app *app.App
 accountLease *accountdirlock.Lease
 startMu sync.Mutex
 starting *startRun
 closeCalls,removeCalls int
}
var ErrFailedToRemoveAccountData=errors.New("fixture remove failed")
var ErrApplicationIsNotRunning=errors.New("fixture app not running")
var ErrFailedToStopApplication=errors.New("fixture stop failed")
type logger struct{}
func (logger) Info(string){}
var log logger
func (s *Service) closeApp() error { s.closeCalls++; s.app=nil; return nil }
func (s *Service) accountRemoveLocalData() error { s.removeCalls++; return s.stop() }
