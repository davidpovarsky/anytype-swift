import Foundation

/// Data-contract errors only. These values do not grant access to a native
/// account, Space, object, writer, database or acknowledgement operation.
public enum TorahAnnotationNativeContractError: Error, Sendable, Equatable {
    case invalidScope
    case invalidCommitment
    case invalidObjectIdentity
}

/// Exact fields from the existing destination and envelope identity. The host
/// must independently capture the actual original account/Space authority.
/// Deliberately not Codable: this is not another envelope or transport format.
public struct TorahAnnotationNativeScope: Sendable, Hashable {
    public let destination: String
    public let account: String
    public let space: String
    public let namespace: String
    public let annotationUUID: UUID

    public init(destination: String, account: String, space: String,
                namespace: String, annotationUUID: UUID) throws {
        guard [destination, account, space, namespace].allSatisfy(
            TorahAnnotationNativeValidation.identifier
        ) else { throw TorahAnnotationNativeContractError.invalidScope }
        self.destination = destination
        self.account = account
        self.space = space
        self.namespace = namespace
        self.annotationUUID = annotationUUID
    }
}

/// Commitments are copied from AnnotationExchangeDelivery/Version and the
/// canonical source witness. This type neither encodes an envelope nor hashes,
/// truncates, rewrites or interprets its original body bytes.
public struct TorahAnnotationNativeCommitment: Sendable, Equatable {
    public let scope: TorahAnnotationNativeScope
    public let messageID: UUID
    public let mutationID: UUID
    public let revision: Int64
    public let sourceDigest: String
    public let payloadDigest: String

    public init(scope: TorahAnnotationNativeScope, messageID: UUID, mutationID: UUID,
                revision: Int64, sourceDigest: String, payloadDigest: String) throws {
        guard revision > 0,
              TorahAnnotationNativeValidation.digest(sourceDigest),
              TorahAnnotationNativeValidation.digest(payloadDigest) else {
            throw TorahAnnotationNativeContractError.invalidCommitment
        }
        self.scope = scope
        self.messageID = messageID
        self.mutationID = mutationID
        self.revision = revision
        self.sourceDigest = sourceDigest
        self.payloadDigest = payloadDigest
    }
}

/// A candidate mapping value. Only fresh original native readback under the
/// current opaque destination capability may establish a durable mapping.
public struct TorahAnnotationNativeIdentity: Sendable, Hashable {
    public let scope: TorahAnnotationNativeScope
    public let objectID: String

    public init(scope: TorahAnnotationNativeScope, objectID: String) throws {
        guard TorahAnnotationNativeValidation.identifier(objectID) else {
            throw TorahAnnotationNativeContractError.invalidObjectIdentity
        }
        self.scope = scope
        self.objectID = objectID
    }
}

public enum TorahAnnotationPromotedWritingType: String, Sendable, Equatable {
    case chiddush
    case article
    case research
}

/// Length, block count and expanded presentation are not classification inputs.
/// A promotion must be an explicit separately owned product operation.
public enum TorahAnnotationNativeClassification: Sendable, Equatable {
    case annotation
    case promotedDocument(TorahAnnotationPromotedWritingType)

    public var isDocument: Bool {
        if case .promotedDocument = self { return true }
        return false
    }
}

public enum TorahAnnotationMaterializationPurpose: Sendable, Equatable {
    case annotation
    case highlightMetadataOnly
    case tombstone
}

public enum TorahAnnotationCreateDispatchState: Sendable, Equatable {
    case notDispatched
    case mayHaveDispatched
    case nativeObjectObserved(String)
}

/// The consumer persists this exact attempt before dispatch. Before a native
/// create can be admitted, its state must already be mayHaveDispatched.
/// Neither a crash nor a new process may reset that state to notDispatched.
public struct TorahAnnotationNativeCreateAttempt: Sendable, Equatable {
    public let attemptID: UUID
    public let commitment: TorahAnnotationNativeCommitment
    public let dispatchState: TorahAnnotationCreateDispatchState

    public init(attemptID: UUID, commitment: TorahAnnotationNativeCommitment,
                dispatchState: TorahAnnotationCreateDispatchState) throws {
        if case let .nativeObjectObserved(id) = dispatchState,
           !TorahAnnotationNativeValidation.identifier(id) {
            throw TorahAnnotationNativeContractError.invalidObjectIdentity
        }
        self.attemptID = attemptID
        self.commitment = commitment
        self.dispatchState = dispatchState
    }
}

public enum TorahAnnotationNativeObjectState: Sendable, Equatable {
    case present
    case archived
    case deleted
    case unavailable
}

/// Explicit observations for pure assessment, not a native receipt or proof of
/// global uniqueness. The eventual adapter must obtain them from the original
/// query/ObjectShow/export route and retain its actual source-bound evidence.
public struct TorahAnnotationNativeCandidate: Sendable, Equatable {
    public let identity: TorahAnnotationNativeIdentity
    public let nativeTypeID: String
    public let objectState: TorahAnnotationNativeObjectState
    public let classification: TorahAnnotationNativeClassification
    public let creationAttemptID: UUID
    public let creationCommitment: TorahAnnotationNativeCommitment
    public let appliedCommitment: TorahAnnotationNativeCommitment?
    public let nativeSnapshotDigest: String?

    public init(identity: TorahAnnotationNativeIdentity, nativeTypeID: String,
                objectState: TorahAnnotationNativeObjectState,
                classification: TorahAnnotationNativeClassification,
                creationAttemptID: UUID,
                creationCommitment: TorahAnnotationNativeCommitment,
                appliedCommitment: TorahAnnotationNativeCommitment? = nil,
                nativeSnapshotDigest: String? = nil) throws {
        guard TorahAnnotationNativeValidation.identifier(nativeTypeID) else {
            throw TorahAnnotationNativeContractError.invalidObjectIdentity
        }
        if let nativeSnapshotDigest,
           !TorahAnnotationNativeValidation.digest(nativeSnapshotDigest) {
            throw TorahAnnotationNativeContractError.invalidCommitment
        }
        self.identity = identity
        self.nativeTypeID = nativeTypeID
        self.objectState = objectState
        self.classification = classification
        self.creationAttemptID = creationAttemptID
        self.creationCommitment = creationCommitment
        self.appliedCommitment = appliedCommitment
        self.nativeSnapshotDigest = nativeSnapshotDigest
    }
}

/// Domain validation follows the existing exchange commitment bounds. The
/// existing strict envelope codec remains the sole wire grammar/64KB authority.
enum TorahAnnotationNativeValidation {
    static func identifier(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 512 && value.utf8.allSatisfy {
            (48...57).contains($0) || (65...90).contains($0)
                || (97...122).contains($0) || [45, 46, 58, 95].contains($0)
        }
    }

    static func digest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
    }
}

