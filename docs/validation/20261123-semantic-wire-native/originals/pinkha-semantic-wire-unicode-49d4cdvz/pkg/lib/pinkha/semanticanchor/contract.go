// Package semanticanchor defines the bounded capture comparison shared by the
// native editor adapter. It grants no account, ACL, cache or persistence authority.
package semanticanchor

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"slices"
	"strings"
	"unicode/utf8"
)

const (
	Version              = 1
	MarkerPrefix         = "pinkha-anchor://v1/"
	MaxIdentityBytes     = 1024
	MaxTextBytes         = 65536
	MaxMarks             = 1024
	MaxMarkParamBytes    = 8192
	MaxAllMarkParamBytes = 262144
	MaxDocumentBlocks    = 10000
	NativeLinkMark       = 5
	NativeMentionMark    = 8
	NativeObjectMark     = 10
)

var (
	ErrInvalid            = errors.New("invalid semantic anchor capture")
	ErrUnsupportedVersion = errors.New("unsupported semantic anchor version")
	ErrLimit              = errors.New("semantic anchor capture limit exceeded")
	ErrConflict           = errors.New("semantic anchor text or marks changed")
	ErrAlreadyLinked      = errors.New("semantic anchor selection already linked")
	ErrDuplicate          = errors.New("semantic anchor identity already present")
	ErrPendingEdit        = errors.New("native editor has a pending text batch")
	ErrUnavailable        = errors.New("semantic anchor native target unavailable")
	ErrUncertain          = errors.New("semantic anchor native commit not acknowledged")
)

// Mark preserves every field of the current native BlockContentTextMark model.
// The adapter must reject a nil mark/range; it must never omit an unsupported
// mark to make a comparison succeed. From/To are transient native UTF-16 ranges.
type Mark struct {
	From  int32  `json:"from"`
	To    int32  `json:"to"`
	Kind  int32  `json:"kind"`
	Param string `json:"param"`
}

type Snapshot struct {
	Text  string `json:"text"`
	Marks []Mark `json:"marks"`
}

type CaptureRequest struct {
	Version  uint32
	SpaceID  string
	ObjectID string
	BlockID  string
	AnchorID string
	From     int32
	To       int32
	Expected Snapshot
}

// Receipt contains a native durable change witness, not saved selection offsets.
// Only the native adapter may issue it after a real Apply and storage readback.
type Receipt struct {
	Version               uint32 `json:"version"`
	SpaceID               string `json:"spaceID"`
	ObjectID              string `json:"objectID"`
	BlockID               string `json:"blockID"`
	AnchorID              string `json:"anchorID"`
	Marker                string `json:"marker"`
	ChangeID              string `json:"changeID"`
	NativeChangeSHA256    string `json:"nativeChangeSHA256"`
	BeforeTextMarksSHA256 string `json:"beforeTextMarksSHA256"`
	AfterTextMarksSHA256  string `json:"afterTextMarksSHA256"`
}

func ValidIdentity(value string) bool {
	return value != "" && len(value) <= MaxIdentityBytes && utf8.ValidString(value) && !strings.ContainsRune(value, 0)
}

func ValidAnchorID(value string) bool {
	if len(value) != 36 {
		return false
	}
	for index, character := range value {
		if index == 8 || index == 13 || index == 18 || index == 23 {
			if character != '-' {
				return false
			}
		} else if !(character >= '0' && character <= '9') && !(character >= 'a' && character <= 'f') {
			return false
		}
	}
	return true
}

func Marker(spaceID, objectID, anchorID string) (string, error) {
	if !ValidIdentity(spaceID) || !ValidIdentity(objectID) || !ValidAnchorID(anchorID) {
		return "", ErrInvalid
	}
	return MarkerPrefix + base64.RawURLEncoding.EncodeToString([]byte(spaceID)) + "/" +
		base64.RawURLEncoding.EncodeToString([]byte(objectID)) + "/" + anchorID, nil
}

func ReservedMarker(value string) bool {
	return strings.HasPrefix(strings.ToLower(value), "pinkha-anchor:")
}

// ScalarRange rejects UTF-16 offsets inside a surrogate pair. The mounted
// editor additionally requires grapheme boundaries when capturing a selection;
// this scalar check alone is not a claim of complete UAX #29 segmentation.
func ScalarRange(text string, from, to int32, nonempty bool) bool {
	if !utf8.ValidString(text) || from < 0 || to < from || (nonempty && from == to) {
		return false
	}
	var offset int32
	fromBoundary, toBoundary := from == 0, to == 0
	for _, character := range text {
		offset++
		if character > 0xffff {
			offset++
		}
		fromBoundary = fromBoundary || from == offset
		toBoundary = toBoundary || to == offset
	}
	return fromBoundary && toBoundary && to <= offset
}

