//go:build pinkha_torah_index_acceptance && pinkha_cutover_acceptance

package core

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/gogo/protobuf/types"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/indexer"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
)

type torahIndexFixtureState struct {
	Nonce          string
	CreatePID      int
	AccountID      string
	Request        PinkhaTorahSpaceIndexRequest
	DocumentID     string
	CanonicalValue string
	DeletedID      string
	Final          contract.Result
}

type torahIndexFixture struct {
	t            *testing.T
	ctx          context.Context
	mw           *Middleware
	root         string
	state        *torahIndexFixtureState
	space        clientspace.Space
	index        spaceindex.Store
	indexer      indexer.Indexer
	observations int
}

func indexText(s string) *types.Value {
	return &types.Value{Kind: &types.Value_StringValue{StringValue: s}}
}
func indexNumber(n float64) *types.Value {
	return &types.Value{Kind: &types.Value_NumberValue{NumberValue: n}}
}

func (f *torahIndexFixture) page(name, uniqueType string, extra map[string]*types.Value) string {
	f.t.Helper()
	fields := map[string]*types.Value{"name": indexText(name)}
	for key, value := range extra {
		fields[key] = value
	}
	r := f.mw.ObjectCreate(f.ctx, &pb.RpcObjectCreateRequest{SpaceId: f.state.Request.SpaceID, ObjectTypeUniqueKey: uniqueType, Details: &types.Struct{Fields: fields}})
	require.NotNil(f.t, r)
	require.NotNil(f.t, r.Error)
	require.Equal(f.t, pb.RpcObjectCreateResponseError_NULL, r.Error.Code, r.Error.Description)
	require.NotEmpty(f.t, r.ObjectId)
	return r.ObjectId
}

func (f *torahIndexFixture) relation(name string, format model.RelationFormat) (id, key string) {
	f.t.Helper()
	r := f.mw.ObjectCreateRelation(f.ctx, &pb.RpcObjectCreateRelationRequest{SpaceId: f.state.Request.SpaceID, Details: &types.Struct{Fields: map[string]*types.Value{
		"name": indexText(name), "relationFormat": indexNumber(float64(format)),
	}}})
	require.NotNil(f.t, r)
	require.NotNil(f.t, r.Error)
	require.Equal(f.t, pb.RpcObjectCreateRelationResponseError_NULL, r.Error.Code, r.Error.Description)
	require.NotEmpty(f.t, r.ObjectId)
	require.NotEmpty(f.t, r.Key)
	return r.ObjectId, r.Key
}

func (f *torahIndexFixture) objectType(name string) (id, key string) {
	f.t.Helper()
	r := f.mw.ObjectCreateObjectType(f.ctx, &pb.RpcObjectCreateObjectTypeRequest{SpaceId: f.state.Request.SpaceID, Details: &types.Struct{Fields: map[string]*types.Value{
		"name": indexText(name), "recommendedLayout": indexNumber(float64(model.ObjectType_basic)),
	}}})
	require.NotNil(f.t, r)
	require.NotNil(f.t, r.Error)
	require.Equal(f.t, pb.RpcObjectCreateObjectTypeResponseError_NULL, r.Error.Code, r.Error.Description)
	require.NotEmpty(f.t, r.ObjectId)
	require.NotNil(f.t, r.Details)
	key = r.Details.Fields["uniqueKey"].GetStringValue()
	require.NotEmpty(f.t, key)
	return r.ObjectId, key
}

func (f *torahIndexFixture) set(id, key, value string) {
	f.t.Helper()
	r := f.mw.ObjectSetDetails(f.ctx, &pb.RpcObjectSetDetailsRequest{ContextId: id, Details: []*model.Detail{{Key: key, Value: indexText(value)}}})
	require.NotNil(f.t, r)
	require.NotNil(f.t, r.Error)
	require.Equal(f.t, pb.RpcObjectSetDetailsResponseError_NULL, r.Error.Code, r.Error.Description)
}

