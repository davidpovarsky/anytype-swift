package core

import (
	"context"
	"errors"
	"slices"
	"sort"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pb/cutoverpb"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
)

// Generated gRPC/gomobile entry points. All account, key, source, target, ACL,
// signed history and root authority remains in the native handlers.
func (mw *Middleware) PinkhaTorahCutoverSourceRead(ctx context.Context, req *cutoverpb.PinkhaTorahCutoverScope) *cutoverpb.PinkhaTorahCutoverSourceReadResponse {
	scope, err := pinkhaCutoverScopeFromWire(req)
	var result PinkhaTorahCutoverSourceSnapshot
	if err == nil {
		result, err = mw.NativeTorahCutoverSourceRead(ctx, scope)
	}
	return pinkhaCutoverSourceToWire(result, err)
}
func (mw *Middleware) PinkhaTorahCutoverRead(ctx context.Context, req *cutoverpb.PinkhaTorahCutoverScope) *cutoverpb.PinkhaTorahCutoverReadResponse {
	scope, err := pinkhaCutoverScopeFromWire(req)
	var result torahops.CutoverNativeSnapshot
	if err == nil {
		result, err = mw.NativeTorahCutoverRead(ctx, scope)
	}
	return pinkhaCutoverReadToWire(result, err)
}
func (mw *Middleware) PinkhaTorahCutoverAppend(ctx context.Context, req *cutoverpb.PinkhaTorahCutoverRecordRequest) *cutoverpb.PinkhaTorahCutoverAppendResponse {
	native, err := pinkhaCutoverRecordFromWire(req)
	var result torahops.CutoverNativeAppendResult
	if err == nil {
		result, err = mw.NativeTorahCutoverAppend(ctx, native)
	}
	return pinkhaCutoverAppendToWire(result, err)
}
func (mw *Middleware) PinkhaTorahCutoverImport(ctx context.Context, req *cutoverpb.PinkhaTorahCutoverOperationRequest) *cutoverpb.PinkhaTorahCutoverOperationResponse {
	return mw.pinkhaCutoverOperationWire(ctx, req, true)
}
func (mw *Middleware) PinkhaTorahCutoverAssociationAppend(ctx context.Context, req *cutoverpb.PinkhaTorahCutoverOperationRequest) *cutoverpb.PinkhaTorahCutoverOperationResponse {
	return mw.pinkhaCutoverOperationWire(ctx, req, false)
}
func (mw *Middleware) pinkhaCutoverOperationWire(ctx context.Context, req *cutoverpb.PinkhaTorahCutoverOperationRequest, importing bool) *cutoverpb.PinkhaTorahCutoverOperationResponse {
	native, err := pinkhaCutoverOperationFromWire(req)
	var result torahops.NativeAppendResult
	if err == nil {
		if importing {
			result, err = mw.NativeTorahCutoverImport(ctx, native)
		} else {
			result, err = mw.NativeTorahCutoverAssociationAppend(ctx, native)
		}
	}
	return pinkhaCutoverOperationToWire(result, err)
}

func pinkhaCutoverOperationToWire(result torahops.NativeAppendResult, err error) *cutoverpb.PinkhaTorahCutoverOperationResponse {
	// Reuse the unchanged v1 receipt mapper, including its durable identity
	// checks and refusal to release a private resolution on any native error.
	v1 := pinkhaTorahAppendToWire(result, err)
	if err == nil && v1.Error.Code != pb.RpcPinkhaTorahOperationsAppendResponseError_NULL {
		if v1.Error.Code == pb.RpcPinkhaTorahOperationsAppendResponseError_READ_LIMIT {
			err = torahops.ErrReadLimit
		} else if result.Disposition != torahops.CollisionDifferentPayload {
			err = errPinkhaTorahWireResult
		}
	}
	out := &cutoverpb.PinkhaTorahCutoverOperationResponse{ProtocolVersion: PinkhaTorahCutoverVersion,
		Receipt: v1.Receipt, Error: pinkhaCutoverWireError(err, result.Disposition == torahops.CollisionDifferentPayload)}
	if out.Size() > pinkhaTorahMaxReplyBytes {
		if out.Receipt != nil {
			out.Receipt.Resolution = nil
		}
		out.Error = pinkhaCutoverWireError(errors.Join(err, torahops.ErrReadLimit), result.Disposition == torahops.CollisionDifferentPayload)
	}
	return out
}

