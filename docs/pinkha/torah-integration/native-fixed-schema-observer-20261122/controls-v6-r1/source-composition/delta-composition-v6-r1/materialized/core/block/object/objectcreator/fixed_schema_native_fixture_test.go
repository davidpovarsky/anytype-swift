package objectcreator_test

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-store/query"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/aclrecordproto"
	"github.com/anyproto/any-sync/commonspace/object/acl/list/listtest"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/nodeconf"
	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/anytype/config"
	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/object/payloadcreator"
	"github.com/anyproto/anytype-heart/core/block/source/sourceimpl"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/session"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/util/pbtypes"
)

// This fixture starts the actual production application in a disposable directory.
// It does not call the existing integration helper, which logs a mnemonic.
// Normal wallet/account/Workspace initialization is fixture setup, not observer work.
type nativeSchemaFixture struct {
	ctx      context.Context
	service  *application.Service
	creator  objectcreator.Service
	observer objectcreator.FixedSchemaObserver
	spaces   space.Service
	blocks   *block.Service
}

func newNativeSchemaFixture(t *testing.T) *nativeSchemaFixture {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	t.Cleanup(cancel)
	service := application.New()
	service.SetClientVersion("otzaria-native-schema-control", "1.0.0")
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	directory := t.TempDir()
	_, _, err := service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: directory})
	nativeSchemaNoError(t, err)
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	account, err := service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{
		Name: "Disposable schema observer control", StorePath: directory,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_LocalOnly,
	})
	nativeSchemaNoError(t, err)
	if account == nil {
		t.Fatal("native AccountCreate returned nil")
	}
	t.Cleanup(func() {
		nativeSchemaNoError(t, service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: true}))
	})
	nativeApp := service.GetApp()
	creator := app.MustComponent[objectcreator.Service](nativeApp)
	observer, ok := creator.(objectcreator.FixedSchemaObserver)
	if !ok {
		t.Fatal("actual native creator does not expose the reviewed additive observer")
	}
	return &nativeSchemaFixture{ctx: ctx, service: service, creator: creator, observer: observer,
		spaces: app.MustComponent[space.Service](nativeApp), blocks: app.MustComponent[*block.Service](nativeApp)}
}

func (f *nativeSchemaFixture) regularSpace(t *testing.T) clientspace.Space {
	t.Helper()
	details := domain.NewDetails()
	details.SetString(bundle.RelationKeyName, "Disposable native schema controls")
	details.SetInt64(bundle.RelationKeySpaceType, int64(model.SpaceType_SpaceTypeRegular))
	id, _, err := f.blocks.CreateWorkspace(f.ctx, &pb.RpcWorkspaceCreateRequest{
		Details: details.ToProto(), UseCase: pb.RpcObjectImportUseCaseRequest_NONE,
	})
	nativeSchemaNoError(t, err)
	spc, err := f.spaces.Wait(f.ctx, id)
	nativeSchemaNoError(t, err)
	if spc == nil || spc.IsPersonal() || spc.CommonSpace() == nil || spc.Storage() == nil || spc.Id() != id {
		t.Fatal("fixture did not obtain a real initialized regular native Space")
	}
	return spc
}

func nativeSchemaDefinition(t *testing.T, kind coresb.SmartBlockType, suffix string) objectcreator.FixedSchemaDefinition {
	t.Helper()
	key, err := domain.NewUniqueKey(kind, "otzariaobserverv5"+suffix)
	nativeSchemaNoError(t, err)
	required := domain.NewDetails()
	required.SetString(bundle.RelationKeyName, "Native observer "+suffix)
	switch kind {
	case coresb.SmartBlockTypeRelation:
		required.SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_relation))
		required.SetInt64(bundle.RelationKeyRelationFormat, int64(model.RelationFormat_longtext))
	case coresb.SmartBlockTypeObjectType:
		required.SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_objectType))
		required.SetInt64(bundle.RelationKeyRecommendedLayout, int64(model.ObjectType_basic))
	default:
		t.Fatal("unsupported fixture definition kind")
	}
	return objectcreator.FixedSchemaDefinition{Key: key, Required: required}
}

func (f *nativeSchemaFixture) createSchema(t *testing.T, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition) string {
	t.Helper()
	details := definition.Required.Copy()
	objectType := bundle.TypeKeyRelation
	if definition.Key.SmartblockType() == coresb.SmartBlockTypeObjectType {
		objectType = bundle.TypeKeyObjectType
		details.SetString(bundle.RelationKeyUniqueKey, definition.Key.Marshal())
	} else {
		details.SetString(bundle.RelationKeyRelationKey, definition.Key.InternalKey())
	}
	id, _, err := f.creator.CreateObject(f.ctx, spc.Id(), objectcreator.CreateObjectRequest{
		Details: details, ObjectTypeKey: objectType,
	})
	nativeSchemaNoError(t, err)
	derived, err := spc.DeriveObjectID(f.ctx, definition.Key)
	nativeSchemaNoError(t, err)
	if id == "" || id != derived {
		t.Fatal("original schema creation did not return the original derived native ID")
	}
	return id
}

