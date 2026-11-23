package service

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/list/listtest"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core"
	"github.com/anyproto/anytype-heart/core/anytype/config"
	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/detailservice"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

// This package's original init has already constructed core.New() and installed
// its real generated proxy/interceptors. This fixture neither replaces that
// handler nor constructs a response. Its wallet/account/Spaces are disposable.
func TestOtzariaOriginalSchemaEndpoint(t *testing.T) {
	f := newEndpointFixture(t)
	spc := f.regularSpace(t)
	request := f.request(spc)
	definitions, err := annotationschema.Definitions()
	endpointNoError(t, err)
	if len(definitions) != 18 {
		t.Fatal("exact original eighteen-definition schema required")
	}
	var ready *pb.RpcAnnotationSchemaRegisterResponse

	if !t.Run("GeneratedValidationDoesNotCreateNativeRoots", func(t *testing.T) {
		for i, data := range [][]byte{{0xff}, nil} {
			response := f.decode(t, AnnotationSchemaRegister(data), fmt.Sprintf("validation-%02d", i))
			if response.Error.Code != pb.RpcAnnotationSchemaRegisterResponseError_BAD_INPUT || response.Registration != nil {
				t.Fatal("original generated malformed/admission rejection changed")
			}
		}
		f.noSchemaRoots(t, spc, definitions)
		f.receipt(t, "validation.json", map[string]any{
			"generated_byte_entrypoint_calls": 2, "native_roots_created": 0,
		})
	}) {
		return
	}

	if !t.Run("GeneratedRegistrationCopiesActualNativeReadback", func(t *testing.T) {
		seen := map[string]bool{}
		applies := 0
		phases := 0
		for ; phases < 21; phases++ {
			response := f.invoke(t, request, fmt.Sprintf("registration-%02d", phases))
			value := response.Registration
			if value == nil || !value.AppAdmitted || value.SchemaProtocol != annotationschema.Protocol {
				t.Fatal("actual endpoint lost original admission/protocol history")
			}
			for _, creation := range value.Creations {
				if creation == nil || creation.Before == nil || creation.After == nil {
					t.Fatal("actual native creation copyout is incomplete")
				}
				if !creation.Invoked {
					continue
				}
				id := creation.Before.ObjectId
				if id == "" || seen[id] || creation.ReturnedObjectId != id {
					t.Fatal("an uncertain or repeated original native creation cannot be resumed")
				}
				seen[id] = true
			}
			if value.TypeApplyInvoked {
				applies++
				if !value.TypeApplyReturned {
					t.Fatal("successful initial registration requires its original Apply to return")
				}
			}
			if response.Error.Code == pb.RpcAnnotationSchemaRegisterResponseError_NULL {
				ready = response
				break
			}
			if response.Error.Code != pb.RpcAnnotationSchemaRegisterResponseError_UNRESOLVED {
				t.Fatalf("native endpoint cannot resume after code=%d", response.Error.Code)
			}
			// Only read-only original observer/index readiness repeats. A later
			// bounded endpoint call may create untouched definitions, never retry
			// an already invoked native ID or complete an uncertain root.
			f.waitReadiness(t, spc, definitions, seen)
		}
		if ready == nil || len(seen) != 18 || applies != 1 {
			t.Fatal("endpoint did not execute eighteen unique creates and one actual type Apply")
		}
		observation := ready.Registration.Observation
		if observation == nil || observation.Disposition != string(annotationschema.MatchingObserved) ||
			observation.AccountIdentity != f.accountID || observation.SpaceId != spc.Id() ||
			len(observation.Definitions) != 18 || observation.TypeLayout == nil ||
			len(observation.TypeLayout.ViewIds) == 0 || !observation.TypeLayout.Hidden || !observation.TypeLayout.DiscoveryHidden {
			t.Fatal("actual serialized endpoint lacks complete original native schema readback")
		}
		for i, definition := range definitions {
			entry := observation.Definitions[i]
			if entry == nil || entry.IndexDisposition != string(annotationschema.IndexMatch) || entry.PersistedStateConflict {
				t.Fatal("serialized native definition index state differs")
			}
			actual := f.observe(t, spc, definition)
			assertEndpointNativeCopy(t, entry.Native, actual)
		}
		f.receipt(t, "registration.json", map[string]any{
			"wire_calls": phases + 1, "unique_actual_creates": len(seen), "actual_type_apply_calls": applies,
			"native_definitions_compared": 18, "raw_wire_preserved": true,
			"readback": "independent original persisted schema observer, no cold account reopen",
		})
	}) {
		return
	}

	if !t.Run("CanceledNativeApplyPreservesErrorPhaseHistory", func(t *testing.T) {
		typeID := ready.Registration.Observation.Definitions[0].Native.ObjectId
		propertyID := ready.Registration.Observation.Definitions[1].Native.ObjectId
		properties := app.MustComponent[detailservice.Service](mw.GetApp())
		_, err := properties.ObjectTypePropertyRemove(f.ctx, typeID, domain.RelationKey(definitions[1].Key.InternalKey()))
		endpointNoError(t, err)
		before := f.observe(t, spc, definitions[0])
		beforeDetails, _ := before.CopyPersistedSchemaState()
		if slices.Contains(domain.NewDetailsFromProto(beforeDetails).GetStringList(bundle.RelationKeyRecommendedHiddenRelations), propertyID) {
			t.Fatal("actual missing-property setup did not persist")
		}
		operation, cancel := context.WithCancel(f.ctx)
		defer cancel()
		var hookCalls atomic.Int32
		endpointNoError(t, spc.DoCtx(f.ctx, typeID, func(object smartblock.SmartBlock) error {
			object.AddHook(func(info smartblock.ApplyInfo) error {
				if info.State != nil && slices.Contains(info.State.Details().GetStringList(bundle.RelationKeyRecommendedHiddenRelations), propertyID) &&
					hookCalls.CompareAndSwap(0, 1) {
					// Cancellation is triggered only by the real original Apply's
					// after-commit hook. No product callback is invoked by the test.
					cancel()
				}
				return nil
			}, smartblock.HookAfterApply)
			return nil
		}))
		// The mobile byte wrapper uses context.Background by original design.
		// Here the already installed original generated proxy carries a genuine
		// Go cancellation context. This is not Swift cancellation qualification.
		actualResponse := clientCommandsHandler.AnnotationSchemaRegister(operation, request)
		if actualResponse == nil {
			t.Fatal("actual original proxy returned no native response")
		}
		raw, err := actualResponse.Marshal()
		endpointNoError(t, err)
		response := f.decode(t, raw, "canceled-after-native-apply")
		value := response.Registration
		if hookCalls.Load() != 1 || !errors.Is(operation.Err(), context.Canceled) ||
			response.Error.Code != pb.RpcAnnotationSchemaRegisterResponseError_CANCELED ||
			value == nil || !value.AppAdmitted || !value.TypeApplyInvoked || !value.TypeApplyReturned ||
			len(value.Creations) != 0 || value.Observation == nil ||
			value.Observation.Disposition == string(annotationschema.MatchingObserved) {
			t.Fatal("non-success RPC erased actual committed Apply history or published current success")
		}
		after := f.observe(t, spc, definitions[0])
		afterDetails, _ := after.CopyPersistedSchemaState()
		if sameEndpointHeads(before.PersistedHeads, after.PersistedHeads) ||
			!slices.Contains(domain.NewDetailsFromProto(afterDetails).GetStringList(bundle.RelationKeyRecommendedHiddenRelations), propertyID) {
			t.Fatal("after-Apply cancellation was not followed by original persisted readback")
		}
		f.receipt(t, "canceled-apply-history.json", map[string]any{
			"actual_after_apply_hooks": hookCalls.Load(), "native_context_canceled": true,
			"error_code": response.Error.Code.String(), "app_admitted": value.AppAdmitted,
			"type_apply_invoked": value.TypeApplyInvoked, "type_apply_returned": value.TypeApplyReturned,
			"actual_persisted_heads_changed": true, "actual_hidden_property_observed": true,
			"entrypoint":                           "original installed generated proxy with actual Go context",
			"mobile_context_propagation_qualified": false, "swift_cancellation_qualified": false,
		})
	}) {
		return
	}

	if !t.Run("SignedNativeReaderRoleMapsPermissionDenied", func(t *testing.T) {
		readerSpace := f.regularSpace(t)
		otherIdentity := newEndpointOtherIdentity(t, f.ctx)
		if !app.MustComponent[*config.Config](mw.GetApp()).IsLocalOnlyMode() {
			t.Fatal("signed ACL fixture requires an actual disposable LocalOnly account")
		}
		acl := readerSpace.CommonSpace().Acl()
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
			if acl.AclState().Permissions(readerSpace.GetAclIdentity()) != list.AclPermissionsReader ||
				acl.AclState().Permissions(otherIdentity) != list.AclPermissionsOwner {
				return errors.New("actual signed ACL did not establish native reader/owner roles")
			}
			return nil
		}()
		endpointNoError(t, err)
		response := f.invoke(t, f.request(readerSpace), "signed-native-reader")
		value := response.Registration
		if response.Error.Code != pb.RpcAnnotationSchemaRegisterResponseError_PERMISSION_DENIED ||
			value == nil || !value.AppAdmitted || len(value.Creations) != 0 || value.TypeApplyInvoked {
			t.Fatal("actual native ACL refusal was not preserved by the generated wire boundary")
		}
		f.noSchemaRoots(t, readerSpace, definitions)
		f.receipt(t, "signed-reader.json", map[string]any{
			"actual_signed_acl_reader": true, "other_actual_account_owner": true,
			"error_code": response.Error.Code.String(), "actual_schema_roots": 0,
		})
	}) {
		return
	}

	t.Run("StoppedNativeRuntimeRejectsHistoricalRequest", func(t *testing.T) {
		f.stop(t)
		if mw.GetApp() != nil {
			t.Fatal("original AccountStop did not retire its actual application")
		}
		response := f.invoke(t, request, "stopped-native-runtime")
		value := response.Registration
		if response.Error.Code != pb.RpcAnnotationSchemaRegisterResponseError_RUNTIME_UNAVAILABLE ||
			value == nil || value.AppAdmitted || value.TypeApplyInvoked || len(value.Creations) != 0 {
			t.Fatal("historical request IDs admitted writes after actual native AccountStop")
		}
		f.receipt(t, "stopped-runtime.json", map[string]any{
			"actual_account_stop_returned": true, "actual_application_absent": true,
			"historical_request_refused": true, "error_code": response.Error.Code.String(),
		})
	})
}

