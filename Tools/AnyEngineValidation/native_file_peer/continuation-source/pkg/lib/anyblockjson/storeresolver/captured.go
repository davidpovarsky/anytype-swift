//go:build pinkha_loaded_account_witness

package storeresolver

import (
	"errors"
	"fmt"
	"reflect"
	"sort"
	"sync"

	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/relationutils"
	"github.com/anyproto/anytype-heart/pkg/lib/anyblockjson"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

var ErrCapturedResolver = errors.New("closed captured native schema resolution required")

// CapturedRow is a pure input, not account authorization. The application joins
// each row's raw snapshot and native root/heads before constructing this index.
type CapturedRow struct {
	ID        string
	Type      model.SmartBlockType
	UniqueKey string
	Snapshot  *model.SmartBlockSnapshotBase
	Deleted   bool
}

type UnmappedReference struct {
	SourceID, Field, Target, Reason string
}

// CapturedResolver never opens an index, object, file or network connection.
// Its copied rows are immutable. Every unresolved lookup is retained explicitly
// so a codec fallback or omitted target cannot masquerade as completeness.
type CapturedResolver struct {
	spaceID         string
	rows            map[string]*domain.Details
	kinds           map[string]model.SmartBlockType
	ids             []string
	propertiesByKey map[string][]string
	typesByKey      map[string][]string
	mu              sync.Mutex
	unmapped        map[UnmappedReference]struct{}
	bundled         map[string]struct{}
}

func (c *CapturedResolver) issue(source, field, target, reason string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.unmapped[UnmappedReference{source, field, target, reason}] = struct{}{}
}
func (c *CapturedResolver) bundledDefinition(kind, key string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.bundled[kind+":"+key] = struct{}{}
}

func NewCaptured(spaceID string, input []CapturedRow) (*CapturedResolver, error) {
	if spaceID == "" || len(input) == 0 || len(input) > 10000 {
		return nil, ErrCapturedResolver
	}
	c := &CapturedResolver{
		spaceID: spaceID, rows: map[string]*domain.Details{}, kinds: map[string]model.SmartBlockType{},
		propertiesByKey: map[string][]string{}, typesByKey: map[string][]string{},
		unmapped: map[UnmappedReference]struct{}{}, bundled: map[string]struct{}{},
	}
	for _, row := range input {
		if row.ID == "" || c.rows[row.ID] != nil || row.Snapshot == nil || row.Snapshot.Details == nil {
			return nil, ErrCapturedResolver
		}
		// Proto cloning detaches nested struct/list values, not just the map.
		snapshot := proto.Clone(row.Snapshot).(*model.SmartBlockSnapshotBase)
		details := domain.NewDetailsFromProto(snapshot.Details)
		if id := details.GetString(bundle.RelationKeyId); id != "" && id != row.ID {
			return nil, ErrCapturedResolver
		}
		if sp := details.GetString(bundle.RelationKeySpaceId); sp != "" && sp != spaceID {
			return nil, ErrCapturedResolver
		}
		details.Set(bundle.RelationKeyId, domain.String(row.ID))
		details.Set(bundle.RelationKeySpaceId, domain.String(spaceID))
		if row.UniqueKey != "" {
			if key := details.GetString(bundle.RelationKeyUniqueKey); key != "" && key != row.UniqueKey {
				return nil, ErrCapturedResolver
			}
			details.Set(bundle.RelationKeyUniqueKey, domain.String(row.UniqueKey))
		}
		if row.Deleted || details.GetBool(bundle.RelationKeyIsUninstalled) {
			details.Set(bundle.RelationKeyIsDeleted, domain.Bool(true))
		}
		switch row.Type {
		case model.SmartBlockType_STRelation:
			details.Set(bundle.RelationKeyResolvedLayout, domain.Int64(int64(model.ObjectType_relation)))
			key := details.GetString(bundle.RelationKeyRelationKey)
			if key == "" {
				c.issue(row.ID, "relationKey", "", "missing-property-key")
			} else {
				c.propertiesByKey[key] = append(c.propertiesByKey[key], row.ID)
			}
		case model.SmartBlockType_STRelationOption:
			details.Set(bundle.RelationKeyResolvedLayout, domain.Int64(int64(model.ObjectType_relationOption)))
		case model.SmartBlockType_STType:
			details.Set(bundle.RelationKeyResolvedLayout, domain.Int64(int64(model.ObjectType_objectType)))
			key, err := domain.GetTypeKeyFromRawUniqueKey(row.UniqueKey)
			if err != nil || key == "" {
				c.issue(row.ID, "uniqueKey", row.UniqueKey, "invalid-type-key")
			} else {
				c.typesByKey[string(key)] = append(c.typesByKey[string(key)], row.ID)
			}
		}
		c.rows[row.ID], c.kinds[row.ID] = details, row.Type
		c.ids = append(c.ids, row.ID)
	}
	sort.Strings(c.ids)
	for key, ids := range c.propertiesByKey {
		if c.uniqueActive(ids) == "" {
			for _, id := range ids {
				c.issue(id, "relationKey", key, "colliding-property-key")
			}
		}
	}
	for key, ids := range c.typesByKey {
		if c.uniqueActive(ids) == "" {
			for _, id := range ids {
				c.issue(id, "uniqueKey", key, "colliding-type-key")
			}
		}
	}
	// Validate source references before any codec branch can silently drop
	// unresolved target types or recommended property IDs.
	for _, row := range input {
		// Native snapshots serialize TypeKey.URL() via domain.MarshalTypeKeys.
		// These URLs are not internal keys or native object IDs. Preserve each
		// original spelling while resolving only the parsed native key.
		seenTypes := map[domain.TypeKey]string{}
		for _, raw := range row.Snapshot.ObjectTypes {
			key, reason := c.snapshotTypeKey(raw)
			if reason != "" {
				c.issue(row.ID, "objectTypes", raw, reason)
				continue
			}
			if previous, exists := seenTypes[key]; exists {
				c.issue(row.ID, "objectTypes", previous, "duplicate-type-alias")
				c.issue(row.ID, "objectTypes", raw, "duplicate-type-alias")
				continue
			}
			seenTypes[key] = raw
			if !c.hasTypeKey(key.String()) {
				c.issue(row.ID, "objectTypes", raw, "missing-type-key")
			}
		}
		d := c.rows[row.ID]
		if row.Type == model.SmartBlockType_STRelation {
			format := model.RelationFormat(d.GetFloat64(bundle.RelationKeyRelationFormat))
			if _, exists := model.RelationFormat_name[int32(format)]; !exists {
				c.issue(row.ID, "relationFormat", fmt.Sprint(int32(format)), "unsupported-property-format")
			}
			for _, target := range d.GetStringList(bundle.RelationKeyRelationFormatObjectTypes) {
				if !c.hasTypeID(target) {
					c.issue(row.ID, "relationFormatObjectTypes", target, "unmapped-target-type")
				}
			}
		}
		if row.Type == model.SmartBlockType_STType {
			for _, field := range recommendedListDetailKeys {
				for _, target := range d.GetStringList(field) {
					if c.kinds[target] != model.SmartBlockType_STRelation {
						c.issue(row.ID, string(field), target, "unmapped-recommended-property")
					}
				}
			}
		}
		for _, link := range row.Snapshot.RelationLinks {
			if link == nil || link.Key == "" {
				continue
			}
			if _, err := c.propertyByKey(link.Key); err != nil {
				c.issue(row.ID, "relationLinks", link.Key, "unmapped-property-definition")
			}
		}
	}
	return c, nil
}

func (c *CapturedResolver) active(id string) bool {
	d := c.rows[id]
	return d != nil && !d.GetBool(bundle.RelationKeyIsDeleted) &&
		!d.GetBool(bundle.RelationKeyIsArchived) && !d.GetBool(bundle.RelationKeyIsUninstalled)
}
func (c *CapturedResolver) uniqueActive(ids []string) string {
	active := ""
	for _, id := range ids {
		if c.active(id) {
			if active != "" {
				return ""
			}
			active = id
		}
	}
	if active != "" {
		return active
	}
	if len(ids) == 1 {
		return ids[0]
	}
	return ""
}
func (c *CapturedResolver) snapshotTypeKey(raw string) (domain.TypeKey, string) {
	// A captured object ID never grants a second meaning to this key slot,
	// even if its spelling could also be parsed as a legacy type URL.
	if _, exists := c.rows[raw]; exists {
		return "", "type-object-id-in-key-slot"
	}
	key, err := bundle.TypeKeyFromUrl(raw)
	if err != nil || key == "" || (raw != key.URL() && raw != key.BundledURL()) {
		return "", "invalid-type-url"
	}
	return key, ""
}

func (c *CapturedResolver) hasTypeKey(key string) bool {
	if ids := c.typesByKey[key]; len(ids) > 0 {
		// Ambiguous captured identities must not become a successful lookup
		// merely because the same key is also present in the bundled table.
		return c.uniqueActive(ids) != ""
	}
	if bundle.HasObjectTypeByKey(domain.TypeKey(key)) {
		c.bundledDefinition("type", key)
		return true
	}
	return false
}
func (c *CapturedResolver) hasTypeID(id string) bool {
	if c.kinds[id] == model.SmartBlockType_STType {
		return true
	}
	if key, err := bundle.TypeKeyFromUrl(id); err == nil && bundle.HasObjectTypeByKey(key) {
		c.bundledDefinition("type", string(key))
		return true
	}
	return false
}
func (c *CapturedResolver) propertyByKey(key string) (*model.Relation, error) {
	if ids := c.propertiesByKey[key]; len(ids) > 0 {
		id := c.uniqueActive(ids)
		if id == "" {
			return nil, ErrCapturedResolver
		}
		return relationutils.RelationFromDetails(c.rows[id]).Relation, nil
	}
	if rel, err := bundle.GetRelation(domain.RelationKey(key)); err == nil && rel != nil {
		c.bundledDefinition("property", key)
		return proto.Clone(rel).(*model.Relation), nil
	}
	return nil, ErrCapturedResolver
}

func (c *CapturedResolver) Unmapped() []UnmappedReference {
	c.mu.Lock()
	defer c.mu.Unlock()
	out := make([]UnmappedReference, 0, len(c.unmapped))
	for item := range c.unmapped {
		out = append(out, item)
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.SourceID != b.SourceID {
			return a.SourceID < b.SourceID
		}
		if a.Field != b.Field {
			return a.Field < b.Field
		}
		if a.Target != b.Target {
			return a.Target < b.Target
		}
		return a.Reason < b.Reason
	})
	return out
}
func (c *CapturedResolver) BundledDefinitionsUsed() []string {
	c.mu.Lock()
	defer c.mu.Unlock()
	out := make([]string, 0, len(c.bundled))
	for item := range c.bundled {
		out = append(out, item)
	}
	sort.Strings(out)
	return out
}

