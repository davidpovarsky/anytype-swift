import Foundation
import Crypto

/// This reference is supplied by the host's account/Space session and retained
/// original creation receipt, never by an untrusted message payload.
public struct AnyNativeMarkdownReference: Sendable, Equatable {
    public let accountID: String
    public let spaceID: String
    public let objectID: String

    public init(accountID: String, spaceID: String, objectID: String) throws {
        guard [accountID, spaceID, objectID].allSatisfy(Self.validID) else {
            throw AnyEngineError.invalidIdentity("markdown scope")
        }
        self.accountID = accountID; self.spaceID = spaceID; self.objectID = objectID
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        same(lhs.accountID, rhs.accountID) && same(lhs.spaceID, rhs.spaceID)
            && same(lhs.objectID, rhs.objectID)
    }

    fileprivate static func same(_ lhs: String, _ rhs: String) -> Bool {
        lhs.utf8.elementsEqual(rhs.utf8)
    }
    fileprivate static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 && value != "." && value != ".."
            && value.utf8.allSatisfy { $0 > 32 && $0 != 127 && ![35, 37, 47, 63, 92].contains($0) }
    }
    fileprivate static func validVersion(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024
            && value.utf8.allSatisfy { $0 >= 33 && $0 <= 126 }
    }
}

public struct AnyNativeMarkdownSnapshot: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let reference: AnyNativeMarkdownReference
    public let content: String
    /// Opaque native version: valid only for the native instance that issued it.
    public let version: String
    public let contentSHA256: String
    public let contentBytes: Int
    public var description: String { "AnyNativeMarkdownSnapshot(private body and version redacted)" }
    public var debugDescription: String { description }
}

/// Correlation is host-owned and must be journaled with the original page ID.
/// The native Markdown endpoint does not provide request-ID deduplication.
public struct AnyNativeMarkdownWriteContext: Sendable {
    public let reference: AnyNativeMarkdownReference
    public let requestID: String
    public let requestedContentSHA256: String
    public let requestedContentBytes: Int
}

public struct AnyNativeMarkdownWriteIntent: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let context: AnyNativeMarkdownWriteContext
    public let expectedVersion: String
    public let content: String

    public init(reference: AnyNativeMarkdownReference, requestID: String,
                expectedVersion: String, content: String) throws {
        guard requestID.utf8.count == 32,
              requestID.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              AnyNativeMarkdownReference.validVersion(expectedVersion),
              content.utf8.count <= AnyNativeMarkdownBody.maximumContentBytes else {
            throw AnyEngineError.invalidOperation("conditional markdown intent")
        }
        context = .init(reference: reference, requestID: requestID,
                        requestedContentSHA256: AnyNativeMarkdownBody.digest(content),
                        requestedContentBytes: content.utf8.count)
        self.expectedVersion = expectedVersion; self.content = content
    }
    public var description: String { "AnyNativeMarkdownWriteIntent(private body and version redacted)" }
    public var debugDescription: String { description }
}

public struct AnyNativeMarkdownAcknowledgement: Sendable {
    public let context: AnyNativeMarkdownWriteContext
    public let nativeVersion: String
    public let insertedBlockIDs: [String]
    public let updatedBlockIDs: [String]
    public let deletedBlockIDs: [String]
    public let unchangedBlocks: Int64
}

public struct AnyNativeMarkdownWriteReceipt: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let acknowledgement: AnyNativeMarkdownAcknowledgement
    public let saved: AnyNativeMarkdownSnapshot
    /// Native Markdown normalizes syntax. A successful save never implicitly
    /// promises that the submitted byte representation survived unchanged.
    public var exactRequestedBytesPreserved: Bool {
        saved.contentBytes == acknowledgement.context.requestedContentBytes
            && saved.contentSHA256 == acknowledgement.context.requestedContentSHA256
    }
    public var description: String { "AnyNativeMarkdownWriteReceipt(private body and version redacted)" }
    public var debugDescription: String { description }
}

/// Every case retains the original account/Space/page correlation. The host
/// records this in its original journal and never creates a replacement page.
public enum AnyNativeMarkdownWriteFailure: Error, Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    case uncertain(AnyNativeMarkdownWriteContext)
    case acknowledgedReadbackUnavailable(AnyNativeMarkdownAcknowledgement)
    case acknowledgedReadbackChanged(AnyNativeMarkdownAcknowledgement)
    public var description: String {
        switch self {
        case .uncertain: "AnyNativeMarkdownWriteFailure(uncertain; reconcile original page)"
        case .acknowledgedReadbackUnavailable: "AnyNativeMarkdownWriteFailure(acknowledged; readback unavailable)"
        case .acknowledgedReadbackChanged: "AnyNativeMarkdownWriteFailure(acknowledged; readback changed)"
        }
    }
    public var debugDescription: String { description }
}

/// Existing conditional native Markdown API. This is one body operation on a
/// known original page, not atomic create-with-body and not a retry scheduler.
/// All reads and response delivery require the live host consumer lease.
public struct AnyNativeMarkdownBody: Sendable {
    public static let maximumContentBytes = 262_144
    private let client: AnyHTTPClient
    public init(client: AnyHTTPClient) { self.client = client }

