//go:build pinkha_readonlyfixer

package readonlyfixer

import (
	"context"
	"errors"
	"testing"

	"github.com/anyproto/any-sync/app/logger"
	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	mock_space "github.com/anyproto/anytype-heart/space/clientspace/mock_clientspace"
	"github.com/stretchr/testify/assert"
)

func nativeDefinition(key string) *domain.Details {
	return domain.NewDetails().SetString(bundle.RelationKeyId, key).
		SetString(bundle.RelationKeySpaceId, "native-space").
		SetString(bundle.RelationKeyRelationKey, key).
		SetString(bundle.RelationKeySourceObject, "_br"+key).
		SetInt64(bundle.RelationKeyRelationFormat, int64(model.RelationFormat_tag)).
		SetBool(bundle.RelationKeyRelationReadonlyValue, true)
}

func TestNativeDerivedDefinitionsSurviveStartupReadonlyMaintenance(t *testing.T) {
	store := objectstore.NewStoreFixture(t)
	objects := []objectstore.TestObject{}
	for _, def := range torah.Definitions {
		object := objectstore.TestObject{}
		for key, value := range nativeDefinition(def.Key).Iterate() {
			object[key] = value
		}
		objects = append(objects, object)
	}
	store.AddObjects(t, "native-space", objects)
	space := mock_space.NewMockSpace(t)
	space.EXPECT().Id().Return("native-space").Maybe()
	// No DoCtx expectation: any write to an immutable definition fails the test.
	toChange, changed, err := (Migration{}).Run(context.Background(), logger.NewNamed("test"), store.SpaceIndex("native-space"), space)
	assert.NoError(t, err)
	assert.Zero(t, toChange)
	assert.Zero(t, changed)
}

func TestNativeDefinitionExclusionUsesIdentityNotDisplayName(t *testing.T) {
	cases := []struct {
		name     string
		details  *domain.Details
		excluded bool
	}{
		{"sources", nativeDefinition(torah.SourcesKey), true},
		{"topics", nativeDefinition(torah.TopicsKey), true},
		{"words", nativeDefinition(torah.WordsKey), true},
		{"user display name collision", nativeDefinition("user-key").SetString(bundle.RelationKeyName, "מקור/ות"), false},
		{"fixed key without bundled identity", nativeDefinition(torah.SourcesKey).SetString(bundle.RelationKeySourceObject, "user-source"), false},
		{"wrong format", nativeDefinition(torah.SourcesKey).SetInt64(bundle.RelationKeyRelationFormat, int64(model.RelationFormat_status)), false},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			input := []database.Record{{Details: test.details}}
			kept, err := preserveNativeDerivedDefinitions(input, nil)
			assert.NoError(t, err)
			assert.Equal(t, test.excluded, len(kept) == 0)
			assert.True(t, test.details.GetBool(bundle.RelationKeyRelationReadonlyValue))
		})
	}
}

func TestNativeDefinitionExclusionPreservesQueryErrors(t *testing.T) {
	expected := errors.New("query failed")
	_, err := preserveNativeDerivedDefinitions(nil, expected)
	assert.ErrorIs(t, err, expected)
}
