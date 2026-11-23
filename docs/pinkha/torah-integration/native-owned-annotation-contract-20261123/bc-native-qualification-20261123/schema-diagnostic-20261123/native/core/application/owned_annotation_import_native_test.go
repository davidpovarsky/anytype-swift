package application_test

import (
	"archive/zip"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"slices"
	"sort"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/list/listtest"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/gogo/protobuf/proto"
	"github.com/google/uuid"

	"github.com/anyproto/anytype-heart/core/anytype/config"
	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/detailservice"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/export"
	importer "github.com/anyproto/anytype-heart/core/block/import"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	importcreator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/import/common/objectid"
	"github.com/anyproto/anytype-heart/core/block/import/common/syncer"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/files/fileobject"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema"
	"github.com/anyproto/anytype-heart/core/relationutils"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

// Genuine new closed-import cases. The four exports below are necessary
// same-account inputs; no previously accepted standalone export/archive selector
// is replayed. All native dependencies, Execute, upload, mapping and Done are real.
func TestOtzariaOwnedAnnotationClosedNativeImport(t *testing.T) {
	f := newOwnedClosedFixture(t)
	specimens := make(map[string]*ownedClosedSpecimen)
	// Finish all original source production before any import starts. The
	// retained producer manifests therefore describe that actual earlier phase.
	for _, kind := range []string{"text", "format", "nested", "attachment"} {
		specimens[kind] = f.produce(t, kind)
	}
	targets := make(map[string]*ownedClosedFixture)
	outcomes := make(map[string]importer.OwnedImportOutcome)
	for _, kind := range []string{"text", "format", "nested", "attachment"} {
		if !t.Run(kind, func(t *testing.T) {
			target := f.target(t, kind, specimens[kind])
			targets[kind] = target
			source := specimens[kind]
			before := target.readOnlyHeads(t, source)
			operation, stage := target.prepare(t, source)
			target.start(operation)
			result := target.wait(t, kind, operation)
			outcomes[kind] = result
			target.stageRemoved(t, stage)
			target.assertRoundTrip(t, source, result)
			after := target.readOnlyHeads(t, source)
			if !reflect.DeepEqual(before, after) {
				t.Fatal("original readonly target schema heads changed during closed import")
			}
			target.receipt(t, "accepted-roundtrip.json", map[string]any{
				"specimen": kind, "whole_source_snapshots": len(source.Snapshots),
				"actual_original_import_returned": true, "actual_same_owner_readback": true,
				"owned_stage_absent_at_actual_done_observation": true, "readonly_schema_heads_unchanged": true,
				"mapping_aware_body_comparison": true, "independent_native_block_checks": true,
			})
		}) {
			return
		}
	}

	if !t.Run("ExistingGraphIdentityRefused", func(t *testing.T) {
		target := targets["text"]
		source := specimens["text"]
		prior, observed := outcomes["text"].OriginalAnnotationReadback()
		if !observed {
			t.Fatal("genuine prior body readback missing")
		}
		before := target.pageHeads(t, prior.RootID())
		target.waitImportedIdentity(t, source.RootID, prior.RootID())
		operation, stage := target.prepare(t, source)
		target.start(operation)
		result := target.wait(t, "existing-identity-refusal", operation)
		target.stageRemoved(t, stage)
		if result.Err() == nil || !strings.Contains(result.Err().Error(), "existing_or_unknown_import_identity") {
			t.Fatalf("genuine existing source identity was not refused: %v", result.Err())
		}
		if _, ok := result.OriginalAnnotationReadback(); ok || len(result.Files()) != 0 {
			t.Fatal("refused existing graph acquired readback or actual file-upload outcome")
		}
		if !slices.Equal(before, target.pageHeads(t, prior.RootID())) {
			t.Fatal("refused original source identity changed the mapped native object")
		}
		target.waitImportedIdentity(t, source.RootID, prior.RootID())
		target.receipt(t, "existing-identity-accepted-refusal.json", map[string]any{
			"actual_prior_mapping_preserved": true, "actual_existing_native_heads_unchanged": true,
			"blind_reimport_refused": true, "operation_returned_and_owned_stage_removed": true,
		})
	}) {
		return
	}

	if !t.Run("CapturedAccountMismatchRefused", func(t *testing.T) {
		source, target := specimens["text"], targets["text"]
		before := target.stagePaths(t)
		operation, err := application.PrepareOwnedAnnotationImportForNativeTest(
			f.service, f.ctx, f.nativeApp, f.accountID+"-mismatch",
			source.Raw, source.Digest, source.RootID, f.spc.Id(), target.spc.Id())
		if operation != nil {
			f.owner.operations = append(f.owner.operations, operation)
		}
		if operation != nil || !errors.Is(err, application.ErrOwnedImportAdmissionUnavailable) {
			t.Fatal("mismatched captured account admitted an owned native operation")
		}
		if !slices.Equal(before, target.stagePaths(t)) {
			t.Fatal("rejected account comparison retained a private archive stage")
		}
		target.receipt(t, "account-mismatch-refusal.json", map[string]any{
			"same_actual_application":             f.service.GetApp() == f.nativeApp,
			"mismatched_expected_account_refused": true, "operation_created": false,
		})
	}) {
		return
	}

	if !t.Run("ActualFreshCreatorCollisionRefused", func(t *testing.T) {
		f.actualCreatorCollision(t, specimens["text"])
	}) {
		return
	}

	if !t.Run("SignedReaderRevocationAfterPrepareRefused", func(t *testing.T) {
		source := specimens["attachment"]
		target := f.target(t, "reader", source)
		operation, stage := target.prepare(t, source)
		identity := f.otherIdentity(t)
		target.downgradeToReader(t, identity)
		// The real operation is already registered and its byte stage is
		// owned. Only the actual later Execute reaches native Space binding.
		target.start(operation)
		result := target.wait(t, "signed-reader-refusal", operation)
		target.stageRemoved(t, stage)
		if !errors.Is(result.Err(), list.ErrInsufficientPermissions) {
			t.Fatalf("actual signed native reader was not refused: %v", result.Err())
		}
		if _, ok := result.OriginalAnnotationReadback(); ok || len(result.Files()) != 0 {
			t.Fatal("reader refusal acquired a body observation or native upload completion")
		}
		target.noImportedIdentity(t, source)
		target.receipt(t, "signed-reader-accepted-refusal.json", map[string]any{
			"actual_operation_registered_before_acl_change": true,
			"actual_signed_reader_and_other_native_owner":   true,
			"actual_execute_returned_permission_denied":     true,
			"actual_owned_stage_removed_before_done":        true,
			"scope":                                         "revocation before Execute native write admission; no atomic zero-effect promise after a concurrent admitted write",
		})
	}) {
		return
	}

	t.Run("RegisteredCancellationAndHistoricalAppRefusal", func(t *testing.T) {
		source := specimens["text"]
		target := f.target(t, "cancel", source)
		operation, stage := target.prepare(t, source)
		err := f.service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true})
		if !errors.Is(err, application.ErrOwnedImportDrainPending) {
			t.Fatalf("registered closed-byte operation was not retained by original Stop: %v", err)
		}
		target.pending(t, operation, stage)
		// RequestCancel/Stop are not completion. Start still enters the real
		// original Execute, which returns its real pre-canceled result.
		target.start(operation)
		result := target.wait(t, "registered-cancellation", operation)
		target.stageRemoved(t, stage)
		if !result.CancellationRequested() || !errors.Is(result.Err(), context.Canceled) {
			t.Fatal("actual original pre-canceled Execute did not preserve cancellation")
		}
		if _, ok := result.OriginalAnnotationReadback(); ok {
			t.Fatal("canceled-before-Execute operation invented body readback")
		}
		target.noImportedIdentity(t, source)
		ownedClosedNoError(t, f.stopActual(f.service))
		if f.service.GetApp() != nil {
			t.Fatal("actual drained Stop left the native app active")
		}
		stale, staleErr := application.PrepareOwnedAnnotationImportForNativeTest(
			f.service, f.ctx, f.nativeApp, f.accountID,
			source.Raw, source.Digest, source.RootID, f.spc.Id(), target.spc.Id())
		if stale != nil {
			f.owner.operations = append(f.owner.operations, stale)
		}
		if stale != nil || !errors.Is(staleErr, application.ErrOwnedImportAdmissionUnavailable) {
			t.Fatal("historical app/account identity admitted after actual Stop")
		}
		if len(target.stagePaths(t)) != 0 {
			t.Fatal("closed or rejected operation retained its private archive stage")
		}
		historical, exists := outcomes["attachment"].OriginalAnnotationReadback()
		if !exists || historical.Stage() != importer.OwnedAnnotationBodyMatched ||
			historical.NativeArchiveSHA256() != sha256.Sum256(historical.CopyNativeArchive()) {
			t.Fatal("actual previous historical readback was lost or altered after retirement")
		}
		target.receipt(t, "cancellation-and-retirement.json", map[string]any{
			"original_stop_pending_while_done_open":                 true,
			"actual_canceled_execute_returned_before_stage_removal": true,
			"actual_final_account_stop_returned":                    true, "actual_application_absent": true,
			"historical_application_request_refused":        true,
			"previous_body_result_retained_as_history_only": true,
		})
	})
}

type ownedClosedOwner struct {
	operations []*importer.OwnedImportOperation
	started    int
	others     []*application.Service
	temp       string
	stopMu     sync.Mutex
	stops      map[*application.Service]*ownedClosedStop
}

// One actual final Stop belongs to this shared fixture owner. A timeout only
// ends that caller's bounded wait; it cannot retire or replace the operation.
type ownedClosedStop struct {
	done chan struct{}
	err  error
}

