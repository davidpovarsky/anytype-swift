import Foundation

/// An exact account/space/object/file scope. Opaque native IDs are compared by
/// UTF-8 bytes; Swift's canonically equivalent text is not a second identity.
public struct AnyNativeFileReference: Sendable {
    public let accountID: String
    public let spaceID: String
    public let objectID: String
    public let fileID: String

    public init(accountID: String, spaceID: String, objectID: String, fileID: String) throws {
        guard [accountID, spaceID, objectID, fileID].allSatisfy(Self.validID) else {
            throw AnyEngineError.invalidIdentity("file scope")
        }
        self.accountID = accountID
        self.spaceID = spaceID
        self.objectID = objectID
        self.fileID = fileID
    }

    fileprivate static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 && value != "." && value != ".." &&
        value.utf8.allSatisfy { $0 > 32 && $0 != 127 && ![35, 37, 47, 63, 92].contains($0) }
    }

    fileprivate static func same(_ left: String, _ right: String) -> Bool {
        left.utf8.elementsEqual(right.utf8)
    }
}

public struct AnyNativeFileStatus: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public enum State: String, Sendable {
        /// The native engine has verified network custody, or the file is inline.
        /// This state alone does not distinguish the two storage tiers.
        case durable
        case inFlight = "inflight"
        /// Actual native storage-limit refusal. Local availability is independent.
        case limited
    }

    public let reference: AnyNativeFileReference
    public let state: State
    public let cached: Bool
    public let failedAttempts: Int64
    /// Private native diagnostic. Do not publish it to analytics or shared logs.
    public let lastError: String?

    public var description: String {
        "AnyNativeFileStatus(state: \(state.rawValue), cached: \(cached), failedAttempts: \(failedAttempts), private diagnostic redacted)"
    }
    public var debugDescription: String { description }
}

/// A 204 acknowledges the retry request, not a new upload, a completed transfer,
/// quota availability or durable custody. Read status again to observe progress.
public struct AnyNativeFileRetryAcknowledgement: Sendable {
    public let reference: AnyNativeFileReference
}

/// Existing native FilesV2 background-work routes, with account, object and
/// consumer-lifetime fences. It never deletes files, clears cached bytes,
/// changes quotas or automatically retries a request with an uncertain outcome.
public struct AnyNativeFileDurability: Sendable {
    private let client: AnyHTTPClient
    public init(client: AnyHTTPClient) { self.client = client }

    public func status(
        _ reference: AnyNativeFileReference,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyNativeFileStatus {
        try requireAccount(reference)
        let body = try await client.requestJSON(method: "GET",
            path: path(reference, action: "status"), maximumResponseBytes: 131_072,
            authorize: authorize)
        let result = try Self.decode(body, reference: reference)
        try await client.checkAccount()
        try await authorize()
        try Task.checkCancellation()
        return result
    }

    /// The read closure must be side-effect-free and validate the live consumer
    /// scope. The separate retry approval admits exactly one native dispatch.
    /// An original typed native error propagates. Lost post-dispatch authority
    /// produces writeUncertain, with no automatic retry or optimistic state.
    public func retry(
        _ reference: AnyNativeFileReference,
        authorizeRead: @escaping @Sendable () async throws -> Void,
        authorizeRetry: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyNativeFileRetryAcknowledgement {
        _ = try await status(reference, authorize: authorizeRead)
        let response = try await client.requestJSONResponse(method: "POST",
            path: path(reference, action: "retry"), maximumResponseBytes: 65_536,
            validateResponse: authorizeRead,
            authorize: {
                try await authorizeRead()
                try await authorizeRetry()
            })
        guard response.statusCode == 204, response.body == .null else {
            throw AnyEngineError.writeUncertain
        }
        return .init(reference: reference)
    }

    private func requireAccount(_ reference: AnyNativeFileReference) throws {
        guard AnyNativeFileReference.same(reference.accountID, client.expectedAccountID) else {
            throw AnyEngineError.accountChanged
        }
    }

    private func path(_ reference: AnyNativeFileReference, action: String) -> [String] {
        ["v1", "spaces", reference.spaceID, "files", reference.fileID, action]
    }

    static func decode(_ body: AnyJSON, reference: AnyNativeFileReference) throws -> AnyNativeFileStatus {
        guard let fileID = body["fileId"]?.string,
              let objectID = body["objectId"]?.string,
              AnyNativeFileReference.same(fileID, reference.fileID),
              AnyNativeFileReference.same(objectID, reference.objectID),
              let stateName = body["state"]?.string,
              let cached = body["cached"]?.bool else {
            throw AnyEngineError.malformedResponse("file status scope or fields")
        }
        guard let state = AnyNativeFileStatus.State(rawValue: stateName),
              state.rawValue.utf8.elementsEqual(stateName.utf8) else {
            throw AnyEngineError.incompatibleSchema("native file state")
        }
        var attempts: Int64 = 0
        if let value = body["attempts"] {
            guard let count = value.integer, count >= 0 else {
                throw AnyEngineError.malformedResponse("file status attempts")
            }
            attempts = count
        }
        var lastError: String?
        if let value = body["lastErr"] {
            guard let message = value.string, message.utf8.count <= 65_536 else {
                throw AnyEngineError.malformedResponse("file status private diagnostic")
            }
            lastError = message.isEmpty ? nil : message
        }
        return .init(reference: reference, state: state, cached: cached,
                     failedAttempts: attempts, lastError: lastError)
    }
}
