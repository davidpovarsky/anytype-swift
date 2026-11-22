package service

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/cidutil"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

// Only this separately built fixture binary links this marker. Product code,
// command schemas and capability advertisements are unchanged.
var t5ACLFixtureSHA = "UNSET"

const t5ACLProtocol = "pinkha-t5-signed-local-revocation-v2"
const t5ACLCurrentReadDenied = "PINKHA_CURRENT_SPACE_READ_DENIED_V1"
const t5ACLCurrentReadInvalidated = "PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1"
const t5ACLHeart = "d98420b1113536afd08cde6de9a5816f6d27ffff"

func t5ACLHash(value []byte) string {
	sum := sha256.Sum256(value)
	return hex.EncodeToString(sum[:])
}

func t5ACLWrite(t *testing.T, path string, value any) {
	t.Helper()
	data, err := json.Marshal(value)
	require.NoError(t, err)
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	require.NoError(t, err)
	_, err = file.Write(data)
	require.NoError(t, err)
	require.NoError(t, file.Sync())
	require.NoError(t, file.Close())
}

// The caller holds the real native ACL lock. Both admission and persistent
// signed-record application use the engine's validators; no permission field
// or account identity is replaced. SyncAcl retains its real updater callback.
func t5ACLApply(t *testing.T, acl list.AclList, raw *consensusproto.RawRecord) string {
	t.Helper()
	require.NoError(t, acl.ValidateRawRecord(raw, nil))
	data, err := raw.MarshalVT()
	require.NoError(t, err)
	id, err := cidutil.NewCidFromBytes(data)
	require.NoError(t, err)
	require.NoError(t, acl.AddRawRecord(&consensusproto.RawRecordWithId{Id: id, Payload: data}))
	require.Equal(t, id, acl.Head().Id)
	return id
}

