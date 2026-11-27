package spaceobjects

import (
	"context"
	"fmt"
	"slices"
	"strings"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/object"
	"github.com/anyproto/any-sync-sdk/internal/properties"
	"github.com/anyproto/any-sync-sdk/internal/types"
	collectiontype "github.com/anyproto/any-sync-sdk/internal/types/collection"
	typetype "github.com/anyproto/any-sync-sdk/internal/types/type"
)

func (s *Store) staticOwnerKind(id string) string {
	if _, ok := ReservedTypeIds[id]; ok {
		return "type"
	}
	for _, t := range s.extTypes {
		if t.Id == id {
			return "type"
		}
	}
	for _, c := range s.extCollections {
		if c.Id == id {
			return "collection"
		}
	}
	return ""
}

// Membership edits from the protected SDK routes are flat property patches,
// not arbitrary record transformations. Read the proposed type/collections
// without mutating the persisted row. Normal property validation still runs.
func nativeMembership(row *anyenc.Value, ch *crdt.Change) (typeID string, collections []string, changedCollections bool, err error) {
	if row != nil {
		typeID = row.GetString("any", "type")
	}
	collections = []string{}
	parseCollections := func(value *anyenc.Value) error {
		collections = []string{}
		if value == nil {
			return nil
		}
		if value.Type() != anyenc.TypeArray {
			return crdt.ErrValidation
		}
		for _, v := range value.GetArray() {
			if v.Type() != anyenc.TypeString || v.GetString() == "" {
				return crdt.ErrValidation
			}
			collections = append(collections, v.GetString())
		}
		return nil
	}
	if row != nil {
		if err = parseCollections(row.Get("any", "collections")); err != nil {
			return
		}
	}
	if ch == nil || ch.Dataset != "objects" {
		return
	}
	if len(ch.Records) != 1 {
		return "", nil, false, crdt.ErrValidation
	}
	if ch.NativeConditionalNoop {
		if len(ch.Records[0].Ops) != 0 || ch.Records[0].Upsert {
			return "", nil, false, crdt.ErrValidation
		}
		// Empty patches retain the current collection-definition fence that
		// an equal nonempty membership patch would acquire and validate.
		changedCollections = true
	}
	for _, op := range ch.Records[0].Ops {
		if op.Type != crdt.OpSet && op.Type != crdt.OpUnset {
			return "", nil, false, crdt.ErrValidation
		}
		if len(op.Path) != 0 || op.Payload == nil || op.Payload.Type() != anyenc.TypeObject {
			return "", nil, false, crdt.ErrValidation
		}
		if value := op.Payload.Get("any.type"); value != nil {
			if op.Type != crdt.OpSet || value.Type() != anyenc.TypeString || value.GetString() == "" {
				return "", nil, false, crdt.ErrValidation
			}
			typeID = value.GetString()
		}
		if value := op.Payload.Get("any.collections"); value != nil {
			changedCollections = true
			if op.Type == crdt.OpUnset {
				collections = []string{}
			} else if err = parseCollections(value); err != nil {
				return
			}
		}
	}
	return
}

// Resolve dependencies before taking any multi-tree lock. Each target is read
// under its own lock only to discover the type. Final reads validate the actual
// type against the locked dependency set; a changed unseen type refuses.
func (s *Store) preloadNativeDefinitions(ctx context.Context, objects map[string]*object.Object, carrier *object.Object, ch *crdt.Change) error {
	owners := map[string]bool{}
	original := make([]*object.Object, 0, len(objects))
	for _, o := range objects {
		original = append(original, o)
	}
	for _, o := range original {
		o.Tree().Lock()
		err := o.GuardReadyLocked(ctx)
		var row *anyenc.Value
		if err == nil {
			row, err = o.Controller().GuardLookup(ctx, "objects", o.Id())
		}
		var typeID string
		var collections []string
		changedCollections := false
		if err == nil {
			var write *crdt.Change
			if o == carrier && ch != nil && ch.NativeObjectPolicy {
				write = ch
			}
			typeID, collections, changedCollections, err = nativeMembership(row, write)
		}
		o.Tree().Unlock()
		if err != nil {
			return err
		}
		if typeID != "" && typeID != typetype.MetaTypeMarker && typeID != collectiontype.MetaMarker {
			owners[typeID] = true
		}
		if changedCollections {
			for _, id := range collections {
				owners[id] = true
			}
		}
	}
	if ch != nil {
		for _, id := range ch.NativeDefinitionOwners {
			if id == "" {
				return crdt.ErrValidation
			}
			owners[id] = true
		}
	}
	if len(owners) > 2048 {
		return crdt.ErrValidation
	}
	ids := make([]string, 0, len(owners))
	for id := range owners {
		ids = append(ids, id)
	}
	slices.Sort(ids)
	for _, id := range ids {
		if s.staticOwnerKind(id) != "" || objects[id] != nil {
			continue
		}
		definition, err := s.Get(ctx, id)
		if err != nil {
			return err
		}
		objects[id] = definition
	}
	return nil
}

