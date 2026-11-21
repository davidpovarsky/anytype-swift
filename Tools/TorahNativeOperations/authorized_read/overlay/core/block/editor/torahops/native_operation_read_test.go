package torahops

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/block/editor/storestate"
	"github.com/stretchr/testify/require"
)

// Real signed/encrypted private changes, receiving validation, tree storage,
// current signed ACL and projection. Target state is controlled here; actual
// settings/document locks and graph classification have separate adapter tests.
func authorizedFixtureLease(f *nativeFixture, calls *int) OperationTargetsLeaser {
	return func(ctx context.Context, targets []Target) (OperationTargetLease, error) {
		*calls = *calls + 1
		result := OperationTargetLease{ACL: f.acl, SnapshotToken: strings.Repeat("a", 64),
			Reachability: map[Target]OperationTargetReachability{}, Validate: func(c context.Context) error { return c.Err() }, Release: func() {}}
		for _, target := range targets {
			if err := f.validateTarget(ctx, target); err != nil {
				return result, err
			}
			result.Reachability[target] = OperationLiveDocument
		}
		return result, nil
	}
}

func authorizedReadCurrent(ctx context.Context) error { return ctx.Err() }

func authorizedRawOperation(t *testing.T, f *nativeFixture, op Operation) *treechangeproto.RawTreeChangeWithId {
	t.Helper()
	id, wire, err := EncodeClaim(op)
	require.NoError(t, err)
	build := &storestate.Builder{}
	require.NoError(t, build.Create(CollectionName, id, wire))
	data, err := build.StoreChange.Marshal()
	require.NoError(t, err)
	f.tree.Lock()
	raw, err := f.tree.PrepareChange(objecttree.SignableChangeContent{Data: data, Key: f.keys.SignKey, ShouldBeEncrypted: true, Timestamp: 1})
	f.tree.Unlock()
	require.NoError(t, err)
	return raw
}

func authorizedReceive(t *testing.T, f *nativeFixture, changes ...*treechangeproto.RawTreeChangeWithId) {
	t.Helper()
	heads := make([]string, len(changes))
	for index, change := range changes {
		heads[index] = change.Id
	}
	f.tree.Lock()
	_, err := f.tree.AddRawChanges(context.Background(), objecttree.RawChangesPayload{NewHeads: heads, RawChanges: changes})
	f.tree.Unlock()
	require.NoError(t, err)
}

func TestNativeAuthorizedOperationReadCompleteExactConflictClosure(t *testing.T) {
	f, first := nativeFixtureWithPopulatedProjection(t)
	second := first
	second.Target.ObjectID = f.config.TargetRoots[1].Id
	second.Payload = []byte{0x00, 0xff, 'x', '\n'}
	// Native receiving boundary, not a two-client transport claim.
	authorizedReceive(t, f, authorizedRawOperation(t, f, second))
	calls := 0
	lease := authorizedFixtureLease(f, &calls)
	result, err := f.host.ReadAuthorizedOperation(context.Background(), first.OperationID, lease, authorizedReadCurrent)
	require.NoError(t, err)
	require.Equal(t, 1, calls)
	require.True(t, result.Complete)
	require.Equal(t, OperationFound, result.Outcome)
	require.Equal(t, f.space.Id(), result.SpaceID)
	require.Equal(t, f.keys.SignKey.GetPublic().Account(), result.AccountID)
	require.True(t, validHex(result.NativeSnapshotToken, 32))
	require.Len(t, result.Variants, 2)
	want := map[string][]byte{}
	for _, op := range []Operation{first, second} {
		id, _, err := EncodeClaim(op)
		require.NoError(t, err)
		canonical, err := op.CanonicalBytes()
		require.NoError(t, err)
		want[id] = canonical
	}
	for index, variant := range result.Variants {
		require.Equal(t, want[variant.ClaimID], variant.CanonicalBytes)
		require.Equal(t, OperationLiveDocument, variant.Reachability)
		require.Len(t, variant.Provenance, 1)
		require.Equal(t, variant.AuthorID, variant.Provenance[0].Creator)
		require.NotEmpty(t, variant.Provenance[0].NativeChangeID)
		require.NotEmpty(t, variant.Provenance[0].NativeACLHeadID)
		if index > 0 {
			require.Less(t, result.Variants[index-1].ClaimID, variant.ClaimID)
		}
	}
	denied := func(ctx context.Context, targets []Target) (OperationTargetLease, error) {
		value, err := lease(ctx, targets)
		delete(value.Reachability, second.Target)
		return value, err
	}
	result, err = f.host.ReadAuthorizedOperation(context.Background(), first.OperationID, denied, authorizedReadCurrent)
	require.ErrorIs(t, err, ErrOperationTargetUnavailable)
	require.Equal(t, AuthorizedOperationSnapshot{}, result, "no partial conflicting closure")
}

