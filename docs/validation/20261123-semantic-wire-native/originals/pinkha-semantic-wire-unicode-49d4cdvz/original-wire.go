package semanticanchor

import (
	"bytes"
	"encoding/json"
	"io"
	"unicode/utf8"
)

const MaxCaptureWireBytes = 4 * 1024 * 1024
const MaxCaptureReplyBytes = 4 * 1024 * 1024
const MaxCaptureNativeEventBytes = 2 * 1024 * 1024

type CaptureWireResponse struct {
	ProtocolVersion uint32   `json:"protocolVersion"`
	Outcome         string   `json:"outcome"`
	Receipt         *Receipt `json:"receipt,omitempty"`
	// The unchanged native Apply response event, serialized as protobuf. The
	// app adapter must dispatch it through its ordinary editor event reducer.
	ResponseEvent []byte `json:"responseEvent,omitempty"`
}

// CaptureFromWire accepts exactly this version's named fields. There are no
// caller-supplied account, signer, permission, native pointer or retry flags.
// Offsets and all current marks are transient CAS input, never the saved anchor.
func CaptureFromWire(raw []byte) (CaptureRequest, error) {
	empty := CaptureRequest{}
	if len(raw) == 0 || len(raw) > MaxCaptureWireBytes {
		return empty, ErrLimit
	}
	if !utf8.Valid(raw) {
		return empty, ErrInvalid
	}
	fields, err := captureWireObject(raw, "protocolVersion", "spaceID", "objectID", "blockID", "anchorID", "from", "to", "expected")
	if err != nil {
		return empty, err
	}
	request := CaptureRequest{}
	if err = captureWireValue(fields["protocolVersion"], &request.Version); err != nil {
		return empty, err
	}
	if request.Version != Version {
		return empty, ErrUnsupportedVersion
	}
	for name, destination := range map[string]*string{"spaceID": &request.SpaceID, "objectID": &request.ObjectID,
		"blockID": &request.BlockID, "anchorID": &request.AnchorID} {
		if err = captureWireValue(fields[name], destination); err != nil {
			return empty, err
		}
	}
	if err = captureWireValue(fields["from"], &request.From); err != nil {
		return empty, err
	}
	if err = captureWireValue(fields["to"], &request.To); err != nil {
		return empty, err
	}
	expected, err := captureWireObject(fields["expected"], "text", "marks")
	if err != nil {
		return empty, err
	}
	if err = captureWireValue(expected["text"], &request.Expected.Text); err != nil {
		return empty, err
	}
	decoder := json.NewDecoder(bytes.NewReader(expected["marks"]))
	start, err := decoder.Token()
	if err != nil || start != json.Delim('[') {
		return empty, ErrInvalid
	}
	for decoder.More() {
		if len(request.Expected.Marks) >= MaxMarks {
			return empty, ErrLimit
		}
		var rawMark json.RawMessage
		if err = decoder.Decode(&rawMark); err != nil {
			return empty, ErrInvalid
		}
		fields, err = captureWireObject(rawMark, "from", "to", "kind", "param")
		if err != nil {
			return empty, err
		}
		mark := Mark{}
		for name, destination := range map[string]*int32{"from": &mark.From, "to": &mark.To, "kind": &mark.Kind} {
			if err = captureWireValue(fields[name], destination); err != nil {
				return empty, err
			}
		}
		if err = captureWireValue(fields["param"], &mark.Param); err != nil {
			return empty, err
		}
		request.Expected.Marks = append(request.Expected.Marks, mark)
	}
	end, err := decoder.Token()
	if err != nil || end != json.Delim(']') || !captureWireEnd(decoder) {
		return empty, ErrInvalid
	}
	if _, err = request.Validate(); err != nil {
		return empty, err
	}
	return request, nil
}

func captureWireObject(raw []byte, names ...string) (map[string]json.RawMessage, error) {
	allowed := make(map[string]bool, len(names))
	for _, name := range names {
		allowed[name] = true
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	start, err := decoder.Token()
	if err != nil || start != json.Delim('{') {
		return nil, ErrInvalid
	}
	fields := make(map[string]json.RawMessage, len(names))
	for decoder.More() {
		key, err := decoder.Token()
		name, ok := key.(string)
		if err != nil || !ok || !allowed[name] || fields[name] != nil {
			return nil, ErrInvalid
		}
		var value json.RawMessage
		if err = decoder.Decode(&value); err != nil {
			return nil, ErrInvalid
		}
		fields[name] = value
	}
	end, err := decoder.Token()
	if err != nil || end != json.Delim('}') || len(fields) != len(names) || !captureWireEnd(decoder) {
		return nil, ErrInvalid
	}
	return fields, nil
}

func captureWireValue(raw json.RawMessage, value any) error {
	if bytes.Equal(bytes.TrimSpace(raw), []byte("null")) || json.Unmarshal(raw, value) != nil {
		return ErrInvalid
	}
	return nil
}

func captureWireEnd(decoder *json.Decoder) bool {
	var extra json.RawMessage
	return decoder.Decode(&extra) == io.EOF
}

// Only fixed public outcomes cross the byte boundary. An uncertain native
// mutation never carries a success receipt or invites an automatic retry.
func CaptureWireFailure(outcome string) []byte {
	switch outcome {
	case "invalid", "unsupportedVersion", "limit", "changed", "alreadyLinked", "pendingEdit", "permissionDenied", "unavailable", "uncertain":
	default:
		outcome = "unavailable"
	}
	raw, err := json.Marshal(CaptureWireResponse{ProtocolVersion: Version, Outcome: outcome})
	if err != nil {
		return []byte(`{"protocolVersion":1,"outcome":"uncertain"}`)
	}
	return raw
}

func CaptureWireSuccess(receipt Receipt, responseEvent []byte) []byte {
	marker, err := Marker(receipt.SpaceID, receipt.ObjectID, receipt.AnchorID)
	if err != nil || receipt.Version != Version || receipt.Marker != marker ||
		!ValidIdentity(receipt.BlockID) || !ValidIdentity(receipt.ChangeID) ||
		!captureWireDigest(receipt.NativeChangeSHA256) || !captureWireDigest(receipt.BeforeTextMarksSHA256) ||
		!captureWireDigest(receipt.AfterTextMarksSHA256) || receipt.BeforeTextMarksSHA256 == receipt.AfterTextMarksSHA256 ||
		len(responseEvent) == 0 || len(responseEvent) > MaxCaptureNativeEventBytes {
		return CaptureWireFailure("uncertain")
	}
	raw, err := json.Marshal(CaptureWireResponse{ProtocolVersion: Version, Outcome: "applied", Receipt: &receipt, ResponseEvent: responseEvent})
	if err != nil || len(raw) > MaxCaptureReplyBytes {
		return CaptureWireFailure("uncertain")
	}
	return raw
}

func captureWireDigest(value string) bool {
	if len(value) != 64 {
		return false
	}
	for _, char := range value {
		if !(char >= '0' && char <= '9') && !(char >= 'a' && char <= 'f') {
			return false
		}
	}
	return true
}
