package torahops

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/util/crypto"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	cutoverroot "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
	"github.com/stretchr/testify/require"
)

// This fixture uses actual encrypted signed SyncTrees, signed ACL records,
// original mandatory commit storage and native SQLite. Its retained legacy
// value is a component-owned lease fixture, not an actual App property/schema.
// Registry/account lifecycle, production property leasing and peer transport
// remain distinct subsequent acceptance gates.
type cutoverSignedFixture struct {
	native   *nativeFixture
	tree     synctree.SyncTree
	host     *CutoverNativeHost
	client   *fixtureSyncClient
	plan     cutover.Plan
	sourceMu sync.Mutex
	value    CutoverLegacyValue
	retired  atomic.Bool
	acquired atomic.Int32
	released atomic.Int32
}

var errCutoverFixtureRetired = errors.New("actual fixture lease retired")

func sharedNativePlan(t *testing.T, space, object, key, mode string) cutover.Plan {
	t.Helper()
	path := os.Getenv("PINKHA_CUTOVER_SHARED_FIXTURE")
	resolved, err := filepath.EvalSymlinks(path)
	require.NoError(t, err)
	require.True(t, filepath.IsAbs(path))
	require.Equal(t, path, resolved)
	st, err := os.Lstat(path)
	require.NoError(t, err)
	require.True(t, st.Mode().IsRegular())
	require.EqualValues(t, 6613720, st.Size())
	raw, err := os.ReadFile(path)
	require.NoError(t, err)
	sum := sha256.Sum256(raw)
	require.Equal(t, "6d7003d580ef253c5666b14c4bef9b9e712cafa9349ba9830ed1e5faa9b0d2a7", hex.EncodeToString(sum[:]))
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, path, space, object, key, mode)
	wire, err := cmd.Output()
	require.NoError(t, err)
	require.LessOrEqual(t, len(wire), cutover.MaxPlanBytes)
	require.Greater(t, len(wire), 0)
	var plan cutover.Plan
	decoder := json.NewDecoder(bytes.NewReader(wire))
	decoder.DisallowUnknownFields()
	require.NoError(t, decoder.Decode(&plan))
	require.Equal(t, space, plan.SpaceID)
	require.Equal(t, object, plan.ObjectID)
	require.Equal(t, key, plan.PropertyKey)
	require.NoError(t, cutover.ValidateSourceCoverage(plan))
	after, err := os.ReadFile(path)
	require.NoError(t, err)
	require.Equal(t, raw, after)
	return plan
}

func newCutoverSignedFixture(t *testing.T) *cutoverSignedFixture {
	t.Helper()
	config, _, _ := makeNativeConfigs(t)
	root := os.Getenv("PINKHA_CUTOVER_NATIVE_WORK")
	require.True(t, filepath.IsAbs(root))
	require.NotContains(t, t.Name(), "/")
	directory := filepath.Join(root, t.Name())
	require.NoError(t, os.Mkdir(directory, 0700))
	config.Dir = filepath.Join(directory, "native")
	require.NoError(t, os.Mkdir(config.Dir, 0700))
	plan := sharedNativePlan(t, config.Space.SpaceHeaderWithId.Id, config.TargetRoots[0].Id, "canonical-property", "populated")
	raw, err := json.Marshal(struct {
		Config nativeFixtureConfig
		Plan   cutover.Plan
	}{config, plan})
	require.NoError(t, err)
	require.NoError(t, os.WriteFile(filepath.Join(directory, "private-fixture.json"), raw, 0600))
	f := openCutoverSignedFixture(t, config, plan)
	t.Cleanup(func() { require.NoError(t, f.close()) })
	return f
}

func openCutoverSignedFixture(t *testing.T, config nativeFixtureConfig, plan cutover.Plan) *cutoverSignedFixture {
	t.Helper()
	ctx := context.Background()
	native, err := openNativeFixture(ctx, config)
	require.NoError(t, err)
	f := &cutoverSignedFixture{native: native, plan: plan,
		value: CutoverLegacyValue{Key: plan.PropertyKey, Present: plan.ValuePresent, Bytes: bytes.Clone(plan.LegacyValue)}}
	root, err := cutoverroot.Root(native.space.Id())
	require.NoError(t, err)
	f.client = &fixtureSyncClient{RequestFactory: synctree.NewRequestFactory(native.space.Id()), spaceID: native.space.Id(), stats: &protocolStats{}}
	deps := synctree.BuildDeps{SpaceId: native.space.Id(), SyncClient: f.client, AclList: native.acl,
		SpaceStorage: native.space, OnClose: func(string) {}, SyncStatus: fixtureStatus{},
		BuildObjectTree: CutoverNativeTreeBuilder(native.space.Id())}
	_, err = native.space.TreeStorage(ctx, root.Id)
	if errors.Is(err, treestorage.ErrUnknownTreeId) {
		f.tree, err = synctree.PutSyncTree(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}}, deps)
	} else if err == nil {
		f.tree, err = synctree.BuildSyncTreeOrGetRemote(ctx, root.Id, deps)
	}
	require.NoError(t, err)
	f.host, err = OpenCutoverNativeHost(ctx, native.projectionDB, native.space.Id(), f.tree, native.keys.SignKey, f.lease)
	require.NoError(t, err)
	require.NotEqual(t, f.tree.Id(), native.tree.Id())
	return f
}

