//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance

package application

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"testing"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/gogo/protobuf/proto"
	"github.com/ipfs/go-cid"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/cache"
	sb "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/files"
	"github.com/anyproto/anytype-heart/core/files/filehelper"
	"github.com/anyproto/anytype-heart/core/files/fileobject"
	"github.com/anyproto/anytype-heart/core/files/fileobject/filemodels"
	"github.com/anyproto/anytype-heart/core/files/filestorage"
	"github.com/anyproto/anytype-heart/pkg/lib/anyblockjson/storeresolver"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/storage"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
)

func loadedSpaceFixtureFile(t *testing.T, f *loadedAccountFixture, payload []byte) (string, string) {
	t.Helper()
	fs := app.MustComponent[files.Service](f.service.GetApp())
	added, err := fs.FileAdd(f.ctx, f.space.Id(), files.WithReader(bytes.NewReader(payload)), files.WithName("source-full.bin"))
	if err != nil {
		t.Fatal("real native FileAdd:", err)
	}
	added.Commit()
	objectService := app.MustComponent[fileobject.Service](f.service.GetApp())
	objectID, _, err := objectService.Create(f.ctx, f.space.Id(), filemodels.CreateRequest{
		FileId: added.FileId, EncryptionKeys: added.EncryptionKeys.EncryptionKeys,
		FileVariants: added.Variants, AsyncMetadataIndexing: false,
	})
	if err != nil || objectID == "" {
		t.Fatal("real native file object:", err)
	}
	return objectID, added.FileId.String()
}

// Warm native objects as fixture preparation. This is outside the source API
// and does not retry or relax its final unchanged-checkpoint comparison.
func loadedSpaceFixtureWarm(t *testing.T, f *loadedAccountFixture) {
	t.Helper()
	inventory := loadedObjectFixtureInventory(t, f)
	picker, ok := f.service.GetApp().Component(block.CName).(*block.Service)
	if !ok {
		t.Fatal("real picker missing")
	}
	for _, id := range inventory.TreeIDs() {
		identity, err := inventory.Tree(id)
		if err != nil {
			t.Fatal(err)
		}
		if identity.DeletedStatus() != 0 || id == inventory.SettingsTreeID() {
			continue
		}
		kind, _, err := typeprovider.GetTypeAndKeyFromRoot(&treechangeproto.RawTreeChangeWithId{Id: id, RawChange: identity.RootRawChange()})
		if err != nil || kind.Valid() != nil || kind.DetailsStoreOwned() {
			continue
		}
		if err := cache.DoContextFullID(picker, f.ctx, domain.FullID{SpaceID: f.space.Id(), ObjectID: id}, func(sb.SmartBlock) error { return nil }); err != nil {
			t.Fatal("real fixture object preparation:", err)
		}
	}
}

func loadedSpaceRequest(f *loadedAccountFixture) LoadedAccountSpaceWitnessRequest {
	return LoadedAccountSpaceWitnessRequest{Source: f.request(), PrivateDirectory: f.dir, MaxFileBytes: 1 << 20,
		FileLimits: files.NativeFileCaptureLimits{MaxVariantBytes: 1 << 20, MaxTotalBytes: 1 << 20, MaxDAGNodes: 1000, MaxDAGBytes: 4 << 20}}
}

