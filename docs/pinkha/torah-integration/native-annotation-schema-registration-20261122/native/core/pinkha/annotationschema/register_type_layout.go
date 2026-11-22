package annotationschema

import (
	"fmt"
	"slices"

	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/template"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/restriction"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// No filtered key resolver runs here. Exact property IDs are freshly verified
// from original persisted roots while the actual type object is locked. The
// original column helper and normal Apply preserve native layout/ACL semantics.
func (s *registrationSession) attachHiddenProperties(result *Registration) error {
	typeID := result.Observation.Definitions[0].Native.ObjectID
	if err := s.current(); err != nil {
		return err
	}
	return s.spc.DoCtx(s.ctx, typeID, func(object smartblock.SmartBlock) error {
		if err := s.current(); err != nil {
			return err
		}
		if object.Id() != typeID || object.SpaceID() != s.spc.Id() || object.Space().Id() != s.spc.Id() ||
			object.Type() != coresb.SmartBlockTypeObjectType || object.UniqueKey() == nil ||
			object.UniqueKey().Marshal() != TypeUniqueKey || object.Tree() == nil || object.IsDeleted() {
			return ErrRegistrationConflict
		}
		policy := object.MemberPolicy()
		if policy.LockSpaceConfig && restriction.IsSpaceConfigObject(object, policy) {
			return restriction.ErrRestricted
		}
		fresh, err := s.readback()
		result.Observation = fresh
		if err != nil {
			return err
		}
		if err = registrationPreflight(fresh); err != nil {
			return err
		}
		if !registrationDefinitionsReady(fresh) {
			return ErrRegistrationUnresolved
		}
		persisted := fresh.Definitions[0].Native
		if !sameHeads(object.Tree().Heads(), persisted.PersistedHeads) {
			return objectcreator.ErrFixedSchemaChanged
		}
		persistedDetails, persistedBlocks := persisted.CopyPersistedSchemaState()
		st := object.NewState()
		if !proto.Equal(st.Details().ToProto(), persistedDetails) || !sameSchemaBlocks(st.BlocksToSave(), persistedBlocks) {
			// A previous failed original Apply may leave in-memory changes.
			// Never use a matching head alone to overwrite such divergence.
			return fmt.Errorf("%w: loaded type differs from complete persisted native state", ErrRegistrationConflict)
		}
		relations := make(map[string]string, len(relationNames))
		for i, definition := range s.definitions[1:] {
			relations[definition.Key.InternalKey()] = fresh.Definitions[i+1].Native.ObjectID
		}
		layout := observeTypeLayout(st.Details().ToProto(), st.BlocksToSave(), typeID, relations)
		if layout.Disposition == Conflict || !layout.Hidden || !layout.DiscoveryHidden || len(layout.ViewIDs) == 0 {
			return ErrRegistrationConflict
		}
		if layout.Disposition == MatchingObserved {
			return nil
		}
		hidden := slices.Clone(layout.HiddenRelationIDs)
		for _, relation := range relationNames {
			if id := relations[relation.key]; !slices.Contains(hidden, id) {
				hidden = append(hidden, id)
			}
		}
		changed := !slices.Equal(hidden, layout.HiddenRelationIDs)
		if changed {
			st.SetDetailAndBundledRelation(bundle.RelationKeyRecommendedHiddenRelations, domain.StringList(hidden))
		}
		block := template.TypeDataviewBlock(st)
		if block == nil {
			return ErrRegistrationUnresolved
		}
		edited := block.Copy()
		columnsChanged := false
		for _, relation := range relationNames {
			_, added := template.AddTypeDataviewColumn(edited.Model().GetDataview(), &model.RelationLink{
				Key: relation.key, Format: model.RelationFormat_longtext,
			}, false)
			columnsChanged = columnsChanged || added
		}
		if columnsChanged {
			st.Set(edited)
			changed = true
		}
		if !changed {
			return ErrRegistrationUnresolved
		}
		if err = s.current(); err != nil {
			return err
		}
		// No NoRestrictions/NoSpaceConfigCheck flags. Original Apply and signed
		// AddContent retain their own current permission and durability checks.
		result.TypeApplyInvoked = true
		err = object.Apply(st)
		result.TypeApplyReturned = err == nil
		return err
	})
}

func sameSchemaBlocks(actual, persisted []*model.Block) bool {
	if len(actual) != len(persisted) {
		return false
	}
	byID := make(map[string]*model.Block, len(persisted))
	for _, block := range persisted {
		if block == nil || block.Id == "" || byID[block.Id] != nil {
			return false
		}
		byID[block.Id] = block
	}
	for _, block := range actual {
		if block == nil || block.Id == "" || !proto.Equal(block, byID[block.Id]) {
			return false
		}
		delete(byID, block.Id)
	}
	return len(byID) == 0
}
