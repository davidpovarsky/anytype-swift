package torahopsobject

import (
	"bytes"
	"context"
	"slices"
	"sync/atomic"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/domain"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
)

type cutoverSourceLeaseKey struct{}

// This token extends the original native settings/document lease. It is never
// serialized or supplied by an RPC caller. The account owner holds its original
// application RLock for the entire call; current must check that held scope
// without recursively acquiring it or an ACL lock.
type cutoverSourceLease struct {
	space       smartblock.Space
	privateID   string
	objectID    string
	propertyKey string
	write       bool
	tree        objecttree.ObjectTree
	native      *targetLease
	value       torahops.CutoverLegacyValue
	heads       []string
	borrowed    atomic.Bool
	validate    func(context.Context) error
}

// AcquireNativeCutoverSourceLease shares the existing signed-settings deletion
// check and original target lock order. No legacy property is changed. Missing,
// present-empty, and exact present string bytes remain distinct; null, numeric,
// list and other property types cannot silently become an empty source.
func AcquireNativeCutoverSourceLease(ctx context.Context, space smartblock.Space,
	objectID, propertyKey string, write bool, acl list.AclList,
	current func(context.Context) error) (context.Context, func(), error) {
	if ctx == nil || space == nil || acl == nil || current == nil ||
		!operationTargetText(objectID) || !operationTargetText(propertyKey) ||
		ctx.Value(cutoverSourceLeaseKey{}) != nil || ctx.Value(semanticAnchorLeaseKey{}) != nil {
		return nil, nil, cutover.ErrInvalid
	}
	if err := current(ctx); err != nil {
		return nil, nil, err
	}
	root, err := torahcutoverroot.Root(space.Id())
	if err != nil {
		return nil, nil, err
	}
	target := torahops.Target{ObjectID: objectID}
	leaseCtx, release, err := AcquireNativeTargetLease(ctx, space, root.Id, target)
	if err != nil {
		return nil, nil, err
	}
	keep := false
	defer func() {
		if !keep {
			release()
		}
	}()
	native, _ := leaseCtx.Value(targetLeaseKey{}).(*targetLease)
	if native == nil || native.object == nil || native.settings == nil {
		return nil, nil, ErrTargetUnavailable
	}
	loader, ok := space.(nativeTargetSpace)
	if !ok {
		return nil, nil, ErrTargetUnavailable
	}
	lease := &cutoverSourceLease{space: space, privateID: root.Id, objectID: objectID,
		propertyKey: propertyKey, write: write, tree: native.object.Tree(), native: native}
	if lease.tree == nil || lease.tree.Id() != objectID ||
		lease.tree.AclList() != acl || native.settings.AclList() != acl {
		return nil, nil, ErrTargetUnavailable
	}
	lease.value, err = readNativeCutoverValue(native.object, propertyKey)
	if err != nil {
		return nil, nil, err
	}
	lease.heads, err = readNativeCutoverHeads(lease.tree)
	if err != nil {
		return nil, nil, err
	}
	lease.validate = func(check context.Context) error {
		if check == nil {
			return cutover.ErrInvalid
		}
		if err := check.Err(); err != nil {
			return err
		}
		if err := current(check); err != nil {
			return err
		}
		if err := CheckNativeTargetLease(leaseCtx, space, root.Id, target); err != nil {
			return err
		}
		if !loader.PinkhaTorahTargetIsCurrent(native.object) || native.object.Tree() != lease.tree ||
			lease.tree.AclList() != acl || native.settings.AclList() != acl {
			return ErrTargetUnavailable
		}
		if err := validateNativeSmartblock(check, space, target, native.object); err != nil {
			return err
		}
		actual, err := readNativeCutoverValue(native.object, propertyKey)
		if err != nil {
			return err
		}
		if actual.Key != lease.value.Key || actual.Present != lease.value.Present || !bytes.Equal(actual.Bytes, lease.value.Bytes) {
			return cutover.ErrLegacyChanged
		}
		heads, err := readNativeCutoverHeads(lease.tree)
		if err != nil {
			return err
		}
		if !slices.Equal(heads, lease.heads) {
			return cutover.ErrLegacyChanged
		}
		return nil
	}
	if err = lease.validate(leaseCtx); err != nil {
		return nil, nil, err
	}
	keep = true
	return context.WithValue(leaseCtx, cutoverSourceLeaseKey{}, lease), release, nil
}

