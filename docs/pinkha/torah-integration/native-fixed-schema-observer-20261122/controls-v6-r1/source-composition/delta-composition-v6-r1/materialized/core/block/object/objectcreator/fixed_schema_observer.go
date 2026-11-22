package objectcreator

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"math"
	"reflect"
	"slices"
	"strings"

	"github.com/anyproto/any-sync/commonspace/headsync/statestorage"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/util/crypto"

	"github.com/anyproto/anytype-heart/core/block/object/payloadcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage"
)

// FixedSchemaDisposition describes a bounded persisted observation, never permission
// to create, initialize, repair, replace, bind an annotation, or acknowledge a body.
type FixedSchemaDisposition uint8

const (
	FixedSchemaUnobserved FixedSchemaDisposition = iota
	FixedSchemaPersistedMatch
	FixedSchemaRootOnlyIncomplete
	FixedSchemaPopulatedConflict
	FixedSchemaLocallyMissing
	FixedSchemaChangedWhileReading
	FixedSchemaUnsupportedDerivationContext
	FixedSchemaUnavailable
)

var (
	ErrFixedSchemaInvalidDefinition  = errors.New("invalid fixed schema definition")
	ErrFixedSchemaUnsupportedContext = errors.New("unsupported fixed schema derivation context")
	ErrFixedSchemaStorage            = errors.New("incomplete or inconsistent fixed schema storage")
	ErrFixedSchemaChanged            = errors.New("fixed schema context or persisted input changed while reading")
	ErrFixedSchemaReadOnly           = errors.New("fixed schema observation does not own a writable or closeable tree")
)

// FixedSchemaDefinition is a requested structural comparison, not account or Space
// authority. Local/derived properties are inadmissible: native headers establish
// unique keys and the original Archive tree establishes archive membership.
type FixedSchemaDefinition struct {
	Key      domain.UniqueKey
	Required *domain.Details
}

type FixedSchemaObservation struct {
	Disposition     FixedSchemaDisposition
	SpaceID         string
	ObjectID        string
	NativeKey       domain.UniqueKey
	PersistedHeads  []string
	ArchiveID       string
	ArchiveHeads    []string
	ACLID           string
	ACLHead         string
	AccountIdentity string
}

// FixedSchemaObserver is additive. Existing Service, generated messages, and all
// creation/initialization paths are unchanged. The caller supplies an already
// retained original native Space; this method never loads a Space or SmartBlock.
type FixedSchemaObserver interface {
	ObserveFixedSchema(context.Context, clientspace.Space, FixedSchemaDefinition) (FixedSchemaObservation, error)
}

var _ FixedSchemaObserver = (*service)(nil)

