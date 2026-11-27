package torahops

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"slices"
	"sync"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/golang/snappy"

	"github.com/anyproto/anytype-heart/core/block/editor/storestate"
	"github.com/anyproto/anytype-heart/pb"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	cutoverroot "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
)

// CutoverSourceLease is issued only by the real account/space/target adapter.
// It retains native settings and object locks until Release. Validate must not
// reacquire those locks: it checks the current account/owner lifetime under the
// already held lease. Values and heads are read from that locked native object.
// Nothing in this structure is accepted as authority from a protobuf request.
type CutoverSourceLease struct {
	Value          CutoverLegacyValue
	Heads          []string
	Validate       func(context.Context) error
	ValidateTarget func(context.Context, Target) error
	Release        func()
}
type CutoverSourceLeaser func(ctx context.Context, objectID, propertyKey string, write bool) (*CutoverSourceLease, error)

type CutoverNativeHost struct {
	store       *CutoverStore
	tree        synctree.SyncTree
	key         crypto.PrivKey
	leaseSource CutoverSourceLeaser
}
type CutoverNativeAppendResult struct {
	CutoverAppendResult
	ChangeID string
}
type CutoverNativeSnapshot struct {
	State               CutoverState
	Source              CutoverLegacyValue
	SourceHeads         []string
	MetadataHeads       []string
	OperationHeads      []string
	MetadataAppliedSeq  uint64
	OperationAppliedSeq uint64
	MetadataHistory     CutoverHistory
	MetadataReceipts    map[string][]Receipt
	OriginalClaims      []Claim
	OriginalReceipts    map[string][]Receipt
}

func OpenCutoverNativeHost(ctx context.Context, db anystore.DB, spaceID string, tree synctree.SyncTree,
	key crypto.PrivKey, lease CutoverSourceLeaser) (*CutoverNativeHost, error) {
	if tree == nil || key == nil || lease == nil {
		return nil, cutover.ErrInvalid
	}
	tree.Lock()
	defer tree.Unlock()
	return OpenCutoverNativeHostLocked(ctx, db, spaceID, tree, key, lease)
}

// The native factory calls this variant while holding this exact metadata tree.
// It does not load or lock the independent v1 host during factory construction.
func OpenCutoverNativeHostLocked(ctx context.Context, db anystore.DB, spaceID string, tree synctree.SyncTree,
	key crypto.PrivKey, lease CutoverSourceLeaser) (*CutoverNativeHost, error) {
	if tree == nil || key == nil || lease == nil {
		return nil, cutover.ErrInvalid
	}
	root, err := cutoverroot.Root(spaceID)
	if err != nil {
		return nil, err
	}
	if tree.Id() != root.Id || !bytes.Equal(tree.Header().RawChange, root.RawChange) {
		return nil, cutover.ErrInvalid
	}
	if _, err = boundNativeCommitStorage(tree); err != nil {
		return nil, err
	}
	acl := tree.AclList()
	acl.RLock()
	defer acl.RUnlock()
	if err = requireCurrentReadAccess(acl, key); err != nil {
		return nil, err
	}
	store, err := NewCutoverStore(ctx, db, spaceID)
	if err != nil {
		return nil, err
	}
	host := &CutoverNativeHost{store: store, tree: tree, key: key, leaseSource: lease}
	if _, err = host.recoverLocked(ctx, tree); err != nil {
		return nil, err
	}
	tree.SetDeferredUpdater(true)
	tree.SetListener(host)
	return host, nil
}
func (h *CutoverNativeHost) Update(tree objecttree.ObjectTree) error {
	_, err := h.recoverLocked(context.Background(), tree)
	return err
}
func (h *CutoverNativeHost) Rebuild(tree objecttree.ObjectTree) error { return h.Update(tree) }

