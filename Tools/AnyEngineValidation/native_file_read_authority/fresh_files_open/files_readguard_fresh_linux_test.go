//go:build linux

package anysyncsdk

// These two integration fixtures create a new SDK, fresh in-memory account and
// network signing identities, and new encrypted CAR data. They never read an
// existing account, wallet, saved ACL record, database or Reader6 snapshot.
// Production Files.Open, the loaded SyncAcl, the production network verifier,
// the full author/content verifier, file decryption and CAR integrity all run.

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store/v2"
	"github.com/anyproto/any-sync/commonfile/fileservice"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/list/listtest"
	"github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
	"github.com/anyproto/any-sync/commonspace/object/acl/syncacl"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/ipfs/go-cid"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/any-sync-sdk/auth"
	"github.com/anyproto/any-sync-sdk/config"
	"github.com/anyproto/any-sync-sdk/internal/files/crypt"
	"github.com/anyproto/any-sync-sdk/internal/files/fetch"
	filestore "github.com/anyproto/any-sync-sdk/internal/files/store"
	"github.com/anyproto/any-sync-sdk/internal/payloads"
	"github.com/anyproto/any-sync-sdk/internal/spaceimpl"
	"github.com/anyproto/any-sync-sdk/space"
)

const freshFilesEvidenceParent = "/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127"

type freshFilesFixture struct {
	ctx          context.Context
	cancel       context.CancelFunc
	sdk          *SDK
	space        space.Space
	localACL     syncacl.SyncAcl
	ownerACL     list.AclList
	networkKey   crypto.PrivKey
	localID      string
	fileID       string
	plain        []byte
	peer         *freshFilesPeer
	metadataDBs  []anystore.DB
	baseURLCalls atomic.Int32
}

// This is a controlled in-memory transport over newly generated CAR bytes.
// The real fetcher still probes, checks CIDs, stores blocks and decrypts them.
// Only the next real post-Open range fetch is paused by the awaiting-read case.
type freshFilesPeer struct {
	spaceID    string
	root       cid.Cid
	car        []byte
	armed      atomic.Bool
	blocked    atomic.Bool
	banned     atomic.Int32
	ranges     atomic.Int32
	entered    chan struct{}
	release    chan struct{}
	releaseOne sync.Once
}

func (p *freshFilesPeer) SourceFor(_ context.Context, spaceID string, root cid.Cid) (fetch.CarSource, func(), bool) {
	if spaceID != p.spaceID || !root.Equals(p.root) {
		return nil, nil, false
	}
	return p, func() { p.banned.Add(1) }, true
}

func (p *freshFilesPeer) PeerReadBudget() (time.Duration, int64) {
	// A finite fixture coordination allowance, not a network-performance claim.
	return 10 * time.Second, 0
}

func (p *freshFilesPeer) ReadProbe(ctx context.Context) ([]byte, int64, error) {
	if err := ctx.Err(); err != nil {
		return nil, 0, err
	}
	n := min(4096, len(p.car))
	return bytes.Clone(p.car[:n]), int64(len(p.car)), nil
}

