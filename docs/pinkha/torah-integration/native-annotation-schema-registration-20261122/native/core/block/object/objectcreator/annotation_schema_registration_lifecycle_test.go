package objectcreator_test

import (
	"context"
	"errors"
	"fmt"
	"runtime"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/list/listtest"

	"github.com/anyproto/anytype-heart/core/anytype/config"
	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema"
	walletComp "github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

func registrationReaderRole(t *testing.T, f *nativeSchemaFixture) {
	t.Helper()
	spc := f.regularSpace(t)
	other := newNativeSchemaFixture(t)
	otherIdentity := app.MustComponent[accountservice.Service](other.service.GetApp()).Account().SignKey.GetPublic()
	if !app.MustComponent[*config.Config](f.service.GetApp()).IsLocalOnlyMode() {
		t.Fatal("signed ACL role control requires the original disposable LocalOnly runtime")
	}
	acl := spc.CommonSpace().Acl()
	err := func() error {
		acl.Lock()
		defer acl.Unlock()
		add, err := acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{{
			Identity: otherIdentity, Permissions: list.AclPermissionsAdmin,
		}}})
		if err != nil {
			return err
		}
		if err = acl.AddRawRecord(listtest.WrapAclRecord(add)); err != nil {
			return err
		}
		transfer, err := acl.RecordBuilder().BuildOwnershipChange(list.OwnershipChangePayload{
			NewOwner: otherIdentity, OldOwnerPermissions: list.AclPermissionsReader,
		})
		if err != nil {
			return err
		}
		if err = acl.AddRawRecord(listtest.WrapAclRecord(transfer)); err != nil {
			return err
		}
		if acl.AclState().Permissions(spc.GetAclIdentity()) != list.AclPermissionsReader ||
			acl.AclState().Permissions(otherIdentity) != list.AclPermissionsOwner {
			return fmt.Errorf("actual signed ACL ingestion did not establish the reader role")
		}
		return nil
	}()
	nativeSchemaNoError(t, err)
	result, err := annotationschema.Register(f.ctx, f.service, registrationAccount(f), spc.Id())
	if !errors.Is(err, list.ErrInsufficientPermissions) || len(result.Creations) != 0 || result.TypeApplyInvoked {
		t.Fatalf("actual native reader admitted registration: %v %+v", err, result)
	}
	registrationOnlyExistingRoots(t, f, spc, nil)
}

