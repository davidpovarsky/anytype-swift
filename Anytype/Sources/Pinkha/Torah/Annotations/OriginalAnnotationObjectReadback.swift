import Foundation
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf

enum OriginalAnnotationObjectReadbackError: Error, Sendable, Equatable {
    case unsupportedOriginalSession
    case unsupportedOriginalAccount
    case missingAccount
    case wrongAccount
    case wrongObject
    case wrongSpace
    case malformedNativeType
    case malformedNativeState
    case unavailableObject
}

/// A narrow read adapter for an already prepared original object. The request is
/// data, not authority: only the retained original session and its captured
/// account/source/document generations admit the actual native read.
///
/// Returned ObjectDetails are a raw native observation, NOT annotation identity,
/// classification, applied-body proof or permission to write a local mapping.
/// Those require the separately provisioned annotation schema and a reviewed
/// synchronous commit-boundary capability. This adapter cannot create, discover,
/// import, select an account, bootstrap a Space, acknowledge or replace an object.
@MainActor
final class OriginalAnnotationObjectReadback {
    private let session: PreparedEditorPageSession
    private let requestedIdentity: TorahAnnotationNativeIdentity
    private let accountManager: AccountManager
    private let basicUserInfo: any BasicUserInfoStorageProtocol
    private let accountCapture: EditorDocumentWriteCapture

    private init(
        session: PreparedEditorPageSession,
        requestedIdentity: TorahAnnotationNativeIdentity,
        accountManager: AccountManager,
        basicUserInfo: any BasicUserInfoStorageProtocol,
        accountCapture: EditorDocumentWriteCapture
    ) {
        self.session = session
        self.requestedIdentity = requestedIdentity
        self.accountManager = accountManager
        self.basicUserInfo = basicUserInfo
        self.accountCapture = accountCapture
    }

    /// This internal seam is for the existing original Host composition. It
    /// accepts neither an unprepared owner nor a caller-provided account service.
    static func bindExistingOriginal(
        session: PreparedEditorPageSession,
        requestedIdentity: TorahAnnotationNativeIdentity
    ) throws -> OriginalAnnotationObjectReadback {
        try Task.checkCancellation()
        guard session.hasExternalSourceBinding,
              session.document is BaseDocument,
              session.data.mode.isHandling,
              session.document.mode.isHandling else {
            throw OriginalAnnotationObjectReadbackError.unsupportedOriginalSession
        }
        guard session.data.objectId.utf8.elementsEqual(requestedIdentity.objectID.utf8),
              session.document.objectId.utf8.elementsEqual(requestedIdentity.objectID.utf8) else {
            throw OriginalAnnotationObjectReadbackError.wrongObject
        }
        guard session.data.spaceId.utf8.elementsEqual(requestedIdentity.scope.space.utf8),
              session.document.spaceId.utf8.elementsEqual(requestedIdentity.scope.space.utf8) else {
            throw OriginalAnnotationObjectReadbackError.wrongSpace
        }
        guard let accountManager = Container.shared.accountManager() as? AccountManager,
              let lifetime = accountManager.editorWriteLifetime else {
            throw OriginalAnnotationObjectReadbackError.unsupportedOriginalAccount
        }
        let value = try OriginalAnnotationObjectReadback(
            session: session,
            requestedIdentity: requestedIdentity,
            accountManager: accountManager,
            basicUserInfo: Container.shared.basicUserInfoStorage(),
            accountCapture: EditorDocumentWriteCapture(lifetime)
        )
        try value.validateOwnedRuntime()
        return value
    }

    /// Drains the same owner's registered writes and closes new UI admission
    /// while ObjectShow and strict response validation execute. The per-RPC
    /// Invocation permit still comes from this exact retained original owner.
    func readFreshDetails() async throws -> ObjectDetails {
        try validateOwnedRuntime()
        let identity = requestedIdentity
        let details = try await session.owner.withExclusiveRead(
            contextId: identity.objectID,
            spaceId: identity.scope.space,
            rpcNames: ["ObjectShow"]
        ) { [self] in
            try await validateOwnedRuntime()
            let response = try await ClientCommands.objectShow(.with {
                $0.contextID = identity.objectID
                $0.objectID = identity.objectID
                $0.spaceID = identity.scope.space
            }).invoke(qos: .userInitiated)
            try await validateOwnedRuntime()
            return try Self.strictDetails(response, requestedIdentity: identity)
        }
        try validateOwnedRuntime()
        return details
    }

    private func validateOwnedRuntime() throws {
        try Task.checkCancellation()
        try accountCapture.validate()
        guard !accountManager.account.id.isEmpty, !basicUserInfo.usersId.isEmpty else {
            throw OriginalAnnotationObjectReadbackError.missingAccount
        }
        guard accountManager.account.id.utf8.elementsEqual(requestedIdentity.scope.account.utf8),
              basicUserInfo.usersId.utf8.elementsEqual(requestedIdentity.scope.account.utf8) else {
            throw OriginalAnnotationObjectReadbackError.wrongAccount
        }
        try session.owner.validateOwnership()
        try session.owner.validateDocument(session.document)
    }

    /// Strictly inspects the actual original protobuf. Linked-object rows may be
    /// present, but a missing or duplicate exact root row is never accepted.
    /// No name/layout/provider cache or indexed search substitutes for this read.
    private nonisolated static func strictDetails(
        _ response: Anytype_Rpc.ObjectShow.Response,
        requestedIdentity: TorahAnnotationNativeIdentity
    ) throws -> ObjectDetails {
        let objectID = requestedIdentity.objectID
        guard response.hasObjectView,
              response.objectView.rootID.utf8.elementsEqual(objectID.utf8) else {
            throw OriginalAnnotationObjectReadbackError.wrongObject
        }
        let matching = response.objectView.details.filter {
            $0.id.utf8.elementsEqual(objectID.utf8)
        }
        guard matching.count == 1, matching[0].hasDetails else {
            throw OriginalAnnotationObjectReadbackError.wrongObject
        }
        let fields = matching[0].details.fields
        guard case .stringValue(let actualID)? = fields[BundledPropertyKey.id.rawValue]?.kind,
              actualID.utf8.elementsEqual(objectID.utf8) else {
            throw OriginalAnnotationObjectReadbackError.wrongObject
        }
        guard case .stringValue(let actualSpace)? = fields[BundledPropertyKey.spaceId.rawValue]?.kind,
              actualSpace.utf8.elementsEqual(requestedIdentity.scope.space.utf8) else {
            throw OriginalAnnotationObjectReadbackError.wrongSpace
        }
        guard case .listValue(let nativeTypes)? = fields[BundledPropertyKey.type.rawValue]?.kind,
              nativeTypes.values.count == 1,
              case .stringValue(let actualType)? = nativeTypes.values[0].kind,
              !actualType.isEmpty, !actualType.utf8.contains(0) else {
            throw OriginalAnnotationObjectReadbackError.malformedNativeType
        }
        for key in [BundledPropertyKey.isArchived, .isDeleted] {
            if let value = fields[key.rawValue] {
                guard case .boolValue(let isUnavailable)? = value.kind else {
                    throw OriginalAnnotationObjectReadbackError.malformedNativeState
                }
                guard !isUnavailable else {
                    throw OriginalAnnotationObjectReadbackError.unavailableObject
                }
            }
        }
        return try ObjectDetails(protobufStruct: matching[0].details)
    }
}
