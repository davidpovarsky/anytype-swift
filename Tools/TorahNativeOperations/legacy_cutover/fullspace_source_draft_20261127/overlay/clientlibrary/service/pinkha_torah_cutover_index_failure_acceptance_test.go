//go:build pinkha_torah_index_acceptance && pinkha_cutover_acceptance

package service

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/types"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	"github.com/anyproto/anytype-heart/core"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pb/cutoverpb"
	pbservice "github.com/anyproto/anytype-heart/pb/service"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/datastore/anystoreprovider"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// One actual private native account, two ORIGINAL generated transports, and a
// real failed index database. Native signed histories use their separate CRDT
// DB. No fake server, mapper, host, signer, author or receipt is substituted.
func TestPinkhaTorahCutoverGeneratedRPCAndByteRetainIndexFailure(t *testing.T) {
	private := os.Getenv("PINKHA_TORAH_INDEX_WIRE_ROOT")
	physical, err := filepath.EvalSymlinks(private)
	require.NoError(t, err)
	require.True(t, filepath.IsAbs(private))
	require.Equal(t, filepath.Clean(private), physical)
	info, err := os.Lstat(private)
	require.NoError(t, err)
	require.True(t, info.IsDir())
	require.EqualValues(t, 0700, info.Mode().Perm())
	dir := filepath.Join(private, t.Name())
	require.NoError(t, os.Mkdir(dir, 0700), "never reuse an existing account")
	require.Nil(t, mw.GetApp())
	ctx, cancel := context.WithTimeout(context.Background(), 240*time.Second)
	defer cancel()
	closedIndex, stopAttempted, stopped := false, false, false
	stop := func() {
		t.Helper()
		if stopAttempted {
			return
		}
		stopAttempted = true
		stopErr := core.PinkhaIndexAcceptanceStopAccount(mw)
		if closedIndex {
			pinkhaRequireOnlyClosedIndexCleanup(t, stopErr)
		} else {
			require.NoError(t, stopErr)
		}
		require.Nil(t, mw.GetApp())
		stopped = true
	}
	t.Cleanup(stop)
	parameters := mw.InitialSetParameters(ctx, &pb.RpcInitialSetParametersRequest{Platform: "test", Version: "1.0.0"})
	require.NotNil(t, parameters.Error)
	require.Equal(t, pb.RpcInitialSetParametersResponseError_NULL, parameters.Error.Code, parameters.Error.Description)
	SetEventHandler(func(*pb.Event) {})
	wallet := mw.WalletCreate(ctx, &pb.RpcWalletCreateRequest{RootPath: dir})
	require.NotNil(t, wallet.Error)
	require.Equal(t, pb.RpcWalletCreateResponseError_NULL, wallet.Error.Code, wallet.Error.Description)
	// Private original credentials are retained only in this mode-0700 fixture.
	// They are never included in the public receipt or assertion descriptions.
	pinkhaIndexWireSave(t, filepath.Join(dir, "private-wallet.json"), wallet)
	createdAccount := mw.AccountCreate(ctx, &pb.RpcAccountCreateRequest{Name: "Index failure wire proof", StorePath: dir, DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly})
	require.NotNil(t, createdAccount.Error)
	require.Equal(t, pb.RpcAccountCreateResponseError_NULL, createdAccount.Error.Code, createdAccount.Error.Description)
	require.NotNil(t, createdAccount.Account)
	require.NotNil(t, createdAccount.Account.Info)
	accountID, spaceID := createdAccount.Account.Id, createdAccount.Account.Info.AccountSpaceId
	require.NotEmpty(t, accountID)
	require.NotEmpty(t, spaceID)
	textValue := func(s string) *types.Value { return &types.Value{Kind: &types.Value_StringValue{StringValue: s}} }
	page := mw.ObjectCreate(ctx, &pb.RpcObjectCreateRequest{SpaceId: spaceID,
		ObjectTypeUniqueKey: domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "page").Marshal(),
		Details:             &types.Struct{Fields: map[string]*types.Value{"name": textValue("Retained signed wire source")}}})
	require.NotNil(t, page.Error)
	require.Equal(t, pb.RpcObjectCreateResponseError_NULL, page.Error.Code, page.Error.Description)
	require.NotEmpty(t, page.ObjectId)
	relation := mw.ObjectCreateRelation(ctx, &pb.RpcObjectCreateRelationRequest{SpaceId: spaceID,
		Details: &types.Struct{Fields: map[string]*types.Value{"name": textValue("Retained source associations"),
			"relationFormat": {Kind: &types.Value_NumberValue{NumberValue: float64(model.RelationFormat_longtext)}}}}})
	require.NotNil(t, relation.Error)
	require.Equal(t, pb.RpcObjectCreateRelationResponseError_NULL, relation.Error.Code, relation.Error.Description)
	plan := pinkhaIndexWireSharedPlan(t, spaceID, page.ObjectId, relation.Key)
	require.Len(t, plan.Facts, 2)
	changed := mw.ObjectSetDetails(ctx, &pb.RpcObjectSetDetailsRequest{ContextId: page.ObjectId,
		Details: []*model.Detail{{Key: relation.Key, Value: textValue(string(plan.LegacyValue))}}})
	require.NotNil(t, changed.Error)
	require.Equal(t, pb.RpcObjectSetDetailsResponseError_NULL, changed.Error.Code, changed.Error.Description)
	client := pinkhaIndexWireClient(t)
	scope := &cutoverpb.PinkhaTorahCutoverScope{ProtocolVersion: 1, SpaceId: spaceID, ObjectId: page.ObjectId, PropertyKey: relation.Key}
	source, err := client.PinkhaTorahCutoverSourceRead(ctx, scope)
	require.NoError(t, err)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, source.Error.Code)
	require.Equal(t, plan.LegacyValue, source.Snapshot.Source.Value)
	planID, err := plan.ID()
	require.NoError(t, err)
	wirePlan := &cutoverpb.PinkhaTorahCutoverPlan{Version: plan.Version, SpaceId: plan.SpaceID, ObjectId: plan.ObjectID, PropertyKey: plan.PropertyKey,
		ValuePresent: plan.ValuePresent, LegacyValue: bytes.Clone(plan.LegacyValue)}
	for _, fact := range plan.Facts {
		wirePlan.Facts = append(wirePlan.Facts, &cutoverpb.PinkhaTorahCutoverFact{BlockId: fact.BlockID, ProviderId: fact.ProviderID, CanonicalRef: fact.CanonicalRef, Payload: bytes.Clone(fact.Payload)})
	}
	begin := &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, RecordId: fmt.Sprintf("%032x", 1), Kind: cutoverpb.PinkhaTorahCutover_BEGIN, PlanId: planID, Plan: wirePlan, SourceHeads: slices.Clone(source.Snapshot.SourceHeads)}
	initial, err := client.PinkhaTorahCutoverAppend(ctx, begin)
	require.NoError(t, err)
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, initial.Error.Code)
	require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, initial.Receipt.Disposition)
	// Both real private roots have now been loaded, indexed and cached by the
	// normal factory. The later failure cannot be an uninitialized-root refusal.
	index := app.MustComponent[objectstore.ObjectStore](mw.GetApp()).SpaceIndex(spaceID)
	metadataRoot, err := torahcutoverroot.Root(spaceID)
	require.NoError(t, err)
	operationRoot, err := torahopscontract.Root(spaceID)
	require.NoError(t, err)
	for _, id := range []string{metadataRoot.Id, operationRoot.Id} {
		head, e := index.GetLastIndexedHeadsHash(ctx, id)
		require.NoError(t, e)
		require.NotEmpty(t, head, "original metadata index must have committed before fault")
	}
	provider := app.MustComponent[anystoreprovider.Provider](mw.GetApp())
	indexDB, err := provider.GetSpaceIndexDb(spaceID)
	require.NoError(t, err)
	crdtDB, err := provider.GetCrdtDb(spaceID).Wait()
	require.NoError(t, err)
	require.NotSame(t, indexDB, crdtDB, "signed store and local index are separate native databases")
	require.NoError(t, indexDB.Close())
	closedIndex = true
	failedTx, err := indexDB.WriteTx(ctx)
	require.ErrorIs(t, err, anystore.ErrDBIsClosed)
	require.Nil(t, failedTx)

	sequence := 0
	saveWire := func(label string, request interface{ Marshal() ([]byte, error) }, response interface{ Marshal() ([]byte, error) }) {
		t.Helper()
		sequence++
		a, e := request.Marshal()
		require.NoError(t, e)
		b, e := response.Marshal()
		require.NoError(t, e)
		pinkhaIndexWireSaveBytes(t, filepath.Join(dir, fmt.Sprintf("%02d-%s-request.pb", sequence, label)), a)
		pinkhaIndexWireSaveBytes(t, filepath.Join(dir, fmt.Sprintf("%02d-%s-response.pb", sequence, label)), b)
	}
	read := func() *cutoverpb.PinkhaTorahCutoverSnapshot {
		t.Helper()
		r, e := client.PinkhaTorahCutoverRead(ctx, scope)
		require.NoError(t, e)
		require.NotNil(t, r.Error)
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, r.Error.Code, r.Error.Description)
		require.NotNil(t, r.Snapshot)
		require.True(t, r.Snapshot.CompleteLocal)
		require.Equal(t, plan.LegacyValue, r.Snapshot.Source.Value)
		return r.Snapshot
	}
	appendRecord := func(label string, request *cutoverpb.PinkhaTorahCutoverRecordRequest, byteTransport bool) *cutoverpb.PinkhaTorahCutoverAppendResponse {
		t.Helper()
		frozen, e := request.Marshal()
		require.NoError(t, e)
		var response *cutoverpb.PinkhaTorahCutoverAppendResponse
		if byteTransport {
			response = &cutoverpb.PinkhaTorahCutoverAppendResponse{}
			require.NoError(t, response.Unmarshal(PinkhaTorahCutoverAppend(frozen)))
		} else {
			response, e = client.PinkhaTorahCutoverAppend(ctx, request)
			require.NoError(t, e)
		}
		after, e := request.Marshal()
		require.NoError(t, e)
		require.Equal(t, frozen, after)
		require.Equal(t, uint32(1), response.ProtocolVersion)
		pinkhaRequireIndexFailureWireError(t, response.Error)
		require.NotNil(t, response.Receipt)
		require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, response.Receipt.Disposition)
		require.NotEmpty(t, response.Receipt.ChangeId)
		require.True(t, cutover.ClaimID(response.Receipt.ClaimId))
		require.Nil(t, response.Receipt.Resolution)
		snapshot := read()
		pinkhaRequireSignedWireReceipt(t, snapshot.MetadataReceipts, response.Receipt.ClaimId, response.Receipt.ChangeId, accountID)
		saveWire(label, request, response)
		// Reconciliation retries only the same immutable request. It must neither
		// mint a new identity nor append a second signed change.
		retry := &cutoverpb.PinkhaTorahCutoverAppendResponse{}
		require.NoError(t, retry.Unmarshal(PinkhaTorahCutoverAppend(frozen)))
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, retry.Error.Code)
		require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, retry.Receipt.Disposition)
		require.Equal(t, response.Receipt.ClaimId, retry.Receipt.ClaimId)
		require.Equal(t, snapshot, read())
		return response
	}
	appendOperation := func(label string, request *cutoverpb.PinkhaTorahCutoverOperationRequest, importing, byteTransport bool) *cutoverpb.PinkhaTorahCutoverOperationResponse {
		t.Helper()
		frozen, e := request.Marshal()
		require.NoError(t, e)
		invokeBytes := PinkhaTorahCutoverAssociationAppend
		if importing {
			invokeBytes = PinkhaTorahCutoverImport
		}
		var response *cutoverpb.PinkhaTorahCutoverOperationResponse
		if byteTransport {
			response = &cutoverpb.PinkhaTorahCutoverOperationResponse{}
			require.NoError(t, response.Unmarshal(invokeBytes(frozen)))
		} else if importing {
			response, e = client.PinkhaTorahCutoverImport(ctx, request)
			require.NoError(t, e)
		} else {
			response, e = client.PinkhaTorahCutoverAssociationAppend(ctx, request)
			require.NoError(t, e)
		}
		after, e := request.Marshal()
		require.NoError(t, e)
		require.Equal(t, frozen, after)
		require.Equal(t, uint32(1), response.ProtocolVersion)
		pinkhaRequireIndexFailureWireError(t, response.Error)
		require.NotNil(t, response.Receipt)
		require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, response.Receipt.Disposition)
		require.NotEmpty(t, response.Receipt.ChangeId)
		require.True(t, cutover.ClaimID(response.Receipt.ClaimId))
		require.Nil(t, response.Receipt.Resolution)
		snapshot := read()
		pinkhaRequireSignedWireReceipt(t, snapshot.OriginalReceipts, response.Receipt.ClaimId, response.Receipt.ChangeId, accountID)
		saveWire(label, request, response)
		retry := &cutoverpb.PinkhaTorahCutoverOperationResponse{}
		require.NoError(t, retry.Unmarshal(invokeBytes(frozen)))
		require.Equal(t, cutoverpb.PinkhaTorahCutoverError_NULL, retry.Error.Code)
		require.Equal(t, pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD, retry.Receipt.Disposition)
		require.Equal(t, response.Receipt.ClaimId, retry.Receipt.ClaimId)
		require.Equal(t, snapshot, read())
		return response
	}
	for i, byteTransport := range []bool{false, true} {
		request := *begin
		request.RecordId = fmt.Sprintf("%032x", 2+i)
		appendRecord(fmt.Sprintf("begin-%t", byteTransport), &request, byteTransport)
	}
	var bindings []*cutoverpb.PinkhaTorahCutoverBinding
	var metadata []string
	for i, fact := range plan.Facts {
		factID, e := fact.ID(spaceID, page.ObjectId)
		require.NoError(t, e)
		operationID, e := cutover.ImportOperationID(planID, factID, accountID)
		require.NoError(t, e)
		operation := &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: scope, PlanId: planID, FactId: factID, OperationId: operationID,
			Kind: pb.RpcPinkhaTorahOperations_ADD, BlockId: fact.BlockID, Source: &pb.RpcPinkhaTorahOperationsSource{ProviderId: fact.ProviderID, CanonicalRef: fact.CanonicalRef}, Payload: bytes.Clone(fact.Payload)}
		imported := appendOperation(fmt.Sprintf("import-%d", i), operation, true, i == 1)
		require.Equal(t, cutoverpb.PinkhaTorahCutover_PENDING, read().State.Status)
		witness := &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, RecordId: fmt.Sprintf("%032x", 10+i), Kind: cutoverpb.PinkhaTorahCutover_IMPORT,
			PlanId: planID, FactId: factID, ImportClaimId: imported.Receipt.ClaimId}
		for _, receipt := range read().OriginalReceipts {
			if receipt.ClaimId == imported.Receipt.ClaimId {
				witness.NativeChanges = append(witness.NativeChanges, &cutoverpb.PinkhaTorahCutoverNativeWitness{ChangeId: receipt.ChangeId, Creator: receipt.Creator, AclHeadId: receipt.AclHeadId})
			}
		}
		require.Len(t, witness.NativeChanges, 1)
		witnessed := appendRecord(fmt.Sprintf("witness-%d", i), witness, i == 1)
		bindings = append(bindings, &cutoverpb.PinkhaTorahCutoverBinding{FactId: factID, ClaimId: imported.Receipt.ClaimId})
		metadata = append(metadata, witnessed.Receipt.ClaimId)
	}
	seal := &cutoverpb.PinkhaTorahCutoverRecordRequest{Scope: scope, RecordId: fmt.Sprintf("%032x", 20), Kind: cutoverpb.PinkhaTorahCutover_SEAL, PlanId: planID, Imported: bindings, ImportRecords: metadata}
	appendRecord("seal", seal, true)
	require.Equal(t, cutoverpb.PinkhaTorahCutover_SEALED, read().State.Status)
	remove := &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: scope, PlanId: planID, OperationId: fmt.Sprintf("%032x", 30), Kind: pb.RpcPinkhaTorahOperations_REMOVE}
	for _, binding := range bindings {
		remove.ObservedClaimIds = append(remove.ObservedClaimIds, binding.ClaimId)
	}
	appendOperation("association-grpc", remove, false, false)
	fact := plan.Facts[0]
	add := &cutoverpb.PinkhaTorahCutoverOperationRequest{Scope: scope, PlanId: planID, OperationId: fmt.Sprintf("%032x", 31), Kind: pb.RpcPinkhaTorahOperations_ADD,
		BlockId: fact.BlockID, Source: &pb.RpcPinkhaTorahOperationsSource{ProviderId: fact.ProviderID, CanonicalRef: fact.CanonicalRef}, Payload: bytes.Clone(fact.Payload)}
	appendOperation("association-bytes", add, false, true)
	final := read()
	require.Equal(t, cutoverpb.PinkhaTorahCutover_SEALED, final.State.Status)
	require.Len(t, final.OriginalClaims, 4)
	require.Len(t, final.MetadataClaims, 6)
	require.Len(t, final.MetadataConflicts, 0)
	require.Equal(t, 9, sequence, "every new post-index-failure native effect must be retained")
	pinkhaIndexWireSave(t, filepath.Join(dir, "final-signed-snapshot.json"), final)
	stop()
	pinkhaIndexWireSave(t, filepath.Join(dir, "proof.json"), map[string]any{
		"status": "PASS_REAL_SIGNED_POST_INDEX_FAILURE_RPC_AND_BYTES", "pid": os.Getpid(), "accountID": accountID, "spaceID": spaceID,
		"physicalIndexDBClosed": true, "signedCRDTDBDistinct": true, "postFailureCreatedChanges": sequence,
		"generatedTransports": []string{"original gRPC", "original gomobile bytes"}, "writeMethods": []string{"Append", "Import", "AssociationAppend"},
		"privateResolutionsWithheld": true, "exactFrozenRetriesDidNotAppend": true, "sourcePropertyUnchanged": true,
		"onlyExpectedClosedIndexCleanupError": true, "accountStopped": stopped, "automaticReplay": false})
}

