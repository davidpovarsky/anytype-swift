package export

import (
	"context"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block/editor/template"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// This exercises the existing state walker, original dataview template and
// indexed unique-key relation lookup. The source field is not a detail key;
// dropping the object-type layout from the collector loses its real document.
func TestOtzariaObjectTypeDataviewExportClosure(t *testing.T) {
	for _, tc := range []struct {
		name     string
		layout   model.ObjectTypeLayout
		included bool
	}{
		{"object_type_original_hidden_column", model.ObjectType_objectType, true},
		{"plain_page_does_not_gain_type_closure", model.ObjectType_basic, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			fx := newFixture(t)
			const id = "original-type-control"
			object := setupObject(id, "original-type-key", smartblock.SmartBlockTypeObjectType,
				map[domain.RelationKey]domain.Value{
					bundle.RelationKeyResolvedLayout: domain.Int64(int64(tc.layout)),
				})
			require.False(t, object.NewState().CombinedDetails().Has(bundle.RelationKeyLastOpenedDate))
			object.AddBlock(simple.New(&model.Block{
				Id: id, ChildrenIds: []string{"dataview"},
				Content: &model.BlockContentOfSmartblock{Smartblock: &model.BlockContentSmartblock{}},
			}))
			object.AddBlock(simple.New(&model.Block{
				Id: "dataview", Content: template.MakeDataviewContent(false, nil, nil, nil),
			}))
			fx.picker.EXPECT().GetObject(context.Background(), id).Return(object, nil)
			fx.store.AddObjects(t, spaceId, []spaceindex.TestObject{
				prepareTestRelationForStore(t, bundle.RelationKeyLastOpenedDate, int64(model.RelationFormat_date)),
			})
			exp := newExportContext(fx.export, pb.RpcObjectListExportRequest{
				SpaceId: spaceId, ObjectIds: []string{id}, Format: model.Export_Protobuf,
			})
			require.NoError(t, exp.collectDerivedObjects(map[string]*Doc{id: nil}))
			keys := make([]string, 0, len(exp.relations))
			for key := range exp.relations {
				keys = append(keys, key)
			}
			require.NoError(t, exp.addRelations(keys))
			_, collected := exp.docs[bundle.RelationKeyLastOpenedDate.String()]
			require.Equal(t, tc.included, collected)
			require.NotContains(t, exp.docs, "unrelated-relation")
		})
	}
}
