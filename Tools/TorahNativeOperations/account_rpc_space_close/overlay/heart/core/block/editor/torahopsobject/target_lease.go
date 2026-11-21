package torahopsobject

import (
	"context"
	"errors"
	"github.com/anyproto/anytype-heart/util/pinkhat2spaceclosetest"
	"sync"
	"sync/atomic"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
)

// Only native Space/cache adapters supply these methods. The settings tree must
// be the existing reserved object that DeleteTree and incoming settings sync use,
// never a second tree built over the same storage with an independent mutex.
type nativeTargetSpace interface {
	GetObject(context.Context, string) (smartblock.SmartBlock, error)
	PinkhaTorahSettingsTree(context.Context) (objecttree.ObjectTree, error)
	PinkhaTorahTargetIsCurrent(smartblock.SmartBlock) bool
}

type targetLeaseKey struct{}
type targetLease struct {
	space     smartblock.Space
	privateID string
	target    torahops.Target
	active    atomic.Bool
	borrowed  atomic.Bool
	release   func()
}

// AcquireNativeTargetLease loads before taking cross-object locks, then acquires
// settings -> target. NativeHost subsequently takes private tree -> ACL. The
// target mutex covers block changes and template uninstall; settings covers the
// durable ObjectDelete intent, which precedes asynchronous SmartBlock deletion.
// The lease can be borrowed by exactly one host call and released only once.
func AcquireNativeTargetLease(ctx context.Context, space smartblock.Space, privateID string, target torahops.Target) (context.Context, func(), error) {
	if ctx == nil {
		return nil, nil, torahops.ErrInvalid
	}
	if err := ctx.Err(); err != nil {
		return nil, nil, err
	}
	if space == nil || target.ObjectID == "" || target.ObjectID == privateID || ctx.Value(targetLeaseKey{}) != nil {
		return nil, nil, ErrTargetUnavailable
	}
	loader, ok := space.(nativeTargetSpace)
	if !ok {
		return nil, nil, ErrTargetUnavailable
	}
	// Loading can call other native services. Never do it while holding a
	// settings, target, private-tree, or ACL lock.
	sb, err := loader.GetObject(ctx, target.ObjectID)
	if err != nil {
		return nil, nil, err
	}
	settings, err := loader.PinkhaTorahSettingsTree(ctx)
	if err != nil {
		return nil, nil, err
	}
	if sb == nil || settings == nil || settings.Id() == privateID || settings.Id() == target.ObjectID {
		return nil, nil, ErrTargetUnavailable
	}
	settings.Lock()
	if err = ctx.Err(); err == nil {
		err = rejectDeletedNativeTarget(ctx, settings, target.ObjectID)
	}
	if err != nil {
		settings.Unlock()
		return nil, nil, err
	}
	sb.Lock()
	if err = ctx.Err(); err == nil {
		if !loader.PinkhaTorahTargetIsCurrent(sb) {
			err = ErrTargetUnavailable
		} else {
			err = validateNativeSmartblock(ctx, space, target, sb)
		}
	}
	if err != nil {
		sb.Unlock()
		settings.Unlock()
		return nil, nil, err
	}
	lease := &targetLease{space: space, privateID: privateID, target: target}
	lease.active.Store(true)
	pinkhat2spaceclosetest.Point(ctx, "lease-settings-held", settings.Id(), "", settings)
	var once sync.Once
	lease.release = func() {
		once.Do(func() {
			lease.active.Store(false)
			pinkhat2spaceclosetest.Point(ctx, "lease-before-release", settings.Id(), "", settings)
			sb.Unlock()
			settings.Unlock()
		})
	}
	return context.WithValue(ctx, targetLeaseKey{}, lease), lease.release, nil
}

// CheckNativeTargetLease is a nonlocking capability check for the first-root
// storage guard. It must not reacquire target/settings while their lease is held.
func CheckNativeTargetLease(ctx context.Context, space smartblock.Space, privateID string, target torahops.Target) error {
	if ctx == nil {
		return torahops.ErrInvalid
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	lease, _ := ctx.Value(targetLeaseKey{}).(*targetLease)
	if lease == nil || !lease.active.Load() || lease.space != space || lease.privateID != privateID || lease.target != target {
		return ErrTargetUnavailable
	}
	return nil
}

func (o *object) leaseTarget(ctx context.Context, target torahops.Target) (func(), error) {
	if lease, _ := ctx.Value(targetLeaseKey{}).(*targetLease); lease != nil {
		if err := CheckNativeTargetLease(ctx, o.space, o.Id(), target); err != nil {
			return nil, err
		}
		if !lease.borrowed.CompareAndSwap(false, true) {
			return nil, ErrTargetUnavailable
		}
		return lease.release, nil
	}
	_, release, err := AcquireNativeTargetLease(ctx, o.space, o.Id(), target)
	return release, err
}

// Caller holds the actual live settings lock. Full genesis history is required:
// a snapshot's accumulated deletion set is not a safe replacement for branches
// preceding that snapshot. Native ObjectDelete is permanent; template uninstall
// and restored blocks are judged by current target state, not this history scan.
func rejectDeletedNativeTarget(ctx context.Context, settings objecttree.ObjectTree, targetID string) error {
	history, err := objecttree.BuildHistoryTree(objecttree.HistoryTreeParams{
		Storage: settings.Storage(), AclList: settings.AclList(),
	})
	if err != nil {
		return err
	}
	if history.Root().Id != settings.Id() {
		return torahops.ErrInvalid
	}
	var iterErr error
	err = history.IterateRoot(func(_ *objecttree.Change, data []byte) (any, error) {
		value := &spacesyncproto.SettingsData{}
		if err := value.UnmarshalVT(data); err != nil {
			return nil, err
		}
		return value, nil
	}, func(change *objecttree.Change) bool {
		if iterErr = ctx.Err(); iterErr != nil {
			return false
		}
		if len(change.PreviousIds) == 0 {
			return true
		}
		data, ok := change.Model.(*spacesyncproto.SettingsData)
		if !ok || data == nil {
			iterErr = torahops.ErrInvalid
			return false
		}
		for _, content := range data.GetContent() {
			if content.GetObjectDelete().GetId() == targetID || content.GetSpaceDelete() != nil {
				iterErr = ErrTargetUnavailable
				return false
			}
		}
		return true
	})
	return errors.Join(err, iterErr, ctx.Err())
}
