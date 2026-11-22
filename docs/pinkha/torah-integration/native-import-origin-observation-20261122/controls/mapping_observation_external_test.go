package importer_test

import (
	"encoding/json"
	"testing"

	importer "github.com/anyproto/anytype-heart/core/block/import"
)

func TestPublicLegacyResponseAndJSONCannotConstructObservation(t *testing.T) {
	var empty importer.NativeProtobufImportMappingObservation
	if empty.CompleteForSelectedSnapshots() {
		t.Fatal("zero value is complete")
	}
	if err := json.Unmarshal([]byte(`{"complete":true,"traceID":"forged","sources":[{"NativeID":"forged"}]}`), &empty); err != nil {
		t.Fatal(err)
	}
	if empty.CompleteForSelectedSnapshots() || len(empty.SourceAssignments()) != 0 {
		t.Fatal("JSON manufactured private observation fields")
	}
	r := &importer.ImportResponse{ProcessId: "caller-supplied", ObjectsCount: 1, RootCollectionId: "caller-supplied"}
	if _, ok := r.NativeMappingObservation(); ok {
		t.Fatal("legacy public fields manufactured a completed observation")
	}
	var nilResponse *importer.ImportResponse
	if _, ok := nilResponse.NativeMappingObservation(); ok || nilResponse.NativeMappingProblems() != nil {
		t.Fatal("nil response manufactured facts")
	}
}
