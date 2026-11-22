package core

import (
	"context"
	"encoding/hex"
	"errors"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/core/block/editor/torahopsobject"
	"github.com/anyproto/anytype-heart/pb"
)

// The generated gomobile and gRPC entry points share this same typed native
// handler. Account, targets and current authority remain entirely native-owned.
func (mw *Middleware) PinkhaTorahAuthorizedOperationRead(ctx context.Context, req *pb.PinkhaTorahAuthorizedOperationReadRequest) *pb.PinkhaTorahAuthorizedOperationReadResponse {
	if req == nil {
		return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, torahops.ErrInvalid)
	}
	if req.ProtocolVersion != torahops.AuthorizedOperationReadVersion {
		return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, torahops.ErrUnsupportedVersion)
	}
	if req.Size() > 2048 {
		return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, torahops.ErrInvalid)
	}
	prepared, err := mw.preparePinkhaAuthorizedOperationRead(ctx, PinkhaTorahAuthorizedOperationReadRequest{
		Version: req.ProtocolVersion, SpaceID: req.SpaceId, OperationID: req.OperationId,
	})
	if err != nil {
		return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, err)
	}
	return prepared.wire(ctx)
}

func pinkhaAuthorizedOperationReadError(err error) *pb.PinkhaTorahAuthorizedOperationReadResponseError {
	type code = pb.PinkhaTorahAuthorizedOperationReadResponseErrorCode
	value, label := code(0), ""
	// Stable priority. Every failure returns zero payload; error descriptions are
	// fixed labels and never the native error string.
	switch {
	case err == nil:
	case errors.Is(err, ErrPinkhaTorahAccountChanged):
		value, label = 6, "native account changed"
	case errors.Is(err, list.ErrInsufficientPermissions), errors.Is(err, list.ErrNoReadKey):
		value, label = 4, "native permission denied"
	case errors.Is(err, ErrNotLoggedIn):
		value, label = 5, "native account unavailable"
	case errors.Is(err, torahops.ErrUnsupportedVersion):
		value, label = 3, "unsupported read contract"
	case errors.Is(err, torahops.ErrInvalid):
		value, label = 2, "invalid native operation read"
	case errors.Is(err, torahops.ErrOperationTargetUnavailable), errors.Is(err, torahopsobject.ErrTargetUnavailable):
		value, label = 7, "native target authority unavailable"
	case errors.Is(err, ErrPinkhaTorahHistoryUnavailable):
		value, label = 8, "local native history unavailable"
	case errors.Is(err, torahops.ErrOperationSnapshotChanged):
		value, label = 9, "native candidate closure changed"
	case errors.Is(err, torahops.ErrProjectionBehind):
		value, label = 10, "native projection recovery required"
	case errors.Is(err, torahops.ErrReadLimit):
		value, label = 11, "native read bound exceeded"
	case errors.Is(err, context.Canceled):
		value, label = 12, "native call cancelled"
	case errors.Is(err, context.DeadlineExceeded):
		value, label = 13, "native call deadline exceeded"
	default:
		value, label = 1, "native operation read failed"
	}
	return &pb.PinkhaTorahAuthorizedOperationReadResponseError{Code: value, Description: label}
}

