package objectcreator

import (
	"context"
	"errors"
	"fmt"
	"slices"

	"github.com/anyproto/anytype-heart/core/block/object/payloadcreator"
	"github.com/anyproto/anytype-heart/core/converter/pbc"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/gogo/protobuf/proto"
)

// OwnedAnnotationSchemaObservation is historical original persisted data. It
// never yields a mutable SmartBlock, initialization, installation, permission,
// body acknowledgement or capability to reuse a later changed object.
type OwnedAnnotationSchemaObservation struct {
	Disposition                                        FixedSchemaDisposition
	SpaceID, ObjectID, AccountIdentity, ACLID, ACLHead string
	PersistedHeads, ArchiveHeads                       []string
	snapshot                                           *pb.SnapshotWithType
}

func (o OwnedAnnotationSchemaObservation) CopySnapshot() *pb.SnapshotWithType {
	if o.Disposition != FixedSchemaPersistedMatch || o.snapshot == nil {
		return nil
	}
	return proto.Clone(o.snapshot).(*pb.SnapshotWithType)
}

// This additive owner surface deliberately leaves the fixed longtext/basic
// observer untouched. Only keys present in the actual original bundled model
// definitions enter this separate read-only observation.
type OwnedAnnotationSchemaObserver interface {
	ObserveOwnedAnnotationFixedSchema(context.Context, clientspace.Space, FixedSchemaDefinition) (OwnedAnnotationSchemaObservation, error)
	ObserveOwnedAnnotationBundledSchema(context.Context, clientspace.Space, domain.UniqueKey) (OwnedAnnotationSchemaObservation, error)
}

var _ OwnedAnnotationSchemaObserver = (*service)(nil)

func (s *service) ObserveOwnedAnnotationBundledSchema(ctx context.Context, spc clientspace.Space, key domain.UniqueKey) (OwnedAnnotationSchemaObservation, error) {
	definition, err := originalOwnedAnnotationBundledDefinition(key)
	if err != nil {
		return OwnedAnnotationSchemaObservation{}, err
	}
	return s.observeOwnedAnnotationSchema(ctx, spc, definition)
}

// The existing fixed longtext/basic admission is called unchanged. This adds
// only a full owned snapshot copy after the same raw persisted observation.
func (s *service) ObserveOwnedAnnotationFixedSchema(ctx context.Context, spc clientspace.Space, requested FixedSchemaDefinition) (OwnedAnnotationSchemaObservation, error) {
	definition, err := freezeFixedSchemaDefinition(requested)
	if err != nil {
		return OwnedAnnotationSchemaObservation{}, err
	}
	return s.observeOwnedAnnotationSchema(ctx, spc, definition)
}