func (f *ownedClosedFixture) produce(t *testing.T, kind string) *ownedClosedSpecimen {
	t.Helper()
	if f.owner.started != 0 {
		t.Fatal("original source production must precede this fixture's imports")
	}
	root := f.annotation(t, "Original closed import "+kind)
	s := &ownedClosedSpecimen{Kind: kind, RootID: root, Expected: make(map[string]*model.Block)}
	switch kind {
	case "text":
		f.text(t, s, root, "", "First native paragraph.", model.BlockContentText_Paragraph, nil)
		f.text(t, s, root, "", "הערה מקורית לבדיקה.", model.BlockContentText_Paragraph, nil)
	case "format":
		f.text(t, s, root, "", "Native heading", model.BlockContentText_Header2, nil)
		marks := &model.BlockContentTextMarks{Marks: []*model.BlockContentTextMark{
			{Range: &model.Range{From: 0, To: 4}, Type: model.BlockContentTextMark_Bold},
			{Range: &model.Range{From: 5, To: 11}, Type: model.BlockContentTextMark_Italic},
		}}
		f.text(t, s, root, "", "Bold italic native text", model.BlockContentText_Paragraph, marks)
	case "nested":
		s.ParentID = f.text(t, s, root, "", "Parent native toggle", model.BlockContentText_Toggle, nil)
		s.ChildID = f.text(t, s, root, s.ParentID, "Nested native text", model.BlockContentText_Paragraph, nil)
		s.LinkedID = f.annotation(t, "Native linked annotation")
		f.text(t, s, s.LinkedID, "", "Linked native object body", model.BlockContentText_Paragraph, nil)
		f.expectedBlock(t, s, root, "", &model.Block{Content: &model.BlockContentOfLink{
			Link: &model.BlockContentLink{TargetBlockId: s.LinkedID},
		}})
	case "attachment":
		s.AttachmentBytes = []byte("Native disposable attachment\nשורה מקורית\n")
		input := filepath.Join(f.directory, "native-attachment.txt")
		ownedClosedNoError(t, os.WriteFile(input, s.AttachmentBytes, 0600))
		id, kind, _, err := f.blocks.UploadFile(f.ctx, f.spc.Id(), block.FileUploadRequest{
			RpcFileUploadRequest: pb.RpcFileUploadRequest{SpaceId: f.spc.Id(), LocalPath: input,
				Type: model.BlockContentFile_File, Style: model.BlockContentFile_Link, CreatedInContext: root},
			ObjectOrigin: objectorigin.None(), Name: "native-attachment.txt",
		})
		ownedClosedNoError(t, err)
		if id == "" {
			t.Fatal("original upload returned no actual file object")
		}
		s.AttachmentID = id
		f.expectedBlock(t, s, root, "", &model.Block{Content: &model.BlockContentOfFile{
			File: &model.BlockContentFile{TargetObjectId: id, Type: kind, State: model.BlockContentFile_Done,
				Style: model.BlockContentFile_Link, Name: "native-attachment.txt", Size_: int64(len(s.AttachmentBytes))},
		}})
	default:
		t.Fatal("unowned fixture specimen")
	}
	f.export(t, s)
	return s
}

type ownedClosedSpecimen struct {
	Raw             []byte
	Digest          [32]byte
	SourceSpace     string
	Snapshots       map[string]*pb.SnapshotWithType
	Kind            string
	RootID          string
	Expected        map[string]*model.Block
	ParentID        string
	ChildID         string
	LinkedID        string
	AttachmentID    string
	AttachmentBytes []byte
}
type ownedClosedFixture struct {
	nativeApp *app.App
	spaces    space.Service
	owner     *ownedClosedOwner
	ctx       context.Context
	service   *application.Service
	directory string
	evidence  string
	accountID string
	spc       clientspace.Space
	blocks    *block.Service
	creator   objectcreator.Service
	observer  objectcreator.FixedSchemaObserver
	store     objectstore.ObjectStore
	exporter  export.Export
	typeKey   domain.TypeKey
}

func newOwnedClosedFixture(t *testing.T) *ownedClosedFixture {
	t.Helper()
	evidence := os.Getenv("OTZARIA_NATIVE_CLOSED_IMPORT_EVIDENCE")
	if evidence == "" || !filepath.IsAbs(evidence) {
		t.Fatal("explicit owned native export evidence directory required")
	}
	info, err := os.Lstat(evidence)
	ownedClosedNoError(t, err)
	if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		t.Fatal("evidence directory must already be owned and real")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 25*time.Minute)
	service := application.New()
	service.SetClientVersion("otzaria-owned-closed-import", "1.0.0")
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	directory, err := os.MkdirTemp("", "otzaria-owned-closed-import-")
	ownedClosedNoError(t, err)
	temp := filepath.Join(directory, "owned-operation-temporary")
	ownedClosedNoError(t, os.Mkdir(temp, 0700))
	t.Setenv("TMPDIR", temp)
	f := &ownedClosedFixture{ctx: ctx, service: service, directory: directory, evidence: evidence,
		owner: &ownedClosedOwner{temp: temp}}
	t.Cleanup(func() {
		defer cancel()
		drained, observedDone := true, 0
		deadline := time.Now().Add(45 * time.Second)
		for _, operation := range f.owner.operations {
			operation.RequestCancel()
			// A prepared operation still has to enter and return from the
			// original Execute even if setup/assertions failed before Start.
			operation.Start()
		}
		for _, operation := range f.owner.operations {
			remaining := time.Until(deadline)
			if remaining <= 0 {
				drained = false
				break
			}
			select {
			case <-operation.Done():
				observedDone++
			case <-time.After(remaining):
				drained = false
			}
			if !drained {
				break
			}
		}
		if !drained {
			t.Error("preserve original disposable data: owned native operation has not drained")
		}
		stopped := drained
		if drained {
			for _, other := range f.owner.others {
				if err := f.stopActual(other); err != nil {
					t.Errorf("preserve other actual account: %v", err)
					stopped = false
				}
			}
			if err := f.stopActual(service); err != nil {
				t.Errorf("preserve original native account: %v", err)
				stopped = false
			}
		}
		stopped = stopped && service.GetApp() == nil
		stagesGone := true
		if entries, err := os.ReadDir(f.owner.temp); err != nil {
			stagesGone = false
		} else {
			for _, entry := range entries {
				if strings.HasPrefix(entry.Name(), "anytype-owned-annotation-") {
					stagesGone = false
				}
			}
		}
		removed := false
		if stopped && stagesGone {
			if err := os.RemoveAll(directory); err != nil {
				t.Errorf("remove exclusively owned disposable data: %v", err)
			} else {
				removed = true
			}
		} else if !stagesGone {
			t.Error("preserve original owned byte stages: native cleanup is incomplete")
		}
		raw, err := json.MarshalIndent(map[string]any{
			"original_operations_prepared": len(f.owner.operations), "test_start_invocations": f.owner.started,
			"actual_done_observed": observedDone, "all_original_operations_drained": drained,
			"original_account_stop_returned_or_app_absent": stopped,
			"owned_annotation_stages_absent":               stagesGone, "owned_directory_removed": removed,
			"cold_reopen_qualified": false, "body_ack_authority": false,
		}, "", "  ")
		if err != nil {
			t.Error(err)
			return
		}
		if err := ownedClosedWrite(filepath.Dir(evidence), "native-import-cleanup.json", append(raw, '\n')); err != nil {
			t.Error(err)
		}
	})
	_, _, err = service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: directory})
	ownedClosedNoError(t, err)
	// No mnemonic or private account material is logged or retained.
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	account, err := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{
		Name: "Disposable original native export", StorePath: directory,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly,
	})
	ownedClosedNoError(t, err)
	if account == nil || service.GetApp() == nil {
		t.Fatal("actual original account/application missing")
	}
	native := service.GetApp()
	f.nativeApp = native
	f.accountID = app.MustComponent[accountservice.Service](native).Account().SignKey.GetPublic().Account()
	if f.accountID == "" {
		t.Fatal("actual original account identity missing")
	}
	f.blocks = app.MustComponent[*block.Service](native)
	f.creator = app.MustComponent[objectcreator.Service](native)
	var hasObserver bool
	f.observer, hasObserver = f.creator.(objectcreator.FixedSchemaObserver)
	if !hasObserver {
		t.Fatal("actual original fixed schema observer missing")
	}
	f.store = app.MustComponent[objectstore.ObjectStore](native)
	f.exporter = app.MustComponent[export.Export](native)
	spaces := app.MustComponent[space.Service](native)
	f.spaces = spaces
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, "Disposable original export Space")
	details.SetInt64(bundle.RelationKeySpaceType, int64(model.SpaceType_SpaceTypeRegular))
	id, _, err := f.blocks.CreateWorkspace(ctx, &pb.RpcWorkspaceCreateRequest{Details: details.ToProto(),
		UseCase: pb.RpcObjectImportUseCaseRequest_NONE})
	ownedClosedNoError(t, err)
	f.spc, err = spaces.Wait(ctx, id)
	ownedClosedNoError(t, err)
	if f.spc == nil || f.spc.IsPersonal() || f.spc.CommonSpace() == nil || f.spc.Storage() == nil || f.spc.Id() != id {
		t.Fatal("actual initialized regular native Space missing")
	}
	acl := f.spc.CommonSpace().Acl()
	if acl == nil || f.spc.GetAclIdentity() == nil {
		t.Fatal("actual original ACL missing")
	}
	acl.RLock()
	canWrite := acl.AclState() != nil && acl.AclState().Permissions(f.spc.GetAclIdentity()).CanWrite()
	acl.RUnlock()
	if !canWrite {
		t.Fatal("actual native account lacks original Space write permission")
	}
	f.registerSchema(t)
	f.typeKey, err = domain.GetTypeKeyFromRawUniqueKey(annotationschema.TypeUniqueKey)
	ownedClosedNoError(t, err)
	return f
}