func pinkhaRequireIndexFailureWireError(t *testing.T, value *cutoverpb.PinkhaTorahCutoverError) {
	t.Helper()
	require.NotNil(t, value)
	// Existing wire version deliberately uses its fixed UNKNOWN label for new
	// index-admission errors. No new enum, raw native error text or success code.
	require.Equal(t, cutoverpb.PinkhaTorahCutoverError_UNKNOWN_ERROR, value.Code)
	require.Equal(t, []cutoverpb.PinkhaTorahCutoverErrorCode{cutoverpb.PinkhaTorahCutoverError_UNKNOWN_ERROR}, value.Issues)
	require.Equal(t, "native cutover failed", value.Description)
}

func pinkhaRequireSignedWireReceipt(t *testing.T, rows []*cutoverpb.PinkhaTorahCutoverNativeReceipt, claim, change, author string) {
	t.Helper()
	count := 0
	for _, row := range rows {
		if row.ClaimId == claim {
			count++
			require.Equal(t, change, row.ChangeId)
			require.Equal(t, author, row.Creator)
			require.NotEmpty(t, row.AclHeadId)
			require.NotEmpty(t, row.Id)
		}
	}
	require.Equal(t, 1, count, "wire ACK must bind the independently read original signed history")
}

func pinkhaRequireOnlyClosedIndexCleanup(t *testing.T, err error) {
	t.Helper()
	require.Error(t, err)
	leaves := 0
	var visit func(error)
	visit = func(current error) {
		require.NotNil(t, current)
		if joined, ok := current.(interface{ Unwrap() []error }); ok {
			for _, child := range joined.Unwrap() {
				if child != nil {
					visit(child)
				}
			}
			return
		}
		if wrapped, ok := current.(interface{ Unwrap() error }); ok && wrapped.Unwrap() != nil {
			visit(wrapped.Unwrap())
			return
		}
		require.True(t, errors.Is(current, anystore.ErrDBIsClosed), "unrelated cleanup error: %v", current)
		leaves++
	}
	visit(err)
	require.Greater(t, leaves, 0)
}