    public func read(
        _ reference: AnyNativeMarkdownReference,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyNativeMarkdownSnapshot {
        try requireAccount(reference)
        let response = try await client.requestJSONResponse(method: "GET",
            path: path(reference), maximumResponseBytes: 2_097_152, authorize: authorize)
        guard response.statusCode == 200 else {
            throw AnyEngineError.malformedResponse("markdown read status")
        }
        let snapshot = try Self.decodeSnapshot(response.body, reference: reference)
        try await client.checkAccount(); try await authorize(); try Task.checkCancellation()
        return snapshot
    }

    /// Use a fresh read's nonempty version. For save-message, the host must first
    /// retain its original creation receipt and require that new page's body is
    /// empty. The native CAS refuses a concurrent edit; no unconditional fallback
    /// or second PUT is issued here.
    public func replace(
        _ intent: AnyNativeMarkdownWriteIntent,
        authorizeRead: @escaping @Sendable () async throws -> Void,
        authorizeWrite: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyNativeMarkdownWriteReceipt {
        try requireAccount(intent.context.reference)
        let response: AnyHTTPJSONResponse
        do {
            response = try await client.requestJSONResponse(method: "PUT",
                path: path(intent.context.reference),
                body: .object(["content": .string(intent.content),
                               "ifVersion": .string(intent.expectedVersion)]),
                maximumResponseBytes: 2_097_152, validateResponse: authorizeRead,
                authorize: {
                    try await authorizeRead()
                    try await authorizeWrite()
                })
        } catch let error as AnyEngineError {
            switch error {
            case .writeUncertain, .writeRejected, .malformedResponse:
                throw AnyNativeMarkdownWriteFailure.uncertain(intent.context)
            case .http(let status, let code):
                // Native Set can apply part of a batch before reporting an SDK
                // rejection. Only these documented pre-write refusals prove
                // no body effect; an undocumented/5xx response is uncertain.
                let refused = (status == 409 && code == "markdown.conflict")
                    || (status == 400 && (code == "markdown.block_too_large"
                        || code.hasPrefix("request.")))
                    || (status == 403 && (code == "space.read_only" || code == "acl.forbidden"))
                if refused { throw error }
                throw AnyNativeMarkdownWriteFailure.uncertain(intent.context)
            default: throw error
            }
        }
        let acknowledgement: AnyNativeMarkdownAcknowledgement
        do {
            guard response.statusCode == 200 else { throw AnyEngineError.writeUncertain }
            acknowledgement = try Self.decodeAcknowledgement(response.body, context: intent.context)
        } catch {
            throw AnyNativeMarkdownWriteFailure.uncertain(intent.context)
        }
        let saved: AnyNativeMarkdownSnapshot
        do {
            saved = try await read(intent.context.reference, authorize: authorizeRead)
        } catch {
            throw AnyNativeMarkdownWriteFailure.acknowledgedReadbackUnavailable(acknowledgement)
        }
        guard AnyNativeMarkdownReference.same(saved.version, acknowledgement.nativeVersion) else {
            throw AnyNativeMarkdownWriteFailure.acknowledgedReadbackChanged(acknowledgement)
        }
        return .init(acknowledgement: acknowledgement, saved: saved)
    }

    private func requireAccount(_ reference: AnyNativeMarkdownReference) throws {
        guard AnyNativeMarkdownReference.same(reference.accountID, client.expectedAccountID) else {
            throw AnyEngineError.accountChanged
        }
    }
    private func path(_ reference: AnyNativeMarkdownReference) -> [String] {
        ["v1", "spaces", reference.spaceID, "objects", reference.objectID,
         "editor", "editor_blocks", "markdown"]
    }
    static func digest(_ value: String) -> String {
        SHA256.hash(data: Data(value.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    static func decodeSnapshot(_ body: AnyJSON, reference: AnyNativeMarkdownReference) throws -> AnyNativeMarkdownSnapshot {
        guard let content = body["content"]?.string, content.utf8.count <= maximumContentBytes,
              let version = body["version"]?.string, AnyNativeMarkdownReference.validVersion(version) else {
            throw AnyEngineError.malformedResponse("markdown body or native version")
        }
        return .init(reference: reference, content: content, version: version,
                     contentSHA256: digest(content), contentBytes: content.utf8.count)
    }
    static func decodeAcknowledgement(_ body: AnyJSON, context: AnyNativeMarkdownWriteContext) throws -> AnyNativeMarkdownAcknowledgement {
        guard let version = body["version"]?.string, AnyNativeMarkdownReference.validVersion(version),
              let unchanged = body["unchanged"]?.integer, (0...10000).contains(unchanged) else {
            throw AnyEngineError.malformedResponse("markdown acknowledgement")
        }
        func ids(_ key: String) throws -> [String] {
            guard let rows = body[key]?.array, rows.count <= 10000 else {
                throw AnyEngineError.malformedResponse("markdown block acknowledgements")
            }
            let values = rows.compactMap(\.string)
            guard values.count == rows.count, values.allSatisfy(AnyNativeMarkdownReference.validID),
                  Set(values.map { Data($0.utf8) }).count == values.count else {
                throw AnyEngineError.malformedResponse("markdown block identities")
            }
            return values
        }
        let inserted = try ids("inserted"), updated = try ids("updated"), deleted = try ids("deleted")
        let all = inserted + updated + deleted
        guard all.count <= 10000, Set(all.map { Data($0.utf8) }).count == all.count else {
            throw AnyEngineError.malformedResponse("overlapping markdown block acknowledgements")
        }
        return .init(context: context, nativeVersion: version, insertedBlockIDs: inserted,
                     updatedBlockIDs: updated, deletedBlockIDs: deleted, unchangedBlocks: unchanged)
    }
}
