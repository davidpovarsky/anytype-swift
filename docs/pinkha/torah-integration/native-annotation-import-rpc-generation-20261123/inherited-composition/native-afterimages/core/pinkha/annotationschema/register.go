package annotationschema

import (
	"context"
	"errors"
	"fmt"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/gogo/protobuf/types"

	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/spacedomain"
)

var ErrRegistrationUnresolved = errors.New("native annotation schema registration remains unresolved")
var ErrRegistrationConflict = errors.New("native annotation schema registration conflicts with persisted state")

// Registration retains what actually ran, even when final cancellation or
// readback fails. Observation is historical data with the same authority limits
// as Observe. AppAdmitted is callback entry, not a native mutation receipt.
type Registration struct {
	Observation       Observation
	AppAdmitted       bool
	Creations         []objectcreator.FixedSchemaCreation
	TypeApplyInvoked  bool
	TypeApplyReturned bool
}

// Register uses the actual active application and existing regular Space. The
// expected account/Space are comparisons, not a caller-created permission.
// A future mobile caller must additionally retain its actual selected-Space
// SourceBinding through original Invocation admission and drain.
//
// There is no accepted Observation argument, native create retry, index-absence
// proof, root-only completion, replacement key, annotation creation, or ACK.
// Each definition and the final type Apply has its own native commit boundary;
// an error preserves all work already admitted. No batch rollback is claimed.
func Register(ctx context.Context, runtime *application.Service, expectedAccount, spaceID string) (result Registration, err error) {
	result.Observation.Disposition = Unavailable
	if ctx == nil || runtime == nil || expectedAccount == "" || spaceID == "" {
		return result, ErrUnqualifiedRuntime
	}
	nativeApp := runtime.GetApp()
	result.AppAdmitted, err = runtime.WithActiveApp(ctx, nativeApp, func(retained *app.App) error {
		session, err := newRegistrationSession(ctx, retained, expectedAccount, spaceID)
		if err != nil {
			return err
		}
		result.Observation, err = session.readback()
		if err != nil {
			return err
		}
		if err = registrationPreflight(result.Observation); err != nil {
			return err
		}
		// Install properties before the type. Every create still performs its
		// own fresh native missing-root and current write-permission checks.
		for step := 0; step < len(session.definitions); step++ {
			i := (step + 1) % len(session.definitions)
			if result.Observation.Definitions[i].Native.Disposition != objectcreator.FixedSchemaLocallyMissing {
				continue
			}
			if err = session.current(); err != nil {
				return err
			}
			definition := session.definitions[i]
			if i == 0 {
				definition.Required = definition.Required.Copy()
				definition.Required.SetBool(bundle.RelationKeyIsHidden, true)
				definition.Required.SetBool(bundle.RelationKeyIsHiddenDiscovery, true)
			}
			creation, createErr := session.creator.CreateFixedSchemaOnce(ctx, session.spc, expectedAccount, definition)
			result.Creations = append(result.Creations, creation)
			if createErr != nil {
				return createErr
			}
		}
		result.Observation, err = session.readback()
		if err != nil {
			return err
		}
		if !registrationDefinitionsReady(result.Observation) {
			return ErrRegistrationUnresolved
		}
		if result.Observation.Disposition == MatchingObserved {
			return session.current()
		}
		if err = session.attachHiddenProperties(&result); err != nil {
			return err
		}
		result.Observation, err = session.readback()
		if err != nil {
			return err
		}
		if result.Observation.Disposition != MatchingObserved {
			return ErrRegistrationUnresolved
		}
		return session.current()
	})
	if err != nil && result.Observation.Disposition == MatchingObserved {
		// A final failed admission/currentness check must not publish current
		// success. Previously copied details and actual call phases are kept.
		result.Observation.Disposition = Unavailable
	}
	return result, err
}

type registrationSession struct {
	ctx         context.Context
	account     accountservice.Service
	identity    crypto.PubKey
	spaces      space.Service
	spc         clientspace.Space
	store       objectstore.ObjectStore
	observer    objectcreator.FixedSchemaObserver
	creator     objectcreator.FixedSchemaCreator
	definitions []objectcreator.FixedSchemaDefinition
}

