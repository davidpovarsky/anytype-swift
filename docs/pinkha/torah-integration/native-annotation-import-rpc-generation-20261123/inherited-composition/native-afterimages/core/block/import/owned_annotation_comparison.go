package importer

import (
	"context"
	"path/filepath"
	"sort"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/editor/template"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	"github.com/anyproto/anytype-heart/core/block/import/markdown/anymark"
	"github.com/anyproto/anytype-heart/core/converter/pbc"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/domain/objectorigin"
	torahtransport "github.com/anyproto/anytype-heart/core/pinkha/torahtransport"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/proto"
)

// expectedConvertedSnapshot applies the original typed normalization helpers to
// an owned copy of the exact generated archive model. It checks the real
// converter's output; it is never installed as a replacement converter result.
func (g *ownedAnnotationGraph) expectedConvertedSnapshot(ctx context.Context, plan *ownedAnnotationMemberPlan, actual *common.Snapshot, ids map[string]string, formats map[domain.RelationKey]int32) (*pb.ChangeSnapshot, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	raw := proto.Clone(plan.snapshot).(*pb.SnapshotWithType)
	expected, err := common.NewSnapshotModelFromProto(raw)
	if err != nil {
		return nil, err
	}
	// Unknown/unrepresented semantic fields cannot silently disappear in the
	// original common-model conversion and then receive a body-equality claim.
	if !proto.Equal(expected.ToProto(), plan.snapshot.Snapshot) {
		return nil, ownedAnnotationRefused("unrepresented_snapshot_fields")
	}
	if expected.SbType == coresb.SmartBlockTypePage {
		var empty *model.Block
		hasRoot := false
		for _, b := range expected.Data.Blocks {
			if b == nil {
				return nil, ownedAnnotationRefused("nil_source_block")
			}
			if b.Content == nil {
				empty = b
			} else if b.GetSmartblock() != nil {
				hasRoot = true
				break
			}
		}
		if !hasRoot && empty != nil {
			empty.Content = &model.BlockContentOfSmartblock{Smartblock: &model.BlockContentSmartblock{}}
		}
	}
	if plan.role == ownedAnnotationFileObject {
		expected.Data.Details.SetString(bundle.RelationKeySource, filepath.Join(g.stage.TempDir(), filepath.FromSlash(plan.fileSource)))
	}
	details := expected.Data.Details
	details.SetString(bundle.RelationKeyOldAnytypeID, plan.sourceID)
	details.SetString(bundle.RelationKeySourceFilePath, filepath.Join(g.archive.spaceID, plan.sourceID))
	if details.GetInt64(bundle.RelationKeyCreatedDate) == 0 {
		actualCreated := actual.Snapshot.Data.Details.GetInt64(bundle.RelationKeyCreatedDate)
		if actualCreated <= 0 || actualCreated < g.conversionStarted || actualCreated > g.conversionFinished {
			return nil, ownedAnnotationRefused("original_conversion_timestamp")
		}
		details.SetInt64(bundle.RelationKeyCreatedDate, actualCreated)
	}
	st, err := state.NewDocFromSnapshot("", expected.ToProto())
	if err != nil {
		return nil, err
	}
	if err := common.UpdateLinksToObjects(st, ids); err != nil {
		return nil, err
	}
	common.UpdateObjectIDsInRelations(st, ids, formats)
	collectionIDs := st.GetStoreSlice(template.CollectionStoreKey)
	for i, id := range collectionIDs {
		if mapped, ok := ids[id]; ok {
			collectionIDs[i] = mapped
		}
	}
	if len(collectionIDs) != 0 {
		st.UpdateStoreSlice(template.CollectionStoreKey, collectionIDs)
	}
	expected.Data.Details = expected.Data.Details.Merge(st.CombinedDetails())
	expected.Data.Blocks = st.Blocks()
	expected.Data.ObjectTypes = domain.MarshalTypeKeys(st.ObjectTypeKeys())
	expected.Data.Collections = st.Store()
	var removed []domain.RelationKey
	for _, key := range bundle.LocalAndDerivedRelationKeys {
		if key != bundle.RelationKeyIsFavorite && key != bundle.RelationKeyIsArchived &&
			key != bundle.RelationKeyCreatedDate && key != bundle.RelationKeyLastModifiedDate &&
			key != bundle.RelationKeyId && key != bundle.RelationKeyResolvedLayout {
			removed = append(removed, key)
		}
	}
	expected.Data.Details = expected.Data.Details.CopyWithoutKeys(removed...)
	return expected.ToProto(), ctx.Err()
}

