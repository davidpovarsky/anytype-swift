// Package migrationintent is the private, destination-local write-ahead ledger
// for the prepared migration route. It is deliberately not a CRDT dataset.
// Every entry is immutable and committed before its signed bytes may enter a
// native object tree. Native history, never a mutable receipt, determines the
// outcome of an append whose acknowledgement was lost.
package migrationintent

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"

	anystore "github.com/anyproto/any-store/v2"
	"github.com/anyproto/any-store/v2/anyenc"
)

const Contract = "pinkha-native-prepared-migration-v1"
const ImmutableRecord = "immutableRecord"
const ImmutableRecordStage = "immutable-record"

const collectionName = "_pinkha_native_migration_prepared_v1"
const maxEntryBytes = 4 << 20

var (
	ErrScope     = errors.New("migration intent: destination store or scope differs")
	ErrCollision = errors.New("migration intent: immutable intent fingerprint differs")
	ErrCorrupt   = errors.New("migration intent: stored preparation is invalid")
	ErrObsolete  = errors.New("migration intent: prepared envelope is obsolete")
	ErrNotFound  = errors.New("migration intent: preparation not found")
)

// Binding is native-account and native-space scoped. StoreID is an opaque
// generation in the projection database. Reset/replacement cannot adopt an old
// caller plan: it yields a different StoreID and refuses before any append.
type Binding struct {
	StoreID    string `json:"storeId"`
	AccountID  string `json:"accountId"`
	SpaceID    string `json:"spaceId"`
	PlanID     string `json:"planId"`
	PlanSHA256 string `json:"planSHA256"`
	IntentID   string `json:"intentId"`
	SourceKey  string `json:"sourceKey"`
}

type Identity struct {
	Contract  string `json:"contract"`
	StoreID   string `json:"storeId"`
	AccountID string `json:"accountId"`
	SpaceID   string `json:"spaceId"`
}

// Prepared contains exactly one signed native root or change. The native SDK
// retains both the user operation and the preparation-time fence. Raw is never
// returned by HTTP and callers cannot choose it at commit.
type Prepared struct {
	Binding      Binding             `json:"binding"`
	Fingerprint  string              `json:"fingerprint"`
	Kind         string              `json:"kind"`
	Stage        string              `json:"stage"`
	ObjectID     string              `json:"objectId"`
	ChangeID     string              `json:"changeId"`
	Raw          []byte              `json:"raw"`
	Spec         []byte              `json:"spec"`
	SourceSpec   []byte              `json:"sourceSpec"`
	SpecSHA256   string              `json:"specSHA256"`
	Payload      []byte              `json:"payload,omitempty"`
	Timestamp    int64               `json:"timestamp,omitempty"`
	RecordIDs    []string            `json:"recordIds,omitempty"`
	Dependencies map[string][]string `json:"dependencies,omitempty"`
}

type Store struct {
	db       anystore.DB
	coll     anystore.Collection
	identity Identity
}

func validHex(value string) bool {
	if len(value) != 64 {
		return false
	}
	decoded, err := hex.DecodeString(value)
	return err == nil && hex.EncodeToString(decoded) == value
}

func ValidID(value string) bool { return validHex(value) }

func Open(ctx context.Context, db anystore.DB, accountID, spaceID string) (*Store, error) {
	if db == nil || accountID == "" || spaceID == "" {
		return nil, ErrScope
	}
	// The SDK projection DB is shared by its Spaces. A private ledger belongs
	// to one native Space/account, just like the prefixed public projections.
	coll, err := db.Collection(ctx, collectionName+"_"+Digest([]byte(spaceID)))
	if err != nil {
		return nil, err
	}
	s := &Store{db: db, coll: coll}
	var identity Identity
	err = s.read(ctx, "identity", &identity)
	if errors.Is(err, ErrNotFound) {
		var random [32]byte
		if _, err = rand.Read(random[:]); err != nil {
			return nil, err
		}
		identity = Identity{Contract: Contract, StoreID: hex.EncodeToString(random[:]), AccountID: accountID, SpaceID: spaceID}
		err = s.insert(ctx, "identity", identity)
		if errors.Is(err, anystore.ErrDocExists) {
			err = s.read(ctx, "identity", &identity)
		}
	}
	if err != nil {
		return nil, err
	}
	if identity.Contract != Contract || !validHex(identity.StoreID) || identity.AccountID != accountID || identity.SpaceID != spaceID {
		return nil, ErrScope
	}
	s.identity = identity
	return s, nil
}

func (s *Store) Identity() Identity { return s.identity }

// Commit repeats the barrier even when prepare previously returned an I/O
// error after its logical insert. Reading that row alone never admits append.
func (s *Store) EnsureDurable(ctx context.Context) error {
	return s.db.Flush(ctx, 0, anystore.FlushModeCheckpointFull)
}

func (s *Store) Check(binding Binding) error {
	if binding.StoreID != s.identity.StoreID || binding.AccountID != s.identity.AccountID || binding.SpaceID != s.identity.SpaceID ||
		!validHex(binding.PlanID) || !validHex(binding.PlanSHA256) || !validHex(binding.IntentID) || binding.SourceKey == "" || len(binding.SourceKey) > 4096 {
		return ErrScope
	}
	return nil
}

