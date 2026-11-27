import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// A condition read from the current native Bookmark definitions. The native
/// engine owns its opaque proof and rechecks it during ordinary object creation.
/// `canWrite` is an observation, never an authorization for a later mutation.
public struct AnyNativeBookmarkCreationFrame: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let workspace: AnyTorahWorkspace
    public let typeID: String
    public let collections: [String]
    public let propertyOwnerID: String
    public let propertyID: String
    public let canWrite: Bool
    internal let definitionFrame: String

    public var description: String { "AnyNativeBookmarkCreationFrame(redacted)" }
    public var debugDescription: String { description }

    internal init(value: AnyJSON, workspace: AnyTorahWorkspace,
                  typeID: String, requestedCollections: [String]) throws {
        try Self.validateRequest(workspace: workspace, typeID: typeID, collections: requestedCollections)
        let keys: Set<String> = ["contract", "version", "accountId", "spaceId", "typeId",
                                 "collections", "propertyOwnerId", "propertyId", "canWrite", "frame"]
        guard let object = value.object, Set(object.keys) == keys,
              value["contract"]?.string == "pinkha-native-bookmark-create-v1",
              value["version"]?.integer == 1,
              let accountID = value["accountId"]?.string,
              let spaceID = value["spaceId"]?.string,
              let returnedTypeID = value["typeId"]?.string,
              Self.validObjectID(accountID), Self.validObjectID(spaceID), Self.validObjectID(returnedTypeID),
              Self.sameBytes(accountID, workspace.accountID), Self.sameBytes(spaceID, workspace.spaceID),
              Self.sameBytes(returnedTypeID, typeID),
              let owner = value["propertyOwnerId"]?.string, Self.validObjectID(owner),
              owner != "any", owner != "bin", owner != "template", !Self.sameBytes(owner, typeID),
              let property = value["propertyId"]?.string,
              !property.isEmpty, property.utf8.count <= 1_024, !property.utf8.contains(0),
              let returned = value["collections"]?.array, returned.count <= 128,
              let canWrite = value["canWrite"]?.bool,
              let token = value["frame"]?.string else {
            throw AnyEngineError.malformedResponse("Bookmark creation frame")
        }
        var actual: [String] = []
        for item in returned {
            guard let id = item.string, Self.validCollection(id, typeID: typeID) else {
                throw AnyEngineError.malformedResponse("Bookmark creation frame collections")
            }
            actual.append(id)
        }
        // IDs are printable ASCII. Explicit byte ordering also documents the
        // native Go contract and avoids locale or Unicode normalization rules.
        let expected = Set(requestedCollections + [owner]).sorted {
            $0.utf8.lexicographicallyPrecedes($1.utf8)
        }
        guard expected.count <= 128, actual.count == expected.count,
              zip(actual, expected).allSatisfy({ Self.sameBytes($0.0, $0.1) }) else {
            throw AnyEngineError.malformedResponse("Bookmark creation frame collection binding")
        }
        try Self.validateToken(token)
        self.workspace = workspace
        self.typeID = typeID
        self.collections = actual
        self.propertyOwnerID = owner
        self.propertyID = property
        self.canWrite = canWrite
        self.definitionFrame = token
    }

    /// Freezes this exact condition and the supplied values. This performs no
    /// native write or journal reservation. A later read cannot replace the
    /// condition inside the returned immutable creation intent.
    public func makeCreationIntent(mutationID: String, initialProperties: AnyJSON) throws
        -> AnyNativeObjectCreationIntent {
        guard let groups = initialProperties.object,
              groups.allSatisfy({ entry in
                  entry.value.object != nil &&
                  (["any", typeID] + collections).contains { Self.sameBytes($0, entry.key) }
              }),
              let owner = groups.first(where: { Self.sameBytes($0.key, propertyOwnerID) })?.value.object,
              owner.first(where: { Self.sameBytes($0.key, propertyID) })?.value.string != nil else {
            throw AnyNativeCreationError.invalidIntent
        }
        let any = groups.first(where: { Self.sameBytes($0.key, "any") })?.value.object
        guard any?.keys.contains(where: { Self.sameBytes($0, "template") }) != true else {
            throw AnyNativeCreationError.invalidIntent
        }
        return try .init(workspace: workspace, mutationID: mutationID, typeID: typeID,
                         collections: collections, initialProperties: initialProperties,
                         bookmarkDefinitionFrame: definitionFrame)
    }

    /// Checks transport encoding only. Inner fields, definition eligibility,
    /// current definition state and authority remain native responsibilities.
    internal static func validateToken(_ token: String) throws {
        let count = token.utf8.count
        guard (1...87_382).contains(count), count % 4 != 1,
              token.utf8.allSatisfy({ byte in
                  (65...90).contains(byte) || (97...122).contains(byte) ||
                  (48...57).contains(byte) || byte == 45 || byte == 95
              }) else {
            throw AnyEngineError.malformedResponse("Bookmark creation frame encoding")
        }
        let padded = token.replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/") + String(repeating: "=", count: (4 - count % 4) % 4)
        guard let raw = Data(base64Encoded: padded), !raw.isEmpty, raw.count <= 65_536 else {
            throw AnyEngineError.malformedResponse("Bookmark creation frame encoding")
        }
        let canonical = raw.base64EncodedString().replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
        guard sameBytes(canonical, token) else {
            throw AnyEngineError.malformedResponse("Bookmark creation frame encoding")
        }
    }

    fileprivate static func validateRequest(workspace: AnyTorahWorkspace, typeID: String,
                                            collections: [String]) throws {
        try validateWorkspace(workspace)
        guard validObjectID(typeID), collections.count <= 128,
              collections.allSatisfy({ validCollection($0, typeID: typeID) }) else {
            throw AnyEngineError.invalidOperation("Bookmark creation frame request")
        }
    }

    fileprivate static func validateWorkspace(_ workspace: AnyTorahWorkspace) throws {
        guard validObjectID(workspace.accountID), validObjectID(workspace.spaceID) else {
            throw AnyEngineError.invalidIdentity("Bookmark creation frame workspace")
        }
    }

    private static func validObjectID(_ value: String) -> Bool {
        (1...1_024).contains(value.utf8.count) && value.utf8.allSatisfy { (0x21...0x7e).contains($0) }
    }

    private static func validCollection(_ value: String, typeID: String) -> Bool {
        validObjectID(value) && value != "any" && value != "bin" && value != "template" && !sameBytes(value, typeID)
    }

    fileprivate static func sameBytes(_ lhs: String, _ rhs: String) -> Bool {
        lhs.utf8.elementsEqual(rhs.utf8)
    }
}