// Only the separate metadata tree is replayed here. Cross-tree references are
// resolved by a jointly locked read; remote arrival order may leave them pending.
func (h *CutoverNativeHost) recoverLocked(ctx context.Context, tree objecttree.ObjectTree) (uint64, error) {
	if tree.Id() != h.tree.Id() || tree.Root().Id != tree.Id() || tree.Root().SnapshotCounter > 1 {
		return 0, fmt.Errorf("cutover tree must retain genesis history: %w", cutover.ErrInvalid)
	}
	tx, err := h.store.state.NewTx(ctx)
	if err != nil {
		return 0, err
	}
	defer func() { _ = tx.Rollback() }()
	convert := func(ch *objecttree.Change, data []byte) (any, error) {
		change, e := decodeCutoverStoreChange(ch, data)
		if e == nil {
			e = validateCutoverStoreChange(h.store.spaceID, ch, change)
		}
		return change, e
	}
	var applyErr error
	iterate := func(ch *objecttree.Change) bool {
		if applyErr = ctx.Err(); applyErr != nil {
			return false
		}
		if ch.Id != tree.Id() {
			change, ok := ch.Model.(*pb.StoreChange)
			if !ok {
				applyErr = cutover.ErrInvalid
				return false
			}
			if applyErr = validateCutoverStoreChange(h.store.spaceID, ch, change); applyErr != nil {
				return false
			}
			applyErr = tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{Id: ch.Id, Order: ch.OrderId,
				Creator: ch.Identity.Account(), AclHeadId: ch.AclHeadId, Timestamp: ch.Timestamp, Changes: change.ChangeSet})
			if applyErr != nil {
				return false
			}
		}
		tx.UpdateMaxAddSeq(ch.AddSeq)
		return true
	}
	if tx.IsFullyReplayed() {
		err = tree.IterateAfterAddSeq(ctx, tx.GetMaxAddSeq(), convert, iterate)
	} else {
		err = tree.IterateRoot(convert, iterate)
	}
	if err = errors.Join(err, applyErr); err != nil {
		return 0, err
	}
	tx.MarkFullyReplayed()
	seq := tx.GetMaxAddSeq()
	return seq, tx.Commit()
}

func (h *CutoverNativeHost) acquireSource(ctx context.Context, objectID, key string, write bool) (*CutoverSourceLease, error) {
	if !cutover.Text(objectID, true, 1024) || !cutover.Text(key, true, 1024) {
		return nil, cutover.ErrInvalid
	}
	lease, err := h.leaseSource(ctx, objectID, key, write)
	if err != nil {
		if lease != nil && lease.Release != nil {
			lease.Release()
		}
		return nil, err
	}
	if lease == nil || lease.Release == nil || lease.Validate == nil || lease.ValidateTarget == nil {
		if lease != nil && lease.Release != nil {
			lease.Release()
		}
		return nil, cutover.ErrInvalid
	}
	release := lease.Release
	var once sync.Once
	lease.Release = func() { once.Do(release) }
	if lease.Value.Key != key || len(lease.Value.Bytes) > cutover.MaxLegacyBytes || (!lease.Value.Present && len(lease.Value.Bytes) != 0) ||
		len(lease.Heads) == 0 || len(lease.Heads) > cutover.MaxSourceHeads {
		lease.Release()
		return nil, cutover.ErrInvalid
	}
	sorted := slices.Clone(lease.Heads)
	slices.Sort(sorted)
	for i, head := range sorted {
		if !cutover.Text(head, true, 1024) || (i > 0 && head == sorted[i-1]) {
			lease.Release()
			return nil, cutover.ErrInvalid
		}
	}
	lease.Heads = sorted
	lease.Value.Bytes = bytes.Clone(lease.Value.Bytes)
	if err = lease.Validate(ctx); err != nil {
		lease.Release()
		return nil, err
	}
	return lease, nil
}

// Both hosts must be the exact current space/account and share the same actual
// native ACL object. A caller cannot join independently authorized snapshots.
func (h *CutoverNativeHost) validatePair(v1 *NativeHost) error {
	if h == nil || h.tree == nil || h.key == nil || v1 == nil || v1.tree == nil || v1.key == nil ||
		h.store.spaceID != v1.store.spaceID || h.key.GetPublic().Account() != v1.key.GetPublic().Account() ||
		h.tree.AclList() != v1.tree.AclList() || h.tree.Id() == v1.tree.Id() {
		return cutover.ErrInvalid
	}
	return nil
}
func (h *CutoverNativeHost) Read(ctx context.Context, v1 *NativeHost, objectID, propertyKey string) (CutoverNativeSnapshot, error) {
	if err := h.validatePair(v1); err != nil {
		return CutoverNativeSnapshot{}, err
	}
	if err := AuthorizeCurrentACL(h.tree.AclList(), h.key, false); err != nil {
		return CutoverNativeSnapshot{}, err
	}
	lease, err := h.acquireSource(ctx, objectID, propertyKey, false)
	if err != nil {
		return CutoverNativeSnapshot{}, err
	}
	defer lease.Release()
	// The shared order is target/settings -> metadata -> v1 -> current ACL.
	// Existing v1 operations use target/settings -> v1, so no reverse edge exists.
	h.tree.Lock()
	defer h.tree.Unlock()
	v1.tree.Lock()
	defer v1.tree.Unlock()
	acl := h.tree.AclList()
	acl.RLock()
	defer acl.RUnlock()
	if err = requireCurrentReadAccess(acl, h.key); err != nil {
		return CutoverNativeSnapshot{}, err
	}
	result, err := h.readLocked(ctx, v1, objectID, lease)
	if err == nil {
		err = lease.Validate(ctx)
	}
	if err != nil {
		return CutoverNativeSnapshot{}, err
	}
	return result, nil
}