func (p *freshFilesPeer) ReadRange(ctx context.Context, offset, length int64) ([]byte, error) {
	if offset < 0 || length < 0 || offset > int64(len(p.car)) || length > int64(len(p.car))-offset {
		return nil, fmt.Errorf("fresh fixture range is outside its own CAR")
	}
	p.ranges.Add(1)
	if p.armed.Load() && p.blocked.CompareAndSwap(false, true) {
		close(p.entered)
		select {
		case <-p.release:
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	return bytes.Clone(p.car[offset : offset+length]), nil
}

func (p *freshFilesPeer) unblock() {
	p.releaseOne.Do(func() { close(p.release) })
}

func freshFilesRoot(t *testing.T) string {
	t.Helper()
	raw := os.Getenv("PINKHA_FRESH_FILES_FIXTURE_ROOT")
	require.NotEmpty(t, raw, "the reviewed qualifier must supply an exclusive fresh fixture root")
	require.Equal(t, raw, filepath.Clean(raw))
	require.True(t, filepath.IsAbs(raw))
	relative, err := filepath.Rel(freshFilesEvidenceParent, raw)
	require.NoError(t, err)
	parts := strings.Split(relative, string(filepath.Separator))
	require.Len(t, parts, 2)
	require.Regexp(t, regexp.MustCompile(`^attempt[1-9][0-9]{0,2}$`), parts[0])
	require.Equal(t, "fixtures", parts[1])
	physical, err := filepath.EvalSymlinks(raw)
	require.NoError(t, err)
	require.Equal(t, raw, physical)
	info, err := os.Lstat(raw)
	require.NoError(t, err)
	require.True(t, info.IsDir())
	require.Zero(t, info.Mode().Perm()&0077)
	root := filepath.Join(raw, t.Name())
	require.NoError(t, os.Mkdir(root, 0700), "never reuse or overwrite a prior fixture")
	// Do not register TempDir/RemoveAll cleanup. The new fixture files remain
	// alongside the actual run receipt, including on failure. Keys stay in RAM.
	return root
}

func freshFilesRequireOSIsolation(t *testing.T) {
	t.Helper()
	status, err := os.ReadFile("/proc/self/status")
	require.NoError(t, err)
	require.Contains(t, string(status), "NoNewPrivs:\t1")
	require.Contains(t, string(status), "Seccomp:\t2")
	// Verify the inherited policy in this process before SDK initialization.
	// EPERM is required; an unreachable endpoint or refused connection is not
	// evidence of OS enforcement. Neither syscall may send a fixture byte.
	address := &syscall.SockaddrInet4{Port: 9, Addr: [4]byte{127, 0, 0, 1}}
	tcp, err := syscall.Socket(syscall.AF_INET, syscall.SOCK_STREAM, 0)
	require.NoError(t, err)
	connectErr := syscall.Connect(tcp, address)
	require.NoError(t, syscall.Close(tcp))
	require.ErrorIs(t, connectErr, syscall.EPERM)
	udp, err := syscall.Socket(syscall.AF_INET, syscall.SOCK_DGRAM, 0)
	require.NoError(t, err)
	sendErr := syscall.Sendto(udp, []byte{0x51}, 0, address)
	require.NoError(t, syscall.Close(udp))
	require.ErrorIs(t, sendErr, syscall.EPERM)
}

func newFreshFilesFixture(t *testing.T, cached bool) *freshFilesFixture {
	t.Helper()
	freshFilesRequireOSIsolation(t)
	root := freshFilesRoot(t)
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	f := &freshFilesFixture{ctx: ctx, cancel: cancel}
	t.Cleanup(func() {
		cancel()
		if f.peer != nil {
			f.peer.unblock()
		}
		if f.sdk != nil {
			closed := make(chan error, 1)
			go func() { closed <- f.sdk.Close() }()
			select {
			case err := <-closed:
				require.NoError(t, err)
			case <-time.After(10 * time.Second):
				t.Fatal("fresh SDK did not close within its bounded cleanup")
			}
		}
		for _, db := range f.metadataDBs {
			require.NoError(t, db.Close())
		}
	})
	accountKey, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	deviceKey, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	// Use the production key generator's raw private-key encoding. The pinned
	// v0.13.8 decoder accepts 64/96 bytes, not a bare 32-byte Ed25519 seed.
	accountRaw, err := accountKey.Raw()
	require.NoError(t, err)
	deviceRaw, err := deviceKey.Raw()
	require.NoError(t, err)
	require.Len(t, accountRaw, 64)
	require.Len(t, deviceRaw, 64)
	provider, err := auth.NewKeyProvider(auth.KeyConfig{AccountKey: accountRaw, DeviceKey: deviceRaw})
	require.NoError(t, err)
	clear(accountRaw)
	clear(deviceRaw)
	f.networkKey, _, err = crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	otherOwner, err := accountdata.NewRandom()
	require.NoError(t, err)
	// The complete network identity is new to this fixture. Its private key is
	// never persisted or printed. The production verifier checks this key.
	configuration := fmt.Sprintf("id: fresh-files-read-authority\nnetworkId: %s\nfileNetworkId: %s\nnodes:\n- peerId: %s\n  addresses: [127.0.0.1:1]\n  types: [coordinator, tree, consensus]\ncreationTime: '2026-11-27T00:00:00Z'\n",
		f.networkKey.GetPublic().Network(), f.networkKey.GetPublic().Network(), otherOwner.PeerId)
	disabled := false
	f.sdk, err = Open(ctx, config.Config{
		Storage:  config.Storage{DataDir: filepath.Join(root, "new-sdk"), Topology: config.StorageShared},
		Network:  config.Network{NodeConfYAML: []byte(configuration)},
		Headless: true,
		P2P:      config.P2P{Enabled: &disabled, LocalDiscovery: &disabled, Global: config.GlobalP2P{Enabled: &disabled}},
	}, provider)
	require.NoError(t, err)
	require.True(t, f.sdk.app.Headless())
	require.False(t, f.sdk.app.P2PEnabled())
	require.False(t, f.sdk.app.GlobalP2PEnabled())
	f.localID = f.sdk.app.AccountKeys().SignKey.GetPublic().Account()
	require.Equal(t, accountKey.GetPublic().Account(), f.localID)

	newStore := func(name string) *filestore.Store {
		db, err := anystore.Open(ctx, filepath.Join(root, name+"-metadata.db"), nil)
		require.NoError(t, err)
		f.metadataDBs = append(f.metadataDBs, db)
		store, err := filestore.New(ctx, filepath.Join(root, name+"-cars"), db)
		require.NoError(t, err)
		return store
	}
	source := newStore("new-source")
	destination := source
	if !cached {
		destination = newStore("new-reader")
	}
	fetcher := fetch.New(destination, func(context.Context) (string, error) {
		f.baseURLCalls.Add(1)
		return "", fmt.Errorf("fresh non-durable fixture must not ask for an HTTP source")
	})
	// Test-only boot wiring, before creating any regular Space or file. The
	// new SDK has no queued file work and no periodic GC. No production hook or
	// dynamic consumer reconfiguration is introduced by this test source.
	f.sdk.spaces.SetFiles(nil, fetcher, destination, nil)
	f.space, err = f.sdk.Spaces().Create(ctx, space.CreateRequest{Name: "fresh held-file authority"})
	require.NoError(t, err)
	// Reload this new fixture space as local-only before any fixture record
	// transitions; its own initial loader was already OS-isolated.
	f.sdk.app.MarkSpaceLocalOnly(f.space.Id())
	require.NoError(t, f.sdk.app.EvictSpace(ctx, f.space.Id()))
	handle, err := f.sdk.app.GetSpace(ctx, f.space.Id())
	require.NoError(t, err)
	f.localACL = handle.Inner().Acl()
	require.True(t, f.sdk.app.IsLocalOnly(f.space.Id()))

	// Larger than the existing fetcher's 4 MiB coalescing span, so a cold
	// Open cannot incidentally cache the entire body before the await barrier.
	f.plain = make([]byte, 6*1024*1024+17)
	for index := range f.plain {
		f.plain[index] = byte((index*31 + index/4096) % 251)
	}
	key := make([]byte, 32)
	_, err = rand.Read(key)
	require.NoError(t, err)
	build, err := source.NewBuild(ctx, f.space.Id())
	require.NoError(t, err)
	encrypted, err := crypt.NewEncryptReader(key, bytes.NewReader(f.plain))
	require.NoError(t, err)
	node, err := fileservice.NewFileHandler(build.Blockstore()).AddFile(ctx, encrypted)
	require.NoError(t, err)
	carInfo, err := build.Finalize(ctx, node.Cid())
	require.NoError(t, err)
	registrar, ok := f.space.(interface{ PayloadsInternal() *spaceimpl.PayloadsAPI })
	require.True(t, ok, "actual SDK Space must provide its production payload registrar")
	f.fileID, _, err = registrar.PayloadsInternal().RegisterFile(ctx, f.space.SpaceIndexObjectId(), spaceimpl.RegisterFileOpts{
		RootCid: carInfo.Root.String(), Size: int64(len(f.plain)),
		Enc: payloads.EncPayload{Key: key, Name: "new-synthetic-reader.bin", Mime: "application/octet-stream"},
	})
	require.NoError(t, err)
	clear(key)
	if !cached {
		carHandle, err := source.Open(ctx, f.space.Id(), carInfo.Root)
		require.NoError(t, err)
		carBytes, readErr := io.ReadAll(io.NewSectionReader(carHandle, 0, carInfo.Size))
		closeErr := carHandle.Close()
		require.NoError(t, readErr)
		require.NoError(t, closeErr)
		f.peer = &freshFilesPeer{spaceID: f.space.Id(), root: carInfo.Root, car: carBytes,
			entered: make(chan struct{}), release: make(chan struct{})}
		fetcher.SetPeer(f.peer)
	}

	// Make the actual SDK's loaded identity a Reader without replacing its
	// ACL object. All three transitions belong solely to this new fixture:
	// add the new owner as Writer, signed ownership transfer (local=>Reader),
	// then the test's later signed removal. There is no state-map assignment.
	full := f.fullIdentity(t, f.sdk.app.AccountKeys())
	raw, err := full.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{{
		Identity: otherOwner.SignKey.GetPublic(), Permissions: list.AclPermissionsWriter, Metadata: []byte("new fixture owner"),
	}}})
	require.NoError(t, err)
	f.apply(t, full, raw)
	raw, err = full.RecordBuilder().BuildOwnershipChange(list.OwnershipChangePayload{
		NewOwner: otherOwner.SignKey.GetPublic(), OldOwnerPermissions: list.AclPermissionsReader,
	})
	require.NoError(t, err)
	f.apply(t, full, raw)
	f.ownerACL = f.fullIdentity(t, otherOwner)
	require.True(t, f.ownerACL.AclState().Permissions(f.ownerACL.AclState().Identity()).IsOwner())
	f.requireLocalPermission(t, list.AclPermissionsReader)
	info, err := f.space.Files().Get(ctx, f.fileID)
	require.NoError(t, err)
	require.False(t, info.Inline)
	require.False(t, info.Durable)
	require.Equal(t, cached, info.Cached)
	require.EqualValues(t, len(f.plain), info.Size)
	t.Logf("fresh fixture only: account=%s space=%s file=%s plaintextSHA256=%x cached=%t originalMaterialUsed=false",
		f.localID, f.space.Id(), f.fileID, sha256.Sum256(f.plain), cached)
	return f
}

