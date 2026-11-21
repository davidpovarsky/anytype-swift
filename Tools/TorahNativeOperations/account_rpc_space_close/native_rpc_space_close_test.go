package service

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/notifications"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/util/pinkhat2spaceclosetest"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

var t2SpaceCloseFixtureSHA = "UNSET"

const t2SpaceCloseProtocol = "pinkha-t2-generated-byte-space-close-v1"

type t2SCState struct {
	Account         t2AccountState
	Author          string
	Request         []byte
	RequestSHA      string
	CreatedClaimID  string
	CreatedChangeID string
	Claims          map[string][]byte
	Before          map[string]string
	BeforeHeads     []string
	Durable         map[string]string
	DurableHeads    []string
}

func t2SCWait[T any](t *testing.T, ch <-chan T, stage string) T {
	t.Helper()
	timer := time.NewTimer(30 * time.Second)
	defer timer.Stop()
	select {
	case value := <-ch:
		return value
	case <-timer.C:
		t.Fatalf("Space.Close stage %q was not observed within its unchanged 30s bound", stage)
		var zero T
		return zero
	}
}

func t2SCNotificationReady(t *testing.T) {
	t.Helper()
	// The actual account notification loader first discovers its tech-space
	// object with a 30s peer deadline. ACL notification teardown waits for that
	// loader (with its own original one-minute startup bound) before reaching
	// the client cache. Finish this unrelated startup before installing the
	// controlled close race; never spend the race's barriers on account boot.
	service := app.MustComponent[notifications.Notifications](mw.GetApp())
	startup, ok := service.(interface{ LoadFinish() chan struct{} })
	require.True(t, ok, "the original account notification readiness provider is required")
	ready := startup.LoadFinish()
	require.NotNil(t, ready)
	timer := time.NewTimer(time.Minute)
	defer timer.Stop()
	select {
	case <-ready:
	case <-timer.C:
		t.Fatal("original account notification startup did not complete before the Space.Close race")
	}
}

func t2SCHistory(t *testing.T, spc clientspace.Space, rootID string) (map[string]string, []string) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	storage, err := spc.Storage().TreeStorage(ctx, rootID)
	require.NoError(t, err)
	root, err := storage.Root(ctx)
	require.NoError(t, err)
	require.Equal(t, rootID, root.Id)
	values := map[string]string{root.Id: t2Hash(root.RawChange)}
	require.NoError(t, storage.GetAfterAddSeq(ctx, 0, func(_ context.Context, change objecttree.StorageChange) (bool, error) {
		require.NotContains(t, values, change.Id)
		values[change.Id] = t2Hash(change.RawChange)
		return true, nil
	}))
	heads, err := storage.Heads(ctx)
	require.NoError(t, err)
	sort.Strings(heads)
	return values, heads
}

func t2SCVerifyCreated(t *testing.T, response *pb.RpcPinkhaTorahOperationsAppendResponse, request *pb.RpcPinkhaTorahOperationsAppendRequest, author string) []byte {
	t.Helper()
	require.Equal(t, uint32(1), response.ProtocolVersion)
	require.NotNil(t, response.Error)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, response.Error.Code)
	require.Empty(t, response.Error.Issues)
	require.NotNil(t, response.Receipt)
	require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, response.Receipt.Disposition)
	require.NotEmpty(t, response.Receipt.ClaimId)
	require.NotEmpty(t, response.Receipt.ChangeId)
	require.NotNil(t, response.Receipt.Resolution)
	require.False(t, response.Receipt.Resolution.Conflict)
	require.Len(t, response.Receipt.Resolution.Claims, 1)
	claim := response.Receipt.Resolution.Claims[0]
	require.Equal(t, response.Receipt.ClaimId, claim.ClaimId)
	require.NotNil(t, claim.Operation)
	op := claim.Operation
	require.Equal(t, uint32(1), op.Version)
	require.Equal(t, pb.RpcPinkhaTorahOperations_ADD, op.Kind)
	require.Empty(t, op.ObservedClaimIds)
	require.Equal(t, author, op.AuthorId)
	require.Equal(t, request.OperationId, op.OperationId)
	require.Equal(t, request.SpaceId, op.SpaceId)
	require.True(t, proto.Equal(request.Target, op.Target))
	require.True(t, proto.Equal(request.Source, op.Source))
	require.Equal(t, request.Payload, op.Payload)
	canonical, err := (torahops.Operation{Version: op.Version, SpaceID: op.SpaceId, OperationID: op.OperationId,
		AuthorID: op.AuthorId, Kind: torahops.Add,
		Target:  torahops.Target{ObjectID: op.Target.ObjectId, BlockID: op.Target.BlockId},
		Source:  torahops.Source{ProviderID: op.Source.ProviderId, CanonicalRef: op.Source.CanonicalRef},
		Payload: op.Payload, Observed: op.ObservedClaimIds}).CanonicalBytes()
	require.NoError(t, err)
	require.NotEmpty(t, canonical)
	raw, err := proto.Marshal(claim)
	require.NoError(t, err)
	return raw
}