func newRegistrationSession(ctx context.Context, nativeApp *app.App, expectedAccount, spaceID string) (*registrationSession, error) {
	account, err := app.GetComponent[accountservice.Service](nativeApp)
	if err != nil {
		return nil, err
	}
	keys := account.Account()
	if keys == nil || keys.SignKey == nil || keys.SignKey.GetPublic() == nil || keys.SignKey.GetPublic().Account() != expectedAccount {
		return nil, ErrRuntimeChanged
	}
	spaces, err := app.GetComponent[space.Service](nativeApp)
	if err != nil {
		return nil, err
	}
	spc, err := spaces.Get(ctx, spaceID)
	if err != nil {
		return nil, err
	}
	creator, err := app.GetComponent[objectcreator.Service](nativeApp)
	if err != nil {
		return nil, err
	}
	observer, hasObserver := creator.(objectcreator.FixedSchemaObserver)
	writer, hasWriter := creator.(objectcreator.FixedSchemaCreator)
	if !hasObserver || !hasWriter {
		return nil, ErrUnqualifiedRuntime
	}
	store, err := app.GetComponent[objectstore.ObjectStore](nativeApp)
	if err != nil {
		return nil, err
	}
	definitions, err := Definitions()
	if err != nil {
		return nil, err
	}
	s := &registrationSession{ctx: ctx, account: account, identity: keys.SignKey.GetPublic(), spaces: spaces,
		spc: spc, store: store, observer: observer, creator: writer, definitions: definitions}
	return s, s.current()
}

func (s *registrationSession) current() error {
	if err := s.ctx.Err(); err != nil {
		return err
	}
	keys := s.account.Account()
	if keys == nil || keys.SignKey == nil || keys.SignKey.GetPublic() == nil ||
		!s.identity.Equals(keys.SignKey.GetPublic()) || s.spc == nil || s.spc.IsPersonal() ||
		s.spc.SpaceType() != spacedomain.SpaceTypeRegular || s.spc.GetAclIdentity() == nil ||
		!s.identity.Equals(s.spc.GetAclIdentity()) || s.spc.CommonSpace() == nil {
		return ErrRuntimeChanged
	}
	currentSpace, err := s.spaces.Get(s.ctx, s.spc.Id())
	if err != nil {
		return err
	}
	if currentSpace != s.spc {
		return ErrRuntimeChanged
	}
	acl := s.spc.CommonSpace().Acl()
	if acl == nil {
		return ErrUnqualifiedRuntime
	}
	acl.RLock()
	defer acl.RUnlock()
	state := acl.AclState()
	if state == nil || state.Identity() == nil || !state.Identity().Equals(s.identity) {
		return ErrRuntimeChanged
	}
	if !state.Permissions(s.identity).CanWrite() {
		return list.ErrInsufficientPermissions
	}
	return nil
}

