// Package torahops implements an experimental immutable operation projection on
// Heart's StoreState. It is not registered as an object type or exposed over RPC.
package torahops

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

const (
	Version            = 1
	MaxPayloadBytes    = 64 * 1024
	MaxObservedClaims  = 256
	MaxVariants        = 256
	MaxWireBytes       = 256 * 1024
	CollectionName     = "_pinkha_torah_claims_v1"
	receiptsCollection = "_pinkha_torah_receipts_v1"
)

var (
	ErrInvalid            = errors.New("invalid torah operation")
	ErrUnsupportedVersion = errors.New("unsupported torah operation version")
	ErrReadLimit          = errors.New("torah operation read limit exceeded")
)

type Kind string

const (
	Add     Kind = "add"
	Remove  Kind = "remove"
	Replace Kind = "replace"
)

type Target struct {
	ObjectID string `json:"objectId"`
	BlockID  string `json:"blockId"`
}

type Source struct {
	ProviderID   string `json:"providerId"`
	CanonicalRef string `json:"canonicalRef"`
}

// Operation uses a fixed binary envelope for content identity. Payload is opaque
// bytes, not a JSON value: callers must reuse the exact bytes on retry. Semantic
// provider/schema validation belongs to the future native host, not this store.
type Operation struct {
	Version     uint32   `json:"version"`
	SpaceID     string   `json:"spaceId"`
	OperationID string   `json:"operationId"`
	AuthorID    string   `json:"authorId"`
	Kind        Kind     `json:"kind"`
	Target      Target   `json:"target"`
	Source      Source   `json:"source"`
	Payload     []byte   `json:"payload"`
	Observed    []string `json:"observed"`
}

type wireClaim struct {
	Operation Operation `json:"operation"`
	Digest    string    `json:"digest"`
}

// Claim is immutable content. Native replay provenance is stored separately,
// because retries may carry another ACL head without changing operation bytes.
type Claim struct {
	ID        string
	Digest    string
	Operation Operation
}

func validText(value string, required bool, limit int) bool {
	return (!required || len(value) != 0) && len(value) <= limit &&
		utf8.ValidString(value) && !strings.ContainsRune(value, 0)
}

func validHex(value string, size int) bool {
	if len(value) != size*2 || value != strings.ToLower(value) {
		return false
	}
	_, err := hex.DecodeString(value)
	return err == nil
}

func validClaimID(value string) bool {
	return len(value) == 129 && value[64] == '/' &&
		validHex(value[:64], 32) && validHex(value[65:], 32)
}

// CanonicalBytes returns domain/version/length-prefixed bytes in fixed field
// order. No Unicode normalization or JSON interpretation is performed. Observed
// claim IDs are a set: input order and duplicate references do not change identity.
func (op Operation) CanonicalBytes() ([]byte, error) {
	if op.Version != Version {
		return nil, ErrUnsupportedVersion
	}
	if !validText(op.SpaceID, true, 1024) || !validHex(op.OperationID, 16) ||
		!validText(op.AuthorID, true, 1024) ||
		!validText(op.Target.ObjectID, true, 1024) || !validText(op.Target.BlockID, false, 1024) ||
		!validText(op.Source.ProviderID, false, 256) || !validText(op.Source.CanonicalRef, false, 4096) ||
		len(op.Payload) > MaxPayloadBytes || len(op.Observed) > MaxObservedClaims {
		return nil, ErrInvalid
	}
	switch op.Kind {
	case Add:
		if len(op.Observed) != 0 || len(op.Payload) == 0 || op.Source.ProviderID == "" || op.Source.CanonicalRef == "" {
			return nil, ErrInvalid
		}
	case Remove:
		if len(op.Observed) == 0 || len(op.Payload) != 0 || op.Source != (Source{}) {
			return nil, ErrInvalid
		}
	case Replace:
		if len(op.Observed) == 0 || len(op.Payload) == 0 || op.Source.ProviderID == "" || op.Source.CanonicalRef == "" {
			return nil, ErrInvalid
		}
	default:
		return nil, ErrInvalid
	}
	observed := normalizedObserved(op.Observed)
	for _, id := range observed {
		if !validClaimID(id) {
			return nil, ErrInvalid
		}
	}
	buf := bytes.NewBufferString("pinkha-t2-operation\x00")
	_ = binary.Write(buf, binary.BigEndian, op.Version)
	for _, value := range []string{op.SpaceID, op.OperationID, op.AuthorID, string(op.Kind),
		op.Target.ObjectID, op.Target.BlockID, op.Source.ProviderID, op.Source.CanonicalRef} {
		putBytes(buf, []byte(value))
	}
	putBytes(buf, op.Payload)
	_ = binary.Write(buf, binary.BigEndian, uint32(len(observed)))
	for _, id := range observed {
		putBytes(buf, []byte(id))
	}
	return buf.Bytes(), nil
}

func normalizedObserved(ids []string) []string {
	result := append([]string{}, ids...)
	sort.Strings(result)
	unique := result[:0]
	for _, id := range result {
		if len(unique) == 0 || unique[len(unique)-1] != id {
			unique = append(unique, id)
		}
	}
	return unique
}

func putBytes(buf *bytes.Buffer, value []byte) {
	_ = binary.Write(buf, binary.BigEndian, uint32(len(value)))
	_, _ = buf.Write(value)
}

func operationKey(spaceID, operationID string) string {
	buf := bytes.NewBufferString("pinkha-t2-operation-key-v1\x00")
	putBytes(buf, []byte(spaceID))
	putBytes(buf, []byte(operationID))
	digest := sha256.Sum256(buf.Bytes())
	return hex.EncodeToString(digest[:])
}

func makeClaim(op Operation) (Claim, []byte, error) {
	canonical, err := op.CanonicalBytes()
	if err != nil {
		return Claim{}, nil, err
	}
	// Own caller slices, including for results returned after a write.
	op.Payload = append([]byte{}, op.Payload...)
	op.Observed = normalizedObserved(op.Observed)
	digest := sha256.Sum256(canonical)
	hexDigest := hex.EncodeToString(digest[:])
	claim := Claim{ID: operationKey(op.SpaceID, op.OperationID) + "/" + hexDigest, Digest: hexDigest, Operation: op}
	wire, err := json.Marshal(wireClaim{Operation: op, Digest: hexDigest})
	return claim, wire, err
}

// DecodeClaim accepts only the canonical typed JSON emitted by EncodeClaim.
// Duplicate keys, unknown fields, whitespace variants and noncanonical base64
// are rejected by exact re-encoding, before StoreState changes are persisted.
func DecodeClaim(id, value string) (Claim, error) {
	if len(value) > MaxWireBytes {
		return Claim{}, ErrInvalid
	}
	var wire wireClaim
	decoder := json.NewDecoder(strings.NewReader(value))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&wire); err != nil {
		return Claim{}, fmt.Errorf("decode claim: %w: %w", ErrInvalid, err)
	}
	claim, canonicalJSON, err := makeClaim(wire.Operation)
	if err != nil {
		return Claim{}, err
	}
	if claim.ID != id || wire.Digest != claim.Digest || !bytes.Equal([]byte(value), canonicalJSON) {
		return Claim{}, ErrInvalid
	}
	return claim, nil
}

func EncodeClaim(op Operation) (id, value string, err error) {
	claim, wire, err := makeClaim(op)
	return claim.ID, string(wire), err
}
