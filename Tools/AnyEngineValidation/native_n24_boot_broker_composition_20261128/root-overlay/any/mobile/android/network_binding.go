//go:build android || gomobile

package mobile

import "github.com/anyproto/any/internal/embedded"

// BoundStartResult is additive: the original StartResult and all existing
// exported functions keep their signatures. An unsuccessful start exposes
// neither an address nor a network identity.
type BoundStartResult struct {
	Code      int32
	Address   string
	Message   string
	NetworkID string
}

// StartBoundWithResult captures network identity inside the same native call
// that starts this listener. It retains the exact original seven host inputs.
func StartBoundWithResult(dataDir, listenAddr, nodeconfYAML, pushPeerId, pushAddrs, mode, controlToken string) *BoundStartResult {
	result, err := embedded.StartBound(embedded.Options{
		DataDir:      dataDir,
		ListenAddr:   listenAddr,
		NodeconfYAML: nodeconfYAML,
		PushPeerId:   pushPeerId,
		PushAddrs:    pushAddrs,
		Mode:         mode,
		ControlToken: controlToken,
	})
	if err != nil {
		return &BoundStartResult{Code: embedded.Code(err), Message: err.Error()}
	}
	return &BoundStartResult{Code: embedded.CodeOK, Address: result.Address, NetworkID: result.NetworkID}
}
