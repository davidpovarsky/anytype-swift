// Closed annotation preparation over the original immutable archive owner.
// This file starts no import and mints no completion/body/ACK capability.
package importer

import (
	"context"
	"crypto/sha256"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/gogo/protobuf/proto"
	"github.com/gogo/protobuf/types"

	"github.com/anyproto/anytype-heart/core/anytype/account"
	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/process"
	"github.com/anyproto/anytype-heart/core/domain"
	annotationschema "github.com/anyproto/anytype-heart/core/pinkha/annotationschema/definition"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/spacedomain"
)

type ownedAnnotationMemberRole uint8

const (
	ownedAnnotationFreshPage ownedAnnotationMemberRole = iota + 1
	ownedAnnotationFixedSchema
	ownedAnnotationBundledSchema
	ownedAnnotationParticipant
	ownedAnnotationFileObject
)

// All fields remain private and are filled from the genuine generated models
// plus actual original account/Space APIs. Expected target IDs are observations,
// not a substitute for the later original provider's real assignment.
type ownedAnnotationMemberPlan struct {
	sourceID       string
	memberPath     string
	role           ownedAnnotationMemberRole
	snapshot       *pb.SnapshotWithType
	expectedTarget string
	nativeKey      domain.UniqueKey
	fileSource     string
	fileID         string
	fileDigest     [32]byte
	fileBytes      uint64
}

type ownedAnnotationGraph struct {
	archive                               *ownedAnnotationArchive
	stage                                 *ownedAnnotationArchiveStaging
	account                               account.Service
	accountID                             string
	identity                              crypto.PubKey
	space                                 clientspace.Space
	spaces                                space.Service
	spaceID                               string
	members                               map[string]*ownedAnnotationMemberPlan
	order                                 []string
	ctx                                   context.Context
	store                                 objectstore.ObjectStore
	observer                              objectcreator.OwnedAnnotationSchemaObserver
	exporter                              export.Export
	additionalContext                     map[string]*ownedAnnotationMemberPlan
	readOnlyHeads                         map[string][]string
	readOnlySnapshots                     map[string]*pb.SnapshotWithType
	fixed                                 map[string]objectcreator.FixedSchemaDefinition
	byConverter                           map[string]*ownedAnnotationMemberPlan
	sourceToConverter                     map[string]string
	converted                             map[string]*pb.ChangeSnapshot
	beforeCreate                          map[string]*pb.ChangeSnapshot
	nativeIDs                             map[string]string
	targets                               map[string]*ownedAnnotationMemberPlan
	conversionStarted, conversionFinished int64
	mu                                    sync.Mutex
	fileUploads                           map[string]ownedAnnotationUploadedFile
	fileInputs                            map[string]*types.Struct
}

func ownedAnnotationRefused(code string) error {
	return fmt.Errorf("owned annotation import refused: %s", code)
}

// This package-private front door takes bytes, never a caller path, request
// policy, converter, executor, callback or success/drain flag. The native
// application owner must retain/register the eventual operation before Start;
// a returned preparation here is not that lifetime registration.
func prepareOwnedAnnotationGraph(ctx context.Context, a *app.App, raw []byte, digest [32]byte,
	sourceRootID, sourceSpaceID, targetSpaceID string,
) (*ownedAnnotationGraph, error) {
	if ctx == nil || a == nil || targetSpaceID == "" {
		return nil, ownedAnnotationRefused("missing_native_owner")
	}
	archive, err := inspectOwnedAnnotationArchive(ctx, raw, digest, sourceRootID, sourceSpaceID)
	if err != nil {
		return nil, err
	}
	accounts := app.MustComponent[account.Service](a)
	spaces := app.MustComponent[space.Service](a)
	if accounts == nil || accounts.Keys() == nil || accounts.Keys().SignKey == nil || spaces == nil {
		return nil, ownedAnnotationRefused("native_account_components")
	}
	g := &ownedAnnotationGraph{archive: archive, account: accounts, accountID: accounts.AccountID(),
		identity: accounts.Keys().SignKey.GetPublic(), spaces: spaces, spaceID: targetSpaceID,
		members: make(map[string]*ownedAnnotationMemberPlan)}
	if err := g.requireCapturedAccount(ctx); err != nil {
		return nil, err
	}
	g.ctx, g.store = ctx, app.MustComponent[objectstore.ObjectStore](a)
	originalCreator := app.MustComponent[objectcreator.Service](a)
	observer, available := originalCreator.(objectcreator.OwnedAnnotationSchemaObserver)
	if !available || g.store == nil {
		return nil, ownedAnnotationRefused("original_schema_observer_unavailable")
	}
	g.observer = observer
	g.exporter = app.MustComponent[export.Export](a)
	g.additionalContext = make(map[string]*ownedAnnotationMemberPlan)
	g.readOnlyHeads = make(map[string][]string)
	g.readOnlySnapshots = make(map[string]*pb.SnapshotWithType)
	g.fixed = make(map[string]objectcreator.FixedSchemaDefinition)
	definitions, err := annotationschema.Definitions()
	if err != nil {
		return nil, err
	}
	for _, definition := range definitions {
		g.fixed[definition.Key.Marshal()] = definition
	}
	g.nativeIDs, g.targets = make(map[string]string), make(map[string]*ownedAnnotationMemberPlan)
	g.fileUploads = make(map[string]ownedAnnotationUploadedFile)
	g.fileInputs = make(map[string]*types.Struct)
	stage, err := archive.stage(ctx)
	if err != nil {
		return nil, err
	}
	g.stage = stage
	if err := g.requireCapturedAccount(ctx); err != nil {
		return nil, errors.Join(err, stage.Close())
	}
	return g, nil
}