type endpointFixture struct {
	ctx       context.Context
	directory string
	accountID string
	spaces    space.Service
	blocks    *block.Service
	observer  objectcreator.FixedSchemaObserver
	store     objectstore.ObjectStore
}

func newEndpointFixture(t *testing.T) *endpointFixture {
	t.Helper()
	if mw == nil || mw.GetApp() != nil || clientCommandsHandler == nil {
		t.Fatal("fresh actual original service initialization required")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Minute)
	t.Cleanup(cancel)
	directory := t.TempDir()
	initial := mw.InitialSetParameters(ctx, &pb.RpcInitialSetParametersRequest{
		Platform: "test", Version: "1.0.0", Workdir: directory,
		LogLevel: "error", DoNotSaveLogs: true, DoNotSendTelemetry: true,
	})
	if initial == nil || initial.Error == nil || initial.Error.Code != pb.RpcInitialSetParametersResponseError_NULL {
		t.Fatal("actual original initial parameter admission failed")
	}
	wallet := mw.WalletCreate(ctx, &pb.RpcWalletCreateRequest{RootPath: directory})
	if wallet == nil || wallet.Error == nil || wallet.Error.Code != pb.RpcWalletCreateResponseError_NULL {
		t.Fatal("actual original WalletCreate failed")
	}
	// Mnemonic/account-key fields are neither logged nor written to evidence.
	wallet = nil
	mw.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	account := mw.AccountCreate(ctx, &pb.RpcAccountCreateRequest{
		Name: "Disposable native endpoint qualification", StorePath: directory,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly,
	})
	if account == nil || account.Error == nil || account.Error.Code != pb.RpcAccountCreateResponseError_NULL ||
		account.Account == nil || mw.GetApp() == nil {
		t.Fatal("actual original LocalOnly AccountCreate failed")
	}
	native := mw.GetApp()
	creator := app.MustComponent[objectcreator.Service](native)
	observer, ok := creator.(objectcreator.FixedSchemaObserver)
	if !ok {
		t.Fatal("actual original object creator lacks the accepted native observer")
	}
	f := &endpointFixture{
		ctx: ctx, directory: directory,
		accountID: app.MustComponent[accountservice.Service](native).Account().SignKey.GetPublic().Account(),
		spaces:    app.MustComponent[space.Service](native), blocks: app.MustComponent[*block.Service](native),
		observer: observer, store: app.MustComponent[objectstore.ObjectStore](native),
	}
	if f.accountID == "" {
		t.Fatal("actual wallet/account identity is absent")
	}
	t.Cleanup(func() { f.stop(t) })
	return f
}