// The genuine endpoint qualification already exercises this original registrar
// as a bounded sequence of retained histories. A single call may safely return
// unresolved after some unique native creates; it does not roll those back.
func (f *ownedClosedFixture) registerSchema(t *testing.T) {
	t.Helper()
	definitions, err := annotationschema.Definitions()
	ownedClosedNoError(t, err)
	if len(definitions) != 18 {
		t.Fatal("original annotation schema definition count changed")
	}
	seen := map[string]bool{}
	applies := 0
	phases := 0
	var ready *annotationschema.Registration
	for ; phases < 21; phases++ {
		value, registerErr := annotationschema.Register(f.ctx, f.service, f.accountID, f.spc.Id())
		category := ownedClosedRegistrationCategory(registerErr)
		f.recordSchemaPhase(t, phases, value, registerErr, category)
		if !value.AppAdmitted {
			t.Fatal("actual original registrar lost application admission history")
		}
		for _, creation := range value.Creations {
			if !creation.Invoked {
				continue
			}
			id := creation.Before.ObjectID
			if id == "" || seen[id] || creation.ReturnedObjectID != id {
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
		if registerErr == nil {
			ready = &value
			break
		}
		if category != "unresolved" {
			ownedClosedNoError(t, registerErr)
		}
		// The unchanged original observer and positive index read are the
		// readiness evidence. Later Register calls may create only untouched
		// definitions; incomplete/conflicting or uncertain roots are refused.
		f.waitSchemaReadiness(t, f.spc, definitions, seen)
	}
	if ready == nil || len(seen) != 18 || applies != 1 {
		t.Fatal("export setup did not execute eighteen unique creates and one actual type Apply")
	}
	if ready.Observation.Disposition != annotationschema.MatchingObserved || !ready.AppAdmitted ||
		ready.Observation.AccountIdentity != f.accountID || ready.Observation.SpaceID != f.spc.Id() ||
		len(ready.Observation.Definitions) != len(definitions) {
		t.Fatal("actual original registrar/readback was not qualified")
	}
	for _, entry := range ready.Observation.Definitions {
		if entry.Index != annotationschema.IndexMatch || entry.PersistedStateConflict ||
			entry.Native.Disposition != objectcreator.FixedSchemaPersistedMatch || !seen[entry.Native.ObjectID] {
			t.Fatal("actual original final schema readback differs from its unique creation history")
		}
	}
	payload, err := json.MarshalIndent(map[string]any{
		"schema": 1, "registration_calls": phases + 1, "unique_actual_creates": len(seen),
		"actual_type_apply_calls": applies, "matching_native_definitions": len(definitions),
		"registration_complete": true, "readiness": "original native observer and positive unique index rows",
		"fixture_setup_only": true, "native_import_activated_in_this_space": false, "body_ack_authority": false,
	}, "", "  ")
	ownedClosedNoError(t, err)
	ownedClosedNoError(t, ownedClosedWrite(f.evidence, "schema-registration.json", append(payload, '\n')))
}

// This preserves the precedence of the actual endpoint's resumable category.
// Cancellation and registration conflict never become an unresolved continuation.
func ownedClosedRegistrationCategory(err error) string {
	switch {
	case err == nil:
		return "none"
	case errors.Is(err, context.Canceled), errors.Is(err, context.DeadlineExceeded):
		return "canceled"
	case errors.Is(err, annotationschema.ErrRegistrationConflict):
		return "conflict"
	case errors.Is(err, annotationschema.ErrRegistrationUnresolved), errors.Is(err, objectcreator.ErrFixedSchemaChanged):
		return "unresolved"
	default:
		return "other"
	}
}

// Retain actual call phases before any success, continuation or identity assertion.
// These are historical native identities and heads, not write/body/ACK authority.
func (f *ownedClosedFixture) recordSchemaPhase(t *testing.T, phase int, value annotationschema.Registration, err error, category string) {
	t.Helper()
	native := func(observation objectcreator.FixedSchemaObservation) map[string]any {
		key := ""
		if observation.NativeKey != nil {
			key = observation.NativeKey.Marshal()
		}
		return map[string]any{
			"disposition": uint32(observation.Disposition), "native_key": key,
			"account_id": observation.AccountIdentity, "space_id": observation.SpaceID,
			"object_id": observation.ObjectID, "acl_id": observation.ACLID, "acl_head": observation.ACLHead,
			"persisted_heads": slices.Clone(observation.PersistedHeads),
			"archive_id":      observation.ArchiveID, "archive_heads": slices.Clone(observation.ArchiveHeads),
		}
	}
	creations := make([]map[string]any, 0, len(value.Creations))
	for _, creation := range value.Creations {
		creations = append(creations, map[string]any{
			"before": native(creation.Before), "after": native(creation.After),
			"invoked": creation.Invoked, "returned_object_id": creation.ReturnedObjectID,
		})
	}
	definitions := make([]map[string]any, 0, len(value.Observation.Definitions))
	for _, definition := range value.Observation.Definitions {
		definitions = append(definitions, map[string]any{
			"native": native(definition.Native), "index": string(definition.Index),
			"persisted_state_conflict": definition.PersistedStateConflict,
		})
	}
	raw, marshalErr := json.MarshalIndent(map[string]any{
		"schema": 1, "phase": phase, "error_category": category,
		"fixed_schema_changed": errors.Is(err, objectcreator.ErrFixedSchemaChanged),
		"app_admitted":         value.AppAdmitted, "observation_disposition": string(value.Observation.Disposition),
		"observation_account_id": value.Observation.AccountIdentity, "observation_space_id": value.Observation.SpaceID,
		"definitions": definitions, "creations": creations,
		"type_apply_invoked": value.TypeApplyInvoked, "type_apply_returned": value.TypeApplyReturned,
		"historical_call_phase_only": true, "body_ack_authority": false,
	}, "", "  ")
	ownedClosedNoError(t, marshalErr)
	if phase < 0 || phase >= 21 || len(creations) > 18 || len(definitions) > 18 || len(raw)+1 > 128<<10 {
		t.Fatal("actual original registration history exceeds its fixed fixture evidence bound")
	}
	payload := append(raw, '\n')
	name := fmt.Sprintf("schema-registration-%02d.json", phase)
	ownedClosedNoError(t, ownedClosedWrite(f.evidence, name, payload))
	sum := sha256.Sum256(payload)
	t.Logf("actual original registration phase %d: %s sha256=%x", phase, name, sum)
}

func (f *ownedClosedFixture) waitSchemaReadiness(t *testing.T, spc clientspace.Space, definitions []objectcreator.FixedSchemaDefinition, known map[string]bool) {
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
			ownedClosedNoError(t, err)
			if value.Disposition == objectcreator.FixedSchemaRootOnlyIncomplete || value.Disposition == objectcreator.FixedSchemaPopulatedConflict {
				t.Fatal("native uncertainty/conflict cannot be retried by export setup")
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
			ownedClosedNoError(t, err)
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

func (f *ownedClosedFixture) annotation(t *testing.T, name string) string {
	t.Helper()
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, name)
	for key, value := range map[string]string{
		"pinkhaTorahAnnotationProtocol":            annotationschema.Protocol,
		"pinkhaTorahAnnotationClassification":      "note",
		"pinkhaTorahAnnotationNamespace":           "otzaria-native-archive-specimen",
		"pinkhaTorahAnnotationUUID":                uuid.NewString(),
		"pinkhaTorahAnnotationCreationDestination": "native-fixture",
		"pinkhaTorahAnnotationCreationAccount":     f.accountID,
		"pinkhaTorahAnnotationCreationSpace":       f.spc.Id(),
	} {
		details.SetString(domain.RelationKey(key), value)
	}
	id, created, err := f.creator.CreateObjectUsingObjectUniqueTypeKey(f.ctx, f.spc.Id(), annotationschema.TypeUniqueKey,
		objectcreator.CreateObjectRequest{Details: details})
	ownedClosedNoError(t, err)
	if id == "" || created == nil {
		t.Fatal("original annotation creation did not return a native object")
	}
	return id
}

func (f *ownedClosedFixture) expectedBlock(t *testing.T, s *ownedClosedSpecimen, root, parent string, b *model.Block) string {
	t.Helper()
	expected := proto.Clone(b).(*model.Block)
	if parent == "" {
		parent = root
	}
	id, err := f.blocks.CreateBlock(session.NewContext(), pb.RpcBlockCreateRequest{
		ContextId: root, TargetId: parent, Position: model.Block_Inner, Block: b,
	})
	ownedClosedNoError(t, err)
	if id == "" {
		t.Fatal("original block creation did not return a native block")
	}
	expected.Id = id
	s.Expected[id] = expected
	return id
}
func (f *ownedClosedFixture) text(t *testing.T, s *ownedClosedSpecimen, root, parent, text string, style model.BlockContentTextStyle, marks *model.BlockContentTextMarks) string {
	t.Helper()
	return f.expectedBlock(t, s, root, parent, &model.Block{Content: &model.BlockContentOfText{
		Text: &model.BlockContentText{Text: text, Style: style, Marks: marks},
	}})
}

func (f *ownedClosedFixture) export(t *testing.T, s *ownedClosedSpecimen) {
	t.Helper()
	exportDir := filepath.Join(f.directory, "export-"+s.Kind)
	ownedClosedNoError(t, os.Mkdir(exportDir, 0700))
	path, report, exportErr := f.exporter.Export(f.ctx, pb.RpcObjectListExportRequest{
		SpaceId: f.spc.Id(), ObjectIds: []string{s.RootID}, Path: exportDir, Format: model.Export_Protobuf,
		Zip: true, IsJson: false, IncludeFiles: true, IncludeNested: true, IncludeArchived: true,
		IncludeBacklinks: false, IncludeSpace: false, NoProgress: true,
	})
	reportBytes, err := json.MarshalIndent(report, "", "  ")
	ownedClosedNoError(t, err)
	ownedClosedNoError(t, ownedClosedWrite(f.evidence, s.Kind+"-export-report.json", append(reportBytes, '\n')))
	// Retain an actual bounded partial/oversized output before asserting
	// success; neither retention nor the archive's existence is acceptance.
	var raw []byte
	if path != "" {
		relative, err := filepath.Rel(exportDir, path)
		ownedClosedNoError(t, err)
		if relative == "." || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) || filepath.IsAbs(relative) {
			t.Fatal("original export path escaped its owned export directory")
		}
		info, err := os.Lstat(path)
		ownedClosedNoError(t, err)
		if !info.Mode().IsRegular() || info.Size() > 8<<20 {
			t.Fatal("native export evidence retention bound exceeded")
		}
		raw, err = os.ReadFile(path)
		ownedClosedNoError(t, err)
		ownedClosedNoError(t, ownedClosedWrite(f.evidence, s.Kind+".zip", raw))
	}
	ownedClosedNoError(t, exportErr)
	ownedClosedNoError(t, f.ctx.Err())
	if report == nil || report.Status != model.ExportReport_SUCCESS || report.Succeed <= 0 || report.ObjectErrors != 0 || report.FileErrors != 0 {
		t.Fatal("actual original export report is not complete")
	}
	for _, issue := range report.Issues {
		if issue == nil || issue.Severity == model.ExportReportIssue_ERROR {
			t.Fatal("actual original export reported an error")
		}
	}
	if len(raw) == 0 {
		t.Fatal("actual original export returned no archive")
	}
	hash := sha256.Sum256(raw)
	zr, err := zip.NewReader(bytes.NewReader(raw), int64(len(raw)))
	ownedClosedNoError(t, err)
	if len(zr.File) == 0 || len(zr.File) > 512 {
		t.Fatal("native specimen member inventory exceeds its bound")
	}
	snapshots := make(map[string]*pb.SnapshotWithType)
	binaries := make(map[string][]byte)
	inventory := make([]map[string]any, 0, len(zr.File))
	seen := make(map[string]bool)
	expanded := 0
	for _, member := range zr.File {
		if seen[member.Name] {
			t.Fatal("duplicate member in actual original export")
		}
		seen[member.Name] = true
		stream, err := member.Open()
		ownedClosedNoError(t, err)
		body, readErr := io.ReadAll(io.LimitReader(stream, int64((8<<20)-expanded)+1))
		closeErr := stream.Close()
		ownedClosedNoError(t, readErr)
		ownedClosedNoError(t, closeErr)
		expanded += len(body)
		if expanded > 8<<20 || uint64(len(body)) != member.UncompressedSize64 {
			t.Fatal("native specimen CRC/size budget failed")
		}
		mh := sha256.Sum256(body)
		row := map[string]any{"name": member.Name, "bytes": len(body), "sha256": hex.EncodeToString(mh[:]),
			"zip_flags": member.Flags, "zip_method": member.Method, "zip_extra_hex": hex.EncodeToString(member.Extra)}
		if strings.HasPrefix(member.Name, "files/") {
			binaries[member.Name] = body
			row["kind"] = "file"
		} else if strings.HasSuffix(member.Name, ".pb") {
			snapshot := &pb.SnapshotWithType{}
			ownedClosedNoError(t, snapshot.Unmarshal(body))
			if snapshot.Snapshot == nil || snapshot.Snapshot.Data == nil || snapshot.Snapshot.Data.Details == nil {
				t.Fatal("original export contains no generated snapshot data")
			}
			details := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
			id := details.GetString(bundle.RelationKeyId)
			if id == "" || snapshots[id] != nil {
				t.Fatal("actual exported identity is missing or duplicated")
			}
			snapshots[id] = snapshot
			row["kind"], row["object_id"], row["space_id"], row["smart_block_type"] = "snapshot", id,
				details.GetString(bundle.RelationKeySpaceId), int32(snapshot.SbType)
			row["unique_key"] = snapshot.Snapshot.Data.Key
			row["object_type_keys"] = snapshot.Snapshot.Data.ObjectTypes
		} else {
			row["kind"] = "other"
		}
		inventory = append(inventory, row)
	}
	root := snapshots[s.RootID]
	if root == nil || !slices.Contains(root.Snapshot.Data.ObjectTypes, f.typeKey.URL()) ||
		domain.NewDetailsFromProto(root.Snapshot.Data.Details).GetString(bundle.RelationKeySpaceId) != f.spc.Id() {
		t.Fatal("actual export lacks its native annotation root/type/Space")
	}
	actualBlocks := make(map[string]*model.Block)
	for _, id := range []string{s.RootID, s.LinkedID} {
		if id == "" {
			continue
		}
		snapshot := snapshots[id]
		if snapshot == nil {
			t.Fatal("actual export omitted the linked native object")
		}
		for _, b := range snapshot.Snapshot.Data.Blocks {
			if b != nil {
				actualBlocks[b.Id] = b
			}
		}
	}
	for id, expected := range s.Expected {
		actual := actualBlocks[id]
		if actual == nil {
			t.Fatal("actual export omitted a created native block")
		}
		switch {
		case expected.GetText() != nil:
			want, got := expected.GetText(), actual.GetText()
			if got == nil || got.Text != want.Text || got.Style != want.Style {
				t.Fatal("actual exported text/style differs from original native API input")
			}
			wm, gm := want.GetMarks().GetMarks(), got.GetMarks().GetMarks()
			if len(wm) != len(gm) {
				t.Fatal("actual exported mark count differs from original native API input")
			}
			for i := range wm {
				if !proto.Equal(wm[i], gm[i]) {
					t.Fatal("actual exported marks differ from original native API input")
				}
			}
		case expected.GetLink() != nil:
			if actual.GetLink() == nil || actual.GetLink().TargetBlockId != expected.GetLink().TargetBlockId {
				t.Fatal("actual exported link differs from the native object")
			}
		case expected.GetFile() != nil:
			if actual.GetFile() == nil || actual.GetFile().TargetObjectId != s.AttachmentID {
				t.Fatal("actual exported file block does not reference original upload")
			}
		default:
			t.Fatal("unsupported fixture expectation")
		}
	}
	if s.ParentID != "" && !slices.Contains(actualBlocks[s.ParentID].ChildrenIds, s.ChildID) {
		t.Fatal("actual native export lost its nested block relationship")
	}
	attachmentSource := ""
	if s.AttachmentID != "" {
		attachment := snapshots[s.AttachmentID]
		if attachment == nil || coresb.SmartBlockType(attachment.SbType) != coresb.SmartBlockTypeFileObject ||
			attachment.Snapshot.Data.FileInfo == nil || attachment.Snapshot.Data.FileInfo.FileId == "" {
			t.Fatal("actual exported upload lacks original file object/FileInfo")
		}
		attachmentSource = domain.NewDetailsFromProto(attachment.Snapshot.Data.Details).GetString(bundle.RelationKeySource)
		if !bytes.Equal(binaries[attachmentSource], s.AttachmentBytes) {
			t.Fatal("actual exported attachment differs from original uploaded bytes")
		}
	}
	s.Raw, s.Digest, s.SourceSpace, s.Snapshots = bytes.Clone(raw), hash, f.spc.Id(), snapshots
	sort.Slice(inventory, func(i, j int) bool { return inventory[i]["name"].(string) < inventory[j]["name"].(string) })
	ids := make([]string, 0, len(snapshots))
	for id := range snapshots {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	manifest := map[string]any{
		"schema": 1, "specimen": s.Kind, "archive": s.Kind + ".zip", "archive_sha256": hex.EncodeToString(hash[:]),
		"archive_bytes": len(raw), "root_id": s.RootID, "space_id": f.spc.Id(), "account_id": f.accountID,
		"generated_snapshot_ids": ids, "members": inventory, "expected_native_blocks": len(s.Expected),
		"native_text_format_nested_attachment_checks_passed": true, "attachment_source": attachmentSource,
		"original_export_report_success": true, "native_import_activated": false, "body_ack_authority": false,
		"cold_reopen_qualified": false, "swift_invocation_qualified": false,
	}
	encoded, err := json.MarshalIndent(manifest, "", "  ")
	ownedClosedNoError(t, err)
	payload := append(encoded, '\n')
	ownedClosedNoError(t, ownedClosedWrite(f.evidence, s.Kind+"-manifest.json", payload))
	rh := sha256.Sum256(payload)
	t.Logf("actual original native specimen=%s members=%d archive_sha256=%s receipt_sha256=%s",
		s.Kind, len(zr.File), hex.EncodeToString(hash[:]), hex.EncodeToString(rh[:]))
}

func ownedClosedWrite(directory, name string, payload []byte) error {
	file, err := os.OpenFile(filepath.Join(directory, name), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	n, writeErr := file.Write(payload)
	closeErr := file.Close()
	if writeErr != nil {
		return writeErr
	}
	if n != len(payload) {
		return io.ErrShortWrite
	}
	return closeErr
}
func ownedClosedNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(fmt.Errorf("actual original native export operation: %w", err))
	}
}

func (f *ownedClosedFixture) target(t *testing.T, name string, source *ownedClosedSpecimen) *ownedClosedFixture {
	t.Helper()
	target := *f
	target.evidence = filepath.Join(filepath.Dir(f.evidence), "target-"+name)
	ownedClosedNoError(t, os.Mkdir(target.evidence, 0700))
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, "Disposable closed import "+name)
	details.SetInt64(bundle.RelationKeySpaceType, int64(model.SpaceType_SpaceTypeRegular))
	id, _, err := f.blocks.CreateWorkspace(f.ctx, &pb.RpcWorkspaceCreateRequest{
		Details: details.ToProto(), UseCase: pb.RpcObjectImportUseCaseRequest_NONE,
	})
	ownedClosedNoError(t, err)
	target.spc, err = f.spaces.Wait(f.ctx, id)
	ownedClosedNoError(t, err)
	if target.spc == nil || target.spc.IsPersonal() || target.spc.Id() != id ||
		target.spc.CommonSpace() == nil || target.spc.Storage() == nil {
		t.Fatal("actual new regular target Space unavailable")
	}
	target.registerSchema(t)
	target.prepareBundled(t, source)
	return &target
}

func (f *ownedClosedFixture) stagePaths(t *testing.T) []string {
	t.Helper()
	entries, err := os.ReadDir(f.owner.temp)
	ownedClosedNoError(t, err)
	var result []string
	for _, entry := range entries {
		if strings.HasPrefix(entry.Name(), "anytype-owned-annotation-") {
			info, err := os.Lstat(filepath.Join(f.owner.temp, entry.Name()))
			ownedClosedNoError(t, err)
			if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
				t.Fatal("original private stage inventory contains an unexpected file kind")
			}
			result = append(result, filepath.Join(f.owner.temp, entry.Name()))
		}
	}
	slices.Sort(result)
	return result
}