// Application registration precedes Start. Only the SAME original Execute may
// now enter Space.Get/derivation; preparation above performs bounded byte work,
// private filesystem staging and component capture without native callbacks.
// A reentrant original Stop therefore sees this operation in its existing registry.
func (g *ownedAnnotationGraph) bindNativeOwner(ctx context.Context) error {
	if err := g.requireCapturedAccount(ctx); err != nil {
		return err
	}
	if g.spaces == nil || g.space != nil || len(g.members) != 0 {
		return ownedAnnotationRefused("native_space_binding_state")
	}
	spc, err := g.spaces.Get(ctx, g.spaceID)
	if err != nil {
		return err
	}
	if spc == nil || spc.Id() != g.spaceID || spc.SpaceType() != spacedomain.SpaceTypeRegular || spc.IsPersonal() {
		return ownedAnnotationRefused("native_account_or_regular_space")
	}
	g.space = spc
	if err := g.requireCurrentWriter(ctx); err != nil {
		return err
	}
	return g.classifyCompleteGraph(ctx)
}

func (g *ownedAnnotationGraph) requireCapturedAccount(ctx context.Context) error {
	if ctx == nil {
		return ownedAnnotationRefused("missing_context")
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	if g == nil || g.account == nil || g.identity == nil || g.accountID == "" ||
		g.account.AccountID() != g.accountID || g.identity.Account() != g.accountID {
		return ownedAnnotationRefused("native_identity_changed")
	}
	keys := g.account.Keys()
	if keys == nil || keys.SignKey == nil || !keys.SignKey.GetPublic().Equals(g.identity) {
		return ownedAnnotationRefused("native_identity_changed")
	}
	return ctx.Err()
}

// This is an actual current native writer admission, not an atomic storage
// transaction. A later revocation/cancel can coexist with earlier historical
// effects. The same admission must be repeated at assignment/create/readback.
func (g *ownedAnnotationGraph) requireCurrentWriter(ctx context.Context) error {
	if err := g.requireCapturedAccount(ctx); err != nil {
		return err
	}
	if g.space == nil || g.space.Id() != g.spaceID || g.space.CommonSpace() == nil || g.space.GetAclIdentity() == nil ||
		!g.space.GetAclIdentity().Equals(g.identity) {
		return ownedAnnotationRefused("native_identity_changed")
	}
	acl := g.space.CommonSpace().Acl()
	if acl == nil {
		return ownedAnnotationRefused("native_acl_missing")
	}
	acl.RLock()
	defer acl.RUnlock()
	state := acl.AclState()
	if state == nil || state.Identity() == nil || !state.Identity().Equals(g.identity) ||
		!state.Permissions(g.identity).CanWrite() {
		return list.ErrInsufficientPermissions
	}
	return ctx.Err()
}

func (g *ownedAnnotationGraph) classifyCompleteGraph(ctx context.Context) error {
	definitions, err := annotationschema.Definitions()
	if err != nil {
		return err
	}
	fixed := make(map[string]*domain.Details, len(definitions))
	for _, definition := range definitions {
		fixed[definition.Key.Marshal()] = definition.Required
	}
	binaries := make(map[string]ownedAnnotationArchiveMember)
	for _, member := range g.archive.members {
		if member.Kind == "file" {
			binaries[member.Name] = member
		}
	}
	claimedFiles := make(map[string]bool)
	expectedTargets := make(map[string]string)
	participantCount := 0
	for _, member := range g.archive.members {
		if err := ctx.Err(); err != nil {
			return err
		}
		if member.Kind == "file" {
			continue
		}
		raw := g.archive.snapshots[member.ObjectID]
		if raw == nil || raw.Snapshot == nil || raw.Snapshot.Data == nil || len(raw.Snapshot.FileKeys) != 0 {
			return ownedAnnotationRefused("unowned_shared_file_keys")
		}
		known := proto.Clone(raw).(*pb.SnapshotWithType)
		proto.DiscardUnknown(known)
		if !proto.Equal(known, raw) {
			return ownedAnnotationRefused("unknown_native_snapshot_semantics")
		}
		producerShape := &pb.SnapshotWithType{SbType: raw.SbType, Snapshot: &pb.ChangeSnapshot{Data: &model.SmartBlockSnapshotBase{
			Blocks: raw.Snapshot.Data.Blocks, Details: raw.Snapshot.Data.Details, ObjectTypes: raw.Snapshot.Data.ObjectTypes,
			Collections: raw.Snapshot.Data.Collections, Key: raw.Snapshot.Data.Key, FileInfo: raw.Snapshot.Data.FileInfo,
		}}}
		if !proto.Equal(raw, producerShape) {
			return ownedAnnotationRefused("not_original_export_snapshot_shape")
		}
		snapshot := proto.Clone(raw).(*pb.SnapshotWithType)
		data := snapshot.Snapshot.Data
		details := domain.NewDetailsFromProto(data.Details)
		plan := &ownedAnnotationMemberPlan{sourceID: member.ObjectID, memberPath: member.Name, snapshot: snapshot}
		switch coresb.SmartBlockType(snapshot.SbType) {
		case coresb.SmartBlockTypePage:
			if len(data.ObjectTypes) != 1 || data.ObjectTypes[0] != annotationschema.TypeUniqueKey || data.Key != "" {
				return ownedAnnotationRefused("non_annotation_page")
			}
			plan.role = ownedAnnotationFreshPage
		case coresb.SmartBlockTypeObjectType, coresb.SmartBlockTypeRelation:
			key, err := domain.NewUniqueKey(coresb.SmartBlockType(snapshot.SbType), data.Key)
			if err != nil || data.Key == "" || details.GetString(bundle.RelationKeyUniqueKey) != key.Marshal() {
				return ownedAnnotationRefused("schema_native_key")
			}
			plan.nativeKey = key
			if required, exists := fixed[key.Marshal()]; exists {
				for field, value := range required.Iterate() {
					if !details.Has(field) || !details.Get(field).Equal(value) {
						return ownedAnnotationRefused("fixed_schema_source_definition")
					}
				}
				plan.role = ownedAnnotationFixedSchema
			} else {
				var bundledSource string
				if key.SmartblockType() == coresb.SmartBlockTypeObjectType && bundle.HasObjectTypeByKey(domain.TypeKey(data.Key)) {
					bundledSource = domain.TypeKey(data.Key).BundledURL()
				} else if key.SmartblockType() == coresb.SmartBlockTypeRelation && bundle.HasRelation(domain.RelationKey(data.Key)) {
					bundledSource = domain.RelationKey(data.Key).BundledURL()
				}
				if bundledSource == "" || details.GetString(bundle.RelationKeySourceObject) != bundledSource {
					return ownedAnnotationRefused("non_original_schema")
				}
				plan.role = ownedAnnotationBundledSchema
			}
			// These original methods only derive the native ID. They do not
			// install the schema or prove its target persisted state.
			if key.SmartblockType() == coresb.SmartBlockTypeObjectType {
				plan.expectedTarget, err = g.space.GetTypeIdByKey(ctx, domain.TypeKey(data.Key))
			} else {
				plan.expectedTarget, err = g.space.GetRelationIdByKey(ctx, domain.RelationKey(data.Key))
			}
			if err != nil || plan.expectedTarget == "" {
				return errors.Join(ownedAnnotationRefused("native_schema_derivation"), err)
			}
		case coresb.SmartBlockTypeParticipant:
			// The initial closed route is same-account. The ordinary native
			// participant provider must later return this exact target ID.
			if details.GetString(bundle.RelationKeyIdentity) != g.accountID ||
				member.ObjectID != g.account.MyParticipantId(g.archive.spaceID) {
				return ownedAnnotationRefused("foreign_participant_context")
			}
			participantCount++
			plan.role = ownedAnnotationParticipant
			plan.expectedTarget = g.account.MyParticipantId(g.spaceID)
		case coresb.SmartBlockTypeFileObject:
			if data.Key != "" || details.GetString(bundle.RelationKeyUniqueKey) != "" ||
				details.GetBool(bundle.RelationKeyIsFavorite) || details.GetBool(bundle.RelationKeyIsArchived) {
				return ownedAnnotationRefused("file_object_reuse_or_external_side_effect")
			}
			binary, exists := binaries[member.FileSource]
			if !exists || member.FileID == "" || data.FileInfo == nil {
				return ownedAnnotationRefused("unowned_file_body")
			}
			paths := make(map[string]bool, len(data.FileInfo.EncryptionKeys))
			for _, key := range data.FileInfo.EncryptionKeys {
				if key == nil || key.Path == "" || key.Key == "" || paths[key.Path] {
					return ownedAnnotationRefused("file_encryption_inventory")
				}
				paths[key.Path] = true
			}
			plan.role, plan.fileSource, plan.fileID = ownedAnnotationFileObject, member.FileSource, member.FileID
			plan.fileDigest, plan.fileBytes = binary.SHA256, binary.Bytes
			claimedFiles[member.FileSource] = true
		default:
			return ownedAnnotationRefused("unsupported_graph_member")
		}
		if plan.expectedTarget != "" {
			if _, exists := expectedTargets[plan.expectedTarget]; exists {
				return ownedAnnotationRefused("non_unique_native_context")
			}
			expectedTargets[plan.expectedTarget] = member.ObjectID
		}
		g.members[member.ObjectID] = plan
		g.order = append(g.order, member.ObjectID)
	}
	if participantCount != 1 || len(g.members) != len(g.archive.snapshots) || len(claimedFiles) != len(binaries) {
		return ownedAnnotationRefused("whole_graph_coverage")
	}
	root := g.members[g.archive.rootID]
	if root == nil || root.role != ownedAnnotationFreshPage {
		return ownedAnnotationRefused("annotation_root")
	}
	sort.Strings(g.order)
	return g.requireCurrentWriter(ctx)
}

// The wrapper calls the actual original converter and records only its real
// execution interval, needed for the original zero-createdDate normalization.
type ownedAnnotationConverter struct {
	native common.Converter
	graph  *ownedAnnotationGraph
}

func (c ownedAnnotationConverter) Name() string { return c.native.Name() }
func (c ownedAnnotationConverter) GetSnapshots(ctx context.Context, request *pb.RpcObjectImportRequest, progress process.Progress) (*common.Response, *common.ConvertError) {
	c.graph.conversionStarted = time.Now().Unix()
	response, err := c.native.GetSnapshots(ctx, request, progress)
	c.graph.conversionFinished = time.Now().Unix()
	return response, err
}

func (g *ownedAnnotationGraph) admitConversion(ctx context.Context, p *importProcessor) error {
	if err := g.requireExactConverterOutput(ctx, p); err != nil {
		return err
	}
	g.converted = make(map[string]*pb.ChangeSnapshot, len(p.converterResponse.Snapshots))
	for _, sn := range p.converterResponse.Snapshots {
		g.converted[sn.Id] = proto.Clone(sn.Snapshot.ToProto()).(*pb.ChangeSnapshot)
	}
	if err := g.admitOriginalImportMetadata(ctx); err != nil {
		return err
	}
	// Resolve the entire graph before the first original provider can upload a
	// file or a worker can create a page. Negative index observations are only
	// preflight; actual provider disposition and actual create collisions remain
	// checked at their original execution points.
	for _, sourceID := range g.order {
		plan := g.members[sourceID]
		if plan.role == ownedAnnotationFreshPage || plan.role == ownedAnnotationFileObject {
			if err := g.requireNoExistingImportIdentity(ctx, plan); err != nil {
				return err
			}
		} else {
			if _, err := g.readOnlyContext(ctx, plan); err != nil {
				return err
			}
		}
	}
	return g.requireCurrentWriter(ctx)
}

func (g *ownedAnnotationGraph) requireNoExistingImportIdentity(ctx context.Context, plan *ownedAnnotationMemberPlan) error {
	if err := g.requireCurrentWriter(ctx); err != nil {
		return err
	}
	rows, err := g.store.SpaceIndex(g.spaceID).QueryRaw(&database.Filters{FilterObj: database.FiltersOr{
		database.FilterEq{Key: bundle.RelationKeyOldAnytypeID, Value: domain.String(plan.sourceID)},
		database.FilterEq{Key: bundle.RelationKeyUniqueKey, Value: domain.String(plan.sourceID)},
		database.FilterEq{Key: bundle.RelationKeyId, Value: domain.String(plan.sourceID)},
	}}, 2, 0)
	if err != nil {
		return err
	}
	if len(rows) != 0 {
		return ownedAnnotationRefused("existing_or_unknown_import_identity")
	}
	return g.requireCurrentWriter(ctx)
}

func (g *ownedAnnotationGraph) uniquePositiveIndex(ctx context.Context, key domain.RelationKey, value, id string) (*domain.Details, error) {
	if err := g.requireCurrentWriter(ctx); err != nil {
		return nil, err
	}
	rows, err := g.store.SpaceIndex(g.spaceID).QueryRaw(&database.Filters{FilterObj: database.FilterEq{Key: key, Value: domain.String(value)}}, 2, 0)
	if err != nil {
		return nil, err
	}
	if len(rows) != 1 || rows[0].Details == nil {
		return nil, ownedAnnotationRefused("non_unique_native_index")
	}
	details := rows[0].Details
	if details.GetString(bundle.RelationKeyId) != id || details.GetString(bundle.RelationKeySpaceId) != g.spaceID ||
		details.GetBool(bundle.RelationKeyIsArchived) || details.GetBool(bundle.RelationKeyIsDeleted) || details.GetBool(bundle.RelationKeyIsUninstalled) {
		return nil, ownedAnnotationRefused("native_index_identity_or_disposition")
	}
	if err := g.requireCurrentWriter(ctx); err != nil {
		return nil, err
	}
	return details.Copy(), nil
}

func (g *ownedAnnotationGraph) readOnlyContext(ctx context.Context, plan *ownedAnnotationMemberPlan) (*domain.Details, error) {
	if err := g.requireCurrentWriter(ctx); err != nil {
		return nil, err
	}
	if plan.role == ownedAnnotationParticipant {
		// Participant objects are original ACL/account context, not imported
		// user pages or a schema tree to initialize. No SmartBlock is opened.
		actual, err := g.uniquePositiveIndex(ctx, bundle.RelationKeyId, plan.expectedTarget, plan.expectedTarget)
		if err != nil {
			return nil, err
		}
		if actual.GetString(bundle.RelationKeyIdentity) != g.accountID ||
			plan.expectedTarget != g.account.MyParticipantId(g.spaceID) {
			return nil, ownedAnnotationRefused("native_participant_identity")
		}
		return actual, nil
	}
	var observed objectcreator.OwnedAnnotationSchemaObservation
	var err error
	switch plan.role {
	case ownedAnnotationFixedSchema:
		definition, ok := g.fixed[plan.nativeKey.Marshal()]
		if !ok {
			return nil, ownedAnnotationRefused("fixed_schema_definition")
		}
		observed, err = g.observer.ObserveOwnedAnnotationFixedSchema(ctx, g.space, definition)
	case ownedAnnotationBundledSchema:
		observed, err = g.observer.ObserveOwnedAnnotationBundledSchema(ctx, g.space, plan.nativeKey)
	default:
		return nil, ownedAnnotationRefused("not_read_only_context")
	}
	if err != nil {
		return nil, err
	}
	snapshot := observed.CopySnapshot()
	if observed.Disposition != objectcreator.FixedSchemaPersistedMatch || observed.SpaceID != g.spaceID ||
		observed.AccountIdentity != g.accountID || observed.ObjectID != plan.expectedTarget ||
		len(observed.PersistedHeads) == 0 || snapshot == nil {
		return nil, ownedAnnotationRefused("native_schema_not_persisted_match")
	}
	if plan.snapshot != nil {
		if err := g.requireSchemaSnapshotCompatibility(ctx, plan, snapshot); err != nil {
			return nil, err
		}
	} else if !g.isOriginalImportMetadata(plan) {
		return nil, ownedAnnotationRefused("unowned_additional_schema")
	}
	g.mu.Lock()
	before := g.readOnlyHeads[plan.expectedTarget]
	heads := append([]string(nil), observed.PersistedHeads...)
	slices.Sort(heads)
	if len(before) == 0 {
		g.readOnlyHeads[plan.expectedTarget] = heads
		g.readOnlySnapshots[plan.expectedTarget] = proto.Clone(snapshot).(*pb.SnapshotWithType)
	} else if !slices.Equal(before, heads) || !proto.Equal(g.readOnlySnapshots[plan.expectedTarget], snapshot) {
		g.mu.Unlock()
		return nil, ownedAnnotationRefused("read_only_schema_changed")
	}
	g.mu.Unlock()
	key, value := bundle.RelationKeyUniqueKey, plan.nativeKey.Marshal()
	if plan.nativeKey.SmartblockType() == coresb.SmartBlockTypeRelation {
		key, value = bundle.RelationKeyRelationKey, plan.nativeKey.InternalKey()
	}
	actual, err := g.uniquePositiveIndex(ctx, key, value, plan.expectedTarget)
	if err != nil {
		return nil, err
	}
	persisted := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
	for _, field := range []domain.RelationKey{bundle.RelationKeyUniqueKey, bundle.RelationKeyName, bundle.RelationKeyLayout, bundle.RelationKeyRelationFormat, bundle.RelationKeyRecommendedLayout, bundle.RelationKeySourceObject, bundle.RelationKeyRevision} {
		if persisted.Has(field) && (!actual.Has(field) || !persisted.Get(field).Equal(actual.Get(field))) {
			return nil, ownedAnnotationRefused("native_schema_index_disagrees")
		}
	}
	return actual, g.requireCurrentWriter(ctx)
}

func (g *ownedAnnotationGraph) beforeAssignment(ctx context.Context, p *importProcessor, sn *common.Snapshot) error {
	if err := g.requireCurrentWriter(ctx); err != nil {
		return err
	}
	plan := g.byConverter[sn.Id]
	baseline := g.converted[sn.Id]
	if plan == nil || baseline == nil || g.nativeIDs[sn.Id] != "" {
		return ownedAnnotationRefused("assignment_source_changed")
	}
	expected := proto.Clone(baseline).(*pb.ChangeSnapshot)
	if plan.role == ownedAnnotationFileObject {
		details := domain.NewDetailsFromProto(expected.Data.Details)
		common.UpdateObjectIDsInDetails(details, p.oldIDToNew, p.relationKeysToFormat)
		expected.Data.Details = details.ToProto()
	}
	if !proto.Equal(expected, sn.Snapshot.ToProto()) {
		return ownedAnnotationRefused("assignment_snapshot_changed")
	}
	if plan.role == ownedAnnotationFileObject {
		// Byte-for-byte request details expected from the original private
		// copyDetailsExcludingFileRelations helper in objectid/oldfile.go.
		details := domain.NewDetails()
		for key, value := range sn.Snapshot.Data.Details.Iterate() {
			if !strings.HasPrefix(string(key), "file") && key != bundle.RelationKeyIconImage {
				details.Set(key, value)
			}
		}
		g.fileInputs[plan.sourceID] = proto.Clone(details.ToProto()).(*types.Struct)
	}
	if plan.role == ownedAnnotationFreshPage || plan.role == ownedAnnotationFileObject {
		return g.requireNoExistingImportIdentity(ctx, plan)
	}
	_, err := g.readOnlyContext(ctx, plan)
	return err
}

func (g *ownedAnnotationGraph) afterAssignment(ctx context.Context, sn *common.Snapshot, id string, payload treestorage.TreeStorageCreatePayload) error {
	plan := g.byConverter[sn.Id]
	if plan == nil || id == "" || g.targets[id] != nil {
		return ownedAnnotationRefused("non_injective_actual_assignment")
	}
	if err := g.requireCurrentWriter(ctx); err != nil {
		return err
	}
	switch plan.role {
	case ownedAnnotationFreshPage:
		if id == plan.sourceID || id == sn.Id || payload.RootRawChange == nil || payload.RootRawChange.Id != id {
			return ownedAnnotationRefused("original_fresh_payload_required")
		}
		exists, err := g.space.Storage().HasTree(ctx, id)
		if err != nil {
			return err
		}
		if exists {
			return ownedAnnotationRefused("actual_payload_already_exists")
		}
	case ownedAnnotationFixedSchema, ownedAnnotationBundledSchema, ownedAnnotationParticipant:
		if id != plan.expectedTarget {
			return ownedAnnotationRefused("original_provider_reuse_disagrees")
		}
		if payload.RootRawChange != nil && payload.RootRawChange.Id != id {
			return ownedAnnotationRefused("original_schema_payload_identity")
		}
		if _, err := g.readOnlyContext(ctx, plan); err != nil {
			return err
		}
	case ownedAnnotationFileObject:
		g.mu.Lock()
		uploaded, ok := g.fileUploads[plan.sourceID]
		g.mu.Unlock()
		if !ok || uploaded.err != nil || uploaded.id != id || payload.RootRawChange != nil {
			return errors.Join(ownedAnnotationRefused("original_file_upload_did_not_complete"), uploaded.err)
		}
	default:
		return ownedAnnotationRefused("assignment_role")
	}
	g.nativeIDs[sn.Id], g.targets[id] = id, plan
	return g.requireCurrentWriter(ctx)
}

// No readonly context is routed through generic import Create: its workspace,
// reset, installation, favorite/archive and sync branches must remain unreachable.
type ownedAnnotationObjectCreator struct {
	original creator.Service
	graph    *ownedAnnotationGraph
}

func (c ownedAnnotationObjectCreator) Create(data *creator.DataObject, sn *common.Snapshot) (*domain.Details, string, error) {
	g := c.graph
	if err := g.requireCurrentWriter(g.ctx); err != nil {
		return nil, "", err
	}
	if sn == nil {
		return nil, "", ownedAnnotationRefused("missing_create_source")
	}
	plan, id := g.byConverter[sn.Id], g.nativeIDs[sn.Id]
	if plan == nil || id == "" {
		return nil, "", ownedAnnotationRefused("unassigned_create_source")
	}
	switch plan.role {
	case ownedAnnotationFreshPage:
		native, ok := c.original.(interface {
			CreateOwnedAnnotationFresh(*creator.DataObject, *common.Snapshot) (*domain.Details, string, error)
		})
		if !ok {
			return nil, "", ownedAnnotationRefused("original_fresh_creator_unavailable")
		}
		details, actualID, err := native.CreateOwnedAnnotationFresh(data, sn)
		if err != nil {
			return details, actualID, err
		}
		if actualID != id {
			return details, actualID, ownedAnnotationRefused("actual_create_identity_changed")
		}
		return details, actualID, g.requireCurrentWriter(g.ctx)
	case ownedAnnotationFixedSchema, ownedAnnotationBundledSchema, ownedAnnotationParticipant:
		details, err := g.readOnlyContext(g.ctx, plan)
		return details, id, err
	case ownedAnnotationFileObject:
		// The original synchronous uploader already performed the actual fresh
		// file create. No second generic import/reset pass is allowed.
		details, err := g.uniquePositiveIndex(g.ctx, bundle.RelationKeyId, id, id)
		if err != nil {
			return nil, id, err
		}
		g.mu.Lock()
		uploaded, ok := g.fileUploads[plan.sourceID]
		g.mu.Unlock()
		if !ok || uploaded.err != nil || uploaded.id != id || details.GetString(bundle.RelationKeyFileId) != uploaded.fileID {
			return nil, id, ownedAnnotationRefused("native_uploaded_file_readback")
		}
		return details, id, g.requireCurrentWriter(g.ctx)
	}
	return nil, "", ownedAnnotationRefused("create_role")
}

// Verify the exact owned extraction produced by the original converter. This
// admits no arbitrary caller pathname, symlink, unbounded read or remote URL.
func (g *ownedAnnotationGraph) verifyExtractedFile(ctx context.Context, plan *ownedAnnotationMemberPlan, path string) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	expected := filepath.Join(g.stage.TempDir(), filepath.FromSlash(plan.fileSource))
	if path != expected || !ownedArchiveFileSource(plan.fileSource) {
		return ownedAnnotationRefused("file_path_not_owned")
	}
	for _, directory := range []string{g.stage.root, g.stage.TempDir(), filepath.Dir(expected)} {
		st, err := os.Lstat(directory)
		if err != nil {
			return err
		}
		if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return ownedAnnotationRefused("file_parent_not_owned")
		}
	}
	before, err := os.Lstat(expected)
	if err != nil {
		return err
	}
	if !before.Mode().IsRegular() || before.Size() < 0 || uint64(before.Size()) != plan.fileBytes {
		return ownedAnnotationRefused("file_inventory_changed")
	}
	file, err := os.Open(expected)
	if err != nil {
		return err
	}
	opened, statErr := file.Stat()
	if statErr != nil {
		return errors.Join(statErr, file.Close())
	}
	if !os.SameFile(before, opened) {
		return errors.Join(ownedAnnotationRefused("file_identity_changed"), file.Close())
	}
	hash := sha256.New()
	n, readErr := io.Copy(hash, io.LimitReader(file, int64(plan.fileBytes)+1))
	closeErr := file.Close()
	if err := errors.Join(readErr, closeErr); err != nil {
		return err
	}
	var digest [32]byte
	copy(digest[:], hash.Sum(nil))
	after, err := os.Lstat(expected)
	if err != nil {
		return err
	}
	if n != int64(plan.fileBytes) || digest != plan.fileDigest || !os.SameFile(before, after) || after.Size() != before.Size() {
		return ownedAnnotationRefused("owned_file_bytes_changed")
	}
	return ctx.Err()
}