// OptionsForObject creates private per-render vocabulary caches over the same
// immutable source rows. Missing lookups carry the actual source object ID.
func (c *CapturedResolver) OptionsForObject(objectID string) (anyblockjson.Options, error) {
	if c == nil || c.rows[objectID] == nil {
		return anyblockjson.Options{}, ErrCapturedResolver
	}
	view := &capturedIndexView{c: c, owner: objectID}
	r := &Resolvers{index: view, optionsFor: map[domain.RelationKey][]*model.RelationOption{}, objectRows: map[string]objectRow{}}
	opts := r.Options()
	opts.ResolveFormat = func(key domain.RelationKey) (model.RelationFormat, bool) {
		format, ok := r.ResolveFormat(key)
		if !ok {
			c.issue(objectID, "propertyFormat", string(key), "unmapped-property-key")
		}
		return format, ok
	}
	adapter := &capturedLookup{r: r, c: c, owner: objectID}
	opts.ResolveProperties = adapter
	opts.ResolveOptions = adapter
	opts.ResolveObjectNames = adapter
	return opts, nil
}

type capturedIndexView struct {
	c     *CapturedResolver
	owner string
}

func (v *capturedIndexView) SpaceId() string { return v.c.spaceID }
func (v *capturedIndexView) GetDetails(id string) (*domain.Details, error) {
	if d := v.c.rows[id]; d != nil {
		return d.Copy(), nil
	}
	v.c.issue(v.owner, "object", id, "unmapped-object")
	return nil, ErrCapturedResolver
}
func (v *capturedIndexView) GetRelationByKey(key string) (*model.Relation, error) {
	rel, err := v.c.propertyByKey(key)
	if err != nil {
		v.c.issue(v.owner, "propertyKey", key, "unmapped-or-colliding-property-key")
	}
	return rel, err
}
func (v *capturedIndexView) GetRelationById(id string) (*model.Relation, error) {
	if v.c.kinds[id] != model.SmartBlockType_STRelation {
		v.c.issue(v.owner, "propertyID", id, "unmapped-property-id")
		return nil, ErrCapturedResolver
	}
	return relationutils.RelationFromDetails(v.c.rows[id]).Relation, nil
}
func (v *capturedIndexView) ListAllRelations() (relationutils.Relations, error) {
	var out relationutils.Relations
	keys := map[string]bool{}
	for _, id := range v.c.ids {
		if v.c.kinds[id] == model.SmartBlockType_STRelation && v.c.active(id) {
			rel := relationutils.RelationFromDetails(v.c.rows[id])
			out = append(out, rel)
			keys[rel.Key] = true
		}
	}
	for _, key := range bundle.SystemRelations {
		if keys[string(key)] {
			continue
		}
		rel, err := v.c.propertyByKey(string(key))
		if err != nil {
			return nil, err
		}
		out = append(out, &relationutils.Relation{Relation: rel})
	}
	return out, nil
}
func (v *capturedIndexView) ListRelationOptions(key domain.RelationKey) ([]*model.RelationOption, error) {
	var out []*model.RelationOption
	for _, id := range v.c.ids {
		d := v.c.rows[id]
		if v.c.kinds[id] == model.SmartBlockType_STRelationOption && v.c.active(id) &&
			d.GetString(bundle.RelationKeyRelationKey) == string(key) {
			out = append(out, relationutils.OptionFromDetails(d).RelationOption)
		}
	}
	return out, nil
}
func (v *capturedIndexView) Query(query database.Query) ([]database.Record, error) {
	var layout model.ObjectTypeLayout
	matched := false
	for _, candidate := range []model.ObjectTypeLayout{model.ObjectType_relation, model.ObjectType_objectType} {
		filters := []database.FilterRequest{{RelationKey: bundle.RelationKeyResolvedLayout,
			Condition: model.BlockContentDataviewFilter_Equal, Value: domain.Int64(int64(candidate))}}
		if candidate == model.ObjectType_objectType {
			filters = append(filters, database.FilterRequest{RelationKey: bundle.RelationKeyIsArchived, Condition: model.BlockContentDataviewFilter_None},
				database.FilterRequest{RelationKey: bundle.RelationKeyIsDeleted, Condition: model.BlockContentDataviewFilter_None})
		}
		if reflect.DeepEqual(query, database.Query{Filters: filters}) {
			layout, matched = candidate, true
			break
		}
	}
	if !matched {
		v.c.issue(v.owner, "query", "", "unsupported-captured-query")
		return nil, ErrCapturedResolver
	}
	var out []database.Record
	for _, id := range v.c.ids {
		d := v.c.rows[id]
		if d.GetInt64(bundle.RelationKeyResolvedLayout) != int64(layout) {
			continue
		}
		if layout == model.ObjectType_relation && !v.c.active(id) {
			continue
		}
		out = append(out, database.Record{Details: d.Copy()})
	}
	return out, nil
}

