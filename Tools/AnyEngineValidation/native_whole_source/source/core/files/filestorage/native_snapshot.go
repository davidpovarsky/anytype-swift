//go:build pinkha_loaded_account_witness

package filestorage

import (
	"errors"

	"github.com/anyproto/any-sync/app"
	ipld "github.com/ipfs/go-ipld-format"
)

// NativeSnapshotLocalDAG accepts only the actual concrete registered storage.
// It grants a local read surface, not account authorization or remote loading.
func NativeSnapshotLocalDAG(component app.Component) (ipld.DAGService, error) {
	storage, ok := component.(*fileStorage)
	if !ok || storage == nil || storage.localDAGService == nil {
		return nil, errors.New("actual native local file storage required")
	}
	return storage.localDAGService, nil
}
