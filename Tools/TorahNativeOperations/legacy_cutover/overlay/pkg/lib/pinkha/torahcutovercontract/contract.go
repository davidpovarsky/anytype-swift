// Package torahcutovercontract defines a separate immutable metadata contract.
// A valid value is not native authority: the signed host must bind its actual
// author, target/property lease, ACL and complete import history before commit.
package torahcutovercontract

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"sort"
	"strings"
	"unicode/utf8"
)

const (
	Version             uint32 = 1
	CollectionName             = "_pinkha_torah_cutovers_v1"
	ReceiptsCollection         = "_pinkha_torah_cutover_receipts_v1"
	MaxLegacyBytes             = 1 << 20
	MaxFactPayloadBytes        = 64 << 10
	MaxFacts                   = 1024
	MaxPlanBytes               = 4 << 20
	MaxBindings                = 10000
	MaxWireBytes               = 8 << 20
	MaxSourceHeads             = 256
	MaxNativeReceipts          = 256
)

var (
	ErrInvalid       = errors.New("invalid Torah legacy cutover metadata")
	ErrConflict      = errors.New("conflicting Torah legacy cutover metadata")
	ErrIncomplete    = errors.New("incomplete Torah legacy cutover history")
	ErrAlreadySealed = errors.New("Torah legacy cutover is already sealed")
	ErrLegacyChanged = errors.New("retained Torah legacy property changed")
)

type Kind string

const (
	Begin  Kind = "begin"
	Import Kind = "import"
	Seal   Kind = "seal"
)

// Fact retains the exact canonical bytes produced by the shared source codec.
// Native code does not replace that codec with a second JSON implementation.
type Fact struct {
	BlockID      string `json:"blockId"`
	ProviderID   string `json:"providerId"`
	CanonicalRef string `json:"canonicalRef"`
	Payload      []byte `json:"payload"`
}

// Plan is immutable and independent of a writer's record/operation IDs. The
// native property presence bit distinguishes missing from present-empty data.
type Plan struct {
	Version      uint32 `json:"version"`
	SpaceID      string `json:"spaceId"`
	ObjectID     string `json:"objectId"`
	PropertyKey  string `json:"propertyKey"`
	ValuePresent bool   `json:"valuePresent"`
	LegacyValue  []byte `json:"legacyValue"`
	Facts        []Fact `json:"facts"`
}

type Binding struct {
	FactID  string `json:"factId"`
	ClaimID string `json:"claimId"`
}

// NativeWitness names an already durable, independently verified v1 claim
// receipt. The v2 metadata author may differ from this original native author.
// No JSON field is a substitute for re-reading the signed v1 history.
type NativeWitness struct {
	ChangeID  string `json:"changeId"`
	Creator   string `json:"creator"`
	ACLHeadID string `json:"aclHeadId"`
}

// Record is not a user source association. It belongs to a separate versioned
// metadata tree. Import is the second durable phase after the real v1 claim;
// a missing import record is unfinished work, never a phantom atomic commit.
// Seals retain their imported history after normal association removal.
type Record struct {
	Version       uint32          `json:"version"`
	SpaceID       string          `json:"spaceId"`
	ObjectID      string          `json:"objectId"`
	RecordID      string          `json:"recordId"`
	AuthorID      string          `json:"authorId"`
	Kind          Kind            `json:"kind"`
	PlanID        string          `json:"planId"`
	Plan          *Plan           `json:"plan,omitempty"`
	FactID        string          `json:"factId,omitempty"`
	ImportClaimID string          `json:"importClaimId,omitempty"`
	Imported      []Binding       `json:"imported,omitempty"`
	SourceHeads   []string        `json:"sourceHeads,omitempty"`
	NativeChanges []NativeWitness `json:"nativeChanges,omitempty"`
	ImportRecords []string        `json:"importRecords,omitempty"`
}

type Claim struct {
	ID     string
	Digest string
	Record Record
}

type wireClaim struct {
	Record Record `json:"record"`
	Digest string `json:"digest"`
}

func Text(value string, required bool, limit int) bool {
	return (!required || len(value) != 0) && len(value) <= limit &&
		utf8.ValidString(value) && !strings.ContainsRune(value, 0)
}

