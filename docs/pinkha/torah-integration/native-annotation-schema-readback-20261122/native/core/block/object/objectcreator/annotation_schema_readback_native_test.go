package objectcreator_test

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/block/detailservice"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

// Only this new parent is selected. The retained original native fixture and
// transaction instrumentation are compiled unchanged; no old case is replayed.
func TestOtzariaAnnotationSchemaReadback(t *testing.T) {
	f := newNativeSchemaFixture(t)
	spc := f.regularSpace(t)
	definitions, err := annotationschema.Definitions()
	nativeSchemaNoError(t, err)
	if len(definitions) != 18 {
		t.Fatal("exactly one type and seventeen annotation relation definitions are required")
	}
	ids := make([]string, len(definitions))
	for i, definition := range definitions {
		if i == 0 {
			definition.Required.SetBool(bundle.RelationKeyIsHidden, true)
			definition.Required.SetBool(bundle.RelationKeyIsHiddenDiscovery, true)
		}
		// Each original create occurs once. Index readiness never repeats it.
		ids[i] = f.createSchema(t, spc, definition)
		waitAnnotationSchemaIndex(t, f, spc.Id(), definition, ids[i], false)
	}
	initialType := annotationSchemaReadback(t, f, spc, definitions[0])
	initialDetails, _ := initialType.CopyPersistedSchemaState()
	if initialDetails == nil {
		t.Fatal("actual created type has no persisted copyout")
	}
	initialHidden := domain.NewDetailsFromProto(initialDetails).GetStringList(bundle.RelationKeyRecommendedHiddenRelations)
	if len(initialHidden) == 0 {
		t.Fatal("original type fixture lacks its unrelated native default hidden properties")
	}
	properties := app.MustComponent[detailservice.Service](f.service.GetApp())
	add := func(t *testing.T, index int, visible bool) {
		t.Helper()
		result, err := properties.ObjectTypePropertyAdd(f.ctx, detailservice.ObjectTypePropertyAddRequest{
			ObjectTypeId: ids[0], Key: domain.RelationKey(definitions[index].Key.InternalKey()),
			Section: detailservice.TypePropertySectionHidden, EnableInViews: visible,
		})
		nativeSchemaNoError(t, err)
		if result.Key.String() != definitions[index].Key.InternalKey() || result.PropertyId != ids[index] {
			t.Fatal("original additive property API returned another native relation")
		}
	}
	remove := func(t *testing.T, index int) {
		t.Helper()
		_, err := properties.ObjectTypePropertyRemove(f.ctx, ids[0], domain.RelationKey(definitions[index].Key.InternalKey()))
		nativeSchemaNoError(t, err)
	}
	for i := 1; i < len(definitions); i++ {
		add(t, i, false)
	}

	t.Run("ActualDefinitionsHiddenAttachmentsAndViews", func(t *testing.T) {
		result := annotationSchemaObservation(t, f, spc.Id())
		if result.Disposition != annotationschema.MatchingObserved || len(result.Definitions) != 18 ||
			result.TypeLayout.Disposition != annotationschema.MatchingObserved || len(result.TypeLayout.ViewIDs) == 0 {
			t.Fatalf("actual original schema did not match: %+v", result)
		}
		for i, observation := range result.Definitions {
			if observation.Native.ObjectID != ids[i] || observation.Native.Disposition != objectcreator.FixedSchemaPersistedMatch ||
				observation.Index != annotationschema.IndexMatch {
				t.Fatal("a definition lacks exact original persisted and positive local index readback")
			}
		}
		for _, id := range initialHidden {
			found := false
			for _, actual := range result.TypeLayout.HiddenRelationIDs {
				found = found || actual == id
			}
			if !found {
				t.Fatal("unrelated original hidden property was lost")
			}
		}
		retainAnnotationSchemaReadback(t, result)
	})

	t.Run("CallerMutationCannotChangeCopiedNativeReadback", func(t *testing.T) {
		observation := annotationSchemaReadback(t, f, spc, definitions[0])
		beforeDetails, beforeBlocks := observation.CopyPersistedSchemaState()
		mutatedDetails, mutatedBlocks := observation.CopyPersistedSchemaState()
		delete(mutatedDetails.Fields, bundle.RelationKeyRecommendedHiddenRelations.String())
		if len(mutatedBlocks) == 0 || mutatedBlocks[0] == nil {
			t.Fatal("no actual original schema blocks were retained")
		}
		mutatedBlocks[0].Id = "caller-modified-copy"
		for _, block := range mutatedBlocks {
			if view := block.GetDataview(); view != nil && len(view.Views) > 0 && len(view.Views[0].Relations) > 0 {
				view.Views[0].Relations[0].Key = "caller-modified-column"
			}
		}
		afterDetails, afterBlocks := observation.CopyPersistedSchemaState()
		if !proto.Equal(beforeDetails, afterDetails) || len(beforeBlocks) != len(afterBlocks) {
			t.Fatal("caller changed the retained native readback")
		}
		for i := range beforeBlocks {
			if !proto.Equal(beforeBlocks[i], afterBlocks[i]) {
				t.Fatal("caller changed retained nested original protobuf block state")
			}
		}
		again := annotationSchemaReadback(t, f, spc, definitions[0])
		nativeDetails, nativeBlocks := again.CopyPersistedSchemaState()
		if !proto.Equal(beforeDetails, nativeDetails) || len(nativeBlocks) != len(beforeBlocks) {
			t.Fatal("copy mutation reached the original persisted schema")
		}
		for i := range beforeBlocks {
			if !proto.Equal(beforeBlocks[i], nativeBlocks[i]) {
				t.Fatal("copy mutation reached an original persisted block")
			}
		}
	})

	t.Run("ConflictCannotExposePersistedPayload", func(t *testing.T) {
		wrong := definitions[0]
		wrong.Required = definitions[0].Required.Copy()
		wrong.Required.SetString(bundle.RelationKeyName, "Different structural definition")
		result, err := f.observer.ObserveFixedSchema(f.ctx, spc, wrong)
		nativeSchemaNoError(t, err)
		details, blocks := result.CopyPersistedSchemaState()
		if result.Disposition != objectcreator.FixedSchemaPopulatedConflict || details != nil || blocks != nil {
			t.Fatal("conflicting original definition exposed a positive persisted payload")
		}
	})

	t.Run("ChangedRowsCannotExposePersistedPayload", func(t *testing.T) {
		db := spc.Storage().AnyStore()
		before := nativeSchemaReadRow(t, f.ctx, db, objecttree.CollName, ids[0])
		t.Cleanup(func() { nativeSchemaRestoreRow(t, f.ctx, db, objecttree.CollName, before) })
		trace := &nativeSchemaTraceDB{DB: db}
		trace.committed = func(index int, done bool) error {
			if !done {
				return errors.New("actual original ReadTx did not release")
			}
			if index != 1 {
				return nil
			}
			collection, err := db.OpenCollection(f.ctx, objecttree.CollName)
			if err != nil {
				return err
			}
			value, err := (&anyenc.Parser{}).Parse(before)
			if err != nil {
				return err
			}
			arena := &anyenc.Arena{}
			value.Set("annotation-copyout-negative", arena.NewString("changed-after-actual-first-snapshot"))
			return collection.UpdateOne(f.ctx, value)
		}
		result, err := f.observer.ObserveFixedSchema(f.ctx, nativeSchemaTracedSpace(spc, trace), definitions[0])
		details, blocks := result.CopyPersistedSchemaState()
		if !errors.Is(err, objectcreator.ErrFixedSchemaChanged) || result.Disposition != objectcreator.FixedSchemaChangedWhileReading ||
			details != nil || blocks != nil || trace.sequence.Load() != 2 {
			t.Fatalf("changed actual rows exposed a persisted payload: %d %v", result.Disposition, err)
		}
	})

	t.Run("FinalCancellationCannotExposePersistedPayload", func(t *testing.T) {
		ctx, cancel := context.WithCancel(f.ctx)
		defer cancel()
		trace := &nativeSchemaTraceDB{DB: spc.Storage().AnyStore()}
		trace.committed = func(index int, done bool) error {
			if !done {
				return errors.New("actual original ReadTx did not release")
			}
			if index == 2 {
				cancel()
			}
			return nil
		}
		result, err := f.observer.ObserveFixedSchema(ctx, nativeSchemaTracedSpace(spc, trace), definitions[0])
		details, blocks := result.CopyPersistedSchemaState()
		if !errors.Is(err, context.Canceled) || result.Disposition != objectcreator.FixedSchemaUnavailable ||
			details != nil || blocks != nil || trace.sequence.Load() != 2 {
			t.Fatalf("cancellation after both original readers exposed a payload: %d %v", result.Disposition, err)
		}
	})

	t.Run("MissingAttachmentRemainsIncomplete", func(t *testing.T) {
		remove(t, 1)
		t.Cleanup(func() { add(t, 1, false) })
		result := annotationSchemaObservation(t, f, spc.Id())
		if result.Disposition != annotationschema.Incomplete || len(result.Definitions) != 18 ||
			len(result.TypeLayout.MissingRelationKeys) != 1 || result.TypeLayout.MissingRelationKeys[0] != definitions[1].Key.InternalKey() {
			t.Fatalf("actual missing native attachment was accepted: %+v", result)
		}
	})

	t.Run("VisibleNativeMetadataColumnIsConflict", func(t *testing.T) {
		remove(t, 1)
		add(t, 1, true)
		t.Cleanup(func() { remove(t, 1); add(t, 1, false) })
		result := annotationSchemaObservation(t, f, spc.Id())
		if result.Disposition != annotationschema.Conflict || result.TypeLayout.Disposition != annotationschema.Conflict {
			t.Fatalf("actual visible metadata column was accepted: %+v", result)
		}
	})

	t.Run("UncertainRootIsPreservedWithoutCreation", func(t *testing.T) {
		empty := f.regularSpace(t)
		rootID := f.createRootOnly(t, empty, definitions[1])
		for attempt := 0; attempt < 2; attempt++ {
			result := annotationSchemaObservation(t, f, empty.Id())
			if result.Disposition != annotationschema.Incomplete || len(result.Definitions) != 18 ||
				result.Definitions[1].Native.Disposition != objectcreator.FixedSchemaRootOnlyIncomplete ||
				result.Definitions[1].Native.ObjectID != rootID {
				t.Fatalf("native root-only uncertainty was reset or repaired: %+v", result)
			}
			for i, entry := range result.Definitions {
				if i != 1 && entry.Native.Disposition != objectcreator.FixedSchemaLocallyMissing {
					t.Fatal("read-only observation created another native schema object")
				}
				details, blocks := entry.Native.CopyPersistedSchemaState()
				if details != nil || blocks != nil {
					t.Fatal("incomplete native schema exposed positive copied state")
				}
			}
		}
		tree := f.tree(t, empty, rootID)
		if tree.Len() != 1 {
			t.Fatal("native root-only state was initialized by observation")
		}
	})

	t.Run("OriginalNativeRetirementIsConflict", func(t *testing.T) {
		retiredSpace := f.regularSpace(t)
		definition := definitions[1]
		id := f.createSchema(t, retiredSpace, definition)
		waitAnnotationSchemaIndex(t, f, retiredSpace.Id(), definition, id, false)
		// The original native deletion path persists exactly this first phase
		// before closing the object. Keep the genuine derived tree and exercise
		// that durable marker independently of head/archive deletion status.
		err := retiredSpace.Do(id, func(b smartblock.SmartBlock) error {
			st := b.NewState()
			st.SetDetailAndBundledRelation(bundle.RelationKeyIsUninstalled, domain.Bool(true))
			return b.Apply(st)
		})
		nativeSchemaNoError(t, err)
		native := annotationSchemaReadback(t, f, retiredSpace, definition)
		details, _ := native.CopyPersistedSchemaState()
		if details == nil || !domain.NewDetailsFromProto(details).GetBool(bundle.RelationKeyIsUninstalled) {
			t.Fatal("actual original retirement marker was not persisted")
		}
		// Persisted native state and its positive local index projection have
		// separate completion boundaries. Wait only for that same actual row;
		// do not repeat Apply, delete, or create while indexing catches up.
		waitAnnotationSchemaIndex(t, f, retiredSpace.Id(), definition, id, true)
		result := annotationSchemaObservation(t, f, retiredSpace.Id())
		if result.Disposition != annotationschema.Conflict || len(result.Definitions) != 18 ||
			!result.Definitions[1].PersistedStateConflict || result.Definitions[1].Index != annotationschema.IndexConflict ||
			result.Definitions[1].Native.ObjectID != id {
			t.Fatalf("original persisted retirement or raw conflicting index row was ignored: %+v", result)
		}
	})
}

