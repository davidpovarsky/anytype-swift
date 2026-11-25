// This file is injected through Go's read-only -overlay into the exact qualified
// Heart tree. It uses original application/native APIs; no server, transport,
// account, native executor, object store or synchronization mock is supplied.
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
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/anytype/config"
	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/gogo/protobuf/proto"
	"github.com/google/uuid"
)

type originalNetworkPointer struct {
	AccountID      string `json:"account_id"`
	SpaceID        string `json:"space_id"`
	ObjectID       string `json:"object_id"`
	AnnotationUUID string `json:"annotation_uuid"`
	BlockID        string `json:"block_id"`
	TextSHA256     string `json:"text_sha256"`
}

func TestOtzariaOriginalNetworkPeer(t *testing.T) {
	phase, root := os.Getenv("OTZARIA_ORIGINAL_NETWORK_PHASE"), os.Getenv("OTZARIA_ORIGINAL_NETWORK_ROOT")
	if (phase != "producer" && phase != "consumer") || !filepath.IsAbs(root) {
		t.Fatal("explicit owned phase and absolute development fixture root required")
	}
	info, err := os.Lstat(root)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 || info.Mode().Perm()&0077 != 0 {
		t.Fatal("private original-network fixture root must already exist with mode0700")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 18*time.Minute)
	defer cancel()
	repo, evidence := filepath.Join(root, phase+"-repository"), filepath.Join(root, "evidence", phase)
	resume := os.Getenv("OTZARIA_ORIGINAL_NETWORK_RESUME") == "1"
	if resume {
		info, err := os.Lstat(repo)
		if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
			t.Fatal("owned previous native repository missing")
		}
	} else if err := os.Mkdir(repo, 0700); err != nil {
		t.Fatal("fresh separate repository required: ", err)
	}
	if err := os.MkdirAll(evidence, 0700); err != nil {
		t.Fatal(err)
	}
	service := application.New()
	service.SetClientVersion("otzaria-original-network-acceptance", "1.0.0")
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	defer func() {
		stopErr := service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: false})
		if stopErr != nil {
			t.Errorf("real original AccountStop failed: %v", stopErr)
		}
		originalNetworkJSON(t, evidence, "stop.json", map[string]any{"returned": stopErr == nil, "application_absent": service.GetApp() == nil})
	}()
	var pointer originalNetworkPointer
	var accountID string
	if phase == "producer" && !resume {
		mnemonic, _, walletErr := service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: repo})
		if walletErr != nil {
			t.Fatal(walletErr)
		}
		credential, createErr := os.OpenFile(filepath.Join(root, "development-mnemonic.private"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if createErr != nil {
			t.Fatal(createErr)
		}
		_, writeErr := credential.WriteString(mnemonic)
		syncErr, closeErr := credential.Sync(), credential.Close()
		if writeErr != nil || syncErr != nil || closeErr != nil {
			t.Fatal("private generated credential could not be retained")
		}
		// A generated DEVELOPMENT credential is never emitted in logs/receipts.
		account, createErr := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{
			Name: "Otzaria development network acceptance", StorePath: repo,
			DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_DefaultConfig,
		})
		if createErr != nil || account == nil {
			t.Fatalf("actual default-network AccountCreate: %v", createErr)
		}
		accountID = account.Id
	} else {
		originalNetworkWaitJSON(t, ctx, root, "source-pointer.json", &pointer)
		credential, readErr := os.ReadFile(filepath.Join(root, "development-mnemonic.private"))
		if readErr != nil {
			t.Fatal("private development credential unavailable")
		}
		// Genuine WalletRecover re-derives this process's in-memory original
		// credentials; it does not overwrite the already present repository.
		if err := service.WalletRecover(&pb.RpcWalletRecoverRequest{RootPath: repo, Mnemonic: string(credential)}); err != nil {
			t.Fatal("original WalletRecover failed: ", err)
		}
		account, selectErr := service.AccountSelect(ctx, &pb.RpcAccountSelectRequest{
			Id: pointer.AccountID, RootPath: repo, PreferredSpaceId: pointer.SpaceID,
			DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_DefaultConfig,
		})
		if selectErr != nil || account == nil {
			t.Fatalf("actual independent AccountSelect: %v", selectErr)
		}
		accountID = account.Id
	}
	native := service.GetApp()
	if native == nil {
		t.Fatal("original native application missing")
	}
	actual := app.MustComponent[accountservice.Service](native).Account().SignKey.GetPublic().Account()
	cfg := app.MustComponent[*config.Config](native)
	if actual != accountID || actual == "" || cfg.NetworkMode == pb.RpcAccount_LocalOnly || !cfg.DontStartLocalNetworkSyncAutomatically {
		t.Fatal("actual original remote account/network mode or disabled LAN sync not observed")
	}
	f := &ownedClosedFixture{ctx: ctx, service: service, nativeApp: native, directory: repo, evidence: evidence,
		accountID: accountID, owner: &ownedClosedOwner{stops: map[*application.Service]*ownedClosedStop{}}}
	f.blocks = app.MustComponent[*block.Service](native)
	f.creator = app.MustComponent[objectcreator.Service](native)
	var ok bool
	f.observer, ok = f.creator.(objectcreator.FixedSchemaObserver)
	if !ok {
		t.Fatal("original fixed-schema observer missing")
	}
	f.store = app.MustComponent[objectstore.ObjectStore](native)
	f.exporter = app.MustComponent[export.Export](native)
	f.spaces = app.MustComponent[space.Service](native)
	f.typeKey, err = domain.GetTypeKeyFromRawUniqueKey(annotationschema.TypeUniqueKey)
	if err != nil {
		t.Fatal(err)
	}
	if phase == "producer" {
		if !resume {
			details := domain.NewDetails()
			details.SetString(bundle.RelationKeyName, "Otzaria original network acceptance")
			details.SetInt64(bundle.RelationKeySpaceType, int64(model.SpaceType_SpaceTypeRegular))
			id, _, createErr := f.blocks.CreateWorkspace(ctx, &pb.RpcWorkspaceCreateRequest{Details: details.ToProto(), UseCase: pb.RpcObjectImportUseCaseRequest_NONE})
			if createErr != nil {
				t.Fatal(createErr)
			}
			f.spc, err = f.spaces.Wait(ctx, id)
			if err != nil {
				t.Fatal(err)
			}
			f.registerSchema(t) // accepted helper calls the genuine original registrar
			pointer = originalNetworkPointer{AccountID: accountID, SpaceID: id, AnnotationUUID: uuid.NewString()}
			details = domain.NewDetails()
			details.SetString(bundle.RelationKeyName, "Saved rich original network note")
			for key, value := range map[string]string{
				"pinkhaTorahAnnotationProtocol":            annotationschema.Protocol,
				"pinkhaTorahAnnotationClassification":      "annotation",
				"pinkhaTorahAnnotationNamespace":           "otzaria.local.annotation",
				"pinkhaTorahAnnotationUUID":                pointer.AnnotationUUID,
				"pinkhaTorahAnnotationCreationDestination": "otzaria.local.draft:original-network-acceptance",
				"pinkhaTorahAnnotationCreationAccount":     accountID,
				"pinkhaTorahAnnotationCreationSpace":       id,
			} {
				details.SetString(domain.RelationKey(key), value)
			}
			pointer.ObjectID, _, err = f.creator.CreateObjectUsingObjectUniqueTypeKey(ctx, id, annotationschema.TypeUniqueKey, objectcreator.CreateObjectRequest{Details: details})
			if err != nil || pointer.ObjectID == "" {
				t.Fatal("actual original annotation creation failed: ", err)
			}
			pointer.BlockID, pointer.TextSHA256 = originalNetworkCreateText(t, f, pointer.ObjectID, "מקור "+uuid.NewString())
		} else {
			originalNetworkWaitSpace(t, f, pointer.SpaceID)
		}
		// Only identities and a one-way body hash cross the control channel.
		// Neither native archive, text content, repository nor index is copied.
		originalNetworkAwaitBody(t, f, pointer, "producer-saved")
		originalNetworkJSON(t, root, "source-pointer.json", pointer)
		var peerReceipt map[string]any
		originalNetworkWaitJSON(t, ctx, root, "consumer-readback.json", &peerReceipt)
		var reverse originalNetworkPointer
		originalNetworkWaitJSON(t, ctx, root, "reverse-pointer.json", &reverse)
		if reverse.AccountID != pointer.AccountID || reverse.SpaceID != pointer.SpaceID || reverse.ObjectID != pointer.ObjectID || reverse.AnnotationUUID != pointer.AnnotationUUID || reverse.BlockID == pointer.BlockID {
			t.Fatal("reverse expected identity differs from the original same-object scope")
		}
		originalNetworkAwaitBody(t, f, reverse, "producer-reverse-readback")
		originalNetworkJSON(t, root, "producer-readback.json", map[string]any{
			"status": "ACTUAL_ORIGINAL_REMOTE_BODY_READBACK", "phase": phase, "pid": os.Getpid(), "repository": repo,
			"same_account": accountID, "same_space": pointer.SpaceID, "same_object": pointer.ObjectID,
			"body_sha256": reverse.TextSHA256, "network_mode": int32(cfg.NetworkMode), "lan_sync_disabled": true,
		})
	} else {
		if accountID != pointer.AccountID {
			t.Fatal("recovered original account identity differs")
		}
		originalNetworkWaitSpace(t, f, pointer.SpaceID)
		originalNetworkAwaitBody(t, f, pointer, "consumer-remote-readback")
		originalNetworkJSON(t, root, "consumer-readback.json", map[string]any{
			"status": "ACTUAL_ORIGINAL_REMOTE_BODY_READBACK", "phase": phase, "pid": os.Getpid(), "repository": repo,
			"same_account": accountID, "same_space": pointer.SpaceID, "same_object": pointer.ObjectID,
			"body_sha256": pointer.TextSHA256, "network_mode": int32(cfg.NetworkMode), "lan_sync_disabled": true,
		})
		reverse := pointer
		reverse.BlockID, reverse.TextSHA256 = originalNetworkCreateText(t, f, pointer.ObjectID, "חזרה "+uuid.NewString())
		originalNetworkAwaitBody(t, f, reverse, "consumer-saved-reverse")
		originalNetworkJSON(t, root, "reverse-pointer.json", reverse)
		var final map[string]any
		originalNetworkWaitJSON(t, ctx, root, "producer-readback.json", &final)
	}
}

