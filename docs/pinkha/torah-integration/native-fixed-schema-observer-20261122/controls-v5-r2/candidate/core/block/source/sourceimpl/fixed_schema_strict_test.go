package sourceimpl_test

import (
	"errors"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/gogo/protobuf/proto"
	"github.com/gogo/protobuf/types"
	"github.com/golang/snappy"

	"github.com/anyproto/anytype-heart/core/block/source/sourceimpl"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

func TestOtzariaFixedSchemaStrictReplayV5(t *testing.T) {
	malformed := func() *types.Struct {
		return &types.Struct{Fields: map[string]*types.Value{"invalid": {}}}
	}
	snapshot := func(id string, fields *types.Struct) *pb.Change {
		return &pb.Change{Snapshot: &pb.ChangeSnapshot{Data: &model.SmartBlockSnapshotBase{
			Blocks: []*model.Block{{Id: id, Fields: fields}},
		}}}
	}
	create := func(id string, fields *types.Struct) *pb.Change {
		return &pb.Change{Content: []*pb.ChangeContent{{
			Value: &pb.ChangeContentValueOfBlockCreate{BlockCreate: &pb.ChangeBlockCreate{
				Blocks: []*model.Block{{Id: id, Fields: fields}},
			}},
		}}}
	}
	setFields := func(fields *types.Struct) *pb.Change {
		return &pb.Change{Content: []*pb.ChangeContent{{
			Value: &pb.ChangeContentValueOfBlockUpdate{BlockUpdate: &pb.ChangeBlockUpdate{
				Events: []*pb.EventMessage{{Value: &pb.EventMessageValueOfBlockSetFields{BlockSetFields: &pb.EventBlockSetFields{
					Id: "original-fixture-block", Fields: fields,
				}}}},
			}},
		}}}
	}
	encode := func(t *testing.T, change *pb.Change) []byte {
		t.Helper()
		data, err := proto.Marshal(change)
		if err != nil {
			t.Fatalf("original protobuf encoding: %v", err)
		}
		return data
	}
	reject := func(t *testing.T, change *pb.Change) {
		t.Helper()
		if _, err := sourceimpl.UnmarshalChangeStrict(&objecttree.Change{}, encode(t, change)); err == nil {
			t.Fatal("strict original decoder admitted malformed original protobuf metadata")
		}
	}
	accept := func(t *testing.T, change *pb.Change) *pb.Change {
		t.Helper()
		result, err := sourceimpl.UnmarshalChangeStrict(&objecttree.Change{}, encode(t, change))
		if err != nil {
			t.Fatalf("strict original decoder refused supported metadata: %v", err)
		}
		got, ok := result.(*pb.Change)
		if !ok {
			t.Fatal("original decoder returned another model")
		}
		if !proto.Equal(got, change) {
			t.Fatal("original decoded protobuf changed the intended field/reset values")
		}
		return got
	}

	t.Run("UnknownDataTypeStrictOnlyRefusal", func(t *testing.T) {
		data := encode(t, &pb.Change{})
		change := &objecttree.Change{DataType: "unsupported-fixture-tag"}
		if _, err := sourceimpl.UnmarshalChangeStrict(change, data); err == nil {
			t.Fatal("unknown strict tag accepted")
		}
		if _, err := sourceimpl.UnmarshalChange(change, data); err != nil {
			t.Fatalf("ordinary original behavior changed: %v", err)
		}
	})

	t.Run("OriginalPlainAndSnappyTagsAccepted", func(t *testing.T) {
		data := encode(t, &pb.Change{})
		if _, err := sourceimpl.UnmarshalChangeStrict(&objecttree.Change{}, data); err != nil {
			t.Fatal(err)
		}
		if _, err := sourceimpl.UnmarshalChangeStrict(&objecttree.Change{DataType: "1/s"}, snappy.Encode(nil, data)); err != nil {
			t.Fatal(err)
		}
	})

	t.Run("InvalidNativeSnappyErrorPropagated", func(t *testing.T) {
		// This is valid original protobuf, while the actual original Snappy
		// length decoder rejects it. The ordinary path must still decode it,
		// isolating compression propagation from an unrelated protobuf error.
		wanted := &pb.Change{}
		data := encode(t, wanted)
		_, nativeCompressionError := snappy.DecodedLen(data)
		if nativeCompressionError == nil {
			t.Fatal("fixture is not an actual original Snappy length failure")
		}
		ordinary, err := sourceimpl.UnmarshalChange(&objecttree.Change{DataType: "1/s"}, data)
		if err != nil {
			t.Fatalf("ordinary original protobuf fallback failed: %v", err)
		}
		got, ok := ordinary.(*pb.Change)
		if !ok || !proto.Equal(got, wanted) {
			t.Fatal("ordinary path did not preserve the actual valid protobuf input")
		}
		_, err = sourceimpl.UnmarshalChangeStrict(&objecttree.Change{DataType: "1/s"}, data)
		if !errors.Is(err, nativeCompressionError) {
			t.Fatalf("strict path lost the actual original compression cause: %v", err)
		}
	})

	t.Run("SnapshotBlockFieldsRefusedBeforeReplay", func(t *testing.T) { reject(t, snapshot("original-fixture-block", malformed())) })
	t.Run("CreatedBlockFieldsRefusedBeforeReplay", func(t *testing.T) { reject(t, create("original-fixture-block", malformed())) })
	t.Run("BlockSetFieldsEventRefusedBeforeReplay", func(t *testing.T) { reject(t, setFields(malformed())) })
	t.Run("NilSnapshotFieldsPreserved", func(t *testing.T) {
		got := accept(t, snapshot("original-fixture-block", nil))
		if got.Snapshot.Data.Blocks[0].Fields != nil {
			t.Fatal("nil snapshot Fields was replaced")
		}
	})
	t.Run("NilCreatedFieldsPreserved", func(t *testing.T) {
		got := accept(t, create("original-fixture-block", nil))
		if got.Content[0].GetBlockCreate().Blocks[0].Fields != nil {
			t.Fatal("nil created Fields was replaced")
		}
	})
	t.Run("NilFieldsResetEventPreserved", func(t *testing.T) {
		got := accept(t, setFields(nil))
		if got.Content[0].GetBlockUpdate().Events[0].GetBlockSetFields().Fields != nil {
			t.Fatal("nil reset Fields was replaced")
		}
	})
	t.Run("EmptySnapshotIDCannotBeSynthesized", func(t *testing.T) { reject(t, snapshot("", nil)) })
	t.Run("EmptyCreatedIDCannotBeSynthesized", func(t *testing.T) { reject(t, create("", nil)) })
	t.Run("MissingOriginalEventRefused", func(t *testing.T) {
		reject(t, &pb.Change{Content: []*pb.ChangeContent{{
			Value: &pb.ChangeContentValueOfBlockUpdate{BlockUpdate: &pb.ChangeBlockUpdate{Events: []*pb.EventMessage{{}}}},
		}}})
	})
}
