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


struct OriginalAnnotationHeldReadObservation: Sendable {
    let objectView: Anytype_Model_ObjectView
    let rootDetails: Google_Protobuf_Struct

    fileprivate init(objectView: Anytype_Model_ObjectView,
                     rootDetails: Google_Protobuf_Struct) {
        self.objectView = objectView
        self.rootDetails = rootDetails
    }
}

/// Actual original responses from one held Owner interval. This is historical
/// observation data, not an atomic native graph or permission to COMMIT/ACK.
struct OriginalAnnotationHeldArchiveObservation: Sendable {
    let before: OriginalAnnotationHeldReadObservation
    let after: OriginalAnnotationHeldReadObservation
    let exportResponse: Anytype_Rpc.Object.ListExport.Response

    fileprivate init(before: OriginalAnnotationHeldReadObservation,
                     after: OriginalAnnotationHeldReadObservation,
                     exportResponse: Anytype_Rpc.Object.ListExport.Response) {
        self.before = before
        self.after = after
        self.exportResponse = exportResponse
    }
}

enum OriginalAnnotationHeldReadOutcome<Value: Sendable>: Sendable {
    case completed(Value)
    case completedWithoutCurrentOwnership(Value, error: any Error)
}

@MainActor
private final class OriginalAnnotationHeldReadCompletion<Value: Sendable> {
    enum State {
        case notCompleted
        case completed(Value)
    }

    var state: State = .notCompleted
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


    func withFreshNativeObservation<Value: Sendable>(
        consume: @MainActor @Sendable (OriginalAnnotationHeldReadObservation) throws -> Value
    ) async throws -> OriginalAnnotationHeldReadOutcome<Value> {
        try validateOwnedRuntime()
        let identity = requestedIdentity
        let completion = OriginalAnnotationHeldReadCompletion<Value>()
        do {
            let value = try await session.owner.withExclusiveRead(
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
                return try await consumeFreshNativeResponse(
                    response, completion: completion, consume: consume
                )
            }
            try validateOwnedRuntime()
            return .completed(value)
        } catch {
            switch completion.state {
            case .notCompleted:
                throw error
            case let .completed(value):
                return .completedWithoutCurrentOwnership(value, error: error)
            }
        }
    }

    /// Uses the original exporter directly in the already acquired barrier.
    /// Inbound native changes are not stopped by this app Owner. The synchronous
    /// consumer may compare the captured archive; it cannot infer whole-graph
    /// atomicity or durable application from this interval alone.
    func withFreshNativeArchiveObservation<Value: Sendable>(
        ownedArchiveDirectory: URL,
        consume: @MainActor @Sendable (OriginalAnnotationHeldArchiveObservation) throws -> Value
    ) async throws -> OriginalAnnotationHeldReadOutcome<Value> {
        try validateOwnedRuntime()
        let identity = requestedIdentity
        let completion = OriginalAnnotationHeldReadCompletion<Value>()
        do {
            let value = try await session.owner.withExclusiveRead(
                contextId: identity.objectID,
                spaceId: identity.scope.space,
                rpcNames: ["ObjectShow", "ObjectListExport"]
            ) { [self] in
                try await validateOwnedRuntime()
                let beforeResponse = try await ClientCommands.objectShow(.with {
                    $0.contextID = identity.objectID
                    $0.objectID = identity.objectID
                    $0.spaceID = identity.scope.space
                }).invoke(qos: .userInitiated)
                let before = try await makeFreshNativeObservation(beforeResponse)
                let exported = try await ClientCommands.objectListExport(.with {
                    $0.spaceID = identity.scope.space
                    $0.objectIds = [identity.objectID]
                    $0.path = ownedArchiveDirectory.path
                    $0.format = .protobuf
                    $0.zip = true
                    $0.isJson = false
                    $0.includeFiles = true
                    $0.includeNested = true
                    $0.includeArchived = true
                    $0.includeBacklinks = false
                    $0.includeSpace = false
                    $0.noProgress = true
                    // No filters, removeBlocks, import or public nested capture.
                }).invoke(qos: .userInitiated)
                // Retain the actual response report even if a later owner check
                // or second ObjectShow fails. This owned temporary file is
                // historical recovery evidence, never body/commit authority.
                try await retainNativeExportReport(exported, in: ownedArchiveDirectory)
                try await validateOwnedRuntime()
                let afterResponse = try await ClientCommands.objectShow(.with {
                    $0.contextID = identity.objectID
                    $0.objectID = identity.objectID
                    $0.spaceID = identity.scope.space
                }).invoke(qos: .userInitiated)
                return try await consumeFreshNativeArchive(
                    before: before, afterResponse: afterResponse, exported: exported,
                    completion: completion, consume: consume
                )
            }
            try validateOwnedRuntime()
            return .completed(value)
        } catch {
            switch completion.state {
            case .notCompleted: throw error
            case let .completed(value):
                return .completedWithoutCurrentOwnership(value, error: error)
            }
        }
    }

    private func retainNativeExportReport(
        _ response: Anytype_Rpc.Object.ListExport.Response, in directory: URL
    ) throws {
        if response.hasReport {
            try response.report.serializedData().write(
                to: directory.appendingPathComponent("native-export-report.pb"),
                options: .withoutOverwriting
            )
        }
    }

    private func consumeFreshNativeArchive<Value: Sendable>(
        before: OriginalAnnotationHeldReadObservation,
        afterResponse: Anytype_Rpc.Object.Show.Response,
        exported: Anytype_Rpc.Object.ListExport.Response,
        completion: OriginalAnnotationHeldReadCompletion<Value>,
        consume: @MainActor @Sendable (OriginalAnnotationHeldArchiveObservation) throws -> Value
    ) throws -> Value {
        let after = try makeFreshNativeObservation(afterResponse)
        let observation = OriginalAnnotationHeldArchiveObservation(
            before: before, after: after, exportResponse: exported
        )
        let value = try consume(observation)
        completion.state = .completed(value)
        try validateOwnedRuntime()
        return value
    }

    private func makeFreshNativeObservation(
        _ response: Anytype_Rpc.Object.Show.Response
    ) throws -> OriginalAnnotationHeldReadObservation {
        try validateOwnedRuntime()
        _ = try Self.strictDetails(response, requestedIdentity: requestedIdentity)
        guard let root = response.objectView.details.first(where: {
            $0.id.utf8.elementsEqual(requestedIdentity.objectID.utf8)
        }) else { throw OriginalAnnotationObjectReadbackError.wrongObject }
        return OriginalAnnotationHeldReadObservation(
            objectView: response.objectView, rootDetails: root.details
        )
    }

    private func consumeFreshNativeResponse<Value: Sendable>(
        _ response: Anytype_Rpc.Object.Show.Response,
        completion: OriginalAnnotationHeldReadCompletion<Value>,
        consume: @MainActor @Sendable (OriginalAnnotationHeldReadObservation) throws -> Value
    ) throws -> Value {
        try validateOwnedRuntime()
        _ = try Self.strictDetails(response, requestedIdentity: requestedIdentity)
        guard let root = response.objectView.details.first(where: {
            $0.id.utf8.elementsEqual(requestedIdentity.objectID.utf8)
        }) else {
            throw OriginalAnnotationObjectReadbackError.wrongObject
        }
        let observation = OriginalAnnotationHeldReadObservation(
            objectView: response.objectView, rootDetails: root.details
        )
        let value = try consume(observation)
        completion.state = .completed(value)
        try validateOwnedRuntime()
        return value
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
        _ response: Anytype_Rpc.Object.Show.Response,
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

