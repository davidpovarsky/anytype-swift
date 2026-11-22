package objectcreator_test

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"slices"
	"sync"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/gogo/protobuf/proto"
	"github.com/gogo/protobuf/types"

	"github.com/anyproto/anytype-heart/core/block/detailservice"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/template"
	"github.com/anyproto/anytype-heart/core/block/object/objectcache"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

func TestOtzariaAnnotationSchemaRegistration(t *testing.T) {
	f := newNativeSchemaFixture(t)
	definitions, err := annotationschema.Definitions()
	nativeSchemaNoError(t, err)
	accountID := registrationAccount(f)

	t.Run("ActualRegistrationAndStrictReadback", func(t *testing.T) {
		spc := f.regularSpace(t)
		result, phases := registrationComplete(t, f, spc)
		created := 0
		for _, phase := range phases {
			for _, creation := range phase.Creations {
				if creation.Invoked {
					created++
				}
			}
		}
		if created != 18 || result.Observation.Disposition != annotationschema.MatchingObserved ||
			len(result.Observation.Definitions) != 18 || len(result.Observation.TypeLayout.ViewIDs) == 0 {
			t.Fatalf("registration lacks eighteen actual native definitions: creates=%d result=%+v", created, result)
		}
		retainAnnotationSchemaReadback(t, result.Observation)
		retainRegistrationPhases(t, phases)
	})

	t.Run("RepeatedRegistrationDoesNotMutate", func(t *testing.T) {
		spc := f.regularSpace(t)
		ready, _ := registrationComplete(t, f, spc)
		again, err := annotationschema.Register(f.ctx, f.service, accountID, spc.Id())
		nativeSchemaNoError(t, err)
		if len(again.Creations) != 0 || again.TypeApplyInvoked || again.Observation.Disposition != annotationschema.MatchingObserved {
			t.Fatal("already matching native schema was mutated")
		}
		for i, entry := range ready.Observation.Definitions {
			registrationSameNative(t, entry.Native, again.Observation.Definitions[i].Native)
		}
	})

	t.Run("MissingAttachmentUsesOneNativeApply", func(t *testing.T) {
		spc := f.regularSpace(t)
		ready, _ := registrationComplete(t, f, spc)
		typeID := ready.Observation.Definitions[0].Native.ObjectID
		retainMissingAttachmentState(t, f, spc, definitions[0], typeID, "00-registered")
		unrelated := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "registrationunrelated")
		unrelatedID := f.createSchema(t, spc, unrelated)
		waitAnnotationSchemaIndex(t, f, spc.Id(), unrelated, unrelatedID, false)
		properties := app.MustComponent[detailservice.Service](f.service.GetApp())
		_, err := properties.ObjectTypePropertyAdd(f.ctx, detailservice.ObjectTypePropertyAddRequest{
			ObjectTypeId: typeID, Key: domain.RelationKey(unrelated.Key.InternalKey()),
			Section: detailservice.TypePropertySectionRecommended, EnableInViews: true,
		})
		nativeSchemaNoError(t, err)
		retainMissingAttachmentState(t, f, spc, definitions[0], typeID, "01-unrelated-property-added")
		nativeSchemaNoError(t, spc.DoCtx(f.ctx, typeID, func(object smartblock.SmartBlock) error {
			st := object.NewState()
			st.SetDetailAndBundledRelation(bundle.RelationKeyDescription, domain.String("preserve this unrelated native description"))
			block := template.TypeDataviewBlock(st).Copy()
			dv := block.Model().GetDataview()
			view := proto.Clone(dv.Views[0]).(*model.BlockContentDataviewView)
			view.Id, view.Name = "native-schema-preserved-view", "Preserved native view"
			for _, column := range view.Relations {
				if column.Key == unrelated.Key.InternalKey() {
					column.Width, column.IsVisible = 193, true
				}
			}
			dv.Views = append(dv.Views, view)
			st.Set(block)
			return object.Apply(st)
		}))
		retainMissingAttachmentState(t, f, spc, definitions[0], typeID, "02-second-view-applied")
		_, err = properties.ObjectTypePropertyRemove(f.ctx, typeID, domain.RelationKey(definitions[1].Key.InternalKey()))
		nativeSchemaNoError(t, err)
		retainMissingAttachmentState(t, f, spc, definitions[0], typeID, "03-metadata-property-removed")
		before := annotationSchemaReadback(t, f, spc, definitions[0])
		retainMissingAttachmentState(t, f, spc, definitions[0], typeID, "04-before-registration-attempt")
		defer retainMissingAttachmentState(t, f, spc, definitions[0], typeID, "05-after-registration-attempt")
		result, phases := registrationComplete(t, f, spc)
		applies := 0
		for _, phase := range phases {
			if len(phase.Creations) != 0 {
				t.Fatal("missing attachment recreated an existing native definition")
			}
			if phase.TypeApplyInvoked {
				applies++
				if !phase.TypeApplyReturned {
					t.Fatal("native missing-property Apply did not return success")
				}
			}
		}
		if applies != 1 || len(result.Observation.TypeLayout.ViewIDs) != 2 {
			t.Fatal("registration did not use one native Apply while preserving both original views")
		}
		after := result.Observation.Definitions[0].Native
		beforeDetails, beforeBlocks := before.CopyPersistedSchemaState()
		afterDetails, afterBlocks := after.CopyPersistedSchemaState()
		key, propertyID := definitions[1].Key.InternalKey(), result.Observation.Definitions[1].Native.ObjectID
		registrationRemoveExpectedAddition(beforeDetails, beforeBlocks, key, propertyID)
		registrationRemoveExpectedAddition(afterDetails, afterBlocks, key, propertyID)
		if !proto.Equal(beforeDetails, afterDetails) || !registrationBlocksEqual(beforeBlocks, afterBlocks) {
			t.Fatal("registration changed unrelated persisted native details, lists, columns or views")
		}
	})

	t.Run("VisibleColumnRemainsConflict", func(t *testing.T) {
		spc := f.regularSpace(t)
		ready, _ := registrationComplete(t, f, spc)
		typeID := ready.Observation.Definitions[0].Native.ObjectID
		properties := app.MustComponent[detailservice.Service](f.service.GetApp())
		_, err := properties.ObjectTypePropertyRemove(f.ctx, typeID, domain.RelationKey(definitions[1].Key.InternalKey()))
		nativeSchemaNoError(t, err)
		_, err = properties.ObjectTypePropertyAdd(f.ctx, detailservice.ObjectTypePropertyAddRequest{
			ObjectTypeId: typeID, Key: domain.RelationKey(definitions[1].Key.InternalKey()),
			Section: detailservice.TypePropertySectionHidden, EnableInViews: true,
		})
		nativeSchemaNoError(t, err)
		before := annotationSchemaReadback(t, f, spc, definitions[0])
		result, err := annotationschema.Register(f.ctx, f.service, accountID, spc.Id())
		if !errors.Is(err, annotationschema.ErrRegistrationConflict) || len(result.Creations) != 0 || result.TypeApplyInvoked {
			t.Fatalf("visible existing metadata was silently repaired: %v %+v", err, result)
		}
		registrationSameNative(t, before, annotationSchemaReadback(t, f, spc, definitions[0]))
	})

	t.Run("RootOnlyStopsAllCreation", func(t *testing.T) {
		spc := f.regularSpace(t)
		id := f.createRootOnly(t, spc, definitions[7])
		before := nativeSchemaReadRow(t, f.ctx, spc.Storage().AnyStore(), objecttree.CollName, id)
		result, err := annotationschema.Register(f.ctx, f.service, accountID, spc.Id())
		if !errors.Is(err, annotationschema.ErrRegistrationUnresolved) || len(result.Creations) != 0 || result.TypeApplyInvoked {
			t.Fatalf("uncertain original root admitted registration: %v %+v", err, result)
		}
		nativeSchemaRowsEqual(t, f.ctx, spc.Storage().AnyStore(), objecttree.CollName, id, before)
		registrationOnlyExistingRoots(t, f, spc, map[string]bool{id: true})
	})

	t.Run("DifferentActiveAccountIsRefused", func(t *testing.T) {
		spc := f.regularSpace(t)
		other := newNativeSchemaFixture(t)
		result, err := annotationschema.Register(f.ctx, f.service, registrationAccount(other), spc.Id())
		if !errors.Is(err, annotationschema.ErrRuntimeChanged) || len(result.Creations) != 0 || result.TypeApplyInvoked {
			t.Fatalf("another real native account was admitted: %v", err)
		}
		registrationOnlyExistingRoots(t, f, spc, nil)
	})

	t.Run("CancelledBeforeAdmissionWritesNothing", func(t *testing.T) {
		spc := f.regularSpace(t)
		ctx, cancel := context.WithCancel(f.ctx)
		cancel()
		result, err := annotationschema.Register(ctx, f.service, accountID, spc.Id())
		if !errors.Is(err, context.Canceled) || result.AppAdmitted || len(result.Creations) != 0 || result.TypeApplyInvoked {
			t.Fatalf("cancelled registration entered native work: %v", err)
		}
		registrationOnlyExistingRoots(t, f, spc, nil)
	})

	t.Run("NativeRootCollisionDoesNotInitialize", func(t *testing.T) {
		spc := f.regularSpace(t)
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "registrationrootcollision")
		var winnerID string
		var winnerRow []byte
		interleaved := &registrationCollisionSpace{Space: spc, key: definition.Key.Marshal(), before: func() {
			winnerID = f.createRootOnly(t, spc, definition)
			winnerRow = nativeSchemaReadRow(t, f.ctx, spc.Storage().AnyStore(), objecttree.CollName, winnerID)
		}}
		creator := f.creator.(objectcreator.FixedSchemaCreator)
		result, err := creator.CreateFixedSchemaOnce(f.ctx, interleaved, accountID, definition)
		if !errors.Is(err, treestorage.ErrTreeExists) || !result.Invoked || result.ReturnedObjectID != "" ||
			result.After.Disposition != objectcreator.FixedSchemaRootOnlyIncomplete || interleaved.calls != 1 {
			t.Fatalf("native fixed-root collision was hidden or retried: %v %+v", err, result)
		}
		nativeSchemaRowsEqual(t, f.ctx, spc.Storage().AnyStore(), objecttree.CollName, winnerID, winnerRow)
	})

	t.Run("NativePopulatedCollisionDoesNotOverwrite", func(t *testing.T) {
		spc := f.regularSpace(t)
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "registrationpopulatedcollision")
		var winner objectcreator.FixedSchemaObservation
		interleaved := &registrationCollisionSpace{Space: spc, key: definition.Key.Marshal(), before: func() {
			id := f.createSchema(t, spc, definition)
			waitAnnotationSchemaIndex(t, f, spc.Id(), definition, id, false)
			winner = annotationSchemaReadback(t, f, spc, definition)
		}}
		creator := f.creator.(objectcreator.FixedSchemaCreator)
		result, err := creator.CreateFixedSchemaOnce(f.ctx, interleaved, accountID, definition)
		if !errors.Is(err, treestorage.ErrTreeExists) || !result.Invoked || result.ReturnedObjectID != "" ||
			result.After.Disposition != objectcreator.FixedSchemaPersistedMatch || interleaved.calls != 1 {
			t.Fatalf("native populated collision was hidden or overwritten: %v %+v", err, result)
		}
		registrationSameNative(t, winner, result.After)
	})

	t.Run("NativeReaderRoleCannotRegister", func(t *testing.T) { registrationReaderRole(t, f) })
	t.Run("QueuedAccountStopDrainsWithCancellation", func(t *testing.T) { registrationQueuedLifecycle(t, true) })
	t.Run("QueuedAccountSelectDrainsNativeApply", func(t *testing.T) { registrationQueuedLifecycle(t, false) })
	t.Run("StopCancelsQueuedSelectWithoutDraining", func(t *testing.T) { registrationStopDuringQueuedSelect(t) })
}

