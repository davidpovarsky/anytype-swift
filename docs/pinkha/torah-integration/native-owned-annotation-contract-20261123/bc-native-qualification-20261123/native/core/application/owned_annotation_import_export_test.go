package application

import (
	"context"

	"github.com/anyproto/any-sync/app"
	importer "github.com/anyproto/anytype-heart/core/block/import"
	walletComp "github.com/anyproto/anytype-heart/core/wallet"
)

// Test-only entry into the actual private application owner. This file is
// compiled only by go test. It adds no production RPC, SDK or import authority.
func PrepareOwnedAnnotationImportForNativeTest(s *Service, ctx context.Context, expected *app.App, accountID string, raw []byte, digest [32]byte, sourceRoot, sourceSpace, targetSpace string) (*importer.OwnedImportOperation, error) {
	owned, err := s.prepareOwnedAccountAnnotationImport(ctx, expected, accountID, raw, digest, sourceRoot, sourceSpace, targetSpace)
	if err != nil {
		return nil, err
	}
	return owned.operation, nil
}

// These copied observations only let the external native fixture assert the
// real private registry/lease. They neither create nor advance lifecycle state.
type OwnedAnnotationNativeTestOwnership struct {
	CurrentApplication   bool
	MatchingUsableLease  bool
	OperationRegistered  bool
	PendingRetirement    bool
	RegisteredOperations int
}

func ObserveOwnedAnnotationImportForNativeTest(s *Service, expected *app.App, accountID string, operation *importer.OwnedImportOperation) OwnedAnnotationNativeTestOwnership {
	var result OwnedAnnotationNativeTestOwnership
	if s == nil || expected == nil || !s.lock.TryRLock() {
		return result
	}
	defer s.lock.RUnlock()
	result.CurrentApplication = s.app == expected
	if result.CurrentApplication {
		wallet, ok := s.app.Component(walletComp.CName).(walletComp.Wallet)
		result.MatchingUsableLease = ok && wallet != nil &&
			wallet.GetAccountPrivkey().GetPublic().Account() == accountID &&
			s.accountLease != nil && s.accountLease.Matches(wallet.RootPath(), accountID) &&
			s.accountLease.Usable()
	}
	r := &s.ownedImports
	r.mu.Lock()
	defer r.mu.Unlock()
	result.PendingRetirement = r.pending
	result.RegisteredOperations = len(r.operations)
	for owned := range r.operations {
		if owned.operation == operation {
			result.OperationRegistered = true
		}
	}
	return result
}