type ownedAnnotationUploadedFile struct {
	id, fileID string
	err        error
}

// Only the actual original ID provider uses this synchronous uploader wrapper.
// The underlying ownedImportBlockService still registers its real file slot
// before native work and retains the actual native result/error for drain.
type ownedAnnotationFileUploader struct {
	ownedImportBlockService
	graph *ownedAnnotationGraph
}

func (s ownedAnnotationFileUploader) UploadFile(_ context.Context, spaceID string, req block.FileUploadRequest) (id string, kind model.BlockContentFileType, details *domain.Details, err error) {
	g := s.graph
	if err = g.requireCurrentWriter(s.owned.ctx); err != nil {
		return
	}
	input := domain.NewDetailsFromProto(req.Details)
	sourceID := input.GetString(bundle.RelationKeyOldAnytypeID)
	plan := g.members[sourceID]
	expectedDetails := g.fileInputs[sourceID]
	if plan == nil || plan.role != ownedAnnotationFileObject || expectedDetails == nil || spaceID != g.spaceID || req.PreloadOnly ||
		!req.ObjectOrigin.IsImported() || req.ObjectOrigin.ImportType != model.Import_Pb {
		err = ownedAnnotationRefused("file_upload_not_owned")
		return
	}
	expectedRequest := &pb.RpcFileUploadRequest{SpaceId: g.spaceID, Details: expectedDetails, LocalPath: filepath.Join(g.stage.TempDir(), filepath.FromSlash(plan.fileSource))}
	if !proto.Equal(&req.RpcFileUploadRequest, expectedRequest) {
		err = ownedAnnotationRefused("file_request_changed")
		return
	}
	info := plan.snapshot.Snapshot.Data.FileInfo
	if info == nil || info.FileId != plan.fileID {
		err = ownedAnnotationRefused("file_info_changed")
		return
	}
	keys := make(map[string]string, len(info.EncryptionKeys))
	for _, key := range info.EncryptionKeys {
		if key == nil || key.Path == "" || key.Key == "" {
			err = ownedAnnotationRefused("file_key_shape")
			return
		}
		if _, exists := keys[key.Path]; exists {
			err = ownedAnnotationRefused("duplicate_file_key_path")
			return
		}
		keys[key.Path] = key.Key
	}
	if len(keys) != len(req.CustomEncryptionKeys) {
		err = ownedAnnotationRefused("file_key_inventory_changed")
		return
	}
	for path, value := range keys {
		if req.CustomEncryptionKeys[path] != value {
			err = ownedAnnotationRefused("file_key_inventory_changed")
			return
		}
	}
	if err = g.verifyExtractedFile(s.owned.ctx, plan, req.LocalPath); err != nil {
		return
	}
	g.mu.Lock()
	if _, exists := g.fileUploads[sourceID]; exists {
		g.mu.Unlock()
		err = ownedAnnotationRefused("duplicate_owned_file_upload")
		return
	}
	g.fileUploads[sourceID] = ownedAnnotationUploadedFile{err: ownedAnnotationRefused("native_file_call_not_returned")}
	g.mu.Unlock()
	id, kind, details, err = s.ownedImportBlockService.UploadFile(s.owned.ctx, spaceID, req)
	// A created file remains historical even if final currentness fails. No
	// cancellation request is relabelled as drain and no pre-existing user
	// object is deleted to simulate rollback.
	err = errors.Join(err, g.verifyExtractedFile(s.owned.ctx, plan, req.LocalPath), g.requireCurrentWriter(s.owned.ctx))
	fileID := ""
	if details != nil {
		fileID = details.GetString(bundle.RelationKeyFileId)
	}
	if err == nil && (id == "" || fileID == "" || id == sourceID) {
		err = ownedAnnotationRefused("original_file_result_identity")
	}
	g.mu.Lock()
	g.fileUploads[sourceID] = ownedAnnotationUploadedFile{id: id, fileID: fileID, err: err}
	g.mu.Unlock()
	return
}

