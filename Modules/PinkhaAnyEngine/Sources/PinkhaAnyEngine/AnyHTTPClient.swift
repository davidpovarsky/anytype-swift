import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

public struct AnyHTTPClient: Sendable {
    public let baseURL: URL
    public let expectedAccountID: String
    private let session: URLSession

    // Safety: stateless delegate, no mutable shared state. Follow-up: retire the
    // unchecked annotation when Foundation exposes Sendable delegate protocols.
    private final class RejectRedirects: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
        func urlSession(_ session: URLSession, task: URLSessionTask,
                        willPerformHTTPRedirection response: HTTPURLResponse,
                        newRequest request: URLRequest,
                        completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
            completionHandler(nil)
        }
    }

    /// The engine exposes unauthenticated data routes. Only a literal loopback
    /// endpoint is accepted; callers retain Hanlin consent and account fencing.
    public init(baseURL: URL, expectedAccountID: String) throws {
        guard baseURL.scheme == "http",
              ["127.0.0.1", "::1", "[::1]"].contains(baseURL.host ?? ""),
              baseURL.user == nil, baseURL.password == nil,
              baseURL.query == nil, baseURL.fragment == nil,
              baseURL.path.isEmpty || baseURL.path == "/" else {
            throw AnyEngineError.invalidEndpoint
        }
        guard !expectedAccountID.isEmpty else { throw AnyEngineError.invalidIdentity("account") }
        self.baseURL = baseURL
        self.expectedAccountID = expectedAccountID
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpShouldSetCookies = false
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        self.session = URLSession(configuration: configuration, delegate: RejectRedirects(), delegateQueue: nil)
    }

    public func requestJSON(
        method: String, path: [String], body: AnyJSON? = nil,
        authorize: @escaping @Sendable () async throws -> Void = {}
    ) async throws -> AnyJSON {
        try await checkAccount()
        try Task.checkCancellation()
        try await authorize()
        try Task.checkCancellation()
        let result = try await raw(method: method, path: path, body: body)
        // A switch can occur while the HTTP request is in flight. The caller
        // must reconcile mutations against this account before claiming success.
        do { try await checkAccount() }
        catch { if method == "GET" { throw error }; throw AnyEngineError.writeUncertain }
        return result
    }

    public func checkAccount() async throws {
        let auth = try await raw(method: "GET", path: ["v1", "auth"], body: nil)
        guard auth["authorized"]?.bool == true,
              auth["accountId"]?.string == expectedAccountID else {
            throw AnyEngineError.accountChanged
        }
    }

    func makeRequest(method: String, path: [String], body: AnyJSON?) throws -> URLRequest {
        guard !path.isEmpty, path.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
            throw AnyEngineError.invalidEndpoint
        }
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)
        let unreserved = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-._~"))
        let escaped = try path.map { part in
            guard let value = part.addingPercentEncoding(withAllowedCharacters: unreserved) else {
                throw AnyEngineError.invalidEndpoint
            }
            return value
        }
        components?.percentEncodedPath = "/" + escaped.joined(separator: "/")
        guard let url = components?.url else { throw AnyEngineError.invalidEndpoint }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = try JSONEncoder().encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        return request
    }

    private func raw(method: String, path: [String], body: AnyJSON?) async throws -> AnyJSON {
        let request = try makeRequest(method: method, path: path, body: body)
        let data: Data
        let response: URLResponse
        do { (data, response) = try await session.data(for: request) }
        catch { if method == "GET" { throw error }; throw AnyEngineError.writeUncertain }
        guard let http = response as? HTTPURLResponse else {
            throw AnyEngineError.malformedResponse("HTTP response")
        }
        return try Self.decodeResponse(status: http.statusCode, data: data)
    }

    static func decodeResponse(status: Int, data: Data) throws -> AnyJSON {
        guard (200..<300).contains(status) else {
            let decoded = try? JSONDecoder().decode(AnyJSON.self, from: data)
            throw AnyEngineError.http(
                status: status,
                code: decoded?["error"]?["code"]?.string ?? decoded?["code"]?.string ?? "unknown"
            )
        }
        let decoded = data.isEmpty ? AnyJSON.null : try JSONDecoder().decode(AnyJSON.self, from: data)
        // Any uses HTTP 200 for partial failures; an HTTP success is not a write receipt.
        if let rejections = decoded["rejections"] {
            guard let rejected = rejections.array else {
                throw AnyEngineError.malformedResponse("rejections")
            }
            if !rejected.isEmpty {
                throw AnyEngineError.writeRejected(rejected.map { $0["code"]?.string ?? "unknown" })
            }
        }
        if let pages = decoded["pages"] {
            guard let values = pages.array else { throw AnyEngineError.malformedResponse("pages") }
            for page in values {
                if let rejections = page["rejections"] {
                    guard let values = rejections.array else { throw AnyEngineError.malformedResponse("page rejections") }
                    if !values.isEmpty {
                        throw AnyEngineError.writeRejected(values.map { $0["code"]?.string ?? "unknown" })
                    }
                }
            }
        }
        return decoded
    }
}
