package torahcutovercontract

import (
	"bytes"
	"encoding/json"
	"os"
	"strings"
	"testing"
)

type sharedCodecVector struct {
	Name      string `json:"name"`
	Wire      []byte `json:"wire"`
	Canonical []byte `json:"canonical"`
}

func sharedVectors(t *testing.T) []sharedCodecVector {
	t.Helper()
	path := os.Getenv("PINKHA_CUTOVER_VECTORS")
	data, err := os.ReadFile(path)
	if err != nil || len(data) == 0 || len(data) > 2<<20 {
		t.Fatalf("actual shared codec artifact: %v", err)
	}
	var vectors []sharedCodecVector
	if err = json.Unmarshal(data, &vectors); err != nil || len(vectors) != 9 {
		t.Fatalf("actual shared codec vectors: %v", err)
	}
	return vectors
}
func sharedPlan(t *testing.T, name string) Plan {
	t.Helper()
	for _, vector := range sharedVectors(t) {
		if vector.Name != name {
			continue
		}
		var plan Plan
		decoder := json.NewDecoder(bytes.NewReader(vector.Wire))
		decoder.DisallowUnknownFields()
		if err := decoder.Decode(&plan); err != nil {
			t.Fatal(err)
		}
		return plan
	}
	t.Fatal("missing shared vector " + name)
	return Plan{}
}
func requireCoverageRefusal(t *testing.T, plan Plan) {
	t.Helper()
	if err := ValidateSourceCoverage(plan); err == nil {
		t.Fatal("incomplete or different source accepted")
	}
}

func TestSourceCoverageUsesActualSharedCodecAndCanonicalFraming(t *testing.T) {
	seen := map[string]bool{}
	for _, vector := range sharedVectors(t) {
		t.Run(vector.Name, func(t *testing.T) {
			if seen[vector.Name] {
				t.Fatal("duplicate vector")
			}
			seen[vector.Name] = true
			plan := sharedPlan(t, vector.Name)
			if err := ValidateSourceCoverage(plan); err != nil {
				t.Fatal(err)
			}
			frame, err := plan.CanonicalBytes()
			if err != nil || !bytes.Equal(frame, vector.Canonical) {
				t.Fatalf("actual Swift/native framing differs: %v", err)
			}
		})
	}
}

func TestSourceCoverageRefusesMissingDuplicateAndForeignFacts(t *testing.T) {
	for _, name := range []string{"missing", "duplicate", "invented", "foreign-owner", "wrong-provider", "wrong-reference", "wrong-block"} {
		t.Run(name, func(t *testing.T) {
			p := sharedPlan(t, "blocks-order")
			switch name {
			case "missing":
				p.Facts = p.Facts[:1]
			case "duplicate":
				p.Facts[1] = p.Facts[0]
			case "invented":
				p.Facts[0].Payload = bytes.Replace(p.Facts[0].Payload, []byte("\"id\":\"first\""), []byte("\"id\":\"invented\""), 1)
				if !bytes.Contains(p.Facts[0].Payload, []byte("invented")) {
					p.Facts[0].Payload = bytes.Replace(p.Facts[0].Payload, []byte("\"id\":\"second\""), []byte("\"id\":\"invented\""), 1)
				}
			case "foreign-owner":
				p.Facts[0].Payload = bytes.ReplaceAll(p.Facts[0].Payload, []byte("cutover-document"), []byte("foreign-document"))
			case "wrong-provider":
				p.Facts[0].ProviderID = "other"
			case "wrong-reference":
				p.Facts[0].CanonicalRef = "Exodus.1.1"
			case "wrong-block":
				p.Facts[0].BlockID = "other-block"
			}
			requireCoverageRefusal(t, p)
		})
	}
}

func TestSourceCoverageRefusesUnknownFieldLossAtEveryLevel(t *testing.T) {
	for _, field := range []string{"outer", "recordFuture", "future"} {
		t.Run(field, func(t *testing.T) {
			p := sharedPlan(t, "document-unknown")
			object, err := coverageObject(p.Facts[0].Payload)
			if err != nil {
				t.Fatal(err)
			}
			// Rename rather than use a second encoder: no decimal conversion can
			// mask the exact original field-loss condition.
			needle := []byte("\"" + field + "\":")
			if !bytes.Contains(p.Facts[0].Payload, needle) {
				t.Fatal("fixture field absent")
			}
			p.Facts[0].Payload = bytes.Replace(p.Facts[0].Payload, needle, []byte("\"discarded_"+field+"\":"), 1)
			if object == nil {
				t.Fatal("fixture")
			}
			requireCoverageRefusal(t, p)
		})
	}
}

