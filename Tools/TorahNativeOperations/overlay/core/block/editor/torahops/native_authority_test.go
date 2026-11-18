package torahops

import (
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/stretchr/testify/require"
)

func TestNativeAccountBoundaryACLUsesCurrentSignedMembership(t *testing.T) {
	f, _ := nativeFixtureWithPopulatedProjection(t)
	require.NoError(t, AuthorizeCurrentACL(f.acl, f.host.key, true))
	require.ErrorIs(t, AuthorizeCurrentACL(nil, f.host.key, false), list.ErrInsufficientPermissions)
	require.ErrorIs(t, AuthorizeCurrentACL(f.acl, nil, false), list.ErrInsufficientPermissions)
	member, err := accountdata.NewRandom()
	require.NoError(t, err)
	require.ErrorIs(t, AuthorizeCurrentACL(f.acl, member.SignKey, false), list.ErrInsufficientPermissions)
	applyNativeACLRecord(t, f.acl, func() (*consensusproto.RawRecord, error) {
		return f.acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{
			{Identity: member.SignKey.GetPublic(), Permissions: list.AclPermissionsReader, Metadata: []byte("disposable boundary reader")},
		}})
	})
	require.NoError(t, AuthorizeCurrentACL(f.acl, member.SignKey, false))
	require.ErrorIs(t, AuthorizeCurrentACL(f.acl, member.SignKey, true), list.ErrInsufficientPermissions)
	removeNativeMember(t, f, member.SignKey)
	require.ErrorIs(t, AuthorizeCurrentACL(f.acl, member.SignKey, false), list.ErrInsufficientPermissions)
	require.ErrorIs(t, AuthorizeCurrentACL(f.acl, member.SignKey, true), list.ErrInsufficientPermissions)
}