func pinkhaCutoverScopeFromWire(req *cutoverpb.PinkhaTorahCutoverScope) (PinkhaTorahCutoverReadRequest, error) {
	if req == nil {
		return PinkhaTorahCutoverReadRequest{}, cutover.ErrInvalid
	}
	if req.ProtocolVersion != PinkhaTorahCutoverVersion {
		return PinkhaTorahCutoverReadRequest{}, torahops.ErrUnsupportedVersion
	}
	if req.Size() > 4096 || !pinkhaTorahText(req.SpaceId, true) || !pinkhaTorahText(req.ObjectId, true) || !pinkhaTorahText(req.PropertyKey, true) {
		return PinkhaTorahCutoverReadRequest{}, cutover.ErrInvalid
	}
	return PinkhaTorahCutoverReadRequest{Version: req.ProtocolVersion, SpaceID: req.SpaceId, ObjectID: req.ObjectId, PropertyKey: req.PropertyKey}, nil
}
func pinkhaCutoverKindFromWire(kind cutoverpb.PinkhaTorahCutoverKind) (cutover.Kind, error) {
	switch kind {
	case cutoverpb.PinkhaTorahCutover_BEGIN:
		return cutover.Begin, nil
	case cutoverpb.PinkhaTorahCutover_IMPORT:
		return cutover.Import, nil
	case cutoverpb.PinkhaTorahCutover_SEAL:
		return cutover.Seal, nil
	default:
		return "", cutover.ErrInvalid
	}
}
func pinkhaCutoverKindToWire(kind cutover.Kind) cutoverpb.PinkhaTorahCutoverKind {
	switch kind {
	case cutover.Begin:
		return cutoverpb.PinkhaTorahCutover_BEGIN
	case cutover.Import:
		return cutoverpb.PinkhaTorahCutover_IMPORT
	case cutover.Seal:
		return cutoverpb.PinkhaTorahCutover_SEAL
	default:
		return cutoverpb.PinkhaTorahCutover_KIND_UNSPECIFIED
	}
}
func pinkhaCutoverPlanFromWire(plan *cutoverpb.PinkhaTorahCutoverPlan) (*cutover.Plan, error) {
	if plan == nil {
		return nil, nil
	}
	if len(plan.Facts) > cutover.MaxFacts || plan.Size() > pinkhaTorahMaxReplyBytes {
		return nil, cutover.ErrInvalid
	}
	out := &cutover.Plan{Version: plan.Version, SpaceID: plan.SpaceId, ObjectID: plan.ObjectId, PropertyKey: plan.PropertyKey,
		ValuePresent: plan.ValuePresent, LegacyValue: slices.Clone(plan.LegacyValue), Facts: make([]cutover.Fact, 0, len(plan.Facts))}
	for _, fact := range plan.Facts {
		if fact == nil {
			return nil, cutover.ErrInvalid
		}
		out.Facts = append(out.Facts, cutover.Fact{BlockID: fact.BlockId, ProviderID: fact.ProviderId,
			CanonicalRef: fact.CanonicalRef, Payload: slices.Clone(fact.Payload)})
	}
	if _, err := out.CanonicalBytes(); err != nil {
		return nil, err
	}
	return out, nil
}
func pinkhaCutoverRecordFromWire(req *cutoverpb.PinkhaTorahCutoverRecordRequest) (PinkhaTorahCutoverRecordRequest, error) {
	if req == nil || req.Size() > pinkhaTorahMaxReplyBytes || len(req.Imported) > cutover.MaxBindings ||
		len(req.SourceHeads) > cutover.MaxSourceHeads || len(req.NativeChanges) > cutover.MaxNativeReceipts ||
		len(req.ImportRecords) > cutover.MaxBindings {
		return PinkhaTorahCutoverRecordRequest{}, cutover.ErrInvalid
	}
	scope, err := pinkhaCutoverScopeFromWire(req.Scope)
	if err != nil {
		return PinkhaTorahCutoverRecordRequest{}, err
	}
	kind, err := pinkhaCutoverKindFromWire(req.Kind)
	if err != nil {
		return PinkhaTorahCutoverRecordRequest{}, err
	}
	plan, err := pinkhaCutoverPlanFromWire(req.Plan)
	if err != nil {
		return PinkhaTorahCutoverRecordRequest{}, err
	}
	out := PinkhaTorahCutoverRecordRequest{PinkhaTorahCutoverReadRequest: scope, RecordID: req.RecordId,
		Kind: kind, PlanID: req.PlanId, Plan: plan, FactID: req.FactId, ImportClaimID: req.ImportClaimId,
		SourceHeads: slices.Clone(req.SourceHeads), ImportRecords: slices.Clone(req.ImportRecords)}
	for _, binding := range req.Imported {
		if binding == nil {
			return PinkhaTorahCutoverRecordRequest{}, cutover.ErrInvalid
		}
		out.Imported = append(out.Imported, cutover.Binding{FactID: binding.FactId, ClaimID: binding.ClaimId})
	}
	for _, witness := range req.NativeChanges {
		if witness == nil {
			return PinkhaTorahCutoverRecordRequest{}, cutover.ErrInvalid
		}
		out.NativeChanges = append(out.NativeChanges, cutover.NativeWitness{ChangeID: witness.ChangeId, Creator: witness.Creator, ACLHeadID: witness.AclHeadId})
	}
	return out, nil
}
func pinkhaCutoverOperationFromWire(req *cutoverpb.PinkhaTorahCutoverOperationRequest) (PinkhaTorahCutoverOperationRequest, error) {
	if req == nil || req.Size() > torahops.MaxWireBytes {
		return PinkhaTorahCutoverOperationRequest{}, cutover.ErrInvalid
	}
	scope, err := pinkhaCutoverScopeFromWire(req.Scope)
	if err != nil {
		return PinkhaTorahCutoverOperationRequest{}, err
	}
	kind, err := pinkhaTorahKindFromWire(req.Kind)
	if err != nil {
		return PinkhaTorahCutoverOperationRequest{}, err
	}
	source := torahops.Source{}
	if req.Source != nil {
		source = torahops.Source{ProviderID: req.Source.ProviderId, CanonicalRef: req.Source.CanonicalRef}
	}
	return PinkhaTorahCutoverOperationRequest{PinkhaTorahCutoverReadRequest: scope, PlanID: req.PlanId,
		FactID: req.FactId, OperationID: req.OperationId, Kind: kind, BlockID: req.BlockId, Source: source,
		Payload: slices.Clone(req.Payload), Observed: slices.Clone(req.ObservedClaimIds)}, nil
}

