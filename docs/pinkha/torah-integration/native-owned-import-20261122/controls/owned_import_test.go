package importer

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/import/common/objectid"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	"github.com/anyproto/anytype-heart/core/files/fileuploader"
	"github.com/anyproto/anytype-heart/core/session"
	sb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

func receive[T any](t *testing.T, c <-chan T) T {
	t.Helper()
	select {
	case value := <-c:
		return value
	case <-time.After(3 * time.Second):
		t.Fatal("controlled native callback did not reach its boundary")
		var zero T
		return zero
	}
}

func pending[T any](t *testing.T, c <-chan T) {
	t.Helper()
	select {
	case <-c:
		t.Fatal("drain returned while an original callback is still held")
	case <-time.After(30 * time.Millisecond):
	}
}

func releaseGate(t *testing.T) (<-chan struct{}, func()) {
	t.Helper()
	c := make(chan struct{})
	var once sync.Once
	release := func() { once.Do(func() { close(c) }) }
	t.Cleanup(release)
	return c, release
}

func ownedExecution(t *testing.T) *ownedImportExecution {
	t.Helper()
	owned := newOwnedImportExecution(context.Background())
	t.Cleanup(owned.cancel)
	if err := owned.beginRun(); err != nil {
		t.Fatal(err)
	}
	return owned
}

type drainResult struct {
	files []ownedImportFileResult
	err   error
}

func drain(owned *ownedImportExecution) <-chan drainResult {
	finished := make(chan drainResult, 1)
	go func() {
		files, err := owned.sealAndDrain()
		finished <- drainResult{files, err}
	}()
	return finished
}

func TestOwnedExecutionAdmitsOnlyOneRun(t *testing.T) {
	owned := ownedExecution(t)
	if !errors.Is(owned.beginRun(), errOwnedImportSealed) {
		t.Fatal("one operation admitted a second import run")
	}
	files, err := owned.sealAndDrain()
	if len(files) != 0 || err != nil || !errors.Is(owned.beginRun(), errOwnedImportSealed) {
		t.Fatal("sealed operation admitted another run")
	}
}

func TestPrecancelledExecutionRejectsRunAndFileAdmission(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	owned := newOwnedImportExecution(ctx)
	t.Cleanup(owned.cancel)
	if !errors.Is(owned.beginRun(), context.Canceled) {
		t.Fatal("cancelled operation admitted a run")
	}
	if slot, err := owned.beginFile("sync", "object", "block"); slot != nil || !errors.Is(err, context.Canceled) {
		t.Fatal("cancelled operation admitted an upload")
	}
}

func TestSynchronousFileSlotIsRegisteredBeforeCallAndWaitsActualReturn(t *testing.T) {
	owned := ownedExecution(t)
	gate, release := releaseGate(t)
	entered := make(chan context.Context, 1)
	returned := make(chan error, 1)
	originalErr := errors.New("original synchronous file failure")
	native := &block.Service{Upload: func(ctx context.Context, space string, request block.FileUploadRequest) (string, model.BlockContentFileType, *domain.Details, error) {
		entered <- ctx
		<-gate
		return "partial-file", 0, nil, originalErr
	}}
	scoped := ownedImportBlockService{Service: native, owned: owned}
	go func() {
		_, _, _, err := scoped.UploadFile(nil, "space", block.FileUploadRequest{CreatedInContext: "owner-object"})
		returned <- err
	}()
	if ctx := receive(t, entered); ctx != owned.ctx {
		t.Fatal("original synchronous upload did not receive owned cancellation")
	}
	owned.mu.Lock()
	registered := len(owned.files)
	owned.mu.Unlock()
	if registered != 1 {
		t.Fatal("slot was not registered before original admission")
	}
	finished := drain(owned)
	owned.cancel()
	pending(t, finished)
	release()
	if !errors.Is(receive(t, returned), originalErr) {
		t.Fatal("direct original error was lost")
	}
	result := receive(t, finished)
	if len(result.files) != 1 || result.files[0].ObjectID != "owner-object" || result.files[0].FileObjectID != "partial-file" || !errors.Is(result.err, originalErr) || !errors.Is(result.err, context.Canceled) {
		t.Fatalf("actual synchronous error/identity lost: %#v", result)
	}
}