func (f *cutoverSignedFixture) close() error {
	var err error
	if f.tree != nil {
		err = f.tree.Close()
		f.tree = nil
	}
	if f.native != nil {
		err = errors.Join(err, f.native.Close())
		f.native = nil
	}
	return err
}

func (f *cutoverSignedFixture) lease(ctx context.Context, object, key string, write bool) (*CutoverSourceLease, error) {
	if object != f.plan.ObjectID || key != f.plan.PropertyKey {
		return nil, cutover.ErrInvalid
	}
	if err := f.native.validateTarget(ctx, Target{ObjectID: object}); err != nil {
		return nil, err
	}
	// Only local component source bytes use this mutex. Target heads themselves
	// come from the actual native target storage and never from an RPC record.
	f.sourceMu.Lock()
	f.acquired.Add(1)
	release := func() { f.released.Add(1); f.sourceMu.Unlock() }
	storage, err := f.native.space.TreeStorage(ctx, object)
	if err != nil {
		release()
		return nil, err
	}
	heads, err := storage.Heads(ctx)
	if err != nil {
		release()
		return nil, err
	}
	validate := func(ctx context.Context) error {
		if err := ctx.Err(); err != nil {
			return err
		}
		if f.retired.Load() {
			return errCutoverFixtureRetired
		}
		return nil
	}
	return &CutoverSourceLease{Value: f.value, Heads: heads, Release: release, Validate: validate,
		ValidateTarget: func(ctx context.Context, target Target) error {
			if err := validate(ctx); err != nil {
				return err
			}
			if target.ObjectID != object {
				return cutover.ErrInvalid
			}
			return f.native.validateTarget(ctx, target)
		}}, nil
}
func (f *cutoverSignedFixture) read(t *testing.T) CutoverNativeSnapshot {
	t.Helper()
	s, err := f.host.Read(context.Background(), f.native.host, f.plan.ObjectID, f.plan.PropertyKey)
	require.NoError(t, err)
	require.Equal(t, f.acquired.Load(), f.released.Load())
	return s
}
func (f *cutoverSignedFixture) record(t *testing.T, key crypto.PrivKey, id int, kind cutover.Kind) cutover.Record {
	t.Helper()
	planID, err := f.plan.ID()
	require.NoError(t, err)
	return cutover.Record{Version: cutover.Version, SpaceID: f.plan.SpaceID, ObjectID: f.plan.ObjectID,
		RecordID: fmt.Sprintf("%032x", id), AuthorID: key.GetPublic().Account(), Kind: kind, PlanID: planID}
}
func (f *cutoverSignedFixture) begin(t *testing.T, key crypto.PrivKey, id int) cutover.Record {
	r := f.record(t, key, id, cutover.Begin)
	r.Plan = &f.plan
	r.SourceHeads = f.read(t).SourceHeads
	return r
}
func (f *cutoverSignedFixture) importOperation(t *testing.T, key crypto.PrivKey, index int) (string, Operation) {
	t.Helper()
	fact := f.plan.Facts[index]
	factID, err := fact.ID(f.plan.SpaceID, f.plan.ObjectID)
	require.NoError(t, err)
	planID, err := f.plan.ID()
	require.NoError(t, err)
	opID, err := cutover.ImportOperationID(planID, factID, key.GetPublic().Account())
	require.NoError(t, err)
	return factID, Operation{Version: Version, SpaceID: f.plan.SpaceID, OperationID: opID, AuthorID: key.GetPublic().Account(),
		Kind: Add, Target: Target{ObjectID: f.plan.ObjectID, BlockID: fact.BlockID}, Source: Source{ProviderID: fact.ProviderID, CanonicalRef: fact.CanonicalRef},
		Payload: bytes.Clone(fact.Payload)}
}
func (f *cutoverSignedFixture) importMetadata(t *testing.T, key crypto.PrivKey, id int, factID, claimID string) cutover.Record {
	t.Helper()
	s := f.read(t)
	r := f.record(t, key, id, cutover.Import)
	r.FactID = factID
	r.ImportClaimID = claimID
	for _, receipt := range s.OriginalReceipts[claimID] {
		require.Equal(t, claimID, receipt.ClaimID)
		require.NotEmpty(t, receipt.ChangeID)
		require.NotEmpty(t, receipt.ACLHeadID)
		r.NativeChanges = append(r.NativeChanges, cutover.NativeWitness{ChangeID: receipt.ChangeID, Creator: receipt.Creator, ACLHeadID: receipt.ACLHeadID})
	}
	require.NotEmpty(t, r.NativeChanges)
	return r
}
func (f *cutoverSignedFixture) seal(t *testing.T, key crypto.PrivKey, id int) cutover.Record {
	t.Helper()
	s := f.read(t)
	r := f.record(t, key, id, cutover.Seal)
	for _, imp := range s.State.Imports {
		// A well-formed seal names only paired phase-two records. The new
		// phase-one claim remains pending and must be refused by the host.
		if len(imp.MetadataClaims) == 0 {
			continue
		}
		r.Imported = append(r.Imported, cutover.Binding{FactID: imp.FactID, ClaimID: imp.ClaimID})
		r.ImportRecords = append(r.ImportRecords, imp.MetadataClaims...)
	}
	return r
}
func (f *cutoverSignedFixture) finishOwner(t *testing.T) CutoverNativeSnapshot {
	t.Helper()
	ctx := context.Background()
	key := f.native.keys.SignKey
	begin := f.begin(t, key, 1)
	written, err := f.host.Append(ctx, f.native.host, begin)
	require.NoError(t, err)
	require.Equal(t, Created, written.Disposition)
	require.NotEmpty(t, written.ChangeID)
	for i := range f.plan.Facts {
		factID, op := f.importOperation(t, key, i)
		imported, err := f.host.AppendImport(ctx, f.native.host, begin.PlanID, factID, op)
		require.NoError(t, err)
		require.Equal(t, Created, imported.Disposition)
		require.NotEmpty(t, imported.ChangeID)
		require.Equal(t, CutoverPending, f.read(t).State.Status, "phase one alone is never sealed")
		metadata := f.importMetadata(t, key, 10+i, factID, imported.ClaimID)
		recorded, err := f.host.Append(ctx, f.native.host, metadata)
		require.NoError(t, err)
		require.Equal(t, Created, recorded.Disposition)
		require.NotEmpty(t, recorded.ChangeID)
	}
	sealed, err := f.host.Append(ctx, f.native.host, f.seal(t, key, 100))
	require.NoError(t, err)
	require.Equal(t, Created, sealed.Disposition)
	require.NotEmpty(t, sealed.ChangeID)
	final := f.read(t)
	require.Equal(t, CutoverSealed, final.State.Status)
	return final
}