func pinkhaIndexWireClient(t *testing.T) pbservice.ClientCommandsClient {
	t.Helper()
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	server := grpc.NewServer()
	pbservice.RegisterClientCommandsServer(server, mw)
	done := make(chan error, 1)
	go func() { done <- server.Serve(listener) }()
	t.Cleanup(func() {
		server.Stop()
		_ = listener.Close()
		select {
		case serveErr := <-done:
			require.True(t, serveErr == nil || errors.Is(serveErr, grpc.ErrServerStopped), "unexpected generated server outcome: %v", serveErr)
		case <-time.After(5 * time.Second):
			t.Error("generated server did not stop")
		}
	})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	connection, err := grpc.DialContext(ctx, listener.Addr().String(), grpc.WithTransportCredentials(insecure.NewCredentials()), grpc.WithBlock())
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, connection.Close()) })
	return pbservice.NewClientCommandsClient(connection)
}

func pinkhaIndexWireSharedPlan(t *testing.T, spaceID, objectID, key string) cutover.Plan {
	t.Helper()
	path, want := os.Getenv("PINKHA_CUTOVER_SHARED_FIXTURE"), os.Getenv("PINKHA_CUTOVER_SHARED_FIXTURE_SHA256")
	require.True(t, cutover.Hex(want, 32))
	physical, err := filepath.EvalSymlinks(path)
	require.NoError(t, err)
	require.True(t, filepath.IsAbs(path))
	require.Equal(t, filepath.Clean(path), physical)
	info, err := os.Lstat(path)
	require.NoError(t, err)
	require.True(t, info.Mode().IsRegular())
	require.NotZero(t, info.Mode().Perm()&0111)
	require.LessOrEqual(t, info.Size(), int64(32*1024*1024))
	before, err := os.ReadFile(path)
	require.NoError(t, err)
	sum := sha256.Sum256(before)
	require.Equal(t, want, hex.EncodeToString(sum[:]))
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	wire, err := exec.CommandContext(ctx, path, spaceID, objectID, key, "populated").Output()
	require.NoError(t, err)
	require.Greater(t, len(wire), 0)
	require.LessOrEqual(t, len(wire), cutover.MaxPlanBytes)
	decoder := json.NewDecoder(bytes.NewReader(wire))
	decoder.DisallowUnknownFields()
	var plan cutover.Plan
	require.NoError(t, decoder.Decode(&plan))
	require.Equal(t, spaceID, plan.SpaceID)
	require.Equal(t, objectID, plan.ObjectID)
	require.Equal(t, key, plan.PropertyKey)
	require.NoError(t, cutover.ValidateSourceCoverage(plan))
	after, err := os.ReadFile(path)
	require.NoError(t, err)
	require.Equal(t, before, after)
	return plan
}

func pinkhaIndexWireSave(t *testing.T, path string, value any) {
	t.Helper()
	raw, err := json.MarshalIndent(value, "", "  ")
	require.NoError(t, err)
	pinkhaIndexWireSaveBytes(t, path, append(raw, '\n'))
}
func pinkhaIndexWireSaveBytes(t *testing.T, path string, raw []byte) {
	t.Helper()
	require.LessOrEqual(t, len(raw), 8*1024*1024)
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	require.NoError(t, err)
	_, err = file.Write(raw)
	require.NoError(t, err)
	require.NoError(t, file.Sync())
	require.NoError(t, file.Close())
}