func pinkhaAuthorizedOperationReadToWire(value torahops.AuthorizedOperationSnapshot, err error) *pb.PinkhaTorahAuthorizedOperationReadResponse {
	out := &pb.PinkhaTorahAuthorizedOperationReadResponse{
		ProtocolVersion: torahops.AuthorizedOperationReadVersion, Error: pinkhaAuthorizedOperationReadError(err),
	}
	if err != nil {
		return out
	}
	invalid := func() *pb.PinkhaTorahAuthorizedOperationReadResponse {
		return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, torahops.ErrInvalid)
	}
	if value.Contract != torahops.AuthorizedOperationReadContract || !value.Complete ||
		!pinkhaTorahText(value.AccountID, true) || !pinkhaTorahText(value.SpaceID, true) || len(value.NativeSnapshotToken) != 64 ||
		validatePinkhaTorahOperationRead(context.Background(), PinkhaTorahAuthorizedOperationReadRequest{
			Version: torahops.AuthorizedOperationReadVersion, SpaceID: value.SpaceID, OperationID: value.OperationID,
		}) != nil {
		return invalid()
	}
	if decoded, decodeErr := hex.DecodeString(value.NativeSnapshotToken); decodeErr != nil || len(decoded) != 32 || hex.EncodeToString(decoded) != value.NativeSnapshotToken {
		return invalid()
	}
	if len(value.Variants) > torahops.MaxVariants {
		return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, torahops.ErrReadLimit)
	}
	snapshot := &pb.PinkhaTorahAuthorizedOperationReadSnapshot{
		Contract: value.Contract, AccountId: value.AccountID, SpaceId: value.SpaceID, OperationId: value.OperationID,
		Complete: value.Complete, NativeSnapshotToken: value.NativeSnapshotToken,
	}
	switch value.Outcome {
	case torahops.OperationFound:
		if len(value.Variants) == 0 {
			return invalid()
		}
		snapshot.Outcome = pb.PinkhaTorahAuthorizedOperationRead_FOUND
	case torahops.OperationAbsentInVerifiedLocalSnapshot:
		if len(value.Variants) != 0 {
			return invalid()
		}
		snapshot.Outcome = pb.PinkhaTorahAuthorizedOperationRead_ABSENT_IN_VERIFIED_LOCAL_SNAPSHOT
	default:
		return invalid()
	}
	used := snapshot.Size() + 64
	previousID := ""
	for _, variant := range value.Variants {
		if variant.ClaimID <= previousID || variant.SpaceID != value.SpaceID || variant.OperationID != value.OperationID ||
			len(variant.CanonicalBytes) == 0 || len(variant.Provenance) == 0 {
			return invalid()
		}
		previousID = variant.ClaimID
		if len(variant.CanonicalBytes) > torahops.MaxAuthorizedOperationReadBytes-used {
			return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, torahops.ErrReadLimit)
		}
		wire := &pb.PinkhaTorahAuthorizedOperationReadVariant{
			ClaimId: variant.ClaimID, OperationId: variant.OperationID, SpaceId: variant.SpaceID, AuthorId: variant.AuthorID,
			Target:         &pb.PinkhaTorahAuthorizedOperationReadTarget{ObjectId: variant.Target.ObjectID, BlockId: variant.Target.BlockID},
			CanonicalBytes: append([]byte{}, variant.CanonicalBytes...),
		}
		switch variant.Reachability {
		case torahops.OperationLiveDocument:
			if variant.Target.BlockID != "" {
				return invalid()
			}
			wire.Reachability = pb.PinkhaTorahAuthorizedOperationRead_LIVE_DOCUMENT
		case torahops.OperationLiveBlock:
			if variant.Target.BlockID == "" {
				return invalid()
			}
			wire.Reachability = pb.PinkhaTorahAuthorizedOperationRead_LIVE_BLOCK
		case torahops.OperationUnreachableBlock:
			if variant.Target.BlockID == "" {
				return invalid()
			}
			wire.Reachability = pb.PinkhaTorahAuthorizedOperationRead_UNREACHABLE_BLOCK
		default:
			return invalid()
		}
		for _, provenance := range variant.Provenance {
			if provenance.Creator != variant.AuthorID || !pinkhaTorahText(provenance.Creator, true) ||
				!pinkhaTorahText(provenance.NativeChangeID, true) || !pinkhaTorahText(provenance.NativeACLHeadID, true) {
				return invalid()
			}
			wire.Provenance = append(wire.Provenance, &pb.PinkhaTorahAuthorizedOperationReadProvenance{
				Creator: provenance.Creator, NativeChangeId: provenance.NativeChangeID, NativeAclHeadId: provenance.NativeACLHeadID,
			})
		}
		used += wire.Size() + 16
		if used > torahops.MaxAuthorizedOperationReadBytes {
			return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, torahops.ErrReadLimit)
		}
		snapshot.Variants = append(snapshot.Variants, wire)
	}
	out.Snapshot = snapshot
	if out.Size() > torahops.MaxAuthorizedOperationReadBytes {
		return pinkhaAuthorizedOperationReadToWire(torahops.AuthorizedOperationSnapshot{}, torahops.ErrReadLimit)
	}
	return out
}
