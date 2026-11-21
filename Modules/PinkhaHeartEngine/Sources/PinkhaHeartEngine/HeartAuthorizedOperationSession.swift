import Foundation
import PinkhaKit

/// The actual native bridge implements this byte boundary. Fixtures can control
/// it to prove cancellation and lifetime fences, without claiming native proof.
public protocol HeartAuthorizedOperationTransport: Sendable {
    func readAuthorizedOperation(request: Data) async throws -> Data
}

/// One adapter-owned account/Space lifetime. Its owner must invalidate this
/// session synchronously before closing/replacing that native account or Space.
/// Reopening creates a new instance, even when both public IDs are unchanged.
/// Native ACL/history authority remains in Heart; these IDs grant no permission.
@MainActor
public final class HeartAuthorizedOperationSession {
    public nonisolated let scope: TorahOperationReadScope
    private let transport: any HeartAuthorizedOperationTransport
    private var active = true

    public init(accountID: String, spaceID: String, sessionGeneration: UUID = UUID(),
                transport: any HeartAuthorizedOperationTransport) throws {
        self.scope = try TorahOperationReadScope(engine: .heart, accountID: accountID,
                                                 spaceID: spaceID, sessionGeneration: sessionGeneration)
        self.transport = transport
    }

    public func invalidate() { active = false }

    public func isCurrent(_ candidate: TorahOperationReadScope) -> Bool { active && candidate == scope }

    /// UI owners use this immediately before publishing on the same main actor.
    /// No await occurs between the final lifetime check and the publication.
    @discardableResult
    public func publishIfCurrent(_ snapshot: TorahAuthorizedOperationSnapshot,
                                 _ publish: @MainActor (TorahAuthorizedOperationSnapshot) -> Void) -> Bool {
        guard !Task.isCancelled, isCurrent(snapshot.scope) else { return false }
        publish(snapshot)
        return true
    }

    fileprivate func read(operationID: String, expected: TorahOperationReadScope) async throws -> TorahAuthorizedOperationSnapshot {
        try Task.checkCancellation()
        guard isCurrent(expected) else { throw TorahOperationReadError.accountChanged }
        let request = try HeartAuthorizedOperationCodec.request(operationID: operationID, scope: scope)
        let bytes = try await transport.readAuthorizedOperation(request: request)
        try Task.checkCancellation()
        guard isCurrent(expected) else { throw TorahOperationReadError.accountChanged }
        let result = try HeartAuthorizedOperationCodec.decode(bytes, operationID: operationID, scope: scope)
        try Task.checkCancellation()
        guard isCurrent(expected) else { throw TorahOperationReadError.accountChanged }
        return result
    }
}

public struct HeartAuthorizedOperationReader: TorahAuthorizedOperationReading {
    public let scope: TorahOperationReadScope
    private let session: HeartAuthorizedOperationSession

    public init(session: HeartAuthorizedOperationSession) {
        self.session = session
        self.scope = session.scope
    }

    public func readOperation(operationID: String) async throws -> TorahAuthorizedOperationSnapshot {
        try await session.read(operationID: operationID, expected: scope)
    }
}
