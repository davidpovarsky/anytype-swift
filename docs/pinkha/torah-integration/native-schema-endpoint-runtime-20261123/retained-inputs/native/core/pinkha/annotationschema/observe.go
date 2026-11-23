package annotationschema

import (
	"context"
	"errors"
	"fmt"
	"slices"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/types"

	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
)

type Disposition string

const (
	MatchingObserved Disposition = "MATCHING_SCHEMA_OBSERVED"
	Incomplete       Disposition = "INCOMPLETE_OR_UNRESOLVED"
	Conflict         Disposition = "CONFLICT"
	Changed          Disposition = "CHANGED_WHILE_READING"
	Unavailable      Disposition = "UNAVAILABLE"
)

type IndexDisposition string

const (
	IndexNotObserved IndexDisposition = "NOT_OBSERVED"
	IndexUnresolved  IndexDisposition = "NO_POSITIVE_INDEX_READINESS"
	IndexMatch       IndexDisposition = "ONE_MATCHING_LOCAL_INDEX_ROW"
	IndexConflict    IndexDisposition = "CONFLICTING_LOCAL_INDEX_ROWS"
)

var ErrRuntimeChanged = errors.New("original annotation schema runtime changed")
var ErrUnqualifiedRuntime = errors.New("original annotation schema runtime unavailable")

type DefinitionObservation struct {
	Native                 objectcreator.FixedSchemaObservation
	Index                  IndexDisposition
	PersistedStateConflict bool
}

type Observation struct {
	Disposition     Disposition
	AccountIdentity string
	SpaceID         string
	Definitions     []DefinitionObservation
	TypeLayout      TypeLayoutObservation
}

// Observe reads the actual active original application's services. There is no
// injectable transport, qualification bootstrap, ObjectShow load, write, retry,
// schema repair or fallback key. Space.Get may load the selected existing Space
// through its original lifecycle; schema objects themselves are never opened.
//
// Each definition is a complete original persisted observation. The batch is
// not an atomic schema transaction, cross-client uniqueness proof, or a lease
// spanning a later operation. Even MATCHING_SCHEMA_OBSERVED grants no create,
// native mutation, mapping, body proof, or ACK authority.
func Observe(ctx context.Context, runtime *application.Service, spaceID string) (result Observation, err error) {
	result.Disposition = Unavailable
	result.SpaceID = spaceID
	if ctx == nil || runtime == nil || spaceID == "" {
		return result, ErrUnqualifiedRuntime
	}
	if err = ctx.Err(); err != nil {
		return result, err
	}
	nativeApp := runtime.GetApp()
	if nativeApp == nil {
		return result, ErrUnqualifiedRuntime
	}
	account, err := app.GetComponent[accountservice.Service](nativeApp)
	if err != nil {
		return result, err
	}
	keys := account.Account()
	if keys == nil || keys.SignKey == nil || keys.SignKey.GetPublic() == nil {
		return result, ErrUnqualifiedRuntime
	}
	identity := keys.SignKey.GetPublic()
	result.AccountIdentity = identity.Account()
	creator, err := app.GetComponent[objectcreator.Service](nativeApp)
	if err != nil {
		return result, err
	}
	observer, ok := creator.(objectcreator.FixedSchemaObserver)
	if !ok {
		return result, ErrUnqualifiedRuntime
	}
	spaces, err := app.GetComponent[space.Service](nativeApp)
	if err != nil {
		return result, err
	}
	store, err := app.GetComponent[objectstore.ObjectStore](nativeApp)
	if err != nil {
		return result, err
	}
	spc, err := spaces.Get(ctx, spaceID)
	if err != nil {
		return result, err
	}
	current := func() error {
		if err := ctx.Err(); err != nil {
			return err
		}
		currentKeys := account.Account()
		if runtime.GetApp() != nativeApp || currentKeys == nil || currentKeys.SignKey == nil ||
			currentKeys.SignKey.GetPublic() == nil || !identity.Equals(currentKeys.SignKey.GetPublic()) ||
			spc == nil || spc.Id() != spaceID || spc.GetAclIdentity() == nil ||
			!identity.Equals(spc.GetAclIdentity()) {
			return ErrRuntimeChanged
		}
		return nil
	}
	if err = current(); err != nil {
		return result, err
	}
	definitions, err := Definitions()
	if err != nil {
		return result, err
	}
	result.Disposition = MatchingObserved
	var first *objectcreator.FixedSchemaObservation
	var typeDetails *types.Struct
	var typeBlocks []*model.Block
	relations := make(map[string]string, len(relationNames))
	for i, definition := range definitions {
		if err = current(); err != nil {
			result.Disposition = Unavailable
			return result, err
		}
		native, observeErr := observer.ObserveFixedSchema(ctx, spc, definition)
		entry := DefinitionObservation{Native: native, Index: IndexNotObserved}
		result.Definitions = append(result.Definitions, entry)
		entryIndex := len(result.Definitions) - 1
		if observeErr != nil {
			result.Disposition = Unavailable
			if errors.Is(observeErr, objectcreator.ErrFixedSchemaChanged) {
				result.Disposition = Changed
			}
			return result, observeErr
		}
		if err = current(); err != nil {
			result.Disposition = Unavailable
			return result, err
		}
		if native.SpaceID != spaceID || native.AccountIdentity != result.AccountIdentity ||
			native.NativeKey == nil || native.NativeKey.Marshal() != definition.Key.Marshal() || native.ObjectID == "" {
			result.Disposition = Unavailable
			return result, ErrRuntimeChanged
		}
		if first == nil {
			copy := native
			first = &copy
		} else if native.ACLID != first.ACLID || native.ACLHead != first.ACLHead ||
			native.ArchiveID != first.ArchiveID || !sameHeads(native.ArchiveHeads, first.ArchiveHeads) {
			result.Disposition = Changed
			return result, objectcreator.ErrFixedSchemaChanged
		}
		switch native.Disposition {
		case objectcreator.FixedSchemaPersistedMatch:
			details, blocks := native.CopyPersistedSchemaState()
			if details == nil {
				result.Disposition = Unavailable
				return result, fmt.Errorf("%w: matching schema has no original persisted readback", ErrUnqualifiedRuntime)
			}
			// A derived schema object's durable retirement marker is independent
			// of the local/index deletion flags. Never adopt a retired definition
			// merely because those derived flags have not caught up.
			for _, field := range []domain.RelationKey{bundle.RelationKeyIsUninstalled,
				bundle.RelationKeyIsDeleted, bundle.RelationKeyIsArchived} {
				flag, flagErr := strictBoolean(details, field.String())
				if flagErr != nil || flag {
					result.Definitions[entryIndex].PersistedStateConflict = true
					result.Disposition = Conflict
				}
			}
			if i == 0 {
				typeDetails, typeBlocks = details, blocks
			} else {
				relations[definition.Key.InternalKey()] = native.ObjectID
			}
			index, indexErr := observeIndex(store, spaceID, definition, native.ObjectID)
			result.Definitions[entryIndex].Index = index
			if indexErr != nil {
				result.Disposition = Unavailable
				return result, indexErr
			}
			if index == IndexConflict {
				result.Disposition = Conflict
			} else if index != IndexMatch && result.Disposition == MatchingObserved {
				result.Disposition = Incomplete
			}
		case objectcreator.FixedSchemaLocallyMissing, objectcreator.FixedSchemaRootOnlyIncomplete:
			if result.Disposition == MatchingObserved {
				result.Disposition = Incomplete
			}
		case objectcreator.FixedSchemaPopulatedConflict:
			result.Disposition = Conflict
		default:
			result.Disposition = Unavailable
			return result, ErrUnqualifiedRuntime
		}
	}
	if typeDetails != nil && len(relations) == len(relationNames) {
		result.TypeLayout = observeTypeLayout(typeDetails, typeBlocks, result.Definitions[0].Native.ObjectID, relations)
		if result.TypeLayout.Disposition == Conflict {
			result.Disposition = Conflict
		} else if result.TypeLayout.Disposition != MatchingObserved && result.Disposition == MatchingObserved {
			result.Disposition = Incomplete
		}
	}
	if err = current(); err != nil {
		result.Disposition = Unavailable
		return result, err
	}
	return result, nil
}

