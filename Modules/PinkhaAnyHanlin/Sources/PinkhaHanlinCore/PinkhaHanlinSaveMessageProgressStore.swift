import Foundation

/// Implemented by the ORIGINAL protected Hanlin journal owner. The generic
/// reservation must already exist and match the complete original identity.
/// Progress shares its file lock, data protection, namespace and removal/drain
/// lifetime. No model-selected path or independent journal is permitted.
public protocol PinkhaHanlinSaveMessageProgressStore: Actor {
    func saveMessageProgress(for identity: PinkhaHanlinWriteIdentity) async throws -> PinkhaHanlinSaveMessageProgress?
    func reserveSaveMessage(_ initial: PinkhaHanlinSaveMessageProgress) async throws
    func advanceSaveMessage(_ expected: PinkhaHanlinSaveMessageProgress,
                            event: PinkhaHanlinSaveMessageProgress.Event) async throws -> PinkhaHanlinSaveMessageProgress
}

/// A bounded, append-only metadata event. The store checks the expected state
/// inside its actor and flushes this record BEFORE exposing the new state.
/// Loading replays every contiguous event against the retained initial manifest;
/// missing/reordered/foreign/tampered bytes fail closed without rewriting history.
public struct PinkhaHanlinSaveMessageProgressRecord: Codable, Equatable, Sendable {
    public let version: Int
    public let identitySHA256: String
    public let manifestSHA256: String
    public let sequence: Int
    public let previousSHA256: String
    public let event: PinkhaHanlinSaveMessageProgress.Event
    public let resultingSHA256: String

    public init(previous: PinkhaHanlinSaveMessageProgress,
                event: PinkhaHanlinSaveMessageProgress.Event) throws {
        let next = try previous.applying(event)
        guard next.sequence == previous.sequence + 1 else {
            throw PinkhaHanlinSaveMessageError.invalidTransition
        }
        version = 1
        identitySHA256 = previous.manifest.identitySHA256
        manifestSHA256 = try previous.manifest.canonicalSHA256()
        sequence = next.sequence
        previousSHA256 = try previous.canonicalSHA256()
        self.event = event
        resultingSHA256 = try next.canonicalSHA256()
    }

    public func replay(on previous: PinkhaHanlinSaveMessageProgress) throws -> PinkhaHanlinSaveMessageProgress {
        try previous.validate()
        guard version == 1, sequence == previous.sequence + 1,
              sequence <= PinkhaHanlinSaveMessageProgress.maximumEvents,
              identitySHA256 == previous.manifest.identitySHA256,
              manifestSHA256 == (try previous.manifest.canonicalSHA256()),
              previousSHA256 == (try previous.canonicalSHA256()) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        let next = try previous.applying(event)
        guard next.sequence == sequence, resultingSHA256 == (try next.canonicalSHA256()) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        return next
    }

    public func canonicalBytes() throws -> Data {
        guard version == 1, (1...PinkhaHanlinSaveMessageProgress.maximumEvents).contains(sequence),
              [identitySHA256, manifestSHA256, previousSHA256, resultingSHA256]
                .allSatisfy(PinkhaHanlinWriteIdentity.isDigest) else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        let bytes = try PinkhaHanlinSaveMessagePlan.canonicalBytes(self)
        guard bytes.count <= 32_768 else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        return bytes
    }

    public static func decodeCanonical(_ bytes: Data,
                                      previous: PinkhaHanlinSaveMessageProgress) throws -> Self {
        guard bytes.count <= 32_768 else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        let result = try JSONDecoder().decode(Self.self, from: bytes)
        guard try result.canonicalBytes() == bytes else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        _ = try result.replay(on: previous)
        return result
    }
}