func t2SCTrace(t *testing.T, capture *pinkhat2spaceclosetest.Capture) map[string]any {
	t.Helper()
	report := capture.Report()
	require.Empty(t, report["gate_timeouts"])
	require.Empty(t, report["gate_cancellations"])
	require.Equal(t, false, report["overflow"])
	events := report["events"].([]pinkhat2spaceclosetest.Event)
	expected := map[string]string{
		"lease-settings-held": "", "append-before-native": "",
		"cache-entry-closing-target": "", "cache-entry-closing-private": "",
		"cache-deadline-target": "DEADLINE_EXCEEDED", "cache-deadline-private": "DEADLINE_EXCEEDED",
		"client-cache-close-return": "OK", "settings-close-attempt": "",
		"commit-before-storage": "", "commit-after-storage": "OK", "lease-before-release": "",
		"settings-close-return": "OK", "native-storage-close-attempt": "",
		"native-storage-close-return": "OK", "client-space-close-return": "OK",
	}
	require.Len(t, events, len(expected))
	counts := report["counts"].(map[string]int)
	require.Len(t, counts, len(expected))
	positions := map[string]int{}
	for index, event := range events {
		result, exists := expected[event.Stage]
		require.True(t, exists)
		require.Equal(t, index+1, event.Sequence)
		require.Equal(t, 1, counts[event.Stage])
		require.Equal(t, result, event.Result)
		require.NotEmpty(t, event.ID)
		positions[event.Stage] = event.Sequence
	}
	for _, order := range [][]string{
		{"lease-settings-held", "append-before-native", "cache-entry-closing-target", "cache-entry-closing-private"},
		{"cache-entry-closing-private", "cache-deadline-target", "client-cache-close-return"},
		{"cache-entry-closing-private", "cache-deadline-private", "client-cache-close-return"},
		{"client-cache-close-return", "settings-close-attempt", "commit-before-storage", "commit-after-storage", "lease-before-release", "settings-close-return", "native-storage-close-attempt", "native-storage-close-return", "client-space-close-return"},
	} {
		for index := 1; index < len(order); index++ {
			require.Less(t, positions[order[index-1]], positions[order[index]])
		}
	}
	for _, pair := range [][2]string{
		{"lease-settings-held", "settings-close-attempt"}, {"lease-settings-held", "lease-before-release"},
		{"lease-settings-held", "settings-close-return"}, {"cache-entry-closing-target", "cache-deadline-target"},
		{"cache-entry-closing-private", "cache-deadline-private"}, {"commit-before-storage", "commit-after-storage"},
		{"native-storage-close-attempt", "native-storage-close-return"}, {"client-cache-close-return", "client-space-close-return"},
	} {
		require.True(t, capture.SameIdentity(pair[0], pair[1]), "the original live object identity must be retained")
	}
	return report
}

