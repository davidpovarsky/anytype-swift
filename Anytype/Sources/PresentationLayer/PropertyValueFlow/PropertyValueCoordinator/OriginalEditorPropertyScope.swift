import Foundation
import Services
import PinkhaKit
import SwiftProtobuf

/// Carries the already prepared document into the original property UI. This
/// owns no generation, store, editor or permission policy of its own.
@MainActor
final class OriginalEditorPropertyScope {
    static let valuePermissions: Set<EditorDocumentWritePermission> = [.editDetails, .editRelationValues]
    static let listPermissions: Set<EditorDocumentWritePermission> = [.editDetails, .editPropertiesList]

    let preparedSession: PreparedEditorPageSession
    let objectId: String
    let spaceId: String
    private let document: any BaseDocumentProtocol
    var owner: EditorDocumentWriteOwner { preparedSession.owner }

    init(preparedSession: PreparedEditorPageSession, objectId: String, spaceId: String,
         document: (any BaseDocumentProtocol)? = nil) {
        self.preparedSession = preparedSession
        self.objectId = objectId
        self.spaceId = spaceId
        self.document = document ?? preparedSession.document
    }

    func withCurrent<Value>(
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        _ operation: () throws -> Value
    ) throws -> Value {
        try owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId, requiresEditing: false,
            requiredPermissions: requiredPermissions
        ) {
            try owner.validateDocument(document)
            return try operation()
        }
    }

    /// The original callback may synchronously schedule another write. Keep
    /// its named document-action admission; a read publication is deliberately
    /// unable to grant that authority to a descendant.
    func withActionCallback<Value>(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        _ operation: () throws -> Value
    ) throws -> Value {
        try owner.performSynchronousDocumentAction(
            contextId: objectId, spaceId: spaceId, requiredPermissions: requiredPermissions
        ) {
            try owner.validateDocument(document)
            return try operation()
        }
    }

    /// Reserve on the actual UI callback, before creating its original task.
    /// A rejected admission stays a failed write in the same capture barrier.
    func schedule(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) {
        let prepared = prepareAction(requiredPermissions: requiredPermissions, operation: operation)
        Task { try await prepared() }
    }

    func prepareAction(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> @MainActor @Sendable () async throws -> Void {
        do {
            let scheduled = try owner.scheduleDocumentAction(
                contextId: objectId, requiredPermissions: requiredPermissions
            )
            // If identity/Space validation fails after reservation, dropping
            // this original one-use handle records the abandoned write.
            try withCurrent {}
            return { try await scheduled.run(operation: operation) }
        } catch { return { throw error } }
    }

    func perform<Value: Sendable>(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        return try await owner.performDocumentAction(
            contextId: objectId, requiredPermissions: requiredPermissions
        ) { [self] in
            try await withCurrent {}
            return try await operation()
        }
    }

    func originalProperties(_ service: any PropertiesServiceProtocol) throws -> any PropertiesServiceProtocol {
        try withCurrent { try OriginalPropertiesServiceBinding.requireOriginal(service) }
    }

    /// Different existing IDs acquire their own actual documents. The original
    /// selected array is passed to its one original native call only after all
    /// selected owners are retained in the same source/account ancestry.
    func withSelectedObjects<Value: Sendable>(
        ids: [String], requiredPermissions: Set<EditorDocumentWritePermission>,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        try withCurrent {}
        guard !ids.isEmpty, !requiredPermissions.isEmpty,
              ids.allSatisfy({ !$0.isEmpty && !$0.utf8.contains(0) }) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        let preparation = try PreparedEditorChildPreparation(owner: owner)
        return try await retainSelectedObjects(
            ids: ids, index: 0, preparation: preparation,
            permissions: requiredPermissions, operation: operation
        )
    }

    private func retainSelectedObjects<Value: Sendable>(
        ids: [String], index: Int, preparation: PreparedEditorChildPreparation,
        permissions: Set<EditorDocumentWritePermission>,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        guard index < ids.count else { return try await operation() }
        return try await preparation.performMutation(
            data: .init(objectId: ids[index], spaceId: spaceId),
            requiredPermissions: permissions
        ) { [self] child in
            let next = try await preparation.deriving(owner: child)
            return try await retainSelectedObjects(
                ids: ids, index: index + 1, preparation: next,
                permissions: permissions, operation: operation
            )
        }
    }
}

