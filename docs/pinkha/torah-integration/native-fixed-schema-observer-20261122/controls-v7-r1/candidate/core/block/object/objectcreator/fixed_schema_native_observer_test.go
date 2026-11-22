package objectcreator_test

import (
	"bytes"
	"context"
	"errors"
	"slices"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/any-sync/commonspace/object/acl/aclrecordproto"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/any-sync/consensus/consensusproto"

	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

func TestOtzariaFixedSchemaNativeObserverV5(t *testing.T) {
	f := newNativeSchemaFixture(t)
	spc := f.regularSpace(t)
	db := spc.Storage().AnyStore()

	makeRelation := func(t *testing.T, suffix string) (objectcreator.FixedSchemaDefinition, string) {
		t.Helper()
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, suffix)
		return definition, f.createSchema(t, spc, definition)
	}

	t.Run("OriginalRelationMatch", func(t *testing.T) {
		definition, id := makeRelation(t, "relation")
		// Exercise the actual current V1 creation path, including its valid empty
		// ACL-root SpaceId; header binding must use the original validator.
		state, err := spc.Storage().StateStorage().GetState(f.ctx)
		nativeSchemaNoError(t, err)
		var rawHeader spacesyncproto.RawSpaceHeader
		nativeSchemaNoError(t, rawHeader.UnmarshalVT(state.SpaceHeader))
		var header spacesyncproto.SpaceHeader
		nativeSchemaNoError(t, header.UnmarshalVT(rawHeader.SpaceHeader))
		var rawACL consensusproto.RawRecord
		nativeSchemaNoError(t, rawACL.UnmarshalVT(header.AclPayload))
		var aclRoot aclrecordproto.AclRoot
		nativeSchemaNoError(t, aclRoot.UnmarshalVT(rawACL.Payload))
		if header.Version != spacesyncproto.SpaceHeaderVersion_SpaceHeaderVersion1 || aclRoot.SpaceId != "" {
			t.Fatal("fixture does not exercise original V1 embedded identity semantics")
		}
		rootBefore := nativeSchemaReadRow(t, f.ctx, db, objecttree.CollName, id)
		f.observe(t, spc, definition, objectcreator.FixedSchemaPersistedMatch)
		nativeSchemaRowsEqual(t, f.ctx, db, objecttree.CollName, id, rootBefore)
	})

	t.Run("OriginalObjectTypeMatch", func(t *testing.T) {
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeObjectType, "type")
		f.createSchema(t, spc, definition)
		f.observe(t, spc, definition, objectcreator.FixedSchemaPersistedMatch)
	})

	t.Run("ExactNativeRootOnly", func(t *testing.T) {
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "rootonly")
		id := f.createRootOnly(t, spc, definition)
		before := nativeSchemaReadRow(t, f.ctx, db, objecttree.CollName, id)
		result := f.observe(t, spc, definition, objectcreator.FixedSchemaRootOnlyIncomplete)
		if !slices.Equal(result.PersistedHeads, []string{id}) {
			t.Fatal("root-only heads were not exact")
		}
		nativeSchemaRowsEqual(t, f.ctx, db, objecttree.CollName, id, before)
	})

	t.Run("NativeLocalMissingWithoutCreation", func(t *testing.T) {
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "missing")
		result := f.observe(t, spc, definition, objectcreator.FixedSchemaLocallyMissing)
		exists, err := spc.Storage().HasTree(f.ctx, result.ObjectID)
		nativeSchemaNoError(t, err)
		if exists {
			t.Fatal("observer created a missing native tree")
		}
	})

	t.Run("ActualLocalZeroCounterAccepted", func(t *testing.T) {
		definition, id := makeRelation(t, "localzero")
		tree := f.tree(t, spc, id)
		added := f.addChange(t, tree, nativeSchemaChangeDescription("actual local ordinary change"), 1700000101)
		stored, err := tree.Storage().Get(f.ctx, added.Added[0].Id)
		nativeSchemaNoError(t, err)
		if stored.SnapshotCounter != 0 {
			t.Fatal("fixture did not exercise the actual native local zero-counter path")
		}
		f.observeStableCounter(t, spc, definition, id, added.Added[0].Id, stored.SnapshotCounter)
	})

	t.Run("NativeComputedRemoteCounterAccepted", func(t *testing.T) {
		definition, id := makeRelation(t, "remotecounter")
		tree := f.tree(t, spc, id)
		raw := nativeSchemaRawChange(t, tree, nativeSchemaChangeDescription("actual native raw ingestion"), 1700000102)
		tree.Lock()
		added, err := tree.AddRawChanges(f.ctx, objecttree.RawChangesPayload{
			NewHeads: []string{raw.Id}, RawChanges: []*treechangeproto.RawTreeChangeWithId{raw},
		})
		tree.Unlock()
		nativeSchemaNoError(t, err)
		if len(added.Added) != 1 {
			t.Fatal("original raw ingestion did not persist exactly one change")
		}
		stored, err := tree.Storage().Get(f.ctx, raw.Id)
		nativeSchemaNoError(t, err)
		if stored.SnapshotCounter <= 0 {
			t.Fatal("fixture did not exercise native computed remote-ingest counter")
		}
		f.observeStableCounter(t, spc, definition, id, raw.Id, stored.SnapshotCounter)
	})

	t.Run("NonzeroCounterMetadataConflict", func(t *testing.T) {
		definition, id := makeRelation(t, "badcounter")
		tree := f.tree(t, spc, id)
		added := f.addChange(t, tree, nativeSchemaChangeDescription("counter conflict"), 1700000103)
		nativeSchemaMutateRow(t, f.ctx, db, objecttree.CollName, added.Added[0].Id, func(a *anyenc.Arena, v *anyenc.Value) {
			v.Set(objecttree.SnapshotCounterKey, a.NewNumberInt(999999))
		})
		f.unavailableCause(t, spc, definition, objectcreator.ErrFixedSchemaStorage, "native snapshot reference/counter")
	})

	t.Run("FractionalCounterCannotDefaultToZero", func(t *testing.T) {
		definition, id := makeRelation(t, "fraction")
		tree := f.tree(t, spc, id)
		added := f.addChange(t, tree, nativeSchemaChangeDescription("fractional row"), 1700000104)
		nativeSchemaMutateRow(t, f.ctx, db, objecttree.CollName, added.Added[0].Id, func(a *anyenc.Arena, v *anyenc.Value) {
			v.Set(objecttree.SnapshotCounterKey, a.NewNumberFloat64(0.25))
		})
		f.unavailable(t, spc, definition)
	})

	t.Run("StoredOrderMustMatchNativeTraversal", func(t *testing.T) {
		definition, id := makeRelation(t, "order")
		tree := f.tree(t, spc, id)
		first := f.addChange(t, tree, nativeSchemaChangeDescription("first native row"), 1700000105).Added[0]
		second := f.addChange(t, tree, nativeSchemaChangeDescription("second native row"), 1700000106).Added[0]
		firstRow := nativeSchemaReadRow(t, f.ctx, db, objecttree.CollName, first.Id)
		secondRow := nativeSchemaReadRow(t, f.ctx, db, objecttree.CollName, second.Id)
		t.Cleanup(func() { nativeSchemaSwapOrder(t, f.ctx, db, first.Id, second.Id, first.OrderId, second.OrderId) })
		nativeSchemaSwapOrder(t, f.ctx, db, first.Id, second.Id, second.OrderId, first.OrderId)
		f.unavailableCause(t, spc, definition, objectcreator.ErrFixedSchemaStorage, "stored order differs from original traversal")
		// Restore atomically before byte readback; cleanup remains idempotent.
		nativeSchemaSwapOrder(t, f.ctx, db, first.Id, second.Id, first.OrderId, second.OrderId)
		nativeSchemaRowsEqual(t, f.ctx, db, objecttree.CollName, first.Id, firstRow)
		nativeSchemaRowsEqual(t, f.ctx, db, objecttree.CollName, second.Id, secondRow)
	})

	t.Run("OlderNativeCommonSnapshotAccepted", func(t *testing.T) {
		definition, id := makeRelation(t, "oldcommon")
		tree := f.tree(t, spc, id)
		f.addChange(t, tree, nativeSchemaChangeDescription("before newer snapshot"), 1700000107)
		snapshot := nativeSchemaSnapshot(t, spc.Id(), tree)
		newer := f.addChange(t, tree, snapshot, 1700000108)
		if newer.Heads[0] == id {
			t.Fatal("native snapshot was not newer than root")
		}
		nativeSchemaNoError(t, spc.Storage().HeadStorage().UpdateEntry(f.ctx, headstorage.HeadsUpdate{
			Id: id, CommonSnapshot: &id,
		}))
		f.observe(t, spc, definition, objectcreator.FixedSchemaPersistedMatch)
	})

	t.Run("UnrelatedNativeSnapshotCannotBecomeCommon", func(t *testing.T) {
		definition, id := makeRelation(t, "branch")
		tree := f.tree(t, spc, id)
		snapshot := nativeSchemaSnapshot(t, spc.Id(), tree)
		branchB := nativeSchemaRawChange(t, tree, snapshot, 1700000109)
		branchA := f.addChange(t, tree, snapshot, 1700000110)
		tree.Lock()
		added, err := tree.AddRawChanges(f.ctx, objecttree.RawChangesPayload{
			NewHeads: []string{branchA.Heads[0], branchB.Id}, RawChanges: []*treechangeproto.RawTreeChangeWithId{branchB},
		})
		tree.Unlock()
		nativeSchemaNoError(t, err)
		if len(added.Heads) != 2 {
			t.Fatal("fixture did not retain two actual native snapshot branches")
		}
		common := branchB.Id
		nativeSchemaNoError(t, spc.Storage().HeadStorage().UpdateEntry(f.ctx, headstorage.HeadsUpdate{
			Id: id, CommonSnapshot: &common,
		}))
		f.unavailableCause(t, spc, definition, objectcreator.ErrFixedSchemaStorage, "persisted common snapshot is not an allowed native ancestor")
	})

	t.Run("ExplicitLongtextPresenceCannotDefault", func(t *testing.T) {
		definition, id := makeRelation(t, "missingformat")
		tree := f.tree(t, spc, id)
		snapshot := nativeSchemaSnapshot(t, spc.Id(), tree)
		delete(snapshot.Snapshot.Data.Details.Fields, string(bundle.RelationKeyRelationFormat))
		f.addChange(t, tree, snapshot, 1700000111)
		f.observe(t, spc, definition, objectcreator.FixedSchemaPopulatedConflict)
	})

	t.Run("ArchiveUsesOriginalNativeLinkTree", func(t *testing.T) {
		definition, id := makeRelation(t, "archive")
		f.archive(t, id)
		f.observe(t, spc, definition, objectcreator.FixedSchemaPopulatedConflict)
	})

	t.Run("WrongDerivedHeaderUnavailable", func(t *testing.T) {
		definition, id := makeRelation(t, "header")
		other := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "otherheader")
		otherID := f.createRootOnly(t, spc, other)
		otherStorage, err := spc.Storage().TreeStorage(f.ctx, otherID)
		nativeSchemaNoError(t, err)
		otherRoot, err := otherStorage.Root(f.ctx)
		nativeSchemaNoError(t, err)
		nativeSchemaMutateRow(t, f.ctx, db, objecttree.CollName, id, func(a *anyenc.Arena, v *anyenc.Value) {
			v.Set("r", a.NewBinary(otherRoot.RawChange))
			v.Set(objecttree.ChangeSizeKey, a.NewNumberInt(len(otherRoot.RawChange)))
		})
		f.unavailableCause(t, spc, definition, objectcreator.ErrFixedSchemaStorage, "original derived header mismatch")
	})

	t.Run("OriginalPooledReaderAndACLLockOrder", func(t *testing.T) {
		definition, _ := makeRelation(t, "pool")
		f.pooledReaderACLControl(t, spc, definition)
	})

	t.Run("FullACLIntermediateRecordRequired", func(t *testing.T) {
		aclSpace := f.regularSpace(t)
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "aclmissing")
		f.createSchema(t, aclSpace, definition)
		f.appendACLRecord(t, aclSpace)
		f.appendACLRecord(t, aclSpace)
		acl := aclSpace.CommonSpace().Acl()
		acl.RLock()
		records := acl.Records()
		if len(records) < 3 {
			acl.RUnlock()
			t.Fatal("native fixture lacks an intermediate ACL record")
		}
		id, aclID := records[len(records)-2].Id, acl.Id()
		acl.RUnlock()
		aclDB := aclSpace.Storage().AnyStore()
		original := nativeSchemaReadRow(t, f.ctx, aclDB, aclID, id)
		collection, err := aclDB.OpenCollection(f.ctx, aclID)
		nativeSchemaNoError(t, err)
		t.Cleanup(func() { nativeSchemaRestoreRow(t, f.ctx, aclDB, aclID, original) })
		nativeSchemaNoError(t, collection.DeleteId(f.ctx, id))
		f.unavailableCause(t, aclSpace, definition, objectcreator.ErrFixedSchemaStorage, "complete persisted ACL chain")
	})

	t.Run("FullACLExtraRecordRefused", func(t *testing.T) {
		aclSpace := f.regularSpace(t)
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "aclextra")
		f.createSchema(t, aclSpace, definition)
		acl := aclSpace.CommonSpace().Acl()
		acl.RLock()
		aclID, headID, count := acl.Id(), acl.Head().Id, len(acl.Records())
		acl.RUnlock()
		aclDB := aclSpace.Storage().AnyStore()
		original := nativeSchemaReadRow(t, f.ctx, aclDB, aclID, headID)
		value, err := (&anyenc.Parser{}).Parse(original)
		nativeSchemaNoError(t, err)
		a := &anyenc.Arena{}
		extraID := "otzaria-observer-extra-acl-row"
		value.Set("id", a.NewString(extraID))
		value.Set("o", a.NewNumberInt(count+1))
		value.Set("p", a.NewString(headID))
		collection, err := aclDB.OpenCollection(f.ctx, aclID)
		nativeSchemaNoError(t, err)
		t.Cleanup(func() { nativeSchemaNoError(t, collection.DeleteId(f.ctx, extraID)) })
		nativeSchemaNoError(t, collection.Insert(f.ctx, value))
		f.unavailable(t, aclSpace, definition)
	})

	t.Run("OriginalACLSignatureCIDVerification", func(t *testing.T) {
		aclSpace := f.regularSpace(t)
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "aclbytes")
		f.createSchema(t, aclSpace, definition)
		f.appendACLRecord(t, aclSpace)
		acl := aclSpace.CommonSpace().Acl()
		acl.RLock()
		aclID, headID := acl.Id(), acl.Head().Id
		acl.RUnlock()
		nativeSchemaMutateRow(t, f.ctx, aclSpace.Storage().AnyStore(), aclID, headID, func(a *anyenc.Arena, v *anyenc.Value) {
			raw := &consensusproto.RawRecord{}
			nativeSchemaNoError(t, raw.UnmarshalVT(v.GetBytes("r")))
			if len(raw.Signature) == 0 {
				t.Fatal("native ACL record has no original author signature")
			}
			raw.Signature[len(raw.Signature)-1] ^= 1
			corrupt, err := raw.MarshalVT()
			nativeSchemaNoError(t, err)
			v.Set("r", a.NewBinary(corrupt))
		})
		f.unavailableCause(t, aclSpace, definition, list.ErrInvalidSignature, "verify original persisted ACL record:")
	})

	t.Run("SecondSnapshotSeesInvisibleEncodedRowChange", func(t *testing.T) {
		definition, id := makeRelation(t, "encoded")
		before := nativeSchemaReadRow(t, f.ctx, db, objecttree.CollName, id)
		t.Cleanup(func() { nativeSchemaRestoreRow(t, f.ctx, db, objecttree.CollName, before) })
		trace := &nativeSchemaTraceDB{DB: db}
		trace.committed = func(index int, done bool) error {
			if !done {
				return errors.New("native read transaction not closed")
			}
			if index == 1 {
				collection, err := db.OpenCollection(f.ctx, objecttree.CollName)
				if err != nil {
					return err
				}
				value, err := (&anyenc.Parser{}).Parse(before)
				if err != nil {
					return err
				}
				a := &anyenc.Arena{}
				value.Set("observer-fixture-extra-metadata", a.NewString("changed-after-first-snapshot"))
				return collection.UpdateOne(f.ctx, value)
			}
			return nil
		}
		result, err := f.observer.ObserveFixedSchema(f.ctx, nativeSchemaTracedSpace(spc, trace), definition)
		if !errors.Is(err, objectcreator.ErrFixedSchemaChanged) || result.Disposition != objectcreator.FixedSchemaChangedWhileReading {
			t.Fatalf("complete native encoded row change was missed: %d %v", result.Disposition, err)
		}
	})

	t.Run("SecondSnapshotSeesExtraNonHeadChange", func(t *testing.T) {
		definition, id := makeRelation(t, "nonhead")
		tree := f.tree(t, spc, id)
		oldHead := nativeSchemaReadRow(t, f.ctx, db, headstorage.HeadsCollectionName, id)
		trace := &nativeSchemaTraceDB{DB: db}
		var addedID string
		trace.committed = func(index int, done bool) error {
			if !done {
				return errors.New("native read transaction not closed")
			}
			if index != 1 {
				return nil
			}
			// This writes through the actual signed/encrypted native AddContent
			// path. The fixture then restores the old encoded head, deliberately
			// leaving one extra persisted non-head row for the second snapshot.
			added := f.addChange(t, tree, nativeSchemaChangeDescription("extra original non-head"), 1700000112)
			addedID = added.Added[0].Id
			nativeSchemaRestoreRow(t, f.ctx, db, headstorage.HeadsCollectionName, oldHead)
			return nil
		}
		result, err := f.observer.ObserveFixedSchema(f.ctx, nativeSchemaTracedSpace(spc, trace), definition)
		if addedID == "" || !errors.Is(err, objectcreator.ErrFixedSchemaChanged) || result.Disposition != objectcreator.FixedSchemaChangedWhileReading {
			t.Fatalf("extra native non-head row was missed: %d %v", result.Disposition, err)
		}
		nativeSchemaRowsEqual(t, f.ctx, db, headstorage.HeadsCollectionName, id, oldHead)
		if _, err := tree.Storage().Get(f.ctx, addedID); err != nil {
			t.Fatal("extra native row did not persist")
		}
	})

	t.Run("RealNativeOperationsPropagateInjectedIteratorCloseCommitErrors", func(t *testing.T) {
		definition, _ := makeRelation(t, "errors")
		iteration := errors.New("fixture iterator error after native scan")
		closeErr := errors.New("fixture close error after native close")
		commit := errors.New("fixture commit error after native commit")
		trace := &nativeSchemaTraceDB{DB: db, faults: &nativeSchemaFaults{iteration: iteration, close: closeErr, commit: commit}}
		commits := 0
		trace.committed = func(_ int, done bool) error {
			if !done {
				return errors.New("real native Commit did not release reader")
			}
			commits++
			return nil
		}
		err := f.unavailable(t, nativeSchemaTracedSpace(spc, trace), definition)
		if !errors.Is(err, iteration) || !errors.Is(err, closeErr) || !errors.Is(err, commit) || commits != 1 {
			t.Fatalf("joined native-delegated fixture errors were lost: commits=%d err=%v", commits, err)
		}
	})

	t.Run("RealNativeOpenFailurePropagationStillReleasesReadTx", func(t *testing.T) {
		definition, _ := makeRelation(t, "openerror")
		readErr := errors.New("fixture read error after genuine OpenCollection")
		commitErr := errors.New("fixture commit error after genuine release")
		trace := &nativeSchemaTraceDB{DB: db, faults: &nativeSchemaFaults{open: readErr, commit: commitErr}}
		released := 0
		trace.committed = func(_ int, done bool) error {
			if done {
				released++
			}
			return nil
		}
		err := f.unavailable(t, nativeSchemaTracedSpace(spc, trace), definition)
		if !errors.Is(err, readErr) || !errors.Is(err, commitErr) || released != 1 {
			t.Fatalf("native read/cleanup propagation mismatch: released=%d err=%v", released, err)
		}
	})

	t.Run("MissingOriginalSpaceStateUnavailable", func(t *testing.T) {
		definition, _ := makeRelation(t, "statemissing")
		before := nativeSchemaReadRow(t, f.ctx, db, "state", spc.Id())
		collection, err := db.OpenCollection(f.ctx, "state")
		nativeSchemaNoError(t, err)
		t.Cleanup(func() { nativeSchemaRestoreRow(t, f.ctx, db, "state", before) })
		nativeSchemaNoError(t, collection.DeleteId(f.ctx, spc.Id()))
		f.unavailable(t, spc, definition)
	})

	t.Run("PersistedStateACLIdentityMismatchUnavailable", func(t *testing.T) {
		definition, _ := makeRelation(t, "stateacl")
		nativeSchemaMutateRow(t, f.ctx, db, "state", spc.Id(), func(a *anyenc.Arena, v *anyenc.Value) {
			v.Set("a", a.NewString(spc.Storage().StateStorage().SettingsId()))
		})
		if err := f.unavailable(t, spc, definition); !errors.Is(err, objectcreator.ErrFixedSchemaStorage) {
			t.Fatalf("actual retained ACL identity mismatch not recognized: %v", err)
		}
	})

	t.Run("PersistedStateSettingsIdentityMismatchUnavailable", func(t *testing.T) {
		definition, id := makeRelation(t, "statesettings")
		actualSettings := spc.Storage().StateStorage().SettingsId()
		nativeSchemaMutateRow(t, f.ctx, db, "state", spc.Id(), func(a *anyenc.Arena, v *anyenc.Value) {
			v.Set("s", a.NewString(id))
		})
		if spc.Storage().StateStorage().SettingsId() != actualSettings {
			t.Fatal("original retained settings getter unexpectedly adopted the corrupt row")
		}
		if err := f.unavailable(t, spc, definition); !errors.Is(err, objectcreator.ErrFixedSchemaStorage) {
			t.Fatalf("actual retained settings identity mismatch not recognized: %v", err)
		}
	})

	t.Run("AnotherRealSpaceHeaderCannotBindCurrentSpace", func(t *testing.T) {
		definition, _ := makeRelation(t, "foreignspace")
		foreign := f.regularSpace(t)
		other, err := foreign.Storage().StateStorage().GetState(f.ctx)
		nativeSchemaNoError(t, err)
		if foreign.Id() == spc.Id() || len(other.SpaceHeader) == 0 {
			t.Fatal("foreign original Space fixture is not distinct")
		}
		nativeSchemaMutateRow(t, f.ctx, db, "state", spc.Id(), func(a *anyenc.Arena, v *anyenc.Value) {
			v.Set("e", a.NewBinary(other.SpaceHeader))
		})
		f.unavailable(t, spc, definition)
	})

	t.Run("ActualSpaceHeaderSignatureCIDFailureUnavailable", func(t *testing.T) {
		definition, _ := makeRelation(t, "badspaceheader")
		nativeSchemaMutateRow(t, f.ctx, db, "state", spc.Id(), func(a *anyenc.Arena, v *anyenc.Value) {
			raw := bytes.Clone(v.GetBytes("e"))
			if len(raw) == 0 {
				t.Fatal("native header fixture is empty")
			}
			raw[len(raw)-1] ^= 1
			v.Set("e", a.NewBinary(raw))
		})
		f.unavailable(t, spc, definition)
	})

	t.Run("SpaceHeaderNativeTypeCannotDefault", func(t *testing.T) {
		definition, _ := makeRelation(t, "headertype")
		nativeSchemaMutateRow(t, f.ctx, db, "state", spc.Id(), func(a *anyenc.Arena, v *anyenc.Value) {
			v.Set("e", a.NewString("invalid-string-in-original-binary-field"))
		})
		f.unavailable(t, spc, definition)
	})

	t.Run("MissingActualSettingsRootUnavailable", func(t *testing.T) {
		definition, _ := makeRelation(t, "settingsmissing")
		id := spc.Storage().StateStorage().SettingsId()
		before := nativeSchemaReadRow(t, f.ctx, db, objecttree.CollName, id)
		collection, err := db.OpenCollection(f.ctx, objecttree.CollName)
		nativeSchemaNoError(t, err)
		t.Cleanup(func() { nativeSchemaRestoreRow(t, f.ctx, db, objecttree.CollName, before) })
		nativeSchemaNoError(t, collection.DeleteId(f.ctx, id))
		f.unavailable(t, spc, definition)
	})

	t.Run("ActualSettingsRootSignatureCIDFailureUnavailable", func(t *testing.T) {
		definition, _ := makeRelation(t, "settingsbytes")
		id := spc.Storage().StateStorage().SettingsId()
		nativeSchemaMutateRow(t, f.ctx, db, objecttree.CollName, id, func(a *anyenc.Arena, v *anyenc.Value) {
			raw := bytes.Clone(v.GetBytes("r"))
			if len(raw) == 0 {
				t.Fatal("original settings root fixture is empty")
			}
			raw[len(raw)-1] ^= 1
			v.Set("r", a.NewBinary(raw))
		})
		f.unavailable(t, spc, definition)
	})

	t.Run("SecondSnapshotSeesCompleteStateRowChange", func(t *testing.T) {
		definition, _ := makeRelation(t, "statebytes")
		before := nativeSchemaReadRow(t, f.ctx, db, "state", spc.Id())
		t.Cleanup(func() { nativeSchemaRestoreRow(t, f.ctx, db, "state", before) })
		trace := &nativeSchemaTraceDB{DB: db}
		trace.committed = func(index int, done bool) error {
			if !done {
				return errors.New("real read transaction not released")
			}
			if index != 1 {
				return nil
			}
			collection, err := db.OpenCollection(f.ctx, "state")
			if err != nil {
				return err
			}
			value, err := (&anyenc.Parser{}).Parse(before)
			if err != nil {
				return err
			}
			a := &anyenc.Arena{}
			value.Set("observer-fixture-extra-state", a.NewString("after-original-first-commit"))
			return collection.UpdateOne(f.ctx, value)
		}
		result, err := f.observer.ObserveFixedSchema(f.ctx, nativeSchemaTracedSpace(spc, trace), definition)
		if !errors.Is(err, objectcreator.ErrFixedSchemaChanged) || result.Disposition != objectcreator.FixedSchemaChangedWhileReading {
			t.Fatalf("full native state row change escaped second snapshot: %d %v", result.Disposition, err)
		}
	})

	t.Run("SecondSnapshotSeesCompleteSettingsRootRowChange", func(t *testing.T) {
		definition, _ := makeRelation(t, "settingsrowbytes")
		id := spc.Storage().StateStorage().SettingsId()
		before := nativeSchemaReadRow(t, f.ctx, db, objecttree.CollName, id)
		t.Cleanup(func() { nativeSchemaRestoreRow(t, f.ctx, db, objecttree.CollName, before) })
		trace := &nativeSchemaTraceDB{DB: db}
		trace.committed = func(index int, done bool) error {
			if !done {
				return errors.New("real read transaction not released")
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
			a := &anyenc.Arena{}
			value.Set("observer-fixture-extra-settings", a.NewString("after-original-first-commit"))
			return collection.UpdateOne(f.ctx, value)
		}
		result, err := f.observer.ObserveFixedSchema(f.ctx, nativeSchemaTracedSpace(spc, trace), definition)
		if !errors.Is(err, objectcreator.ErrFixedSchemaChanged) || result.Disposition != objectcreator.FixedSchemaChangedWhileReading {
			t.Fatalf("full actual settings root row change escaped second snapshot: %d %v", result.Disposition, err)
		}
	})

	t.Run("CanceledCallerCannotPublishObservation", func(t *testing.T) {
		definition := nativeSchemaDefinition(t, coresb.SmartBlockTypeRelation, "cancel")
		ctx, cancel := context.WithCancel(f.ctx)
		cancel()
		result, err := f.observer.ObserveFixedSchema(ctx, spc, definition)
		if !errors.Is(err, context.Canceled) || result.Disposition != objectcreator.FixedSchemaUnavailable {
			t.Fatalf("canceled full observer published success: %d %v", result.Disposition, err)
		}
	})
}

