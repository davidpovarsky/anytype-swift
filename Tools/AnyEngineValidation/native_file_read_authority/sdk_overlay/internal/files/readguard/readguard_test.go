package readguard

import (
	"bytes"
	"context"
	"errors"
	"io"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/internal/readlifetime"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/list/listtest"
	"github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/stretchr/testify/require"
)

// These fixtures apply actual signed ACL records through the unmodified full
// verifier. They do not substitute a role boolean for native ACL state.
type signedFixture struct {
	owner           list.AclList
	local           list.AclList
	memberKeys      *accountdata.AccountKeys
	permission      list.AclPermissions
	accountLifetime readlifetime.Token
	spaceLifetime   readlifetime.Token
}

func newSignedFixture(t *testing.T, permission list.AclPermissions) *signedFixture {
	t.Helper()
	ownerKeys, err := accountdata.NewRandom()
	require.NoError(t, err)
	memberKeys, err := accountdata.NewRandom()
	require.NoError(t, err)
	owner, err := list.NewInMemoryDerivedAcl("file-read-authority-space", ownerKeys)
	require.NoError(t, err)
	f := &signedFixture{owner: owner, memberKeys: memberKeys, permission: permission}
	grant, err := owner.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{{
		Identity: memberKeys.SignKey.GetPublic(), Permissions: permission, Metadata: []byte("file reader fixture"),
	}}})
	require.NoError(t, err)
	raw := listtest.WrapAclRecord(grant)
	require.NoError(t, owner.AddRawRecord(raw))
	storage, err := list.NewInMemoryStorage(owner.Id(), []*consensusproto.RawRecordWithId{owner.Root(), raw})
	require.NoError(t, err)
	f.local, err = list.BuildAclListWithIdentity(memberKeys, storage, recordverifier.NewValidateFull())
	require.NoError(t, err)
	require.Equal(t, permission, f.local.AclState().Permissions(f.local.AclState().Identity()))
	require.True(t, f.local.AclState().Identity().Equals(memberKeys.SignKey.GetPublic()))
	return f
}

func (f *signedFixture) load(context.Context) (Scope, error) {
	return Scope{ACL: f.local, Account: &f.accountLifetime, Space: &f.spaceLifetime}, nil
}

func (f *signedFixture) revoke() error {
	metadataKey, _, err := crypto.GenerateRandomEd25519KeyPair()
	if err != nil {
		return err
	}
	f.owner.Lock()
	raw, err := f.owner.RecordBuilder().BuildAccountRemove(list.AccountRemovePayload{
		Identities: []crypto.PubKey{f.memberKeys.SignKey.GetPublic()},
		Change:     list.ReadKeyChangePayload{MetadataKey: metadataKey, ReadKey: crypto.NewAES()},
	})
	if err != nil {
		f.owner.Unlock()
		return err
	}
	record := listtest.WrapAclRecord(raw)
	err = f.owner.AddRawRecord(record)
	f.owner.Unlock()
	if err != nil {
		return err
	}
	f.local.Lock()
	defer f.local.Unlock()
	return f.local.AddRawRecord(record)
}

func (f *signedFixture) restore() error {
	f.owner.Lock()
	raw, err := f.owner.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{{
		Identity: f.memberKeys.SignKey.GetPublic(), Permissions: f.permission, Metadata: []byte("explicit fixture restoration"),
	}}})
	if err != nil {
		f.owner.Unlock()
		return err
	}
	record := listtest.WrapAclRecord(raw)
	err = f.owner.AddRawRecord(record)
	f.owner.Unlock()
	if err != nil {
		return err
	}
	f.local.Lock()
	defer f.local.Unlock()
	return f.local.AddRawRecord(record)
}

func (f *signedFixture) advanceUnrelatedInvite() error {
	f.owner.Lock()
	invite, err := f.owner.RecordBuilder().BuildInvite()
	if err != nil {
		f.owner.Unlock()
		return err
	}
	record := listtest.WrapAclRecord(invite.InviteRec)
	err = f.owner.AddRawRecord(record)
	f.owner.Unlock()
	if err != nil {
		return err
	}
	f.local.Lock()
	defer f.local.Unlock()
	return f.local.AddRawRecord(record)
}

type trackedReader struct {
	*bytes.Reader
	readFn     func([]byte) (int, error)
	seekFn     func(int64, int) (int64, error)
	reads      atomic.Int32
	seeks      atomic.Int32
	closes     atomic.Int32
	maxRequest atomic.Int64
}