func (f *endpointFixture) stop(t *testing.T) {
	t.Helper()
	if mw.GetApp() == nil {
		return
	}
	response := mw.AccountStop(context.Background(), &pb.RpcAccountStopRequest{RemoveData: true})
	if response == nil || response.Error == nil || response.Error.Code != pb.RpcAccountStopResponseError_NULL {
		t.Error("actual original AccountStop failed")
	}
}

func (f *endpointFixture) regularSpace(t *testing.T) clientspace.Space {
	t.Helper()
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, "Disposable original endpoint Space")
	details.SetInt64(bundle.RelationKeySpaceType, int64(model.SpaceType_SpaceTypeRegular))
	id, _, err := f.blocks.CreateWorkspace(f.ctx, &pb.RpcWorkspaceCreateRequest{
		Details: details.ToProto(), UseCase: pb.RpcObjectImportUseCaseRequest_NONE,
	})
	endpointNoError(t, err)
	spc, err := f.spaces.Wait(f.ctx, id)
	endpointNoError(t, err)
	if spc == nil || spc.IsPersonal() || spc.Id() != id || spc.CommonSpace() == nil ||
		spc.Storage() == nil || spc.GetAclIdentity() == nil || spc.GetAclIdentity().Account() != f.accountID {
		t.Fatal("actual original regular Space/account/ACL identity is unqualified")
	}
	return spc
}