func (f *nativeSchemaFixture) createRootOnly(t *testing.T, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition) string {
	t.Helper()
	payload, err := spc.DeriveTreePayload(f.ctx, payloadcreator.PayloadDerivationParams{Key: definition.Key})
	nativeSchemaNoError(t, err)
	if payload.RootRawChange == nil {
		t.Fatal("original root payload is nil")
	}
	_, err = spc.Storage().CreateTreeStorage(f.ctx, payload)
	nativeSchemaNoError(t, err)
	return payload.RootRawChange.Id
}

func (f *nativeSchemaFixture) tree(t *testing.T, spc clientspace.Space, id string) objecttree.ObjectTree {
	t.Helper()
	storage, err := spc.Storage().TreeStorage(f.ctx, id)
	nativeSchemaNoError(t, err)
	tree, err := objecttree.BuildObjectTree(storage, spc.CommonSpace().Acl())
	nativeSchemaNoError(t, err)
	return tree // Do not Close: this original storage borrows live collections.
}

func nativeSchemaNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatalf("native fixture operation: %v", err)
	}
}

func (f *nativeSchemaFixture) observe(t *testing.T, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition, expected objectcreator.FixedSchemaDisposition) objectcreator.FixedSchemaObservation {
	t.Helper()
	result, err := f.observer.ObserveFixedSchema(f.ctx, spc, definition)
	nativeSchemaNoError(t, err)
	if result.Disposition != expected || result.SpaceID != spc.Id() || result.ObjectID == "" {
		t.Fatalf("unexpected full native observation: disposition=%d expected=%d", result.Disposition, expected)
	}
	return result
}

func (f *nativeSchemaFixture) unavailable(t *testing.T, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition) error {
	t.Helper()
	result, err := f.observer.ObserveFixedSchema(f.ctx, spc, definition)
	if err == nil || result.Disposition != objectcreator.FixedSchemaUnavailable {
		t.Fatalf("corrupt original storage must remain unavailable; disposition=%d err=%v", result.Disposition, err)
	}
	return err
}

// A generic unavailable result can be masked by an earlier independent failure.
// The selected retry negatives must reach their exact original failure boundary.
func (f *nativeSchemaFixture) unavailableCause(t *testing.T, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition, wanted error, fragment string) {
	t.Helper()
	err := f.unavailable(t, spc, definition)
	if !errors.Is(err, wanted) || !strings.Contains(err.Error(), fragment) {
		t.Fatalf("wrong original unavailable cause: wanted %v / %q; got %v", wanted, fragment, err)
	}
}

func nativeSchemaChangeDescription(value string) *pb.Change {
	return &pb.Change{Content: []*pb.ChangeContent{{
		Value: &pb.ChangeContentValueOfDetailsSet{DetailsSet: &pb.ChangeDetailsSet{
			Key: string(bundle.RelationKeyDescription), Value: pbtypes.String(value),
		}},
	}}}
}

func (f *nativeSchemaFixture) addChange(t *testing.T, tree objecttree.ObjectTree, change *pb.Change, timestamp int64) objecttree.AddResult {
	t.Helper()
	data, dataType, err := sourceimpl.MarshalChange(change)
	nativeSchemaNoError(t, err)
	acl := tree.AclList()
	acl.RLock()
	key := acl.AclState().Key()
	acl.RUnlock()
	tree.Lock()
	defer tree.Unlock()
	result, err := tree.AddContent(f.ctx, objecttree.SignableChangeContent{
		Data: data, DataType: dataType, Key: key, IsSnapshot: change.Snapshot != nil,
		ShouldBeEncrypted: true, Timestamp: timestamp,
	})
	nativeSchemaNoError(t, err)
	if len(result.Added) != 1 || len(result.Heads) != 1 {
		t.Fatal("native local change did not produce exactly one original persisted change")
	}
	return result
}

// Build the snapshot input from the actual original replayed State using the same
// original projection fields as sourceimpl.treeSource.buildChange. This constructs
// fixture data; signature, encryption, graph, storage and replay remain original.
func nativeSchemaSnapshot(t *testing.T, spaceID string, tree objecttree.ObjectTree) *pb.Change {
	t.Helper()
	tree.Lock()
	defer tree.Unlock()
	state, _, _, err := sourceimpl.BuildStateStrict(spaceID, tree)
	nativeSchemaNoError(t, err)
	snapshot := &pb.Change{Version: state.MigrationVersion(), Snapshot: &pb.ChangeSnapshot{
		Data: &model.SmartBlockSnapshotBase{
			Blocks: state.BlocksToSave(), Details: state.Details().ToProto(),
			ObjectTypes: domain.MarshalTypeKeys(state.ObjectTypeKeys()), Collections: state.Store(),
			RelationLinks: state.PickRelationLinks(), Key: state.UniqueKeyInternal(),
			OriginalCreatedTimestamp: state.OriginalCreatedTimestamp(), FileInfo: state.GetFileInfo().ToModel(),
		},
	}}
	return proto.Clone(snapshot).(*pb.Change)
}