func TestCutoverNativeSignedPhasesUnlinkAndReopen(t *testing.T) {
	f := newCutoverSignedFixture(t)
	ctx := context.Background()
	require.Equal(t, CutoverLegacy, f.read(t).State.Status)
	sealed := f.finishOwner(t)
	require.Len(t, sealed.State.Imports, 2)
	require.Len(t, sealed.State.Seals, 1)
	require.Equal(t, f.plan.LegacyValue, sealed.Source.Bytes)
	require.Len(t, sealed.OriginalClaims, 2)
	require.Len(t, sealed.MetadataHistory.Claims, 4)
	v1, err := f.native.host.ReadTarget(ctx, Target{ObjectID: f.plan.ObjectID}, 10)
	require.NoError(t, err)
	require.Len(t, v1.Projection.Live, 2)
	remove := Operation{Version: Version, SpaceID: f.plan.SpaceID, OperationID: strings.Repeat("f", 32),
		AuthorID: f.native.keys.SignKey.GetPublic().Account(), Kind: Remove, Target: Target{ObjectID: f.plan.ObjectID}}
	for _, imp := range sealed.State.Imports {
		remove.Observed = append(remove.Observed, imp.ClaimID)
	}
	result, err := f.host.AppendAssociation(ctx, f.native.host, sealed.State.PlanID, remove)
	require.NoError(t, err)
	require.Equal(t, Created, result.Disposition)
	require.NotEmpty(t, result.ChangeID)
	after := f.read(t)
	require.Equal(t, CutoverSealed, after.State.Status)
	require.Equal(t, sealed.State.Imports, after.State.Imports)
	v1, err = f.native.host.ReadTarget(ctx, remove.Target, 10)
	require.NoError(t, err)
	require.Empty(t, v1.Projection.Live)
	config, plan := f.native.config, f.plan
	require.NoError(t, f.close())
	reopened := openCutoverSignedFixture(t, config, plan)
	defer func() { require.NoError(t, reopened.close()) }()
	cold := reopened.read(t)
	require.Equal(t, after, cold)
	v1, err = reopened.native.host.ReadTarget(ctx, remove.Target, 10)
	require.NoError(t, err)
	require.Empty(t, v1.Projection.Live)
	retry, err := reopened.host.AppendAssociation(ctx, reopened.native.host, sealed.State.PlanID, remove)
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.Equal(t, cold, reopened.read(t))
	t.Log("actual signed metadata/v1 phases, durable seal after unlink and independent SQLite/tree reopen; same OS process, no App/property registry claim")
}