func TestT5NativeCachedQueriesAfterSignedRevocation(t *testing.T) {
	root, report := os.Getenv("PINKHA_T5_ACL_ROOT"), os.Getenv("PINKHA_T5_ACL_REPORT")
	nonce := os.Getenv("PINKHA_T5_ACL_NONCE")
	require.True(t, filepath.IsAbs(root))
	require.Equal(t, "account-root", filepath.Base(root))
	parent := filepath.Dir(root)
	require.Equal(t, parent, filepath.Dir(report))
	require.Equal(t, "native-observation.json", filepath.Base(report))
	require.Len(t, nonce, 32)
	_, err := hex.DecodeString(nonce)
	require.NoError(t, err)
	entries, err := os.ReadDir(root)
	require.NoError(t, err)
	require.Empty(t, entries, "only an empty controller-owned account may be opened")
	owner, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	require.NoError(t, err)
	require.Equal(t, string(owner), os.Getenv("PINKHA_T5_ACL_OWNERSHIP"))
	var owned struct {
		Protocol      string `json:"protocol"`
		Nonce         string `json:"nonce"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	require.NoError(t, json.Unmarshal(owner, &owned))
	require.Equal(t, t5ACLProtocol, owned.Protocol)
	require.Equal(t, nonce, owned.Nonce)
	require.True(t, owned.SyntheticOnly)
	require.Len(t, t5ACLFixtureSHA, 64)
	require.Equal(t, t5ACLFixtureSHA, os.Getenv("PINKHA_T5_ACL_FIXTURE_SHA256"))
	require.Equal(t, t5ACLHeart, vcs.GitCommit)
	require.Equal(t, os.Getenv("PINKHA_T5_ACL_RUNTIME_VERSION"), vcs.GitSummary)
	calls := map[string]int{}
	rawCall := func(call func([]byte) []byte, request, response proto.Message) {
		t.Helper()
		name := strings.TrimSuffix(strings.TrimPrefix(reflect.TypeOf(request).Elem().Name(), "Rpc"), "Request")
		calls[name]++
		data, err := proto.Marshal(request)
		require.NoError(t, err)
		require.NoError(t, proto.Unmarshal(call(data), response))
	}
	invoke := func(call func([]byte) []byte, request, response proto.Message) {
		t.Helper()
		rawCall(call, request, response)
		field := reflect.ValueOf(response).Elem().FieldByName("Error")
		if field.IsValid() && !field.IsNil() && field.Elem().FieldByName("Code").Int() != 0 {
			t.Fatalf("%T returned native error code %d", response, field.Elem().FieldByName("Code").Int())
		}
	}
	wait := func(label string, predicate func() bool) {
		t.Helper()
		deadline := time.Now().Add(45 * time.Second)
		for time.Now().Before(deadline) {
			if predicate() {
				return
			}
			time.Sleep(100 * time.Millisecond)
		}
		t.Fatal("native fixture readiness failed: " + label)
	}
	SetEventHandler(func(*pb.Event) {})
	invoke(InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	version := &pb.RpcAppGetVersionResponse{}
	invoke(AppGetVersion, &pb.RpcAppGetVersionRequest{}, version)
	require.Equal(t, vcs.GitSummary, version.Version)
	wallet := &pb.RpcWalletCreateResponse{}
	invoke(WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, wallet)
	require.NotEmpty(t, wallet.AccountKey)
	require.NotEmpty(t, wallet.Mnemonic)
	t5ACLWrite(t, filepath.Join(parent, "sensitive-needles.private"), []string{wallet.AccountKey, wallet.Mnemonic})
	created := &pb.RpcAccountCreateResponse{}
	invoke(AccountCreate, &pb.RpcAccountCreateRequest{Name: "Disposable signed revocation fixture",
		NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true}, created)
	require.NotNil(t, created.Account)
	accountID := created.Account.Id
	require.NotEmpty(t, accountID)
	closed := false
	closeAccount := func() {
		if closed {
			return
		}
		invoke(AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{})
		require.Nil(t, mw.GetApp())
		invoke(AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{})
		closed = true
	}
	t.Cleanup(closeAccount)
	createdSpace := &pb.RpcWorkspaceCreateResponse{}
	invoke(WorkspaceCreate, &pb.RpcWorkspaceCreateRequest{Details: domain.NewDetails().
		SetString(bundle.RelationKeyName, "Disposable signed revocation Space").ToProto()}, createdSpace)
	spaceID := createdSpace.SpaceId
	require.NotEmpty(t, spaceID)
	invoke(WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: spaceID}, &pb.RpcWorkspaceOpenResponse{})
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()
	spc, err := app.MustComponent[space.Service](mw.GetApp()).Get(ctx, spaceID)
	require.NoError(t, err)
	require.NoError(t, spc.WaitMandatoryObjects(ctx))
	keys := app.MustComponent[accountservice.Service](mw.GetApp()).Account()
	require.Equal(t, accountID, keys.SignKey.GetPublic().Account())
	require.True(t, spc.GetAclIdentity().Equals(keys.SignKey.GetPublic()))
	acl := spc.CommonSpace().Acl()
	acl.RLock()
	ownerPermission := acl.AclState().Permissions(keys.SignKey.GetPublic())
	acl.RUnlock()
	require.Equal(t, list.AclPermissionsOwner, ownerPermission)
	show := func(objectID string) *pb.RpcObjectShowResponse {
		t.Helper()
		response := &pb.RpcObjectShowResponse{}
		invoke(ObjectShow, &pb.RpcObjectShowRequest{SpaceId: spaceID, ObjectId: objectID, ContextId: objectID}, response)
		require.NotNil(t, response.ObjectView)
		require.Equal(t, objectID, response.ObjectView.RootId)
		return response
	}
	details := func(shown *pb.RpcObjectShowResponse, objectID string) *domain.Details {
		t.Helper()
		for _, entry := range shown.ObjectView.Details {
			if entry.Id == objectID {
				return domain.NewDetailsFromProto(entry.Details)
			}
		}
		t.Fatal("actual native ObjectShow omitted requested document details")
		return nil
	}
	// Use the already qualified native fixture's binding shape. The canonical
	// Property and three registered Types are actual native Objects. Auxiliary
	// template/folder slots are outside this single-source query scenario.
	// WaitMandatoryObjects starts bundled installation asynchronously. Require
	// its actual indexed Page before any one-shot ObjectCreate; never retry a
	// mutation whose native outcome may be ambiguous.
	wait("actual indexed native Page type", func() bool {
		response := &pb.RpcObjectSearchResponse{}
		invoke(ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: spaceID, Limit: 2,
			Filters: []*model.BlockContentDataviewFilter{{RelationKey: "uniqueKey",
				Condition: model.BlockContentDataviewFilter_Equal, Value: domain.String("ot-page").ToProto()}},
			Keys: []string{"id", "spaceId", "uniqueKey"}}, response)
		if len(response.Records) == 0 {
			return false
		}
		require.Len(t, response.Records, 1)
		row := domain.NewDetailsFromProto(response.Records[0])
		require.NotEmpty(t, row.GetString(bundle.RelationKeyId))
		require.Equal(t, spaceID, row.GetString(bundle.RelationKeySpaceId))
		require.Equal(t, "ot-page", row.GetString(bundle.RelationKeyUniqueKey))
		return true
	})
	canonical := &pb.RpcObjectCreateRelationResponse{}
	invoke(ObjectCreateRelation, &pb.RpcObjectCreateRelationRequest{SpaceId: spaceID, Details: domain.NewDetails().
		SetString(bundle.RelationKeyName, "Synthetic canonical source").SetInt64(bundle.RelationKeyRelationFormat, 0).ToProto()}, canonical)
	canonicalKey := domain.NewDetailsFromProto(canonical.Details).GetString(bundle.RelationKeyRelationKey)
	require.NotEmpty(t, canonicalKey)
	types, typeKeys := map[string]string{}, map[string]string{}
	for _, role := range []string{"chiddush", "article", "research"} {
		value := &pb.RpcObjectCreateObjectTypeResponse{}
		invoke(ObjectCreateObjectType, &pb.RpcObjectCreateObjectTypeRequest{SpaceId: spaceID, Details: domain.NewDetails().
			SetString(bundle.RelationKeyName, role).SetInt64(bundle.RelationKeyRecommendedLayout, int64(model.ObjectType_basic)).ToProto()}, value)
		types[role] = value.ObjectId
		typeKeys[role] = domain.NewDetailsFromProto(value.Details).GetString(bundle.RelationKeyUniqueKey)
		require.NotEmpty(t, types[role])
		require.NotEmpty(t, typeKeys[role])
	}
	manifest := &pb.RpcObjectCreateResponse{}
	invoke(ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: spaceID, ObjectTypeUniqueKey: "ot-page", Details: domain.NewDetails().
		SetString(bundle.RelationKeyName, torah.ManifestUniqueKey).SetString(bundle.RelationKeyUniqueKey, torah.ManifestUniqueKey).
		SetBool(bundle.RelationKeyIsHidden, true).ToProto()}, manifest)
	manifestRaw, err := json.Marshal(map[string]any{"schemaVersion": 1, "spaceId": spaceID, "provisioningState": "complete",
		"manifestObjectId": manifest.ObjectId, "documentAssociationsPropertyId": canonical.ObjectId,
		"documentAssociationsPropertyKey": canonicalKey, "registeredDocumentTypes": types,
		"defaultTemplateIds": map[string]string{"chiddush": "unused-template-h", "article": "unused-template-a", "research": "unused-template-r"},
		"parentPropertyId":   "unused-parent", "parentPropertyKey": "unusedParent", "orderPropertyId": "unused-order",
		"orderPropertyKey": "unusedOrder", "folderTypeId": "unused-folder", "bookFolderTypeId": "unused-book"})
	require.NoError(t, err)
	invoke(ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: manifest.ObjectId,
		Details: []*model.Detail{{Key: "description", Value: domain.String(string(manifestRaw)).ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
	wait("actual r15 lookup capability", func() bool {
		return details(show(manifest.ObjectId), manifest.ObjectId).GetInt64(torah.RelatedVersionKey) == 1
	})
	document := &pb.RpcObjectCreateResponse{}
	invoke(ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: spaceID, ObjectTypeUniqueKey: typeKeys["chiddush"],
		Details: domain.NewDetails().SetString(bundle.RelationKeyName, "Synthetic protected source row").ToProto()}, document)
	objectID := document.ObjectId
	require.NotEmpty(t, objectID)
	body := "Synthetic protected native body"
	block := &pb.RpcBlockCreateResponse{}
	invoke(BlockCreate, &pb.RpcBlockCreateRequest{ContextId: objectID, TargetId: objectID, Position: model.Block_Inner,
		Block: &model.Block{Content: &model.BlockContentOfText{Text: &model.BlockContentText{Text: body}}}}, block)
	require.NotEmpty(t, block.BlockId)
	canonicalRaw, err := json.Marshal(map[string]any{"version": 2, "records": []any{map[string]any{
		"spaceId": spaceID, "objectId": objectID, "item": map[string]string{"id": "signed-revocation-source", "kind": "ref",
			"role": "context", "providerID": "sefaria", "canonicalKey": "Genesis 3:3", "externalID": "Genesis 3:3", "labelHe": "מקור בדיקה"}}}})
	require.NoError(t, err)
	invoke(ObjectSetDetails, &pb.RpcObjectSetDetailsRequest{ContextId: objectID,
		Details: []*model.Detail{{Key: canonicalKey, Value: domain.String(string(canonicalRaw)).ToProto()}}}, &pb.RpcObjectSetDetailsResponse{})
	identity := torah.Identity(torah.Ref, "sefaria", "Genesis 3:3", "")
	query := &pb.RpcObjectSearchRequest{SpaceId: spaceID, NeedTotal: true, Limit: 10,
		Filters: []*model.BlockContentDataviewFilter{{RelationKey: torah.RelatedSourcesKey, Format: model.RelationFormat_tag,
			Condition: model.BlockContentDataviewFilter_In, Value: domain.StringList([]string{identity}).ToProto()}},
		Keys: []string{"id", "spaceId", "name", "type", canonicalKey, torah.RelatedSourcesKey}}
	readPositive := func() {
		t.Helper()
		wait("actual indexed related source", func() bool {
			response := &pb.RpcObjectSearchResponse{}
			invoke(ObjectSearch, query, response)
			if len(response.Records) == 0 {
				return false
			}
			require.Len(t, response.Records, 1)
			require.Equal(t, int64(1), response.Total)
			row := domain.NewDetailsFromProto(response.Records[0])
			require.Equal(t, objectID, row.GetString(bundle.RelationKeyId))
			require.Equal(t, spaceID, row.GetString(bundle.RelationKeySpaceId))
			require.Equal(t, string(canonicalRaw), row.GetString(domain.RelationKey(canonicalKey)))
			require.Equal(t, []string{identity}, row.GetStringList(torah.RelatedSourcesKey))
			return true
		})
		shown := show(objectID)
		require.Equal(t, string(canonicalRaw), details(shown, objectID).GetString(domain.RelationKey(canonicalKey)))
		found := false
		for _, value := range shown.ObjectView.Blocks {
			if value.Id == block.BlockId {
				require.NotNil(t, value.GetText())
				require.Equal(t, body, value.GetText().Text)
				found = true
			}
		}
		require.True(t, found)
	}
	readPositive()
	cached, err := spc.GetObject(ctx, objectID)
	require.NoError(t, err)
	require.Equal(t, objectID, cached.Id())
	newOwner, err := accountdata.NewRandom()
	require.NoError(t, err)
	newOwnerModel, _, err := domain.DeriveAccountMetadata(newOwner.SignKey)
	require.NoError(t, err)
	newOwnerMetadata, err := newOwnerModel.Marshal()
	require.NoError(t, err)
	var addHead, transferHead, previousReadKey string
	func() {
		acl.Lock()
		defer acl.Unlock()
		raw, err := acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{
			{Identity: newOwner.SignKey.GetPublic(), Permissions: list.AclPermissionsWriter, Metadata: newOwnerMetadata}}})
		require.NoError(t, err)
		addHead = t5ACLApply(t, acl, raw)
		raw, err = acl.RecordBuilder().BuildOwnershipChange(list.OwnershipChangePayload{
			NewOwner: newOwner.SignKey.GetPublic(), OldOwnerPermissions: list.AclPermissionsReader})
		require.NoError(t, err)
		transferHead = t5ACLApply(t, acl, raw)
		require.Equal(t, list.AclPermissionsReader, acl.AclState().Permissions(keys.SignKey.GetPublic()))
		require.Equal(t, list.AclPermissionsOwner, acl.AclState().Permissions(newOwner.SignKey.GetPublic()))
		previousReadKey = acl.AclState().CurrentReadKeyId()
	}()
	// The actual original middleware still owns the same account and native
	// objects after its real signed downgrade; Reader remains a positive control.
	readPositive()
	stillCached, err := spc.GetObject(ctx, objectID)
	require.NoError(t, err)
	require.Same(t, cached, stillCached)
	acl.RLock()
	records, err := acl.RecordsAfter(ctx, "")
	acl.RUnlock()
	require.NoError(t, err)
	require.NotEmpty(t, records)
	require.Equal(t, acl.Root().Id, records[0].Id)
	storage, err := list.NewInMemoryStorage(acl.Id(), records)
	require.NoError(t, err)
	signer, err := list.BuildAclListWithIdentity(newOwner, storage, recordverifier.NewValidateFull())
	require.NoError(t, err)
	require.Equal(t, transferHead, signer.Head().Id)
	require.Equal(t, list.AclPermissionsOwner, signer.AclState().Permissions(newOwner.SignKey.GetPublic()))
	metadata, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	removal, err := signer.RecordBuilder().BuildAccountRemove(list.AccountRemovePayload{
		Identities: []crypto.PubKey{keys.SignKey.GetPublic()},
		Change:     list.ReadKeyChangePayload{MetadataKey: metadata, ReadKey: crypto.NewAES()}})
	require.NoError(t, err)
	var removeHead, readKeyAfter string
	func() {
		acl.Lock()
		defer acl.Unlock()
		removeHead = t5ACLApply(t, acl, removal)
		require.Equal(t, list.AclPermissionsNone, acl.AclState().Permissions(keys.SignKey.GetPublic()))
		require.True(t, acl.AclState().HadReadPermissions(keys.SignKey.GetPublic()))
		readKeyAfter = acl.AclState().CurrentReadKeyId()
		require.NotEqual(t, previousReadKey, readKeyAfter)
	}()
	// No updater is replaced or suppressed. These are ordinary actual generated
	// RPCs after the same native ACL has verified, persisted and notified removal.
	require.NotNil(t, mw.GetApp())
	require.Equal(t, accountID, app.MustComponent[accountservice.Service](mw.GetApp()).Account().SignKey.GetPublic().Account())
	searchAfter := &pb.RpcObjectSearchResponse{}
	rawCall(ObjectSearch, query, searchAfter)
	showAfter := &pb.RpcObjectShowResponse{}
	rawCall(ObjectShow, &pb.RpcObjectShowRequest{SpaceId: spaceID, ObjectId: objectID, ContextId: objectID}, showAfter)
	searchCode, showCode := int32(-1), int32(-1)
	if searchAfter.Error != nil {
		searchCode = int32(searchAfter.Error.Code)
	}
	if showAfter.Error != nil {
		showCode = int32(showAfter.Error.Code)
	}
	searchDescription, showDescription := "", ""
	if searchAfter.Error != nil {
		searchDescription = searchAfter.Error.Description
	}
	if showAfter.Error != nil {
		showDescription = showAfter.Error.Description
	}
	// The unchanged native ACL updater may already have retired this Space.
	// Both exact current-authority outcomes deny the read; generic errors and
	// success-with-empty results remain failures. All payload counts stay zero.
	searchAuthorityStopped := searchDescription == t5ACLCurrentReadDenied || searchDescription == t5ACLCurrentReadInvalidated
	showAuthorityStopped := showDescription == t5ACLCurrentReadDenied || showDescription == t5ACLCurrentReadInvalidated
	searchDenied := searchAfter.Error != nil && searchCode == int32(pb.RpcObjectSearchResponseError_BAD_INPUT) && searchAuthorityStopped && len(searchAfter.Records) == 0 && searchAfter.Total == 0
	showDenied := showAfter.Error != nil && showCode == int32(pb.RpcObjectShowResponseError_BAD_INPUT) && showAuthorityStopped && showAfter.ObjectView == nil
	closeAccount()
	observation := map[string]any{"protocol": t5ACLProtocol, "nonce": nonce, "pid": os.Getpid(),
		"heart_sha": vcs.GitCommit, "runtime_version": vcs.GitSummary, "fixture_sha256": t5ACLFixtureSHA,
		"account_id_sha256": t5ACLHash([]byte(accountID)), "space_id_sha256": t5ACLHash([]byte(spaceID)),
		"object_id_sha256": t5ACLHash([]byte(objectID)), "canonical_sha256": t5ACLHash(canonicalRaw),
		"same_engine_account": true, "populated_native_cache": true, "reader_positive": true,
		"signed_acl_add_head": addHead, "signed_acl_transfer_head": transferHead, "signed_acl_remove_head": removeHead,
		"current_permission": "none", "had_read_permission": true, "read_key_rotated": previousReadKey != readKeyAfter,
		"read_key_id_before": previousReadKey, "read_key_id_after": readKeyAfter,
		"native_acl_updater": "NOT_REPLACED_OR_SUPPRESSED", "local_signed_delivery": true,
		"object_search_error_code": searchCode, "object_search_rows": len(searchAfter.Records), "object_search_total": searchAfter.Total,
		"object_search_error_description": searchDescription, "object_show_error_description": showDescription,
		"object_search_explicit_denial": searchDenied, "object_show_error_code": showCode,
		"object_show_has_payload": showAfter.ObjectView != nil, "object_show_explicit_denial": showDenied,
		"account_stop_verified": closed, "rpc_calls": calls, "network_acl_transport": "NOT_RUN",
		"offline_unknown_revocation": "NOT_PROVEN", "ios_acceptance": "NOT_RUN", "full_t5_acceptance": "NOT_PROVEN"}
	if searchDenied && showDenied {
		observation["status"] = "PASS_LOCAL_SIGNED_REVOCATION"
	} else {
		observation["status"] = "FAIL_REVOKED_NATIVE_QUERY_EXPOSED_OR_AMBIGUOUS"
	}
	t5ACLWrite(t, report, observation)
	// A success-with-empty global result is not an authorization response.
	require.True(t, searchDenied, "actual revoked ObjectSearch must explicitly deny with no rows or total")
	require.True(t, showDenied, "actual revoked ObjectShow must explicitly deny with no object payload")
}
