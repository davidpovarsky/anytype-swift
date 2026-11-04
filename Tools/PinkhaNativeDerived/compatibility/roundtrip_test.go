package compatibility

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/clientlibrary/service"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/jsonpb"
	"github.com/gogo/protobuf/proto"
)

// The same test compiles against an untouched pinned Heart and the modified
// Heart. It deliberately imports no Pinkha module or custom implementation.
// Input snapshots must be exports produced by the real product API fixture.
func TestActualExportImportRoundTrip(t *testing.T) {
	input := os.Getenv("PINKHA_COMPATIBILITY_INPUT")
	if input == "" {
		t.Skip("real native export fixture directory required")
	}
	var contract struct {
		CanonicalRaw string `json:"canonicalRaw"`
		DocumentName string `json:"documentName"`
	}
	data, err := os.ReadFile(filepath.Join(input, "contract.json"))
	if err != nil {
		t.Fatal(err)
	}
	if err = json.Unmarshal(data, &contract); err != nil {
		t.Fatal(err)
	}
	if contract.CanonicalRaw == "" || contract.DocumentName == "" {
		t.Fatal("incomplete real-export contract")
	}
	makeInvoker := func(t *testing.T) func(func([]byte) []byte, proto.Message, proto.Message) {
		return func(call func([]byte) []byte, req, resp proto.Message) {
			t.Helper()
			data, err := proto.Marshal(req)
			if err != nil {
				t.Fatal(err)
			}
			if err = proto.Unmarshal(call(data), resp); err != nil {
				t.Fatal(err)
			}
			field := reflect.ValueOf(resp).Elem().FieldByName("Error")
			if field.IsValid() && !field.IsNil() && field.Elem().FieldByName("Code").Int() != 0 {
				t.Fatalf("%T error %d: %s", req, field.Elem().FieldByName("Code").Int(), field.Elem().FieldByName("Description").String())
			}
		}
	}
	invoke := makeInvoker(t)
	service.SetEventHandler(func(*pb.Event) {})
	root := t.TempDir()
	invoke(service.InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root, DoNotSendLogs: true, DoNotSaveLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	// The mnemonic stays solely in the process and its disposable temporary root.
	invoke(service.WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, &pb.RpcWalletCreateResponse{})
	invoke(service.AccountCreate, &pb.RpcAccountCreateRequest{Name: "Disposable export compatibility", NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true}, &pb.RpcAccountCreateResponse{})
	t.Cleanup(func() { invoke(service.AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{}) })
	for _, format := range []string{"pbc", "json"} {
		t.Run(format, func(t *testing.T) {
			invoke := makeInvoker(t)
			space := &pb.RpcWorkspaceCreateResponse{}
			invoke(service.WorkspaceCreate, &pb.RpcWorkspaceCreateRequest{Details: domain.NewDetails().SetString(bundle.RelationKeyName, "Disposable imported "+format).ToProto()}, space)
			invoke(service.WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: space.SpaceId}, &pb.RpcWorkspaceOpenResponse{})
			imported := &pb.RpcObjectImportResponse{}
			invoke(service.ObjectImport, &pb.RpcObjectImportRequest{SpaceId: space.SpaceId, Type: model.Import_Pb, Mode: pb.RpcObjectImportRequest_ALL_OR_NOTHING, NoProgress: true,
				Params: &pb.RpcObjectImportRequestParamsOfPbParams{PbParams: &pb.RpcObjectImportRequestPbParams{Path: []string{filepath.Join(input, format)}, NoCollection: true}}}, imported)
			// The original RPC dispatches asynchronous import and returns an empty
			// response. Verify the actual imported Object through search/readback.
			var id string
			deadline := time.Now().Add(45 * time.Second)
			for time.Now().Before(deadline) {
				found := &pb.RpcObjectSearchResponse{}
				invoke(service.ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: space.SpaceId, Filters: []*model.BlockContentDataviewFilter{{RelationKey: "name", Condition: model.BlockContentDataviewFilter_Equal, Value: domain.String(contract.DocumentName).ToProto()}}, Keys: []string{"id"}}, found)
				if len(found.Records) == 1 {
					id = domain.NewDetailsFromProto(found.Records[0]).GetString(bundle.RelationKeyId)
					break
				}
				time.Sleep(100 * time.Millisecond)
			}
			if id == "" {
				t.Fatal("imported document missing from real native search")
			}
			show := func() *domain.Details {
				response := &pb.RpcObjectShowResponse{}
				invoke(service.ObjectShow, &pb.RpcObjectShowRequest{SpaceId: space.SpaceId, ContextId: id, ObjectId: id}, response)
				for _, row := range response.ObjectView.Details {
					if row.Id == id {
						return domain.NewDetailsFromProto(row.Details)
					}
				}
				t.Fatal("native ObjectShow omitted imported Object")
				return nil
			}
			canonicalKey := func(details *domain.Details) string {
				for key, value := range details.Iterate() {
					if value.String() == contract.CanonicalRaw && os.Getenv("PINKHA_COMPATIBILITY_EXPECT_NATIVE") != "1" {
						return string(key)
					}
					if os.Getenv("PINKHA_COMPATIBILITY_EXPECT_NATIVE") == "1" && importedCanonicalEquivalent(contract.CanonicalRaw, value.String(), space.SpaceId, id) {
						return string(key)
					}
				}
				t.Fatal("native import/export lost canonical identities or changed fields outside destination context IDs")
				return ""
			}
			details := show()
			key := canonicalKey(details)
			// An ordinary native edit must coexist with the opaque canonical payload.
			invoke(service.ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: id, Details: []*model.Detail{{Key: "name", Value: domain.String("Unmodified client ordinary edit").ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
			if canonicalKey(show()) != key {
				t.Fatal("ordinary native edit changed canonical property identity")
			}
			for _, kind := range []model.ExportFormat{model.Export_Protobuf, model.Export_JSON} {
				response := &pb.RpcObjectExportResponse{}
				invoke(service.ObjectExport, &pb.RpcObjectExportRequest{SpaceId: space.SpaceId, ObjectId: id, Format: kind}, response)
				snapshot := &pb.SnapshotWithType{}
				if kind == model.Export_Protobuf {
					raw, err := base64.StdEncoding.DecodeString(response.Result)
					if err != nil {
						t.Fatal(err)
					}
					if err = proto.Unmarshal(raw, snapshot); err != nil {
						t.Fatal(err)
					}
				} else if err = jsonpb.UnmarshalString(response.Result, snapshot); err != nil {
					t.Fatal(err)
				}
				canonicalKey(domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details))
			}
			if os.Getenv("PINKHA_COMPATIBILITY_EXPECT_NATIVE") == "1" {
				details = show()
				if !details.GetBool("_pinkhaTorahReady") || len(details.GetStringList("pinkhaTorahSources")) != 1 || len(details.GetStringList("pinkhaTorahTopics")) != 1 || len(details.GetStringList("pinkhaTorahWords")) != 1 {
					t.Fatal("canonical bytes survived import but native query projection did not recover in the destination Space")
				}
				for _, relation := range []string{"pinkhaTorahSources", "pinkhaTorahTopics", "pinkhaTorahWords"} {
					found := &pb.RpcObjectSearchResponse{}
					invoke(service.ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: space.SpaceId, Filters: []*model.BlockContentDataviewFilter{{RelationKey: relation, Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList(details.GetStringList(domain.RelationKey(relation))).ToProto()}}, Keys: []string{"id"}}, found)
					if len(found.Records) != 1 || domain.NewDetailsFromProto(found.Records[0]).GetString(bundle.RelationKeyId) != id {
						t.Fatalf("imported %s membership is not queryable", relation)
					}
				}
			}
			t.Logf("real native %s import, ordinary edit and PBC/JSON re-export preserved canonical identities and unknown fields", format)
		})
	}
}

