//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance && pinkha_native_file_peer_acceptance

package application

import (
	"context"
	"encoding/json"
	"errors"
	"net"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/net/peerservice"
	"github.com/anyproto/any-sync/net/pool"
	"github.com/ipfs/go-cid"
	ipld "github.com/ipfs/go-ipld-format"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/device"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/core/files/filehelper"
	"github.com/anyproto/anytype-heart/core/files/filestorage"
	"github.com/anyproto/anytype-heart/core/wallet"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/spacecore"
	"github.com/anyproto/anytype-heart/space/spacecore/clientserver"
	"github.com/anyproto/anytype-heart/space/spacecore/peerstore"
	corenative "github.com/anyproto/anytype-heart/space/spacecore/storage"
)

const nativeFilePeerProtocol = "pinkha-native-source-file-peers-v1"

type nativeFilePeerIdentity struct {
	AccountID, PeerID, IP, Namespace string
	Port, PID                        int
}
type nativeFilePeerVariantExpectation struct {
	Path, ContentID, MetadataID, MetadataSHA256, PlaintextSHA256 string
	MetadataBytes                                                int
	PlaintextBytes                                               int64
}
type nativeFilePeerSource struct {
	SpaceID, PageID, FileObjectID, FileID string
	Variants                              []nativeFilePeerVariantExpectation
}
type nativeFilePeerCommand struct {
	Protocol, Nonce, Phase string
	Peer                   *nativeFilePeerIdentity
	Source                 *nativeFilePeerSource
	ACLHead                string
}
type nativeFilePeerWallet struct {
	AccountID, Mnemonic string
	Source              *nativeFilePeerSource
}

