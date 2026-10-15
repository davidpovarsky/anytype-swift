import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

@Suite("Sefaria text provider")
struct SefariaTextProviderTests {
    @Test("V3 section text preserves segment order, gaps, navigation, version and license")
    func sectionText() async throws {
        let metadata = #"{"is_ref":true,"depth":2,"start_indexes":[0],"navigation_refs":{"prev_section_ref":"Genesis 0","next_section_ref":"Genesis 2"}}"#
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: metadata),
            textURL: MockHTTPResponse(data: try TorahFixture.data("text-section"))
        ])
        let provider = SefariaTextProvider(client: SefariaClient(transport: transport))

        let document = try await provider.fetchText(reference: "Genesis 1", request: TorahTextRequest())

        #expect(document.canonicalRef == "Genesis 1")
        #expect(document.sectionRef == "Genesis 1")
        #expect(document.segments.map(\.canonicalRef) == ["Genesis 1:1", "Genesis 1:3"])
        #expect(document.segments.map(\.ordinal) == [1, 3])
        #expect(document.previousSectionRef == "Genesis 0")
        #expect(document.nextSectionRef == "Genesis 2")
        #expect(document.version.versionTitle == "Fixture Hebrew")
        #expect(document.version.license == "CC-BY")
        #expect(document.version.direction == "rtl")
    }

    @Test("Exact segment identity is preserved")
    func exactSegment() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201:7"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201:7?version=hebrew&fill_in_missing_segments=0&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true,"depth":2,"start_indexes":[0,6],"navigation_refs":{}}"#),
            textURL: MockHTTPResponse(json: #"{"ref":"Genesis 1:7","heRef":"בראשית א׳:ז׳","sectionRef":"Genesis 1","versions":[{"language":"he","versionTitle":"Fixture","text":"פסוק"}]}"#)
        ])
        let document = try await SefariaTextProvider(client: SefariaClient(transport: transport))
            .fetchText(
                reference: "Genesis 1:7",
                request: TorahTextRequest(language: "hebrew", fillInMissingSegments: false)
            )

        #expect(document.canonicalRef == "Genesis 1:7")
        #expect(document.sectionRef == "Genesis 1")
        #expect(document.segments.count == 1)
        #expect(document.segments[0].canonicalRef == "Genesis 1:7")
        #expect(document.segments[0].ordinal == 7)
    }

    @Test("Unavailable requested version falls back to source without relabeling language")
    func sourceFallback() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201"
        let requestedURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let sourceURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=source&fill_in_missing_segments=1&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true,"depth":2,"start_indexes":[0],"navigation_refs":{}}"#),
            requestedURL: MockHTTPResponse(json: #"{"ref":"Genesis 1","sectionRef":"Genesis 1","versions":[]}"#),
            sourceURL: MockHTTPResponse(json: #"{"ref":"Genesis 1","sectionRef":"Genesis 1","versions":[{"language":"en","actualLanguage":"en","versionTitle":"English Source","direction":"ltr","text":["In the beginning"]}]}"#)
        ])

        let document = try await SefariaTextProvider(client: SefariaClient(transport: transport))
            .fetchText(reference: "Genesis 1")

        #expect(document.version.language == "en")
        #expect(document.version.actualLanguage == "en")
        #expect(document.version.versionTitle == "English Source")
        #expect(document.version.direction == "ltr")
        #expect(document.segments[0].text == "In the beginning")
    }

    @Test("No available version is noText rather than a fake empty document")
    func noAvailableVersion() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201"
        let requestedURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let sourceURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=source&fill_in_missing_segments=1&return_format=text_only"
        let empty = #"{"ref":"Genesis 1","sectionRef":"Genesis 1","versions":[]}"#
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true}"#),
            requestedURL: MockHTTPResponse(json: empty),
            sourceURL: MockHTTPResponse(json: empty)
        ])
        await #expect(throws: TorahError.noText) {
            _ = try await SefariaTextProvider(client: SefariaClient(transport: transport))
                .fetchText(reference: "Genesis 1")
        }
    }

    @Test("Malformed text and failed HTTP are distinct")
    func textErrors() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let malformedTransport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true}"#),
            textURL: MockHTTPResponse(json: "not-json")
        ])
        await #expect(throws: TorahError.malformedResponse) {
            _ = try await SefariaTextProvider(client: SefariaClient(transport: malformedTransport))
                .fetchText(reference: "Genesis 1")
        }

        let failedTransport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true}"#),
            textURL: MockHTTPResponse(statusCode: 503, json: #"{"error":"unavailable"}"#)
        ])
        do {
            _ = try await SefariaTextProvider(client: SefariaClient(transport: failedTransport))
                .fetchText(reference: "Genesis 1")
            Issue.record("Expected HTTP failure")
        } catch let error as TorahError {
            guard case .network(let message) = error else {
                Issue.record("Expected network status error, got \(error)")
                return
            }
            #expect(message.contains("503"))
        }
    }
}
