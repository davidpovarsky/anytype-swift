//go:build pinkha_loaded_account_witness

package application

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"time"

	"github.com/anyproto/anytype-heart/core/files"
	"github.com/anyproto/anytype-heart/core/files/filestorage"
	"github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
	"github.com/anyproto/anytype-heart/space/spacecore"
)

// This identifies a comparison between complete native inventories only.
// The production prefetch still performs one attempt and never retries.
var ErrLoadedAccountFilePrefetchCheckpointChanged = errors.New("native source checkpoint changed during file prefetch")

type loadedAccountFilePrefetchCheckpointChangedError struct{ stage string }

func (e loadedAccountFilePrefetchCheckpointChangedError) Error() string {
	return errors.Join(ErrLoadedAccountSpaceWitness,
		fmt.Errorf("%w: %s", ErrLoadedAccountFilePrefetchCheckpointChanged, e.stage),
		localstorewitness.ErrNativeTreeInventory).Error()
}
func (loadedAccountFilePrefetchCheckpointChangedError) Unwrap() []error {
	return []error{ErrLoadedAccountSpaceWitness, ErrLoadedAccountFilePrefetchCheckpointChanged, localstorewitness.ErrNativeTreeInventory}
}

type LoadedAccountFilePrefetchRequest struct {
	Source   LoadedAccountWitnessRequest
	Captured *LoadedAccountSpaceWitness
	// These limits cover the entire stage, not each file independently.
	MaxFiles    int
	MaxDAGNodes int
	MaxDAGBytes int64
	MaxDuration time.Duration
}
type LoadedAccountFilePrefetchReceipt struct {
	Version                                   string
	Files                                     int
	DAGNodes, NativeFetches                   int
	DAGBytes                                  int64
	AccountSessionAuthorizedAtFinalRead       bool
	CapturedFileIDsBoundToUnchangedCheckpoint bool
	EveryFetchedBlockRereadFromLocalStore     bool
	RequiresNewFrozenCapture                  bool
	FilePayloadCompleteness                   bool
	HasNativeSourceAdmission                  bool
	PermitsDestinationWrites                  bool
	FileReceipts                              []files.NativeFilePrefetchReceipt
}

