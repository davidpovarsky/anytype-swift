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
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
)

// CutoverStore is only the replayable local projection of the separate signed
// cutover tree. It is not authority to create a root or to write native history.
type CutoverStore struct {
	state    *storestate.StoreState
	claims   anystore.Collection
	receipts anystore.Collection
	spaceID  string
}
type CutoverResolution struct {
	RecordID string
	Conflict bool
	Claims   []cutover.Claim
}
type CutoverAppendResult struct {
	Disposition Disposition
	ClaimID     string
	Resolution  CutoverResolution
}
type CutoverHistory struct {
	Claims    []cutover.Claim
	Conflicts []CutoverResolution
}

// A separate namespace is essential: opening the cutover projection must not
// change v1's StoreState replay watermark or register metadata in its tree.
func NewCutoverStore(ctx context.Context, db anystore.DB, spaceID string) (*CutoverStore, error) {
	if !cutover.Text(spaceID, true, 1024) {
		return nil, cutover.ErrInvalid
	}
	h := &cutoverHandler{spaceID: spaceID}
	key := sha256.Sum256([]byte("pinkha-torah-cutover-projection-v1\x00" + spaceID))
	state, err := storestate.New(ctx, "pinkha-torah-cutover-v1-"+hex.EncodeToString(key[:]), db, h)
	if err != nil {
		return nil, err
	}
	return &CutoverStore{state: state, claims: h.claims, receipts: h.receipts, spaceID: spaceID}, nil
}

func (s *CutoverStore) checkLocal(ctx context.Context, claim cutover.Claim) (CutoverAppendResult, error) {
	resolution, err := s.ReadRecord(ctx, claim.Record.RecordID)
	if err != nil {
		return CutoverAppendResult{}, err
	}
	for _, existing := range resolution.Claims {
		if existing.ID != claim.ID {
			continue
		}
		a, _ := existing.Record.CanonicalBytes()
		b, _ := claim.Record.CanonicalBytes()
		if !bytes.Equal(a, b) {
			return CutoverAppendResult{}, errors.Join(storestate.ErrCritical, cutover.ErrConflict)
		}
		return CutoverAppendResult{Disposition: AlreadyExistsSamePayload, ClaimID: claim.ID, Resolution: resolution}, nil
	}
	if len(resolution.Claims) != 0 {
		return CutoverAppendResult{Disposition: CollisionDifferentPayload, ClaimID: claim.ID, Resolution: resolution}, nil
	}
	return CutoverAppendResult{Disposition: Created, ClaimID: claim.ID,
		Resolution: CutoverResolution{RecordID: claim.Record.RecordID, Claims: []cutover.Claim{claim}}}, nil
}

// AppendLocal/Replay accept a component's supplied NativeChange only for tests
// of the actual StoreState projection. Production uses the signed native host.
func (s *CutoverStore) AppendLocal(ctx context.Context, record cutover.Record, native NativeChange) (CutoverAppendResult, error) {
	claim, wire, err := cutover.Encode(record)
	if err != nil || record.SpaceID != s.spaceID || record.AuthorID != native.Creator || !validNative(native) {
		return CutoverAppendResult{}, errors.Join(cutover.ErrInvalid, err)
	}
	tx, err := s.state.NewTx(ctx)
	if err != nil {
		return CutoverAppendResult{}, err
	}
	defer func() { _ = tx.Rollback() }()
	result, err := s.checkLocal(tx.Context(), claim)
	if err != nil || result.Disposition != Created {
		return result, err
	}
	if err = s.apply(tx, claim.ID, wire, native); err != nil {
		return CutoverAppendResult{}, err
	}
	if err = tx.Commit(); err != nil {
		return CutoverAppendResult{}, err
	}
	return result, nil
}