func (r *trackedReader) Read(p []byte) (int, error) {
	r.reads.Add(1)
	for old := r.maxRequest.Load(); int64(len(p)) > old; old = r.maxRequest.Load() {
		if r.maxRequest.CompareAndSwap(old, int64(len(p))) {
			break
		}
	}
	if r.readFn != nil {
		return r.readFn(p)
	}
	return r.Reader.Read(p)
}

func (r *trackedReader) Seek(offset int64, whence int) (int64, error) {
	r.seeks.Add(1)
	if r.seekFn != nil {
		return r.seekFn(offset, whence)
	}
	return r.Reader.Seek(offset, whence)
}

func (r *trackedReader) Close() error { r.closes.Add(1); return nil }

func openFixture(t *testing.T, ctx context.Context, f *signedFixture, source *trackedReader) Reader {
	t.Helper()
	r, err := Open(ctx, f.load, func() (Reader, error) { return source, nil })
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, r.Close()) })
	return r
}

func TestReadGuardPreservesCurrentSignedReaderAndGuest(t *testing.T) {
	for _, role := range []struct {
		name       string
		permission list.AclPermissions
	}{{"reader", list.AclPermissionsReader}, {"guest", list.AclPermissionsGuest}} {
		t.Run(role.name, func(t *testing.T) {
			f := newSignedFixture(t, role.permission)
			source := &trackedReader{Reader: bytes.NewReader([]byte("exact allowed plaintext"))}
			r := openFixture(t, context.Background(), f, source)
			got, err := io.ReadAll(r)
			require.NoError(t, err)
			require.Equal(t, "exact allowed plaintext", string(got))
			require.Equal(t, int64(len(got)), r.Size())
		})
	}
}

func TestReadGuardUsesLoadedGuestIdentityAfterItsSignedRemoval(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsGuest)
	source := &trackedReader{Reader: bytes.NewReader([]byte("guest-visible cached plaintext"))}
	r := openFixture(t, context.Background(), f, source)
	require.NoError(t, f.revoke())
	// The owner's account remains authorized; the loaded Guest key does not.
	require.True(t, f.owner.AclState().Permissions(f.owner.AclState().Identity()).IsOwner())
	n, err := r.Read(make([]byte, 16))
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, n)
	require.Zero(t, source.reads.Load())
}

func TestReadGuardRefusesRevokedOpenBeforeContentLookup(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	require.NoError(t, f.revoke())
	called := false
	r, err := Open(context.Background(), f.load, func() (Reader, error) { called = true; return nil, nil })
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Nil(t, r)
	require.False(t, called)
}

func TestReadGuardHeldCachedReaderStopsAfterCurrentSignedRemoval(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	source := &trackedReader{Reader: bytes.NewReader([]byte("previously cached secret"))}
	r := openFixture(t, context.Background(), f, source)
	first := make([]byte, 3)
	n, err := r.Read(first)
	require.NoError(t, err)
	require.Equal(t, "pre", string(first[:n]))
	require.NoError(t, f.revoke())
	buffer := bytes.Repeat([]byte{0xa5}, 32)
	n, err = r.Read(buffer)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, n)
	require.Equal(t, bytes.Repeat([]byte{0xa5}, 32), buffer)
	require.Equal(t, int32(1), source.reads.Load(), "revoked read must not touch cached plaintext")
}

func TestReadGuardRechecksSignedAuthorityAfterAwaitedFetch(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	entered, release := make(chan struct{}), make(chan struct{})
	source := &trackedReader{Reader: bytes.NewReader(nil), readFn: func(p []byte) (int, error) {
		close(entered)
		<-release
		return copy(p, "downloaded private plaintext"), nil
	}}
	r := openFixture(t, context.Background(), f, source)
	buffer := bytes.Repeat([]byte{0xa5}, 64)
	type outcome struct {
		n   int
		err error
	}
	done := make(chan outcome, 1)
	go func() { n, err := r.Read(buffer); done <- outcome{n, err} }()
	select {
	case <-entered:
	case <-time.After(time.Second):
		t.Fatal("fetch was not entered")
	}
	revoked := make(chan error, 1)
	go func() { revoked <- f.revoke() }()
	var revokeErr error
	select {
	case revokeErr = <-revoked:
	case <-time.After(time.Second):
		close(release)
		t.Fatal("file I/O held the ACL lock and blocked signed removal")
	}
	require.NoError(t, revokeErr)
	close(release)
	select {
	case got := <-done:
		require.ErrorIs(t, got.err, list.ErrInsufficientPermissions)
		require.Zero(t, got.n)
	case <-time.After(time.Second):
		t.Fatal("guarded fetch did not finish")
	}
	require.Equal(t, bytes.Repeat([]byte{0xa5}, 64), buffer)
}

