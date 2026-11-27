package anystorage_test

import (
	"bytes"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/util/cidutil"
	"github.com/anyproto/any-sync/util/crypto"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	contract "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage"
	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
	"github.com/anyproto/anytype-heart/space/spacedomain"
	"github.com/stretchr/testify/require"
)

// The original builder/decoder and type provider are real. This control proves
// header identity admission only; it does not claim an account session or a
// full native/index snapshot from synthetic Head rows.
func TestPinkhaNativeRootPreservesSignedAndUnsignedDerivedIdentity(t *testing.T) {
	key, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	payload, err := (&model.ObjectChangePayload{SmartBlockType: model.SmartBlockType_Page}).Marshal()
	require.NoError(t, err)
	builder := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), nil)
	_, signed, err := builder.BuildRoot(objecttree.InitialContent{SpaceId: "scope-a", AclHeadId: "original-acl", PrivKey: key,
		ChangeType: spacedomain.ChangeType, ChangePayload: payload, Seed: []byte("fixed header fixture"), Timestamp: 17})
	require.NoError(t, err)
	_, derived, err := builder.BuildDerivedRoot(objecttree.InitialDerivedContent{SpaceId: "scope-a", ChangeType: spacedomain.ChangeType,
		ChangePayload: payload, ParentId: signed.Id})
	require.NoError(t, err)
	private, err := torahopscontract.Root("scope-a")
	require.NoError(t, err)
	for _, raw := range []*treechangeproto.RawTreeChangeWithId{signed, derived, private} {
		root, e := objecttree.UnmarshallRoot(raw)
		require.NoError(t, e)
		head := contract.Head{ID: raw.Id, Heads: []string{raw.Id}, IsDerived: root.IsDerived, ParentID: root.ParentId}
		got, e := anystorage.PinkhaNativeRoot("scope-a", head, raw, typeprovider.GetTypeAndKeyFromRootForSpace)
		require.NoError(t, e)
		require.True(t, got.HeaderVerified)
		require.Len(t, got.HeaderSHA256, 64)
		if raw == private {
			require.Equal(t, uint64(coresb.SmartBlockTypePinkhaTorahOperations), got.NativeType)
		} else {
			require.Equal(t, uint64(coresb.SmartBlockTypePage), got.NativeType)
		}
		wrong, e := anystorage.PinkhaNativeRoot("scope-b", head, raw, typeprovider.GetTypeAndKeyFromRootForSpace)
		require.Error(t, e)
		require.False(t, wrong.HeaderVerified)
		head.IsDerived = !head.IsDerived
		wrong, e = anystorage.PinkhaNativeRoot("scope-a", head, raw, typeprovider.GetTypeAndKeyFromRootForSpace)
		require.ErrorIs(t, e, contract.ErrInvalidWitness)
		require.False(t, wrong.HeaderVerified)
	}
}

func TestPinkhaNativeRootRefusesRehashedForgeryAndNoncanonicalDerivedWrapper(t *testing.T) {
	key, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	payload, err := (&model.ObjectChangePayload{SmartBlockType: model.SmartBlockType_Page}).Marshal()
	require.NoError(t, err)
	builder := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), nil)
	_, signed, err := builder.BuildRoot(objecttree.InitialContent{SpaceId: "scope-a", AclHeadId: "original-acl", PrivKey: key,
		ChangeType: spacedomain.ChangeType, ChangePayload: payload, Seed: []byte("tamper fixture"), Timestamp: 17})
	require.NoError(t, err)
	_, derived, err := builder.BuildDerivedRoot(objecttree.InitialDerivedContent{SpaceId: "scope-a", ChangeType: spacedomain.ChangeType,
		ChangePayload: payload, ParentId: signed.Id})
	require.NoError(t, err)
	for _, raw := range []*treechangeproto.RawTreeChangeWithId{signed, derived} {
		var wrapper treechangeproto.RawTreeChange
		require.NoError(t, wrapper.UnmarshalVT(raw.RawChange))
		wrapper.Signature = bytes.Repeat([]byte{0x41}, 64)
		forgedBytes, e := wrapper.MarshalVT()
		require.NoError(t, e)
		forgedID, e := cidutil.NewCidFromBytes(forgedBytes)
		require.NoError(t, e)
		forged := &treechangeproto.RawTreeChangeWithId{Id: forgedID, RawChange: forgedBytes}
		root, e := objecttree.UnmarshallRoot(forged)
		require.NoError(t, e)
		// The original decoder deliberately does not verify a derived-root
		// author signature. Canonical bytes must reject its added wrapper data.
		if root.IsDerived {
			_, e = objecttree.NewChangeBuilder(crypto.NewKeyStorage(), forged).Unmarshall(forged, true)
			require.NoError(t, e)
		}
		head := contract.Head{ID: forgedID, Heads: []string{forgedID}, IsDerived: root.IsDerived, ParentID: root.ParentId}
		got, e := anystorage.PinkhaNativeRoot("scope-a", head, forged, typeprovider.GetTypeAndKeyFromRootForSpace)
		require.Error(t, e)
		require.False(t, got.HeaderVerified)
	}
}