func (g *ownedAnnotationGraph) requireExactConverterOutput(ctx context.Context, p *importProcessor) error {
	b := p.nativeMapping
	if b == nil || len(b.problems) != 0 || len(b.generatedIDs) != 0 || len(b.keptIDs) != 0 ||
		len(b.sources) != len(g.members) || len(p.converterResponse.Snapshots) != len(g.members) ||
		p.converterResponse.RootObjectID != "" || len(p.converterResponse.TypesCreated) != 0 {
		return ownedAnnotationRefused("original_converter_coverage")
	}
	ids := make(map[string]string, len(g.members))
	byConverter := make(map[string]*ownedAnnotationMemberPlan, len(g.members))
	formats := make(map[domain.RelationKey]int32)
	for _, row := range b.sources {
		plan := g.members[row.sourceObjectID]
		if plan == nil || !row.selected || row.encoding != ".pb" || row.archivePath != g.stage.archivePath ||
			row.memberPath != plan.memberPath || row.sourceSpaceID != g.archive.spaceID || row.converterID == "" ||
			ids[row.sourceObjectID] != "" || byConverter[row.converterID] != nil {
			return ownedAnnotationRefused("original_source_correspondence")
		}
		ids[row.sourceObjectID], byConverter[row.converterID] = row.converterID, plan
		if plan.nativeKey != nil && plan.nativeKey.SmartblockType() == coresb.SmartBlockTypeRelation {
			value := domain.NewDetailsFromProto(plan.snapshot.Snapshot.Data.Details).GetInt64(bundle.RelationKeyRelationFormat)
			formats[domain.RelationKey(plan.nativeKey.InternalKey())] = int32(value)
		}
	}
	if len(ids) != len(g.members) {
		return ownedAnnotationRefused("incomplete_source_correspondence")
	}
	seen := make(map[string]bool, len(byConverter))
	for _, actual := range p.converterResponse.Snapshots {
		if actual == nil || actual.Snapshot == nil || actual.Snapshot.Data == nil || actual.Snapshot.Data.Details == nil || seen[actual.Id] {
			return ownedAnnotationRefused("invalid_converter_snapshot")
		}
		plan := byConverter[actual.Id]
		if plan == nil || actual.Snapshot.SbType.ToProto() != plan.snapshot.SbType {
			return ownedAnnotationRefused("converter_native_kind")
		}
		expected, err := g.expectedConvertedSnapshot(ctx, plan, actual, ids, formats)
		if err != nil {
			return err
		}
		if !proto.Equal(expected, actual.Snapshot.ToProto()) {
			return ownedAnnotationRefused("original_converter_semantic_delta")
		}
		seen[actual.Id] = true
	}
	g.byConverter, g.sourceToConverter = byConverter, ids
	return g.requireCurrentWriter(ctx)
}

// Original local/derived details and original import bookkeeping are not user
// annotation content. Every other persisted value, nested protobuf field, mark,
// child order, relation/collection value and block body remains compared.
func ownedAnnotationComparisonDetails(details *domain.Details) *domain.Details {
	removed := append([]domain.RelationKey(nil), bundle.LocalAndDerivedRelationKeys...)
	removed = append(removed, bundle.RelationKeyId, bundle.RelationKeySpaceId,
		bundle.RelationKeyCreatedDate, bundle.RelationKeyLastModifiedDate,
		bundle.RelationKeyCreator, bundle.RelationKeyLastModifiedBy,
		bundle.RelationKeyOrigin, bundle.RelationKeyImportType,
		bundle.RelationKeyOldAnytypeID, bundle.RelationKeySourceFilePath)
	return details.CopyWithoutKeys(removed...)
}

func canonicalOwnedAnnotationSnapshot(snapshot *pb.SnapshotWithType) (*pb.SnapshotWithType, error) {
	if snapshot == nil || snapshot.Snapshot == nil || snapshot.Snapshot.Data == nil {
		return nil, ownedAnnotationRefused("missing_comparison_snapshot")
	}
	result := proto.Clone(snapshot).(*pb.SnapshotWithType)
	data := result.Snapshot.Data
	data.Details = ownedAnnotationComparisonDetails(domain.NewDetailsFromProto(data.Details)).ToProto()
	ids := make(map[string]bool, len(data.Blocks))
	for _, b := range data.Blocks {
		if b == nil || b.Id == "" || ids[b.Id] {
			return nil, ownedAnnotationRefused("non_unique_body_block")
		}
		ids[b.Id] = true
	}
	// The inventory order of independent protobuf blocks is not child order.
	// ChildrenIds, text/marks and every nested repeated field remain untouched.
	sort.Slice(data.Blocks, func(i, j int) bool { return data.Blocks[i].Id < data.Blocks[j].Id })
	if info := data.FileInfo; info != nil {
		paths := make(map[string]bool, len(info.EncryptionKeys))
		for _, key := range info.EncryptionKeys {
			if key == nil || key.Path == "" || paths[key.Path] {
				return nil, ownedAnnotationRefused("non_unique_body_file_key")
			}
			paths[key.Path] = true
		}
		sort.Slice(info.EncryptionKeys, func(i, j int) bool { return info.EncryptionKeys[i].Path < info.EncryptionKeys[j].Path })
	}
	return result, nil
}

