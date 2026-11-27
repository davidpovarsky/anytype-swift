package torahindex

import (
	"context"
	"crypto/rand"
	"encoding/hex"

	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
)

func newReadinessRunID() string {
	var bytes [32]byte
	if _, err := rand.Read(bytes[:]); err != nil {
		return ""
	}
	return hex.EncodeToString(bytes[:])
}

// ReadinessRunID belongs to this initialized index instance, never to a
// persistent row or a process-global current account. Cold startup replaces it.
func (i *Index) ReadinessRunID() string { return i.readinessRunID }

// ReadinessBinding uses the original resolver/descriptor reader in the caller's
// already-open index ReadTx. Candidate IDs come from the bounded complete row
// snapshot, so a missing or stale process-local manifest hint cannot hide a new
// conflicting manifest. The temporary view never writes or calls Recover.
func (i *Index) ReadinessBinding(ctx context.Context, rows map[string]*domain.Details, key string) (torah.Binding, string, error) {
	if len(rows) > contract.MaxObjects || key == "" || i.readinessRunID == "" {
		return torah.Binding{}, "", contract.ErrInvalidWitness
	}
	view := &Index{space: i.space, objects: i.objects}
	for id, row := range rows {
		if isManifest(row) {
			view.manifests.Store(id, struct{}{})
		}
	}
	binding, err := torah.ResolveBinding(ctx, source{index: view}, i.space)
	if err != nil {
		return torah.Binding{}, "", err
	}
	if binding.SpaceID != i.space || binding.CanonicalKey != key {
		return torah.Binding{}, "", torah.ErrBinding
	}
	// The caller must also correlate both descriptor rows with authoritative
	// native roots. An orphan index-only manifest/property is not a binding.
	property, err := (source{index: view}).CanonicalProperty(ctx, i.space, key)
	if err != nil {
		return torah.Binding{}, "", err
	}
	return binding, property.ID, nil
}

type ReadinessDocument struct {
	Classification string
	Proof          string
	Eligible       bool
	Reason         contract.Reason
}

// ReadinessProjection recomputes the existing projector into a copy. It checks
// current canonical input, schema/binding and every derived output, including an
// explicit supported empty payload. No caller-supplied readiness bit is enough.
func (i *Index) ReadinessProjection(binding torah.Binding, native contract.NativeRoot, original *domain.Details) ReadinessDocument {
	result := ReadinessDocument{}
	if original == nil || original.GetString(bundle.RelationKeyId) == "" ||
		(original.GetString(bundle.RelationKeySpaceId) != "" && original.GetString(bundle.RelationKeySpaceId) != i.space) {
		result.Reason = contract.UnknownObject
		return result
	}
	kind := coresb.SmartBlockType(native.NativeType)
	if kind.Valid() != nil || kind == coresb.SmartBlockTypeMissingObject {
		result.Reason = contract.UnknownObject
		return result
	}
	if original.GetBool(bundle.RelationKeyIsDeleted) {
		// Original derived-type/property/option/template deletion keeps its live
		// native tree and indexed corpse. Its matched native heads plus the exact
		// original uninstalled flags distinguish it from a physical tombstone.
		if !native.Head.IsDerived || !original.GetBool(bundle.RelationKeyIsUninstalled) ||
			!kind.IsOneOf(coresb.SmartBlockTypeObjectType, coresb.SmartBlockTypeRelation, coresb.SmartBlockTypeRelationOption, coresb.SmartBlockTypeTemplate) {
			result.Reason = contract.UnknownObject
			return result
		}
		result.Classification = "current-uninstalled-derived-object"
	} else if isManifest(original) {
		result.Classification = "canonical-manifest"
	} else if isUserDocument(original) {
		if original.Has(bundle.RelationKeyTargetObjectType) || original.GetBool(bundle.RelationKeyIsArchived) {
			result.Classification = "current-template-or-archived"
		} else {
			result.Classification, result.Eligible = "eligible-document", true
		}
	} else if knownExcludedDetails(original, kind) {
		result.Classification = "current-native-nondocument"
	} else {
		result.Reason = contract.UnknownObject
		return result
	}
	if result.Eligible {
		types := original.GetStringList(bundle.RelationKeyType)
		if scalar := original.GetString(bundle.RelationKeyType); scalar != "" {
			types = []string{scalar}
		}
		if len(types) != 1 || types[0] == "" {
			result.Reason = contract.UnknownObject
			return result
		}
	}
	projected := clear(original)
	if key := original.GetString(domain.RelationKey(torah.CanonicalKeyKey)); key != "" {
		projected.SetString(domain.RelationKey(torah.CanonicalKeyKey), key)
	}
	i.project(binding, projected)
	keys := make([]domain.RelationKey, 0, len(torah.LocalKeys()))
	for _, key := range torah.LocalKeys() {
		keys = append(keys, domain.RelationKey(key))
	}
	if !original.CopyOnlyKeys(keys...).Equal(projected.CopyOnlyKeys(keys...)) {
		result.Reason = contract.StaleProjection
		return result
	}
	if result.Eligible {
		if !projected.GetBool(domain.RelationKey(torah.ReadyKey)) ||
			projected.GetInt64(domain.RelationKey(torah.VersionKey)) != torah.Version ||
			projected.GetInt64(domain.RelationKey(torah.RelatedVersionKey)) != torah.RelatedVersion ||
			projected.GetString(domain.RelationKey(torah.StatusKey)) != "READY" {
			result.Reason = contract.UnsupportedProjection
			return result
		}
		if !reusableCache(binding, original) {
			result.Reason = contract.MissingProjection
			return result
		}
	}
	result.Proof = cacheProof(binding, projected)
	if result.Proof == "" {
		result.Reason = contract.StaleProjection
	}
	return result
}

