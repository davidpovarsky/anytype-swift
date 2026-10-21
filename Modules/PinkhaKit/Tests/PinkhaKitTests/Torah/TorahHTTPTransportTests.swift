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

    @Test("Transient GET status retries are bounded and reuse the exact request")
    func transientStatusRetry() async throws {
        let url = "https://www.sefaria.org/api/ref/Genesis%201"
        let transport = MockTorahHTTPTransport(responseSequences: [
            url: [
                MockHTTPResponse(statusCode: 503, json: #"{"error":"unavailable"}"#),
                MockHTTPResponse(
                    statusCode: 429,
                    json: #"{"error":"limited"}"#,
                    headers: ["Retry-After": "1"]
                ),
                MockHTTPResponse(json: #"{"is_ref":true}"#)
            ]
        ])
        let client = SefariaClient(
            transport: transport,
            retryPolicy: SefariaRetryPolicy(
                maximumRetryCount: 2,
                baseDelay: .zero,
                maximumDelay: .zero
            ),
            sleep: { _ in }
        )

        let (_, response) = try await client.get(pathSegments: ["api", "ref", "Genesis 1"])
        let requestedURLs = await transport.urls()

        #expect(response.statusCode == 200)
        #expect(requestedURLs == [url, url, url])
    }

    @Test("Transient timeout retries and recovers")
    func transientTimeoutRetry() async throws {
        let transport = TimeoutThenSuccessTorahHTTPTransport()
        let client = SefariaClient(
            transport: transport,
            retryPolicy: SefariaRetryPolicy(
                maximumRetryCount: 2,
                baseDelay: .zero,
                maximumDelay: .zero
            ),
            sleep: { _ in }
        )

        let (_, response) = try await client.get(pathSegments: ["api", "ref", "Genesis 1"])

        #expect(response.statusCode == 200)
        #expect(await transport.count() == 2)
    }

    @Test("Non-transient status is returned without retry")
    func nonTransientStatusDoesNotRetry() async throws {
        let url = "https://www.sefaria.org/api/ref/Bad"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(statusCode: 400, json: #"{"error":"bad request"}"#)
        ])
        let client = SefariaClient(
            transport: transport,
            retryPolicy: SefariaRetryPolicy(baseDelay: .zero, maximumDelay: .zero),
            sleep: { _ in }
        )

        let (_, response) = try await client.get(pathSegments: ["api", "ref", "Bad"])
        let requestedURLs = await transport.urls()

        #expect(response.statusCode == 400)
        #expect(requestedURLs == [url])
    }

    @Test("Cancellation during retry backoff remains cancellation")
    func retryBackoffCancellation() async {
        let url = "https://www.sefaria.org/api/ref/Genesis%201"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(statusCode: 503, json: #"{"error":"unavailable"}"#)
        ])
        let client = SefariaClient(
            transport: transport,
            retryPolicy: SefariaRetryPolicy(maximumRetryCount: 2),
            sleep: { _ in try await Task.sleep(for: .seconds(30)) }
        )
        let task = Task {
            try await client.get(pathSegments: ["api", "ref", "Genesis 1"])
        }
        for _ in 0..<1_000 {
            let requests = await transport.urls()
            if !requests.isEmpty { break }
            await Task.yield()
        }
        task.cancel()

        await #expect(throws: CancellationError.self) {
            _ = try await task.value
        }
        let requestedURLs = await transport.urls()
        #expect(requestedURLs.count == 1)
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
