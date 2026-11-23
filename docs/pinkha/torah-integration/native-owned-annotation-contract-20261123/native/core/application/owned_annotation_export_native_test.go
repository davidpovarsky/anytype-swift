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
	"slices"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/proto"
	"github.com/google/uuid"

	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema"
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

// Real LocalOnly app/wallet/Space, original registrar and native object,
// block/file/export APIs produce these specimens. No hand-built archive,
// replacement app, import activation, cold reopen or Host ACK is involved.
func TestOtzariaOwnedAnnotationNativeExports(t *testing.T) {
	f := newOwnedExportFixture(t)
	for _, kind := range []string{"text", "format", "nested", "attachment"} {
		t.Run(kind, func(t *testing.T) {
			root := f.annotation(t, "Native archive "+kind)
			s := &ownedExportSpecimen{Kind: kind, RootID: root, Expected: make(map[string]*model.Block)}
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
				parent := f.text(t, s, root, "", "Parent native toggle", model.BlockContentText_Toggle, nil)
				child := f.text(t, s, root, parent, "Nested native text", model.BlockContentText_Paragraph, nil)
				s.ParentID, s.ChildID = parent, child
				linked := f.annotation(t, "Native linked annotation")
				f.text(t, s, linked, "", "Linked native object body", model.BlockContentText_Paragraph, nil)
				s.LinkedID = linked
				f.expectedBlock(t, s, root, "", &model.Block{Content: &model.BlockContentOfLink{
					Link: &model.BlockContentLink{TargetBlockId: linked},
				}})
			case "attachment":
				content := []byte("Native disposable attachment\nשורה מקורית\n")
				input := filepath.Join(f.directory, "native-attachment.txt")
				ownedExportNoError(t, os.WriteFile(input, content, 0600))
				id, fileType, _, err := f.blocks.UploadFile(f.ctx, f.spc.Id(), block.FileUploadRequest{
					RpcFileUploadRequest: pb.RpcFileUploadRequest{SpaceId: f.spc.Id(), LocalPath: input,
						Type: model.BlockContentFile_File, Style: model.BlockContentFile_Link, CreatedInContext: root},
					ObjectOrigin: objectorigin.None(), Name: "native-attachment.txt",
				})
				ownedExportNoError(t, err)
				if id == "" {
					t.Fatal("original upload returned no actual file object")
				}
				f.expectedBlock(t, s, root, "", &model.Block{Content: &model.BlockContentOfFile{
					File: &model.BlockContentFile{TargetObjectId: id, Type: fileType, State: model.BlockContentFile_Done,
						Style: model.BlockContentFile_Link, Name: "native-attachment.txt", Size_: int64(len(content))},
				}})
				s.AttachmentID, s.AttachmentBytes = id, content
			}
			f.export(t, s)
		})
	}
}