func (f *endpointFixture) request(spc clientspace.Space) *pb.RpcAnnotationSchemaRegisterRequest {
	return &pb.RpcAnnotationSchemaRegisterRequest{
		ExpectedAccountId: f.accountID, SpaceId: spc.Id(), SchemaProtocol: annotationschema.Protocol,
	}
}

func (f *endpointFixture) invoke(t *testing.T, request *pb.RpcAnnotationSchemaRegisterRequest, name string) *pb.RpcAnnotationSchemaRegisterResponse {
	t.Helper()
	data, err := request.Marshal()
	endpointNoError(t, err)
	return f.decode(t, AnnotationSchemaRegister(data), name)
}

func (f *endpointFixture) decode(t *testing.T, raw []byte, name string) *pb.RpcAnnotationSchemaRegisterResponse {
	t.Helper()
	if len(raw) == 0 {
		t.Fatal("actual original native entrypoint returned empty wire bytes")
	}
	response := &pb.RpcAnnotationSchemaRegisterResponse{}
	endpointNoError(t, response.Unmarshal(raw))
	if response.Error == nil {
		t.Fatal("actual original response has no error envelope")
	}
	f.write(t, name+".pb", raw)
	return response
}

func (f *endpointFixture) observe(t *testing.T, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition) objectcreator.FixedSchemaObservation {
	t.Helper()
	for attempt := 0; attempt < 3; attempt++ {
		value, err := f.observer.ObserveFixedSchema(f.ctx, spc, definition)
		if errors.Is(err, objectcreator.ErrFixedSchemaChanged) && attempt < 2 {
			continue
		}
		endpointNoError(t, err)
		if value.Disposition != objectcreator.FixedSchemaPersistedMatch {
			t.Fatalf("independent original schema observer returned disposition=%d", value.Disposition)
		}
		return value
	}
	panic("unreachable")
}