func originalNetworkCreateText(t *testing.T, f *ownedClosedFixture, root, text string) (string, string) {
	t.Helper()
	content := &model.BlockContentText{Text: text, Style: model.BlockContentText_Paragraph, Marks: &model.BlockContentTextMarks{Marks: []*model.BlockContentTextMark{{Range: &model.Range{From: 0, To: 4}, Type: model.BlockContentTextMark_Bold}}}}
	id, err := f.blocks.CreateBlock(session.NewContext(), pb.RpcBlockCreateRequest{ContextId: root, TargetId: root, Position: model.Block_Inner, Block: &model.Block{Content: &model.BlockContentOfText{Text: content}}})
	if err != nil || id == "" {
		t.Fatal("actual original text creation: ", err)
	}
	raw, err := proto.Marshal(content)
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(raw)
	return id, hex.EncodeToString(sum[:])
}

func originalNetworkAwaitBody(t *testing.T, f *ownedClosedFixture, p originalNetworkPointer, label string) {
	t.Helper()
	var last error
	for attempt := 0; ; attempt++ {
		archive, snapshot, err := originalNetworkExport(f, p.ObjectID)
		if err == nil {
			details := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
			if details.GetString(domain.RelationKey("pinkhaTorahAnnotationUUID")) != p.AnnotationUUID || details.GetString(domain.RelationKey("pinkhaTorahAnnotationClassification")) != "annotation" {
				t.Fatal("actual remote native Annotation identity/classification differs")
			}
			for _, b := range snapshot.Snapshot.Data.Blocks {
				if b.Id != p.BlockID || b.GetText() == nil {
					continue
				}
				raw, marshalErr := proto.Marshal(b.GetText())
				if marshalErr != nil {
					t.Fatal(marshalErr)
				}
				sum := sha256.Sum256(raw)
				if hex.EncodeToString(sum[:]) == p.TextSHA256 {
					if err := os.WriteFile(filepath.Join(f.evidence, label+".zip"), archive, 0600); err != nil {
						t.Fatal(err)
					}
					hash := sha256.Sum256(archive)
					originalNetworkJSON(t, f.evidence, label+".json", map[string]any{"status": "ACTUAL_ORIGINAL_EXPORT_BODY_MATCHED", "export_archive_sha256": hex.EncodeToString(hash[:]), "block_sha256": p.TextSHA256, "read_attempts": attempt + 1, "native_object_id": p.ObjectID})
					return
				}
			}
			last = errors.New("original export has not yet observed the expected remote body")
		} else {
			last = err
		}
		select {
		case <-f.ctx.Done():
			t.Fatalf("real original peer body not observed: %v; %v", last, f.ctx.Err())
		case <-time.After(2 * time.Second):
		}
	}
}

