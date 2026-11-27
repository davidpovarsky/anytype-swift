package torahopsobject

import (
	"context"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/source"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// CutoverStoreObject is a separate native capability. Existing v1 StoreObject
// methods and its signed wire tree stay unchanged. Reads never install roots,
// import a legacy property, append metadata, or delete any original property.
type CutoverStoreObject interface {
	smartblock.SmartBlock
	ReadTorahCutover(context.Context, StoreObject, string, string) (torahops.CutoverNativeSnapshot, error)
	AppendTorahCutover(context.Context, StoreObject, cutover.Record) (torahops.CutoverNativeAppendResult, error)
	ImportTorahCutoverFact(context.Context, StoreObject, string, string, torahops.Operation) (torahops.NativeAppendResult, error)
	AppendTorahCutoverAssociation(context.Context, StoreObject, string, torahops.Operation) (torahops.NativeAppendResult, error)
}

type cutoverObject struct {
	smartblock.SmartBlock
	space        smartblock.Space
	projectionDB anystore.DB
	key          crypto.PrivKey
	host         *torahops.CutoverNativeHost
}

type cutoverPairKey struct{}
type cutoverPair struct {
	metadata *cutoverObject
	original *object
}

func NewCutover(sb smartblock.SmartBlock, space smartblock.Space, db anystore.DB, key crypto.PrivKey) CutoverStoreObject {
	return &cutoverObject{SmartBlock: sb, space: space, projectionDB: db, key: key}
}

func (o *cutoverObject) Init(ctx *smartblock.InitContext) error {
	if ctx == nil || ctx.Ctx == nil || ctx.Source == nil || o.space == nil || o.projectionDB == nil || o.key == nil {
		return torahcutoverroot.ErrPrivateRoot
	}
	provider, ok := ctx.Source.(source.ObjectTreeProvider)
	if !ok {
		return torahcutoverroot.ErrPrivateRoot
	}
	tree, ok := provider.Tree().(synctree.SyncTree)
	if !ok {
		return torahcutoverroot.ErrPrivateRoot
	}
	init, ok := o.SmartBlock.(interface {
		InitTorahCutover(*smartblock.InitContext) error
	})
	if !ok {
		return torahopscontract.ErrPrivateOperation
	}
	if err := init.InitTorahCutover(ctx); err != nil {
		return err
	}
	host, err := torahops.OpenCutoverNativeHostLocked(ctx.Ctx, o.projectionDB, o.space.Id(), tree, o.key, o.leaseSource)
	if err != nil {
		return err
	}
	if err = bindNativeIndexHook(ctx.Ctx, o.SmartBlock, host); err != nil {
		return err
	}
	o.host = host
	return nil
}

// No caller can provide a synthetic host implementation or independently
// loaded authority snapshot. Both objects must be the current registered cache
// instances in the same native Space/account and retain one actual ACL object.
func (pair cutoverPair) validate(ctx context.Context) error {
	if ctx == nil {
		return cutover.ErrInvalid
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	o, original := pair.metadata, pair.original
	if o == nil || original == nil || o.host == nil || original.host == nil || o.space == nil ||
		o.space != original.space || o.key == nil || original.key == nil ||
		!o.key.GetPublic().Equals(original.key.GetPublic()) || o.Tree() == nil || original.Tree() == nil ||
		o.Tree().AclList() != original.Tree().AclList() || o.Id() == original.Id() ||
		o.Type() != coresb.SmartBlockTypePinkhaTorahCutover || original.Type() != coresb.SmartBlockTypePinkhaTorahOperations {
		return torahcutoverroot.ErrPrivateRoot
	}
	loader, ok := o.space.(nativeTargetSpace)
	if !ok || !loader.PinkhaTorahTargetIsCurrent(o) || !loader.PinkhaTorahTargetIsCurrent(original) {
		return ErrTargetUnavailable
	}
	return nil
}

func (o *cutoverObject) bindOriginal(ctx context.Context, host StoreObject) (context.Context, *torahops.NativeHost, error) {
	if ctx == nil || ctx.Value(cutoverPairKey{}) != nil {
		return nil, nil, cutover.ErrInvalid
	}
	original, ok := host.(*object)
	if !ok {
		return nil, nil, torahcutoverroot.ErrPrivateRoot
	}
	pair := cutoverPair{metadata: o, original: original}
	if err := pair.validate(ctx); err != nil {
		return nil, nil, err
	}
	return context.WithValue(ctx, cutoverPairKey{}, pair), original.host, nil
}

func (o *cutoverObject) leaseSource(ctx context.Context, objectID, propertyKey string, write bool) (*torahops.CutoverSourceLease, error) {
	pair, ok := ctx.Value(cutoverPairKey{}).(cutoverPair)
	if !ok || pair.metadata != o {
		return nil, cutover.ErrInvalid
	}
	if err := pair.validate(ctx); err != nil {
		return nil, err
	}
	lease, err := BorrowNativeCutoverSourceLease(ctx, o.space, o.Tree(), objectID, propertyKey, write)
	if err != nil {
		return nil, err
	}
	sourceValidate, targetValidate := lease.Validate, lease.ValidateTarget
	lease.Validate = func(check context.Context) error {
		if err := sourceValidate(check); err != nil {
			return err
		}
		return pair.validate(check)
	}
	lease.ValidateTarget = func(check context.Context, target torahops.Target) error {
		if err := targetValidate(check, target); err != nil {
			return err
		}
		return pair.validate(check)
	}
	return lease, nil
}

func (o *cutoverObject) ReadTorahCutover(ctx context.Context, v1 StoreObject, objectID, key string) (torahops.CutoverNativeSnapshot, error) {
	bound, original, err := o.bindOriginal(ctx, v1)
	if err != nil {
		return torahops.CutoverNativeSnapshot{}, err
	}
	return o.host.Read(bound, original, objectID, key)
}
func (o *cutoverObject) AppendTorahCutover(ctx context.Context, v1 StoreObject, record cutover.Record) (torahops.CutoverNativeAppendResult, error) {
	bound, original, err := o.bindOriginal(ctx, v1)
	if err != nil {
		return torahops.CutoverNativeAppendResult{}, err
	}
	return o.host.Append(bound, original, record)
}
func (o *cutoverObject) ImportTorahCutoverFact(ctx context.Context, v1 StoreObject, planID, factID string, op torahops.Operation) (torahops.NativeAppendResult, error) {
	bound, original, err := o.bindOriginal(ctx, v1)
	if err != nil {
		return torahops.NativeAppendResult{}, err
	}
	return o.host.AppendImport(bound, original, planID, factID, op)
}
func (o *cutoverObject) AppendTorahCutoverAssociation(ctx context.Context, v1 StoreObject, planID string, op torahops.Operation) (torahops.NativeAppendResult, error) {
	bound, original, err := o.bindOriginal(ctx, v1)
	if err != nil {
		return torahops.NativeAppendResult{}, err
	}
	return o.host.AppendAssociation(bound, original, planID, op)
}

func (*cutoverObject) Show() (*model.ObjectView, error) {
	return nil, torahopscontract.ErrPrivateOperation
}
func (*cutoverObject) Apply(*state.State, ...smartblock.ApplyFlag) error {
	return torahopscontract.ErrPrivateOperation
}
func (*cutoverObject) ResetToVersion(*state.State) error { return torahopscontract.ErrPrivateOperation }
func (*cutoverObject) StateAppend(func(state.Doc) (*state.State, []*pb.ChangeContent, error)) error {
	return torahopscontract.ErrPrivateOperation
}
func (*cutoverObject) StateRebuild(state.Doc) error { return torahopscontract.ErrPrivateOperation }
func (*cutoverObject) UniqueKey() domain.UniqueKey {
	return domain.MustUniqueKey(coresb.SmartBlockTypePinkhaTorahCutover, torahcutoverroot.UniqueKeyVersion)
}