type capturedLookup struct {
	r     *Resolvers
	c     *CapturedResolver
	owner string
}

func (a *capturedLookup) PropertyById(id string) (anyblockjson.PropertyDefinition, bool) {
	def, ok := a.r.PropertyById(id)
	if !ok {
		a.c.issue(a.owner, "propertyID", id, "unmapped-property-id")
	}
	return def, ok
}
func (a *capturedLookup) PropertyId(def anyblockjson.PropertyDefinition) (string, bool) {
	id, ok := a.r.PropertyId(def)
	if !ok {
		a.c.issue(a.owner, "propertyKey", string(def.Key), "unmapped-property-key")
	}
	return id, ok
}
func (a *capturedLookup) OptionName(key domain.RelationKey, id string) (string, bool) {
	name, ok := a.r.OptionName(key, id)
	if !ok {
		a.c.issue(a.owner, "optionID", id, "unmapped-option-id")
	}
	return name, ok
}
func (a *capturedLookup) OptionId(key domain.RelationKey, name string) (string, bool) {
	id, ok := a.r.OptionId(key, name)
	if !ok {
		a.c.issue(a.owner, "optionName", name, "unmapped-or-colliding-option-name")
	}
	return id, ok
}
func (a *capturedLookup) ObjectName(id string) (string, bool)  { return a.r.ObjectName(id) }
func (a *capturedLookup) ObjectExists(id string) (bool, bool)  { return a.r.ObjectExists(id) }
func (a *capturedLookup) ObjectDeleted(id string) (bool, bool) { return a.r.ObjectDeleted(id) }
func (a *capturedLookup) TypeKeyById(id string) (string, bool) {
	key, ok := a.r.TypeKeyById(id)
	if !ok {
		a.c.issue(a.owner, "targetTypeID", id, "unmapped-target-type")
	}
	return key, ok
}
func (a *capturedLookup) TypeIdByKey(key string) (string, bool) {
	id, ok := a.r.TypeIdByKey(key)
	if !ok {
		a.c.issue(a.owner, "typeKey", key, "unmapped-type-key")
	}
	return id, ok
}

// RecordUnmapped retains a raw source field that cannot be closed over this captured set.
func (c *CapturedResolver) RecordUnmapped(source, field, target, reason string) {
	c.issue(source, field, target, reason)
}
