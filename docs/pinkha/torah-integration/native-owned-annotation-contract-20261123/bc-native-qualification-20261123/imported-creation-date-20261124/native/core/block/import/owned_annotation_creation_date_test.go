package importer

import (
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/proto"
	"github.com/ipfs/go-cid"
	"github.com/stretchr/testify/require"
	"testing"
)

func originalAddedDatePayload(t *testing.T, space string, timestamp int64) *treechangeproto.RawTreeChangeWithId {
	t.Helper()
	root, err := (&treechangeproto.RootChange{SpaceId: space, Timestamp: timestamp}).MarshalVT()
	require.NoError(t, err)
	raw, err := (&treechangeproto.RawTreeChange{Payload: root}).MarshalVT()
	require.NoError(t, err)
	id, err := (cid.Prefix{Version: 1, Codec: cid.DagCBOR, MhType: 0x12, MhLength: -1}).Sum(raw)
	require.NoError(t, err)
	return &treechangeproto.RawTreeChangeWithId{Id: id.String(), RawChange: raw}
}

func TestOtzariaOriginalImportedCreationDate(t *testing.T) {
	t.Run("assigned_header_timestamp_seconds", func(t *testing.T) {
		payload := originalAddedDatePayload(t, "target-space", 1795533751)
		before := append([]byte(nil), payload.RawChange...)
		details := domain.NewDetailsFromMap(map[domain.RelationKey]domain.Value{bundle.RelationKeyCreatedDate: domain.Int64(1600000000), bundle.RelationKeyName: domain.String("Original body")})
		require.NoError(t, expectedOriginalImportedAddedDate(details, payload, payload.Id, "target-space"))
		require.EqualValues(t, 1795533751, details.GetInt64(bundle.RelationKeyAddedDate))
		require.EqualValues(t, 1600000000, details.GetInt64(bundle.RelationKeyCreatedDate))
		require.Equal(t, "Original body", details.GetString(bundle.RelationKeyName))
		require.Equal(t, before, payload.RawChange)
	})
	t.Run("source_supplied_added_date_preserved", func(t *testing.T) {
		payload := originalAddedDatePayload(t, "target-space", 1795533751)
		details := domain.NewDetailsFromMap(map[domain.RelationKey]domain.Value{bundle.RelationKeyAddedDate: domain.Int64(1500000000)})
		before := proto.Clone(details.ToProto())
		require.NoError(t, expectedOriginalImportedAddedDate(details, payload, payload.Id, "target-space"))
		require.True(t, proto.Equal(before, details.ToProto()))
	})
	t.Run("changed_added_date_still_refused_by_full_comparison", func(t *testing.T) {
		payload := originalAddedDatePayload(t, "target-space", 1795533751)
		details := domain.NewDetails()
		require.NoError(t, expectedOriginalImportedAddedDate(details, payload, payload.Id, "target-space"))
		left := &pb.SnapshotWithType{SbType: coresb.SmartBlockTypePage.ToProto(), Snapshot: &pb.ChangeSnapshot{Data: &model.SmartBlockSnapshotBase{Details: details.ToProto(), Blocks: []*model.Block{{Id: payload.Id, Content: &model.BlockContentOfSmartblock{Smartblock: &model.BlockContentSmartblock{}}}}}}}
		right := proto.Clone(left).(*pb.SnapshotWithType)
		changed := domain.NewDetailsFromProto(right.Snapshot.Data.Details)
		changed.SetInt64(bundle.RelationKeyAddedDate, 1795533752)
		right.Snapshot.Data.Details = changed.ToProto()
		l, err := canonicalOwnedAnnotationSnapshot(left)
		require.NoError(t, err)
		r, err := canonicalOwnedAnnotationSnapshot(right)
		require.NoError(t, err)
		require.False(t, proto.Equal(l, r), "addedDate is compared, never stripped or copied from readback")
	})
	t.Run("wrong_assigned_payload_identity_refused", func(t *testing.T) {
		payload := originalAddedDatePayload(t, "target-space", 1795533751)
		other := originalAddedDatePayload(t, "target-space", 1795533752)
		details := domain.NewDetails()
		require.EqualError(t, expectedOriginalImportedAddedDate(details, payload, other.Id, "target-space"), "owned annotation import refused: expected_original_creation_header")
		payload.Id = other.Id
		require.EqualError(t, expectedOriginalImportedAddedDate(details, payload, other.Id, "target-space"), "owned annotation import refused: expected_original_creation_header")
		require.False(t, details.Has(bundle.RelationKeyAddedDate))
	})
	t.Run("missing_or_malformed_header_refused", func(t *testing.T) {
		details := domain.NewDetails()
		require.EqualError(t, expectedOriginalImportedAddedDate(details, nil, "target", "target-space"), "owned annotation import refused: expected_original_creation_header")
		invalid := []byte{0xff}
		id, err := (cid.Prefix{Version: 1, Codec: cid.DagCBOR, MhType: 0x12, MhLength: -1}).Sum(invalid)
		require.NoError(t, err)
		payload := &treechangeproto.RawTreeChangeWithId{Id: id.String(), RawChange: invalid}
		require.EqualError(t, expectedOriginalImportedAddedDate(details, payload, payload.Id, "target-space"), "owned annotation import refused: expected_original_creation_header")
		require.False(t, details.Has(bundle.RelationKeyAddedDate))
	})
	t.Run("wrong_space_or_nonpositive_timestamp_refused", func(t *testing.T) {
		for _, tc := range []struct {
			space     string
			timestamp int64
		}{{"wrong-space", 1795533751}, {"target-space", 0}, {"target-space", -1}} {
			payload := originalAddedDatePayload(t, tc.space, tc.timestamp)
			details := domain.NewDetails()
			require.EqualError(t, expectedOriginalImportedAddedDate(details, payload, payload.Id, "target-space"), "owned annotation import refused: expected_original_creation_header")
			require.False(t, details.Has(bundle.RelationKeyAddedDate))
		}
	})
}
