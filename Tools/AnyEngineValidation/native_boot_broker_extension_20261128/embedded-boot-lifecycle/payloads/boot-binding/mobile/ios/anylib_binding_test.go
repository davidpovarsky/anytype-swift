package main

import (
	"path/filepath"
	"testing"

	"github.com/anyproto/any/internal/embedded"
)

func TestBoundCArchiveCoreCarriesExactIdentityAndClearsFailure(t *testing.T) {
	embedded.Stop(true)
	defer embedded.Stop(true)
	const identity = "pinkha-c-bound-identity"
	result := startBoundEngine(
		filepath.Join(t.TempDir(), "account-root"), "127.0.0.1:0",
		"networkId: "+identity+"\nnodes: []\n", "", "", "managed", "bound-c-capability")
	if result.code != embedded.CodeOK || result.address == "" || result.message != "" || result.networkID != identity {
		t.Fatalf("bound C core result: %#v", result)
	}
	refused := startBoundEngine(
		filepath.Join(t.TempDir(), "other-root"), "127.0.0.1:0",
		"networkId: pinkha-another\nnodes: []\n", "", "", "managed", "bound-c-capability")
	if refused.code != embedded.Code(embedded.ErrAlreadyRunning) || refused.address != "" ||
		refused.networkID != "" || refused.message == "" {
		t.Fatalf("failed C core leaked another start's identity: %#v", refused)
	}
}