// Swap actual unique native order fields within one real outer WriteTx so the
// corruption fixture never relies on a transient uniqueness conflict.
func nativeSchemaSwapOrder(t *testing.T, ctx context.Context, db anystore.DB, firstID, secondID, firstOrder, secondOrder string) {
	t.Helper()
	tx, err := db.WriteTx(ctx)
	nativeSchemaNoError(t, err)
	defer tx.Rollback()
	collection, err := db.OpenCollection(tx.Context(), objecttree.CollName)
	nativeSchemaNoError(t, err)
	set := func(id, order string) {
		doc, err := collection.FindId(tx.Context(), id)
		nativeSchemaNoError(t, err)
		a := &anyenc.Arena{}
		value := doc.Value()
		value.Set(objecttree.OrderKey, a.NewString(order))
		nativeSchemaNoError(t, collection.UpdateOne(tx.Context(), value))
	}
	set(firstID, "~otzaria-v5-unique-temporary-order")
	set(secondID, secondOrder)
	set(firstID, firstOrder)
	nativeSchemaNoError(t, tx.Commit())
}

// Compile-time interface checks ensure decorators preserve the actual native
// interfaces; their values and authority always come from the retained runtime.
var _ clientspace.Space = (*tracedSchemaSpace)(nil)
var _ anystore.DB = (*nativeSchemaTraceDB)(nil)
var _ anystore.ReadTx = (*nativeSchemaTraceTx)(nil)
var _ anystore.Query = (*nativeSchemaTraceQuery)(nil)
var _ anystore.Iterator = (*nativeSchemaTraceIterator)(nil)
