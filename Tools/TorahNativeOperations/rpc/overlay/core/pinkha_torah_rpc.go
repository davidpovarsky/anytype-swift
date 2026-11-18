package core

import (
	"context"
	"errors"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// A successful wire response is bounded by the normal gRPC message limit.
// Bounds never cause a truncated successful projection or erase a write receipt.
const pinkhaTorahMaxReplyBytes = 4 * 1024 * 1024

// These methods are the generated ClientCommands boundary. They deliberately
// delegate all account, ACL, author, target, root and lifecycle authority to the
// existing native handlers. Neither registration nor a local receipt enables UI
// or acknowledges another client's synchronization.
func (mw *Middleware) PinkhaTorahOperationsAppend(ctx context.Context, req *pb.RpcPinkhaTorahOperationsAppendRequest) *pb.RpcPinkhaTorahOperationsAppendResponse {
	native, err := pinkhaTorahAppendFromWire(req)
	if err != nil {
		return pinkhaTorahAppendToWire(torahops.NativeAppendResult{}, err)
	}
	result, err := mw.NativeTorahOperationAppend(ctx, native)
	return pinkhaTorahAppendToWire(result, err)
}

func (mw *Middleware) PinkhaTorahOperationsReadTarget(ctx context.Context, req *pb.RpcPinkhaTorahOperationsReadTargetRequest) *pb.RpcPinkhaTorahOperationsReadTargetResponse {
	native, err := pinkhaTorahReadFromWire(req)
	if err != nil {
		return pinkhaTorahReadToWire(torahops.NativeSnapshot{}, err)
	}
	result, err := mw.NativeTorahTargetRead(ctx, native)
	return pinkhaTorahReadToWire(result, err)
}

func pinkhaTorahAppendFromWire(req *pb.RpcPinkhaTorahOperationsAppendRequest) (PinkhaTorahAppendRequest, error) {
	if req == nil {
		return PinkhaTorahAppendRequest{}, torahops.ErrInvalid
	}
	if req.ProtocolVersion != PinkhaTorahOperationsVersion {
		return PinkhaTorahAppendRequest{}, torahops.ErrUnsupportedVersion
	}
	if req.Target == nil || req.Size() > torahops.MaxWireBytes {
		return PinkhaTorahAppendRequest{}, torahops.ErrInvalid
	}
	kind, err := pinkhaTorahKindFromWire(req.Kind)
	if err != nil {
		return PinkhaTorahAppendRequest{}, err
	}
	source := torahops.Source{}
	if req.Source != nil {
		source = torahops.Source{ProviderID: req.Source.ProviderId, CanonicalRef: req.Source.CanonicalRef}
	}
	return PinkhaTorahAppendRequest{Version: req.ProtocolVersion, SpaceID: req.SpaceId,
		OperationID: req.OperationId, Kind: kind,
		Target: torahops.Target{ObjectID: req.Target.ObjectId, BlockID: req.Target.BlockId}, Source: source,
		Payload: append([]byte{}, req.Payload...), Observed: append([]string{}, req.ObservedClaimIds...)}, nil
}

func pinkhaTorahReadFromWire(req *pb.RpcPinkhaTorahOperationsReadTargetRequest) (PinkhaTorahReadRequest, error) {
	if req == nil {
		return PinkhaTorahReadRequest{}, torahops.ErrInvalid
	}
	if req.ProtocolVersion != PinkhaTorahOperationsVersion {
		return PinkhaTorahReadRequest{}, torahops.ErrUnsupportedVersion
	}
	if req.Target == nil || req.Limit == 0 || req.Limit > 10000 || req.Size() > torahops.MaxWireBytes {
		return PinkhaTorahReadRequest{}, torahops.ErrInvalid
	}
	return PinkhaTorahReadRequest{Version: req.ProtocolVersion, SpaceID: req.SpaceId,
		Target: torahops.Target{ObjectID: req.Target.ObjectId, BlockID: req.Target.BlockId}, Limit: uint(req.Limit)}, nil
}

func pinkhaTorahKindFromWire(kind pb.RpcPinkhaTorahOperationsKind) (torahops.Kind, error) {
	switch kind {
	case pb.RpcPinkhaTorahOperations_ADD:
		return torahops.Add, nil
	case pb.RpcPinkhaTorahOperations_REMOVE:
		return torahops.Remove, nil
	case pb.RpcPinkhaTorahOperations_REPLACE:
		return torahops.Replace, nil
	default:
		return "", torahops.ErrInvalid
	}
}

func pinkhaTorahKindToWire(kind torahops.Kind) pb.RpcPinkhaTorahOperationsKind {
	switch kind {
	case torahops.Add:
		return pb.RpcPinkhaTorahOperations_ADD
	case torahops.Remove:
		return pb.RpcPinkhaTorahOperations_REMOVE
	case torahops.Replace:
		return pb.RpcPinkhaTorahOperations_REPLACE
	default:
		return pb.RpcPinkhaTorahOperations_KIND_UNSPECIFIED
	}
}

func pinkhaTorahClaimToWire(claim torahops.Claim) *pb.RpcPinkhaTorahOperationsClaim {
	op := claim.Operation
	return &pb.RpcPinkhaTorahOperationsClaim{ClaimId: claim.ID, Digest: claim.Digest,
		Operation: &pb.RpcPinkhaTorahOperationsOperation{Version: op.Version, SpaceId: op.SpaceID,
			OperationId: op.OperationID, AuthorId: op.AuthorID, Kind: pinkhaTorahKindToWire(op.Kind),
			Target:  &pb.RpcPinkhaTorahOperationsTarget{ObjectId: op.Target.ObjectID, BlockId: op.Target.BlockID},
			Source:  &pb.RpcPinkhaTorahOperationsSource{ProviderId: op.Source.ProviderID, CanonicalRef: op.Source.CanonicalRef},
			Payload: append([]byte{}, op.Payload...), ObservedClaimIds: append([]string{}, op.Observed...)}}
}

func pinkhaTorahResolutionToWire(result torahops.Resolution, budget int) (*pb.RpcPinkhaTorahOperationsResolution, error) {
	out := &pb.RpcPinkhaTorahOperationsResolution{OperationId: result.OperationID, Conflict: result.Conflict}
	used := out.Size()
	if used > budget {
		return nil, torahops.ErrReadLimit
	}
	for _, claim := range result.Claims {
		if len(claim.Operation.Payload) > budget-used {
			return nil, torahops.ErrReadLimit
		}
		wire := pinkhaTorahClaimToWire(claim)
		used += wire.Size() + 16 // Conservative tag/length envelope bound.
		if used > budget {
			return nil, torahops.ErrReadLimit
		}
		out.Claims = append(out.Claims, wire)
	}
	return out, nil
}

func pinkhaTorahAppendToWire(result torahops.NativeAppendResult, err error) *pb.RpcPinkhaTorahOperationsAppendResponse {
	var receipt *pb.RpcPinkhaTorahOperationsAppendReceipt
	if result.Disposition != "" || result.ClaimID != "" || result.ChangeID != "" || result.Resolution.OperationID != "" {
		var resolution *pb.RpcPinkhaTorahOperationsResolution
		if err == nil {
			var resolutionErr error
			resolution, resolutionErr = pinkhaTorahResolutionToWire(result.Resolution, pinkhaTorahMaxReplyBytes-1024)
			err = errors.Join(err, resolutionErr)
		}
		receipt = &pb.RpcPinkhaTorahOperationsAppendReceipt{ClaimId: result.ClaimID, ChangeId: result.ChangeID, Resolution: resolution}
		switch result.Disposition {
		case torahops.Created:
			receipt.Disposition = pb.RpcPinkhaTorahOperations_CREATED
		case torahops.AlreadyExistsSamePayload:
			receipt.Disposition = pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD
		case torahops.CollisionDifferentPayload:
			receipt.Disposition = pb.RpcPinkhaTorahOperations_COLLISION_DIFFERENT_PAYLOAD
		default:
			err = errors.Join(err, errPinkhaTorahWireResult)
		}
		if result.ClaimID == "" || (result.Disposition == torahops.Created && result.ChangeID == "") ||
			(result.Disposition != torahops.Created && result.ChangeID != "") {
			err = errors.Join(err, errPinkhaTorahWireResult)
		}
		if err != nil {
			// A durable identity receipt is not renewed read authority. Keep its
			// metadata but never release cached private payloads after any failed
			// native authority/lifecycle/projection fence.
			receipt.Resolution = nil
		}
	} else if err == nil {
		err = errPinkhaTorahWireResult
	}
	code, description, issues := pinkhaTorahWireError(err, result.Disposition == torahops.CollisionDifferentPayload)
	out := &pb.RpcPinkhaTorahOperationsAppendResponse{ProtocolVersion: PinkhaTorahOperationsVersion, Receipt: receipt,
		Error: &pb.RpcPinkhaTorahOperationsAppendResponseError{
			Code: pb.RpcPinkhaTorahOperationsAppendResponseErrorCode(code), Description: description, Issues: issues}}
	if out.Size() > pinkhaTorahMaxReplyBytes {
		// The committed identity/disposition survives; an oversized resolution is
		// unavailable with an explicit error, never a partial list of variants.
		receipt.Resolution = nil
		code, description, issues = pinkhaTorahWireError(errors.Join(err, torahops.ErrReadLimit), result.Disposition == torahops.CollisionDifferentPayload)
		out.Error = &pb.RpcPinkhaTorahOperationsAppendResponseError{
			Code: pb.RpcPinkhaTorahOperationsAppendResponseErrorCode(code), Description: description, Issues: issues}
	}
	return out
}

func pinkhaTorahReadToWire(result torahops.NativeSnapshot, err error) *pb.RpcPinkhaTorahOperationsReadTargetResponse {
	if err == nil && len(result.Heads) == 0 {
		err = errPinkhaTorahWireResult
	}
	code, description, issues := pinkhaTorahWireError(err, false)
	out := &pb.RpcPinkhaTorahOperationsReadTargetResponse{ProtocolVersion: PinkhaTorahOperationsVersion,
		Error: &pb.RpcPinkhaTorahOperationsReadTargetResponseError{
			Code: pb.RpcPinkhaTorahOperationsReadTargetResponseErrorCode(code), Description: description, Issues: issues}}
	if err != nil {
		return out // Never release a cached snapshot after any failed native fence.
	}
	snapshot := &pb.RpcPinkhaTorahOperationsSnapshot{PendingObservedClaimIds: append([]string{}, result.Projection.PendingObserved...),
		VerifiedLocalHeads: append([]string{}, result.Heads...), LocalAppliedSeq: result.AppliedSeq,
		Scope: pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE}
	used := snapshot.Size() + 1024
	if used > pinkhaTorahMaxReplyBytes {
		return pinkhaTorahReadToWire(torahops.NativeSnapshot{}, torahops.ErrReadLimit)
	}
	for _, claim := range result.Projection.Live {
		if len(claim.Operation.Payload) > pinkhaTorahMaxReplyBytes-used {
			return pinkhaTorahReadToWire(torahops.NativeSnapshot{}, torahops.ErrReadLimit)
		}
		wire := pinkhaTorahClaimToWire(claim)
		used += wire.Size() + 16
		if used > pinkhaTorahMaxReplyBytes {
			return pinkhaTorahReadToWire(torahops.NativeSnapshot{}, torahops.ErrReadLimit)
		}
		snapshot.Live = append(snapshot.Live, wire)
	}
	for _, conflict := range result.Projection.Conflicts {
		wire, boundErr := pinkhaTorahResolutionToWire(conflict, pinkhaTorahMaxReplyBytes-used-16)
		if boundErr != nil {
			return pinkhaTorahReadToWire(torahops.NativeSnapshot{}, boundErr)
		}
		used += wire.Size() + 16
		snapshot.Conflicts = append(snapshot.Conflicts, wire)
	}
	out.Snapshot = snapshot
	if out.Size() > pinkhaTorahMaxReplyBytes {
		return pinkhaTorahReadToWire(torahops.NativeSnapshot{}, torahops.ErrReadLimit)
	}
	return out
}

var errPinkhaTorahWireResult = errors.New("invalid native Torah result")

type pinkhaTorahIssueSpec struct {
	issue  pb.RpcPinkhaTorahOperationsIssue
	code   int32
	label  string
	errors []error
}

// Primary-code priority is stable; every joined leaf issue is retained. Labels
// are constants, so native errors cannot leak payloads, identifiers or keys.
var pinkhaTorahIssueSpecs = []pinkhaTorahIssueSpec{
	{pb.RpcPinkhaTorahOperations_ISSUE_ACCOUNT_CHANGED, 6, "native account changed", []error{ErrPinkhaTorahAccountChanged}},
	{pb.RpcPinkhaTorahOperations_ISSUE_PERMISSION_DENIED, 4, "native permission denied", []error{list.ErrInsufficientPermissions, list.ErrNoReadKey}},
	{pb.RpcPinkhaTorahOperations_ISSUE_NOT_LOGGED_IN, 5, "native account unavailable", []error{ErrNotLoggedIn}},
	{pb.RpcPinkhaTorahOperations_ISSUE_UNSUPPORTED_VERSION, 3, "unsupported protocol version", []error{torahops.ErrUnsupportedVersion}},
	{pb.RpcPinkhaTorahOperations_ISSUE_BAD_INPUT, 2, "invalid native operation request", []error{torahops.ErrInvalid}},
	{pb.RpcPinkhaTorahOperations_ISSUE_TARGET_UNAVAILABLE, 7, "native target unavailable", []error{torahopsobject.ErrTargetUnavailable}},
	{pb.RpcPinkhaTorahOperations_ISSUE_HISTORY_UNAVAILABLE, 8, "local native history unavailable", []error{ErrPinkhaTorahHistoryUnavailable}},
	{pb.RpcPinkhaTorahOperations_ISSUE_PROJECTION_BEHIND, 9, "native projection recovery required", []error{torahops.ErrProjectionBehind}},
	{pb.RpcPinkhaTorahOperations_ISSUE_READ_LIMIT, 10, "native read bound exceeded", []error{torahops.ErrReadLimit}},
	{pb.RpcPinkhaTorahOperations_ISSUE_CANCELLED, 11, "native call cancelled", []error{context.Canceled}},
	{pb.RpcPinkhaTorahOperations_ISSUE_DEADLINE_EXCEEDED, 12, "native call deadline exceeded", []error{context.DeadlineExceeded}},
	{pb.RpcPinkhaTorahOperations_ISSUE_COLLISION, 13, "operation identity collision", nil},
	{pb.RpcPinkhaTorahOperations_ISSUE_INVALID_NATIVE_HISTORY, 1, "invalid private native history", []error{torahopscontract.ErrPrivateRoot, torahopscontract.ErrPrivateOperation}},
	{pb.RpcPinkhaTorahOperations_ISSUE_UNKNOWN_INTERNAL, 1, "native operation failed", nil},
}

func pinkhaTorahWireError(err error, collision bool) (int32, string, []pb.RpcPinkhaTorahOperationsIssue) {
	seen := map[pb.RpcPinkhaTorahOperationsIssue]bool{}
	var visit func(error, int)
	visit = func(current error, depth int) {
		if current == nil {
			return
		}
		if depth > 32 {
			seen[pb.RpcPinkhaTorahOperations_ISSUE_UNKNOWN_INTERNAL] = true
			return
		}
		if joined, ok := current.(interface{ Unwrap() []error }); ok {
			for _, child := range joined.Unwrap() {
				visit(child, depth+1)
			}
			return
		}
		if wrapped, ok := current.(interface{ Unwrap() error }); ok && wrapped.Unwrap() != nil {
			visit(wrapped.Unwrap(), depth+1)
			return
		}
		for _, spec := range pinkhaTorahIssueSpecs {
			for _, match := range spec.errors {
				if errors.Is(current, match) {
					seen[spec.issue] = true
					return
				}
			}
		}
		seen[pb.RpcPinkhaTorahOperations_ISSUE_UNKNOWN_INTERNAL] = true
	}
	visit(err, 0)
	if err != nil && len(seen) == 0 {
		seen[pb.RpcPinkhaTorahOperations_ISSUE_UNKNOWN_INTERNAL] = true
	}
	if collision {
		seen[pb.RpcPinkhaTorahOperations_ISSUE_COLLISION] = true
	}
	var issues []pb.RpcPinkhaTorahOperationsIssue
	var code int32
	var description string
	for _, spec := range pinkhaTorahIssueSpecs {
		if !seen[spec.issue] {
			continue
		}
		if len(issues) == 0 {
			code, description = spec.code, spec.label
		}
		issues = append(issues, spec.issue)
	}
	return code, description, issues
}