enum OriginalEditorPropertyModalError: Error, Sendable {
    case unsupportedTarget
    case internalIdentityUnavailable
    case invalidPropertyIdentity
    case unsupportedOriginalDelegate
}

/// Per-operation metadata from the original canonical read. This is not a
/// lifetime/permission token and is never cached for a later user action.
struct OriginalEditorPropertyIdentitySnapshot: Sendable {
    fileprivate let scope: OriginalEditorPropertyScope
    fileprivate let spaceId: String
    fileprivate let pinkhaEnabled: Bool
    fileprivate let internalIdentities: PinkhaInternalPropertyIdentities?
    fileprivate let canonicalManifest: PinkhaSpaceManifest?
}

@MainActor
extension OriginalEditorPropertyScope {
    /// This increment qualifies the original slash-menu object target. The
    /// type, dataview and library routes need their own actual prepared target.
    func requireModalTarget(_ target: PropertiesModuleTarget, spaceId: String) throws {
        try withCurrent {
            guard self.spaceId.utf8.elementsEqual(spaceId.utf8),
                  case .object(let selectedObjectId) = target,
                  selectedObjectId.utf8.elementsEqual(objectId.utf8) else {
                throw OriginalEditorPropertyModalError.unsupportedTarget
            }
        }
    }

    /// Read the actual canonical manifest in the captured account. The old
    /// Space-only singleton cache is deliberately not accepted as provenance.
    func loadModalPropertyIdentity() async throws -> OriginalEditorPropertyIdentitySnapshot {
        try withCurrent {}
        let enabled = PinkhaRuntime.enabled
        guard enabled else {
            return .init(scope: self, spaceId: spaceId, pinkhaEnabled: false,
                         internalIdentities: nil, canonicalManifest: nil)
        }
        guard let original = Container.shared.pinkhaSpaceManifestStore() as? PinkhaSpaceManifestStore else {
            throw OriginalEditorPropertyModalError.unsupportedOriginalDelegate
        }
        let manifest = try await owner.performRead(
            contextId: objectId, spaceId: spaceId, rpcNames: ["ObjectSearch", "ObjectShow"]
        ) { [spaceId] in
            try await original.loadOriginalEditorManifest(spaceId: spaceId)
        }
        return try withCurrent {
            guard PinkhaRuntime.enabled == enabled, let manifest,
                  manifest.spaceId.utf8.elementsEqual(spaceId.utf8), manifest.isComplete,
                  manifest.schemaVersion == PinkhaSpaceManifest.currentSchemaVersion,
                  let manifestId = manifest.manifestObjectId, !manifestId.isEmpty, !manifestId.utf8.contains(0),
                  let identities = PinkhaInternalPropertyIdentities(manifest: manifest),
                  identities.canonicalPropertyId.utf8.elementsEqual(manifest.documentAssociationsPropertyId.utf8),
                  identities.canonicalPropertyKey.utf8.elementsEqual(manifest.documentAssociationsPropertyKey.utf8),
                  identities.orderPropertyId.utf8.elementsEqual(manifest.orderPropertyId.utf8),
                  identities.orderPropertyKey.utf8.elementsEqual(manifest.orderPropertyKey.utf8),
                  [identities.canonicalPropertyId, identities.canonicalPropertyKey,
                   identities.orderPropertyId, identities.orderPropertyKey].allSatisfy({ !$0.isEmpty && !$0.utf8.contains(0) }) else {
                throw OriginalEditorPropertyModalError.internalIdentityUnavailable
            }
            return .init(scope: self, spaceId: spaceId, pinkhaEnabled: enabled,
                         internalIdentities: identities, canonicalManifest: manifest)
        }
    }

