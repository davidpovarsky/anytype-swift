import Foundation
import Crypto
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

    /// Stream a verified private copy to the separate prepared-file route.
    /// Neither the source file nor its complete bytes are retained in memory.
    /// A transport failure can have committed native preparation: callers must
    /// reconcile the immutable intent before deciding to retry.
    public func prepareMigrationFileJSON(
        path: [String], metadata: AnyJSON, fileURL: URL,
        size: Int64, contentSHA256: String,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyJSON {
        guard path.count == 9, path[0] == "v1", path[1] == "spaces",
              Array(path[3...5]) == ["pinkha", "migration", "intents"],
              Array(path[7...8]) == ["file", "prepare"],
              (4096...Int64(512 << 20)).contains(size),
              contentSHA256.utf8.count == 64,
              contentSHA256.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            throw AnyEngineError.invalidOperation("prepared file bounds")
        }
        let header = try JSONEncoder().encode(metadata).base64EncodedString()
        guard header.utf8.count <= 16 << 10 else { throw AnyEngineError.readLimit }
        try await checkAccount()
        try await authorize()
        try Task.checkCancellation()
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-migration-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        defer { try? FileManager.default.removeItem(at: directory) }
        let copy = directory.appendingPathComponent("payload")
        try Self.copyVerifiedMigrationFile(from: fileURL, to: copy, size: size, digest: contentSHA256)
        try await checkAccount()
        try await authorize()
        try Task.checkCancellation()
        var request = try makeRequest(method: "PUT", path: path, body: nil)
        request.timeoutInterval = 120
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        request.setValue(String(size), forHTTPHeaderField: "Content-Length")
        request.setValue(header, forHTTPHeaderField: "X-Pinkha-Migration")
        let data: Data
        let response: URLResponse
        do { (data, response) = try await session.upload(for: request, fromFile: copy) }
        catch { throw AnyEngineError.writeUncertain }
        guard let http = response as? HTTPURLResponse else { throw AnyEngineError.writeUncertain }
        guard data.count <= 65_536 else { throw AnyEngineError.writeUncertain }
        let result = try Self.decodeResponse(status: http.statusCode, data: data)
        do { try await checkAccount(); try await authorize(); try Task.checkCancellation() }
        catch { throw AnyEngineError.writeUncertain }
        return result
    }

    static func copyVerifiedMigrationFile(from source: URL, to destination: URL, size: Int64, digest: String) throws {
        guard source.isFileURL, destination.isFileURL,
              (4096...Int64(512 << 20)).contains(size) else { throw AnyEngineError.invalidOperation("prepared file bounds") }
        let attributes = try source.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard attributes.isRegularFile == true, attributes.isSymbolicLink != true,
              attributes.fileSize == Int(size) else { throw AnyEngineError.invalidOperation("prepared file source changed") }
        guard FileManager.default.createFile(atPath: destination.path, contents: nil, attributes: [.posixPermissions: 0o600]) else {
            throw AnyEngineError.invalidOperation("prepared file private staging")
        }
        let input = try FileHandle(forReadingFrom: source)
        defer { try? input.close() }
        let output = try FileHandle(forWritingTo: destination)
        defer { try? output.close() }
        var hash = SHA256()
        var count: Int64 = 0
        while let bytes = try input.read(upToCount: 1 << 20), !bytes.isEmpty {
            try Task.checkCancellation()
            count += Int64(bytes.count)
            guard count <= size else { throw AnyEngineError.invalidOperation("prepared file source changed") }
            hash.update(data: bytes)
            try output.write(contentsOf: bytes)
        }
        let actual = hash.finalize().map { String(format: "%02x", $0) }.joined()
        guard count == size, actual == digest else { throw AnyEngineError.invalidOperation("prepared file content digest differs") }
        try output.close()
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
        do { (data, response) = try await session.data(for: request) }
        catch { if method == "GET" { throw error }; throw AnyEngineError.writeUncertain }
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
