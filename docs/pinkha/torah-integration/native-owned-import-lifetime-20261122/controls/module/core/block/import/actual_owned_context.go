package importer
import "context"
import "sync"
import "github.com/anyproto/anytype-heart/core/files/fileuploader"
type ownedImportFileResult struct {
	Kind, ObjectID, BlockID, FileObjectID string
	Err                                   error
}

// A slot is registered before native upload admission, including its initial
// object-lock/Apply phase. Cancelling a context never closes ready or Done.
type ownedImportFileSlot struct {
	ready  chan struct{}
	async  *fileuploader.OwnedUpload
	result ownedImportFileResult
}

type ownedImportExecution struct {
	ctx         context.Context
	cancel      context.CancelFunc
	mu          sync.Mutex
	started     bool
	sealed      bool
	files       []*ownedImportFileSlot
	fileResults []ownedImportFileResult
}

func newOwnedImportExecution(ctx context.Context) *ownedImportExecution {
	ownedCtx, cancel := context.WithCancel(ctx)
	return &ownedImportExecution{ctx: ownedCtx, cancel: cancel}
}
