package importer

import (
	"context"
	"crypto/sha256"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	"github.com/anyproto/anytype-heart/core/converter/pbc"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	"github.com/anyproto/anytype-heart/core/files/fileobject/fileblocks"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/proto"
)

// OwnedAnnotationReadbackObservation is a historical local original-export and
// mapping-aware annotation-body comparison. It is not a cold reopen, remote
// backup drain, current Host/Swift permission, persisted mapping or delivery ACK.
// Only finishReadback can create a populated value after real native execution.
type OwnedAnnotationReadbackStage uint8

const (
	OwnedAnnotationReadbackUnobserved OwnedAnnotationReadbackStage = iota
	OwnedAnnotationExportReturned
	OwnedAnnotationArchiveValidated
	OwnedAnnotationBodyMatched
)

type OwnedAnnotationReadbackObservation struct {
	stage                                                                               OwnedAnnotationReadbackStage
	accountID, spaceID, rootID                                                          string
	sourceDigest, archiveDigest                                                         [32]byte
	archive                                                                             []byte
	report                                                                              *model.ExportReport
	sourceSnapshots, annotationPages, fileObjects, readOnlyContexts, additionalContexts int
}

func (o OwnedAnnotationReadbackObservation) Stage() OwnedAnnotationReadbackStage { return o.stage }
func (o OwnedAnnotationReadbackObservation) AccountID() string                   { return o.accountID }
func (o OwnedAnnotationReadbackObservation) SpaceID() string                     { return o.spaceID }
func (o OwnedAnnotationReadbackObservation) RootID() string                      { return o.rootID }
func (o OwnedAnnotationReadbackObservation) SourceArchiveSHA256() [32]byte       { return o.sourceDigest }
func (o OwnedAnnotationReadbackObservation) NativeArchiveSHA256() [32]byte       { return o.archiveDigest }
func (o OwnedAnnotationReadbackObservation) CopyNativeArchive() []byte {
	return append([]byte(nil), o.archive...)
}
func (o OwnedAnnotationReadbackObservation) SourceSnapshots() int  { return o.sourceSnapshots }
func (o OwnedAnnotationReadbackObservation) AnnotationPages() int  { return o.annotationPages }
func (o OwnedAnnotationReadbackObservation) FileObjects() int      { return o.fileObjects }
func (o OwnedAnnotationReadbackObservation) ReadOnlyContexts() int { return o.readOnlyContexts }
func (o OwnedAnnotationReadbackObservation) AdditionalImportContexts() int {
	return o.additionalContexts
}
func (o OwnedAnnotationReadbackObservation) CopyExportReport() *model.ExportReport {
	if o.report == nil {
		return nil
	}
	return proto.Clone(o.report).(*model.ExportReport)
}
func (o OwnedAnnotationReadbackObservation) copy() OwnedAnnotationReadbackObservation {
	o.archive = o.CopyNativeArchive()
	o.report = o.CopyExportReport()
	return o
}

func (g *ownedAnnotationGraph) actualMapping(p *importProcessor, response *ImportResponse) (map[string]string, error) {
	mapping, ok := response.NativeMappingObservation()
	if !ok || !mapping.CompleteForSelectedSnapshots() || mapping.TraceID() == "" || mapping.TargetSpaceID() != g.spaceID ||
		len(response.NativeMappingProblems()) != 0 || len(mapping.FilteredSources()) != 0 || len(mapping.GeneratedAssignments()) != 0 ||
		len(mapping.KeptReferenceIDs()) != 0 || mapping.NonInjectiveDestinations() {
		return nil, ownedAnnotationRefused("incomplete_original_native_mapping")
	}
	rows := mapping.SourceAssignments()
	if len(rows) != len(g.members) {
		return nil, ownedAnnotationRefused("native_mapping_graph_count")
	}
	result := make(map[string]string, len(rows))
	destinations := make(map[string]bool, len(rows))
	for _, row := range rows {
		plan := g.members[row.SourceObjectID]
		if plan == nil || row.ArchivePath != g.stage.archivePath || row.MemberPath != plan.memberPath || row.SourceSpaceID != g.archive.spaceID ||
			row.ConverterID != g.sourceToConverter[row.SourceObjectID] || row.NativeID == "" || row.NativeID != g.nativeIDs[row.ConverterID] ||
			result[row.SourceObjectID] != "" || destinations[row.NativeID] {
			return nil, ownedAnnotationRefused("native_mapping_source_binding")
		}
		result[row.SourceObjectID] = row.NativeID
		destinations[row.NativeID] = true
	}
	if result[g.archive.rootID] == "" || p.request.SpaceId != g.spaceID {
		return nil, ownedAnnotationRefused("native_mapping_root")
	}
	return result, nil
}