func Hex(value string, size int) bool {
	if len(value) != size*2 || value != strings.ToLower(value) {
		return false
	}
	_, err := hex.DecodeString(value)
	return err == nil
}

func ClaimID(value string) bool {
	return len(value) == 129 && value[64] == '/' && Hex(value[:64], 32) && Hex(value[65:], 32)
}

func put(buf *bytes.Buffer, value []byte) {
	_ = binary.Write(buf, binary.BigEndian, uint32(len(value)))
	_, _ = buf.Write(value)
}

func (f Fact) CanonicalBytes(spaceID, objectID string) ([]byte, error) {
	if !Text(spaceID, true, 1024) || !Text(objectID, true, 1024) ||
		!Text(f.BlockID, false, 1024) || !Text(f.ProviderID, true, 256) ||
		!Text(f.CanonicalRef, true, 4096) || len(f.Payload) == 0 ||
		len(f.Payload) > MaxFactPayloadBytes || !json.Valid(f.Payload) {
		return nil, ErrInvalid
	}
	b := bytes.NewBufferString("pinkha-torah-cutover-fact-v1\x00")
	for _, value := range []string{spaceID, objectID, f.BlockID, f.ProviderID, f.CanonicalRef} {
		put(b, []byte(value))
	}
	put(b, f.Payload)
	return b.Bytes(), nil
}

func (f Fact) ID(spaceID, objectID string) (string, error) {
	b, err := f.CanonicalBytes(spaceID, objectID)
	if err != nil {
		return "", err
	}
	d := sha256.Sum256(b)
	return hex.EncodeToString(d[:]), nil
}

func (p Plan) canonical() (Plan, [][]byte, error) {
	if p.Version != Version || !Text(p.SpaceID, true, 1024) || !Text(p.ObjectID, true, 1024) ||
		!Text(p.PropertyKey, true, 1024) || len(p.LegacyValue) > MaxLegacyBytes ||
		(!p.ValuePresent && len(p.LegacyValue) != 0) || !utf8.Valid(p.LegacyValue) ||
		len(p.Facts) > MaxFacts {
		return Plan{}, nil, ErrInvalid
	}
	out := p
	out.LegacyValue = append([]byte{}, p.LegacyValue...)
	out.Facts = make([]Fact, len(p.Facts))
	type ordered struct {
		fact Fact
		wire []byte
	}
	rows := make([]ordered, 0, len(p.Facts))
	size := 0
	for _, f := range p.Facts {
		b, err := f.CanonicalBytes(p.SpaceID, p.ObjectID)
		if err != nil {
			return Plan{}, nil, err
		}
		size += len(b)
		if size > MaxPlanBytes {
			return Plan{}, nil, ErrInvalid
		}
		f.Payload = append([]byte{}, f.Payload...)
		rows = append(rows, ordered{fact: f, wire: b})
	}
	sort.Slice(rows, func(i, j int) bool { return bytes.Compare(rows[i].wire, rows[j].wire) < 0 })
	wires := make([][]byte, len(rows))
	for i, row := range rows {
		if i > 0 && bytes.Equal(row.wire, rows[i-1].wire) {
			return Plan{}, nil, ErrInvalid
		}
		out.Facts[i], wires[i] = row.fact, row.wire
	}
	return out, wires, nil
}

func (p Plan) CanonicalBytes() ([]byte, error) {
	p, facts, err := p.canonical()
	if err != nil {
		return nil, err
	}
	b := bytes.NewBufferString("pinkha-torah-legacy-cutover-v1\x00")
	_ = binary.Write(b, binary.BigEndian, p.Version)
	for _, value := range []string{p.SpaceID, p.ObjectID, p.PropertyKey} {
		put(b, []byte(value))
	}
	if p.ValuePresent {
		_ = b.WriteByte(1)
	} else {
		_ = b.WriteByte(0)
	}
	put(b, p.LegacyValue)
	_ = binary.Write(b, binary.BigEndian, uint32(len(facts)))
	for _, f := range facts {
		put(b, f)
	}
	if b.Len() > MaxPlanBytes {
		return nil, ErrInvalid
	}
	return b.Bytes(), nil
}

func (p Plan) ID() (string, error) {
	b, err := p.CanonicalBytes()
	if err != nil {
		return "", err
	}
	d := sha256.Sum256(b)
	return hex.EncodeToString(d[:]), nil
}