// The unchanged original converter/creator adds import bookkeeping, and the
// native sync updater adds exactly three local sync relations during lifecycle
// transitions. Their schema dependencies may be absent from a source archive.
// Admit only this bounded set, with complete pre-import read-only observation;
// no key is a fabricated archive member or a substitute for a source mapping.
func originalOwnedAnnotationMetadataKeys() []domain.RelationKey {
	return []domain.RelationKey{bundle.RelationKeyImportType, bundle.RelationKeyOldAnytypeID, bundle.RelationKeySourceFilePath, bundle.RelationKeySyncStatus, bundle.RelationKeySyncDate, bundle.RelationKeySyncError}
}

func (g *ownedAnnotationGraph) isOriginalImportMetadata(plan *ownedAnnotationMemberPlan) bool {
	if plan == nil || plan.sourceID != "" || plan.snapshot != nil || plan.role != ownedAnnotationBundledSchema || plan.nativeKey == nil || plan.nativeKey.SmartblockType() != coresb.SmartBlockTypeRelation {
		return false
	}
	key := domain.RelationKey(plan.nativeKey.InternalKey())
	return slices.Contains(originalOwnedAnnotationMetadataKeys(), key)
}
func (g *ownedAnnotationGraph) admitOriginalImportMetadata(ctx context.Context) error {
	for _, key := range originalOwnedAnnotationMetadataKeys() {
		unique, err := domain.NewUniqueKey(coresb.SmartBlockTypeRelation, key.String())
		if err != nil {
			return err
		}
		found := false
		for _, plan := range g.members {
			if plan.nativeKey != nil && plan.nativeKey.Marshal() == unique.Marshal() {
				found = true
				break
			}
		}
		if found {
			continue
		}
		id, err := g.space.GetRelationIdByKey(ctx, key)
		if err != nil {
			return err
		}
		plan := &ownedAnnotationMemberPlan{role: ownedAnnotationBundledSchema, nativeKey: unique, expectedTarget: id}
		if _, err := g.readOnlyContext(ctx, plan); err != nil {
			return err
		}
		g.additionalContext[id] = plan
	}
	return g.requireCurrentWriter(ctx)
}