// Fingerprint includes the complete normalized native operation, its immutable
// source identity, and the destination generation. A client-provided hash is
// only compared to this value; it never chooses native bytes.
func (s *Store) Fingerprint(binding Binding, kind string, spec, sourceSpec []byte) (string, error) {
	if err := s.Check(binding); err != nil {
		return "", err
	}
	if kind != "object" && kind != "editorBlock" && kind != ImmutableRecord {
		return "", ErrScope
	}
	if !json.Valid(spec) || len(spec) == 0 || len(spec) > maxEntryBytes/2 {
		return "", ErrCorrupt
	}
	if !json.Valid(sourceSpec) || len(sourceSpec) == 0 || len(sourceSpec) > 1<<20 {
		return "", ErrCorrupt
	}
	if ValidateNumbers(spec) != nil || ValidateNumbers(sourceSpec) != nil {
		return "", ErrCorrupt
	}
	nativeHash, sourceHash := Digest(spec), Digest(sourceSpec)
	h := sha256.New()
	for _, value := range []string{Contract, binding.AccountID, binding.SpaceID, binding.StoreID, binding.PlanID, binding.PlanSHA256, binding.IntentID, binding.SourceKey, kind, nativeHash, sourceHash} {
		var length [8]byte
		binary.BigEndian.PutUint64(length[:], uint64(len(value)))
		h.Write(length[:])
		h.Write([]byte(value))
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func Digest(value []byte) string { sum := sha256.Sum256(value); return hex.EncodeToString(sum[:]) }

func stageKey(intentID, stage string) (string, error) {
	if !validHex(intentID) {
		return "", ErrScope
	}
	if stage != "root" && stage != "bootstrap" && stage != "block" && stage != ImmutableRecordStage {
		return "", ErrScope
	}
	// Intent IDs are unique within a physical account/Space store, across plans.
	// Reusing one under another plan is a collision, never a second allocation.
	return "intent/" + intentID + "/" + stage, nil
}

func (s *Store) Load(ctx context.Context, intentID, stage string) (*Prepared, error) {
	key, err := stageKey(intentID, stage)
	if err != nil {
		return nil, err
	}
	var entry Prepared
	if err = s.read(ctx, key, &entry); err != nil {
		return nil, err
	}
	if err = s.validate(&entry); err != nil {
		return nil, err
	}
	if entry.Binding.IntentID != intentID || entry.Stage != stage {
		return nil, ErrCorrupt
	}
	if err = s.checkBindings(ctx, &entry); err != nil {
		return nil, err
	}
	return &entry, nil
}

func (s *Store) validate(entry *Prepared) error {
	if entry == nil || s.Check(entry.Binding) != nil || !validHex(entry.Fingerprint) || len(entry.Raw) == 0 ||
		entry.ObjectID == "" || entry.ChangeID == "" || !json.Valid(entry.Spec) || entry.Timestamp < 0 {
		return ErrCorrupt
	}
	if entry.Kind == "object" {
		if entry.Stage != "root" && entry.Stage != "bootstrap" {
			return ErrCorrupt
		}
	} else if entry.Kind == ImmutableRecord {
		if entry.Stage != ImmutableRecordStage {
			return ErrCorrupt
		}
	} else if entry.Kind != "editorBlock" || entry.Stage != "block" {
		return ErrCorrupt
	}
	if entry.Stage == "root" && entry.ChangeID != entry.ObjectID {
		return ErrCorrupt
	}
	fingerprint, err := s.Fingerprint(entry.Binding, entry.Kind, entry.Spec, entry.SourceSpec)
	if err != nil || fingerprint != entry.Fingerprint || entry.SpecSHA256 != Digest(entry.SourceSpec) {
		return ErrCorrupt
	}
	return nil
}

// Reserve wins by the database's unique primary key, across concurrent native
// callers as well as process restart. A duplicate returns the FIRST exact
// signed envelope, never the loser's newly generated signature/seed/time.
// A returned error authorizes no native append, even when Insert may have
// committed: the caller must re-open and Load to reconcile that uncertainty.
func (s *Store) Reserve(ctx context.Context, proposed *Prepared) (*Prepared, error) {
	if err := s.validate(proposed); err != nil {
		return nil, err
	}
	// This transaction covers only the private projection-store ledger. It
	// never encloses native DAG creation/publication or native tree callbacks.
	// Plan/entity/intent identity and exact bytes become visible together.
	tx, err := s.db.WriteTx(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	txCtx := tx.Context()
	if err := s.bindPlan(txCtx, proposed.Binding); err != nil {
		return nil, err
	}
	if err := s.bindIntent(txCtx, proposed); err != nil {
		return nil, err
	}
	key, err := stageKey(proposed.Binding.IntentID, proposed.Stage)
	if err != nil {
		return nil, err
	}
	err = s.insert(txCtx, key, proposed)
	if err != nil && !errors.Is(err, anystore.ErrDocExists) {
		return nil, err
	}
	stored, err := s.Load(txCtx, proposed.Binding.IntentID, proposed.Stage)
	if err != nil {
		return nil, err
	}
	if stored.Binding != proposed.Binding || stored.Fingerprint != proposed.Fingerprint || stored.Kind != proposed.Kind || !bytes.Equal(stored.Spec, proposed.Spec) || !bytes.Equal(stored.SourceSpec, proposed.SourceSpec) {
		return nil, ErrCollision
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}
	// Projection databases normally defer WAL fsync. A successful logical
	// commit alone is therefore insufficient for a native write-ahead claim.
	// Full checkpoint is a required durability barrier; a store without an
	// enabled durability controller fails closed here and may append nothing.
	if err := s.EnsureDurable(ctx); err != nil {
		return nil, fmt.Errorf("migration prepared durability: %w", err)
	}
	return stored, nil
}

type planBinding struct {
	StoreID    string `json:"storeId"`
	AccountID  string `json:"accountId"`
	SpaceID    string `json:"spaceId"`
	PlanID     string `json:"planId"`
	PlanSHA256 string `json:"planSHA256"`
}

type intentBinding struct {
	Binding          Binding `json:"binding"`
	Kind             string  `json:"kind"`
	Fingerprint      string  `json:"fingerprint"`
	SpecSHA256       string  `json:"specSHA256"`
	NativeSpecSHA256 string  `json:"nativeSpecSHA256"`
}

func (s *Store) bindIntent(ctx context.Context, entry *Prepared) error {
	want := intentBinding{entry.Binding, entry.Kind, entry.Fingerprint, entry.SpecSHA256, Digest(entry.Spec)}
	for _, key := range []string{"intent/" + entry.Binding.IntentID + "/identity", entityKey(entry)} {
		err := s.insert(ctx, key, want)
		if err != nil && !errors.Is(err, anystore.ErrDocExists) {
			return err
		}
		var got intentBinding
		if err = s.read(ctx, key, &got); err != nil {
			return err
		}
		if got != want {
			return ErrCollision
		}
	}
	return nil
}

func entityKey(entry *Prepared) string {
	hash := sha256.New()
	for _, value := range []string{Contract + "/entity", entry.Binding.PlanID, entry.Binding.SourceKey, entry.Kind} {
		var length [8]byte
		binary.BigEndian.PutUint64(length[:], uint64(len(value)))
		hash.Write(length[:])
		hash.Write([]byte(value))
	}
	return "entity/" + hex.EncodeToString(hash.Sum(nil))
}

func (s *Store) checkBindings(ctx context.Context, entry *Prepared) error {
	binding := entry.Binding
	wantPlan := planBinding{binding.StoreID, binding.AccountID, binding.SpaceID, binding.PlanID, binding.PlanSHA256}
	var plan planBinding
	if err := s.read(ctx, "plan/"+binding.PlanID, &plan); err != nil || plan != wantPlan {
		return ErrCorrupt
	}
	wantIntent := intentBinding{binding, entry.Kind, entry.Fingerprint, entry.SpecSHA256, Digest(entry.Spec)}
	for _, key := range []string{"intent/" + binding.IntentID + "/identity", entityKey(entry)} {
		var intent intentBinding
		if err := s.read(ctx, key, &intent); err != nil || intent != wantIntent {
			return ErrCorrupt
		}
	}
	return nil
}

// A logical plan keeps its identity when its archive changes. It can never
// silently acquire additional or removed source entities under a new digest.
// This unique insert commits BEFORE any entity preparation is admitted.
func (s *Store) bindPlan(ctx context.Context, binding Binding) error {
	want := planBinding{binding.StoreID, binding.AccountID, binding.SpaceID, binding.PlanID, binding.PlanSHA256}
	key := "plan/" + binding.PlanID
	err := s.insert(ctx, key, want)
	if err != nil && !errors.Is(err, anystore.ErrDocExists) {
		return err
	}
	var got planBinding
	if err = s.read(ctx, key, &got); err != nil {
		return err
	}
	if got != want {
		return ErrCollision
	}
	return nil
}

func (s *Store) read(ctx context.Context, id string, target any) error {
	doc, err := s.coll.FindId(ctx, id)
	if errors.Is(err, anystore.ErrDocNotFound) {
		return ErrNotFound
	}
	if err != nil {
		return err
	}
	encoded := doc.Value().GetStringBytes("body")
	if len(encoded) == 0 || len(encoded) > maxEntryBytes || json.Unmarshal(encoded, target) != nil {
		return ErrCorrupt
	}
	return nil
}

func (s *Store) insert(ctx context.Context, id string, value any) error {
	encoded, err := json.Marshal(value)
	if err != nil {
		return err
	}
	if len(encoded) > maxEntryBytes {
		return fmt.Errorf("%w: size", ErrCorrupt)
	}
	a := &anyenc.Arena{}
	doc := a.NewObject()
	doc.Set("id", a.NewString(id))
	doc.Set("body", a.NewString(string(encoded)))
	return s.coll.Insert(ctx, doc)
}
