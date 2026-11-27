package spaceobjects

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"slices"
	"sort"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/bookmarkcreate"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	anytype "github.com/anyproto/any-sync-sdk/internal/types/any"
	collectiontype "github.com/anyproto/any-sync-sdk/internal/types/collection"
	typetype "github.com/anyproto/any-sync-sdk/internal/types/type"
)

const maxBookmarkDefinitionBytes = 128 * 1024

// ReadBookmarkCreateFrame performs one discovery read, followed by a complete
// snapshot. The second read derives and checks the owner again; a changed
// owner is a refusal, never an independently combined descriptor snapshot.
func (s *Store) ReadBookmarkCreateFrame(ctx context.Context, typeID string, requested []string) (bookmarkcreate.Response, error) {
	var out bookmarkcreate.Response
	if s == nil || s.signKey == nil || !bookmarkcreate.ValidObjectID(typeID) || len(requested) > bookmarkcreate.MaxCollections || s.staticOwnerKind(typeID) != "" {
		return out, bookmarkcreate.ErrInvalid
	}
	for _, id := range requested {
		if !bookmarkcreate.ValidObjectID(id) || id == "bin" || id == "template" {
			return out, bookmarkcreate.ErrInvalid
		}
	}
	var ownerID string
	err := s.nativeReadSnapshot(ctx, []string{typeID}, func(view crdt.NativeReadView) error {
		raw, err := view.Lookup(typeID, "objects", typeID)
		if err != nil {
			return err
		}
		ownerID, _, err = bookmarkLayout(raw, s.spaceId, typeID)
		return err
	}, s.bookmarkExistingGeneration)
	if err != nil {
		return out, err
	}
	collections, err := bookmarkcreate.NormalizeCollections(requested, ownerID)
	if err != nil {
		return out, err
	}
	ids, _, err := s.bookmarkDependencyIDs(typeID, collections)
	if err != nil {
		return out, err
	}
	err = s.nativeReadSnapshot(ctx, ids, func(view crdt.NativeReadView) error {
		native, ok := view.(snapshotReadView)
		if !ok {
			return bookmarkcreate.ErrIneligible
		}
		frame, err := native.lockedReadView.bookmarkFrame(typeID, collections)
		if err != nil {
			return err
		}
		if frame.PropertyOwnerID != ownerID || frame.StoreGeneration != view.ReadStamp().StoreGeneration {
			return bookmarkcreate.ErrChanged
		}
		// The captured projection and all dependency heads belong to this same
		// read transaction and the complete native tree lock set.
		if !equalBookmarkHeads(frame.Dependencies, view.ReadStamp().TreeHeads) {
			return bookmarkcreate.ErrChanged
		}
		token, err := bookmarkcreate.Encode(frame)
		if err != nil {
			return err
		}
		out = bookmarkcreate.Response{Contract: bookmarkcreate.Contract, Version: 1,
			AccountID: frame.AccountID, SpaceID: frame.SpaceID, TypeID: frame.TypeID,
			Collections: append([]string{}, frame.Collections...), PropertyOwnerID: frame.PropertyOwnerID,
			PropertyID: frame.PropertyID, CanWrite: view.CanWrite(), Frame: token}
		return nil
	}, s.bookmarkExistingGeneration)
	if err != nil {
		return bookmarkcreate.Response{}, err
	}
	return out, nil
}

// CheckBookmarkCreateFrame is the pre-root optimization only. The bootstrap's
// native locked check below is decisive; no successful preflight removes it.
func (s *Store) CheckBookmarkCreateFrame(ctx context.Context, expected bookmarkcreate.Frame) error {
	if err := expected.Validate(); err != nil {
		return err
	}
	current, err := s.ReadBookmarkCreateFrame(ctx, expected.TypeID, expected.Collections)
	if err != nil {
		return err
	}
	token, err := bookmarkcreate.Encode(expected)
	if err != nil {
		return err
	}
	if current.Frame != token {
		return bookmarkcreate.ErrChanged
	}
	return nil
}

func equalBookmarkHeads(dependencies []bookmarkcreate.Dependency, heads map[string][]string) bool {
	if len(dependencies) != len(heads) {
		return false
	}
	for _, d := range dependencies {
		if !slices.Equal(d.Heads, heads[d.ObjectID]) {
			return false
		}
	}
	return true
}

