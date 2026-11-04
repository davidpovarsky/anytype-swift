// Package torahderived implements the read-only canonical projection shared by
// the native Heart indexer and its Swift/Go compatibility fixtures.
package torahderived

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"golang.org/x/text/unicode/norm"
)

type Kind string

const (
	Ref   Kind = "ref"
	Topic Kind = "topic"
	Word  Kind = "word"
)

var ErrMalformed = errors.New("malformed canonical data")
var ErrUnsupported = errors.New("unsupported canonical version")
var ErrBinding = errors.New("invalid Space binding")
var ErrIneligible = errors.New("ineligible document")

// Binding contains validated native identifiers, never human display names.
type Binding struct {
	SpaceID        string
	CanonicalKey   string
	WritingTypeIDs [3]string
	Generation     string
}

type Input struct {
	SpaceID    string
	ObjectID   string
	TypeID     string
	IsTemplate bool
	IsDeleted  bool
	IsArchived bool
	Raw        []byte
}

type Projection struct {
	Sources         []string                `json:"sources"`
	Topics          []string                `json:"topics"`
	Words           []string                `json:"words"`
	CanonicalSHA256 string                  `json:"canonicalSHA256"`
	Labels          map[string]DisplayLabel `json:"labels,omitempty"`
}

// Display labels are a rebuildable local cache, never synced association data.
type DisplayLabel struct {
	Hebrew  string `json:"he"`
	English string `json:"en,omitempty"`
}

// Identity matches Swift's NFC identity and length-prefixes UTF-8 bytes.
// The version prefix allows a future local rebuild without rewriting user data.
func Identity(kind Kind, provider, canonical, external string) string {
	if canonical == "" {
		canonical = external
	}
	parts := []string{string(kind), provider, canonical}
	for i, part := range parts {
		part = norm.NFC.String(part)
		parts[i] = fmt.Sprintf("%d:%s", len(part), part)
	}
	return "torah1|" + strings.Join(parts, "|")
}

func (b Binding) Validate() error {
	if b.SpaceID == "" || b.CanonicalKey == "" || b.Generation == "" || IsLocalKey(b.CanonicalKey) {
		return ErrBinding
	}
	seen := map[string]bool{}
	for _, id := range b.WritingTypeIDs {
		id = norm.NFC.String(id)
		if id == "" || seen[id] {
			return ErrBinding
		}
		seen[id] = true
	}
	return nil
}

func Project(b Binding, in Input) (Projection, error) {
	if err := b.Validate(); err != nil {
		return Projection{}, err
	}
	eligible := false
	for _, id := range b.WritingTypeIDs {
		eligible = eligible || exact(id, in.TypeID)
	}
	if !exact(b.SpaceID, in.SpaceID) || in.ObjectID == "" || !eligible || in.IsTemplate || in.IsDeleted || in.IsArchived {
		return Projection{}, ErrIneligible
	}
	hash := sha256.Sum256(in.Raw)
	result := Projection{Sources: []string{}, Topics: []string{}, Words: []string{}, Labels: map[string]DisplayLabel{}, CanonicalSHA256: hex.EncodeToString(hash[:])}
	// The current repository treats absent or empty native longText as no links.
	if len(in.Raw) == 0 {
		return result, nil
	}
	if !utf8.Valid(in.Raw) {
		return Projection{}, ErrMalformed
	}
	envelope, err := object(in.Raw)
	if err != nil {
		return Projection{}, err
	}
	var version int
	if err = required(envelope, "version", &version); err != nil {
		return Projection{}, err
	}
	var records []record
	switch version {
	case 1:
		var items []json.RawMessage
		if err = required(envelope, "items", &items); err != nil {
			return Projection{}, err
		}
		for _, item := range items {
			records = append(records, record{SpaceID: in.SpaceID, ObjectID: in.ObjectID, Item: item})
		}
	case 2:
		var rawRecords []json.RawMessage
		if err = required(envelope, "records", &rawRecords); err != nil {
			return Projection{}, err
		}
		for _, raw := range rawRecords {
			fields, e := object(raw)
			if e != nil {
				return Projection{}, e
			}
			var r record
			if e = required(fields, "spaceId", &r.SpaceID); e != nil {
				return Projection{}, e
			}
			if e = required(fields, "objectId", &r.ObjectID); e != nil {
				return Projection{}, e
			}
			if v := fields["blockId"]; v != nil && string(v) != "null" {
				var block string
				if e = json.Unmarshal(v, &block); e != nil {
					return Projection{}, ErrMalformed
				}
				r.BlockID = &block
			}
			if e = required(fields, "item", &r.Item); e != nil {
				return Projection{}, e
			}
			records = append(records, r)
		}
	default:
		return Projection{}, fmt.Errorf("%w: %d", ErrUnsupported, version)
	}
	ids, identities := map[string]bool{}, map[string]bool{}
	for _, r := range records {
		item, err := decodeItem(r.Item)
		if err != nil {
			return Projection{}, err
		}
		if !exact(r.SpaceID, in.SpaceID) || !exact(r.ObjectID, in.ObjectID) || r.BlockID != nil || item.Role != "context" || strings.HasPrefix(item.CanonicalKey, "anytype-note:") {
			continue
		}
		identity := Identity(item.Kind, item.ProviderID, item.CanonicalKey, item.ExternalID)
		id := norm.NFC.String(item.ID)
		if ids[id] || identities[identity] {
			continue
		}
		ids[id], identities[identity] = true, true
		result.Labels[identity] = DisplayLabel{Hebrew: item.LabelHe, English: item.LabelEn}
		switch item.Kind {
		case Ref:
			result.Sources = append(result.Sources, identity)
		case Topic:
			result.Topics = append(result.Topics, identity)
		case Word:
			result.Words = append(result.Words, identity)
		}
	}
	sort.Strings(result.Sources)
	sort.Strings(result.Topics)
	sort.Strings(result.Words)
	return result, nil
}

