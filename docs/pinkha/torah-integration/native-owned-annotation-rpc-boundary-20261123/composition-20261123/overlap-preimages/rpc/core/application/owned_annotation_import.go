package application

import (
	"context"

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
	// Only bounded immutable byte inspection, exclusive private filesystem
	// staging and the original component constructors run here. Native Space
	// binding, derivation, callbacks and import remain inside the later Execute.
	operation, err := importer.PrepareOwnedAnnotationImport(ctx, expected, raw, digest, sourceRootID, sourceSpaceID, targetSpaceID)
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
