package torahops

import (
	"context"
	"fmt"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/cidutil"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/stretchr/testify/require"
)

// These are real signed ACL records, applied by the actual native ACL validator
// and persisted in the disposable native space. No account-state map or mock
// permission object is patched. There is no claim of coordinator/ACL transport.
func applyNativeACLRecord(t *testing.T, acl list.AclList, build func() (*consensusproto.RawRecord, error)) {
	t.Helper()
	acl.Lock()
	defer acl.Unlock()
	record, err := build()
	require.NoError(t, err)
	data, err := record.MarshalVT()
	require.NoError(t, err)
	id, err := cidutil.NewCidFromBytes(data)
	require.NoError(t, err)
	require.NoError(t, acl.AddRawRecord(&consensusproto.RawRecordWithId{Id: id, Payload: data}))
}

func nativeFixtureWithPopulatedProjection(t *testing.T) (*nativeFixture, Operation) {
	t.Helper()
	config, _, author := makeNativeConfigs(t)
	f, err := openNativeFixture(context.Background(), config)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, f.Close()) })
	op := Operation{Version: Version, SpaceID: f.space.Id(), OperationID: fmt.Sprintf("%032x", 1),
		AuthorID: author, Kind: Add, Target: Target{ObjectID: config.TargetRoots[0].Id},
		Source: Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte("existing protected projection")}
	_, err = f.host.Append(context.Background(), op)
	require.NoError(t, err)
	result, err := f.host.ReadTarget(context.Background(), op.Target, 10)
	require.NoError(t, err)
	require.Len(t, result.Projection.Live, 1)
	return f, op
}

func TestNativeCurrentReadAuthority(t *testing.T) {
	t.Run("foreign key cannot open or read populated projection", func(t *testing.T) {
		f, op := nativeFixtureWithPopulatedProjection(t)
		outsider, err := accountdata.NewRandom()
		require.NoError(t, err)
		host, err := OpenNativeHost(context.Background(), f.projectionDB, f.space.Id(), f.tree, outsider.SignKey, f.validateTarget)
		require.ErrorIs(t, err, list.ErrInsufficientPermissions)
		require.Nil(t, host)

		// Defense at read entry also rejects a stale/misbound internal host,
		// even though its tree and projection already contain decrypted data.
		misbound := *f.host
		misbound.key = outsider.SignKey
		snapshot, err := misbound.ReadTarget(context.Background(), op.Target, 10)
		require.ErrorIs(t, err, list.ErrInsufficientPermissions)
		require.Equal(t, NativeSnapshot{}, snapshot)
		ownerSnapshot, err := f.host.ReadTarget(context.Background(), op.Target, 10)
		require.NoError(t, err)
		require.Len(t, ownerSnapshot.Projection.Live, 1)
	})

	for _, role := range []struct {
		name        string
		permissions list.AclPermissions
	}{
		{"reader", list.AclPermissionsReader},
		{"guest", list.AclPermissionsGuest},
	} {
		t.Run(role.name+" reads until locally verified removal", func(t *testing.T) {
			f, op := nativeFixtureWithPopulatedProjection(t)
			member, err := accountdata.NewRandom()
			require.NoError(t, err)
			applyNativeACLRecord(t, f.acl, func() (*consensusproto.RawRecord, error) {
				return f.acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{
					{Identity: member.SignKey.GetPublic(), Permissions: role.permissions, Metadata: []byte("disposable read member")},
				}})
			})
			memberHost, err := OpenNativeHost(context.Background(), f.projectionDB, f.space.Id(), f.tree, member.SignKey, f.validateTarget)
			require.NoError(t, err)
			snapshot, err := memberHost.ReadTarget(context.Background(), op.Target, 10)
			require.NoError(t, err)
			require.Len(t, snapshot.Projection.Live, 1)
			write := op
			write.OperationID = fmt.Sprintf("%032x", 2)
			write.AuthorID = member.SignKey.GetPublic().Account()
			_, err = memberHost.Append(context.Background(), write)
			require.ErrorIs(t, err, list.ErrInsufficientPermissions)

			metadata, _, err := crypto.GenerateRandomEd25519KeyPair()
			require.NoError(t, err)
			applyNativeACLRecord(t, f.acl, func() (*consensusproto.RawRecord, error) {
				return f.acl.RecordBuilder().BuildAccountRemove(list.AccountRemovePayload{
					Identities: []crypto.PubKey{member.SignKey.GetPublic()},
					Change:     list.ReadKeyChangePayload{MetadataKey: metadata, ReadKey: crypto.NewAES()},
				})
			})
			f.acl.RLock()
			current := f.acl.AclState().Permissions(member.SignKey.GetPublic())
			hadRead := f.acl.AclState().HadReadPermissions(member.SignKey.GetPublic())
			f.acl.RUnlock()
			require.Equal(t, list.AclPermissionsNone, current)
			require.True(t, hadRead, "historical read authority must not authorize a current read")

			// The projection still exists and the native tree retains its signed
			// history; current known revocation must block both access paths.
			snapshot, err = memberHost.ReadTarget(context.Background(), op.Target, 10)
			require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			require.Equal(t, NativeSnapshot{}, snapshot)
			reopened, err := OpenNativeHost(context.Background(), f.projectionDB, f.space.Id(), f.tree, member.SignKey, f.validateTarget)
			require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			require.Nil(t, reopened)
			ownerSnapshot, err := f.host.ReadTarget(context.Background(), op.Target, 10)
			require.NoError(t, err)
			require.Len(t, ownerSnapshot.Projection.Live, 1)
		})
	}
}
