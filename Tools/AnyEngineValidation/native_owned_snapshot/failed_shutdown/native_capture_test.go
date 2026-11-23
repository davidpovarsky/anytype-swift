//go:build pinkha_localstore_witness

package localstorewitness

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/spacepayloads"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	nativecrypto "github.com/anyproto/any-sync/util/crypto"

	"github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage"
	"github.com/anyproto/anytype-heart/space/spacedomain"
)

type nativeOwnedService interface {
	CreateSpaceStorage(context.Context, spacestorage.SpaceStorageCreatePayload) (spacestorage.SpaceStorage, error)
	WaitSpaceStorage(context.Context, string) (spacestorage.SpaceStorage, error)
	DeleteSpaceStorage(context.Context, string) error
	ListCorruptedBackups() []anystorage.CorruptedBackup
	Close(context.Context) error
}

type nativeOwnedFixture struct {
	root    string
	service nativeOwnedService
	storage spacestorage.SpaceStorage
	payload spacestorage.SpaceStorageCreatePayload
	handles []spacestorage.SpaceStorage
}

func nativeOwnedContext(t *testing.T) context.Context {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	t.Cleanup(cancel)
	return ctx
}

func newNativeOwnedFixture(t *testing.T, ctx context.Context) *nativeOwnedFixture {
	t.Helper()
	private := os.Getenv("PINKHA_NATIVE_OWNED_SNAPSHOT_PRIVATE_ROOT")
	info, err := os.Lstat(private)
	must(t, err)
	if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 || info.Mode().Perm() != 0700 {
		t.Fatal("explicit private native fixture root required")
	}
	root, err := os.MkdirTemp(private, "native-case-")
	must(t, err)
	service := anystorage.New(root, &anystore.Config{})
	f := &nativeOwnedFixture{root: root, service: service}
	t.Cleanup(func() {
		closeCtx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		defer cancel()
		for i := len(f.handles) - 1; i >= 0; i-- {
			if err := f.handles[i].Close(closeCtx); err != nil {
				t.Errorf("actual native handle cleanup: %v", err)
			}
		}
		if err := service.Close(closeCtx); err != nil {
			t.Errorf("actual native service cleanup: %v", err)
		}
	})
	keys, err := accountdata.NewRandom()
	must(t, err)
	master, _, err := nativecrypto.GenerateRandomEd25519KeyPair()
	must(t, err)
	meta, _, err := nativecrypto.GenerateRandomEd25519KeyPair()
	must(t, err)
	f.payload, err = spacepayloads.StoragePayloadForSpaceCreate(spacepayloads.SpaceCreatePayload{
		SigningKey: keys.SignKey, SpaceType: spacedomain.SpaceTypeRegular.String(), ReplicationKey: 10,
		MasterKey: master, ReadKey: nativecrypto.NewAES(), MetadataKey: meta, Metadata: []byte("native-owned-snapshot-private-fixture")})
	must(t, err)
	f.storage, err = service.CreateSpaceStorage(ctx, f.payload)
	must(t, err)
	f.handles = append(f.handles, f.storage)
	if f.storage.Id() != f.payload.SpaceHeaderWithId.Id {
		t.Fatal("actual native initialized Space binding differs")
	}
	must(t, f.storage.StateStorage().SetHash(ctx, "native-owned-before"))
	collection, err := f.storage.AnyStore().CreateCollection(ctx, "native-owned-unknown")
	must(t, err)
	must(t, collection.Insert(ctx, probe("native-a", []byte{0, 255, 7, 0})))
	_, err = f.storage.AnyStore().CreateCollection(ctx, "native-owned-empty")
	must(t, err)
	return f
}

func nativeOwnedCapability(t *testing.T, storage spacestorage.SpaceStorage) *anystorage.LocalSnapshotCapability {
	t.Helper()
	source, ok := storage.(anystorage.LocalSnapshotSource)
	if !ok {
		t.Fatal("actual native storage has no owned snapshot capability")
	}
	capability, err := source.LocalSnapshotCapability()
	must(t, err)
	return capability
}