func originalNetworkExport(f *ownedClosedFixture, objectID string) ([]byte, *pb.SnapshotWithType, error) {
	directory, err := os.MkdirTemp(f.directory, "network-read-")
	if err != nil {
		return nil, nil, err
	}
	defer os.RemoveAll(directory)
	path, report, err := f.exporter.Export(f.ctx, pb.RpcObjectListExportRequest{SpaceId: f.spc.Id(), ObjectIds: []string{objectID}, Path: directory, Format: model.Export_Protobuf, Zip: true, IncludeFiles: false, IncludeNested: true, IncludeArchived: true, NoProgress: true})
	if err != nil {
		return nil, nil, err
	}
	if report == nil || report.Status != model.ExportReport_SUCCESS || report.Succeed < 1 || report.ObjectErrors != 0 || report.FileErrors != 0 {
		return nil, nil, errors.New("original export report incomplete")
	}
	for _, issue := range report.Issues {
		if issue == nil || issue.Severity == model.ExportReportIssue_ERROR {
			return nil, nil, errors.New("original export issue")
		}
	}
	rel, err := filepath.Rel(directory, path)
	if err != nil || rel == "." || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) || filepath.IsAbs(rel) {
		return nil, nil, errors.New("original export path invalid")
	}
	info, err := os.Lstat(path)
	if err != nil || !info.Mode().IsRegular() || info.Size() > 8<<20 {
		return nil, nil, errors.New("original export size/type invalid")
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, nil, err
	}
	archive, err := zip.NewReader(bytes.NewReader(raw), int64(len(raw)))
	if err != nil {
		return nil, nil, err
	}
	for _, member := range archive.File {
		if member.Name != "objects/"+objectID+".pb" {
			continue
		}
		reader, err := member.Open()
		if err != nil {
			return nil, nil, err
		}
		body, err := io.ReadAll(io.LimitReader(reader, (8<<20)+1))
		closeErr := reader.Close()
		if err != nil || closeErr != nil || len(body) > 8<<20 {
			return nil, nil, errors.New("original root export member invalid")
		}
		var snapshot pb.SnapshotWithType
		if err := proto.Unmarshal(body, &snapshot); err != nil {
			return nil, nil, err
		}
		if snapshot.Snapshot == nil || snapshot.Snapshot.Data == nil || snapshot.Snapshot.Data.Details == nil {
			return nil, nil, errors.New("original root snapshot missing")
		}
		return raw, &snapshot, nil
	}
	return nil, nil, fmt.Errorf("actual root member not yet available")
}