func (s *service) observeOwnedAnnotationSchema(ctx context.Context, spc clientspace.Space, definition FixedSchemaDefinition) (result OwnedAnnotationSchemaObservation, err error) {
	result.Disposition = FixedSchemaUnavailable
	defer func() {
		if errors.Is(err, ErrFixedSchemaChanged) {
			result.Disposition = FixedSchemaChangedWhileReading
		}
	}()
	if ctx == nil {
		return result, ErrFixedSchemaInvalidDefinition
	}
	scope, err := captureFixedSchemaScope(spc)
	if err != nil {
		return result, err
	}
	result.SpaceID, result.AccountIdentity = scope.spaceID, scope.identity.Account()
	result.ACLID, result.ACLHead = scope.aclID, scope.aclHead
	if err := ctx.Err(); err != nil {
		return result, err
	}
	expected, err := spc.DeriveTreePayload(ctx, payloadcreator.PayloadDerivationParams{Key: definition.Key})
	if err != nil {
		return result, err
	}
	archiveKey, err := domain.NewUniqueKey(coresb.SmartBlockTypeArchive, "")
	if err != nil {
		return result, err
	}
	archive, err := spc.DeriveTreePayload(ctx, payloadcreator.PayloadDerivationParams{Key: archiveKey})
	if err != nil {
		return result, err
	}
	if expected.RootRawChange == nil || expected.RootRawChange.Id == "" || archive.RootRawChange == nil ||
		archive.RootRawChange.Id == "" || archive.RootRawChange.Id != spc.DerivedIDs().Archive {
		return result, ErrFixedSchemaStorage
	}
	result.ObjectID = expected.RootRawChange.Id
	// This original helper performs the actual immutable DB read, checks signed
	// Space/ACL rows and archive membership, and strictly replays the complete
	// native derived tree. It does not invoke the fixed public definition gate.
	first, disposition, err := observeFixedSchemaSnapshot(ctx, scope, definition, expected.RootRawChange, archive.RootRawChange)
	result.PersistedHeads, result.ArchiveHeads = slices.Clone(first.schema.head.Heads), slices.Clone(first.archive.head.Heads)
	if err != nil {
		return result, err
	}
	var snapshot *pb.SnapshotWithType
	if disposition == FixedSchemaPersistedMatch {
		// Reuse the same owned copied rows, not a cache/SmartBlock/open fallback.
		st, count, replayErr := replayFixedSchemaTree(ctx, scope, first.schema, expected.RootRawChange, definition.Key.SmartblockType(), definition.Key.InternalKey())
		if replayErr != nil || count < 2 {
			return result, errors.Join(ErrFixedSchemaStorage, replayErr)
		}
		raw := pbc.NewConverter(st, false).Convert(definition.Key.SmartblockType().ToProto())
		snapshot = &pb.SnapshotWithType{}
		if len(raw) == 0 {
			return result, ErrFixedSchemaStorage
		}
		if err := proto.Unmarshal(raw, snapshot); err != nil {
			return result, err
		}
		if snapshot.Snapshot == nil || snapshot.Snapshot.Data == nil ||
			snapshot.SbType != definition.Key.SmartblockType().ToProto() || snapshot.Snapshot.Data.Key != definition.Key.InternalKey() {
			return result, ErrFixedSchemaStorage
		}
	}
	last, err := rereadFixedSchemaSnapshot(ctx, scope, result.ObjectID, archive.RootRawChange.Id)
	if err != nil {
		return result, err
	}
	current, err := captureFixedSchemaScope(spc)
	if err != nil {
		return result, err
	}
	if !scope.same(current) || !first.same(last) {
		return result, ErrFixedSchemaChanged
	}
	if err := ctx.Err(); err != nil {
		return result, err
	}
	result.Disposition = disposition
	if disposition == FixedSchemaPersistedMatch {
		result.snapshot = snapshot
	}
	return result, nil
}

// Structural expectations are derived from the actual compiled original bundle,
// never a caller-supplied layout/format/readiness boolean. Full source-versus-
// target snapshot compatibility is a separate comparison by the archive owner.
func originalOwnedAnnotationBundledDefinition(request domain.UniqueKey) (FixedSchemaDefinition, error) {
	if request == nil {
		return FixedSchemaDefinition{}, ErrFixedSchemaInvalidDefinition
	}
	key, err := domain.UnmarshalUniqueKey(request.Marshal())
	if err != nil || key == nil || key.SmartblockType() != request.SmartblockType() || key.InternalKey() != request.InternalKey() {
		return FixedSchemaDefinition{}, ErrFixedSchemaInvalidDefinition
	}
	required := domain.NewDetails()
	required.SetString(bundle.RelationKeyUniqueKey, key.Marshal())
	switch key.SmartblockType() {
	case coresb.SmartBlockTypeRelation:
		original, err := bundle.GetRelation(domain.RelationKey(key.InternalKey()))
		if err != nil || original == nil || original.Key != key.InternalKey() || original.Name == "" {
			return FixedSchemaDefinition{}, errors.Join(ErrFixedSchemaInvalidDefinition, err)
		}
		required.SetString(bundle.RelationKeyName, original.Name)
		required.SetString(bundle.RelationKeySourceObject, domain.RelationKey(original.Key).BundledURL())
		required.SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_relation))
		required.SetInt64(bundle.RelationKeyRelationFormat, int64(original.Format))
		required.SetInt64(bundle.RelationKeyRevision, original.Revision)
	case coresb.SmartBlockTypeObjectType:
		original, err := bundle.GetType(domain.TypeKey(key.InternalKey()))
		if err != nil || original == nil || original.Key != key.InternalKey() || original.Name == "" {
			return FixedSchemaDefinition{}, errors.Join(ErrFixedSchemaInvalidDefinition, err)
		}
		required.SetString(bundle.RelationKeyName, original.Name)
		required.SetString(bundle.RelationKeySourceObject, domain.TypeKey(original.Key).BundledURL())
		required.SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_objectType))
		required.SetInt64(bundle.RelationKeyRecommendedLayout, int64(original.Layout))
		required.SetInt64(bundle.RelationKeyRevision, original.Revision)
	default:
		return FixedSchemaDefinition{}, fmt.Errorf("%w: not an original bundled schema", ErrFixedSchemaInvalidDefinition)
	}
	return FixedSchemaDefinition{Key: key, Required: required}, nil
}