func (s *service) ObserveFixedSchema(ctx context.Context, spc clientspace.Space, requested FixedSchemaDefinition) (result FixedSchemaObservation, err error) {
	result.Disposition = FixedSchemaUnavailable
	defer func() {
		if errors.Is(err, ErrFixedSchemaChanged) {
			result.Disposition = FixedSchemaChangedWhileReading
		}
	}()
	definition, err := freezeFixedSchemaDefinition(requested)
	if err != nil {
		return result, err
	}
	scope, err := captureFixedSchemaScope(spc)
	if err != nil {
		if errors.Is(err, ErrFixedSchemaUnsupportedContext) {
			result.Disposition = FixedSchemaUnsupportedDerivationContext
		}
		return result, err
	}
	result.SpaceID = scope.spaceID
	result.NativeKey = definition.Key
	result.ACLID, result.ACLHead = scope.aclID, scope.aclHead
	result.AccountIdentity = scope.identity.Account()
	if err = ctx.Err(); err != nil {
		return result, err
	}

	expected, err := spc.DeriveTreePayload(ctx, payloadcreator.PayloadDerivationParams{Key: definition.Key})
	if err != nil {
		return result, fmt.Errorf("derive original fixed root: %w", err)
	}
	archiveKey, err := domain.NewUniqueKey(coresb.SmartBlockTypeArchive, "")
	if err != nil {
		return result, err
	}
	archive, err := spc.DeriveTreePayload(ctx, payloadcreator.PayloadDerivationParams{Key: archiveKey})
	if err != nil {
		return result, fmt.Errorf("derive original archive root: %w", err)
	}
	if expected.RootRawChange == nil || archive.RootRawChange == nil ||
		expected.RootRawChange.Id == "" || archive.RootRawChange.Id == "" ||
		archive.RootRawChange.Id != spc.DerivedIDs().Archive {
		return result, fmt.Errorf("%w: original derived target is unavailable", ErrFixedSchemaStorage)
	}
	result.ObjectID, result.ArchiveID = expected.RootRawChange.Id, archive.RootRawChange.Id

	first, disposition, err := observeFixedSchemaSnapshot(ctx, scope, definition, expected.RootRawChange, archive.RootRawChange)
	result.PersistedHeads = slices.Clone(first.schema.head.Heads)
	result.ArchiveHeads = slices.Clone(first.archive.head.Heads)
	if err != nil {
		return result, fmt.Errorf("observe original persisted schema: %w", err)
	}
	// A second independently owned read transaction can see commits after the
	// first snapshot. Compare complete native encoded rows, not just heads:
	// an extra non-head row must not disappear from this check.
	last, err := rereadFixedSchemaSnapshot(ctx, scope, result.ObjectID, result.ArchiveID)
	if err != nil {
		return result, fmt.Errorf("recheck original persisted inputs: %w", err)
	}
	current, err := captureFixedSchemaScope(spc)
	if err != nil {
		return result, fmt.Errorf("recheck original native scope: %w", err)
	}
	if !scope.same(current) || !first.same(last) {
		result.Disposition = FixedSchemaChangedWhileReading
		return result, ErrFixedSchemaChanged
	}
	if err = ctx.Err(); err != nil {
		return result, err
	}
	result.Disposition = disposition
	return result, nil
}

func freezeFixedSchemaDefinition(request FixedSchemaDefinition) (FixedSchemaDefinition, error) {
	if request.Key == nil || request.Required == nil || request.Required.Len() == 0 {
		return FixedSchemaDefinition{}, ErrFixedSchemaInvalidDefinition
	}
	key, err := domain.UnmarshalUniqueKey(request.Key.Marshal())
	if err != nil || key == nil || key.SmartblockType() != request.Key.SmartblockType() || key.InternalKey() != request.Key.InternalKey() {
		return FixedSchemaDefinition{}, fmt.Errorf("%w: native key", ErrFixedSchemaInvalidDefinition)
	}
	required := domain.NewDetails()
	for field, value := range request.Required.Iterate() {
		if field == "" || slices.Contains(bundle.LocalAndDerivedRelationKeys, field) {
			return FixedSchemaDefinition{}, fmt.Errorf("%w: local or derived field %q", ErrFixedSchemaInvalidDefinition, field)
		}
		// Preserve native value types; copy list storage before any suspension.
		switch {
		case value.IsString():
			required.Set(field, domain.String(value.String()))
		case value.IsBool():
			required.Set(field, domain.Bool(value.Bool()))
		case value.IsFloat64():
			number, ok := value.TryFloat64()
			if !ok || math.IsNaN(number) || math.IsInf(number, 0) {
				return FixedSchemaDefinition{}, ErrFixedSchemaInvalidDefinition
			}
			required.Set(field, domain.Float64(number))
		case value.IsStringList():
			values, ok := value.TryStringList()
			if !ok {
				return FixedSchemaDefinition{}, ErrFixedSchemaInvalidDefinition
			}
			required.Set(field, domain.StringList(values))
		default:
			return FixedSchemaDefinition{}, fmt.Errorf("%w: unsupported structural value %q", ErrFixedSchemaInvalidDefinition, field)
		}
	}
	name, hasName := required.TryString(bundle.RelationKeyName)
	if !hasName || name == "" {
		return FixedSchemaDefinition{}, fmt.Errorf("%w: missing name", ErrFixedSchemaInvalidDefinition)
	}
	switch key.SmartblockType() {
	case coresb.SmartBlockTypeRelation:
		if !required.Has(bundle.RelationKeyLayout) || !required.Has(bundle.RelationKeyRelationFormat) ||
			!required.Get(bundle.RelationKeyLayout).Equal(domain.Int64(model.ObjectType_relation)) ||
			!required.Get(bundle.RelationKeyRelationFormat).Equal(domain.Int64(model.RelationFormat_longtext)) {
			return FixedSchemaDefinition{}, fmt.Errorf("%w: explicit relation layout and longtext required", ErrFixedSchemaInvalidDefinition)
		}
	case coresb.SmartBlockTypeObjectType:
		if !required.Has(bundle.RelationKeyLayout) || !required.Has(bundle.RelationKeyRecommendedLayout) ||
			!required.Get(bundle.RelationKeyLayout).Equal(domain.Int64(model.ObjectType_objectType)) ||
			!required.Get(bundle.RelationKeyRecommendedLayout).Equal(domain.Int64(model.ObjectType_basic)) {
			return FixedSchemaDefinition{}, fmt.Errorf("%w: explicit object type and basic layout required", ErrFixedSchemaInvalidDefinition)
		}
	default:
		return FixedSchemaDefinition{}, fmt.Errorf("%w: unsupported native kind", ErrFixedSchemaInvalidDefinition)
	}
	return FixedSchemaDefinition{Key: key, Required: required}, nil
}

