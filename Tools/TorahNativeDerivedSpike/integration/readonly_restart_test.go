package heartprobe

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/clientlibrary/service"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
	"github.com/gogo/protobuf/proto"
)

type privateReadonlyFixture struct {
	Seed        string
	AccountID   string
	SpaceID     string
	Definitions map[string]string
	OrdinaryID  string
}

// Real middleware in two separate processes. The synthetic seed exists only in
// a mode-0600 file under t.TempDir; it never enters arguments, logs or artifacts.
func TestNativeReadonlyDefinitionProcessRestart(t *testing.T) {
	if os.Getenv("PINKHA_NATIVE_WIRE_ACCEPTANCE") != "1" {
		t.Skip("disposable native wallet opt-in required")
	}
	stage := os.Getenv("PINKHA_READONLY_STAGE")
	if stage == "" {
		root := t.TempDir()
		binary, err := os.Executable()
		if err != nil {
			t.Fatal(err)
		}
		for _, name := range []string{"create", "reopen"} {
			cmd := exec.Command(binary, "-test.run=^TestNativeReadonlyDefinitionProcessRestart$", "-test.v")
			cmd.Env = append(os.Environ(), "PINKHA_READONLY_STAGE="+name, "PINKHA_READONLY_ROOT="+root)
			output, err := cmd.CombinedOutput()
			if err != nil {
				// Do not relay native wallet/client logging. Only our credential-free
				// assertion locations are useful to diagnose this focused test.
				for _, line := range strings.Split(string(output), "\n") {
					if strings.Contains(line, "readonly_restart_test.go:") {
						t.Log(line)
					}
				}
				t.Fatalf("fresh native %s process failed: %v", name, err)
			}
			t.Logf("fresh native %s process passed", name)
		}
		return
	}
	root := os.Getenv("PINKHA_READONLY_ROOT")
	if root == "" {
		t.Fatal("missing private disposable root")
	}
	privateFile := filepath.Join(root, "private-readonly-fixture.json")
	invoke := func(call func([]byte) []byte, request, response proto.Message) {
		t.Helper()
		data, err := proto.Marshal(request)
		if err != nil {
			t.Fatal("request serialization failed")
		}
		if err := proto.Unmarshal(call(data), response); err != nil {
			t.Fatal("response decoding failed")
		}
		field := reflect.ValueOf(response).Elem().FieldByName("Error")
		if field.IsValid() && !field.IsNil() && field.Elem().FieldByName("Code").Int() != 0 {
			t.Fatalf("%T returned error code %d", request, field.Elem().FieldByName("Code").Int())
		}
	}
	service.SetEventHandler(func(*pb.Event) {})
	invoke(service.InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSendLogs: true, DoNotSaveLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	fixture := privateReadonlyFixture{Definitions: map[string]string{}}
	if stage == "create" {
		wallet := &pb.RpcWalletCreateResponse{}
		invoke(service.WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, wallet)
		fixture.Seed = wallet.Mnemonic
		account := &pb.RpcAccountCreateResponse{}
		invoke(service.AccountCreate, &pb.RpcAccountCreateRequest{Name: "Disposable readonly restart", NetworkMode: pb.RpcAccount_LocalOnly,
			DisableLocalNetworkSync: true}, account)
		fixture.AccountID = account.Account.GetId()
		space := &pb.RpcWorkspaceCreateResponse{}
		invoke(service.WorkspaceCreate, &pb.RpcWorkspaceCreateRequest{Details: domain.NewDetails().SetString(bundle.RelationKeyName, "Fresh readonly restart").ToProto()}, space)
		fixture.SpaceID = space.SpaceId
	} else if stage == "reopen" {
		raw, err := os.ReadFile(privateFile)
		if err != nil {
			t.Fatal("private fixture read failed")
		}
		if err := json.Unmarshal(raw, &fixture); err != nil {
			t.Fatal("private fixture decode failed")
		}
		invoke(service.WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, Mnemonic: fixture.Seed}, &pb.RpcWalletRecoverResponse{})
		invoke(service.AccountSelect, &pb.RpcAccountSelectRequest{Id: fixture.AccountID, RootPath: root,
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true, PreferredSpaceId: fixture.SpaceID}, &pb.RpcAccountSelectResponse{})
	} else {
		t.Fatal("unexpected subprocess stage")
	}
	t.Cleanup(func() { invoke(service.AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{}) })
	invoke(service.WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: fixture.SpaceID}, &pb.RpcWorkspaceOpenResponse{})
	show := func(id string) *domain.Details {
		t.Helper()
		response := &pb.RpcObjectShowResponse{}
		invoke(service.ObjectShow, &pb.RpcObjectShowRequest{SpaceId: fixture.SpaceID, ObjectId: id, ContextId: id}, response)
		for _, object := range response.ObjectView.Details {
			if object.Id == id {
				return domain.NewDetailsFromProto(object.Details)
			}
		}
		t.Fatal("requested definition missing from ObjectShow")
		return nil
	}
	if stage == "create" {
		for _, definition := range torah.Definitions {
			response := &pb.RpcObjectCreateRelationResponse{}
			details := domain.NewDetails().SetString(bundle.RelationKeyName, definition.Name).
				SetString(bundle.RelationKeyRelationKey, definition.Key).
				SetInt64(bundle.RelationKeyRelationFormat, int64(model.RelationFormat_tag)).
				SetBool(bundle.RelationKeyRelationReadonlyValue, true)
			invoke(service.ObjectCreateRelation, &pb.RpcObjectCreateRelationRequest{SpaceId: fixture.SpaceID, Details: details.ToProto()}, response)
			fixture.Definitions[definition.Key] = response.ObjectId
			if !show(response.ObjectId).GetBool(bundle.RelationKeyRelationReadonlyValue) {
				t.Fatal("new native definition is not readonly")
			}
		}
		ordinary := &pb.RpcObjectCreateRelationResponse{}
		invoke(service.ObjectCreateRelation, &pb.RpcObjectCreateRelationRequest{SpaceId: fixture.SpaceID, Details: domain.NewDetails().
			SetString(bundle.RelationKeyName, "מקור/ות").SetInt64(bundle.RelationKeyRelationFormat, int64(model.RelationFormat_tag)).
			SetBool(bundle.RelationKeyRelationReadonlyValue, true).ToProto()}, ordinary)
		fixture.OrdinaryID = ordinary.ObjectId
		raw, err := json.Marshal(fixture)
		if err != nil {
			t.Fatal("private fixture encoding failed")
		}
		if err := os.WriteFile(privateFile, raw, 0600); err != nil {
			t.Fatal("private fixture write failed")
		}
		return
	}
	// Wait for the ORIGINAL maintenance to act on the ordinary readonly Tag.
	// This proves the native assertions run after maintenance, not before it.
	deadline := time.Now().Add(45 * time.Second)
	for show(fixture.OrdinaryID).GetBool(bundle.RelationKeyRelationReadonlyValue) {
		if time.Now().After(deadline) {
			t.Fatal("ordinary Tag maintenance did not finish")
		}
		time.Sleep(100 * time.Millisecond)
	}
	for key, id := range fixture.Definitions {
		details := show(id)
		if !details.GetBool(bundle.RelationKeyRelationReadonlyValue) || details.GetString(bundle.RelationKeySourceObject) != "_br"+key {
			t.Fatalf("native definition %s lost readonly identity after process restart", key)
		}
	}
	search := &pb.RpcObjectSearchResponse{}
	invoke(service.ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: fixture.SpaceID, Keys: []string{"id", "relationKey", "relationReadonlyValue", "sourceObject"},
		Filters: []*model.BlockContentDataviewFilter{{RelationKey: "relationKey", Condition: model.BlockContentDataviewFilter_In,
			Value: domain.StringList([]string{torah.SourcesKey, torah.TopicsKey, torah.WordsKey}).ToProto()}}}, search)
	if len(search.Records) != 3 {
		t.Fatal("native definition count changed after restart")
	}
	for _, record := range search.Records {
		details := domain.NewDetailsFromProto(record)
		if !details.GetBool(bundle.RelationKeyRelationReadonlyValue) {
			t.Fatal("indexed native readonly flag lost after restart")
		}
	}
}