func registrationQueuedLifecycle(t *testing.T, stop bool) {
	t.Helper()
	f := newNativeSchemaFixture(t)
	spc := f.regularSpace(t)
	nativeApp := f.service.GetApp()
	accountID := registrationAccount(f)
	rootPath := app.MustComponent[walletComp.Wallet](nativeApp).RootPath()
	selectRequest := &pb.RpcAccountSelectRequest{Id: accountID, RootPath: rootPath,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly}
	// A stopped fixture is reopened before the original fixture's cleanup,
	// even if a later assertion fails. No live or unrelated directory is used.
	if stop {
		t.Cleanup(func() {
			if f.service.GetApp() == nil {
				_, err := f.service.AccountSelect(f.ctx, selectRequest)
				if err != nil {
					t.Errorf("restore owned stopped fixture for cleanup: %v", err)
				}
			}
		})
	}
	name := "AccountSelect"
	suffix := "registrationqueuedselect"
	if stop {
		name, suffix = "AccountStop", "registrationqueuedstop"
	}
	definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, suffix)
	creator := f.creator.(objectcreator.FixedSchemaCreator)
	operationContext, cancel := context.WithCancel(f.ctx)
	defer cancel()
	lifecycleDone := make(chan error, 1)
	var createdID string
	var originalReadback objectcreator.FixedSchemaObservation
	entered, operationErr := f.service.WithActiveApp(operationContext, nativeApp, func(retained *app.App) error {
		if retained != nativeApp {
			return errors.New("lease did not retain the exact native application")
		}
		go func() {
			if stop {
				lifecycleDone <- f.service.AccountStop(&pb.RpcAccountStopRequest{})
			} else {
				_, err := f.service.AccountSelect(f.ctx, selectRequest)
				lifecycleDone <- err
			}
		}()
		// Observe the real Go writer blocked in the original lifecycle method,
		// then execute the actual create/Apply path behind that queued writer.
		// A mere goroutine-start signal would not establish RWMutex contention.
		if err := registrationWaitQueuedWriter(operationContext, name, lifecycleDone); err != nil {
			return err
		}
		t.Logf("observed original %s queued at sync.RWMutex.Lock before native writes", name)
		created, err := creator.CreateFixedSchemaOnce(operationContext, spc, accountID, definition)
		createdID = created.ReturnedObjectID
		if err != nil {
			return err
		}
		if !created.Invoked || createdID == "" || createdID != created.Before.ObjectID {
			return errors.New("original retained-Space create was not executed")
		}
		err = spc.DoCtx(operationContext, createdID, func(object smartblock.SmartBlock) error {
			st := object.NewState()
			st.SetDetailAndBundledRelation(bundle.RelationKeyDescription, domain.String("native write completed behind queued "+name))
			return object.Apply(st)
		})
		if err != nil {
			return err
		}
		originalReadback, err = registrationDirectRead(operationContext, f.observer, spc, definition)
		if err != nil {
			return err
		}
		select {
		case err := <-lifecycleDone:
			return fmt.Errorf("lifecycle returned before the admitted native operation drained: %v", err)
		default:
		}
		if stop {
			// Cancellation after both actual writes must retain entered=true and
			// return cancellation, while Stop continues waiting for the RUnlock.
			cancel()
		}
		return nil
	})
	if !entered || (stop && !errors.Is(operationErr, context.Canceled)) || (!stop && operationErr != nil) {
		t.Fatalf("original native work did not drain correctly: entered=%t error=%v", entered, operationErr)
	}
	select {
	case err := <-lifecycleDone:
		nativeSchemaNoError(t, err)
	case <-time.After(45 * time.Second):
		t.Fatal("queued original account lifecycle did not finish after native drain")
	}
	if stop {
		if f.service.GetApp() != nil {
			t.Fatal("original AccountStop did not retire the native application")
		}
		_, err := f.service.AccountSelect(f.ctx, selectRequest)
		nativeSchemaNoError(t, err)
		if f.service.GetApp() == nativeApp {
			t.Fatal("original account reopen retained a retired application pointer")
		}
		called := false
		entered, err := f.service.WithActiveApp(f.ctx, nativeApp, func(*app.App) error { called = true; return nil })
		if entered || called || !errors.Is(err, application.ErrActiveAppChanged) {
			t.Fatal("an equal-account replacement revived an old native application lease")
		}
	}
	currentApp := f.service.GetApp()
	currentSpace, err := app.MustComponent[space.Service](currentApp).Get(f.ctx, spc.Id())
	nativeSchemaNoError(t, err)
	currentObserver := app.MustComponent[objectcreator.Service](currentApp).(objectcreator.FixedSchemaObserver)
	after, err := registrationDirectRead(f.ctx, currentObserver, currentSpace, definition)
	nativeSchemaNoError(t, err)
	details, _ := after.CopyPersistedSchemaState()
	if after.ObjectID != createdID || details == nil ||
		details.Fields[bundle.RelationKeyDescription.String()].GetStringValue() != "native write completed behind queued "+name {
		t.Fatal("actual admitted native content was lost after lifecycle completion")
	}
	registrationSameNative(t, originalReadback, after)
}

