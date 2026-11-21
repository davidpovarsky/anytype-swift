package torahops

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"slices"
	"sync"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/golang/snappy"

	"github.com/anyproto/anytype-heart/pb"
)

// This is an additive read contract. It does not change immutable operation
// bytes, Append, ReadTarget, or advertise an application capability.
const AuthorizedOperationReadContract = "pinkha-authorized-operation-read-v1"
const AuthorizedOperationReadVersion uint32 = 1
const MaxAuthorizedOperationReadBytes = 4 * 1024 * 1024

var (
	ErrOperationSnapshotChanged   = errors.New("native operation candidate closure changed")
	ErrOperationTargetUnavailable = errors.New("native operation target authority unavailable")
)

type OperationTargetReachability string

const (
	OperationLiveDocument     OperationTargetReachability = "liveDocument"
	OperationLiveBlock        OperationTargetReachability = "liveBlock"
	OperationUnreachableBlock OperationTargetReachability = "unreachableBlock"
)

type AuthorizedOperationProvenance struct {
	Creator         string `json:"creator"`
	NativeChangeID  string `json:"nativeChangeId"`
	NativeACLHeadID string `json:"nativeAclHeadId"`
}

type AuthorizedOperationVariant struct {
	ClaimID        string                          `json:"claimId"`
	OperationID    string                          `json:"operationId"`
	SpaceID        string                          `json:"spaceId"`
	AuthorID       string                          `json:"authorId"`
	Target         Target                          `json:"target"`
	CanonicalBytes []byte                          `json:"canonicalBytes"`
	Provenance     []AuthorizedOperationProvenance `json:"provenance"`
	Reachability   OperationTargetReachability     `json:"reachability"`
}

type AuthorizedOperationOutcome string

const (
	OperationFound                         AuthorizedOperationOutcome = "found"
	OperationAbsentInVerifiedLocalSnapshot AuthorizedOperationOutcome = "absentInVerifiedLocalSnapshot"
)

// NativeSnapshotToken is an opaque identity of this local snapshot and its
// authority. It is neither a causal clock nor a reusable permission token.
type AuthorizedOperationSnapshot struct {
	Contract            string                       `json:"contract"`
	AccountID           string                       `json:"accountId"`
	SpaceID             string                       `json:"spaceId"`
	OperationID         string                       `json:"operationId"`
	Outcome             AuthorizedOperationOutcome   `json:"outcome"`
	Complete            bool                         `json:"complete"`
	NativeSnapshotToken string                       `json:"nativeSnapshotToken"`
	Variants            []AuthorizedOperationVariant `json:"variants"`
}

// OperationTargetLease is supplied only by the native object adapter. It owns
// one settings lock and sorted distinct document locks. Validate must perform
// nonlocking lifetime/cache checks: the private tree and ACL are held by the
// caller at that point. The actual same ACL instance is part of the binding.
type OperationTargetLease struct {
	ACL           list.AclList
	SnapshotToken string
	Reachability  map[Target]OperationTargetReachability
	Validate      func(context.Context) error
	Release       func()
}

type OperationTargetsLeaser func(context.Context, []Target) (OperationTargetLease, error)

type operationReadCandidate struct {
	ClaimID string
	Target  Target
}

