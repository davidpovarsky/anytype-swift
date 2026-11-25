import Foundation

public enum AnyNativeFileReferenceError: Error, Equatable, Sendable {
    case invalidIdentity, invalidURI
}

/// The native file namespace is distinct from an object's any:// identity.
/// This represents the complete original file, never a query-selected variant,
/// credential-bearing URL, local gateway address or guessed object URI.
public struct AnyNativeFileReference: Codable, Hashable, Sendable {
    public let spaceID: String
    public let fileID: String
    public var uri: String { "any://f/" + spaceID + "/" + fileID }

    public init(spaceID: String, fileID: String) throws {
        guard Self.component(spaceID), Self.component(fileID) else {
            throw AnyNativeFileReferenceError.invalidIdentity
        }
        self.spaceID = spaceID; self.fileID = fileID
    }

    public init(uri: String) throws {
        guard uri.utf8.count <= 2_057, uri.hasPrefix("any://f/") else {
            throw AnyNativeFileReferenceError.invalidURI
        }
        let parts = uri.dropFirst("any://f/".count).split(separator: "/", omittingEmptySubsequences: false)
        guard parts.count == 2 else { throw AnyNativeFileReferenceError.invalidURI }
        try self.init(spaceID: String(parts[0]), fileID: String(parts[1]))
        guard Data(self.uri.utf8) == Data(uri.utf8) else { throw AnyNativeFileReferenceError.invalidURI }
    }

    private static func component(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1_024 && value != "." && value != ".." &&
        value.utf8.allSatisfy {
            (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) ||
            [45, 46, 95, 126].contains($0)
        }
    }
    private enum CodingKeys: String, CodingKey { case spaceID, fileID }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(spaceID: c.decode(String.self, forKey: .spaceID), fileID: c.decode(String.self, forKey: .fileID))
    }
}
