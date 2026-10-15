import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import TorahInspectorCore

public struct SefariaClient: Sendable {
    private let transport: any TorahHTTPTransport
    private let baseURL: URL

    public init(
        transport: any TorahHTTPTransport = URLSessionTorahTransport(),
        baseURL: URL = URL(string: "https://www.sefaria.org")!
    ) {
        self.transport = transport
        self.baseURL = baseURL
    }

    public func get(
        pathSegments: [String],
        query: [URLQueryItem] = []
    ) async throws -> (Data, HTTPURLResponse) {
        try Task.checkCancellation()
        let requestURL = try makeURL(pathSegments: pathSegments, query: query)
        var request = URLRequest(url: requestURL)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        do {
            let result = try await transport.data(for: request)
            try Task.checkCancellation()
            return result
        } catch {
            if URLSessionTorahTransport.isCancellation(error) { throw CancellationError() }
            if let torahError = error as? TorahError { throw torahError }
            throw TorahError.network(error.localizedDescription)
        }
    }

    public func makeURL(pathSegments: [String], query: [URLQueryItem] = []) throws -> URL {
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw TorahError.malformedResponse
        }

        var allowed = CharacterSet.urlPathAllowed
        allowed.remove(charactersIn: "/?#%")
        let encodedSegments = try pathSegments.map { segment -> String in
            guard let encoded = segment.addingPercentEncoding(withAllowedCharacters: allowed) else {
                throw TorahError.malformedResponse
            }
            return encoded
        }

        let basePath = components.percentEncodedPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.percentEncodedPath = ([basePath] + encodedSegments)
            .filter { !$0.isEmpty }
            .joined(separator: "/")
        components.percentEncodedPath = "/" + components.percentEncodedPath
        components.queryItems = query.isEmpty ? nil : query

        guard let url = components.url else { throw TorahError.malformedResponse }
        return url
    }
}

enum SefariaJSON {
    static func object(from data: Data) throws -> Any {
        do {
            return try JSONSerialization.jsonObject(with: data)
        } catch {
            throw TorahError.malformedResponse
        }
    }

    static func payload(_ object: Any) -> String {
        guard JSONSerialization.isValidJSONObject(object),
              let data = try? JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        else { return "{}" }
        return String(decoding: data, as: UTF8.self)
    }

    static func string(_ dictionary: [String: Any], keys: String...) -> String? {
        string(dictionary, keys: keys)
    }

    static func string(_ dictionary: [String: Any], keys: [String]) -> String? {
        for key in keys {
            guard let value = dictionary[key] as? String else { continue }
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty { return trimmed }
        }
        return nil
    }

    static func localizedTitle(_ value: Any?) -> (he: String?, en: String?) {
        if let text = value as? String { return (text, text) }
        guard let dictionary = value as? [String: Any] else { return (nil, nil) }
        return (
            string(dictionary, keys: ["he", "hebrew", "primary_he"]),
            string(dictionary, keys: ["en", "english", "primary_en"])
        )
    }

    static func requireSuccess(_ response: HTTPURLResponse, operation: String) throws {
        guard (200..<300).contains(response.statusCode) else {
            throw TorahError.network("Sefaria \(operation) returned HTTP \(response.statusCode).")
        }
    }
}