func (f *torahIndexFixture) read(label string) contract.Result {
	f.t.Helper()
	r, err := f.mw.NativeTorahSpaceIndexReadiness(f.ctx, f.state.Request)
	require.NoError(f.t, err, label)
	require.Equal(f.t, contract.Contract, r.Contract)
	require.Equal(f.t, contract.Version, r.Version)
	require.Equal(f.t, f.state.Request.SpaceID, r.SpaceID)
	require.Equal(f.t, f.state.Request.CanonicalKey, r.CanonicalKey)
	digest, err := hex.DecodeString(r.Readiness.Generation)
	require.NoError(f.t, err)
	require.Len(f.t, digest, 32)
	f.observations++
	cutoverCrashJSON(f.t, filepath.Join(f.root, fmt.Sprintf("%s-%03d-%s.json", os.Getenv("PINKHA_TORAH_INDEX_PHASE"), f.observations, label)), r)
	return r
}

func (f *torahIndexFixture) ready(label string) contract.Result {
	f.t.Helper()
	var result contract.Result
	for attempt := 0; attempt < 180; attempt++ {
		result = f.read(label)
		if result.Complete {
			require.Empty(f.t, result.Reasons)
			require.Equal(f.t, "ready-local-snapshot", result.Readiness.State)
			require.Equal(f.t, result.AuthoritativeObjectCount, result.IndexedObjectCount)
			return result
		}
		select {
		case <-f.ctx.Done():
			f.t.Fatal(f.ctx.Err())
		case <-time.After(100 * time.Millisecond):
		}
	}
	f.t.Fatalf("complete native index never became ready: %+v", result)
	return result
}

func (f *torahIndexFixture) bindSchema() (articleTypeKey string) {
	f.t.Helper()
	canonicalID, key := f.relation("Native canonical associations", model.RelationFormat_longtext)
	f.state.Request.CanonicalKey = key
	parentID, parentKey := f.relation("Native parent", model.RelationFormat_object)
	orderID, orderKey := f.relation("Native order", model.RelationFormat_number)
	typesByRole, templatesByRole := map[string]string{}, map[string]string{}
	for _, role := range []string{"chiddush", "article", "research"} {
		typeID, typeKey := f.objectType("Native " + role)
		typesByRole[role] = typeID
		if role == "article" {
			articleTypeKey = typeKey
		}
		templatesByRole[role] = f.page("Native template "+role, domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "template").Marshal(), map[string]*types.Value{"targetObjectType": indexText(typeID)})
	}
	folderID, _ := f.objectType("Native folder")
	bookFolderID, _ := f.objectType("Native book folder")
	manifest := map[string]any{"schemaVersion": 1, "spaceId": f.state.Request.SpaceID, "provisioningState": "complete",
		"documentAssociationsPropertyId": canonicalID, "documentAssociationsPropertyKey": key,
		"parentPropertyId": parentID, "parentPropertyKey": parentKey, "orderPropertyId": orderID, "orderPropertyKey": orderKey,
		"folderTypeId": folderID, "bookFolderTypeId": bookFolderID, "registeredDocumentTypes": typesByRole, "defaultTemplateIds": templatesByRole}
	raw, err := json.Marshal(manifest)
	require.NoError(f.t, err)
	manifestID := f.page(torah.ManifestUniqueKey, domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "page").Marshal(), map[string]*types.Value{"description": indexText(string(raw))})
	manifest["manifestObjectId"] = manifestID
	raw, err = json.Marshal(manifest)
	require.NoError(f.t, err)
	f.set(manifestID, "description", string(raw))
	cutoverCrashJSON(f.t, filepath.Join(f.root, "actual-native-binding.json"), manifest)
	return articleTypeKey
}

func (f *torahIndexFixture) indexDocument(id string) {
	f.t.Helper()
	require.NoError(f.t, f.space.Do(id, func(sb smartblock.SmartBlock) error { return f.indexer.Index(sb.GetDocInfo()) }))
}

