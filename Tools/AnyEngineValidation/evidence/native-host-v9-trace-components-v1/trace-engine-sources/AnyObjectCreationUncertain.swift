import Foundation

/// Metadata for an object whose creation was attempted in the original Space.
/// It is a recovery identity, never a committed or UI-navigation receipt.
public struct AnyObjectCreationUncertain: Error, Equatable, Sendable,
    CustomStringConvertible, CustomDebugStringConvertible {
    public enum Stage: String, Sendable {
        case rootPrepared = "root-prepared"
        case rootStored = "root-stored"
        case bootstrapStored = "bootstrap-stored"
    }
    public let spaceID: String
    public let objectID: String
    public let stage: Stage
    public var description: String { "AnyObjectCreationUncertain(recovery metadata redacted)" }
    public var debugDescription: String { description }

    public init(spaceID: String, objectID: String, stage: Stage) throws {
        guard Self.validID(spaceID), Self.validID(objectID) else {
            throw AnyEngineError.malformedResponse("native creation recovery identity")
        }
        self.spaceID = spaceID; self.objectID = objectID; self.stage = stage
    }

    static func decode(status: Int, response: AnyJSON?) -> Self? {
        guard status == 503,
              response?["error"]?["code"]?.string == "pinkha.object_create_uncertain",
              let details = response?["error"]?["details"],
              details["cleanup"]?.string == "not-attempted",
              details["outcome"]?.string == "uncertain",
              let space = details["spaceId"]?.string,
              let object = details["objectId"]?.string,
              let stageText = details["creationStage"]?.string,
              let stage = Stage(rawValue: stageText) else { return nil }
        return try? .init(spaceID: space, objectID: object, stage: stage)
    }

    /// Only the dedicated create route has this exact success-ID contract.
    /// A late account switch suppresses user delivery while retaining the
    /// original-scope recovery ID for the protected journal.
    static func lostConfirmation(method: String, path: [String], response: AnyJSON) -> Self? {
        guard method == "POST", path.count == 5,
              path[0] == "v1", path[1] == "spaces", path[3] == "pinkha", path[4] == "objects",
              let object = response["objectId"]?.string else { return nil }
        return try? .init(spaceID: path[2], objectID: object, stage: .bootstrapStored)
    }

    private static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 && value != "." && value != ".." &&
        value.utf8.allSatisfy {
            (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) ||
            $0 == 45 || $0 == 46 || $0 == 95
        }
    }
}