func waitAnnotationSchemaIndex(t *testing.T, f *nativeSchemaFixture, spaceID string, definition objectcreator.FixedSchemaDefinition, id string, requireRetired bool) {
	t.Helper()
	store := app.MustComponent[objectstore.ObjectStore](f.service.GetApp())
	key, value := bundle.RelationKeyUniqueKey, definition.Key.Marshal()
	if value != annotationschema.TypeUniqueKey {
		key, value = bundle.RelationKeyRelationKey, definition.Key.InternalKey()
	}
	deadline := time.Now().Add(30 * time.Second)
	for {
		rows, err := store.SpaceIndex(spaceID).QueryRaw(&database.Filters{FilterObj: database.FilterEq{
			Key: key, Cond: model.BlockContentDataviewFilter_Equal, Value: domain.String(value),
		}}, 2, 0)
		nativeSchemaNoError(t, err)
		if len(rows) > 1 {
			t.Fatal("actual fixture relation index is ambiguous")
		}
		if len(rows) == 1 {
			if rows[0].Details.GetString(bundle.RelationKeyId) != id {
				t.Fatal("actual fixture index names another object")
			}
			if !requireRetired {
				return
			}
			retired, present := rows[0].Details.TryBool(bundle.RelationKeyIsUninstalled)
			if present && retired {
				return
			}
		}
		if time.Now().After(deadline) {
			t.Fatal("actual original positive indexing did not finish; creation is not retried")
		}
		select {
		case <-f.ctx.Done():
			t.Fatal(f.ctx.Err())
		case <-time.After(50 * time.Millisecond):
		}
	}
}