func registrationAccount(f *nativeSchemaFixture) string {
	return app.MustComponent[accountservice.Service](f.service.GetApp()).Account().SignKey.GetPublic().Account()
}

func registrationComplete(t *testing.T, f *nativeSchemaFixture, spc clientspace.Space) (annotationschema.Registration, []annotationschema.Registration) {
	t.Helper()
	seen := make(map[string]bool)
	var phases []annotationschema.Registration
	for phase := 0; phase < 21; phase++ {
		result, err := annotationschema.Register(f.ctx, f.service, registrationAccount(f), spc.Id())
		phases = append(phases, result)
		t.Logf("native registration phase=%d creates=%d apply=%t returned=%t disposition=%s error=%v", phase+1,
			len(result.Creations), result.TypeApplyInvoked, result.TypeApplyReturned, result.Observation.Disposition, err)
		for _, creation := range result.Creations {
			if !creation.Invoked {
				continue
			}
			id := creation.Before.ObjectID
			if id == "" || seen[id] {
				t.Fatal("the product repeated a native create for the same fixed object")
			}
			seen[id] = true
			if creation.ReturnedObjectID != id {
				t.Fatalf("uncertain original create must not be retried: %v", err)
			}
		}
		if err == nil {
			if result.Observation.Disposition != annotationschema.MatchingObserved {
				t.Fatal("successful registration lacks full strict native readback")
			}
			return result, phases
		}
		if !errors.Is(err, objectcreator.ErrFixedSchemaChanged) && !errors.Is(err, annotationschema.ErrRegistrationUnresolved) {
			t.Fatalf("registration cannot resume after this failure: %v", err)
		}
		// Explicit fixture readiness precedes a new bounded registration phase.
		// Only readback repeats. Every already-created ID is independently seen
		// as complete before later phases can install untouched definitions.
		registrationWaitReadiness(t, f, spc.Id(), seen)
	}
	t.Fatal("bounded registration phases did not complete")
	return annotationschema.Registration{}, nil
}

