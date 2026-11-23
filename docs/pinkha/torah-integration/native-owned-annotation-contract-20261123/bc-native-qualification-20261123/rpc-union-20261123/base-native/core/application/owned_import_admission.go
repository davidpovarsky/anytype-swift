package application

import (
	"context"
	"errors"
	"sync"

	"github.com/anyproto/any-sync/app"

	importer "github.com/anyproto/anytype-heart/core/block/import"
	walletComp "github.com/anyproto/anytype-heart/core/wallet"
)

var ErrOwnedImportDrainPending = errors.New("owned original import cancellation requested; actual drain is pending")
var ErrOwnedImportAdmissionUnavailable = errors.New("owned original import application admission is unavailable")

// These fields bind an internally constructed operation to the actual retained
// app and wallet. The target Space is the original request's declared target;
// this is not an ACL, archive, semantic body or ACK capability.
type ownedAccountImport struct {
	app        *app.App
	accountID  string
	spaceID    string
	operation  *importer.OwnedImportOperation
	annotation *ownedAnnotationCancellationBinding
}

// The registry's mutex is never held while waiting for an import, invoking a
// cancellation function or acquiring Service.lock. Admission takes Service's
// read lock first. Lifecycle reserves retirement before its existing writer
// lock, beginStart and account-lease effects.
type ownedImportRegistry struct {
	mu          sync.Mutex
	operations  map[*ownedAccountImport]struct{}
	retirements uint64
	pending     bool
}

func (r *ownedImportRegistry) pruneDrainedLocked() {
	for owned := range r.operations {
		// Only the closed original operation supplies Done. No caller-provided
		// channel, completion closure or mutable success flag is accepted.
		select {
		case <-owned.operation.Done():
			delete(r.operations, owned)
		default:
		}
	}
}

// beginOwnedImportRetirement never joins native work. A synchronous original
// event callback may reenter Stop here; waiting would join its own import or
// block GetApp behind a writer. Pending is an error, not successful Stop.
func (s *Service) beginOwnedImportRetirement() (func(), error) {
	r := &s.ownedImports
	r.mu.Lock()
	r.pruneDrainedLocked()
	if len(r.operations) != 0 {
		r.pending = true
		operations := make([]*importer.OwnedImportOperation, 0, len(r.operations))
		for owned := range r.operations {
			operations = append(operations, owned.operation)
		}
		r.mu.Unlock()
		for _, operation := range operations {
			operation.RequestCancel()
		}
		return nil, ErrOwnedImportDrainPending
	}
	// This is a count, not an exclusive lifecycle gate: with no owned import,
	// newer original starts still publish and cancel older starts in exactly
	// their original order, and AccountStop retains its fast cancelStart path.
	r.retirements++
	r.pending = false
	r.mu.Unlock()
	var once sync.Once
	return func() {
		once.Do(func() {
			r.mu.Lock()
			r.retirements--
			r.mu.Unlock()
		})
	}, nil
}

// startOwnedImport is package-private and has no production caller. The future
// native route must supply authentic archive/attempt/permission binding before
// using it. This method only establishes actual app lifetime and wallet identity.
func (s *Service) startOwnedImport(ctx context.Context, expected *app.App, accountID string, request *importer.ImportRequest) (*ownedAccountImport, error) {
	owned, err := s.prepareOwnedAccountImport(ctx, expected, accountID, request)
	if err != nil {
		return nil, err
	}
	// Registration is already visible before the first native work. A lifecycle
	// request in this gap can cancel the operation, but must still return pending
	// until the now-cancelled original Execute actually returns.
	owned.operation.Start()
	return owned, nil
}

func (s *Service) prepareOwnedAccountImport(ctx context.Context, expected *app.App, accountID string, request *importer.ImportRequest) (*ownedAccountImport, error) {
	if s == nil || ctx == nil || expected == nil || accountID == "" || request == nil || request.RpcObjectImportRequest == nil {
		return nil, ErrOwnedImportAdmissionUnavailable
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	// Do not queue a new owned admission behind an original startup's possibly
	// long writer lock. This private route fails closed and can be retried.
	if !s.lock.TryRLock() {
		return nil, ErrOwnedImportAdmissionUnavailable
	}
	defer s.lock.RUnlock()
	if s.app == nil || s.app != expected {
		return nil, ErrOwnedImportAdmissionUnavailable
	}
	wallet, ok := s.app.Component(walletComp.CName).(walletComp.Wallet)
	if !ok || wallet == nil || wallet.GetAccountPrivkey().GetPublic().Account() != accountID ||
		s.accountLease == nil || !s.accountLease.Matches(wallet.RootPath(), accountID) || !s.accountLease.Usable() {
		return nil, ErrOwnedImportAdmissionUnavailable
	}
	r := &s.ownedImports
	r.mu.Lock()
	defer r.mu.Unlock()
	r.pruneDrainedLocked()
	if r.pending || r.retirements != 0 {
		return nil, ErrOwnedImportAdmissionUnavailable
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	operation, err := importer.PrepareOwnedImport(ctx, expected, request)
	if err != nil {
		return nil, err
	}
	owned := &ownedAccountImport{app: expected, accountID: accountID, spaceID: operation.TargetSpaceID(), operation: operation}
	if r.operations == nil {
		r.operations = make(map[*ownedAccountImport]struct{})
	}
	r.operations[owned] = struct{}{}
	return owned, nil
}