func (g *ownedAnnotationGraph) requireSchemaSnapshotCompatibility(ctx context.Context, plan *ownedAnnotationMemberPlan, actual *pb.SnapshotWithType) error {
	if plan == nil || plan.snapshot == nil || actual == nil || actual.Snapshot == nil || actual.Snapshot.Data == nil ||
		plan.snapshot.SbType != actual.SbType || plan.snapshot.Snapshot.Data.Key != actual.Snapshot.Data.Key {
		return ownedAnnotationRefused("schema_snapshot_shape")
	}
	raw := proto.Clone(plan.snapshot).(*pb.SnapshotWithType)
	ids := make(map[string]string)
	formats := make(map[domain.RelationKey]int32)
	for sourceID, member := range g.members {
		if member.expectedTarget != "" {
			ids[sourceID] = member.expectedTarget
		}
		if member.nativeKey != nil && member.nativeKey.SmartblockType() == coresb.SmartBlockTypeRelation {
			formats[domain.RelationKey(member.nativeKey.InternalKey())] = int32(domain.NewDetailsFromProto(member.snapshot.Snapshot.Data.Details).GetInt64(bundle.RelationKeyRelationFormat))
		}
	}
	// Root identity is the actual derived native target. All original child
	// blocks and their ordering are preserved; only this root ID is remapped.
	for _, b := range raw.Snapshot.Data.Blocks {
		if b == nil {
			return ownedAnnotationRefused("nil_schema_block")
		}
		if b.Id == plan.sourceID {
			b.Id = plan.expectedTarget
		}
		for i, id := range b.ChildrenIds {
			if id == plan.sourceID {
				b.ChildrenIds[i] = plan.expectedTarget
			}
		}
	}
	st, err := state.NewDocFromSnapshot(plan.expectedTarget, raw.Snapshot)
	if err != nil {
		return err
	}
	if err := common.UpdateLinksToObjects(st, ids); err != nil {
		return err
	}
	common.UpdateObjectIDsInRelations(st, ids, formats)
	var expected pb.SnapshotWithType
	bytes := pbc.NewConverter(st, false).Convert(raw.SbType)
	if len(bytes) == 0 {
		return ownedAnnotationRefused("schema_expected_conversion")
	}
	if err := proto.Unmarshal(bytes, &expected); err != nil {
		return err
	}
	left, err := canonicalOwnedAnnotationSnapshot(&expected)
	if err != nil {
		return err
	}
	right, err := canonicalOwnedAnnotationSnapshot(actual)
	if err != nil {
		return err
	}
	if !proto.Equal(left, right) {
		return ownedAnnotationRefused("source_target_schema_semantics_differ")
	}
	return ctx.Err()
}

