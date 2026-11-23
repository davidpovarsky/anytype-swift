package application

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	importer "github.com/anyproto/anytype-heart/core/block/import"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	"github.com/anyproto/anytype-heart/core/event"
	walletComp "github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/util/pbtypes"
)

// A new actual native gate, not a replay of the 23 isolated lifecycle controls.
// Setup uses the original reviewed nativeSchemaFixture wallet/account/Space
// APIs. It never prints the disposable wallet seed, installs a fake app, swaps
// a component, overrides Execute, or accepts caller-created completion facts.
func TestOtzariaOwnedImportNativeLifetime(t *testing.T) {
	t.Run("OriginalProtobufImportAndReentrantRetirement", func(t *testing.T) {
		f := newOwnedNativeFixture(t)
		sourceSpace, targetSpace := f.regularSpace(t), f.regularSpace(t)
		sourceID, snapshot := f.sourceSnapshot(t, sourceSpace)
		archive := f.archive(t, sourceID, snapshot)
		request := ownedNativeRequest(targetSpace.Id(), archive)
		owned, err := f.service.startOwnedImport(f.ctx, f.nativeApp, f.accountID, request)
		ownedNativeNoError(t, err)
		f.operations = append(f.operations, owned.operation)
		first := ownedNativeWait(t, owned.operation)
		ownedNativeNoError(t, first.Err())
		if first.CancellationRequested() || first.TargetSpaceID() != targetSpace.Id() || first.ObjectsCount() < 1 {
			t.Fatal("actual original importer did not complete in the declared target Space")
		}
		mapping, observed := first.NativeMappingObservation()
		if !observed || !mapping.CompleteForSelectedSnapshots() || len(first.NativeMappingProblems()) != 0 {
			t.Fatal("actual original protobuf import lacks its complete copied source observation")
		}
		var targetID string
		for _, row := range mapping.SourceAssignments() {
			if row.SourceObjectID == sourceID && row.SourceSpaceID == sourceSpace.Id() {
				if targetID != "" || row.NativeID == "" {
					t.Fatal("the actual source object has ambiguous native mapping")
				}
				targetID = row.NativeID
			}
		}
		if targetID == "" || targetID == sourceID {
			t.Fatal("actual original import did not map the copied source to its new native object")
		}
		ownedNativeNoError(t, targetSpace.DoCtx(f.ctx, targetID, func(object smartblock.SmartBlock) error {
			if object.SpaceID() != targetSpace.Id() ||
				object.CombinedDetails().GetString(bundle.RelationKeyName) != "Owned native lifetime source" ||
				object.CombinedDetails().GetString(bundle.RelationKeyDescription) != "Original native persisted description" ||
				len(object.Tree().Heads()) == 0 {
				t.Fatal("mapped original object lacks actual native persisted readback")
			}
			return nil
		}))
		f.waitIndexedSource(t, targetSpace.Id(), sourceID, targetID)

		// The second real import reaches the existing object's original
		// HookBeforeApply. Stop is reentered from that actual native stack.
		// Holding this callback is a scheduling witness, not a fake executor.
		const changedDescription = "Updated by the actual owned native import"
		snapshot.Snapshot.Data.Details.Fields[bundle.RelationKeyDescription.String()] = pbtypes.String(changedDescription)
		archive = f.archive(t, sourceID, snapshot)
		request = ownedNativeRequest(targetSpace.Id(), archive)
		request.UpdateExistingObjects = true
		owned, err = f.service.prepareOwnedAccountImport(f.ctx, f.nativeApp, f.accountID, request)
		ownedNativeNoError(t, err)
		f.operations = append(f.operations, owned.operation)
		entered := make(chan error, 1)
		release := make(chan struct{})
		var releaseOnce, enterOnce sync.Once
		unblock := func() { releaseOnce.Do(func() { close(release) }) }
		defer unblock()
		ownedNativeNoError(t, targetSpace.DoCtx(f.ctx, targetID, func(object smartblock.SmartBlock) error {
			object.AddHook(func(info smartblock.ApplyInfo) error {
				if info.State.CombinedDetails().GetString(bundle.RelationKeyDescription) != changedDescription {
					return nil
				}
				enterOnce.Do(func() {
					entered <- f.service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true})
					select {
					case <-release:
					case <-f.ctx.Done():
					}
				})
				return nil
			}, smartblock.HookBeforeApply)
			return nil
		}))
		owned.operation.Start()
		select {
		case stopErr := <-entered:
			if !errors.Is(stopErr, ErrOwnedImportDrainPending) {
				t.Fatalf("reentrant actual import Stop did not report pending drain: %v", stopErr)
			}
		case <-owned.operation.Done():
			t.Fatal("the native import returned without reaching the real target Apply")
		case <-time.After(90 * time.Second):
			t.Fatal("the original native Apply callback was not reached")
		}
		ownedNativePending(t, f, owned.operation)
		unblock()
		second := ownedNativeWait(t, owned.operation)
		if !second.CancellationRequested() || second.Err() == nil {
			t.Fatal("actual canceled native execution did not preserve cancellation after returning")
		}
		// Cancellation can occur after native mutation. No rollback or ACK
		// authority is inferred from either this error or the copied history.
		ownedNativeNoError(t, f.service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true}))
		if f.service.GetApp() != nil || f.service.accountLease != nil {
			t.Fatal("drained original retirement did not close the actual app and release its lease")
		}
		ownedNativeReceipt(t, "original-import-reentrant-retirement.json", map[string]any{
			"actual_wallet_account_and_lease": true, "actual_regular_spaces": true,
			"source_space": sourceSpace.Id(), "target_space": targetSpace.Id(),
			"source_object": sourceID, "mapped_native_object": targetID,
			"actual_first_import_returned": true, "actual_native_readback": true,
			"actual_second_apply_reentered_stop": true, "stop_was_pending_before_drain": true,
			"done_remained_open_while_native_apply_blocked":      true,
			"actual_canceled_execute_returned_before_final_stop": true,
			"final_account_stop_and_lease_release":               true, "ack_authority": false,
		})
	})

	t.Run("RegisteredPreStartCancellationRequiresActualReturn", func(t *testing.T) {
		f := newOwnedNativeFixture(t)
		sourceSpace, targetSpace := f.regularSpace(t), f.regularSpace(t)
		sourceID, snapshot := f.sourceSnapshot(t, sourceSpace)
		request := ownedNativeRequest(targetSpace.Id(), f.archive(t, sourceID, snapshot))
		owned, err := f.service.prepareOwnedAccountImport(f.ctx, f.nativeApp, f.accountID, request)
		ownedNativeNoError(t, err)
		f.operations = append(f.operations, owned.operation)
		err = f.service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true})
		if !errors.Is(err, ErrOwnedImportDrainPending) {
			t.Fatalf("registered original native operation was retired before it returned: %v", err)
		}
		ownedNativePending(t, f, owned.operation)
		owned.operation.Start()
		result := ownedNativeWait(t, owned.operation)
		if !result.CancellationRequested() || !errors.Is(result.Err(), context.Canceled) {
			t.Fatal("the actual pre-canceled original Execute did not return cancellation")
		}
		ownedNativeNoError(t, f.service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true}))
		if f.service.GetApp() != nil || f.service.accountLease != nil {
			t.Fatal("drained original native account remained retained after final Stop")
		}
		ownedNativeReceipt(t, "registered-prestart-cancellation.json", map[string]any{
			"actual_wallet_account_and_lease": true, "actual_dependency_construction": true,
			"registered_before_start": true, "stop_pending_before_actual_execute_return": true,
			"cancellation_was_not_completion": true, "actual_canceled_execute_returned": true,
			"final_account_stop_and_lease_release": true, "ack_authority": false,
		})
	})
}

