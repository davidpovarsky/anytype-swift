package torahops

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-store/query"

	"github.com/anyproto/anytype-heart/core/block/editor/storestate"
	"github.com/anyproto/anytype-heart/pb"
)

// NativeChange must come from a verified native change, not caller-supplied RPC
// fields. This component checks author binding but does not verify ACL authority.
type NativeChange struct {
	ID        string
	Order     string
	Creator   string
	ACLHeadID string
}

type Receipt struct {
	ID        string `json:"id"`
	ClaimID   string `json:"claimId"`
	ChangeID  string `json:"changeId"`
	Creator   string `json:"creator"`
	ACLHeadID string `json:"aclHeadId"`
}

type Disposition string

const (
	Created                   Disposition = "created"
	AlreadyExistsSamePayload  Disposition = "already_exists_same_payload"
	CollisionDifferentPayload Disposition = "collision_different_payload"
)

// Resolution never contains a selected winner. All conflicting claims remain
// available, sorted by their immutable physical IDs.
type Resolution struct {
	OperationID string
	Conflict    bool
	Claims      []Claim
}

type AppendResult struct {
	Disposition Disposition
	ClaimID     string
	Resolution  Resolution
}

type Store struct {
	state    *storestate.StoreState
	claims   anystore.Collection
	receipts anystore.Collection
	spaceID  string
}

// New creates only a materialized StoreState namespace in an account-scoped DB.
// It does NOT create the sanctioned hidden native host or a signed change tree.
// Production writes must wait for that host's RPC/ACL/lifecycle implementation.
func New(ctx context.Context, db anystore.DB, spaceID string) (*Store, error) {
	if !validText(spaceID, true, 1024) {
		return nil, ErrInvalid
	}
	h := &handler{spaceID: spaceID}
	key := sha256.Sum256([]byte("pinkha-t2-projection-host-v1\x00" + spaceID))
	state, err := storestate.New(ctx, "pinkha-t2-v1-"+hex.EncodeToString(key[:]), db, h)
	if err != nil {
		return nil, fmt.Errorf("open torah projection: %w", err)
	}
	return &Store{state: state, claims: h.claims, receipts: h.receipts, spaceID: spaceID}, nil
}

