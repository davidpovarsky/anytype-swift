package torahops

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/anyproto/anytype-heart/core/block/editor/storestate"
	"github.com/anyproto/anytype-heart/pb"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/stretchr/testify/require"
)

func cutoverFixtureRecord(t *testing.T, id int, author string) cutover.Record {
	t.Helper()
	plan := cutover.Plan{Version: cutover.Version, SpaceID: "disposable-space", ObjectID: "disposable-document",
		PropertyKey: "native-property", ValuePresent: true, LegacyValue: []byte("{\"legacy\":\"retained\"}"),
		Facts: []cutover.Fact{{ProviderID: "sefaria", CanonicalRef: "Genesis.1.1", Payload: []byte("{\"component\":\"canonical-source-bytes\"}")}}}
	planID, err := plan.ID()
	require.NoError(t, err)
	return cutover.Record{Version: cutover.Version, SpaceID: plan.SpaceID, ObjectID: plan.ObjectID,
		RecordID: fmt.Sprintf("%032x", id), AuthorID: author, Kind: cutover.Begin, PlanID: planID, Plan: &plan, SourceHeads: []string{"actual-component-source-head"}}
}
func cutoverNative(record cutover.Record, id string) NativeChange {
	return NativeChange{ID: id, Order: id, Creator: record.AuthorID, ACLHeadID: "component-verified-acl"}
}
func openCutoverProjection(t *testing.T, fx *fixture) *CutoverStore {
	t.Helper()
	s, err := NewCutoverStore(testContext, fx.db, "disposable-space")
	require.NoError(t, err)
	return s
}
func cutoverCounts(t *testing.T, s *CutoverStore, claims, receipts int) {
	t.Helper()
	n, err := s.claims.Count(testContext)
	require.NoError(t, err)
	require.Equal(t, claims, n)
	n, err = s.receipts.Count(testContext)
	require.NoError(t, err)
	require.Equal(t, receipts, n)
}

func TestCutoverMetadataKeepsV1NamespaceAndOrdinaryClaims(t *testing.T) {
	fx := openFixture(t, "")
	original := appendLocal(t, fx, add(301, "original v1 association"), "ordinary-301")
	before := projection(t, fx)
	s := openCutoverProjection(t, fx)
	record := cutoverFixtureRecord(t, 1, "writer-a")
	out, err := s.AppendLocal(testContext, record, cutoverNative(record, "metadata-1"))
	require.NoError(t, err)
	require.Equal(t, Created, out.Disposition)
	require.NotEqual(t, original.ClaimID, out.ClaimID)
	require.Equal(t, before, projection(t, fx))
	counts(t, fx, 1, 1)
	cutoverCounts(t, s, 1, 1)
	fx.reopen(t)
	s = openCutoverProjection(t, fx)
	require.Equal(t, before, projection(t, fx))
	counts(t, fx, 1, 1)
	cutoverCounts(t, s, 1, 1)
	read, err := s.ReadObject(testContext, record.ObjectID, 100)
	require.NoError(t, err)
	require.Len(t, read.Claims, 1)
	require.Empty(t, read.Conflicts)
	require.Equal(t, record.PlanID, read.Claims[0].Record.PlanID)
}

func TestCutoverMetadataIndependentDisksRetainActualComponentAuthors(t *testing.T) {
	// Actual independent SQLite projections and explicit component replay.
	// This is not a native signature, ACL or two-peer transport acceptance.
	a, b := openFixture(t, ""), openFixture(t, "")
	sa, sb := openCutoverProjection(t, a), openCutoverProjection(t, b)
	ra, rb := cutoverFixtureRecord(t, 1, "writer-a"), cutoverFixtureRecord(t, 2, "writer-b")
	require.Equal(t, ra.PlanID, rb.PlanID)
	oa, err := sa.AppendLocal(testContext, ra, cutoverNative(ra, "change-a"))
	require.NoError(t, err)
	ob, err := sb.AppendLocal(testContext, rb, cutoverNative(rb, "change-b"))
	require.NoError(t, err)
	require.NotEqual(t, oa.ClaimID, ob.ClaimID)
	require.NoError(t, sa.Replay(testContext, rb, cutoverNative(rb, "change-b")))
	require.NoError(t, sb.Replay(testContext, ra, cutoverNative(ra, "change-a")))
	left, err := sa.ReadObject(testContext, ra.ObjectID, 100)
	require.NoError(t, err)
	right, err := sb.ReadObject(testContext, ra.ObjectID, 100)
	require.NoError(t, err)
	require.Equal(t, left, right)
	require.Len(t, left.Claims, 2)
	require.Empty(t, left.Conflicts)
	for _, s := range []*CutoverStore{sa, sb} {
		for _, claim := range left.Claims {
			receipts, err := s.Receipts(testContext, claim.ID)
			require.NoError(t, err)
			require.Len(t, receipts, 1)
			require.Equal(t, claim.Record.AuthorID, receipts[0].Creator)
			require.Equal(t, "component-verified-acl", receipts[0].ACLHeadID)
		}
		cutoverCounts(t, s, 2, 2)
	}
	a.reopen(t)
	sa = openCutoverProjection(t, a)
	after, err := sa.ReadObject(testContext, ra.ObjectID, 100)
	require.NoError(t, err)
	require.Equal(t, left, after)
}

