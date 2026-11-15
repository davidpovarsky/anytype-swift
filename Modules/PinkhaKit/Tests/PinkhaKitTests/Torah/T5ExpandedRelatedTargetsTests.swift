import Foundation
import Testing
@testable import PinkhaKit

@Suite("T5 explicit expanded target materialization")
struct T5ExpandedRelatedTargetsTests {
    let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")

    @Test func documentAndBlocksRemainSeparateWithRoleBucketsAndReadOnlyQuotes() async throws {
        let records = [record("doc-context"), record("shared", block: "K"),
                       record("shared", block: "K", role: .sourceQuote),
                       record("q2", block: "K", role: .sourceQuote), record("q2", block: "K", role: .sourceQuote),
                       record("quote-only", block: "Q", role: .sourceQuote)]
        let candidate = document(records: records)
        var collector = makeCollector()
        try await collector.append(document: candidate, graph: graph(blocks: ["K", "Q"]), nativeRelatedVersion: 1)
        let result = collector.snapshot
        #expect(result.targets.count == 3)
        let doc = try #require(result.targets.first { $0.blockID == nil })
        let block = try #require(result.targets.first { $0.blockID == "K" })
        #expect(doc.canUnlink)
        #expect(block.contextAssociationIDs == ["shared"])
        #expect(block.sourceQuoteAssociationIDs == ["q2", "shared"])
        #expect(!block.canUnlink)
        #expect(result.targets.first { $0.blockID == "Q" }?.canUnlink == false)
        #expect(result.targets.allSatisfy { $0.document.records.isEmpty })
        #expect(candidate.records == records)
        #expect(!result.hasStaleCandidates)
        #expect(!result.isCapabilityUnavailable)
    }

    @Test func mixedDocumentQuoteGroupCannotUseContextOnlyUnlink() async throws {
        var collector = makeCollector()
        try await collector.append(document: document(records: [record("context"), record("quote", role: .sourceQuote)]), graph: graph(), nativeRelatedVersion: 1)
        #expect(collector.snapshot.targets.count == 1)
        #expect(collector.snapshot.targets[0].sourceQuoteAssociationIDs == ["quote"])
        #expect(!collector.snapshot.targets[0].canUnlink)
    }

    @Test func invalidForeignAndOrphanBlockTargetsNeverBecomeDocumentRows() async throws {
        let invalid = try await T5BlockReachability.evaluate(spaceID: "S", rootID: "doc", nodes: [.init(id: "doc", childIDs: ["missing"])])
        var collector = makeCollector()
        try await collector.append(document: document(records: [record("doc"), record("bad", block: "K")]), graph: invalid, nativeRelatedVersion: 1)
        #expect(collector.snapshot.targets.map(\.blockID) == [nil])
        #expect(collector.snapshot.hasStaleCandidates)

        let foreign = try await graph(object: "other", blocks: ["K"])
        var foreignCollector = makeCollector()
        try await foreignCollector.append(document: document(records: [record("bad", block: "K")]), graph: foreign, nativeRelatedVersion: 1)
        #expect(foreignCollector.snapshot.targets.isEmpty)
        #expect(foreignCollector.snapshot.hasStaleCandidates)

        let orphan = try await T5BlockReachability.evaluate(spaceID: "S", rootID: "doc", nodes: [.init(id: "doc", childIDs: ["K"]), .init(id: "K"), .init(id: "orphan")])
        var orphanCollector = makeCollector()
        try await orphanCollector.append(document: document(records: [record("valid", block: "K"), record("orphan", block: "orphan"), record("root", block: "doc"), record("empty", block: "")]), graph: orphan, nativeRelatedVersion: 1)
        #expect(orphanCollector.snapshot.targets.map(\.blockID) == ["K"])
        #expect(orphanCollector.snapshot.hasStaleCandidates)
    }

    @Test func explicitCapabilityAndRowVersionAreRequiredDespiteDefaultReadyDTO() async throws {
        let candidate = document(records: [record("doc")])
        var unavailable = T5ExpandedRelatedTargets(requestSpaceID: "S", source: source, capability: .unavailable)
        try await unavailable.append(document: candidate, graph: graph(), nativeRelatedVersion: 1)
        #expect(unavailable.snapshot.targets.isEmpty)
        #expect(unavailable.snapshot.isCapabilityUnavailable)
        for version in [nil, 0, 2] as [Int?] {
            var collector = makeCollector()
            try await collector.append(document: candidate, graph: graph(), nativeRelatedVersion: version)
            #expect(collector.snapshot.targets.isEmpty)
            #expect(collector.snapshot.hasStaleCandidates)
        }
    }