func TestLoadedAccountWholeSourceBindsLocalPayloadAndMetadata(t *testing.T) {
	f := newLoadedAccountFixture(t)
	const text = "מקור מלא ושמור — טקסט עם הפניה"
	pageID := loadedObjectFixturePage(t, f, text, false)
	payload := bytes.Repeat([]byte("native-source-plain-0123456789\x00\xff"), 600)
	fileObjectID, fileID := loadedSpaceFixtureFile(t, f, payload)
	loadedSpaceFixtureKeyValue(t, f)
	loadedSpaceFixtureWarm(t, f)
	captured, err := f.service.CaptureLoadedAccountSpaceWitness(f.ctx, f.token, loadedSpaceRequest(f))
	if err != nil {
		t.Fatal("actual whole source capture:", err)
	}
	receipt, err := captured.Receipt()
	if err != nil {
		t.Fatal(err)
	}
	if !receipt.AccountSessionAuthorizedAtFinalCapture || !receipt.AllNativeHeadRowsAccounted ||
		!receipt.CapturedSnapshotsBoundToUnchangedCheckpoint || !receipt.IndexResolverSnapshotBound ||
		!receipt.OriginalNativeHistoryRowsRetained || receipt.NativeTrees < 3 ||
		receipt.HistorySemanticsValidated || receipt.SemanticCompleteness || receipt.HasNativeSourceAdmission || receipt.PermitsDestinationWrites {
		t.Fatal("source authority or bounded completeness flags differ")
	}
	foundPage, foundFile := false, false
	for _, object := range captured.Objects() {
		if object.ObjectID() == pageID {
			foundPage = bytes.Contains(object.SnapshotBase(), []byte(text))
			copy := object.SnapshotBase()
			copy[0] ^= 1
			if bytes.Equal(copy, object.SnapshotBase()) {
				t.Fatal("raw snapshot alias escaped")
			}
		}
		if object.ObjectID() == fileObjectID {
			foundFile = true
		}
	}
	if !foundPage || !foundFile {
		t.Fatal("actual page or file raw snapshot missing")
	}
	capture := captured.File(fileID)
	if capture == nil || len(capture.Variants()) != 1 {
		t.Fatal("actual native file payload not captured")
	}
	variant := capture.Variants()[0]
	if !variant.Original() || variant.Size() != int64(len(payload)) || variant.ContentSHA256() != loadedFixtureHash(payload) {
		t.Fatal("whole-byte payload identity differs")
	}
	reader, err := variant.Open()
	if err != nil {
		t.Fatal(err)
	}
	actual, readErr := io.ReadAll(reader)
	closeErr := reader.Close()
	if errors.Join(readErr, closeErr) != nil || !bytes.Equal(actual, payload) {
		t.Fatal("captured plaintext differs")
	}
	meta := new(storage.FileInfo)
	if err := proto.Unmarshal(variant.Metadata(), meta); err != nil {
		t.Fatal(err)
	}
	if meta.Hash != variant.ContentID() || meta.Name != variant.Name() || meta.Media != variant.MIME() || meta.Size_ != variant.Size() {
		t.Fatal("full original variant metadata differs")
	}
	metadataCopy := variant.Metadata()
	metadataCopy[0] ^= 1
	if bytes.Equal(metadataCopy, variant.Metadata()) {
		t.Fatal("metadata alias escaped")
	}
	linked := false
	for _, ref := range captured.FileReferences() {
		if ref.OwnerObjectID == fileObjectID && ref.TargetObjectID == fileObjectID && ref.FileID == fileID && ref.Field == "fileInfo.fileId" {
			linked = true
		}
	}
	if !linked {
		t.Fatal("native file owner/reference join missing")
	}
	raw, err := os.ReadFile(filepath.Join(captured.PrivateBundleDirectory(), "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest NativeSourceBundleManifest
	if err := json.Unmarshal(raw, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Contract != "pinkha-native-whole-source-bundle-v1" || len(manifest.Files) != 1 || len(manifest.Objects) != receipt.CapturedObjects {
		t.Fatal("private canonical bundle incomplete")
	}
	members := []NativeSourceMember{manifest.SourceRows}
	for _, object := range manifest.Objects {
		members = append(members, object.Snapshot)
	}
	for _, file := range manifest.Files {
		for _, variant := range file.Variants {
			members = append(members, variant.Payload, variant.Metadata)
		}
	}
	for _, member := range members {
		path := filepath.Join(captured.PrivateBundleDirectory(), filepath.FromSlash(member.Path))
		data, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		if int64(len(data)) != member.Bytes || loadedFixtureHash(data) != member.SHA256 {
			t.Fatal("original bundle member hash differs")
		}
	}
	f.privateNote(t, "whole-source-local-payload", map[string]any{
		"receipt": receipt, "payloadSHA256": loadedFixtureHash(payload), "payloadBytes": len(payload),
		"manifestSHA256": loadedFixtureHash(raw), "manifestBytes": len(raw), "membersVerified": len(members),
	})
	t.Run("missing-local-leaf-refused", func(t *testing.T) {
		local, err := filestorage.NativeSnapshotLocalDAG(f.service.GetApp().Component(filestorage.CName))
		if err != nil {
			t.Fatal(err)
		}
		contentID, err := cid.Parse(variant.ContentID())
		if err != nil {
			t.Fatal(err)
		}
		// Delete one actual content node in this disposable native fixture only.
		if err := filehelper.NewDAGServiceWithSpaceID(f.space.Id(), local).Remove(f.ctx, contentID); err != nil {
			t.Fatal(err)
		}
		missing, err := f.service.CaptureLoadedAccountSpaceWitness(f.ctx, f.token, loadedSpaceRequest(f))
		if err != nil {
			t.Fatal(err)
		}
		missingReceipt, err := missing.Receipt()
		if err != nil {
			t.Fatal(err)
		}
		gap := false
		for _, entry := range missing.Gaps() {
			if entry.Target == fileID && entry.Reason == "native-local-payload-capture-refused" {
				gap = true
			}
		}
		if missing.File(fileID) != nil || !gap || missingReceipt.CurrentFilePayloadCompleteness {
			t.Fatal("missing native leaf was admitted")
		}
		f.privateNote(t, "whole-source-missing-leaf", map[string]any{"receipt": missingReceipt, "explicitFileGap": gap})
	})
	loadedSpaceFixtureRefuseKeyValueHeads(t, f)
	t.Logf("WHOLE_SOURCE_NATIVE_OBSERVATION payload_sha256=%s payload_bytes=%d members_verified=%d", loadedFixtureHash(payload), len(payload), len(members))
}

// This context forwards the real deadline/error. It observes the new file
// capture's callsite and performs a real native edit after raw snapshots were
// captured, before the final checkpoint. It never supplies successful results.
type loadedSpaceMutationContext struct {
	context.Context
	once   sync.Once
	mutate func()
}

func (c *loadedSpaceMutationContext) observe() {
	if c.Context.Err() != nil {
		return
	}
	var pcs [40]uintptr
	n := runtime.Callers(2, pcs[:])
	frames := runtime.CallersFrames(pcs[:n])
	insideFile, insideWhole := false, false
	for {
		frame, more := frames.Next()
		if frame.Function == "github.com/anyproto/anytype-heart/core/files.CaptureNativeLocalFile" {
			insideFile = true
		}
		if frame.Function == "github.com/anyproto/anytype-heart/core/application.(*Service).CaptureLoadedAccountSpaceWitness" {
			insideWhole = true
		}
		if !more {
			break
		}
	}
	if insideFile && insideWhole {
		c.once.Do(c.mutate)
	}
}

func (c *loadedSpaceMutationContext) Err() error {
	c.observe()
	return c.Context.Err()
}
func (c *loadedSpaceMutationContext) Done() <-chan struct{} {
	c.observe()
	return c.Context.Done()
}

func TestLoadedAccountWholeSourceRefusesChangedCheckpointAndAuthority(t *testing.T) {
	f := newLoadedAccountFixture(t)
	pageID := loadedObjectFixturePage(t, f, "לפני שינוי ממשי", false)
	_, _ = loadedSpaceFixtureFile(t, f, bytes.Repeat([]byte("checkpoint-file"), 1200))
	loadedSpaceFixtureWarm(t, f)
	request := loadedSpaceRequest(f)
	t.Run("invalid-session", func(t *testing.T) {
		captured, err := f.service.CaptureLoadedAccountSpaceWitness(f.ctx, "nonexistent-native-session", request)
		if captured != nil || !errors.Is(err, ErrLoadedAccountWitnessSession) {
			t.Fatal("invalid full-session admitted", err)
		}
	})
	t.Run("object-bound", func(t *testing.T) {
		limited := request
		limited.MaxObjects = 1
		captured, err := f.service.CaptureLoadedAccountSpaceWitness(f.ctx, f.token, limited)
		if captured != nil || !errors.Is(err, ErrLoadedAccountSpaceWitness) {
			t.Fatal("partial head enumeration admitted", err)
		}
	})
	t.Run("unsafe-output-directory", func(t *testing.T) {
		link := filepath.Join(f.dir, "not-canonical")
		if err := os.Symlink(f.dir, link); err != nil {
			t.Fatal(err)
		}
		unsafe := request
		unsafe.PrivateDirectory = link
		captured, err := f.service.CaptureLoadedAccountSpaceWitness(f.ctx, f.token, unsafe)
		if captured != nil || !errors.Is(err, ErrLoadedAccountSpaceWitness) {
			t.Fatal("symlink output directory admitted", err)
		}
	})
	edited := false
	observed := &loadedSpaceMutationContext{Context: f.ctx, mutate: func() {
		loadedObjectFixtureEdit(t, f, pageID, "שינוי אמיתי בזמן צילום")
		edited = true
	}}
	captured, err := f.service.CaptureLoadedAccountSpaceWitness(observed, f.token, request)
	if !edited || captured != nil || !errors.Is(err, ErrLoadedAccountSpaceWitness) {
		t.Fatal("real changed native checkpoint was admitted", err)
	}
	f.privateNote(t, "whole-source-checkpoint-refusal", map[string]any{"actualNativeEdit": edited, "refusedChangedCheckpoint": true, "invalidSessionRefused": true, "objectBoundRefused": true, "symlinkOutputRefused": true})
}

func loadedCapturedRow(id string, kind model.SmartBlockType, values map[domain.RelationKey]domain.Value) storeresolver.CapturedRow {
	details := domain.NewDetails()
	for key, value := range values {
		details.Set(key, value)
	}
	return storeresolver.CapturedRow{ID: id, Type: kind, Snapshot: &model.SmartBlockSnapshotBase{Details: details.ToProto()}}
}

func TestLoadedAccountCapturedResolverAccountsForMissingSchemas(t *testing.T) {
	t.Run("detached-row-and-no-live-fallback", func(t *testing.T) {
		row := loadedCapturedRow("captured-object", model.SmartBlockType_Page, map[domain.RelationKey]domain.Value{bundle.RelationKeyName: domain.String("שם מקורי")})
		resolver, err := storeresolver.NewCaptured("captured-space", []storeresolver.CapturedRow{row})
		if err != nil {
			t.Fatal(err)
		}
		row.Snapshot.Details.Fields[string(bundle.RelationKeyName)] = domain.String("mutated input").ToProto()
		opts, err := resolver.OptionsForObject(row.ID)
		if err != nil {
			t.Fatal(err)
		}
		name, ok := opts.ResolveObjectNames.ObjectName(row.ID)
		if !ok || name != "שם מקורי" {
			t.Fatal("input mutation changed captured resolver")
		}
		if _, ok := opts.ResolveObjectNames.ObjectName("missing-object"); ok {
			t.Fatal("missing object resolved")
		}
		if len(resolver.Unmapped()) == 0 {
			t.Fatal("missing object disappeared from accounting")
		}
	})
	t.Run("missing-target-type-is-explicit", func(t *testing.T) {
		property := loadedCapturedRow("native-property", model.SmartBlockType_STRelation, map[domain.RelationKey]domain.Value{
			bundle.RelationKeyName: domain.String("custom relation"), bundle.RelationKeyRelationKey: domain.String("custom-property-key"),
			bundle.RelationKeyRelationFormat:            domain.Int64(int64(model.RelationFormat_object)),
			bundle.RelationKeyRelationFormatObjectTypes: domain.StringList([]string{"native-type-that-is-missing"}),
		})
		resolver, err := storeresolver.NewCaptured("captured-space", []storeresolver.CapturedRow{property})
		if err != nil {
			t.Fatal(err)
		}
		found := false
		for _, gap := range resolver.Unmapped() {
			if gap.SourceID == property.ID && gap.Target == "native-type-that-is-missing" && gap.Reason == "unmapped-target-type" {
				found = true
			}
		}
		if !found {
			t.Fatal("target type was silently dropped")
		}
	})
	t.Run("colliding-keys-refuse-ambiguous-format", func(t *testing.T) {
		a := loadedCapturedRow("property-a", model.SmartBlockType_STRelation, map[domain.RelationKey]domain.Value{
			bundle.RelationKeyRelationKey: domain.String("same-key"), bundle.RelationKeyRelationFormat: domain.Int64(int64(model.RelationFormat_file)),
		})
		b := loadedCapturedRow("property-b", model.SmartBlockType_STRelation, map[domain.RelationKey]domain.Value{
			bundle.RelationKeyRelationKey: domain.String("same-key"), bundle.RelationKeyRelationFormat: domain.Int64(int64(model.RelationFormat_shorttext)),
		})
		resolver, err := storeresolver.NewCaptured("captured-space", []storeresolver.CapturedRow{a, b})
		if err != nil {
			t.Fatal(err)
		}
		opts, err := resolver.OptionsForObject(a.ID)
		if err != nil {
			t.Fatal(err)
		}
		if _, ok := opts.ResolveFormat(domain.RelationKey("same-key")); ok {
			t.Fatal("colliding schema picked an arbitrary definition")
		}
		collisions := 0
		for _, gap := range resolver.Unmapped() {
			if gap.Reason == "colliding-property-key" {
				collisions++
			}
		}
		if collisions != 2 {
			t.Fatal("colliding native identities not retained")
		}
	})
	t.Run("mismatched-native-row-refused", func(t *testing.T) {
		row := loadedCapturedRow("native-owner", model.SmartBlockType_Page, map[domain.RelationKey]domain.Value{bundle.RelationKeySpaceId: domain.String("other-space")})
		if resolver, err := storeresolver.NewCaptured("captured-space", []storeresolver.CapturedRow{row}); resolver != nil || !errors.Is(err, storeresolver.ErrCapturedResolver) {
			t.Fatal("cross-space row admitted")
		}
	})
	t.Log("WHOLE_SOURCE_CAPTURED_RESOLVER_OBSERVATION detached_rows=PASS missing_target=PASS collision=PASS cross_space_refusal=PASS")
}