func pinkhaCutoverSourceValue(value torahops.CutoverLegacyValue) *cutoverpb.PinkhaTorahCutoverSourceValue {
	return &cutoverpb.PinkhaTorahCutoverSourceValue{Key: value.Key, Present: value.Present, Value: slices.Clone(value.Bytes)}
}
func pinkhaCutoverPlanToWire(plan *cutover.Plan) *cutoverpb.PinkhaTorahCutoverPlan {
	if plan == nil {
		return nil
	}
	out := &cutoverpb.PinkhaTorahCutoverPlan{Version: plan.Version, SpaceId: plan.SpaceID, ObjectId: plan.ObjectID,
		PropertyKey: plan.PropertyKey, ValuePresent: plan.ValuePresent, LegacyValue: slices.Clone(plan.LegacyValue)}
	for _, fact := range plan.Facts {
		out.Facts = append(out.Facts, &cutoverpb.PinkhaTorahCutoverFact{BlockId: fact.BlockID, ProviderId: fact.ProviderID,
			CanonicalRef: fact.CanonicalRef, Payload: slices.Clone(fact.Payload)})
	}
	return out
}
func pinkhaCutoverClaimToWire(claim cutover.Claim) *cutoverpb.PinkhaTorahCutoverMetadataClaim {
	record := claim.Record
	out := &cutoverpb.PinkhaTorahCutoverRecord{Version: record.Version, SpaceId: record.SpaceID, ObjectId: record.ObjectID,
		RecordId: record.RecordID, AuthorId: record.AuthorID, Kind: pinkhaCutoverKindToWire(record.Kind), PlanId: record.PlanID,
		Plan: pinkhaCutoverPlanToWire(record.Plan), FactId: record.FactID, ImportClaimId: record.ImportClaimID,
		SourceHeads: slices.Clone(record.SourceHeads), ImportRecords: slices.Clone(record.ImportRecords)}
	for _, binding := range record.Imported {
		out.Imported = append(out.Imported, &cutoverpb.PinkhaTorahCutoverBinding{FactId: binding.FactID, ClaimId: binding.ClaimID})
	}
	for _, witness := range record.NativeChanges {
		out.NativeChanges = append(out.NativeChanges, &cutoverpb.PinkhaTorahCutoverNativeWitness{ChangeId: witness.ChangeID, Creator: witness.Creator, AclHeadId: witness.ACLHeadID})
	}
	return &cutoverpb.PinkhaTorahCutoverMetadataClaim{ClaimId: claim.ID, Digest: claim.Digest, Record: out}
}
func pinkhaCutoverResolutionToWire(result torahops.CutoverResolution, budget int) (*cutoverpb.PinkhaTorahCutoverMetadataResolution, error) {
	out := &cutoverpb.PinkhaTorahCutoverMetadataResolution{RecordId: result.RecordID, Conflict: result.Conflict}
	used := out.Size()
	if used > budget {
		return nil, torahops.ErrReadLimit
	}
	for _, claim := range result.Claims {
		wire := pinkhaCutoverClaimToWire(claim)
		used += wire.Size() + 16
		if used > budget {
			return nil, torahops.ErrReadLimit
		}
		out.Claims = append(out.Claims, wire)
	}
	return out, nil
}
func pinkhaCutoverStateToWire(state torahops.CutoverState) (*cutoverpb.PinkhaTorahCutoverState, error) {
	status := cutoverpb.PinkhaTorahCutover_STATUS_UNSPECIFIED
	switch state.Status {
	case torahops.CutoverLegacy:
		status = cutoverpb.PinkhaTorahCutover_LEGACY
	case torahops.CutoverPending:
		status = cutoverpb.PinkhaTorahCutover_PENDING
	case torahops.CutoverSealed:
		status = cutoverpb.PinkhaTorahCutover_SEALED
	case torahops.CutoverDiverged:
		status = cutoverpb.PinkhaTorahCutover_DIVERGED
	case torahops.CutoverConflicted:
		status = cutoverpb.PinkhaTorahCutover_CONFLICTED
	default:
		return nil, errPinkhaTorahWireResult
	}
	out := &cutoverpb.PinkhaTorahCutoverState{Status: status, PlanId: state.PlanID, Plan: pinkhaCutoverPlanToWire(state.Plan), Seals: slices.Clone(state.Seals)}
	for _, item := range state.Imports {
		out.Imports = append(out.Imports, &cutoverpb.PinkhaTorahCutoverImportBinding{FactId: item.FactID, ClaimId: item.ClaimID, MetadataClaimIds: slices.Clone(item.MetadataClaims)})
	}
	for _, issue := range state.Pending {
		out.Pending = append(out.Pending, &cutoverpb.PinkhaTorahCutoverIssue{Reason: issue.Reason, Reference: issue.Reference})
	}
	for _, issue := range state.Conflicts {
		out.Conflicts = append(out.Conflicts, &cutoverpb.PinkhaTorahCutoverIssue{Reason: issue.Reason, Reference: issue.Reference})
	}
	return out, nil
}
func pinkhaCutoverSourceToWire(result PinkhaTorahCutoverSourceSnapshot, err error) *cutoverpb.PinkhaTorahCutoverSourceReadResponse {
	out := &cutoverpb.PinkhaTorahCutoverSourceReadResponse{ProtocolVersion: PinkhaTorahCutoverVersion}
	if err == nil && (len(result.SourceHeads) == 0 || !pinkhaTorahText(result.Source.Key, true) ||
		(!result.Source.Present && len(result.Source.Bytes) != 0) || len(result.Source.Bytes) > cutover.MaxLegacyBytes) {
		err = errPinkhaTorahWireResult
	}
	if err == nil {
		out.Snapshot = &cutoverpb.PinkhaTorahCutoverSourceSnapshot{Source: pinkhaCutoverSourceValue(result.Source), SourceHeads: slices.Clone(result.SourceHeads)}
		if out.Size() > pinkhaTorahMaxReplyBytes {
			out.Snapshot = nil
			err = torahops.ErrReadLimit
		}
	}
	out.Error = pinkhaCutoverWireError(err, false)
	return out
}
func pinkhaCutoverReadToWire(result torahops.CutoverNativeSnapshot, err error) *cutoverpb.PinkhaTorahCutoverReadResponse {
	out := &cutoverpb.PinkhaTorahCutoverReadResponse{ProtocolVersion: PinkhaTorahCutoverVersion}
	if err == nil && (len(result.SourceHeads) == 0 || len(result.MetadataHeads) == 0 || len(result.OperationHeads) == 0) {
		err = errPinkhaTorahWireResult
	}
	if err == nil {
		out.Snapshot, err = pinkhaCutoverSnapshotToWire(result)
	}
	if err != nil {
		out.Snapshot = nil
	}
	out.Error = pinkhaCutoverWireError(err, false)
	if out.Size() > pinkhaTorahMaxReplyBytes {
		out.Snapshot = nil
		out.Error = pinkhaCutoverWireError(torahops.ErrReadLimit, false)
	}
	return out
}
func pinkhaCutoverSnapshotToWire(result torahops.CutoverNativeSnapshot) (*cutoverpb.PinkhaTorahCutoverSnapshot, error) {
	state, err := pinkhaCutoverStateToWire(result.State)
	if err != nil {
		return nil, err
	}
	out := &cutoverpb.PinkhaTorahCutoverSnapshot{State: state, Source: pinkhaCutoverSourceValue(result.Source),
		SourceHeads: slices.Clone(result.SourceHeads), MetadataHeads: slices.Clone(result.MetadataHeads), OperationHeads: slices.Clone(result.OperationHeads),
		MetadataAppliedSeq: result.MetadataAppliedSeq, OperationAppliedSeq: result.OperationAppliedSeq, CompleteLocal: true}
	used := out.Size() + 1024
	take := func(n int) error {
		used += n + 16
		if used > pinkhaTorahMaxReplyBytes {
			return torahops.ErrReadLimit
		}
		return nil
	}
	if used > pinkhaTorahMaxReplyBytes {
		return nil, torahops.ErrReadLimit
	}
	for _, claim := range result.MetadataHistory.Claims {
		wire := pinkhaCutoverClaimToWire(claim)
		if err = take(wire.Size()); err != nil {
			return nil, err
		}
		out.MetadataClaims = append(out.MetadataClaims, wire)
	}
	for _, resolution := range result.MetadataHistory.Conflicts {
		wire, e := pinkhaCutoverResolutionToWire(resolution, pinkhaTorahMaxReplyBytes-used-16)
		if e != nil {
			return nil, e
		}
		if err = take(wire.Size()); err != nil {
			return nil, err
		}
		out.MetadataConflicts = append(out.MetadataConflicts, wire)
	}
	for _, claim := range result.OriginalClaims {
		wire := pinkhaTorahClaimToWire(claim)
		if err = take(wire.Size()); err != nil {
			return nil, err
		}
		out.OriginalClaims = append(out.OriginalClaims, wire)
	}
	receipts := func(input map[string][]torahops.Receipt) ([]*cutoverpb.PinkhaTorahCutoverNativeReceipt, error) {
		keys := make([]string, 0, len(input))
		for key := range input {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		var output []*cutoverpb.PinkhaTorahCutoverNativeReceipt
		for _, key := range keys {
			rows := slices.Clone(input[key])
			sort.Slice(rows, func(i, j int) bool { return rows[i].ID < rows[j].ID })
			for _, receipt := range rows {
				if receipt.ClaimID != key {
					return nil, errPinkhaTorahWireResult
				}
				wire := &cutoverpb.PinkhaTorahCutoverNativeReceipt{Id: receipt.ID, ClaimId: receipt.ClaimID, ChangeId: receipt.ChangeID, Creator: receipt.Creator, AclHeadId: receipt.ACLHeadID}
				if e := take(wire.Size()); e != nil {
					return nil, e
				}
				output = append(output, wire)
			}
		}
		return output, nil
	}
	if out.MetadataReceipts, err = receipts(result.MetadataReceipts); err != nil {
		return nil, err
	}
	if out.OriginalReceipts, err = receipts(result.OriginalReceipts); err != nil {
		return nil, err
	}
	return out, nil
}
func pinkhaCutoverAppendToWire(result torahops.CutoverNativeAppendResult, err error) *cutoverpb.PinkhaTorahCutoverAppendResponse {
	out := &cutoverpb.PinkhaTorahCutoverAppendResponse{ProtocolVersion: PinkhaTorahCutoverVersion}
	if result.Disposition != "" || result.ClaimID != "" || result.ChangeID != "" || result.Resolution.RecordID != "" {
		disposition := pb.RpcPinkhaTorahOperations_DISPOSITION_UNSPECIFIED
		switch result.Disposition {
		case torahops.Created:
			disposition = pb.RpcPinkhaTorahOperations_CREATED
		case torahops.AlreadyExistsSamePayload:
			disposition = pb.RpcPinkhaTorahOperations_ALREADY_EXISTS_SAME_PAYLOAD
		case torahops.CollisionDifferentPayload:
			disposition = pb.RpcPinkhaTorahOperations_COLLISION_DIFFERENT_PAYLOAD
		}
		if disposition == pb.RpcPinkhaTorahOperations_DISPOSITION_UNSPECIFIED || !cutover.ClaimID(result.ClaimID) ||
			(result.Disposition == torahops.Created && !pinkhaTorahText(result.ChangeID, true)) ||
			(result.Disposition != torahops.Created && result.ChangeID != "") {
			err = errors.Join(err, errPinkhaTorahWireResult)
		} else {
			out.Receipt = &cutoverpb.PinkhaTorahCutoverAppendReceipt{Disposition: disposition, ClaimId: result.ClaimID, ChangeId: result.ChangeID}
			if err == nil {
				var e error
				out.Receipt.Resolution, e = pinkhaCutoverResolutionToWire(result.Resolution, pinkhaTorahMaxReplyBytes-1024)
				err = errors.Join(err, e)
			}
		}
	} else if err == nil {
		err = errPinkhaTorahWireResult
	}
	if err != nil && out.Receipt != nil {
		out.Receipt.Resolution = nil
	}
	out.Error = pinkhaCutoverWireError(err, result.Disposition == torahops.CollisionDifferentPayload)
	if out.Size() > pinkhaTorahMaxReplyBytes {
		if out.Receipt != nil {
			out.Receipt.Resolution = nil
		}
		out.Error = pinkhaCutoverWireError(errors.Join(err, torahops.ErrReadLimit), result.Disposition == torahops.CollisionDifferentPayload)
	}
	return out
}

type pinkhaCutoverIssueSpec struct {
	code    cutoverpb.PinkhaTorahCutoverErrorCode
	label   string
	matches []error
}

var pinkhaCutoverIssueSpecs = []pinkhaCutoverIssueSpec{
	{cutoverpb.PinkhaTorahCutoverError_ACCOUNT_CHANGED, "native account changed", []error{ErrPinkhaTorahAccountChanged}},
	{cutoverpb.PinkhaTorahCutoverError_PERMISSION_DENIED, "native permission denied", []error{list.ErrInsufficientPermissions, list.ErrNoReadKey}},
	{cutoverpb.PinkhaTorahCutoverError_NOT_LOGGED_IN, "native account unavailable", []error{ErrNotLoggedIn}},
	{cutoverpb.PinkhaTorahCutoverError_UNSUPPORTED_VERSION, "unsupported cutover protocol version", []error{torahops.ErrUnsupportedVersion}},
	{cutoverpb.PinkhaTorahCutoverError_BAD_INPUT, "invalid cutover request", []error{cutover.ErrInvalid, torahops.ErrInvalid}},
	{cutoverpb.PinkhaTorahCutoverError_LEGACY_CHANGED, "retained legacy source changed", []error{cutover.ErrLegacyChanged}},
	{cutoverpb.PinkhaTorahCutoverError_INCOMPLETE, "native cutover history incomplete", []error{cutover.ErrIncomplete}},
	{cutoverpb.PinkhaTorahCutoverError_ALREADY_SEALED, "native cutover already sealed", []error{cutover.ErrAlreadySealed}},
	{cutoverpb.PinkhaTorahCutoverError_COLLISION, "native cutover identity conflict", []error{cutover.ErrConflict}},
	{cutoverpb.PinkhaTorahCutoverError_TARGET_STATE_UNAVAILABLE, "native target unavailable", []error{torahopsobject.ErrTargetUnavailable}},
	{cutoverpb.PinkhaTorahCutoverError_HISTORY_UNAVAILABLE, "local native history unavailable", []error{ErrPinkhaTorahHistoryUnavailable}},
	{cutoverpb.PinkhaTorahCutoverError_PROJECTION_BEHIND, "native projection recovery required", []error{torahops.ErrProjectionBehind}},
	{cutoverpb.PinkhaTorahCutoverError_READ_LIMIT, "native cutover wire bound exceeded", []error{torahops.ErrReadLimit}},
	{cutoverpb.PinkhaTorahCutoverError_CANCELLED, "native call cancelled", []error{context.Canceled}},
	{cutoverpb.PinkhaTorahCutoverError_DEADLINE_EXCEEDED, "native call deadline exceeded", []error{context.DeadlineExceeded}},
	{cutoverpb.PinkhaTorahCutoverError_UNKNOWN_ERROR, "native cutover failed", nil},
}

func pinkhaCutoverWireError(err error, collision bool) *cutoverpb.PinkhaTorahCutoverError {
	seen := map[cutoverpb.PinkhaTorahCutoverErrorCode]bool{}
	var visit func(error, int)
	visit = func(current error, depth int) {
		if current == nil {
			return
		}
		if depth > 32 {
			seen[cutoverpb.PinkhaTorahCutoverError_UNKNOWN_ERROR] = true
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
		for _, spec := range pinkhaCutoverIssueSpecs {
			for _, match := range spec.matches {
				if errors.Is(current, match) {
					seen[spec.code] = true
					return
				}
			}
		}
		seen[cutoverpb.PinkhaTorahCutoverError_UNKNOWN_ERROR] = true
	}
	visit(err, 0)
	if err != nil && len(seen) == 0 {
		seen[cutoverpb.PinkhaTorahCutoverError_UNKNOWN_ERROR] = true
	}
	if collision {
		seen[cutoverpb.PinkhaTorahCutoverError_COLLISION] = true
	}
	out := &cutoverpb.PinkhaTorahCutoverError{}
	for _, spec := range pinkhaCutoverIssueSpecs {
		if !seen[spec.code] {
			continue
		}
		if len(out.Issues) == 0 {
			out.Code = spec.code
			out.Description = spec.label
		}
		out.Issues = append(out.Issues, spec.code)
	}
	return out
}
