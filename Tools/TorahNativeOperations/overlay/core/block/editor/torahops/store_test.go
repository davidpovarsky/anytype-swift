package torahops

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block/editor/storestate"
	"github.com/anyproto/anytype-heart/pb"
)

var testContext = context.Background()
var testTarget = Target{ObjectID: "disposable-document", BlockID: "stable-block"}

type fixture struct {
	db    anystore.DB
	store *Store
	path  string
}

func openFixture(t *testing.T, path string) *fixture {
	t.Helper()
	if path == "" {
		path = filepath.Join(t.TempDir(), "claims.db")
	}
	db, err := anystore.Open(testContext, path, nil)
	require.NoError(t, err)
	s, err := New(testContext, db, "disposable-space")
	require.NoError(t, err)
	fx := &fixture{db: db, store: s, path: path}
	t.Cleanup(func() {
		if fx.db != nil {
			require.NoError(t, fx.db.Close())
		}
	})
	return fx
}

func (fx *fixture) reopen(t *testing.T) {
	t.Helper()
	require.NoError(t, fx.db.Close())
	db, err := anystore.Open(testContext, fx.path, nil)
	require.NoError(t, err)
	fx.db = db
	fx.store, err = New(testContext, db, "disposable-space")
	require.NoError(t, err)
}

func add(id int, payload string) Operation {
	return Operation{Version: Version, SpaceID: "disposable-space", OperationID: fmt.Sprintf("%032x", id),
		AuthorID: "disposable-account", Kind: Add, Target: testTarget,
		Source: Source{ProviderID: "sefaria", CanonicalRef: "Genesis.1.1"}, Payload: []byte(payload)}
}

func native(id string) NativeChange {
	return NativeChange{ID: id, Order: id, Creator: "disposable-account", ACLHeadID: "verified-native-acl-head"}
}

func claimID(t *testing.T, op Operation) string {
	t.Helper()
	id, _, err := EncodeClaim(op)
	require.NoError(t, err)
	return id
}

func appendLocal(t *testing.T, fx *fixture, op Operation, changeID string) AppendResult {
	t.Helper()
	result, err := fx.store.AppendLocal(testContext, op, native(changeID))
	require.NoError(t, err)
	return result
}

func projection(t *testing.T, fx *fixture) Projection {
	t.Helper()
	p, err := fx.store.ReadTarget(testContext, testTarget, 100)
	require.NoError(t, err)
	return p
}

func counts(t *testing.T, fx *fixture, claims, receipts int) {
	t.Helper()
	n, err := fx.store.claims.Count(testContext)
	require.NoError(t, err)
	require.Equal(t, claims, n)
	n, err = fx.store.receipts.Count(testContext)
	require.NoError(t, err)
	require.Equal(t, receipts, n)
}

func TestIndependentDiskProjectionsPreserveOfflineUnion(t *testing.T) {
	// Two actual independent SQLite stores, followed by explicit component replay.
	// This deliberately does not stand in for two syncing Heart processes.
	a, b := openFixture(t, ""), openFixture(t, "")
	opA, opB := add(1, "A: בראשית"), add(2, "B: commentary")
	require.Equal(t, Created, appendLocal(t, a, opA, "change-A").Disposition)
	require.Equal(t, Created, appendLocal(t, b, opB, "change-B").Disposition)
	a.reopen(t)
	b.reopen(t)
	require.NoError(t, a.store.Replay(testContext, opB, native("change-B")))
	require.NoError(t, b.store.Replay(testContext, opA, native("change-A")))
	require.Len(t, projection(t, a).Live, 2)
	require.Equal(t, projection(t, a), projection(t, b))
	counts(t, a, 2, 2)
	counts(t, b, 2, 2)
	a.reopen(t)
	b.reopen(t)
	require.Equal(t, projection(t, a), projection(t, b))
	for _, fx := range []*fixture{a, b} {
		for _, op := range []Operation{opA, opB} {
			receipts, err := fx.store.Receipts(testContext, claimID(t, op))
			require.NoError(t, err)
			require.Len(t, receipts, 1)
			require.Equal(t, "disposable-account", receipts[0].Creator)
			require.Equal(t, "verified-native-acl-head", receipts[0].ACLHeadID)
		}
	}
}

