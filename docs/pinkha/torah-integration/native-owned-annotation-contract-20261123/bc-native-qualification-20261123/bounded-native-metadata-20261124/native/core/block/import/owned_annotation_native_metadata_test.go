package importer

import (
	"context"
	"testing"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	"github.com/anyproto/anytype-heart/core/files/fileobject/fileblocks"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

func originalMetadataPlan(t *testing.T, key domain.RelationKey) *ownedAnnotationMemberPlan {
	t.Helper()
	unique, err := domain.NewUniqueKey(coresb.SmartBlockTypeRelation, key.String())
	require.NoError(t, err)
	return &ownedAnnotationMemberPlan{role: ownedAnnotationBundledSchema, nativeKey: unique, expectedTarget: "native-target"}
}

func originalMetadataObservation(t *testing.T) (*ownedAnnotationGraph, *ownedAnnotationMemberPlan, *pb.SnapshotWithType) {
	t.Helper()
	plan := originalMetadataPlan(t, bundle.RelationKeySyncStatus)
	details := domain.NewDetailsFromMap(map[domain.RelationKey]domain.Value{
		bundle.RelationKeyId:             domain.String(plan.expectedTarget),
		bundle.RelationKeySpaceId:        domain.String("target-space"),
		bundle.RelationKeyName:           domain.String("Sync status"),
		bundle.RelationKeyRelationKey:    domain.String(bundle.RelationKeySyncStatus.String()),
		bundle.RelationKeyRelationFormat: domain.Int64(int64(model.RelationFormat_number)),
	})
	raw := &pb.SnapshotWithType{SbType: coresb.SmartBlockTypeRelation.ToProto(), Snapshot: &pb.ChangeSnapshot{Data: &model.SmartBlockSnapshotBase{
		Key: plan.nativeKey.InternalKey(), Details: details.ToProto(),
	}}}
	g := &ownedAnnotationGraph{spaceID: "target-space", readOnlySnapshots: map[string]*pb.SnapshotWithType{plan.expectedTarget: raw}}
	return g, plan, proto.Clone(raw).(*pb.SnapshotWithType)
}

func TestOtzariaBoundedOriginalNativeMetadata(t *testing.T) {
	t.Run("exact_six_original_native_keys_admitted", func(t *testing.T) {
		expected := []domain.RelationKey{bundle.RelationKeyImportType, bundle.RelationKeyOldAnytypeID, bundle.RelationKeySourceFilePath,
			bundle.RelationKeySyncStatus, bundle.RelationKeySyncDate, bundle.RelationKeySyncError}
		require.ElementsMatch(t, expected, originalOwnedAnnotationMetadataKeys())
		g := &ownedAnnotationGraph{}
		for _, key := range expected {
			require.True(t, g.isOriginalImportMetadata(originalMetadataPlan(t, key)), key.String())
		}
	})
	t.Run("arbitrary_or_other_original_relation_refused", func(t *testing.T) {
		g := &ownedAnnotationGraph{}
		for _, key := range []domain.RelationKey{"unreviewedMetadata", bundle.RelationKeyName, bundle.RelationKeyDescription, bundle.RelationKeyAddedDate} {
			require.False(t, g.isOriginalImportMetadata(originalMetadataPlan(t, key)), key.String())
		}
	})
	t.Run("source_backed_wrong_role_or_native_kind_refused", func(t *testing.T) {
		g := &ownedAnnotationGraph{}
		require.False(t, g.isOriginalImportMetadata(nil))
		for _, change := range []func(*ownedAnnotationMemberPlan){
			func(p *ownedAnnotationMemberPlan) { p.sourceID = "source" },
			func(p *ownedAnnotationMemberPlan) { p.snapshot = &pb.SnapshotWithType{} },
			func(p *ownedAnnotationMemberPlan) { p.role = ownedAnnotationFreshPage },
			func(p *ownedAnnotationMemberPlan) { p.nativeKey = nil },
			func(p *ownedAnnotationMemberPlan) {
				var err error
				p.nativeKey, err = domain.NewUniqueKey(coresb.SmartBlockTypeObjectType, bundle.RelationKeySyncStatus.String())
				require.NoError(t, err)
			},
		} {
			plan := originalMetadataPlan(t, bundle.RelationKeySyncStatus)
			change(plan)
			require.False(t, g.isOriginalImportMetadata(plan))
		}
	})
	t.Run("observed_schema_identity_and_space_bound", func(t *testing.T) {
		g, plan, observed := originalMetadataObservation(t)
		require.NoError(t, g.compareObservedSchemaExport(context.Background(), plan, observed))
		for _, change := range []func(*pb.SnapshotWithType){
			func(s *pb.SnapshotWithType) { s.SbType = coresb.SmartBlockTypeObjectType.ToProto() },
			func(s *pb.SnapshotWithType) { s.Snapshot.Data.Key = bundle.RelationKeySyncError.String() },
			func(s *pb.SnapshotWithType) {
				d := domain.NewDetailsFromProto(s.Snapshot.Data.Details)
				d.SetString(bundle.RelationKeyId, "unowned-target")
				s.Snapshot.Data.Details = d.ToProto()
			},
			func(s *pb.SnapshotWithType) {
				d := domain.NewDetailsFromProto(s.Snapshot.Data.Details)
				d.SetString(bundle.RelationKeySpaceId, "wrong-space")
				s.Snapshot.Data.Details = d.ToProto()
			},
		} {
			changed := proto.Clone(observed).(*pb.SnapshotWithType)
			change(changed)
			require.EqualError(t, g.compareObservedSchemaExport(context.Background(), plan, changed), "owned annotation import refused: observed_schema_export_identity")
		}
	})
	t.Run("altered_nonlocal_schema_body_refused", func(t *testing.T) {
		g, plan, observed := originalMetadataObservation(t)
		for _, change := range []func(*pb.SnapshotWithType){
			func(s *pb.SnapshotWithType) {
				d := domain.NewDetailsFromProto(s.Snapshot.Data.Details)
				d.SetString(bundle.RelationKeyName, "Unreviewed schema")
				s.Snapshot.Data.Details = d.ToProto()
			},
			func(s *pb.SnapshotWithType) {
				d := domain.NewDetailsFromProto(s.Snapshot.Data.Details)
				d.SetInt64(bundle.RelationKeyRelationFormat, int64(model.RelationFormat_longtext))
				s.Snapshot.Data.Details = d.ToProto()
			},
		} {
			changed := proto.Clone(observed).(*pb.SnapshotWithType)
			change(changed)
			require.EqualError(t, g.compareObservedSchemaExport(context.Background(), plan, changed), "owned annotation import refused: native_schema_export_differs_from_observed_state")
		}
	})
	t.Run("missing_preimport_observation_refused", func(t *testing.T) {
		g, plan, observed := originalMetadataObservation(t)
		delete(g.readOnlySnapshots, plan.expectedTarget)
		require.EqualError(t, g.compareObservedSchemaExport(context.Background(), plan, observed), "owned annotation import refused: observed_schema_export_identity")
		require.EqualError(t, g.compareObservedSchemaExport(context.Background(), plan, nil), "owned annotation import refused: missing_observed_schema_export")
	})

	t.Run("file_source_schema_requires_authenticated_file_member", func(t *testing.T) {
		member := originalMetadataOwnedFile(t)
		g := &ownedAnnotationGraph{members: map[string]*ownedAnnotationMemberPlan{member.sourceID: member}}
		require.Len(t, g.originalImportMetadataKeys(), 7)
		require.True(t, g.isOriginalImportMetadata(originalMetadataPlan(t, bundle.RelationKeySource)))
		require.ElementsMatch(t, append(originalOwnedAnnotationMetadataKeys(), bundle.RelationKeySource), g.originalImportMetadataKeys())
	})
	t.Run("file_source_schema_refused_without_valid_file_member", func(t *testing.T) {
		for _, change := range []func(*ownedAnnotationMemberPlan){
			func(p *ownedAnnotationMemberPlan) { p.role = ownedAnnotationFreshPage },
			func(p *ownedAnnotationMemberPlan) { p.sourceID = "" },
			func(p *ownedAnnotationMemberPlan) { p.snapshot = nil },
			func(p *ownedAnnotationMemberPlan) { p.snapshot.SbType = coresb.SmartBlockTypePage.ToProto() },
			func(p *ownedAnnotationMemberPlan) { p.snapshot.Snapshot.Data.FileInfo = nil },
			func(p *ownedAnnotationMemberPlan) { p.fileSource = "files/unowned.txt" },
		} {
			member := originalMetadataOwnedFile(t)
			change(member)
			g := &ownedAnnotationGraph{members: map[string]*ownedAnnotationMemberPlan{"source": member}}
			require.ElementsMatch(t, originalOwnedAnnotationMetadataKeys(), g.originalImportMetadataKeys())
			require.False(t, g.isOriginalImportMetadata(originalMetadataPlan(t, bundle.RelationKeySource)))
		}
		g := &ownedAnnotationGraph{}
		require.False(t, g.isOriginalImportMetadata(originalMetadataPlan(t, bundle.RelationKeySource)))
	})
	t.Run("file_origin_delta_matches_original_template_order", func(t *testing.T) {
		for _, alreadyImported := range []bool{false, true} {
			details := originalMetadataFileDetails()
			if alreadyImported {
				objectorigin.Import(model.Import_Pb).AddToDetails(details)
			}
			source := originalMetadataFileSnapshot(t, details)
			frozen := proto.Clone(source).(*pb.SnapshotWithType)
			expected := proto.Clone(source).(*pb.SnapshotWithType)
			require.NoError(t, expectedOriginalFileMetadataBlocks(expected.Snapshot.Data, "source-file"))
			after := details.CopyWithoutKeys()
			objectorigin.Import(model.Import_Pb).AddToDetails(after)
			native := originalMetadataFileSnapshot(t, after)
			left, err := canonicalOwnedAnnotationSnapshot(expected)
			require.NoError(t, err)
			right, err := canonicalOwnedAnnotationSnapshot(native)
			require.NoError(t, err)
			require.True(t, proto.Equal(left, right), "projection must equal the original new-upload template including child order")
			require.True(t, proto.Equal(source, frozen), "original source is not mutated")
			root := originalMetadataRoot(t, expected)
			require.Equal(t, []string{"header", "file", "info", "description", "fileExt", "sizeInBytes", "origin", "importType", "addedDate"}, root.ChildrenIds)
		}
	})
	t.Run("file_origin_delta_preserves_user_body_and_order", func(t *testing.T) {
		source := originalMetadataFileSnapshot(t, originalMetadataFileDetails())
		user := &model.Block{Id: "user-body", Content: &model.BlockContentOfText{Text: &model.BlockContentText{
			Text: "Retain the source body", Marks: &model.BlockContentTextMarks{Marks: []*model.BlockContentTextMark{
				{Range: &model.Range{From: 0, To: 6}, Type: model.BlockContentTextMark_Bold},
			}},
		}}}
		source.Snapshot.Data.Blocks = append(source.Snapshot.Data.Blocks, user)
		root := originalMetadataRoot(t, source)
		root.ChildrenIds = append(root.ChildrenIds, user.Id)
		beforeChildren := append([]string(nil), root.ChildrenIds...)
		beforeUser := proto.Clone(user).(*model.Block)
		require.NoError(t, expectedOriginalFileMetadataBlocks(source.Snapshot.Data, "source-file"))
		require.True(t, proto.Equal(beforeUser, user), "metadata projection cannot replace a source text/mark")
		var retained []string
		for _, id := range root.ChildrenIds {
			if id != "origin" && id != "importType" {
				retained = append(retained, id)
			}
		}
		require.Equal(t, beforeChildren, retained, "every pair of source children retains its order")
		afterDetails := originalMetadataFileDetails()
		objectorigin.Import(model.Import_Pb).AddToDetails(afterDetails)
		droppedBody := originalMetadataFileSnapshot(t, afterDetails)
		left, err := canonicalOwnedAnnotationSnapshot(source)
		require.NoError(t, err)
		right, err := canonicalOwnedAnnotationSnapshot(droppedBody)
		require.NoError(t, err)
		require.False(t, proto.Equal(left, right), "loss of arbitrary source body must remain refused")
		changed := proto.Clone(source).(*pb.SnapshotWithType)
		for _, block := range changed.Snapshot.Data.Blocks {
			if block.Id == user.Id {
				block.GetText().Marks.Marks[0].Range.To = 7
			}
		}
		right, err = canonicalOwnedAnnotationSnapshot(changed)
		require.NoError(t, err)
		require.False(t, proto.Equal(left, right), "altered source marks must remain refused")
	})
	t.Run("file_origin_delta_refuses_reserved_block_collision", func(t *testing.T) {
		source := originalMetadataFileSnapshot(t, originalMetadataFileDetails())
		source.Snapshot.Data.Blocks = append(source.Snapshot.Data.Blocks,
			&model.Block{Id: "origin", Content: &model.BlockContentOfText{Text: &model.BlockContentText{Text: "User body at a reserved ID"}}})
		frozen := proto.Clone(source)
		require.EqualError(t, expectedOriginalFileMetadataBlocks(source.Snapshot.Data, "source-file"),
			"owned annotation import refused: expected_original_file_metadata_collision")
		require.True(t, proto.Equal(source, frozen), "refusal cannot partially change a source block")
	})
	t.Run("file_origin_delta_refuses_changed_anchor_order", func(t *testing.T) {
		for _, remove := range []bool{false, true} {
			source := originalMetadataFileSnapshot(t, originalMetadataFileDetails())
			root := originalMetadataRoot(t, source)
			if remove {
				root.ChildrenIds = append(root.ChildrenIds[:1], root.ChildrenIds[2:]...)
			} else {
				root.ChildrenIds[1], root.ChildrenIds[2] = root.ChildrenIds[2], root.ChildrenIds[1]
			}
			frozen := proto.Clone(source)
			require.EqualError(t, expectedOriginalFileMetadataBlocks(source.Snapshot.Data, "source-file"),
				"owned annotation import refused: expected_original_file_metadata_preimage")
			require.True(t, proto.Equal(source, frozen))
		}
	})
}

func originalMetadataFileDetails() *domain.Details {
	return domain.NewDetailsFromMap(map[domain.RelationKey]domain.Value{
		bundle.RelationKeyId:           domain.String("source-file"),
		bundle.RelationKeyName:         domain.String("native-attachment"),
		bundle.RelationKeyFileMimeType: domain.String("text/plain; charset=utf-8"),
		bundle.RelationKeySizeInBytes:  domain.Int64(51),
		bundle.RelationKeyAddedDate:    domain.Int64(1600000000),
		bundle.RelationKeySource:       domain.String("files/native-attachment.txt"),
	})
}

func originalMetadataFileSnapshot(t *testing.T, details *domain.Details) *pb.SnapshotWithType {
	t.Helper()
	st := state.NewDoc("source-file", nil).NewState()
	fileblocks.InitEmptyFileState(st)
	require.NoError(t, fileblocks.AddFileBlocks(st, details, "source-file"))
	return &pb.SnapshotWithType{SbType: coresb.SmartBlockTypeFileObject.ToProto(), Snapshot: &pb.ChangeSnapshot{Data: &model.SmartBlockSnapshotBase{
		Blocks: st.Blocks(), Details: details.CopyWithoutKeys().ToProto(), FileInfo: &model.FileInfo{FileId: "source-blob"},
	}}}
}

func originalMetadataOwnedFile(t *testing.T) *ownedAnnotationMemberPlan {
	t.Helper()
	return &ownedAnnotationMemberPlan{role: ownedAnnotationFileObject, sourceID: "source-file",
		fileSource: "files/native-attachment.txt", snapshot: originalMetadataFileSnapshot(t, originalMetadataFileDetails())}
}

func originalMetadataRoot(t *testing.T, snapshot *pb.SnapshotWithType) *model.Block {
	t.Helper()
	for _, block := range snapshot.Snapshot.Data.Blocks {
		if block.Id == "source-file" {
			return block
		}
	}
	t.Fatal("original file root missing")
	return nil
}
