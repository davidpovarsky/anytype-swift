package semanticanchor

import (
	"bytes"
	"errors"
	"reflect"
	"testing"
)

// Only this new method is selected in the Unicode continuation. The original
// three wire methods keep their original execution/source provenance.
func TestSemanticAnchorWireRejectsUnpairedEscapesWithoutChangingValidUnicode(t *testing.T) {
	for _, scenario := range []string{
		"high-text", "low-text", "high-high-text", "high-bmp-text", "low-high-text", "truncated-pair",
		"high-identity", "low-param", "valid-pair", "valid-uppercase-pair", "valid-bmp",
		"literal-replacement", "escaped-replacement", "literal-backslash-param",
	} {
		t.Run(scenario, func(t *testing.T) {
			value := wireFixture()
			raw := wireJSON(t, value)
			wantText, wantParam, valid := "אבג 😀 text", "red", false
			switch scenario {
			case "high-text", "low-text", "high-high-text", "high-bmp-text", "low-high-text", "truncated-pair":
				escape := map[string]string{
					"high-text": `\ud800`, "low-text": `\udc00`, "high-high-text": `\ud800\ud800`,
					"high-bmp-text": `\ud800\u0041`, "low-high-text": `\udc00\ud800`, "truncated-pair": `\ud800\udc`,
				}[scenario]
				raw = bytes.Replace(raw, []byte(`"text":"אבג 😀 text"`), []byte(`"text":"אבג 😀 text`+escape+`"`), 1)
			case "high-identity":
				raw = bytes.Replace(raw, []byte(`"spaceID":"space"`), []byte(`"spaceID":"space\ud800"`), 1)
			case "low-param":
				raw = bytes.Replace(raw, []byte(`"param":"red"`), []byte(`"param":"\udfff"`), 1)
			case "valid-pair":
				raw, valid = bytes.Replace(raw, []byte("😀"), []byte(`\ud83d\ude00`), 1), true
			case "valid-uppercase-pair":
				raw, valid = bytes.Replace(raw, []byte("😀"), []byte(`\uD83D\uDE00`), 1), true
			case "valid-bmp":
				raw, valid = bytes.Replace(raw, []byte("אבג"), []byte(`\u05d0\u05d1\u05d2`), 1), true
			case "literal-replacement":
				raw, valid = bytes.Replace(raw, []byte(`"text":"אבג 😀 text"`), []byte(`"text":"אבג 😀 text�"`), 1), true
				wantText += "�"
			case "escaped-replacement":
				raw, valid = bytes.Replace(raw, []byte(`"text":"אבג 😀 text"`), []byte(`"text":"אבג 😀 text\ufffd"`), 1), true
				wantText += "�"
			case "literal-backslash-param":
				raw, valid = bytes.Replace(raw, []byte(`"param":"red"`), []byte(`"param":"\\ud800"`), 1), true
				wantParam = `\ud800`
			}
			request, err := CaptureFromWire(raw)
			if !valid {
				if !errors.Is(err, ErrInvalid) || !reflect.DeepEqual(request, CaptureRequest{}) {
					t.Fatalf("unpaired UTF-16 escape was normalized instead of refused: %v", err)
				}
				return
			}
			if err != nil || request.Expected.Text != wantText || len(request.Expected.Marks) != 3 ||
				request.Expected.Marks[1].Param != wantParam || request.From != 4 || request.To != 6 ||
				request.SpaceID != "space" || request.ObjectID != "document" || request.BlockID != "paragraph" {
				t.Fatalf("valid Unicode or escaped backslash was changed/rejected: %v", err)
			}
		})
	}
}
