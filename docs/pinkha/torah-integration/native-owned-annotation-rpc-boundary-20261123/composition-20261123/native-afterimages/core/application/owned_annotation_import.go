package application

import (
	"context"
	"crypto/subtle"
	"errors"

	"github.com/anyproto/any-sync/app"

	importer "github.com/anyproto/anytype-heart/core/block/import"
	walletComp "github.com/anyproto/anytype-heart/core/wallet"
)

// This private typed entry reuses the original account/lease admission and its
// existing registry. The target/source IDs and digest are comparisons, not a
// Host, selected-Space, body or acknowledgement capability. No RPC is enabled.
func (s *Service) startOwnedAnnotationImport(ctx context.Context, expected *app.App, accountID string, raw []byte, digest [32]byte, sourceRootID, sourceSpaceID, targetSpaceID string) (*ownedAccountImport, error) {
	owned, err := s.prepareOwnedAccountAnnotationImport(ctx, expected, accountID, raw, digest, sourceRootID, sourceSpaceID, targetSpaceID)
	if err != nil {
		return nil, err
	}
	// The original registry is already visible, and its mutex/Service RLock
	// have been released, before Execute can enter Space.Get or native work.
	owned.operation.Start()
	return owned, nil
}

func (s *Service) prepareOwnedAccountAnnotationImport(ctx context.Context, expected *app.App, accountID string, raw []byte, digest [32]byte, sourceRootID, sourceSpaceID, targetSpaceID string) (*ownedAccountImport, error) {
	return s.prepareBoundOwnedAccountAnnotationImport(ctx, expected, accountID, raw, digest, sourceRootID, sourceSpaceID, targetSpaceID, nil)
}