// This runs on the SAME original owned operation goroutine after Execute and
// its workers/file slots have actually drained, before owned.cancel and Done.
func (g *ownedAnnotationGraph) finishReadback(ctx context.Context, p *importProcessor, response *ImportResponse) (*OwnedAnnotationReadbackObservation, error) {
	if response == nil || response.Err != nil {
		return nil, ownedAnnotationRefused("native_execution_not_successful")
	}
	if err := g.requireCurrentWriter(ctx); err != nil {
		return nil, err
	}
	ids, err := g.actualMapping(p, response)
	if err != nil {
		return nil, err
	}
	rootID := ids[g.archive.rootID]
	for _, sourceID := range g.order {
		plan := g.members[sourceID]
		if plan.role == ownedAnnotationFreshPage || plan.role == ownedAnnotationFileObject {
			if _, err := g.uniquePositiveIndex(ctx, bundle.RelationKeyId, ids[sourceID], ids[sourceID]); err != nil {
				return nil, err
			}
		} else if _, err := g.readOnlyContext(ctx, plan); err != nil {
			return nil, err
		}
	}
	for _, plan := range g.additionalContext {
		if _, err := g.readOnlyContext(ctx, plan); err != nil {
			return nil, err
		}
	}
	exportDir := filepath.Join(g.stage.root, "readback")
	if err := os.Mkdir(exportDir, 0700); err != nil {
		return nil, err
	}
	path, report, exportErr := g.exporter.Export(ctx, pb.RpcObjectListExportRequest{
		SpaceId: g.spaceID, ObjectIds: []string{rootID}, Path: exportDir, Format: model.Export_Protobuf,
		Zip: true, IsJson: false, IncludeFiles: true, IncludeNested: true, IncludeArchived: true,
		IncludeBacklinks: false, IncludeSpace: false, NoProgress: true,
	})
	result := &OwnedAnnotationReadbackObservation{stage: OwnedAnnotationExportReturned, accountID: g.accountID, spaceID: g.spaceID, rootID: rootID, sourceDigest: g.archive.digest, sourceSnapshots: len(g.members)}
	if report != nil {
		result.report = proto.Clone(report).(*model.ExportReport)
	}
	// The original Export normalizes context.Canceled to nil; its real report
	// and the still-owned context remain mandatory independent conditions.
	if err := errors.Join(exportErr, ctx.Err()); err != nil {
		return result, err
	}
	if report == nil || report.Status != model.ExportReport_SUCCESS || report.Succeed <= 0 || report.ObjectErrors != 0 || report.FileErrors != 0 || len(report.Issues) != 0 {
		return result, ownedAnnotationRefused("original_export_incomplete")
	}
	raw, err := readOwnedAnnotationExport(ctx, exportDir, path)
	if err != nil {
		return result, err
	}
	digest := sha256.Sum256(raw)
	result.archive, result.archiveDigest = append([]byte(nil), raw...), digest
	actual, err := inspectOwnedAnnotationArchive(ctx, raw, digest, rootID, g.spaceID)
	if err != nil {
		return result, err
	}
	if int(report.Succeed) != len(actual.snapshots) {
		return result, ownedAnnotationRefused("original_export_report_inventory")
	}
	result.stage = OwnedAnnotationArchiveValidated
	if err := g.compareNativeExport(ctx, p, ids, actual, result); err != nil {
		return result, err
	}
	// Reobserve every readonly native schema after original export. A native
	// initializer/reviser or concurrent modification cannot silently become a
	// body receipt: the actual persisted heads must still match admission.
	for _, sourceID := range g.order {
		plan := g.members[sourceID]
		if plan.expectedTarget != "" {
			if _, err := g.readOnlyContext(ctx, plan); err != nil {
				return result, err
			}
		}
	}
	for _, plan := range g.additionalContext {
		if _, err := g.readOnlyContext(ctx, plan); err != nil {
			return result, err
		}
	}
	if err := g.requireCurrentWriter(ctx); err != nil {
		return result, err
	}
	result.stage = OwnedAnnotationBodyMatched
	return result, nil
}