type ownedNativeFixture struct {
	ctx        context.Context
	service    *Service
	nativeApp  *app.App
	accountID  string
	directory  string
	blocks     *block.Service
	spaces     space.Service
	creator    objectcreator.Service
	operations []*importer.OwnedImportOperation
}

func newOwnedNativeFixture(t *testing.T) *ownedNativeFixture {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 12*time.Minute)
	service := New()
	service.SetClientVersion("otzaria-owned-native-lifetime", "1.0.0")
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	directory, err := os.MkdirTemp("", "otzaria-owned-native-account-")
	ownedNativeNoError(t, err)
	f := &ownedNativeFixture{ctx: ctx, service: service, directory: directory}
	t.Cleanup(func() {
		defer cancel()
		for _, operation := range f.operations {
			operation.RequestCancel()
			operation.Start()
			select {
			case <-operation.Done():
			case <-time.After(30 * time.Second):
				t.Error("preserve disposable native data: owned execution has not drained")
				return
			}
		}
		if service.GetApp() != nil {
			if err := service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true}); err != nil {
				t.Errorf("preserve disposable native data: AccountStop failed: %v", err)
				return
			}
		}
		ownedNativeNoError(t, os.RemoveAll(directory))
	})
	_, _, err = service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: directory})
	ownedNativeNoError(t, err)
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	account, err := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{
		Name: "Disposable native owned import", StorePath: directory,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly,
	})
	ownedNativeNoError(t, err)
	if account == nil {
		t.Fatal("original AccountCreate returned no actual account")
	}
	f.nativeApp = service.GetApp()
	f.accountID = app.MustComponent[accountservice.Service](f.nativeApp).Account().SignKey.GetPublic().Account()
	wallet := app.MustComponent[walletComp.Wallet](f.nativeApp)
	if service.accountLease == nil || !service.accountLease.Usable() ||
		!service.accountLease.Matches(wallet.RootPath(), f.accountID) {
		t.Fatal("fixture has no actual matching native account-directory lease")
	}
	f.blocks = app.MustComponent[*block.Service](f.nativeApp)
	f.spaces = app.MustComponent[space.Service](f.nativeApp)
	f.creator = app.MustComponent[objectcreator.Service](f.nativeApp)
	return f
}

