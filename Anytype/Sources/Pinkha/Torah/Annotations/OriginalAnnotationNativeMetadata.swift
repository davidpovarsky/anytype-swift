import Foundation
import PinkhaKit
import ProtobufMessages
import SwiftProtobuf

enum OriginalAnnotationMetadataError: Error, Sendable, Equatable {
    case missingOrMalformedField(String)
    case unsupportedProtocol
    case unsupportedClassification
    case noncanonicalUUID(String)
    case invalidRevision(String)
    case wrongRoot
    case wrongNativeSpace
    case malformedNativeType
    case incompleteAppliedCommitment
}

enum OriginalAnnotationMetadataField: String, CaseIterable, Sendable {
    case schemaProtocol = "pinkhaTorahAnnotationProtocol"
    case classification = "pinkhaTorahAnnotationClassification"
    case namespace = "pinkhaTorahAnnotationNamespace"
    case annotationUUID = "pinkhaTorahAnnotationUUID"
    case creationDestination = "pinkhaTorahAnnotationCreationDestination"
    case creationAccount = "pinkhaTorahAnnotationCreationAccount"
    case creationSpace = "pinkhaTorahAnnotationCreationSpace"
    case creationMessageID = "pinkhaTorahAnnotationCreationMessageID"
    case creationMutationID = "pinkhaTorahAnnotationCreationMutationID"
    case creationRevision = "pinkhaTorahAnnotationCreationRevision"
    case creationSourceDigest = "pinkhaTorahAnnotationCreationSourceDigest"
    case creationPayloadDigest = "pinkhaTorahAnnotationCreationPayloadDigest"
    case appliedMessageID = "pinkhaTorahAnnotationAppliedMessageID"
    case appliedMutationID = "pinkhaTorahAnnotationAppliedMutationID"
    case appliedRevision = "pinkhaTorahAnnotationAppliedRevision"
    case appliedSourceDigest = "pinkhaTorahAnnotationAppliedSourceDigest"
    case appliedPayloadDigest = "pinkhaTorahAnnotationAppliedPayloadDigest"
}

enum OriginalAnnotationNativeMetadata {
    static let protocolValue = "pinkha.torah.annotation/1"
    static let originalTypeUniqueKey = "ot-pinkhatorahannotationv1"
    static let relationFormat: Anytype_Model_RelationFormat = .longtext

    private static let appliedFields: [OriginalAnnotationMetadataField] = [
        .appliedMessageID, .appliedMutationID, .appliedRevision,
        .appliedSourceDigest, .appliedPayloadDigest
    ]