    @Test func requestSpaceRecordSpaceObjectAndExactIdentityAreEnforced() async throws {
        var wrongProvider = record("provider")
        wrongProvider.item.providerID = "other"
        var wrongVerse = record("verse")
        wrongVerse.item.canonicalKey = "Genesis 3:4"
        var wrongKind = record("kind")
        wrongKind.item.kind = .topic
        let records = [wrongProvider, wrongVerse, wrongKind, record("foreign-space", space: "private"), record("foreign-object", object: "other")]
        var collector = makeCollector()
        try await collector.append(document: document(records: records), graph: graph(), nativeRelatedVersion: 1)
        #expect(collector.snapshot.targets.isEmpty)
        #expect(collector.snapshot.hasStaleCandidates)
        var wrongSpace = makeCollector()
        try await wrongSpace.append(document: document(space: "private", records: [record("private", space: "private")]), graph: graph(space: "private"), nativeRelatedVersion: 1)
        #expect(wrongSpace.snapshot.targets.isEmpty)
    }

    @Test func legacyQuoteCodecIsConsumedWithoutChangingContextOnlyIdentityPolicy() async throws {
        let raw = #"{"version":2,"records":[{"spaceId":"S","objectId":"doc","blockId":"K","item":{"id":"legacy","kind":"ref","role":"source_quote","providerID":"sefaria","canonicalKey":"Genesis 3:3","externalID":"Genesis 3:3","labelHe":"בראשית ג ג"}}]}"#
        let payload = try TorahAssociationPayloadCodec().decodeCanonicalDocument(raw, legacyLocation: .init(spaceId: "S", target: .object(objectId: "doc")))
        #expect(!source.matches(payload.records[0].item))
        var collector = makeCollector()
        try await collector.append(document: document(records: payload.records), graph: graph(blocks: ["K"]), nativeRelatedVersion: 1)
        #expect(collector.snapshot.targets[0].sourceQuoteAssociationIDs == ["legacy"])
        #expect(!collector.snapshot.targets[0].canUnlink)
    }

    @Test func independentTargetCapIsDeterministicAndKeepsRetainedQuoteIDs() async throws {
        let blocks = (0...500).map { String(format: "b%03d", $0) }
        let records = blocks.map { record("context-\($0)", block: $0) }
            + [record("late-quote-1", block: "b000", role: .sourceQuote), record("late-quote-2", block: "b000", role: .sourceQuote)]
        let verified = try await graph(blocks: blocks)
        var first = makeCollector()
        var reverse = makeCollector()
        try await first.append(document: document(records: records), graph: verified, nativeRelatedVersion: 1)
        try await reverse.append(document: document(records: Array(records.reversed())), graph: verified, nativeRelatedVersion: 1)
        #expect(first.snapshot.targets.count == 500)
        #expect(first.snapshot.isTruncated)
        #expect(first.snapshot.targets.map(\.id) == reverse.snapshot.targets.map(\.id))
        let retained = try #require(first.snapshot.targets.first { $0.blockID == "b000" })
        #expect(retained.sourceQuoteAssociationIDs == ["late-quote-1", "late-quote-2"])
    }

    @Test func globalDateAndStableIDRankIsIndependentOfAppendOrder() async throws {
        let rows = [document(object: "A", records: [record("A", object: "A")], updated: 1),
                    document(object: "B", records: [record("B", object: "B")], updated: 3),
                    document(object: "C", records: [record("C", object: "C")], updated: 2)]
        var first = makeCollector(limit: 2)
        var reverse = makeCollector(limit: 2)
        for row in rows { try await first.append(document: row, graph: graph(object: row.objectID), nativeRelatedVersion: 1) }
        for row in rows.reversed() { try await reverse.append(document: row, graph: graph(object: row.objectID), nativeRelatedVersion: 1) }
        #expect(first.snapshot.targets.map(\.document.objectID) == ["B", "C"])
        #expect(first.snapshot.targets.map(\.id) == reverse.snapshot.targets.map(\.id))
        #expect(first.snapshot.isTruncated)
    }

    @Test func cancellationDoesNotPublishPartialAppendState() async throws {
        var initial = makeCollector()
        try await initial.append(document: document(records: [record("existing")]), graph: graph(), nativeRelatedVersion: 1)
        let expected = initial.snapshot.targets.map(\.id)
        let verified = try await graph(blocks: ["K"])
        let task = Task {
            var collector = initial
            withUnsafeCurrentTask { $0?.cancel() }
            do {
                try await collector.append(document: document(records: [record("new", block: "K")]), graph: verified, nativeRelatedVersion: 1)
                Issue.record("Cancelled append returned success")
            } catch is CancellationError {
            } catch {
                Issue.record("Unexpected error: \(error)")
            }
            return collector.snapshot
        }
        let result = await task.value
        #expect(result.targets.map(\.id) == expected)
        #expect(!result.hasStaleCandidates)
    }

