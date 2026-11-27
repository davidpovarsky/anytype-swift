// Package bookmarkcreate contains the closed, local-only condition for an
// ordinary imported Bookmark create. A frame is a state precondition, never a
// credential, signed capability, idempotency key, or replicated operation.
package bookmarkcreate

import (
	"bytes"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"slices"
	"strings"
	"unicode/utf8"
)

const (
	Contract              = "pinkha-native-bookmark-create-v1"
	PresentationContract  = "pinkha-heart-native-bookmark-presentation-v1"
	MaxFrameBytes         = 65536
	MaxFrameEncodedBytes  = 87382
	MaxIDBytes            = 1024
	MaxCollections        = 128
	MaxDependencies       = 129
	MaxHeadsPerDependency = 64
	MaxHeads              = 512
	MaxGenerationBytes    = 256
)

var (
	ErrInvalid    = errors.New("bookmark create: invalid closed frame or input")
	ErrChanged    = errors.New("bookmark create: selected definition state changed")
	ErrIneligible = errors.New("bookmark create: current definitions are ineligible")
)

type Dependency struct {
	ObjectID string   `json:"objectId"`
	Heads    []string `json:"heads"`
}

// StaticOwner binds immutable, registered Collection definitions too. These
// have no tree heads, but a later executable must not silently substitute a
// different compiled descriptor while accepting an old frame.
type StaticOwner struct {
	ObjectID string `json:"objectId"`
	SHA256   string `json:"sha256"`
}

type Frame struct {
	Contract        string        `json:"contract"`
	Version         int           `json:"version"`
	AccountID       string        `json:"accountId"`
	SpaceID         string        `json:"spaceId"`
	StoreGeneration string        `json:"storeGeneration"`
	TypeID          string        `json:"typeId"`
	Collections     []string      `json:"collections"`
	PropertyOwnerID string        `json:"propertyOwnerId"`
	PropertyID      string        `json:"propertyId"`
	TypeSHA256      string        `json:"typeSHA256"`
	OwnerSHA256     string        `json:"ownerSHA256"`
	PropertySHA256  string        `json:"propertySHA256"`
	Dependencies    []Dependency  `json:"dependencies"`
	StaticOwners    []StaticOwner `json:"staticOwners"`
}

// Response is intentionally small and closed. Descriptor eligibility is
// checked by the native engine; the opaque frame cannot confer authority.
type Response struct {
	Contract        string   `json:"contract"`
	Version         int      `json:"version"`
	AccountID       string   `json:"accountId"`
	SpaceID         string   `json:"spaceId"`
	TypeID          string   `json:"typeId"`
	Collections     []string `json:"collections"`
	PropertyOwnerID string   `json:"propertyOwnerId"`
	PropertyID      string   `json:"propertyId"`
	CanWrite        bool     `json:"canWrite"`
	Frame           string   `json:"frame"`
}

func ValidText(value string, limit int) bool {
	return value != "" && len(value) <= limit && utf8.ValidString(value) && !strings.ContainsRune(value, 0)
}

func ValidID(value string) bool { return ValidText(value, MaxIDBytes) }

// Current native graph/account IDs are printable ASCII CIDs/base58 or
// registered slugs, matching the existing Host object-identity contract.
func ValidObjectID(value string) bool {
	if !ValidID(value) {
		return false
	}
	for i := 0; i < len(value); i++ {
		if value[i] < 0x21 || value[i] > 0x7e {
			return false
		}
	}
	return true
}

func validDigest(value string) bool {
	if len(value) != 64 || strings.ToLower(value) != value {
		return false
	}
	_, err := hex.DecodeString(value)
	return err == nil
}

func sortedUnique(values []string, limit int) bool {
	if values == nil || len(values) > limit {
		return false
	}
	for i, value := range values {
		if !ValidObjectID(value) || (i > 0 && values[i-1] >= value) {
			return false
		}
	}
	return true
}

