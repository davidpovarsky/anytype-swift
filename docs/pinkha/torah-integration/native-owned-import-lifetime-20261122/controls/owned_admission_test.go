package application

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/application/accountdirlock"
	importer "github.com/anyproto/anytype-heart/core/block/import"
	walletComp "github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
)

func awaitSignal(t *testing.T, signal <-chan struct{}) {
	t.Helper()
	select {
	case <-signal:
	case <-time.After(3 * time.Second):
		t.Fatal("controlled boundary did not complete")
	}
}

func awaitEntry(t *testing.T, execution *importer.FixtureExecution) context.Context {
	t.Helper()
	select {
	case ctx := <-execution.Entered:
		return ctx
	case <-time.After(3 * time.Second):
		t.Fatal("controlled Execute was not entered")
		return nil
	}
}

func expectPending(t *testing.T, operation *importer.OwnedImportOperation) {
	t.Helper()
	select {
	case <-operation.Done():
		t.Fatal("operation completed before actual fixture Execute returned")
	default:
	}
	if _, complete := operation.Result(); complete { t.Fatal("premature result") }
}

func applicationFixture(t *testing.T, plans ...*importer.FixtureExecution) (*Service, *app.App, *importer.FixtureController, *importer.ImportRequest, *accountdirlock.Lease) {
	t.Helper()
	for _, plan := range plans { t.Cleanup(plan.Finish) }
	controller := &importer.FixtureController{Plans: plans}
	wallet := &walletComp.Fixture{AccountID: "actual-wallet-fixture", Root: "fixture-root"}
	a := &app.App{Components: map[string]any{importer.FixtureComponentName: controller, walletComp.CName: wallet}}
	lease := &accountdirlock.Lease{Root: wallet.Root, AccountID: wallet.AccountID, IsUsable: true}
	service := &Service{app: a, accountLease: lease}
	request := &importer.ImportRequest{RpcObjectImportRequest: &pb.RpcObjectImportRequest{SpaceId: "declared-space"}, IsSync: true}
	return service, a, controller, request, lease
}

func start(t *testing.T, service *Service, a *app.App, request *importer.ImportRequest, ctx context.Context) *ownedAccountImport {
	t.Helper()
	owned, err := service.startOwnedImport(ctx, a, "actual-wallet-fixture", request)
	if err != nil { t.Fatal(err) }
	return owned
}

func TestAdmissionRejectsWrongOwnerBeforeConstruction(t *testing.T) {
	for _, scenario := range []string{"nil-app", "wrong-app", "wrong-account", "missing-wallet", "missing-lease", "wrong-lease-root", "wrong-lease-account", "unusable-lease", "cancelled-context", "nil-request"} {
		execution := importer.NewFixtureExecution()
		service, a, controller, request, lease := applicationFixture(t, execution)
		expected, account, ctx := a, "actual-wallet-fixture", context.Background()
		switch scenario {
		case "nil-app": service.app = nil
		case "wrong-app": expected = &app.App{}
		case "wrong-account": account = "foreign-account"
		case "missing-wallet": delete(a.Components, walletComp.CName)
		case "missing-lease": service.accountLease = nil
		case "wrong-lease-root": lease.Root = "foreign-root"
		case "wrong-lease-account": lease.AccountID = "foreign-account"
		case "unusable-lease": lease.IsUsable = false
		case "cancelled-context": cancelled, cancel := context.WithCancel(ctx); cancel(); ctx = cancelled
		case "nil-request": request = nil
		}
		owned, err := service.prepareOwnedAccountImport(ctx, expected, account, request)
		if owned != nil || err == nil || controller.Calls() != 0 || execution.ExecuteCalls.Load() != 0 {
			t.Fatal("invalid ownership reached construction: " + scenario)
		}
	}
}

func TestAdmissionDoesNotQueueBehindExistingWriter(t *testing.T) {
	execution := importer.NewFixtureExecution()
	service, a, controller, request, _ := applicationFixture(t, execution)
	service.lock.Lock()
	defer service.lock.Unlock()
	returned := make(chan error, 1)
	go func() { _, err := service.prepareOwnedAccountImport(context.Background(), a, "actual-wallet-fixture", request); returned <- err }()
	select {
	case err := <-returned:
		if !errors.Is(err, ErrOwnedImportAdmissionUnavailable) || controller.Calls() != 0 { t.Fatal("busy writer admission did not fail closed") }
	case <-time.After(3 * time.Second):
		t.Fatal("new admission queued behind a writer")
	}
}

