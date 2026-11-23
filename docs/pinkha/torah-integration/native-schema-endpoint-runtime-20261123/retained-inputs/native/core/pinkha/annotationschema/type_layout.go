package annotationschema

import (
	"fmt"

	"github.com/gogo/protobuf/types"

	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

type TypeLayoutObservation struct {
	Disposition         Disposition
	Reason              string
	Hidden              bool
	DiscoveryHidden     bool
	HiddenRelationIDs   []string
	MissingRelationKeys []string
	ViewIDs             []string
}

func observeTypeLayout(details *types.Struct, blocks []*model.Block, typeID string, relations map[string]string) (result TypeLayoutObservation) {
	result.Disposition = MatchingObserved
	fail := func(disposition Disposition, reason string) TypeLayoutObservation {
		result.Disposition, result.Reason = disposition, reason
		return result
	}
	var err error
	result.Hidden, err = strictBoolean(details, bundle.RelationKeyIsHidden.String())
	if err != nil {
		return fail(Conflict, err.Error())
	}
	result.DiscoveryHidden, err = strictBoolean(details, bundle.RelationKeyIsHiddenDiscovery.String())
	if err != nil {
		return fail(Conflict, err.Error())
	}
	if !result.Hidden || !result.DiscoveryHidden {
		result.Disposition, result.Reason = Incomplete, "type visibility flags are not both true"
	}
	lists := make(map[string]map[string]bool, 4)
	for _, key := range []string{bundle.RelationKeyRecommendedRelations.String(),
		bundle.RelationKeyRecommendedFeaturedRelations.String(), bundle.RelationKeyRecommendedHiddenRelations.String(),
		bundle.RelationKeyRecommendedFileRelations.String()} {
		ids, err := strictStringList(details, key)
		if err != nil {
			return fail(Conflict, err.Error())
		}
		set := make(map[string]bool, len(ids))
		for _, id := range ids {
			if set[id] {
				return fail(Conflict, "duplicate native property ID in "+key)
			}
			set[id] = true
		}
		lists[key] = set
		if key == bundle.RelationKeyRecommendedHiddenRelations.String() {
			result.HiddenRelationIDs = ids
		}
	}
	for _, relation := range relationNames {
		id, found := relations[relation.key]
		if !found || id == "" {
			return fail(Incomplete, "missing persisted relation "+relation.key)
		}
		for key, ids := range lists {
			if key != bundle.RelationKeyRecommendedHiddenRelations.String() && ids[id] {
				return fail(Conflict, "annotation metadata appears outside the hidden section: "+relation.key)
			}
		}
		if !lists[bundle.RelationKeyRecommendedHiddenRelations.String()][id] {
			result.Disposition, result.Reason = Incomplete, "missing hidden metadata attachment"
			result.MissingRelationKeys = append(result.MissingRelationKeys, relation.key)
		}
	}
	setOf, err := strictStringList(details, bundle.RelationKeySetOf.String())
	if err != nil {
		return fail(Conflict, err.Error())
	}
	if len(setOf) != 1 || setOf[0] != typeID {
		return fail(Conflict, "original type setOf does not identify its own native type")
	}
	var dataview *model.BlockContentDataview
	blockIDs := make(map[string]bool, len(blocks))
	for _, block := range blocks {
		if block == nil || block.Id == "" || blockIDs[block.Id] {
			return fail(Conflict, "malformed or duplicate original schema block")
		}
		blockIDs[block.Id] = true
		if view := block.GetDataview(); view != nil {
			if dataview != nil {
				return fail(Conflict, "multiple original type dataview blocks")
			}
			dataview = view
		}
	}
	if dataview == nil || len(dataview.Views) == 0 {
		return fail(Incomplete, "original type dataview or views are missing")
	}
	if dataview.IsCollection || dataview.TargetObjectId != typeID {
		return fail(Conflict, "original dataview is not scoped to its own native type")
	}
	links := make(map[string]model.RelationFormat, len(dataview.RelationLinks))
	for _, link := range dataview.RelationLinks {
		if link == nil || link.Key == "" {
			return fail(Conflict, "malformed original dataview relation link")
		}
		if _, duplicate := links[link.Key]; duplicate {
			return fail(Conflict, "duplicate original dataview relation link")
		}
		links[link.Key] = link.Format
	}
	for _, relation := range relationNames {
		format, found := links[relation.key]
		if !found {
			result.Disposition, result.Reason = Incomplete, "missing original metadata relation link"
		} else if format != model.RelationFormat_longtext {
			return fail(Conflict, "original metadata relation link has another native format")
		}
	}
	viewIDs := make(map[string]bool, len(dataview.Views))
	for _, view := range dataview.Views {
		if view == nil || view.Id == "" || viewIDs[view.Id] {
			return fail(Conflict, "malformed or duplicate original dataview view")
		}
		viewIDs[view.Id] = true
		result.ViewIDs = append(result.ViewIDs, view.Id)
		columns := make(map[string]bool, len(view.Relations))
		for _, column := range view.Relations {
			if column == nil || column.Key == "" {
				return fail(Conflict, "malformed original dataview column")
			}
			if _, duplicate := columns[column.Key]; duplicate {
				return fail(Conflict, "duplicate original dataview column")
			}
			columns[column.Key] = column.IsVisible
		}
		for _, relation := range relationNames {
			visible, found := columns[relation.key]
			if !found {
				result.Disposition, result.Reason = Incomplete, "missing original metadata view column"
			} else if visible {
				return fail(Conflict, "original metadata column is visible in view "+view.Id)
			}
		}
	}
	return result
}

func strictStringList(details *types.Struct, key string) ([]string, error) {
	value, present := details.Fields[key]
	if !present {
		return nil, nil
	}
	list, ok := value.GetKind().(*types.Value_ListValue)
	if !ok || list.ListValue == nil {
		return nil, fmt.Errorf("malformed original string list %s", key)
	}
	result := make([]string, len(list.ListValue.Values))
	for i, item := range list.ListValue.Values {
		text, ok := item.GetKind().(*types.Value_StringValue)
		if !ok || text.StringValue == "" {
			return nil, fmt.Errorf("malformed original string list item %s", key)
		}
		result[i] = text.StringValue
	}
	return result, nil
}

func strictBoolean(details *types.Struct, key string) (bool, error) {
	value, present := details.Fields[key]
	if !present {
		return false, nil
	}
	flag, ok := value.GetKind().(*types.Value_BoolValue)
	if !ok {
		return false, fmt.Errorf("malformed original boolean %s", key)
	}
	return flag.BoolValue, nil
}
