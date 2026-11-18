package typeprovider

import (
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space/spacedomain"
	"github.com/stretchr/testify/require"
)

func TestPinkhaPrivateRegistryRequiresCanonicalSpaceRoot(t *testing.T) {
	raw, err := torahopscontract.Root("space-a")
	require.NoError(t, err)
	tp, key, err := GetTypeAndKeyFromRootForSpace("space-a", raw)
	require.NoError(t, err)
	require.Equal(t, smartblock.SmartBlockTypePinkhaTorahOperations, tp)
	require.Equal(t, "v1", key)
	for _, spaceID := range []string{"", "space-b"} {
		_, _, err = GetTypeAndKeyFromRootForSpace(spaceID, raw)
		require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
	}
	root, err := objecttree.UnmarshallRoot(raw)
	require.NoError(t, err)
	root.SpaceId = ""
	_, _, err = GetTypeAndKeyFromRootChange(root)
	require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
}

func TestPinkhaPrivateRegistryRejectsGenericEnumForgery(t *testing.T) {
	payload, err := (&model.ObjectChangePayload{
		SmartBlockType: model.SmartBlockType(smartblock.SmartBlockTypePinkhaTorahOperations), Key: "v1",
	}).Marshal()
	require.NoError(t, err)
	_, _, err = GetTypeAndKeyFromRootChange(&treechangeproto.RootChange{
		SpaceId: "space-a", ChangeType: spacedomain.ChangeType, ChangePayload: payload,
	})
	require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
	payload, err = (&model.ObjectChangePayload{SmartBlockType: model.SmartBlockType_Page}).Marshal()
	require.NoError(t, err)
	tp, _, err := GetTypeAndKeyFromRootChange(&treechangeproto.RootChange{ChangeType: spacedomain.ChangeType, ChangePayload: payload})
	require.NoError(t, err)
	require.Equal(t, smartblock.SmartBlockTypePage, tp, "legacy generic page resolution is unchanged")
}

func TestPinkhaPrivateCachedTypeStillRequiresReceivingSpace(t *testing.T) {
	raw, err := torahopscontract.Root("space-a")
	require.NoError(t, err)
	p := &provider{cache: map[string]smartblock.SmartBlockType{raw.Id: smartblock.SmartBlockTypePinkhaTorahOperations}}
	tp, err := p.Type("space-a", raw.Id)
	require.NoError(t, err)
	require.Equal(t, smartblock.SmartBlockTypePinkhaTorahOperations, tp)
	for _, spaceID := range []string{"", "space-b"} {
		_, err = p.Type(spaceID, raw.Id)
		require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
	}
}