type ownedExportSpecimen struct {
	Kind            string
	RootID          string
	Expected        map[string]*model.Block
	ParentID        string
	ChildID         string
	LinkedID        string
	AttachmentID    string
	AttachmentBytes []byte
}
type ownedExportFixture struct {
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

func newOwnedExportFixture(t *testing.T) *ownedExportFixture {
	t.Helper()
	evidence := os.Getenv("OTZARIA_NATIVE_EXPORT_FIXTURES")
	if evidence == "" || !filepath.IsAbs(evidence) {
		t.Fatal("explicit owned native export evidence directory required")
	}
	info, err := os.Lstat(evidence)
	ownedExportNoError(t, err)
	if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		t.Fatal("evidence directory must already be owned and real")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Minute)
	service := application.New()
	service.SetClientVersion("otzaria-owned-native-export", "1.0.0")
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	directory, err := os.MkdirTemp("", "otzaria-owned-native-export-")
	ownedExportNoError(t, err)
	f := &ownedExportFixture{ctx: ctx, service: service, directory: directory, evidence: evidence}
	// Install before any setup can activate the app and fail. An unfinished
	// original stop preserves data; it is never converted into claimed drain.
	t.Cleanup(func() {
		defer cancel()
		stopped := service.GetApp() == nil
		if !stopped {
			done := make(chan error, 1)
			go func() { done <- service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true}) }()
			select {
			case stopErr := <-done:
				if stopErr != nil {
					t.Errorf("preserve native export data: AccountStop failed: %v", stopErr)
				} else {
					stopped = true
				}
			case <-time.After(30 * time.Second):
				t.Error("preserve native export data: original AccountStop did not drain within the cleanup bound")
			}
		}
		removed := false
		if stopped {
			if err := os.RemoveAll(directory); err != nil {
				t.Errorf("remove owned native data: %v", err)
			} else {
				removed = true
			}
		}
		raw, err := json.MarshalIndent(map[string]any{
			"original_account_stop_returned_or_app_absent": stopped, "owned_directory_removed": removed,
			"import_started": false, "cold_reopen_qualified": false, "body_ack_authority": false,
		}, "", "  ")
		if err != nil {
			t.Error(err)
			return
		}
		if err := ownedExportWrite(evidence, "native-export-cleanup.json", append(raw, '\n')); err != nil {
			t.Error(err)
		}
	})
	_, _, err = service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: directory})
	ownedExportNoError(t, err)
	// No mnemonic or private account material is logged or retained.
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	account, err := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{
		Name: "Disposable original native export", StorePath: directory,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly,
	})
	ownedExportNoError(t, err)
	if account == nil || service.GetApp() == nil {
		t.Fatal("actual original account/application missing")
	}
	native := service.GetApp()
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
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, "Disposable original export Space")
	details.SetInt64(bundle.RelationKeySpaceType, int64(model.SpaceType_SpaceTypeRegular))
	id, _, err := f.blocks.CreateWorkspace(ctx, &pb.RpcWorkspaceCreateRequest{Details: details.ToProto(),
		UseCase: pb.RpcObjectImportUseCaseRequest_NONE})
	ownedExportNoError(t, err)
	f.spc, err = spaces.Wait(ctx, id)
	ownedExportNoError(t, err)
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
	ownedExportNoError(t, err)
	return f
}

// The genuine endpoint qualification already exercises this original registrar
// as a bounded sequence of retained histories. A single call may safely return
// unresolved after some unique native creates; it does not roll those back.
func (f *ownedExportFixture) registerSchema(t *testing.T) {
	t.Helper()
	definitions, err := annotationschema.Definitions()
	ownedExportNoError(t, err)
	if len(definitions) != 18 {
		t.Fatal("original annotation schema definition count changed")
	}
	seen := map[string]bool{}
	applies := 0
	phases := 0
	var ready *annotationschema.Registration
	for ; phases < 21; phases++ {
		value, registerErr := annotationschema.Register(f.ctx, f.service, f.accountID, f.spc.Id())
		category := ownedExportRegistrationCategory(registerErr)
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
			ownedExportNoError(t, registerErr)
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
		"fixture_setup_only": true, "native_import_activated": false, "body_ack_authority": false,
	}, "", "  ")
	ownedExportNoError(t, err)
	ownedExportNoError(t, ownedExportWrite(f.evidence, "schema-registration.json", append(payload, '\n')))
}