func (s *Store) bookmarkDependencyIDs(typeID string, collections []string) ([]string, []bookmarkcreate.StaticOwner, error) {
	if s.staticOwnerKind(typeID) != "" {
		return nil, nil, bookmarkcreate.ErrIneligible
	}
	dynamic := []string{typeID}
	statics := []bookmarkcreate.StaticOwner{}
	for _, id := range collections {
		if id == typeID || id == "bin" || id == "template" {
			return nil, nil, bookmarkcreate.ErrIneligible
		}
		switch s.staticOwnerKind(id) {
		case "":
			dynamic = append(dynamic, id)
		case "collection":
			found := false
			for _, collection := range s.extCollections {
				if collection.Id != id {
					continue
				}
				digest, err := bookmarkJSONHash(collection)
				if err != nil {
					return nil, nil, err
				}
				statics = append(statics, bookmarkcreate.StaticOwner{ObjectID: id, SHA256: digest})
				found = true
				break
			}
			if !found {
				return nil, nil, bookmarkcreate.ErrIneligible
			}
		default:
			return nil, nil, bookmarkcreate.ErrIneligible
		}
	}
	sort.Strings(dynamic)
	if len(dynamic) > bookmarkcreate.MaxDependencies {
		return nil, nil, bookmarkcreate.ErrInvalid
	}
	return dynamic, statics, nil
}

