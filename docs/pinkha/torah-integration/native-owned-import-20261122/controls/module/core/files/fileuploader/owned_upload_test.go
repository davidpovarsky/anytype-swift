package fileuploader

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/domain"
)

// These are controlled component callbacks, not native storage or upload mocks
// presented as acceptance. The production channel/collector bodies are exact.
func receive[T any](t *testing.T, c <-chan T) T {
	t.Helper()
	select {
	case value := <-c:
		return value
	case <-time.After(3 * time.Second):
		t.Fatal("controlled callback did not reach the required boundary")
		var zero T
		return zero
	}
}

func pending(t *testing.T, c <-chan struct{}) {
	t.Helper()
	select {
	case <-c:
		t.Fatal("completion published while actual upload callback is held")
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

type foreignUploader struct{}

func (foreignUploader) UploadAsync(context.Context) chan UploadResult {
	panic("foreign uploader must not be invoked")
}

func TestOwnedUploadRejectsUnownedOrInactiveAdmission(t *testing.T) {
	var invoked atomic.Int32
	callback := func(context.Context) UploadResult { invoked.Add(1); return UploadResult{} }
	dead, cancel := context.WithCancel(context.Background())
	cancel()
	var nilNative *uploader
	cases := []struct {
		ctx      context.Context
		prepared Uploader
		expect   error
	}{
		{nil, &uploader{serviceCtx: context.Background(), upload: callback}, ErrOwnedUploadUnavailable},
		{dead, &uploader{serviceCtx: context.Background(), upload: callback}, context.Canceled},
		{context.Background(), foreignUploader{}, ErrOwnedUploadUnavailable},
		{context.Background(), nilNative, ErrOwnedUploadUnavailable},
		{context.Background(), &uploader{upload: callback}, ErrOwnedUploadUnavailable},
		{context.Background(), &uploader{serviceCtx: dead, upload: callback}, ErrOwnedUploadUnavailable},
		{context.Background(), &uploader{serviceCtx: context.Background(), preloadId: "shared-preload", upload: callback}, ErrOwnedUploadUnavailable},
	}
	for index, item := range cases {
		handle, err := StartOwnedUpload(item.ctx, item.prepared)
		if handle != nil || !errors.Is(err, item.expect) {
			t.Fatalf("admission %d returned handle=%v error=%v", index, handle, err)
		}
	}
	if invoked.Load() != 0 {
		t.Fatal("rejected admission executed an upload")
	}
}

func TestOwnedCancellationWaitsForActualCallbackAndReturnsCopiedResult(t *testing.T) {
	gate, release := releaseGate(t)
	entered := make(chan context.Context, 1)
	service := context.Background()
	originalErr := errors.New("controlled original upload failure")
	native := &uploader{serviceCtx: service, upload: func(ctx context.Context) UploadResult {
		entered <- ctx
		<-gate
		return UploadResult{FileObjectId: "actual-callback-file", Name: "document", MIME: "text/plain", Size: 19, Err: originalErr}
	}}
	handle, err := StartOwnedUpload(context.Background(), native)
	if err != nil {
		t.Fatal(err)
	}
	ownedContext := receive(t, entered)
	if _, complete := handle.Result(); complete {
		t.Fatal("result published before callback return")
	}
	handle.RequestCancel()
	handle.RequestCancel()
	receive(t, ownedContext.Done())
	pending(t, handle.Done())
	if service.Err() != nil || native.serviceCtx != service {
		t.Fatal("owned cancellation changed global service or prepared uploader")
	}
	release()
	receive(t, handle.Done())
	result, complete := handle.Result()
	if !complete || !result.CancellationRequested || !errors.Is(result.Err, originalErr) || result.FileObjectID != "actual-callback-file" || result.Name != "document" || result.MIME != "text/plain" || result.Size != 19 {
		t.Fatalf("actual completed outcome lost: %#v, complete=%v", result, complete)
	}
	result.FileObjectID = "caller-mutated-copy"
	again, complete := handle.Result()
	if !complete || again.FileObjectID != "actual-callback-file" {
		t.Fatal("caller mutation changed retained outcome")
	}
}

func TestServiceCancellationPropagatesWithoutPublishingPrematureDrain(t *testing.T) {
	service, cancelService := context.WithCancel(context.Background())
	t.Cleanup(cancelService)
	caller := context.Background()
	gate, release := releaseGate(t)
	entered := make(chan context.Context, 1)
	handle, err := StartOwnedUpload(caller, &uploader{serviceCtx: service, upload: func(ctx context.Context) UploadResult {
		entered <- ctx
		<-gate
		return UploadResult{FileObjectId: "completed-after-service-stop"}
	}})
	if err != nil {
		t.Fatal(err)
	}
	actual := receive(t, entered)
	cancelService()
	receive(t, actual.Done())
	pending(t, handle.Done())
	if caller.Err() != nil {
		t.Fatal("service cancellation escaped into the caller context")
	}
	release()
	receive(t, handle.Done())
	result, complete := handle.Result()
	if !complete || !result.CancellationRequested || result.FileObjectID != "completed-after-service-stop" {
		t.Fatalf("wrong completion: %#v", result)
	}
}

func TestLegacyUploadAsyncStillUsesOriginalServiceContext(t *testing.T) {
	service := context.WithValue(context.Background(), struct{}{}, "service")
	caller, cancel := context.WithCancel(context.Background())
	cancel()
	entered := make(chan context.Context, 1)
	native := &uploader{serviceCtx: service, upload: func(ctx context.Context) UploadResult {
		entered <- ctx
		return UploadResult{FileObjectId: "legacy-result"}
	}}
	channel := native.UploadAsync(caller)
	if actual := receive(t, entered); actual != service || actual.Err() != nil {
		t.Fatal("legacy entry changed to caller cancellation context")
	}
	if result := receive(t, channel); result.FileObjectId != "legacy-result" {
		t.Fatal("original result channel lost its result")
	}
	select {
	case _, open := <-channel:
		if open {
			t.Fatal("original result channel did not close")
		}
	case <-time.After(3 * time.Second):
		t.Fatal("original result channel remained open")
	}
}

func TestZeroOrNilOwnedHandleCannotManufactureCompletion(t *testing.T) {
	var nilHandle *OwnedUpload
	for _, handle := range []*OwnedUpload{nilHandle, {}} {
		handle.RequestCancel()
		if handle.Done() != nil {
			t.Fatal("uninitialized handle has a completion channel")
		}
		if _, complete := handle.Result(); complete {
			t.Fatal("uninitialized handle claims a completed upload")
		}
	}
}

type objectGetterFixture struct {
	contexts []context.Context
	ids      []string
}

func (g *objectGetterFixture) GetObject(ctx context.Context, id string) (smartblock.SmartBlock, error) {
	g.contexts = append(g.contexts, ctx)
	g.ids = append(g.ids, id)
	return "object", nil
}

func (g *objectGetterFixture) GetObjectByFullID(ctx context.Context, id domain.FullID) (smartblock.SmartBlock, error) {
	g.contexts = append(g.contexts, ctx)
	g.ids = append(g.ids, id.SpaceID+"/"+id.ObjectID)
	return "full-object", nil
}

func TestOwnedObjectGetterBindsBothOriginalLookupRoutes(t *testing.T) {
	owned, cancel := context.WithCancel(context.Background())
	t.Cleanup(cancel)
	original := &objectGetterFixture{}
	getter := ownedUploadObjectGetter{original: original, ctx: owned}
	if _, err := getter.GetObject(context.Background(), "object-a"); err != nil {
		t.Fatal(err)
	}
	if _, err := getter.GetObjectByFullID(nil, domain.FullID{SpaceID: "space", ObjectID: "object-b"}); err != nil {
		t.Fatal(err)
	}
	if len(original.contexts) != 2 || original.contexts[0] != owned || original.contexts[1] != owned || original.ids[0] != "object-a" || original.ids[1] != "space/object-b" {
		t.Fatal("original getter did not receive the exact owned contexts and identities")
	}
}

func TestSuccessfulOwnedUploadDoesNotInventCancellation(t *testing.T) {
	native := &uploader{serviceCtx: context.Background(), upload: func(context.Context) UploadResult {
		return UploadResult{FileObjectId: "successful-result"}
	}}
	handle, err := StartOwnedUpload(context.Background(), native)
	if err != nil {
		t.Fatal(err)
	}
	receive(t, handle.Done())
	result, complete := handle.Result()
	if !complete || result.CancellationRequested || result.Err != nil || result.FileObjectID != "successful-result" {
		t.Fatalf("unexpected normal outcome: %#v", result)
	}
}