func (f *freshFilesFixture) fullIdentity(t *testing.T, keys *accountdata.AccountKeys) list.AclList {
	t.Helper()
	f.localACL.RLock()
	id := f.localACL.Id()
	head := f.localACL.Head().Id
	count := len(f.localACL.Records())
	// Records() is the decoded, compacted view. The original serving API
	// returns the complete signed bytes from this new fixture's own storage.
	// Nothing is re-marshalled from a view or read from a retained account.
	records, err := f.localACL.RecordsAfter(f.ctx, "")
	f.localACL.RUnlock()
	require.NoError(t, err)
	require.NotEmpty(t, records)
	require.Len(t, records, count)
	require.Equal(t, id, records[0].Id, "fresh signed chain starts at its original root")
	require.Equal(t, head, records[len(records)-1].Id, "fresh signed chain ends at the captured head")
	storage, err := list.NewInMemoryStorage(id, records)
	require.NoError(t, err)
	verified, err := list.BuildAclListWithIdentity(keys, storage, recordverifier.NewValidateFull())
	require.NoError(t, err)
	return verified
}

func (f *freshFilesFixture) apply(t *testing.T, full list.AclList, raw *consensusproto.RawRecord) {
	t.Helper()
	var err error
	raw.AcceptorIdentity, err = f.networkKey.GetPublic().Marshall()
	require.NoError(t, err)
	raw.AcceptorSignature, err = f.networkKey.Sign(raw.Payload)
	require.NoError(t, err)
	require.NoError(t, recordverifier.New(f.networkKey.GetPublic()).VerifyAcceptor(raw))
	record := listtest.WrapAclRecord(raw)
	full.Lock()
	err = full.AddRawRecord(record)
	full.Unlock()
	require.NoError(t, err, "full author/content verifier must accept the fresh signed transition")
	f.localACL.Lock()
	previous := f.localACL.Head().Id
	err = f.localACL.AddRawRecords([]*consensusproto.RawRecordWithId{record})
	current := f.localACL.Head().Id
	f.localACL.Unlock()
	require.NoError(t, err, "actual loaded SyncAcl with the fixture network key must accept the transition")
	require.NotEqual(t, previous, current)
	require.Equal(t, record.Id, current)
}