func (s *CutoverStore) Replay(ctx context.Context, record cutover.Record, native NativeChange) error {
	claim, wire, err := cutover.Encode(record)
	if err != nil || record.SpaceID != s.spaceID || record.AuthorID != native.Creator || !validNative(native) {
		return errors.Join(cutover.ErrInvalid, err)
	}
	tx, err := s.state.NewTx(ctx)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	if err = s.apply(tx, claim.ID, wire, native); err != nil {
		return err
	}
	return tx.Commit()
}
func (s *CutoverStore) apply(tx *storestate.StoreStateTx, id string, wire []byte, native NativeChange) error {
	builder := &storestate.Builder{}
	if err := builder.Create(cutover.CollectionName, id, string(wire)); err != nil {
		return err
	}
	return tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{Id: native.ID, Order: native.Order,
		Creator: native.Creator, AclHeadId: native.ACLHeadID, Changes: builder.ChangeSet})
}

func (s *CutoverStore) ReadRecord(ctx context.Context, id string) (CutoverResolution, error) {
	if !cutover.Hex(id, 16) {
		return CutoverResolution{}, cutover.ErrInvalid
	}
	claims, err := readCutoverClaims(ctx, s.claims.Find(map[string]any{"record.recordId": id}), MaxVariants)
	if err != nil {
		return CutoverResolution{}, err
	}
	return CutoverResolution{RecordID: id, Conflict: len(claims) > 1, Claims: claims}, nil
}
func (s *CutoverStore) ReadObject(ctx context.Context, objectID string, limit uint) (result CutoverHistory, err error) {
	if !cutover.Text(objectID, true, 1024) || limit == 0 || limit > 10000 {
		return CutoverHistory{}, cutover.ErrInvalid
	}
	tx, err := s.claims.ReadTx(ctx)
	if err != nil {
		return CutoverHistory{}, err
	}
	defer func() { err = errors.Join(err, tx.Commit()) }()
	ctx = tx.Context()
	candidates, err := readCutoverClaims(ctx, s.claims.Find(map[string]any{"record.objectId": objectID}), limit)
	if err != nil {
		return CutoverHistory{}, err
	}
	seen := map[string]bool{}
	for _, claim := range candidates {
		if seen[claim.Record.RecordID] {
			continue
		}
		seen[claim.Record.RecordID] = true
		resolution, err := s.ReadRecord(ctx, claim.Record.RecordID)
		if err != nil {
			return CutoverHistory{}, err
		}
		if resolution.Conflict {
			result.Conflicts = append(result.Conflicts, resolution)
		}
		// Retain every variant, including a collision's foreign-target variant.
		if len(result.Claims)+len(resolution.Claims) > int(limit) {
			return CutoverHistory{}, ErrReadLimit
		}
		result.Claims = append(result.Claims, resolution.Claims...)
	}
	return result, nil
}
func (s *CutoverStore) Receipts(ctx context.Context, claimID string) ([]Receipt, error) {
	// Receipt identity is already domain separated by the cutover physical ID.
	// Reuse the existing bounded receipt reader without changing its semantics.
	reader := Store{receipts: s.receipts}
	return reader.Receipts(ctx, claimID)
}
func readCutoverClaims(ctx context.Context, q anystore.Query, limit uint) (result []cutover.Claim, err error) {
	iter, err := q.Sort("id").Limit(limit + 1).Iter(ctx)
	if err != nil {
		return nil, err
	}
	defer func() { err = errors.Join(err, iter.Close()) }()
	for iter.Next() {
		if uint(len(result)) == limit {
			return nil, ErrReadLimit
		}
		doc, e := iter.Doc()
		if e != nil {
			return nil, e
		}
		claim, e := cutoverClaimFromValue(doc.Value())
		if e != nil {
			return nil, e
		}
		result = append(result, claim)
	}
	return result, iter.Err()
}
func cutoverClaimFromValue(value *anyenc.Value) (cutover.Claim, error) {
	recordValue := value.Get("record")
	if recordValue == nil {
		return cutover.Claim{}, cutover.ErrInvalid
	}
	var record cutover.Record
	if err := json.Unmarshal([]byte(recordValue.String()), &record); err != nil {
		return cutover.Claim{}, err
	}
	claim, _, err := cutover.Encode(record)
	if err != nil {
		return cutover.Claim{}, err
	}
	if value.GetString("id") != claim.ID || value.GetString("digest") != claim.Digest {
		return cutover.Claim{}, cutover.ErrInvalid
	}
	return claim, nil
}

