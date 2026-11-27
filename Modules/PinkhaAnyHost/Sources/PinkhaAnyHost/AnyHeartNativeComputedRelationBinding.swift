import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// An exact captured Heart relation whose current value is read from the
/// native link index. This is a read contract, not an SDK property declaration:
/// it has no native property owner/key and grants no mutation authority.
public struct AnyHeartNativeComputedRelationBinding: Codable, Equatable, Sendable {
    public static let contract = "pinkha-heart-native-link-index-relation-v1"

    public enum Role: String, Codable, CaseIterable, Sendable {
        case outgoingLinks = "links"
        case backlinks

        var sourceName: String {
            switch self {
            case .outgoingLinks: "Links"
            case .backlinks: "Backlinks"
            }
        }

        var sourceDescription: String {
            switch self {
            case .outgoingLinks: "Outgoing links"
            case .backlinks: "List of links coming to object"
            }
        }
    }

    public let evidence: AnyDestinationDefinitionEvidence
    public let role: Role
    public let readContract: String
    public var sourceRelationKey: String { role.rawValue }
    public var sourceHidden: Bool? { evidence.snapshot.details["isHidden"]?.bool }
    public var permitsDestinationWrites: Bool { false }
    public var visibilityKey: String { "derived:v1:" + Self.contract + ":" + role.rawValue }

    public init(evidence: AnyDestinationDefinitionEvidence) throws {
        self.evidence = evidence
        guard let key = evidence.snapshot.details["relationKey"]?.string,
              let role = Role(rawValue: key) else {
            throw AnyDestinationMigrationError.invalidPlan("unknown native link-index source relation")
        }
        self.role = role
        self.readContract = Self.contract
        try validate()
    }

    func requireSource(_ source: AnyDestinationSourceBinding, objectID: String) throws {
        try evidence.requireSource(source, objectID: objectID)
    }

    private func validate() throws {
        let row = evidence.snapshot, details = row.details
        guard readContract == Self.contract,
              row.nativeType == 521,
              Data(row.uniqueKey.utf8) == Data(("rel-" + role.rawValue).utf8),
              row.issues.isEmpty,
              details["relationKey"] == .string(role.rawValue),
              details["relationFormat"] == .integer(100),
              details["relationMaxCount"] == .integer(0),
              details["relationReadonlyValue"] == .bool(true),
              details["relationDefaultValue"] == .null,
              details["relationFormatIncludeTime"] == .bool(false),
              details["relationFormatObjectTypes"] == .array([]),
              details["name"] == .string(role.sourceName),
              details["description"] == .string(role.sourceDescription),
              details["isArchived"] == nil || details["isArchived"] == .bool(false),
              details["isReadonly"] == nil || details["isReadonly"] == .bool(false),
              details["isHidden"] == nil || details["isHidden"]?.bool != nil,
              details["internalFlags"] == nil || details["internalFlags"] == .array([]),
              Set(details.keys).isSubset(of: AnyDestinationDefinitionChecks.nameDetailFields) else {
            throw AnyDestinationMigrationError.invalidPlan("native link-index source relation contract")
        }
    }

    private enum CodingKeys: String, CodingKey { case evidence, role, readContract }

    public init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        evidence = try container.decode(AnyDestinationDefinitionEvidence.self, forKey: .evidence)
        role = try container.decode(Role.self, forKey: .role)
        readContract = try container.decode(String.self, forKey: .readContract)
        try validate()
    }
}