func nativeOwnedLease(t *testing.T, ctx context.Context, capability *anystorage.LocalSnapshotCapability) *anystorage.LocalSnapshotLease {
	t.Helper()
	lease, err := capability.AcquireWitnessLease(ctx)
	must(t, err)
	return lease
}

func nativeOwnedReceipt(t *testing.T, f *nativeOwnedFixture, label string, witness *Witness) Receipt {
	t.Helper()
	receipt, err := witness.Receipt()
	must(t, err)
	if receipt.Authority != NativeOwnedStoreAuthority || receipt.SpaceSHA256 != sum([]byte(f.storage.Id())) ||
		receipt.Generation == 0 || !receipt.LocalDecodedRowsComplete || receipt.HasNativeSourceAdmission ||
		receipt.PermitsDestinationWrites || !receipt.NativeSnapshotProofRequired || !receipt.NativeIdentityCensusRequired {
		t.Fatal("native ownership was mislabeled as broader source or write authority")
	}
	var private bytes.Buffer
	must(t, witness.WritePrivate(&private))
	out := filepath.Join(f.root, label+".witness.bin")
	file, err := os.OpenFile(out, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	must(t, err)
	n, writeErr := file.Write(private.Bytes())
	closeErr := file.Close()
	must(t, writeErr)
	must(t, closeErr)
	if n != private.Len() {
		t.Fatal("private native witness short write")
	}
	info, err := os.Lstat(out)
	must(t, err)
	if !info.Mode().IsRegular() || info.Mode().Perm() != 0600 {
		t.Fatal("private witness permissions differ")
	}
	raw, err := json.Marshal(receipt)
	must(t, err)
	fmt.Printf("NATIVE_OWNED_WITNESS_RECEIPT %s %s\n", label, raw)
	return receipt
}

func nativeOwnedObservation(t *testing.T, facts map[string]bool, counts map[string]int) {
	t.Helper()
	for name, value := range facts {
		if !value {
			t.Fatalf("native outcome not established: %s", name)
		}
	}
	raw, err := json.Marshal(struct {
		Facts  map[string]bool
		Counts map[string]int
	}{facts, counts})
	must(t, err)
	fmt.Printf("NATIVE_OWNED_SNAPSHOT_OBSERVATION %s %s\n", t.Name(), raw)
}

func nativeOwnedRefused(t *testing.T, ctx context.Context, capability *anystorage.LocalSnapshotCapability) {
	t.Helper()
	lease, err := capability.AcquireWitnessLease(ctx)
	if lease != nil || !errors.Is(err, anystorage.ErrSnapshotOwnership) {
		if lease != nil {
			_ = lease.Close()
		}
		t.Fatal("stale or unowned capability was not refused")
	}
}

func TestNativeOwnedSnapshotBindsActualServiceHandle(t *testing.T) {
	ctx := nativeOwnedContext(t)
	f := newNativeOwnedFixture(t, ctx)
	capability := nativeOwnedCapability(t, f.storage)
	witness, err := CaptureNativeOwned(ctx, capability, DefaultLimits())
	must(t, err)
	first := nativeOwnedReceipt(t, f, "native-initial", witness)
	unknown := witness.collection("native-owned-unknown")
	empty := witness.collection("native-owned-empty")
	if unknown == nil || !unknown.unresolved || len(unknown.rows) != 1 ||
		empty == nil || !empty.unresolved || len(empty.rows) != 0 {
		t.Fatal("actual native unknown/empty collections were lost")
	}
	// This creates only an unowned wrapper; it opens no additional native DB.
	alias, err := anystorage.NewClientStorage(ctx, f.storage)
	must(t, err)
	if _, err = alias.LocalSnapshotCapability(); !errors.Is(err, anystorage.ErrSnapshotOwnership) {
		t.Fatal("generic storage wrapper minted native ownership")
	}
	nativeOwnedRefused(t, ctx, nil)
	nativeOwnedRefused(t, ctx, &anystorage.LocalSnapshotCapability{})
	if got, err := CaptureNativeOwned(ctx, nil, DefaultLimits()); got != nil || !errors.Is(err, ErrOwnership) {
		t.Fatal("nil native capture capability was accepted")
	}

	other := newNativeOwnedFixture(t, ctx)
	foreign, err := other.storage.AnyStore().ReadTx(ctx)
	must(t, err)
	defer foreign.Commit()
	_, err = other.storage.AnyStore().GetCollectionNames(foreign.Context())
	must(t, err)
	// An un-rebound query is rejected by the actual any-store DB identity gate.
	if _, err = f.storage.AnyStore().GetCollectionNames(foreign.Context()); !errors.Is(err, anystore.ErrTxOtherInstance) {
		t.Fatal("actual foreign DB transaction was not refused for a direct query")
	}
	// ReadTx intentionally starts a fresh native-DB transaction, shadowing an
	// ambient foreign transaction. It must not reuse or commit the foreign one.
	witness, err = CaptureNativeOwned(foreign.Context(), capability, DefaultLimits())
	must(t, err)
	second := nativeOwnedReceipt(t, f, "native-ambient-foreign", witness)
	if first.WitnessSHA256 != second.WitnessSHA256 || foreign.Done() {
		t.Fatal("native capture reused, changed, or completed the ambient transaction")
	}
	_, err = other.storage.AnyStore().GetCollectionNames(foreign.Context())
	must(t, err)
	must(t, foreign.Commit())
	if _, err = witness.LocalTreeCensus(ctx, DefaultCensusLimits()); !errors.Is(err, ErrOwnership) {
		t.Fatal("fixture-only census authority was silently widened")
	}
	nativeOwnedObservation(t, map[string]bool{
		"actual_service_constructor": true, "native_unknown_and_empty_retained": true,
		"generic_and_zero_issuance_refused": true, "fresh_same_db_read_transaction": true,
		"foreign_transaction_not_reused_or_committed": true, "census_authority_unchanged": true,
	}, map[string]int{"native_witnesses": 2, "native_stores": 2})
}

func TestNativeOwnedSnapshotCloseRevokesAndDrains(t *testing.T) {
	ctx := nativeOwnedContext(t)
	f := newNativeOwnedFixture(t, ctx)
	capability := nativeOwnedCapability(t, f.storage)
	lease := nativeOwnedLease(t, ctx, capability)
	defer lease.Close()
	before := lease.Binding()
	copied := *lease
	var zero anystorage.LocalSnapshotLease
	if !errors.Is(copied.Close(), anystorage.ErrSnapshotOwnership) ||
		!errors.Is(zero.Close(), anystorage.ErrSnapshotOwnership) ||
		copied.Context() != nil || copied.Storage() != nil || lease.Context().Err() != nil {
		t.Fatal("copied/zero lease affected or exposed the genuine lease")
	}
	blockedCtx, cancelBlocked := context.WithTimeout(ctx, 75*time.Millisecond)
	extra, err := capability.AcquireWitnessLease(blockedCtx)
	cancelBlocked()
	if extra != nil || !errors.Is(err, context.DeadlineExceeded) {
		if extra != nil {
			_ = extra.Close()
		}
		t.Fatal("copied lease released the actual per-space gate")
	}
	tx, err := f.storage.AnyStore().ReadTx(lease.Context())
	must(t, err)
	defer tx.Commit()
	_, err = f.storage.AnyStore().GetCollectionNames(tx.Context())
	must(t, err)
	closed := make(chan error, 1)
	go func() { closed <- f.storage.Close(ctx) }()
	select {
	case <-lease.Context().Done():
	case <-ctx.Done():
		t.Fatal("native close did not revoke its owned lease")
	}
	if !errors.Is(lease.CheckCurrent(ctx), anystorage.ErrSnapshotOwnership) {
		t.Fatal("closing native handle kept its lease current")
	}
	select {
	case <-closed:
		t.Fatal("native database closed before its actual read lease drained")
	default:
	}
	// The backend is still alive; only the lease-derived scan context is canceled.
	_, err = f.storage.AnyStore().GetCollectionNames(ctx)
	must(t, err)
	must(t, tx.Commit())
	releaseErr := lease.Close()
	if !errors.Is(releaseErr, anystorage.ErrSnapshotOwnership) || !errors.Is(releaseErr, context.Canceled) {
		t.Fatal("genuine revoked lease lost its original revocation/cancellation")
	}
	select {
	case err = <-closed:
		must(t, err)
	case <-ctx.Done():
		t.Fatal("native close did not finish after the genuine lease release")
	}
	if !errors.Is(lease.Close(), anystorage.ErrSnapshotOwnership) || !errors.Is(copied.Close(), anystorage.ErrSnapshotOwnership) {
		t.Fatal("repeated or copied release changed the completed outcome")
	}
	if _, err = f.storage.AnyStore().ReadTx(ctx); !errors.Is(err, anystore.ErrDBIsClosed) {
		t.Fatal("actual native database remained open after close completed")
	}
	nativeOwnedRefused(t, ctx, capability)
	reopened, err := f.service.WaitSpaceStorage(ctx, f.storage.Id())
	must(t, err)
	f.handles = append(f.handles, reopened)
	current := nativeOwnedLease(t, ctx, nativeOwnedCapability(t, reopened))
	if current.Binding().Generation <= before.Generation || current.Binding().OwnerNonce != before.OwnerNonce {
		t.Fatal("reopened native handle reused an old generation")
	}
	must(t, current.Close())
	nativeOwnedObservation(t, map[string]bool{
		"copied_and_zero_lease_refused_without_effect": true, "copied_lease_cannot_release_gate": true,
		"actual_read_tx_precedes_close": true, "revocation_cancels_scan": true,
		"backend_close_waited_for_real_release": true, "revoked_release_drained_once": true,
		"native_reopen_uses_new_handle_generation": true,
	}, map[string]int{"real_handle_closes": 1, "reopened_handles": 1, "copied_leases": 1})
}

func TestNativeOwnedSnapshotDeletePreservesLeaseBoundary(t *testing.T) {
	ctx := nativeOwnedContext(t)
	f := newNativeOwnedFixture(t, ctx)
	capability := nativeOwnedCapability(t, f.storage)
	secondStorage, err := f.service.WaitSpaceStorage(ctx, f.storage.Id())
	must(t, err)
	f.handles = append(f.handles, secondStorage)
	secondCapability := nativeOwnedCapability(t, secondStorage)
	secondLease := nativeOwnedLease(t, ctx, secondCapability)
	secondBinding := secondLease.Binding()
	must(t, secondLease.Close())
	lease := nativeOwnedLease(t, ctx, capability)
	defer lease.Close()
	firstBinding := lease.Binding()
	if firstBinding.SpaceID != secondBinding.SpaceID || firstBinding.OwnerNonce != secondBinding.OwnerNonce ||
		firstBinding.Generation == secondBinding.Generation || f.storage.AnyStore() == secondStorage.AnyStore() {
		t.Fatal("same-Space native DB handles were conflated")
	}
	deleteCtx, cancelDelete := context.WithCancel(ctx)
	cancelDelete()
	if err = f.service.DeleteSpaceStorage(deleteCtx, f.storage.Id()); !errors.Is(err, context.Canceled) {
		t.Fatal("canceled delete passed the held native snapshot gate")
	}
	if _, err = os.Stat(filepath.Join(f.root, f.storage.Id(), "store.db")); err != nil {
		t.Fatal("canceled delete removed the actual native store")
	}
	must(t, lease.CheckCurrent(ctx))
	must(t, lease.Close())
	must(t, f.service.DeleteSpaceStorage(ctx, f.storage.Id()))
	nativeOwnedRefused(t, ctx, capability)
	nativeOwnedRefused(t, ctx, secondCapability)
	if _, err = os.Stat(filepath.Join(f.root, f.storage.Id())); !os.IsNotExist(err) {
		t.Fatal("actual native deletion did not remove the owned fixture directory")
	}
	// Retire detached old handles before the same private fixture path is reused.
	must(t, f.storage.Close(ctx))
	must(t, secondStorage.Close(ctx))
	recreated, err := f.service.CreateSpaceStorage(ctx, f.payload)
	must(t, err)
	f.handles = append(f.handles, recreated)
	current := nativeOwnedLease(t, ctx, nativeOwnedCapability(t, recreated))
	if current.Binding().Generation <= secondBinding.Generation {
		t.Fatal("native recreation did not move beyond both prior DB epochs")
	}
	must(t, current.Close())
	nativeOwnedRefused(t, ctx, capability)

	recovery := newNativeOwnedFixture(t, ctx)
	oldRecoveryCap := nativeOwnedCapability(t, recovery.storage)
	// Only this disposable native fixture loses its mandatory changes collection.
	// Actual WaitSpaceStorage must follow its existing uninitialized-store backup.
	changes, err := recovery.storage.AnyStore().OpenCollection(ctx, objecttree.CollName)
	must(t, err)
	must(t, changes.Drop(ctx))
	replacement, err := recovery.service.WaitSpaceStorage(ctx, recovery.storage.Id())
	if replacement != nil || !errors.Is(err, spacestorage.ErrSpaceStorageMissing) {
		t.Fatal("actual native missing-collection recovery outcome differs")
	}
	backups := recovery.service.ListCorruptedBackups()
	if len(backups) != 1 || backups[0].SpaceId != recovery.storage.Id() {
		t.Fatal("actual native successful backup was not recorded")
	}
	if _, err = os.Stat(filepath.Join(backups[0].BackupPath, "store.db")); err != nil {
		t.Fatal("native recovery did not preserve the detached fixture")
	}
	nativeOwnedRefused(t, ctx, oldRecoveryCap)
	must(t, recovery.storage.Close(ctx))
	nativeOwnedObservation(t, map[string]bool{
		"same_space_distinct_db_epochs": true, "canceled_delete_preserves_store_and_lease": true,
		"actual_delete_revokes_all_same_space_handles": true, "recreate_refuses_all_old_capabilities": true,
		"actual_successful_backup_revokes_detached_handle": true, "original_recovery_decision_unchanged": true,
	}, map[string]int{"same_space_prior_handles": 2, "actual_deletions": 1, "actual_backup_renames": 1})
}

// Linux-only qualification observes the actual new SQLite file descriptor,
// not a synthetic constructor hook or caller-controlled production callback.
func nativeOwnedDBDescriptors(t *testing.T, path string) int {
	t.Helper()
	entries, err := os.ReadDir("/proc/self/fd")
	must(t, err)
	count := 0
	for _, entry := range entries {
		target, err := os.Readlink(filepath.Join("/proc/self/fd", entry.Name()))
		if err == nil && target == path {
			count++
		}
	}
	return count
}

func TestNativeOwnedSnapshotShutdownAndCanceledAcquire(t *testing.T) {
	ctx := nativeOwnedContext(t)
	f := newNativeOwnedFixture(t, ctx)
	capability := nativeOwnedCapability(t, f.storage)
	held := nativeOwnedLease(t, ctx, capability)
	defer held.Close()
	canceled, cancel := context.WithCancel(ctx)
	cancel()
	if lease, err := capability.AcquireWitnessLease(canceled); lease != nil || !errors.Is(err, context.Canceled) {
		t.Fatal("canceled acquisition was counted or exposed")
	}
	must(t, held.CheckCurrent(ctx))
	serviceClosed := make(chan error, 1)
	go func() { serviceClosed <- f.service.Close(ctx) }()
	select {
	case <-held.Context().Done():
	case <-ctx.Done():
		t.Fatal("native service shutdown did not revoke its live lease")
	}
	select {
	case <-serviceClosed:
		t.Fatal("native service shutdown passed a live lease")
	default:
	}
	if !errors.Is(held.Close(), anystorage.ErrSnapshotOwnership) {
		t.Fatal("revoked lease did not report shutdown")
	}
	select {
	case err := <-serviceClosed:
		must(t, err)
	case <-ctx.Done():
		t.Fatal("native service shutdown did not drain after release")
	}
	nativeOwnedRefused(t, ctx, capability)
	if storage, err := f.service.WaitSpaceStorage(ctx, f.storage.Id()); storage != nil || !errors.Is(err, anystorage.ErrSnapshotOwnership) {
		t.Fatal("closed native service opened or published a new handle")
	}

	inflight := newNativeOwnedFixture(t, ctx)
	write, err := inflight.storage.AnyStore().WriteTx(ctx)
	must(t, err)
	defer write.Rollback()
	dbPath := filepath.Join(inflight.root, inflight.storage.Id(), "store.db")
	baselineFDs := nativeOwnedDBDescriptors(t, dbPath)
	if baselineFDs == 0 {
		t.Fatal("actual native SQLite descriptors are absent")
	}
	type openedResult struct {
		storage spacestorage.SpaceStorage
		err     error
	}
	opened := make(chan openedResult, 1)
	go func() {
		storage, openErr := inflight.service.WaitSpaceStorage(ctx, inflight.storage.Id())
		opened <- openedResult{storage, openErr}
	}()
	ticker := time.NewTicker(5 * time.Millisecond)
	defer ticker.Stop()
	observedFDs := baselineFDs
	for observedFDs <= baselineFDs {
		select {
		case result := <-opened:
			if result.storage != nil {
				inflight.handles = append(inflight.handles, result.storage)
			}
			t.Fatal("native reopen completed before the actual in-flight open barrier")
		case <-ctx.Done():
			t.Fatal("native in-flight SQLite open was not observed")
		case <-ticker.C:
			observedFDs = nativeOwnedDBDescriptors(t, dbPath)
		}
	}
	// A separate real DB open exists, blocked by the native write transaction.
	// Shutdown wins before that constructor can register its resulting handle.
	must(t, inflight.service.Close(ctx))
	must(t, write.Rollback())
	select {
	case result := <-opened:
		if result.storage != nil {
			inflight.handles = append(inflight.handles, result.storage)
			t.Fatal("in-flight native constructor published after shutdown")
		}
		if !errors.Is(result.err, anystorage.ErrSnapshotOwnership) {
			t.Fatal("in-flight constructor lost the native shutdown refusal")
		}
	case <-ctx.Done():
		t.Fatal("in-flight native constructor did not finish cleanup")
	}
	// SQLite can retain a closed connection's OS descriptor while another
	// connection on this inode still holds a POSIX lock. Close the original
	// fixture handle before asserting that all native descriptors are gone.
	afterRejectedFDs := nativeOwnedDBDescriptors(t, dbPath)
	originalCloseErr := inflight.storage.Close(ctx)
	afterOriginalCloseFDs := nativeOwnedDBDescriptors(t, dbPath)
	fmt.Printf("NATIVE_OWNED_SHUTDOWN_FD_COUNTS {\"baseline\":%d,\"inflight\":%d,\"after_rejected_open\":%d,\"after_original_close\":%d}\n", baselineFDs, observedFDs, afterRejectedFDs, afterOriginalCloseFDs)
	must(t, originalCloseErr)
	if afterOriginalCloseFDs != 0 {
		t.Fatalf("native database descriptors remain after both closes: baseline=%d inflight=%d after-rejection=%d final=%d", baselineFDs, observedFDs, afterRejectedFDs, afterOriginalCloseFDs)
	}
	nativeOwnedObservation(t, map[string]bool{
		"canceled_acquisition_preserves_real_holder": true, "service_shutdown_revokes_and_drains": true,
		"closed_service_refuses_new_open": true, "actual_inflight_sqlite_open_observed": true,
		"post_open_registration_rechecks_shutdown": true, "unpublished_native_handle_closed": true,
	}, map[string]int{"baseline_native_db_fds": baselineFDs, "observed_inflight_native_db_fds": observedFDs})
}
