package importer

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/pb"
)

func requireSignal(t *testing.T, signal <-chan struct{}) {
	t.Helper()
	select {
	case <-signal:
	case <-time.After(3 * time.Second):
		t.Fatal("controlled execution did not reach its expected boundary")
	}
}

func entered(t *testing.T, execution *FixtureExecution) context.Context {
	t.Helper()
	select {
	case ctx := <-execution.Entered:
		return ctx
	case <-time.After(3 * time.Second):
		t.Fatal("controlled Execute was not entered")
		return nil
	}
}

func notCompleted(t *testing.T, operation *OwnedImportOperation) {
	t.Helper()
	select {
	case <-operation.Done():
		t.Fatal("operation reported completion before Execute returned")
	default:
	}
	if _, complete := operation.Result(); complete {
		t.Fatal("result was available before actual Execute return")
	}
}

func operationFixture(t *testing.T, parent context.Context, plans ...*FixtureExecution) (*app.App, *FixtureController, *ImportRequest) {
	t.Helper()
	for _, plan := range plans {
		t.Cleanup(plan.Finish)
	}
	controller := &FixtureController{Plans: plans}
	a := &app.App{Components: map[string]any{FixtureComponentName: controller}}
	return a, controller, &ImportRequest{RpcObjectImportRequest: &pb.RpcObjectImportRequest{SpaceId: "declared-space"}, IsSync: true}
}

func TestZeroOperationCannotReportCompletion(t *testing.T) {
	for _, operation := range []*OwnedImportOperation{nil, {}} {
		operation.Start()
		operation.RequestCancel()
		if operation.Done() != nil || operation.TargetSpaceID() != "" {
			t.Fatal("zero operation acquired a completion/destination identity")
		}
		if _, complete := operation.Result(); complete {
			t.Fatal("zero operation supplied a result")
		}
	}
}

func TestPrepareRejectsMissingOrCancelledOwnerBeforeConstructor(t *testing.T) {
	execution := NewFixtureExecution()
	a, controller, request := operationFixture(t, context.Background(), execution)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	for _, input := range []struct{ ctx context.Context; app *app.App }{{nil, a}, {context.Background(), nil}, {ctx, a}} {
		operation, err := PrepareOwnedImport(input.ctx, input.app, request)
		if err == nil || operation != nil {
			t.Fatal("invalid owner was prepared")
		}
	}
	if controller.Calls() != 0 {
		t.Fatal("invalid owner reached constructor")
	}
}

func TestPrepareErrorCancelsOnlyDerivedContext(t *testing.T) {
	parent, cancel := context.WithCancel(context.Background())
	defer cancel()
	a, controller, request := operationFixture(t, parent)
	wanted := errors.New("controlled constructor failure")
	controller.PrepareError = wanted
	operation, err := PrepareOwnedImport(parent, a, request)
	if operation != nil || !errors.Is(err, wanted) || controller.Calls() != 1 {
		t.Fatal("constructor failure was not preserved")
	}
	if !errors.Is(controller.PreparedContexts[0].Err(), context.Canceled) || parent.Err() != nil {
		t.Fatal("failed preparation did not release only its derived context")
	}
}

func TestPreparedTargetIsCopiedBeforeCallerMutation(t *testing.T) {
	execution := NewFixtureExecution()
	a, _, request := operationFixture(t, context.Background(), execution)
	operation, err := PrepareOwnedImport(context.Background(), a, request)
	if err != nil { t.Fatal(err) }
	request.SpaceId = "caller-changed-space"
	if operation.TargetSpaceID() != "declared-space" || execution.ExecuteCalls.Load() != 0 {
		t.Fatal("preparation executed work or reread caller target")
	}
	operation.Start()
	entered(t, execution)
	execution.Finish()
	requireSignal(t, operation.Done())
	result, complete := operation.Result()
	if !complete || result.TargetSpaceID() != "declared-space" || result.Err() != nil {
		t.Fatal("copied target was not retained through completion")
	}
}

func TestConcurrentStartRunsExactlyOneExecuteAndWaitsForReturn(t *testing.T) {
	execution := NewFixtureExecution()
	a, _, request := operationFixture(t, context.Background(), execution)
	operation, err := PrepareOwnedImport(context.Background(), a, request)
	if err != nil { t.Fatal(err) }
	var group sync.WaitGroup
	for range 24 {
		group.Add(1)
		go func() { defer group.Done(); operation.Start() }()
	}
	group.Wait()
	entered(t, execution)
	notCompleted(t, operation)
	if execution.ExecuteCalls.Load() != 1 { t.Fatal("Execute count differs") }
	execution.Finish()
	requireSignal(t, operation.Done())
	operation.Start()
	result, complete := operation.Result()
	if !complete || result.ProcessID() != "fixture-process" || result.RootCollectionID() != "fixture-root" || result.ObjectsCount() != 2 || result.CancellationRequested() || execution.ExecuteCalls.Load() != 1 {
		t.Fatal("actual completion facts or Start ownership differ")
	}
}