func TestReadGuardClosesOpenedReaderWhenAuthorityChangedDuringOpen(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	source := &trackedReader{Reader: bytes.NewReader([]byte("never released"))}
	r, err := Open(context.Background(), f.load, func() (Reader, error) {
		require.NoError(t, f.revoke())
		return source, nil
	})
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Nil(t, r)
	require.Equal(t, int32(1), source.closes.Load())
	require.Zero(t, source.reads.Load())
}

func TestReadGuardSeekThenReadRechecksCurrentSignedPermission(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	source := &trackedReader{Reader: bytes.NewReader([]byte("range secret"))}
	r := openFixture(t, context.Background(), f, source)
	position, err := r.Seek(6, io.SeekStart)
	require.NoError(t, err)
	require.Equal(t, int64(6), position)
	require.NoError(t, f.revoke())
	n, err := r.Read(make([]byte, 6))
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, n)
	_, err = r.Seek(0, io.SeekStart)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Equal(t, int32(1), source.seeks.Load())
	require.Zero(t, source.reads.Load())
}

func TestReadGuardRechecksAfterAnAwaitedSeek(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	source := &trackedReader{Reader: bytes.NewReader([]byte("range secret")), seekFn: func(int64, int) (int64, error) {
		require.NoError(t, f.revoke())
		return 6, nil
	}}
	r := openFixture(t, context.Background(), f, source)
	position, err := r.Seek(6, io.SeekStart)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, position)
	require.Zero(t, source.reads.Load())
}

func TestReadGuardLateContextCancellationDiscardsFetchedPlaintext(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	source := &trackedReader{Reader: bytes.NewReader(nil), readFn: func(p []byte) (int, error) {
		cancel()
		return copy(p, "must remain private"), nil
	}}
	r := openFixture(t, ctx, f, source)
	buffer := bytes.Repeat([]byte{0xa5}, 32)
	n, err := r.Read(buffer)
	require.ErrorIs(t, err, context.Canceled)
	require.Zero(t, n)
	require.Equal(t, bytes.Repeat([]byte{0xa5}, 32), buffer)
}

func TestReadGuardCannotReadWithRetiredAuthorityLoader(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	retired := errors.New("captured account space cache closed")
	var loadErr error
	loads := 0
	load := func(ctx context.Context) (Scope, error) { loads++; scope, _ := f.load(ctx); return scope, loadErr }
	source := &trackedReader{Reader: bytes.NewReader([]byte("retired account plaintext"))}
	r, err := Open(context.Background(), load, func() (Reader, error) { return source, nil })
	require.NoError(t, err)
	defer r.Close()
	require.Equal(t, 2, loads)
	loadErr = retired
	n, err := r.Read(make([]byte, 16))
	require.ErrorIs(t, err, retired)
	require.Zero(t, n)
	require.Equal(t, 3, loads)
	require.Zero(t, source.reads.Load())
}

func TestReadGuardPreservesByteRangesEOFAndBoundedPrivateMemory(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	data := bytes.Repeat([]byte("native-file-range-contract"), 65537)
	source := &trackedReader{Reader: bytes.NewReader(data)}
	r := openFixture(t, context.Background(), f, source)
	largeCallerBuffer := make([]byte, 3*maxReadChunk)
	n, err := r.Read(largeCallerBuffer)
	require.NoError(t, err)
	require.Equal(t, maxReadChunk, n)
	require.Equal(t, data[:n], largeCallerBuffer[:n])
	position, err := r.Seek(12345, io.SeekStart)
	require.NoError(t, err)
	require.Equal(t, int64(12345), position)
	got, err := io.ReadAll(r)
	require.NoError(t, err)
	require.Equal(t, data[12345:], got)
	require.LessOrEqual(t, source.maxRequest.Load(), int64(maxReadChunk))
	n, err = r.Read(largeCallerBuffer)
	require.Zero(t, n)
	require.ErrorIs(t, err, io.EOF)
}