func (f *endpointFixture) waitReadiness(t *testing.T, spc clientspace.Space, definitions []objectcreator.FixedSchemaDefinition, known map[string]bool) {
	t.Helper()
	deadline := time.Now().Add(30 * time.Second)
	for {
		ready := true
		for _, definition := range definitions {
			value, err := f.observer.ObserveFixedSchema(f.ctx, spc, definition)
			if errors.Is(err, objectcreator.ErrFixedSchemaChanged) {
				ready = false
				continue
			}
			endpointNoError(t, err)
			if value.Disposition == objectcreator.FixedSchemaRootOnlyIncomplete || value.Disposition == objectcreator.FixedSchemaPopulatedConflict {
				t.Fatal("native uncertainty/conflict cannot be retried through the endpoint")
			}
			if known[value.ObjectID] && value.Disposition != objectcreator.FixedSchemaPersistedMatch {
				ready = false
			}
			if value.Disposition != objectcreator.FixedSchemaPersistedMatch {
				continue
			}
			key, expected := bundle.RelationKeyUniqueKey, definition.Key.Marshal()
			if expected != annotationschema.TypeUniqueKey {
				key, expected = bundle.RelationKeyRelationKey, definition.Key.InternalKey()
			}
			rows, err := f.store.SpaceIndex(spc.Id()).QueryRaw(&database.Filters{FilterObj: database.FilterEq{
				Key: key, Cond: model.BlockContentDataviewFilter_Equal, Value: domain.String(expected),
			}}, 2, 0)
			endpointNoError(t, err)
			if len(rows) == 0 {
				ready = false
				continue
			}
			if len(rows) != 1 || rows[0].Details == nil || rows[0].Details.GetString(bundle.RelationKeyId) != value.ObjectID {
				t.Fatal("actual native index is ambiguous or names another object")
			}
			for field, expected := range definition.Required.Iterate() {
				if !rows[0].Details.Has(field) || !rows[0].Details.Get(field).Equal(expected) {
					t.Fatal("actual native positive index row conflicts with required schema")
				}
			}
		}
		if ready {
			return
		}
		if time.Now().After(deadline) {
			t.Fatal("original read-only readiness did not converge; native creation is not retried")
		}
		select {
		case <-f.ctx.Done():
			t.Fatal(f.ctx.Err())
		case <-time.After(100 * time.Millisecond):
		}
	}
}

func (f *endpointFixture) noSchemaRoots(t *testing.T, spc clientspace.Space, definitions []objectcreator.FixedSchemaDefinition) {
	t.Helper()
	for _, definition := range definitions {
		id, err := spc.DeriveObjectID(f.ctx, definition.Key)
		endpointNoError(t, err)
		present, err := spc.Storage().HasTree(f.ctx, id)
		endpointNoError(t, err)
		if present {
			t.Fatal("rejected native endpoint created a schema root")
		}
	}
}

