package main

/*
#include <stdint.h>

// Additive ABI. The original AnyLibStartResult layout is unchanged.
// network_id is exact and never truncated: the shared core rejects identities
// longer than 4096 UTF-8 bytes, invalid UTF-8, NUL or ASCII whitespace/control.
// All buffers are NUL-terminated and returned by value; no caller free.
typedef struct {
    int32_t code;
    char    address[64];
    char    message[512];
    char    network_id[4097];
} AnyLibBoundStartResult;
*/
import "C"

import "github.com/anyproto/any/internal/embedded"

type boundStartResult struct {
	code      int32
	address   string
	message   string
	networkID string
}

func startBoundEngine(dataDir, listenAddr, nodeconfYAML, pushPeerId, pushAddrs, mode, controlToken string) boundStartResult {
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
		return boundStartResult{code: embedded.Code(err), message: err.Error()}
	}
	return boundStartResult{code: embedded.CodeOK, address: result.Address, networkID: result.NetworkID}
}

// AnyLibStartBoundWithMode is the additive network-bound lifecycle entry point.
// A failure contains no identity from another already-running instance.
//
//export AnyLibStartBoundWithMode
func AnyLibStartBoundWithMode(dataDir, listenAddr, nodeconfYAML, pushPeerId, pushAddrs, mode, controlToken *C.char) C.AnyLibBoundStartResult {
	result := startBoundEngine(
		C.GoString(dataDir), C.GoString(listenAddr), C.GoString(nodeconfYAML),
		C.GoString(pushPeerId), C.GoString(pushAddrs),
		C.GoString(mode), C.GoString(controlToken),
	)
	var out C.AnyLibBoundStartResult
	out.code = C.int32_t(result.code)
	fillC(out.address[:], result.address)
	fillC(out.message[:], result.message)
	fillC(out.network_id[:], result.networkID)
	return out
}
