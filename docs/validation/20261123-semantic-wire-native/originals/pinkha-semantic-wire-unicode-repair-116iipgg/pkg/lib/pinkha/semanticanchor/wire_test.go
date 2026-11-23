package semanticanchor

import (
	"bytes"
	"encoding/json"
	"errors"
	"reflect"
	"strings"
	"testing"
)

func wireFixture() map[string]any {
	return map[string]any{"protocolVersion": 1, "spaceID": "space", "objectID": "document", "blockID": "paragraph",
		"anchorID": "00112233-4455-6677-8899-aabbccddeeff", "from": 4, "to": 6,
		"expected": map[string]any{"text": "אבג 😀 text", "marks": []Mark{
			{From: 0, To: 3, Kind: 1}, {From: 7, To: 11, Kind: 6, Param: "red"}, {From: 7, To: 11, Kind: 6, Param: "red"}}}}
}

func wireJSON(t *testing.T, value any) []byte {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func TestSemanticAnchorWireKeepsExactUTF16AndEveryOrderedNativeMark(t *testing.T) {
	raw := wireJSON(t, wireFixture())
	request, err := CaptureFromWire(raw)
	if err != nil {
		t.Fatal(err)
	}
	want := CaptureRequest{Version: 1, SpaceID: "space", ObjectID: "document", BlockID: "paragraph",
		AnchorID: "00112233-4455-6677-8899-aabbccddeeff", From: 4, To: 6,
		Expected: Snapshot{Text: "אבג 😀 text", Marks: []Mark{
			{From: 0, To: 3, Kind: 1}, {From: 7, To: 11, Kind: 6, Param: "red"}, {From: 7, To: 11, Kind: 6, Param: "red"}}}}
	if !reflect.DeepEqual(want, request) {
		t.Fatal("wire capture omitted or normalized native comparison input")
	}
	planned, err := request.Plan(request.Expected)
	if err != nil || len(planned.Marks) != 4 {
		t.Fatalf("wire capture did not retain the existing contract: %v", err)
	}
}

func TestSemanticAnchorWireRejectsAmbiguousUnknownNullAndUnboundedInput(t *testing.T) {
	valid := wireJSON(t, wireFixture())
	for _, scenario := range []string{"duplicate-top", "duplicate-snapshot", "duplicate-mark", "case-alias", "unknown-authority",
		"missing-field", "null-version", "null-string", "null-offset", "null-snapshot", "null-text", "null-marks",
		"fractional-offset", "overflow-offset", "utf16-surrogate-offset", "future-version", "too-many-marks", "oversized-wire", "invalid-utf8", "trailing-object"} {
		t.Run(scenario, func(t *testing.T) {
			value := wireFixture()
			raw := bytes.Clone(valid)
			want := ErrInvalid
			switch scenario {
			case "duplicate-top":
				raw = append([]byte(`{"from":4,`), raw[1:]...)
			case "duplicate-snapshot":
				raw = bytes.Replace(raw, []byte(`"expected":{`), []byte(`"expected":{"text":"same",`), 1)
			case "duplicate-mark":
				raw = bytes.Replace(raw, []byte(`"kind":1`), []byte(`"kind":1,"kind":1`), 1)
			case "case-alias":
				value["SpaceID"] = value["spaceID"]
				raw = wireJSON(t, value)
			case "unknown-authority":
				value["canWrite"] = true
				raw = wireJSON(t, value)
			case "missing-field":
				delete(value, "from")
				raw = wireJSON(t, value)
			case "null-version", "null-string", "null-offset", "null-snapshot":
				name := map[string]string{"null-version": "protocolVersion", "null-string": "spaceID", "null-offset": "from", "null-snapshot": "expected"}[scenario]
				value[name] = nil
				raw = wireJSON(t, value)
			case "null-text", "null-marks":
				value["expected"].(map[string]any)[strings.TrimPrefix(scenario, "null-")] = nil
				raw = wireJSON(t, value)
			case "fractional-offset":
				value["from"] = 4.5
				raw = wireJSON(t, value)
			case "overflow-offset":
				value["to"] = int64(1) << 40
				raw = wireJSON(t, value)
			case "utf16-surrogate-offset":
				value["from"] = 5
				raw = wireJSON(t, value)
			case "future-version":
				value["protocolVersion"] = 2
				raw, want = wireJSON(t, value), ErrUnsupportedVersion
			case "too-many-marks":
				value["expected"].(map[string]any)["marks"] = make([]Mark, MaxMarks+1)
				raw, want = wireJSON(t, value), ErrLimit
			case "oversized-wire":
				raw, want = bytes.Repeat([]byte{' '}, MaxCaptureWireBytes+1), ErrLimit
			case "invalid-utf8":
				raw = append(raw, 0xff)
			case "trailing-object":
				raw = append(raw, []byte(`{}`)...)
			}
			request, err := CaptureFromWire(raw)
			if !errors.Is(err, want) || !reflect.DeepEqual(request, CaptureRequest{}) {
				t.Fatalf("unsafe request was not refused before native authority: %v", err)
			}
		})
	}
}

func TestSemanticAnchorWireReplyRequiresWitnessAndKeepsNativeResponseEvents(t *testing.T) {
	marker, err := Marker("space", "document", "00112233-4455-6677-8899-aabbccddeeff")
	if err != nil {
		t.Fatal(err)
	}
	receipt := Receipt{Version: 1, SpaceID: "space", ObjectID: "document", BlockID: "paragraph",
		AnchorID: "00112233-4455-6677-8899-aabbccddeeff", Marker: marker, ChangeID: "native-change-id",
		NativeChangeSHA256: strings.Repeat("c", 64), BeforeTextMarksSHA256: strings.Repeat("a", 64), AfterTextMarksSHA256: strings.Repeat("b", 64)}
	events := []byte("explicit synthetic native-event bytes; codec control only")
	var reply CaptureWireResponse
	if err := json.Unmarshal(CaptureWireSuccess(receipt, events), &reply); err != nil || reply.Outcome != "applied" ||
		reply.Receipt == nil || *reply.Receipt != receipt || !bytes.Equal(reply.ResponseEvent, events) {
		t.Fatalf("wire changed its receipt or opaque native event: %v", err)
	}
	for _, scenario := range []string{"wrong-marker", "invalid-digest", "unchanged-digest", "missing-events", "oversized-events"} {
		t.Run(scenario, func(t *testing.T) {
			changed, event := receipt, events
			switch scenario {
			case "wrong-marker":
				changed.Marker += "foreign"
			case "invalid-digest":
				changed.NativeChangeSHA256 = strings.Repeat("x", 64)
			case "unchanged-digest":
				changed.AfterTextMarksSHA256 = changed.BeforeTextMarksSHA256
			case "missing-events":
				event = nil
			case "oversized-events":
				event = make([]byte, MaxCaptureNativeEventBytes+1)
			}
			var value CaptureWireResponse
			if err := json.Unmarshal(CaptureWireSuccess(changed, event), &value); err != nil || value.Outcome != "uncertain" || value.Receipt != nil || len(value.ResponseEvent) != 0 {
				t.Fatalf("incomplete native result was promoted: %v", err)
			}
		})
	}
	var failure CaptureWireResponse
	if err := json.Unmarshal(CaptureWireFailure("sensitive arbitrary native error"), &failure); err != nil ||
		failure.Outcome != "unavailable" || failure.Receipt != nil || len(failure.ResponseEvent) != 0 {
		t.Fatalf("wire leaked an arbitrary error or payload: %v", err)
	}
}
