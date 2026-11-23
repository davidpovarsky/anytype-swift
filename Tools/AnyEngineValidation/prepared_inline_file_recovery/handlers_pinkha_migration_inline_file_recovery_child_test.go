//go:build linux && pinkha_inline_recovery

package server

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"sync"
	"syscall"
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any-sync/app/logger"
	"github.com/anyproto/any/internal/api"
	"github.com/anyproto/any/internal/config"
	"github.com/stretchr/testify/require"
)

type inlineRecoveryIdentityFile struct {
	Protocol string `json:"protocol"`
	Nonce    string `json:"nonce"`
	Account  string `json:"account"`
	Space    string `json:"space"`
	Owner    string `json:"owner"`
}

type inlineRecoveryBuffered struct {
	header http.Header
	body   bytes.Buffer
	status int
}

func (w *inlineRecoveryBuffered) Header() http.Header { return w.header }
func (w *inlineRecoveryBuffered) WriteHeader(status int) {
	if w.status == 0 {
		w.status = status
	}
}
func (w *inlineRecoveryBuffered) Write(raw []byte) (int, error) {
	if w.status == 0 {
		w.WriteHeader(http.StatusOK)
	}
	if w.body.Len()+len(raw) > 65536 {
		return 0, fmt.Errorf("actual response exceeds the bounded capture")
	}
	return w.body.Write(raw)
}

func inlineRecoveryObserveNative(sp space.Space, original space.MigrationInlineFileReceipt) (inlineRecoveryObservation, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	var o inlineRecoveryObservation
	native, ok := sp.Files().(space.PreparedInlineFileService)
	if !ok {
		return o, fmt.Errorf("actual native inline service is absent")
	}
	var err error
	o.Receipt, err = native.MigrationInlineFileStatus(ctx, original.IntentID)
	if err != nil {
		return o, err
	}
	if !inlineRecoveryIdentityEqual(original, o.Receipt) {
		return o, fmt.Errorf("native receipt changed reserved identities or source bindings")
	}
	o.Stats, err = sp.Files().Stats(ctx)
	if err != nil {
		return o, err
	}
	o.Files, err = sp.Files().List(ctx, space.FileListOpts{})
	if err != nil {
		return o, err
	}
	info, getErr := sp.Files().Get(ctx, original.FileID)
	if o.Receipt.Stage != "complete" {
		if getErr == nil || len(o.Files) != 0 || o.Stats.Total != 0 {
			return o, fmt.Errorf("uncommitted reservation exposed a file row")
		}
		return o, nil
	}
	if o.Receipt.Outcome != "committed" {
		return o, fmt.Errorf("native row is not the original committed result")
	}
	if getErr != nil {
		return o, getErr
	}
	o.Info = &info
	reader, err := sp.Files().Open(ctx, original.FileID, space.VariantOriginal)
	if err != nil {
		return o, err
	}
	o.Content, err = io.ReadAll(io.LimitReader(reader, 4096))
	closeErr := reader.Close()
	if err != nil {
		return o, err
	}
	if closeErr != nil {
		return o, closeErr
	}
	o.ContentSHA256 = inlineHTTPHash(o.Content)
	if o.ContentSHA256 != original.ContentSHA256 || int64(len(o.Content)) != original.Size ||
		len(o.Files) != 1 || o.Stats.Total != 1 || o.Files[0].FileId != original.FileID {
		return o, fmt.Errorf("native plaintext or independently enumerated row count differs")
	}
	return o, nil
}