func TestStartedAsyncHandleSurvivesInitialApplyFailureUntilActualDrain(t *testing.T) {
	owned := ownedExecution(t)
	initialGate, releaseInitial := releaseGate(t)
	workGate, releaseWork := releaseGate(t)
	entered := make(chan context.Context, 1)
	uploadEntered := make(chan context.Context, 1)
	returned := make(chan error, 1)
	initialErr := errors.New("initial original Apply failed")
	uploadErr := errors.New("later original upload failed")
	native := &block.Service{Start: func(ctx context.Context, _ session.Context, _ block.UploadRequest, _ string) (*fileuploader.OwnedUpload, error) {
		handle, err := fileuploader.StartOwnedUpload(ctx, fileuploader.FixturePrepared(context.Background(), nil, func(actual context.Context) fileuploader.UploadResult {
			uploadEntered <- actual
			<-workGate
			return fileuploader.UploadResult{FileObjectId: "late-file", Err: uploadErr}
		}))
		if err != nil {
			return nil, err
		}
		entered <- ctx
		<-initialGate
		return handle, initialErr
	}}
	scoped := ownedImportBlockService{Service: native, owned: owned}
	go func() {
		_, err := scoped.UploadBlockFile(nil, block.UploadRequest{ContextId: "object", BlockId: "file-block"}, "group", false)
		returned <- err
	}()
	if receive(t, entered) != owned.ctx {
		t.Fatal("initial native admission lost owned context")
	}
	actual := receive(t, uploadEntered)
	finished := drain(owned)
	pending(t, finished)
	releaseInitial()
	if !errors.Is(receive(t, returned), initialErr) {
		t.Fatal("initial Apply error was lost")
	}
	owned.cancel()
	receive(t, actual.Done())
	pending(t, finished)
	releaseWork()
	result := receive(t, finished)
	if len(result.files) != 1 || result.files[0].BlockID != "file-block" || result.files[0].FileObjectID != "late-file" || !errors.Is(result.err, initialErr) || !errors.Is(result.err, uploadErr) || !errors.Is(result.err, context.Canceled) {
		t.Fatalf("initial failure discarded actual later completion: %#v", result)
	}
}

func TestMissingAsyncHandleIsRetainedAsFailure(t *testing.T) {
	owned := ownedExecution(t)
	scoped := ownedImportBlockService{Service: &block.Service{Start: func(context.Context, session.Context, block.UploadRequest, string) (*fileuploader.OwnedUpload, error) {
		return nil, nil
	}}, owned: owned}
	_, err := scoped.UploadBlockFile(nil, block.UploadRequest{}, "", false)
	if !errors.Is(err, fileuploader.ErrOwnedUploadCompletion) {
		t.Fatal("missing handle accepted as successful original operation")
	}
	result := receive(t, drain(owned))
	if len(result.files) != 1 || !errors.Is(result.err, fileuploader.ErrOwnedUploadCompletion) {
		t.Fatal("missing-handle failure not retained through final drain")
	}
}

func TestOwnedFileAdapterRejectsSharedPreloadAndUnreviewedSyncRoute(t *testing.T) {
	owned := ownedExecution(t)
	scoped := ownedImportBlockService{Service: &block.Service{}, owned: owned}
	_, _, _, err := scoped.UploadFile(context.Background(), "space", block.FileUploadRequest{PreloadOnly: true})
	if !errors.Is(err, errOwnedImportPreload) {
		t.Fatal("shared preload admitted")
	}
	if _, err := scoped.UploadBlockFile(nil, block.UploadRequest{}, "", true); !errors.Is(err, fileuploader.ErrOwnedUploadUnavailable) {
		t.Fatal("unreviewed synchronous editor upload admitted")
	}
	if len(owned.files) != 0 {
		t.Fatal("rejected route registered or started native work")
	}
}

