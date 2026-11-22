package objectcreator

import (
	"context"
	"errors"
	"fmt"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/spacedomain"
)

var ErrFixedSchemaCreationRefused = errors.New("fixed schema creation is not admitted")

// FixedSchemaCreation preserves the actual call phase and both observations.
// Invoked remains true on an error after the original create was entered.
// Neither a successful call nor a historical readback is a write/body receipt.
type FixedSchemaCreation struct {
	Before           FixedSchemaObservation
	After            FixedSchemaObservation
	Invoked          bool
	ReturnedObjectID string
}

type FixedSchemaCreator interface {
	CreateFixedSchemaOnce(context.Context, clientspace.Space, string, FixedSchemaDefinition) (FixedSchemaCreation, error)
}

var _ FixedSchemaCreator = (*service)(nil)

// CreateFixedSchemaOnce is the retained-Space counterpart of the existing
// creator. Its caller must retain the actual application lifetime. It never
// accepts an observation as authority: definition, native storage, exact Space
// identity and current ACL write permission are checked inside this operation.
//
// Only an actually missing original fixed root reaches the original create.
// One call is made. PutTree's native insert owns collision admission; a competing
// root causes the original error before InitObject. Existing incomplete roots
// are never opened, initialized, removed, or rewritten by this method.
func (s *service) CreateFixedSchemaOnce(ctx context.Context, spc clientspace.Space, accountIdentity string, requested FixedSchemaDefinition) (result FixedSchemaCreation, err error) {
	if ctx == nil || accountIdentity == "" || spc == nil || spc.SpaceType() != spacedomain.SpaceTypeRegular {
		return result, ErrFixedSchemaCreationRefused
	}
	definition, err := freezeFixedSchemaDefinition(requested)
	if err != nil {
		return result, err
	}
	scope, err := captureFixedSchemaScope(spc)
	if err != nil {
		return result, err
	}
	if scope.identity.Account() != accountIdentity {
		return result, ErrFixedSchemaCreationRefused
	}
	if err = scope.requireCurrentWritePermission(); err != nil {
		return result, err
	}
	result.Before, err = s.ObserveFixedSchema(ctx, spc, definition)
	if err != nil {
		return result, err
	}
	if result.Before.AccountIdentity != accountIdentity || result.Before.SpaceID != spc.Id() ||
		result.Before.ACLID != scope.aclID || result.Before.ACLHead != scope.aclHead {
		return result, ErrFixedSchemaChanged
	}
	switch result.Before.Disposition {
	case FixedSchemaPersistedMatch:
		result.After = result.Before
		return result, fixedSchemaRejectRetired(result.Before)
	case FixedSchemaLocallyMissing:
	default:
		return result, ErrFixedSchemaCreationRefused
	}

	// The native root, not zero index rows, determines the creation path. Any
	// contradictory local row preserves uncertainty/conflict before a mutation.
	key, value := bundle.RelationKeyUniqueKey, definition.Key.Marshal()
	if definition.Key.SmartblockType() == coresb.SmartBlockTypeRelation {
		key, value = bundle.RelationKeyRelationKey, definition.Key.InternalKey()
	}
	rows, err := s.objectStore.SpaceIndex(spc.Id()).QueryRaw(&database.Filters{FilterObj: database.FilterEq{
		Key: key, Cond: model.BlockContentDataviewFilter_Equal, Value: domain.String(value),
	}}, 2, 0)
	if err != nil {
		return result, err
	}
	if len(rows) != 0 {
		return result, fmt.Errorf("%w: indexed candidate without complete native root", ErrFixedSchemaCreationRefused)
	}
	details := definition.Required.Copy()
	typeKey := bundle.TypeKeyRelation
	if definition.Key.SmartblockType() == coresb.SmartBlockTypeObjectType {
		typeKey = bundle.TypeKeyObjectType
		details.SetString(bundle.RelationKeyUniqueKey, definition.Key.Marshal())
	} else {
		details.SetString(bundle.RelationKeyRelationKey, definition.Key.InternalKey())
	}
	if err = ctx.Err(); err != nil {
		return result, err
	}
	current, err := captureFixedSchemaScope(spc)
	if err != nil {
		return result, err
	}
	if !scope.same(current) {
		return result, ErrFixedSchemaChanged
	}
	if err = current.requireCurrentWritePermission(); err != nil {
		return result, err
	}
	// Do not retain the ACL RLock through this call: original derivation and
	// AddContent acquire that lock themselves. AddContent performs its actual
	// current CanWrite check before signing/storing initialized content.
	result.Invoked = true
	id, _, createErr := s.createObjectInSpace(ctx, spc, CreateObjectRequest{
		Details: details, ObjectTypeKey: typeKey,
	})
	result.ReturnedObjectID = id
	if createErr == nil && id != result.Before.ObjectID {
		createErr = fmt.Errorf("%w: original creator returned another fixed identity", ErrFixedSchemaCreationRefused)
	}
	result.After, err = s.ObserveFixedSchema(ctx, spc, definition)
	if createErr != nil || err != nil {
		return result, errors.Join(createErr, err)
	}
	current, err = captureFixedSchemaScope(spc)
	if err != nil || !scope.same(current) {
		return result, errors.Join(err, ErrFixedSchemaChanged)
	}
	if err = current.requireCurrentWritePermission(); err != nil {
		return result, err
	}
	if result.After.Disposition != FixedSchemaPersistedMatch || result.After.ObjectID != result.Before.ObjectID {
		return result, fmt.Errorf("%w: original create lacks complete matching native readback", ErrFixedSchemaCreationRefused)
	}
	return result, errors.Join(fixedSchemaRejectRetired(result.After), ctx.Err())
}

func (scope fixedSchemaScope) requireCurrentWritePermission() error {
	scope.acl.RLock()
	defer scope.acl.RUnlock()
	current, err := scope.captureACLStateLocked()
	if err != nil {
		return err
	}
	if !scope.same(current) {
		return ErrFixedSchemaChanged
	}
	if !scope.acl.AclState().Permissions(scope.identity).CanWrite() {
		return list.ErrInsufficientPermissions
	}
	return nil
}

func fixedSchemaRejectRetired(observation FixedSchemaObservation) error {
	copy, _ := observation.CopyPersistedSchemaState()
	if copy == nil {
		return ErrFixedSchemaCreationRefused
	}
	details := domain.NewDetailsFromProto(copy)
	for _, key := range []domain.RelationKey{bundle.RelationKeyIsUninstalled, bundle.RelationKeyIsDeleted, bundle.RelationKeyIsArchived} {
		if details.Has(key) && (!details.Get(key).IsBool() || details.GetBool(key)) {
			return fmt.Errorf("%w: retired or malformed native definition", ErrFixedSchemaCreationRefused)
		}
	}
	return nil
}