    /// The original object's Add button uses the original pure eligibility
    /// rule with this operation's canonical read, never the Space-only cache.
    /// Template classification comes from the actual type in the same account;
    /// ObjectDetails.isTemplate would consult an unbound global type cache.
    /// This is a display/presentation check; actual modal writes retain their
    /// existing named action reservations.
    func canAddOriginalProperty(identity: OriginalEditorPropertyIdentitySnapshot) async throws -> Bool {
        let input: (details: ObjectDetails, permissions: ObjectPermissions)? = try withCurrent {
            try requireModalIdentity(identity)
            guard identity.pinkhaEnabled, let details = document.details,
                  details.id.utf8.elementsEqual(objectId.utf8),
                  details.spaceId.utf8.elementsEqual(spaceId.utf8),
                  !details.type.isEmpty, !details.type.utf8.contains(0),
                  document.permissions.canEditRelationValues,
                  document.permissions.canEditDetails,
                  document.permissions.canEditPropertiesList,
                  details.isReadonly == false else { return nil }
            return (details, document.permissions)
        }
        guard let input else { return false }
        let original = try withCurrent {
            try OriginalSearchMiddleServiceBinding.requireOriginal(Container.shared.searchMiddleService())
        }
        let typeId = input.details.type
        try Task.checkCancellation()
        let types = try await owner.performRead(
            contextId: objectId, spaceId: spaceId, rpcNames: ["ObjectSearch"]
        ) { [spaceId, typeId] in
            try await original.search(
                spaceId: spaceId, filters: [SearchHelper.includeIdsFilter([typeId])],
                keys: [BundledPropertyKey.id, .spaceId, .layout, .resolvedLayout, .uniqueKey].map(\.rawValue),
                limit: 0
            )
        }
        try Task.checkCancellation()
        return try withCurrent {
            try requireModalIdentity(identity)
            guard let details = document.details, details == input.details,
                  details.id.utf8.elementsEqual(objectId.utf8),
                  details.spaceId.utf8.elementsEqual(spaceId.utf8),
                  details.type.utf8.elementsEqual(typeId.utf8),
                  document.permissions == input.permissions,
                  types.count == 1, let actualType = types.first,
                  actualType.id.utf8.elementsEqual(typeId.utf8),
                  actualType.spaceId.utf8.elementsEqual(spaceId.utf8),
                  (actualType.resolvedLayout ?? actualType.layout) == DetailsLayout.objectType.rawValue,
                  case .stringValue(let uniqueKey)? = actualType.values[BundledPropertyKey.uniqueKey.rawValue]?.kind,
                  !uniqueKey.isEmpty, !uniqueKey.utf8.contains(0),
                  uniqueKey.utf8.elementsEqual(actualType.uniqueKey.utf8) else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
            return TorahDocumentPropertyEligibility.includesDocument(
                objectId: details.id, typeId: details.type, spaceId: spaceId,
                layout: details.resolvedLayout ?? details.layout,
                isTemplate: uniqueKey == ObjectTypeUniqueKey.template.value,
                isDeleted: details.isDeleted, isArchived: details.isArchived,
                isInternal: details.isHidden || !details.uniqueKey.isEmpty ||
                    details.values[BundledPropertyKey.relationKey.rawValue] != nil ||
                    details.values[BundledPropertyKey.relationFormat.rawValue] != nil ||
                    details.values[BundledPropertyKey.recommendedLayout.rawValue] != nil,
                manifest: identity.canonicalManifest
            )
        }
    }

    func requireModalProperty(_ property: PropertyDetails, identity: OriginalEditorPropertyIdentitySnapshot) throws {
        try withCurrent {
            try requireModalIdentity(identity)
            try Self.requireModalProperty(property, spaceId: spaceId, identity: identity)
        }
    }

