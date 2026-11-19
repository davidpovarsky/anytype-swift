package detailservice

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block/editor/basic"
	"github.com/anyproto/anytype-heart/core/block/editor/converter"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock/smarttest"
	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// The native detail service and native projector decide eligibility. The
// existing fixture supplies only object lookup; no synthetic ready result or
// substitute attachment implementation participates in this test.
func TestTorahExplicitAttachmentsSurviveOrdinaryDetailsEdits(t *testing.T) {
	const objectID = "attachment-document"
	const canonicalKey domain.RelationKey = "attachmentCanonical"
	const canonical = `{"version":1,"items":[{"id":"source","kind":"ref","role":"context","providerID":"sefaria","canonicalKey":"Genesis 1:1","externalID":"Genesis 1:1","labelHe":"בראשית א:א"}]}`
	f := newFixture(t)
	manifest, err := json.Marshal(map[string]any{
		"schemaVersion": 1, "spaceId": spaceId, "manifestObjectId": "attachment-manifest", "provisioningState": "complete",
		"documentAssociationsPropertyId": "attachment-canonical-property", "documentAssociationsPropertyKey": canonicalKey,
		"registeredDocumentTypes": map[string]string{"chiddush": "h", "article": "a", "research": "r"},
		"defaultTemplateIds":      map[string]string{"chiddush": "th", "article": "ta", "research": "tr"},
		"parentPropertyId":        "parent", "parentPropertyKey": "parentKey", "orderPropertyId": "order", "orderPropertyKey": "orderKey",
		"folderTypeId": "folder", "bookFolderTypeId": "book",
	})
	require.NoError(t, err)
	f.store.AddObjects(t, spaceId, []objectstore.TestObject{{
		bundle.RelationKeyId:             domain.String("attachment-canonical-property"),
		bundle.RelationKeySpaceId:        domain.String(spaceId),
		bundle.RelationKeyRelationKey:    domain.String(string(canonicalKey)),
		bundle.RelationKeyRelationFormat: domain.Int64(int64(model.RelationFormat_longtext)),
		bundle.RelationKeyLayout:         domain.Int64(int64(model.ObjectType_relation)),
	}, {
		bundle.RelationKeyId:          domain.String("attachment-manifest"),
		bundle.RelationKeySpaceId:     domain.String(spaceId),
		bundle.RelationKeyName:        domain.String(torah.ManifestUniqueKey),
		bundle.RelationKeyDescription: domain.String(string(manifest)),
	}})
	sb := smarttest.New(objectID)
	sb.SetSpaceId(spaceId)
	initial := sb.NewState()
	initial.SetDetails(domain.NewDetails().
		SetString(bundle.RelationKeyId, objectID).
		SetString(bundle.RelationKeyName, "before explicit attachment").
		SetString(bundle.RelationKeySpaceId, spaceId).
		SetString(bundle.RelationKeyType, "h").
		SetInt64(bundle.RelationKeyLayout, int64(model.ObjectType_basic)).
		SetString(canonicalKey, canonical))
	projector, ok := f.store.SpaceIndex(spaceId).(interface {
		TorahLocalDetails(context.Context, *domain.Details) (*domain.Details, error)
	})
	require.True(t, ok, "the original native Space index must expose its actual projector")
	projected, err := projector.TorahLocalDetails(context.Background(), initial.CombinedDetails())
	require.NoError(t, err)
	require.NotNil(t, projected)
	require.True(t, projected.GetBool(domain.RelationKey(torah.ReadyKey)), "eligibility comes from the provisioned native store")
	require.Len(t, projected.GetStringList(domain.RelationKey(torah.SourcesKey)), 1)
	initial.AddLocalDetails(projected)
	require.Empty(t, initial.PickRelationLinks())
	require.NoError(t, sb.Apply(initial))
	f.getter.EXPECT().GetObject(mock.Anything, objectID).Return(sb, nil).Times(2)
	keys := []string{torah.SourcesKey, torah.TopicsKey, torah.WordsKey}
	for attempt := 0; attempt < 2; attempt++ {
		require.NoError(t, f.Service.(*service).AttachTorahProperties(nil, objectID, keys))
		links := sb.NewState().PickRelationLinks()
		require.Len(t, links, len(keys), "repeated explicit attachment stays idempotent")
		actualKeys := make([]string, 0, len(links))
		for _, link := range links {
			require.Equal(t, model.RelationFormat_tag, link.Format)
			actualKeys = append(actualKeys, link.Key)
		}
		require.ElementsMatch(t, keys, actualKeys)
	}
	editor := basic.NewBasic(sb, f.store.SpaceIndex(spaceId), converter.NewLayoutConverter(), nil)
	require.NoError(t, editor.SetDetails(nil, []domain.Detail{{Key: bundle.RelationKeyName, Value: domain.String("after ordinary edit")}}, false))
	actual := sb.NewState()
	require.Equal(t, "after ordinary edit", actual.Details().GetString(bundle.RelationKeyName))
	require.Equal(t, canonical, actual.Details().GetString(canonicalKey))
	attached := []string{}
	for _, link := range actual.PickRelationLinks() {
		if torah.IsProperty(link.Key) {
			attached = append(attached, link.Key)
		}
	}
	require.ElementsMatch(t, keys, attached, "ordinary edits preserve the explicit native attachment decision")
	require.Equal(t, projected.GetStringList(domain.RelationKey(torah.SourcesKey)), actual.LocalDetails().GetStringList(domain.RelationKey(torah.SourcesKey)))
}