func readOwnedAnnotationExport(ctx context.Context, directory, path string) ([]byte, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	relative, err := filepath.Rel(directory, path)
	if err != nil {
		return nil, err
	}
	// Original protobuf ZIP is a direct regular child of this private directory.
	if relative == "." || relative == ".." || filepath.IsAbs(relative) || strings.ContainsAny(relative, "/\\") || filepath.Ext(relative) != ".zip" {
		return nil, ownedAnnotationRefused("native_export_path_not_owned")
	}
	before, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !before.Mode().IsRegular() || before.Size() <= 0 || before.Size() > ownedArchiveMaxBytes {
		return nil, ownedAnnotationRefused("native_export_compressed_budget")
	}
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	opened, err := file.Stat()
	if err != nil {
		return nil, errors.Join(err, file.Close())
	}
	if !os.SameFile(before, opened) {
		return nil, errors.Join(ownedAnnotationRefused("native_export_identity_changed"), file.Close())
	}
	raw, readErr := io.ReadAll(io.LimitReader(file, ownedArchiveMaxBytes+1))
	closeErr := file.Close()
	if err := errors.Join(readErr, closeErr, ctx.Err()); err != nil {
		return nil, err
	}
	after, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if int64(len(raw)) != before.Size() || !os.SameFile(before, after) || before.Size() != after.Size() {
		return nil, ownedAnnotationRefused("native_export_bytes_changed")
	}
	return raw, nil
}

// expectedOriginalFileMetadataBlocks derives the original uploader's bounded
// origin/importType block additions from source metadata and Import(Pb). It does
// not inspect readback and never replaces, removes, or rewrites a source block.
func expectedOriginalFileMetadataBlocks(data *model.SmartBlockSnapshotBase, nativeID string) error {
	if data == nil || data.Details == nil || nativeID == "" {
		return ownedAnnotationRefused("expected_original_file_metadata")
	}
	project := func(details *domain.Details) (map[string]*model.Block, error) {
		st := state.NewDoc(nativeID, nil).NewState()
		fileblocks.InitEmptyFileState(st)
		if err := fileblocks.AddFileBlocks(st, details, nativeID); err != nil {
			return nil, err
		}
		blocks := make(map[string]*model.Block)
		for _, block := range st.Blocks() {
			blocks[block.Id] = block
		}
		return blocks, nil
	}
	beforeDetails := domain.NewDetailsFromProto(data.Details).CopyWithoutKeys()
	afterDetails := beforeDetails.CopyWithoutKeys()
	objectorigin.Import(model.Import_Pb).AddToDetails(afterDetails)
	before, err := project(beforeDetails)
	if err != nil {
		return err
	}
	after, err := project(afterDetails)
	if err != nil {
		return err
	}
	current := make(map[string]*model.Block)
	for _, block := range data.Blocks {
		if block == nil || block.Id == "" || current[block.Id] != nil {
			return ownedAnnotationRefused("expected_original_file_metadata_preimage")
		}
		current[block.Id] = block
	}
	root, oldRoot, newRoot := current[nativeID], before[nativeID], after[nativeID]
	if root == nil || oldRoot == nil || newRoot == nil {
		return ownedAnnotationRefused("expected_original_file_metadata_preimage")
	}
	positions := make(map[string]int)
	for i, id := range root.ChildrenIds {
		if _, duplicate := positions[id]; duplicate {
			return ownedAnnotationRefused("expected_original_file_metadata_preimage")
		}
		positions[id] = i
	}
	last := -1
	for _, id := range oldRoot.ChildrenIds {
		pos, exists := positions[id]
		if !exists || pos <= last {
			return ownedAnnotationRefused("expected_original_file_metadata_preimage")
		}
		last = pos
	}
	additions := make(map[string]*model.Block)
	for id, block := range after {
		if id == nativeID {
			continue
		}
		old := before[id]
		if old != nil {
			if !proto.Equal(old, block) {
				return ownedAnnotationRefused("unexpected_original_file_template_delta")
			}
			continue
		}
		if (id != bundle.RelationKeyOrigin.String() && id != bundle.RelationKeyImportType.String()) ||
			block.GetRelation() == nil || block.GetRelation().Key != id || current[id] != nil {
			return ownedAnnotationRefused("expected_original_file_metadata_collision")
		}
		additions[id] = proto.Clone(block).(*model.Block)
	}
	for id := range before {
		if after[id] == nil {
			return ownedAnnotationRefused("unexpected_original_file_template_delta")
		}
	}
	children := append([]string(nil), root.ChildrenIds...)
	var added []*model.Block
	for i, id := range newRoot.ChildrenIds {
		block := additions[id]
		if block == nil {
			continue
		}
		at := len(children)
		for _, following := range newRoot.ChildrenIds[i+1:] {
			if before[following] == nil {
				continue
			}
			for j, existing := range children {
				if existing == following {
					at = j
					break
				}
			}
			break
		}
		children = append(children, "")
		copy(children[at+1:], children[at:])
		children[at] = id
		added = append(added, block)
	}
	if len(added) != len(additions) {
		return ownedAnnotationRefused("unexpected_original_file_template_delta")
	}
	// No source child changes its position relative to another source child.
	root.ChildrenIds = children
	data.Blocks = append(data.Blocks, added...)
	return nil
}

