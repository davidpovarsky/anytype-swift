import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
import TorahInspectorCore

protocol AnyNativeTorahRelatedQuerying: Sendable {
    var workspace: AnyTorahWorkspace { get }
    func related(to source: T5SourceIdentity, limit: Int) async throws -> AnyNativeRelatedQueryResult
}

extension AnyGuardedTorahIndex: AnyNativeTorahRelatedQuerying {}

/// Native target index supplies context and quote matches. Metadata is read under
/// current access, then the native generation is rechecked before delivery.
public struct AnyNativeTorahRelatedPresentation: Sendable {
    public let workspace: AnyTorahWorkspace
    private let index: any AnyNativeTorahRelatedQuerying
    private let reader: any AnyTorahRelatedDocumentReading
    private let associations: AnyTorahAssociationRepository

    public init(index: AnyGuardedTorahIndex, reader: any AnyTorahRelatedDocumentReading,
                associations: AnyTorahAssociationRepository) throws {
        try self.init(index: index as any AnyNativeTorahRelatedQuerying,
                      reader: reader, associations: associations)
    }

    init(index: any AnyNativeTorahRelatedQuerying, reader: any AnyTorahRelatedDocumentReading,
         associations: AnyTorahAssociationRepository) throws {
        guard index.workspace == reader.workspace, associations.workspace == index.workspace else {
            throw AnyEngineError.invalidIdentity("mixed native related workspace")
        }
        workspace = index.workspace
        self.index = index; self.reader = reader; self.associations = associations
    }

    public func snapshot(source: T5SourceIdentity) async throws -> TorahRelatedDocumentsSnapshot {
        let initial = try await index.related(to: source, limit: 1000)
        var metadata: [String: AnyTorahRelatedDocumentMetadata] = [:]
        for target in initial.targets {
            if metadata[target.target.objectId] == nil {
                metadata[target.target.objectId] = try await reader.metadata(objectID: target.target.objectId)
            }
        }
        let final = try await index.related(to: source, limit: 1000)
        guard initial.readiness == final.readiness, initial.targets == final.targets,
              initial.conflictingTargets == final.conflictingTargets else {
            throw AnyEngineError.malformedResponse("native related snapshot changed during metadata read")
        }
        let documents = try final.targets.map { target -> TorahRelatedDocument in
            guard let value = metadata[target.target.objectId],
                  value.objectID == target.target.objectId, value.spaceID == workspace.spaceID else {
                throw TorahAssociationRepositoryError.targetOutsideSpace
            }
            let objectID = target.target.objectId
            let blockID = target.target.blockId
            return .init(id: "\(objectID.utf8.count):\(objectID)|\(blockID ?? "")",
                         spaceID: workspace.spaceID, objectID: objectID, title: value.title,
                         sourceReference: source.canonicalReference,
                         kind: value.isNote ? .note : .document, blockID: blockID,
                         typeID: value.typeID, iconEmoji: value.iconEmoji, iconName: value.iconName,
                         iconImageID: value.iconImageID, updatedAt: value.updatedAt,
                         canUnlink: final.readiness.complete && target.canSafelyUnlink && value.canUnlink)
        }
        return .init(documents: documents, coverage: .indexedTargetsOnly,
                     limitations: final.readiness.complete ? [] : [.indexFreshnessUnverified])
    }

    public func unlink(document: TorahRelatedDocument, source: T5SourceIdentity,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard document.spaceID == workspace.spaceID, document.blockID == nil, document.canUnlink else {
            throw TorahAssociationRepositoryError.permissionDenied
        }
        guard document.sourceReference == source.canonicalReference else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
        try await authorize()
        let current = try await index.related(to: source, limit: 1000)
        guard current.readiness.complete,
              let target = current.targets.first(where: {
                  $0.target.objectId == document.objectID && $0.target.blockId == nil
              }), target.canSafelyUnlink else {
            throw TorahAssociationRepositoryError.writeConflict("Related source changed")
        }
        let metadata = try await reader.metadata(objectID: document.objectID)
        guard metadata.objectID == document.objectID, metadata.spaceID == workspace.spaceID,
              metadata.canUnlink else { throw TorahAssociationRepositoryError.permissionDenied }
        let items = try await associations.listDocumentAssociations(
            objectId: document.objectID, spaceId: workspace.spaceID)
        let expectedIDs = Set(target.contextItemIDs)
        let selected = items.filter { expectedIDs.contains($0.id) }
        guard Set(selected.map(\.id)) == expectedIDs, !selected.isEmpty,
              selected.allSatisfy({ item in
                  item.role == .context && item.kind == .ref &&
                  item.providerID == source.providerID &&
                  (item.canonicalKey.isEmpty ? item.externalID : item.canonicalKey)
                      .precomposedStringWithCanonicalMapping ==
                    source.canonicalReference.precomposedStringWithCanonicalMapping
              }) else {
            throw TorahAssociationRepositoryError.writeConflict("Related source identities changed")
        }
        for item in selected {
            try await authorize()
            try await associations.removeAssociation(associationId: item.id,
                target: .object(objectId: document.objectID), spaceId: workspace.spaceID,
                authorize: authorize)
        }
    }
}