// The consumer does not import the transport implementation. Compare every
// root/record field as raw JSON bytes, allowing only the two assigned context
// identities in owned records. Item IDs, provider/canonical IDs, block IDs and
// unknown fields must survive unchanged through import, edit and both exports.
func importedCanonicalEquivalent(before, after, space, object string) bool {
	var old, next map[string]json.RawMessage
	if json.Unmarshal([]byte(before), &old) != nil || json.Unmarshal([]byte(after), &next) != nil || len(old) != len(next) {
		return false
	}
	for key, raw := range old {
		if key != "records" && !bytes.Equal(raw, next[key]) {
			return false
		}
	}
	var oldRecords, nextRecords []map[string]json.RawMessage
	if json.Unmarshal(old["records"], &oldRecords) != nil || json.Unmarshal(next["records"], &nextRecords) != nil || len(oldRecords) == 0 || len(oldRecords) != len(nextRecords) {
		return false
	}
	for index, record := range oldRecords {
		rewritten := nextRecords[index]
		if len(record) != len(rewritten) {
			return false
		}
		for key, raw := range record {
			if key == "spaceId" || key == "objectId" {
				var value string
				if json.Unmarshal(rewritten[key], &value) != nil {
					return false
				}
				if key == "spaceId" && value != space || key == "objectId" && value != object {
					return false
				}
			} else if !bytes.Equal(raw, rewritten[key]) {
				return false
			}
		}
	}
	return true
}