// readOperationCandidates is intentionally metadata-only. It does not return
// payload, canonical bytes or receipts to an adapter before target authorization.
// The final fully decoded read repeats and validates this complete indexed ID
// closure under all native leases; truncation is always an error.
func (s *Store) readOperationCandidates(ctx context.Context, operationID string) (result []operationReadCandidate, err error) {
	if !validHex(operationID, 16) {
		return nil, ErrInvalid
	}
	iter, err := s.claims.Find(map[string]any{"operation.operationId": operationID}).Sort("id").Limit(MaxVariants + 1).Iter(ctx)
	if err != nil {
		return nil, err
	}
	defer func() { err = errors.Join(err, iter.Close()) }()
	for iter.Next() {
		if len(result) == MaxVariants {
			return nil, ErrReadLimit
		}
		if err = ctx.Err(); err != nil {
			return nil, err
		}
		doc, readErr := iter.Doc()
		if readErr != nil {
			return nil, readErr
		}
		value := doc.Value()
		op := value.Get("operation")
		if op == nil || op.GetString("operationId") != operationID || op.GetString("spaceId") != s.spaceID {
			return nil, ErrInvalid
		}
		target := op.Get("target")
		if target == nil {
			return nil, ErrInvalid
		}
		candidate := operationReadCandidate{ClaimID: value.GetString("id"),
			Target: Target{ObjectID: target.GetString("objectId"), BlockID: target.GetString("blockId")}}
		if !validClaimID(candidate.ClaimID) || candidate.ClaimID[:64] != operationKey(s.spaceID, operationID) ||
			!validText(candidate.Target.ObjectID, true, 1024) || !validText(candidate.Target.BlockID, false, 1024) ||
			(len(result) > 0 && result[len(result)-1].ClaimID >= candidate.ClaimID) {
			return nil, ErrInvalid
		}
		result = append(result, candidate)
	}
	return result, iter.Err()
}

func operationReadTargets(candidates []operationReadCandidate) []Target {
	seen := map[Target]bool{}
	result := make([]Target, 0, len(candidates))
	for _, candidate := range candidates {
		if !seen[candidate.Target] {
			seen[candidate.Target] = true
			result = append(result, candidate.Target)
		}
	}
	slices.SortFunc(result, func(a, b Target) int {
		if a.ObjectID < b.ObjectID || (a.ObjectID == b.ObjectID && a.BlockID < b.BlockID) {
			return -1
		}
		if a == b {
			return 0
		}
		return 1
	})
	return result
}

func (h *NativeHost) operationCandidates(ctx context.Context, operationID string, current func(context.Context) error) ([]operationReadCandidate, error) {
	h.tree.Lock()
	defer h.tree.Unlock()
	acl := h.tree.AclList()
	acl.RLock()
	defer acl.RUnlock()
	if err := requireCurrentReadAccess(acl, h.key); err != nil {
		return nil, err
	}
	if err := current(ctx); err != nil {
		return nil, err
	}
	if _, err := h.recoverLocked(ctx, h.tree); err != nil {
		return nil, errors.Join(ErrProjectionBehind, err)
	}
	result, err := h.store.readOperationCandidates(ctx, operationID)
	if err = errors.Join(err, current(ctx), ctx.Err()); err != nil {
		return nil, err
	}
	return result, nil
}