func registrationStopDuringQueuedSelect(t *testing.T) {
	t.Helper()
	f := newNativeSchemaFixture(t)
	spc := f.regularSpace(t)
	nativeApp := f.service.GetApp()
	accountID := registrationAccount(f)
	rootPath := app.MustComponent[walletComp.Wallet](nativeApp).RootPath()
	selectRequest := &pb.RpcAccountSelectRequest{Id: accountID, RootPath: rootPath,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly}
	t.Cleanup(func() {
		if f.service.GetApp() == nil {
			_, err := f.service.AccountSelect(f.ctx, selectRequest)
			if err != nil {
				t.Errorf("restore owned cancelled-select fixture for cleanup: %v", err)
			}
		}
	})
	definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "registrationstopqueuedselect")
	creator := f.creator.(objectcreator.FixedSchemaCreator)
	selectDone := make(chan error, 1)
	stopDone := make(chan error, 1)
	var createdID string
	var originalReadback objectcreator.FixedSchemaObservation
	entered, operationErr := f.service.WithActiveApp(f.ctx, nativeApp, func(retained *app.App) error {
		if retained != nativeApp {
			return errors.New("lease did not retain the exact native application")
		}
		// These concurrent original lifecycle callers are the external race
		// under test; production admitted callbacks never call lifecycle APIs.
		go func() {
			_, err := f.service.AccountSelect(f.ctx, selectRequest)
			selectDone <- err
		}()
		if err := registrationWaitQueuedWriter(f.ctx, "AccountSelect", selectDone); err != nil {
			return err
		}
		go func() { stopDone <- f.service.AccountStop(&pb.RpcAccountStopRequest{}) }()
		select {
		case err := <-stopDone:
			if err != nil {
				return fmt.Errorf("original Stop did not acknowledge queued Select cancellation: %w", err)
			}
		case <-time.After(5 * time.Second):
			return errors.New("original Stop failed to acknowledge cancellation before native drain")
		case <-f.ctx.Done():
			return f.ctx.Err()
		}
		select {
		case err := <-selectDone:
			return fmt.Errorf("cancelled Select returned while the original admission was held: %v", err)
		default:
		}
		t.Log("original Stop acknowledged queued Select cancellation before admitted native writes")
		created, err := creator.CreateFixedSchemaOnce(f.ctx, spc, accountID, definition)
		createdID = created.ReturnedObjectID
		if err != nil {
			return err
		}
		if !created.Invoked || createdID == "" || createdID != created.Before.ObjectID {
			return errors.New("original native create after Stop acknowledgement was not executed")
		}
		err = spc.DoCtx(f.ctx, createdID, func(object smartblock.SmartBlock) error {
			st := object.NewState()
			st.SetDetailAndBundledRelation(bundle.RelationKeyDescription, domain.String("native write after early Stop acknowledgement"))
			return object.Apply(st)
		})
		if err != nil {
			return err
		}
		originalReadback, err = registrationDirectRead(f.ctx, f.observer, spc, definition)
		if err != nil {
			return err
		}
		select {
		case err := <-selectDone:
			return fmt.Errorf("cancelled Select closed before native operation drain: %v", err)
		default:
		}
		return nil
	})
	var selectErr error
	select {
	case selectErr = <-selectDone:
	case <-time.After(45 * time.Second):
		t.Fatal("cancelled original Select did not finish after native drain")
	}
	if !entered || operationErr != nil {
		t.Fatalf("native operation after early Stop acknowledgement failed: entered=%t error=%v", entered, operationErr)
	}
	// The same-account GetInfo path may return nil or the cancelled context.
	// In both cases the original deferred beginStart end() closes the app
	// under its write lock, after the admitted callback has released RLock.
	if selectErr != nil && !errors.Is(selectErr, context.Canceled) {
		t.Fatalf("unexpected cancelled original Select outcome: %v", selectErr)
	}
	t.Logf("original queued Select finished after native drain: %v", selectErr)
	if f.service.GetApp() != nil {
		t.Fatal("original cancelled Select did not close the app after admission drain")
	}
	_, err := f.service.AccountSelect(f.ctx, selectRequest)
	nativeSchemaNoError(t, err)
	called := false
	entered, err = f.service.WithActiveApp(f.ctx, nativeApp, func(*app.App) error { called = true; return nil })
	if entered || called || !errors.Is(err, application.ErrActiveAppChanged) {
		t.Fatal("reopening after cancelled Select revived the retired application admission")
	}
	currentApp := f.service.GetApp()
	currentSpace, err := app.MustComponent[space.Service](currentApp).Get(f.ctx, spc.Id())
	nativeSchemaNoError(t, err)
	currentObserver := app.MustComponent[objectcreator.Service](currentApp).(objectcreator.FixedSchemaObserver)
	after, err := registrationDirectRead(f.ctx, currentObserver, currentSpace, definition)
	nativeSchemaNoError(t, err)
	details, _ := after.CopyPersistedSchemaState()
	if after.ObjectID != createdID || details == nil ||
		details.Fields[bundle.RelationKeyDescription.String()].GetStringValue() != "native write after early Stop acknowledgement" {
		t.Fatal("native write after early Stop acknowledgement was not retained across reopen")
	}
	registrationSameNative(t, originalReadback, after)
}

func registrationWaitQueuedWriter(ctx context.Context, method string, finished <-chan error) error {
	deadline := time.Now().Add(5 * time.Second)
	buffer := make([]byte, 2*1024*1024)
	for {
		count := runtime.Stack(buffer, true)
		for _, stack := range strings.Split(string(buffer[:count]), "\n\n") {
			if strings.Contains(stack, "sync.(*RWMutex).Lock(") && strings.Contains(stack, "application.(*Service)."+method+"(") {
				return nil
			}
		}
		select {
		case err := <-finished:
			return fmt.Errorf("original %s returned without queueing: %v", method, err)
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(5 * time.Millisecond):
		}
		if time.Now().After(deadline) {
			return fmt.Errorf("did not observe original %s at the real queued writer boundary", method)
		}
	}
}

func registrationDirectRead(ctx context.Context, observer objectcreator.FixedSchemaObserver, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition) (objectcreator.FixedSchemaObservation, error) {
	deadline := time.Now().Add(5 * time.Second)
	for {
		result, err := observer.ObserveFixedSchema(ctx, spc, definition)
		if !errors.Is(err, objectcreator.ErrFixedSchemaChanged) {
			if err == nil && result.Disposition != objectcreator.FixedSchemaPersistedMatch {
				return result, errors.New("complete original persisted definition was not observed")
			}
			return result, err
		}
		if time.Now().After(deadline) {
			return result, err
		}
		select {
		case <-ctx.Done():
			return result, ctx.Err()
		case <-time.After(10 * time.Millisecond):
		}
	}
}