func TestCutoverMetadataRecordCollisionHasNoWinnerOrSilentRetry(t *testing.T) {
	fx := openFixture(t, "")
	s := openCutoverProjection(t, fx)
	a, b := cutoverFixtureRecord(t, 1, "writer-a"), cutoverFixtureRecord(t, 1, "writer-b")
	first, err := s.AppendLocal(testContext, a, cutoverNative(a, "first"))
	require.NoError(t, err)
	collision, err := s.AppendLocal(testContext, b, cutoverNative(b, "ordered-conflict"))
	require.NoError(t, err)
	require.Equal(t, CollisionDifferentPayload, collision.Disposition)
	cutoverCounts(t, s, 1, 1)
	require.NoError(t, s.Replay(testContext, b, cutoverNative(b, "remote-conflict")))
	resolution, err := s.ReadRecord(testContext, a.RecordID)
	require.NoError(t, err)
	require.True(t, resolution.Conflict)
	require.Len(t, resolution.Claims, 2)
	retry, err := s.AppendLocal(testContext, a, cutoverNative(a, "retry"))
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.Equal(t, first.ClaimID, retry.ClaimID)
	require.True(t, retry.Resolution.Conflict)
	cutoverCounts(t, s, 2, 2)
	history, err := s.ReadObject(testContext, a.ObjectID, 100)
	require.NoError(t, err)
	require.Len(t, history.Claims, 2)
	require.Len(t, history.Conflicts, 1)
}

func TestCutoverMetadataCommitExitAndFrozenRetry(t *testing.T) {
	path := filepath.Join(t.TempDir(), "cutover-exit.db")
	cmd := exec.Command(os.Args[0], "-test.run=^TestCutoverMetadataCommitChild$")
	cmd.Env = append(os.Environ(), "PINKHA_CUTOVER_COMPONENT_CHILD=1", "PINKHA_CUTOVER_COMPONENT_DB="+path)
	output, err := cmd.CombinedOutput()
	var exitError *exec.ExitError
	require.ErrorAs(t, err, &exitError, string(output))
	require.Equal(t, 17, exitError.ExitCode(), string(output))
	fx := openFixture(t, path)
	s := openCutoverProjection(t, fx)
	record := cutoverFixtureRecord(t, 1, "writer-a")
	retry, err := s.AppendLocal(testContext, record, cutoverNative(record, "retry-after-process-exit"))
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	cutoverCounts(t, s, 1, 1)
	record.SourceHeads = []string{"different-source-head"}
	changed, err := s.AppendLocal(testContext, record, cutoverNative(record, "changed-retry"))
	require.NoError(t, err)
	require.Equal(t, CollisionDifferentPayload, changed.Disposition)
	cutoverCounts(t, s, 1, 1)
	receipts, err := s.Receipts(testContext, retry.ClaimID)
	require.NoError(t, err)
	require.Len(t, receipts, 1)
	require.Equal(t, "durable-before-reply", receipts[0].ChangeID)
}
func TestCutoverMetadataCommitChild(t *testing.T) {
	if os.Getenv("PINKHA_CUTOVER_COMPONENT_CHILD") != "1" {
		t.Skip("separate component process only")
	}
	fx := openFixture(t, os.Getenv("PINKHA_CUTOVER_COMPONENT_DB"))
	s := openCutoverProjection(t, fx)
	record := cutoverFixtureRecord(t, 1, "writer-a")
	out, err := s.AppendLocal(testContext, record, cutoverNative(record, "durable-before-reply"))
	require.NoError(t, err)
	require.Equal(t, Created, out.Disposition)
	os.Exit(17)
}

