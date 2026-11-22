package importer

import (
	"context"
	"errors"
	"sync"

	"github.com/anyproto/any-sync/app"
)

var ErrOwnedImportOperationUnavailable = errors.New("owned original import operation is unavailable")

// OwnedImportFileObservation is copied from this execution's admitted native
// calls and actual upload completions. A returned file ID does not prove that
// the original final block update succeeded or that a body is semantically equal.
type OwnedImportFileObservation struct {
	Kind, ObjectID, BlockID, FileObjectID string
	Err                                   error
}

// OwnedImportOutcome is a historical local completion. It has no caller-facing
// constructor and grants no account, archive, mapping, body or ACK authority.
// In particular, nil Err does not imply complete file/reference/body coverage.
type OwnedImportOutcome struct {
	targetSpaceID         string
	processID             string
	rootCollectionID      string
	objectsCount          int64
	cancellationRequested bool
	err                   error
	files                 []OwnedImportFileObservation
	mapping               NativeProtobufImportMappingObservation
	hasMapping            bool
	mappingProblems       []string
}

func (o OwnedImportOutcome) TargetSpaceID() string       { return o.targetSpaceID }
func (o OwnedImportOutcome) ProcessID() string           { return o.processID }
func (o OwnedImportOutcome) RootCollectionID() string    { return o.rootCollectionID }
func (o OwnedImportOutcome) ObjectsCount() int64         { return o.objectsCount }
func (o OwnedImportOutcome) CancellationRequested() bool { return o.cancellationRequested }
func (o OwnedImportOutcome) Err() error                  { return o.err }
func (o OwnedImportOutcome) Files() []OwnedImportFileObservation {
	return append([]OwnedImportFileObservation(nil), o.files...)
}
func (o OwnedImportOutcome) NativeMappingObservation() (NativeProtobufImportMappingObservation, bool) {
	return o.mapping.copy(), o.hasMapping
}
func (o OwnedImportOutcome) NativeMappingProblems() []string {
	return append([]string(nil), o.mappingProblems...)
}
func (o OwnedImportOutcome) copy() OwnedImportOutcome {
	o.files = o.Files()
	o.mapping = o.mapping.copy()
	o.mappingProblems = o.NativeMappingProblems()
	return o
}

// OwnedImportOperation retains only the actual original processor. There is no
// injected executor, caller completion callback or writable drained flag. Its
// owner must register it against the native application's lifetime BEFORE Start.
// The zero value cannot start or report completion. No production RPC uses it.
type OwnedImportOperation struct {
	processor     *importProcessor
	owned         *ownedImportExecution
	targetSpaceID string
	start         sync.Once
	done          chan struct{}
	outcome       OwnedImportOutcome
}

// PrepareOwnedImport constructs the original fresh dependency closure without
// starting native import work. It is not lifetime admission by itself. The
// request's protobuf is cloned by the reviewed private processor constructor.
func PrepareOwnedImport(ctx context.Context, a *app.App, request *ImportRequest) (*OwnedImportOperation, error) {
	if ctx == nil || a == nil {
		return nil, ErrOwnedImportOperationUnavailable
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	owned := newOwnedImportExecution(ctx)
	prepared := false
	defer func() {
		if !prepared {
			owned.cancel()
		}
	}()
	processor, err := newOwnedImportProcessor(a, owned, request)
	if err != nil {
		return nil, err
	}
	operation := &OwnedImportOperation{processor: processor, owned: owned, targetSpaceID: processor.request.SpaceId, done: make(chan struct{})}
	prepared = true
	return operation, nil
}

// TargetSpaceID is copied from the cloned request, not reread from caller data.
// It is a declared destination, not proof of native membership or permission.
func (o *OwnedImportOperation) TargetSpaceID() string {
	if o == nil {
		return ""
	}
	return o.targetSpaceID
}

// Start dispatches exactly one original Execute. It must follow the native
// owner's registration; even cancellation before Start still runs that owned
// execution to its actual return before Done closes. Starting a zero handle
// does nothing and cannot make it look drained.
func (o *OwnedImportOperation) Start() {
	if o == nil || o.processor == nil || o.owned == nil || o.done == nil {
		return
	}
	o.start.Do(func() {
		go o.run()
	})
}

func (o *OwnedImportOperation) run() {
	response := o.processor.Execute(o.owned.ctx)
	result := OwnedImportOutcome{
		targetSpaceID:         o.targetSpaceID,
		cancellationRequested: o.owned.ctx.Err() != nil,
	}
	if response == nil {
		result.err = ErrOwnedImportOperationUnavailable
	} else {
		result.processID = response.ProcessId
		result.rootCollectionID = response.RootCollectionId
		result.objectsCount = response.ObjectsCount
		result.err = response.Err
		result.mapping, result.hasMapping = response.NativeMappingObservation()
		result.mappingProblems = response.NativeMappingProblems()
	}
	if o.processor.request.SpaceId != o.targetSpaceID {
		result.err = errors.Join(result.err, ErrOwnedImportOperationUnavailable)
	}
	for _, file := range o.owned.fileResults {
		result.files = append(result.files, OwnedImportFileObservation{
			Kind: file.Kind, ObjectID: file.ObjectID, BlockID: file.BlockID,
			FileObjectID: file.FileObjectID, Err: file.Err,
		})
	}
	o.outcome = result
	// Release the derived cancellation only after Execute's finalizer and
	// mapping copyout have returned. It never substitutes for their drain.
	o.owned.cancel()
	close(o.done)
}

func (o *OwnedImportOperation) RequestCancel() {
	if o != nil && o.owned != nil && o.owned.cancel != nil {
		o.owned.cancel()
	}
}

func (o *OwnedImportOperation) Done() <-chan struct{} {
	if o == nil {
		return nil
	}
	return o.done
}

func (o *OwnedImportOperation) Result() (OwnedImportOutcome, bool) {
	if o == nil || o.done == nil {
		return OwnedImportOutcome{}, false
	}
	select {
	case <-o.done:
		return o.outcome.copy(), true
	default:
		return OwnedImportOutcome{}, false
	}
}
