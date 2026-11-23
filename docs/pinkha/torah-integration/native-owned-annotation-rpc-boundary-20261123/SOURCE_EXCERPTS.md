# Exact original cancellation and completion source excerpts

These are read-only excerpts from the immutable sources in SOURCE_INPUTS.json. No new native behavior is supplied by these excerpts.

## S26 owned_import_admission.go

Revision 455e1c55d765b25f8dd63bd472964057e5cbffc7; path docs/pinkha/torah-integration/native-owned-import-lifetime-20261122/native/core/application/owned_import_admission.go.

```go
func (r *ownedImportRegistry) pruneDrainedLocked() {
	for owned := range r.operations {
		// Only the closed original operation supplies Done. No caller-provided
		// channel, completion closure or mutable success flag is accepted.
		select {
		case <-owned.operation.Done():
			delete(r.operations, owned)
		default:
		}
	}
}
```

## S26 owned_import_admission.go

Revision 455e1c55d765b25f8dd63bd472964057e5cbffc7; path docs/pinkha/torah-integration/native-owned-import-lifetime-20261122/native/core/application/owned_import_admission.go.

```go
func (s *Service) beginOwnedImportRetirement() (func(), error) {
	r := &s.ownedImports
	r.mu.Lock()
	r.pruneDrainedLocked()
	if len(r.operations) != 0 {
		r.pending = true
		operations := make([]*importer.OwnedImportOperation, 0, len(r.operations))
		for owned := range r.operations {
			operations = append(operations, owned.operation)
		}
		r.mu.Unlock()
		for _, operation := range operations {
			operation.RequestCancel()
		}
		return nil, ErrOwnedImportDrainPending
	}
	// This is a count, not an exclusive lifecycle gate: with no owned import,
	// newer original starts still publish and cancel older starts in exactly
	// their original order, and AccountStop retains its fast cancelStart path.
	r.retirements++
	r.pending = false
	r.mu.Unlock()
	var once sync.Once
	return func() {
		once.Do(func() {
			r.mu.Lock()
			r.retirements--
			r.mu.Unlock()
		})
	}, nil
}
```

## S03 owned_import_operation.go

Revision 62e5f1c9d62c99cc00debfe7e1975557eeec32fa; path docs/pinkha/torah-integration/native-owned-annotation-contract-20261123/bc-candidate-20261123/native/core/block/import/owned_import_operation.go.

```go
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
```

## S30 core/block/process/noop.go

Revision d98420b1113536afd08cde6de9a5816f6d27ffff; path core/block/process/noop.go.

```go
func (n *noOp) Id() string {
	return ""
}

func (n *noOp) Cancel() (err error) {
	return err
}

func (n *noOp) Info() pb.ModelProcess {
	return pb.ModelProcess{}
}

func (n *noOp) Done() chan struct{} {
	return nil
}
```

## S32 core/process.go

Revision d98420b1113536afd08cde6de9a5816f6d27ffff; path core/process.go.

```go
func (mw *Middleware) ProcessCancel(cctx context.Context, req *pb.RpcProcessCancelRequest) *pb.RpcProcessCancelResponse {
	response := func(code pb.RpcProcessCancelResponseErrorCode, err error) *pb.RpcProcessCancelResponse {
		m := &pb.RpcProcessCancelResponse{Error: &pb.RpcProcessCancelResponseError{Code: code}}
		if err != nil {
			m.Error.Description = getErrorDescription(err)
		}
		return m
	}
	err := mw.doBlockService(func(bs *block.Service) error {
		return bs.ProcessCancel(req.Id)
	})
	if err != nil {
		return response(pb.RpcProcessCancelResponseError_UNKNOWN_ERROR, err)
	}
	return response(pb.RpcProcessCancelResponseError_NULL, nil)
}
```