type record struct {
	SpaceID  string
	ObjectID string
	BlockID  *string
	Item     json.RawMessage
}

type item struct {
	ID           string
	Kind         Kind
	Role         string
	ProviderID   string
	CanonicalKey string
	ExternalID   string
	LabelHe      string
	LabelEn      string
}

func decodeItem(raw json.RawMessage) (item, error) {
	fields, err := object(raw)
	if err != nil {
		return item{}, err
	}
	var value item
	for _, f := range []struct {
		name   string
		target any
	}{
		{"id", &value.ID}, {"kind", &value.Kind}, {"role", &value.Role},
		{"providerID", &value.ProviderID}, {"canonicalKey", &value.CanonicalKey},
		{"externalID", &value.ExternalID}, {"labelHe", &value.LabelHe},
	} {
		if err := required(fields, f.name, f.target); err != nil {
			return item{}, err
		}
	}
	if value.Kind != Ref && value.Kind != Topic && value.Kind != Word {
		return item{}, ErrMalformed
	}
	if value.Role == "source_quote" {
		value.Role = "sourceQuote"
	}
	if value.Role != "context" && value.Role != "sourceQuote" {
		return item{}, ErrMalformed
	}
	if value.ID == "" || value.ProviderID == "" || (value.CanonicalKey == "" && value.ExternalID == "") {
		return item{}, ErrMalformed
	}
	// Validate the known optional fields as Swift's existing codec does. They
	// never participate in identity, but invalid typed data must fail closed.
	for _, key := range []string{"labelEn", "rawInput", "providerPayload"} {
		if raw := fields[key]; raw != nil && string(raw) != "null" {
			var text string
			if json.Unmarshal(raw, &text) != nil {
				return item{}, ErrMalformed
			}
			if key == "labelEn" {
				value.LabelEn = text
			}
		}
	}
	for _, key := range []string{"createdAt", "updatedAt"} {
		if raw := fields[key]; raw != nil && string(raw) != "null" {
			var timestamp string
			if json.Unmarshal(raw, &timestamp) != nil {
				return item{}, ErrMalformed
			}
			if _, err := time.Parse(time.RFC3339Nano, timestamp); err != nil {
				return item{}, ErrMalformed
			}
		}
	}
	if raw := fields["customMetadata"]; raw != nil && string(raw) != "null" {
		var metadata map[string]json.RawMessage
		if json.Unmarshal(raw, &metadata) != nil {
			return item{}, ErrMalformed
		}
		for _, rawValue := range metadata {
			var text string
			if string(rawValue) == "null" || json.Unmarshal(rawValue, &text) != nil {
				return item{}, ErrMalformed
			}
		}
	}
	return value, nil
}

func object(raw []byte) (map[string]json.RawMessage, error) {
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil || fields == nil {
		return nil, ErrMalformed
	}
	return fields, nil
}

func required(fields map[string]json.RawMessage, key string, value any) error {
	raw, exists := fields[key]
	if !exists || string(raw) == "null" {
		return ErrMalformed
	}
	if err := json.Unmarshal(raw, value); err != nil {
		return ErrMalformed
	}
	return nil
}

func exact(a, b string) bool { return norm.NFC.String(a) == norm.NFC.String(b) }