func nativeFilePeerWrite(t *testing.T, root, name string, value any) {
	t.Helper()
	require.Equal(t, filepath.Base(name), name)
	raw, err := json.MarshalIndent(value, "", "  ")
	require.NoError(t, err)
	final := filepath.Join(root, name)
	_, err = os.Lstat(final)
	require.True(t, os.IsNotExist(err), "owned phase cannot be replayed")
	temp, err := os.CreateTemp(root, "owned-phase-")
	require.NoError(t, err)
	require.NoError(t, temp.Chmod(0600))
	_, writeErr := temp.Write(append(raw, '\n'))
	require.NoError(t, errors.Join(writeErr, temp.Sync(), temp.Close()))
	require.NoError(t, os.Rename(temp.Name(), final))
}
func nativeFilePeerCommandRead(t *testing.T, ctx context.Context, root, phase, nonce string) nativeFilePeerCommand {
	t.Helper()
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	for {
		raw, err := os.ReadFile(filepath.Join(root, phase+".command.json"))
		if err == nil {
			require.LessOrEqual(t, len(raw), 128<<10)
			var command nativeFilePeerCommand
			require.NoError(t, json.Unmarshal(raw, &command))
			require.Equal(t, nativeFilePeerProtocol, command.Protocol)
			require.Equal(t, nonce, command.Nonce)
			require.Equal(t, phase, command.Phase)
			return command
		}
		require.True(t, os.IsNotExist(err), "owned command read failed")
		select {
		case <-ctx.Done():
			t.Fatal("owned peer phase deadline:", phase, ctx.Err())
		case <-ticker.C:
		}
	}
}
func nativeFilePeerIPv4(t *testing.T) []string {
	t.Helper()
	interfaces, err := net.Interfaces()
	require.NoError(t, err)
	var addresses []string
	for _, entry := range interfaces {
		if entry.Flags&net.FlagUp == 0 || entry.Flags&net.FlagLoopback != 0 {
			continue
		}
		entries, err := entry.Addrs()
		require.NoError(t, err)
		for _, entry := range entries {
			ip, _, err := net.ParseCIDR(entry.String())
			require.NoError(t, err)
			if ip = ip.To4(); ip != nil && !ip.IsLoopback() {
				addresses = append(addresses, ip.String())
			}
		}
	}
	sort.Strings(addresses)
	return addresses
}
func nativeFilePeerRoute(t *testing.T, f *loadedAccountFixture, remote nativeFilePeerIdentity, spaceID string) {
	t.Helper()
	require.NotEmpty(t, remote.PeerID)
	require.NotNil(t, net.ParseIP(remote.IP))
	require.Greater(t, remote.Port, 0)
	require.Less(t, remote.Port, 65536)
	app.MustComponent[peerservice.PeerService](f.service.GetApp()).SetPeerAddrs(remote.PeerID, []string{"yamux://" + net.JoinHostPort(remote.IP, strconv.Itoa(remote.Port))})
	app.MustComponent[peerstore.PeerStore](f.service.GetApp()).UpdateLocalPeer(remote.PeerID, []string{spaceID})
}
func nativeFilePeerNetwork(t *testing.T, f *loadedAccountFixture, online bool) {
	t.Helper()
	state := model.DeviceNetworkType_NOT_CONNECTED
	if online {
		state = model.DeviceNetworkType_WIFI
	}
	app.MustComponent[device.NetworkState](f.service.GetApp()).SetNetworkState(state, "owned-native-file-peer-bridge")
}
func nativeFilePeerWait(t *testing.T, ctx context.Context, label string, fn func() bool) {
	t.Helper()
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	for {
		if fn() {
			return
		}
		select {
		case <-ctx.Done():
			t.Fatal("native file peer wait:", label, ctx.Err())
		case <-ticker.C:
		}
	}
}
func newNativeFilePeerFixture(t *testing.T, root, role, phase string) (*loadedAccountFixture, nativeFilePeerIdentity, *nativeFilePeerWallet) {
	t.Helper()
	require.Equal(t, "/private", root)
	info, err := os.Lstat(root)
	require.NoError(t, err)
	require.True(t, info.IsDir())
	require.Equal(t, os.FileMode(0700), info.Mode().Perm())
	physical, err := filepath.EvalSymlinks(root)
	require.NoError(t, err)
	require.Equal(t, root, physical)
	accountRoot := filepath.Join(root, "account-root")
	entries, err := os.ReadDir(accountRoot)
	require.NoError(t, err)
	if phase == "reopen" {
		require.NotEmpty(t, entries)
		require.Empty(t, nativeFilePeerIPv4(t))
	} else {
		require.Empty(t, entries)
		require.Len(t, nativeFilePeerIPv4(t), 1)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 18*time.Minute)
	f := &loadedAccountFixture{service: New(), ctx: ctx, cancel: cancel, dir: root}
	t.Cleanup(func() {
		if !f.stopped {
			require.NoError(t, f.service.Stop())
			f.stopped = true
		}
		cancel()
	})
	f.service.SetClientVersion("pinkha-native-source-file-peer", "1.0.0")
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	f.service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	saved := &nativeFilePeerWallet{}
	if phase == "reopen" {
		require.Equal(t, "member", role)
		raw, err := os.ReadFile(filepath.Join(root, "own-wallet.private.json"))
		require.NoError(t, err)
		require.NoError(t, json.Unmarshal(raw, saved))
		require.NotEmpty(t, saved.AccountID)
		require.NotEmpty(t, saved.Mnemonic)
		require.NoError(t, f.service.WalletRecover(&pb.RpcWalletRecoverRequest{RootPath: accountRoot, Mnemonic: saved.Mnemonic}))
		f.account, err = f.service.AccountSelect(ctx, &pb.RpcAccountSelectRequest{Id: saved.AccountID, RootPath: accountRoot, NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true})
		require.NoError(t, err)
		require.Equal(t, saved.AccountID, f.account.Id)
	} else {
		mnemonic, _, err := f.service.WalletCreate(&pb.RpcWalletCreateRequest{RootPath: accountRoot})
		require.NoError(t, err)
		require.NotEmpty(t, mnemonic)
		f.account, err = f.service.AccountCreate(ctx, &pb.RpcAccountCreateRequest{Name: "Owned native file peer " + role, StorePath: accountRoot, NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: false})
		require.NoError(t, err)
		require.NotNil(t, f.account)
		require.NotEmpty(t, f.account.Id)
		saved.AccountID, saved.Mnemonic = f.account.Id, mnemonic
	}
	f.mnemonic = saved.Mnemonic
	f.core = app.MustComponent[spacecore.SpaceCoreService](f.service.GetApp())
	var ok bool
	f.provider, ok = f.service.GetApp().Component(spacestorage.CName).(corenative.ClientStorage)
	require.True(t, ok)
	keys := app.MustComponent[accountservice.Service](f.service.GetApp()).Account()
	require.Equal(t, f.account.Id, keys.SignKey.GetPublic().Account())
	ownedWallet := app.MustComponent[wallet.Wallet](f.service.GetApp())
	require.Equal(t, filepath.Join(accountRoot, f.account.Id), ownedWallet.RepoPath())
	f.token = f.newFullSession(t)
	namespace, err := os.Readlink("/proc/self/ns/net")
	require.NoError(t, err)
	identity := nativeFilePeerIdentity{AccountID: f.account.Id, PeerID: keys.PeerId, Namespace: namespace, PID: os.Getpid()}
	if phase != "reopen" {
		nativeFilePeerNetwork(t, f, true)
		server := app.MustComponent[clientserver.ClientServer](f.service.GetApp())
		nativeFilePeerWait(t, ctx, "actual native server", server.ServerStarted)
		identity.Port = server.Port()
		identity.IP = nativeFilePeerIPv4(t)[0]
	}
	return f, identity, saved
}
func nativeFilePeerConnect(t *testing.T, f *loadedAccountFixture, remote nativeFilePeerIdentity) {
	t.Helper()
	ctx, cancel := context.WithTimeout(f.ctx, 30*time.Second)
	defer cancel()
	connection, err := app.MustComponent[pool.Service](f.service.GetApp()).Get(ctx, remote.PeerID)
	require.NoError(t, err)
	require.NotNil(t, connection)
	require.Equal(t, remote.PeerID, connection.Id())
}