// Verify the real torahtransport pass and freeze its exact before-create state.
// Reconstructed copies are comparison controls only, never production inputs.
func (g *ownedAnnotationGraph) admitCreationGraph(ctx context.Context, p *importProcessor) error {
	if err := g.requireCurrentWriter(ctx); err != nil {
		return err
	}
	if len(g.nativeIDs) != len(g.members) || len(g.targets) != len(g.members) || p.nativeMapping == nil || len(p.nativeMapping.problems) != 0 {
		return ownedAnnotationRefused("creation_graph_assignment_coverage")
	}
	expected := make(map[string]*common.Snapshot, len(g.members))
	objects := make([]torahtransport.Object, 0, len(g.members))
	for _, actual := range p.converterResponse.Snapshots {
		plan := g.byConverter[actual.Id]
		baseline := g.converted[actual.Id]
		if plan == nil || baseline == nil {
			return ownedAnnotationRefused("creation_graph_source")
		}
		snapshot, err := common.NewSnapshotModelFromProto(&pb.SnapshotWithType{SbType: plan.snapshot.SbType, Snapshot: proto.Clone(baseline).(*pb.ChangeSnapshot)})
		if err != nil {
			return err
		}
		if plan.role == ownedAnnotationFileObject {
			common.UpdateObjectIDsInDetails(snapshot.Data.Details, p.oldIDToNew, p.relationKeysToFormat)
		}
		expected[actual.Id] = &common.Snapshot{Id: actual.Id, Snapshot: snapshot}
		objects = append(objects, torahtransport.Object{ID: actual.Id, OriginalID: snapshot.Data.Details.GetString(bundle.RelationKeyOldAnytypeID), PropertyKey: snapshot.Data.Key, Details: snapshot.Data.Details})
	}
	if err := torahtransport.RemapObjects(g.spaceID, objects, p.oldIDToNew); err != nil {
		return err
	}
	g.beforeCreate = make(map[string]*pb.ChangeSnapshot, len(expected))
	for _, actual := range p.converterResponse.Snapshots {
		if !proto.Equal(expected[actual.Id].Snapshot.ToProto(), actual.Snapshot.ToProto()) {
			return ownedAnnotationRefused("original_creation_graph_changed")
		}
		g.beforeCreate[actual.Id] = proto.Clone(actual.Snapshot.ToProto()).(*pb.ChangeSnapshot)
	}
	for _, alias := range p.nativeMapping.aliases {
		plan := g.byConverter[alias.ConverterID]
		if plan == nil || plan.nativeKey == nil || alias.SourceKey != plan.nativeKey.InternalKey() || alias.NativeKey != alias.SourceKey {
			return ownedAnnotationRefused("original_native_schema_key_changed")
		}
	}
	return g.requireCurrentWriter(ctx)
}

func (g *ownedAnnotationGraph) expectedCreatedPage(p *importProcessor, converterID, nativeID string) (*pb.SnapshotWithType, error) {
	baseline := g.beforeCreate[converterID]
	plan := g.byConverter[converterID]
	if baseline == nil || plan == nil || plan.role != ownedAnnotationFreshPage {
		return nil, ownedAnnotationRefused("expected_page_source")
	}
	modelCopy, err := common.NewSnapshotModelFromProto(&pb.SnapshotWithType{SbType: plan.snapshot.SbType, Snapshot: proto.Clone(baseline).(*pb.ChangeSnapshot)})
	if err != nil {
		return nil, err
	}
	data := modelCopy.Data
	found := false
	for _, b := range data.Blocks {
		if b.Id == nativeID {
			found = true
			break
		}
	}
	if !found {
		data.Blocks = anymark.AddRootBlock(data.Blocks, nativeID)
	}
	created := data.Details.GetInt64(bundle.RelationKeyCreatedDate)
	if data.Details.GetInt64(bundle.RelationKeyLastModifiedDate) == 0 && created != 0 {
		data.Details.SetInt64(bundle.RelationKeyLastModifiedDate, created)
	}
	if created > 0 {
		data.OriginalCreatedTimestamp = created
	}
	origin := objectorigin.Import(model.Import_Pb)
	data.Details.SetInt64(bundle.RelationKeyOrigin, int64(origin.Origin))
	data.Details.SetInt64(bundle.RelationKeyImportType, int64(origin.ImportType))
	st, err := state.NewDocFromSnapshot(nativeID, modelCopy.ToProto())
	if err != nil {
		return nil, err
	}
	st.SetLocalDetail(bundle.RelationKeyLastModifiedDate, data.Details.Get(bundle.RelationKeyLastModifiedDate))
	common.UpdateObjectIDsInRelations(st, p.oldIDToNew, p.relationKeysToFormat)
	if err := common.UpdateLinksToObjects(st, p.oldIDToNew); err != nil {
		return nil, err
	}
	// Exact original updateKeys semantics; no alternative ID assignment.
	for key, value := range st.Details().Iterate() {
		if mapped, ok := p.oldIDToNew[string(key)]; ok && mapped != string(key) {
			st.SetDetail(domain.RelationKey(mapped), value)
			if format, ok := p.relationKeysToFormat[key]; ok {
				st.AddRelationLinks(&model.RelationLink{Key: mapped, Format: model.RelationFormat(format)})
			}
			st.RemoveRelation(key)
		}
	}
	if mapped, ok := p.oldIDToNew[st.ObjectTypeKey().String()]; ok {
		st.SetObjectTypeKey(domain.TypeKey(mapped))
	}
	raw := pbc.NewConverter(st, false).Convert(plan.snapshot.SbType)
	expected := &pb.SnapshotWithType{}
	if len(raw) == 0 {
		return nil, ownedAnnotationRefused("expected_native_page_conversion")
	}
	if err := proto.Unmarshal(raw, expected); err != nil {
		return nil, err
	}
	return expected, nil
}