// ReadAuthorizedOperation returns every variant of one logical operation only
// after all its targets and current membership are authorized together. Native
// target loading happens between the two private-tree snapshots, with no cross-
// object locks held. A changed candidate closure cannot reuse the first lease.
// An absent result describes only this existing verified local history.
func (h *NativeHost) ReadAuthorizedOperation(ctx context.Context, operationID string,
	leaseTargets OperationTargetsLeaser, current func(context.Context) error) (AuthorizedOperationSnapshot, error) {
	if ctx == nil || !validHex(operationID, 16) || leaseTargets == nil || current == nil || h == nil || h.tree == nil || h.store == nil || h.key == nil {
		return AuthorizedOperationSnapshot{}, ErrInvalid
	}
	if err := errors.Join(ctx.Err(), current(ctx)); err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	// Denied membership must not load or inspect any target, even when a local
	// projection and historical decryption keys are still populated.
	if err := AuthorizeCurrentACL(h.tree.AclList(), h.key, false); err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	before, err := h.operationCandidates(ctx, operationID, current)
	if err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	targets := operationReadTargets(before)
	lease, err := leaseTargets(ctx, targets)
	if lease.Release != nil {
		var once sync.Once
		defer once.Do(lease.Release)
	}
	if err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	if lease.Release == nil || lease.Validate == nil || lease.ACL != h.tree.AclList() ||
		!validHex(lease.SnapshotToken, 32) || len(lease.Reachability) != len(targets) {
		return AuthorizedOperationSnapshot{}, ErrOperationTargetUnavailable
	}
	for _, target := range targets {
		reachability, exists := lease.Reachability[target]
		if !exists || (target.BlockID == "" && reachability != OperationLiveDocument) ||
			(target.BlockID != "" && reachability != OperationLiveBlock && reachability != OperationUnreachableBlock) {
			return AuthorizedOperationSnapshot{}, ErrOperationTargetUnavailable
		}
	}
	h.tree.Lock()
	defer h.tree.Unlock()
	acl := h.tree.AclList()
	acl.RLock()
	defer acl.RUnlock()
	if err = requireCurrentReadAccess(acl, h.key); err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	if err = errors.Join(current(ctx), lease.Validate(ctx), ctx.Err()); err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	if _, err = h.recoverLocked(ctx, h.tree); err != nil {
		return AuthorizedOperationSnapshot{}, errors.Join(ErrProjectionBehind, err)
	}
	after, err := h.store.readOperationCandidates(ctx, operationID)
	if err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	if !slices.Equal(before, after) {
		return AuthorizedOperationSnapshot{}, ErrOperationSnapshotChanged
	}
	resolution, err := h.store.ReadOperation(ctx, operationID)
	if err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	if len(resolution.Claims) != len(after) {
		return AuthorizedOperationSnapshot{}, ErrOperationSnapshotChanged
	}
	result := AuthorizedOperationSnapshot{Contract: AuthorizedOperationReadContract,
		AccountID: h.key.GetPublic().Account(), SpaceID: h.store.spaceID, OperationID: operationID,
		Outcome: OperationAbsentInVerifiedLocalSnapshot, Complete: true, Variants: make([]AuthorizedOperationVariant, 0, len(after))}
	if len(after) != 0 {
		result.Outcome = OperationFound
	}
	used := 1024 + len(result.AccountID) + len(result.SpaceID)
	for index, claim := range resolution.Claims {
		if err = ctx.Err(); err != nil {
			return AuthorizedOperationSnapshot{}, err
		}
		op := claim.Operation
		if claim.ID != after[index].ClaimID || op.Target != after[index].Target || op.SpaceID != h.store.spaceID || op.OperationID != operationID {
			return AuthorizedOperationSnapshot{}, ErrInvalid
		}
		canonical, canonicalErr := op.CanonicalBytes()
		if canonicalErr != nil {
			return AuthorizedOperationSnapshot{}, canonicalErr
		}
		receipts, receiptErr := h.store.Receipts(ctx, claim.ID)
		if receiptErr != nil {
			return AuthorizedOperationSnapshot{}, receiptErr
		}
		if len(receipts) == 0 {
			return AuthorizedOperationSnapshot{}, ErrInvalid
		}
		variant := AuthorizedOperationVariant{ClaimID: claim.ID, OperationID: op.OperationID,
			SpaceID: op.SpaceID, AuthorID: op.AuthorID, Target: op.Target, CanonicalBytes: canonical,
			Reachability: lease.Reachability[op.Target], Provenance: make([]AuthorizedOperationProvenance, 0, len(receipts))}
		used += len(canonical) + len(claim.ID) + len(op.OperationID) + len(op.SpaceID) + len(op.AuthorID) + len(op.Target.ObjectID) + len(op.Target.BlockID) + 128
		if used > MaxAuthorizedOperationReadBytes {
			return AuthorizedOperationSnapshot{}, ErrReadLimit
		}
		previousReceipt := ""
		for _, receipt := range receipts {
			if receipt.ID <= previousReceipt {
				return AuthorizedOperationSnapshot{}, ErrInvalid
			}
			previousReceipt = receipt.ID
			if err = h.verifyOperationReceipt(claim, canonical, receipt); err != nil {
				return AuthorizedOperationSnapshot{}, err
			}
			variant.Provenance = append(variant.Provenance, AuthorizedOperationProvenance{
				Creator: receipt.Creator, NativeChangeID: receipt.ChangeID, NativeACLHeadID: receipt.ACLHeadID})
			used += len(receipt.Creator) + len(receipt.ChangeID) + len(receipt.ACLHeadID) + 64
			if used > MaxAuthorizedOperationReadBytes {
				return AuthorizedOperationSnapshot{}, ErrReadLimit
			}
		}
		result.Variants = append(result.Variants, variant)
	}
	// The native bounded JSON envelope is conservative for the protobuf wire
	// response. The wire adapter independently checks its exact encoded Size.
	encoded, err := json.Marshal(result)
	if err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	if len(encoded)+64 > MaxAuthorizedOperationReadBytes {
		return AuthorizedOperationSnapshot{}, ErrReadLimit
	}
	aclHead := acl.Head()
	if aclHead == nil || aclHead.Id == "" {
		return AuthorizedOperationSnapshot{}, ErrInvalid
	}
	heads := slices.Clone(h.tree.Heads())
	slices.Sort(heads)
	if len(heads) == 0 || len(heads) > 10000 {
		return AuthorizedOperationSnapshot{}, ErrReadLimit
	}
	token := bytes.NewBufferString(AuthorizedOperationReadContract + "\x00heart\x00")
	putBytes(token, []byte(h.tree.Id()))
	putBytes(token, []byte(aclHead.Id))
	putBytes(token, []byte(lease.SnapshotToken))
	for _, head := range heads {
		putBytes(token, []byte(head))
	}
	putBytes(token, encoded)
	digest := sha256.Sum256(token.Bytes())
	result.NativeSnapshotToken = hex.EncodeToString(digest[:])
	if err = errors.Join(current(ctx), lease.Validate(ctx), ctx.Err()); err != nil {
		return AuthorizedOperationSnapshot{}, err
	}
	return result, nil
}

