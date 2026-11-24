//go:build pinkha_loaded_account_witness

package application

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"

	nativeexport "github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/core/files"
	"github.com/anyproto/anytype-heart/core/files/filestorage"
	"github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
	"github.com/anyproto/anytype-heart/pkg/lib/anyblockjson/storeresolver"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/spacecore"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
)

var ErrLoadedAccountSpaceWitness = errors.New("authorized unchanged whole native source capture required")

type LoadedAccountSpaceWitnessRequest struct {
	Source LoadedAccountWitnessRequest
	// PrivateDirectory must exist, be canonical, non-symlink, and mode 0700.
	// Capture creates a new owned child; it never overwrites an existing artifact.
	PrivateDirectory string
	MaxObjects       int
	MaxObjectBytes   int
	MaxSnapshotBytes int
	MaxFiles         int
	MaxFileBytes     int64
	FileLimits       files.NativeFileCaptureLimits
}

// NativeSourceGap is private source information, not a public receipt. Missing
// and unsupported identities remain explicit; original rows are always retained.
type NativeSourceGap struct{ ObjectID, Field, Target, Reason string }

type NativeSourceTree struct {
	ObjectID   string
	NativeType int32
	Status     string
}

// LoadedAccountSpaceWitness owns a complete head inventory, every admitted
// current raw object, a closed resolver, and all admitted file payloads. It
// cannot be constructed by a caller. Partial semantic coverage is explicit.
type LoadedAccountSpaceWitness struct {
	source           *LoadedAccountWitness
	inventory        *localstorewitness.NativeTreeInventory
	objects          []*nativeexport.NativeRawObject
	resolver         *nativeexport.NativeCapturedResolver
	trees            []NativeSourceTree
	fileReferences   []nativeexport.NativeFileReference
	files            map[string]*files.NativeFileCapture
	fileIDs          []string
	gaps             []NativeSourceGap
	privateDirectory string
	complete         bool
}

type LoadedAccountSpaceWitnessReceipt struct {
	Version                                                                   string
	Source                                                                    LoadedAccountWitnessReceipt
	Inventory                                                                 localstorewitness.NativeTreeInventoryReceipt
	NativeTrees, CapturedObjects, Tombstones, SettingsTrees, UnsupportedTrees int
	FileReferences, CapturedFiles, UnresolvedEntries, ClosedResolverUnmapped  int
	SnapshotBytes, MetadataBytes                                              int
	PlaintextBytes                                                            int64
	AccountSessionAuthorizedAtFinalCapture                                    bool
	AllNativeHeadRowsAccounted                                                bool
	CapturedSnapshotsBoundToUnchangedCheckpoint                               bool
	IndexResolverSnapshotBound                                                bool
	AllCurrentObjectsCaptured                                                 bool
	CurrentFilePayloadCompleteness                                            bool
	OriginalNativeHistoryRowsRetained                                         bool
	HistorySemanticsValidated                                                 bool
	SemanticCompleteness                                                      bool
	HasNativeSourceAdmission                                                  bool
	PermitsDestinationWrites                                                  bool
	Objects                                                                   []nativeexport.NativeRawObjectReceipt
	Files                                                                     []files.NativeFileCaptureReceipt
}

func (w *LoadedAccountSpaceWitness) PrivateWitness() *localstorewitness.Witness {
	if w == nil || !w.complete || w.source == nil {
		return nil
	}
	return w.source.PrivateWitness()
}
func (w *LoadedAccountSpaceWitness) Objects() []*nativeexport.NativeRawObject {
	if w == nil || !w.complete {
		return nil
	}
	return append([]*nativeexport.NativeRawObject(nil), w.objects...)
}
func (w *LoadedAccountSpaceWitness) Trees() []NativeSourceTree {
	if w == nil || !w.complete {
		return nil
	}
	return append([]NativeSourceTree(nil), w.trees...)
}
func (w *LoadedAccountSpaceWitness) FileReferences() []nativeexport.NativeFileReference {
	if w == nil || !w.complete {
		return nil
	}
	return append([]nativeexport.NativeFileReference(nil), w.fileReferences...)
}
func (w *LoadedAccountSpaceWitness) FileIDs() []string {
	if w == nil || !w.complete {
		return nil
	}
	return append([]string(nil), w.fileIDs...)
}
func (w *LoadedAccountSpaceWitness) File(id string) *files.NativeFileCapture {
	if w == nil || !w.complete {
		return nil
	}
	return w.files[id]
}
func (w *LoadedAccountSpaceWitness) Gaps() []NativeSourceGap {
	if w == nil || !w.complete {
		return nil
	}
	return append([]NativeSourceGap(nil), w.gaps...)
}
func (w *LoadedAccountSpaceWitness) ResolverUnmapped() []storeresolver.UnmappedReference {
	if w == nil || !w.complete || w.resolver == nil {
		return nil
	}
	return w.resolver.Unmapped()
}
func (w *LoadedAccountSpaceWitness) RenderCapturedObject(ctx context.Context, id string, maxBytes int) ([]byte, error) {
	if w == nil || !w.complete || w.resolver == nil {
		return nil, ErrLoadedAccountSpaceWitness
	}
	return w.resolver.Render(ctx, id, maxBytes)
}