func TestSealedOperationRejectsLateSyncAndAsyncAdmission(t *testing.T) {
	owned := ownedExecution(t)
	if _, err := owned.sealAndDrain(); err != nil {
		t.Fatal(err)
	}
	scoped := ownedImportBlockService{Service: &block.Service{}, owned: owned}
	_, _, _, err := scoped.UploadFile(context.Background(), "space", block.FileUploadRequest{})
	if !errors.Is(err, errOwnedImportSealed) {
		t.Fatal("late synchronous upload admitted")
	}
	if _, err := scoped.UploadBlockFile(nil, block.UploadRequest{}, "", false); !errors.Is(err, errOwnedImportSealed) {
		t.Fatal("late asynchronous upload admitted")
	}
}

func TestOwnedBlockGettersOverrideBackgroundAndNilContexts(t *testing.T) {
	owned := ownedExecution(t)
	var contexts []context.Context
	var ids []string
	scoped := ownedImportBlockService{Service: &block.Service{
		Get: func(ctx context.Context, id string) (smartblock.SmartBlock, error) { contexts = append(contexts, ctx); ids = append(ids, id); return nil, nil },
		GetFull: func(ctx context.Context, id domain.FullID) (smartblock.SmartBlock, error) { contexts = append(contexts, ctx); ids = append(ids, id.SpaceID+"/"+id.ObjectID); return nil, nil },
	}, owned: owned}
	_, _ = scoped.GetObject(context.Background(), "first")
	_, _ = scoped.GetObjectByFullID(nil, domain.FullID{SpaceID: "space", ObjectID: "second"})
	if len(contexts) != 2 || contexts[0] != owned.ctx || contexts[1] != owned.ctx || ids[0] != "first" || ids[1] != "space/second" {
		t.Fatal("owned getter changed identities or retained unowned context")
	}
}

type blockFixture struct{ block *model.Block }

func (b blockFixture) Model() *model.Block { return b.block }

func TestLiveBookmarkGuardRejectsOnlyUnjoinedFetch(t *testing.T) {
	guard := ownedImportBookmarkSyncer{}
	err := guard.Sync(domain.FullID{}, nil, blockFixture{&model.Block{Bookmark: &model.Bookmark{Url: "https://fixture.invalid/book"}}}, objectorigin.ObjectOrigin{})
	if !errors.Is(err, common.ErrFileLoad) || !errors.Is(err, errOwnedImportBookmark) {
		t.Fatal("live URL fetch was not a typed file-load failure")
	}
	for _, item := range []*model.Block{{}, {Bookmark: &model.Bookmark{}}, {Bookmark: &model.Bookmark{Url: "https://fixture.invalid/book", TargetObjectId: "existing-target"}}} {
		if err := guard.Sync(domain.FullID{}, nil, blockFixture{item}, objectorigin.ObjectOrigin{}); err != nil {
			t.Fatal("already-linked or non-fetch block was rejected")
		}
	}
}

func fileSnapshot(kind sb.SmartBlockType) *common.Snapshot {
	details := domain.NewDetails()
	details.Set("source", "https://fixture.invalid/file")
	details.Set("id", "remote-blob-id")
	return &common.Snapshot{Id: "source-id", Snapshot: &common.NativeSnapshot{SbType: kind, Data: &common.Data{Details: details}}}
}

