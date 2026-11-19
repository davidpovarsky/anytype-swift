package basic

import (
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// Exercise the original basic editor against its real State and indexed
// relation definitions. Only the three exact native property keys are local
// projections; an ordinary user property with a similar key must still attach.
func TestTorahOrdinaryDetailsDoNotAttachProjectedProperties(t *testing.T) {
	const canonicalKey domain.RelationKey = "attachmentCanonical"
	const userTag domain.RelationKey = "attachmentUserTag"
	const lookalike domain.RelationKey = "pinkhaTorahSourcesCustom"
	const canonical = `{"version":1,"items":[],"unknown":{"retained":true}}`
	for _, api := range []string{"SetDetails", "UpdateDetails"} {
		for _, alreadyAttached := range []bool{false, true} {
			name := api + "/unattached"
			if alreadyAttached {
				name = api + "/explicit-source-already-attached"
			}
			t.Run(name, func(t *testing.T) {
				f := newBasicFixture(t)
				for _, key := range []domain.RelationKey{canonicalKey, userTag, lookalike} {
					format := model.RelationFormat_tag
					if key == canonicalKey {
						format = model.RelationFormat_longtext
					}
					f.store.AddObjects(t, []objectstore.TestObject{{
						bundle.RelationKeyId:             domain.String("rel-" + string(key)),
						bundle.RelationKeySpaceId:        domain.String(spaceId),
						bundle.RelationKeyRelationKey:    domain.String(string(key)),
						bundle.RelationKeyUniqueKey:      domain.String("rel-" + string(key)),
						bundle.RelationKeyRelationFormat: domain.Int64(int64(format)),
					}})
				}
				initial := f.sb.NewState()
				initial.SetDetail(bundle.RelationKeyName, domain.String("before ordinary edit"))
				initial.SetDetail(canonicalKey, domain.String(canonical))
				for _, key := range []string{torah.SourcesKey, torah.TopicsKey, torah.WordsKey} {
					initial.SetLocalDetail(domain.RelationKey(key), domain.StringList([]string{"projected-" + key}))
				}
				if alreadyAttached {
					initial.AddRelationLinks(&model.RelationLink{Key: torah.SourcesKey, Format: model.RelationFormat_tag})
				}
				require.NoError(t, f.sb.Apply(initial))
				updates := []domain.Detail{
					{Key: bundle.RelationKeyName, Value: domain.String("after ordinary edit")},
					{Key: userTag, Value: domain.StringList([]string{"ordinary-option"})},
					{Key: lookalike, Value: domain.StringList([]string{"lookalike-option"})},
				}
				if api == "SetDetails" {
					require.NoError(t, f.basic.SetDetails(nil, updates, false))
				} else {
					require.NoError(t, f.basic.UpdateDetails(nil, func(current *domain.Details) (*domain.Details, error) {
						for _, update := range updates {
							current.Set(update.Key, update.Value)
						}
						return current, nil
					}))
				}
				actual := f.sb.NewState()
				require.Equal(t, "after ordinary edit", actual.Details().GetString(bundle.RelationKeyName))
				require.Equal(t, canonical, actual.Details().GetString(canonicalKey))
				links := map[string]bool{}
				for _, link := range actual.PickRelationLinks() {
					links[link.Key] = true
				}
				require.True(t, links[string(userTag)], "ordinary user tag keeps the native automatic attachment behavior")
				require.True(t, links[string(lookalike)], "a similar key is not a native property")
				require.Equal(t, alreadyAttached, links[torah.SourcesKey], "an ordinary edit must preserve the existing attachment decision")
				require.False(t, links[torah.TopicsKey], "projected topics must not create an attachment")
				require.False(t, links[torah.WordsKey], "projected words must not create an attachment")
				for _, key := range []string{torah.SourcesKey, torah.TopicsKey, torah.WordsKey} {
					require.Equal(t, []string{"projected-" + key}, actual.LocalDetails().GetStringList(domain.RelationKey(key)))
					require.False(t, actual.Details().Has(domain.RelationKey(key)), "projection values remain local")
				}
			})
		}
	}
}