// Uses retained components only. Calling Observe here would reenter GetApp
// while WithActiveApp owns its RLock, which can deadlock behind a queued writer.
func (s *registrationSession) readback() (result Observation, err error) {
	result.Disposition = MatchingObserved
	result.AccountIdentity, result.SpaceID = s.identity.Account(), s.spc.Id()
	var typeDetails *types.Struct
	var typeBlocks []*model.Block
	relations := make(map[string]string, len(relationNames))
	var first *objectcreator.FixedSchemaObservation
	for i, definition := range s.definitions {
		if err = s.current(); err != nil {
			result.Disposition = Unavailable
			return result, err
		}
		native, nativeErr := s.observer.ObserveFixedSchema(s.ctx, s.spc, definition)
		entry := DefinitionObservation{Native: native, Index: IndexNotObserved}
		result.Definitions = append(result.Definitions, entry)
		position := len(result.Definitions) - 1
		if nativeErr != nil {
			result.Disposition = Unavailable
			if errors.Is(nativeErr, objectcreator.ErrFixedSchemaChanged) {
				result.Disposition = Changed
			}
			return result, nativeErr
		}
		if native.SpaceID != result.SpaceID || native.AccountIdentity != result.AccountIdentity ||
			native.NativeKey == nil || native.NativeKey.Marshal() != definition.Key.Marshal() || native.ObjectID == "" {
			result.Disposition = Unavailable
			return result, ErrRuntimeChanged
		}
		if first == nil {
			copy := native
			first = &copy
		} else if native.ACLID != first.ACLID || native.ACLHead != first.ACLHead || native.ArchiveID != first.ArchiveID ||
			!sameHeads(native.ArchiveHeads, first.ArchiveHeads) {
			result.Disposition = Changed
			return result, objectcreator.ErrFixedSchemaChanged
		}
		index, indexErr := observeIndex(s.store, result.SpaceID, definition, native.ObjectID)
		result.Definitions[position].Index = index
		if indexErr != nil {
			result.Disposition = Unavailable
			return result, indexErr
		}
		if index == IndexConflict {
			result.Disposition = Conflict
		} else if index != IndexMatch && result.Disposition == MatchingObserved {
			result.Disposition = Incomplete
		}
		if i > 0 {
			// This is the original derived address, even for a missing root.
			// Overall readiness still requires every persisted definition.
			relations[definition.Key.InternalKey()] = native.ObjectID
		}
		switch native.Disposition {
		case objectcreator.FixedSchemaPersistedMatch:
			details, blocks := native.CopyPersistedSchemaState()
			if details == nil {
				return result, ErrUnqualifiedRuntime
			}
			for _, key := range []domain.RelationKey{bundle.RelationKeyIsUninstalled, bundle.RelationKeyIsDeleted, bundle.RelationKeyIsArchived} {
				flag, flagErr := strictBoolean(details, key.String())
				if flagErr != nil || flag {
					result.Definitions[position].PersistedStateConflict = true
					result.Disposition = Conflict
				}
			}
			if i == 0 {
				typeDetails, typeBlocks = details, blocks
			}
		case objectcreator.FixedSchemaLocallyMissing, objectcreator.FixedSchemaRootOnlyIncomplete:
			if result.Disposition == MatchingObserved {
				result.Disposition = Incomplete
			}
			if index != IndexUnresolved {
				result.Disposition = Conflict
			}
		case objectcreator.FixedSchemaPopulatedConflict:
			result.Disposition = Conflict
		default:
			result.Disposition = Unavailable
			return result, ErrUnqualifiedRuntime
		}
	}
	if typeDetails != nil {
		result.TypeLayout = observeTypeLayout(typeDetails, typeBlocks, result.Definitions[0].Native.ObjectID, relations)
		if result.TypeLayout.Disposition == Conflict {
			result.Disposition = Conflict
		} else if result.TypeLayout.Disposition != MatchingObserved && result.Disposition == MatchingObserved {
			result.Disposition = Incomplete
		}
	}
	if err = s.current(); err != nil {
		result.Disposition = Unavailable
	}
	return result, err
}

func registrationPreflight(observation Observation) error {
	if observation.Disposition == Conflict {
		return ErrRegistrationConflict
	}
	if len(observation.Definitions) != len(relationNames)+1 {
		return ErrRegistrationUnresolved
	}
	for _, entry := range observation.Definitions {
		if entry.PersistedStateConflict || entry.Index == IndexConflict {
			return ErrRegistrationConflict
		}
		switch entry.Native.Disposition {
		case objectcreator.FixedSchemaPersistedMatch, objectcreator.FixedSchemaLocallyMissing:
		default:
			return ErrRegistrationUnresolved
		}
	}
	if observation.Definitions[0].Native.Disposition == objectcreator.FixedSchemaPersistedMatch &&
		(!observation.TypeLayout.Hidden || !observation.TypeLayout.DiscoveryHidden || len(observation.TypeLayout.ViewIDs) == 0) {
		return fmt.Errorf("%w: existing type visibility or dataview is not repairable by missing-property registration", ErrRegistrationConflict)
	}
	return nil
}

func registrationDefinitionsReady(observation Observation) bool {
	if len(observation.Definitions) != len(relationNames)+1 || observation.Disposition == Conflict ||
		observation.Disposition == Changed || observation.Disposition == Unavailable {
		return false
	}
	for _, entry := range observation.Definitions {
		if entry.Native.Disposition != objectcreator.FixedSchemaPersistedMatch || entry.Index != IndexMatch || entry.PersistedStateConflict {
			return false
		}
	}
	return true
}