func (f *ownedClosedFixture) prepare(t *testing.T, source *ownedClosedSpecimen) (*importer.OwnedImportOperation, string) {
	t.Helper()
	if len(f.stagePaths(t)) != 0 {
		t.Fatal("prior owned annotation staging has not drained")
	}
	input := bytes.Clone(source.Raw)
	operation, err := application.PrepareOwnedAnnotationImportForNativeTest(
		f.service, f.ctx, f.nativeApp, f.accountID, input, source.Digest,
		source.RootID, source.SourceSpace, f.spc.Id())
	if operation != nil {
		// Register cleanup immediately, before any assertion may stop this test.
		f.owner.operations = append(f.owner.operations, operation)
	}
	ownedClosedNoError(t, err)
	if operation == nil {
		t.Fatal("original application owner returned no real native operation")
	}
	ownership := application.ObserveOwnedAnnotationImportForNativeTest(f.service, f.nativeApp, f.accountID, operation)
	if !ownership.CurrentApplication || !ownership.MatchingUsableLease || !ownership.OperationRegistered || ownership.PendingRetirement {
		t.Fatal("closed native operation was not retained by original account/lease/registry")
	}
	select {
	case <-operation.Done():
		t.Fatal("prepared native operation claimed completion before Start")
	default:
	}
	if _, done := operation.Result(); done {
		t.Fatal("prepared native operation manufactured a result")
	}
	stages := f.stagePaths(t)
	if len(stages) != 1 {
		t.Fatal("original byte owner did not create one exclusive private stage")
	}
	stage := stages[0]
	info, err := os.Lstat(stage)
	ownedClosedNoError(t, err)
	if info.Mode().Perm() != 0700 {
		t.Fatal("private annotation stage is not mode0700")
	}
	archive := filepath.Join(stage, "archive.zip")
	info, err = os.Lstat(archive)
	ownedClosedNoError(t, err)
	if !info.Mode().IsRegular() || info.Mode().Perm() != 0600 || info.Size() != int64(len(source.Raw)) {
		t.Fatal("owned native archive is not an exact private0600 file")
	}
	// Mutate only the caller's already-copied slice. The real stage and
	// converter input must remain the original observed immutable bytes.
	input[0] ^= 0xff
	staged, err := os.ReadFile(archive)
	ownedClosedNoError(t, err)
	if !bytes.Equal(staged, source.Raw) || sha256.Sum256(staged) != source.Digest {
		t.Fatal("caller slice mutation changed the original owned staged archive")
	}
	return operation, stage
}