func (p Plan) MatchesProperty(present bool, value []byte) bool {
	return p.ValuePresent == present && bytes.Equal(p.LegacyValue, value)
}

func canonicalBindings(values []Binding) ([]Binding, error) {
	if len(values) > MaxBindings {
		return nil, ErrInvalid
	}
	out := append([]Binding{}, values...)
	for _, v := range out {
		if !Hex(v.FactID, 32) || !ClaimID(v.ClaimID) {
			return nil, ErrInvalid
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].FactID != out[j].FactID {
			return out[i].FactID < out[j].FactID
		}
		return out[i].ClaimID < out[j].ClaimID
	})
	seen := map[string]bool{}
	for _, v := range out {
		if seen[v.ClaimID] {
			return nil, ErrInvalid
		}
		seen[v.ClaimID] = true
	}
	return out, nil
}

func (r Record) canonical() (Record, error) {
	if r.Version != Version || !Text(r.SpaceID, true, 1024) || !Text(r.ObjectID, true, 1024) ||
		!Text(r.AuthorID, true, 1024) || !Hex(r.RecordID, 16) || !Hex(r.PlanID, 32) {
		return Record{}, ErrInvalid
	}
	switch r.Kind {
	case Begin:
		if r.Plan == nil || r.FactID != "" || r.ImportClaimID != "" || len(r.Imported) != 0 || len(r.NativeChanges) != 0 || len(r.ImportRecords) != 0 {
			return Record{}, ErrInvalid
		}
		p, _, err := r.Plan.canonical()
		if err != nil {
			return Record{}, err
		}
		id, err := p.ID()
		if err != nil || id != r.PlanID || p.SpaceID != r.SpaceID || p.ObjectID != r.ObjectID {
			return Record{}, ErrInvalid
		}
		r.Plan = &p
		r.SourceHeads, err = canonicalStrings(r.SourceHeads, MaxSourceHeads, false)
		if err != nil {
			return Record{}, err
		}
	case Import:
		if r.Plan != nil || len(r.Imported) != 0 || len(r.SourceHeads) != 0 || len(r.ImportRecords) != 0 || !Hex(r.FactID, 32) || !ClaimID(r.ImportClaimID) {
			return Record{}, ErrInvalid
		}
		witnesses, err := canonicalWitnesses(r.NativeChanges)
		if err != nil {
			return Record{}, err
		}
		r.NativeChanges = witnesses
	case Seal:
		if r.Plan != nil || r.FactID != "" || r.ImportClaimID != "" || len(r.SourceHeads) != 0 || len(r.NativeChanges) != 0 {
			return Record{}, ErrInvalid
		}
		bindings, err := canonicalBindings(r.Imported)
		if err != nil {
			return Record{}, err
		}
		r.Imported = bindings
		r.ImportRecords, err = canonicalStrings(r.ImportRecords, MaxBindings, true)
		if err != nil {
			return Record{}, err
		}
		for _, id := range r.ImportRecords {
			if !ClaimID(id) {
				return Record{}, ErrInvalid
			}
		}
		if (len(r.Imported) == 0) != (len(r.ImportRecords) == 0) {
			return Record{}, ErrInvalid
		}
	default:
		return Record{}, ErrInvalid
	}
	return r, nil
}

func (r Record) CanonicalBytes() ([]byte, error) {
	r, err := r.canonical()
	if err != nil {
		return nil, err
	}
	b := bytes.NewBufferString("pinkha-torah-cutover-record-v1\x00")
	_ = binary.Write(b, binary.BigEndian, r.Version)
	for _, v := range []string{r.SpaceID, r.ObjectID, r.RecordID, r.AuthorID, string(r.Kind), r.PlanID} {
		put(b, []byte(v))
	}
	switch r.Kind {
	case Begin:
		p, err := r.Plan.CanonicalBytes()
		if err != nil {
			return nil, err
		}
		put(b, p)
		_ = binary.Write(b, binary.BigEndian, uint32(len(r.SourceHeads)))
		for _, head := range r.SourceHeads {
			put(b, []byte(head))
		}
	case Import:
		put(b, []byte(r.FactID))
		put(b, []byte(r.ImportClaimID))
		_ = binary.Write(b, binary.BigEndian, uint32(len(r.NativeChanges)))
		for _, witness := range r.NativeChanges {
			put(b, []byte(witness.ChangeID))
			put(b, []byte(witness.Creator))
			put(b, []byte(witness.ACLHeadID))
		}
	case Seal:
		_ = binary.Write(b, binary.BigEndian, uint32(len(r.Imported)))
		for _, v := range r.Imported {
			put(b, []byte(v.FactID))
			put(b, []byte(v.ClaimID))
		}
		_ = binary.Write(b, binary.BigEndian, uint32(len(r.ImportRecords)))
		for _, id := range r.ImportRecords {
			put(b, []byte(id))
		}
	}
	return b.Bytes(), nil
}