func t2SCRace(t *testing.T, rpc *t2AccountRPC, state *t2SCState, parent string) map[string]any {
	t.Helper()
	t2SCNotificationReady(t)
	state.Account.OperationID = fmt.Sprintf("%032x", 1)
	rpc.createTarget(&state.Account)
	root, err := torahopscontract.Root(state.Account.SpaceID)
	require.NoError(t, err)
	state.Account.RootID = root.Id
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	t2CreateNativeRPCOperation(t, ctx, &state.Account)
	spc := t2Space(t, state.Account.SpaceID)
	target, err := spc.GetObject(ctx, state.Account.DocumentID)
	require.NoError(t, err)
	private, err := spc.GetObject(ctx, state.Account.RootID)
	require.NoError(t, err)
	provider, ok := spc.(interface {
		PinkhaTorahSettingsTree(context.Context) (objecttree.ObjectTree, error)
	})
	require.True(t, ok)
	settings, err := provider.PinkhaTorahSettingsTree(ctx)
	require.NoError(t, err)
	require.NotNil(t, settings)
	closeOwned, err := space.PinkhaT2OwnedSpaceCloser(ctx, app.MustComponent[space.Service](mw.GetApp()), spc)
	require.NoError(t, err)
	state.Author = app.MustComponent[accountservice.Service](mw.GetApp()).Account().SignKey.GetPublic().Account()
	state.Before, state.BeforeHeads = t2SCHistory(t, spc, state.Account.RootID)
	require.Len(t, state.Before, 2)
	require.Equal(t, []string{state.Account.ChangeID}, state.BeforeHeads)
	request, readRequest := t2NativeRPCRequests(&state.Account)
	seed := t2WireRead(t, readRequest)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, seed.Error.Code)
	require.NotNil(t, seed.Snapshot)
	require.Len(t, seed.Snapshot.Live, 1)
	seedRaw, err := proto.Marshal(seed.Snapshot.Live[0])
	require.NoError(t, err)
	state.Claims = map[string][]byte{state.Account.ClaimID: seedRaw}
	request.OperationId = fmt.Sprintf("%032x", 2)
	state.Request, err = proto.Marshal(request)
	require.NoError(t, err)
	state.RequestSHA = t2Hash(state.Request)
	capture, err := pinkhat2spaceclosetest.Begin([]pinkhat2spaceclosetest.Filter{
		{Stage: "lease-settings-held", ID: settings.Id(), Identity: settings},
		{Stage: "append-before-native", ID: state.Account.RootID, Pause: true},
		{Stage: "cache-entry-closing-target", ID: state.Account.DocumentID, Identity: target},
		{Stage: "cache-entry-closing-private", ID: state.Account.RootID, Identity: private},
		{Stage: "cache-deadline-target", ID: state.Account.DocumentID, Identity: target},
		{Stage: "cache-deadline-private", ID: state.Account.RootID, Identity: private},
		{Stage: "client-cache-close-return", ID: state.Account.SpaceID, Identity: spc},
		{Stage: "settings-close-attempt", ID: settings.Id(), Identity: settings},
		{Stage: "commit-before-storage", ID: state.Account.RootID},
		{Stage: "commit-after-storage", ID: state.Account.RootID, Pause: true},
		{Stage: "lease-before-release", ID: settings.Id(), Identity: settings},
		{Stage: "settings-close-return", ID: settings.Id(), Identity: settings},
		{Stage: "native-storage-close-attempt", ID: state.Account.SpaceID, Identity: spc.Storage()},
		{Stage: "native-storage-close-return", ID: state.Account.SpaceID, Identity: spc.Storage()},
		{Stage: "client-space-close-return", ID: state.Account.SpaceID, Identity: spc},
	})
	require.NoError(t, err)
	// Failure diagnostics are original observations too. Closing this test-only
	// capture releases its own gates; no native lock or lifetime is fabricated.
	t.Cleanup(func() {
		capture.Close()
		raw, encodeErr := json.MarshalIndent(capture.Report(), "", "  ")
		require.NoError(t, encodeErr)
		t2WriteFresh(t, filepath.Join(parent, "race-trace.json"), raw)
	})
	appendDone := make(chan []byte, 1)
	go func() { appendDone <- PinkhaTorahOperationsAppend(state.Request) }()
	t2SCWait(t, capture.Arrival("append-before-native"), "append-before-native")
	targetDone, privateDone, closeDone := make(chan error, 1), make(chan error, 1), make(chan error, 1)
	go func() { targetDone <- spc.Remove(ctx, state.Account.DocumentID) }()
	t2SCWait(t, capture.Arrival("cache-entry-closing-target"), "cache-entry-closing-target")
	go func() { privateDone <- spc.Remove(ctx, state.Account.RootID) }()
	t2SCWait(t, capture.Arrival("cache-entry-closing-private"), "cache-entry-closing-private")
	// Both real cache entries are already Closing before the original owned
	// controller begins teardown. Its unchanged cache uses its original 10s
	// deadline; the private-tree closer cannot silently mask the settings fence.
	go func() { closeDone <- closeOwned(ctx) }()
	t2SCWait(t, capture.Arrival("cache-deadline-target"), "cache-deadline-target")
	t2SCWait(t, capture.Arrival("cache-deadline-private"), "cache-deadline-private")
	t2SCWait(t, capture.Arrival("settings-close-attempt"), "settings-close-attempt")
	require.False(t, capture.Seen("settings-close-return"))
	require.False(t, capture.Seen("native-storage-close-attempt"))
	stillBefore, stillHeads := t2SCHistory(t, spc, state.Account.RootID)
	require.Equal(t, state.Before, stillBefore)
	require.Equal(t, state.BeforeHeads, stillHeads)
	capture.Release("append-before-native")
	t2SCWait(t, capture.Arrival("commit-after-storage"), "commit-after-storage")
	require.False(t, capture.Seen("settings-close-return"))
	require.False(t, capture.Seen("native-storage-close-attempt"))
	state.Durable, state.DurableHeads = t2SCHistory(t, spc, state.Account.RootID)
	require.Len(t, state.Durable, 3)
	for id, hash := range state.Before {
		require.Equal(t, hash, state.Durable[id])
	}
	capture.Release("commit-after-storage")
	appended := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	require.NoError(t, proto.Unmarshal(t2SCWait(t, appendDone, "original-append-return"), appended))
	createdRaw := t2SCVerifyCreated(t, appended, request, state.Author)
	state.CreatedClaimID, state.CreatedChangeID = appended.Receipt.ClaimId, appended.Receipt.ChangeId
	state.Claims[state.CreatedClaimID] = createdRaw
	require.Len(t, state.Claims, 2)
	require.Equal(t, []string{state.CreatedChangeID}, state.DurableHeads)
	require.NotEmpty(t, state.Durable[state.CreatedChangeID])
	require.NotContains(t, state.Before, state.CreatedChangeID)
	require.NoError(t, t2SCWait(t, targetDone, "target-remove-return"))
	require.NoError(t, t2SCWait(t, privateDone, "private-remove-return"))
	require.NoError(t, t2SCWait(t, closeDone, "original-controller-close-return"))
	trace := t2SCTrace(t, capture)
	capture.Close()
	closedTx, closeErr := spc.Storage().AnyStore().ReadTx(ctx)
	if closedTx != nil {
		_ = closedTx.Commit()
	}
	require.Error(t, closeErr)
	require.Nil(t, closedTx)
	require.NoError(t, ctx.Err(), "post-close denial must not be a cancelled probe")
	return map[string]any{"trace": trace, "identity_checks": "ALL_EIGHT_PAIRS_EXACT_SAME_LIVE_INSTANCE",
		"account_notification_startup": "ORIGINAL_LOAD_FINISH_BEFORE_RACE_BARRIERS",
		"cache_close_timeout_seconds":  10, "both_entries_closing_before_controller_close": true,
		"settings_fence_observed_before_and_after_durable_commit": true,
		"post_physical_close_read":                                "DENIED_WITH_LIVE_PROBE_CONTEXT", "native_append": "CREATED_ORIGINAL_RESPONSE",
		"original_controller_close_calls": 1, "raced_generated_append_calls": 1,
		"raw_changes_sha256_before_append": state.Before, "heads_before_append": state.BeforeHeads,
		"raw_changes_sha256_at_durable_boundary": state.Durable, "heads_at_durable_boundary": state.DurableHeads}
}

