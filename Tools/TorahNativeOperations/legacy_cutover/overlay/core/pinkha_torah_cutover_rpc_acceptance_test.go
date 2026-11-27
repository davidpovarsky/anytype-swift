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
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
)

// This uses real generated gRPC client/server byte serialization and a real
// native account. The earlier component and typed-core tests are not substituted
// for dispatch through the generated methods.
func TestPinkhaTorahCutoverActualGeneratedRPCAndReopen(t *testing.T) {
	private := os.Getenv("PINKHA_CUTOVER_RPC_PRIVATE_ROOT")
	physical, err := filepath.EvalSymlinks(private)
	require.NoError(t, err)
	st, err := os.Lstat(private)
	require.NoError(t, err)
	require.True(t, filepath.IsAbs(private))
	require.Equal(t, filepath.Clean(private), physical)
	require.True(t, st.IsDir())
	require.Zero(t, st.Mode()&os.ModeSymlink)
	require.EqualValues(t, 0700, st.Mode().Perm())
	dir := filepath.Join(private, t.Name())
	require.NoError(t, os.Mkdir(dir, 0700))
	ctx, cancel := context.WithTimeout(context.Background(), 480*time.Second)
	defer cancel()
	mw := New()
	service := mw.applicationService
	t.Cleanup(func() { require.NoError(t, service.Stop(), "real account shutdown") })
	service.SetClientVersion("pinkha-cutover-generated-rpc-acceptance", "1.0.0")
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	_, _, err = service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: dir})
	require.NoError(t, err)
	account, err := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{Name: "Cutover generated RPC", StorePath: dir, DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly})
	require.NoError(t, err)
	require.NotNil(t, account)
	require.NotNil(t, account.Info)
	accountID, spaceID := account.Id, account.Info.AccountSpaceId
	require.NotEmpty(t, accountID)
	require.NotEmpty(t, spaceID)
	textValue := func(s string) *types.Value { return &types.Value{Kind: &types.Value_StringValue{StringValue: s}} }
	created := mw.ObjectCreate(ctx, &pb.RpcObjectCreateRequest{SpaceId: spaceID,
		ObjectTypeUniqueKey: domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "page").Marshal(),
		Details:             &types.Struct{Fields: map[string]*types.Value{"name": textValue("RPC retained source")}}})
	require.NotNil(t, created)
	require.NotNil(t, created.Error)
	require.Equal(t, pb.RpcObjectCreateResponseError_NULL, created.Error.Code, created.Error.Description)
	require.NotEmpty(t, created.ObjectId)
	relation := mw.ObjectCreateRelation(ctx, &pb.RpcObjectCreateRelationRequest{SpaceId: spaceID, Details: &types.Struct{Fields: map[string]*types.Value{
		"name":           textValue("Retained source associations"),
		"relationFormat": {Kind: &types.Value_NumberValue{NumberValue: float64(model.RelationFormat_longtext)}},
	}}})
	require.NotNil(t, relation)
	require.NotNil(t, relation.Error)
	require.Equal(t, pb.RpcObjectCreateRelationResponseError_NULL, relation.Error.Code, relation.Error.Description)
	require.NotEmpty(t, relation.Key)
	plan := actualCoreSharedCutoverPlan(t, spaceID, created.ObjectId, relation.Key)
	require.Len(t, plan.Facts, 2)
	set := mw.ObjectSetDetails(ctx, &pb.RpcObjectSetDetailsRequest{ContextId: created.ObjectId, Details: []*model.Detail{{Key: relation.Key, Value: textValue(string(plan.LegacyValue))}}})
	require.NotNil(t, set)
	require.NotNil(t, set.Error)
	require.Equal(t, pb.RpcObjectSetDetailsResponseError_NULL, set.Error.Code, set.Error.Description)
	client := newCutoverGeneratedRPCClient(t, mw)
	scope := &cutoverpb.PinkhaTorahCutoverScope{ProtocolVersion: 1, SpaceId: spaceID, ObjectId: created.ObjectId, PropertyKey: relation.Key}
	source, err := client.PinkhaTorahCutoverSourceRead(ctx, scope)
	require.NoError(t, err)
	require.NotNil(t, source.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, source.Error.Code)
	require.NotNil(t, source.Snapshot)
	require.NotNil(t, source.Snapshot.Source)
	require.True(t, source.Snapshot.Source.Present)
	require.Equal(t, plan.LegacyValue, source.Snapshot.Source.Value)
	require.NotEmpty(t, source.Snapshot.SourceHeads)
	planID, err := plan.ID()
	require.NoError(t, err)
	begin := &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, RecordId: fmt.Sprintf("%032x", 1), Kind: cutoverpb.PinkhaTorahCutover_BEGIN,
		PlanId: planID, Plan: pinkhaCutoverPlanToWire(&plan), SourceHeads: slices.Clone(source.Snapshot.SourceHeads)}
	began, err := client.PinkhaTorahCutoverAppend(ctx, begin)
	require.NoError(t, err)
	require.NotNil(t, began.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, began.Error.Code, began.Error.Description)
	require.NotNil(t, began.Receipt)
	require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, began.Receipt.Disposition)
	require.NotEmpty(t, began.Receipt.ChangeId)
	require.NotNil(t, began.Receipt.Resolution)
	require.Len(t, began.Receipt.Resolution.Claims, 1)
	require.Equal(t, accountID, began.Receipt.Resolution.Claims[0].Record.AuthorId)
	read := func() *cutoverpb.PinkhaTorahCutoverSnapshot {
		t.Helper()
		r, e := client.PinkhaTorahCutoverRead(ctx, scope)
		require.NoError(t, e)
		require.NotNil(t, r.Error)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, r.Error.Code, r.Error.Description)
		require.NotNil(t, r.Snapshot)
		require.True(t, r.Snapshot.CompleteLocal)
		require.NotNil(t, r.Snapshot.State)
		require.Equal(t, planID, r.Snapshot.State.PlanId)
		require.Equal(t, plan.LegacyValue, r.Snapshot.Source.Value)
		require.NotEmpty(t, r.Snapshot.SourceHeads)
		require.NotEmpty(t, r.Snapshot.MetadataHeads)
		require.NotEmpty(t, r.Snapshot.OperationHeads)
		for _, c := range r.Snapshot.MetadataClaims {
			require.Equal(t, accountID, c.Record.AuthorId)
		}
		for _, c := range r.Snapshot.OriginalClaims {
			require.Equal(t, accountID, c.Operation.AuthorId)
		}
		for _, receipt := range append(slices.Clone(r.Snapshot.MetadataReceipts), r.Snapshot.OriginalReceipts...) {
			require.Equal(t, accountID, receipt.Creator)
			require.NotEmpty(t, receipt.ChangeId)
			require.NotEmpty(t, receipt.AclHeadId)
		}
		return r.Snapshot
	}
	require.Equal(t, cutoverpb.PinkhaTorahCutover_PENDING, read().State.Status)
	var bindings []*cutoverpb.PinkhaTorahCutoverBinding
	var metadata []string
	var lastImport *cutoverpb.PinkhaTorahCutoverOperationRequest
	for i, fact := range plan.Facts {
		factID, e := fact.ID(spaceID, created.ObjectId)
		require.NoError(t, e)
		operationID, e := cutover.ImportOperationID(planID, factID, accountID)
		require.NoError(t, e)
		operation := &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: scope, PlanId: planID, FactId: factID, OperationId: operationID,
			Kind: pb.RpcPinkhaTorahOperations_ADD, BlockId: fact.BlockID, Source: &pb.RpcPinkhaTorahOperationsSource{ProviderId: fact.ProviderID, CanonicalRef: fact.CanonicalRef}, Payload: bytes.Clone(fact.Payload)}
		imported, e := client.PinkhaTorahCutoverImport(ctx, operation)
		require.NoError(t, e)
		require.NotNil(t, imported.Error)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, imported.Error.Code, imported.Error.Description)
		require.NotNil(t, imported.Receipt)
		require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, imported.Receipt.Disposition)
		require.NotEmpty(t, imported.Receipt.ChangeId)
		half := read()
		require.Equal(t, cutoverpb.PinkhaTorahCutover_PENDING, half.State.Status)
		record := &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, RecordId: fmt.Sprintf("%032x", 10+i), Kind: cutoverpb.PinkhaTorahCutover_IMPORT,
			PlanId: planID, FactId: factID, ImportClaimId: imported.Receipt.ClaimId}
		for _, r := range half.OriginalReceipts {
			if r.ClaimId == imported.Receipt.ClaimId {
				require.Equal(t, imported.Receipt.ChangeId, r.ChangeId)
				record.NativeChanges = append(record.NativeChanges, &cutoverpb.PinkhaTorahCutoverNativeWitness{ChangeId: r.ChangeId, Creator: r.Creator, AclHeadId: r.AclHeadId})
			}
		}
		require.NotEmpty(t, record.NativeChanges)
		witnessed, e := client.PinkhaTorahCutoverAppend(ctx, record)
		require.NoError(t, e)
		require.NotNil(t, witnessed.Error)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, witnessed.Error.Code, witnessed.Error.Description)
		require.NotNil(t, witnessed.Receipt)
		require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, witnessed.Receipt.Disposition)
		bindings = append(bindings, &cutoverpb.PinkhaTorahCutoverBinding{FactId: factID, ClaimId: imported.Receipt.ClaimId})
		metadata = append(metadata, witnessed.Receipt.ClaimId)
		stable := read()
		retry, e := client.PinkhaTorahCutoverImport(ctx, operation)
		require.NoError(t, e)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, retry.Error.Code)
		require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, retry.Receipt.Disposition)
		require.Empty(t, retry.Receipt.ChangeId)
		require.Equal(t, stable, read())
		lastImport = operation
	}
	sealed, e := client.PinkhaTorahCutoverAppend(ctx, &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, RecordId: fmt.Sprintf("%032x", 100),
		Kind: cutoverpb.PinkhaTorahCutover_SEAL, PlanId: planID, Imported: bindings, ImportRecords: metadata})
	require.NoError(t, e)
	require.NotNil(t, sealed.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, sealed.Error.Code, sealed.Error.Description)
	complete := read()
	require.Equal(t, cutoverpb.PinkhaTorahCutover_SEALED, complete.State.Status)
	require.Len(t, complete.State.Seals, 1)
	require.Len(t, complete.MetadataClaims, 4)
	require.Len(t, complete.OriginalClaims, 2)
	// A valid Seal does not invalidate the original frozen import's lost ACK.
	frozen, e := client.PinkhaTorahCutoverImport(ctx, lastImport)
	require.NoError(t, e)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, frozen.Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, frozen.Receipt.Disposition)
	require.Equal(t, complete, read())
	observed := []string{bindings[0].ClaimId, bindings[1].ClaimId}
	slices.Sort(observed)
	removal := &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: scope,
		PlanId: planID, OperationId: fmt.Sprintf("%032x", 200), Kind: pb.RpcPinkhaTorahOperations_REMOVE, ObservedClaimIds: observed}
	removed, e := client.PinkhaTorahCutoverAssociationAppend(ctx, removal)
	require.NoError(t, e)
	require.NotNil(t, removed.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, removed.Error.Code, removed.Error.Description)
	require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, removed.Receipt.Disposition)
	before := read()
	require.Equal(t, cutoverpb.PinkhaTorahCutover_SEALED, before.State.Status)
	require.Equal(t, complete.State.Seals, before.State.Seals)
	require.Len(t, before.OriginalClaims, 3)
	require.Len(t, before.MetadataClaims, 4)
	v1, e := client.PinkhaTorahOperationsReadTarget(ctx, &pb.RpcPinkhaTorahOperationsReadTargetRequest{ProtocolVersion: 1, SpaceId: spaceID, Target: &pb.RpcPinkhaTorahOperationsTarget{ObjectId: created.ObjectId}, Limit: 100})
	require.NoError(t, e)
	require.Equal(t, pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL, v1.Error.Code)
	require.Empty(t, v1.Snapshot.Live)
	require.Empty(t, v1.Snapshot.Conflicts)
	require.Empty(t, v1.Snapshot.PendingObservedClaimIds)
	require.NoError(t, service.Stop())
	closed, e := client.PinkhaTorahCutoverRead(ctx, scope)
	require.NoError(t, e)
	require.NotEqual(t, cutoverpb.PinkhaTorahCutoverError_NULL, closed.Error.Code)
	require.Nil(t, closed.Snapshot)
	reopened, e := service.AccountSelect(ctx, &pb.RpcAccountSelectRequest{Id: accountID, RootPath: dir, DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly})
	require.NoError(t, e)
	require.Equal(t, accountID, reopened.Id)
	after := read()
	require.Equal(t, before.State, after.State)
	require.Equal(t, before.Source, after.Source)
	require.Equal(t, before.SourceHeads, after.SourceHeads)
	require.Equal(t, before.MetadataHeads, after.MetadataHeads)
	require.Equal(t, before.OperationHeads, after.OperationHeads)
	require.Equal(t, before.MetadataClaims, after.MetadataClaims)
	require.Equal(t, before.MetadataReceipts, after.MetadataReceipts)
	require.Equal(t, before.OriginalClaims, after.OriginalClaims)
	require.Equal(t, before.OriginalReceipts, after.OriginalReceipts)
	// Retain actual generated request/response frames for the Swift boundary;
	// these are evidence from real dispatch, never replayed as native authority.
	actualRead, e := client.PinkhaTorahCutoverRead(ctx, scope)
	require.NoError(t, e)
	require.NotNil(t, actualRead.Error)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, actualRead.Error.Code)
	require.Equal(t, after, actualRead.Snapshot)
	for name, message := range map[string]proto.Message{
		"source-read-response.pb":          source,
		"begin-request.pb":                 begin,
		"begin-response.pb":                began,
		"frozen-import-request.pb":         lastImport,
		"frozen-import-response.pb":        frozen,
		"association-append-request.pb":    removal,
		"association-append-response.pb":   removed,
		"sealed-unlinked-read-response.pb": actualRead,
	} {
		encoded, e := proto.Marshal(message)
		require.NoError(t, e)
		file, e := os.OpenFile(filepath.Join(dir, name), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		require.NoError(t, e)
		_, e = file.Write(encoded)
		require.NoError(t, e)
		require.NoError(t, file.Sync())
		require.NoError(t, file.Close())
	}
	proof, e := json.MarshalIndent(map[string]any{"contract": "pinkha-cutover-generated-grpc-v1", "realAccounts": 1, "realLegacyFacts": 2,
		"signedMetadataRecords": 4, "signedV1ImportClaims": 2, "signedV1RemovalClaims": 1, "generatedGRPC": true, "allFiveGeneratedMethodsExecuted": true,
		"sourceBytesRetained": true, "nativeSignersVerified": true, "sealedImportRetryIdempotent": true, "accountStopAndReopen": true,
		"newProcessReopen": false, "peerTransport": false, "appleUI": false}, "", "  ")
	require.NoError(t, e)
	require.NoError(t, os.WriteFile(filepath.Join(dir, "generated-rpc-proof.json"), append(proof, '\n'), 0600))
}
