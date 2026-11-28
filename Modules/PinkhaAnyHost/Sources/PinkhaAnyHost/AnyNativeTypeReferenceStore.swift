import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public struct AnyNativeTypeReferenceDefinitionSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let presentation: AnyNativeTypeReferencePresentation
    /// nil is a source-only Type description, not a destination Type endpoint.
    public let currentType: AnyNativeImportedDefinitionSnapshot?
    /// Only actual mapped properties are read. Computed providers remain
    /// explicit typed references and unresolved fields have no invented value.
    public let currentProperties: [AnyNativeImportedDefinitionSnapshot]
    public var permitsDestinationWrites: Bool { false }
    public var qualifiesOriginalFamilyBehavior: Bool { false }
}

public enum AnyNativeTypeReferenceValue: Sendable {
    case property(value: AnyJSON?, definition: AnyNativePropertyDefinition,
                  canonicalValueSemantics: AnyNativeCanonicalValueSemantics?)
    case computed(AnyNativeComputedRelationSnapshot)
}

public struct AnyNativeTypeReferenceValueSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let objectID: String
    public let sourceTypeObjectID: String
    public let reference: AnyNativeTypeReference
    public let value: AnyNativeTypeReferenceValue
    public var permitsDestinationWrites: Bool { false }
}

/// Uses existing native definition/property/link-index readers. It creates no
/// property, Type, provider alias, journal or storage subsystem. Equal reads
/// bound a local observation; they are not a cross-object/peer transaction and
/// never establish the original encrypted history or a missing family adapter.
public struct AnyNativeTypeReferenceStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let definitions: AnyNativeImportedDefinitionStore
    private let properties: AnyNativePropertyStore
    private let computed: AnyNativeComputedRelationStore

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                policy: AnyNativePropertyPolicy) throws {
        guard Data(client.expectedAccountID.utf8) == Data(workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        self.workspace = workspace
        definitions = try .init(client: client, workspace: workspace)
        properties = try .init(client: client, workspace: workspace, policy: policy)
        computed = try .init(client: client, workspace: workspace)
    }

    /// The source presentation stays complete even when its native Type does
    /// not exist yet. Such a result explicitly has currentType=nil; every
    /// mapped property still goes through its actual immutable-intent reader.
    public func readDefinition(sourceTypeObjectID: String, plan: AnyHeartNativeTypeReferencePlan,
                               lease: AnyHostLease) async throws -> AnyNativeTypeReferenceDefinitionSnapshot {
        try await validate(plan, lease: lease)
        guard let presentation = plan.presentation(sourceTypeObjectID: sourceTypeObjectID) else {
            throw AnyNativeTypeReferenceError.missingSourceDefinition(sourceTypeObjectID)
        }
        let typeBefore = try await type(presentation, plan: plan, lease: lease)
        var values: [AnyNativeImportedDefinitionSnapshot] = [], seen = Set<Data>()
        for reference in presentation.groups.flatMap(\.references) + presentation.definitionHidden {
            guard seen.insert(Data(reference.sourceObjectID.utf8)).inserted,
                  case .property = reference.target else { continue }
            let value = try await definitions.read(sourceObjectID: reference.sourceObjectID,
                directory: plan.directory, lease: lease)
            try Self.requireProperty(value, reference: reference)
            values.append(value)
        }
        let typeAfter = try await type(presentation, plan: plan, lease: lease)
        try Self.requireSameType(typeBefore, typeAfter, sourceID: sourceTypeObjectID)
        try await validate(plan, lease: lease)
        return .init(workspace: workspace, generation: lease.generation,
            engineStartedAt: lease.engineStartedAt, presentation: presentation,
            currentType: typeAfter, currentProperties: values)
    }

    /// An unresolved reference cannot be read as null/empty, and a source-only
    /// Type cannot be applied to an arbitrary destination object. The existing
    /// source-to-native Type binding must match the object's current membership.
    public func readValue(sourceTypeObjectID: String, sourceRelationObjectID: String,
                          objectID: String, plan: AnyHeartNativeTypeReferencePlan,
                          lease: AnyHostLease) async throws -> AnyNativeTypeReferenceValueSnapshot {
        try await validate(plan, lease: lease)
        guard let presentation = plan.presentation(sourceTypeObjectID: sourceTypeObjectID) else {
            throw AnyNativeTypeReferenceError.missingSourceDefinition(sourceTypeObjectID)
        }
        guard let typeID = presentation.currentNativeTypeID else {
            throw AnyNativeTypeReferenceError.unmappedType(sourceTypeObjectID)
        }
        guard AnyEditorBlock.validID(objectID),
              let reference = (presentation.groups.flatMap(\.references) + presentation.definitionHidden).first(where: {
                  Data($0.sourceObjectID.utf8) == Data(sourceRelationObjectID.utf8)
              }) else { throw AnyNativeTypeReferenceError.missingSourceDefinition(sourceRelationObjectID) }
        guard reference.isExecutable else { throw AnyNativeTypeReferenceError.unavailableReference(sourceRelationObjectID) }
        let typeBefore = try await type(presentation, plan: plan, lease: lease)
        let before = try await properties.read(objectID: objectID, lease: lease)
        try Self.requireMembership(before, typeID: typeID, objectID: objectID, workspace: workspace, lease: lease)
        let value: AnyNativeTypeReferenceValue
        let propertyBefore: AnyNativeImportedDefinitionSnapshot?
        switch reference.target {
        case .property(let binding):
            let current = try await definitions.read(sourceObjectID: sourceRelationObjectID,
                directory: plan.directory, lease: lease)
            let definition = try Self.requireProperty(current, reference: reference)
            guard let row = before.rows.first(where: {
                Data($0.definition.key.ownerID.utf8) == Data(binding.key.ownerID.utf8) &&
                Data($0.definition.key.propertyID.utf8) == Data(binding.key.propertyID.utf8)
            }), try AnyHostCanonical.bytes(row.definition.raw, maximumBytes: 131_072) ==
                    AnyHostCanonical.bytes(definition.raw, maximumBytes: 131_072) else {
                throw AnyNativeTypeReferenceError.changedCurrentDefinition(sourceRelationObjectID)
            }
            value = .property(value: row.value, definition: definition,
                canonicalValueSemantics: binding.canonicalValueSemantics)
            propertyBefore = current
        case .computed(let binding):
            value = .computed(try await computed.read(binding, objectID: objectID, lease: lease))
            propertyBefore = nil
        case .unresolved:
            throw AnyNativeTypeReferenceError.unavailableReference(sourceRelationObjectID)
        }
        let after = try await properties.read(objectID: objectID, lease: lease)
        try Self.requireMembership(after, typeID: typeID, objectID: objectID, workspace: workspace, lease: lease)
        guard try AnyHostCanonical.bytes(before.raw, maximumBytes: 4_194_304) ==
            AnyHostCanonical.bytes(after.raw, maximumBytes: 4_194_304) else { throw AnyHostError.changedDocument }
        if let propertyBefore {
            let currentAfter = try await definitions.read(sourceObjectID: sourceRelationObjectID,
                directory: plan.directory, lease: lease)
            let definitionAfter = try Self.requireProperty(currentAfter, reference: reference)
            guard try AnyHostCanonical.bytes(propertyBefore.raw, maximumBytes: 131_072) ==
                    AnyHostCanonical.bytes(currentAfter.raw, maximumBytes: 131_072),
                  propertyBefore.nativeCreationOutcome == currentAfter.nativeCreationOutcome,
                  let afterRow = after.rows.first(where: {
                      Data($0.definition.key.ownerID.utf8) == Data(definitionAfter.key.ownerID.utf8) &&
                      Data($0.definition.key.propertyID.utf8) == Data(definitionAfter.key.propertyID.utf8)
                  }), try AnyHostCanonical.bytes(afterRow.definition.raw, maximumBytes: 131_072) ==
                    AnyHostCanonical.bytes(definitionAfter.raw, maximumBytes: 131_072) else {
                throw AnyNativeTypeReferenceError.changedCurrentDefinition(sourceRelationObjectID)
            }
        }
        let typeAfter = try await type(presentation, plan: plan, lease: lease)
        try Self.requireSameType(typeBefore, typeAfter, sourceID: sourceTypeObjectID)
        try await validate(plan, lease: lease)
        return .init(workspace: workspace, generation: lease.generation,
            engineStartedAt: lease.engineStartedAt, objectID: objectID,
            sourceTypeObjectID: sourceTypeObjectID, reference: reference, value: value)
    }

    private func validate(_ plan: AnyHeartNativeTypeReferencePlan, lease: AnyHostLease) async throws {
        guard Data(plan.directory.binding.workspace.accountID.utf8) == Data(workspace.accountID.utf8),
              Data(plan.directory.binding.workspace.spaceID.utf8) == Data(workspace.spaceID.utf8),
              Data(lease.workspace.accountID.utf8) == Data(workspace.accountID.utf8),
              Data(lease.workspace.spaceID.utf8) == Data(workspace.spaceID.utf8) else { throw AnyHostError.wrongWorkspace }
        try await lease.validate()
        try Task.checkCancellation()
    }

    private func type(_ presentation: AnyNativeTypeReferencePresentation,
                      plan: AnyHeartNativeTypeReferencePlan,
                      lease: AnyHostLease) async throws -> AnyNativeImportedDefinitionSnapshot? {
        guard let nativeID = presentation.currentNativeTypeID else { return nil }
        let current = try await definitions.read(sourceObjectID: presentation.sourceType.sourceObjectID,
            directory: plan.directory, lease: lease)
        guard current.matchesOriginalDescriptor, case .type(let owner) = current.value,
              Data(owner.id.utf8) == Data(nativeID.utf8) else {
            throw AnyNativeTypeReferenceError.changedCurrentDefinition(presentation.sourceType.sourceObjectID)
        }
        return current
    }

    @discardableResult
    private static func requireProperty(_ current: AnyNativeImportedDefinitionSnapshot,
                                        reference: AnyNativeTypeReference) throws -> AnyNativePropertyDefinition {
        guard case .property(let binding) = reference.target,
              current.matchesOriginalDescriptor, current.entry.address == binding.entry.address,
              Data(current.entry.sourceObjectID.utf8) == Data(reference.sourceObjectID.utf8),
              case .property(let definition) = current.value,
              Data(definition.key.ownerID.utf8) == Data(binding.key.ownerID.utf8),
              Data(definition.key.propertyID.utf8) == Data(binding.key.propertyID.utf8) else {
            throw AnyNativeTypeReferenceError.changedCurrentDefinition(reference.sourceObjectID)
        }
        return definition
    }

    private static func requireSameType(_ before: AnyNativeImportedDefinitionSnapshot?,
                                        _ after: AnyNativeImportedDefinitionSnapshot?, sourceID: String) throws {
        switch (before, after) {
        case (nil, nil): return
        case (.some(let before), .some(let after)):
            guard try AnyHostCanonical.bytes(before.raw, maximumBytes: 262_144) ==
                    AnyHostCanonical.bytes(after.raw, maximumBytes: 262_144),
                  before.nativeCreationOutcome == after.nativeCreationOutcome else {
                throw AnyNativeTypeReferenceError.changedCurrentDefinition(sourceID)
            }
        default: throw AnyNativeTypeReferenceError.changedCurrentDefinition(sourceID)
        }
    }

    private static func requireMembership(_ value: AnyNativePropertySnapshot, typeID: String, objectID: String,
                                          workspace: AnyTorahWorkspace, lease: AnyHostLease) throws {
        guard Data(value.workspace.accountID.utf8) == Data(workspace.accountID.utf8),
              Data(value.workspace.spaceID.utf8) == Data(workspace.spaceID.utf8),
              Data(value.objectID.utf8) == Data(objectID.utf8),
              Data(value.currentTypeID.utf8) == Data(typeID.utf8),
              value.generation == lease.generation,
              Data(value.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8) else { throw AnyHostError.wrongWorkspace }
    }
}
