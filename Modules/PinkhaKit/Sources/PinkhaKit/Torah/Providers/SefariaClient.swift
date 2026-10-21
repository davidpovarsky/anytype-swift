import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import TorahInspectorCore

public struct SefariaRetryPolicy: Sendable {
    public let maximumRetryCount: Int
    public let baseDelay: Duration
    public let maximumDelay: Duration

    public init(
        maximumRetryCount: Int = 2,
        baseDelay: Duration = .milliseconds(250),
        maximumDelay: Duration = .seconds(2)
    ) {
        self.maximumRetryCount = max(0, maximumRetryCount)
        self.baseDelay = baseDelay
        self.maximumDelay = maximumDelay
    }
}

public struct SefariaRequestMetric: Sendable {
    public enum Result: Sendable {
        case response(statusCode: Int)
        case transportFailure
    }

    /// A bounded endpoint family such as `api/ref`; canonical references and
    /// query values are intentionally omitted.
    public let endpoint: String
    public let attempt: Int
    public let elapsed: Duration
    public let result: Result
    public let willRetry: Bool
}

public struct SefariaClient: Sendable {
    private let transport: any TorahHTTPTransport
    private let baseURL: URL
    private let retryPolicy: SefariaRetryPolicy
    private let sleep: @Sendable (Duration) async throws -> Void
    private let metrics: (@Sendable (SefariaRequestMetric) -> Void)?

    public init(
        transport: any TorahHTTPTransport = URLSessionTorahTransport(),
        baseURL: URL = URL(string: "https://www.sefaria.org")!,
        retryPolicy: SefariaRetryPolicy = SefariaRetryPolicy(),
        sleep: @escaping @Sendable (Duration) async throws -> Void = { delay in
            try await Task.sleep(for: delay)
        },
        metrics: (@Sendable (SefariaRequestMetric) -> Void)? = nil
    ) {
        self.transport = transport
        self.baseURL = baseURL
        self.retryPolicy = retryPolicy
        self.sleep = sleep
        self.metrics = metrics
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

        let endpoint = pathSegments.prefix(2).joined(separator: "/")
        let clock = ContinuousClock()
        for retryIndex in 0...retryPolicy.maximumRetryCount {
            let started = clock.now
            do {
                let result = try await transport.data(for: request)
                try Task.checkCancellation()
                let willRetry = Self.isRetryable(statusCode: result.1.statusCode)
                    && retryIndex < retryPolicy.maximumRetryCount
                metrics?(SefariaRequestMetric(
                    endpoint: endpoint,
                    attempt: retryIndex + 1,
                    elapsed: started.duration(to: clock.now),
                    result: .response(statusCode: result.1.statusCode),
                    willRetry: willRetry
                ))
                guard willRetry else { return result }
                try await sleep(retryDelay(response: result.1, retryIndex: retryIndex))
            } catch {
                if URLSessionTorahTransport.isCancellation(error) { throw CancellationError() }
                let willRetry = Self.isRetryable(error: error)
                    && retryIndex < retryPolicy.maximumRetryCount
                metrics?(SefariaRequestMetric(
                    endpoint: endpoint,
                    attempt: retryIndex + 1,
                    elapsed: started.duration(to: clock.now),
                    result: .transportFailure,
                    willRetry: willRetry
                ))
                if willRetry {
                    try await sleep(retryDelay(response: nil, retryIndex: retryIndex))
                    continue
                }
                if let torahError = error as? TorahError { throw torahError }
                throw TorahError.network(error.localizedDescription)
            }
        }
        throw TorahError.network("Sefaria request exhausted its retry budget.")
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

    private func retryDelay(response: HTTPURLResponse?, retryIndex: Int) -> Duration {
        if let raw = response?.value(forHTTPHeaderField: "Retry-After"),
           let seconds = Double(raw),
           seconds >= 0 {
            return min(.seconds(seconds), retryPolicy.maximumDelay)
        }
        let multiplier = 1 << min(retryIndex, 16)
        return min(retryPolicy.baseDelay * multiplier, retryPolicy.maximumDelay)
    }

    private static func isRetryable(statusCode: Int) -> Bool {
        statusCode == 408
            || statusCode == 429
            || [500, 502, 503, 504].contains(statusCode)
    }

    private static func isRetryable(error: Error) -> Bool {
        guard let urlError = error as? URLError else { return false }
        return switch urlError.code {
        case .timedOut,
             .cannotFindHost,
             .cannotConnectToHost,
             .networkConnectionLost,
             .dnsLookupFailed,
             .notConnectedToInternet,
             .resourceUnavailable:
            true
        default:
            false
        }
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
