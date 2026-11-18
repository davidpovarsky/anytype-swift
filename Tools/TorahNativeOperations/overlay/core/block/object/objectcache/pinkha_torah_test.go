package objectcache

import (
	"context"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/object/payloadcreator"
	"github.com/anyproto/anytype-heart/core/domain"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
	"testing"
)

// Only Space identity is required for derivation. Any unexpected request for
// account keys, tree creation or indexing panics through the nil embedded API.
type derivationSpace struct {
	smartblock.Space
	id string
}

func (s derivationSpace) Id() string { return s.id }

func TestPinkhaPrivateCreationIsCanonicalAndLazy(t *testing.T) {
	ctx := context.Background()
	key := domain.MustUniqueKey(coresb.SmartBlockTypePinkhaTorahOperations, "v1")
	c := &objectCache{space: derivationSpace{id: "space-a"}, personalSpaceId: "space-a"}
	payload, err := c.DeriveTreePayload(ctx, payloadcreator.PayloadDerivationParams{Key: key})
	require.NoError(t, err)
	root, err := torahopscontract.Root("space-a")
	require.NoError(t, err)
	require.Equal(t, root, payload.RootRawChange)
	require.Equal(t, []string{root.Id}, payload.Heads)
	require.Empty(t, payload.Changes)
	c.personalSpaceId = "another-personal-space"
	again, err := c.DeriveTreePayload(ctx, payloadcreator.PayloadDerivationParams{Key: key})
	require.NoError(t, err)
	require.Equal(t, payload, again, "shared/personal status must not fork the namespace")
	for _, params := range []payloadcreator.PayloadDerivationParams{
		{Key: key, ParentId: "page"}, {Key: key, UseAccountSignature: true},
		{Key: domain.MustUniqueKey(coresb.SmartBlockTypePinkhaTorahOperations, "v2")},
	} {
		_, err = c.DeriveTreePayload(ctx, params)
		require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
	}
	_, err = c.CreateTreePayload(ctx, payloadcreator.PayloadCreationParams{SmartblockType: coresb.SmartBlockTypePinkhaTorahOperations})
	require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	_, err = createChangePayload(coresb.SmartBlockTypePinkhaTorahOperations, key)
	require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
}

func TestPinkhaPrivateCreationRefusesForeignOrPopulatedPayload(t *testing.T) {
	c := &objectCache{space: derivationSpace{id: "space-a"}}
	root, err := torahopscontract.Root("space-a")
	require.NoError(t, err)
	foreign, err := torahopscontract.Root("space-b")
	require.NoError(t, err)
	for _, payload := range []treestorage.TreeStorageCreatePayload{
		{RootRawChange: foreign, Heads: []string{foreign.Id}},
		{RootRawChange: root, Heads: []string{"unexpected-head"}},
		{RootRawChange: root, Heads: []string{root.Id}, Changes: []*treechangeproto.RawTreeChangeWithId{{Id: "unexpected-history"}}},
	} {
		_, err = c.CreateTreeObjectWithPayload(context.Background(), payload, nil)
		require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
	}
}