func observeIndex(store objectstore.ObjectStore, spaceID string, definition objectcreator.FixedSchemaDefinition, id string) (IndexDisposition, error) {
	key := bundle.RelationKeyUniqueKey
	value := definition.Key.Marshal()
	if definition.Key.Marshal() != TypeUniqueKey {
		key, value = bundle.RelationKeyRelationKey, definition.Key.InternalKey()
	}
	// Two rows are enough to establish ambiguity. No hidden/deleted/format
	// predicate is allowed to discard a conflicting candidate before assessment.
	rows, err := store.SpaceIndex(spaceID).QueryRaw(&database.Filters{FilterObj: database.FilterEq{
		Key: key, Cond: model.BlockContentDataviewFilter_Equal, Value: domain.String(value),
	}}, 2, 0)
	if err != nil {
		return IndexNotObserved, err
	}
	if len(rows) == 0 {
		return IndexUnresolved, nil
	}
	if len(rows) != 1 || rows[0].Details == nil {
		return IndexConflict, nil
	}
	details := rows[0].Details
	for field, expected := range map[domain.RelationKey]string{
		bundle.RelationKeyId: id, bundle.RelationKeySpaceId: spaceID,
		bundle.RelationKeyUniqueKey: definition.Key.Marshal(), key: value,
	} {
		actual, present := details.TryString(field)
		if !present || actual != expected {
			return IndexConflict, nil
		}
	}
	for field, expected := range definition.Required.Iterate() {
		if !details.Has(field) || !details.Get(field).Equal(expected) {
			return IndexConflict, nil
		}
	}
	for _, field := range []domain.RelationKey{bundle.RelationKeyIsUninstalled,
		bundle.RelationKeyIsDeleted, bundle.RelationKeyIsArchived} {
		if details.Has(field) {
			flag, valid := details.Get(field).TryBool()
			if !valid || flag {
				return IndexConflict, nil
			}
		}
	}
	return IndexMatch, nil
}

func sameHeads(a, b []string) bool {
	a, b = slices.Clone(a), slices.Clone(b)
	slices.Sort(a)
	slices.Sort(b)
	return len(a) != 0 && slices.Equal(a, b)
}