    /// The original value editor supplies its own editable/value semantics.
    /// This shared check only excludes the current account's internal/native
    /// properties; it does not grant a property-definition mutation.
    func requireOriginalPropertyValue(propertyId: String, key: String,
                                      identity: OriginalEditorPropertyIdentitySnapshot) throws {
        try withCurrent {
            try requireModalIdentity(identity)
            guard !propertyId.isEmpty, !propertyId.utf8.contains(0),
                  !key.isEmpty, !key.utf8.contains(0),
                  TorahNativePropertyDefinition.definition(for: key) == nil,
                  identity.internalIdentities?.isInternal(propertyId: propertyId, key: key) != true else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
        }
    }

    func requireNewModalProperty(_ property: PropertyDetails, spaceId: String,
                                 identity: OriginalEditorPropertyIdentitySnapshot) throws {
        try withCurrent(requiredPermissions: Self.listPermissions) {
            try requireModalIdentity(identity)
            guard self.spaceId.utf8.elementsEqual(spaceId.utf8),
                  property.id.isEmpty, property.key.isEmpty, property.sourceObject.isEmpty,
                  property.spaceId.isEmpty || property.spaceId.utf8.elementsEqual(spaceId.utf8),
                  !property.isHidden, !property.isReadOnly, !property.isReadOnlyValue,
                  !property.isDeleted, !property.name.isEmpty,
                  property.format != .unrecognized, property.objectTypes.isEmpty else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
        }
    }

    /// Definition and last-used/archive writes belong to the actual selected
    /// property document. Never relabel a foreign ID as this parent context.
    func withSelectedModalProperty<Value: Sendable>(
        id: String, requiredPermissions: Set<EditorDocumentWritePermission>,
        beforeMutation: (@MainActor @Sendable (PropertyDetails) async throws -> Void)? = nil,
        operation: @escaping @MainActor @Sendable (PreparedEditorPageSession, PropertyDetails, OriginalEditorPropertyIdentitySnapshot) async throws -> Value
    ) async throws -> Value {
        try withCurrent {
            guard !id.isEmpty, !id.utf8.contains(0) else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
        }
        // Finish this parent read before any child tracking lease is active.
        let identity = try await loadModalPropertyIdentity()
        let preparation = try PreparedEditorChildPreparation(owner: owner)
        let child = try await preparation.prepare(
            data: .init(objectId: id, spaceId: spaceId), requiredPermissions: requiredPermissions
        )
        defer { child.retire() }
        let selected = try Self.modalPropertySnapshot(child: child, id: id, identity: identity, requiredPermissions: requiredPermissions)
        // Parent work runs in its original scheduled lineage, before entering
        // the child's operation. A child never re-enters its passive parent.
        try await beforeMutation?(selected)
        let result = try await child.owner.performDocumentAction(
            contextId: id, requiredPermissions: requiredPermissions,
            onDrained: { [child] in withExtendedLifetime(child) {} }
        ) { [child] in
            let property = try await Self.modalPropertySnapshot(child: child, id: id, identity: identity, requiredPermissions: requiredPermissions)
            guard property.key.utf8.elementsEqual(selected.key.utf8), property.format == selected.format else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
            return try await operation(child, property, identity)
        }
        try withCurrent {}
        return result
    }

    static func modalPropertySnapshot(
        child: PreparedEditorPageSession, id: String,
        identity: OriginalEditorPropertyIdentitySnapshot,
        requiredPermissions: Set<EditorDocumentWritePermission>
    ) throws -> PropertyDetails {
        try child.owner.performSynchronousDocumentAction(
            contextId: id, spaceId: child.data.spaceId,
            requiredPermissions: requiredPermissions
        ) {
            try child.owner.validateDocument(child.document)
            guard let details = child.document.details,
                  details.id.utf8.elementsEqual(id.utf8),
                  details.spaceId.utf8.elementsEqual(child.data.spaceId.utf8),
                  details.resolvedLayoutValue == .relation,
                  !details.isArchived, !details.isDeleted else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
            let property = PropertyDetails(details: details)
            try requireModalProperty(property, spaceId: child.data.spaceId, identity: identity)
            return property
        }
    }