func TestNativeAuthorizedOperationReadRetainsNonLiveHistoryAndLocalAbsence(t *testing.T) {
	f, add := nativeFixtureWithPopulatedProjection(t)
	id, _, err := EncodeClaim(add)
	require.NoError(t, err)
	remove := add
	remove.OperationID = fmt.Sprintf("%032x", 2)
	remove.Kind, remove.Source, remove.Payload, remove.Observed = Remove, Source{}, nil, []string{id}
	_, err = f.host.Append(context.Background(), remove)
	require.NoError(t, err)
	current, err := f.host.ReadTarget(context.Background(), add.Target, 10)
	require.NoError(t, err)
	require.Empty(t, current.Projection.Live)
	calls := 0
	result, err := f.host.ReadAuthorizedOperation(context.Background(), add.OperationID, authorizedFixtureLease(f, &calls), authorizedReadCurrent)
	require.NoError(t, err)
	require.Len(t, result.Variants, 1)
	require.Equal(t, id, result.Variants[0].ClaimID)
	canonical, err := add.CanonicalBytes()
	require.NoError(t, err)
	require.Equal(t, canonical, result.Variants[0].CanonicalBytes)
	result, err = f.host.ReadAuthorizedOperation(context.Background(), fmt.Sprintf("%032x", 999), authorizedFixtureLease(f, &calls), authorizedReadCurrent)
	require.NoError(t, err)
	require.Equal(t, OperationAbsentInVerifiedLocalSnapshot, result.Outcome)
	require.True(t, result.Complete)
	require.Empty(t, result.Variants)
	require.True(t, validHex(result.NativeSnapshotToken, 32))
	require.Equal(t, 2, calls, "absence also needs settings/lifetime authority")
}

