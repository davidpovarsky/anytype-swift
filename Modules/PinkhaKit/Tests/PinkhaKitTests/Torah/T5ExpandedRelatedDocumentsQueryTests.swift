import Foundation
import Testing
@testable import PinkhaKit

@Suite("T5 expanded native candidate pagination")
struct T5ExpandedRelatedDocumentsQueryTests {
    private let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")

    @Test func unavailableRuntimeDoesNotQueryEvenWhenRowsWouldAdvertiseVersionOne() async throws {
        let row = try await candidate("document", blocks: ["quoted"], role: .sourceQuote)
        let pages = Pages([[row]])
        let result = try await T5ExpandedRelatedDocumentsQuery().execute(
            spaceID: "S", source: source, capability: .unavailable
        ) { excluded, limit in
            await pages.fetch(excluded, limit)
        }
        #expect(result.isCapabilityUnavailable)
        #expect(result.targets.isEmpty)
        #expect(await pages.calls.isEmpty)
    }

    @Test func pagesRetainExactBlocksAndQuotesWhileRejectingUnreadyCanonicalDocuments() async throws {
        let block = try await candidate("A", blocks: ["verse"], updated: 1)
        let unavailable = try await candidate("stale", ready: false)
        let quote = try await candidate("B", role: .sourceQuote, updated: 2)
        let pages = Pages([[block, unavailable], [quote]])
        let result = try await T5ExpandedRelatedDocumentsQuery(pageSize: 2).execute(
            spaceID: "S", source: source, capability: .verified
        ) { excluded, limit in
            await pages.fetch(excluded, limit)
        }
        #expect(result.targets.map(\.document.objectID) == ["B", "A"])
        #expect(result.targets.map(\.blockID) == [nil, "verse"])
        #expect(result.targets[0].sourceQuoteAssociationIDs == ["B-document"])
        #expect(result.targets.allSatisfy { !$0.canUnlink })
        #expect(result.hasStaleCandidates)
        #expect(!result.isTruncated)
        let calls = await pages.calls
        #expect(calls.count == 2)
        #expect(calls[0].excluded.isEmpty && calls[0].limit == 2)
        #expect(calls[1].excluded == ["A", "stale"] && calls[1].limit == 2)
    }

    @Test func candidateAndTargetCapsAreIndependentAndDisclosed() async throws {
        let a = try await candidate("A", blocks: ["one", "two", "three"], updated: 1)
        let b = try await candidate("B", updated: 2)
        let c = try await candidate("C", updated: 3)
        let pages = Pages([[a], [b], [c]])
        let result = try await T5ExpandedRelatedDocumentsQuery(
            pageSize: 1, candidateLimit: 2, targetLimit: 2
        ).execute(spaceID: "S", source: source, capability: .verified) { excluded, limit in
            await pages.fetch(excluded, limit)
        }
        #expect(result.targets.count == 2)
        #expect(result.targets.first?.document.objectID == "B")
        #expect(!result.targets.contains { $0.document.objectID == "C" })
        #expect(result.isTruncated)
        #expect(await pages.calls.count == 2)
    }