func originalNetworkJSON(t *testing.T, root, name string, value any) {
	t.Helper()
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	temp, err := os.CreateTemp(root, ".receipt-")
	if err != nil {
		t.Fatal(err)
	}
	if err := temp.Chmod(0600); err != nil {
		t.Fatal(err)
	}
	if _, err := temp.Write(append(raw, '\n')); err != nil {
		t.Fatal(err)
	}
	if err := temp.Sync(); err != nil {
		t.Fatal(err)
	}
	if err := temp.Close(); err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(temp.Name(), filepath.Join(root, name)); err != nil {
		t.Fatal(err)
	}
}
func originalNetworkWaitJSON(t *testing.T, ctx context.Context, root, name string, value any) {
	t.Helper()
	for {
		raw, err := os.ReadFile(filepath.Join(root, name))
		if err == nil {
			if json.Unmarshal(raw, value) != nil {
				t.Fatal("invalid owned control receipt")
			}
			return
		}
		if !os.IsNotExist(err) {
			t.Fatal(err)
		}
		select {
		case <-ctx.Done():
			t.Fatal("original peer control receipt not observed: ", name)
		case <-time.After(500 * time.Millisecond):
		}
	}
}

// A newly created real remote Space can arrive after account recovery. Waiting
// for the actual service is not a fabricated ACK and never supplies a Space.
func originalNetworkWaitSpace(t *testing.T, f *ownedClosedFixture, id string) {
	t.Helper()
	for {
		observed, err := f.spaces.Wait(f.ctx, id)
		if err == nil && observed != nil && observed.Id() == id {
			f.spc = observed
			return
		}
		select {
		case <-f.ctx.Done():
			t.Fatalf("actual original remote Space not observed: %v", err)
		case <-time.After(2 * time.Second):
		}
	}
}