/// A read-only native operation, although its bounded request uses HTTP POST.
/// The same side-effect-free read authorization is checked at dispatch, after
/// each response and immediately before returning the validated private frame.
/// It must check the original owner's monotonic lifetime, never reacquire a new
/// owner or revive a retired lease while this operation is suspended.
public struct AnyNativeBookmarkCreationFrameReader: Sendable {
    private let client: AnyHTTPClient
    public let workspace: AnyTorahWorkspace

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard AnyNativeBookmarkCreationFrame.sameBytes(client.expectedAccountID, workspace.accountID) else {
            throw AnyEngineError.accountChanged
        }
        try AnyNativeBookmarkCreationFrame.validateWorkspace(workspace)
        self.client = client
        self.workspace = workspace
    }

    public func frame(typeID: String, collections: [String] = [],
                      authorizeRead: @escaping @Sendable () async throws -> Void) async throws
        -> AnyNativeBookmarkCreationFrame {
        try Task.checkCancellation()
        try AnyNativeBookmarkCreationFrame.validateRequest(workspace: workspace, typeID: typeID, collections: collections)
        let capabilities = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"],
            maximumResponseBytes: 256 << 10, validateResponse: authorizeRead, authorize: authorizeRead)
        guard capabilities["contract"]?.string == "pinkha-torah-native-v1",
              capabilities["currentWriterObjectCreate"]?.integer == 1,
              capabilities["nativeBookmarkObjectCreate"]?.integer == 1 else {
            throw AnyEngineError.incompatibleSchema("native Bookmark definition condition unavailable")
        }
        try Task.checkCancellation()
        let value = try await client.requestJSON(method: "POST",
            path: ["v1", "spaces", workspace.spaceID, "pinkha", "bookmark-create-frame"],
            body: .object(["typeId": .string(typeID), "collections": .array(collections.map(AnyJSON.string))]),
            maximumResponseBytes: 256 << 10, validateResponse: authorizeRead, authorize: authorizeRead)
        let frame = try AnyNativeBookmarkCreationFrame(value: value, workspace: workspace,
            typeID: typeID, requestedCollections: collections)
        try Task.checkCancellation()
        try await authorizeRead()
        try Task.checkCancellation()
        // The final asynchronous owner check can itself span an account
        // transition. Refuse that changed native account before delivery too.
        try await client.checkAccount()
        try Task.checkCancellation()
        // The account read is another suspension point. Recheck the same
        // monotonic owner after it, without refreshing that owner's lifetime.
        try await authorizeRead()
        try Task.checkCancellation()
        return frame
    }
}
