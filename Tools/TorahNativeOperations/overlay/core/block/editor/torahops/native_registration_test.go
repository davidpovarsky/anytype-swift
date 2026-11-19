package torahops

import (
	"context"
	"path/filepath"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
)

func TestNativeLockedConstructorRecoversWhileCallerOwnsTree(t *testing.T) {
	config, _, author := makeNativeConfigs(t)
	f, err := openNativeFixture(context.Background(), config)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, f.Close()) })
	op := Operation{Version: Version, SpaceID: f.space.Id(), OperationID: "000000000000000000000000000000a1", AuthorID: author, Kind: Add,
		Target: Target{ObjectID: config.TargetRoots[0].Id}, Source: Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte("locked constructor replay")}
	_, err = f.host.Append(context.Background(), op)
	require.NoError(t, err)
	fresh, err := anystore.Open(context.Background(), filepath.Join(t.TempDir(), "projection.db"), &anystore.Config{ReadConnections: 1})
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, fresh.Close()) })
	f.tree.Lock()
	reopened, err := OpenNativeHostLocked(context.Background(), fresh, f.space.Id(), f.tree, f.keys.SignKey, f.acquireTarget)
	f.tree.Unlock()
	require.NoError(t, err)
	result, err := reopened.ReadTarget(context.Background(), op.Target, 100)
	require.NoError(t, err)
	require.Len(t, result.Projection.Live, 1)
	require.Equal(t, op.Payload, result.Projection.Live[0].Operation.Payload)
}

func TestNativeReceivingValidatorPreservesSignedHistory(t *testing.T) {
	ctx := context.Background()
	config, _, author := makeNativeConfigs(t)
	f, err := openNativeFixture(ctx, config)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, f.Close()) })
	op := Operation{Version: Version, SpaceID: f.space.Id(), OperationID: "000000000000000000000000000000a2", AuthorID: author, Kind: Add,
		Target: Target{ObjectID: config.TargetRoots[0].Id}, Source: Source{ProviderID: "fixture", CanonicalRef: "fixture:2"}, Payload: []byte("signed native validator fixture")}
	result, err := f.host.Append(ctx, op)
	require.NoError(t, err)
	raw, err := f.tree.Storage().Get(ctx, result.ChangeID)
	require.NoError(t, err)
	for _, test := range []string{"valid", "foreign Space", "wrong heads", "corrupt CID"} {
		t.Run(test, func(t *testing.T) {
			db, err := anystore.Open(ctx, filepath.Join(t.TempDir(), "native.db"), &anystore.Config{ReadConnections: 1})
			require.NoError(t, err)
			defer func() { require.NoError(t, db.Close()) }()
			receiver, err := spacestorage.Create(ctx, db, config.Space)
			require.NoError(t, err)
			change := raw.RawTreeChangeWithId()
			payload := treestorage.TreeStorageCreatePayload{RootRawChange: f.tree.Header(), Heads: []string{result.ChangeID}, Changes: []*treechangeproto.RawTreeChangeWithId{change}}
			spaceID := f.space.Id()
			switch test {
			case "foreign Space":
				spaceID += "-foreign"
			case "wrong heads":
				payload.Heads = []string{result.ChangeID, "missing-native-head"}
			case "corrupt CID":
				payload.Changes = []*treechangeproto.RawTreeChangeWithId{{Id: change.Id, RawChange: append(append([]byte{}, change.RawChange...), 0)}}
			}
			tree, err := NativeTreeValidator(spaceID)(payload, receiver, f.acl)
			if test == "valid" {
				require.NoError(t, err)
				require.Equal(t, 2, tree.Len())
				require.Equal(t, payload.Heads, tree.Heads())
				require.NoError(t, tree.Close())
			} else {
				require.Error(t, err)
				if test == "foreign Space" {
					require.ErrorIs(t, err, torahopscontract.ErrPrivateRoot)
				}
				if test == "corrupt CID" {
					require.ErrorIs(t, err, objecttree.ErrIncorrectCid)
				}
			}
		})
	}
}