func (w *LoadedAccountSpaceWitness) Receipt() (LoadedAccountSpaceWitnessReceipt, error) {
	if w == nil || !w.complete || w.source == nil || w.inventory == nil {
		return LoadedAccountSpaceWitnessReceipt{}, ErrLoadedAccountSpaceWitness
	}
	sr, err := w.source.Receipt()
	if err != nil {
		return LoadedAccountSpaceWitnessReceipt{}, err
	}
	ir, err := w.inventory.Receipt()
	if err != nil {
		return LoadedAccountSpaceWitnessReceipt{}, err
	}
	r := LoadedAccountSpaceWitnessReceipt{
		Version: "loaded-account-native-space-source-v1", Source: sr, Inventory: ir,
		NativeTrees: len(w.trees), CapturedObjects: len(w.objects), FileReferences: len(w.fileReferences), CapturedFiles: len(w.files),
		UnresolvedEntries: len(w.gaps), ClosedResolverUnmapped: len(w.ResolverUnmapped()),
		AccountSessionAuthorizedAtFinalCapture: true, AllNativeHeadRowsAccounted: len(w.trees) == ir.Trees,
		CapturedSnapshotsBoundToUnchangedCheckpoint: true, IndexResolverSnapshotBound: w.resolver != nil,
		OriginalNativeHistoryRowsRetained: true,
	}
	for _, entry := range w.trees {
		switch entry.Status {
		case "captured-current-snapshot":
		case "native-tombstone-retained":
			r.Tombstones++
		case "space-settings-retained":
			r.SettingsTrees++
		default:
			r.UnsupportedTrees++
		}
	}
	for _, object := range w.objects {
		if err := object.MatchInventory(w.inventory); err != nil {
			return LoadedAccountSpaceWitnessReceipt{}, err
		}
		receipt, err := object.Receipt()
		if err != nil {
			return LoadedAccountSpaceWitnessReceipt{}, err
		}
		r.SnapshotBytes += receipt.SnapshotBytes
		r.Objects = append(r.Objects, receipt)
	}
	for _, id := range w.fileIDs {
		receipt, err := w.files[id].Receipt()
		if err != nil {
			return LoadedAccountSpaceWitnessReceipt{}, err
		}
		r.MetadataBytes += receipt.MetadataBytes
		r.PlaintextBytes += receipt.PlaintextBytes
		r.Files = append(r.Files, receipt)
	}
	r.AllCurrentObjectsCaptured = r.AllNativeHeadRowsAccounted && r.UnsupportedTrees == 0
	// Unknown property formats can hide file references. They must never turn a
	// zero-file export into an unjustified completeness claim.
	r.CurrentFilePayloadCompleteness = r.AllCurrentObjectsCaptured && len(w.gaps) == 0 && r.ClosedResolverUnmapped == 0
	for _, ref := range w.fileReferences {
		if ref.FileID == "" || w.files[ref.FileID] == nil {
			r.CurrentFilePayloadCompleteness = false
		}
	}
	// Historical changes, external collections, non-text destination semantics,
	// and destination mapping have distinct gates; this source receipt grants no
	// blanket migration completion or destination write permission.
	return r, nil
}

func normalizeSpaceWitnessRequest(r *LoadedAccountSpaceWitnessRequest) error {
	if r.MaxObjects == 0 {
		r.MaxObjects = 10000
	}
	if r.MaxObjectBytes == 0 {
		r.MaxObjectBytes = 1 << 20
	}
	if r.MaxSnapshotBytes == 0 {
		r.MaxSnapshotBytes = 64 << 20
	}
	if r.MaxFiles == 0 {
		r.MaxFiles = 256
	}
	if r.MaxFileBytes == 0 {
		r.MaxFileBytes = 2 << 30
	}
	if r.FileLimits == (files.NativeFileCaptureLimits{}) {
		r.FileLimits = files.DefaultNativeFileCaptureLimits()
	}
	if r.MaxObjects < 1 || r.MaxObjects > 10000 || r.MaxObjectBytes < 1 || r.MaxObjectBytes > 8<<20 || r.MaxSnapshotBytes < 1 || r.MaxSnapshotBytes > 64<<20 ||
		r.MaxFiles < 1 || r.MaxFiles > 256 || r.MaxFileBytes < 1 || r.MaxFileBytes > 2<<30 {
		return ErrLoadedAccountSpaceWitness
	}
	if !filepath.IsAbs(r.PrivateDirectory) {
		return ErrLoadedAccountSpaceWitness
	}
	info, err := os.Lstat(r.PrivateDirectory)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 || info.Mode().Perm() != 0700 {
		return errors.Join(ErrLoadedAccountSpaceWitness, err)
	}
	physical, err := filepath.EvalSymlinks(r.PrivateDirectory)
	if err != nil || physical != filepath.Clean(r.PrivateDirectory) {
		return errors.Join(ErrLoadedAccountSpaceWitness, err)
	}
	return nil
}