func TestNativeAuthorizedOperationReadCurrentACLAndLifetimeFences(t *testing.T) {
	for _, scenario := range []string{"foreign-reader-before-targets", "revoked-after-discovery", "cancelled-after-discovery", "closed-after-discovery", "target-unavailable", "foreign-acl-lease"} {
		t.Run(scenario, func(t *testing.T) {
			f, op := nativeFixtureWithPopulatedProjection(t)
			host := f.host
			member, err := accountdata.NewRandom()
			require.NoError(t, err)
			if scenario == "foreign-reader-before-targets" {
				misbound := *host
				misbound.key = member.SignKey
				host = &misbound
			} else if scenario == "revoked-after-discovery" {
				applyNativeACLRecord(t, f.acl, func() (*consensusproto.RawRecord, error) {
					return f.acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{
						{Identity: member.SignKey.GetPublic(), Permissions: list.AclPermissionsReader},
					}})
				})
				host, err = OpenNativeHost(context.Background(), f.projectionDB, f.space.Id(), f.tree, member.SignKey, f.acquireTarget)
				require.NoError(t, err)
			}
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			active, released, calls := true, 0, 0
			closed := errors.New("owned native host closed")
			current := func(c context.Context) error {
				if !active {
					return closed
				}
				return c.Err()
			}
			lease := func(c context.Context, targets []Target) (OperationTargetLease, error) {
				value, err := authorizedFixtureLease(f, &calls)(c, targets)
				value.Release = func() { released++ }
				switch scenario {
				case "revoked-after-discovery":
					metadata, _, keyErr := crypto.GenerateRandomEd25519KeyPair()
					require.NoError(t, keyErr)
					applyNativeACLRecord(t, f.acl, func() (*consensusproto.RawRecord, error) {
						return f.acl.RecordBuilder().BuildAccountRemove(list.AccountRemovePayload{
							Identities: []crypto.PubKey{member.SignKey.GetPublic()},
							Change:     list.ReadKeyChangePayload{MetadataKey: metadata, ReadKey: crypto.NewAES()},
						})
					})
				case "cancelled-after-discovery":
					cancel()
				case "closed-after-discovery":
					active = false
				case "target-unavailable":
					err = ErrOperationTargetUnavailable
				case "foreign-acl-lease":
					value.ACL = nil
				}
				return value, err
			}
			result, err := host.ReadAuthorizedOperation(ctx, op.OperationID, lease, current)
			require.Error(t, err)
			require.Equal(t, AuthorizedOperationSnapshot{}, result)
			if scenario == "foreign-reader-before-targets" {
				require.Zero(t, calls)
				require.Zero(t, released)
			} else {
				require.Equal(t, 1, calls)
				require.Equal(t, 1, released)
			}
			if scenario == "revoked-after-discovery" || scenario == "foreign-reader-before-targets" {
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			}
			if scenario == "cancelled-after-discovery" {
				require.ErrorIs(t, err, context.Canceled)
			}
			if scenario == "closed-after-discovery" {
				require.ErrorIs(t, err, closed)
			}
		})
	}
}

func TestNativeAuthorizedOperationReadRejectsChangedCandidateClosure(t *testing.T) {
	f, first := nativeFixtureWithPopulatedProjection(t)
	second := first
	second.Target.ObjectID = f.config.TargetRoots[1].Id
	second.Payload = []byte("concurrent variant")
	raw := authorizedRawOperation(t, f, second)
	calls, released := 0, 0
	lease := func(ctx context.Context, targets []Target) (OperationTargetLease, error) {
		require.Equal(t, []Target{first.Target}, targets)
		value, err := authorizedFixtureLease(f, &calls)(ctx, targets)
		value.Release = func() { released++ }
		authorizedReceive(t, f, raw)
		return value, err
	}
	result, err := f.host.ReadAuthorizedOperation(context.Background(), first.OperationID, lease, authorizedReadCurrent)
	require.ErrorIs(t, err, ErrOperationSnapshotChanged)
	require.Equal(t, AuthorizedOperationSnapshot{}, result)
	require.Equal(t, 1, released)
	result, err = f.host.ReadAuthorizedOperation(context.Background(), first.OperationID, authorizedFixtureLease(f, &calls), authorizedReadCurrent)
	require.NoError(t, err)
	require.Len(t, result.Variants, 2)
}

func TestNativeAuthorizedOperationReadReopensExactSignedReceipts(t *testing.T) {
	config, _, author := makeNativeConfigs(t)
	f, err := openNativeFixture(context.Background(), config)
	require.NoError(t, err)
	defer func() {
		if f != nil {
			require.NoError(t, f.Close())
		}
	}()
	op := Operation{Version: Version, SpaceID: f.space.Id(), AuthorID: author, OperationID: strings.Repeat("1", 32),
		Kind: Add, Target: Target{ObjectID: config.TargetRoots[0].Id}, Source: Source{ProviderID: "fixture", CanonicalRef: "שָׁלוֹם"}, Payload: []byte("exact\x00payload")}
	_, err = f.host.Append(context.Background(), op)
	require.NoError(t, err)
	calls := 0
	before, err := f.host.ReadAuthorizedOperation(context.Background(), op.OperationID, authorizedFixtureLease(f, &calls), authorizedReadCurrent)
	require.NoError(t, err)
	require.NoError(t, f.Close())
	f = nil
	f, err = openNativeFixture(context.Background(), config)
	require.NoError(t, err)
	after, err := f.host.ReadAuthorizedOperation(context.Background(), op.OperationID, authorizedFixtureLease(f, &calls), authorizedReadCurrent)
	require.NoError(t, err)
	require.Equal(t, before, after)
}

