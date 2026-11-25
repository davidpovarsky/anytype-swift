//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance

package application

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/gogo/protobuf/jsonpb"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"

	nativeexport "github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// Compare the derived view against each actual captured native protobuf and its
// private bundle members. No live resolver or source authority is substituted.
func loadedSnapshotJSONViews(t *testing.T, captured *LoadedAccountSpaceWitness) int {
	t.Helper()
	require.NotNil(t, captured)
	manifestRaw, err := os.ReadFile(filepath.Join(captured.PrivateBundleDirectory(), "manifest.json"))
	require.NoError(t, err)
	var manifest NativeSourceBundleManifest
	require.NoError(t, json.Unmarshal(manifestRaw, &manifest))
	members := map[string]NativeSourceObjectMember{}
	for _, member := range manifest.Objects {
		_, exists := members[member.ObjectID]
		require.False(t, exists)
		members[member.ObjectID] = member
	}
	objects := captured.Objects()
	require.NotEmpty(t, objects)
	require.Len(t, members, len(objects))
	for _, object := range objects {
		raw := object.SnapshotBase()
		before := append([]byte(nil), raw...)
		view, err := object.JSONView()
		require.NoError(t, err)
		again, err := object.JSONView()
		require.NoError(t, err)
		require.Equal(t, view, again, "native JSON view must be deterministic")
		require.Equal(t, before, object.SnapshotBase())
		var envelope nativeexport.NativeSnapshotJSONView
		require.NoError(t, json.Unmarshal(view, &envelope))
		require.Equal(t, "pinkha-native-snapshot-json-v1", envelope.Contract)
		require.Equal(t, object.ObjectID(), envelope.ObjectID)
		require.NotEmpty(t, envelope.SpaceID)
		require.Equal(t, int32(object.Type()), envelope.NativeType)
		require.Equal(t, object.UniqueKey(), envelope.UniqueKey)
		require.Equal(t, loadedFixtureHash(raw), envelope.SnapshotSHA256)
		require.Equal(t, len(raw), envelope.SnapshotBytes)
		original, derived := new(model.SmartBlockSnapshotBase), new(model.SmartBlockSnapshotBase)
		require.NoError(t, proto.Unmarshal(raw, original))
		require.NoError(t, jsonpb.Unmarshal(bytes.NewReader(envelope.Snapshot), derived))
		require.True(t, proto.Equal(original, derived), "all native known snapshot fields must survive JSON view")
		member, exists := members[object.ObjectID()]
		require.True(t, exists)
		for _, entry := range []NativeSourceMember{member.Snapshot, member.NativeJSONView} {
			require.Equal(t, filepath.Base(entry.Path), entry.Path)
			data, err := os.ReadFile(filepath.Join(captured.PrivateBundleDirectory(), entry.Path))
			require.NoError(t, err)
			require.Equal(t, int64(len(data)), entry.Bytes)
			require.Equal(t, loadedFixtureHash(data), entry.SHA256)
		}
		viewMember, err := os.ReadFile(filepath.Join(captured.PrivateBundleDirectory(), member.NativeJSONView.Path))
		require.NoError(t, err)
		require.Equal(t, view, viewMember)
		snapshotMember, err := os.ReadFile(filepath.Join(captured.PrivateBundleDirectory(), member.Snapshot.Path))
		require.NoError(t, err)
		require.Equal(t, raw, snapshotMember)
	}
	return len(objects)
}

func TestLoadedAccountNativeSnapshotJSONView(t *testing.T) {
	f := newLoadedAccountFixture(t)
	pageID := loadedObjectFixturePage(t, f, "צילום מקור — עברית, 123, והפניה", false)
	fileObjectID, _ := loadedSpaceFixtureFile(t, f, bytes.Repeat([]byte("json-view-file"), 500))
	loadedSpaceFixtureWarm(t, f)
	captured, err := f.service.CaptureLoadedAccountSpaceWitness(f.ctx, f.token, loadedSpaceRequest(f))
	require.NoError(t, err)
	count := loadedSnapshotJSONViews(t, captured)
	require.GreaterOrEqual(t, count, 2)
	seen := map[string]bool{}
	var textPair map[string]any
	for _, object := range captured.Objects() {
		seen[object.ObjectID()] = true
		if object.ObjectID() == pageID {
			original := object.SnapshotBase()
			snapshot := new(model.SmartBlockSnapshotBase)
			require.NoError(t, proto.Unmarshal(original, snapshot))
			require.Nil(t, snapshot.FileInfo)
			require.Nil(t, snapshot.FileKeys)
			view, err := object.JSONView()
			require.NoError(t, err)
			pbName, jsonName := "native-json-consumer-text.pb", "native-json-consumer-text.json"
			loadedFixtureWrite(t, filepath.Join(f.dir, pbName), original)
			require.NoError(t, os.Chmod(filepath.Join(f.dir, pbName), 0400))
			loadedFixtureWrite(t, filepath.Join(f.dir, jsonName), view)
			require.NoError(t, os.Chmod(filepath.Join(f.dir, jsonName), 0400))
			textPair = map[string]any{
				"objectID": object.ObjectID(), "protobufPath": pbName, "jsonPath": jsonName,
				"protobufSHA256": loadedFixtureHash(original), "protobufBytes": len(original),
				"jsonSHA256": loadedFixtureHash(view), "jsonBytes": len(view),
				"nativeCreatedTextOnly": true, "fileInfoAbsent": true, "fileKeysAbsent": true,
			}
		}
	}
	require.True(t, seen[pageID])
	require.True(t, seen[fileObjectID])
	var absent *nativeexport.NativeRawObject
	view, err := absent.JSONView()
	require.Error(t, err)
	require.Nil(t, view)
	receipt, err := captured.Receipt()
	require.NoError(t, err)
	require.False(t, receipt.SemanticCompleteness)
	require.False(t, receipt.HasNativeSourceAdmission)
	require.False(t, receipt.PermitsDestinationWrites)
	f.privateNote(t, "native-snapshot-json-view", map[string]any{
		"contract": "pinkha-native-snapshot-json-v1", "capturedObjects": count,
		"actualNativeProtoRoundTrips": count, "deterministicViews": count,
		"originalPBMembersVerified": count, "privateJSONMembersVerified": count,
		"rawSnapshotUnchanged": true, "sourceReceipt": receipt, "privateConsumerTextPair": textPair,
	})
	t.Logf("NATIVE_SNAPSHOT_JSON_VIEW_OBSERVATION original_pb_verified=%d known_native_fields_roundtrip=PASS deterministic=PASS", count)
}