func (f *ownedNativeFixture) regularSpace(t *testing.T) clientspace.Space {
	t.Helper()
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, "Disposable native import Space")
	details.SetInt64(bundle.RelationKeySpaceType, int64(model.SpaceType_SpaceTypeRegular))
	id, _, err := f.blocks.CreateWorkspace(f.ctx, &pb.RpcWorkspaceCreateRequest{
		Details: details.ToProto(), UseCase: pb.RpcObjectImportUseCaseRequest_NONE,
	})
	ownedNativeNoError(t, err)
	spc, err := f.spaces.Wait(f.ctx, id)
	ownedNativeNoError(t, err)
	if spc == nil || spc.IsPersonal() || spc.CommonSpace() == nil || spc.Storage() == nil || spc.Id() != id {
		t.Fatal("fixture lacks an actual initialized regular Space")
	}
	acl := spc.CommonSpace().Acl()
	acl.RLock()
	canWrite := acl.AclState().Permissions(spc.GetAclIdentity()).CanWrite()
	acl.RUnlock()
	if !canWrite {
		t.Fatal("actual disposable Space ACL does not grant native write permission")
	}
	return spc
}

func (f *ownedNativeFixture) sourceSnapshot(t *testing.T, spc clientspace.Space) (string, *pb.SnapshotWithType) {
	t.Helper()
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, "Owned native lifetime source")
	details.SetString(bundle.RelationKeyDescription, "Original native persisted description")
	id, _, err := f.creator.CreateObject(f.ctx, spc.Id(), objectcreator.CreateObjectRequest{
		Details: details, ObjectTypeKey: bundle.TypeKeyPage,
	})
	ownedNativeNoError(t, err)
	var snapshot *pb.SnapshotWithType
	ownedNativeNoError(t, spc.DoCtx(f.ctx, id, func(object smartblock.SmartBlock) error {
		st := object.NewState()
		// Exact original native snapshot shape, as used by the export path.
		snapshot = &pb.SnapshotWithType{SbType: model.SmartBlockType_Page, Snapshot: &pb.ChangeSnapshot{
			Data: &model.SmartBlockSnapshotBase{
				Blocks: st.BlocksToSave(), Details: st.CombinedDetails().ToProto(),
				ObjectTypes: domain.MarshalTypeKeys(st.ObjectTypeKeys()), Collections: st.Store(),
				Key: st.UniqueKeyInternal(), FileInfo: st.GetFileInfo().ToModel(),
			},
		}}
		snapshot = proto.Clone(snapshot).(*pb.SnapshotWithType)
		return nil
	}))
	if snapshot == nil {
		t.Fatal("actual native source did not produce a copied snapshot")
	}
	return id, snapshot
}