    @Test func missingAndEarliestDatesStillUseStableTargetIDTieBreak() async throws {
        let a = T5IndexedDocument(objectID: "A", spaceID: "S", title: "A", typeID: "page", records: [record("A", object: "A")])
        let b = T5IndexedDocument(objectID: "B", spaceID: "S", title: "B", typeID: "page", updatedAt: .distantPast, records: [record("B", object: "B")])
        var first = makeCollector(limit: 1)
        var reverse = makeCollector(limit: 1)
        for row in [a, b] { try await first.append(document: row, graph: graph(object: row.objectID), nativeRelatedVersion: 1) }
        for row in [b, a] { try await reverse.append(document: row, graph: graph(object: row.objectID), nativeRelatedVersion: 1) }
        #expect(first.snapshot.targets.map(\.document.objectID) == ["A"])
        #expect(reverse.snapshot.targets.map(\.document.objectID) == ["A"])
    }

    @Test func internalSelectedIdentityIsRejectedForCanonicalAndExternalFallbackRecords() async throws {
        let internalSource = T5SourceIdentity(providerID: "sefaria", canonicalReference: "anytype-note:origin")
        for usesFallback in [false, true] {
            var origin = record("origin")
            origin.item.canonicalKey = usesFallback ? "" : internalSource.canonicalReference
            origin.item.externalID = internalSource.canonicalReference
            var collector = T5ExpandedRelatedTargets(requestSpaceID: "S", source: internalSource, capability: .verified)
            do {
                try await collector.append(document: document(records: [origin]), graph: graph(), nativeRelatedVersion: 1)
                Issue.record("Reserved internal identity was accepted")
            } catch T5SpaceRelatedDocumentsError.invalidIdentity {
            }
            #expect(collector.snapshot.targets.isEmpty)
        }
    }

    @Test func resolvedReferenceUsesCanonicalBeforeExternalFallback() async throws {
        var canonical = record("canonical")
        canonical.item.externalID = "anytype-note:unrelated-fallback"
        var fallback = record("fallback", block: "K", role: .sourceQuote)
        fallback.item.canonicalKey = ""
        var originCanonical = record("internal-canonical")
        originCanonical.item.canonicalKey = "anytype-note:origin"
        var originFallback = record("internal-fallback")
        originFallback.item.canonicalKey = ""
        originFallback.item.externalID = "anytype-note:origin"
        var collector = makeCollector()
        try await collector.append(
            document: document(records: [canonical, fallback, originCanonical, originFallback]),
            graph: graph(blocks: ["K"]), nativeRelatedVersion: 1
        )
        #expect(collector.snapshot.targets.count == 2)
        #expect(collector.snapshot.targets.first { $0.blockID == nil }?.contextAssociationIDs == ["canonical"])
        #expect(collector.snapshot.targets.first { $0.blockID == "K" }?.sourceQuoteAssociationIDs == ["fallback"])
        #expect(!collector.snapshot.hasStaleCandidates)
    }

    private func makeCollector(limit: Int = 500) -> T5ExpandedRelatedTargets {
        T5ExpandedRelatedTargets(requestSpaceID: "S", source: source, capability: .verified, targetLimit: limit)
    }

    private func record(_ id: String, block: String? = nil, role: TorahAssociationRole = .context, space: String = "S", object: String = "doc") -> TorahStoredAssociationRecord {
        var item = source.item
        item.id = id
        item.role = role
        let target: TorahAssociationTarget = block.map { .block(objectId: object, blockId: $0) } ?? .object(objectId: object)
        return TorahStoredAssociationRecord(location: .init(spaceId: space, target: target), item: item)
    }

    private func document(space: String = "S", object: String = "doc", records: [TorahStoredAssociationRecord], updated: TimeInterval = 1) -> T5IndexedDocument {
        T5IndexedDocument(objectID: object, spaceID: space, title: "Actual title", typeID: "page", updatedAt: Date(timeIntervalSince1970: updated), canUnlink: true, records: records)
    }

    private func graph(space: String = "S", object: String = "doc", blocks: [String] = []) async throws -> T5BlockReachability.Result {
        try await T5BlockReachability.evaluate(spaceID: space, rootID: object, nodes: [.init(id: object, childIDs: blocks)] + blocks.map { .init(id: $0) })
    }
}
