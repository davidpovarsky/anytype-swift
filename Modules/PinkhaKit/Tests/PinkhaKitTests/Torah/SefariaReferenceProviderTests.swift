import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

@Suite("Sefaria reference provider")
struct SefariaReferenceProviderTests {
    @Test("Hebrew partial search preserves provider identity and display label")
    func hebrewSuggestions() async throws {
        let query = "בראשית א א"
        let expectedURL = try SefariaClient().makeURL(
            pathSegments: ["api", "name", query],
            query: [
                URLQueryItem(name: "type", value: "ref"),
                URLQueryItem(name: "limit", value: "12")
            ]
        ).absoluteString
        let transport = MockTorahHTTPTransport(responses: [
            expectedURL: MockHTTPResponse(data: try TorahFixture.data("reference-name"))
        ])
        let provider = SefariaReferenceProvider(client: SefariaClient(transport: transport))

        let values = try await provider.suggestReferences(query: query, limit: 12)

        #expect(values.first?.id == "Genesis 1:1")
        #expect(values.first?.label == "בראשית א׳:א׳")
        #expect(values.contains(ReferenceCandidate(id: "Genesis", label: "בראשית")))
        #expect(await transport.urls() == [expectedURL])
        #expect(expectedURL.contains("%D7%91%D7%A8%D7%90%D7%A9%D7%99%D7%AA"))
    }

    @Test("English exact resolution preserves canonical and provider metadata")
    func englishResolution() async throws {
        let expectedURL = "https://www.sefaria.org/api/ref/Genesis%201:1"
        let transport = MockTorahHTTPTransport(responses: [
            expectedURL: MockHTTPResponse(data: try TorahFixture.data("reference-resolved"))
        ])
        let provider = SefariaReferenceProvider(client: SefariaClient(transport: transport))

        let resolved = try await provider.resolveReference("Genesis 1:1")

        #expect(resolved.canonical == "Genesis 1:1")
        #expect(resolved.labelHe == "בראשית א׳:א׳")
        #expect(resolved.labelEn == "Genesis 1:1")
        #expect(resolved.urlRef == "Genesis.1.1")
        #expect(resolved.startIndexes == [1, 1])
        #expect(resolved.firstAvailableSectionRef == "Genesis 1")
        #expect(resolved.payload.contains(#""node_type":"JaggedArrayNode""#))
        #expect(resolved.isEmbeddableSource)
    }

    @Test("Broad book and tractate sources are not classified as embeddable")
    func broadClassification() {
        let book = ResolvedReference(
            canonical: "Genesis",
            labelHe: "בראשית",
            nodeType: "JaggedArrayNode",
            depth: 2,
            firstAvailableSectionRef: "Genesis 1"
        )
        let tractate = ResolvedReference(
            canonical: "Rosh Hashanah",
            labelHe: "ראש השנה",
            nodeType: "JaggedArrayNode",
            depth: 2,
            firstAvailableSectionRef: "Rosh Hashanah 2a"
        )
        let section = ResolvedReference(
            canonical: "Rosh Hashanah 16b",
            labelHe: "ראש השנה ט״ז ב׳",
            nodeType: "JaggedArrayNode",
            depth: 2,
            startIndexes: [31]
        )

        #expect(!book.isEmbeddableSource)
        #expect(!tractate.isEmbeddableSource)
        #expect(section.isEmbeddableSource)
    }

    @Test("Rosh Hashanah daf fixture resolves with canonical daf identity")
    func talmudDafResolution() async throws {
        let url = "https://www.sefaria.org/api/ref/Rosh%20Hashanah%2016b"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(data: try TorahFixture.data("reference-rosh-hashanah"))
        ])
        let resolved = try await SefariaReferenceProvider(client: SefariaClient(transport: transport))
            .resolveReference("Rosh Hashanah 16b")

        #expect(resolved.canonical == "Rosh Hashanah 16b")
        #expect(resolved.labelHe == "ראש השנה ט״ז ב׳")
        #expect(resolved.startIndexes == [31])
        #expect(resolved.firstAvailableSectionRef == "Rosh Hashanah 2a")
        #expect(resolved.isEmbeddableSource)
    }

    @Test("Empty reference query is a legitimate empty result without transport")
    func emptyQuery() async throws {
        let transport = MockTorahHTTPTransport(responses: [:])
        let provider = SefariaReferenceProvider(client: SefariaClient(transport: transport))
        #expect(try await provider.suggestReferences(query: "   ", limit: 10).isEmpty)
        #expect(await transport.urls().isEmpty)
    }

    @Test("Invalid references remain distinct from malformed responses")
    func invalidVersusMalformed() async throws {
        let invalidURL = "https://www.sefaria.org/api/ref/not-a-ref"
        let invalidTransport = MockTorahHTTPTransport(responses: [
            invalidURL: MockHTTPResponse(statusCode: 404, json: #"{"error":"not found"}"#)
        ])
        await #expect(throws: TorahError.invalidReference) {
            _ = try await SefariaReferenceProvider(client: SefariaClient(transport: invalidTransport))
                .resolveReference("not-a-ref")
        }

        let malformedURL = "https://www.sefaria.org/api/ref/Genesis"
        let malformedTransport = MockTorahHTTPTransport(responses: [
            malformedURL: MockHTTPResponse(json: "[]")
        ])
        await #expect(throws: TorahError.malformedResponse) {
            _ = try await SefariaReferenceProvider(client: SefariaClient(transport: malformedTransport))
                .resolveReference("Genesis")
        }
    }
}