func TestCommittedProcessExitAndRetry(t *testing.T) {
	path := filepath.Join(t.TempDir(), "committed.db")
	cmd := exec.Command(os.Args[0], "-test.run=^TestCommittedProcessExitHelper$")
	cmd.Env = append(os.Environ(), "PINKHA_T2_EXIT_HELPER=1", "PINKHA_T2_EXIT_DB="+path)
	output, err := cmd.CombinedOutput()
	var exitError *exec.ExitError
	require.ErrorAs(t, err, &exitError, string(output))
	require.Equal(t, 17, exitError.ExitCode(), string(output))
	fx := openFixture(t, path)
	op := add(1, "committed before response")
	retry := appendLocal(t, fx, op, "retry-after-exit")
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.False(t, retry.Resolution.Conflict)
	counts(t, fx, 1, 1)
	op.Payload = []byte("different bytes")
	require.Equal(t, CollisionDifferentPayload, appendLocal(t, fx, op, "ordered-collision").Disposition)
	counts(t, fx, 1, 1)
	fx.reopen(t)
	require.Equal(t, "committed before response", string(projection(t, fx).Live[0].Operation.Payload))
}

func TestCommittedProcessExitHelper(t *testing.T) {
	if os.Getenv("PINKHA_T2_EXIT_HELPER") != "1" {
		t.Skip("subprocess only")
	}
	fx := openFixture(t, os.Getenv("PINKHA_T2_EXIT_DB"))
	require.Equal(t, Created, appendLocal(t, fx, add(1, "committed before response"), "commit-without-response").Disposition)
	// Exit after the real write transaction commits, without Close or cleanup.
	os.Exit(17)
}

func TestOfflineCollisionIsExplicitAndArrivalIndependent(t *testing.T) {
	opA, opB := add(1, "conflicting A"), add(1, "conflicting B")
	var expected Resolution
	for i, ordered := range [][]Operation{{opA, opB}, {opB, opA}} {
		fx := openFixture(t, "")
		for _, op := range ordered {
			require.NoError(t, fx.store.Replay(testContext, op, native("change-"+string(op.Payload))))
		}
		require.NoError(t, fx.store.Replay(testContext, opA, native("duplicate-A")))
		require.NoError(t, fx.store.Replay(testContext, opA, native("duplicate-A")))
		resolution, err := fx.store.ReadOperation(testContext, opA.OperationID)
		require.NoError(t, err)
		require.True(t, resolution.Conflict)
		require.Len(t, resolution.Claims, 2)
		if i == 0 {
			expected = resolution
		} else {
			require.Equal(t, expected, resolution)
		}
		retry := appendLocal(t, fx, opA, "local-retry")
		require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
		require.True(t, retry.Resolution.Conflict)
		p := projection(t, fx)
		require.Empty(t, p.Live)
		require.Equal(t, []Resolution{resolution}, p.Conflicts)
		counts(t, fx, 2, 3)
		fx.reopen(t)
		require.Equal(t, p, projection(t, fx))
	}
}

func TestTargetIndexDoesNotConcealCrossTargetCollision(t *testing.T) {
	fx := openFixture(t, "")
	a, b := add(1, "one"), add(1, "other target")
	b.Target.ObjectID = "different-document"
	require.NoError(t, fx.store.Replay(testContext, a, native("A")))
	require.NoError(t, fx.store.Replay(testContext, b, native("B")))
	for _, target := range []Target{a.Target, b.Target} {
		p, err := fx.store.ReadTarget(testContext, target, 10)
		require.NoError(t, err)
		require.Empty(t, p.Live)
		require.Len(t, p.Conflicts, 1)
		require.Len(t, p.Conflicts[0].Claims, 2)
	}
}

func TestObservedRemoveRetainsUnseenAddAcrossArrivalOrders(t *testing.T) {
	old, fresh := add(1, "observed old"), add(2, "unseen new")
	remove := add(3, "")
	remove.Kind, remove.Source, remove.Observed = Remove, Source{}, []string{claimID(t, old)}
	ops := []Operation{old, fresh, remove}
	for _, order := range [][]int{{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}} {
		t.Run(fmt.Sprint(order), func(t *testing.T) {
			fx := openFixture(t, "")
			for _, i := range order {
				require.NoError(t, fx.store.Replay(testContext, ops[i], native(fmt.Sprint(i))))
			}
			require.NoError(t, fx.store.Replay(testContext, remove, native("2")))
			p := projection(t, fx)
			require.Len(t, p.Live, 1)
			require.Equal(t, claimID(t, fresh), p.Live[0].ID)
			require.Empty(t, p.PendingObserved)
			counts(t, fx, 3, 3)
			fx.reopen(t)
			require.Equal(t, p, projection(t, fx))
		})
	}
}