func annotationSchemaReadback(t *testing.T, f *nativeSchemaFixture, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition) objectcreator.FixedSchemaObservation {
	t.Helper()
	for attempt := 1; attempt <= 3; attempt++ {
		value, err := f.observer.ObserveFixedSchema(f.ctx, spc, definition)
		t.Logf("original copyout observation: disposition=%d attempt=%d error=%v", value.Disposition, attempt, err)
		if errors.Is(err, objectcreator.ErrFixedSchemaChanged) && attempt < 3 {
			continue
		}
		nativeSchemaNoError(t, err)
		if value.Disposition != objectcreator.FixedSchemaPersistedMatch {
			t.Fatalf("native readback mismatch: %d", value.Disposition)
		}
		return value
	}
	panic("unreachable")
}

func annotationSchemaObservation(t *testing.T, f *nativeSchemaFixture, spaceID string) annotationschema.Observation {
	t.Helper()
	for attempt := 1; attempt <= 3; attempt++ {
		value, err := annotationschema.Observe(f.ctx, f.service, spaceID)
		t.Logf("original schema attempt: disposition=%s attempt=%d error=%v", value.Disposition, attempt, err)
		if errors.Is(err, objectcreator.ErrFixedSchemaChanged) && attempt < 3 {
			continue
		}
		nativeSchemaNoError(t, err)
		t.Logf("original native schema observation: disposition=%s definitions=%d views=%d attempt=%d", value.Disposition, len(value.Definitions), len(value.TypeLayout.ViewIDs), attempt)
		return value
	}
	panic("unreachable")
}