    private func requireModalIdentity(_ identity: OriginalEditorPropertyIdentitySnapshot) throws {
        guard identity.scope === self, identity.spaceId.utf8.elementsEqual(spaceId.utf8),
              identity.pinkhaEnabled == PinkhaRuntime.enabled else {
            throw OriginalEditorPropertyModalError.invalidPropertyIdentity
        }
    }

    private static func requireModalProperty(
        _ property: PropertyDetails, spaceId: String,
        identity: OriginalEditorPropertyIdentitySnapshot
    ) throws {
        guard identity.spaceId.utf8.elementsEqual(spaceId.utf8), identity.pinkhaEnabled == PinkhaRuntime.enabled,
              !identity.pinkhaEnabled || identity.internalIdentities != nil,
              !property.id.isEmpty, !property.id.utf8.contains(0),
              !property.key.isEmpty, !property.key.utf8.contains(0),
              property.spaceId.utf8.elementsEqual(spaceId.utf8),
              !property.isHidden, !property.isReadOnly, !property.isReadOnlyValue,
              !property.isDeleted, property.format != .unrecognized,
              !BundledPropertyKey.internalKeys.contains(where: { $0.rawValue.utf8.elementsEqual(property.key.utf8) }),
              TorahNativePropertyDefinition.definition(for: property.key) == nil,
              identity.internalIdentities?.isInternal(propertyId: property.id, key: property.key) != true else {
            throw OriginalEditorPropertyModalError.invalidPropertyIdentity
        }
    }
}

@MainActor
extension PropertyModuleConfiguration {
    var originalEditorScope: OriginalEditorPropertyScope? {
        preparedSession.map {
            OriginalEditorPropertyScope(preparedSession: $0, objectId: objectId, spaceId: spaceId)
        }
    }

    func scheduleOriginalPropertyAction(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) {
        if let scope = originalEditorScope {
            scope.schedule(requiredPermissions: requiredPermissions, operation: operation)
        } else {
            Task { try await operation() }
        }
    }

    func performOriginalPropertyAction<Value: Sendable>(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        if let scope = originalEditorScope {
            return try await scope.perform(requiredPermissions: requiredPermissions, operation: operation)
        }
        return try await operation()
    }

    func prepareOriginalPropertyAction(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> @MainActor @Sendable () async throws -> Void {
        originalEditorScope?.prepareAction(requiredPermissions: requiredPermissions, operation: operation) ?? operation
    }

    func originalPropertyButtonPreparation(
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard preparedSession != nil else { return nil }
        return { prepareOriginalPropertyAction(operation: operation) }
    }

    func withCurrentOriginalProperty<Value>(_ operation: () throws -> Value) throws -> Value {
        if let scope = originalEditorScope { return try scope.withCurrent(operation) }
        return try operation()
    }

    func withOriginalPropertyActionCallback<Value>(_ operation: () throws -> Value) throws -> Value {
        if let scope = originalEditorScope { return try scope.withActionCallback(operation) }
        return try operation()
    }

    func originalSelectedOptionsModel(_ model: any PropertySelectedOptionsModelProtocol) throws -> any PropertySelectedOptionsModelProtocol {
        if preparedSession != nil {
            guard let original = model as? PropertySelectedOptionsModel,
                  original.config.preparedSession === preparedSession,
                  original.config.objectId.utf8.elementsEqual(objectId.utf8),
                  original.config.spaceId.utf8.elementsEqual(spaceId.utf8),
                  original.config.relationKey.utf8.elementsEqual(relationKey.utf8) else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
        }
        return model
    }

    func originalPropertiesService(_ service: any PropertiesServiceProtocol) throws -> any PropertiesServiceProtocol {
        if let scope = originalEditorScope { return try scope.originalProperties(service) }
        return service
    }
}