func (v lockedReadView) definitionKind(id string) (string, error) {
	if v.store == nil || id == "" {
		return "", crdt.ErrValidation
	}
	if kind := v.store.staticOwnerKind(id); kind != "" {
		return kind, nil
	}
	owner := v.objects[id]
	if owner == nil {
		return "", crdt.ErrPreconditionFailed
	}
	row, err := owner.Controller().GuardLookup(v.ctx, "objects", id)
	if err != nil {
		return "", err
	}
	if row == nil || row.Get("_deletedAt") != nil || row.GetString("id") != id || row.GetString("spaceId") != v.store.spaceId {
		return "", crdt.ErrValidation
	}
	switch row.GetString("any", "type") {
	case typetype.MetaTypeMarker:
		return "type", nil
	case collectiontype.MetaMarker:
		return "collection", nil
	default:
		return "", crdt.ErrValidation
	}
}

func (v lockedReadView) compiledType(id string) (*types.CompiledType, error) {
	kind, err := v.definitionKind(id)
	if err != nil {
		return nil, err
	}
	if kind != "type" {
		return nil, properties.ErrWrongSlot
	}
	for _, t := range v.store.extTypes {
		if t.Id == id {
			return StaticTypeParts(t, v.store.moduleInfos)
		}
	}
	if _, ok := ReservedTypeIds[id]; ok {
		return &types.CompiledType{}, nil
	}
	return v.store.TypeParts(v.ctx, id)
}

func (v lockedReadView) TypeDeclaresDataset(typeID, module, dataset string, canonicalOnly bool) (bool, error) {
	compiled, err := v.compiledType(typeID)
	if err != nil {
		return false, err
	}
	if compiled == nil {
		return false, nil
	}
	for _, d := range compiled.Datasets {
		if !d.Invalid && d.Name == dataset && (module == "" || d.Module == module) && (!canonicalOnly || d.Canonical) {
			return true, nil
		}
	}
	return false, nil
}

// ValidateNativeObjectChange is called after sequence checks, with every
// discovered definition held. Unrelated/orphan property groups remain stored.
func (v lockedReadView) ValidateNativeObjectChange(ch *crdt.Change) error {
	if ch == nil || !ch.NativeObjectPolicy || v.store == nil {
		return crdt.ErrValidation
	}
	carrier := v.objects[ch.ObjectId]
	// ObjectId is native metadata and may not have been stamped yet on the
	// ordinary route. The locker captures the actual carrier explicitly.
	if carrier == nil {
		carrier = v.carrier
	}
	if carrier == nil {
		return crdt.ErrValidation
	}
	row, err := carrier.Controller().GuardLookup(v.ctx, "objects", carrier.Id())
	if err != nil {
		return err
	}
	typeID, collections, changedCollections, err := nativeMembership(row, ch)
	if err != nil {
		return err
	}
	if typeID == "" || properties.IsMetaType(typeID) {
		return properties.ErrMetaType
	}
	kind, err := v.definitionKind(typeID)
	if err != nil {
		return err
	}
	if kind != "type" {
		return properties.ErrWrongSlot
	}
	compiled, err := v.compiledType(typeID)
	if err != nil {
		return err
	}
	if compiled != nil && typeID != carrier.Id() {
		for _, d := range compiled.Datasets {
			if !d.Invalid && v.store.moduleInfos.Reserved(d.Module) {
				return crdt.ErrValidation
			}
		}
	}
	for _, required := range ch.NativeTypeDatasets {
		if required.Module == "" || required.Dataset == "" {
			return crdt.ErrValidation
		}
		allowed, err := v.TypeDeclaresDataset(typeID, required.Module, required.Dataset, required.Canonical)
		if err != nil {
			return err
		}
		if !allowed {
			return fmt.Errorf("%w: destination type no longer declares the required native dataset", crdt.ErrPreconditionFailed)
		}
	}
	if changedCollections {
		for _, id := range collections {
			if properties.IsMetaType(id) {
				return properties.ErrMetaType
			}
			kind, err := v.definitionKind(id)
			if err != nil {
				return err
			}
			if kind != "collection" {
				return properties.ErrWrongSlot
			}
		}
	}
	for _, id := range ch.NativeDefinitionOwners {
		if _, err := v.definitionKind(id); err != nil {
			return err
		}
		// With no field op, the ordinary property validator has no owner
		// path to check. Verify the requested owner against this locked row.
		if ch.NativeConditionalNoop && id != "any" && id != typeID && !slices.Contains(collections, id) {
			return properties.ErrWrongSlot
		}
	}
	if ch.Dataset != "objects" {
		if slices.Contains(collections, "bin") || slices.Contains(collections, "template") {
			return fmt.Errorf("%w: inactive document", crdt.ErrValidation)
		}
		allowed, err := v.TypeDeclaresDataset(typeID, "", ch.Dataset, false)
		if err != nil {
			return err
		}
		if !allowed {
			return fmt.Errorf("%w: current type no longer declares dataset %s", crdt.ErrValidation, ch.Dataset)
		}
	}
	// Refuse forged membership paths hidden in a nested any object. The
	// protected API uses patchOps/bootstrap's documented flat path map.
	if ch.Dataset == "objects" {
		for _, r := range ch.Records {
			for _, op := range r.Ops {
				obj, _ := op.Payload.Object()
				if obj == nil {
					continue
				}
				invalid := false
				obj.Visit(func(key []byte, _ *anyenc.Value) {
					if string(key) == "any" || strings.HasPrefix(string(key), "any.type.") || strings.HasPrefix(string(key), "any.collections.") {
						invalid = true
					}
				})
				if invalid {
					return crdt.ErrValidation
				}
			}
		}
	}
	if ch.NativeBookmarkCreateFrame != nil {
		return v.validateBookmarkCreate(ch, typeID, collections)
	}
	return nil
}
