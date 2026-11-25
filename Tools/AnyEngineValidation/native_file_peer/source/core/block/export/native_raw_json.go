//go:build pinkha_loaded_account_witness

package export

import (
	"bytes"
	"encoding/json"
	"errors"

	"github.com/gogo/protobuf/jsonpb"
)

// NativeSnapshotJSONView is a derived semantic view of one detached original
// protobuf. Snapshot follows the generated native protobuf JSON schema: original
// field names, explicit defaults, integer enums and protobuf-JSON 64-bit strings.
// It is not source admission. Unknown protobuf fields remain in the original
// SnapshotBase bytes, which callers must retain and verify by SnapshotSHA256.
type NativeSnapshotJSONView struct {
	Contract       string
	ObjectID       string
	SpaceID        string
	NativeType     int32
	UniqueKey      string
	SnapshotSHA256 string
	SnapshotBytes  int
	Snapshot       json.RawMessage
}

const nativeSnapshotJSONLimit = 32 << 20

type nativeSnapshotJSONBuffer struct {
	buffer bytes.Buffer
}

func (b *nativeSnapshotJSONBuffer) Write(p []byte) (int, error) {
	if len(p) > nativeSnapshotJSONLimit-b.buffer.Len() {
		return 0, errors.New("native snapshot JSON exceeds bounded view")
	}
	return b.buffer.Write(p)
}

// JSONView decodes only the private captured snapshot. It cannot resolve an
// object, consult a mutable index, fetch a file, or confer current authority.
// Map keys are sorted by encoding/json without converting JSON numbers to float.
func (w *NativeRawObject) JSONView() ([]byte, error) {
	row, err := w.capturedRow()
	if err != nil {
		return nil, err
	}
	var encoded nativeSnapshotJSONBuffer
	marshaler := jsonpb.Marshaler{OrigName: true, EmitDefaults: true, EnumsAsInts: true}
	if err := marshaler.Marshal(&encoded, row.Snapshot); err != nil {
		return nil, err
	}
	decoder := json.NewDecoder(bytes.NewReader(encoded.buffer.Bytes()))
	decoder.UseNumber()
	var semantic any
	if err := decoder.Decode(&semantic); err != nil {
		return nil, err
	}
	canonical, err := json.Marshal(semantic)
	if err != nil || len(canonical) > nativeSnapshotJSONLimit {
		return nil, errors.Join(ErrNativeObjectWitness, err)
	}
	view := NativeSnapshotJSONView{
		Contract: "pinkha-native-snapshot-json-v1",
		ObjectID: w.objectID, SpaceID: w.spaceID, NativeType: int32(w.nativeType),
		UniqueKey: w.uniqueKey, SnapshotSHA256: nativeObjectWitnessHash(w.snapshot),
		SnapshotBytes: len(w.snapshot), Snapshot: canonical,
	}
	raw, err := json.Marshal(view)
	if err != nil || len(raw) > nativeSnapshotJSONLimit {
		return nil, errors.Join(ErrNativeObjectWitness, err)
	}
	return raw, nil
}