func (g *ownedAnnotationGraph) compareNativeExport(ctx context.Context, p *importProcessor, ids map[string]string, actual *ownedAnnotationArchive, result *OwnedAnnotationReadbackObservation) error {
	if len(actual.snapshots) < len(g.members) || len(actual.snapshots) > len(g.members)+len(g.additionalContext) {
		return ownedAnnotationRefused("native_export_graph_inventory")
	}
	seen := make(map[string]bool, len(actual.snapshots))
	fileMembers := make(map[string]ownedAnnotationArchiveMember)
	for _, member := range actual.members {
		if member.Kind == "file" {
			fileMembers[member.Name] = member
		}
	}
	usedFiles := make(map[string]bool, len(fileMembers))
	formats := make(map[domain.RelationKey]int32)
	for _, plan := range g.members {
		if plan.nativeKey != nil && plan.nativeKey.SmartblockType() == coresb.SmartBlockTypeRelation {
			formats[domain.RelationKey(plan.nativeKey.InternalKey())] = int32(domain.NewDetailsFromProto(plan.snapshot.Snapshot.Data.Details).GetInt64(bundle.RelationKeyRelationFormat))
		}
	}
	for _, sourceID := range g.order {
		if err := ctx.Err(); err != nil {
			return err
		}
		plan := g.members[sourceID]
		targetID := ids[sourceID]
		observed := actual.snapshots[targetID]
		if observed == nil || observed.Snapshot == nil || observed.Snapshot.Data == nil || observed.SbType != plan.snapshot.SbType || seen[targetID] {
			return ownedAnnotationRefused("native_export_source_member")
		}
		seen[targetID] = true
		details := domain.NewDetailsFromProto(observed.Snapshot.Data.Details)
		if details.GetString(bundle.RelationKeyId) != targetID || details.GetString(bundle.RelationKeySpaceId) != g.spaceID {
			return ownedAnnotationRefused("native_export_member_identity")
		}
		switch plan.role {
		case ownedAnnotationFreshPage:
			expected, err := g.expectedCreatedPage(p, g.sourceToConverter[sourceID], targetID)
			if err != nil {
				return err
			}
			left, err := canonicalOwnedAnnotationSnapshot(expected)
			if err != nil {
				return err
			}
			right, err := canonicalOwnedAnnotationSnapshot(observed)
			if err != nil {
				return err
			}
			if !proto.Equal(left, right) {
				return ownedAnnotationRefused("native_annotation_body_differs")
			}
			result.annotationPages++
		case ownedAnnotationFixedSchema, ownedAnnotationBundledSchema:
			if err := g.requireSchemaSnapshotCompatibility(ctx, plan, observed); err != nil {
				return err
			}
			if err := g.compareObservedSchemaExport(ctx, plan, observed); err != nil {
				return err
			}
			result.readOnlyContexts++
		case ownedAnnotationParticipant:
			// Participant display/profile state belongs to the actual account,
			// not to the imported annotation. Preserve that native context;
			// compare identity and original participant type without resetting it.
			if details.GetString(bundle.RelationKeyIdentity) != g.accountID || targetID != g.account.MyParticipantId(g.spaceID) ||
				len(observed.Snapshot.Data.ObjectTypes) != 1 || observed.Snapshot.Data.ObjectTypes[0] != bundle.TypeKeyParticipant.URL() {
				return ownedAnnotationRefused("native_export_participant_context")
			}
			result.readOnlyContexts++
		case ownedAnnotationFileObject:
			source := details.GetString(bundle.RelationKeySource)
			binary, ok := fileMembers[source]
			if !ok || binary.Bytes != plan.fileBytes || binary.SHA256 != plan.fileDigest {
				return ownedAnnotationRefused("native_file_body_differs")
			}
			usedFiles[source] = true
			expected := proto.Clone(plan.snapshot).(*pb.SnapshotWithType)
			for _, b := range expected.Snapshot.Data.Blocks {
				if b.Id == sourceID {
					b.Id = targetID
				}
				for i, id := range b.ChildrenIds {
					if id == sourceID {
						b.ChildrenIds[i] = targetID
					}
				}
			}
			if err := expectedOriginalFileMetadataBlocks(expected.Snapshot.Data, targetID); err != nil {
				return err
			}
			st, err := state.NewDocFromSnapshot(targetID, expected.Snapshot)
			if err != nil {
				return err
			}
			common.UpdateObjectIDsInRelations(st, ids, formats)
			if err := common.UpdateLinksToObjects(st, ids); err != nil {
				return err
			}
			st.SetDetail(bundle.RelationKeySource, domain.String(source))
			bytes := pbc.NewConverter(st, false).Convert(expected.SbType)
			if len(bytes) == 0 {
				return ownedAnnotationRefused("expected_file_model")
			}
			if err := proto.Unmarshal(bytes, expected); err != nil {
				return err
			}
			g.mu.Lock()
			uploaded, ok := g.fileUploads[sourceID]
			g.mu.Unlock()
			if !ok || uploaded.err != nil || uploaded.id != targetID || observed.Snapshot.Data.FileInfo == nil || observed.Snapshot.Data.FileInfo.FileId != uploaded.fileID || expected.Snapshot.Data.FileInfo == nil {
				return ownedAnnotationRefused("native_file_completion_binding")
			}
			expected.Snapshot.Data.FileInfo.FileId = uploaded.fileID
			ed := domain.NewDetailsFromProto(expected.Snapshot.Data.Details)
			ed.SetString(bundle.RelationKeyFileId, uploaded.fileID)
			expected.Snapshot.Data.Details = ed.ToProto()
			left, err := canonicalOwnedAnnotationSnapshot(expected)
			if err != nil {
				return err
			}
			right, err := canonicalOwnedAnnotationSnapshot(observed)
			if err != nil {
				return err
			}
			if !proto.Equal(left, right) {
				return ownedAnnotationRefused("native_file_snapshot_differs")
			}
			result.fileObjects++
		default:
			return ownedAnnotationRefused("native_export_unknown_source_role")
		}
	}
	for id, snapshot := range actual.snapshots {
		if seen[id] {
			continue
		}
		plan := g.additionalContext[id]
		if plan == nil || !g.isOriginalImportMetadata(plan) || snapshot == nil || snapshot.Snapshot == nil || snapshot.Snapshot.Data == nil ||
			snapshot.Snapshot.Data.Key != plan.nativeKey.InternalKey() {
			return ownedAnnotationRefused("unaccounted_native_export_dependency")
		}
		if _, err := g.readOnlyContext(ctx, plan); err != nil {
			return err
		}
		if err := g.compareObservedSchemaExport(ctx, plan, snapshot); err != nil {
			return err
		}
		seen[id] = true
		result.additionalContexts++
	}
	if len(seen) != len(actual.snapshots) || len(usedFiles) != len(fileMembers) || result.annotationPages == 0 {
		return ownedAnnotationRefused("native_export_complete_body_coverage")
	}
	return g.requireCurrentWriter(ctx)
}

