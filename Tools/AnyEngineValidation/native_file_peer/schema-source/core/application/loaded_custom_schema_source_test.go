//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance

package application

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/cache"
	sb "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	nativeexport "github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// A separate owned source journey. Every definition, option and document is
// created through the native object service. Native IDs, relation keys and type
// keys stay separate; no destination identifier or success result is injected.
func TestLoadedAccountCustomSchemaSource(t *testing.T) {
	f := newLoadedAccountFixture(t)
	creator := app.MustComponent[objectcreator.Service](f.service.GetApp())
	picker := app.MustComponent[*block.Service](f.service.GetApp())
	create := func(kind domain.TypeKey, details *domain.Details) (string, *domain.Details) {
		t.Helper()
		id, actual, err := creator.CreateObject(f.ctx, f.space.Id(),
			objectcreator.CreateObjectRequest{ObjectTypeKey: kind, Details: details})
		require.NoError(t, err)
		require.NotEmpty(t, id)
		require.NotNil(t, actual)
		require.NotEmpty(t, actual.GetString(bundle.RelationKeyUniqueKey))
		return id, actual
	}
	type property struct {
		Label, ID, Key, UniqueKey string
		Format                    model.RelationFormat
		Requested                 *domain.Details
	}
	properties := map[string]property{}
	addProperty := func(label string, format model.RelationFormat, extra func(*domain.Details)) property {
		t.Helper()
		details := domain.NewDetails()
		details.SetString(bundle.RelationKeyName, "Owned source "+label)
		details.SetString(bundle.RelationKeyDescription, "Native source schema fixture "+label)
		details.SetInt64(bundle.RelationKeyRelationFormat, int64(format))
		if format != model.RelationFormat_tag {
			details.SetInt64(bundle.RelationKeyRelationMaxCount, 1)
		} else {
			details.SetInt64(bundle.RelationKeyRelationMaxCount, 0)
		}
		if extra != nil {
			extra(details)
		}
		requested := details.Copy()
		id, actual := create(bundle.TypeKeyRelation, details)
		key := actual.GetString(bundle.RelationKeyRelationKey)
		require.NotEmpty(t, key)
		require.NotEqual(t, id, key)
		require.NotEqual(t, id, actual.GetString(bundle.RelationKeyUniqueKey))
		item := property{Label: label, ID: id, Key: key,
			UniqueKey: actual.GetString(bundle.RelationKeyUniqueKey), Format: format, Requested: requested}
		properties[label] = item
		return item
	}
	textProperty := addProperty("text", model.RelationFormat_longtext, func(d *domain.Details) {
		d.SetString(bundle.RelationKeyRelationDefaultValue, "native default a\u0301 — ברירת מחדל")
	})
	numberProperty := addProperty("number", model.RelationFormat_number, nil)
	checkProperty := addProperty("checkbox", model.RelationFormat_checkbox, nil)
	dateProperty := addProperty("date", model.RelationFormat_date, func(d *domain.Details) {
		d.SetBool(bundle.RelationKeyRelationFormatIncludeTime, true)
	})
	statusProperty := addProperty("status", model.RelationFormat_status, nil)
	tagProperty := addProperty("tag", model.RelationFormat_tag, nil)

	type option struct {
		ID, UniqueKey, RelationKey, Name, Color, OrderID string
	}
	options := []option{}
	addOption := func(property property, name, color, order string) option {
		t.Helper()
		details := domain.NewDetails()
		details.SetString(bundle.RelationKeyName, name)
		details.SetString(bundle.RelationKeyRelationKey, property.Key)
		details.SetString(bundle.RelationKeyRelationOptionColor, color)
		details.SetString(bundle.RelationKeyOrderId, order)
		id, actual := create(bundle.TypeKeyRelationOption, details)
		item := option{ID: id, UniqueKey: actual.GetString(bundle.RelationKeyUniqueKey),
			RelationKey: property.Key, Name: name, Color: color,
			OrderID: actual.GetString(bundle.RelationKeyOrderId)}
		require.NotEmpty(t, item.OrderID)
		require.NotEqual(t, item.ID, item.RelationKey)
		options = append(options, item)
		return item
	}
	statusA := addOption(statusProperty, "ממתין — a\u0301", "yellow", "a1")
	statusB := addOption(statusProperty, "הושלם", "green", "b1")
	tagA := addOption(tagProperty, "תג אחד", "blue", "a2")
	tagB := addOption(tagProperty, "תג שני", "red", "b2")
	require.NotEqual(t, statusA.OrderID, statusB.OrderID)
	require.NotEqual(t, tagA.OrderID, tagB.OrderID)

	featured := []string{textProperty.ID, statusProperty.ID}
	recommended := []string{numberProperty.ID, dateProperty.ID, tagProperty.ID}
	hidden := []string{checkProperty.ID}
	typeDetails := domain.NewDetails()
	typeDetails.SetString(bundle.RelationKeyName, "Owned native schema — סוג")
	typeDetails.SetString(bundle.RelationKeyPluralName, "Owned native schemas — סוגים")
	typeDetails.SetInt64(bundle.RelationKeyRecommendedLayout, int64(model.ObjectType_basic))
	typeDetails.SetStringList(bundle.RelationKeyRecommendedFeaturedRelations, featured)
	typeDetails.SetStringList(bundle.RelationKeyRecommendedRelations, recommended)
	typeDetails.SetStringList(bundle.RelationKeyRecommendedHiddenRelations, hidden)
	typeDetails.SetStringList(bundle.RelationKeyRecommendedFileRelations, []string{})
	typeID, actualType := create(bundle.TypeKeyObjectType, typeDetails)
	typeUniqueKey := actualType.GetString(bundle.RelationKeyUniqueKey)
	typeKey, err := domain.GetTypeKeyFromRawUniqueKey(typeUniqueKey)
	require.NoError(t, err)
	require.NotEmpty(t, typeKey)
	require.NotEqual(t, typeID, typeKey.String())
	require.NotEqual(t, typeID, typeKey.URL())

	// The native target-type ID is available only after creating the type.
	// Update the same native type through its ordinary locked Apply path.
	objectProperty := addProperty("object", model.RelationFormat_object, func(d *domain.Details) {
		d.SetStringList(bundle.RelationKeyRelationFormatObjectTypes, []string{typeID})
	})
	recommended = []string{numberProperty.ID, dateProperty.ID, objectProperty.ID, tagProperty.ID}
	require.NoError(t, cache.DoContextFullID(picker, f.ctx,
		domain.FullID{SpaceID: f.space.Id(), ObjectID: typeID}, func(object sb.SmartBlock) error {
			st := object.NewState()
			st.SetDetailAndBundledRelation(bundle.RelationKeyRecommendedRelations, domain.StringList(recommended))
			return object.Apply(st)
		}))

	createDocument := func(label, body string, values map[domain.RelationKey]domain.Value) string {
		t.Helper()
		root, child := "owned-schema-root-"+label, "owned-schema-body-"+label
		st := state.NewDoc(root, map[string]simple.Block{
			root: simple.New(&model.Block{Id: root, ChildrenIds: []string{child},
				Content: &model.BlockContentOfSmartblock{Smartblock: &model.BlockContentSmartblock{}}}),
			child: simple.New(&model.Block{Id: child,
				Content: &model.BlockContentOfText{Text: &model.BlockContentText{
					Text: body, Style: model.BlockContentText_Paragraph,
				}}}),
		}).(*state.State)
		details := domain.NewDetailsFromMap(values).Copy()
		details.SetString(bundle.RelationKeyName, "Owned typed document "+label)
		st.SetDetails(details)
		id, _, err := creator.CreateSmartBlockFromState(f.ctx, f.space.Id(), []domain.TypeKey{typeKey}, st)
		require.NoError(t, err)
		require.NotEmpty(t, id)
		return id
	}
	firstValues := map[domain.RelationKey]domain.Value{
		domain.RelationKey(textProperty.Key):   domain.String(""),
		domain.RelationKey(numberProperty.Key): domain.Float64(0),
		domain.RelationKey(checkProperty.Key):  domain.Bool(false),
		domain.RelationKey(dateProperty.Key):   domain.Float64(1795533300),
		domain.RelationKey(statusProperty.Key): domain.StringList([]string{}),
		domain.RelationKey(tagProperty.Key):    domain.StringList([]string{}),
		domain.RelationKey(objectProperty.Key): domain.StringList([]string{}),
	}
	firstID := createDocument("A", "מקור א — a\u0301", firstValues)
	secondValues := map[domain.RelationKey]domain.Value{
		domain.RelationKey(textProperty.Key):   domain.String("שָׁלוֹם — a\u0301 / 123\nשורה שנייה"),
		domain.RelationKey(numberProperty.Key): domain.Float64(19.625),
		domain.RelationKey(checkProperty.Key):  domain.Bool(true),
		domain.RelationKey(dateProperty.Key):   domain.Float64(1795536965),
		domain.RelationKey(statusProperty.Key): domain.StringList([]string{statusB.ID}),
		domain.RelationKey(tagProperty.Key):    domain.StringList([]string{tagB.ID, tagA.ID}),
		domain.RelationKey(objectProperty.Key): domain.StringList([]string{firstID}),
	}
	secondID := createDocument("B", "מקור ב — הפניה למקור א", secondValues)
	require.NotEqual(t, firstID, secondID)
	loadedSpaceFixtureWarm(t, f)
	captured, err := loadedCaptureFreshAttempts(f.ctx, func() (*LoadedAccountSpaceWitness, error) {
		return f.service.CaptureLoadedAccountSpaceWitness(f.ctx, f.token, loadedSpaceRequest(f))
	}, func(note loadedNativeCaptureAttempt) {
		f.privateNote(t, fmt.Sprintf("native-custom-schema-capture-attempt-%d", note.Attempt), map[string]any{
			"contract": "pinkha-native-source-capture-attempt-v1", "attemptLimit": loadedNativeCaptureAttemptLimit,
			"stage": "custom-schema", "attempt": note, "newCaptureRequiredAfterRefusal": true,
		})
	})
	require.NoError(t, err)
	receipt, err := captured.Receipt()
	require.NoError(t, err)
	require.True(t, receipt.AllNativeHeadRowsAccounted)
	require.True(t, receipt.AllCurrentObjectsCaptured)
	require.True(t, receipt.AccountSessionAuthorizedAtFinalCapture)
	require.True(t, receipt.CapturedSnapshotsBoundToUnchangedCheckpoint)
	require.True(t, receipt.IndexResolverSnapshotBound)
	require.Zero(t, receipt.ClosedResolverUnmapped)
	require.False(t, receipt.HasNativeSourceAdmission)
	require.False(t, receipt.SemanticCompleteness)
	require.False(t, receipt.HistorySemanticsValidated)
	require.False(t, receipt.PermitsDestinationWrites)

	originals := map[string]*nativeexport.NativeRawObject{}
	bases := map[string]*model.SmartBlockSnapshotBase{}
	for _, object := range captured.Objects() {
		require.NotContains(t, originals, object.ObjectID())
		originals[object.ObjectID()] = object
		base := new(model.SmartBlockSnapshotBase)
		require.NoError(t, proto.Unmarshal(object.SnapshotBase(), base))
		bases[object.ObjectID()] = base
	}
	rawObject := func(id string, kind model.SmartBlockType, uniqueKey string) *model.SmartBlockSnapshotBase {
		t.Helper()
		require.Contains(t, originals, id)
		require.Equal(t, kind, originals[id].Type())
		require.Equal(t, uniqueKey, originals[id].UniqueKey())
		require.NotNil(t, bases[id].Details)
		return bases[id]
	}
	assertValue := func(base *model.SmartBlockSnapshotBase, key domain.RelationKey, expected domain.Value) {
		t.Helper()
		actual, exists := base.Details.Fields[key.String()]
		require.True(t, exists, "native persisted field must remain present")
		require.True(t, proto.Equal(expected.ToProto(), actual), "native raw value must remain exact")
	}
	typeBase := rawObject(typeID, model.SmartBlockType_STType, typeUniqueKey)
	assertValue(typeBase, bundle.RelationKeyName, typeDetails.Get(bundle.RelationKeyName))
	assertValue(typeBase, bundle.RelationKeyPluralName, typeDetails.Get(bundle.RelationKeyPluralName))
	assertValue(typeBase, bundle.RelationKeyRecommendedLayout, domain.Int64(int64(model.ObjectType_basic)))
	for key, values := range map[domain.RelationKey][]string{
		bundle.RelationKeyRecommendedFeaturedRelations: featured,
		bundle.RelationKeyRecommendedRelations:         recommended,
		bundle.RelationKeyRecommendedHiddenRelations:   hidden,
		bundle.RelationKeyRecommendedFileRelations:     {},
	} {
		assertValue(typeBase, key, domain.StringList(values))
	}
	identitySet := map[string]bool{typeID: true, firstID: true, secondID: true}
	privateProperties := []map[string]any{}
	for _, label := range []string{"text", "number", "checkbox", "date", "object", "status", "tag"} {
		item := properties[label]
		require.False(t, identitySet[item.ID])
		identitySet[item.ID] = true
		base := rawObject(item.ID, model.SmartBlockType_STRelation, item.UniqueKey)
		assertValue(base, bundle.RelationKeyRelationKey, domain.String(item.Key))
		for key, value := range item.Requested.Iterate() {
			assertValue(base, key, value)
		}
		privateProperties = append(privateProperties, map[string]any{
			"label": label, "objectID": item.ID, "relationKey": item.Key, "uniqueKey": item.UniqueKey,
			"format": int32(item.Format), "snapshotSHA256": loadedFixtureHash(originals[item.ID].SnapshotBase()),
		})
	}
	privateOptions := []map[string]any{}
	for _, item := range options {
		require.False(t, identitySet[item.ID])
		identitySet[item.ID] = true
		base := rawObject(item.ID, model.SmartBlockType_STRelationOption, item.UniqueKey)
		assertValue(base, bundle.RelationKeyRelationKey, domain.String(item.RelationKey))
		assertValue(base, bundle.RelationKeyName, domain.String(item.Name))
		assertValue(base, bundle.RelationKeyRelationOptionColor, domain.String(item.Color))
		assertValue(base, bundle.RelationKeyOrderId, domain.String(item.OrderID))
		privateOptions = append(privateOptions, map[string]any{
			"objectID": item.ID, "uniqueKey": item.UniqueKey, "relationKey": item.RelationKey,
			"orderID": item.OrderID, "snapshotSHA256": loadedFixtureHash(originals[item.ID].SnapshotBase()),
		})
	}
	for id, values := range map[string]map[domain.RelationKey]domain.Value{firstID: firstValues, secondID: secondValues} {
		base := rawObject(id, model.SmartBlockType_Page, "")
		require.Equal(t, []string{typeKey.URL()}, base.ObjectTypes)
		formats := map[string]model.RelationFormat{}
		for _, link := range base.RelationLinks {
			formats[link.Key] = link.Format
		}
		for _, item := range properties {
			require.Equal(t, item.Format, formats[item.Key])
			require.Contains(t, formats, item.Key)
		}
		for key, value := range values {
			assertValue(base, key, value)
		}
	}
	require.Len(t, identitySet, 14)
	count := loadedSnapshotJSONViews(t, captured)
	manifestRaw, err := os.ReadFile(filepath.Join(captured.PrivateBundleDirectory(), "manifest.json"))
	require.NoError(t, err)
	var manifest NativeSourceBundleManifest
	require.NoError(t, json.Unmarshal(manifestRaw, &manifest))
	f.privateNote(t, "native-custom-schema-source", map[string]any{
		"contract":        "pinkha-native-custom-schema-source-v1",
		"sourceAccountID": f.account.Id, "sourceSpaceID": f.space.Id(),
		"sourceReceipt": receipt, "capturedObjects": count, "customIdentityCount": len(identitySet),
		"typeObjectID": typeID, "typeUniqueKey": typeUniqueKey, "typeKey": typeKey.String(),
		"properties": privateProperties, "options": privateOptions,
		"featuredRelationIDs": featured, "recommendedRelationIDs": recommended,
		"hiddenRelationIDs": hidden, "fileRelationIDs": []string{},
		"firstDocumentID": firstID, "secondDocumentID": secondID,
		"originalSourceManifestSHA256":              loadedFixtureHash(manifestRaw),
		"originalSourceRowsSHA256":                  manifest.SourceRows.SHA256,
		"nativeDefinitionsAndCurrentValuesVerified": true,
		"emptyAndDefaultValuesVerified":             true, "orderedNativeIdentitiesVerified": true,
		"originalPBAndJSONMembersVerified": count, "wholeSpaceSemanticMigrationComplete": false,
	})
	t.Logf("NATIVE_CUSTOM_SCHEMA_SOURCE_OBSERVATION custom_type=1 properties=7 options=4 typed_documents=2 identities=14 original_snapshots=%d", count)
}