// AppendLocal atomically checks logical operation identity and applies one local
// claim inside the real any-store write transaction. A mismatching ordered write
// returns CollisionDifferentPayload without inserting a claim or a receipt.
// A retry of existing bytes succeeds even if a remote conflict is now present;
// its returned Resolution still exposes that conflict explicitly.
func (s *Store) AppendLocal(ctx context.Context, op Operation, native NativeChange) (AppendResult, error) {
	claim, wire, err := makeClaim(op)
	if err != nil {
		return AppendResult{}, err
	}
	if err = s.validateNative(op, native); err != nil {
		return AppendResult{}, err
	}
	tx, err := s.state.NewTx(ctx)
	if err != nil {
		return AppendResult{}, fmt.Errorf("begin local append: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	resolution, err := s.ReadOperation(tx.Context(), op.OperationID)
	if err != nil {
		return AppendResult{}, err
	}
	for _, existing := range resolution.Claims {
		if existing.ID == claim.ID {
			left, _ := existing.Operation.CanonicalBytes()
			right, _ := op.CanonicalBytes()
			if !bytes.Equal(left, right) {
				return AppendResult{}, fmt.Errorf("content digest collision: %w", storestate.ErrCritical)
			}
			return AppendResult{Disposition: AlreadyExistsSamePayload, ClaimID: claim.ID, Resolution: resolution}, nil
		}
	}
	if len(resolution.Claims) != 0 {
		return AppendResult{Disposition: CollisionDifferentPayload, ClaimID: claim.ID, Resolution: resolution}, nil
	}
	if err = apply(tx, claim.ID, string(wire), native); err != nil {
		return AppendResult{}, err
	}
	if err = tx.Commit(); err != nil {
		return AppendResult{}, fmt.Errorf("commit local append: %w", err)
	}
	return AppendResult{Disposition: Created, ClaimID: claim.ID,
		Resolution: Resolution{OperationID: op.OperationID, Claims: []Claim{claim}}}, nil
}

// Replay merges an already-authorized immutable native claim. Unlike a local
// ordered append, offline variants must both be retained, independently of arrival
// order. Calling this helper is a component replay test, not a transport test.
func (s *Store) Replay(ctx context.Context, op Operation, native NativeChange) error {
	claim, wire, err := makeClaim(op)
	if err != nil {
		return err
	}
	if err = s.validateNative(op, native); err != nil {
		return err
	}
	tx, err := s.state.NewTx(ctx)
	if err != nil {
		return fmt.Errorf("begin native replay: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err = apply(tx, claim.ID, string(wire), native); err != nil {
		return err
	}
	if err = tx.Commit(); err != nil {
		return fmt.Errorf("commit native replay: %w", err)
	}
	return nil
}

func (s *Store) validateNative(op Operation, native NativeChange) error {
	if op.SpaceID != s.spaceID || op.AuthorID != native.Creator || !validNative(native) {
		return ErrInvalid
	}
	return nil
}

func validNative(native NativeChange) bool {
	return validText(native.ID, true, 1024) && validText(native.Order, true, 1024) &&
		validText(native.Creator, true, 1024) && validText(native.ACLHeadID, true, 1024)
}

func apply(tx *storestate.StoreStateTx, id, wire string, native NativeChange) error {
	build := &storestate.Builder{}
	if err := build.Create(CollectionName, id, wire); err != nil {
		return fmt.Errorf("build native claim: %w", err)
	}
	if err := tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{Id: native.ID, Order: native.Order,
		Creator: native.Creator, AclHeadId: native.ACLHeadID, Changes: build.ChangeSet}); err != nil {
		return fmt.Errorf("apply native claim: %w", err)
	}
	return nil
}

func (s *Store) ReadOperation(ctx context.Context, operationID string) (Resolution, error) {
	if !validHex(operationID, 16) {
		return Resolution{}, ErrInvalid
	}
	claims, err := readClaims(ctx, s.claims.Find(map[string]any{"operation.operationId": operationID}), MaxVariants)
	if err != nil {
		return Resolution{}, err
	}
	return Resolution{OperationID: operationID, Conflict: len(claims) > 1, Claims: claims}, nil
}

func (s *Store) Receipts(ctx context.Context, claimID string) (result []Receipt, err error) {
	if !validClaimID(claimID) {
		return nil, ErrInvalid
	}
	iter, err := s.receipts.Find(map[string]any{"claimId": claimID}).Sort("id").Limit(MaxVariants + 1).Iter(ctx)
	if err != nil {
		return nil, err
	}
	defer func() { err = errors.Join(err, iter.Close()) }()
	for iter.Next() {
		if len(result) == MaxVariants {
			return nil, ErrReadLimit
		}
		doc, readErr := iter.Doc()
		if readErr != nil {
			return nil, readErr
		}
		var receipt Receipt
		if readErr = json.Unmarshal([]byte(doc.Value().String()), &receipt); readErr != nil {
			return nil, readErr
		}
		result = append(result, receipt)
	}
	return result, iter.Err()
}

func readClaims(ctx context.Context, q anystore.Query, limit uint) (result []Claim, err error) {
	iter, err := q.Sort("id").Limit(limit + 1).Iter(ctx)
	if err != nil {
		return nil, fmt.Errorf("query claims: %w", err)
	}
	defer func() { err = errors.Join(err, iter.Close()) }()
	for iter.Next() {
		if uint(len(result)) == limit {
			return nil, ErrReadLimit
		}
		doc, readErr := iter.Doc()
		if readErr != nil {
			return nil, readErr
		}
		claim, readErr := claimFromValue(doc.Value())
		if readErr != nil {
			return nil, readErr
		}
		result = append(result, claim)
	}
	return result, iter.Err()
}

func claimFromValue(value *anyenc.Value) (Claim, error) {
	var op Operation
	operationValue := value.Get("operation")
	if operationValue == nil {
		return Claim{}, ErrInvalid
	}
	if err := json.Unmarshal([]byte(operationValue.String()), &op); err != nil {
		return Claim{}, err
	}
	claim, _, err := makeClaim(op)
	if err != nil {
		return Claim{}, err
	}
	if value.GetString("id") != claim.ID || value.GetString("digest") != claim.Digest {
		return Claim{}, ErrInvalid
	}
	return claim, nil
}

type handler struct {
	spaceID  string
	claims   anystore.Collection
	receipts anystore.Collection
}

var _ storestate.Handler = (*handler)(nil)

func (h *handler) CollectionName() string { return CollectionName }

func (h *handler) Init(ctx context.Context, state *storestate.StoreState) (err error) {
	if h.claims, err = state.Collection(ctx, CollectionName); err != nil {
		return err
	}
	if h.receipts, err = state.Collection(ctx, receiptsCollection); err != nil {
		return err
	}
	if err = h.claims.EnsureIndex(ctx,
		anystore.IndexInfo{Name: "operation", Fields: []string{"operation.operationId"}},
		anystore.IndexInfo{Name: "target", Fields: []string{"operation.target.objectId", "operation.target.blockId"}}); err != nil {
		return err
	}
	return h.receipts.EnsureIndex(ctx, anystore.IndexInfo{Name: "claim", Fields: []string{"claimId"}})
}

func (h *handler) BeforeCreate(ctx context.Context, ch storestate.ChangeOp) error {
	create := ch.Change.Change.GetCreate()
	claim, err := DecodeClaim(create.DocumentId, create.Value)
	if err != nil {
		return errors.Join(storestate.ErrValidation, err)
	}
	native := NativeChange{ID: ch.Change.Id, Order: ch.Change.Order, Creator: ch.Change.Creator, ACLHeadID: ch.Change.AclHeadId}
	if claim.Operation.SpaceID != h.spaceID || claim.Operation.AuthorID != native.Creator || !validNative(native) {
		return errors.Join(storestate.ErrValidation, ErrInvalid)
	}
	existing, err := h.claims.FindId(ctx, claim.ID)
	duplicate := err == nil
	if err != nil && !errors.Is(err, anystore.ErrDocNotFound) {
		return errors.Join(storestate.ErrCritical, err)
	}
	if duplicate {
		old, parseErr := claimFromValue(existing.Value())
		if parseErr != nil {
			return errors.Join(storestate.ErrCritical, parseErr)
		}
		left, _ := old.Operation.CanonicalBytes()
		right, _ := claim.Operation.CanonicalBytes()
		if !bytes.Equal(left, right) {
			return fmt.Errorf("content digest collision: %w", storestate.ErrCritical)
		}
	}
	if err = h.insertReceipt(ctx, ch, claim.ID); err != nil {
		return errors.Join(storestate.ErrCritical, err)
	}
	if duplicate {
		return storestate.ErrIgnore
	}
	return nil
}

func (h *handler) insertReceipt(ctx context.Context, ch storestate.ChangeOp, claimID string) error {
	buf := bytes.NewBufferString("pinkha-t2-receipt-v1\x00")
	putBytes(buf, []byte(claimID))
	putBytes(buf, []byte(ch.Change.Id))
	digest := sha256.Sum256(buf.Bytes())
	receipt := Receipt{ID: hex.EncodeToString(digest[:]), ClaimID: claimID, ChangeID: ch.Change.Id,
		Creator: ch.Change.Creator, ACLHeadID: ch.Change.AclHeadId}
	existing, err := h.receipts.FindId(ctx, receipt.ID)
	if err == nil {
		var old Receipt
		if err = json.Unmarshal([]byte(existing.Value().String()), &old); err != nil {
			return err
		}
		if old != receipt {
			return fmt.Errorf("native change provenance mismatch: %w", ErrInvalid)
		}
		return nil
	}
	if !errors.Is(err, anystore.ErrDocNotFound) {
		return err
	}
	v := ch.Arena.NewObject()
	v.Set("id", ch.Arena.NewString(receipt.ID))
	v.Set("claimId", ch.Arena.NewString(receipt.ClaimID))
	v.Set("changeId", ch.Arena.NewString(receipt.ChangeID))
	v.Set("creator", ch.Arena.NewString(receipt.Creator))
	v.Set("aclHeadId", ch.Arena.NewString(receipt.ACLHeadID))
	return h.receipts.Insert(ctx, v)
}

func (h *handler) BeforeModify(context.Context, storestate.ChangeOp) (storestate.ModifyMode, error) {
	return storestate.ModifyModeUpdate, fmt.Errorf("immutable claim: %w", storestate.ErrValidation)
}

func (h *handler) BeforeDelete(context.Context, storestate.ChangeOp) (storestate.DeleteMode, error) {
	return storestate.DeleteModeKeep, fmt.Errorf("append an observed remove: %w", storestate.ErrValidation)
}

func (h *handler) UpgradeKeyModifier(_ storestate.ChangeOp, _ *pb.KeyModify, mod query.Modifier) query.Modifier {
	return mod
}