func TestFileProviderFallbackCannotHideOwnedSynchronousUploadFailure(t *testing.T) {
	owned := ownedExecution(t)
	originalErr := errors.New("provider synchronous upload failed")
	var actualContext context.Context
	native := &block.Service{Upload: func(ctx context.Context, space string, req block.FileUploadRequest) (string, model.BlockContentFileType, *domain.Details, error) {
		actualContext = ctx
		if space != "space" || req.Url != "https://fixture.invalid/file" {
			t.Error("original upload request lost its source/space")
		}
		return "", 0, nil, originalErr
	}}
	scoped := ownedImportBlockService{Service: native, owned: owned}
	provider := objectid.NewIDProviderWithFileUploader(nil, nil, scoped, nil)
	id, _, err := provider.GetIDAndPayload(context.Background(), "space", fileSnapshot(sb.SmartBlockTypeFileObject), time.Time{}, false, objectorigin.ObjectOrigin{})
	if err != nil || id != "fixture-tree-id" || actualContext != owned.ctx {
		t.Fatal("legacy fallback ID/error semantics or scoped context changed")
	}
	result := receive(t, drain(owned))
	if len(result.files) != 1 || !errors.Is(result.err, originalErr) {
		t.Fatal("nil provider error hid the original upload failure")
	}
}

type storeFixture struct{ keys []domain.FileEncryptionKeys }

func (s *storeFixture) AddFileKeys(keys domain.FileEncryptionKeys) error { s.keys = append(s.keys, keys); return nil }

type fileObjectFixture struct{ ids []domain.FullFileId }

func (s *fileObjectFixture) CreateFromImport(id domain.FullFileId, _ objectorigin.ObjectOrigin, _ *domain.Details) (string, error) { s.ids = append(s.ids, id); return "original-file-fallback", nil }

func TestOldFileFallbackAndKeysRemainOriginalWhileUploadErrorIsObserved(t *testing.T) {
	owned := ownedExecution(t)
	originalErr := errors.New("old-file upload failed")
	native := &block.Service{Upload: func(context.Context, string, block.FileUploadRequest) (string, model.BlockContentFileType, *domain.Details, error) { return "", 0, nil, originalErr }}
	store, objects := &storeFixture{}, &fileObjectFixture{}
	provider := objectid.NewIDProviderWithFileUploader(store, nil, ownedImportBlockService{Service: native, owned: owned}, objects)
	snapshot := fileSnapshot(sb.SmartBlockTypeFile)
	snapshot.Snapshot.Data.FileInfo = &common.FileInfo{FileId: "original-file-cid", EncryptionKeys: []common.Key{{Path: "blob-path", Key: "blob-key"}}}
	id, _, err := provider.GetIDAndPayload(context.Background(), "space", snapshot, time.Time{}, false, objectorigin.ObjectOrigin{})
	if err != nil || id != "original-file-fallback" || len(store.keys) != 1 || store.keys[0].FileId != "original-file-cid" || store.keys[0].EncryptionKeys["blob-path"] != "blob-key" || len(objects.ids) != 1 || objects.ids[0].SpaceId != "space" || objects.ids[0].FileId != "original-file-cid" {
		t.Fatal("original key installation/fallback behavior changed")
	}
	if result := receive(t, drain(owned)); len(result.files) != 1 || !errors.Is(result.err, originalErr) {
		t.Fatal("old-file fallback hid owned upload failure")
	}
}

func TestOrdinaryProviderKeepsConcreteDependencyAndFallbackBehavior(t *testing.T) {
	caller := context.WithValue(context.Background(), struct{}{}, "ordinary")
	var actual context.Context
	native := &block.Service{Upload: func(ctx context.Context, _ string, _ block.FileUploadRequest) (string, model.BlockContentFileType, *domain.Details, error) { actual = ctx; return "", 0, nil, errors.New("ordinary original failure") }}
	provider := objectid.NewIDProvider(nil, nil, native, nil)
	id, _, err := provider.GetIDAndPayload(caller, "space", fileSnapshot(sb.SmartBlockTypeFileObject), time.Time{}, false, objectorigin.ObjectOrigin{})
	if actual != caller || id != "fixture-tree-id" || err != nil {
		t.Fatal("ordinary original context or fallback changed")
	}
}