func knownExcludedDetails(d *domain.Details, kind coresb.SmartBlockType) bool {
	// These are positive original classifier inputs, read only after the native
	// head match. An absent/unknown mutable type or layout is never an exclusion.
	if d.GetBool(bundle.RelationKeyIsHidden) || d.GetString(bundle.RelationKeyUniqueKey) != "" ||
		d.Has(bundle.RelationKeyRelationKey) || d.Has(bundle.RelationKeyRelationFormat) ||
		d.Has(bundle.RelationKeyRecommendedLayout) || d.Has(bundle.RelationKeyTargetObjectType) {
		return true
	}
	if kind.IsOneOf(coresb.SmartBlockTypeHome, coresb.SmartBlockTypeArchive,
		coresb.SmartBlockTypeWidget, coresb.SmartBlockTypeWorkspace,
		coresb.SmartBlockTypeRelation, coresb.SmartBlockTypeObjectType,
		coresb.SmartBlockTypeRelationOption, coresb.SmartBlockTypeBundledRelation,
		coresb.SmartBlockTypeBundledObjectType, coresb.SmartBlockTypeSpaceView,
		coresb.SmartBlockTypeAccountObject, coresb.SmartBlockTypeTechSpaceObject,
		coresb.SmartBlockTypeTechSpaceVirtualObject) {
		return true
	}
	layout, ok := d.TryInt64(bundle.RelationKeyResolvedLayout)
	if !ok {
		layout, ok = d.TryInt64(bundle.RelationKeyLayout)
	}
	if !ok || layout < 0 || layout > 1<<31-1 {
		return false
	}
	_, known := model.ObjectTypeLayout_name[int32(layout)]
	return known && !isUserDocument(d)
}

// CouldDeliverRelated catches an extra stale indexed document which has no
// authoritative native head. Such a row cannot be ignored merely because it is
// absent from the native enumeration; a related query could still expose it.
func CouldDeliverRelated(d *domain.Details) bool {
	return d != nil && !d.GetBool(bundle.RelationKeyIsDeleted) &&
		(d.GetBool(domain.RelationKey(torah.ReadyKey)) ||
			d.GetInt64(domain.RelationKey(torah.RelatedVersionKey)) != 0 ||
			len(d.GetStringList(domain.RelationKey(torah.RelatedSourcesKey))) != 0 ||
			(isUserDocument(d) && !d.GetBool(bundle.RelationKeyIsArchived) && !d.Has(bundle.RelationKeyTargetObjectType)))
}

// A terminal deletion must have the original exact id/Space tombstone and no
// live document projection or canonical payload. Non-deliverable cache-binding
// hints left by the original projector are permitted; they grant no readiness.
func IsReadinessTombstone(d *domain.Details, space, id, canonicalKey string) bool {
	if d == nil || d.GetString(bundle.RelationKeyId) != id || d.GetString(bundle.RelationKeySpaceId) != space || !d.GetBool(bundle.RelationKeyIsDeleted) || d.Has(domain.RelationKey(canonicalKey)) {
		return false
	}
	for _, key := range torah.LocalKeys() {
		if key == torah.CanonicalKeyKey || key == torah.CacheIntegrityKey {
			continue
		}
		if d.Has(domain.RelationKey(key)) {
			return false
		}
	}
	return true
}