// This preserves the precedence of the actual endpoint's resumable category.
// Cancellation and registration conflict never become an unresolved continuation.
func ownedExportRegistrationCategory(err error) string {
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
func (f *ownedExportFixture) recordSchemaPhase(t *testing.T, phase int, value annotationschema.Registration, err error, category string) {
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
	ownedExportNoError(t, marshalErr)
	if phase < 0 || phase >= 21 || len(creations) > 18 || len(definitions) > 18 || len(raw)+1 > 128<<10 {
		t.Fatal("actual original registration history exceeds its fixed fixture evidence bound")
	}
	payload := append(raw, '\n')
	name := fmt.Sprintf("schema-registration-%02d.json", phase)
	ownedExportNoError(t, ownedExportWrite(f.evidence, name, payload))
	sum := sha256.Sum256(payload)
	t.Logf("actual original registration phase %d: %s sha256=%x", phase, name, sum)
}

func (f *ownedExportFixture) waitSchemaReadiness(t *testing.T, spc clientspace.Space, definitions []objectcreator.FixedSchemaDefinition, known map[string]bool) {
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
			ownedExportNoError(t, err)
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
			ownedExportNoError(t, err)
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

func (f *ownedExportFixture) annotation(t *testing.T, name string) string {
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
	ownedExportNoError(t, err)
	if id == "" || created == nil {
		t.Fatal("original annotation creation did not return a native object")
	}
	return id
}

func (f *ownedExportFixture) expectedBlock(t *testing.T, s *ownedExportSpecimen, root, parent string, b *model.Block) string {
	t.Helper()
	expected := proto.Clone(b).(*model.Block)
	if parent == "" {
		parent = root
	}
	id, err := f.blocks.CreateBlock(session.NewContext(), pb.RpcBlockCreateRequest{
		ContextId: root, TargetId: parent, Position: model.Block_Inner, Block: b,
	})
	ownedExportNoError(t, err)
	if id == "" {
		t.Fatal("original block creation did not return a native block")
	}
	expected.Id = id
	s.Expected[id] = expected
	return id
}
func (f *ownedExportFixture) text(t *testing.T, s *ownedExportSpecimen, root, parent, text string, style model.BlockContentTextStyle, marks *model.BlockContentTextMarks) string {
	t.Helper()
	return f.expectedBlock(t, s, root, parent, &model.Block{Content: &model.BlockContentOfText{
		Text: &model.BlockContentText{Text: text, Style: style, Marks: marks},
	}})
}

func (f *ownedExportFixture) export(t *testing.T, s *ownedExportSpecimen) {
	t.Helper()
	exportDir := filepath.Join(f.directory, "export-"+s.Kind)
	ownedExportNoError(t, os.Mkdir(exportDir, 0700))
	path, report, exportErr := f.exporter.Export(f.ctx, pb.RpcObjectListExportRequest{
		SpaceId: f.spc.Id(), ObjectIds: []string{s.RootID}, Path: exportDir, Format: model.Export_Protobuf,
		Zip: true, IsJson: false, IncludeFiles: true, IncludeNested: true, IncludeArchived: true,
		IncludeBacklinks: false, IncludeSpace: false, NoProgress: true,
	})
	reportBytes, err := json.MarshalIndent(report, "", "  ")
	ownedExportNoError(t, err)
	ownedExportNoError(t, ownedExportWrite(f.evidence, s.Kind+"-export-report.json", append(reportBytes, '\n')))
	// Retain an actual bounded partial/oversized output before asserting
	// success; neither retention nor the archive's existence is acceptance.
	var raw []byte
	if path != "" {
		relative, err := filepath.Rel(exportDir, path)
		ownedExportNoError(t, err)
		if relative == "." || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) || filepath.IsAbs(relative) {
			t.Fatal("original export path escaped its owned export directory")
		}
		info, err := os.Lstat(path)
		ownedExportNoError(t, err)
		if !info.Mode().IsRegular() || info.Size() > 8<<20 {
			t.Fatal("native export evidence retention bound exceeded")
		}
		raw, err = os.ReadFile(path)
		ownedExportNoError(t, err)
		ownedExportNoError(t, ownedExportWrite(f.evidence, s.Kind+".zip", raw))
	}
	ownedExportNoError(t, exportErr)
	ownedExportNoError(t, f.ctx.Err())
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
	ownedExportNoError(t, err)
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
		ownedExportNoError(t, err)
		body, readErr := io.ReadAll(io.LimitReader(stream, int64((8<<20)-expanded)+1))
		closeErr := stream.Close()
		ownedExportNoError(t, readErr)
		ownedExportNoError(t, closeErr)
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
			ownedExportNoError(t, snapshot.Unmarshal(body))
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
	ownedExportNoError(t, err)
	payload := append(encoded, '\n')
	ownedExportNoError(t, ownedExportWrite(f.evidence, s.Kind+"-manifest.json", payload))
	rh := sha256.Sum256(payload)
	t.Logf("actual original native specimen=%s members=%d archive_sha256=%s receipt_sha256=%s",
		s.Kind, len(zr.File), hex.EncodeToString(hash[:]), hex.EncodeToString(rh[:]))
}

func ownedExportWrite(directory, name string, payload []byte) error {
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
func ownedExportNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(fmt.Errorf("actual original native export operation: %w", err))
	}
}
