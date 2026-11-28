package embedded

import (
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"reflect"
	"runtime/debug"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any/internal/config"
)

func TestBoundNetworkOfficialUsesNativeParserAndPreservesDefaults(t *testing.T) {
	cfg := assembleConfig(Options{})
	original := cfg
	raw, err := config.LoadNodeconf(original.Network)
	if err != nil {
		t.Fatal(err)
	}
	want, err := config.NodeconfNetworkId(raw)
	if err != nil {
		t.Fatal(err)
	}
	got, err := pinBoundNetwork(&cfg)
	if err != nil || got != want || got == "" {
		t.Fatalf("official parser binding: got %q, want %q, error %v", got, want, err)
	}
	// This proves exact YAML pinning while retaining all original network,
	// push, P2P, mode, index and permission configuration, without booting
	// or making any connection to the official production network.
	original.Network.Nodeconf = string(raw)
	if !reflect.DeepEqual(cfg, original) {
		t.Fatal("pinning changed configuration beyond the exact resolved nodeconf bytes")
	}
}

func TestBoundNetworkCustomPreservesExactIdentityAndConfiguration(t *testing.T) {
	identities := []string{"pinkha-custom-a", "pinkha-\u00e9", "pinkha-e\u0301", strings.Repeat("a", 4096), strings.Repeat("\u00e9", 2048)}
	for _, identity := range identities {
		opts := Options{
			NodeconfYAML: " \nnetworkId: \"" + identity + "\"\nnodes: []\n ",
			PushPeerId:   "12D3KooWBoundTest",
			PushAddrs:    "quic://127.0.0.1:1",
			Mode:         "managed", ControlToken: "bound-test-capability",
		}
		cfg := assembleConfig(opts)
		original := cfg
		got, err := pinBoundNetwork(&cfg)
		if err != nil || got != identity {
			t.Fatalf("exact custom identity (%d bytes): got %q, error %v", len(identity), got, err)
		}
		if !reflect.DeepEqual(cfg, original) {
			t.Fatal("custom pin changed already-resolved configuration")
		}
	}
}

func TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem(t *testing.T) {
	resetState(t)
	defer resetState(t)
	previousLimit := debug.SetMemoryLimit(-1)
	defer debug.SetMemoryLimit(previousLimit)
	cases := []struct{ name, yaml string }{
		{"missing", "nodes: []\n"},
		{"malformed", "networkId: [\n"},
		{"duplicate", "networkId: one\nnetworkId: two\n"},
		{"empty", "networkId: \"\"\n"},
		{"space", "networkId: \"a b\"\n"},
		{"tab", "networkId: \"a\\tb\"\n"},
		{"nul", "networkId: \"a\\u0000b\"\n"},
		{"del", "networkId: \"a\\u007fb\"\n"},
		{"long_ascii", "networkId: " + strings.Repeat("x", 4097) + "\n"},
		{"long_utf8", "networkId: " + strings.Repeat("\u00e9", 2049) + "\n"},
	}
	root := t.TempDir()
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			directory := filepath.Join(root, item.name)
			result, err := StartBound(Options{
				DataDir: directory, ListenAddr: "127.0.0.1:0",
				NodeconfYAML: item.yaml, Mode: "managed", ControlToken: "bound-test-capability",
			})
			if !errors.Is(err, ErrBadOptions) || result != (BoundStartResult{}) {
				t.Fatalf("invalid identity admitted or leaked a result: %#v, %v", result, err)
			}
			if _, err := os.Lstat(directory); !errors.Is(err, os.ErrNotExist) {
				t.Fatalf("invalid identity touched the requested data directory: %v", err)
			}
			if Address() != "" {
				t.Fatal("invalid identity left a listener")
			}
		})
	}
}

func TestBoundStartCapturesExactBootAndCannotBorrowRunningIdentity(t *testing.T) {
	resetState(t)
	defer resetState(t)
	previousLimit := debug.SetMemoryLimit(-1)
	defer debug.SetMemoryLimit(previousLimit)
	disabled := false
	const token = "bound-start-test-capability"
	options := func(identity, directory string) Options {
		return Options{
			DataDir: directory, ListenAddr: "127.0.0.1:0",
			NodeconfYAML: "networkId: " + identity + "\nnodes: []\n",
			Mode:         "managed", ControlToken: token,
			LocalDiscovery: &disabled, GlobalP2PEnabled: &disabled,
		}
	}
	transport := &http.Transport{Proxy: nil}
	defer transport.CloseIdleConnections()
	client := &http.Client{
		Transport: transport, Timeout: 5 * time.Second,
		CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse },
	}
	check := func(result BoundStartResult, want string) {
		t.Helper()
		host, port, err := net.SplitHostPort(result.Address)
		if err != nil || host != "127.0.0.1" || port == "" || port == "0" || result.NetworkID != want {
			t.Fatalf("bound native result: %#v, %v", result, err)
		}
		request, err := http.NewRequest(http.MethodGet, "http://"+result.Address+"/v1/health", nil)
		if err != nil {
			t.Fatal(err)
		}
		request.Header.Set("X-Any-Control-Token", token)
		response, err := client.Do(request)
		if err != nil {
			t.Fatal(err)
		}
		body, readErr := io.ReadAll(io.LimitReader(response.Body, 65537))
		closeErr := response.Body.Close()
		if readErr != nil || closeErr != nil || response.StatusCode != 200 || len(body) > 65536 {
			t.Fatalf("bounded real native health: status %d, read %v, close %v", response.StatusCode, readErr, closeErr)
		}
		var health struct {
			NetworkID string `json:"networkId"`
			Account   string `json:"account"`
		}
		if err := json.Unmarshal(body, &health); err != nil {
			t.Fatal(err)
		}
		// The expected value is the original launch input, never obtained
		// from this response. No account or network peer is needed.
		if health.NetworkID != want || health.Account != "" {
			t.Fatalf("native boot did not use its captured config: %#v", health)
		}
	}
	firstDirectory := filepath.Join(t.TempDir(), "first")
	first, err := StartBound(options("pinkha-bound-first", firstDirectory))
	if err != nil {
		t.Fatal(err)
	}
	check(first, "pinkha-bound-first")
	secondDirectory := filepath.Join(t.TempDir(), "second")
	refused, err := StartBound(options("pinkha-bound-second", secondDirectory))
	if !errors.Is(err, ErrAlreadyRunning) || refused != (BoundStartResult{}) {
		t.Fatalf("another live engine lent its identity to a failed start: %#v, %v", refused, err)
	}
	if _, err := os.Lstat(secondDirectory); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("double start touched another data root: %v", err)
	}
	check(first, "pinkha-bound-first")
	Stop(true)
	second, err := StartBound(options("pinkha-bound-second", secondDirectory))
	if err != nil {
		t.Fatal(err)
	}
	check(second, "pinkha-bound-second")
	if first.NetworkID != "pinkha-bound-first" || first.NetworkID == second.NetworkID {
		t.Fatal("a later start changed or reused the immutable prior result")
	}
}
