import Foundation

public struct T5SourceIdentity: Hashable, Sendable {
    public let providerID: String
    public let canonicalReference: String

    public init(providerID: String, canonicalReference: String) {
        self.providerID = providerID.precomposedStringWithCanonicalMapping
        self.canonicalReference = canonicalReference.precomposedStringWithCanonicalMapping
    }

    public var item: TorahAssociationItem {
        TorahAssociationItem(
            kind: .ref, role: .context, providerID: providerID,
            externalID: canonicalReference, canonicalKey: canonicalReference,
            labelHe: canonicalReference
        )
    }

    public var indexValue: String { TorahDerivedQueryProjection.identity(item) }

    public func matches(_ item: TorahAssociationItem) -> Bool {
        item.kind == .ref && item.role == .context
            && TorahDerivedQueryProjection.identity(item) == indexValue
    }
}

public struct T5IndexedDocument: Sendable {
    public let objectID: String
    public let spaceID: String
    public let title: String
    public let typeID: String
    public let iconEmoji: String?
    public let iconName: String?
    public let iconImageID: String?
    public let updatedAt: Date?
    public let isNote: Bool
    public let isEligible: Bool
    public let isProjectionReady: Bool
    public let canUnlink: Bool
    public let records: [TorahStoredAssociationRecord]

    public init(
        objectID: String, spaceID: String, title: String, typeID: String,
        iconEmoji: String? = nil, iconName: String? = nil, iconImageID: String? = nil,
        updatedAt: Date? = nil, isNote: Bool = false, isEligible: Bool = true,
        isProjectionReady: Bool = true, canUnlink: Bool = false, records: [TorahStoredAssociationRecord]
    ) {
        self.objectID = objectID
        self.spaceID = spaceID
        self.title = title
        self.typeID = typeID
        self.iconEmoji = iconEmoji
        self.iconName = iconName
        self.iconImageID = iconImageID
        self.updatedAt = updatedAt
        self.isNote = isNote
        self.isEligible = isEligible
        self.isProjectionReady = isProjectionReady
        self.canUnlink = canUnlink
        self.records = records
    }
}

public struct T5RelatedDocumentMatch: Sendable {
    public let document: T5IndexedDocument
    public let associationIDs: [String]

    public var id: String {
        [document.spaceID, document.objectID, ""].map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
    }
}

public struct T5SpaceRelatedDocumentsResult: Sendable {
    public let matches: [T5RelatedDocumentMatch]
    public let isTruncated: Bool
    public let hasStaleCandidates: Bool
}

public enum T5SpaceRelatedDocumentsError: Error, Equatable, Sendable {
    case invalidIdentity
    case paginationDidNotAdvance
    case indexUnavailable
}

public struct T5SpaceRelatedDocumentsQuery: Sendable {
    public typealias FetchPage = @Sendable (_ excludedIDs: [String], _ limit: Int) async throws -> [T5IndexedDocument]

    public let pageSize: Int
    public let candidateLimit: Int

    public init(pageSize: Int = 50, candidateLimit: Int = 500) {
        self.pageSize = min(max(pageSize, 1), 100)
        self.candidateLimit = min(max(candidateLimit, 1), 2_000)
    }

    public func execute(
        spaceID: String, source: T5SourceIdentity, fetchPage: FetchPage
    ) async throws -> T5SpaceRelatedDocumentsResult {
        guard !spaceID.isEmpty, !source.providerID.isEmpty, !source.canonicalReference.isEmpty else {
            throw T5SpaceRelatedDocumentsError.invalidIdentity
        }
        var seen = Set<String>()
        var matches: [T5RelatedDocumentMatch] = []
        var stale = false
        while seen.count < candidateLimit {
            try Task.checkCancellation()
            let limit = min(pageSize, candidateLimit - seen.count)
            let page = try await fetchPage(seen.sorted(), limit)
            try Task.checkCancellation()
            guard page.count <= limit else { throw T5SpaceRelatedDocumentsError.paginationDidNotAdvance }
            if page.isEmpty {
                return .init(matches: sorted(matches), isTruncated: false, hasStaleCandidates: stale)
            }
            let previousCount = seen.count
            for document in page {
                guard !document.objectID.isEmpty, seen.insert(document.objectID).inserted else { continue }
                guard document.spaceID == spaceID, document.isEligible else { stale = true; continue }
                guard document.isProjectionReady else { stale = true; continue }
                let ids = Set(document.records.filter {
                    $0.spaceId == spaceID && $0.objectId == document.objectID
                        && $0.blockId == nil && source.matches($0.item)
                }.map(\.item.id)).sorted()
                guard !ids.isEmpty else { stale = true; continue }
                matches.append(.init(document: document, associationIDs: ids))
            }
            guard seen.count > previousCount else { throw T5SpaceRelatedDocumentsError.paginationDidNotAdvance }
            if page.count < limit {
                return .init(matches: sorted(matches), isTruncated: false, hasStaleCandidates: stale)
            }
        }
        return .init(matches: sorted(matches), isTruncated: true, hasStaleCandidates: stale)
    }

    private func sorted(_ matches: [T5RelatedDocumentMatch]) -> [T5RelatedDocumentMatch] {
        matches.sorted {
            if $0.document.updatedAt != $1.document.updatedAt {
                return ($0.document.updatedAt ?? .distantPast) > ($1.document.updatedAt ?? .distantPast)
            }
            return $0.id < $1.id
        }
    }
}