// The additional original metadata schemas are not archive source members. Their
// export must still equal the actual bounded raw native snapshot admitted before
// import, not merely share its key. Source schema members also use this separate
// native observation comparison in addition to source-to-target correspondence.
func (g *ownedAnnotationGraph) compareObservedSchemaExport(ctx context.Context, plan *ownedAnnotationMemberPlan, actual *pb.SnapshotWithType) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	if plan == nil || actual == nil || actual.Snapshot == nil || actual.Snapshot.Data == nil {
		return ownedAnnotationRefused("missing_observed_schema_export")
	}
	g.mu.Lock()
	retained := g.readOnlySnapshots[plan.expectedTarget]
	var expected *pb.SnapshotWithType
	if retained != nil {
		expected = proto.Clone(retained).(*pb.SnapshotWithType)
	}
	g.mu.Unlock()
	if expected == nil || actual.SbType != expected.SbType || actual.Snapshot.Data.Key != plan.nativeKey.InternalKey() {
		return ownedAnnotationRefused("observed_schema_export_identity")
	}
	details := domain.NewDetailsFromProto(actual.Snapshot.Data.Details)
	if details.GetString(bundle.RelationKeyId) != plan.expectedTarget || details.GetString(bundle.RelationKeySpaceId) != g.spaceID {
		return ownedAnnotationRefused("observed_schema_export_identity")
	}
	left, err := canonicalOwnedAnnotationSnapshot(expected)
	if err != nil {
		return err
	}
	right, err := canonicalOwnedAnnotationSnapshot(actual)
	if err != nil {
		return err
	}
	if !proto.Equal(left, right) {
		return ownedAnnotationRefused("native_schema_export_differs_from_observed_state")
	}
	return ctx.Err()
}
