package embedded

import (
	"fmt"
	"unicode/utf8"

	"github.com/anyproto/any/internal/config"
)

// BoundNetworkIDMaximumBytes matches the native HTTP account/run identity
// contract. It is a byte bound, not a Unicode character count.
const BoundNetworkIDMaximumBytes = 4096

// BoundStartResult belongs to one successful in-process start. NetworkID comes
// from the same resolved, pinned YAML bytes passed to server.RunWith. It is not
// inferred from a later HTTP response, an account record, or a process-global
// "current network" accessor.
type BoundStartResult struct {
	Address   string
	NetworkID string
}

// StartBound retains the original lifecycle and configuration defaults. Every
// failed attempt returns an entirely empty result, including already-running
// refusal: it cannot accidentally lend another boot's identity to the caller.
func StartBound(opts Options) (BoundStartResult, error) {
	var result BoundStartResult
	address, err := startEmbeddedWithBinding(opts, &result)
	if err != nil {
		return BoundStartResult{}, err
	}
	result.Address = address
	return result, nil
}

// Resolve only with the native configuration parser. assembleConfig must run
// first so official-network push/P2P defaults are decided from the ORIGINAL
// options; replacing an empty official option with YAML before assembly would
// silently change those defaults. The server receives these exact pinned bytes.
func pinBoundNetwork(cfg *config.Config) (string, error) {
	raw, err := config.LoadNodeconf(cfg.Network)
	if err != nil {
		return "", fmt.Errorf("%w: %w", ErrBadOptions, err)
	}
	networkID, err := config.NodeconfNetworkId(raw)
	if err != nil {
		return "", fmt.Errorf("%w: %w", ErrBadOptions, err)
	}
	if len(networkID) == 0 || len(networkID) > BoundNetworkIDMaximumBytes || !utf8.ValidString(networkID) {
		return "", fmt.Errorf("%w: network identity cannot cross the bound-start contract", ErrBadOptions)
	}
	for _, b := range []byte(networkID) {
		if b <= 32 || b == 127 {
			return "", fmt.Errorf("%w: network identity cannot cross the bound-start contract", ErrBadOptions)
		}
	}
	cfg.Network.Nodeconf = string(raw)
	return networkID, nil
}
