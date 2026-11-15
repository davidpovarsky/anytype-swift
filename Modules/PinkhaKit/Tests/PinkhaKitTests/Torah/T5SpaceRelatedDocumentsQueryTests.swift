import Foundation
import Testing
@testable import PinkhaKit

@Suite("T5 exact current-Space indexed backlinks")
struct T5SpaceRelatedDocumentsQueryTests {
    let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")

    @Test func canonicalIdentityUsesProviderKindAndUTF8Normalization() {
        #expect(source.indexValue == "torah1|3:ref|7:sefaria|11:Genesis 3:3")
        var item = source.item
        item.labelHe = "בראשית ג ג"
        item.labelEn = "different label"
        #expect(source.matches(item))
        item.providerID = "other"
        #expect(!source.matches(item))
        item = source.item
        item.canonicalKey = "Genesis 3:4"
        #expect(!source.matches(item))
        item = source.item
        item.kind = .topic
        #expect(!source.matches(item))
        #expect(T5SourceIdentity(providerID: "e\u{301}", canonicalReference: "שָׁלוֹם").indexValue
            == T5SourceIdentity(providerID: "é", canonicalReference: "שָׁלוֹם").indexValue)
    }

    @Test func threeTypesAcrossPagesAndDuplicateAssociationsBecomeOnePerDocument() async throws {
        let query = T5SpaceRelatedDocumentsQuery(pageSize: 2, candidateLimit: 10)
        let rows = [row("page", type: "page"), row("note", type: "note"), row("חידוש", type: "custom")]
        let result = try await query.execute(spaceID: "space", source: source) { excluded, limit in
            Array(rows.filter { !excluded.contains($0.objectID) }.prefix(limit))
        }
        #expect(result.matches.count == 3)
        #expect(Set(result.matches.map(\.document.typeID)) == ["page", "note", "custom"])
        #expect(Set(result.matches.map(\.id)).count == 3)
        #expect(!result.isTruncated)
        #expect(!result.hasStaleCandidates)
        #expect(result.matches.allSatisfy { $0.associationIDs.count == 2 })
    }

    @Test func wrongSpaceObjectBlockQuoteProviderVerseAndIneligibleRowsAreExcluded() async throws {
        var wrongObject = record("mismatch")
        wrongObject.objectId = "other-object"
        var wrongProvider = record("provider")
        wrongProvider.item.providerID = "other"
        var wrongVerse = record("verse")
        wrongVerse.item.canonicalKey = "Genesis 3:4"
        var block = record("block")
        block.blockId = "paragraph"
        var quote = record("quote")
        quote.item.role = .sourceQuote
        var wrongRecordSpace = record("record-space")
        wrongRecordSpace.spaceId = "private-space"
        let rows = [
            row("foreign", space: "private-space"), row("deleted", eligible: false),
            row("not-ready", ready: false), row("mismatch", records: [wrongObject]),
            row("provider", records: [wrongProvider]), row("verse", records: [wrongVerse]),
            row("block", records: [block]), row("quote", records: [quote]),
            row("record-space", records: [wrongRecordSpace]), row("real")
        ]
        let result = try await T5SpaceRelatedDocumentsQuery().execute(spaceID: "space", source: source) { _, _ in rows }
        #expect(result.matches.map(\.document.objectID) == ["real"])
        #expect(result.hasStaleCandidates)
    }

    @Test func staleUnlinkReadbackDoesNotShowIndexedPositive() async throws {
        let result = try await T5SpaceRelatedDocumentsQuery().execute(spaceID: "space", source: source) { _, _ in
            [row("unlinked", records: [])]
        }
        #expect(result.matches.isEmpty)
        #expect(result.hasStaleCandidates)
    }

    @Test func resultLimitAndSortAreExplicit() async throws {
        let rows = (0..<5).map { row(String($0), updated: Date(timeIntervalSince1970: Double($0))) }
        let result = try await T5SpaceRelatedDocumentsQuery(pageSize: 2, candidateLimit: 3)
            .execute(spaceID: "space", source: source) { excluded, limit in
                Array(rows.filter { !excluded.contains($0.objectID) }.prefix(limit))
            }
        #expect(result.matches.map(\.document.objectID) == ["2", "1", "0"])
        #expect(result.isTruncated)
    }

    @Test func repeatedPageFailsInsteadOfLoopingOrClaimingCompletion() async {
        await #expect(throws: T5SpaceRelatedDocumentsError.paginationDidNotAdvance) {
            try await T5SpaceRelatedDocumentsQuery(pageSize: 1).execute(spaceID: "space", source: source) { _, _ in [row("same")] }
        }
    }

    @Test func backendFailureIsNotEmpty() async {
        await #expect(throws: T5SpaceRelatedDocumentsError.indexUnavailable) {
            try await T5SpaceRelatedDocumentsQuery().execute(spaceID: "space", source: source) { _, _ in
                throw T5SpaceRelatedDocumentsError.indexUnavailable
            }
        }
    }

    @Test func cancellationDiscardsNoncooperativePage() async {
        let gate = T5PageGate()
        let task = Task {
            try await T5SpaceRelatedDocumentsQuery().execute(spaceID: "space", source: source) { _, _ in
                await gate.wait()
                return [row("late")]
            }
        }
        await gate.awaitStarted()
        task.cancel()
        await gate.release()
        do {
            _ = try await task.value
            Issue.record("Cancelled query returned a stale snapshot")
        } catch is CancellationError {
        } catch {
            Issue.record("Unexpected cancellation result: \(error)")
        }
    }

    @Test func noteSelfAssociationIsCanonicalSourceRatherThanSelectionOrNoteID() {
        let item = source.item
        #expect(item.kind == .ref)
        #expect(item.role == .context)
        #expect(item.providerID == "sefaria")
        #expect(item.canonicalKey == "Genesis 3:3")
        #expect(!item.canonicalKey.hasPrefix("anytype-note:"))
        #expect(source.matches(item))
    }

    private func record(_ id: String) -> TorahStoredAssociationRecord {
        var item = source.item
        item.id = "link-\(id)"
        return .init(location: .init(spaceId: "space", target: .object(objectId: id)), item: item)
    }

    private func row(
        _ id: String, space: String = "space", type: String = "page", eligible: Bool = true,
        ready: Bool = true, records: [TorahStoredAssociationRecord]? = nil, updated: Date? = nil
    ) -> T5IndexedDocument {
        var second = record(id)
        second.item.id += "-duplicate"
        return .init(
            objectID: id, spaceID: space, title: "Real title", typeID: type,
            updatedAt: updated, isEligible: eligible, isProjectionReady: ready,
            records: records ?? [record(id), second]
        )
    }
}

private actor T5PageGate {
    private var continuation: CheckedContinuation<Void, Never>?
    private var started = false

    func wait() async {
        started = true
        await withCheckedContinuation { continuation = $0 }
    }

    func awaitStarted() async {
        while !started { await Task.yield() }
    }

    func release() {
        continuation?.resume()
        continuation = nil
    }
}
