package torahopscontract

import (
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/stretchr/testify/require"
)

func TestPrivateRootIdentityAndSpaceBinding(t *testing.T) {
	root, err := Root("space-a")
	require.NoError(t, err)
	legacy, err := objecttree.DeriveObjectTreeRoot(objecttree.ObjectTreeDerivePayload{
		SpaceId: "space-a", ChangeType: "pinkha.torah.operations.v1",
		ChangePayload: []byte("store-change/immutable-claims-v1"), IsEncrypted: true,
	}, nil)
	require.NoError(t, err)
	require.Equal(t, legacy, root, "registration must not change the previously tested root identity")
	require.NoError(t, ValidateRoot("space-a", root))
	require.ErrorIs(t, ValidateRoot("space-b", root), ErrPrivateRoot)
	require.ErrorIs(t, ValidateRoot("", root), ErrPrivateRoot)
	require.ErrorIs(t, ValidateRoot("space-a", nil), ErrPrivateRoot)
	for _, invalid := range []string{"", "space\x00a", string([]byte{0xff})} {
		_, err = Root(invalid)
		require.ErrorIs(t, err, ErrPrivateRoot)
	}
	tampered := &treechangeproto.RawTreeChangeWithId{Id: root.Id, RawChange: append([]byte(nil), root.RawChange...)}
	tampered.RawChange[len(tampered.RawChange)-1] ^= 1
	require.ErrorIs(t, ValidateRoot("space-a", tampered), ErrPrivateRoot)
}

func TestPrivateRootRejectsNoncanonicalEnvelope(t *testing.T) {
	for _, tc := range []struct {
		name   string
		change func(*treechangeproto.RootChange)
	}{
		{"missing-space", func(r *treechangeproto.RootChange) { r.SpaceId = "" }},
		{"foreign-type", func(r *treechangeproto.RootChange) { r.ChangeType = "anytype.object" }},
		{"future-type", func(r *treechangeproto.RootChange) { r.ChangeType = "pinkha.torah.operations.v2" }},
		{"payload", func(r *treechangeproto.RootChange) { r.ChangePayload = []byte("other") }},
		{"parent", func(r *treechangeproto.RootChange) { r.ParentId = "user-page" }},
		{"seed", func(r *treechangeproto.RootChange) { r.Seed = []byte("random") }},
		{"signed-root-variant", func(r *treechangeproto.RootChange) { r.IsDerived = false }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			raw, err := Root("space-a")
			require.NoError(t, err)
			root, err := objecttree.UnmarshallRoot(raw)
			require.NoError(t, err)
			require.NoError(t, ValidateRootChange(root))
			tc.change(root)
			require.ErrorIs(t, ValidateRootChange(root), ErrPrivateRoot)
		})
	}
}
