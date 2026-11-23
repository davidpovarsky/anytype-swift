package export

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// Exercise the original indexed collector and state walker. The target type
// IDs are deliberately unrelated to any bundled image type: target constraints
// are graph edges, not a special case for one relation, name, or CID.
func TestOtzariaRelationTargetTypeExportClosure(t *testing.T) {
	const (
		rootID   = "selected-original-root"
		rootType = "selected-original-type"
		targetA  = "arbitrary-constraint-type-a"
		targetB  = "arbitrary-constraint-type-b"
		unused   = "unselected-definition-type"
	)
	targetReadFailure := errors.New("original target type could not be read")
	for _, tc := range []struct {
		name        string
		selected    bool
		targets     []string
		second      []string
		recommended bool
		readFailure bool
		want        []string
	}{
		{name: "direct_arbitrary_type", selected: true, targets: []string{targetA}, want: []string{targetA}},
		{name: "ordered_multiple_types", selected: true, targets: []string{targetB, targetA}, want: []string{targetA, targetB}},
		{name: "transitive_type_constraint", selected: true, targets: []string{targetA}, second: []string{targetB}, want: []string{targetA, targetB}},
		{name: "recommended_only_relation", recommended: true, targets: []string{targetA}, want: []string{targetA}},
		{name: "cycle_visits_each_type_once", selected: true, targets: []string{targetA}, second: []string{rootType}, want: []string{targetA}},
		{name: "unselected_definition_and_scalar_id_are_not_followed", targets: []string{targetA}},
		{name: "empty_constraint_adds_no_type", selected: true},
		{name: "target_read_error_is_propagated", selected: true, targets: []string{targetA}, readFailure: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			fx := newFixture(t)
			rootDetails := map[domain.RelationKey]domain.Value{
				bundle.RelationKeyName: domain.String(targetA),
			}
			if tc.selected {
				rootDetails[bundle.RelationKeyCreator] = domain.String("original-author-value")
			}
			root := setupObject(rootID, rootType, smartblock.SmartBlockTypePage, rootDetails)
			fx.picker.EXPECT().GetObject(context.Background(), rootID).Return(root, nil).Once()

			var recommendations []string
			relationKey := bundle.RelationKeyCreator
			if tc.recommended {
				relationKey = domain.RelationKey("originalRecommendedConstraint")
				recommendations = []string{relationKey.String()}
			}
			relation := prepareTestRelationForStore(t, relationKey, int64(model.RelationFormat_object))
			relation[bundle.RelationKeyRelationFormatObjectTypes] = domain.StringList(tc.targets)
			unselectedRelation := prepareTestRelationForStore(t, domain.RelationKey("unselectedConstraint"), int64(model.RelationFormat_object))
			unselectedRelation[bundle.RelationKeyRelationFormatObjectTypes] = domain.StringList([]string{unused})
			fx.store.AddObjects(t, spaceId, []spaceindex.TestObject{
				relation, unselectedRelation, prepareTestObjectTypeForStore(t, unused, nil),
			})

			addType := func(id string, recommended []string, linksToAnotherConstraint bool) {
				row := prepareTestObjectTypeForStore(t, id, recommended)
				fx.store.AddObjects(t, spaceId, []spaceindex.TestObject{row})
				details := map[domain.RelationKey]domain.Value{
					bundle.RelationKeyUniqueKey:      row[bundle.RelationKeyUniqueKey],
					bundle.RelationKeyResolvedLayout: domain.Int64(int64(model.ObjectType_objectType)),
				}
				if linksToAnotherConstraint {
					details[bundle.RelationKeyLastModifiedBy] = domain.String("original-editor-value")
				}
				object := setupObject(id, id, smartblock.SmartBlockTypeObjectType, details)
				// The existing processed-ID set must make cycles terminate. A
				// second acquisition is an unexpected original picker call.
				fx.picker.EXPECT().GetObject(context.Background(), id).Return(object, nil).Once()
			}
			addType(rootType, recommendations, false)
			if len(tc.second) != 0 {
				second := prepareTestRelationForStore(t, bundle.RelationKeyLastModifiedBy, int64(model.RelationFormat_object))
				second[bundle.RelationKeyRelationFormatObjectTypes] = domain.StringList(tc.second)
				fx.store.AddObjects(t, spaceId, []spaceindex.TestObject{second})
			}
			if tc.readFailure {
				fx.store.AddObjects(t, spaceId, []spaceindex.TestObject{prepareTestObjectTypeForStore(t, targetA, nil)})
				fx.picker.EXPECT().GetObject(context.Background(), targetA).Return(nil, targetReadFailure).Once()
			} else {
				for _, id := range tc.want {
					addType(id, nil, id == targetA && len(tc.second) != 0)
				}
				if len(tc.want) == 0 {
					// A present indexed type alone is not export authority.
					fx.store.AddObjects(t, spaceId, []spaceindex.TestObject{prepareTestObjectTypeForStore(t, targetA, nil)})
				}
			}
			exp := newExportContext(fx.export, pb.RpcObjectListExportRequest{
				SpaceId: spaceId, ObjectIds: []string{rootID}, Format: model.Export_Protobuf,
			})
			exp.docs[rootID] = &Doc{Details: root.NewState().CombinedDetails()}
			err := exp.addDerivedObjects()
			if tc.readFailure {
				require.ErrorIs(t, err, targetReadFailure)
				require.NotContains(t, exp.docs, targetA)
				return
			}
			require.NoError(t, err)
			for _, id := range tc.want {
				require.Contains(t, exp.docs, id)
			}
			require.NotContains(t, exp.docs, unused)
			if len(tc.want) == 0 {
				require.NotContains(t, exp.docs, targetA)
				require.NotContains(t, exp.docs, targetB)
			}
			actualTypes := make([]string, 0, len(exp.objectTypes))
			for id := range exp.objectTypes {
				actualTypes = append(actualTypes, id)
			}
			require.ElementsMatch(t, append([]string{rootType}, tc.want...), actualTypes)
			if tc.selected || tc.recommended {
				require.Contains(t, exp.docs, relationKey.String())
				actualConstraint := exp.docs[relationKey.String()].Details.GetStringList(bundle.RelationKeyRelationFormatObjectTypes)
				require.Len(t, actualConstraint, len(tc.targets))
				for i, expected := range tc.targets {
					require.Equal(t, expected, actualConstraint[i])
				}
			}
		})
	}
}