func TestPinkhaTorahSpaceIndexActualNativeTransitions(t *testing.T) {
	torahIndexActualPhase(t, "prepare")
}
func TestPinkhaTorahSpaceIndexActualColdProcess(t *testing.T) { torahIndexActualPhase(t, "cold") }

func torahIndexActualPhase(t *testing.T, phase string) {
	require.Equal(t, phase, os.Getenv("PINKHA_TORAH_INDEX_PHASE"))
	root := os.Getenv("PINKHA_TORAH_INDEX_ROOT")
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
	require.Equal(t, os.Getenv("PINKHA_TORAH_INDEX_OWNER"), string(owner))
	var ownership struct {
		Protocol, Nonce string
		SyntheticOnly   bool
	}
	require.NoError(t, json.Unmarshal(owner, &ownership))
	require.Equal(t, "pinkha-heart-torah-fullspace-v1", ownership.Protocol)
	require.True(t, ownership.SyntheticOnly)
	require.NotEmpty(t, ownership.Nonce)
	state := &torahIndexFixtureState{Nonce: ownership.Nonce, CreatePID: os.Getpid(), Request: PinkhaTorahSpaceIndexRequest{Version: 1, NativeSchemaVersion: 1}}
	accountRoot := filepath.Join(root, "account")
	if phase == "prepare" {
		require.NoError(t, os.Mkdir(accountRoot, 0700))
	} else {
		data, e := os.ReadFile(filepath.Join(root, "checkpoint.json"))
		require.NoError(t, e)
		require.NoError(t, json.Unmarshal(data, state))
		require.Equal(t, ownership.Nonce, state.Nonce)
		require.NotEqual(t, state.CreatePID, os.Getpid())
		require.NotEmpty(t, state.AccountID)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 480*time.Second)
	defer cancel()
	mw := New()
	service := mw.applicationService
	stopped := false
	stop := func() {
		if !stopped {
			require.NoError(t, service.Stop())
			stopped = true
		}
	}
	t.Cleanup(stop)
	service.SetClientVersion("pinkha-native-fullspace-acceptance", "1.0.0")
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	if phase == "prepare" {
		mnemonic, key, e := service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: accountRoot})
		require.NoError(t, e)
		require.NotEmpty(t, key)
		require.NotEmpty(t, mnemonic)
		cutoverCrashWriteFresh(t, filepath.Join(root, "account-key.private"), []byte(key))
		cutoverCrashJSON(t, filepath.Join(root, "sensitive-needles.private"), []string{key, mnemonic})
		account, e := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{Name: "Native fullSpace fixture", StorePath: accountRoot, DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly})
		require.NoError(t, e)
		require.NotNil(t, account)
		require.NotNil(t, account.Info)
		state.AccountID = account.Id
		state.Request.SpaceID = account.Info.AccountSpaceId
		require.NotEmpty(t, state.AccountID)
		require.NotEmpty(t, state.Request.SpaceID)
	} else {
		key, e := os.ReadFile(filepath.Join(root, "account-key.private"))
		require.NoError(t, e)
		require.NoError(t, service.WalletRecover(&pb.RpcWalletRecoverRequest{RootPath: accountRoot, AccountKey: string(key)}))
		account, e := service.AccountSelect(ctx, &pb.RpcAccountSelectRequest{Id: state.AccountID, RootPath: accountRoot, PreferredSpaceId: state.Request.SpaceID, DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly})
		require.NoError(t, e)
		require.NotNil(t, account)
		require.Equal(t, state.AccountID, account.Id)
	}
	// Explicit fixture setup may finish the normal native load. The readiness
	// method itself must use only the completed loader and must not start one.
	scope, err := mw.pinkhaTorahScope(ctx)
	require.NoError(t, err)
	spc, err := scope.spaces.Get(ctx, state.Request.SpaceID)
	require.NoError(t, err)
	store, err := app.GetComponent[objectstore.ObjectStore](scope.application)
	require.NoError(t, err)
	indexerService, err := app.GetComponent[indexer.Indexer](scope.application)
	require.NoError(t, err)
	f := &torahIndexFixture{t: t, ctx: ctx, mw: mw, root: root, state: state, space: spc, index: store.SpaceIndex(state.Request.SpaceID), indexer: indexerService}
	scope.close()
	if phase == "cold" {
		cold := f.ready("cold-local-snapshot")
		require.NotEqual(t, state.Final.Readiness.Generation, cold.Readiness.Generation, "cold native index owner never inherits a prior generation")
		require.Equal(t, state.Final.AuthoritativeObjectCount, cold.AuthoritativeObjectCount)
		require.Equal(t, state.Final.EligibleDocumentCount, cold.EligibleDocumentCount)
		require.Equal(t, cold, f.read("cold-stable-second-read"))
		deleted, e := spc.Storage().HeadStorage().GetEntry(ctx, state.DeletedID)
		require.NoError(t, e)
		require.Equal(t, headstorage.DeletedStatusDeleted, deleted.DeletedStatus)
		cutoverCrashJSON(t, filepath.Join(root, "cold-proof.json"), map[string]any{"pid": os.Getpid(), "previousPID": state.CreatePID, "readiness": cold, "originalAccount": state.AccountID, "noSourceRewrite": true})
		stop()
		result, e := mw.NativeTorahSpaceIndexReadiness(ctx, state.Request)
		require.Error(t, e)
		require.Equal(t, contract.Result{}, result)
		return
	}
	articleKey := f.bindSchema()
	pageKey := domain.MustUniqueKey(coresb.SmartBlockTypeObjectType, "page").Marshal()
	state.DocumentID = f.page("Current native document", pageKey, nil)
	state.CanonicalValue = `{"version":1,"items":[]}`
	f.set(state.DocumentID, state.Request.CanonicalKey, state.CanonicalValue)
	require.NoError(t, f.indexer.ReindexSpace(spc))
	baseline := f.ready("initial-existing-data")
	require.Greater(t, baseline.EligibleDocumentCount, 0)
	require.Equal(t, baseline, f.read("initial-stable-second-read"))

	// A real signed root becomes visible while its original index transaction
	// waits behind this owned empty WriteTx. Readiness must see the missing head
	// match; releasing the transaction lets the ORIGINAL worker restore ready.
	blocker, err := f.index.WriteTx(ctx)
	require.NoError(t, err)
	defer blocker.Rollback()
	beforeHeads, err := anystorage.PinkhaHeadsSnapshot(ctx, spc.Storage(), &contract.Budget{}, typeprovider.GetTypeAndKeyFromRootForSpace)
	require.NoError(t, err)
	created := make(chan *pb.RpcObjectCreateResponse, 1)
	go func() {
		created <- mw.ObjectCreate(ctx, &pb.RpcObjectCreateRequest{SpaceId: state.Request.SpaceID, ObjectTypeUniqueKey: pageKey, Details: &types.Struct{Fields: map[string]*types.Value{"name": indexText("Signed before index commit")}}})
	}()
	var unindexed contract.NativeSnapshot
	for n := 0; n < 100; n++ {
		unindexed, err = anystorage.PinkhaHeadsSnapshot(ctx, spc.Storage(), &contract.Budget{}, typeprovider.GetTypeAndKeyFromRootForSpace)
		require.NoError(t, err)
		if len(unindexed.Roots) > len(beforeHeads.Roots) {
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	require.Greater(t, len(unindexed.Roots), len(beforeHeads.Roots), "actual signed native root must commit before the held index tx")
	gap := f.read("new-signed-unindexed-object")
	require.False(t, gap.Complete)
	require.True(t, slices.Contains(gap.Reasons, contract.MissingIndexedHeads) || slices.Contains(gap.Reasons, contract.IndexedHeadsChanged), "native head must be counted before classification")
	require.NoError(t, blocker.Rollback())
	var response *pb.RpcObjectCreateResponse
	select {
	case response = <-created:
	case <-time.After(20 * time.Second):
		t.Fatal("original native index task did not complete")
	}
	require.NotNil(t, response)
	require.NotNil(t, response.Error)
	require.Equal(t, pb.RpcObjectCreateResponseError_NULL, response.Error.Code, response.Error.Description)
	state.DeletedID = response.ObjectId
	require.NotEmpty(t, state.DeletedID)
	afterIndex := f.ready("new-object-index-commit")
	require.NotEqual(t, baseline.Readiness.Generation, afterIndex.Readiness.Generation)
	require.Equal(t, baseline.AuthoritativeObjectCount+1, afterIndex.AuthoritativeObjectCount)
	cutoverCrashJSON(t, filepath.Join(root, "signed-unindexed-heads.json"), unindexed)

	// Rollback of a derived head write is invisible; a committed stale head is
	// incomplete on every read until the original native task runs again.
	tx, err := f.index.WriteTx(ctx)
	require.NoError(t, err)
	require.NoError(t, f.index.SaveLastIndexedHeadsHash(tx.Context(), state.DocumentID, "stale-test-head"))
	require.NoError(t, tx.Rollback())
	require.Equal(t, afterIndex, f.read("rolled-back-head-is-invisible"))
	require.NoError(t, f.index.SaveLastIndexedHeadsHash(ctx, state.DocumentID, "stale-test-head"))
	stale := f.read("committed-stale-head")
	require.False(t, stale.Complete)
	require.Contains(t, stale.Reasons, contract.IndexedHeadsChanged)
	require.Equal(t, stale, f.read("stale-read-does-not-repair"))
	f.indexDocument(state.DocumentID)
	require.Equal(t, afterIndex, f.ready("native-task-repaired-head"))

	f.set(state.DocumentID, state.Request.CanonicalKey, `{"version":999,"items":[]}`)
	unsupported := f.read("unsupported-canonical-content")
	require.False(t, unsupported.Complete)
	require.Contains(t, unsupported.Reasons, contract.UnsupportedProjection)
	f.set(state.DocumentID, state.Request.CanonicalKey, state.CanonicalValue)
	restored := f.ready("supported-canonical-restored")
	require.NotEqual(t, afterIndex.Readiness.Generation, restored.Readiness.Generation)
	typed := mw.ObjectSetObjectType(ctx, &pb.RpcObjectSetObjectTypeRequest{ContextId: state.DocumentID, ObjectTypeUniqueKey: articleKey})
	require.NotNil(t, typed)
	require.NotNil(t, typed.Error)
	require.Equal(t, pb.RpcObjectSetObjectTypeResponseError_NULL, typed.Error.Code, typed.Error.Description)
	afterType := f.ready("current-type-transition")
	require.NotEqual(t, restored.Readiness.Generation, afterType.Readiness.Generation)
	archive := mw.ObjectListSetIsArchived(ctx, &pb.RpcObjectListSetIsArchivedRequest{ObjectIds: []string{state.DocumentID}, IsArchived: true})
	require.NotNil(t, archive)
	require.NotNil(t, archive.Error)
	require.Equal(t, pb.RpcObjectListSetIsArchivedResponseError_NULL, archive.Error.Code, archive.Error.Description)
	archived := f.ready("archive-transition")
	require.NotEqual(t, afterType.Readiness.Generation, archived.Readiness.Generation)
	require.Equal(t, afterType.EligibleDocumentCount-1, archived.EligibleDocumentCount)
	archive = mw.ObjectListSetIsArchived(ctx, &pb.RpcObjectListSetIsArchivedRequest{ObjectIds: []string{state.DocumentID}, IsArchived: false})
	require.Equal(t, pb.RpcObjectListSetIsArchivedResponseError_NULL, archive.Error.Code, archive.Error.Description)
	unarchived := f.ready("unarchive-transition")
	require.Equal(t, afterType.EligibleDocumentCount, unarchived.EligibleDocumentCount)

	// The private signed store is metadata-only but must still admit its exact
	// native heads through the original queue after the durable append.
	appended, e := mw.NativeTorahOperationAppend(ctx, PinkhaTorahAppendRequest{Version: 1, SpaceID: state.Request.SpaceID, OperationID: fmt.Sprintf("%032x", 71), Kind: torahops.Add,
		Target: torahops.Target{ObjectID: state.DocumentID}, Source: torahops.Source{ProviderID: "fullspace-fixture", CanonicalRef: "actual:1"}, Payload: []byte("retained signed metadata")})
	require.NoError(t, e)
	require.Equal(t, torahops.Created, appended.Disposition)
	require.NotEmpty(t, appended.ChangeID)
	afterMetadata := f.ready("private-signed-metadata-admitted")
	require.NotEqual(t, unarchived.Readiness.Generation, afterMetadata.Readiness.Generation)
	cutoverCrashJSON(t, filepath.Join(root, "actual-native-metadata-receipt.json"), appended)

	deleted := mw.ObjectListDelete(ctx, &pb.RpcObjectListDeleteRequest{ObjectIds: []string{state.DeletedID}})
	require.NotNil(t, deleted)
	require.NotNil(t, deleted.Error)
	require.Equal(t, pb.RpcObjectListDeleteResponseError_NULL, deleted.Error.Code, deleted.Error.Description)
	afterDelete := f.ready("terminal-deletion-admitted")
	require.NotEqual(t, afterMetadata.Readiness.Generation, afterDelete.Readiness.Generation)
	admission, e := anystorage.PinkhaDeletionAdmission(ctx, spc.Storage(), state.Request.SpaceID, state.DeletedID)
	require.NoError(t, e)
	require.Equal(t, headstorage.DeletedStatusDeleted, admission.Terminal.DeletedStatus)
	staleAdmission := admission
	staleAdmission.Terminal.LastAddSeq++
	require.NoError(t, spaceindex.PinkhaDeleteObject(f.index, state.DeletedID, staleAdmission))
	staleDelete := f.read("stale-deletion-generation")
	require.False(t, staleDelete.Complete)
	require.Contains(t, staleDelete.Reasons, contract.StaleDeletionAdmission)
	require.NoError(t, spaceindex.PinkhaDeleteObject(f.index, state.DeletedID, admission))
	f.ready("exact-terminal-generation-restored")
	require.NoError(t, f.index.DeleteObject(state.DeletedID))
	missing := f.read("missing-terminal-witness")
	require.False(t, missing.Complete)
	require.Contains(t, missing.Reasons, contract.MissingDeletionAdmission)
	require.NoError(t, spaceindex.PinkhaDeleteObject(f.index, state.DeletedID, admission))
	state.Final = f.ready("final-complete-native-snapshot")
	require.Equal(t, state.Final, f.read("final-stable-second-read"))
	foreign := state.Request
	foreign.SpaceID = "unloaded-foreign-space"
	result, e := mw.NativeTorahSpaceIndexReadiness(ctx, foreign)
	require.Error(t, e)
	require.True(t, errors.Is(e, contract.ErrNotLoaded) || errors.Is(e, contract.ErrScopeChanged))
	require.Equal(t, contract.Result{}, result)
	cutoverCrashJSON(t, filepath.Join(root, "checkpoint.json"), state)
	stop()
	result, e = mw.NativeTorahSpaceIndexReadiness(ctx, state.Request)
	require.Error(t, e)
	require.Equal(t, contract.Result{}, result)
	cutoverCrashJSON(t, filepath.Join(root, "prepare-proof.json"), map[string]any{"pid": os.Getpid(), "retiredOwnerRefused": true, "foreignSpaceRefused": true, "observations": f.observations, "final": state.Final})
}