// NormalizeCollections is only for the engine's read request. Creation never
// normalizes a caller's condition or opts to make a mismatched intent pass.
func NormalizeCollections(requested []string, propertyOwnerID string) ([]string, error) {
	if len(requested) > MaxCollections || !ValidObjectID(propertyOwnerID) {
		return nil, ErrInvalid
	}
	result := make([]string, 0, len(requested)+1)
	for _, id := range requested {
		if !ValidObjectID(id) || id == "bin" || id == "template" {
			return nil, ErrInvalid
		}
		result = append(result, id)
	}
	result = append(result, propertyOwnerID)
	slices.Sort(result)
	result = slices.Compact(result)
	if len(result) > MaxCollections {
		return nil, ErrInvalid
	}
	return result, nil
}

func (f Frame) Validate() error {
	if f.Contract != Contract || f.Version != 1 || !ValidObjectID(f.AccountID) || !ValidObjectID(f.SpaceID) ||
		!ValidText(f.StoreGeneration, MaxGenerationBytes) || !ValidObjectID(f.TypeID) ||
		!ValidObjectID(f.PropertyOwnerID) || f.PropertyOwnerID == f.TypeID || f.PropertyOwnerID == "any" ||
		!ValidID(f.PropertyID) || !sortedUnique(f.Collections, MaxCollections) ||
		!slices.Contains(f.Collections, f.PropertyOwnerID) || slices.Contains(f.Collections, "bin") ||
		slices.Contains(f.Collections, "template") || slices.Contains(f.Collections, f.TypeID) ||
		!validDigest(f.TypeSHA256) || !validDigest(f.OwnerSHA256) || !validDigest(f.PropertySHA256) ||
		f.Dependencies == nil || len(f.Dependencies) < 2 || len(f.Dependencies) > MaxDependencies ||
		f.StaticOwners == nil || len(f.StaticOwners) > MaxCollections {
		return ErrInvalid
	}
	seen := make(map[string]bool, len(f.Dependencies)+len(f.StaticOwners))
	heads := 0
	for i, d := range f.Dependencies {
		if !ValidObjectID(d.ObjectID) || (i > 0 && f.Dependencies[i-1].ObjectID >= d.ObjectID) ||
			!sortedUnique(d.Heads, MaxHeadsPerDependency) || len(d.Heads) == 0 ||
			(d.ObjectID != f.TypeID && !slices.Contains(f.Collections, d.ObjectID)) {
			return ErrInvalid
		}
		seen[d.ObjectID] = true
		heads += len(d.Heads)
	}
	if heads > MaxHeads || !seen[f.TypeID] || !seen[f.PropertyOwnerID] {
		return ErrInvalid
	}
	for i, d := range f.StaticOwners {
		if !ValidObjectID(d.ObjectID) || (i > 0 && f.StaticOwners[i-1].ObjectID >= d.ObjectID) ||
			seen[d.ObjectID] || !slices.Contains(f.Collections, d.ObjectID) || !validDigest(d.SHA256) {
			return ErrInvalid
		}
		seen[d.ObjectID] = true
	}
	if len(seen) != len(f.Collections)+1 {
		return ErrInvalid
	}
	return nil
}

func Encode(f Frame) (string, error) {
	if err := f.Validate(); err != nil {
		return "", err
	}
	raw, err := json.Marshal(f)
	if err != nil || len(raw) > MaxFrameBytes {
		return "", ErrInvalid
	}
	return base64.RawURLEncoding.EncodeToString(raw), nil
}

func Decode(token string) (Frame, error) {
	var f Frame
	if token == "" || len(token) > MaxFrameEncodedBytes {
		return f, ErrInvalid
	}
	raw, err := base64.RawURLEncoding.Strict().DecodeString(token)
	if err != nil || len(raw) > MaxFrameBytes || !utf8.Valid(raw) || base64.RawURLEncoding.EncodeToString(raw) != token {
		return f, ErrInvalid
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if err := d.Decode(&f); err != nil {
		return Frame{}, ErrInvalid
	}
	if err := d.Decode(new(any)); err != io.EOF {
		return Frame{}, ErrInvalid
	}
	canonical, err := Encode(f)
	// A unique canonical serialization also rejects duplicate keys, omitted
	// required fields, case-folded field names, alternate escapes and numbers.
	if err != nil || canonical != token {
		return Frame{}, ErrInvalid
	}
	return f, nil
}