func Encode(r Record) (Claim, []byte, error) {
	r, err := r.canonical()
	if err != nil {
		return Claim{}, nil, err
	}
	b, err := r.CanonicalBytes()
	if err != nil {
		return Claim{}, nil, err
	}
	d := sha256.Sum256(b)
	digest := hex.EncodeToString(d[:])
	key := bytes.NewBufferString("pinkha-torah-cutover-key-v1\x00")
	put(key, []byte(r.SpaceID))
	put(key, []byte(r.RecordID))
	k := sha256.Sum256(key.Bytes())
	c := Claim{ID: hex.EncodeToString(k[:]) + "/" + digest, Digest: digest, Record: r}
	wire, err := json.Marshal(wireClaim{Record: r, Digest: digest})
	if err != nil || len(wire) > MaxWireBytes {
		return Claim{}, nil, ErrInvalid
	}
	return c, wire, nil
}

// Decode accepts only the exact canonical closed wire emitted by Encode. This
// parser does not substitute for native signature/historical/current ACL checks.
func Decode(id string, wire []byte) (Claim, error) {
	if len(wire) == 0 || len(wire) > MaxWireBytes {
		return Claim{}, ErrInvalid
	}
	var value wireClaim
	d := json.NewDecoder(bytes.NewReader(wire))
	d.DisallowUnknownFields()
	if err := d.Decode(&value); err != nil {
		return Claim{}, ErrInvalid
	}
	c, encoded, err := Encode(value.Record)
	if err != nil || c.ID != id || c.Digest != value.Digest || !bytes.Equal(wire, encoded) {
		return Claim{}, ErrInvalid
	}
	return c, nil
}

func canonicalStrings(values []string, limit int, allowEmpty bool) ([]string, error) {
	if len(values) > limit || (!allowEmpty && len(values) == 0) {
		return nil, ErrInvalid
	}
	out := append([]string{}, values...)
	for _, value := range out {
		if !Text(value, true, 1024) {
			return nil, ErrInvalid
		}
	}
	sort.Strings(out)
	for i := 1; i < len(out); i++ {
		if out[i] == out[i-1] {
			return nil, ErrInvalid
		}
	}
	return out, nil
}
func canonicalWitnesses(values []NativeWitness) ([]NativeWitness, error) {
	if len(values) == 0 || len(values) > MaxNativeReceipts {
		return nil, ErrInvalid
	}
	out := append([]NativeWitness{}, values...)
	for _, witness := range out {
		if !Text(witness.ChangeID, true, 1024) || !Text(witness.Creator, true, 1024) || !Text(witness.ACLHeadID, true, 1024) {
			return nil, ErrInvalid
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ChangeID < out[j].ChangeID })
	for i := 1; i < len(out); i++ {
		if out[i].ChangeID == out[i-1].ChangeID {
			return nil, ErrInvalid
		}
	}
	return out, nil
}

// ImportOperationID is deterministic per exact plan, fact and actual author.
// Different native authors never share a logical operation ID merely because
// their source fact is equal. The adapter retains all their signed claims.
func ImportOperationID(planID, factID, authorID string) (string, error) {
	if !Hex(planID, 32) || !Hex(factID, 32) || !Text(authorID, true, 1024) {
		return "", ErrInvalid
	}
	b := bytes.NewBufferString("pinkha-torah-cutover-import-operation-v1\x00")
	put(b, []byte(planID))
	put(b, []byte(factID))
	put(b, []byte(authorID))
	d := sha256.Sum256(b.Bytes())
	return hex.EncodeToString(d[:16]), nil
}