    @Test(arguments: [false, true])
    func duplicateAndOversizedPagesFailWithoutPublishingPartialResults(oversized: Bool) async throws {
        let a = try await candidate("A")
        let b = try await candidate("B")
        let pages = Pages(oversized ? [[a, b]] : [[a], [a]])
        await #expect(throws: T5SpaceRelatedDocumentsError.paginationDidNotAdvance) {
            try await T5ExpandedRelatedDocumentsQuery(pageSize: 1).execute(
                spaceID: "S", source: source, capability: .verified
            ) { excluded, limit in
                await pages.fetch(excluded, limit)
            }
        }
    }

    @Test func laterPageFailureDoesNotReturnTheEarlierTargetsAsACompleteSnapshot() async throws {
        let a = try await candidate("A")
        let pages = Pages([[a]])
        await #expect(throws: FetchFailure.unavailable) {
            try await T5ExpandedRelatedDocumentsQuery(pageSize: 1).execute(
                spaceID: "S", source: source, capability: .verified
            ) { excluded, limit in
                if !excluded.isEmpty { throw FetchFailure.unavailable }
                return await pages.fetch(excluded, limit)
            }
        }
    }

    @Test func cancellationAfterFetchCannotPublishTargets() async throws {
        let row = try await candidate("A", blocks: ["verse"])
        let task = Task {
            do {
                _ = try await T5ExpandedRelatedDocumentsQuery().execute(
                    spaceID: "S", source: source, capability: .verified
                ) { _, _ in
                    withUnsafeCurrentTask { $0?.cancel() }
                    return [row]
                }
                return false
            } catch is CancellationError {
                return true
            } catch {
                return false
            }
        }
        #expect(await task.value)
    }

    @Test func refreshReadsCanonicalMembershipAgainAndDoesNotResurrectRemovedBlocks() async throws {
        let first = try await candidate("A", blocks: ["removed"])
        let goneGraph = try await T5BlockReachability.evaluate(
            spaceID: "S", rootID: "A", nodes: [.init(id: "A")]
        )
        let removed = T5ExpandedRelatedDocumentsQuery.Candidate(
            document: first.document, graph: goneGraph, nativeRelatedVersion: 1
        )
        let pages = Pages([[first], [removed], []])
        let query = T5ExpandedRelatedDocumentsQuery(pageSize: 2)
        let before = try await query.execute(spaceID: "S", source: source, capability: .verified) {
            await pages.fetch($0, $1)
        }
        let after = try await query.execute(spaceID: "S", source: source, capability: .verified) {
            await pages.fetch($0, $1)
        }
        let deleted = try await query.execute(spaceID: "S", source: source, capability: .verified) {
            await pages.fetch($0, $1)
        }
        #expect(before.targets.map(\.blockID) == ["removed"])
        #expect(after.targets.isEmpty && after.hasStaleCandidates)
        #expect(deleted.targets.isEmpty && !deleted.hasStaleCandidates)
        #expect(await pages.calls.count == 3)
    }

    @Test func reservedInternalIdentityCannotTriggerANativeSearch() async throws {
        let pages = Pages([])
        await #expect(throws: T5SpaceRelatedDocumentsError.invalidIdentity) {
            try await T5ExpandedRelatedDocumentsQuery().execute(
                spaceID: "S",
                source: .init(providerID: "sefaria", canonicalReference: "anytype-note:origin"),
                capability: .verified
            ) { excluded, limit in
                await pages.fetch(excluded, limit)
            }
        }
        #expect(await pages.calls.isEmpty)
    }

    private func candidate(
        _ id: String, blocks: [String]? = nil, role: TorahAssociationRole = .context,
        ready: Bool = true, updated: TimeInterval = 1
    ) async throws -> T5ExpandedRelatedDocumentsQuery.Candidate {
        let targets: [String?] = blocks.map { $0.map(Optional.some) } ?? [nil]
        let records = targets.map { block -> TorahStoredAssociationRecord in
            var item = source.item
            item.id = id + "-" + (block ?? "document")
            item.role = role
            let target: TorahAssociationTarget = block.map { .block(objectId: id, blockId: $0) }
                ?? .object(objectId: id)
            return .init(location: .init(spaceId: "S", target: target), item: item)
        }
        let graph = try await T5BlockReachability.evaluate(
            spaceID: "S", rootID: id,
            nodes: [.init(id: id, childIDs: blocks ?? [])] + (blocks ?? []).map { .init(id: $0) }
        )
        return .init(
            document: T5IndexedDocument(
                objectID: id, spaceID: "S", title: id, typeID: "custom-document",
                updatedAt: Date(timeIntervalSince1970: updated), isProjectionReady: ready,
                canUnlink: true, records: records
            ), graph: graph, nativeRelatedVersion: 1
        )
    }

    private enum FetchFailure: Error { case unavailable }

    private actor Pages {
        struct Call: Sendable { let excluded: [String]; let limit: Int }
        let pages: [[T5ExpandedRelatedDocumentsQuery.Candidate]]
        private(set) var calls: [Call] = []

        init(_ pages: [[T5ExpandedRelatedDocumentsQuery.Candidate]]) { self.pages = pages }

        func fetch(_ excluded: [String], _ limit: Int) -> [T5ExpandedRelatedDocumentsQuery.Candidate] {
            let index = calls.count
            calls.append(.init(excluded: excluded, limit: limit))
            return index < pages.count ? pages[index] : []
        }
    }
}