func (snapshot Snapshot) Validate() error {
	if len(snapshot.Text) > MaxTextBytes || len(snapshot.Marks) > MaxMarks {
		return ErrLimit
	}
	if !utf8.ValidString(snapshot.Text) {
		return ErrInvalid
	}
	paramBytes := 0
	for _, mark := range snapshot.Marks {
		paramBytes += len(mark.Param)
		if len(mark.Param) > MaxMarkParamBytes || paramBytes > MaxAllMarkParamBytes {
			return ErrLimit
		}
		if mark.Kind < 0 || mark.Kind > NativeObjectMark || !utf8.ValidString(mark.Param) ||
			!ScalarRange(snapshot.Text, mark.From, mark.To, true) {
			return ErrInvalid
		}
	}
	return nil
}

func (request CaptureRequest) Validate() (string, error) {
	if request.Version != Version {
		return "", ErrUnsupportedVersion
	}
	if !ValidIdentity(request.BlockID) {
		return "", ErrInvalid
	}
	marker, err := Marker(request.SpaceID, request.ObjectID, request.AnchorID)
	if err != nil {
		return "", err
	}
	if err = request.Expected.Validate(); err != nil {
		return "", err
	}
	if len(request.Expected.Marks) == MaxMarks {
		return "", ErrLimit
	}
	if !ScalarRange(request.Expected.Text, request.From, request.To, true) {
		return "", ErrInvalid
	}
	for _, mark := range request.Expected.Marks {
		if mark.Param == marker {
			return "", ErrDuplicate
		}
		if mark.From < request.To && request.From < mark.To &&
			(mark.Kind == NativeLinkMark || mark.Kind == NativeMentionMark || mark.Kind == NativeObjectMark || ReservedMarker(mark.Param)) {
			return "", ErrAlreadyLinked
		}
	}
	return marker, nil
}

// Exact compares text bytes and all ordered native mark fields. This is the
// pre-write CAS predicate; a caller cannot submit only its semantic-link marks.
func (snapshot Snapshot) Exact(other Snapshot) bool {
	return snapshot.Text == other.Text && slices.Equal(snapshot.Marks, other.Marks)
}

// SameMarks tolerates only native mark reordering during Apply's Diff. It keeps
// duplicates and every mark field, and never sorts either caller-owned slice.
func (snapshot Snapshot) SameMarks(other Snapshot) bool {
	if snapshot.Text != other.Text || len(snapshot.Marks) != len(other.Marks) {
		return false
	}
	left, right := slices.Clone(snapshot.Marks), slices.Clone(other.Marks)
	less := func(a, b Mark) int {
		if a.From != b.From {
			if a.From < b.From {
				return -1
			}
			return 1
		}
		if a.To != b.To {
			if a.To < b.To {
				return -1
			}
			return 1
		}
		if a.Kind != b.Kind {
			if a.Kind < b.Kind {
				return -1
			}
			return 1
		}
		return strings.Compare(a.Param, b.Param)
	}
	slices.SortFunc(left, less)
	slices.SortFunc(right, less)
	return slices.Equal(left, right)
}

// Plan adds exactly one native link mark after the complete comparison. It is
// pure planning: the caller still needs native lock, authority and commit proof.
func (request CaptureRequest) Plan(current Snapshot) (Snapshot, error) {
	marker, err := request.Validate()
	if err != nil {
		return Snapshot{}, err
	}
	if err = current.Validate(); err != nil {
		return Snapshot{}, err
	}
	if !request.Expected.Exact(current) {
		return Snapshot{}, ErrConflict
	}
	after := Snapshot{Text: current.Text, Marks: slices.Clone(current.Marks)}
	after.Marks = append(after.Marks, Mark{From: request.From, To: request.To, Kind: NativeLinkMark, Param: marker})
	return after, after.Validate()
}

func (snapshot Snapshot) Digest() string {
	// The fixed field-only schema cannot fail JSON encoding. Empty and nil mark
	// slices have the same canonical representation for this receipt digest.
	canonical := Snapshot{Text: snapshot.Text, Marks: append([]Mark{}, snapshot.Marks...)}
	wire, _ := json.Marshal(canonical)
	digest := sha256.Sum256(wire)
	return hex.EncodeToString(digest[:])
}