func t2SCReopen(t *testing.T, state *t2SCState) map[string]any {
	t.Helper()
	spc := t2Space(t, state.Account.SpaceID)
	before, beforeHeads := t2SCHistory(t, spc, state.Account.RootID)
	require.Equal(t, state.Durable, before)
	require.Equal(t, state.DurableHeads, beforeHeads)
	_, readRequest := t2NativeRPCRequests(&state.Account)
	read := t2WireRead(t, readRequest)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, read.Error.Code)
	require.Empty(t, read.Error.Issues)
	require.NotNil(t, read.Snapshot)
	require.Equal(t, pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE, read.Snapshot.Scope)
	require.Equal(t, state.DurableHeads, read.Snapshot.VerifiedLocalHeads)
	require.Empty(t, read.Snapshot.Conflicts)
	require.Empty(t, read.Snapshot.PendingObservedClaimIds)
	require.Len(t, read.Snapshot.Live, 2)
	seen := map[string]bool{}
	for _, claim := range read.Snapshot.Live {
		require.Contains(t, state.Claims, claim.ClaimId)
		require.False(t, seen[claim.ClaimId])
		seen[claim.ClaimId] = true
		expected := proto.Clone(claim)
		require.NoError(t, proto.Unmarshal(state.Claims[claim.ClaimId], expected))
		require.True(t, proto.Equal(expected, claim))
	}
	require.Equal(t, state.RequestSHA, t2Hash(state.Request))
	// Forward the retained original request bytes once, after cold reopen and
	// before any other append; do not regenerate a request or fabricate a reply.
	retry := &pb.RpcPinkhaTorahOperationsAppendResponse{}
	require.NoError(t, proto.Unmarshal(PinkhaTorahOperationsAppend(state.Request), retry))
	require.Equal(t, uint32(1), retry.ProtocolVersion)
	require.NotNil(t, retry.Error)
	require.Equal(t, pb.RpcPinkhaTorahOperationsAppendResponseError_NULL, retry.Error.Code)
	require.Empty(t, retry.Error.Issues)
	require.NotNil(t, retry.Receipt)
	require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, retry.Receipt.Disposition)
	require.Equal(t, state.CreatedClaimID, retry.Receipt.ClaimId)
	require.Empty(t, retry.Receipt.ChangeId)
	require.NotNil(t, retry.Receipt.Resolution)
	require.False(t, retry.Receipt.Resolution.Conflict)
	require.Len(t, retry.Receipt.Resolution.Claims, 1)
	claim := retry.Receipt.Resolution.Claims[0]
	require.Equal(t, state.CreatedClaimID, claim.ClaimId)
	expected := proto.Clone(claim)
	require.NoError(t, proto.Unmarshal(state.Claims[state.CreatedClaimID], expected))
	require.True(t, proto.Equal(expected, claim))
	afterRead := t2WireRead(t, readRequest)
	require.True(t, proto.Equal(read, afterRead), "exact retry must preserve all claims, heads and local watermark")
	after, afterHeads := t2SCHistory(t, spc, state.Account.RootID)
	require.Equal(t, before, after)
	require.Equal(t, beforeHeads, afterHeads)
	return map[string]any{"raw_changes_sha256_before_retry": before, "heads_before_retry": beforeHeads,
		"raw_changes_sha256_after_retry": after, "heads_after_retry": afterHeads,
		"read_before_retry":   "TWO_EXACT_PERSISTED_CLAIMS_LOCAL_VERIFIED_TREE",
		"original_byte_retry": "ALREADY_EXISTS_SAME_PAYLOAD_NO_CHANGE_ID",
		"read_after_retry":    "PROTO_EQUAL_INCLUDING_LOCAL_WATERMARK", "original_request_forwards": 1}
}

