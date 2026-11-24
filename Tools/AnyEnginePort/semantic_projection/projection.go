// Package semanticprojection decodes the pinned Heart export dialect. Its
// detached values are conversion inputs, never source or destination authority.
package semanticprojection

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"unicode/utf16"
	"unicode/utf8"

	"github.com/anyproto/any-block/codec/anyblockjson"
	"github.com/anyproto/any-block/format/v1/model"
)

const Contract = "pinkha-heart-inline-projection-v1"
const Codec = "any-block/9906a7c36b68"
const MaximumTextBytes = 65536
const MaximumMarks = 4096

var ErrLimit = errors.New("semantic projection limit exceeded")
var ErrInvalidMark = errors.New("native semantic mark is not representable")

type Mark struct {
	Kind      string `json:"kind"`
	Start     int    `json:"start"`
	End       int    `json:"end"`
	Parameter string `json:"parameter"`
}

type Projection struct {
	Contract     string `json:"contract"`
	Codec        string `json:"codec"`
	SourceSHA256 string `json:"sourceSHA256"`
	SourceUTF16  int    `json:"sourceUTF16"`
	Literal      bool   `json:"literal"`
	Text         string `json:"text"`
	Marks        []Mark `json:"marks"`
}

// ProjectInline uses the actual source codec, not a Markdown approximation.
// Literal is for native code/embed text only. The caller retains the original
// document bytes and independently proves native snapshot/census admission.
func ProjectInline(source string, literal bool) (Projection, error) {
	if !utf8.ValidString(source) || len(source) > MaximumTextBytes {
		return Projection{}, ErrLimit
	}
	sum := sha256.Sum256([]byte(source))
	p := Projection{Contract: Contract, Codec: Codec, SourceSHA256: hex.EncodeToString(sum[:]),
		SourceUTF16: len(utf16.Encode([]rune(source))), Literal: literal, Text: source, Marks: []Mark{}}
	if literal {
		return p, nil
	}
	text, marks, err := anyblockjson.ParseInlineText(source)
	if err != nil {
		return Projection{}, err
	}
	if !utf8.ValidString(text) || len(text) > MaximumTextBytes || len(marks) > MaximumMarks {
		return Projection{}, ErrLimit
	}
	p.Text = text
	units := utf16.Encode([]rune(text))
	boundary := func(i int) bool {
		return i >= 0 && i <= len(units) && (i == 0 || i == len(units) ||
			!(units[i-1] >= 0xd800 && units[i-1] <= 0xdbff && units[i] >= 0xdc00 && units[i] <= 0xdfff))
	}
	for _, mark := range marks {
		if mark == nil || mark.Range == nil {
			return Projection{}, ErrInvalidMark
		}
		kind, ok := markKind(mark.Type)
		start, end := int(mark.Range.From), int(mark.Range.To)
		if !ok || start >= end || !boundary(start) || !boundary(end) {
			return Projection{}, ErrInvalidMark
		}
		p.Marks = append(p.Marks, Mark{Kind: kind, Start: start, End: end, Parameter: mark.Param})
	}
	return p, nil
}

func markKind(kind model.BlockContentTextMarkType) (string, bool) {
	switch kind {
	case model.BlockContentTextMark_Bold:
		return "bold", true
	case model.BlockContentTextMark_Italic:
		return "italic", true
	case model.BlockContentTextMark_Strikethrough:
		return "strike", true
	case model.BlockContentTextMark_Keyboard:
		return "code", true
	case model.BlockContentTextMark_Link:
		return "link", true
	case model.BlockContentTextMark_Object:
		return "object", true
	case model.BlockContentTextMark_Mention:
		return "mention", true
	case model.BlockContentTextMark_Underscored:
		return "underline", true
	case model.BlockContentTextMark_TextColor:
		return "textColor", true
	case model.BlockContentTextMark_BackgroundColor:
		return "backgroundColor", true
	default:
		return "", false
	}
}