func registrationWaitReadiness(t *testing.T, f *nativeSchemaFixture, spaceID string, known map[string]bool) {
	t.Helper()
	deadline := time.Now().Add(30 * time.Second)
	for {
		value, err := annotationschema.Observe(f.ctx, f.service, spaceID)
		ready := err == nil && value.Disposition != annotationschema.Conflict && len(value.Definitions) == 18
		if err != nil && !errors.Is(err, objectcreator.ErrFixedSchemaChanged) {
			t.Fatalf("native readiness failed: %v", err)
		}
		if err == nil && value.Disposition == annotationschema.Conflict {
			t.Fatal("native registration readiness found a conflict")
		}
		for _, entry := range value.Definitions {
			if known[entry.Native.ObjectID] && entry.Native.Disposition != objectcreator.FixedSchemaPersistedMatch {
				ready = false
			}
			if entry.Native.Disposition == objectcreator.FixedSchemaRootOnlyIncomplete || entry.Native.Disposition == objectcreator.FixedSchemaPopulatedConflict {
				t.Fatal("native uncertainty/conflict cannot be repaired by another create")
			}
			if entry.Native.Disposition == objectcreator.FixedSchemaPersistedMatch && entry.Index != annotationschema.IndexMatch {
				ready = false
			}
		}
		if ready {
			return
		}
		if time.Now().After(deadline) {
			t.Fatal("read-only native schema readiness did not converge")
		}
		select {
		case <-f.ctx.Done():
			t.Fatal(f.ctx.Err())
		case <-time.After(100 * time.Millisecond):
		}
	}
}