func retainAnnotationSchemaReadback(t *testing.T, result annotationschema.Observation) {
	t.Helper()
	directory := os.Getenv("OTZARIA_ANNOTATION_SCHEMA_EVIDENCE")
	if directory == "" {
		t.Fatal("dedicated native schema evidence directory is required")
	}
	definitions := make([]map[string]any, 0, len(result.Definitions))
	for _, entry := range result.Definitions {
		details, blocks := entry.Native.CopyPersistedSchemaState()
		if details == nil {
			t.Fatal("positive schema report lacks actual persisted details")
		}
		detailsBytes, err := proto.Marshal(details)
		nativeSchemaNoError(t, err)
		blockBytes := make([][]byte, len(blocks))
		for i, block := range blocks {
			if block == nil {
				t.Fatal("positive schema report contains nil native block")
			}
			blockBytes[i], err = proto.Marshal(block)
			nativeSchemaNoError(t, err)
		}
		definitions = append(definitions, map[string]any{
			"native_key": entry.Native.NativeKey.Marshal(), "object_id": entry.Native.ObjectID,
			"space_id": entry.Native.SpaceID, "account_identity": entry.Native.AccountIdentity,
			"acl_id": entry.Native.ACLID, "acl_head": entry.Native.ACLHead,
			"archive_id": entry.Native.ArchiveID, "archive_heads": entry.Native.ArchiveHeads,
			"persisted_heads": entry.Native.PersistedHeads, "disposition": entry.Native.Disposition,
			"index": entry.Index, "details_protobuf": detailsBytes, "blocks_protobuf": blockBytes,
		})
	}
	data, err := json.MarshalIndent(map[string]any{
		"schema": "otzaria-native-schema-readback/1", "protocol": annotationschema.Protocol,
		"scope":      "historical native schema observations; no create, registration receipt, identity, body or ACK authority",
		"process_id": os.Getpid(), "disposition": result.Disposition,
		"account_identity": result.AccountIdentity, "space_id": result.SpaceID,
		"definitions": definitions, "type_layout": result.TypeLayout,
	}, "", "  ")
	nativeSchemaNoError(t, err)
	file, err := os.OpenFile(filepath.Join(directory, "annotation-schema-readback.json"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	nativeSchemaNoError(t, err)
	_, writeErr := file.Write(append(data, '\n'))
	syncErr := file.Sync()
	closeErr := file.Close()
	nativeSchemaNoError(t, errors.Join(writeErr, syncErr, closeErr))
}