type fixedSchemaACLRecordIdentity struct {
	id         string
	previousID string
}

type fixedSchemaScope struct {
	spaceID      string
	storage      anystorage.ClientSpaceStorage
	stateStorage statestorage.StateStorage
	settingsID   string
	acl          list.AclList
	identity     crypto.PubKey
	aclID        string
	aclHead      string
	aclRoot      []byte
	aclRecords   []fixedSchemaACLRecordIdentity
}

func captureFixedSchemaScope(spc clientspace.Space) (fixedSchemaScope, error) {
	var scope fixedSchemaScope
	if spc == nil || spc.CommonSpace() == nil || spc.TreeBuilder() == nil || spc.IsPersonal() {
		return scope, ErrFixedSchemaUnsupportedContext
	}
	scope.spaceID, scope.storage, scope.acl = spc.Id(), spc.Storage(), spc.CommonSpace().Acl()
	scope.identity = spc.GetAclIdentity()
	if scope.spaceID == "" || scope.storage == nil || scope.storage.Id() != scope.spaceID ||
		scope.storage.AnyStore() == nil || scope.storage.HeadStorage() == nil || scope.storage.StateStorage() == nil ||
		scope.acl == nil || scope.identity == nil {
		return scope, fmt.Errorf("%w: native Space storage or identity", ErrFixedSchemaStorage)
	}
	// These are retained native getters only: no DB read or initialization.
	scope.stateStorage = scope.storage.StateStorage()
	scope.settingsID = strings.Clone(scope.stateStorage.SettingsId())
	if scope.settingsID == "" {
		return scope, fmt.Errorf("%w: native settings identity", ErrFixedSchemaStorage)
	}
	scope.acl.RLock()
	defer scope.acl.RUnlock()
	return scope.captureACLStateLocked()
}

