package spaceindex

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/stretchr/testify/require"
)

func pinkhaStoredDeletion(t *testing.T, s *StoreFixture, id string) contract.DeletionAdmission {
	t.Helper()
	doc, err := s.headsState.FindId(context.Background(), id)
	require.NoError(t, err)
	require.Empty(t, doc.Value().GetString(headsStateField))
	require.Nil(t, doc.Value().Get(pinkhaNativeAdmissionField))
	var got contract.DeletionAdmission
	require.NoError(t, json.Unmarshal(doc.Value().GetStringBytes(pinkhaDeletionAdmissionField), &got))
	return got
}

func TestPinkhaNativeMetadataHeadsAndAdmissionShareTheOriginalTransaction(t *testing.T) {
	s := NewStoreFixture(t)
	ctx := context.Background()
	a := contract.NativeAdmission{Version: 1, SpaceID: "test", RootID: "metadata-root", HeaderSHA256: strings.Repeat("a", 64),
		NativeType: uint64(coresb.SmartBlockTypePinkhaTorahOperations), HeadsHash: contract.HeadsHash([]string{"native-head"})}
	tx, err := s.WriteTx(ctx)
	require.NoError(t, err)
	require.NoError(t, SavePinkhaNativeAdmission(tx.Context(), s.dsObjectStore, a))
	require.NoError(t, tx.Rollback())
	hash, err := s.GetLastIndexedHeadsHash(ctx, a.RootID)
	require.NoError(t, err)
	require.Empty(t, hash)
	_, err = s.headsState.FindId(ctx, a.RootID)
	require.Error(t, err, "rollback must retain neither witness nor heads")
	tx, err = s.WriteTx(ctx)
	require.NoError(t, err)
	require.NoError(t, SavePinkhaNativeAdmission(tx.Context(), s.dsObjectStore, a))
	require.NoError(t, tx.Commit())
	doc, err := s.headsState.FindId(ctx, a.RootID)
	require.NoError(t, err)
	require.Equal(t, a.HeadsHash, doc.Value().GetString(headsStateField))
	var stored contract.NativeAdmission
	require.NoError(t, json.Unmarshal(doc.Value().GetStringBytes(pinkhaNativeAdmissionField), &stored))
	require.Equal(t, a, stored)
	require.Nil(t, doc.Value().Get(pinkhaDeletionAdmissionField))
	foreign := a
	foreign.SpaceID = "foreign"
	require.ErrorIs(t, SavePinkhaNativeAdmission(ctx, s.dsObjectStore, foreign), contract.ErrInvalidWitness)
}

