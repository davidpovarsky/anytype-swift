import Foundation
import HanlinHostContracts

/// Additive metadata for a native root whose requested business initialization
/// was not verified. The original v1 journal Entry wire format is unchanged.
struct PinkhaHanlinKnownObjectRecovery: Codable, Equatable, Sendable {
    static let suffix = ".known-object"
    let version: Int
    let identity: PinkhaHanlinWriteIdentity
    let createdObjectReference: String

    static func decode(_ bytes: Data, fileName: String,
                       namespace: HanlinConversationNamespace) throws -> Self {
        let value = try JSONDecoder().decode(Self.self, from: bytes)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try value.identity.validate()
        guard value.version == 1, value.identity.session.context.namespace == namespace,
              !value.createdObjectReference.isEmpty, value.createdObjectReference.utf8.count <= 256,
              !value.createdObjectReference.utf8.contains(0),
              fileName == value.identity.key + suffix, try encoder.encode(value) == bytes else {
            throw PinkhaHanlinWriteError.corruptJournal
        }
        return value
    }

    func validate(against entry: PinkhaHanlinWriteJournal.Entry) throws {
        try identity.validate()
        guard version == 1, !createdObjectReference.isEmpty,
              createdObjectReference.utf8.count <= 256,
              !createdObjectReference.utf8.contains(0) else {
            throw PinkhaHanlinWriteError.corruptJournal
        }
        guard entry.version == 1, identity == entry.identity,
              entry.effect != .notDispatched else { throw PinkhaHanlinWriteError.conflict }
        if entry.effect == .committed {
            guard entry.createdObjectReference.map({ Data($0.utf8) }) == Data(createdObjectReference.utf8) else {
                throw PinkhaHanlinWriteError.conflict
            }
        } else {
            guard entry.createdObjectReference == nil else { throw PinkhaHanlinWriteError.corruptJournal }
        }
    }
}
