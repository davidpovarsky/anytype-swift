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
    private let expandedQuery: T5ExpandedRelatedDocumentsQuery

    init(
        associations: any TorahAssociationRepository, query: T5SpaceRelatedDocumentsQuery = .init(),
        expandedQuery: T5ExpandedRelatedDocumentsQuery = .init()
    ) {
        self.associations = associations
        self.query = query
        self.expandedQuery = expandedQuery
    }

    func relatedDocuments(spaceID: String, selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot {
        let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
        guard !spaceID.isEmpty, !source.providerID.isEmpty, !source.canonicalReference.isEmpty else {
            throw T5SpaceRelatedDocumentsError.invalidIdentity
        }
        try Task.checkCancellation()
        if case .verified = try await AnytypeT5NativeRelatedLookup.current() {
            return try await expandedDocuments(spaceID: spaceID, source: source)
        }
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

    func unlink(
        document: TorahRelatedDocument, selection: TorahInspectorSelection, spaceID: String,
        authorize: @MainActor () throws -> Void
    ) async throws {
        try Task.checkCancellation()
        try authorize()
        guard document.spaceID == spaceID, document.blockID == nil, document.canUnlink else {
            throw TorahAssociationRepositoryError.permissionDenied
        }
        let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
        guard document.sourceReference == source.canonicalReference else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
        let items = try await associations.listDocumentAssociations(objectId: document.objectID, spaceId: spaceID)
        try Task.checkCancellation()
        try authorize()
        for item in items where source.matches(item) {
            try Task.checkCancellation()
            try authorize()
            try await associations.removeAssociation(
                associationId: item.id, target: .object(objectId: document.objectID), spaceId: spaceID
            )
        }
    }

    private func expandedDocuments(
        spaceID: String, source: T5SourceIdentity
    ) async throws -> TorahRelatedDocumentsSnapshot {
        let result = try await expandedQuery.execute(
            spaceID: spaceID, source: source, capability: .verified
        ) { [self] excludedIDs, limit in
            try await loadPage(
                spaceID: spaceID, source: source, excludedIDs: excludedIDs,
                limit: limit, scope: .expanded
            )
        }
        var limitations: [TorahRelatedDocumentsLimitation] = [.indexFreshnessUnverified]
        if result.isTruncated { limitations.append(.resultLimitReached) }
        if result.hasStaleCandidates { limitations.append(.staleCandidates) }
        return TorahRelatedDocumentsSnapshot(
            documents: result.targets.map { target in
                let document = target.document
                return TorahRelatedDocument(
                    id: target.id, spaceID: spaceID, objectID: document.objectID,
                    title: document.title, sourceReference: source.canonicalReference,
                    kind: document.isNote ? .note : .document, blockID: target.blockID,
                    typeID: document.typeID, iconEmoji: document.iconEmoji,
                    iconName: document.iconName, iconImageID: document.iconImageID,
                    updatedAt: document.updatedAt, canUnlink: target.canUnlink
                )
            }, coverage: .indexedTargetsOnly, limitations: limitations
        )
    }

    private enum LookupScope {
        case documents
        case expanded

        var indexKey: String {
            switch self {
            case .documents: return "pinkhaTorahSources"
            case .expanded: return "_pinkhaTorahRelatedSources"
            }
        }
    }

    private func page(
        spaceID: String, source: T5SourceIdentity, excludedIDs: [String], limit: Int
    ) async throws -> [T5IndexedDocument] {
        try await loadPage(
            spaceID: spaceID, source: source, excludedIDs: excludedIDs,
            limit: limit, scope: .documents
        ).map(\.document)
    }

    private func loadPage(
        spaceID: String, source: T5SourceIdentity, excludedIDs: [String], limit: Int,
        scope: LookupScope
    ) async throws -> [T5ExpandedRelatedDocumentsQuery.Candidate] {
        var filters = SearchHelper.notHiddenFilters()
        filters.append(SearchHelper.templateScheme(include: false))
        filters.append(SearchHelper.spaceIdFilter(spaceID))
        filters.append(.with {
            $0.relationKey = scope.indexKey
            $0.condition = .in
            $0.value = [source.indexValue].protobufValue
        })
        if !excludedIDs.isEmpty { filters.append(SearchHelper.excludedIdsFilter(excludedIDs)) }
        var keys = [
            BundledPropertyKey.id.rawValue, BundledPropertyKey.spaceId.rawValue,
            TorahNativePropertyDefinition.readinessKey, TorahNativePropertyDefinition.statusKey,
            TorahNativePropertyDefinition.engineVersionKey
        ]
        if case .expanded = scope { keys.append("_pinkhaTorahRelatedVersion") }
        let candidates = try await search.search(
            spaceId: spaceID, filters: filters,
            sorts: [SearchHelper.sort(relation: .id, type: .asc, noCollate: true)],
            keys: keys, limit: limit
        )
        guard candidates.count <= limit else { throw T5SpaceRelatedDocumentsError.paginationDidNotAdvance }
        var documents: [T5ExpandedRelatedDocumentsQuery.Candidate] = []
        for candidate in candidates {
            try Task.checkCancellation()
            guard !candidate.id.isEmpty, candidate.spaceId == spaceID, isProjectionReady(candidate) else {
                documents.append(try await unavailableExpandedCandidate(candidate, spaceID: spaceID))
                continue
            }
            if case .expanded = scope, relatedVersion(candidate) != 1 {
                documents.append(try await unavailableExpandedCandidate(candidate, spaceID: spaceID))
                continue
            }
            do {
                let response = try await ClientCommands.objectShow(.with {
                    $0.contextID = candidate.id
                    $0.objectID = candidate.id
                    $0.spaceID = spaceID
                }).invoke(qos: .userInitiated)
                try Task.checkCancellation()
                guard response.objectView.rootID == candidate.id,
                      let raw = response.objectView.details.first(where: { $0.id == candidate.id })?.details else {
                    documents.append(try await unavailableExpandedCandidate(candidate, spaceID: spaceID))
                    continue
                }
                let details = try ObjectDetails(protobufStruct: raw)
                // A ready index row can predate revocation, deletion or a rebuild.
                // Recheck the live ObjectShow details before accepting canonical links.
                guard details.id == candidate.id, details.spaceId == spaceID, isProjectionReady(details),
                      let canonicalKey = details.values["_pinkhaTorahCanonicalPropertyKey"]?.stringValue,
                      !canonicalKey.isEmpty,
                      let canonical = details.values[canonicalKey]?.stringValue else {
                    documents.append(try await unavailableExpandedCandidate(candidate, spaceID: spaceID))
                    continue
                }
                if case .expanded = scope, relatedVersion(details) != 1 {
                    documents.append(try await unavailableExpandedCandidate(candidate, spaceID: spaceID))
                    continue
                }
                let records = try TorahAssociationPayloadCodec().decodeCanonicalDocument(
                    canonical, legacyLocation: .init(spaceId: spaceID, target: .object(objectId: candidate.id))
                ).records
                let restrictions = MiddlewareObjectRestrictionsConverter
                    .convertObjectRestrictions(middlewareRestrictions: response.objectView.restrictions).objectRestriction
                let layout = details.resolvedLayout ?? details.layout
                let eligible = !details.isDeleted && !details.isArchived
                    && !details.isHidden && !details.isHiddenDiscovery && details.targetObjectType.isEmpty
                    && details.uniqueKey.isEmpty && !details.type.isEmpty
                    && details.values[BundledPropertyKey.relationKey.rawValue] == nil
                    && details.values[BundledPropertyKey.relationFormat.rawValue] == nil
                    && details.values[BundledPropertyKey.recommendedLayout.rawValue] == nil
                    && [0, 1, 2, 3, 9, 11, 14].contains(layout ?? -1)
                let nodes: [T5BlockReachability.Node]
                switch scope {
                case .expanded:
                    nodes = response.objectView.blocks.map { .init(id: $0.id, childIDs: $0.childrenIds) }
                case .documents:
                    nodes = [.init(id: candidate.id)]
                }
                let graph = try await T5BlockReachability.evaluate(
                    spaceID: spaceID, rootID: candidate.id, nodes: nodes
                )
                let document = T5IndexedDocument(
                    objectID: details.id, spaceID: details.spaceId, title: details.name,
                    typeID: details.type,
                    iconEmoji: nonempty(details.values[BundledPropertyKey.iconEmoji.rawValue]?.stringValue),
                    iconImageID: nonempty(details.iconImage), updatedAt: details.lastModifiedDate,
                    isNote: layout == DetailsLayout.note.rawValue, isEligible: eligible,
                    isProjectionReady: true,
                    canUnlink: !details.isReadonly && !restrictions.contains(.details),
                    records: records
                )
                documents.append(.init(
                    document: document, graph: graph, nativeRelatedVersion: relatedVersion(details)
                ))
            } catch is CancellationError {
                throw CancellationError()
            } catch let error as Anytype_Rpc.Object.Show.Response.Error where error.code == .notFound || error.code == .objectDeleted {
                documents.append(try await unavailableExpandedCandidate(candidate, spaceID: spaceID))
            }
        }
        return documents
    }

    private func isProjectionReady(_ details: ObjectDetails) -> Bool {
        details.values[TorahNativePropertyDefinition.readinessKey]?.boolValue == true
            && details.values[TorahNativePropertyDefinition.statusKey]?.stringValue == "READY"
            && details.values[TorahNativePropertyDefinition.engineVersionKey]?.numberValue == 1
    }

    private func relatedVersion(_ details: ObjectDetails) -> Int? {
        details.values["_pinkhaTorahRelatedVersion"]?.numberValue == 1 ? 1 : nil
    }

    private func unavailableExpandedCandidate(
        _ details: ObjectDetails, spaceID: String
    ) async throws -> T5ExpandedRelatedDocumentsQuery.Candidate {
        let graph = try await T5BlockReachability.evaluate(
            spaceID: spaceID, rootID: details.id, nodes: []
        )
        return .init(
            document: unavailableCandidate(details, spaceID: spaceID),
            graph: graph, nativeRelatedVersion: nil
        )
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