func (f *freshFilesFixture) requireLocalPermission(t *testing.T, permission list.AclPermissions) {
	t.Helper()
	f.localACL.RLock()
	identity := f.localACL.AclState().Identity()
	account := identity.Account()
	actual := f.localACL.AclState().Permissions(identity)
	f.localACL.RUnlock()
	require.Equal(t, f.localID, account)
	require.Equal(t, permission, actual)
}

func (f *freshFilesFixture) revoke(t *testing.T) {
	t.Helper()
	metadataKey, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	raw, err := f.ownerACL.RecordBuilder().BuildAccountRemove(list.AccountRemovePayload{
		Identities: []crypto.PubKey{f.sdk.app.AccountKeys().SignKey.GetPublic()},
		Change: list.ReadKeyChangePayload{MetadataKey: metadataKey, ReadKey: crypto.NewAES()},
	})
	require.NoError(t, err)
	f.apply(t, f.ownerACL, raw)
	f.localACL.RLock()
	removed := f.localACL.AclState().Permissions(f.localACL.AclState().Identity()).NoPermissions()
	f.localACL.RUnlock()
	require.True(t, removed, "current loaded signed state must observe this fixture's removal")
}

func TestFilesOpenFreshCachedReaderStopsAtSignedRemoval(t *testing.T) {
	f := newFreshFilesFixture(t, true)
	reader, err := f.space.Files().Open(f.ctx, f.fileID, space.VariantOriginal)
	require.NoError(t, err)
	t.Cleanup(func() { f.cancel(); require.NoError(t, reader.Close()) })
	prefix := make([]byte, 32)
	n, err := reader.Read(prefix)
	require.NoError(t, err)
	require.Equal(t, 32, n)
	require.Equal(t, f.plain[:32], prefix)
	f.revoke(t)
	sentinel := bytes.Repeat([]byte{0xa5}, 64)
	before := bytes.Clone(sentinel)
	n, err = reader.Read(sentinel)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, n)
	require.Equal(t, before, sentinel, "no newly delivered cached plaintext after current removal")
	position, err := reader.Seek(0, io.SeekStart)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, position)
	n, err = reader.Read(sentinel)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, n)
	require.Equal(t, before, sentinel)
	require.Zero(t, f.baseURLCalls.Load())
}