func (h *CutoverNativeHost) Append(ctx context.Context, v1 *NativeHost, record cutover.Record) (CutoverNativeAppendResult, error) {
	claim, wire, err := cutover.Encode(record)
	if err != nil {
		return CutoverNativeAppendResult{}, err
	}
	record = claim.Record // own the canonical, deep-copied frozen operation bytes.
	if err = h.validatePair(v1); err != nil {
		return CutoverNativeAppendResult{}, err
	}
	if record.SpaceID != h.store.spaceID || record.AuthorID != h.key.GetPublic().Account() {
		return CutoverNativeAppendResult{}, cutover.ErrInvalid
	}
	if err = AuthorizeCurrentACL(h.tree.AclList(), h.key, true); err != nil {
		return CutoverNativeAppendResult{}, err
	}
	propertyKey := ""
	if record.Kind == cutover.Begin {
		propertyKey = record.Plan.PropertyKey
	} else {
		// This lookup supplies only a candidate key. It carries no source/ACL
		// authority and is revalidated against full signed history below.
		h.tree.Lock()
		candidate, e := h.candidatePropertyLocked(ctx, record.ObjectID, record.PlanID)
		h.tree.Unlock()
		if e != nil {
			return CutoverNativeAppendResult{}, e
		}
		propertyKey = candidate
	}
	lease, err := h.acquireSource(ctx, record.ObjectID, propertyKey, true)
	if err != nil {
		return CutoverNativeAppendResult{}, err
	}
	defer lease.Release()
	h.tree.Lock()
	defer h.tree.Unlock()
	v1.tree.Lock()
	defer v1.tree.Unlock()
	acl := h.tree.AclList()
	acl.RLock()
	if !acl.AclState().Permissions(h.key.GetPublic()).CanWrite() {
		acl.RUnlock()
		return CutoverNativeAppendResult{}, list.ErrInsufficientPermissions
	}
	snapshot, err := h.readLocked(ctx, v1, record.ObjectID, lease)
	if err == nil {
		err = lease.Validate(ctx)
	}
	if err == nil {
		err = requireCurrentCutoverSource(snapshot.State)
	}
	if err != nil {
		acl.RUnlock()
		return CutoverNativeAppendResult{}, err
	}
	existing, err := h.store.checkLocal(ctx, claim)
	if err != nil || existing.Disposition != Created {
		acl.RUnlock()
		return CutoverNativeAppendResult{CutoverAppendResult: existing}, err
	}
	err = validateCutoverAppend(record, snapshot)
	if err == nil {
		plan := snapshot.State.Plan
		if record.Kind == cutover.Begin {
			plan = record.Plan
		}
		if plan == nil {
			err = cutover.ErrIncomplete
		} else {
			for _, fact := range plan.Facts {
				if err = lease.ValidateTarget(ctx, Target{ObjectID: record.ObjectID, BlockID: fact.BlockID}); err != nil {
					break
				}
			}
		}
	}
	acl.RUnlock()
	if err != nil {
		return CutoverNativeAppendResult{}, err
	}
	// Do not hold ACL RLock recursively across commit: the mandatory storage
	// guard acquires it immediately before durable storage and checks current ACL.
	return h.appendLocked(ctx, claim, wire, lease)
}
func (h *CutoverNativeHost) candidatePropertyLocked(ctx context.Context, objectID, planID string) (string, error) {
	// Even this internal property-key lookup holds verified current authority
	// through recovery and history access. A later held source lease revalidates
	// the full property and operation; this candidate is never RPC authority.
	acl := h.tree.AclList()
	acl.RLock()
	defer acl.RUnlock()
	if err := requireCurrentReadAccess(acl, h.key); err != nil {
		return "", err
	}
	if !acl.AclState().Permissions(h.key.GetPublic()).CanWrite() {
		return "", list.ErrInsufficientPermissions
	}
	if _, err := h.recoverLocked(ctx, h.tree); err != nil {
		return "", err
	}
	history, err := h.metadataHistoryLocked(ctx, objectID, &cutoverReadBudget{remaining: maxCutoverHistoryBytes})
	if err != nil {
		return "", err
	}
	key := ""
	for _, claim := range history.Claims {
		r := claim.Record
		if r.ObjectID != objectID {
			return "", cutover.ErrConflict
		}
		if r.Kind == cutover.Begin && r.PlanID == planID {
			if key != "" && key != r.Plan.PropertyKey {
				return "", cutover.ErrConflict
			}
			key = r.Plan.PropertyKey
		}
	}
	if key == "" {
		return "", cutover.ErrIncomplete
	}
	return key, nil
}
func validateCutoverAppend(record cutover.Record, s CutoverNativeSnapshot) error {
	if err := requireCurrentCutoverSource(s.State); err != nil {
		return err
	}
	switch record.Kind {
	case cutover.Begin:
		if record.Plan == nil || cutover.ValidateSourceCoverage(*record.Plan) != nil {
			return cutover.ErrInvalid
		}
		p := record.Plan
		if p.PropertyKey != s.Source.Key || p.ValuePresent != s.Source.Present || !bytes.Equal(p.LegacyValue, s.Source.Bytes) {
			return cutover.ErrLegacyChanged
		}
		heads := slices.Clone(record.SourceHeads)
		slices.Sort(heads)
		if !slices.Equal(heads, s.SourceHeads) {
			return cutover.ErrLegacyChanged
		}
		if s.State.PlanID != "" && s.State.PlanID != record.PlanID {
			return cutover.ErrConflict
		}
		return nil
	case cutover.Import:
		if s.State.Plan == nil || s.State.PlanID != record.PlanID {
			return cutover.ErrIncomplete
		}
		var found *CutoverImport
		for i := range s.State.Imports {
			if s.State.Imports[i].FactID == record.FactID && s.State.Imports[i].ClaimID == record.ImportClaimID {
				found = &s.State.Imports[i]
			}
		}
		if found == nil {
			return cutover.ErrIncomplete
		}
		actual := s.OriginalReceipts[found.ClaimID]
		if len(actual) != len(record.NativeChanges) {
			return cutover.ErrIncomplete
		}
		for _, receipt := range actual {
			present := false
			for _, w := range record.NativeChanges {
				if w.ChangeID == receipt.ChangeID && w.Creator == receipt.Creator && w.ACLHeadID == receipt.ACLHeadID {
					present = true
				}
			}
			if !present {
				return cutover.ErrIncomplete
			}
		}
		return nil
	case cutover.Seal:
		return requireCompleteSeal(s.State, record)
	default:
		return cutover.ErrInvalid
	}
}