func TestConcurrentReplacementsRetainBothSuccessors(t *testing.T) {
	old, a, b := add(1, "old"), add(2, "replacement A"), add(3, "replacement B")
	a.Kind, b.Kind = Replace, Replace
	a.Observed, b.Observed = []string{claimID(t, old)}, []string{claimID(t, old)}
	ops := []Operation{old, a, b}
	var expected Projection
	for n, order := range [][]int{{0, 1, 2}, {2, 1, 0}, {1, 0, 2}} {
		fx := openFixture(t, "")
		for _, i := range order {
			require.NoError(t, fx.store.Replay(testContext, ops[i], native(fmt.Sprint(i))))
		}
		p := projection(t, fx)
		require.Len(t, p.Live, 2)
		if n == 0 {
			expected = p
		} else {
			require.Equal(t, expected, p)
		}
		fx.reopen(t)
		require.Equal(t, p, projection(t, fx))
	}
}

func TestLocalConcurrentWritersUseOneNativeTransaction(t *testing.T) {
	for _, sameBytes := range []bool{true, false} {
		t.Run(fmt.Sprintf("same-bytes-%t", sameBytes), func(t *testing.T) {
			fx := openFixture(t, "")
			start := make(chan struct{})
			results := make(chan AppendResult, 2)
			errorsCh := make(chan error, 2)
			var wg sync.WaitGroup
			for i := 0; i < 2; i++ {
				wg.Add(1)
				go func(i int) {
					defer wg.Done()
					op := add(1, "same")
					if !sameBytes {
						op.Payload = []byte(fmt.Sprint(i))
					}
					<-start
					result, err := fx.store.AppendLocal(testContext, op, native(fmt.Sprint(i)))
					results <- result
					errorsCh <- err
				}(i)
			}
			close(start)
			wg.Wait()
			dispositions := map[Disposition]int{}
			for i := 0; i < 2; i++ {
				require.NoError(t, <-errorsCh)
				dispositions[(<-results).Disposition]++
			}
			require.Equal(t, 1, dispositions[Created])
			if sameBytes {
				require.Equal(t, 1, dispositions[AlreadyExistsSamePayload])
			} else {
				require.Equal(t, 1, dispositions[CollisionDifferentPayload])
			}
			counts(t, fx, 1, 1)
		})
	}
}

func TestHandlerRejectsModifyDeleteAndRollsBackPartialBatch(t *testing.T) {
	fx := openFixture(t, "")
	op := add(1, "original")
	id := appendLocal(t, fx, op, "first").ClaimID
	for _, action := range []string{"modify", "delete"} {
		tx, err := fx.store.state.NewTx(testContext)
		require.NoError(t, err)
		build := &storestate.Builder{}
		if action == "modify" {
			require.NoError(t, build.Modify(CollectionName, id, []string{"operation", "payload"}, pb.ModifyOp_Set, "overwritten"))
		} else {
			build.Delete(CollectionName, id)
		}
		err = tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{Id: action, Order: action, Creator: op.AuthorID, AclHeadId: "acl", Changes: build.ChangeSet})
		require.ErrorIs(t, err, storestate.ErrValidation)
		require.NoError(t, tx.Rollback())
	}
	counts(t, fx, 1, 1)
	require.Equal(t, "original", string(projection(t, fx).Live[0].Operation.Payload))
	tx, err := fx.store.state.NewTx(testContext)
	require.NoError(t, err)
	build := &storestate.Builder{}
	newID, wire, err := EncodeClaim(add(2, "must roll back"))
	require.NoError(t, err)
	require.NoError(t, build.Create(CollectionName, newID, wire))
	require.NoError(t, build.Create(CollectionName, "invalid-id", wire))
	err = tx.ApplyChangeSetReturnAllErrors(storestate.ChangeSet{Id: "batch", Order: "batch", Creator: op.AuthorID, AclHeadId: "acl", Changes: build.ChangeSet})
	require.ErrorIs(t, err, storestate.ErrValidation)
	require.NoError(t, tx.Rollback())
	counts(t, fx, 1, 1)
}