func TestFilesOpenFreshAwaitedFetchDiscardsAfterSignedRemoval(t *testing.T) {
	f := newFreshFilesFixture(t, false)
	reader, err := f.space.Files().Open(f.ctx, f.fileID, space.VariantOriginal)
	require.NoError(t, err)
	t.Cleanup(func() { f.peer.unblock(); f.cancel(); require.NoError(t, reader.Close()) })
	info, err := f.space.Files().Get(f.ctx, f.fileID)
	require.NoError(t, err)
	require.False(t, info.Cached, "do not clear or relabel a fixture accidentally made complete by Open")
	f.peer.armed.Store(true)
	type readOutcome struct {
		n, releasedBefore int
		err               error
		buffer            []byte
		fixtureError      string
	}
	returned := make(chan readOutcome, 1)
	go func() {
		offset := 0
		for offset < len(f.plain) {
			buffer := bytes.Repeat([]byte{0xa5}, 64*1024)
			n, readErr := reader.Read(buffer)
			if f.peer.blocked.Load() {
				returned <- readOutcome{n: n, releasedBefore: offset, err: readErr, buffer: buffer}
				return
			}
			if n <= 0 || n > len(buffer) || offset+n > len(f.plain) || !bytes.Equal(buffer[:n], f.plain[offset:offset+n]) || readErr != nil {
				returned <- readOutcome{fixtureError: "cached prefix differed before the controlled pending fetch"}
				return
			}
			offset += n
		}
		returned <- readOutcome{fixtureError: "no actual range fetch remained after Open"}
	}()
	select {
	case <-f.peer.entered:
	case early := <-returned:
		t.Fatalf("fixture did not reach the actual fetch barrier: %s", early.fixtureError)
	case <-time.After(5 * time.Second):
		t.Fatal("actual fetch did not reach its bounded fixture barrier")
	}
	f.revoke(t)
	f.peer.unblock()
	select {
	case observed := <-returned:
		require.Empty(t, observed.fixtureError)
		require.ErrorIs(t, observed.err, list.ErrInsufficientPermissions)
		require.Zero(t, observed.n)
		require.Equal(t, bytes.Repeat([]byte{0xa5}, 64*1024), observed.buffer,
			"fetched plaintext must remain private after observed removal")
		t.Logf("actual SDK fetch boundary: releasedBeforeRemoval=%d rejectedAfterRemoval=%d", observed.releasedBefore, observed.n)
	case <-time.After(5 * time.Second):
		t.Fatal("pending real SDK read did not finish after fixture release")
	}
	require.True(t, f.peer.blocked.Load())
	require.Positive(t, f.peer.ranges.Load())
	require.Zero(t, f.peer.banned.Load(), "the fixture must serve valid CAR bytes, not trigger a fallback error")
	require.Zero(t, f.baseURLCalls.Load())
}
