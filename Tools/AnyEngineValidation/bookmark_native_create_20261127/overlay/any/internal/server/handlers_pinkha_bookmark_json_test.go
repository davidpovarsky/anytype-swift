package server

import (
	"strings"
	"testing"
)

func TestBookmarkCreateJSONRefusesDuplicateNestedAndUnboundedInputs(t *testing.T) {
	for _, valid := range []string{`{"typeId":"a","collections":[]}`, `{"initialProperties":{"owner":{"url":"https://example.test/"}},"bookmarkDefinitionFrame":"opaque"}`} {
		if err := validateBookmarkJSON([]byte(valid)); err != nil {
			t.Fatal(err)
		}
	}
	for _, invalid := range []string{
		`{"typeId":"a","typeId":"b","collections":[]}`,
		`{"initialProperties":{"owner":{"url":"first","\u0075rl":"second"}}}`,
		`{"bookmarkDefinitionFrame":"a","bookmarkDefinitionFrame":"a"}`,
		`{} {}`, `{"a":`, strings.Repeat("[", 34) + "0" + strings.Repeat("]", 34),
		`{"a":"` + strings.Repeat("x", maxBookmarkCreateRequestBytes) + `"}`,
		string([]byte{'{', '"', 'a', '"', ':', '"', 0xff, '"', '}'}),
	} {
		if err := validateBookmarkJSON([]byte(invalid)); err == nil {
			t.Fatal("invalid conditional request accepted")
		}
	}
}

func TestBookmarkCreateDoesNotWidenStockCreateVocabulary(t *testing.T) {
	for _, field := range objectCreateFields {
		if field == "bookmarkDefinitionFrame" {
			t.Fatal("stock ordinary object create unexpectedly accepts the Pinkha condition")
		}
	}
}