// Only this disposable member's actual flat-store DAG is removed, after the
// controller has detached its network. No creator store or native tree is
// removed or copied, and no bytes are seeded into the member.
func nativeFilePeerOffload(t *testing.T, f *loadedAccountFixture, fileID string) int {
	t.Helper()
	require.Empty(t, nativeFilePeerIPv4(t))
	local, err := filestorage.NativeSnapshotLocalDAG(f.service.GetApp().Component(filestorage.CName))
	require.NoError(t, err)
	dag := filehelper.NewDAGServiceWithSpaceID(f.space.Id(), local)
	root, err := cid.Parse(fileID)
	require.NoError(t, err)
	queue := []cid.Cid{root}
	seen := map[string]bool{}
	var present []cid.Cid
	for len(queue) > 0 {
		id := queue[0]
		queue = queue[1:]
		if seen[id.String()] {
			continue
		}
		seen[id.String()] = true
		require.LessOrEqual(t, len(seen), 4000)
		node, err := dag.Get(f.ctx, id)
		if ipld.IsNotFound(err) {
			continue
		}
		require.NoError(t, err)
		require.NotNil(t, node)
		actual, err := id.Prefix().Sum(node.RawData())
		require.NoError(t, err)
		require.True(t, actual.Equals(id))
		present = append(present, id)
		for _, link := range node.Links() {
			require.NotNil(t, link)
			queue = append(queue, link.Cid)
		}
	}
	for _, id := range present {
		require.NoError(t, dag.Remove(f.ctx, id))
	}
	_, err = dag.Get(f.ctx, root)
	require.True(t, ipld.IsNotFound(err), "native file root must be absent locally")
	return len(present)
}
