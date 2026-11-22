package semanticanchor

import (
	"errors"
	"slices"
	"strings"
	"testing"
)

func semanticRequest() CaptureRequest {
	return CaptureRequest{Version: Version, SpaceID: "space", ObjectID: "document", BlockID: "paragraph",
		AnchorID: "00112233-4455-6677-8899-aabbccddeeff", From: 4, To: 6,
		Expected: Snapshot{Text: "אבג 😀 text", Marks: []Mark{{From: 0, To: 3, Kind: 3}, {From: 7, To: 11, Kind: 6, Param: "red"}}}}
}

func TestSemanticAnchorCaptureComparesEveryNativeMarkAndPreservesBytes(t *testing.T) {
	request := semanticRequest()
	before := Snapshot{Text: request.Expected.Text, Marks: slices.Clone(request.Expected.Marks)}
	after, err := request.Plan(before)
	if err != nil {
		t.Fatal(err)
	}
	marker := "pinkha-anchor://v1/c3BhY2U/ZG9jdW1lbnQ/00112233-4455-6677-8899-aabbccddeeff"
	if after.Text != before.Text || !slices.Equal(after.Marks[:2], before.Marks) || after.Marks[2] != (Mark{From: 4, To: 6, Kind: NativeLinkMark, Param: marker}) {
		t.Fatalf("capture changed text/other marks: %#v", after)
	}
	after.Marks[0].Param = "changed"
	if !request.Expected.Exact(before) {
		t.Fatal("planning aliased the native/expected marks")
	}
	for _, mutation := range []func(*Snapshot){
		func(s *Snapshot) { s.Text = "different text" },
		func(s *Snapshot) { s.Marks[0].Kind = 2 },
		func(s *Snapshot) { s.Marks[0].Param = "new" },
		func(s *Snapshot) { s.Marks[0].To = 2 },
		func(s *Snapshot) { s.Marks = s.Marks[:1] },
		func(s *Snapshot) { s.Marks = append(s.Marks, Mark{From: 0, To: 1, Kind: 4}) },
		func(s *Snapshot) { s.Marks[0], s.Marks[1] = s.Marks[1], s.Marks[0] },
	} {
		changed := Snapshot{Text: before.Text, Marks: slices.Clone(before.Marks)}
		mutation(&changed)
		if _, err = request.Plan(changed); !errors.Is(err, ErrConflict) {
			t.Fatalf("stale complete native snapshot accepted: %v", err)
		}
	}
}

func TestSemanticAnchorCaptureRejectsUTF16AndIdentityAmbiguity(t *testing.T) {
	for _, bounds := range [][2]int32{{4, 5}, {5, 6}, {-1, 2}, {7, 7}, {7, 99}} {
		req := semanticRequest()
		req.From, req.To = bounds[0], bounds[1]
		if _, err := req.Validate(); !errors.Is(err, ErrInvalid) {
			t.Fatalf("bad UTF16 %v accepted: %v", bounds, err)
		}
	}
	for _, value := range []string{"", "00112233-4455-6677-8899-AABBCCDDEEFF", "00112233445566778899aabbccddeeff", "00112233-4455-6677-8899-aabbccddeef/"} {
		req := semanticRequest()
		req.AnchorID = value
		if _, err := req.Validate(); !errors.Is(err, ErrInvalid) {
			t.Fatalf("noncanonical identity accepted: %v", err)
		}
	}
	req := semanticRequest()
	req.SpaceID = "sp\x00ace"
	if _, err := req.Validate(); !errors.Is(err, ErrInvalid) {
		t.Fatal("NUL scope accepted")
	}
	req = semanticRequest()
	req.Version++
	if _, err := req.Validate(); !errors.Is(err, ErrUnsupportedVersion) {
		t.Fatal("future protocol accepted")
	}
	marker, err := Marker("מרחב", "מסמך/פרק", semanticRequest().AnchorID)
	if err != nil || !strings.HasPrefix(marker, MarkerPrefix) || strings.Contains(marker, "=") {
		t.Fatalf("Unicode scope encoding: %q %v", marker, err)
	}
}

func TestSemanticAnchorCaptureRefusesExistingLinksAndDuplicateIdentity(t *testing.T) {
	for _, kind := range []int32{NativeLinkMark, NativeMentionMark, NativeObjectMark} {
		req := semanticRequest()
		req.Expected.Marks = append(req.Expected.Marks, Mark{From: 4, To: 6, Kind: kind, Param: "existing"})
		if _, err := req.Validate(); !errors.Is(err, ErrAlreadyLinked) {
			t.Fatalf("existing native link %d erased: %v", kind, err)
		}
	}
	req := semanticRequest()
	marker, _ := req.Validate()
	req.Expected.Marks = append(req.Expected.Marks, Mark{From: 7, To: 8, Kind: NativeLinkMark, Param: marker})
	if _, err := req.Validate(); !errors.Is(err, ErrDuplicate) {
		t.Fatal("identity reused outside selection")
	}
	req = semanticRequest()
	req.Expected.Marks = append(req.Expected.Marks, Mark{From: 4, To: 6, Kind: 3, Param: "PINKHA-ANCHOR://v999/bad"})
	if _, err := req.Validate(); !errors.Is(err, ErrAlreadyLinked) {
		t.Fatal("malformed reserved marker ignored")
	}
}

func TestSemanticAnchorPostApplyComparisonKeepsEveryMarkAndDuplicate(t *testing.T) {
	left := semanticRequest().Expected
	right := Snapshot{Text: left.Text, Marks: slices.Clone(left.Marks)}
	right.Marks[0], right.Marks[1] = right.Marks[1], right.Marks[0]
	original := slices.Clone(right.Marks)
	if left.Exact(right) || !left.SameMarks(right) || !slices.Equal(right.Marks, original) {
		t.Fatal("mark ordering contract or purity broken")
	}
	right.Marks[0].Param = "blue"
	if left.SameMarks(right) {
		t.Fatal("post-Apply mark mutation accepted")
	}
	right = Snapshot{Text: left.Text, Marks: append(slices.Clone(left.Marks), left.Marks[0])}
	if left.SameMarks(right) {
		t.Fatal("duplicate mark discarded")
	}
	if (Snapshot{Text: "x"}).Digest() != (Snapshot{Text: "x", Marks: []Mark{}}).Digest() {
		t.Fatal("empty marks are not canonical")
	}
}

func TestSemanticAnchorCaptureBoundsMalformedNativeMarks(t *testing.T) {
	for _, mark := range []Mark{{From: 0, To: 1, Kind: 11}, {From: 4, To: 5, Kind: 3}, {From: 0, To: 0, Kind: 3}, {From: 0, To: 1, Kind: 3, Param: string([]byte{0xff})}} {
		req := semanticRequest()
		req.Expected.Marks = []Mark{mark}
		if _, err := req.Validate(); !errors.Is(err, ErrInvalid) {
			t.Fatalf("malformed complete native state accepted: %v", err)
		}
	}
	req := semanticRequest()
	req.Expected.Text = strings.Repeat("x", MaxTextBytes+1)
	if _, err := req.Validate(); !errors.Is(err, ErrLimit) {
		t.Fatal("text limit ignored")
	}
	req = semanticRequest()
	req.Expected.Marks = make([]Mark, MaxMarks)
	for i := range req.Expected.Marks {
		req.Expected.Marks[i] = Mark{From: 0, To: 1, Kind: 3}
	}
	if _, err := req.Validate(); !errors.Is(err, ErrLimit) {
		t.Fatal("capture exceeded mark bound")
	}
}
