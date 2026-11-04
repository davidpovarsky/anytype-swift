import Foundation

/// Native derived properties use the existing list wire representation. Their
/// immutable keys select Torah semantics; values are canonical identities, never
/// IDs of Tag option objects. The engine owns and rejects arbitrary value writes.
public struct TorahNativePropertyDefinition: Sendable, Equatable, Hashable {
    public let kind: TorahAssociationKind
    public let key: String
    public let name: String
    public let englishName: String

    public static let wireFormat = 11
    public static let engineVersion = 1
    public static let engineVersionKey = "_pinkhaTorahProjectionVersion"
    public static let readinessKey = "_pinkhaTorahReady"
    public static let labelsKey = "_pinkhaTorahLabels"
    public static let statusKey = "_pinkhaTorahState"

    public static let all: [Self] = [
        Self(kind: .ref, key: "pinkhaTorahSources", name: "מקור/ות", englishName: "Source(s)"),
        Self(kind: .topic, key: "pinkhaTorahTopics", name: "נושא", englishName: "Topic(s)"),
        Self(kind: .word, key: "pinkhaTorahWords", name: "מילה / ערך", englishName: "Word / entry")
    ]

    public static func definition(for key: String) -> Self? {
        all.first { $0.key == key }
    }
}

public struct TorahNativePropertyRegistration: Sendable, Equatable {
    public let spaceId: String
    public let propertyIdsByKey: [String: String]

    public init(spaceId: String, propertyIdsByKey: [String: String]) {
        self.spaceId = spaceId
        self.propertyIdsByKey = propertyIdsByKey
    }
}

public struct TorahNativePropertyDescriptor: Sendable, Equatable {
    public let id: String
    public let key: String
    public let spaceId: String
    public let format: Int
    public let isReadOnlyValue: Bool

    public init(id: String, key: String, spaceId: String, format: Int, isReadOnlyValue: Bool) {
        self.id = id
        self.key = key
        self.spaceId = spaceId
        self.format = format
        self.isReadOnlyValue = isReadOnlyValue
    }
}

public enum TorahNativeSchemaError: Error, Sendable, Equatable, LocalizedError, CustomNSError {
    case unsupportedEngine
    case invalidManifest
    case invalidProperty(String)

    public static var errorDomain: String { "PinkhaKit.TorahNativeSchemaError" }

    public var errorCode: Int {
        switch self {
        case .unsupportedEngine: 1
        case .invalidManifest: 2
        case .invalidProperty: 3
        }
    }

    public var errorDescription: String? {
        switch self {
        case .unsupportedEngine:
            "מנוע המאפיינים התורניים אינו זמין בגרסה המותקנת."
        case .invalidManifest:
            "אימות סכמת המאפיינים התורניים של המרחב נכשל (manifest/version)."
        case .invalidProperty(let key):
            "אימות רישום המאפיין התורני נכשל: \(key)."
        }
    }

    public var errorUserInfo: [String: Any] {
        var info: [String: Any] = [:]
        if let desc = errorDescription {
            info[NSLocalizedDescriptionKey] = desc
        }
        switch self {
        case .invalidProperty(let key):
            info["propertyKey"] = key
        default:
            break
        }
        return info
    }
}

public protocol TorahNativePropertyProvisioningStore: Sendable {
    func engineVersion(spaceId: String, manifestObjectId: String) async throws -> Int
    func property(key: String, spaceId: String) async throws -> TorahNativePropertyDescriptor?
    func installProperty(_ definition: TorahNativePropertyDefinition, spaceId: String) async throws -> TorahNativePropertyDescriptor
    func attachedPropertyIds(typeId: String, spaceId: String) async throws -> [String]
    func addRecommendedProperties(_ definitions: [TorahNativePropertyDefinition], typeId: String, spaceId: String) async throws
}