    static func decode(
        _ nativeDetails: Google_Protobuf_Struct, rootID: String
    ) throws -> TorahAnnotationNativeCandidate {
        let fields = nativeDetails.fields
        let objectID = try string("id", fields: fields)
        guard objectID.utf8.elementsEqual(rootID.utf8) else {
            throw OriginalAnnotationMetadataError.wrongRoot
        }
        guard try string(.schemaProtocol, fields: fields).utf8.elementsEqual(protocolValue.utf8) else {
            throw OriginalAnnotationMetadataError.unsupportedProtocol
        }
        let scope = try TorahAnnotationNativeScope(
            destination: string(.creationDestination, fields: fields),
            account: string(.creationAccount, fields: fields),
            space: string(.creationSpace, fields: fields),
            namespace: string(.namespace, fields: fields),
            annotationUUID: uuid(.annotationUUID, fields: fields)
        )
        guard try string("spaceId", fields: fields).utf8.elementsEqual(scope.space.utf8) else {
            throw OriginalAnnotationMetadataError.wrongNativeSpace
        }
        guard case .listValue(let types)? = fields["type"]?.kind,
              types.values.count == 1,
              case .stringValue(let nativeTypeID)? = types.values[0].kind else {
            throw OriginalAnnotationMetadataError.malformedNativeType
        }
        let creation = try TorahAnnotationNativeCommitment(
            scope: scope,
            messageID: uuid(.creationMessageID, fields: fields),
            mutationID: uuid(.creationMutationID, fields: fields),
            revision: revision(.creationRevision, fields: fields),
            sourceDigest: string(.creationSourceDigest, fields: fields),
            payloadDigest: string(.creationPayloadDigest, fields: fields)
        )
        let classification: TorahAnnotationNativeClassification
        switch try string(.classification, fields: fields) {
        case "annotation": classification = .annotation
        case "chiddush": classification = .promotedDocument(.chiddush)
        case "article": classification = .promotedDocument(.article)
        case "research": classification = .promotedDocument(.research)
        default: throw OriginalAnnotationMetadataError.unsupportedClassification
        }
        let applied: TorahAnnotationNativeCommitment?
        let presentApplied = appliedFields.filter { fields[$0.rawValue] != nil }
        if presentApplied.isEmpty {
            applied = nil
        } else {
            guard presentApplied.count == appliedFields.count else {
                throw OriginalAnnotationMetadataError.incompleteAppliedCommitment
            }
            applied = try TorahAnnotationNativeCommitment(
                scope: scope,
                messageID: uuid(.appliedMessageID, fields: fields),
                mutationID: uuid(.appliedMutationID, fields: fields),
                revision: revision(.appliedRevision, fields: fields),
                sourceDigest: string(.appliedSourceDigest, fields: fields),
                payloadDigest: string(.appliedPayloadDigest, fields: fields)
            )
        }
        let archived = try nativeBoolean("isArchived", fields: fields)
        let deleted = try nativeBoolean("isDeleted", fields: fields)
        let state: TorahAnnotationNativeObjectState
        if deleted {
            state = .deleted
        } else if archived {
            state = .archived
        } else {
            state = .present
        }
        return try TorahAnnotationNativeCandidate(
            identity: TorahAnnotationNativeIdentity(scope: scope, objectID: objectID),
            nativeTypeID: nativeTypeID,
            objectState: state,
            classification: classification,
            creationAttemptID: creation.messageID,
            creationCommitment: creation,
            appliedCommitment: applied,
            nativeSnapshotDigest: nil
        )
    }

    private static func string(
        _ field: OriginalAnnotationMetadataField,
        fields: [String: Google_Protobuf_Value]
    ) throws -> String {
        try string(field.rawValue, fields: fields)
    }

    private static func string(
        _ key: String, fields: [String: Google_Protobuf_Value]
    ) throws -> String {
        guard case .stringValue(let value)? = fields[key]?.kind else {
            throw OriginalAnnotationMetadataError.missingOrMalformedField(key)
        }
        return value
    }

    private static func uuid(
        _ field: OriginalAnnotationMetadataField,
        fields: [String: Google_Protobuf_Value]
    ) throws -> UUID {
        let text = try string(field, fields: fields)
        guard let value = UUID(uuidString: text),
              value.uuidString.utf8.elementsEqual(text.utf8) else {
            throw OriginalAnnotationMetadataError.noncanonicalUUID(field.rawValue)
        }
        return value
    }

    private static func revision(
        _ field: OriginalAnnotationMetadataField,
        fields: [String: Google_Protobuf_Value]
    ) throws -> Int64 {
        let text = try string(field, fields: fields)
        guard !text.isEmpty, text.utf8.count <= 19,
              text.utf8.allSatisfy({ (48...57).contains($0) }),
              let value = Int64(text), value > 0,
              String(value).utf8.elementsEqual(text.utf8) else {
            throw OriginalAnnotationMetadataError.invalidRevision(field.rawValue)
        }
        return value
    }

    private static func nativeBoolean(
        _ key: String, fields: [String: Google_Protobuf_Value]
    ) throws -> Bool {
        guard let value = fields[key] else { return false }
        guard case .boolValue(let flag)? = value.kind else {
            throw OriginalAnnotationMetadataError.missingOrMalformedField(key)
        }
        return flag
    }
}