func (f *ownedClosedFixture) start(operation *importer.OwnedImportOperation) {
	f.owner.started++
	operation.Start()
}

func (f *ownedClosedFixture) stageRemoved(t *testing.T, stage string) {
	t.Helper()
	if _, err := os.Lstat(stage); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("real Done did not follow removal of the owned byte stage: %v", err)
	}
}

func (f *ownedClosedFixture) pending(t *testing.T, operation *importer.OwnedImportOperation, stage string) {
	t.Helper()
	select {
	case <-operation.Done():
		t.Fatal("cancellation falsely closed native Done before actual Execute returned")
	default:
	}
	if _, observed := operation.Result(); observed {
		t.Fatal("pending native operation reported completion")
	}
	owner := application.ObserveOwnedAnnotationImportForNativeTest(f.service, f.nativeApp, f.accountID, operation)
	if !owner.CurrentApplication || !owner.MatchingUsableLease || !owner.OperationRegistered || !owner.PendingRetirement {
		t.Fatal("original pending import lost account, lease or registry ownership")
	}
	if _, err := os.Stat(f.directory); err != nil {
		t.Fatal("original pending native account directory was removed")
	}
	if _, err := os.Stat(filepath.Join(stage, "archive.zip")); err != nil {
		t.Fatal("cancel request removed the archive before actual owned execution")
	}
}

func (f *ownedClosedFixture) wait(t *testing.T, name string, operation *importer.OwnedImportOperation) importer.OwnedImportOutcome {
	t.Helper()
	select {
	case <-operation.Done():
	case <-time.After(150 * time.Second):
		t.Fatal("original closed annotation import did not return within its native bound")
	case <-f.ctx.Done():
		t.Fatal("native fixture deadline before original operation completion")
	}
	result, complete := operation.Result()
	if !complete {
		t.Fatal("actual closed Done lacks its immutable historical result")
	}
	// Preserve real return data before semantic assertions. This also retains
	// bounded partial readback when the original operation fails.
	observation, hasReadback := result.OriginalAnnotationReadback()
	mapping, hasMapping := result.NativeMappingObservation()
	problems := result.NativeMappingProblems()
	problemCount := len(problems)
	if len(problems) > 16 {
		problems = problems[:16]
	}
	if len(mapping.SourceAssignments()) > 512 || len(result.Files()) > 512 {
		t.Fatal("native historical result exceeds fixed evidence bounds")
	}
	errorDescription := ""
	if result.Err() != nil {
		errorDescription = result.Err().Error()
		if len(errorDescription) > 2048 {
			errorDescription = errorDescription[:2048]
		}
	}
	files := make([]map[string]any, 0, len(result.Files()))
	for _, value := range result.Files() {
		files = append(files, map[string]any{"kind": value.Kind, "object_id": value.ObjectID,
			"block_id": value.BlockID, "file_object_id": value.FileObjectID, "returned_error": value.Err != nil})
	}
	schemaDiagnostic := map[string]any{"available": false, "written": false, "truncated": false}
	var mismatch interface{ OwnedAnnotationSchemaDiagnostic() []byte }
	if errors.As(result.Err(), &mismatch) {
		raw := mismatch.OwnedAnnotationSchemaDiagnostic()
		schemaDiagnostic["available"] = true
		schemaDiagnostic["bytes"] = len(raw)
		if len(raw) == 0 || len(raw) > 3<<20 || !json.Valid(raw) {
			schemaDiagnostic["status"] = "OMITTED_INVALID_OR_OVERSIZED"
		} else if err := ownedClosedWrite(f.evidence, name+"-schema-comparison-diagnostic.json", raw); err != nil {
			schemaDiagnostic["status"] = "WRITE_FAILED"
			t.Log("historical schema diagnostic could not be retained; original refusal is unchanged")
		} else {
			schemaDiagnostic["status"] = "COMPLETE"
			schemaDiagnostic["written"] = true
		}
	}
	values := map[string]any{
		"schema_comparison_diagnostic": schemaDiagnostic,
		"actual_done_observed":         complete, "target_space": result.TargetSpaceID(),
		"actual_process_id": result.ProcessID(), "object_count": result.ObjectsCount(),
		"cancellation_requested": result.CancellationRequested(), "returned_error": result.Err() != nil,
		"bounded_error_description": errorDescription,
		"native_mapping_observed":   hasMapping, "native_mapping_complete": mapping.CompleteForSelectedSnapshots(),
		"native_trace_id": mapping.TraceID(), "native_mapping_problems": problems,
		"native_mapping_problem_count": problemCount,
		"source_assignments":           mapping.SourceAssignments(), "actual_file_returns": files,
		"readback_observed": hasReadback, "readback_stage": uint8(observation.Stage()),
		"readback_source_snapshots":    observation.SourceSnapshots(),
		"readback_annotation_pages":    observation.AnnotationPages(),
		"readback_file_objects":        observation.FileObjects(),
		"readback_readonly_contexts":   observation.ReadOnlyContexts(),
		"readback_additional_contexts": observation.AdditionalImportContexts(),
		"actual_export_report":         observation.CopyExportReport(),
	}
	if hasReadback {
		raw := observation.CopyNativeArchive()
		if len(raw) > 1048576 {
			t.Fatal("historical readback archive exceeds the explicit annotation policy")
		}
		values["readback_archive_bytes"] = len(raw)
		sum := sha256.Sum256(raw)
		values["readback_archive_sha256"] = hex.EncodeToString(sum[:])
		if len(raw) != 0 {
			ownedClosedNoError(t, ownedClosedWrite(f.evidence, name+"-native-readback.zip", raw))
		}
	}
	f.receipt(t, name+"-outcome.json", values)
	return result
}

