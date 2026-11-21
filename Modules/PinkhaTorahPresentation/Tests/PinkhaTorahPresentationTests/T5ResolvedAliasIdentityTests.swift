#if canImport(SwiftUI)
import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import PinkhaKit
import XCTest
import TorahInspectorCore
@testable import PinkhaTorahPresentation

/// Controlled HTTP responses exercise the real resolver, shared selection
/// mapper and both shared query paths. This is not a live Sefaria/network test.
final class T5ResolvedAliasIdentityTests: XCTestCase {
    @MainActor
    func testResolvedAliasesRemainDistinctFromOtherVersesAndProviders() async throws {
        let hebrewInput = "בראשית א׳:א׳"
        let englishInput = "Genesis 1:1"
        let differentVerse = "Genesis 1:2"
        let fixtureURL = try XCTUnwrap(Bundle.module.url(forResource: "reference-resolved", withExtension: "json"))
        // Exact bytes copied from the unchanged PinkhaKit reference fixture;
        // both aliases receive the same provider-owned canonical response.
        let firstVerse = try Data(contentsOf: fixtureURL)
        var secondVerse = try XCTUnwrap(JSONSerialization.jsonObject(with: firstVerse) as? [String: Any])
        secondVerse["normalized"] = differentVerse
        secondVerse["ref"] = differentVerse
        secondVerse["hebrew"] = "בראשית א׳:ב׳"
        secondVerse["url_ref"] = "Genesis.1.2"
        secondVerse["start_indexes"] = [1, 2]
        secondVerse["end_indexes"] = [1, 2]
        secondVerse["start_labels"] = ["1", "2"]
        secondVerse["end_labels"] = ["1", "2"]
        let inputs = [hebrewInput, englishInput, differentVerse]
        let expectedURLs = try inputs.map {
            try SefariaClient().makeURL(pathSegments: ["api", "ref", $0]).absoluteString
        }
        let transport = R05ReferenceTransport(responses: [
            expectedURLs[0]: firstVerse,
            expectedURLs[1]: firstVerse,
            expectedURLs[2]: try JSONSerialization.data(withJSONObject: secondVerse, options: [.sortedKeys])
        ])
        let provider = SefariaReferenceProvider(client: SefariaClient(transport: transport))
        var selections: [TorahInspectorSelection] = []
        for input in inputs {
            let resolved = try await provider.resolveReference(input)
            selections.append(try TorahEditorSession.inspectorSelection(for: resolved))
        }
        let requestedURLs = await transport.urls()
        XCTAssertEqual(requestedURLs, expectedURLs)
        XCTAssertTrue(expectedURLs[0].contains("%D7%91%D7%A8%D7%90%D7%A9%D7%99%D7%AA"))
        XCTAssertEqual(expectedURLs[1], "https://www.sefaria.org/api/ref/Genesis%201:1")
        XCTAssertEqual(expectedURLs[2], "https://www.sefaria.org/api/ref/Genesis%201:2")
        XCTAssertEqual(selections[0], selections[1])
        XCTAssertTrue(selections.allSatisfy { $0.canonicalRef == "Genesis 1" && $0.scope == .segment })
        XCTAssertEqual(selections[0].relationshipRef, englishInput)
        XCTAssertEqual(selections[2].relationshipRef, differentVerse)
        XCTAssertNotEqual(selections[0], selections[2])

        let identities = selections.map {
            T5SourceIdentity(providerID: $0.providerID, canonicalReference: $0.relationshipRef)
        }
        let otherProvider = T5SourceIdentity(providerID: "other-provider", canonicalReference: englishInput)
        XCTAssertEqual(identities[0], identities[1])
        XCTAssertEqual(identities[0].indexValue, "torah1|3:ref|7:sefaria|11:Genesis 1:1")
        XCTAssertEqual(Set([identities[0].indexValue, identities[2].indexValue, otherProvider.indexValue]).count, 3)
        let rows = [
            row("exact-source", source: identities[0]),
            row("different-verse", source: identities[2]),
            row("different-provider", source: otherProvider)
        ]
        var expanded: [T5ExpandedRelatedDocumentsQuery.Candidate] = []
        for document in rows {
            let graph = try await T5BlockReachability.evaluate(
                spaceID: "r05-space", rootID: document.objectID, nodes: [.init(id: document.objectID)])
            expanded.append(.init(document: document, graph: graph, nativeRelatedVersion: 1))
        }
        let expandedRows = expanded
        let cases = [(identities[0], "exact-source"), (identities[1], "exact-source"),
                     (identities[2], "different-verse"), (otherProvider, "different-provider")]
        for (identity, expectedObject) in cases {
            // A stale or overbroad native candidate page must not merge another
            // verse/provider merely because the displayed label is identical.
            let documents = try await T5SpaceRelatedDocumentsQuery(pageSize: 2, candidateLimit: 10)
                .execute(spaceID: "r05-space", source: identity) { excluded, limit in
                    Array(rows.filter { !excluded.contains($0.objectID) }.prefix(limit))
                }
            XCTAssertEqual(documents.matches.map(\.document.objectID), [expectedObject])
            XCTAssertEqual(documents.matches.first?.associationIDs, ["link-" + expectedObject])
            XCTAssertFalse(documents.isTruncated)
            XCTAssertTrue(documents.hasStaleCandidates)
            let targets = try await T5ExpandedRelatedDocumentsQuery(pageSize: 2, candidateLimit: 10)
                .execute(spaceID: "r05-space", source: identity, capability: .verified) { excluded, limit in
                    Array(expandedRows.filter { !excluded.contains($0.document.objectID) }.prefix(limit))
                }
            XCTAssertEqual(targets.targets.map(\.document.objectID), [expectedObject])
            XCTAssertTrue(targets.targets.allSatisfy { $0.blockID == nil })
            XCTAssertEqual(targets.targets.first?.contextAssociationIDs, ["link-" + expectedObject])
            XCTAssertTrue(targets.targets.allSatisfy { $0.sourceQuoteAssociationIDs.isEmpty })
            XCTAssertFalse(targets.isTruncated)
            XCTAssertTrue(targets.hasStaleCandidates)
        }
    }

    private func row(_ id: String, source: T5SourceIdentity) -> T5IndexedDocument {
        var item = source.item
        item.id = "link-" + id
        item.labelHe = "אותה תווית תצוגה"
        item.labelEn = "Identical display label"
        let record = TorahStoredAssociationRecord(
            location: .init(spaceId: "r05-space", target: .object(objectId: id)), item: item)
        return .init(objectID: id, spaceID: "r05-space", title: "Same title", typeID: "page", records: [record])
    }
}

private actor R05ReferenceTransport: TorahHTTPTransport {
    private let responses: [String: Data]
    private var requests: [String] = []
    init(responses: [String: Data]) { self.responses = responses }

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        try Task.checkCancellation()
        let url = try XCTUnwrap(request.url)
        requests.append(url.absoluteString)
        let bytes = try XCTUnwrap(responses[url.absoluteString])
        let response = try XCTUnwrap(HTTPURLResponse(
            url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: ["Content-Type": "application/json"]))
        return (bytes, response)
    }

    func urls() -> [String] { requests }
}
#endif
