import Foundation

/// Reads native candidates afresh for each request, then validates each canonical
/// record and exact block target. A ready index row alone never supplies a target.
public struct T5ExpandedRelatedDocumentsQuery: Sendable {
    public struct Candidate: Sendable {
        public let document: T5IndexedDocument
        public let graph: T5BlockReachability.Result
        public let nativeRelatedVersion: Int?

        public init(
            document: T5IndexedDocument, graph: T5BlockReachability.Result,
            nativeRelatedVersion: Int?
        ) {
            self.document = document
            self.graph = graph
            self.nativeRelatedVersion = nativeRelatedVersion
        }
    }

    public typealias FetchPage = @Sendable (
        _ excludedIDs: [String], _ limit: Int
    ) async throws -> [Candidate]

    public let pageSize: Int
    public let candidateLimit: Int
    public let targetLimit: Int

    public init(pageSize: Int = 50, candidateLimit: Int = 500, targetLimit: Int = 500) {
        self.pageSize = min(max(pageSize, 1), 100)
        self.candidateLimit = min(max(candidateLimit, 1), 2_000)
        self.targetLimit = min(max(targetLimit, 1), 2_000)
    }

    public func execute(
        spaceID: String, source: T5SourceIdentity,
        capability: T5ExpandedRelatedTargets.Capability, fetchPage: FetchPage
    ) async throws -> T5ExpandedRelatedTargets.Snapshot {
        try Task.checkCancellation()
        guard !spaceID.isEmpty, !source.providerID.isEmpty, !source.canonicalReference.isEmpty,
              !source.canonicalReference.hasPrefix("anytype-note:") else {
            throw T5SpaceRelatedDocumentsError.invalidIdentity
        }
        var collector = T5ExpandedRelatedTargets(
            requestSpaceID: spaceID, source: source, capability: capability, targetLimit: targetLimit
        )
        guard !collector.snapshot.isCapabilityUnavailable else { return collector.snapshot }

        var seen = Set<String>()
        while seen.count < candidateLimit {
            try Task.checkCancellation()
            let limit = min(pageSize, candidateLimit - seen.count)
            let page = try await fetchPage(seen.sorted(), limit)
            try Task.checkCancellation()
            guard page.count <= limit else { throw T5SpaceRelatedDocumentsError.paginationDidNotAdvance }
            if page.isEmpty { return collector.snapshot }

            let previousCount = seen.count
            for candidate in page {
                try Task.checkCancellation()
                let objectID = candidate.document.objectID
                guard !objectID.isEmpty, seen.insert(objectID).inserted else { continue }
                try await collector.append(
                    document: candidate.document, graph: candidate.graph,
                    nativeRelatedVersion: candidate.nativeRelatedVersion
                )
            }
            guard seen.count > previousCount else { throw T5SpaceRelatedDocumentsError.paginationDidNotAdvance }
            if page.count < limit { return collector.snapshot }
        }
        let result = collector.snapshot
        return .init(
            targets: result.targets, hasStaleCandidates: result.hasStaleCandidates,
            isTruncated: true, isCapabilityUnavailable: result.isCapabilityUnavailable
        )
    }
}