func (f *ownedClosedFixture) stopActual(service *application.Service) error {
	f.owner.stopMu.Lock()
	stop := f.owner.stops[service]
	start := false
	// Resolve an owned Stop before consulting app absence: the original
	// operation can still be returning after the app pointer becomes nil.
	if stop == nil && service.GetApp() != nil {
		if f.owner.stops == nil {
			f.owner.stops = make(map[*application.Service]*ownedClosedStop)
		}
		stop = &ownedClosedStop{done: make(chan struct{})}
		f.owner.stops[service] = stop
		start = true
	}
	f.owner.stopMu.Unlock()
	if stop == nil {
		return nil
	}
	if start {
		go func() {
			stop.err = service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true})
			close(stop.done)
		}()
	}
	select {
	case <-stop.done:
		// Closing done publishes this exact original return, including a
		// failure. Later cleanup joins it without an implicit native retry.
		return stop.err
	case <-time.After(30 * time.Second):
		return errors.New("actual original AccountStop has not returned within the cleanup bound")
	}
}

func (f *ownedClosedFixture) receipt(t *testing.T, name string, values map[string]any) {
	t.Helper()
	values["schema"] = 1
	values["actual_account_identity"] = f.accountID
	values["actual_space_id"] = f.spc.Id()
	values["historical_native_evidence_only"] = true
	values["body_ack_authority"] = false
	values["cold_reopen_qualified"] = false
	values["swift_invocation_qualified"] = false
	raw, err := json.MarshalIndent(values, "", "  ")
	ownedClosedNoError(t, err)
	payload := append(raw, '\n')
	if len(payload) > 512<<10 || filepath.Base(name) != name {
		t.Fatal("native receipt exceeded the exact owned path/size boundary")
	}
	ownedClosedNoError(t, ownedClosedWrite(f.evidence, name, payload))
	sum := sha256.Sum256(payload)
	t.Logf("actual closed original import receipt=%s sha256=%x", name, sum)
}

func (f *ownedClosedFixture) schemaKeys(t *testing.T, source *ownedClosedSpecimen) []domain.UniqueKey {
	t.Helper()
	byKey := make(map[string]domain.UniqueKey)
	for _, snapshot := range source.Snapshots {
		kind := coresb.SmartBlockType(snapshot.SbType)
		if kind != coresb.SmartBlockTypeObjectType && kind != coresb.SmartBlockTypeRelation {
			continue
		}
		key, err := domain.NewUniqueKey(kind, snapshot.Snapshot.Data.Key)
		ownedClosedNoError(t, err)
		if byKey[key.Marshal()] != nil {
			t.Fatal("genuine source graph has duplicate native schema keys")
		}
		byKey[key.Marshal()] = key
	}
	for _, relation := range []domain.RelationKey{bundle.RelationKeyImportType, bundle.RelationKeyOldAnytypeID, bundle.RelationKeySourceFilePath} {
		key, err := domain.NewUniqueKey(coresb.SmartBlockTypeRelation, relation.String())
		ownedClosedNoError(t, err)
		byKey[key.Marshal()] = key
	}
	names := make([]string, 0, len(byKey))
	for name := range byKey {
		names = append(names, name)
	}
	slices.Sort(names)
	keys := make([]domain.UniqueKey, 0, len(names))
	for _, name := range names {
		keys = append(keys, byKey[name])
	}
	return keys
}

func (f *ownedClosedFixture) prepareBundled(t *testing.T, source *ownedClosedSpecimen) {
	t.Helper()
	definitions, err := annotationschema.Definitions()
	ownedClosedNoError(t, err)
	fixed := make(map[string]bool, len(definitions))
	for _, value := range definitions {
		fixed[value.Key.Marshal()] = true
	}
	var sourceObjects []string
	for _, key := range f.schemaKeys(t, source) {
		if fixed[key.Marshal()] {
			continue
		}
		switch key.SmartblockType() {
		case coresb.SmartBlockTypeObjectType:
			if !bundle.HasObjectTypeByKey(domain.TypeKey(key.InternalKey())) {
				t.Fatal("source schema is not an actual original bundled type")
			}
			sourceObjects = append(sourceObjects, domain.TypeKey(key.InternalKey()).BundledURL())
		case coresb.SmartBlockTypeRelation:
			if !bundle.HasRelation(domain.RelationKey(key.InternalKey())) {
				t.Fatal("source schema is not an actual original bundled relation")
			}
			sourceObjects = append(sourceObjects, domain.RelationKey(key.InternalKey()).BundledURL())
		default:
			t.Fatal("unexpected original schema preparation kind")
		}
	}
	slices.Sort(sourceObjects)
	ids, _, installErr := f.blocks.SpaceInstallBundledObjects(f.ctx, f.spc.Id(), sourceObjects)
	f.receipt(t, "bundled-preparation-call.json", map[string]any{
		"original_requested_bundled_sources": sourceObjects, "original_returned_ids": ids,
		"original_returned_error": installErr != nil, "fixture_setup_before_this_space_import": true,
		"readiness_claimed_from_installer_return": false,
	})
	ownedClosedNoError(t, installErr)
	// Original install may report partial work without an error. Readiness
	// must come from complete real raw native observations and unique index
	// rows; no installer return, elapsed delay or callback boolean qualifies it.
	deadline := time.Now().Add(45 * time.Second)
	var preceding map[string][]string
	for {
		current, ready := f.observeSchemaHeads(t, source, false)
		if ready && preceding != nil && reflect.DeepEqual(preceding, current) {
			f.receipt(t, "readonly-prerequisites.json", map[string]any{
				"exact_schema_keys": len(current), "stable_original_heads": current,
				"actual_complete_raw_native_observations": true, "actual_unique_positive_index_rows": true,
				"additional_metadata_keys": []string{bundle.RelationKeyImportType.String(), bundle.RelationKeyOldAnytypeID.String(), bundle.RelationKeySourceFilePath.String()},
			})
			return
		}
		if ready {
			preceding = current
		} else {
			preceding = nil
		}
		if time.Now().After(deadline) {
			t.Fatal("actual readonly bundled prerequisites did not become complete and stable")
		}
		select {
		case <-f.ctx.Done():
			t.Fatal(f.ctx.Err())
		case <-time.After(100 * time.Millisecond):
		}
	}
}

func (f *ownedClosedFixture) observeSchemaHeads(t *testing.T, source *ownedClosedSpecimen, require bool) (map[string][]string, bool) {
	t.Helper()
	observer, ok := f.creator.(objectcreator.OwnedAnnotationSchemaObserver)
	if !ok {
		t.Fatal("actual original creator does not expose the additive raw observer")
	}
	definitions, err := annotationschema.Definitions()
	ownedClosedNoError(t, err)
	fixed := make(map[string]objectcreator.FixedSchemaDefinition, len(definitions))
	for _, value := range definitions {
		fixed[value.Key.Marshal()] = value
	}
	heads, complete := make(map[string][]string), true
	for _, key := range f.schemaKeys(t, source) {
		var actual objectcreator.OwnedAnnotationSchemaObservation
		if definition, present := fixed[key.Marshal()]; present {
			actual, err = observer.ObserveOwnedAnnotationFixedSchema(f.ctx, f.spc, definition)
		} else {
			actual, err = observer.ObserveOwnedAnnotationBundledSchema(f.ctx, f.spc, key)
		}
		if errors.Is(err, objectcreator.ErrFixedSchemaChanged) && !require {
			complete = false
			continue
		}
		ownedClosedNoError(t, err)
		if actual.Disposition == objectcreator.FixedSchemaRootOnlyIncomplete ||
			actual.Disposition == objectcreator.FixedSchemaPopulatedConflict {
			f.receipt(t, "schema-prerequisite-failure.json", map[string]any{
				"schema_key": key.Marshal(), "disposition": uint8(actual.Disposition),
				"require_persisted_match": require,
				"persisted_head_count":    len(actual.PersistedHeads), "archive_head_count": len(actual.ArchiveHeads),
				"installer_retry_performed": false, "readiness_accepted": false,
			})
			t.Fatalf("uncertain/conflicting native prerequisite cannot be installed again or treated as ready: key=%s disposition=%d", key.Marshal(), actual.Disposition)
		}
		if actual.Disposition != objectcreator.FixedSchemaPersistedMatch {
			if require {
				t.Fatalf("original readonly schema is not a real persisted match: disposition=%d", actual.Disposition)
			}
			complete = false
			continue
		}
		if actual.AccountIdentity != f.accountID || actual.SpaceID != f.spc.Id() ||
			actual.ObjectID == "" || len(actual.PersistedHeads) == 0 || actual.CopySnapshot() == nil {
			t.Fatal("actual raw schema readback has another account/Space or missing persisted data")
		}
		field, value := bundle.RelationKeyUniqueKey, key.Marshal()
		if key.SmartblockType() == coresb.SmartBlockTypeRelation {
			field, value = bundle.RelationKeyRelationKey, key.InternalKey()
		}
		rows, err := f.store.SpaceIndex(f.spc.Id()).QueryRaw(&database.Filters{FilterObj: database.FilterEq{
			Key: field, Cond: model.BlockContentDataviewFilter_Equal, Value: domain.String(value),
		}}, 2, 0)
		ownedClosedNoError(t, err)
		if len(rows) == 0 && !require {
			complete = false
			continue
		}
		if len(rows) != 1 || rows[0].Details == nil ||
			rows[0].Details.GetString(bundle.RelationKeyId) != actual.ObjectID ||
			rows[0].Details.GetString(bundle.RelationKeySpaceId) != f.spc.Id() ||
			rows[0].Details.GetBool(bundle.RelationKeyIsArchived) ||
			rows[0].Details.GetBool(bundle.RelationKeyIsDeleted) ||
			rows[0].Details.GetBool(bundle.RelationKeyIsUninstalled) {
			t.Fatal("actual schema positive index identity or disposition is inconsistent")
		}
		valueHeads := slices.Clone(actual.PersistedHeads)
		slices.Sort(valueHeads)
		heads[actual.ObjectID] = valueHeads
	}
	return heads, complete
}

