package importer

import (
	"context"
	"testing"

	"github.com/anyproto/anytype-heart/core/domain"
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
}