func TestCutoverNativeTwoAuthorsRetainAllBindingsAndOlderWriterDiverges(t *testing.T) {
	f := newCutoverSignedFixture(t)
	ctx := context.Background()
	owner := f.native.keys.SignKey
	writer := addNativeWriter(t, f.native)
	writerV1, err := OpenNativeHost(ctx, f.native.projectionDB, f.plan.SpaceID, f.native.tree, writer, f.native.acquireTarget)
	require.NoError(t, err)
	writerHost, err := OpenCutoverNativeHost(ctx, f.native.projectionDB, f.plan.SpaceID, f.tree, writer, f.lease)
	require.NoError(t, err)
	begin := f.begin(t, owner, 1)
	_, err = f.host.Append(ctx, f.native.host, begin)
	require.NoError(t, err)
	writerBegin := f.begin(t, writer, 2)
	_, err = writerHost.Append(ctx, writerV1, writerBegin)
	require.NoError(t, err)
	require.NotEqual(t, begin.AuthorID, writerBegin.AuthorID)
	for i := range f.plan.Facts {
		for j, key := range []crypto.PrivKey{owner, writer} {
			h, v1 := f.host, f.native.host
			if j == 1 {
				h, v1 = writerHost, writerV1
			}
			factID, op := f.importOperation(t, key, i)
			result, err := h.AppendImport(ctx, v1, begin.PlanID, factID, op)
			require.NoError(t, err)
			require.Equal(t, Created, result.Disposition)
			before := f.read(t)
			incomplete := f.seal(t, key, 90+i*2+j)
			_, err = incomplete.CanonicalBytes()
			require.NoError(t, err, "partial-history probe must first be a valid metadata request")
			_, err = h.Append(ctx, v1, incomplete)
			require.ErrorIs(t, err, cutover.ErrIncomplete)
			require.Equal(t, before, f.read(t))
			metadata := f.importMetadata(t, key, 10+i*2+j, factID, result.ClaimID)
			_, err = h.Append(ctx, v1, metadata)
			require.NoError(t, err)
		}
	}
	final := f.read(t)
	require.Len(t, final.State.Imports, 4)
	require.Empty(t, final.State.Conflicts)
	sealed, err := f.host.Append(ctx, f.native.host, f.seal(t, owner, 100))
	require.NoError(t, err)
	require.NotEmpty(t, sealed.ChangeID)
	require.Equal(t, CutoverSealed, f.read(t).State.Status)
	// The exact historical legacy property remains. An old writer changing it
	// produces divergence; it cannot be silently unioned or removed by a read.
	f.sourceMu.Lock()
	f.value.Bytes = append(bytes.Clone(f.value.Bytes), ' ')
	f.sourceMu.Unlock()
	diverged := f.read(t)
	require.Equal(t, CutoverDiverged, diverged.State.Status)
	require.NotEmpty(t, diverged.State.Conflicts)
	require.Len(t, diverged.State.Imports, 4)
	require.NotEmpty(t, diverged.State.Seals)
	newOp := Operation{Version: Version, SpaceID: f.plan.SpaceID, OperationID: strings.Repeat("a", 32), AuthorID: owner.GetPublic().Account(),
		Kind: Remove, Target: Target{ObjectID: f.plan.ObjectID}, Observed: []string{diverged.State.Imports[0].ClaimID}}
	_, err = f.host.AppendAssociation(ctx, f.native.host, begin.PlanID, newOp)
	require.ErrorIs(t, err, cutover.ErrLegacyChanged)
	require.Equal(t, diverged, f.read(t))
	t.Log("two actual signed ACL authors, four physical imports, incomplete seal refusal, older-writer component-property divergence; no peer transport claimed")
}

