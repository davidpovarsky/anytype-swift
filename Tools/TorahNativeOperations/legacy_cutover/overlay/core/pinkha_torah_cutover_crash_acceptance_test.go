//go:build pinkha_cutover_acceptance

package core

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"testing"
	"time"

	"github.com/gogo/protobuf/proto"
	"github.com/gogo/protobuf/types"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pb/cutoverpb"
	pbservice "github.com/anyproto/anytype-heart/pb/service"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
)

type cutoverCrashState struct {
	Nonce          string
	CreatePID      int
	AccountID      string
	Scope          *cutoverpb.PinkhaTorahCutoverScope
	Plan           cutover.Plan
	FirstOperation *cutoverpb.PinkhaTorahCutoverOperationRequest
	FirstClaimID   string
	FirstChangeID  string
	Before         []byte
}

func cutoverCrashWriteFresh(t *testing.T, path string, data []byte) {
	t.Helper()
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	require.NoError(t, err)
	_, err = f.Write(data)
	require.NoError(t, err)
	require.NoError(t, f.Sync())
	require.NoError(t, f.Close())
	directory, err := os.Open(filepath.Dir(path))
	require.NoError(t, err)
	require.NoError(t, directory.Sync())
	require.NoError(t, directory.Close())
}
func cutoverCrashJSON(t *testing.T, path string, value any) {
	t.Helper()
	data, err := json.MarshalIndent(value, "", "  ")
	require.NoError(t, err)
	cutoverCrashWriteFresh(t, path, append(data, '\n'))
}
func cutoverCrashRead(t *testing.T, ctx context.Context, client pbservice.ClientCommandsClient, state *cutoverCrashState) *cutoverpb.PinkhaTorahCutoverSnapshot {
	t.Helper()
	r, err := client.PinkhaTorahCutoverRead(ctx, state.Scope)
	require.NoError(t, err)
	require.NotNil(t, r.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, r.Error.Code, r.Error.Description)
	require.NotNil(t, r.Snapshot)
	require.True(t, r.Snapshot.CompleteLocal)
	require.Equal(t, state.Plan.LegacyValue, r.Snapshot.Source.Value)
	require.NotEmpty(t, r.Snapshot.SourceHeads)
	require.NotEmpty(t, r.Snapshot.MetadataHeads)
	require.NotEmpty(t, r.Snapshot.OperationHeads)
	for _, claim := range r.Snapshot.MetadataClaims {
		require.Equal(t, state.AccountID, claim.Record.AuthorId)
	}
	for _, claim := range r.Snapshot.OriginalClaims {
		require.Equal(t, state.AccountID, claim.Operation.AuthorId)
	}
	for _, receipt := range append(slices.Clone(r.Snapshot.MetadataReceipts), r.Snapshot.OriginalReceipts...) {
		require.Equal(t, state.AccountID, receipt.Creator)
		require.NotEmpty(t, receipt.ChangeId)
		require.NotEmpty(t, receipt.AclHeadId)
	}
	return r.Snapshot
}
func cutoverCrashSameSnapshot(t *testing.T, expected, actual *cutoverpb.PinkhaTorahCutoverSnapshot) {
	t.Helper()
	require.Equal(t, expected.State, actual.State)
	require.Equal(t, expected.Source, actual.Source)
	require.Equal(t, expected.SourceHeads, actual.SourceHeads)
	require.Equal(t, expected.MetadataHeads, actual.MetadataHeads)
	require.Equal(t, expected.OperationHeads, actual.OperationHeads)
	require.Equal(t, expected.MetadataClaims, actual.MetadataClaims)
	require.Equal(t, expected.MetadataConflicts, actual.MetadataConflicts)
	require.Equal(t, expected.MetadataReceipts, actual.MetadataReceipts)
	require.Equal(t, expected.OriginalClaims, actual.OriginalClaims)
	require.Equal(t, expected.OriginalReceipts, actual.OriginalReceipts)
}
func cutoverCrashImportOperation(t *testing.T, state *cutoverCrashState, fact cutover.Fact) *cutoverpb.PinkhaTorahCutoverOperationRequest {
	t.Helper()
	planID, err := state.Plan.ID()
	require.NoError(t, err)
	factID, err := fact.ID(state.Scope.SpaceId, state.Scope.ObjectId)
	require.NoError(t, err)
	operationID, err := cutover.ImportOperationID(planID, factID, state.AccountID)
	require.NoError(t, err)
	return &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: state.Scope, PlanId: planID, FactId: factID,
		OperationId: operationID, Kind: pb.RpcPinkhaTorahOperations_ADD, BlockId: fact.BlockID,
		Source:  &pb.RpcPinkhaTorahOperationsSource{ProviderId: fact.ProviderID, CanonicalRef: fact.CanonicalRef},
		Payload: bytes.Clone(fact.Payload)}
}