func (h *CutoverNativeHost) appendLocked(ctx context.Context, claim cutover.Claim, wire []byte, lease *CutoverSourceLease) (CutoverNativeAppendResult, error) {
	if err := lease.Validate(ctx); err != nil {
		return CutoverNativeAppendResult{}, err
	}
	tx, err := h.store.state.NewTx(ctx)
	if err != nil {
		return CutoverNativeAppendResult{}, err
	}
	defer func() { _ = tx.Rollback() }()
	result, err := h.store.checkLocal(tx.Context(), claim)
	if err != nil || result.Disposition != Created {
		return CutoverNativeAppendResult{CutoverAppendResult: result}, err
	}
	build := &storestate.Builder{}
	if err = build.Create(cutover.CollectionName, claim.ID, string(wire)); err != nil {
		return CutoverNativeAppendResult{}, err
	}
	data, err := build.StoreChange.Marshal()
	if err != nil {
		return CutoverNativeAppendResult{}, err
	}
	dataType := ""
	if len(data) > 64 {
		data, dataType = snappy.Encode(nil, data), nativeSnappy
	}
	appendCtx, guard, err := nativeCommitContext(ctx, h.tree, h.key.GetPublic(), lease.Release)
	if err != nil {
		return CutoverNativeAppendResult{}, err
	}
	added, err := h.tree.AddContentWithValidator(appendCtx, objecttree.SignableChangeContent{
		Data: data, DataType: dataType, Key: h.key, ShouldBeEncrypted: true, Timestamp: time.Now().Unix(),
	}, func(raw objecttree.StorageChange) error {
		if e := lease.Validate(ctx); e != nil {
			return e
		}
		ch, e := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), h.tree.Header()).Unmarshall(raw.RawTreeChangeWithId(), true)
		if e != nil {
			return e
		}
		if ch.Identity == nil || ch.Identity.Account() != claim.Record.AuthorID || !validNative(NativeChange{ID: ch.Id, Order: raw.OrderId, Creator: ch.Identity.Account(), ACLHeadID: ch.AclHeadId}) {
			return cutover.ErrInvalid
		}
		return tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{Id: ch.Id, Order: raw.OrderId, Creator: ch.Identity.Account(), AclHeadId: ch.AclHeadId, Timestamp: ch.Timestamp, Changes: build.ChangeSet})
	})
	if guard.committed == nil {
		if err == nil {
			err = ErrNativeCommitGuard
		}
		return CutoverNativeAppendResult{}, err
	}
	committed := guard.committed
	response := CutoverNativeAppendResult{CutoverAppendResult: result, ChangeID: committed.Id}
	if err == nil && (len(added.Added) != 1 || added.Added[0].Id != committed.Id) {
		err = fmt.Errorf("unexpected cutover native append result: %w", cutover.ErrInvalid)
	}
	tx.UpdateMaxAddSeq(committed.AddSeq)
	if projectionErr := tx.Commit(); projectionErr != nil {
		return response, errors.Join(err, ErrProjectionBehind, projectionErr)
	}
	return response, err
}
