import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

@Suite("Torah HTTP transport and client")
struct TorahHTTPTransportTests {
    @Test("Hebrew reference path is encoded as one exact path component")
    func hebrewPathEncoding() throws {
        let client = SefariaClient(baseURL: URL(string: "https://www.sefaria.org")!)
        let url = try client.makeURL(pathSegments: ["api", "ref", "בראשית א:א"])
        #expect(
            url.absoluteString
                == "https://www.sefaria.org/api/ref/%D7%91%D7%A8%D7%90%D7%A9%D7%99%D7%AA%20%D7%90:%D7%90"
        )
    }

    @Test("Path and query values are encoded without manual concatenation")
    func pathAndQueryEncoding() throws {
        let client = SefariaClient(baseURL: URL(string: "https://www.sefaria.org")!)
        let url = try client.makeURL(
            pathSegments: ["api", "words", "שַׁעַר"],
            query: [URLQueryItem(name: "lookup_ref", value: "Deuteronomy 6:9")]
        )
        #expect(url.absoluteString.contains("/api/words/%D7%A9%D6%B7%D7%81%D7%A2%D6%B7%D7%A8"))
        #expect(url.absoluteString.contains("lookup_ref=Deuteronomy%206:9"))
        #expect(!url.absoluteString.contains(" "))
    }

    @Test("Cancellation remains cancellation")
    func cancellationPropagation() async {
        let client = SefariaClient(transport: SuspendedTorahHTTPTransport())
        let task = Task {
            try await client.get(pathSegments: ["api", "name", "בראשית"])
        }
        await Task.yield()
        task.cancel()
        await #expect(throws: CancellationError.self) {
            _ = try await task.value
        }
    }

    @Test("HTTP status is preserved in provider diagnostics")
    func httpFailureIncludesStatus() async throws {
        let url = "https://www.sefaria.org/api/name/Genesis?type=ref&limit=5"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(statusCode: 429, json: #"{"error":"rate limited"}"#)
        ])
        let provider = SefariaReferenceProvider(client: SefariaClient(transport: transport))

        do {
            _ = try await provider.suggestReferences(query: "Genesis", limit: 5)
            Issue.record("Expected an HTTP error")
        } catch let error as TorahError {
            guard case .network(let message) = error else {
                Issue.record("Expected TorahError.network, got \(error)")
                return
            }
            #expect(message.contains("429"))
        }
    }

    @Test("Malformed JSON is not normalized to an empty result")
    func malformedJSON() async throws {
        let url = "https://www.sefaria.org/api/name/Genesis?type=ref&limit=5"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(json: "not-json")
        ])
        let provider = SefariaReferenceProvider(client: SefariaClient(transport: transport))
        await #expect(throws: TorahError.malformedResponse) {
            _ = try await provider.suggestReferences(query: "Genesis", limit: 5)
        }
    }

    @Test("Unexpected mock requests fail deterministically")
    func unknownMockRouteFails() async {
        let transport = MockTorahHTTPTransport(responses: [:])
        let client = SefariaClient(transport: transport)
        await #expect(throws: TorahError.self) {
            _ = try await client.get(pathSegments: ["api", "unexpected"])
        }
    }
}