func processor(t *testing.T, service creator.Service) *importProcessor {
	t.Helper()
	return &importProcessor{owned: ownedExecution(t), errors: &common.ConvertError{}, deps: &dependencyFixture{objectCreator: service}, request: &requestFixture{}, response: &responseFixture{}, nativeMapping: &struct{}{}}
}

func dataObject() *creator.DataObject {
	return creator.NewDataObject(context.Background(), nil, nil, nil, objectorigin.ObjectOrigin{}, "space")
}

func TestSuccessfulBatchWaitsOriginalWorkersAndReturnsBothResults(t *testing.T) {
	var calls atomic.Int32
	p := processor(t, creator.FixtureService(func(_ *creator.DataObject, sn *common.Snapshot) (*domain.Details, string, error) {
		calls.Add(1)
		return domain.NewDetails(), "created-" + sn.Id, nil
	}))
	result := p.createOwnedObjectsBatch(dataObject(), []*common.Snapshot{{Id: "a"}, {Id: "b"}})
	if calls.Load() != 2 || len(result) != 2 || result["created-a"] == nil || result["created-b"] == nil || p.errors.Error() != nil || p.nativeMappingBatchesDrained != 1 {
		t.Fatal("original successful worker/result closure was not preserved")
	}
}

func TestPrecancelledBatchDoesNotStartOriginalTasks(t *testing.T) {
	var calls atomic.Int32
	p := processor(t, creator.FixtureService(func(*creator.DataObject, *common.Snapshot) (*domain.Details, string, error) { calls.Add(1); return nil, "", nil }))
	p.owned.cancel()
	result := p.createOwnedObjectsBatch(dataObject(), []*common.Snapshot{{Id: "a"}})
	if result != nil || calls.Load() != 0 || p.nativeMappingBatchesDrained != 0 || !errors.Is(p.errors.Error(), context.Canceled) {
		t.Fatal("cancelled batch started work or manufactured a drained batch")
	}
}

func TestEmptyBatchJoinsOriginalSubmissionAndZeroWorkerClosure(t *testing.T) {
	p := processor(t, creator.FixtureService(func(*creator.DataObject, *common.Snapshot) (*domain.Details, string, error) { panic("empty batch invoked a task") }))
	finished := make(chan map[string]*domain.Details, 1)
	go func() { finished <- p.createOwnedObjectsBatch(dataObject(), nil) }()
	result := receive(t, finished)
	if result == nil || len(result) != 0 || p.nativeMappingBatchesDrained != 1 || p.errors.Error() != nil {
		t.Fatal("empty original channel/submission closure did not complete")
	}
}

func TestCancellationWaitsAllAlreadyExecutingOriginalTasks(t *testing.T) {
	first, releaseFirst := releaseGate(t)
	second, releaseSecond := releaseGate(t)
	entered := make(chan string, 2)
	p := processor(t, creator.FixtureService(func(_ *creator.DataObject, sn *common.Snapshot) (*domain.Details, string, error) {
		entered <- sn.Id
		if sn.Id == "first" { <-first } else { <-second }
		return domain.NewDetails(), "created-" + sn.Id, nil
	}))
	finished := make(chan map[string]*domain.Details, 1)
	go func() { finished <- p.createOwnedObjectsBatch(dataObject(), []*common.Snapshot{{Id: "first"}, {Id: "second"}}) }()
	ids := map[string]bool{receive(t, entered): true}
	ids[receive(t, entered)] = true
	if !ids["first"] || !ids["second"] { t.Fatal("both original workers did not enter") }
	p.owned.cancel()
	pending(t, finished)
	releaseFirst()
	pending(t, finished)
	releaseSecond()
	if result := receive(t, finished); result != nil || !errors.Is(p.errors.Error(), context.Canceled) || p.nativeMappingBatchesDrained != 1 {
		t.Fatal("cancellation acknowledged before original worker/submission drain")
	}
}

