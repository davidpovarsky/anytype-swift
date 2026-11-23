package importer

import (
	"context"
	"testing"

	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/simple/base"
	"github.com/anyproto/anytype-heart/core/converter/pbc"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

func originalRestrictionComparisonFixture(t *testing.T) (*ownedAnnotationGraph, *ownedAnnotationMemberPlan, *pb.SnapshotWithType) {
	t.Helper()
	const id = "original-schema-control"
	key := domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "originalSchemaControl")
	raw := &pb.SnapshotWithType{
		SbType: coresb.SmartBlockTypeObjectType.ToProto(),
		Snapshot: &pb.ChangeSnapshot{Data: &model.SmartBlockSnapshotBase{
			Key: key.InternalKey(), ObjectTypes: []string{"ot-objectType"},
			Details: domain.NewDetailsFromMap(map[domain.RelationKey]domain.Value{
				bundle.RelationKeyName: domain.String("Original schema restriction control"),
				bundle.RelationKeyRecommendedHiddenRelations: domain.StringList([]string{
					bundle.RelationKeyLastOpenedDate.BundledURL(),
				}),
			}).ToProto(),
			Blocks: []*model.Block{
				{Id: id, ChildrenIds: []string{"dataview"},
					Content: &model.BlockContentOfSmartblock{Smartblock: &model.BlockContentSmartblock{}}},
				{Id: "dataview", Restrictions: &model.BlockRestrictions{},
					Content: &model.BlockContentOfDataview{Dataview: &model.BlockContentDataview{
						Views: []*model.BlockContentDataviewView{{Id: "original", Name: "Original view"}},
					}}},
			},
		}},
	}
	doc, err := state.NewDocFromSnapshot(id, raw.Snapshot)
	require.NoError(t, err)
	var target pb.SnapshotWithType
	require.NoError(t, proto.Unmarshal(pbc.NewConverter(doc, false).Convert(raw.SbType), &target))
	plan := &ownedAnnotationMemberPlan{sourceID: id, expectedTarget: id, snapshot: raw, nativeKey: key}
	graph := &ownedAnnotationGraph{members: map[string]*ownedAnnotationMemberPlan{id: plan}}
	return graph, plan, &target
}

func originalControlDataview(t *testing.T, s *pb.SnapshotWithType) *model.Block {
	t.Helper()
	for _, b := range s.Snapshot.Data.Blocks {
		if b.Id == "dataview" {
			return b
		}
	}
	t.Fatal("original dataview missing")
	return nil
}

func TestOtzariaOriginalSchemaRestrictionSemantics(t *testing.T) {
	t.Run("original_diff_nil_empty_no_event", func(t *testing.T) {
		left := &model.Block{Id: "native-diff"}
		right := &model.Block{Id: "native-diff", Restrictions: &model.BlockRestrictions{}}
		events, err := base.NewBase(left).Diff("", base.NewBase(right))
		require.NoError(t, err)
		require.Empty(t, events)
		require.NotNil(t, left.Restrictions)
		require.True(t, proto.Equal(left, right))
	})
	t.Run("replayed_nil_matches_exported_empty", func(t *testing.T) {
		graph, plan, target := originalRestrictionComparisonFixture(t)
		originalControlDataview(t, target).Restrictions = nil
		beforeSource, beforeTarget := proto.Clone(plan.snapshot), proto.Clone(target)
		require.NoError(t, graph.requireSchemaSnapshotCompatibility(context.Background(), plan, target))
		require.True(t, proto.Equal(beforeSource, plan.snapshot), "source must remain immutable")
		require.True(t, proto.Equal(beforeTarget, target), "replay observation must remain immutable")
	})
	for _, tc := range []struct {
		name        string
		restriction model.BlockRestrictions
	}{
		{"read", model.BlockRestrictions{Read: true}},
		{"edit", model.BlockRestrictions{Edit: true}},
		{"remove", model.BlockRestrictions{Remove: true}},
		{"drag", model.BlockRestrictions{Drag: true}},
		{"drop_on", model.BlockRestrictions{DropOn: true}},
	} {
		t.Run("refuse_changed_"+tc.name, func(t *testing.T) {
			graph, plan, target := originalRestrictionComparisonFixture(t)
			originalControlDataview(t, target).Restrictions = &tc.restriction
			err := graph.requireSchemaSnapshotCompatibility(context.Background(), plan, target)
			require.EqualError(t, err, "owned annotation import refused: source_target_schema_semantics_differ")
		})
	}
	t.Run("refuse_changed_hidden_relation", func(t *testing.T) {
		graph, plan, target := originalRestrictionComparisonFixture(t)
		details := domain.NewDetailsFromProto(target.Snapshot.Data.Details)
		details.SetStringList(bundle.RelationKeyRecommendedHiddenRelations, []string{
			bundle.RelationKeyCreatedDate.BundledURL(),
		})
		target.Snapshot.Data.Details = details.ToProto()
		err := graph.requireSchemaSnapshotCompatibility(context.Background(), plan, target)
		require.EqualError(t, err, "owned annotation import refused: source_target_schema_semantics_differ")
	})
	t.Run("refuse_changed_nested_body", func(t *testing.T) {
		graph, plan, target := originalRestrictionComparisonFixture(t)
		originalControlDataview(t, target).GetDataview().Views[0].Name = "Changed view"
		err := graph.requireSchemaSnapshotCompatibility(context.Background(), plan, target)
		require.EqualError(t, err, "owned annotation import refused: source_target_schema_semantics_differ")
	})
}
