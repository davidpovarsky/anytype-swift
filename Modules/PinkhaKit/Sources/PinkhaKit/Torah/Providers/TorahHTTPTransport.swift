import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import TorahInspectorCore

public protocol TorahHTTPTransport: Sendable {
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

public struct URLSessionTorahTransport: TorahHTTPTransport {
    private let session: URLSession

    public init(timeout: TimeInterval = 12) {
        let boundedTimeout = max(1, timeout)
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = boundedTimeout
        configuration.timeoutIntervalForResource = boundedTimeout
        self.session = URLSession(configuration: configuration)
    }

    public func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        do {
            try Task.checkCancellation()
            let (data, response) = try await session.data(for: request)
            try Task.checkCancellation()
            guard let httpResponse = response as? HTTPURLResponse else {
                throw TorahError.malformedResponse
            }
            return (data, httpResponse)
        } catch {
            if Self.isCancellation(error) { throw CancellationError() }
            throw error
        }
    }

    static func isCancellation(_ error: Error) -> Bool {
        if error is CancellationError { return true }
        if let urlError = error as? URLError, urlError.code == .cancelled { return true }
        let nsError = error as NSError
        return nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorCancelled
    }
}
