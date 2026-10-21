import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import TorahInspectorCore
@testable import PinkhaKit

enum TestTransportError: Error, Equatable {
    case unexpectedURL(String)
    case fixtureMissing(String)
}

struct MockHTTPResponse: Sendable {
    let statusCode: Int
    let data: Data
    let headers: [String: String]

    init(statusCode: Int = 200, json: String, headers: [String: String] = [:]) {
        self.statusCode = statusCode
        self.data = Data(json.utf8)
        self.headers = headers
    }

    init(statusCode: Int = 200, data: Data, headers: [String: String] = [:]) {
        self.statusCode = statusCode
        self.data = data
        self.headers = headers
    }
}

actor MockTorahHTTPTransport: TorahHTTPTransport {
    private var responses: [String: [MockHTTPResponse]]
    private(set) var requestedURLs: [String] = []

    init(responses: [String: MockHTTPResponse]) {
        self.responses = responses.mapValues { [$0] }
    }

    init(responseSequences: [String: [MockHTTPResponse]]) {
        self.responses = responseSequences
    }

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        try Task.checkCancellation()
        guard let url = request.url else { throw TorahError.malformedResponse }
        let absoluteURL = url.absoluteString
        requestedURLs.append(absoluteURL)
        guard var queued = responses[absoluteURL], let response = queued.first else {
            throw TestTransportError.unexpectedURL(absoluteURL)
        }
        if queued.count > 1 {
            queued.removeFirst()
            responses[absoluteURL] = queued
        }
        var headers = response.headers
        headers["Content-Type"] = headers["Content-Type"] ?? "application/json"
        guard let http = HTTPURLResponse(
            url: url,
            statusCode: response.statusCode,
            httpVersion: "HTTP/1.1",
            headerFields: headers
        ) else { throw TorahError.malformedResponse }
        return (response.data, http)
    }

    func urls() -> [String] { requestedURLs }
}

actor ThrowingTorahHTTPTransport: TorahHTTPTransport {
    private let error: any Error & Sendable

    init(error: any Error & Sendable) {
        self.error = error
    }

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        throw error
    }
}

actor TimeoutThenSuccessTorahHTTPTransport: TorahHTTPTransport {
    private var requestCount = 0

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        try Task.checkCancellation()
        requestCount += 1
        if requestCount == 1 {
            throw URLError(.timedOut)
        }
        guard let url = request.url,
              let response = HTTPURLResponse(
                url: url,
                statusCode: 200,
                httpVersion: "HTTP/1.1",
                headerFields: ["Content-Type": "application/json"]
              ) else {
            throw TorahError.malformedResponse
        }
        return (Data(#"{"is_ref":true}"#.utf8), response)
    }

    func count() -> Int { requestCount }
}

actor SuspendedTorahHTTPTransport: TorahHTTPTransport {
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        try await Task.sleep(for: .seconds(30))
        throw TorahError.malformedResponse
    }
}

enum TorahFixture {
    static func data(_ name: String, file: StaticString = #filePath, line: UInt = #line) throws -> Data {
        guard let url = Bundle.module.url(forResource: name, withExtension: "json") else {
            throw TestTransportError.fixtureMissing(name)
        }
        return try Data(contentsOf: url)
    }

    static func string(_ name: String) throws -> String {
        String(decoding: try data(name), as: UTF8.self)
    }
}

func sampleDocument(
    providerID: String = "fixture",
    requestedRef: String = "Genesis 1",
    canonicalRef: String = "Genesis 1",
    sectionRef: String = "Genesis 1"
) -> TorahTextDocument {
    TorahTextDocument(
        providerID: providerID,
        requestedRef: requestedRef,
        canonicalRef: canonicalRef,
        hebrewRef: "בראשית א׳",
        sectionRef: sectionRef,
        hebrewSectionRef: "בראשית א׳",
        segments: [
            TorahTextSegment(
                canonicalRef: "Genesis 1:1",
                hebrewRef: "בראשית א׳:א׳",
                text: "בְּרֵאשִׁית בָּרָא",
                ordinal: 1
            )
        ],
        nextSectionRef: "Genesis 2",
        version: TorahTextVersionMetadata(
            language: "he",
            actualLanguage: "he",
            languageFamilyName: "hebrew",
            versionTitle: "Fixture Hebrew",
            license: "CC-BY",
            direction: "rtl"
        ),
        rawProviderPayload: #"{"fixture":true}"#
    )
}