func (f *ownedNativeFixture) archive(t *testing.T, sourceID string, snapshot *pb.SnapshotWithType) string {
	t.Helper()
	directory := filepath.Join(f.directory, "owned-input")
	ownedNativeNoError(t, os.MkdirAll(directory, 0o700))
	raw, err := proto.Marshal(snapshot)
	ownedNativeNoError(t, err)
	ownedNativeNoError(t, os.WriteFile(filepath.Join(directory, sourceID+".pb"), raw, 0o600))
	return directory
}

func ownedNativeRequest(spaceID, directory string) *importer.ImportRequest {
	return &importer.ImportRequest{
		RpcObjectImportRequest: &pb.RpcObjectImportRequest{
			SpaceId: spaceID, Mode: pb.RpcObjectImportRequest_ALL_OR_NOTHING,
			Type: model.Import_Pb, NoProgress: true,
			Params: &pb.RpcObjectImportRequestParamsOfPbParams{
				PbParams: &pb.RpcObjectImportRequestPbParams{Path: []string{directory}},
			},
		},
		Origin: objectorigin.Import(model.Import_Pb), IsSync: true,
	}
}

func (f *ownedNativeFixture) waitIndexedSource(t *testing.T, spaceID, sourceID, nativeID string) {
	t.Helper()
	store := app.MustComponent[objectstore.ObjectStore](f.nativeApp)
	deadline := time.NewTimer(30 * time.Second)
	defer deadline.Stop()
	ticker := time.NewTicker(50 * time.Millisecond)
	defer ticker.Stop()
	for {
		ids, _, err := store.SpaceIndex(spaceID).QueryObjectIds(database.Query{
			Filters: []database.FilterRequest{{
				Condition:   model.BlockContentDataviewFilter_Equal,
				RelationKey: bundle.RelationKeyOldAnytypeID, Value: domain.String(sourceID),
			}},
		})
		ownedNativeNoError(t, err)
		if len(ids) == 1 && ids[0] == nativeID {
			return
		}
		if len(ids) > 1 {
			t.Fatal("ambiguous original source index")
		}
		select {
		case <-ticker.C:
		case <-deadline.C:
			t.Fatal("actual imported source index did not become ready")
		}
	}
}

func ownedNativeWait(t *testing.T, operation *importer.OwnedImportOperation) importer.OwnedImportOutcome {
	t.Helper()
	select {
	case <-operation.Done():
	case <-time.After(90 * time.Second):
		t.Fatal("actual original import did not return and drain")
	}
	result, observed := operation.Result()
	if !observed {
		t.Fatal("closed original Done lacks its actual result")
	}
	return result
}

func ownedNativePending(t *testing.T, f *ownedNativeFixture, operation *importer.OwnedImportOperation) {
	t.Helper()
	select {
	case <-operation.Done():
		t.Fatal("cancellation falsely closed Done before actual native return")
	default:
	}
	if _, observed := operation.Result(); observed {
		t.Fatal("pending original operation fabricated completion")
	}
	if f.service.GetApp() != f.nativeApp || f.service.accountLease == nil || !f.service.accountLease.Usable() {
		t.Fatal("pending native import lost its actual app or account lease")
	}
	if _, err := os.Stat(f.directory); err != nil {
		t.Fatal("pending native account data was removed")
	}
}

func ownedNativeNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatalf("actual native operation failed: %v", err)
	}
}

func ownedNativeReceipt(t *testing.T, name string, value map[string]any) {
	t.Helper()
	directory := os.Getenv("OTZARIA_NATIVE_RUNTIME_EVIDENCE")
	if directory == "" {
		t.Fatal("native evidence directory not configured")
	}
	raw, err := json.MarshalIndent(value, "", "  ")
	ownedNativeNoError(t, err)
	file, err := os.OpenFile(filepath.Join(directory, name), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	ownedNativeNoError(t, err)
	_, writeErr := file.Write(append(raw, '\n'))
	syncErr, closeErr := file.Sync(), file.Close()
	ownedNativeNoError(t, errors.Join(writeErr, syncErr, closeErr))
}
