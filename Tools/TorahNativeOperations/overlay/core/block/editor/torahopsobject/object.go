// Package torahopsobject binds the private native host to Heart's object cache.
// It is a storage adapter, not a document renderer or a second AI engine.
package torahopsobject

import (
	"context"
	"errors"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/source"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

var ErrTargetUnavailable = errors.New("native Torah target is unavailable in this Space")

// StoreObject methods acquire their own native tree lock. Call them after
// GetObject returns, never from Space.Do or another callback holding this tree.
// These methods are not yet application RPCs and do not enable an App capability.
type StoreObject interface {
	smartblock.SmartBlock
	AppendTorahOperation(context.Context, torahops.Operation) (torahops.NativeAppendResult, error)
	ReadTorahTarget(context.Context, torahops.Target, uint) (torahops.NativeSnapshot, error)
}

type object struct {
	smartblock.SmartBlock
	space        smartblock.Space
	projectionDB anystore.DB
	key          crypto.PrivKey
	host         *torahops.NativeHost
}

func New(sb smartblock.SmartBlock, space smartblock.Space, projectionDB anystore.DB, key crypto.PrivKey) StoreObject {
	return &object{SmartBlock: sb, space: space, projectionDB: projectionDB, key: key}
}

func (o *object) Init(ctx *smartblock.InitContext) error {
	if ctx == nil || ctx.Ctx == nil || ctx.Source == nil || o.space == nil || o.projectionDB == nil || o.key == nil {
		return torahopscontract.ErrPrivateRoot
	}
	provider, ok := ctx.Source.(source.ObjectTreeProvider)
	if !ok {
		return torahopscontract.ErrPrivateRoot
	}
	tree, ok := provider.Tree().(synctree.SyncTree)
	if !ok {
		return torahopscontract.ErrPrivateRoot
	}
	init, ok := o.SmartBlock.(interface {
		InitTorahOperations(*smartblock.InitContext) error
	})
	if !ok {
		return torahopscontract.ErrPrivateOperation
	}
	if err := init.InitTorahOperations(ctx); err != nil {
		return err
	}
	// The factory holds this tree lock. Calling OpenNativeHost here would
	// re-enter it. The CRDT projection DB is distinct from native store.db.
	host, err := torahops.OpenNativeHostLocked(ctx.Ctx, o.projectionDB, o.space.Id(), tree, o.key, o.validateTarget)
	if err != nil {
		return err
	}
	o.host = host
	return nil
}

func (o *object) validateTarget(ctx context.Context, target torahops.Target) error {
	return ValidateNativeTarget(ctx, o.space, o.Id(), target)
}

// ValidateNativeTarget is shared by the account-scoped boundary before lazy
// root creation and by NativeHost immediately before a write/read. It does not
// grant ACL authority and must receive a native Space, never RPC lookup data.
func ValidateNativeTarget(ctx context.Context, space smartblock.Space, privateID string, target torahops.Target) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	// Reject our own ID before Space.Do can try to acquire this same tree lock.
	if space == nil || target.ObjectID == "" || target.ObjectID == privateID {
		return ErrTargetUnavailable
	}
	return space.Do(target.ObjectID, func(sb smartblock.SmartBlock) error {
		if err := ctx.Err(); err != nil {
			return err
		}
		if sb.SpaceID() != space.Id() || sb.IsDeleted() || sb.Details().GetBool(bundle.RelationKeyIsDeleted) ||
			sb.Details().GetBool(bundle.RelationKeyIsUninstalled) ||
			!sb.Type().IsOneOf(coresb.SmartBlockTypePage, coresb.SmartBlockTypeTemplate) {
			return ErrTargetUnavailable
		}
		if target.BlockID != "" && sb.Pick(target.BlockID) == nil {
			return ErrTargetUnavailable
		}
		return nil
	})
}

func (o *object) AppendTorahOperation(ctx context.Context, op torahops.Operation) (torahops.NativeAppendResult, error) {
	if o.host == nil {
		return torahops.NativeAppendResult{}, torahopscontract.ErrPrivateOperation
	}
	// A previously durable receipt is preserved, but the host adapter refuses
	// new/retried access through a target that is currently unavailable. The
	// native callback checks again under the operation-tree lock before write.
	if err := o.validateTarget(ctx, op.Target); err != nil {
		return torahops.NativeAppendResult{}, err
	}
	return o.host.Append(ctx, op)
}

func (o *object) ReadTorahTarget(ctx context.Context, target torahops.Target, limit uint) (torahops.NativeSnapshot, error) {
	if o.host == nil {
		return torahops.NativeSnapshot{}, torahopscontract.ErrPrivateOperation
	}
	if err := o.validateTarget(ctx, target); err != nil {
		return torahops.NativeSnapshot{}, err
	}
	return o.host.ReadTarget(ctx, target, limit)
}

func (*object) Show() (*model.ObjectView, error) { return nil, torahopscontract.ErrPrivateOperation }
func (*object) Apply(*state.State, ...smartblock.ApplyFlag) error {
	return torahopscontract.ErrPrivateOperation
}
func (*object) ResetToVersion(*state.State) error { return torahopscontract.ErrPrivateOperation }
func (*object) StateAppend(func(state.Doc) (*state.State, []*pb.ChangeContent, error)) error {
	return torahopscontract.ErrPrivateOperation
}
func (*object) StateRebuild(state.Doc) error { return torahopscontract.ErrPrivateOperation }
func (*object) UniqueKey() domain.UniqueKey {
	return domain.MustUniqueKey(coresb.SmartBlockTypePinkhaTorahOperations, torahopscontract.UniqueKeyVersion)
}