func TestRegistrationPrecedesStartAndCancellationDoesNotForgeDrain(t *testing.T) {
	execution := importer.NewFixtureExecution()
	service, a, _, request, lease := applicationFixture(t, execution)
	owned, err := service.prepareOwnedAccountImport(context.Background(), a, "actual-wallet-fixture", request)
	if err != nil { t.Fatal(err) }
	if len(service.ownedImports.operations) != 1 || execution.ExecuteCalls.Load() != 0 || owned.app != a || owned.accountID != "actual-wallet-fixture" || owned.spaceID != "declared-space" {
		t.Fatal("operation was not registered before dispatch")
	}
	if !errors.Is(service.Stop(), ErrOwnedImportDrainPending) { t.Fatal("pre-start stop reported completion") }
	if service.GetApp() != a || lease.Releases != 0 || service.closeCalls != 0 { t.Fatal("pre-start stop retired native owner") }
	expectPending(t, owned.operation)
	owned.operation.Start()
	ctx := awaitEntry(t, execution)
	if !errors.Is(ctx.Err(), context.Canceled) { t.Fatal("registered pre-start operation was not cancelled") }
	expectPending(t, owned.operation)
	execution.Finish(); awaitSignal(t, owned.operation.Done())
	if err := service.Stop(); err != nil { t.Fatal(err) }
	if service.GetApp() != nil || lease.Releases != 1 || service.closeCalls != 1 { t.Fatal("retry did not retire after actual return") }
}

func TestStopPreservesAppAndLeaseUntilActualReturn(t *testing.T) {
	execution := importer.NewFixtureExecution()
	service, a, _, request, lease := applicationFixture(t, execution)
	owned := start(t, service, a, request, context.Background())
	ctx := awaitEntry(t, execution)
	if !errors.Is(service.Stop(), ErrOwnedImportDrainPending) { t.Fatal("stop accepted an undrained import") }
	awaitSignal(t, ctx.Done())
	if service.GetApp() != a || service.accountLease != lease || lease.Releases != 0 || service.closeCalls != 0 { t.Fatal("app or lease released before actual return") }
	expectPending(t, owned.operation)
	execution.Finish(); awaitSignal(t, owned.operation.Done())
	if err := service.Stop(); err != nil { t.Fatal(err) }
	if lease.Releases != 1 || service.accountLease != nil || len(service.ownedImports.operations) != 0 { t.Fatal("completed operation was not pruned before stop") }
}

func TestRemoveDataCannotDispatchWhileImportIsPending(t *testing.T) {
	execution := importer.NewFixtureExecution()
	service, a, _, request, lease := applicationFixture(t, execution)
	owned := start(t, service, a, request, context.Background()); awaitEntry(t, execution)
	stop := &pb.RpcAccountStopRequest{RemoveData: true}
	if !errors.Is(service.AccountStop(stop), ErrOwnedImportDrainPending) || service.removeCalls != 0 || lease.Releases != 0 { t.Fatal("data removal dispatched before drain") }
	execution.Finish(); awaitSignal(t, owned.operation.Done())
	if err := service.AccountStop(stop); err != nil { t.Fatal(err) }
	if service.removeCalls != 1 || lease.Releases != 1 { t.Fatal("drained retry did not reach original removal route fixture") }
}

func TestReentrantStopInsideExecuteDoesNotJoinItself(t *testing.T) {
	execution := importer.NewFixtureExecution()
	service, a, _, request, _ := applicationFixture(t, execution)
	callback := make(chan error, 1)
	execution.EnterHook = func(context.Context) {
		if service.GetApp() != a { callback <- errors.New("app vanished inside callback"); return }
		callback <- service.Stop()
	}
	owned := start(t, service, a, request, context.Background()); awaitEntry(t, execution)
	select {
	case err := <-callback:
		if !errors.Is(err, ErrOwnedImportDrainPending) { t.Fatal("reentrant stop result differs", err) }
	case <-time.After(3 * time.Second):
		t.Fatal("Stop joined its own importing callback")
	}
	if service.GetApp() != a || service.closeCalls != 0 { t.Fatal("callback retired owner before return") }
	expectPending(t, owned.operation)
	execution.Finish(); awaitSignal(t, owned.operation.Done())
}

func TestPendingRetirementBlocksNewAdmissionUntilLifecycleRetry(t *testing.T) {
	first, next := importer.NewFixtureExecution(), importer.NewFixtureExecution()
	service, a, controller, request, _ := applicationFixture(t, first, next)
	one := start(t, service, a, request, context.Background()); awaitEntry(t, first)
	if !errors.Is(service.Stop(), ErrOwnedImportDrainPending) { t.Fatal("pending stop missing") }
	first.Finish(); awaitSignal(t, one.operation.Done())
	if _, err := service.prepareOwnedAccountImport(context.Background(), a, "actual-wallet-fixture", request); !errors.Is(err, ErrOwnedImportAdmissionUnavailable) || controller.Calls() != 1 { t.Fatal("new admission bypassed pending lifecycle retry") }
	release, err := service.beginOwnedImportRetirement(); if err != nil { t.Fatal(err) }; release()
	two := start(t, service, a, request, context.Background()); awaitEntry(t, next)
	next.Finish(); awaitSignal(t, two.operation.Done())
}

