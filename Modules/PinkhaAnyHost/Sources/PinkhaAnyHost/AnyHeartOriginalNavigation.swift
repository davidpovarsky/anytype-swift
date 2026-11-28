import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Classification of a captured Heart homepage value. An object reference
/// still requires its original-source mapping and current destination access.
public enum AnyHeartOriginalHomeValue: Sendable {
    case absent
    case empty
    case builtIn(BuiltIn)
    case sourceObject(String)
    case unsupported(AnyJSON)

    public enum BuiltIn: String, Codable, CaseIterable, Sendable {
        case widgets, graph, lastOpened, chat
    }

    static func project(_ value: AnyJSON?) -> Self {
        guard let value else { return .absent }
        guard let text = value.string else { return .unsupported(value) }
        if text.isEmpty { return .empty }
        for item in BuiltIn.allCases where item.rawValue.utf8.elementsEqual(text.utf8) {
            return .builtIn(item)
        }
        guard text.utf8.count <= 4096,
              text.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }) else {
            return .unsupported(value)
        }
        return .sourceObject(text)
    }
}

/// The four original navigation contexts retain their native identity. They
/// are read through the original signed catalog, not converted into Pages.
public struct AnyHeartOriginalNavigationBinding: Codable, Equatable, Sendable {
    public enum Context: String, Codable, CaseIterable, Sendable {
        case workspace = "ws"
        case home, archive, widget

        public var nativeType: Int64 {
            switch self {
            case .workspace: 518
            case .home: 32
            case .archive: 48
            case .widget: 112
            }
        }
    }

    public static let contract = "pinkha-heart-original-navigation-v1"
    public let context: Context
    public let evidence: AnyDestinationDefinitionEvidence
    public let readContract: String
    public var permitsDestinationWrites: Bool { false }
    public var provesCurrentHomeSelection: Bool { false }

    public init(evidence: AnyDestinationDefinitionEvidence) throws {
        guard evidence.snapshot.issues.isEmpty,
              let context = Context.allCases.first(where: {
                  $0.nativeType == evidence.snapshot.nativeType
                    && $0.rawValue.utf8.elementsEqual(evidence.snapshot.uniqueKey.utf8)
              }) else {
            throw AnyDestinationMigrationError.invalidPlan("original navigation context")
        }
        self.context = context
        self.evidence = evidence
        self.readContract = Self.contract
    }

    public func requireSource(_ source: AnyDestinationSourceBinding) throws {
        try evidence.requireSource(source, objectID: evidence.sourceObjectID)
    }

    private enum CodingKeys: String, CodingKey { case context, evidence, readContract }

    public init(from decoder: any Decoder) throws {
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        let context = try fields.decode(Context.self, forKey: .context)
        let contract = try fields.decode(String.self, forKey: .readContract)
        try self.init(evidence: fields.decode(AnyDestinationDefinitionEvidence.self, forKey: .evidence))
        guard self.context == context,
              contract.utf8.elementsEqual(Self.contract.utf8) else {
            throw AnyDestinationMigrationError.invalidPlan("original navigation contract")
        }
    }
}

public struct AnyHeartOriginalNavigationSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let binding: AnyHeartOriginalNavigationBinding
    public let catalog: AnyNativeImportedCatalogSnapshot
    public let homepage: AnyHeartOriginalHomeValue
    public let legacyDashboard: AnyHeartOriginalHomeValue
    public var permitsDestinationWrites: Bool { false }
    public var provesCurrentHomeSelection: Bool { false }

    /// A present empty or unsupported value is still an explicit original
    /// field. It must not silently activate a legacy dashboard or UI default.
    public var hasExplicitHomepage: Bool {
        if case .absent = homepage { false } else { true }
    }

    static func project(_ key: String, snapshot: AnyHeartNativeSnapshotView) -> AnyHeartOriginalHomeValue {
        let value = snapshot.details.first { $0.key.utf8.elementsEqual(key.utf8) }?.value
        return AnyHeartOriginalHomeValue.project(value)
    }
}

/// This facade inherits current membership, immutable intent, signed creation,
/// double-read and lease checks from the common imported-catalog reader.
public struct AnyHeartOriginalNavigationStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let catalog: AnyNativeImportedCatalogStore

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        self.workspace = workspace
        self.catalog = try .init(client: client, workspace: workspace)
    }

    public func read(_ binding: AnyHeartOriginalNavigationBinding,
                     directory: AnyNativeImportedCatalogDirectory,
                     lease: AnyHostLease) async throws -> AnyHeartOriginalNavigationSnapshot {
        try binding.requireSource(directory.source)
        let original = try await catalog.read(sourceObjectID: binding.evidence.sourceObjectID,
            directory: directory, lease: lease)
        guard let evidence = original.entry.evidence, evidence == binding.evidence else {
            throw AnyNativeImportedCatalogError.changedSource(binding.evidence.sourceObjectID)
        }
        try await lease.validate()
        try Task.checkCancellation()
        return .init(workspace: workspace, generation: lease.generation,
            engineStartedAt: lease.engineStartedAt, binding: binding, catalog: original,
            homepage: AnyHeartOriginalNavigationSnapshot.project("homepage", snapshot: evidence.snapshot),
            legacyDashboard: AnyHeartOriginalNavigationSnapshot.project("spaceDashboardId", snapshot: evidence.snapshot))
    }
}