func (f *ownedClosedFixture) readOnlyHeads(t *testing.T, source *ownedClosedSpecimen) map[string][]string {
	t.Helper()
	heads, complete := f.observeSchemaHeads(t, source, true)
	if !complete {
		t.Fatal("complete actual readonly prerequisite observation required")
	}
	return heads
}

func (f *ownedClosedFixture) pageHeads(t *testing.T, id string) []string {
	t.Helper()
	var heads []string
	ownedClosedNoError(t, f.spc.DoCtx(f.ctx, id, func(object smartblock.SmartBlock) error {
		if object.SpaceID() != f.spc.Id() || object.Tree() == nil {
			return errors.New("actual mapped native object identity missing")
		}
		heads = slices.Clone(object.Tree().Heads())
		return nil
	}))
	if len(heads) == 0 {
		t.Fatal("actual mapped native object has no persisted heads")
	}
	slices.Sort(heads)
	return heads
}

func (f *ownedClosedFixture) waitImportedIdentity(t *testing.T, sourceID, targetID string) {
	t.Helper()
	deadline := time.Now().Add(30 * time.Second)
	for {
		rows, err := f.store.SpaceIndex(f.spc.Id()).QueryRaw(&database.Filters{FilterObj: database.FilterEq{
			Key: bundle.RelationKeyOldAnytypeID, Cond: model.BlockContentDataviewFilter_Equal, Value: domain.String(sourceID),
		}}, 2, 0)
		ownedClosedNoError(t, err)
		if len(rows) == 1 && rows[0].Details != nil && rows[0].Details.GetString(bundle.RelationKeyId) == targetID {
			return
		}
		if len(rows) != 0 {
			t.Fatal("actual imported source index is ambiguous or inconsistent")
		}
		if time.Now().After(deadline) {
			t.Fatal("real imported source identity index did not become ready")
		}
		select {
		case <-f.ctx.Done():
			t.Fatal(f.ctx.Err())
		case <-time.After(100 * time.Millisecond):
		}
	}
}

func (f *ownedClosedFixture) noImportedIdentity(t *testing.T, source *ownedClosedSpecimen) {
	t.Helper()
	for id, snapshot := range source.Snapshots {
		kind := coresb.SmartBlockType(snapshot.SbType)
		if kind != coresb.SmartBlockTypePage && kind != coresb.SmartBlockTypeFileObject {
			continue
		}
		rows, err := f.store.SpaceIndex(f.spc.Id()).QueryRaw(&database.Filters{FilterObj: database.FiltersOr{
			database.FilterEq{Key: bundle.RelationKeyOldAnytypeID, Value: domain.String(id)},
			database.FilterEq{Key: bundle.RelationKeyUniqueKey, Value: domain.String(id)},
			database.FilterEq{Key: bundle.RelationKeyId, Value: domain.String(id)},
		}}, 2, 0)
		ownedClosedNoError(t, err)
		if len(rows) != 0 {
			t.Fatal("refused-before-write native operation left an imported source identity")
		}
	}
}

func (f *ownedClosedFixture) assertRoundTrip(t *testing.T, source *ownedClosedSpecimen, result importer.OwnedImportOutcome) {
	t.Helper()
	ownedClosedNoError(t, result.Err())
	if result.CancellationRequested() || result.TargetSpaceID() != f.spc.Id() || result.ProcessID() != "" {
		t.Fatal("actual original no-progress import completion identity is inconsistent")
	}
	mapping, hasMapping := result.NativeMappingObservation()
	if !hasMapping || !mapping.CompleteForSelectedSnapshots() || mapping.TraceID() == "" ||
		mapping.TargetSpaceID() != f.spc.Id() || mapping.ProcessID() != "" ||
		len(result.NativeMappingProblems()) != 0 || len(mapping.FilteredSources()) != 0 ||
		len(mapping.GeneratedAssignments()) != 0 || len(mapping.KeptReferenceIDs()) != 0 ||
		mapping.NonInjectiveDestinations() {
		t.Fatal("actual original mapping lacks complete injective whole-graph source coverage")
	}
	assignments := make(map[string]string)
	targets := make(map[string]bool)
	for _, row := range mapping.SourceAssignments() {
		if source.Snapshots[row.SourceObjectID] == nil || row.SourceSpaceID != source.SourceSpace ||
			row.NativeID == "" || row.ConverterID == "" || row.ArchivePath == "" || row.MemberPath == "" ||
			assignments[row.SourceObjectID] != "" || targets[row.NativeID] {
			t.Fatal("actual native mapping is not bound to the genuine complete source graph")
		}
		assignments[row.SourceObjectID] = row.NativeID
		targets[row.NativeID] = true
	}
	if len(assignments) != len(source.Snapshots) || assignments[source.RootID] == "" ||
		assignments[source.RootID] == source.RootID {
		t.Fatal("actual native mapping omitted or reused the original annotation root")
	}
	readback, observed := result.OriginalAnnotationReadback()
	if !observed || readback.Stage() != importer.OwnedAnnotationBodyMatched ||
		readback.AccountID() != f.accountID || readback.SpaceID() != f.spc.Id() ||
		readback.RootID() != assignments[source.RootID] || readback.SourceArchiveSHA256() != source.Digest ||
		readback.SourceSnapshots() != len(source.Snapshots) {
		t.Fatal("same-owner actual original export/body observation is not complete and bound")
	}
	report := readback.CopyExportReport()
	if report == nil || report.Status != model.ExportReport_SUCCESS || report.Succeed <= 0 ||
		report.ObjectErrors != 0 || report.FileErrors != 0 || len(report.Issues) != 0 {
		t.Fatal("actual readback export report is incomplete")
	}
	raw := readback.CopyNativeArchive()
	if len(raw) == 0 || len(raw) > 1048576 || sha256.Sum256(raw) != readback.NativeArchiveSHA256() {
		t.Fatal("actual readback bytes/digest differ from their historical native observation")
	}
	zr, err := zip.NewReader(bytes.NewReader(raw), int64(len(raw)))
	ownedClosedNoError(t, err)
	if len(zr.File) == 0 || len(zr.File) > 512 {
		t.Fatal("actual readback archive member count outside original policy")
	}
	snapshots, binaries := make(map[string]*pb.SnapshotWithType), make(map[string][]byte)
	seen := make(map[string]bool)
	expanded := 0
	for _, member := range zr.File {
		if seen[member.Name] || !member.Mode().IsRegular() {
			t.Fatal("actual readback duplicate or non-regular member")
		}
		seen[member.Name] = true
		stream, err := member.Open()
		ownedClosedNoError(t, err)
		body, readErr := io.ReadAll(io.LimitReader(stream, int64((8<<20)-expanded)+1))
		closeErr := stream.Close()
		ownedClosedNoError(t, errors.Join(readErr, closeErr))
		expanded += len(body)
		if expanded > 8<<20 || uint64(len(body)) != member.UncompressedSize64 {
			t.Fatal("actual readback CRC/expanded member size differs")
		}
		if strings.HasPrefix(member.Name, "files/") {
			binaries[member.Name] = body
		} else if strings.HasSuffix(member.Name, ".pb") {
			value := &pb.SnapshotWithType{}
			ownedClosedNoError(t, value.Unmarshal(body))
			if value.Snapshot == nil || value.Snapshot.Data == nil || value.Snapshot.Data.Details == nil {
				t.Fatal("actual native export omitted generated snapshot data")
			}
			details := domain.NewDetailsFromProto(value.Snapshot.Data.Details)
			id := details.GetString(bundle.RelationKeyId)
			if id == "" || snapshots[id] != nil || details.GetString(bundle.RelationKeySpaceId) != f.spc.Id() {
				t.Fatal("actual exported object identity is not in the mapped target Space")
			}
			snapshots[id] = value
		} else {
			t.Fatal("unexpected actual native readback member")
		}
	}
	for _, target := range assignments {
		if snapshots[target] == nil {
			t.Fatal("actual native readback dropped a complete original graph member")
		}
	}
	for id, value := range snapshots {
		if targets[id] {
			continue
		}
		key := domain.RelationKey(value.Snapshot.Data.Key)
		if coresb.SmartBlockType(value.SbType) != coresb.SmartBlockTypeRelation ||
			(key != bundle.RelationKeyImportType && key != bundle.RelationKeyOldAnytypeID && key != bundle.RelationKeySourceFilePath) {
			t.Fatal("native readback contains an unowned additional graph member")
		}
		expected, err := f.spc.GetRelationIdByKey(f.ctx, key)
		ownedClosedNoError(t, err)
		if id != expected {
			t.Fatal("native import metadata does not use its real original bundled target identity")
		}
	}
	if len(snapshots)-len(assignments) != readback.AdditionalImportContexts() ||
		readback.AdditionalImportContexts() > 3 {
		t.Fatal("native readback additional metadata inventory differs")
	}
	actualBlocks := make(map[string]*model.Block)
	for _, sourceID := range []string{source.RootID, source.LinkedID} {
		if sourceID == "" {
			continue
		}
		value := snapshots[assignments[sourceID]]
		if value == nil || !slices.Contains(value.Snapshot.Data.ObjectTypes, f.typeKey.URL()) {
			t.Fatal("mapped original annotation object/type omitted by genuine readback")
		}
		for _, b := range value.Snapshot.Data.Blocks {
			if b != nil {
				actualBlocks[b.Id] = b
			}
		}
	}
	for id, expected := range source.Expected {
		actual := actualBlocks[id]
		if actual == nil {
			t.Fatal("actual mapped native export omitted an original API-created block")
		}
		switch {
		case expected.GetText() != nil:
			want, got := expected.GetText(), actual.GetText()
			if got == nil || got.Text != want.Text || got.Style != want.Style {
				t.Fatal("actual imported text/style differs from original native API input")
			}
			wm, gm := want.GetMarks().GetMarks(), got.GetMarks().GetMarks()
			if len(wm) != len(gm) {
				t.Fatal("actual imported mark count differs from original native API input")
			}
			for i := range wm {
				if !proto.Equal(wm[i], gm[i]) {
					t.Fatal("actual imported marks differ from original native API input")
				}
			}
		case expected.GetLink() != nil:
			if actual.GetLink() == nil ||
				actual.GetLink().TargetBlockId != assignments[expected.GetLink().TargetBlockId] {
				t.Fatal("actual original linked annotation was not mapped in native body")
			}
		case expected.GetFile() != nil:
			if actual.GetFile() == nil ||
				actual.GetFile().TargetObjectId != assignments[source.AttachmentID] ||
				actual.GetFile().Name != expected.GetFile().Name ||
				actual.GetFile().Size_ != int64(len(source.AttachmentBytes)) {
				t.Fatal("actual original file block does not match the returned native upload and bytes")
			}
		default:
			t.Fatal("unowned native expectation")
		}
	}
	if source.ParentID != "" && !slices.Contains(actualBlocks[source.ParentID].ChildrenIds, source.ChildID) {
		t.Fatal("actual imported nested block relationship changed")
	}
	pages, fileObjects := 1, 0
	if source.LinkedID != "" {
		pages++
	}
	if source.AttachmentID != "" {
		fileObjects = 1
		attachment := snapshots[assignments[source.AttachmentID]]
		if attachment == nil || coresb.SmartBlockType(attachment.SbType) != coresb.SmartBlockTypeFileObject ||
			attachment.Snapshot.Data.FileInfo == nil || attachment.Snapshot.Data.FileInfo.FileId == "" {
			t.Fatal("actual native mapped attachment file identity missing")
		}
		fileSource := domain.NewDetailsFromProto(attachment.Snapshot.Data.Details).GetString(bundle.RelationKeySource)
		if len(binaries) != 1 || !bytes.Equal(binaries[fileSource], source.AttachmentBytes) {
			t.Fatal("actual original uploader/readback did not preserve the complete native binary")
		}
	} else if len(binaries) != 0 {
		t.Fatal("native readback invented a binary for a non-file specimen")
	}
	if readback.AnnotationPages() != pages || readback.FileObjects() != fileObjects ||
		readback.ReadOnlyContexts()+pages+fileObjects != len(source.Snapshots) {
		t.Fatal("actual whole native graph role counts differ from genuine original inputs")
	}
	for _, file := range result.Files() {
		if file.Err != nil {
			t.Fatal("actual native file outcome returned an error despite body success")
		}
	}
	f.waitImportedIdentity(t, source.RootID, readback.RootID())
	_ = f.pageHeads(t, readback.RootID())
}