func TestFirstTaskFailureWaitsOtherOriginalWorkerBeforeReturning(t *testing.T) {
	failGate, releaseFailure := releaseGate(t)
	slowGate, releaseSlow := releaseGate(t)
	entered := make(chan string, 2)
	originalErr := errors.New("original task failed")
	p := processor(t, creator.FixtureService(func(_ *creator.DataObject, sn *common.Snapshot) (*domain.Details, string, error) {
		entered <- sn.Id
		if sn.Id == "failed" { <-failGate; return nil, "", originalErr }
		<-slowGate
		return domain.NewDetails(), "slow-created", nil
	}))
	finished := make(chan map[string]*domain.Details, 1)
	go func() { finished <- p.createOwnedObjectsBatch(dataObject(), []*common.Snapshot{{Id: "failed"}, {Id: "slow"}}) }()
	receive(t, entered)
	receive(t, entered)
	releaseFailure()
	receive(t, p.owned.ctx.Done())
	pending(t, finished)
	releaseSlow()
	if result := receive(t, finished); result != nil || !errors.Is(p.errors.Error(), originalErr) || p.nativeMappingBatchesDrained != 1 {
		t.Fatal("failed batch lost original failure or returned before other worker drained")
	}
}

func TestFinalizationWaitsActualUploadAndPreservesPriorAndFileErrors(t *testing.T) {
	p := processor(t, nil)
	gate, release := releaseGate(t)
	entered := make(chan struct{}, 1)
	originalErr := errors.New("final upload failure")
	priorErr := errors.New("earlier import failure")
	p.response.Err = priorErr
	native := &block.Service{Start: func(ctx context.Context, _ session.Context, _ block.UploadRequest, _ string) (*fileuploader.OwnedUpload, error) {
		return fileuploader.StartOwnedUpload(ctx, fileuploader.FixturePrepared(context.Background(), nil, func(context.Context) fileuploader.UploadResult {
			entered <- struct{}{}
			<-gate
			return fileuploader.UploadResult{Err: originalErr}
		}))
	}}
	scoped := ownedImportBlockService{Service: native, owned: p.owned}
	if _, err := scoped.UploadBlockFile(nil, block.UploadRequest{}, "", false); err != nil { t.Fatal(err) }
	receive(t, entered)
	finished := make(chan struct{})
	go func() { p.finalizeOwnedImport(p.owned.ctx, "attempt"); close(finished) }()
	pending(t, finished)
	release()
	receive(t, finished)
	if !errors.Is(p.response.Err, priorErr) || !errors.Is(p.response.Err, originalErr) || p.widgetCalls != 0 || p.finishCalls != 1 || p.eventCalls != 1 || len(p.owned.fileResults) != 1 {
		t.Fatal("finalizer replaced errors or published success-side effects")
	}
}

func TestSuccessfulFinalizationRunsOnlyAfterOriginalFileCompletion(t *testing.T) {
	p := processor(t, nil)
	gate, release := releaseGate(t)
	entered := make(chan struct{}, 1)
	native := &block.Service{Upload: func(context.Context, string, block.FileUploadRequest) (string, model.BlockContentFileType, *domain.Details, error) { entered <- struct{}{}; <-gate; return "completed-file", 0, nil, nil }}
	scoped := ownedImportBlockService{Service: native, owned: p.owned}
	returned := make(chan struct{})
	go func() { _, _, _, _ = scoped.UploadFile(nil, "space", block.FileUploadRequest{}); close(returned) }()
	receive(t, entered)
	finished := make(chan struct{})
	go func() { p.finalizeOwnedImport(p.owned.ctx, "attempt"); close(finished) }()
	pending(t, finished)
	release()
	receive(t, returned)
	receive(t, finished)
	if p.response.Err != nil || p.widgetCalls != 1 || p.finishCalls != 1 || p.eventCalls != 1 || len(p.owned.fileResults) != 1 || p.owned.fileResults[0].FileObjectID != "completed-file" {
		t.Fatal("successful finalization did not retain actual completion")
	}
}