func TestCutoverMetadataRefusesForeignAuthorSpaceAndMissingACL(t *testing.T) {
	for _, kind := range []string{"author", "space", "acl", "change"} {
		t.Run(kind, func(t *testing.T) {
			fx := openFixture(t, "")
			s := openCutoverProjection(t, fx)
			record := cutoverFixtureRecord(t, 1, "writer-a")
			native := cutoverNative(record, "change")
			switch kind {
			case "author":
				native.Creator = "writer-b"
			case "space":
				record.SpaceID = "foreign-space"
				record.Plan.SpaceID = "foreign-space"
				id, e := record.Plan.ID()
				require.NoError(t, e)
				record.PlanID = id
			case "acl":
				native.ACLHeadID = ""
			case "change":
				native.ID = ""
			}
			_, err := s.AppendLocal(testContext, record, native)
			require.Error(t, err)
			require.Error(t, s.Replay(testContext, record, native))
			cutoverCounts(t, s, 0, 0)
		})
	}
}

func TestCutoverMetadataNeverTruncatesHistoryOrHidesCrossObjectCollision(t *testing.T) {
	fx := openFixture(t, "")
	s := openCutoverProjection(t, fx)
	a := cutoverFixtureRecord(t, 1, "writer-a")
	b := cutoverFixtureRecord(t, 2, "writer-a")
	_, err := s.AppendLocal(testContext, a, cutoverNative(a, "a"))
	require.NoError(t, err)
	_, err = s.AppendLocal(testContext, b, cutoverNative(b, "b"))
	require.NoError(t, err)
	history, err := s.ReadObject(testContext, a.ObjectID, 1)
	require.ErrorIs(t, err, ErrReadLimit)
	require.Empty(t, history.Claims)
	b = a
	b.ObjectID = "another-object"
	plan := *a.Plan
	plan.ObjectID = b.ObjectID
	b.Plan = &plan
	b.PlanID, err = plan.ID()
	require.NoError(t, err)
	require.NoError(t, s.Replay(testContext, b, cutoverNative(b, "foreign-target-variant")))
	history, err = s.ReadObject(testContext, a.ObjectID, 100)
	require.NoError(t, err)
	require.Len(t, history.Conflicts, 1)
	require.Len(t, history.Conflicts[0].Claims, 2)
	require.Len(t, history.Claims, 3)
	objects := map[string]bool{}
	for _, claim := range history.Claims {
		objects[claim.Record.ObjectID] = true
	}
	require.True(t, objects["another-object"])
	require.True(t, objects[a.ObjectID])
}

func TestCutoverMetadataModifyDeleteAndRawWireForgeryRefuse(t *testing.T) {
	fx := openFixture(t, "")
	s := openCutoverProjection(t, fx)
	record := cutoverFixtureRecord(t, 1, "writer-a")
	out, err := s.AppendLocal(testContext, record, cutoverNative(record, "begin"))
	require.NoError(t, err)
	for _, kind := range []string{"modify", "delete", "unknown-wire"} {
		tx, err := s.state.NewTx(testContext)
		require.NoError(t, err)
		builder := &storestate.Builder{}
		switch kind {
		case "modify":
			require.NoError(t, builder.Modify(cutover.CollectionName, out.ClaimID, []string{"digest"}, pb.ModifyOp_Set, "changed"))
		case "delete":
			builder.Delete(cutover.CollectionName, out.ClaimID)
		case "unknown-wire":
			claim, wire, e := cutover.Encode(record)
			require.NoError(t, e)
			wire = []byte(strings.Replace(string(wire), "{\"record\":", "{\"unknown\":1,\"record\":", 1))
			require.NoError(t, builder.Create(cutover.CollectionName, claim.ID, string(wire)))
		}
		err = tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{Id: "forgery-" + kind, Order: "forgery-" + kind,
			Creator: record.AuthorID, AclHeadId: "component-verified-acl", Changes: builder.ChangeSet})
		require.Error(t, err)
		require.NoError(t, tx.Rollback())
		cutoverCounts(t, s, 1, 1)
	}
}

func TestCutoverMetadataCancelledContextCannotWrite(t *testing.T) {
	fx := openFixture(t, "")
	s := openCutoverProjection(t, fx)
	record := cutoverFixtureRecord(t, 1, "writer-a")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	_, err := s.AppendLocal(ctx, record, cutoverNative(record, "cancelled"))
	require.Error(t, err)
	cutoverCounts(t, s, 0, 0)
}