func (f *ownedClosedFixture) otherIdentity(t *testing.T) crypto.PubKey {
	t.Helper()
	other := application.New()
	other.SetClientVersion("otzaria-closed-import-acl-owner", "1.0.0")
	directory, err := os.MkdirTemp(f.directory, "other-actual-account-")
	ownedClosedNoError(t, err)
	// The shared early cleanup now owns this account before setup can fail.
	f.owner.others = append(f.owner.others, other)
	_, _, err = other.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: directory})
	ownedClosedNoError(t, err)
	other.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	account, err := other.AccountCreate(f.ctx, &pb.RpcAccountCreateRequest{
		Name: "Disposable original signed ACL owner", StorePath: directory,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly,
	})
	ownedClosedNoError(t, err)
	if account == nil || other.GetApp() == nil {
		t.Fatal("other actual original account did not start")
	}
	return app.MustComponent[accountservice.Service](other.GetApp()).Account().SignKey.GetPublic()
}

func (f *ownedClosedFixture) downgradeToReader(t *testing.T, otherIdentity crypto.PubKey) {
	t.Helper()
	if !app.MustComponent[*config.Config](f.nativeApp).IsLocalOnlyMode() {
		t.Fatal("signed ACL control must own an actual disposable LocalOnly account")
	}
	acl := f.spc.CommonSpace().Acl()
	ownedClosedNoError(t, func() error {
		acl.Lock()
		defer acl.Unlock()
		add, err := acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{
			Additions: []list.AccountAdd{{Identity: otherIdentity, Permissions: list.AclPermissionsAdmin}},
		})
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
		if acl.AclState().Permissions(f.spc.GetAclIdentity()) != list.AclPermissionsReader ||
			acl.AclState().Permissions(otherIdentity) != list.AclPermissionsOwner {
			return errors.New("actual original signed ACL did not establish reader/owner roles")
		}
		return nil
	}())
	f.receipt(t, "signed-acl-change.json", map[string]any{
		"actual_signed_original_records_added": 2,
		"executing_account_reader":             true, "other_actual_account_owner": true,
		"other_account_public_identity": otherIdentity.Account(),
	})
}

func (f *ownedClosedFixture) actualCreatorCollision(t *testing.T, source *ownedClosedSpecimen) {
	t.Helper()
	// This lower-layer negative witness uses the real original ID provider,
	// its signed fresh payload and the actual original creator. It is separate
	// from the closed whole-graph roundtrip and grants no import/Host authority.
	fileObjects := app.MustComponent[fileobject.Service](f.nativeApp)
	provider := objectid.NewIDProvider(f.store, f.spaces, f.blocks, fileObjects)
	cloneSource := func() *common.Snapshot {
		value := proto.Clone(source.Snapshots[source.RootID]).(*pb.SnapshotWithType)
		model, err := common.NewSnapshotModelFromProto(value)
		ownedClosedNoError(t, err)
		model.Data.Details.SetString(bundle.RelationKeyOldAnytypeID, source.RootID)
		return &common.Snapshot{Id: source.RootID, Snapshot: model}
	}
	nativeID, payload, err := provider.GetIDAndPayload(f.ctx, f.spc.Id(), cloneSource(), time.Now(), false, objectorigin.Import(model.Import_Pb))
	ownedClosedNoError(t, err)
	if nativeID == "" || nativeID == source.RootID || payload.RootRawChange == nil || payload.RootRawChange.Id != nativeID {
		t.Fatal("original provider did not return an actual fresh signed page payload")
	}
	present, err := f.spc.Storage().HasTree(f.ctx, nativeID)
	ownedClosedNoError(t, err)
	if present {
		t.Fatal("original fresh provider payload was already present before the first native create")
	}
	ids := make(map[string]string, len(source.Snapshots))
	formats := make(map[domain.RelationKey]int32)
	for id, snapshot := range source.Snapshots {
		ids[id] = id
		if coresb.SmartBlockType(snapshot.SbType) == coresb.SmartBlockTypeRelation {
			details := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
			formats[domain.RelationKey(details.GetString(bundle.RelationKeyRelationKey))] =
				int32(details.GetInt64(bundle.RelationKeyRelationFormat))
		}
	}
	ids[source.RootID] = nativeID
	data := importcreator.NewDataObject(f.ctx, ids,
		map[string]treestorage.TreeStorageCreatePayload{nativeID: payload}, formats,
		objectorigin.Import(model.Import_Pb), f.spc.Id())
	factory := syncer.New(syncer.NewFileSyncer(f.blocks, fileObjects),
		syncer.NewBookmarkSyncer(f.blocks), syncer.NewIconSyncer(f.blocks, fileObjects))
	ordinary := importcreator.New(app.MustComponent[detailservice.Service](f.nativeApp),
		factory, f.store, syncer.NewFileRelationSyncer(f.blocks, fileObjects), f.spaces,
		f.creator, f.blocks, app.MustComponent[relationutils.RelationFormatFetcher](f.nativeApp))
	creator, ok := ordinary.(*importcreator.ObjectCreator)
	if !ok {
		t.Fatal("original importer creator has an unexpected concrete native implementation")
	}
	details, firstID, err := creator.CreateOwnedAnnotationFresh(data, cloneSource())
	ownedClosedNoError(t, err)
	if details == nil || firstID != nativeID {
		t.Fatal("actual first original fresh page creation did not return its provider identity")
	}
	before := f.pageHeads(t, nativeID)
	secondDetails, secondID, collisionErr := creator.CreateOwnedAnnotationFresh(data, cloneSource())
	f.receipt(t, "actual-native-creator-collision.json", map[string]any{
		"native_provider_id": nativeID, "native_payload_root_id": payload.RootRawChange.Id,
		"actual_first_create_returned_id": firstID, "second_create_returned_id": secondID,
		"second_create_returned_details": secondDetails != nil,
		"actual_tree_exists_error":       errors.Is(collisionErr, treestorage.ErrTreeExists),
		"first_native_heads":             before, "after_second_native_heads": f.pageHeads(t, nativeID),
		"scope": "actual strict creator ErrTreeExists disposition only; not a second whole-graph import",
	})
	if !errors.Is(collisionErr, treestorage.ErrTreeExists) || secondDetails != nil || secondID != "" ||
		!slices.Equal(before, f.pageHeads(t, nativeID)) {
		t.Fatal("actual native creator collision was converted to existing-object success or mutation")
	}
}