func registrationOnlyExistingRoots(t *testing.T, f *nativeSchemaFixture, spc clientspace.Space, wanted map[string]bool) {
	t.Helper()
	definitions, err := annotationschema.Definitions()
	nativeSchemaNoError(t, err)
	for _, definition := range definitions {
		id, err := spc.DeriveObjectID(f.ctx, definition.Key)
		nativeSchemaNoError(t, err)
		has, err := spc.Storage().HasTree(f.ctx, id)
		nativeSchemaNoError(t, err)
		if has != wanted[id] {
			t.Fatal("unexpected local native schema root creation")
		}
	}
}

func registrationSameNative(t *testing.T, before, after objectcreator.FixedSchemaObservation) {
	t.Helper()
	bd, bb := before.CopyPersistedSchemaState()
	ad, ab := after.CopyPersistedSchemaState()
	if before.ObjectID != after.ObjectID || !slices.Equal(before.PersistedHeads, after.PersistedHeads) ||
		!proto.Equal(bd, ad) || !registrationBlocksEqual(bb, ab) {
		t.Fatal("native schema persisted heads or complete content changed")
	}
}

func registrationBlocksEqual(before, after []*model.Block) bool {
	if len(before) != len(after) {
		return false
	}
	items := make(map[string]*model.Block, len(before))
	for _, block := range before {
		if block == nil || items[block.Id] != nil {
			return false
		}
		items[block.Id] = block
	}
	for _, block := range after {
		if block == nil || !proto.Equal(block, items[block.Id]) {
			return false
		}
		delete(items, block.Id)
	}
	return len(items) == 0
}