// PrefetchLoadedAccountSourceFiles is an explicit preparation step. It rechecks
// the current real account/session/ACL and exact captured source identities
// before using the existing native remote file proxy. No arbitrary caller file
// ID, encryption key or successful detached receipt substitutes for that join.
//
// Successful prefetch proves locally cached CID bytes only. The caller MUST
// invoke a new CaptureLoadedAccountSpaceWitness to decrypt/read every variant
// and bind the resulting payloads to a new unchanged authorized checkpoint.
func (s *Service) PrefetchLoadedAccountSourceFiles(ctx context.Context, token string, request LoadedAccountFilePrefetchRequest) (LoadedAccountFilePrefetchReceipt, error) {
	captured := request.Captured
	if s == nil || ctx == nil || captured == nil || !captured.complete || captured.source == nil || captured.inventory == nil ||
		request.Source.AccountID != captured.source.accountID || request.Source.SpaceID != captured.inventory.SpaceID() ||
		request.MaxFiles < 1 || request.MaxFiles > 256 || request.MaxDAGNodes < 1 || request.MaxDAGNodes > 50000 ||
		request.MaxDAGBytes < 1 || request.MaxDAGBytes > 3<<30 || request.MaxDuration < time.Second || request.MaxDuration > 5*time.Minute {
		return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountSpaceWitness
	}
	ctx, cancel := context.WithTimeout(ctx, request.MaxDuration)
	defer cancel()
	initial, err := s.CaptureLoadedAccountWitness(ctx, token, request.Source)
	if err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	inventory, err := initial.PrivateWitness().NativeTreeIdentities(ctx)
	if err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	if !s.lock.TryRLock() {
		return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountWitnessBusy
	}
	defer s.lock.RUnlock()
	if !s.appSessionsLock.TryLock() {
		return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountWitnessBusy
	}
	defer s.appSessionsLock.Unlock()
	currentApp := s.app
	currentWallet, err := s.loadedWitnessAccountLocked(request.Source.AccountID)
	if err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	lease := s.accountLease
	if loadedAccountWitnessHash(lease.AccountDir()) != initial.accountDirectorySHA256 {
		return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountWitnessIdentity
	}
	if err := s.validateLoadedWitnessSessionLocked(token); err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	spaceComponent := currentApp.Component(spacecore.CName)
	fileComponent := currentApp.Component(files.CName)
	storageComponent := currentApp.Component(filestorage.CName)
	if err := ctx.Err(); err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	if err := captured.inventory.SameCheckpoint(inventory); err != nil {
		return LoadedAccountFilePrefetchReceipt{}, loadedAccountFilePrefetchCheckpointChangedError{stage: "before-fetch"}
	}
	// Only IDs from immutable raw snapshots actually captured by this application
	// enter the fetch plan. Missing/unsupported reference targets remain missing.
	ids := map[string]bool{}
	for _, object := range captured.objects {
		if err := object.MatchInventory(inventory); err != nil {
			return LoadedAccountFilePrefetchReceipt{}, err
		}
		info, err := object.FileInfo()
		if err != nil {
			return LoadedAccountFilePrefetchReceipt{}, err
		}
		if info != nil {
			if _, err := nativeSourceFileInfoKey(info); err != nil {
				return LoadedAccountFilePrefetchReceipt{}, err
			}
			ids[info.FileId] = true
		}
	}
	if len(ids) > request.MaxFiles {
		return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountSpaceWitness
	}
	ordered := make([]string, 0, len(ids))
	for id := range ids {
		ordered = append(ordered, id)
	}
	sort.Strings(ordered)
	result := LoadedAccountFilePrefetchReceipt{Version: "loaded-account-bounded-file-prefetch-v1", RequiresNewFrozenCapture: true}
	for _, id := range ordered {
		remainingNodes := request.MaxDAGNodes - result.DAGNodes
		remainingBytes := request.MaxDAGBytes - result.DAGBytes
		if remainingNodes < 1 || remainingBytes < 1 {
			return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountSpaceWitness
		}
		receipt, err := files.PrefetchNativeFileDAG(ctx, fileComponent, storageComponent, request.Source.SpaceID, id,
			files.NativeFilePrefetchLimits{MaxDAGNodes: remainingNodes, MaxDAGBytes: remainingBytes, MaxDuration: request.MaxDuration})
		if err != nil {
			return LoadedAccountFilePrefetchReceipt{}, err
		}
		result.Files++
		result.DAGNodes += receipt.DAGNodes
		result.DAGBytes += receipt.DAGBytes
		result.NativeFetches += receipt.NativeFetches
		result.FileReceipts = append(result.FileReceipts, receipt)
	}
	finalSource, err := spacecore.CaptureLoadedWitness(ctx, spaceComponent, request.Source.SpaceID, request.Source.Limits)
	if err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	if finalSource.AccountID() != request.Source.AccountID {
		return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountWitnessIdentity
	}
	finalInventory, err := finalSource.PrivateWitness().NativeTreeIdentities(ctx)
	if err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	if err := ctx.Err(); err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	if s.app != currentApp || s.accountLease != lease || currentApp.Component(spacecore.CName) != spaceComponent ||
		currentApp.Component(files.CName) != fileComponent || currentApp.Component(filestorage.CName) != storageComponent {
		return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountWitnessIdentity
	}
	finalWallet, err := s.loadedWitnessAccountLocked(request.Source.AccountID)
	if err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	if finalWallet != currentWallet {
		return LoadedAccountFilePrefetchReceipt{}, ErrLoadedAccountWitnessIdentity
	}
	if err := s.validateLoadedWitnessSessionLocked(token); err != nil {
		return LoadedAccountFilePrefetchReceipt{}, err
	}
	// Classify a complete checkpoint change only after final current account,
	// component, session and context guards. Authority failures stay terminal.
	if err := inventory.SameCheckpoint(finalInventory); err != nil {
		return LoadedAccountFilePrefetchReceipt{}, loadedAccountFilePrefetchCheckpointChangedError{stage: "after-fetch"}
	}
	result.AccountSessionAuthorizedAtFinalRead = true
	result.CapturedFileIDsBoundToUnchangedCheckpoint = true
	result.EveryFetchedBlockRereadFromLocalStore = true
	return result, nil
}