func assertEndpointNativeCopy(t *testing.T, wire *pb.RpcAnnotationSchemaNativeObservation, actual objectcreator.FixedSchemaObservation) {
	t.Helper()
	details, blocks := actual.CopyPersistedSchemaState()
	if wire == nil || actual.NativeKey == nil || wire.Disposition != uint32(actual.Disposition) ||
		wire.NativeKey != actual.NativeKey.Marshal() || wire.AccountIdentity != actual.AccountIdentity ||
		wire.SpaceId != actual.SpaceID || wire.ObjectId != actual.ObjectID ||
		wire.ArchiveId != actual.ArchiveID || wire.AclId != actual.ACLID || wire.AclHead != actual.ACLHead ||
		!sameEndpointHeads(wire.PersistedHeads, actual.PersistedHeads) ||
		!sameEndpointHeads(wire.ArchiveHeads, actual.ArchiveHeads) ||
		!proto.Equal(wire.Details, details) || len(wire.Blocks) != len(blocks) {
		t.Fatal("actual endpoint copyout differs from independent original persisted state")
	}
	byID := make(map[string]*model.Block, len(blocks))
	for _, block := range blocks {
		if block == nil || byID[block.Id] != nil {
			t.Fatal("original native block readback is incomplete")
		}
		byID[block.Id] = block
	}
	for _, block := range wire.Blocks {
		if block == nil || !proto.Equal(block, byID[block.Id]) {
			t.Fatal("endpoint omitted or altered original represented native block fields")
		}
		delete(byID, block.Id)
	}
	if len(byID) != 0 {
		t.Fatal("endpoint omitted an original native block")
	}
}

func sameEndpointHeads(a, b []string) bool {
	a, b = slices.Clone(a), slices.Clone(b)
	slices.Sort(a)
	slices.Sort(b)
	return slices.Equal(a, b)
}

func newEndpointOtherIdentity(t *testing.T, ctx context.Context) crypto.PubKey {
	t.Helper()
	other := application.New()
	other.SetClientVersion("test", "1.0.0")
	directory := t.TempDir()
	_, _, err := other.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: directory})
	endpointNoError(t, err)
	other.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	account, err := other.AccountCreate(ctx, &pb.RpcAccountCreateRequest{
		Name: "Disposable actual ACL owner", StorePath: directory,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly,
	})
	endpointNoError(t, err)
	if account == nil || other.GetApp() == nil {
		t.Fatal("second actual native account is absent")
	}
	t.Cleanup(func() { endpointNoError(t, other.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true})) })
	return app.MustComponent[accountservice.Service](other.GetApp()).Account().SignKey.GetPublic()
}

func (f *endpointFixture) write(t *testing.T, name string, raw []byte) {
	t.Helper()
	directory := os.Getenv("OTZARIA_NATIVE_RUNTIME_EVIDENCE")
	if directory == "" || filepath.Base(name) != name {
		t.Fatal("owned native endpoint evidence path required")
	}
	output, err := os.OpenFile(filepath.Join(directory, name), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	endpointNoError(t, err)
	_, writeErr := output.Write(raw)
	closeErr := output.Close()
	endpointNoError(t, writeErr)
	endpointNoError(t, closeErr)
}

func (f *endpointFixture) receipt(t *testing.T, name string, values map[string]any) {
	t.Helper()
	values["account_identity"] = f.accountID
	values["ack_authority"] = false
	values["body_authority"] = false
	values["swift_invocation_qualified"] = false
	raw, err := json.MarshalIndent(values, "", "  ")
	endpointNoError(t, err)
	f.write(t, name, append(raw, '\n'))
	digest := sha256.Sum256(raw)
	t.Logf("actual native endpoint receipt=%s sha256=%s", name, hex.EncodeToString(digest[:]))
}

func endpointNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatalf("original native endpoint fixture operation: %v", err)
	}
}

// Keep a compile-time link to the original Middleware type; no test transport,
// replacement constructor or hand-written generated method is introduced.
var _ *core.Middleware = mw
