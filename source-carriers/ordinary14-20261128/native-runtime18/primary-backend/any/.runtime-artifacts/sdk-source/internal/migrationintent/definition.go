package migrationintent

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"

	anystore "github.com/anyproto/any-store/v2"
)

const DefinitionContract = "pinkha-native-prepared-definitions-v1"
const (
	TypeDefinition       = "typeDefinition"
	CollectionDefinition = "collectionDefinition"
	PropertyDefinition   = "propertyDefinition"
	PartDefinition       = "partDefinition"
	DefinitionRoot       = "definition-root"
	DefinitionBootstrap  = "definition-bootstrap"
	DefinitionProperty   = "definition-property"
	DefinitionPart       = "definition-part"
)

// Definition intents have closed kinds/stages. Ordinary object, block and file
// admission remain unchanged; all routes share the unique intent binding.
func DefinitionChangeType(kind string) string {
	switch kind {
	case TypeDefinition:
		return "type"
	case CollectionDefinition:
		return "collection"
	}
	return ""
}
func IsDefinition(kind string) bool {
	return DefinitionChangeType(kind) != "" || (kind == PropertyDefinition || kind == PartDefinition)
}

func (s *Store) DefinitionFingerprint(binding Binding, kind string, spec, source []byte) (string, error) {
	if err := s.Check(binding); err != nil {
		return "", err
	}
	var shape struct {
		Kind string `json:"kind"`
	}
	if !IsDefinition(kind) || len(spec) == 0 || len(spec) > 256<<10 || json.Unmarshal(spec, &shape) != nil || shape.Kind != kind || ValidateNumbers(spec) != nil || len(source) == 0 || len(source) > 1<<20 || !json.Valid(source) || ValidateNumbers(source) != nil {
		return "", ErrScope
	}
	h := sha256.New()
	for _, v := range []string{DefinitionContract, binding.AccountID, binding.SpaceID, binding.StoreID, binding.PlanID, binding.PlanSHA256, binding.IntentID, binding.SourceKey, kind, Digest(spec), Digest(source)} {
		var n [8]byte
		binary.BigEndian.PutUint64(n[:], uint64(len(v)))
		h.Write(n[:])
		h.Write([]byte(v))
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
func definitionKey(intent, stage string) (string, error) {
	if !validHex(intent) || (stage != DefinitionRoot && stage != DefinitionBootstrap && stage != DefinitionProperty && stage != DefinitionPart) {
		return "", ErrScope
	}
	return "intent/" + intent + "/" + stage, nil
}
func (s *Store) validateDefinition(e *Prepared) error {
	if e == nil || e.ObjectID == "" || e.ChangeID == "" || len(e.Raw) == 0 || len(e.Raw) > 512<<10 || e.Timestamp < 0 {
		return ErrCorrupt
	}
	fp, err := s.DefinitionFingerprint(e.Binding, e.Kind, e.Spec, e.SourceSpec)
	if err != nil || fp != e.Fingerprint || e.SpecSHA256 != Digest(e.SourceSpec) {
		return ErrCorrupt
	}
	if e.Stage == DefinitionRoot {
		if DefinitionChangeType(e.Kind) == "" || e.ObjectID != e.ChangeID || len(e.RecordIDs) != 0 || len(e.Payload) != 0 || len(e.Dependencies) != 0 {
			return ErrCorrupt
		}
	} else {
		if e.Stage == DefinitionBootstrap {
			if DefinitionChangeType(e.Kind) == "" {
				return ErrCorrupt
			}
		} else if e.Stage == DefinitionPart {
			if e.Kind != PartDefinition {
				return ErrCorrupt
			}
		} else if e.Stage != DefinitionProperty || e.Kind != PropertyDefinition {
			return ErrCorrupt
		}
		if !validDefinitionRecordIDs(e) || len(e.Payload) == 0 || len(e.Payload) > 256<<10 || e.Timestamp <= 0 || len(e.Dependencies) != 1 || len(e.Dependencies[e.ObjectID]) == 0 {
			return ErrCorrupt
		}
		if e.Stage == DefinitionBootstrap && e.RecordIDs[0] != e.ObjectID {
			return ErrCorrupt
		}
		if e.Stage == DefinitionProperty || e.Stage == DefinitionPart {
			var shape struct {
				OwnerObjectID string `json:"ownerObjectId"`
			}
			if json.Unmarshal(e.Spec, &shape) != nil || shape.OwnerObjectID != e.ObjectID {
				return ErrCorrupt
			}
		}
	}
	return nil
}
func (s *Store) LoadDefinition(ctx context.Context, intent, stage string) (*Prepared, error) {
	key, err := definitionKey(intent, stage)
	if err != nil {
		return nil, err
	}
	var e Prepared
	if err = s.read(ctx, key, &e); err != nil {
		return nil, err
	}
	if e.Binding.IntentID != intent || e.Stage != stage {
		return nil, ErrCorrupt
	}
	if err = s.validateDefinition(&e); err != nil {
		return nil, err
	}
	if err = s.checkBindings(ctx, &e); err != nil {
		return nil, err
	}
	return &e, nil
}
func (s *Store) ReserveDefinition(ctx context.Context, proposed *Prepared) (*Prepared, error) {
	if err := s.validateDefinition(proposed); err != nil {
		return nil, err
	}
	if proposed.Stage == DefinitionBootstrap {
		root, err := s.LoadDefinition(ctx, proposed.Binding.IntentID, DefinitionRoot)
		if err != nil {
			return nil, err
		}
		if root.Binding != proposed.Binding || root.Kind != proposed.Kind || root.Fingerprint != proposed.Fingerprint || root.ObjectID != proposed.ObjectID {
			return nil, ErrCollision
		}
	}
	tx, err := s.db.WriteTx(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	tc := tx.Context()
	if err = s.bindPlan(tc, proposed.Binding); err != nil {
		return nil, err
	}
	if err = s.bindIntent(tc, proposed); err != nil {
		return nil, err
	}
	key, _ := definitionKey(proposed.Binding.IntentID, proposed.Stage)
	if err = s.insert(tc, key, proposed); err != nil && !errors.Is(err, anystore.ErrDocExists) {
		return nil, err
	}
	stored, err := s.LoadDefinition(tc, proposed.Binding.IntentID, proposed.Stage)
	if err != nil {
		return nil, err
	}
	if stored.Binding != proposed.Binding || stored.Kind != proposed.Kind || stored.Fingerprint != proposed.Fingerprint || !bytes.Equal(stored.Spec, proposed.Spec) || !bytes.Equal(stored.SourceSpec, proposed.SourceSpec) {
		return nil, ErrCollision
	}
	if err = tx.Commit(); err != nil {
		return nil, err
	}
	if err = s.EnsureDurable(ctx); err != nil {
		return nil, fmt.Errorf("definition prepared durability: %w", err)
	}
	return stored, nil
}

func validDefinitionRecordIDs(e *Prepared) bool {
	if e.Kind != PartDefinition {
		return len(e.RecordIDs) == 1 && e.RecordIDs[0] != ""
	}
	if len(e.RecordIDs) < 1 || len(e.RecordIDs) > 2048 {
		return false
	}
	seen := map[string]bool{}
	for _, id := range e.RecordIDs {
		if id == "" || seen[id] {
			return false
		}
		seen[id] = true
	}
	return true
}
