package torahops

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"slices"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/golang/snappy"

	"github.com/anyproto/anytype-heart/pb"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
)

// A bound is a refusal, never pagination/truncation. It covers both complete
// immutable histories before a cutover can be presented or locally sealed.
const maxCutoverHistoryClaims = 10000
const maxCutoverHistoryBytes = 64 * 1024 * 1024

type cutoverReadBudget struct{ remaining int }

func (b *cutoverReadBudget) take(n int) error {
	if n < 0 || n > b.remaining {
		return ErrReadLimit
	}
	b.remaining -= n
	return nil
}
func readCutoverBounded(ctx context.Context, q anystore.Query, limit uint, b *cutoverReadBudget) (result []cutover.Claim, err error) {
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
		if e = b.take(len(doc.Value().String())); e != nil {
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
func readOriginalBounded(ctx context.Context, q anystore.Query, limit uint, b *cutoverReadBudget) (result []Claim, err error) {
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
		if e = b.take(len(doc.Value().String())); e != nil {
			return nil, e
		}
		claim, e := claimFromValue(doc.Value())
		if e != nil {
			return nil, e
		}
		result = append(result, claim)
	}
	return result, iter.Err()
}
func (h *CutoverNativeHost) metadataHistoryLocked(ctx context.Context, objectID string, b *cutoverReadBudget) (CutoverHistory, error) {
	candidates, err := readCutoverBounded(ctx, h.store.claims.Find(map[string]any{"record.objectId": objectID}), maxCutoverHistoryClaims, b)
	if err != nil {
		return CutoverHistory{}, err
	}
	result := CutoverHistory{Claims: []cutover.Claim{}, Conflicts: []CutoverResolution{}}
	seen := map[string]bool{}
	for _, claim := range candidates {
		id := claim.Record.RecordID
		if seen[id] {
			continue
		}
		seen[id] = true
		variants, err := readCutoverBounded(ctx, h.store.claims.Find(map[string]any{"record.recordId": id}), MaxVariants, b)
		if err != nil {
			return CutoverHistory{}, err
		}
		if len(result.Claims)+len(variants) > maxCutoverHistoryClaims {
			return CutoverHistory{}, ErrReadLimit
		}
		for _, variant := range variants {
			// A cross-object logical collision is an explicit refusal. Never leak its
			// payload under the source object's lease or silently pick the local row.
			if variant.Record.SpaceID != h.store.spaceID || variant.Record.ObjectID != objectID {
				return CutoverHistory{}, cutover.ErrConflict
			}
		}
		if len(variants) > 1 {
			result.Conflicts = append(result.Conflicts, CutoverResolution{RecordID: id, Conflict: true, Claims: variants})
		}
		result.Claims = append(result.Claims, variants...)
	}
	return result, nil
}
func originalHistoryLocked(ctx context.Context, v1 *NativeHost, objectID string, b *cutoverReadBudget) ([]Claim, error) {
	candidates, err := readOriginalBounded(ctx, v1.store.claims.Find(map[string]any{"operation.target.objectId": objectID}), maxCutoverHistoryClaims, b)
	if err != nil {
		return nil, err
	}
	result := []Claim{}
	seen := map[string]bool{}
	for _, claim := range candidates {
		id := claim.Operation.OperationID
		if seen[id] {
			continue
		}
		seen[id] = true
		variants, err := readOriginalBounded(ctx, v1.store.claims.Find(map[string]any{"operation.operationId": id}), MaxVariants, b)
		if err != nil {
			return nil, err
		}
		if len(result)+len(variants) > maxCutoverHistoryClaims {
			return nil, ErrReadLimit
		}
		for _, variant := range variants {
			if variant.Operation.SpaceID != v1.store.spaceID || variant.Operation.Target.ObjectID != objectID {
				return nil, cutover.ErrConflict
			}
		}
		result = append(result, variants...)
	}
	return result, nil
}

// Caller holds source/settings, metadata, v1, and the shared current ACL read
// lock. SQLite rows are never enough: every receipt is checked against the
// actual native signed change and canonical operation bytes in its own tree.
func (h *CutoverNativeHost) readLocked(ctx context.Context, v1 *NativeHost, objectID string, lease *CutoverSourceLease) (CutoverNativeSnapshot, error) {
	if err := lease.Validate(ctx); err != nil {
		return CutoverNativeSnapshot{}, err
	}
	metadataSeq, err := h.recoverLocked(ctx, h.tree)
	if err != nil {
		return CutoverNativeSnapshot{}, err
	}
	originalSeq, err := v1.recoverLocked(ctx, v1.tree)
	if err != nil {
		return CutoverNativeSnapshot{}, err
	}
	budget := &cutoverReadBudget{remaining: maxCutoverHistoryBytes}
	history, err := h.metadataHistoryLocked(ctx, objectID, budget)
	if err != nil {
		return CutoverNativeSnapshot{}, err
	}
	originals, err := originalHistoryLocked(ctx, v1, objectID, budget)
	if err != nil {
		return CutoverNativeSnapshot{}, err
	}
	metadataReceipts := map[string][]Receipt{}
	originalReceipts := map[string][]Receipt{}
	for _, claim := range history.Claims {
		canonical, e := claim.Record.CanonicalBytes()
		if e != nil {
			return CutoverNativeSnapshot{}, e
		}
		receipts, e := h.store.Receipts(ctx, claim.ID)
		if e != nil {
			return CutoverNativeSnapshot{}, e
		}
		if len(receipts) == 0 {
			return CutoverNativeSnapshot{}, ErrProjectionBehind
		}
		for _, receipt := range receipts {
			if e = h.verifyReceipt(claim, canonical, receipt); e != nil {
				return CutoverNativeSnapshot{}, e
			}
		}
		metadataReceipts[claim.ID] = receipts
	}
	for _, claim := range originals {
		canonical, e := claim.Operation.CanonicalBytes()
		if e != nil {
			return CutoverNativeSnapshot{}, e
		}
		receipts, e := v1.store.Receipts(ctx, claim.ID)
		if e != nil {
			return CutoverNativeSnapshot{}, e
		}
		if len(receipts) == 0 {
			return CutoverNativeSnapshot{}, ErrProjectionBehind
		}
		for _, receipt := range receipts {
			if e = v1.verifyOperationReceipt(claim, canonical, receipt); e != nil {
				return CutoverNativeSnapshot{}, e
			}
		}
		originalReceipts[claim.ID] = receipts
	}
	state, err := projectCutover(history, originals, originalReceipts, lease.Value)
	if err != nil {
		return CutoverNativeSnapshot{}, err
	}
	metadataHeads := slices.Clone(h.tree.Heads())
	slices.Sort(metadataHeads)
	originalHeads := slices.Clone(v1.tree.Heads())
	slices.Sort(originalHeads)
	if err = lease.Validate(ctx); err != nil {
		return CutoverNativeSnapshot{}, err
	}
	return CutoverNativeSnapshot{State: state, Source: lease.Value, SourceHeads: slices.Clone(lease.Heads),
		MetadataHeads: metadataHeads, OperationHeads: originalHeads, MetadataAppliedSeq: metadataSeq, OperationAppliedSeq: originalSeq,
		MetadataHistory: history, MetadataReceipts: metadataReceipts, OriginalClaims: originals, OriginalReceipts: originalReceipts}, nil
}
func (h *CutoverNativeHost) verifyReceipt(claim cutover.Claim, canonical []byte, receipt Receipt) error {
	if receipt.ClaimID != claim.ID || receipt.Creator != claim.Record.AuthorID || !validText(receipt.ChangeID, true, 1024) || !validText(receipt.ACLHeadID, true, 1024) {
		return cutover.ErrInvalid
	}
	framed := bytes.NewBufferString("pinkha-t2-receipt-v1\x00")
	putBytes(framed, []byte(claim.ID))
	putBytes(framed, []byte(receipt.ChangeID))
	id := sha256.Sum256(framed.Bytes())
	if receipt.ID != hex.EncodeToString(id[:]) {
		return cutover.ErrInvalid
	}
	change, err := h.tree.GetChange(receipt.ChangeID)
	if err != nil {
		return err
	}
	if change == nil || change.Identity == nil || change.Identity.Account() != receipt.Creator || change.AclHeadId != receipt.ACLHeadID {
		return cutover.ErrInvalid
	}
	native, ok := change.Model.(*pb.StoreChange)
	if !ok || native == nil {
		keys, exists := h.tree.AclList().AclState().Keys()[change.ReadKeyId]
		if !exists || keys.ReadKey == nil {
			return list.ErrNoReadKey
		}
		rawKey, e := keys.ReadKey.Raw()
		if e != nil {
			return e
		}
		key, e := crypto.NewKeyDeriver(fmt.Sprintf(crypto.AnysyncTreePath, h.tree.Id())).DeriveKey(rawKey)
		if e != nil {
			return e
		}
		if len(change.Data) > snappy.MaxEncodedLen(maxCutoverNativeBytes)+128 {
			return ErrReadLimit
		}
		data, e := key.Decrypt(change.Data)
		if e != nil {
			return e
		}
		native, err = decodeCutoverStoreChange(change, data)
		if err != nil {
			return err
		}
	}
	if err = validateCutoverStoreChange(h.store.spaceID, change, native); err != nil {
		return err
	}
	create := native.ChangeSet[0].GetCreate()
	signed, err := cutover.Decode(create.DocumentId, []byte(create.Value))
	if err != nil {
		return err
	}
	actual, err := signed.Record.CanonicalBytes()
	if err != nil {
		return err
	}
	if signed.ID != claim.ID || !bytes.Equal(canonical, actual) {
		return cutover.ErrInvalid
	}
	return nil
}
