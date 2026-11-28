//go:build android || gomobile

package mobile

import (
	"path/filepath"
	"testing"

	"github.com/anyproto/any/internal/embedded"
)

func TestBoundMobileResultCarriesExactIdentityAndClearsFailure(t *testing.T) {
	embedded.Stop(true)
	defer embedded.Stop(true)
	const identity = "pinkha-mobile-bound-identity"
	result := StartBoundWithResult(
		filepath.Join(t.TempDir(), "account-root"), "127.0.0.1:0",
		"networkId: "+identity+"\nnodes: []\n", "", "", "managed", "bound-mobile-capability")
	if result == nil || result.Code != embedded.CodeOK || result.Address == "" ||
		result.Message != "" || result.NetworkID != identity {
		t.Fatalf("bound mobile result: %#v", result)
	}
	refused := StartBoundWithResult(
		filepath.Join(t.TempDir(), "other-root"), "127.0.0.1:0",
		"networkId: pinkha-another\nnodes: []\n", "", "", "managed", "bound-mobile-capability")
	if refused == nil || refused.Code != embedded.Code(embedded.ErrAlreadyRunning) ||
		refused.Address != "" || refused.NetworkID != "" || refused.Message == "" {
		t.Fatalf("failed mobile call leaked another start's identity: %#v", refused)
	}
}