func TestReadGuardCloseDoesNotWaitForFetchOrReleasePendingBytes(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	entered, release := make(chan struct{}), make(chan struct{})
	source := &trackedReader{Reader: bytes.NewReader(nil), readFn: func(p []byte) (int, error) {
		close(entered)
		<-release
		return copy(p, "pending plaintext"), nil
	}}
	r := openFixture(t, context.Background(), f, source)
	buffer := bytes.Repeat([]byte{0xa5}, 32)
	done := make(chan error, 1)
	go func() {
		n, err := r.Read(buffer)
		if n != 0 {
			done <- errors.New("closed reader released bytes")
			return
		}
		done <- err
	}()
	select {
	case <-entered:
	case <-time.After(time.Second):
		t.Fatal("fetch was not entered")
	}
	closed := make(chan error, 1)
	go func() { closed <- r.Close() }()
	select {
	case err := <-closed:
		require.NoError(t, err)
	case <-time.After(time.Second):
		close(release)
		t.Fatal("Close waited for a network fetch")
	}
	close(release)
	select {
	case err := <-done:
		require.ErrorIs(t, err, io.ErrClosedPipe)
	case <-time.After(time.Second):
		t.Fatal("fetch did not finish")
	}
	require.Equal(t, bytes.Repeat([]byte{0xa5}, 32), buffer)
	require.Equal(t, int32(1), source.closes.Load())
}

func TestReadGuardInvalidatedReaderRequiresFreshOpenAfterExplicitGrant(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	source := &trackedReader{Reader: bytes.NewReader([]byte("old held plaintext"))}
	r := openFixture(t, context.Background(), f, source)
	require.NoError(t, f.revoke())
	_, err := r.Read(make([]byte, 4))
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.NoError(t, f.restore())
	_, err = r.Read(make([]byte, 4))
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	fresh := openFixture(t, context.Background(), f, &trackedReader{Reader: bytes.NewReader([]byte("fresh allowed plaintext"))})
	got, err := io.ReadAll(fresh)
	require.NoError(t, err)
	require.Equal(t, "fresh allowed plaintext", string(got))
}

func TestReadGuardRejectsSignedRevokeRestoreABA(t *testing.T) {
	for _, boundary := range []string{"open", "read"} {
		t.Run(boundary, func(t *testing.T) {
			f := newSignedFixture(t, list.AclPermissionsReader)
			source := &trackedReader{Reader: bytes.NewReader([]byte("old generation plaintext"))}
			change := func() {
				require.NoError(t, f.revoke())
				require.NoError(t, f.restore())
				require.Equal(t, list.AclPermissionsReader, f.local.AclState().Permissions(f.local.AclState().Identity()))
			}
			if boundary == "open" {
				r, err := Open(context.Background(), f.load, func() (Reader, error) {
					change()
					return source, nil
				})
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
				require.Nil(t, r)
				require.Equal(t, int32(1), source.closes.Load())
			} else {
				source.readFn = func(p []byte) (int, error) {
					change()
					return copy(p, "old generation plaintext"), nil
				}
				r := openFixture(t, context.Background(), f, source)
				buffer := bytes.Repeat([]byte{0xa5}, 64)
				n, err := r.Read(buffer)
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
				require.Zero(t, n)
				require.Equal(t, bytes.Repeat([]byte{0xa5}, 64), buffer)
			}
			fresh := openFixture(t, context.Background(), f, &trackedReader{Reader: bytes.NewReader([]byte("fresh generation plaintext"))})
			got, err := io.ReadAll(fresh)
			require.NoError(t, err)
			require.Equal(t, "fresh generation plaintext", string(got))
		})
	}
}

func TestReadGuardSignedHeadChangeRequiresFreshOpenEvenWithSameRole(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	source := &trackedReader{Reader: bytes.NewReader([]byte("still allowed through a fresh reader"))}
	r := openFixture(t, context.Background(), f, source)
	require.NoError(t, f.advanceUnrelatedInvite())
	require.Equal(t, list.AclPermissionsReader, f.local.AclState().Permissions(f.local.AclState().Identity()))
	n, err := r.Read(make([]byte, 16))
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, n)
	require.Zero(t, source.reads.Load())
	fresh := openFixture(t, context.Background(), f, &trackedReader{Reader: bytes.NewReader([]byte("fresh current authority"))})
	got, err := io.ReadAll(fresh)
	require.NoError(t, err)
	require.Equal(t, "fresh current authority", string(got))
}

func TestReadGuardCannotSwitchSignedAccountOrSpaceDuringFetch(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	other := newSignedFixture(t, list.AclPermissionsReader)
	active := f
	source := &trackedReader{Reader: bytes.NewReader(nil), readFn: func(p []byte) (int, error) {
		active = other
		return copy(p, "original account plaintext"), nil
	}}
	r, err := Open(context.Background(), func(ctx context.Context) (Scope, error) { return active.load(ctx) }, func() (Reader, error) { return source, nil })
	require.NoError(t, err)
	defer r.Close()
	buffer := bytes.Repeat([]byte{0xa5}, 64)
	n, err := r.Read(buffer)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, n)
	require.Equal(t, bytes.Repeat([]byte{0xa5}, 64), buffer)
}