func TestT2GeneratedByteSpaceClose(t *testing.T) {
	phase := os.Getenv("PINKHA_T2_SPACE_CLOSE_PHASE")
	root, reportPath := os.Getenv("PINKHA_T2_SPACE_CLOSE_ROOT"), os.Getenv("PINKHA_T2_SPACE_CLOSE_REPORT")
	nonce := os.Getenv("PINKHA_T2_SPACE_CLOSE_NONCE")
	require.Contains(t, []string{"race", "reopen"}, phase)
	require.Equal(t, "new", t2AccountRuntimeRole)
	require.Equal(t, t2HeartPin, vcs.GitCommit)
	require.NotEqual(t, "UNSET", t2AccountFixtureSHA)
	require.NotEqual(t, "UNSET", t2RPCAccountSchemaSHA)
	require.NotEqual(t, "UNSET", t2SpaceCloseFixtureSHA)
	require.Equal(t, t2SpaceCloseFixtureSHA, os.Getenv("PINKHA_T2_SPACE_CLOSE_FIXTURE_SHA"))
	require.NotEmpty(t, nonce)
	require.True(t, filepath.IsAbs(root))
	require.Equal(t, "account-root", filepath.Base(root))
	parent := filepath.Dir(root)
	require.Equal(t, parent, filepath.Dir(reportPath))
	require.Equal(t, phase+".json", filepath.Base(reportPath))
	owner, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	require.NoError(t, err)
	require.Equal(t, string(owner), os.Getenv("PINKHA_T2_SPACE_CLOSE_OWNER_TOKEN"))
	var ownership struct {
		Protocol      string `json:"protocol"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	require.NoError(t, json.Unmarshal(owner, &ownership))
	require.Equal(t, t2SpaceCloseProtocol, ownership.Protocol)
	require.True(t, ownership.SyntheticOnly)
	statePath, keyPath := filepath.Join(parent, "state.json"), filepath.Join(parent, "account-key.private")
	state := &t2SCState{}
	stateSHA := ""
	if phase == "race" {
		entries, readErr := os.ReadDir(root)
		require.NoError(t, readErr)
		require.Empty(t, entries, "never attach to existing user data")
	} else {
		raw, readErr := os.ReadFile(statePath)
		require.NoError(t, readErr)
		stateSHA = t2Hash(raw)
		require.Equal(t, stateSHA, os.Getenv("PINKHA_T2_SPACE_CLOSE_STATE_SHA"))
		require.NoError(t, json.Unmarshal(raw, state))
		require.NotEmpty(t, state.Account.AccountID)
		require.Equal(t, filepath.Base(state.Account.AccountID), state.Account.AccountID)
		entries, readErr := os.ReadDir(filepath.Join(root, state.Account.AccountID))
		require.NoError(t, readErr)
		require.NotEmpty(t, entries, "cold process must reopen the same native account")
	}
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	rpc.invoke(InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	started, stopped, shutdownDone := false, false, false
	shutdown := func() {
		if started && !stopped {
			rpc.invoke(AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{})
			require.Nil(t, mw.GetApp())
			stopped = true
		}
		if !shutdownDone {
			rpc.invoke(AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{})
			shutdownDone = true
		}
	}
	t.Cleanup(shutdown)
	var observation map[string]any
	if phase == "race" {
		wallet := &pb.RpcWalletCreateResponse{}
		rpc.invoke(WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, wallet)
		require.NotEmpty(t, wallet.AccountKey)
		require.NotEmpty(t, wallet.Mnemonic)
		t2WriteFresh(t, keyPath, []byte(wallet.AccountKey))
		needles, marshalErr := json.Marshal([]string{wallet.AccountKey, wallet.Mnemonic})
		require.NoError(t, marshalErr)
		t2WriteFresh(t, filepath.Join(parent, "sensitive-needles.private"), needles)
		created := &pb.RpcAccountCreateResponse{}
		rpc.invoke(AccountCreate, &pb.RpcAccountCreateRequest{Name: "T2 disposable standalone Space close",
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true}, created)
		started = true
		require.NotNil(t, created.Account)
		require.NotEmpty(t, created.Account.Id)
		state.Account.AccountID = created.Account.Id
		observation = t2SCRace(t, rpc, state, parent)
	} else {
		key, readErr := os.ReadFile(keyPath)
		require.NoError(t, readErr)
		require.NotEmpty(t, key)
		rpc.invoke(WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)}, &pb.RpcWalletRecoverResponse{})
		selected := &pb.RpcAccountSelectResponse{}
		rpc.invoke(AccountSelect, &pb.RpcAccountSelectRequest{Id: state.Account.AccountID, RootPath: root,
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true, PreferredSpaceId: state.Account.SpaceID}, selected)
		started = true
		require.NotNil(t, selected.Account)
		require.Equal(t, state.Account.AccountID, selected.Account.Id)
		rpc.invoke(WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.Account.SpaceID}, &pb.RpcWorkspaceOpenResponse{})
		observation = t2SCReopen(t, state)
	}
	shutdown()
	require.True(t, stopped && shutdownDone)
	if phase == "race" {
		raw, encodeErr := json.Marshal(state)
		require.NoError(t, encodeErr)
		t2WriteFresh(t, statePath, raw)
		stateSHA = t2Hash(raw)
	} else {
		raw, readErr := os.ReadFile(statePath)
		require.NoError(t, readErr)
		require.Equal(t, stateSHA, t2Hash(raw))
	}
	raw, err := json.MarshalIndent(map[string]any{"protocol": t2SpaceCloseProtocol, "phase": phase, "nonce": nonce,
		"pid": os.Getpid(), "heart_sha": vcs.GitCommit, "fixture_sha256": t2SpaceCloseFixtureSHA,
		"status": "PASS_ORIGINAL_NATIVE_SPACE_CLOSE_PHASE", "account_id": state.Account.AccountID,
		"space_id": state.Account.SpaceID, "target_id": state.Account.DocumentID, "block_id": state.Account.BlockID,
		"private_root_id": state.Account.RootID, "request_sha256": state.RequestSHA, "state_sha256": stateSHA,
		"created_claim_id": state.CreatedClaimID, "created_change_id": state.CreatedChangeID,
		"observation": observation, "account_stop_verified": stopped, "app_shutdown_verified": shutdownDone,
		"app_capability": "OFF", "instrumentation": "SEPARATE_PINNED_TEST_COMPILE_OVERLAY_NOT_SHIPPED_PRODUCT",
		"response_return_order_relative_to_close": "NOT_ASSERTED", "duplicate_close_completion": "NOT_CLAIMED",
		"settings_delete": "NOT_RUN", "account_switch": "NOT_RUN", "new_engine_parity": "NOT_PROVEN"}, "", "  ")
	require.NoError(t, err)
	t2WriteFresh(t, reportPath, raw)
}