/// Metadata-only upgrade of already-provisioned Spaces. Fixed native keys and
/// readback make retries independent of a partially saved app manifest. Existing
/// Type/template IDs, canonical keys and all user associations remain untouched.
public actor TorahNativeSchemaProvisioner {
    private let store: any TorahNativePropertyProvisioningStore
    private var inFlight: [String: Task<TorahNativePropertyRegistration, Error>] = [:]

    public init(store: any TorahNativePropertyProvisioningStore) {
        self.store = store
    }

    public func provision(manifest: PinkhaSpaceManifest) async throws -> TorahNativePropertyRegistration {
        guard manifest.isFullyProvisioned,
              manifest.schemaVersion == PinkhaSpaceManifest.currentSchemaVersion,
              !manifest.spaceId.isEmpty,
              let manifestId = manifest.manifestObjectId, !manifestId.isEmpty else {
            throw TorahNativeSchemaError.invalidManifest
        }
        if let task = inFlight[manifest.spaceId] { return try await task.value }
        let store = store
        let task = Task { try await Self.install(manifest: manifest, manifestId: manifestId, store: store) }
        inFlight[manifest.spaceId] = task
        defer { inFlight[manifest.spaceId] = nil }
        return try await task.value
    }

    private static func install(
        manifest: PinkhaSpaceManifest,
        manifestId: String,
        store: any TorahNativePropertyProvisioningStore
    ) async throws -> TorahNativePropertyRegistration {
        guard try await store.engineVersion(spaceId: manifest.spaceId, manifestObjectId: manifestId)
                == TorahNativePropertyDefinition.engineVersion else {
            throw TorahNativeSchemaError.unsupportedEngine
        }
        var idsByKey: [String: String] = [:]
        for definition in TorahNativePropertyDefinition.all {
            let found = try await store.property(key: definition.key, spaceId: manifest.spaceId)
            let property: TorahNativePropertyDescriptor
            if let found {
                property = found
            } else {
                _ = try await store.installProperty(definition, spaceId: manifest.spaceId)
                guard let readback = try await store.property(key: definition.key, spaceId: manifest.spaceId) else {
                    throw TorahNativeSchemaError.invalidProperty(definition.key)
                }
                property = readback
            }
            guard !property.id.isEmpty, property.key == definition.key,
                  property.spaceId == manifest.spaceId,
                  property.format == TorahNativePropertyDefinition.wireFormat,
                  property.isReadOnlyValue else {
                throw TorahNativeSchemaError.invalidProperty(definition.key)
            }
            idsByKey[definition.key] = property.id
        }
        let typeIds = [PinkhaSchemaRoles.chiddushKey, PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey]
            .compactMap { manifest.registeredDocumentTypes[$0] }
        guard typeIds.count == 3, Set(typeIds).count == 3, !typeIds.contains("") else {
            throw TorahNativeSchemaError.invalidManifest
        }
        let nativeIds = TorahNativePropertyDefinition.all.compactMap { idsByKey[$0.key] }
        for typeId in typeIds {
            let current = try await store.attachedPropertyIds(typeId: typeId, spaceId: manifest.spaceId)
            let seen = Set(current)
            let additions = TorahNativePropertyDefinition.all.filter { definition in
                guard let id = idsByKey[definition.key] else { return false }
                return !seen.contains(id)
            }
            if !additions.isEmpty {
                try await store.addRecommendedProperties(additions, typeId: typeId, spaceId: manifest.spaceId)
                let expected = Set(current + nativeIds)
                var satisfied = false
                let clock = ContinuousClock()
                let deadline = clock.now.advanced(by: .seconds(10))
                repeat {
                    let readback = try await store.attachedPropertyIds(typeId: typeId, spaceId: manifest.spaceId)
                    if expected.isSubset(of: Set(readback)) {
                        satisfied = true
                        break
                    }
                    try await Task.sleep(for: .milliseconds(100))
                } while clock.now < deadline
                guard satisfied else {
                    throw TorahNativeSchemaError.invalidProperty(typeId)
                }
            }
        }
        return TorahNativePropertyRegistration(spaceId: manifest.spaceId, propertyIdsByKey: idsByKey)
    }
}
