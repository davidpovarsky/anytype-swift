import Foundation
import AnytypeCore
import Factory
import PinkhaKit
import Services
import ProtobufMessages
import TorahInspectorCore

@MainActor
final class AnytypeTorahSpaceRelatedDocumentsService {
    @Injected(\.searchMiddleService)
    private var search: any SearchMiddleServiceProtocol

    private let associations: any TorahAssociationRepository
    private let query: T5SpaceRelatedDocumentsQuery

    init(associations: any TorahAssociationRepository, query: T5SpaceRelatedDocumentsQuery = .init()) {
        self.associations = associations
        self.query = query
    }

    func relatedDocuments(spaceID: String, selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot {
        let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
        guard !spaceID.isEmpty, !source.providerID.isEmpty, !source.canonicalReference.isEmpty else {
            throw T5SpaceRelatedDocumentsError.invalidIdentity
        }
        try Task.checkCancellation()
        guard let definition = TorahNativePropertyDefinition.definition(for: "pinkhaTorahSources") else {
            throw T5SpaceRelatedDocumentsError.indexUnavailable
        }
        let descriptors = try await search.search(
            spaceId: spaceID,
            filters: [SearchHelper.relationKey(definition.key)],
            keys: PropertyDetails.subscriptionKeys.map(\.rawValue), limit: 2
        )
        guard descriptors.count == 1,
              PinkhaTorahNativePropertyCatalog.isVerifiedNativeDescriptor(
                PropertyDetails(details: descriptors[0]), definition: definition, spaceId: spaceID
              ) else { throw T5SpaceRelatedDocumentsError.indexUnavailable }

        let result = try await query.execute(spaceID: spaceID, source: source) { [self] excludedIDs, limit in
            try await page(spaceID: spaceID, source: source, excludedIDs: excludedIDs, limit: limit)
        }
        var limitations: [TorahRelatedDocumentsLimitation] = [
            .blockAssociationsNotIndexed, .sourceQuotesNotIndexed, .indexFreshnessUnverified
        ]
        if result.isTruncated { limitations.append(.resultLimitReached) }
        if result.hasStaleCandidates { limitations.append(.staleCandidates) }
        return TorahRelatedDocumentsSnapshot(
            documents: result.matches.map { match in
                let document = match.document
                return TorahRelatedDocument(
                    id: match.id, spaceID: spaceID, objectID: document.objectID,
                    title: document.title, sourceReference: source.canonicalReference,
                    kind: document.isNote ? .note : .document,
                    typeID: document.typeID, iconEmoji: document.iconEmoji,
                    iconImageID: document.iconImageID, updatedAt: document.updatedAt,
                    canUnlink: document.canUnlink
                )
            },
            coverage: .indexedDocumentsOnly, limitations: limitations
        )
    }

    func unlink(document: TorahRelatedDocument, selection: TorahInspectorSelection, spaceID: String) async throws {
        guard document.spaceID == spaceID, document.blockID == nil, document.canUnlink else {
            throw TorahAssociationRepositoryError.permissionDenied
        }
        let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
        guard document.sourceReference == source.canonicalReference else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
        let items = try await associations.listDocumentAssociations(objectId: document.objectID, spaceId: spaceID)
        for item in items where source.matches(item) {
            try Task.checkCancellation()
            try await associations.removeAssociation(
                associationId: item.id, target: .object(objectId: document.objectID), spaceId: spaceID
            )
        }
    }

    private func page(
        spaceID: String, source: T5SourceIdentity, excludedIDs: [String], limit: Int
    ) async throws -> [T5IndexedDocument] {
        var filters = SearchHelper.notHiddenFilters()
        filters.append(SearchHelper.templateScheme(include: false))
        filters.append(SearchHelper.spaceIdFilter(spaceID))
        filters.append(.with {
            $0.relationKey = "pinkhaTorahSources"
            $0.condition = .in
            $0.value = [source.indexValue].protobufValue
        })
        if !excludedIDs.isEmpty { filters.append(SearchHelper.excludedIdsFilter(excludedIDs)) }
        let candidates = try await search.search(
            spaceId: spaceID, filters: filters,
            sorts: [SearchHelper.sort(relation: .id, type: .asc, noCollate: true)],
            keys: [BundledPropertyKey.id.rawValue, BundledPropertyKey.spaceId.rawValue,
                   TorahNativePropertyDefinition.readinessKey, TorahNativePropertyDefinition.statusKey,
                   TorahNativePropertyDefinition.engineVersionKey],
            limit: limit
        )
        var documents: [T5IndexedDocument] = []
        for candidate in candidates {
            try Task.checkCancellation()
            guard candidate.spaceId == spaceID,
                  candidate.values[TorahNativePropertyDefinition.readinessKey]?.boolValue == true,
                  candidate.values[TorahNativePropertyDefinition.statusKey]?.stringValue == "READY",
                  candidate.values[TorahNativePropertyDefinition.engineVersionKey]?.numberValue == 1 else {
                documents.append(unavailableCandidate(candidate, spaceID: spaceID))
                continue
            }
            do {
                let response = try await ClientCommands.objectShow(.with {
                    $0.contextID = candidate.id
                    $0.objectID = candidate.id
                    $0.spaceID = spaceID
                }).invoke(qos: .userInitiated)
                try Task.checkCancellation()
                guard let raw = response.objectView.details.first(where: { $0.id == candidate.id })?.details else {
                    documents.append(unavailableCandidate(candidate, spaceID: spaceID))
                    continue
                }
                let details = try ObjectDetails(protobufStruct: raw)
                guard let canonicalKey = details.values["_pinkhaTorahCanonicalPropertyKey"]?.stringValue,
                      !canonicalKey.isEmpty,
                      let canonical = details.values[canonicalKey]?.stringValue else {
                    documents.append(unavailableCandidate(candidate, spaceID: spaceID))
                    continue
                }
                let records = try TorahAssociationPayloadCodec().decodeCanonicalDocument(
                    canonical, legacyLocation: .init(spaceId: spaceID, target: .object(objectId: candidate.id))
                ).records
                let restrictions = MiddlewareObjectRestrictionsConverter
                    .convertObjectRestrictions(middlewareRestrictions: response.objectView.restrictions).objectRestriction
                let layout = details.resolvedLayout ?? details.layout
                let eligible = details.spaceId == spaceID && !details.isDeleted && !details.isArchived
                    && !details.isHidden && !details.isHiddenDiscovery && details.targetObjectType.isEmpty
                    && details.uniqueKey.isEmpty && !details.type.isEmpty
                    && details.values[BundledPropertyKey.relationKey.rawValue] == nil
                    && details.values[BundledPropertyKey.relationFormat.rawValue] == nil
                    && details.values[BundledPropertyKey.recommendedLayout.rawValue] == nil
                    && [0, 1, 2, 3, 9, 11, 14].contains(layout ?? -1)
                documents.append(T5IndexedDocument(
                    objectID: details.id, spaceID: details.spaceId, title: details.name,
                    typeID: details.type,
                    iconEmoji: nonempty(details.values[BundledPropertyKey.iconEmoji.rawValue]?.stringValue),
                    iconImageID: nonempty(details.iconImage), updatedAt: details.lastModifiedDate,
                    isNote: layout == DetailsLayout.note.rawValue, isEligible: eligible,
                    canUnlink: !details.isReadonly && !restrictions.contains(.details),
                    records: records
                ))
            } catch is CancellationError {
                throw CancellationError()
            } catch let error as Anytype_Rpc.Object.Show.Response.Error where error.code == .notFound || error.code == .objectDeleted {
                documents.append(unavailableCandidate(candidate, spaceID: spaceID))
            }
        }
        return documents
    }

    private func unavailableCandidate(_ details: ObjectDetails, spaceID: String) -> T5IndexedDocument {
        T5IndexedDocument(
            objectID: details.id, spaceID: spaceID, title: "", typeID: "",
            isEligible: false, isProjectionReady: false, records: []
        )
    }

    private func nonempty(_ value: String?) -> String? {
        value?.isEmpty == false ? value : nil
    }
}
