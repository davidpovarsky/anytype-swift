package semanticprojection

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"testing"
)

func TestNativeDialectIsNotMarkdown(t *testing.T) {
	p, err := ProjectInline(`![alt](https://example.com) &lt;u&gt; <u>קו</u>`, false)
	if err != nil {
		t.Fatal(err)
	}
	if p.Text != "!alt <u> קו" {
		t.Fatalf("native visible text %q", p.Text)
	}
	var link, underline bool
	for _, m := range p.Marks {
		if m.Kind == "link" && m.Start == 1 && m.End == 4 {
			link = true
		}
		if m.Kind == "underline" {
			underline = true
		}
	}
	if !link || !underline {
		t.Fatalf("lost native marks: %+v", p.Marks)
	}
}

func TestUnicodeRangesAndSourceBinding(t *testing.T) {
	source := "א😀 **ב**"
	p, err := ProjectInline(source, false)
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256([]byte(source))
	if p.Contract != Contract || p.Codec != Codec || p.SourceSHA256 != hex.EncodeToString(sum[:]) || p.SourceUTF16 != 9 {
		t.Fatalf("bad binding: %+v", p)
	}
	if p.Text != "א😀 ב" || len(p.Marks) != 1 || p.Marks[0].Kind != "bold" || p.Marks[0].Start != 4 || p.Marks[0].End != 5 {
		t.Fatalf("UTF16 marks: %+v", p)
	}
}

func TestObjectReferenceRequiresExactNativeGrammar(t *testing.T) {
	p, err := ProjectInline(`[a](anytype://object?objectId=source) [b](anytype://object?objectId=source&spaceId=other)`, false)
	if err != nil {
		t.Fatal(err)
	}
	var objects, links int
	for _, m := range p.Marks {
		switch m.Kind {
		case "object":
			objects++
			if m.Parameter != "source" {
				t.Fatal(m)
			}
		case "link":
			links++
		}
	}
	if objects != 1 || links != 1 {
		t.Fatalf("must not guess reference identity: %+v", p.Marks)
	}
}

func TestLiteralCodeAndMalformedMarkup(t *testing.T) {
	source := "<u>not closed **literal**"
	p, err := ProjectInline(source, true)
	if err != nil || p.Text != source || len(p.Marks) != 0 || !p.Literal {
		t.Fatalf("literal changed: %+v %v", p, err)
	}
	if p, err := ProjectInline(source, false); err == nil || p.Contract != "" {
		t.Fatalf("invalid source admitted: %+v %v", p, err)
	}
}

func TestBoundedSource(t *testing.T) {
	for _, source := range []string{strings.Repeat("x", MaximumTextBytes+1), string([]byte{0xff})} {
		if p, err := ProjectInline(source, false); err != ErrLimit || p.Contract != "" {
			t.Fatalf("limit admitted: %v", err)
		}
	}
}