func readNativeCutoverValue(object smartblock.SmartBlock, propertyKey string) (torahops.CutoverLegacyValue, error) {
	result := torahops.CutoverLegacyValue{Key: propertyKey}
	if object == nil {
		return result, ErrTargetUnavailable
	}
	// State.Details may be nil for a loaded document with no properties.
	// The native domain map explicitly defines nil.TryGet as absent. Current
	// document/cache/tree/settings authority is held and checked by the lease;
	// an absent map is not a present null property.
	value, present := object.Details().TryGet(domain.RelationKey(propertyKey))
	if !present {
		return result, nil
	}
	text, ok := value.TryString()
	if !ok {
		return result, cutover.ErrInvalid
	}
	if len(text) > cutover.MaxLegacyBytes {
		return result, torahops.ErrReadLimit
	}
	result.Present, result.Bytes = true, []byte(text)
	return result, nil
}

func readNativeCutoverHeads(tree objecttree.ObjectTree) ([]string, error) {
	if tree == nil {
		return nil, ErrTargetUnavailable
	}
	heads := slices.Clone(tree.Heads())
	slices.Sort(heads)
	if len(heads) == 0 || len(heads) > cutover.MaxSourceHeads {
		return nil, torahops.ErrReadLimit
	}
	for index, head := range heads {
		if !operationTargetText(head) || (index > 0 && heads[index-1] == head) {
			return nil, ErrTargetUnavailable
		}
	}
	return heads, nil
}

// CheckNativeCutoverSourceLease is used only by the native root-install guard.
// It does not consume the one host call, acquire nested locks, or read a caller
// provided snapshot. NativeHost separately retains current signed ACL authority.
func CheckNativeCutoverSourceLease(ctx context.Context, space smartblock.Space,
	privateID, objectID, propertyKey string, write bool) error {
	if ctx == nil {
		return cutover.ErrInvalid
	}
	lease, _ := ctx.Value(cutoverSourceLeaseKey{}).(*cutoverSourceLease)
	if lease == nil || lease.space != space || lease.privateID != privateID ||
		lease.objectID != objectID || lease.propertyKey != propertyKey || lease.write != write {
		return ErrTargetUnavailable
	}
	return lease.validate(ctx)
}

// BorrowNativeCutoverSourceLease receives the actual registered metadata tree,
// not a root ID/permission boolean from a request. A lease belongs to exactly one
// matching host call; all facts validate against that same still-locked document.
func BorrowNativeCutoverSourceLease(ctx context.Context, space smartblock.Space,
	metadata objecttree.ObjectTree, objectID, propertyKey string, write bool) (*torahops.CutoverSourceLease, error) {
	if ctx == nil || metadata == nil {
		return nil, cutover.ErrInvalid
	}
	if err := CheckNativeCutoverSourceLease(ctx, space, metadata.Id(), objectID, propertyKey, write); err != nil {
		return nil, err
	}
	lease := ctx.Value(cutoverSourceLeaseKey{}).(*cutoverSourceLease)
	if metadata.AclList() != lease.tree.AclList() || !lease.borrowed.CompareAndSwap(false, true) {
		return nil, ErrTargetUnavailable
	}
	validateTarget := func(check context.Context, target torahops.Target) error {
		if err := lease.validate(check); err != nil {
			return err
		}
		if target.ObjectID != objectID {
			return ErrTargetUnavailable
		}
		if err := validateNativeSmartblock(check, space, target, lease.native.object); err != nil {
			return err
		}
		if target.BlockID == "" {
			return nil
		}
		reachable, err := validateOperationDocumentGraph(check, lease.native.object, lease.native.object.RootId(), nil)
		if err != nil {
			return err
		}
		if !reachable[target.BlockID] {
			return ErrTargetUnavailable
		}
		return nil
	}
	return &torahops.CutoverSourceLease{
		Value: torahops.CutoverLegacyValue{Key: lease.value.Key, Present: lease.value.Present, Bytes: bytes.Clone(lease.value.Bytes)},
		Heads: slices.Clone(lease.heads), Validate: lease.validate, ValidateTarget: validateTarget, Release: lease.native.release,
	}, nil
}