func TestSourceCoverageExactNumbersDuplicateKeysAndUnicodeRefuse(t *testing.T) {
	for _, name := range []string{"rounded-number", "escaped-duplicate", "unpaired-surrogate", "date-precision"} {
		t.Run(name, func(t *testing.T) {
			p := sharedPlan(t, "document-unknown")
			before := append([]byte{}, p.LegacyValue...)
			switch name {
			case "rounded-number":
				p.LegacyValue = bytes.Replace(p.LegacyValue, []byte("9007199254740992"), []byte("9007199254740993"), 1)
			case "escaped-duplicate":
				p.LegacyValue = bytes.Replace(p.LegacyValue, []byte("\"id\":\"first\""), []byte("\"id\":\"first\",\"i\\u0064\":\"second\""), 1)
			case "unpaired-surrogate":
				p.LegacyValue = bytes.Replace(p.LegacyValue, []byte("\"outer\":\"exact\""), []byte("\"outer\":\"\\ud800\""), 1)
			case "date-precision":
				p.LegacyValue = bytes.Replace(p.LegacyValue, []byte(".125Z"), []byte(".1250000001Z"), 1)
			}
			if bytes.Equal(before, p.LegacyValue) {
				t.Fatal("mutation did not reach actual fixture")
			}
			requireCoverageRefusal(t, p)
		})
	}
}

func TestSourceCoverageMarkerCannotMoveToAnotherOwnerOrBlock(t *testing.T) {
	for _, name := range []string{"foreign-marker", "block-owned", "future-version"} {
		t.Run(name, func(t *testing.T) {
			p := sharedPlan(t, "semantic-owner")
			var source map[string]any
			if err := json.Unmarshal(p.LegacyValue, &source); err != nil {
				t.Fatal(err)
			}
			record := source["records"].([]any)[0].(map[string]any)
			item := record["item"].(map[string]any)
			metadata := item["customMetadata"].(map[string]any)
			marker := metadata["pinkha.semanticTextAnchor"].(string)
			switch name {
			case "foreign-marker":
				marker = strings.Replace(marker, "Y3V0b3Zlci1kb2N1bWVudA", "Zm9yZWlnbi1kb2N1bWVudA", 1)
			case "block-owned":
				record["blockId"] = "actual-block"
				p.Facts[0].BlockID = "actual-block"
			case "future-version":
				marker = strings.Replace(marker, "\"version\":1", "\"version\":2", 1)
			}
			metadata["pinkha.semanticTextAnchor"] = marker
			raw, err := json.Marshal(source)
			if err != nil {
				t.Fatal(err)
			}
			p.LegacyValue = raw
			p.Facts[0].Payload = append([]byte{}, raw...)
			requireCoverageRefusal(t, p)
		})
	}
}

func TestSourceCoverageRetainsUnknownReservedMetadataWithoutRewriting(t *testing.T) {
	p := sharedPlan(t, "semantic-owner")
	var source map[string]any
	if err := json.Unmarshal(p.LegacyValue, &source); err != nil {
		t.Fatal(err)
	}
	record := source["records"].([]any)[0].(map[string]any)
	metadata := record["item"].(map[string]any)["customMetadata"].(map[string]any)
	marker := metadata["pinkha.semanticTextAnchor"].(string)
	marker = strings.Replace(marker, "{", "{\"future\":\"retained\",", 1)
	metadata["pinkha.semanticTextAnchor"] = marker
	raw, err := json.Marshal(source)
	if err != nil {
		t.Fatal(err)
	}
	p.LegacyValue = raw
	p.Facts[0].Payload = append([]byte{}, raw...)
	if err = ValidateSourceCoverage(p); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(p.LegacyValue, raw) || !bytes.Contains(p.Facts[0].Payload, []byte("retained")) {
		t.Fatal("source rewritten")
	}
}

func TestSourceCoverageEmptySourceCannotInventFacts(t *testing.T) {
	for _, name := range []string{"missing", "present-empty", "empty-with-unknown"} {
		t.Run(name, func(t *testing.T) {
			p := sharedPlan(t, name)
			p.Facts = sharedPlan(t, "document-unknown").Facts
			requireCoverageRefusal(t, p)
		})
	}
}

func TestSourceCoverageMalformedLegacyDoesNotBecomeEmpty(t *testing.T) {
	for _, raw := range []string{" ", "null", "{\"version\":3,\"records\":[]}", "{\"version\":2,\"records\":null}", "{\"version\":2,\"records\":[],\"records\":[]}"} {
		p := sharedPlan(t, "present-empty")
		p.LegacyValue = []byte(raw)
		requireCoverageRefusal(t, p)
	}
}
