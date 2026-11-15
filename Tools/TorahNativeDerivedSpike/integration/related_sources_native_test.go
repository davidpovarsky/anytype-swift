package heartprobe

import (
	"encoding/base64"
	"encoding/json"
	"reflect"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/clientlibrary/service"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
	"github.com/gogo/protobuf/jsonpb"
	"github.com/gogo/protobuf/proto"
)

func exerciseRelatedNativeRPC(t *testing.T, spaceID, manifestID, canonicalKey, customType string) {
	t.Helper()
	invoke := func(call func([]byte) []byte, request, response proto.Message) {
		t.Helper()
		data, err := proto.Marshal(request)
		if err != nil {
			t.Fatal(err)
		}
		if err = proto.Unmarshal(call(data), response); err != nil {
			t.Fatal(err)
		}
		field := reflect.ValueOf(response).Elem().FieldByName("Error")
		if field.IsValid() && !field.IsNil() && field.Elem().FieldByName("Code").Int() != 0 {
			t.Fatalf("%T failed: %v", request, response)
		}
	}
	identity := torah.Identity(torah.Ref, "sefaria", "Genesis 3:3", "")
	manifest := &pb.RpcObjectShowResponse{}
	invoke(service.ObjectShow, &pb.RpcObjectShowRequest{SpaceId: spaceID, ObjectId: manifestID, ContextId: manifestID}, manifest)
	capable := false
	for _, entry := range manifest.ObjectView.Details {
		if entry.Id == manifestID {
			d := domain.NewDetailsFromProto(entry.Details)
			capable = d.GetString(bundle.RelationKeySpaceId) == spaceID && d.GetInt64(torah.VersionKey) == 1 && d.GetInt64(torah.RelatedVersionKey) == 1
		}
	}
	if !capable {
		t.Fatal("actual selected manifest does not advertise independent private capability")
	}
	ids := []string{}
	raws := map[string]string{}
	customTypeID := ""
	for n, typeKey := range []string{"ot-page", "ot-note", customType} {
		created := &pb.RpcObjectCreateResponse{}
		invoke(service.ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: spaceID, ObjectTypeUniqueKey: typeKey, Details: domain.NewDetails().SetString(bundle.RelationKeyName, "T5 real native explicit link").ToProto()}, created)
		ids = append(ids, created.ObjectId)
		record := map[string]any{"spaceId": spaceID, "objectId": created.ObjectId, "item": map[string]string{"id": "source", "kind": "ref", "role": "context", "providerID": "sefaria", "canonicalKey": "Genesis 3:3", "externalID": "Genesis 3:3", "labelHe": "source"}}
		if n > 0 {
			block := &pb.RpcBlockCreateResponse{}
			invoke(service.BlockCreate, &pb.RpcBlockCreateRequest{ContextId: created.ObjectId, TargetId: created.ObjectId, Position: model.Block_Inner, Block: &model.Block{Content: &model.BlockContentOfText{Text: &model.BlockContentText{Text: "T5 authorized block sentinel"}}}}, block)
			if block.BlockId == "" {
				t.Fatal("native BlockCreate returned no real block ID")
			}
			record["blockId"] = block.BlockId
			if n == 2 {
				record["item"].(map[string]string)["role"] = "sourceQuote"
			}
		}
		raw, _ := json.Marshal(map[string]any{"version": 2, "records": []any{record}, "sentinel": "preserve"})
		raws[created.ObjectId] = string(raw)
		invoke(service.ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: created.ObjectId, Details: []*model.Detail{{Key: canonicalKey, Value: domain.String(string(raw)).ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
		shown := &pb.RpcObjectShowResponse{}
		invoke(service.ObjectShow, &pb.RpcObjectShowRequest{SpaceId: spaceID, ObjectId: created.ObjectId, ContextId: created.ObjectId}, shown)
		found := false
		for _, entry := range shown.ObjectView.Details {
			if entry.Id == created.ObjectId {
				d := domain.NewDetailsFromProto(entry.Details)
				if n == 2 {
					customTypeID = d.GetString(bundle.RelationKeyType)
				}
				found = d.GetInt64(torah.RelatedVersionKey) == 1 && d.GetString(domain.RelationKey(canonicalKey)) == string(raw)
			}
		}
		if !found {
			t.Fatal("real ObjectShow lacks private capability or changed canonical payload")
		}
	}
	if customTypeID == "" {
		t.Fatal("real custom document omitted actual Type ID")
	}
	reject := func(call func([]byte) []byte, request, response proto.Message) {
		t.Helper()
		data, err := proto.Marshal(request)
		if err != nil {
			t.Fatal(err)
		}
		if err = proto.Unmarshal(call(data), response); err != nil {
			t.Fatal(err)
		}
		value := reflect.ValueOf(response).Elem()
		failure := value.FieldByName("Error")
		if !failure.IsValid() || failure.IsNil() || failure.Elem().FieldByName("Code").Int() == 0 {
			t.Fatalf("private metadata API unexpectedly succeeded: %T", request)
		}
		if id := value.FieldByName("ObjectId"); id.IsValid() && id.String() != "" {
			t.Fatalf("rejected private metadata request created object: %T", request)
		}
		if id := value.FieldByName("PropertyId"); id.IsValid() && id.String() != "" {
			t.Fatalf("rejected private metadata request installed Property: %T", request)
		}
	}
	typeBefore := &pb.RpcObjectShowResponse{}
	invoke(service.ObjectShow, &pb.RpcObjectShowRequest{SpaceId: spaceID, ObjectId: customTypeID, ContextId: customTypeID}, typeBefore)
	for _, key := range []string{torah.RelatedSourcesKey, torah.RelatedVersionKey} {
		details := domain.NewDetails().SetString(bundle.RelationKeyName, "T5 private leak sentinel").SetString(bundle.RelationKeyRelationKey, key)
		reject(service.ObjectCreateRelationOption, &pb.RpcObjectCreateRelationOptionRequest{SpaceId: spaceID, Details: details.ToProto()}, &pb.RpcObjectCreateRelationOptionResponse{})
		reject(service.ObjectCreateRelation, &pb.RpcObjectCreateRelationRequest{SpaceId: spaceID, Details: details.Copy().SetInt64(bundle.RelationKeyRelationFormat, 11).ToProto()}, &pb.RpcObjectCreateRelationResponse{})
		reject(service.ObjectRelationAdd, &pb.RpcObjectRelationAddRequest{ContextId: ids[0], RelationKeys: []string{key}}, &pb.RpcObjectRelationAddResponse{})
		reject(service.ObjectTypePropertyAdd, &pb.RpcObjectTypePropertyAddRequest{ObjectTypeId: customTypeID, Key: key, Section: pb.RpcObjectTypePropertyAddRequest_Recommended, EnableInViews: true}, &pb.RpcObjectTypePropertyAddResponse{})
	}
	typeAfter := &pb.RpcObjectShowResponse{}
	invoke(service.ObjectShow, &pb.RpcObjectShowRequest{SpaceId: spaceID, ObjectId: customTypeID, ContextId: customTypeID}, typeAfter)
	typeProperties := func(view *pb.RpcObjectShowResponse) *domain.Details {
		for _, entry := range view.ObjectView.Details {
			if entry.Id == customTypeID {
				return domain.NewDetailsFromProto(entry.Details).CopyOnlyKeys(bundle.RelationKeyRecommendedRelations, bundle.RelationKeyRecommendedFeaturedRelations, bundle.RelationKeyRecommendedHiddenRelations)
			}
		}
		t.Fatal("Type ObjectShow omitted metadata")
		return nil
	}
	if !typeProperties(typeBefore).Equal(typeProperties(typeAfter)) {
		t.Fatal("private rejection changed Type Property attachments")
	}
	leaked := &pb.RpcObjectSearchResponse{}
	invoke(service.ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: spaceID, Filters: []*model.BlockContentDataviewFilter{{RelationKey: "name", Condition: model.BlockContentDataviewFilter_Equal, Value: domain.String("T5 private leak sentinel").ToProto()}}, Keys: []string{"id"}, NeedTotal: true, Limit: 10}, leaked)
	if len(leaked.Records) != 0 {
		t.Fatal("private API rejection left a created option/Property sentinel object")
	}
	t.Log("PASS T5 actual native private option/Property creation and object/Type attachment rejection; no returned object/Property IDs or sentinel objects")
	filter := &model.BlockContentDataviewFilter{RelationKey: torah.RelatedSourcesKey, Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList([]string{identity}).ToProto()}
	deadline := time.Now().Add(45 * time.Second)
	for {
		response := &pb.RpcObjectSearchResponse{}
		invoke(service.ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: spaceID, Filters: []*model.BlockContentDataviewFilter{filter}, Keys: []string{"id", torah.RelatedVersionKey, torah.ReadyKey}, Limit: 50}, response)
		got := map[string]bool{}
		for _, record := range response.Records {
			d := domain.NewDetailsFromProto(record)
			if !d.GetBool(torah.ReadyKey) || d.GetInt64(torah.RelatedVersionKey) != 1 {
				t.Fatal("native private filter omitted readiness/version guard")
			}
			got[d.GetString(bundle.RelationKeyId)] = true
		}
		if len(got) == len(ids) {
			for _, id := range ids {
				if !got[id] {
					t.Fatalf("private candidate union omitted native object %s", id)
				}
			}
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("real private ObjectSearch timeout: got%d want%d", len(got), len(ids))
		}
		time.Sleep(100 * time.Millisecond)
	}
	public := &pb.RpcObjectSearchResponse{}
	invoke(service.ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: spaceID, Filters: []*model.BlockContentDataviewFilter{{RelationKey: torah.SourcesKey, Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList([]string{identity}).ToProto()}}, Keys: []string{"id"}}, public)
	if len(public.Records) != 1 || domain.NewDetailsFromProto(public.Records[0]).GetString(bundle.RelationKeyId) != ids[0] {
		t.Fatal("private candidate expansion changed public Property membership")
	}
	for _, id := range ids {
		for _, format := range []model.ExportFormat{model.Export_Protobuf, model.Export_JSON} {
			exported := &pb.RpcObjectExportResponse{}
			invoke(service.ObjectExport, &pb.RpcObjectExportRequest{SpaceId: spaceID, ObjectId: id, Format: format}, exported)
			snapshot := &pb.SnapshotWithType{}
			if format == model.Export_Protobuf {
				data, err := base64.StdEncoding.DecodeString(exported.Result)
				if err != nil {
					t.Fatal(err)
				}
				if err = proto.Unmarshal(data, snapshot); err != nil {
					t.Fatal(err)
				}
			} else if err := jsonpb.UnmarshalString(exported.Result, snapshot); err != nil {
				t.Fatal(err)
			}
			d := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
			if d.Has(torah.RelatedSourcesKey) || d.Has(torah.RelatedVersionKey) || d.GetString(domain.RelationKey(canonicalKey)) != raws[id] {
				t.Fatal("real native export leaked private fields or changed canonical bytes")
			}
		}
	}
	t.Log("PASS T5 real native ObjectCreate/BlockCreate/ObjectSetDetails/ObjectShow/private ObjectSearch and public-membership/export separation; not block UI navigation or compatibility-pair acceptance")
}