func TestNativeAuthorizedOperationReadRejectsForgedProjectionProvenance(t *testing.T) {
	f, first := nativeFixtureWithPopulatedProjection(t)
	second := first
	second.OperationID = strings.Repeat("2", 32)
	second.Payload = []byte("different signed operation")
	_, err := f.host.Append(context.Background(), second)
	require.NoError(t, err)
	firstID, _, err := EncodeClaim(first)
	require.NoError(t, err)
	secondID, _, err := EncodeClaim(second)
	require.NoError(t, err)
	old, err := f.host.store.Receipts(context.Background(), firstID)
	require.NoError(t, err)
	other, err := f.host.store.Receipts(context.Background(), secondID)
	require.NoError(t, err)
	for _, receipt := range old {
		require.NoError(t, f.host.store.receipts.DeleteId(context.Background(), receipt.ID))
	}
	forged := other[0]
	forged.ClaimID = firstID
	framed := bytes.NewBufferString("pinkha-t2-receipt-v1\x00")
	putBytes(framed, []byte(firstID))
	putBytes(framed, []byte(forged.ChangeID))
	digest := sha256.Sum256(framed.Bytes())
	forged.ID = hex.EncodeToString(digest[:])
	raw, err := json.Marshal(forged)
	require.NoError(t, err)
	require.NoError(t, f.host.store.receipts.Insert(context.Background(), anyenc.MustParseJson(string(raw))))
	calls := 0
	result, err := f.host.ReadAuthorizedOperation(context.Background(), first.OperationID, authorizedFixtureLease(f, &calls), authorizedReadCurrent)
	require.ErrorIs(t, err, ErrInvalid)
	require.Equal(t, AuthorizedOperationSnapshot{}, result, "an unrelated signed change cannot authorize this payload")
}

func TestNativeAuthorizedOperationReadBoundsNeverReturnPartialClosure(t *testing.T) {
	for _, scenario := range []string{"variant-count", "encoded-response"} {
		t.Run(scenario, func(t *testing.T) {
			f, first := nativeFixtureWithPopulatedProjection(t)
			count := MaxVariants
			if scenario == "encoded-response" {
				count = 52
			}
			changes := make([]*treechangeproto.RawTreeChangeWithId, 0, count)
			for index := 0; index < count; index++ {
				op := first
				op.Payload = []byte(fmt.Sprintf("variant-%03d", index))
				if scenario == "encoded-response" {
					op.Payload = append(op.Payload, bytes.Repeat([]byte{'x'}, MaxPayloadBytes-len(op.Payload))...)
				}
				changes = append(changes, authorizedRawOperation(t, f, op))
			}
			authorizedReceive(t, f, changes...)
			calls := 0
			result, err := f.host.ReadAuthorizedOperation(context.Background(), first.OperationID, authorizedFixtureLease(f, &calls), authorizedReadCurrent)
			require.ErrorIs(t, err, ErrReadLimit)
			require.Equal(t, AuthorizedOperationSnapshot{}, result)
			if scenario == "variant-count" {
				require.Zero(t, calls, "overlarge closure fails before target access")
			}
		})
	}
}

func TestNativeAuthorizedOperationReadInvalidShapeBeforeAuthority(t *testing.T) {
	var host *NativeHost
	for _, id := range []string{"", strings.Repeat("A", 32), strings.Repeat("1", 31), strings.Repeat("x", 32)} {
		result, err := host.ReadAuthorizedOperation(context.Background(), id, nil, nil)
		require.ErrorIs(t, err, ErrInvalid)
		require.Equal(t, AuthorizedOperationSnapshot{}, result)
	}
}