// Projection receipts alone are insufficient: bind every returned receipt back
// to the actual verified signed change currently in the private native tree.
// Caller holds the private tree and current ACL read lock.
func (h *NativeHost) verifyOperationReceipt(claim Claim, canonical []byte, receipt Receipt) error {
	if receipt.ClaimID != claim.ID || receipt.Creator != claim.Operation.AuthorID ||
		!validText(receipt.ChangeID, true, 1024) || !validText(receipt.ACLHeadID, true, 1024) {
		return ErrInvalid
	}
	framed := bytes.NewBufferString("pinkha-t2-receipt-v1\x00")
	putBytes(framed, []byte(claim.ID))
	putBytes(framed, []byte(receipt.ChangeID))
	id := sha256.Sum256(framed.Bytes())
	if receipt.ID != hex.EncodeToString(id[:]) {
		return ErrInvalid
	}
	change, err := h.tree.GetChange(receipt.ChangeID)
	if err != nil {
		return err
	}
	if change == nil || change.Identity == nil || change.Identity.Account() != receipt.Creator || change.AclHeadId != receipt.ACLHeadID {
		return ErrInvalid
	}
	native, ok := change.Model.(*pb.StoreChange)
	if !ok || native == nil {
		keys, exists := h.tree.AclList().AclState().Keys()[change.ReadKeyId]
		if !exists || keys.ReadKey == nil {
			return list.ErrNoReadKey
		}
		rawKey, keyErr := keys.ReadKey.Raw()
		if keyErr != nil {
			return keyErr
		}
		key, keyErr := crypto.NewKeyDeriver(fmt.Sprintf(crypto.AnysyncTreePath, h.tree.Id())).DeriveKey(rawKey)
		if keyErr != nil {
			return keyErr
		}
		if len(change.Data) > snappy.MaxEncodedLen(maxNativeBytes)+128 {
			return ErrReadLimit
		}
		data, decodeErr := key.Decrypt(change.Data)
		if decodeErr != nil {
			return decodeErr
		}
		native, err = decodeNativeStoreChange(change, data)
		if err != nil {
			return err
		}
	}
	if err = validateNativeStoreChange(h.store.spaceID, change, native); err != nil {
		return err
	}
	create := native.ChangeSet[0].GetCreate()
	signed, err := DecodeClaim(create.DocumentId, create.Value)
	if err != nil {
		return err
	}
	signedBytes, err := signed.Operation.CanonicalBytes()
	if err != nil {
		return err
	}
	if signed.ID != claim.ID || !bytes.Equal(signedBytes, canonical) {
		return ErrInvalid
	}
	return nil
}
