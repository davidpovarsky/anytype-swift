package heartprobe

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/anyproto/anytype-heart/clientlibrary/service"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/proto"
)

// Native export fixtures only: never a hand-built substitute for product export.
// A fresh destination is mandatory so stale evidence cannot be reused silently.
func emitCompatibilityExports(t *testing.T, spaceID string, ids []string, documentName, canonicalRaw string) {
	t.Helper()
	directory := os.Getenv("PINKHA_NATIVE_COMPAT_EXPORT")
	if directory == "" {
		return
	}
	if err := os.Mkdir(directory, 0700); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"pbc", "json"} {
		if err := os.Mkdir(filepath.Join(directory, name), 0700); err != nil {
			t.Fatal(err)
		}
	}
	hashes := map[string]string{}
	for _, id := range ids {
		for _, format := range []model.ExportFormat{model.Export_Protobuf, model.Export_JSON} {
			request, err := proto.Marshal(&pb.RpcObjectExportRequest{SpaceId: spaceID, ObjectId: id, Format: format})
			if err != nil {
				t.Fatal(err)
			}
			response := &pb.RpcObjectExportResponse{}
			if err = proto.Unmarshal(service.ObjectExport(request), response); err != nil {
				t.Fatal(err)
			}
			if response.Error != nil && response.Error.Code != 0 {
				t.Fatalf("native compatibility export failed: %d %s", response.Error.Code, response.Error.Description)
			}
			var output []byte
			var relative string
			if format == model.Export_Protobuf {
				output, err = base64.StdEncoding.DecodeString(response.Result)
				relative = filepath.Join("pbc", id+".pb")
			} else {
				output = []byte(response.Result)
				relative = filepath.Join("json", id+".json")
			}
			if err != nil {
				t.Fatal(err)
			}
			if err = os.WriteFile(filepath.Join(directory, relative), output, 0600); err != nil {
				t.Fatal(err)
			}
			sum := sha256.Sum256(output)
			hashes[relative] = hex.EncodeToString(sum[:])
		}
	}
	contract, err := json.MarshalIndent(map[string]any{"documentName": documentName, "canonicalRaw": canonicalRaw, "nativeExportHashes": hashes}, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(directory, "contract.json"), contract, 0600); err != nil {
		t.Fatal(err)
	}
	t.Logf("Created actual PBC/JSON compatibility exports for %d real native Objects", len(ids))
}
