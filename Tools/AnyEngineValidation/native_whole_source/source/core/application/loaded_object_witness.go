//go:build pinkha_loaded_account_witness

package application

import (
	"context"
	"errors"
	"sort"

	nativeexport "github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
	"github.com/anyproto/anytype-heart/space/spacecore"
)

var ErrLoadedAccountObjectWitness = errors.New("authorized unchanged native object capture required")

type LoadedAccountObjectWitnessRequest struct {
	Source         LoadedAccountWitnessRequest
	ObjectIDs      []string
	MaxObjectBytes int
	MaxTotalBytes  int
}

// LoadedAccountObjectWitness binds selected current-state exports to an actual
// authorized native checkpoint. It retains the full original raw witness but
// makes no claim that unselected trees, index resolvers, historical semantics or
// file payloads have been migrated.
type LoadedAccountObjectWitness struct {
	source    *LoadedAccountWitness
	inventory *localstorewitness.NativeTreeInventory
	objects   []*nativeexport.NativeObjectWitness
	complete  bool
}

type LoadedAccountObjectWitnessReceipt struct {
	Version                                      string
	SelectedObjects, UnrepresentedNativeTrees    int
	SelectedSnapshotBytes, SelectedAnyBlockBytes int
	AccountSessionAuthorizedAtFinalCapture       bool
	SelectedObjectsBoundToNativeCheckpoint       bool
	OriginalNativeRowsRetained                   bool
	IndexResolverSnapshotBound                   bool
	HistorySemanticsValidated                    bool
	SemanticCompleteness                         bool
	FilePayloadCompleteness                      bool
	HasNativeSourceAdmission                     bool
	PermitsDestinationWrites                     bool
	Source                                       LoadedAccountWitnessReceipt
	Inventory                                    localstorewitness.NativeTreeInventoryReceipt
	Objects                                      []nativeexport.NativeObjectWitnessReceipt
}

func (w *LoadedAccountObjectWitness) PrivateWitness() *localstorewitness.Witness {
	if w == nil || !w.complete || w.source == nil {
		return nil
	}
	return w.source.PrivateWitness()
}

func (w *LoadedAccountObjectWitness) Objects() []*nativeexport.NativeObjectWitness {
	if w == nil || !w.complete {
		return nil
	}
	return append([]*nativeexport.NativeObjectWitness(nil), w.objects...)
}

func (w *LoadedAccountObjectWitness) Receipt() (LoadedAccountObjectWitnessReceipt, error) {
	if w == nil || !w.complete || w.source == nil || w.inventory == nil || len(w.objects) == 0 {
		return LoadedAccountObjectWitnessReceipt{}, ErrLoadedAccountObjectWitness
	}
	source, err := w.source.Receipt()
	if err != nil {
		return LoadedAccountObjectWitnessReceipt{}, err
	}
	inventory, err := w.inventory.Receipt()
	if err != nil {
		return LoadedAccountObjectWitnessReceipt{}, err
	}
	result := LoadedAccountObjectWitnessReceipt{
		Version:         "loaded-account-native-object-join-v1",
		SelectedObjects: len(w.objects), UnrepresentedNativeTrees: inventory.Trees - len(w.objects),
		AccountSessionAuthorizedAtFinalCapture: true, SelectedObjectsBoundToNativeCheckpoint: true,
		OriginalNativeRowsRetained: true, Source: source, Inventory: inventory,
	}
	for _, object := range w.objects {
		if err := object.MatchInventory(w.inventory); err != nil {
			return LoadedAccountObjectWitnessReceipt{}, err
		}
		receipt, err := object.Receipt()
		if err != nil {
			return LoadedAccountObjectWitnessReceipt{}, err
		}
		result.Objects = append(result.Objects, receipt)
		result.SelectedSnapshotBytes += receipt.SnapshotBaseBytes
		result.SelectedAnyBlockBytes += receipt.AnyBlockBytes
	}
	if result.UnrepresentedNativeTrees < 0 {
		return LoadedAccountObjectWitnessReceipt{}, ErrLoadedAccountObjectWitness
	}
	return result, nil
}

