package readguard

import (
	"context"
	"errors"
	"testing"

	"github.com/anyproto/any-sync-sdk/internal/readlifetime"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/list/listtest"
	"github.com/stretchr/testify/require"
)

func TestRuntimeObservationBindsActualReaderAndGuestHead(t *testing.T) {
	for _, permission := range []list.AclPermissions{list.AclPermissionsReader, list.AclPermissionsGuest} {
		fixture := newSignedFixture(t, permission)
		fixture.local.RLock()
		want := Observation{ACLID: fixture.local.Id(), HeadID: fixture.local.Head().Id,
			Identity: fixture.local.AclState().Identity().Account(), ACLIsEmpty: fixture.local.AclState().IsEmpty()}
		fixture.local.RUnlock()
		got, err := ObserveValue(context.Background(), fixture.load, func(observation Observation) (Observation, error) {
			// The materializer can acquire the write lock: no original ACL or
			// lifetime lock extends over its work.
			fixture.local.Lock()
			fixture.local.Unlock()
			return observation, nil
		})
		require.NoError(t, err)
		require.Equal(t, want, got)
		require.Equal(t, fixture.memberKeys.SignKey.GetPublic().Account(), got.Identity)
	}
}

func TestRuntimeObservationWithholdsAfterCurrentAuthorityChanges(t *testing.T) {
	for _, change := range []struct {
		name  string
		apply func(*signedFixture) error
	}{
		{"signed-removal", func(f *signedFixture) error { return f.revoke() }},
		{"signed-head", func(f *signedFixture) error { return f.advanceUnrelatedInvite() }},
		{"account-retirement", func(f *signedFixture) error { f.accountLifetime.Retire(); return nil }},
		{"space-retirement", func(f *signedFixture) error { f.spaceLifetime.Retire(); return nil }},
	} {
		t.Run(change.name, func(t *testing.T) {
			fixture := newSignedFixture(t, list.AclPermissionsReader)
			privateErr := errors.New("private materializer diagnostic")
			got, err := ObserveValue(context.Background(), fixture.load, func(observation Observation) (Observation, error) {
				require.NoError(t, change.apply(fixture))
				return observation, privateErr
			})
			require.ErrorIs(t, err, list.ErrInsufficientPermissions)
			require.NotErrorIs(t, err, privateErr)
			require.Zero(t, got)
		})
	}
	fixture := newSignedFixture(t, list.AclPermissionsReader)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	got, err := ObserveValue(ctx, fixture.load, func(observation Observation) (Observation, error) {
		cancel()
		return observation, nil
	})
	require.ErrorIs(t, err, context.Canceled)
	require.Zero(t, got)
}

func TestRuntimeObservationUsesOriginalACLIsEmptyIncludingInvites(t *testing.T) {
	keys, err := accountdata.NewRandom()
	require.NoError(t, err)
	acl, err := list.NewInMemoryDerivedAcl("new-runtime-invite-observation", keys)
	require.NoError(t, err)
	var accountToken, spaceToken readlifetime.Token
	load := func(context.Context) (Scope, error) {
		return Scope{ACL: acl, Account: &accountToken, Space: &spaceToken}, nil
	}
	read := func(observation Observation) (Observation, error) { return observation, nil }
	before, err := ObserveValue(context.Background(), load, read)
	require.NoError(t, err)
	require.True(t, before.ACLIsEmpty)
	acl.Lock()
	invite, err := acl.RecordBuilder().BuildInvite()
	if err == nil {
		err = acl.AddRawRecord(listtest.WrapAclRecord(invite.InviteRec))
	}
	acl.Unlock()
	require.NoError(t, err)
	after, err := ObserveValue(context.Background(), load, read)
	require.NoError(t, err)
	require.False(t, after.ACLIsEmpty, "an invite changes original IsEmpty even before another active member exists")
	require.Equal(t, before.Identity, after.Identity)
	require.Equal(t, before.ACLID, after.ACLID)
	require.NotEqual(t, before.HeadID, after.HeadID)
}
