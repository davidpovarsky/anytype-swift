package torahcutovercontract

import (
	"bytes"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"reflect"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

// ValidateSourceCoverage is a read-only verifier, not an association encoder.
// The application creates each fact with the existing shared Swift codec. This
// independent native boundary proves that those facts cover the actual retained
// property exactly, including unknown fields and exact decimal values.
func ValidateSourceCoverage(plan Plan) error {
	if _, err := plan.CanonicalBytes(); err != nil {
		return err
	}
	if !plan.ValuePresent || len(plan.LegacyValue) == 0 {
		if len(plan.Facts) != 0 {
			return ErrIncomplete
		}
		return nil
	}
	root, err := coverageObject(plan.LegacyValue)
	if err != nil {
		return err
	}
	version, ok := root["version"].(coverageNumber)
	if !ok || (version != (coverageNumber{"1", 0}) && version != (coverageNumber{"2", 0})) {
		return ErrInvalid
	}
	legacy := version.Coefficient == "1"
	arrayKey := "records"
	if legacy {
		arrayKey = "items"
	}
	values, ok := root[arrayKey].([]any)
	if !ok || len(values) > MaxFacts || len(values) != len(plan.Facts) {
		return ErrIncomplete
	}
	envelope := coverageUnknown(root, "version", arrayKey)
	records := map[string]map[string]any{}
	for _, value := range values {
		var record map[string]any
		if legacy {
			record = map[string]any{"spaceId": plan.SpaceID, "objectId": plan.ObjectID, "item": value}
		} else {
			record, ok = value.(map[string]any)
			if !ok {
				return ErrInvalid
			}
		}
		key, _, _, _, e := normalizeCoverageRecord(record, plan.SpaceID, plan.ObjectID)
		if e != nil {
			return e
		}
		if _, exists := records[key]; exists {
			return ErrConflict
		}
		records[key] = record
	}
	seen := map[string]bool{}
	for _, fact := range plan.Facts {
		actual, e := coverageObject(fact.Payload)
		if e != nil {
			return e
		}
		if actual["version"] != (coverageNumber{"2", 0}) {
			return ErrInvalid
		}
		one, isArray := actual["records"].([]any)
		if !isArray || len(one) != 1 || !reflect.DeepEqual(coverageUnknown(actual, "version", "records"), envelope) {
			return ErrIncomplete
		}
		record, isObject := one[0].(map[string]any)
		if !isObject {
			return ErrInvalid
		}
		key, block, provider, ref, e := normalizeCoverageRecord(record, plan.SpaceID, plan.ObjectID)
		if e != nil {
			return e
		}
		if seen[key] || record == nil || records[key] == nil || fact.BlockID != block ||
			fact.ProviderID != provider || fact.CanonicalRef != ref || !reflect.DeepEqual(records[key], record) {
			return ErrIncomplete
		}
		seen[key] = true
	}
	if len(seen) != len(records) {
		return ErrIncomplete
	}
	return nil
}

func coverageUnknown(object map[string]any, keys ...string) map[string]any {
	result := make(map[string]any, len(object))
	for key, value := range object {
		result[key] = value
	}
	for _, key := range keys {
		delete(result, key)
	}
	return result
}

// This is the documented Codable lens only. It does not discard unknown keys.
// Known optional nulls are omitted, source_quote is the supported old role,
// and known timestamps compare as exact RFC3339 instants. All other strings
// and all unknown values retain their exact decoded identity.
func normalizeCoverageRecord(record map[string]any, spaceID, objectID string) (key, block, provider, ref string, err error) {
	fail := func() (string, string, string, string, error) { return "", "", "", "", ErrInvalid }
	if record["spaceId"] != spaceID || record["objectId"] != objectID {
		return fail()
	}
	if value, exists := record["blockId"]; exists {
		if value == nil {
			delete(record, "blockId")
		} else {
			var ok bool
			block, ok = value.(string)
			if !ok || !Text(block, true, 1024) {
				return fail()
			}
		}
	}
	item, ok := record["item"].(map[string]any)
	if !ok {
		return fail()
	}
	required := []string{"id", "kind", "role", "providerID", "externalID", "canonicalKey", "labelHe"}
	for _, name := range required {
		if _, ok = item[name].(string); !ok {
			return fail()
		}
	}
	id := item["id"].(string)
	provider = item["providerID"].(string)
	ref = item["canonicalKey"].(string)
	if ref == "" {
		ref = item["externalID"].(string)
	}
	if id == "" || !Text(provider, true, 256) || !Text(ref, true, 4096) {
		return fail()
	}
	switch item["kind"] {
	case "ref", "topic", "word":
	default:
		return fail()
	}
	switch item["role"] {
	case "source_quote":
		item["role"] = "sourceQuote"
	case "context", "sourceQuote":
	default:
		return fail()
	}
	for _, name := range []string{"labelEn", "rawInput", "providerPayload", "createdAt", "updatedAt", "customMetadata"} {
		value, present := item[name]
		if !present {
			continue
		}
		if value == nil {
			delete(item, name)
			continue
		}
		if name == "customMetadata" {
			metadata, isObject := value.(map[string]any)
			if !isObject {
				return fail()
			}
			for _, field := range metadata {
				if _, ok = field.(string); !ok {
					return fail()
				}
			}
			if marker, exists := metadata["pinkha.semanticTextAnchor"]; exists {
				if block != "" || validateCoverageMarker(marker.(string), spaceID, objectID) != nil {
					return fail()
				}
			}
			continue
		}
		text, isString := value.(string)
		if !isString {
			return fail()
		}
		if name == "createdAt" || name == "updatedAt" {
			instant, e := time.Parse(time.RFC3339Nano, text)
			if e != nil {
				return fail()
			}
			fraction := ""
			if len(text) > 19 && (text[19] == '.' || text[19] == ',') {
				end := 20
				for end < len(text) && text[end] >= '0' && text[end] <= '9' {
					end++
				}
				fraction = strings.TrimRight(text[20:end], "0")
			}
			item[name] = coverageDate{Seconds: instant.Unix(), Fraction: fraction}
		}
	}
	// Length framing preserves unusual valid IDs without delimiter ambiguity.
	key = fmt.Sprintf("%d:%s%d:%s", len(block), block, len(id), id)
	return key, block, provider, ref, nil
}

func validateCoverageMarker(raw, spaceID, objectID string) error {
	if len(raw) > 4096 {
		return ErrInvalid
	}
	value, err := coverageObject([]byte(raw))
	if err != nil || value["version"] != (coverageNumber{"1", 0}) {
		return ErrInvalid
	}
	marker, ok := value["marker"].(string)
	if !ok {
		return ErrInvalid
	}
	prefix := "pinkha-anchor://v1/" + base64.RawURLEncoding.EncodeToString([]byte(spaceID)) + "/" +
		base64.RawURLEncoding.EncodeToString([]byte(objectID)) + "/"
	if !strings.HasPrefix(marker, prefix) {
		return ErrInvalid
	}
	uuid := strings.TrimPrefix(marker, prefix)
	if len(uuid) != 36 || uuid != strings.ToLower(uuid) || uuid[8] != '-' || uuid[13] != '-' || uuid[18] != '-' || uuid[23] != '-' {
		return ErrInvalid
	}
	rawID, e := hex.DecodeString(strings.ReplaceAll(uuid, "-", ""))
	if e != nil || len(rawID) != 16 {
		return ErrInvalid
	}
	return nil
}

type coverageDate struct {
	Seconds  int64
	Fraction string
}

type coverageNumber struct {
	Coefficient string
	Scale       int64
}

func coverageDecimal(raw string) (coverageNumber, error) {
	negative := strings.HasPrefix(raw, "-")
	raw = strings.TrimPrefix(raw, "-")
	parts := strings.FieldsFunc(raw, func(r rune) bool { return r == 'e' || r == 'E' })
	digits := strings.ReplaceAll(parts[0], ".", "")
	fraction := 0
	if dot := strings.IndexByte(parts[0], '.'); dot >= 0 {
		fraction = len(parts[0]) - dot - 1
	}
	digits = strings.TrimLeft(digits, "0")
	if digits == "" {
		return coverageNumber{"0", 0}, nil
	}
	exponent := int64(0)
	if len(parts) == 2 {
		expText := strings.TrimLeft(strings.TrimLeft(parts[1], "+-"), "0")
		if len(expText) > 8 {
			return coverageNumber{}, ErrInvalid
		}
		if expText != "" {
			var err error
			exponent, err = strconv.ParseInt(expText, 10, 64)
			if err != nil {
				return coverageNumber{}, ErrInvalid
			}
			if strings.HasPrefix(parts[1], "-") {
				exponent = -exponent
			}
		}
	}
	scale := exponent - int64(fraction)
	for strings.HasSuffix(digits, "0") {
		digits = strings.TrimSuffix(digits, "0")
		scale++
	}
	if negative {
		digits = "-" + digits
	}
	return coverageNumber{digits, scale}, nil
}

func coverageObject(raw []byte) (map[string]any, error) {
	if !utf8.Valid(raw) || len(raw) == 0 || len(raw) > MaxLegacyBytes || !json.Valid(raw) || !coverageSurrogates(raw) {
		return nil, ErrInvalid
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	value, err := coverageValue(decoder, 0)
	if err != nil {
		return nil, err
	}
	if _, err = decoder.Token(); err != io.EOF {
		return nil, ErrInvalid
	}
	object, ok := value.(map[string]any)
	if !ok {
		return nil, ErrInvalid
	}
	return object, nil
}
func coverageValue(decoder *json.Decoder, depth int) (any, error) {
	if depth > 512 {
		return nil, ErrInvalid
	}
	token, err := decoder.Token()
	if err != nil {
		return nil, err
	}
	switch token := token.(type) {
	case json.Delim:
		switch token {
		case '{':
			object := map[string]any{}
			for decoder.More() {
				key, e := decoder.Token()
				if e != nil {
					return nil, e
				}
				name, ok := key.(string)
				if !ok {
					return nil, ErrInvalid
				}
				if _, exists := object[name]; exists {
					return nil, ErrInvalid
				}
				value, e := coverageValue(decoder, depth+1)
				if e != nil {
					return nil, e
				}
				object[name] = value
			}
			if end, e := decoder.Token(); e != nil || end != json.Delim('}') {
				return nil, ErrInvalid
			}
			return object, nil
		case '[':
			array := []any{}
			for decoder.More() {
				value, e := coverageValue(decoder, depth+1)
				if e != nil {
					return nil, e
				}
				array = append(array, value)
			}
			if end, e := decoder.Token(); e != nil || end != json.Delim(']') {
				return nil, ErrInvalid
			}
			return array, nil
		default:
			return nil, ErrInvalid
		}
	case json.Number:
		return coverageDecimal(string(token))
	case string, bool, nil:
		return token, nil
	default:
		return nil, ErrInvalid
	}
}

// encoding/json accepts unmatched escaped surrogates by replacement. The shared
// codec must not gain a different string identity through that normalization.
func coverageSurrogates(raw []byte) bool {
	inString := false
	for i := 0; i < len(raw); i++ {
		if raw[i] == '"' {
			inString = !inString
			continue
		}
		if !inString || raw[i] != '\\' {
			continue
		}
		i++
		if i >= len(raw) {
			return false
		}
		if raw[i] != 'u' {
			continue
		}
		if i+4 >= len(raw) {
			return false
		}
		value, err := strconv.ParseUint(string(raw[i+1:i+5]), 16, 16)
		if err != nil {
			return false
		}
		i += 4
		if value >= 0xDC00 && value <= 0xDFFF {
			return false
		}
		if value >= 0xD800 && value <= 0xDBFF {
			if i+6 >= len(raw) || raw[i+1] != '\\' || raw[i+2] != 'u' {
				return false
			}
			low, e := strconv.ParseUint(string(raw[i+3:i+7]), 16, 16)
			if e != nil || low < 0xDC00 || low > 0xDFFF {
				return false
			}
			i += 6
		}
	}
	return !inString
}