func (s *Service) prepareBoundOwnedAccountAnnotationImport(ctx context.Context, expected *app.App, accountID string, raw []byte, digest [32]byte, sourceRootID, sourceSpaceID, targetSpaceID string, annotation *ownedAnnotationCancellationBinding) (*ownedAccountImport, error) {
	if s == nil || ctx == nil || expected == nil || accountID == "" || targetSpaceID == "" {
		return nil, ErrOwnedImportAdmissionUnavailable
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
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
	if annotation != nil {
		for active := range r.operations {
			if active.annotation != nil && subtle.ConstantTimeCompare(active.annotation.secret[:], annotation.secret[:]) == 1 {
				return nil, ErrOwnedAnnotationAttemptConflict
			}
		}
	}
	// Only bounded immutable byte inspection, exclusive private filesystem
	// staging and the original component constructors run here. Native Space
	// binding, derivation, callbacks and import remain inside the later Execute.
	operation, err := importer.PrepareOwnedAnnotationImport(ctx, expected, raw, digest, sourceRootID, sourceSpaceID, targetSpaceID)
	if err != nil {
		return nil, err
	}
	owned := &ownedAccountImport{app: expected, accountID: accountID, spaceID: operation.TargetSpaceID(), operation: operation}
	if annotation != nil {
		bound := *annotation
		owned.annotation = &bound
	}
	if r.operations == nil {
		r.operations = make(map[*ownedAccountImport]struct{})
	}
	r.operations[owned] = struct{}{}
	return owned, nil
}

var ErrOwnedAnnotationAttemptInvalid = errors.New("owned annotation import attempt is invalid")
var ErrOwnedAnnotationAttemptConflict = errors.New("owned annotation import attempt is already registered")

// This immutable private binding only locates an already admitted operation.
// It is not account, selected-Space, import, currentness or acknowledgement authority.
type ownedAnnotationCancellationBinding struct {
	secret        [32]byte
	sourceDigest  [32]byte
	sourceRootID  string
	sourceSpaceID string
}

// OwnedAnnotationImportCompletion contains historical facts copied only from
// this Service's registered original operation after its real Done closes.
type OwnedAnnotationImportCompletion struct {
	registered bool
	done       bool
	outcome    importer.OwnedImportOutcome
}

func (c OwnedAnnotationImportCompletion) Registered() bool { return c.registered }
func (c OwnedAnnotationImportCompletion) Done() bool       { return c.done }
func (c OwnedAnnotationImportCompletion) Outcome() (importer.OwnedImportOutcome, bool) {
	return c.outcome, c.done
}

// OwnedAnnotationCancelDisposition is a cancellation lookup observation.
// Neither a miss nor a cancellation request is a drain or replacement permit.
type OwnedAnnotationCancelDisposition uint8

const (
	OwnedAnnotationCancelNotObserved OwnedAnnotationCancelDisposition = iota
	OwnedAnnotationCancelRequested
	OwnedAnnotationCancelDoneObserved
)

// ImportOwnedAnnotation is the one blocking original native route. Expected IDs
// and the secret are data comparisons only. The original wallet, account lease,
// actual application, regular Space and writer admission remain authoritative.
func (s *Service) ImportOwnedAnnotation(ctx context.Context, accountID string, raw []byte, digest [32]byte,
	sourceRootID, sourceSpaceID, targetSpaceID string, secret [32]byte,
) (OwnedAnnotationImportCompletion, error) {
	var completion OwnedAnnotationImportCompletion
	if s == nil || ctx == nil || secret == ([32]byte{}) {
		return completion, ErrOwnedAnnotationAttemptInvalid
	}
	if err := ctx.Err(); err != nil {
		return completion, err
	}
	// Capture the actual app without waiting behind startup. The existing
	// preparation below rechecks that SAME app under the original read lock.
	if !s.lock.TryRLock() {
		return completion, ErrOwnedImportAdmissionUnavailable
	}
	expected := s.app
	s.lock.RUnlock()
	binding := &ownedAnnotationCancellationBinding{
		secret: secret, sourceDigest: digest,
		sourceRootID: sourceRootID, sourceSpaceID: sourceSpaceID,
	}
	owned, err := s.prepareBoundOwnedAccountAnnotationImport(ctx, expected, accountID, raw, digest,
		sourceRootID, sourceSpaceID, targetSpaceID, binding)
	if err != nil {
		return completion, err
	}
	completion.registered = true
	// The real registry entry exists before Start; no Service/registry lock
	// remains held while Execute, cancellation or completion can run.
	owned.operation.Start()
	select {
	case <-owned.operation.Done():
	case <-ctx.Done():
		owned.operation.RequestCancel()
		// Context cancellation never substitutes for actual Execute, native
		// workers, readback or private staging cleanup returning.
		<-owned.operation.Done()
	}
	outcome, observed := owned.operation.Result()
	if !observed {
		return completion, importer.ErrOwnedImportOperationUnavailable
	}
	completion.done, completion.outcome = true, outcome
	// Retain no terminal-result registry. This local call owns its copied
	// history; deletion is permitted only after the original Done/Result.
	r := &s.ownedImports
	r.mu.Lock()
	delete(r.operations, owned)
	r.mu.Unlock()
	return completion, outcome.Err()
}

// CancelOwnedAnnotationImport can only request cancellation of a matching
// already-registered original operation. It deliberately does not reacquire
// current app/Space write authority: the historical owner survives retirement.
// A pre-registration miss cannot certify that the import never starts.
func (s *Service) CancelOwnedAnnotationImport(accountID, sourceRootID, sourceSpaceID, targetSpaceID string,
	digest, secret [32]byte,
) OwnedAnnotationCancelDisposition {
	if s == nil || secret == ([32]byte{}) {
		return OwnedAnnotationCancelNotObserved
	}
	r := &s.ownedImports
	r.mu.Lock()
	var operation *importer.OwnedImportOperation
	for owned := range r.operations {
		binding := owned.annotation
		if binding != nil && owned.app != nil &&
			owned.accountID == accountID && owned.spaceID == targetSpaceID &&
			binding.sourceRootID == sourceRootID && binding.sourceSpaceID == sourceSpaceID &&
			subtle.ConstantTimeCompare(binding.sourceDigest[:], digest[:]) == 1 &&
			subtle.ConstantTimeCompare(binding.secret[:], secret[:]) == 1 {
			operation = owned.operation
			break
		}
	}
	r.mu.Unlock()
	if operation == nil {
		return OwnedAnnotationCancelNotObserved
	}
	select {
	case <-operation.Done():
		return OwnedAnnotationCancelDoneObserved
	default:
	}
	// Cancellation runs outside both locks and never deletes/releases its owner.
	operation.RequestCancel()
	return OwnedAnnotationCancelRequested
}
