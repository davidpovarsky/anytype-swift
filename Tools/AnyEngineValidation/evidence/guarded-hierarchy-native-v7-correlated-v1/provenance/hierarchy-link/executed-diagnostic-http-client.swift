import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Opaque per-boot capability for a managed mobile runtime. It is never
/// serialized into diagnostics or persisted alongside document metadata.
public struct AnyHTTPAuthorization: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    fileprivate let token: String
    public init(token: String) throws {
        guard token.utf8.count == 64, token.utf8.allSatisfy({
            (48...57).contains($0) || (97...102).contains($0)
        }) else { throw AnyEngineError.invalidIdentity("managed authorization") }
        self.token = token
    }
    public var description: String { "AnyHTTPAuthorization(redacted)" }
    public var debugDescription: String { description }
}

public struct AnyHTTPClient: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let baseURL: URL
    public let expectedAccountID: String
    private let session: URLSession
    private let authorization: AnyHTTPAuthorization?
    public var hasManagedAuthorization: Bool { authorization != nil }
    public var description: String { "AnyHTTPClient(loopback, managed authorization redacted)" }
    public var debugDescription: String { description }

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

    /// A managed mobile runtime requires its per-boot authorization. Standalone
    /// component fixtures may omit it. Only literal loopback is accepted;
    /// Hanlin consent and account/Space fences remain independent requirements.
    public init(baseURL: URL, expectedAccountID: String,
                authorization: AnyHTTPAuthorization? = nil) throws {
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
        self.authorization = authorization
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpShouldSetCookies = false
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        self.session = URLSession(configuration: configuration, delegate: RejectRedirects(), delegateQueue: nil)
    }

    public func requestJSON(
        method: String, path: [String], body: AnyJSON? = nil,
        query: [String: String] = [:], maximumResponseBytes: Int? = nil,
        authorize: @escaping @Sendable () async throws -> Void = {}
    ) async throws -> AnyJSON {
        try await checkAccount()
        try Task.checkCancellation()
        try await authorize()
        try Task.checkCancellation()
        let result = try await raw(method: method, path: path, body: body,
                                   query: query, maximumResponseBytes: maximumResponseBytes)
        // A switch can occur while the HTTP request is in flight. The caller
        // must reconcile mutations against this account before claiming success.
        do { try await checkAccount() }
        catch {
            if method == "GET" { throw error }
            if let recovery = AnyObjectCreationUncertain.lostConfirmation(method: method, path: path, response: result) {
                throw recovery
            }
            throw AnyEngineError.writeUncertain
        }
        return result
    }

    public func checkAccount() async throws {
        let auth = try await raw(method: "GET", path: ["v1", "auth"], body: nil)
        guard auth["authorized"]?.bool == true,
              auth["accountId"]?.string == expectedAccountID else {
            throw AnyEngineError.accountChanged
        }
    }

    func makeRequest(method: String, path: [String], body: AnyJSON?,
                     query: [String: String] = [:]) throws -> URLRequest {
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
        guard query.count <= 32, query.allSatisfy({ !$0.key.isEmpty && $0.key.utf8.count <= 128
            && $0.value.utf8.count <= 8192 && !$0.key.utf8.contains(0) && !$0.value.utf8.contains(0) }) else {
            throw AnyEngineError.invalidEndpoint
        }
        if !query.isEmpty {
            components?.queryItems = query.keys.sorted().map { URLQueryItem(name: $0, value: query[$0]) }
        }
        guard let url = components?.url else { throw AnyEngineError.invalidEndpoint }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let authorization {
            request.setValue(authorization.token, forHTTPHeaderField: "X-Any-Control-Token")
        }
        if let body {
            request.httpBody = try JSONEncoder().encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        return request
    }

    private func raw(method: String, path: [String], body: AnyJSON?,
                     query: [String: String] = [:], maximumResponseBytes: Int? = nil) async throws -> AnyJSON {
        if let bound = maximumResponseBytes {
            guard (1...64 * 1024 * 1024).contains(bound) else { throw AnyEngineError.readLimit }
        }
        let request = try makeRequest(method: method, path: path, body: body, query: query)
        let data: Data
        let response: URLResponse
        let diagnosticID = UUID().uuidString
        let diagnosticStart = ProcessInfo.processInfo.systemUptime
        pinkhaDiagnosticHTTPTrace(id: diagnosticID, phase: "begin", method: method,
            path: request.url?.path ?? "", start: diagnosticStart, response: nil, error: nil)
        do { (data, response) = try await session.data(for: request) }
        catch {
            pinkhaDiagnosticHTTPTrace(id: diagnosticID, phase: "error", method: method,
                path: request.url?.path ?? "", start: diagnosticStart, response: nil, error: error)
            if method == "GET" { throw error }; throw AnyEngineError.writeUncertain
        }
        pinkhaDiagnosticHTTPTrace(id: diagnosticID, phase: "response", method: method,
            path: request.url?.path ?? "", start: diagnosticStart,
            response: response as? HTTPURLResponse, error: nil)
        guard let http = response as? HTTPURLResponse else {
            throw AnyEngineError.malformedResponse("HTTP response")
        }
        if let maximumResponseBytes, data.count > maximumResponseBytes { throw AnyEngineError.readLimit }
        return try Self.decodeResponse(status: http.statusCode, data: data)
    }

    static func decodeResponse(status: Int, data: Data) throws -> AnyJSON {
        guard (200..<300).contains(status) else {
            let decoded = try? JSONDecoder().decode(AnyJSON.self, from: data)
            if let recovery = AnyObjectCreationUncertain.decode(status: status, response: decoded) {
                throw recovery
            }
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


// DIAGNOSTIC COPY ONLY: no body, query, authorization or arbitrary header values.
private func pinkhaDiagnosticHTTPTrace(
    id: String, phase: String, method: String, path: String, start: TimeInterval,
    response: HTTPURLResponse?, error: (any Error)?
) {
    var event: [String: Any] = [
        "id": id, "phase": phase, "method": method, "path": path,
        "elapsedMs": Int(max(0, ProcessInfo.processInfo.systemUptime - start) * 1000),
        "timestampUnixMs": Int64((Date().timeIntervalSince1970 * 1000).rounded(.down))
    ]
    if let response {
        event["status"] = response.statusCode
        var framing: [String: String] = [:]
        if let value = response.value(forHTTPHeaderField: "Content-Length") {
            framing["Content-Length"] = value.utf8.count <= 20 && !value.isEmpty &&
                value.utf8.allSatisfy({ (48...57).contains($0) }) ? value : "invalid"
        }
        if let value = response.value(forHTTPHeaderField: "Transfer-Encoding") {
            let value = value.lowercased().trimmingCharacters(in: .whitespaces)
            framing["Transfer-Encoding"] = ["chunked", "identity", "gzip", "deflate"].contains(value) ? value : "other"
        }
        if let value = response.value(forHTTPHeaderField: "Connection") {
            let value = value.lowercased().trimmingCharacters(in: .whitespaces)
            framing["Connection"] = ["close", "keep-alive"].contains(value) ? value : "other"
        }
        event["framing"] = framing
    }
    if let error {
        let nsError = error as NSError
        event["errorDomain"] = nsError.domain == NSURLErrorDomain ? "NSURLErrorDomain" : "other"
        event["errorCode"] = nsError.code
    }
    if let data = try? JSONSerialization.data(withJSONObject: event, options: [.sortedKeys]) {
        var line = Data("ANY_HTTP_TRACE ".utf8)
        line.append(data)
        line.append(Data([10]))
        FileHandle.standardError.write(line)
    }
}