type cutoverHandler struct {
	spaceID  string
	claims   anystore.Collection
	receipts anystore.Collection
}

var _ storestate.Handler = (*cutoverHandler)(nil)

func (h *cutoverHandler) CollectionName() string { return cutover.CollectionName }
func (h *cutoverHandler) Init(ctx context.Context, state *storestate.StoreState) (err error) {
	if h.claims, err = state.Collection(ctx, cutover.CollectionName); err != nil {
		return err
	}
	if h.receipts, err = state.Collection(ctx, cutover.ReceiptsCollection); err != nil {
		return err
	}
	if err = h.claims.EnsureIndex(ctx, anystore.IndexInfo{Name: "record", Fields: []string{"record.recordId"}},
		anystore.IndexInfo{Name: "object", Fields: []string{"record.objectId"}}); err != nil {
		return err
	}
	return h.receipts.EnsureIndex(ctx, anystore.IndexInfo{Name: "claim", Fields: []string{"claimId"}})
}
func (h *cutoverHandler) BeforeCreate(ctx context.Context, ch storestate.ChangeOp) error {
	create := ch.Change.Change.GetCreate()
	claim, err := cutover.Decode(create.DocumentId, []byte(create.Value))
	if err != nil {
		return errors.Join(storestate.ErrValidation, err)
	}
	native := NativeChange{ID: ch.Change.Id, Order: ch.Change.Order, Creator: ch.Change.Creator, ACLHeadID: ch.Change.AclHeadId}
	if claim.Record.SpaceID != h.spaceID || claim.Record.AuthorID != native.Creator || !validNative(native) {
		return errors.Join(storestate.ErrValidation, cutover.ErrInvalid)
	}
	existing, err := h.claims.FindId(ctx, claim.ID)
	duplicate := err == nil
	if err != nil && !errors.Is(err, anystore.ErrDocNotFound) {
		return errors.Join(storestate.ErrCritical, err)
	}
	if duplicate {
		old, e := cutoverClaimFromValue(existing.Value())
		if e != nil {
			return errors.Join(storestate.ErrCritical, e)
		}
		a, _ := old.Record.CanonicalBytes()
		b, _ := claim.Record.CanonicalBytes()
		if !bytes.Equal(a, b) {
			return errors.Join(storestate.ErrCritical, cutover.ErrConflict)
		}
	}
	// The existing receipt function binds actual change/creator/ACL metadata;
	// its claim input is the already domain-separated immutable cutover ID.
	receiptWriter := handler{receipts: h.receipts}
	if err = receiptWriter.insertReceipt(ctx, ch, claim.ID); err != nil {
		return errors.Join(storestate.ErrCritical, err)
	}
	if duplicate {
		return storestate.ErrIgnore
	}
	return nil
}
func (*cutoverHandler) BeforeModify(context.Context, storestate.ChangeOp) (storestate.ModifyMode, error) {
	return storestate.ModifyModeUpdate, fmt.Errorf("immutable cutover metadata: %w", storestate.ErrValidation)
}
func (*cutoverHandler) BeforeDelete(context.Context, storestate.ChangeOp) (storestate.DeleteMode, error) {
	return storestate.DeleteModeKeep, fmt.Errorf("retain original cutover metadata: %w", storestate.ErrValidation)
}
func (*cutoverHandler) UpgradeKeyModifier(_ storestate.ChangeOp, _ *pb.KeyModify, modifier query.Modifier) query.Modifier {
	return modifier
}