// The production projection exposes the signed physical import before its
// second metadata phase. The crash boundary requires exactly that import,
// no metadata witness, visible pending work and a refused (nonmutating) Seal.
func cutoverCrashRequireUnwitnessedImport(t *testing.T, ctx context.Context, client pbservice.ClientCommandsClient,
	state *cutoverCrashState, snapshot *cutoverpb.PinkhaTorahCutoverSnapshot) {
	t.Helper()
	require.NotNil(t, snapshot.State)
	require.Equal(t, cutoverpb.PinkhaTorahCutover_PENDING, snapshot.State.Status)
	require.Len(t, state.Plan.Facts, 2)
	require.Len(t, snapshot.State.Imports, 1)
	binding := snapshot.State.Imports[0]
	require.Equal(t, state.FirstOperation.FactId, binding.FactId)
	require.Equal(t, state.FirstClaimID, binding.ClaimId)
	require.Empty(t, binding.MetadataClaimIds, "the durable v1 import has no signed metadata witness")
	require.Len(t, snapshot.MetadataClaims, 1)
	require.Equal(t, cutoverpb.PinkhaTorahCutover_BEGIN, snapshot.MetadataClaims[0].Record.Kind)
	require.Equal(t, state.AccountID, snapshot.MetadataClaims[0].Record.AuthorId)
	require.Len(t, snapshot.MetadataReceipts, 1)
	require.Equal(t, snapshot.MetadataClaims[0].ClaimId, snapshot.MetadataReceipts[0].ClaimId)
	require.Len(t, snapshot.OriginalClaims, 1)
	original := snapshot.OriginalClaims[0]
	require.Equal(t, state.FirstClaimID, original.ClaimId)
	require.Equal(t, state.FirstOperation.OperationId, original.Operation.OperationId)
	require.Equal(t, state.AccountID, original.Operation.AuthorId)
	require.Equal(t, state.FirstOperation.Payload, original.Operation.Payload)
	require.Len(t, snapshot.OriginalReceipts, 1)
	require.Equal(t, state.FirstClaimID, snapshot.OriginalReceipts[0].ClaimId)
	require.Equal(t, state.FirstChangeID, snapshot.OriginalReceipts[0].ChangeId)
	require.Equal(t, state.AccountID, snapshot.OriginalReceipts[0].Creator)
	secondFactID, err := state.Plan.Facts[1].ID(state.Scope.SpaceId, state.Scope.ObjectId)
	require.NoError(t, err)
	require.ElementsMatch(t, []*cutoverpb.PinkhaTorahCutoverIssue{
		{Reason: "importMetadataNotCommitted", Reference: state.FirstClaimID},
		{Reason: "sourceFactNotImported", Reference: secondFactID},
	}, snapshot.State.Pending)
	require.Empty(t, snapshot.State.Seals)
	require.Empty(t, snapshot.State.Conflicts)
	planID, err := state.Plan.ID()
	require.NoError(t, err)
	// Empty bindings are structurally valid, but cannot cover this two-fact
	// source or its missing signed metadata. Refusal must not add any history.
	seal, err := client.PinkhaTorahCutoverAppend(ctx, &cutoverpb.PinkhaTorahCutoverRecordRequest{
		Scope: state.Scope, RecordId: fmt.Sprintf("%032x", 99),
		Kind: cutoverpb.PinkhaTorahCutover_SEAL, PlanId: planID,
	})
	require.NoError(t, err)
	require.NotNil(t, seal.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_INCOMPLETE, seal.Error.Code)
	require.Nil(t, seal.Receipt, "a refused Seal has no committed identity or private resolution")
	cutoverCrashSameSnapshot(t, snapshot, cutoverCrashRead(t, ctx, client, state))
}

func TestPinkhaTorahCutoverCrashPrepare(t *testing.T) { cutoverCrashPhase(t, "prepare") }
func TestPinkhaTorahCutoverCrashResume(t *testing.T)  { cutoverCrashPhase(t, "resume") }
func TestPinkhaTorahCutoverCrashVerify(t *testing.T)  { cutoverCrashPhase(t, "verify") }