func TestRetirementCountBlocksUntilEveryLegacyReservationFinishes(t *testing.T) {
	execution := importer.NewFixtureExecution()
	service, a, controller, request, _ := applicationFixture(t, execution)
	first, err := service.beginOwnedImportRetirement(); if err != nil { t.Fatal(err) }
	second, err := service.beginOwnedImportRetirement(); if err != nil { t.Fatal(err) }
	if service.ownedImports.retirements != 2 { t.Fatal("overlapping lifecycle reservation rejected") }
	first(); first()
	if service.ownedImports.retirements != 1 { t.Fatal("one reservation was released more than once") }
	if _, err := service.prepareOwnedAccountImport(context.Background(), a, "actual-wallet-fixture", request); !errors.Is(err, ErrOwnedImportAdmissionUnavailable) || controller.Calls() != 0 { t.Fatal("admission ignored remaining lifecycle") }
	second()
	owned := start(t, service, a, request, context.Background()); awaitEntry(t, execution)
	execution.Finish(); awaitSignal(t, owned.operation.Done())
}

func TestConcurrentRetirementsPreserveOriginalStartSupersession(t *testing.T) {
	service := &Service{}
	first, err := service.beginOwnedImportRetirement(); if err != nil { t.Fatal(err) }; defer first()
	firstCtx, firstEnd := service.beginStart(context.Background())
	second, err := service.beginOwnedImportRetirement(); if err != nil { t.Fatal(err) }; defer second()
	secondCtx, secondEnd := service.beginStart(context.Background())
	if !errors.Is(firstCtx.Err(), context.Canceled) || secondCtx.Err() != nil { t.Fatal("newer start failed to supersede old start") }
	service.lock.Lock(); firstEnd(); service.lock.Unlock()
	if service.starting == nil || service.starting.ctx != secondCtx { t.Fatal("old completion cleared newer start") }
	if !service.cancelStart() { t.Fatal("newer start was not cancellable") }
	awaitSignal(t, secondCtx.Done())
	service.lock.Lock(); secondEnd(); service.lock.Unlock()
	if service.starting != nil { t.Fatal("cancelled start was not retracted") }
}

func TestAccountStopFastCancellationRemainsBeforeWriterLock(t *testing.T) {
	service := &Service{}
	ctx, end := service.beginStart(context.Background())
	service.lock.Lock()
	defer service.lock.Unlock()
	returned := make(chan error, 1)
	go func() { returned <- service.AccountStop(&pb.RpcAccountStopRequest{}) }()
	select {
	case err := <-returned:
		if err != nil { t.Fatal(err) }
	case <-time.After(3 * time.Second):
		t.Fatal("AccountStop waited behind the start writer")
	}
	awaitSignal(t, ctx.Done())
	if service.closeCalls != 0 || service.ownedImports.retirements != 0 { t.Fatal("fast cancellation changed original cleanup owner") }
	end()
}

func TestEveryRegisteredOperationMustReturnBeforeRetirement(t *testing.T) {
	first, second := importer.NewFixtureExecution(), importer.NewFixtureExecution()
	service, a, _, request, lease := applicationFixture(t, first, second)
	one := start(t, service, a, request, context.Background()); firstCtx := awaitEntry(t, first)
	two := start(t, service, a, request, context.Background()); secondCtx := awaitEntry(t, second)
	if !errors.Is(service.Stop(), ErrOwnedImportDrainPending) { t.Fatal("parallel imports not retained") }
	awaitSignal(t, firstCtx.Done()); awaitSignal(t, secondCtx.Done())
	first.Finish(); awaitSignal(t, one.operation.Done())
	if !errors.Is(service.Stop(), ErrOwnedImportDrainPending) || service.GetApp() != a || lease.Releases != 0 { t.Fatal("one completed import released another's native owner") }
	expectPending(t, two.operation)
	second.Finish(); awaitSignal(t, two.operation.Done())
	if err := service.Stop(); err != nil { t.Fatal(err) }
	if lease.Releases != 1 || service.closeCalls != 1 { t.Fatal("all-drained retirement did not finish once") }
}

func TestParentCancellationCannotManufactureLifecycleCompletion(t *testing.T) {
	execution := importer.NewFixtureExecution()
	service, a, _, request, lease := applicationFixture(t, execution)
	ctx, cancel := context.WithCancel(context.Background()); defer cancel()
	owned := start(t, service, a, request, ctx); nativeCtx := awaitEntry(t, execution)
	cancel(); awaitSignal(t, nativeCtx.Done())
	expectPending(t, owned.operation)
	if !errors.Is(service.Stop(), ErrOwnedImportDrainPending) || lease.Releases != 0 { t.Fatal("parent cancellation forged completed drain") }
	execution.Finish(); awaitSignal(t, owned.operation.Done())
	if err := service.Stop(); err != nil { t.Fatal(err) }
}
