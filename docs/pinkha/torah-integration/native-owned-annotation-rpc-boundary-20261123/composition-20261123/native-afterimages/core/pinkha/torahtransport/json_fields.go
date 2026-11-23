package torahtransport

import (
	"bytes"
	"encoding/json"
	"fmt"
	"sort"
)

type field struct {
	name       string
	start, end int
	raw        json.RawMessage
}
type replacement struct {
	start, end int
	value      string
}

// Decoder offsets retain all bytes outside explicitly replaced identity values,
// including unknown fields, object order, spacing and escaped text.
func fields(data []byte) ([]field, error) {
	decoder := json.NewDecoder(bytes.NewReader(data))
	token, err := decoder.Token()
	if err != nil || token != json.Delim('{') {
		return nil, fmt.Errorf("expected JSON object")
	}
	var result []field
	seen := map[string]bool{}
	for decoder.More() {
		token, err = decoder.Token()
		if err != nil {
			return nil, err
		}
		name, ok := token.(string)
		if !ok {
			return nil, fmt.Errorf("invalid JSON field")
		}
		if seen[name] {
			return nil, fmt.Errorf("ambiguous JSON field")
		}
		seen[name] = true
		var raw json.RawMessage
		if err = decoder.Decode(&raw); err != nil {
			return nil, err
		}
		end := int(decoder.InputOffset())
		result = append(result, field{name: name, start: end - len(raw), end: end, raw: raw})
	}
	if _, err = decoder.Token(); err != nil {
		return nil, err
	}
	return result, nil
}

func replace(data []byte, changes []replacement) ([]byte, error) {
	sort.Slice(changes, func(i, j int) bool { return changes[i].start < changes[j].start })
	var output bytes.Buffer
	cursor := 0
	for _, change := range changes {
		if change.start < cursor || change.end > len(data) {
			return nil, fmt.Errorf("overlapping identity replacement")
		}
		encoded, err := json.Marshal(change.value)
		if err != nil {
			return nil, err
		}
		output.Write(data[cursor:change.start])
		output.Write(encoded)
		cursor = change.end
	}
	output.Write(data[cursor:])
	return output.Bytes(), nil
}

func remapCanonical(raw []byte, sourceSpace, sourceObject, targetSpace, targetObject string) ([]byte, error) {
	var header struct {
		Version int `json:"version"`
	}
	if json.Unmarshal(raw, &header) != nil || header.Version != 2 {
		return raw, nil
	}
	root, err := fields(raw)
	if err != nil {
		return raw, nil
	}
	var changes []replacement
	for _, property := range root {
		if property.name != "records" {
			continue
		}
		decoder := json.NewDecoder(bytes.NewReader(property.raw))
		token, err := decoder.Token()
		if err != nil || token != json.Delim('[') {
			return raw, nil
		}
		for decoder.More() {
			var record json.RawMessage
			if err = decoder.Decode(&record); err != nil {
				return raw, nil
			}
			base := property.start + int(decoder.InputOffset()) - len(record)
			var location struct {
				SpaceID  string `json:"spaceId"`
				ObjectID string `json:"objectId"`
			}
			if json.Unmarshal(record, &location) != nil || location.SpaceID != sourceSpace || location.ObjectID != sourceObject {
				continue
			}
			members, err := fields(record)
			if err != nil {
				return raw, nil
			}
			for _, member := range members {
				target := ""
				if member.name == "spaceId" {
					target = targetSpace
				}
				if member.name == "objectId" {
					target = targetObject
				}
				if target != "" {
					changes = append(changes, replacement{base + member.start, base + member.end, target})
				}
			}
		}
	}
	return replace(raw, changes)
}