func cutoverCrashPhase(t *testing.T, phase string) {
	require.Equal(t, phase, os.Getenv("PINKHA_CUTOVER_CRASH_PHASE"))
	root := os.Getenv("PINKHA_CUTOVER_CRASH_ROOT")
	physical, err := filepath.EvalSymlinks(root)
	require.NoError(t, err)
	require.True(t, filepath.IsAbs(root))
	require.Equal(t, filepath.Clean(root), physical)
	info, err := os.Lstat(root)
	require.NoError(t, err)
	require.True(t, info.IsDir())
	require.EqualValues(t, 0700, info.Mode().Perm())
	owner, err := os.ReadFile(filepath.Join(root, "ownership.json"))
	require.NoError(t, err)
	require.Equal(t, os.Getenv("PINKHA_CUTOVER_CRASH_OWNER"), string(owner))
	var ownership struct {
		Protocol      string
		Nonce         string
		SyntheticOnly bool
	}
	require.NoError(t, json.Unmarshal(owner, &ownership))
	require.Equal(t, "pinkha-cutover-process-crash-v1", ownership.Protocol)
	require.NotEmpty(t, ownership.Nonce)
	require.True(t, ownership.SyntheticOnly)
	accountRoot := filepath.Join(root, "account")
	state := &cutoverCrashState{Nonce: ownership.Nonce, CreatePID: os.Getpid()}
	if phase == "prepare" {
		require.NoError(t, os.Mkdir(accountRoot, 0700))
	} else {
		raw, e := os.ReadFile(filepath.Join(root, "checkpoint.json"))
		require.NoError(t, e)
		require.NoError(t, json.Unmarshal(raw, state))
		require.Equal(t, ownership.Nonce, state.Nonce)
		require.NotEqual(t, state.CreatePID, os.Getpid(), "crash recovery requires a new process")
		require.NotEmpty(t, state.AccountID)
		require.Equal(t, filepath.Base(state.AccountID), state.AccountID)
		entries, e := os.ReadDir(filepath.Join(accountRoot, state.AccountID))
		require.NoError(t, e)
		require.NotEmpty(t, entries)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 480*time.Second)
	defer cancel()
	mw := New()
	service := mw.applicationService
	stopped := false
	shutdown := func() {
		if !stopped {
			require.NoError(t, service.Stop(), "actual native shutdown")
			stopped = true
		}
	}
	t.Cleanup(shutdown)
	service.SetClientVersion("pinkha-cutover-crash-acceptance", "1.0.0")
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	if phase == "prepare" {
		mnemonic, accountKey, e := service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: accountRoot})
		require.NoError(t, e)
		require.NotEmpty(t, accountKey)
		require.NotEmpty(t, mnemonic)
		cutoverCrashWriteFresh(t, filepath.Join(root, "account-key.private"), []byte(accountKey))
		cutoverCrashJSON(t, filepath.Join(root, "sensitive-needles.private"), []string{accountKey, mnemonic})
		account, e := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{Name: "Cutover crash fixture", StorePath: accountRoot, DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly})
		require.NoError(t, e)
		require.NotNil(t, account)
		require.NotNil(t, account.Info)
		state.AccountID = account.Id
		require.NotEmpty(t, state.AccountID)
		spaceID := account.Info.AccountSpaceId
		require.NotEmpty(t, spaceID)
		textValue := func(s string) *types.Value { return &types.Value{Kind: &types.Value_StringValue{StringValue: s}} }
		created := mw.ObjectCreate(ctx, &pb.RpcObjectCreateRequest{SpaceId: spaceID,
			ObjectTypeUniqueKey: domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "page").Marshal(),
			Details:             &types.Struct{Fields: map[string]*types.Value{"name": textValue("Crash retained source")}}})
		require.NotNil(t, created)
		require.NotNil(t, created.Error)
		require.Equal(t, pb.RpcObjectCreateResponseError_NULL, created.Error.Code, created.Error.Description)
		require.NotEmpty(t, created.ObjectId)
		relation := mw.ObjectCreateRelation(ctx, &pb.RpcObjectCreateRelationRequest{SpaceId: spaceID,
			Details: &types.Struct{Fields: map[string]*types.Value{"name": textValue("Crash source property"),
				"relationFormat": {Kind: &types.Value_NumberValue{NumberValue: float64(model.RelationFormat_longtext)}}}}})
		require.NotNil(t, relation)
		require.NotNil(t, relation.Error)
		require.Equal(t, pb.RpcObjectCreateRelationResponseError_NULL, relation.Error.Code, relation.Error.Description)
		require.NotEmpty(t, relation.Key)
		state.Scope = &cutoverpb.PinkhaTorahCutoverScope{ProtocolVersion: 1, SpaceId: spaceID, ObjectId: created.ObjectId, PropertyKey: relation.Key}
		state.Plan = actualCoreSharedCutoverPlan(t, spaceID, created.ObjectId, relation.Key)
		require.Len(t, state.Plan.Facts, 2)
		set := mw.ObjectSetDetails(ctx, &pb.RpcObjectSetDetailsRequest{ContextId: created.ObjectId,
			Details: []*model.Detail{{Key: relation.Key, Value: textValue(string(state.Plan.LegacyValue))}}})
		require.NotNil(t, set)
		require.NotNil(t, set.Error)
		require.Equal(t, pb.RpcObjectSetDetailsResponseError_NULL, set.Error.Code, set.Error.Description)
	} else {
		key, e := os.ReadFile(filepath.Join(root, "account-key.private"))
		require.NoError(t, e)
		require.NoError(t, service.WalletRecover(&pb.RpcWalletRecoverRequest{RootPath: accountRoot, AccountKey: string(key)}))
		selected, e := service.AccountSelect(ctx, &pb.RpcAccountSelectRequest{Id: state.AccountID, RootPath: accountRoot,
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true, PreferredSpaceId: state.Scope.SpaceId})
		require.NoError(t, e)
		require.NotNil(t, selected)
		require.Equal(t, state.AccountID, selected.Id)
	}
	client := newCutoverGeneratedRPCClient(t, mw)
	planID, err := state.Plan.ID()
	require.NoError(t, err)
	if phase == "prepare" {
		source, e := client.PinkhaTorahCutoverSourceRead(ctx, state.Scope)
		require.NoError(t, e)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, source.Error.Code)
		require.Equal(t, state.Plan.LegacyValue, source.Snapshot.Source.Value)
		begun, e := client.PinkhaTorahCutoverAppend(ctx, &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: state.Scope,
			RecordId: fmt.Sprintf("%032x", 1), Kind: cutoverpb.PinkhaTorahCutover_BEGIN, PlanId: planID, Plan: pinkhaCutoverPlanToWire(&state.Plan),
			SourceHeads: slices.Clone(source.Snapshot.SourceHeads)})
		require.NoError(t, e)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, begun.Error.Code)
		require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, begun.Receipt.Disposition)
		state.FirstOperation = cutoverCrashImportOperation(t, state, state.Plan.Facts[0])
		imported, e := client.PinkhaTorahCutoverImport(ctx, state.FirstOperation)
		require.NoError(t, e)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, imported.Error.Code)
		require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, imported.Receipt.Disposition)
		require.NotEmpty(t, imported.Receipt.ChangeId)
		state.FirstClaimID, state.FirstChangeID = imported.Receipt.ClaimId, imported.Receipt.ChangeId
		before := cutoverCrashRead(t, ctx, client, state)
		cutoverCrashRequireUnwitnessedImport(t, ctx, client, state, before)
		state.Before, err = proto.Marshal(before)
		require.NoError(t, err)
		cutoverCrashJSON(t, filepath.Join(root, "checkpoint.json"), state)
		cutoverCrashJSON(t, filepath.Join(root, "ready-for-sigkill.json"), map[string]any{
			"protocol": "pinkha-cutover-process-crash-v1", "nonce": state.Nonce, "pid": os.Getpid(),
			"signedMetadata": 1, "signedV1Imports": 1, "metadataWitnesses": 0, "seals": 0, "gracefulStop": false})
		// The controller must kill this actual test process, after durability but
		// before Import metadata. Cleanup is deliberately never reached.
		<-ctx.Done()
		t.Fatal("controller did not inject SIGKILL at the retained durable boundary")
	}
	if phase == "resume" {
		expected := &cutoverpb.PinkhaTorahCutoverSnapshot{}
		require.NoError(t, proto.Unmarshal(state.Before, expected))
		after := cutoverCrashRead(t, ctx, client, state)
		cutoverCrashSameSnapshot(t, expected, after)
		cutoverCrashRequireUnwitnessedImport(t, ctx, client, state, after)
		retried, e := client.PinkhaTorahCutoverImport(ctx, state.FirstOperation)
		require.NoError(t, e)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, retried.Error.Code)
		require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, retried.Receipt.Disposition)
		require.Equal(t, state.FirstClaimID, retried.Receipt.ClaimId)
		require.Empty(t, retried.Receipt.ChangeId)
		cutoverCrashSameSnapshot(t, after, cutoverCrashRead(t, ctx, client, state))
		var bindings []*cutoverpb.PinkhaTorahCutoverBinding
		var metadataIDs []string
		for i, fact := range state.Plan.Facts {
			operation := cutoverCrashImportOperation(t, state, fact)
			claimID := state.FirstClaimID
			if i > 0 {
				imported, e := client.PinkhaTorahCutoverImport(ctx, operation)
				require.NoError(t, e)
				require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, imported.Error.Code)
				require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, imported.Receipt.Disposition)
				claimID = imported.Receipt.ClaimId
			}
			current := cutoverCrashRead(t, ctx, client, state)
			record := &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: state.Scope, RecordId: fmt.Sprintf("%032x", 10+i),
				Kind: cutoverpb.PinkhaTorahCutover_IMPORT, PlanId: planID, FactId: operation.FactId, ImportClaimId: claimID}
			for _, r := range current.OriginalReceipts {
				if r.ClaimId == claimID {
					if i == 0 {
						require.Equal(t, state.FirstChangeID, r.ChangeId)
					}
					record.NativeChanges = append(record.NativeChanges, &cutoverpb.PinkhaTorahCutoverNativeWitness{ChangeId: r.ChangeId, Creator: r.Creator, AclHeadId: r.AclHeadId})
				}
			}
			require.NotEmpty(t, record.NativeChanges)
			witnessed, e := client.PinkhaTorahCutoverAppend(ctx, record)
			require.NoError(t, e)
			require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, witnessed.Error.Code)
			require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, witnessed.Receipt.Disposition)
			bindings = append(bindings, &cutoverpb.PinkhaTorahCutoverBinding{FactId: operation.FactId, ClaimId: claimID})
			metadataIDs = append(metadataIDs, witnessed.Receipt.ClaimId)
		}
		seal, e := client.PinkhaTorahCutoverAppend(ctx, &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: state.Scope, RecordId: fmt.Sprintf("%032x", 100),
			Kind: cutoverpb.PinkhaTorahCutover_SEAL, PlanId: planID, Imported: bindings, ImportRecords: metadataIDs})
		require.NoError(t, e)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, seal.Error.Code)
		require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, seal.Receipt.Disposition)
		complete := cutoverCrashRead(t, ctx, client, state)
		require.Equal(t, cutoverpb.PinkhaTorahCutover_SEALED, complete.State.Status)
		require.Len(t, complete.State.Imports, 2)
		require.Len(t, complete.State.Seals, 1)
		require.Len(t, complete.MetadataClaims, 4)
		require.Len(t, complete.OriginalClaims, 2)
		require.Empty(t, complete.State.Pending)
		require.Empty(t, complete.State.Conflicts)
		var found bool
		for _, claim := range complete.OriginalClaims {
			if claim.ClaimId == state.FirstClaimID {
				require.Equal(t, expected.OriginalClaims[0], claim)
				found = true
			}
		}
		require.True(t, found, "the interrupted import retains its original signed identity")
		encoded, e := proto.Marshal(complete)
		require.NoError(t, e)
		cutoverCrashWriteFresh(t, filepath.Join(root, "sealed-snapshot.pb"), encoded)
		shutdown()
		cutoverCrashJSON(t, filepath.Join(root, "resume-proof.json"), map[string]any{
			"protocol": "pinkha-cutover-process-crash-v1", "nonce": state.Nonce, "pid": os.Getpid(), "createPID": state.CreatePID,
			"samePendingStateAfterCrash": true, "frozenImportRetryIdempotent": true, "originalNativeReceiptPreserved": true,
			"sourceAndFactBytesPreserved": true, "signedMetadata": 4, "signedV1Imports": 2, "sealed": true, "accountStopped": stopped})
	} else {
		require.Equal(t, "verify", phase)
		raw, e := os.ReadFile(filepath.Join(root, "sealed-snapshot.pb"))
		require.NoError(t, e)
		expected := &cutoverpb.PinkhaTorahCutoverSnapshot{}
		require.NoError(t, proto.Unmarshal(raw, expected))
		final := cutoverCrashRead(t, ctx, client, state)
		cutoverCrashSameSnapshot(t, expected, final)
		require.Equal(t, cutoverpb.PinkhaTorahCutover_SEALED, final.State.Status)
		require.Len(t, final.MetadataClaims, 4)
		require.Len(t, final.OriginalClaims, 2)
		shutdown()
		cutoverCrashJSON(t, filepath.Join(root, "verify-proof.json"), map[string]any{
			"protocol": "pinkha-cutover-process-crash-v1", "nonce": state.Nonce, "pid": os.Getpid(), "createPID": state.CreatePID,
			"exactSealedNativeHistoryPreserved": true, "sourceAndFactBytesPreserved": true, "accountStopped": stopped,
			"generatedGRPC": true, "newProcessReopen": true, "peerTransport": false, "appleUI": false})
	}
}
