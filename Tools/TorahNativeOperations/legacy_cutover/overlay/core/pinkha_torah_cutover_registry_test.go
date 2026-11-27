//go:build pinkha_cutover_acceptance

package core

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/types"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space"
)

// This is one real LocalOnly account using the actual application, Space,
// factory, object cache, signed trees and persisted source property. There is
// no replacement account, host, lease, ACL or property reader. Peer transport,
// generated RPC and Apple UI remain separate qualifications.
func TestPinkhaTorahCutoverActualCoreRegistryAndReopen(t *testing.T) {
	private := os.Getenv("PINKHA_CUTOVER_CORE_PRIVATE_ROOT")
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
	service.SetClientVersion("pinkha-cutover-core-acceptance", "1.0.0")
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	_, _, err = service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: dir})
	require.NoError(t, err)
	account, err := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{
		Name: "Actual cutover registry", StorePath: dir,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly,
	})
	require.NoError(t, err)
	require.NotNil(t, account)
	require.NotNil(t, account.Info)
	require.NotEmpty(t, account.Id)
	require.NotEmpty(t, account.Info.AccountSpaceId)
	accountID, spaceID := account.Id, account.Info.AccountSpaceId
	spaceService, err := app.GetComponent[space.Service](mw.GetApp())
	require.NoError(t, err)
	spc, err := spaceService.Get(ctx, spaceID)
	require.NoError(t, err)

	textValue := func(s string) *types.Value { return &types.Value{Kind: &types.Value_StringValue{StringValue: s}} }
	create := mw.ObjectCreate(ctx, &pb.RpcObjectCreateRequest{
		SpaceId: spaceID, ObjectTypeUniqueKey: domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "page").Marshal(),
		Details: &types.Struct{Fields: map[string]*types.Value{"name": textValue("Cutover source")}},
	})
	require.NotNil(t, create)
	require.NotNil(t, create.Error)
	require.Equal(t, pb.RpcObjectCreateResponseError_NULL, create.Error.Code, create.Error.Description)
	require.NotEmpty(t, create.ObjectId)
	relation := mw.ObjectCreateRelation(ctx, &pb.RpcObjectCreateRelationRequest{
		SpaceId: spaceID, Details: &types.Struct{Fields: map[string]*types.Value{
			"name":           textValue("Retained source associations"),
			"relationFormat": {Kind: &types.Value_NumberValue{NumberValue: float64(model.RelationFormat_longtext)}},
		}},
	})
	require.NotNil(t, relation)
	require.NotNil(t, relation.Error)
	require.Equal(t, pb.RpcObjectCreateRelationResponseError_NULL, relation.Error.Code, relation.Error.Description)
	require.NotEmpty(t, relation.Key)
	req := PinkhaTorahCutoverReadRequest{Version: PinkhaTorahCutoverVersion,
		SpaceID: spaceID, ObjectID: create.ObjectId, PropertyKey: relation.Key}
	v1Root, err := torahopscontract.Root(spaceID)
	require.NoError(t, err)
	v2Root, err := torahcutoverroot.Root(spaceID)
	require.NoError(t, err)
	require.NotEqual(t, v1Root.Id, v2Root.Id)
	requireAbsent := func() {
		t.Helper()
		for _, id := range []string{v1Root.Id, v2Root.Id} {
			exists, err := spc.Storage().HasTree(ctx, id)
			require.NoError(t, err)
			require.False(t, exists, "a read or invalid plan must not create a private tree")
		}
	}
	requireAbsent()
	missing, err := mw.NativeTorahCutoverSourceRead(ctx, req)
	require.NoError(t, err)
	require.Equal(t, relation.Key, missing.Source.Key)
	require.False(t, missing.Source.Present)
	require.Empty(t, missing.Source.Bytes)
	require.NotEmpty(t, missing.SourceHeads)
	unavailable, err := mw.NativeTorahCutoverRead(ctx, req)
	require.ErrorIs(t, err, ErrPinkhaTorahHistoryUnavailable)
	require.Equal(t, torahops.CutoverNativeSnapshot{}, unavailable)
	requireAbsent()

	plan := actualCoreSharedCutoverPlan(t, spaceID, create.ObjectId, relation.Key)
	require.Len(t, plan.Facts, 2)
	require.True(t, plan.ValuePresent)
	setSource := func(value []byte) {
		t.Helper()
		result := mw.ObjectSetDetails(ctx, &pb.RpcObjectSetDetailsRequest{ContextId: create.ObjectId,
			Details: []*model.Detail{{Key: relation.Key, Value: textValue(string(value))}}})
		require.NotNil(t, result)
		require.NotNil(t, result.Error)
		require.Equal(t, pb.RpcObjectSetDetailsResponseError_NULL, result.Error.Code, result.Error.Description)
	}
	setSource(plan.LegacyValue)
	source, err := mw.NativeTorahCutoverSourceRead(ctx, req)
	require.NoError(t, err)
	require.Equal(t, torahops.CutoverLegacyValue{Key: relation.Key, Present: true, Bytes: plan.LegacyValue}, source.Source)
	require.NotEmpty(t, source.SourceHeads)
	requireAbsent()
	planID, err := plan.ID()
	require.NoError(t, err)

	bad := plan
	bad.Facts = slices.Clone(plan.Facts[:1])
	badID, err := bad.ID()
	require.NoError(t, err, "the omitted-fact request has valid wire shape")
	_, err = mw.NativeTorahCutoverAppend(ctx, PinkhaTorahCutoverRecordRequest{
		PinkhaTorahCutoverReadRequest: req, RecordID: fmt.Sprintf("%032x", 999),
		Kind: cutover.Begin, PlanID: badID, Plan: &bad, SourceHeads: slices.Clone(source.SourceHeads),
	})
	require.Error(t, err, "actual shared-codec coverage must reject the omitted source fact")
	requireAbsent()
	badVersion := req
	badVersion.Version++
	zero, err := mw.NativeTorahCutoverSourceRead(ctx, badVersion)
	require.ErrorIs(t, err, torahops.ErrUnsupportedVersion)
	require.Equal(t, PinkhaTorahCutoverSourceSnapshot{}, zero)
	requireAbsent()

	begin := PinkhaTorahCutoverRecordRequest{PinkhaTorahCutoverReadRequest: req,
		RecordID: fmt.Sprintf("%032x", 1), Kind: cutover.Begin, PlanID: planID,
		Plan: &plan, SourceHeads: slices.Clone(source.SourceHeads)}
	written, err := mw.NativeTorahCutoverAppend(ctx, begin)
	require.NoError(t, err)
	require.Equal(t, torahops.Created, written.Disposition)
	require.NotEmpty(t, written.ChangeID)
	require.NotEmpty(t, written.ClaimID)
	read := func() torahops.CutoverNativeSnapshot {
		t.Helper()
		s, err := mw.NativeTorahCutoverRead(ctx, req)
		require.NoError(t, err)
		require.Equal(t, source.Source, s.Source)
		require.Equal(t, source.SourceHeads, s.SourceHeads)
		return s
	}
	pending := read()
	require.Equal(t, torahops.CutoverPending, pending.State.Status)
	require.Len(t, pending.MetadataHistory.Claims, 1)
	require.Equal(t, accountID, pending.MetadataHistory.Claims[0].Record.AuthorID)
	require.Empty(t, pending.OriginalClaims)
	for _, id := range []string{v1Root.Id, v2Root.Id} {
		object, err := spc.GetObject(ctx, id)
		require.NoError(t, err)
		_, err = object.Show()
		require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	}
	retry, err := mw.NativeTorahCutoverAppend(ctx, begin)
	require.NoError(t, err)
	require.Equal(t, torahops.AlreadyExistsSamePayload, retry.Disposition)
	require.Equal(t, pending, read(), "frozen original Begin retry must not append")

	seal := func(id int) PinkhaTorahCutoverRecordRequest {
		t.Helper()
		s := read()
		request := PinkhaTorahCutoverRecordRequest{PinkhaTorahCutoverReadRequest: req,
			RecordID: fmt.Sprintf("%032x", id), Kind: cutover.Seal, PlanID: planID}
		for _, imp := range s.State.Imports {
			if len(imp.MetadataClaims) == 0 {
				continue
			}
			request.Imported = append(request.Imported, cutover.Binding{FactID: imp.FactID, ClaimID: imp.ClaimID})
			request.ImportRecords = append(request.ImportRecords, imp.MetadataClaims...)
		}
		return request
	}
	for index, fact := range plan.Facts {
		factID, err := fact.ID(spaceID, create.ObjectId)
		require.NoError(t, err)
		operationID, err := cutover.ImportOperationID(planID, factID, accountID)
		require.NoError(t, err)
		operation := PinkhaTorahCutoverOperationRequest{PinkhaTorahCutoverReadRequest: req,
			PlanID: planID, FactID: factID, OperationID: operationID, Kind: torahops.Add,
			BlockID: fact.BlockID, Source: torahops.Source{ProviderID: fact.ProviderID, CanonicalRef: fact.CanonicalRef},
			Payload: bytes.Clone(fact.Payload)}
		imported, err := mw.NativeTorahCutoverImport(ctx, operation)
		require.NoError(t, err)
		require.Equal(t, torahops.Created, imported.Disposition)
		require.NotEmpty(t, imported.ChangeID)
		require.NotEmpty(t, imported.ClaimID)
		half := read()
		require.Equal(t, torahops.CutoverPending, half.State.Status)
		earlySeal := seal(200 + index)
		validShape := cutover.Record{Version: cutover.Version, SpaceID: spaceID, ObjectID: create.ObjectId,
			RecordID: earlySeal.RecordID, AuthorID: accountID, Kind: cutover.Seal, PlanID: planID,
			Imported: earlySeal.Imported, ImportRecords: earlySeal.ImportRecords}
		_, err = validShape.CanonicalBytes()
		require.NoError(t, err, "partial-import refusal must reach the actual host authority")
		_, err = mw.NativeTorahCutoverAppend(ctx, earlySeal)
		require.ErrorIs(t, err, cutover.ErrIncomplete)
		require.Equal(t, half, read(), "refused early Seal must retain both actual signed histories")
		record := PinkhaTorahCutoverRecordRequest{PinkhaTorahCutoverReadRequest: req,
			RecordID: fmt.Sprintf("%032x", 10+index), Kind: cutover.Import, PlanID: planID,
			FactID: factID, ImportClaimID: imported.ClaimID}
		for _, receipt := range half.OriginalReceipts[imported.ClaimID] {
			require.Equal(t, imported.ClaimID, receipt.ClaimID)
			require.Equal(t, accountID, receipt.Creator)
			require.NotEmpty(t, receipt.ChangeID)
			require.NotEmpty(t, receipt.ACLHeadID)
			record.NativeChanges = append(record.NativeChanges, cutover.NativeWitness{
				ChangeID: receipt.ChangeID, Creator: receipt.Creator, ACLHeadID: receipt.ACLHeadID})
		}
		require.NotEmpty(t, record.NativeChanges)
		recorded, err := mw.NativeTorahCutoverAppend(ctx, record)
		require.NoError(t, err)
		require.Equal(t, torahops.Created, recorded.Disposition)
		require.NotEmpty(t, recorded.ChangeID)
		stable := read()
		again, err := mw.NativeTorahCutoverImport(ctx, operation)
		require.NoError(t, err)
		require.Equal(t, torahops.AlreadyExistsSamePayload, again.Disposition)
		require.Equal(t, stable, read())
	}
	sealRequest := seal(100)
	sealedReceipt, err := mw.NativeTorahCutoverAppend(ctx, sealRequest)
	require.NoError(t, err)
	require.Equal(t, torahops.Created, sealedReceipt.Disposition)
	require.NotEmpty(t, sealedReceipt.ChangeID)
	sealed := read()
	require.Equal(t, torahops.CutoverSealed, sealed.State.Status)
	require.Len(t, sealed.State.Imports, 2)
	require.Len(t, sealed.State.Seals, 1)
	require.Empty(t, sealed.State.Pending)
	require.Empty(t, sealed.State.Conflicts)
	original, err := mw.NativeTorahTargetRead(ctx, PinkhaTorahReadRequest{
		Version: PinkhaTorahOperationsVersion, SpaceID: spaceID, Target: torahops.Target{ObjectID: create.ObjectId}, Limit: 100})
	require.NoError(t, err)
	require.Len(t, original.Projection.Live, 2, "ordinary v1 reader receives only original compatible claims")
	require.Empty(t, original.Projection.Conflicts)
	require.Empty(t, original.Projection.PendingObserved)
	observed := make([]string, 0, len(original.Projection.Live))
	for _, claim := range original.Projection.Live {
		observed = append(observed, claim.ID)
	}
	slices.Sort(observed)
	remove := PinkhaTorahCutoverOperationRequest{PinkhaTorahCutoverReadRequest: req,
		PlanID: planID, OperationID: fmt.Sprintf("%032x", 300), Kind: torahops.Remove, Observed: observed}
	removed, err := mw.NativeTorahCutoverAssociationAppend(ctx, remove)
	require.NoError(t, err)
	require.Equal(t, torahops.Created, removed.Disposition)
	require.NotEmpty(t, removed.ChangeID)
	final := read()
	require.Equal(t, torahops.CutoverSealed, final.State.Status, "durable Seal survives final unlink")
	require.Equal(t, sealed.State.Seals, final.State.Seals)
	require.Equal(t, sealed.State.Imports, final.State.Imports)
	require.Equal(t, sealed.MetadataHistory, final.MetadataHistory)
	readOriginal := func() torahops.NativeSnapshot {
		t.Helper()
		value, err := mw.NativeTorahTargetRead(ctx, PinkhaTorahReadRequest{
			Version: PinkhaTorahOperationsVersion, SpaceID: spaceID, Target: torahops.Target{ObjectID: create.ObjectId}, Limit: 100})
		require.NoError(t, err)
		require.Empty(t, value.Projection.Live, "retained legacy bytes must not resurrect unlinked sources")
		require.Empty(t, value.Projection.Conflicts)
		require.Empty(t, value.Projection.PendingObserved)
		return value
	}
	empty := readOriginal()
	again, err := mw.NativeTorahCutoverAssociationAppend(ctx, remove)
	require.NoError(t, err)
	require.Equal(t, torahops.AlreadyExistsSamePayload, again.Disposition)
	require.Equal(t, final, read())
	require.Equal(t, empty, readOriginal())

	require.NoError(t, service.Stop())
	closed, err := mw.NativeTorahCutoverRead(ctx, req)
	require.Error(t, err)
	require.Equal(t, torahops.CutoverNativeSnapshot{}, closed)
	closedWrite, err := mw.NativeTorahCutoverAssociationAppend(ctx, remove)
	require.Error(t, err)
	require.Equal(t, torahops.NativeAppendResult{}, closedWrite)
	reopened, err := service.AccountSelect(ctx, &pb.RpcAccountSelectRequest{Id: accountID,
		RootPath: dir, DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly})
	require.NoError(t, err)
	require.Equal(t, accountID, reopened.Id)
	cold := read()
	require.Equal(t, final.State, cold.State)
	require.Equal(t, final.MetadataHeads, cold.MetadataHeads)
	require.Equal(t, final.OperationHeads, cold.OperationHeads)
	require.Equal(t, final.MetadataHistory, cold.MetadataHistory)
	require.Equal(t, final.OriginalClaims, cold.OriginalClaims)
	require.Equal(t, final.MetadataReceipts, cold.MetadataReceipts)
	require.Equal(t, final.OriginalReceipts, cold.OriginalReceipts)
	require.Equal(t, empty.Projection, readOriginal().Projection)

	// The old property API is deliberately retained. A later old-writer change
	// is visible divergence, not a migration, silent union, or source deletion.
	changedLegacy := append(bytes.Clone(plan.LegacyValue), ' ')
	setSource(changedLegacy)
	diverged, err := mw.NativeTorahCutoverRead(ctx, req)
	require.NoError(t, err)
	require.Equal(t, torahops.CutoverDiverged, diverged.State.Status)
	require.NotEmpty(t, diverged.State.Conflicts)
	require.Equal(t, changedLegacy, diverged.Source.Bytes)
	require.True(t, diverged.Source.Present)
	require.Equal(t, final.State.Seals, diverged.State.Seals)
	require.Equal(t, final.State.Imports, diverged.State.Imports)
	refused, err := mw.NativeTorahCutoverAssociationAppend(ctx, remove)
	require.ErrorIs(t, err, cutover.ErrLegacyChanged)
	require.Equal(t, torahops.NativeAppendResult{}, refused)
	metadataRetry, err := mw.NativeTorahCutoverAppend(ctx, begin)
	require.ErrorIs(t, err, cutover.ErrLegacyChanged)
	require.Equal(t, torahops.CutoverNativeAppendResult{}, metadataRetry)
	firstFact := plan.Facts[0]
	firstFactID, err := firstFact.ID(spaceID, create.ObjectId)
	require.NoError(t, err)
	firstOperationID, err := cutover.ImportOperationID(planID, firstFactID, accountID)
	require.NoError(t, err)
	importRetry, err := mw.NativeTorahCutoverImport(ctx, PinkhaTorahCutoverOperationRequest{
		PinkhaTorahCutoverReadRequest: req, PlanID: planID, FactID: firstFactID,
		OperationID: firstOperationID, Kind: torahops.Add, BlockID: firstFact.BlockID,
		Source:  torahops.Source{ProviderID: firstFact.ProviderID, CanonicalRef: firstFact.CanonicalRef},
		Payload: bytes.Clone(firstFact.Payload)})
	require.ErrorIs(t, err, cutover.ErrLegacyChanged)
	require.Equal(t, torahops.NativeAppendResult{}, importRetry)
	after, err := mw.NativeTorahCutoverRead(ctx, req)
	require.NoError(t, err)
	require.Equal(t, diverged, after)
	require.Empty(t, readOriginal().Projection.Live)

	proof, err := json.MarshalIndent(map[string]any{
		"contract": "pinkha-actual-core-cutover-registry-v1", "realAccounts": 1,
		"realLegacyFacts": 2, "signedMetadataRecords": 4, "signedV1ImportClaims": 2,
		"finalUnlinkRetainsSeal": true, "exactFrozenRetries": 4,
		"missingSourceReadCreatesNoRoots": true, "omittedFactCreatesNoRoots": true,
		"incompleteImportSealsRefused": 2, "ordinaryV1ReaderRemainsCompatible": true,
		"actualAccountStoppedAndReopened": true, "reopenUsesSameOSProcess": true,
		"stoppedAccountReadAndWriteRefused": true, "olderPropertyWriterDivergenceVisible": true,
		"divergedMetadataRetryRefused": true, "divergedImportRetryRefused": true,
		"legacyPropertyRetained": true, "peerTransport": false, "generatedRPC": false, "appleUI": false,
	}, "", "  ")
	require.NoError(t, err)
	proofFile, err := os.OpenFile(filepath.Join(dir, "core-cutover-proof.json"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	require.NoError(t, err)
	_, err = proofFile.Write(append(proof, '\n'))
	require.NoError(t, err)
	require.NoError(t, proofFile.Sync())
	require.NoError(t, proofFile.Close())
	t.Log("ACTUAL_CORE_CUTOVER real_account=1 facts=2 signed_metadata=4 native_imports=2 seal_after_unlink=true reopen=same_process old_writer_divergence=true peer=false rpc=false apple=false")
}

func actualCoreSharedCutoverPlan(t *testing.T, spaceID, objectID, key string) cutover.Plan {
	t.Helper()
	path := os.Getenv("PINKHA_CUTOVER_SHARED_FIXTURE")
	want := os.Getenv("PINKHA_CUTOVER_SHARED_FIXTURE_SHA256")
	require.True(t, cutover.Hex(want, 32), "controller pins the actual compiled shared Swift codec")
	physical, err := filepath.EvalSymlinks(path)
	require.NoError(t, err)
	require.True(t, filepath.IsAbs(path))
	require.Equal(t, filepath.Clean(path), physical)
	st, err := os.Lstat(path)
	require.NoError(t, err)
	require.True(t, st.Mode().IsRegular())
	require.NotZero(t, st.Mode().Perm()&0111)
	require.LessOrEqual(t, st.Size(), int64(32*1024*1024))
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