func bookmarkJSONHash(value any) (string, error) {
	raw, err := json.Marshal(value)
	if err != nil || len(raw) > maxBookmarkDefinitionBytes {
		return "", bookmarkcreate.ErrIneligible
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func bookmarkRowHash(value *anyenc.Value) (string, error) {
	if value == nil {
		return "", bookmarkcreate.ErrIneligible
	}
	raw := value.String()
	if len(raw) > maxBookmarkDefinitionBytes {
		return "", bookmarkcreate.ErrIneligible
	}
	var decoded any
	decoder := json.NewDecoder(bytes.NewBufferString(raw))
	decoder.UseNumber()
	if err := decoder.Decode(&decoded); err != nil {
		return "", bookmarkcreate.ErrIneligible
	}
	return bookmarkJSONHash(decoded)
}

// Generation's general LoadOrInit route can write when metadata is missing.
// This condition instead requires an existing epoch and reads it only. The
// original key is shared with native changefeed/purge, not a parallel store ID.
func (s *Store) bookmarkExistingGeneration(ctx context.Context) (string, error) {
	collection, err := s.db.Collection(ctx, crdt.MetaCollectionName)
	if err != nil {
		return "", err
	}
	doc, err := collection.FindId(ctx, crdt.SpaceMetaKey(s.spaceId))
	if err != nil {
		return "", err
	}
	row := doc.Value()
	if row == nil || row.Get("gen") == nil || row.Get("gen").Type() != anyenc.TypeString ||
		!bookmarkcreate.ValidText(row.GetString("gen"), bookmarkcreate.MaxGenerationBytes) {
		return "", bookmarkcreate.ErrChanged
	}
	return row.GetString("gen"), nil
}

func bookmarkExactObject(value *anyenc.Value, required, optional []string) bool {
	if value == nil || value.Type() != anyenc.TypeObject {
		return false
	}
	for _, key := range required {
		if value.Get(key) == nil {
			return false
		}
	}
	obj, err := value.Object()
	if err != nil {
		return false
	}
	valid := true
	obj.Visit(func(key []byte, _ *anyenc.Value) {
		if !slices.Contains(required, string(key)) && !slices.Contains(optional, string(key)) {
			valid = false
		}
	})
	return valid
}

func bookmarkLayout(row *anyenc.Value, spaceID, typeID string) (string, string, error) {
	if row == nil || row.Get(crdt.DeletedAtField) != nil || row.GetString("id") != typeID ||
		row.GetString("spaceId") != spaceID || row.GetString("any", "type") != typetype.MetaTypeMarker ||
		row.GetString("type", "layout", "type") != "bookmark" {
		return "", "", bookmarkcreate.ErrIneligible
	}
	d := row.Get("type", "layout", "config", "pinkhaHeart")
	if !bookmarkExactObject(d, []string{"contract", "sourceRecommendedLayout", "propertyOwnerId", "recommended", "featured", "hidden", "files", "sourceURL"}, []string{"definitionHidden"}) ||
		d.GetString("contract") != bookmarkcreate.PresentationContract || d.Get("sourceRecommendedLayout").Type() != anyenc.TypeNumber ||
		d.GetFloat64("sourceRecommendedLayout") != 11 {
		return "", "", bookmarkcreate.ErrIneligible
	}
	owner := d.GetString("propertyOwnerId")
	url := d.Get("sourceURL")
	if !bookmarkcreate.ValidObjectID(owner) || owner == "any" || owner == typeID ||
		!bookmarkExactObject(url, []string{"ownerId", "propertyId"}, nil) || url.GetString("ownerId") != owner ||
		!bookmarkcreate.ValidID(url.GetString("propertyId")) {
		return "", "", bookmarkcreate.ErrIneligible
	}
	return owner, url.GetString("propertyId"), nil
}

func (v lockedReadView) bookmarkFrame(typeID string, collections []string) (bookmarkcreate.Frame, error) {
	var frame bookmarkcreate.Frame
	if v.store == nil || v.store.signKey == nil {
		return frame, bookmarkcreate.ErrIneligible
	}
	ids, statics, err := v.store.bookmarkDependencyIDs(typeID, collections)
	if err != nil {
		return frame, err
	}
	if len(v.objects) != len(ids) && (v.carrier == nil || len(v.objects) != len(ids)+1) {
		return frame, bookmarkcreate.ErrChanged
	}
	for id := range v.objects {
		if (v.carrier == nil || id != v.carrier.Id()) && !slices.Contains(ids, id) {
			return frame, bookmarkcreate.ErrChanged
		}
	}
	for _, id := range ids {
		kind, err := v.definitionKind(id)
		if err != nil {
			return frame, err
		}
		if (id == typeID && kind != "type") || (id != typeID && kind != "collection") {
			return frame, bookmarkcreate.ErrIneligible
		}
	}
	typeRow, err := v.Lookup(typeID, "objects", typeID)
	if err != nil {
		return frame, err
	}
	ownerID, propertyID, err := bookmarkLayout(typeRow, v.store.spaceId, typeID)
	if err != nil {
		return frame, err
	}
	if !slices.Contains(collections, ownerID) || v.store.staticOwnerKind(ownerID) != "" || v.objects[ownerID] == nil {
		return frame, bookmarkcreate.ErrChanged
	}
	eligible, err := v.TypeDeclaresDataset(typeID, "editor", "editor_blocks", true)
	if err != nil {
		return frame, err
	}
	if !eligible {
		return frame, bookmarkcreate.ErrIneligible
	}
	ownerRow, err := v.Lookup(ownerID, "objects", ownerID)
	if err != nil {
		return frame, err
	}
	if ownerRow == nil || ownerRow.GetString("any", "type") != collectiontype.MetaMarker {
		return frame, bookmarkcreate.ErrIneligible
	}
	definitions, err := v.Query(ownerID, typetype.DatasetPropertyDefs, nil, 4097)
	if err != nil {
		return frame, err
	}
	if len(definitions) > 4096 {
		return frame, bookmarkcreate.ErrIneligible
	}
	byID := make(map[string]*anyenc.Value, len(definitions))
	for _, row := range definitions {
		if row == nil || row.Get(crdt.DeletedAtField) != nil {
			continue
		}
		id := row.GetString("id")
		if !bookmarkcreate.ValidID(id) || byID[id] != nil {
			return frame, bookmarkcreate.ErrIneligible
		}
		byID[id] = row
	}
	property := byID[propertyID]
	if property == nil || property.GetString(typetype.FieldKind) != "string" ||
		(property.Get(typetype.FieldScope) != nil && property.GetString(typetype.FieldScope) != "synced") ||
		property.GetString(typetype.FieldXFormat, "type") != "url" {
		return frame, bookmarkcreate.ErrIneligible
	}
	// Existing import provenance is part of the current selected descriptor,
	// never a claim that ordinary creation replays original Heart history.
	source := property.Get(typetype.FieldXFormat, "pinkhaHeart")
	if source == nil || source.GetString("sourceUniqueKey") != "rel-source" || source.GetString("relationKey") != "source" ||
		!bookmarkcreate.ValidID(source.GetString("sourceObjectID")) {
		return frame, bookmarkcreate.ErrIneligible
	}
	descriptor := typeRow.Get("type", "layout", "config", "pinkhaHeart")
	visible := false
	for _, field := range []string{"recommended", "featured", "hidden", "files", "definitionHidden"} {
		values := descriptor.Get(field)
		if values == nil && field == "definitionHidden" {
			continue
		}
		if values == nil || values.Type() != anyenc.TypeArray || len(values.GetArray()) > 512 {
			return frame, bookmarkcreate.ErrIneligible
		}
		seen := map[string]bool{}
		for _, address := range values.GetArray() {
			if !bookmarkExactObject(address, []string{"ownerId", "propertyId"}, nil) {
				return frame, bookmarkcreate.ErrIneligible
			}
			owner, id := address.GetString("ownerId"), address.GetString("propertyId")
			if !bookmarkcreate.ValidObjectID(owner) || !bookmarkcreate.ValidID(id) {
				return frame, bookmarkcreate.ErrIneligible
			}
			key := owner + "\x00" + id
			if seen[key] {
				return frame, bookmarkcreate.ErrIneligible
			}
			seen[key] = true
			if owner == ownerID {
				if byID[id] == nil {
					return frame, bookmarkcreate.ErrIneligible
				}
			} else if owner == "any" {
				found := false
				for _, p := range anytype.Properties {
					if p.Id == id {
						found = true
						break
					}
				}
				if !found {
					return frame, bookmarkcreate.ErrIneligible
				}
			} else {
				return frame, bookmarkcreate.ErrIneligible
			}
			if owner == ownerID && id == propertyID && (field == "recommended" || field == "featured") {
				visible = true
			}
		}
	}
	if !visible {
		return frame, bookmarkcreate.ErrIneligible
	}
	typeHash, err := bookmarkRowHash(typeRow)
	if err != nil {
		return frame, err
	}
	ownerHash, err := bookmarkRowHash(ownerRow)
	if err != nil {
		return frame, err
	}
	propertyHash, err := bookmarkRowHash(property)
	if err != nil {
		return frame, err
	}
	generation, err := v.store.bookmarkExistingGeneration(v.ctx)
	if err != nil {
		return frame, err
	}
	dependencies := make([]bookmarkcreate.Dependency, 0, len(ids))
	for _, id := range ids {
		heads := append([]string{}, v.objects[id].Tree().Heads()...)
		sort.Strings(heads)
		dependencies = append(dependencies, bookmarkcreate.Dependency{ObjectID: id, Heads: heads})
	}
	frame = bookmarkcreate.Frame{Contract: bookmarkcreate.Contract, Version: 1, AccountID: v.store.signKey.GetPublic().Account(),
		SpaceID: v.store.spaceId, StoreGeneration: generation, TypeID: typeID, Collections: append([]string{}, collections...),
		PropertyOwnerID: ownerID, PropertyID: propertyID, TypeSHA256: typeHash, OwnerSHA256: ownerHash,
		PropertySHA256: propertyHash, Dependencies: dependencies, StaticOwners: statics}
	return frame, frame.Validate()
}

// validateBookmarkCreate runs inside the ORIGINAL complete definition lock
// set, before the current-writer durable append. It never reloads a tree,
// reacquires a tree lock or calls an unrestricted SDK descriptor API.
func (v lockedReadView) validateBookmarkCreate(ch *crdt.Change, typeID string, collections []string) error {
	expected := ch.NativeBookmarkCreateFrame
	if expected == nil || ch.Dataset != "objects" || len(ch.Records) != 1 || !ch.Records[0].Upsert ||
		v.carrier == nil || ch.Records[0].Id != v.carrier.Id() || typeID != expected.TypeID ||
		!slices.Equal(collections, expected.Collections) {
		return bookmarkcreate.ErrChanged
	}
	actual, err := v.bookmarkFrame(typeID, collections)
	if err != nil {
		return err
	}
	want, err := bookmarkcreate.Encode(*expected)
	if err != nil {
		return err
	}
	got, err := bookmarkcreate.Encode(actual)
	if err != nil {
		return err
	}
	if want != got {
		return bookmarkcreate.ErrChanged
	}
	for _, owner := range ch.NativeDefinitionOwners {
		if owner != "any" && owner != typeID && !slices.Contains(collections, owner) {
			return bookmarkcreate.ErrInvalid
		}
	}
	urlCount := 0
	for _, op := range ch.Records[0].Ops {
		if op.Type != crdt.OpSet || len(op.Path) != 0 || op.Payload == nil {
			return bookmarkcreate.ErrInvalid
		}
		if value := op.Payload.Get(expected.PropertyOwnerID + "." + expected.PropertyID); value != nil {
			if value.Type() != anyenc.TypeString {
				return bookmarkcreate.ErrInvalid
			}
			urlCount++
		}
	}
	if urlCount != 1 {
		return bookmarkcreate.ErrInvalid
	}
	return nil
}