func TestNativeValidationCannotBeBypassedByGenericBuilder(t *testing.T) {
	fx := openFixture(t, "")
	op := add(1, "validated")
	id, wire, err := EncodeClaim(op)
	require.NoError(t, err)
	cases := map[string]string{
		"duplicate-key":  strings.Replace(wire, `"version":1`, `"version":1,"version":1`, 1),
		"future-version": strings.Replace(wire, `"version":1`, `"version":2`, 1),
		"wrong-space":    strings.Replace(wire, `disposable-space`, `other-space`, 1),
		"unknown-field":  strings.TrimSuffix(wire, "}") + `,"extra":true}`,
		"hash-tamper":    strings.Replace(wire, `"digest":"`, `"digest":"0`, 1),
		"whitespace":     " " + wire,
		"trailing-data":  wire + "{}",
		"author-spoof":   strings.Replace(wire, `disposable-account`, `another-account`, 1),
	}
	for name, malformed := range cases {
		t.Run(name, func(t *testing.T) {
			tx, beginErr := fx.store.state.NewTx(testContext)
			require.NoError(t, beginErr)
			err := apply(tx, id, malformed, native(name))
			require.Error(t, err)
			require.NoError(t, tx.Rollback())
			counts(t, fx, 0, 0)
		})
	}
	// A correctly rehashed claim still cannot cross the native space/author binding.
	for _, foreign := range []Operation{func() Operation { x := op; x.SpaceID = "other-space"; return x }(), func() Operation { x := op; x.AuthorID = "other-account"; return x }()} {
		foreignID, foreignWire, encodeErr := EncodeClaim(foreign)
		require.NoError(t, encodeErr)
		tx, beginErr := fx.store.state.NewTx(testContext)
		require.NoError(t, beginErr)
		require.ErrorIs(t, apply(tx, foreignID, foreignWire, native("foreign")), storestate.ErrValidation)
		require.NoError(t, tx.Rollback())
	}
	counts(t, fx, 0, 0)
}

func TestNativeProvenanceCannotBeRewritten(t *testing.T) {
	fx := openFixture(t, "")
	op := add(1, "provenance")
	require.NoError(t, fx.store.Replay(testContext, op, native("change")))
	forged := native("change")
	forged.ACLHeadID = "different-acl-for-same-change"
	require.ErrorIs(t, fx.store.Replay(testContext, op, forged), storestate.ErrCritical)
	counts(t, fx, 1, 1)
	receipts, err := fx.store.Receipts(testContext, claimID(t, op))
	require.NoError(t, err)
	require.Equal(t, "verified-native-acl-head", receipts[0].ACLHeadID)
}

func TestSpaceIsolationReadBoundsAndNativeIndex(t *testing.T) {
	fx := openFixture(t, "")
	for i := 1; i <= 3; i++ {
		appendLocal(t, fx, add(i, "bounded"), fmt.Sprint(i))
	}
	_, err := fx.store.ReadTarget(testContext, testTarget, 2)
	require.ErrorIs(t, err, ErrReadLimit)
	other, err := New(testContext, fx.db, "second-disposable-space")
	require.NoError(t, err)
	missing, err := other.ReadOperation(testContext, add(1, "").OperationID)
	require.NoError(t, err)
	require.Empty(t, missing.Claims)
	foreign := add(1, "second-space")
	foreign.SpaceID = "second-disposable-space"
	result, err := other.AppendLocal(testContext, foreign, native("other"))
	require.NoError(t, err)
	require.Equal(t, Created, result.Disposition)
	require.ErrorIs(t, fx.store.Replay(testContext, foreign, native("wrong-space")), ErrInvalid)
	counts(t, fx, 3, 3)
	explanation, err := fx.store.claims.Find(map[string]any{"operation.operationId": add(1, "").OperationID}).Explain(testContext)
	require.NoError(t, err)
	used := false
	for _, index := range explanation.Indexes {
		used = used || (index.Name == "operation" && index.Used)
	}
	require.True(t, used, "lookup must use the actual any-store operation index")
	canceled, cancel := context.WithCancel(testContext)
	cancel()
	_, err = fx.store.ReadOperation(canceled, add(1, "").OperationID)
	require.True(t, errors.Is(err, context.Canceled), "got %v", err)
}