func TestPreparedInlineFileRecoveryChild(t *testing.T) {
	launchPath := os.Getenv("PINKHA_INLINE_RECOVERY_LAUNCH")
	require.True(t, filepath.IsAbs(launchPath), "helper may run only as the owned explicitly launched child")
	raw, err := os.ReadFile(launchPath)
	require.NoError(t, err)
	require.LessOrEqual(t, len(raw), 16384)
	var launch inlineRecoveryLaunch
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	require.NoError(t, decoder.Decode(&launch))
	require.Equal(t, inlineRecoveryProtocol, launch.Protocol)
	require.Len(t, launch.Nonce, 32)
	require.Equal(t, launch.ParentPID, os.Getppid())
	group, err := syscall.Getpgid(0)
	require.NoError(t, err)
	require.Equal(t, os.Getpid(), group)
	info, err := os.Lstat(launch.Directory)
	require.NoError(t, err)
	require.True(t, info.IsDir() && info.Mode().Perm() == 0700)
	require.Equal(t, uint32(os.Getuid()), info.Sys().(*syscall.Stat_t).Uid)
	require.Equal(t, filepath.Join(launch.Directory, fmt.Sprintf("child-%d-launch.json", launch.Child)), launchPath)

	control := os.NewFile(3, "owned-recovery-control")
	results := os.NewFile(4, "owned-recovery-results")
	require.NotNil(t, control)
	require.NotNil(t, results)
	input := json.NewDecoder(control)
	output := json.NewEncoder(results)
	var emitMu sync.Mutex
	emit := func(frame inlineRecoveryFrame) error {
		frame.Protocol = inlineRecoveryProtocol
		frame.Nonce = launch.Nonce
		frame.PID = os.Getpid()
		frame.PGID = group
		emitMu.Lock()
		defer emitMu.Unlock()
		return output.Encode(frame)
	}

	local, err := os.ReadFile("../pinkha/migrationnative/testdata/local.yml")
	require.NoError(t, err)
	require.Equal(t, "a3fe3c21144c2c82afa03b58014752c6bca6e5a9f3e69a1bc1b2b38415434756", inlineHTTPHash(local))
	reject, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	go func() {
		for {
			c, err := reject.Accept()
			if err != nil {
				return
			}
			_ = c.Close()
		}
	}()
	port := reject.Addr().(*net.TCPAddr).Port
	addresses := regexp.MustCompile(`127\.0\.0\.1:\d+`)
	require.Len(t, addresses.FindAll(local, -1), 8)
	network := addresses.ReplaceAll(local, []byte("127.0.0.1:"+strconv.Itoa(port)))
	cfg := config.Defaults()
	cfg.DataDir = launch.Directory
	cfg.Network.NodeconfPath = ""
	cfg.Network.Nodeconf = string(network)
	disabled := false
	cfg.P2P.Enabled = &disabled
	cfg.P2P.LocalDiscovery = &disabled
	cfg.P2P.Global.Enabled = &disabled
	cfg.P2P.Global.RelayUrls = nil
	cfg.P2P.Global.PkarrRelayUrls = nil
	cfg.Push = config.Push{}
	require.False(t, cfg.P2P.IsEnabled())
	require.False(t, cfg.P2P.GlobalEnabled())
	require.False(t, cfg.Push.Active())
	networkID, err := pinNodeconf(&cfg)
	require.NoError(t, err)
	provider, created, err := OpenWallet(filepath.Join(launch.Directory, "wallet.key"), "", "", 0)
	require.NoError(t, err)
	require.Equal(t, launch.Child == 1, created)
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	sdk, err := OpenSDK(ctx, cfg, network, launch.Directory, provider)
	require.NoError(t, err)
	account, err := AccountID(ctx, provider)
	require.NoError(t, err)
	signKey, err := accountKey(ctx, provider)
	require.NoError(t, err)

	eng := newEngine()
	eng.sdk = sdk
	eng.account = account
	eng.signKey = signKey
	eng.chunkers = NewIndexRegistry()
	eng.derived, err = resolveDerivedSpaces(ctx, sdk)
	require.NoError(t, err)
	d := &deps{startedAt: time.Now().UTC(), networkId: networkID, shutdown: make(chan struct{}, 1),
		root: launch.Directory, cfg: cfg, runCtx: context.Background(), eng: eng, sdk: sdk,
		account: account, signKey: signKey, derived: eng.derived, shutdownCtx: eng.ctx}
	d.ready.Store(true)
	identityPath := filepath.Join(launch.Directory, "identity.json")
	var identity inlineRecoveryIdentityFile
	var sp space.Space
	if created {
		_, err = os.Lstat(identityPath)
		require.True(t, os.IsNotExist(err))
		sp, err = sdk.Spaces().Create(ctx, space.CreateRequest{Name: "owned inline recovery"})
		require.NoError(t, err)
		owner, err := space.CreateCurrentWriter(ctx, sp, space.CreateObjectOpts{Type: "page",
			InitialProperties: map[string]map[string]any{"any": {"name": "owned recovery file owner"}}})
		require.NoError(t, err)
		identity = inlineRecoveryIdentityFile{Protocol: inlineRecoveryProtocol, Nonce: launch.Nonce,
			Account: account, Space: sp.Id(), Owner: owner.ObjectID}
		require.NoError(t, inlineRecoveryWrite(identityPath, identity))
	} else {
		raw, err := os.ReadFile(identityPath)
		require.NoError(t, err)
		require.NoError(t, json.Unmarshal(raw, &identity))
		require.Equal(t, inlineRecoveryProtocol, identity.Protocol)
		require.Equal(t, launch.Nonce, identity.Nonce)
		require.Equal(t, account, identity.Account)
		sp, err = sdk.Spaces().Get(ctx, identity.Space)
		require.NoError(t, err)
		_, err = sp.Objects().Get(ctx, identity.Owner)
		require.NoError(t, err)
	}
	cancel()

	router := buildEcho(d)
	var dropMu sync.Mutex
	var armed *inlineRecoveryCommand
	dropCount := 0
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		dropMu.Lock()
		match := armed != nil && r.Method == http.MethodPost && r.URL.Path == armed.Path &&
			r.Header.Get("X-Pinkha-Recovery-Nonce") == launch.Nonce
		var requested inlineRecoveryCommand
		if match {
			requested = *armed
			armed = nil
			dropCount++
		}
		count := dropCount
		dropMu.Unlock()
		if !match {
			router.ServeHTTP(w, r)
			return
		}

		var proof inlineRecoveryDrop
		fail := func(err error) {
			_ = emit(inlineRecoveryFrame{Kind: "dropped", Error: err.Error(), Drop: &proof})
			http.Error(w, "owned fault boundary failed", http.StatusInternalServerError)
		}
		body, err := io.ReadAll(io.LimitReader(r.Body, 65537))
		_ = r.Body.Close()
		if err != nil {
			fail(err)
			return
		}
		proof.RequestSHA256 = inlineHTTPHash(body)
		if len(body) > 65536 || proof.RequestSHA256 != requested.RequestSHA256 || count != 1 {
			fail(fmt.Errorf("fault target request differs from the one exact armed commit"))
			return
		}
		r.Body = io.NopCloser(bytes.NewReader(body))
		buffer := &inlineRecoveryBuffered{header: make(http.Header)}
		// The real route performs the native commit; only its outgoing bytes wait.
		router.ServeHTTP(buffer, r)
		proof.ResponseStatus = buffer.status
		proof.ResponseBytes = buffer.body.Len()
		proof.ResponseSHA256 = inlineHTTPHash(buffer.body.Bytes())
		proof.TargetRequests = count
		var response space.MigrationInlineFileReceipt
		if err = json.Unmarshal(buffer.body.Bytes(), &response); err != nil {
			fail(err)
			return
		}
		if buffer.status != http.StatusOK || response.Stage != "complete" || response.Outcome != "committed" ||
			!inlineRecoveryIdentityEqual(requested.Receipt, response) {
			fail(fmt.Errorf("real commit handler did not return the exact complete native receipt"))
			return
		}
		proof.Observation, err = inlineRecoveryObserveNative(sp, requested.Receipt)
		if err != nil {
			fail(err)
			return
		}
		if proof.Observation.Receipt.Stage != "complete" || proof.Observation.Receipt.Outcome != "committed" {
			fail(fmt.Errorf("independent native readback did not establish commit before response loss"))
			return
		}
		hijacker, ok := w.(http.Hijacker)
		if !ok {
			fail(fmt.Errorf("real HTTP connection does not support owned hijack"))
			return
		}
		connection, buffered, err := hijacker.Hijack()
		if err != nil {
			fail(err)
			return
		}
		proof.Hijacked = true
		proof.NetworkBufferedBytes = buffered.Writer.Buffered()
		if proof.NetworkBufferedBytes != 0 {
			_ = connection.Close()
			_ = emit(inlineRecoveryFrame{Kind: "dropped", Error: "unexpected response bytes buffered on actual socket", Drop: &proof})
			return
		}
		// No buffered handler response is copied to this actual client socket.
		proof.ForwardedBytes = 0
		err = connection.Close()
		proof.ConnectionClosed = err == nil
		if err != nil {
			_ = emit(inlineRecoveryFrame{Kind: "dropped", Error: err.Error(), Drop: &proof})
			return
		}
		if err := emit(inlineRecoveryFrame{Kind: "dropped", Drop: &proof}); err != nil {
			t.Errorf("write owned drop proof: %v", err)
		}
	})
	server := httptest.NewServer(handler)
	require.True(t, server.Listener.Addr().(*net.TCPAddr).IP.IsLoopback())
	client := inlineRecoveryHTTPClient()
	response, err := client.Get(server.URL + "/v1/spaces/" + identity.Space + "/pinkha/migration/inline-file/capabilities")
	require.NoError(t, err)
	require.Equal(t, http.StatusOK, response.StatusCode)
	var capability api.MigrationInlineFileCapabilities
	require.NoError(t, json.NewDecoder(io.LimitReader(response.Body, 65536)).Decode(&capability))
	require.NoError(t, response.Body.Close())
	client.CloseIdleConnections()
	require.Equal(t, identity.Account, capability.AccountID)
	require.Equal(t, identity.Space, capability.SpaceID)
	require.NoError(t, emit(inlineRecoveryFrame{Kind: "ready", Ready: &inlineRecoveryReady{
		URL: server.URL, Owner: identity.Owner, Capability: capability, WalletCreated: created}}))

	sequence := 0
	for {
		var command inlineRecoveryCommand
		require.NoError(t, input.Decode(&command), "control channel ended without an explicit completion")
		sequence++
		require.Equal(t, inlineRecoveryProtocol, command.Protocol)
		require.Equal(t, launch.Nonce, command.Nonce)
		require.Equal(t, sequence, command.Sequence)
		frame := inlineRecoveryFrame{Kind: command.Kind, Sequence: command.Sequence}
		switch command.Kind {
		case "observe":
			o, err := inlineRecoveryObserveNative(sp, command.Receipt)
			frame.Observation = &o
			if err != nil {
				frame.Error = err.Error()
			}
		case "arm-drop":
			dropMu.Lock()
			if armed != nil || dropCount != 0 || command.Receipt.OwnerObjectID != identity.Owner ||
				command.Receipt.AccountID != identity.Account || command.Receipt.SpaceID != identity.Space ||
				command.Path != "/v1/spaces/"+identity.Space+"/pinkha/migration/intents/"+command.Receipt.IntentID+"/inline-file/commit" ||
				len(command.RequestSHA256) != 64 {
				frame.Error = "refused a repeated or out-of-scope response-loss arm"
			} else {
				copy := command
				armed = &copy
			}
			dropMu.Unlock()
		case "close":
			start := filepath.Join(launch.Directory, fmt.Sprintf("child-%d-close-start.json", launch.Child))
			done := filepath.Join(launch.Directory, fmt.Sprintf("child-%d-close-complete.json", launch.Child))
			require.NoError(t, inlineRecoveryWrite(start, map[string]any{"pid": os.Getpid(), "nonce": launch.Nonce}))
			server.Close()
			d.teardownEngine(logger.NewNamed("owned-inline-recovery"), api.SubscribeClosedServerShutdown)
			require.NoError(t, reject.Close())
			require.NoError(t, inlineRecoveryWrite(done, map[string]any{"pid": os.Getpid(), "nonce": launch.Nonce}))
			require.NoError(t, emit(frame))
			require.NoError(t, control.Close())
			require.NoError(t, results.Close())
			return
		default:
			frame.Error = "unknown owned control command"
		}
		require.NoError(t, emit(frame))
	}
}