func TestCancellationBeforeStartStillWaitsForExecuteReturn(t *testing.T) {
	execution := NewFixtureExecution()
	a, _, request := operationFixture(t, context.Background(), execution)
	operation, err := PrepareOwnedImport(context.Background(), a, request)
	if err != nil { t.Fatal(err) }
	operation.RequestCancel()
	notCompleted(t, operation)
	operation.Start()
	ctx := entered(t, execution)
	if !errors.Is(ctx.Err(), context.Canceled) { t.Fatal("pre-start cancellation lost") }
	notCompleted(t, operation)
	execution.Finish()
	requireSignal(t, operation.Done())
	result, complete := operation.Result()
	if !complete || !result.CancellationRequested() { t.Fatal("cancelled completion was not reported") }
}

func TestCancellationDuringExecuteIsRequestUntilActualReturn(t *testing.T) {
	execution := NewFixtureExecution()
	a, _, request := operationFixture(t, context.Background(), execution)
	operation, err := PrepareOwnedImport(context.Background(), a, request)
	if err != nil { t.Fatal(err) }
	operation.Start()
	ctx := entered(t, execution)
	operation.RequestCancel()
	requireSignal(t, ctx.Done())
	notCompleted(t, operation)
	execution.Finish()
	requireSignal(t, operation.Done())
	result, complete := operation.Result()
	if !complete || !result.CancellationRequested() { t.Fatal("actual cancelled completion missing") }
}

func TestNilExecuteResponseIsUnavailableAfterReturn(t *testing.T) {
	execution := NewFixtureExecution()
	execution.Response = nil
	a, _, request := operationFixture(t, context.Background(), execution)
	operation, err := PrepareOwnedImport(context.Background(), a, request)
	if err != nil { t.Fatal(err) }
	operation.Start()
	entered(t, execution)
	execution.Finish()
	requireSignal(t, operation.Done())
	result, complete := operation.Result()
	if !complete || !errors.Is(result.Err(), ErrOwnedImportOperationUnavailable) { t.Fatal("nil response became success") }
}

func TestOutcomeReturnsIndependentCopiesOfRetainedSlices(t *testing.T) {
	execution := NewFixtureExecution()
	execution.Files = []OwnedImportFileObservation{{Kind: "fixture-file", FileObjectID: "native-choice-fixture"}}
	execution.Response.nativeMapping = &NativeProtobufImportMappingObservation{complete: true, sources: []NativeProtobufSourceAssignment{{SourceObjectID: "source-fixture", NativeID: "destination-fixture"}}}
	execution.Response.nativeMappingProblems = []string{"diagnostic-fixture"}
	a, _, request := operationFixture(t, context.Background(), execution)
	operation, err := PrepareOwnedImport(context.Background(), a, request)
	if err != nil { t.Fatal(err) }
	operation.Start(); entered(t, execution); execution.Finish(); requireSignal(t, operation.Done())
	result, _ := operation.Result()
	files := result.Files(); files[0].FileObjectID = "mutated"
	problems := result.NativeMappingProblems(); problems[0] = "mutated"
	mapping, ok := result.NativeMappingObservation()
	if !ok { t.Fatal("controlled mapping response was not retained") }
	mapping.sources[0].NativeID = "mutated"
	again, _ := operation.Result()
	mapAgain, _ := again.NativeMappingObservation()
	if again.Files()[0].FileObjectID != "native-choice-fixture" || again.NativeMappingProblems()[0] != "diagnostic-fixture" || mapAgain.SourceAssignments()[0].NativeID != "destination-fixture" {
		t.Fatal("returned slice mutation changed retained outcome")
	}
}

func TestChangedProcessorTargetFailsClosedAtReturn(t *testing.T) {
	execution := NewFixtureExecution(); execution.MutateTarget = "unexpected-target"
	a, _, request := operationFixture(t, context.Background(), execution)
	operation, err := PrepareOwnedImport(context.Background(), a, request)
	if err != nil { t.Fatal(err) }
	operation.Start(); entered(t, execution); execution.Finish(); requireSignal(t, operation.Done())
	result, complete := operation.Result()
	if !complete || result.TargetSpaceID() != "declared-space" || !errors.Is(result.Err(), ErrOwnedImportOperationUnavailable) { t.Fatal("changed processor destination escaped error") }
}

func TestCancellationIsIsolatedToOneOwnedOperation(t *testing.T) {
	first, second := NewFixtureExecution(), NewFixtureExecution()
	a, _, request := operationFixture(t, context.Background(), first, second)
	one, err := PrepareOwnedImport(context.Background(), a, request); if err != nil { t.Fatal(err) }
	two, err := PrepareOwnedImport(context.Background(), a, request); if err != nil { t.Fatal(err) }
	one.Start(); two.Start()
	firstCtx, secondCtx := entered(t, first), entered(t, second)
	one.RequestCancel(); requireSignal(t, firstCtx.Done())
	if secondCtx.Err() != nil { t.Fatal("one cancellation affected another operation") }
	first.Finish(); requireSignal(t, one.Done()); notCompleted(t, two)
	second.Finish(); requireSignal(t, two.Done())
	result, _ := two.Result()
	if result.CancellationRequested() { t.Fatal("uncancelled operation acquired cancellation") }
}
