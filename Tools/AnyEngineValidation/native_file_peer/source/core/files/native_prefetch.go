//go:build pinkha_loaded_account_witness

package files

import (
	"context"
	"errors"
	"sort"
	"strings"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/ipfs/go-cid"
	ipld "github.com/ipfs/go-ipld-format"

	"github.com/anyproto/anytype-heart/core/files/filehelper"
	"github.com/anyproto/anytype-heart/core/files/filestorage"
)

// Prefetch is an explicit preparatory read through the actual native proxy.
// The frozen local capture never calls this function or falls back to it.
type NativeFilePrefetchLimits struct {
	MaxDAGNodes int
	MaxDAGBytes int64
	MaxDuration time.Duration
}
type NativeFilePrefetchReceipt struct {
	Version, FileIDSHA256, DAGInventorySHA256    string
	DAGNodes, InitiallyLocalNodes, NativeFetches int
	DAGBytes                                     int64
	EveryFetchedBlockRereadFromLocalStore        bool
	RequiresNewFrozenCapture                     bool
	SourceAccountAuthorized                      bool
	HasNativeSourceAdmission                     bool
	PermitsDestinationWrites                     bool
}

func PrefetchNativeFileDAG(ctx context.Context, fileComponent, storageComponent app.Component,
	spaceID, fileID string, limits NativeFilePrefetchLimits) (NativeFilePrefetchReceipt, error) {
	owner, ok := fileComponent.(*service)
	if ctx == nil || !ok || owner == nil || owner.dagService == nil || spaceID == "" || fileID == "" ||
		limits.MaxDAGNodes < 1 || limits.MaxDAGNodes > 50000 || limits.MaxDAGBytes < 1 || limits.MaxDAGBytes > 3<<30 ||
		limits.MaxDuration < time.Second || limits.MaxDuration > 5*time.Minute {
		return NativeFilePrefetchReceipt{}, ErrNativeFileCapture
	}
	ctx, cancel := context.WithTimeout(ctx, limits.MaxDuration)
	defer cancel()
	actualLocal, err := filestorage.NativeSnapshotLocalDAG(storageComponent)
	if err != nil {
		return NativeFilePrefetchReceipt{}, err
	}
	local := nativeVerifiedDAG{filehelper.NewDAGServiceWithSpaceID(spaceID, actualLocal)}
	remote := nativeVerifiedDAG{filehelper.NewDAGServiceWithSpaceID(spaceID, owner.dagService)}
	root, err := cid.Parse(fileID)
	if err != nil {
		return NativeFilePrefetchReceipt{}, err
	}
	queue := []cid.Cid{root}
	seen := map[string]bool{root.String(): true}
	receipt := NativeFilePrefetchReceipt{Version: "native-bounded-file-prefetch-v1", FileIDSHA256: nativeFileHash([]byte(fileID)), RequiresNewFrozenCapture: true}
	var rows []string
	for len(queue) > 0 {
		if err := ctx.Err(); err != nil {
			return NativeFilePrefetchReceipt{}, err
		}
		id := queue[0]
		queue = queue[1:]
		node, localErr := local.Get(ctx, id)
		if localErr == nil {
			receipt.InitiallyLocalNodes++
		} else {
			// Corruption and arbitrary I/O errors are not a cache-miss authorization.
			if !ipld.IsNotFound(localErr) {
				return NativeFilePrefetchReceipt{}, localErr
			}
			node, err = remote.Get(ctx, id)
			if err != nil {
				return NativeFilePrefetchReceipt{}, err
			}
			// Native proxy logs some cache-write failures without returning them.
			// A successful remote Get therefore cannot by itself prove local readiness.
			reread, err := local.Get(ctx, id)
			if err != nil || nativeFileHash(reread.RawData()) != nativeFileHash(node.RawData()) {
				return NativeFilePrefetchReceipt{}, errors.Join(ErrNativeFileCapture, err)
			}
			receipt.NativeFetches++
		}
		receipt.DAGNodes++
		receipt.DAGBytes += int64(len(node.RawData()))
		if receipt.DAGNodes > limits.MaxDAGNodes || receipt.DAGBytes > limits.MaxDAGBytes {
			return NativeFilePrefetchReceipt{}, ErrNativeFileCapture
		}
		rows = append(rows, id.String()+":"+nativeFileHash(node.RawData()))
		for _, link := range node.Links() {
			if link == nil {
				return NativeFilePrefetchReceipt{}, ErrNativeFileCapture
			}
			if !seen[link.Cid.String()] {
				if len(seen) >= limits.MaxDAGNodes {
					return NativeFilePrefetchReceipt{}, ErrNativeFileCapture
				}
				seen[link.Cid.String()] = true
				queue = append(queue, link.Cid)
			}
		}
	}
	sort.Strings(rows)
	receipt.DAGInventorySHA256 = nativeFileHash([]byte(strings.Join(rows, "\n")))
	receipt.EveryFetchedBlockRereadFromLocalStore = true
	return receipt, nil
}