// Caller owns the actual original ACL lock. This makes no database call.
func (scope fixedSchemaScope) captureACLStateLocked() (fixedSchemaScope, error) {
	state, head, root := scope.acl.AclState(), scope.acl.Head(), scope.acl.Root()
	if state == nil || state.Identity() == nil || !state.Identity().Equals(scope.identity) ||
		head == nil || head.Id == "" || root == nil || root.Id != scope.acl.Id() || len(root.Payload) == 0 {
		return scope, fmt.Errorf("%w: actual ACL identity or root", ErrFixedSchemaStorage)
	}
	// This is read admission only. No native CanWrite or UI permission is minted.
	switch state.Permissions(scope.identity) {
	case list.AclPermissionsReader, list.AclPermissionsGuest, list.AclPermissionsWriter, list.AclPermissionsAdmin, list.AclPermissionsOwner:
	default:
		return scope, list.ErrInsufficientPermissions
	}
	if !state.HadReadPermissions(scope.identity) {
		return scope, list.ErrNoReadKey
	}
	scope.aclID, scope.aclHead = strings.Clone(scope.acl.Id()), strings.Clone(head.Id)
	scope.aclRoot = slices.Clone(root.Payload)
	records := scope.acl.Records() // The original list includes the root at index 0.
	scope.aclRecords = make([]fixedSchemaACLRecordIdentity, 0, len(records))
	seen := make(map[string]struct{}, len(records))
	previousID := ""
	for _, record := range records {
		if record == nil || record.Id == "" || record.PrevId != previousID {
			return scope, fmt.Errorf("%w: actual ACL chain", ErrFixedSchemaStorage)
		}
		if _, duplicate := seen[record.Id]; duplicate {
			return scope, fmt.Errorf("%w: duplicate actual ACL record", ErrFixedSchemaStorage)
		}
		seen[record.Id] = struct{}{}
		scope.aclRecords = append(scope.aclRecords, fixedSchemaACLRecordIdentity{id: strings.Clone(record.Id), previousID: strings.Clone(record.PrevId)})
		previousID = record.Id
	}
	if len(scope.aclRecords) == 0 || scope.aclRecords[0].id != scope.aclID || previousID != scope.aclHead {
		return scope, fmt.Errorf("%w: actual ACL endpoints", ErrFixedSchemaStorage)
	}
	return scope, nil
}

func (s fixedSchemaScope) same(other fixedSchemaScope) bool {
	return s.spaceID == other.spaceID && s.storage == other.storage && s.acl == other.acl &&
		s.stateStorage == other.stateStorage && s.settingsID == other.settingsID &&
		s.identity.Equals(other.identity) && s.aclID == other.aclID && s.aclHead == other.aclHead &&
		bytes.Equal(s.aclRoot, other.aclRoot) && slices.Equal(s.aclRecords, other.aclRecords)
}

type fixedSchemaRead struct {
	space   fixedSchemaStoredSpace
	schema  fixedSchemaStoredTree
	archive fixedSchemaStoredTree
	acl     fixedSchemaStoredACL
}

func (r fixedSchemaRead) same(other fixedSchemaRead) bool {
	return r.space.same(other.space) && r.schema.same(other.schema) && r.archive.same(other.archive) && r.acl.same(other.acl)
}

// These comparisons intentionally describe historical local observations. They
// are not a lock held across a later RPC, an account lifetime, or a global absence
// fence. Any later mutation needs fresh original capability and source admission.
func equalFixedSchemaHeads(a, b []string) bool {
	a, b = slices.Clone(a), slices.Clone(b)
	slices.Sort(a)
	slices.Sort(b)
	return len(a) != 0 && slices.Equal(a, b) && len(slices.Compact(a)) == len(a)
}

func fixedSchemaDetailsMatch(got, required *domain.Details) bool {
	for key, wanted := range required.Iterate() {
		if !got.Has(key) || !got.Get(key).Equal(wanted) {
			return false
		}
	}
	return true
}

// Keep the observation comparison independent of original decoder defaults by
// also retaining native anyenc bytes for every persisted record and head entry.
func equalFixedSchemaRows(a, b map[string][]byte) bool {
	return reflect.DeepEqual(a, b)
}

func fixedSchemaObjectTypeMatches(kind coresb.SmartBlockType, keys []domain.TypeKey) bool {
	if len(keys) != 1 {
		return false
	}
	switch kind {
	case coresb.SmartBlockTypeRelation:
		return keys[0] == bundle.TypeKeyRelation
	case coresb.SmartBlockTypeObjectType:
		return keys[0] == bundle.TypeKeyObjectType
	default:
		return false
	}
}