func nativeSchemaReadRow(t *testing.T, ctx context.Context, db anystore.DB, collectionName, id string) []byte {
	t.Helper()
	collection, err := db.OpenCollection(ctx, collectionName)
	nativeSchemaNoError(t, err)
	doc, err := collection.FindId(ctx, id)
	nativeSchemaNoError(t, err)
	return doc.Value().MarshalTo(nil)
}

func nativeSchemaRestoreRow(t *testing.T, ctx context.Context, db anystore.DB, collectionName string, data []byte) {
	t.Helper()
	collection, err := db.OpenCollection(ctx, collectionName)
	nativeSchemaNoError(t, err)
	value, err := (&anyenc.Parser{}).Parse(data)
	nativeSchemaNoError(t, err)
	nativeSchemaNoError(t, collection.UpsertOne(ctx, value))
}

func nativeSchemaMutateRow(t *testing.T, ctx context.Context, db anystore.DB, collectionName, id string, mutate func(*anyenc.Arena, *anyenc.Value)) {
	t.Helper()
	original := nativeSchemaReadRow(t, ctx, db, collectionName, id)
	t.Cleanup(func() { nativeSchemaRestoreRow(t, ctx, db, collectionName, original) })
	collection, err := db.OpenCollection(ctx, collectionName)
	nativeSchemaNoError(t, err)
	result, err := collection.UpdateId(ctx, id, query.ModifyFunc(func(arena *anyenc.Arena, value *anyenc.Value) (*anyenc.Value, bool, error) {
		mutate(arena, value)
		return value, true, nil
	}))
	nativeSchemaNoError(t, err)
	if result.Matched != 1 || result.Modified != 1 {
		t.Fatal("native corruption fixture did not change exactly one row")
	}
}

func nativeSchemaRowsEqual(t *testing.T, ctx context.Context, db anystore.DB, collectionName, id string, wanted []byte) {
	t.Helper()
	if !bytes.Equal(nativeSchemaReadRow(t, ctx, db, collectionName, id), wanted) {
		t.Fatal("unexpected native row mutation")
	}
}

func (f *nativeSchemaFixture) appendACLRecord(t *testing.T, spc clientspace.Space) {
	t.Helper()
	nativeSchemaNoError(t, f.ctx.Err())
	nativeApp := f.service.GetApp()
	if !app.MustComponent[*config.Config](nativeApp).IsLocalOnlyMode() ||
		app.MustComponent[nodeconf.Service](nativeApp).Configuration().NetworkId != "" {
		t.Fatal("local ACL fixture requires actual original LocalOnly configuration without a network acceptor")
	}
	// The original LocalOnly runtime selected its own verifier at Space startup.
	// Do not replace it or manufacture an acceptor signature. The original test
	// helper only wraps the already author-signed native record with its real CID.
	// Actual AddRawRecord performs native signature/CID/content/state/storage work.
	acl := spc.CommonSpace().Acl()
	acl.Lock()
	defer acl.Unlock()
	before := len(acl.Records())
	raw, err := acl.RecordBuilder().BuildSpaceOptionsChange(&aclrecordproto.AclSpaceOptions{})
	nativeSchemaNoError(t, err)
	record := listtest.WrapAclRecord(raw)
	nativeSchemaNoError(t, acl.AddRawRecord(record))
	if len(acl.Records()) != before+1 || acl.Head().Id != record.Id {
		t.Fatal("original local ACL ingestion did not advance exactly one actual signed record")
	}
	storage, err := spc.Storage().AclStorage()
	nativeSchemaNoError(t, err)
	persisted, err := storage.Get(f.ctx, record.Id)
	nativeSchemaNoError(t, err)
	if persisted.Id != record.Id || !bytes.Equal(persisted.RawRecord, record.Payload) {
		t.Fatal("actual original ACL storage did not retain the exact native record")
	}
}

func nativeSchemaRawChange(t *testing.T, tree objecttree.ObjectTree, change *pb.Change, timestamp int64) *treechangeproto.RawTreeChangeWithId {
	t.Helper()
	data, dataType, err := sourceimpl.MarshalChange(change)
	nativeSchemaNoError(t, err)
	acl := tree.AclList()
	acl.RLock()
	key := acl.AclState().Key()
	acl.RUnlock()
	tree.Lock()
	defer tree.Unlock()
	raw, err := tree.PrepareChange(objecttree.SignableChangeContent{
		Data: data, DataType: dataType, Key: key, IsSnapshot: change.Snapshot != nil,
		ShouldBeEncrypted: true, Timestamp: timestamp,
	})
	nativeSchemaNoError(t, err)
	return raw
}

func nativeSchemaError(stage string, err error) error {
	if err == nil {
		return nil
	}
	return fmt.Errorf("%s: %w", stage, err)
}

type nativeSchemaArchiver interface {
	SetIsArchived(session.Context, context.Context, string, bool, bool) error
}

func (f *nativeSchemaFixture) archive(t *testing.T, id string) {
	t.Helper()
	archiver := app.MustComponent[nativeSchemaArchiver](f.service.GetApp())
	nativeSchemaNoError(t, archiver.SetIsArchived(session.NewContext(), f.ctx, id, true, true))
}