func TestPinkhaTerminalAdmissionRequiresOriginalTombstoneAndPreservesDeletionAudit(t *testing.T) {
	s := NewStoreFixture(t)
	ctx := context.Background()
	s.AddObjects(t, []TestObject{liveObject("deleted")})
	a := contract.DeletionAdmission{Version: 1, SpaceID: "test", Provenance: "retained-terminal-and-original-tombstone",
		Terminal: contract.Head{ID: "deleted", Heads: []string{"original-head"}, CommonSnapshot: "original-snapshot",
			DeletedStatus: headstorage.DeletedStatusDeleted, LastAddSeq: 47}}
	live, err := s.GetDetails("deleted")
	require.NoError(t, err)
	require.ErrorIs(t, PinkhaDeleteObject(s.dsObjectStore, "deleted", a), contract.ErrInvalidWitness)
	after, err := s.GetDetails("deleted")
	require.NoError(t, err)
	require.Equal(t, live, after, "no retrospective tombstone may be fabricated")
	require.NoError(t, s.DeleteObject("deleted"))
	require.NoError(t, s.ModifyObjectDetails("deleted", func(d *domain.Details) (*domain.Details, bool, error) {
		d.SetString(bundle.RelationKeyDeletedBy, "original-deleter")
		d.SetInt64(bundle.RelationKeyDeletedDate, 1234)
		d.SetString(bundle.RelationKeyDeletionChangeId, "original-delete-change")
		return d, true, nil
	}, false))
	before, err := s.GetDetails("deleted")
	require.NoError(t, err)
	for n := 0; n < 2; n++ {
		require.NoError(t, PinkhaDeleteObject(s.dsObjectStore, "deleted", a))
		require.Equal(t, a, pinkhaStoredDeletion(t, s, "deleted"))
		after, err = s.GetDetails("deleted")
		require.NoError(t, err)
		require.Equal(t, before, after, "one-time reindex must preserve exact original deletion audit")
	}
	// Inspect only the changed index boundary with explicit model head rows.
	// The full native acceptance separately obtains these from HeadStorage.
	native := contract.NativeSnapshot{SpaceID: "test", ACLID: "acl", SettingsID: "settings", Roots: []contract.NativeRoot{
		{Head: contract.Head{ID: "acl"}, Protocol: true}, {Head: contract.Head{ID: "settings"}, Protocol: true}, {Head: a.Terminal},
	}}
	positive, err := PinkhaTorahSnapshot(ctx, s.dsObjectStore, native, "canonical", &contract.Budget{})
	require.NoError(t, err)
	require.Equal(t, 1, positive.IndexedObjectCount)
	require.NotContains(t, positive.Reasons, contract.StaleDeletionAdmission)
	for _, change := range []func(*contract.Head){
		func(h *contract.Head) { h.LastAddSeq++ }, func(h *contract.Head) { h.Heads = []string{"new-head"} },
		func(h *contract.Head) { h.CommonSnapshot = "new-snapshot" }, func(h *contract.Head) { h.ParentID = "new-parent" },
		func(h *contract.Head) { h.IsDerived = true }, func(h *contract.Head) { h.DeletedStatus = headstorage.DeletedStatusQueued },
		func(h *contract.Head) { h.DeletedStatus = headstorage.DeletedStatusNotDeleted },
	} {
		changed := native
		changed.Roots = append([]contract.NativeRoot(nil), native.Roots...)
		change(&changed.Roots[2].Head)
		negative, e := PinkhaTorahSnapshot(ctx, s.dsObjectStore, changed, "canonical", &contract.Budget{})
		require.NoError(t, e)
		require.Zero(t, negative.IndexedObjectCount, "old tombstone never proves a new generation or resurrected object")
	}
	require.Equal(t, a, pinkhaStoredDeletion(t, s, "deleted"), "readiness must not repair or rewrite a stale witness")
}

func TestPinkhaCollectionBoundNeverSucceedsWithPrefix(t *testing.T) {
	s := NewStoreFixture(t)
	ctx := context.Background()
	c, err := s.db.Collection(ctx, "_pinkhaOwnedBoundFixture")
	require.NoError(t, err)
	tx, err := s.db.WriteTx(ctx)
	require.NoError(t, err)
	for n := 0; n <= contract.MaxObjects; n++ {
		require.NoError(t, c.Insert(tx.Context(), anyenc.MustParse(fmt.Sprintf(`{"id":"%05d","v":"retained"}`, n))))
	}
	require.NoError(t, tx.Commit())
	visited := 0
	err = pinkhaReadCollection(ctx, c, &contract.Budget{}, func(*anyenc.Value) error { visited++; return nil })
	require.ErrorIs(t, err, contract.ErrBound)
	require.Equal(t, contract.MaxObjects, visited)
	budget := &contract.Budget{}
	require.NoError(t, budget.Add(contract.MaxWitnessBytes-1))
	visited = 0
	err = pinkhaReadCollection(ctx, c, budget, func(*anyenc.Value) error { visited++; return nil })
	require.ErrorIs(t, err, contract.ErrBound)
	require.Zero(t, visited, "oversized row cannot enter a partial snapshot")
	canceled, cancel := context.WithCancel(ctx)
	cancel()
	err = pinkhaReadCollection(canceled, c, &contract.Budget{}, func(*anyenc.Value) error { t.Fatal("canceled snapshot delivered a row"); return nil })
	require.Error(t, err)
}