func nativeSourceFileInfoKey(info *model.FileInfo) (string, error) {
	if info == nil || info.FileId == "" {
		return "", ErrLoadedAccountSpaceWitness
	}
	keys := map[string]string{}
	for _, key := range info.EncryptionKeys {
		if key == nil || key.Path == "" {
			return "", ErrLoadedAccountSpaceWitness
		}
		if _, exists := keys[key.Path]; exists {
			return "", ErrLoadedAccountSpaceWitness
		}
		keys[key.Path] = key.Key
	}
	raw, err := json.Marshal(struct {
		FileID string
		Keys   map[string]string
	}{info.FileId, keys})
	return string(raw), err
}

// CaptureLoadedAccountSpaceWitness never loads another account, starts a
// missing Space, performs remote file I/O, or retries a changed checkpoint.
func (s *Service) CaptureLoadedAccountSpaceWitness(ctx context.Context, token string, request LoadedAccountSpaceWitnessRequest) (*LoadedAccountSpaceWitness, error) {
	if s == nil || ctx == nil {
		return nil, ErrLoadedAccountSpaceWitness
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if err := normalizeSpaceWitnessRequest(&request); err != nil {
		return nil, err
	}
	initial, err := s.CaptureLoadedAccountWitness(ctx, token, request.Source)
	if err != nil {
		return nil, err
	}
	inventory, err := initial.PrivateWitness().NativeTreeIdentities(ctx)
	if err != nil {
		return nil, err
	}
	if len(inventory.TreeIDs()) > request.MaxObjects {
		return nil, ErrLoadedAccountSpaceWitness
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
	fileComponent := currentApp.Component(files.CName)
	storageComponent := currentApp.Component(filestorage.CName)
	privateDir, err := os.MkdirTemp(request.PrivateDirectory, "native-source-")
	if err != nil {
		return nil, err
	}
	dirInfo, err := os.Lstat(privateDir)
	if err != nil {
		return nil, err
	}
	success := false
	defer func() {
		if !success {
			if now, e := os.Lstat(privateDir); e == nil && os.SameFile(now, dirInfo) {
				_ = os.RemoveAll(privateDir)
			}
		}
	}()
	result := &LoadedAccountSpaceWitness{inventory: inventory, files: map[string]*files.NativeFileCapture{}, privateDirectory: privateDir}
	snapshotBytes := 0
	fileInfos := map[string]*model.FileInfo{}
	fileInfoKeys := map[string]string{}
	badFiles := map[string]bool{}
	for _, id := range inventory.TreeIDs() {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		identity, err := inventory.Tree(id)
		if err != nil {
			return nil, err
		}
		entry := NativeSourceTree{ObjectID: id, NativeType: -1}
		switch {
		case identity.DeletedStatus() != 0:
			entry.Status = "native-tombstone-retained"
		case id == inventory.SettingsTreeID():
			entry.Status = "space-settings-retained"
		default:
			kind, _, kindErr := typeprovider.GetTypeAndKeyFromRoot(&treechangeproto.RawTreeChangeWithId{Id: id, RawChange: identity.RootRawChange()})
			if kindErr != nil || kind.Valid() != nil || kind.DetailsStoreOwned() {
				entry.Status = "unsupported-native-object-retained"
				result.gaps = append(result.gaps, NativeSourceGap{id, "nativeRoot", "", "unsupported-native-object-header-or-store-owned-details"})
			} else {
				entry.NativeType = int32(kind.ToProto())
				object, err := nativeexport.CaptureNativeRawObject(ctx, exportComponent, inventory, id, request.MaxObjectBytes)
				if err != nil {
					return nil, errors.Join(ErrLoadedAccountSpaceWitness, err)
				}
				receipt, err := object.Receipt()
				if err != nil {
					return nil, err
				}
				snapshotBytes += receipt.SnapshotBytes
				if snapshotBytes > request.MaxSnapshotBytes {
					return nil, ErrLoadedAccountSpaceWitness
				}
				result.objects = append(result.objects, object)
				entry.Status = "captured-current-snapshot"
				if receipt.StoreBacked {
					entry.Status = "captured-store-backed-object-with-external-state"
					result.gaps = append(result.gaps, NativeSourceGap{id, "nativeStore", "", "store-backed-semantic-state-requires-separate-admission"})
				}
				info, err := object.FileInfo()
				if err != nil {
					return nil, err
				}
				if info != nil {
					key, keyErr := nativeSourceFileInfoKey(info)
					if keyErr != nil {
						result.gaps = append(result.gaps, NativeSourceGap{id, "fileInfo", info.FileId, "invalid-native-file-info"})
					} else if previous, exists := fileInfoKeys[info.FileId]; exists && previous != key {
						badFiles[info.FileId] = true
						result.gaps = append(result.gaps, NativeSourceGap{id, "fileInfo", info.FileId, "colliding-native-file-encryption-keys"})
					} else {
						fileInfos[info.FileId] = info
						fileInfoKeys[info.FileId] = key
					}
				}
			}
		}
		result.trees = append(result.trees, entry)
	}
	if len(result.objects) > 0 {
		result.resolver, err = nativeexport.NewNativeCapturedResolver(inventory, result.objects)
		if err != nil {
			return nil, err
		}
		result.fileReferences, err = result.resolver.FileReferences()
		if err != nil {
			return nil, err
		}
	}
	if len(fileInfos) > request.MaxFiles {
		return nil, ErrLoadedAccountSpaceWitness
	}
	fileIDs := make([]string, 0, len(fileInfos))
	for id := range fileInfos {
		fileIDs = append(fileIDs, id)
	}
	sort.Strings(fileIDs)
	var totalFileBytes int64
	for _, id := range fileIDs {
		if badFiles[id] {
			continue
		}
		fileDir := filepath.Join(privateDir, loadedAccountWitnessHash(id))
		if err := os.Mkdir(fileDir, 0700); err != nil {
			return nil, err
		}
		limits := request.FileLimits
		remaining := request.MaxFileBytes - totalFileBytes
		if remaining < 1 {
			return nil, ErrLoadedAccountSpaceWitness
		}
		if limits.MaxTotalBytes > remaining {
			limits.MaxTotalBytes = remaining
		}
		capture, captureErr := files.CaptureNativeLocalFile(ctx, fileComponent, storageComponent, request.Source.SpaceID, fileInfos[id], fileDir, limits)
		if captureErr != nil {
			if err := ctx.Err(); err != nil {
				return nil, err
			}
			result.gaps = append(result.gaps, NativeSourceGap{"", "filePayload", id, "native-local-payload-capture-refused"})
			continue
		}
		receipt, err := capture.Receipt()
		if err != nil {
			return nil, err
		}
		totalFileBytes += receipt.PlaintextBytes
		snapshotBytes += receipt.MetadataBytes
		if totalFileBytes > request.MaxFileBytes || snapshotBytes > request.MaxSnapshotBytes {
			return nil, ErrLoadedAccountSpaceWitness
		}
		result.files[id] = capture
		result.fileIDs = append(result.fileIDs, id)
	}
	// This is a fresh real native ACL/owner/checkpoint check, not reuse of the
	// detached source or mutable index. Any source-row change causes refusal.
	finalSource, err := spacecore.CaptureLoadedWitness(ctx, spaceComponent, request.Source.SpaceID, request.Source.Limits)
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
		return nil, errors.Join(ErrLoadedAccountSpaceWitness, err)
	}
	for _, object := range result.objects {
		if err := object.MatchInventory(finalInventory); err != nil {
			return nil, err
		}
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if s.app != currentApp || s.accountLease != lease || currentApp.Component(spacecore.CName) != spaceComponent ||
		currentApp.Component(nativeexport.CName) != exportComponent || currentApp.Component(files.CName) != fileComponent ||
		currentApp.Component(filestorage.CName) != storageComponent {
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
	result.source = &LoadedAccountWitness{source: finalSource, accountID: request.Source.AccountID, accountDirectorySHA256: loadedAccountWitnessHash(lease.AccountDir()), complete: true}
	result.inventory = finalInventory
	result.complete = true
	if _, err := result.Receipt(); err != nil {
		return nil, err
	}
	// Ensure the final checkpoint remains represented in a private canonical
	// bundle. This writes new files only; payload files already belong to it.
	if err := result.writePrivateBundle(); err != nil {
		return nil, fmt.Errorf("private native source bundle: %w", err)
	}
	success = true
	return result, nil
}