func registrationRemoveExpectedAddition(details *types.Struct, blocks []*model.Block, key, id string) {
	values := details.Fields[bundle.RelationKeyRecommendedHiddenRelations.String()].GetListValue()
	filtered := values.Values[:0]
	for _, value := range values.Values {
		if value.GetStringValue() != id {
			filtered = append(filtered, value)
		}
	}
	values.Values = filtered
	for _, block := range blocks {
		if dv := block.GetDataview(); dv != nil {
			links := dv.RelationLinks[:0]
			for _, link := range dv.RelationLinks {
				if link.Key != key {
					links = append(links, link)
				}
			}
			dv.RelationLinks = links
			for _, view := range dv.Views {
				columns := view.Relations[:0]
				for _, column := range view.Relations {
					if column.Key != key {
						columns = append(columns, column)
					}
				}
				view.Relations = columns
			}
		}
	}
}

type registrationCollisionSpace struct {
	clientspace.Space
	key    string
	before func()
	once   sync.Once
	calls  int
}

func (s *registrationCollisionSpace) DeriveTreeObject(ctx context.Context, params objectcache.TreeDerivationParams) (smartblock.SmartBlock, error) {
	if params.Key.Marshal() == s.key {
		s.calls++
		s.once.Do(s.before)
	}
	return s.Space.DeriveTreeObject(ctx, params)
}

func retainRegistrationPhases(t *testing.T, phases []annotationschema.Registration) {
	t.Helper()
	var calls []map[string]any
	for _, phase := range phases {
		var creations []map[string]any
		for _, creation := range phase.Creations {
			creations = append(creations, map[string]any{"invoked": creation.Invoked,
				"fixed_id": creation.Before.ObjectID, "returned_id": creation.ReturnedObjectID,
				"before": creation.Before.Disposition, "after": creation.After.Disposition})
		}
		calls = append(calls, map[string]any{"app_admitted": phase.AppAdmitted, "creations": creations,
			"type_apply_invoked": phase.TypeApplyInvoked, "type_apply_returned": phase.TypeApplyReturned,
			"disposition": phase.Observation.Disposition})
	}
	data, err := json.MarshalIndent(map[string]any{"schema": "otzaria-native-schema-registration-phases/1",
		"process_id": os.Getpid(), "calls": calls, "boundary": "actual disposable native calls and historical readback; no annotation create, mapping, body or ACK authority"}, "", "  ")
	nativeSchemaNoError(t, err)
	directory := os.Getenv("OTZARIA_ANNOTATION_SCHEMA_EVIDENCE")
	if directory == "" {
		t.Fatal("dedicated native evidence directory is required")
	}
	file, err := os.OpenFile(filepath.Join(directory, "annotation-schema-registration-phases.json"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	nativeSchemaNoError(t, err)
	_, writeErr := file.Write(append(data, '\n'))
	nativeSchemaNoError(t, errors.Join(writeErr, file.Sync(), file.Close()))
}