// CaptureLoadedAccountObjectWitness does not modify the existing capture API.
// Its initial read uses that API unchanged. It then holds the actual app/account
// and full-session locks through object capture and a fresh authorized native
// checkpoint. Native ACL leases are held only inside each native capture, never
// while loading or locking objects. A change anywhere in the original native
// witness causes refusal; no successful checkpoint is fabricated by retry.
//
// The object cache's lock and underlying native cleanup keep their existing
// scheduling behavior. This function does not claim a new hard deadline.
func (s *Service) CaptureLoadedAccountObjectWitness(ctx context.Context, token string,
	request LoadedAccountObjectWitnessRequest,
) (*LoadedAccountObjectWitness, error) {
	if s == nil || ctx == nil || len(request.ObjectIDs) == 0 || len(request.ObjectIDs) > 128 {
		return nil, ErrLoadedAccountObjectWitness
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if request.MaxObjectBytes == 0 {
		request.MaxObjectBytes = 1 << 20
	}
	if request.MaxTotalBytes == 0 {
		request.MaxTotalBytes = 16 << 20
	}
	if request.MaxObjectBytes < 1 || request.MaxObjectBytes > 8<<20 ||
		request.MaxTotalBytes < 1 || request.MaxTotalBytes > 64<<20 {
		return nil, ErrLoadedAccountObjectWitness
	}
	ids := append([]string(nil), request.ObjectIDs...)
	sort.Strings(ids)
	for i, id := range ids {
		if id == "" || (i > 0 && id == ids[i-1]) {
			return nil, ErrLoadedAccountObjectWitness
		}
	}
	initial, err := s.CaptureLoadedAccountWitness(ctx, token, request.Source)
	if err != nil {
		return nil, err
	}
	inventory, err := initial.PrivateWitness().NativeTreeIdentities(ctx)
	if err != nil {
		return nil, err
	}
	for _, id := range ids {
		entry, err := inventory.Tree(id)
		if err != nil || entry.DeletedStatus() != 0 {
			return nil, errors.Join(ErrLoadedAccountObjectWitness, err)
		}
	}
	if !s.lock.TryRLock() {
		return nil, ErrLoadedAccountWitnessBusy
	}
	defer s.lock.RUnlock()
	if !s.appSessionsLock.TryLock() {
		return nil, ErrLoadedAccountWitnessBusy
	}
	defer s.appSessionsLock.Unlock()
	currentApp := s.app
	currentWallet, err := s.loadedWitnessAccountLocked(request.Source.AccountID)
	if err != nil {
		return nil, err
	}
	lease := s.accountLease
	if loadedAccountWitnessHash(lease.AccountDir()) != initial.accountDirectorySHA256 {
		return nil, ErrLoadedAccountWitnessIdentity
	}
	if err := s.validateLoadedWitnessSessionLocked(token); err != nil {
		return nil, err
	}
	spaceComponent := currentApp.Component(spacecore.CName)
	exportComponent := currentApp.Component(nativeexport.CName)
	result := &LoadedAccountObjectWitness{inventory: inventory}
	exportIDs := map[string]bool{}
	totalBytes := 0
	for _, id := range ids {
		captured, err := nativeexport.CaptureNativeObjectWitness(
			ctx, exportComponent, inventory, id, request.MaxObjectBytes)
		if err != nil {
			return nil, err
		}
		if exportIDs[captured.ExportID()] {
			return nil, ErrLoadedAccountObjectWitness
		}
		exportIDs[captured.ExportID()] = true
		receipt, err := captured.Receipt()
		if err != nil {
			return nil, err
		}
		totalBytes += receipt.SnapshotBaseBytes + receipt.AnyBlockBytes
		if totalBytes > request.MaxTotalBytes {
			return nil, ErrLoadedAccountObjectWitness
		}
		result.objects = append(result.objects, captured)
	}
	// The real native capture revalidates current ACL authority and the owned
	// already-loaded Space. It does not trust the earlier detached inventory.
	finalSource, err := spacecore.CaptureLoadedWitness(ctx, spaceComponent,
		request.Source.SpaceID, request.Source.Limits)
	if err != nil {
		return nil, err
	}
	if finalSource.AccountID() != request.Source.AccountID {
		return nil, ErrLoadedAccountWitnessIdentity
	}
	finalInventory, err := finalSource.PrivateWitness().NativeTreeIdentities(ctx)
	if err != nil {
		return nil, err
	}
	if err := inventory.SameCheckpoint(finalInventory); err != nil {
		return nil, errors.Join(ErrLoadedAccountObjectWitness, err)
	}
	for _, object := range result.objects {
		if err := object.MatchInventory(finalInventory); err != nil {
			return nil, errors.Join(ErrLoadedAccountObjectWitness, err)
		}
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if s.app != currentApp || s.accountLease != lease ||
		currentApp.Component(spacecore.CName) != spaceComponent ||
		currentApp.Component(nativeexport.CName) != exportComponent {
		return nil, ErrLoadedAccountWitnessIdentity
	}
	finalWallet, err := s.loadedWitnessAccountLocked(request.Source.AccountID)
	if err != nil {
		return nil, err
	}
	if finalWallet != currentWallet {
		return nil, ErrLoadedAccountWitnessIdentity
	}
	if err := s.validateLoadedWitnessSessionLocked(token); err != nil {
		return nil, err
	}
	result.source = &LoadedAccountWitness{
		source: finalSource, accountID: request.Source.AccountID,
		accountDirectorySHA256: loadedAccountWitnessHash(lease.AccountDir()), complete: true,
	}
	result.inventory = finalInventory
	result.complete = true
	if _, err := result.Receipt(); err != nil {
		return nil, err
	}
	return result, nil
}
