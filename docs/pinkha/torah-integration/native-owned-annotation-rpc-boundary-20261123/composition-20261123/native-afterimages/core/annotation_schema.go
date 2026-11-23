package core

import (
	"context"
	"errors"
	"slices"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"

	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/restriction"
	"github.com/anyproto/anytype-heart/core/pinkha/annotationschema"
	"github.com/anyproto/anytype-heart/pb"
)

// AnnotationSchemaRegister is reached through the original generated service
// command route. Expected IDs are comparisons, never caller-minted authority.
// Register itself retains the actual original application and revalidates the
// original account/Space/ACL at its native mutation boundaries.
func (mw *Middleware) AnnotationSchemaRegister(ctx context.Context, req *pb.RpcAnnotationSchemaRegisterRequest) *pb.RpcAnnotationSchemaRegisterResponse {
	response := &pb.RpcAnnotationSchemaRegisterResponse{
		Error: &pb.RpcAnnotationSchemaRegisterResponseError{},
	}
	if req == nil || req.ExpectedAccountId == "" || req.SpaceId == "" || req.SchemaProtocol != annotationschema.Protocol {
		response.Error.Code = pb.RpcAnnotationSchemaRegisterResponseError_BAD_INPUT
		response.Error.Description = "invalid original annotation schema registration request"
		return response
	}
	if mw == nil || mw.applicationService == nil {
		response.Error.Code = pb.RpcAnnotationSchemaRegisterResponseError_RUNTIME_UNAVAILABLE
		response.Error.Description = annotationschema.ErrUnqualifiedRuntime.Error()
		return response
	}

	// No doBlockService/mustService/GetApp wrapper runs inside the admitted
	// callback. The actual original application service goes directly to the
	// existing bounded registrar. There is no new write or retry here.
	actual, err := annotationschema.Register(ctx, mw.applicationService, req.ExpectedAccountId, req.SpaceId)
	response.Registration = copyAnnotationSchemaRegistration(actual)
	if err != nil {
		response.Error.Code = annotationSchemaRegistrationErrorCode(err)
		response.Error.Description = getErrorDescription(err)
	}
	return response
}

// Copyout occurs even for a non-NULL error. AppAdmitted and Invoked are phase
// facts only; no atomic batch, rollback, durable body or current lease is claimed.
func copyAnnotationSchemaRegistration(actual annotationschema.Registration) *pb.RpcAnnotationSchemaRegistration {
	result := &pb.RpcAnnotationSchemaRegistration{
		SchemaProtocol:    annotationschema.Protocol,
		Observation:       copyAnnotationSchemaObservation(actual.Observation),
		AppAdmitted:       actual.AppAdmitted,
		TypeApplyInvoked:  actual.TypeApplyInvoked,
		TypeApplyReturned: actual.TypeApplyReturned,
	}
	for _, creation := range actual.Creations {
		result.Creations = append(result.Creations, &pb.RpcAnnotationSchemaCreation{
			Before:           copyAnnotationSchemaNativeObservation(creation.Before),
			After:            copyAnnotationSchemaNativeObservation(creation.After),
			Invoked:          creation.Invoked,
			ReturnedObjectId: creation.ReturnedObjectID,
		})
	}
	return result
}

func copyAnnotationSchemaObservation(actual annotationschema.Observation) *pb.RpcAnnotationSchemaObservation {
	layout := actual.TypeLayout
	result := &pb.RpcAnnotationSchemaObservation{
		Disposition:     string(actual.Disposition),
		AccountIdentity: actual.AccountIdentity,
		SpaceId:         actual.SpaceID,
		TypeLayout: &pb.RpcAnnotationSchemaTypeLayoutObservation{
			Disposition:         string(layout.Disposition),
			Reason:              layout.Reason,
			Hidden:              layout.Hidden,
			DiscoveryHidden:     layout.DiscoveryHidden,
			HiddenRelationIds:   slices.Clone(layout.HiddenRelationIDs),
			MissingRelationKeys: slices.Clone(layout.MissingRelationKeys),
			ViewIds:             slices.Clone(layout.ViewIDs),
		},
	}
	for _, definition := range actual.Definitions {
		result.Definitions = append(result.Definitions, &pb.RpcAnnotationSchemaDefinitionObservation{
			Native:                 copyAnnotationSchemaNativeObservation(definition.Native),
			IndexDisposition:       string(definition.Index),
			PersistedStateConflict: definition.PersistedStateConflict,
		})
	}
	return result
}

func copyAnnotationSchemaNativeObservation(actual objectcreator.FixedSchemaObservation) *pb.RpcAnnotationSchemaNativeObservation {
	details, blocks := actual.CopyPersistedSchemaState()
	result := &pb.RpcAnnotationSchemaNativeObservation{
		Disposition:     uint32(actual.Disposition),
		AccountIdentity: actual.AccountIdentity,
		SpaceId:         actual.SpaceID,
		ObjectId:        actual.ObjectID,
		PersistedHeads:  slices.Clone(actual.PersistedHeads),
		ArchiveId:       actual.ArchiveID,
		ArchiveHeads:    slices.Clone(actual.ArchiveHeads),
		AclId:           actual.ACLID,
		AclHead:         actual.ACLHead,
		Details:         details,
		Blocks:          blocks,
	}
	if actual.NativeKey != nil {
		result.NativeKey = actual.NativeKey.Marshal()
	}
	return result
}

func annotationSchemaRegistrationErrorCode(err error) pb.RpcAnnotationSchemaRegisterResponseErrorCode {
	switch {
	case errors.Is(err, context.Canceled), errors.Is(err, context.DeadlineExceeded):
		return pb.RpcAnnotationSchemaRegisterResponseError_CANCELED
	case errors.Is(err, annotationschema.ErrRegistrationConflict):
		return pb.RpcAnnotationSchemaRegisterResponseError_CONFLICT
	case errors.Is(err, annotationschema.ErrRegistrationUnresolved), errors.Is(err, objectcreator.ErrFixedSchemaChanged):
		return pb.RpcAnnotationSchemaRegisterResponseError_UNRESOLVED
	case errors.Is(err, annotationschema.ErrRuntimeChanged), errors.Is(err, annotationschema.ErrUnqualifiedRuntime), errors.Is(err, application.ErrActiveAppChanged):
		return pb.RpcAnnotationSchemaRegisterResponseError_RUNTIME_UNAVAILABLE
	case errors.Is(err, list.ErrInsufficientPermissions), errors.Is(err, restriction.ErrRestricted):
		return pb.RpcAnnotationSchemaRegisterResponseError_PERMISSION_DENIED
	default:
		return pb.RpcAnnotationSchemaRegisterResponseError_UNKNOWN_ERROR
	}
}