func TestCutoverNativeCurrentACLAndRetiredLeaseRefuseReadAndRetry(t *testing.T) {
	f := newCutoverSignedFixture(t)
	ctx := context.Background()
	f.finishOwner(t)
	writer := addNativeWriter(t, f.native)
	v1, err := OpenNativeHost(ctx, f.native.projectionDB, f.plan.SpaceID, f.native.tree, writer, f.native.acquireTarget)
	require.NoError(t, err)
	h, err := OpenCutoverNativeHost(ctx, f.native.projectionDB, f.plan.SpaceID, f.tree, writer, f.lease)
	require.NoError(t, err)
	before, err := h.Read(ctx, v1, f.plan.ObjectID, f.plan.PropertyKey)
	require.NoError(t, err)
	require.Equal(t, CutoverSealed, before.State.Status)
	removeNativeMember(t, f.native, writer)
	calls := f.acquired.Load()
	denied, err := h.Read(ctx, v1, f.plan.ObjectID, f.plan.PropertyKey)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Equal(t, CutoverNativeSnapshot{}, denied)
	r := f.record(t, writer, 200, cutover.Seal)
	r.Imported = []cutover.Binding{}
	_, err = h.Append(ctx, v1, r)
	require.Error(t, err)
	require.Equal(t, calls, f.acquired.Load(), "known revoked author must not inspect source")
	after := f.read(t)
	require.Equal(t, before.MetadataHeads, after.MetadataHeads)
	require.Equal(t, before.OperationHeads, after.OperationHeads)
	f.retired.Store(true)
	denied, err = f.host.Read(ctx, f.native.host, f.plan.ObjectID, f.plan.PropertyKey)
	require.ErrorIs(t, err, errCutoverFixtureRetired)
	require.Equal(t, CutoverNativeSnapshot{}, denied)
	require.Equal(t, f.acquired.Load(), f.released.Load())
	f.retired.Store(false)
	require.Equal(t, after, f.read(t))
}

func TestCutoverNativeLostACKRetainsOneSignedBeginAndLeaseBoundary(t *testing.T) {
	f := newCutoverSignedFixture(t)
	ctx := context.Background()
	begin := f.begin(t, f.native.keys.SignKey, 1)
	storage, err := boundNativeCommitStorage(f.tree)
	require.NoError(t, err)
	originalStorage, originalFactory := storage.Storage, f.client.RequestFactory
	defer func() { storage.Storage = originalStorage; f.client.RequestFactory = originalFactory }()
	startAcquired, startReleased := f.acquired.Load(), f.released.Load()
	checkHeld := func() {
		require.False(t, nativeMutexAvailable(&f.sourceMu))
		require.Equal(t, startReleased, f.released.Load())
	}
	storage.Storage = &nativeCommitStorageObserver{Storage: originalStorage, before: checkHeld, after: checkHeld}
	failure := errors.New("actual cutover head advertisement failed after durable commit")
	f.client.RequestFactory = &nativeFailingHeadUpdate{RequestFactory: originalFactory, failure: failure, observe: func() {
		require.Equal(t, startAcquired+1, f.acquired.Load())
		require.Equal(t, startReleased+1, f.released.Load())
		require.True(t, nativeMutexAvailable(&f.sourceMu))
		require.True(t, nativeACLWriteLockAvailable(t, f.native.acl))
	}}
	result, err := f.host.Append(ctx, f.native.host, begin)
	require.ErrorIs(t, err, failure)
	require.Equal(t, Created, result.Disposition)
	require.NotEmpty(t, result.ChangeID)
	exists, err := f.tree.Storage().Has(ctx, result.ChangeID)
	require.NoError(t, err)
	require.True(t, exists)
	storage.Storage = originalStorage
	f.client.RequestFactory = originalFactory
	snapshot := f.read(t)
	require.Len(t, snapshot.MetadataHistory.Claims, 1)
	receipts := snapshot.MetadataReceipts[result.ClaimID]
	require.Len(t, receipts, 1)
	require.Equal(t, result.ChangeID, receipts[0].ChangeID)
	require.Equal(t, begin.AuthorID, receipts[0].Creator)
	retry, err := f.host.Append(ctx, f.native.host, begin)
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	after := f.read(t)
	require.Equal(t, snapshot, after)
	require.Equal(t, f.acquired.Load(), f.released.Load())
	require.True(t, slices.Equal(snapshot.MetadataHeads, after.MetadataHeads))
}
