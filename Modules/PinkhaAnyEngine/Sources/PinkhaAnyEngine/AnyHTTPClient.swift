import Foundation
import Crypto
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif
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

public struct AnyHTTPJSONResponse: Sendable {
    public let statusCode: Int
    public let body: AnyJSON
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
        validateResponse: (@Sendable () async throws -> Void)? = nil,
        authorize: @escaping @Sendable () async throws -> Void = {}
    ) async throws -> AnyJSON {
        try await requestJSONResponse(method: method, path: path, body: body, query: query,
                                      maximumResponseBytes: maximumResponseBytes,
                                      validateResponse: validateResponse, authorize: authorize).body
    }

    /// Preserve HTTP 202 versus 201 for native asynchronous operations such as joining.
    /// `authorize` admits dispatch and may consume a one-shot mutation approval. GET
    /// rechecks it before delivering the response unless `validateResponse` is supplied.
    /// Mutations can supply a separate, side-effect-free response lifetime check;
    /// their dispatch approval is never consumed again. Callers that journal native
    /// receipts must retain them in the original scope before publishing to a consumer.
    public func requestJSONResponse(
        method: String, path: [String], body: AnyJSON? = nil,
        query: [String: String] = [:], maximumResponseBytes: Int? = nil,
        validateResponse: (@Sendable () async throws -> Void)? = nil,
        authorize: @escaping @Sendable () async throws -> Void = {}
    ) async throws -> AnyHTTPJSONResponse {
        try await checkAccount()
        try Task.checkCancellation()
        try await authorize()
        try Task.checkCancellation()
        let result = try await rawResponse(method: method, path: path, body: body,
                                           query: query, maximumResponseBytes: maximumResponseBytes)
        // A switch can occur while the HTTP request is in flight. The caller
        // must reconcile mutations against this account before claiming success.
        do {
            try await checkAccount()
            if let validateResponse { try await validateResponse() }
            else if method == "GET" { try await authorize() }
            try Task.checkCancellation()
        } catch {
            if method == "GET" { throw error }
            if let recovery = AnyObjectCreationUncertain.lostConfirmation(method: method, path: path, response: result.body) {
                throw recovery
            }
            throw AnyEngineError.writeUncertain
        }
        return result
    }

    public func checkAccount() async throws {
        let auth = try await raw(method: "GET", path: ["v1", "auth"], body: nil)
        guard auth["authorized"]?.bool == true,
              let actualAccountID = auth["accountId"]?.string,
              actualAccountID.utf8.elementsEqual(expectedAccountID.utf8) else {
            throw AnyEngineError.accountChanged
        }
    }

    /// Read the server's current account/network/run tuple. Legacy servers
    /// fail this contract explicitly; there is no unbound write fallback.
    public func nativeAccountRunBinding(expectedNetworkID: String) async throws -> AnyNativeAccountRunBinding {
        let value = try await requestJSON(method: "GET",
            path: ["v1", "auth", "engine-binding"], maximumResponseBytes: 16_384)
        return try .decode(value, expectedAccountID: expectedAccountID,
                           expectedNetworkID: expectedNetworkID)
    }

    public func requireNativeAccountRun(_ binding: AnyNativeAccountRunBinding) async throws {
        guard binding.accountID.utf8.elementsEqual(expectedAccountID.utf8),
              try await nativeAccountRunBinding(expectedNetworkID: binding.networkID) == binding else {
            throw AnyEngineError.accountChanged
        }
    }

    /// Dispatch once against the captured native engine. The native gate
    /// verifies the tuple and the current signed authority before the effect.
    /// After a valid acknowledgment this method performs no awaited check:
    /// callers first retain it, then validate their lease/current membership.
    public func dispatchBoundJSONResponse(
        method: String, path: [String], body: AnyJSON,
        binding: AnyNativeAccountRunBinding, maximumResponseBytes: Int = 65_536,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyNativeBoundMutationResponse {
        try AnyNativeAccountRunBinding.requireRoute(method: method, path: path)
        try await requireNativeAccountRun(binding)
        try Task.checkCancellation()
        try await authorize()
        try Task.checkCancellation()
        let response = try await rawResponse(method: method, path: path, body: body,
            maximumResponseBytes: maximumResponseBytes, nativeBinding: binding)
        return .init(binding: binding, response: response)
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
        try await rawResponse(method: method, path: path, body: body, query: query,
                              maximumResponseBytes: maximumResponseBytes).body
    }

    private func rawResponse(method: String, path: [String], body: AnyJSON?,
                             query: [String: String] = [:],
                             maximumResponseBytes: Int? = nil,
                             nativeBinding: AnyNativeAccountRunBinding? = nil) async throws -> AnyHTTPJSONResponse {
        if let bound = maximumResponseBytes {
            guard (1...64 * 1024 * 1024).contains(bound) else { throw AnyEngineError.readLimit }
        }
        var request = try makeRequest(method: method, path: path, body: body, query: query)
        if let nativeBinding {
            try AnyNativeAccountRunBinding.requireRoute(method: method, path: path)
            guard nativeBinding.accountID.utf8.elementsEqual(expectedAccountID.utf8) else {
                throw AnyEngineError.accountChanged
            }
            nativeBinding.apply(to: &request)
        }
        let data: Data
        let response: URLResponse
        do { (data, response) = try await session.data(for: request) }
        catch { if method == "GET" { throw error }; throw AnyEngineError.writeUncertain }
        guard let http = response as? HTTPURLResponse else {
            if nativeBinding != nil { throw AnyEngineError.writeUncertain }
            throw AnyEngineError.malformedResponse("HTTP response")
        }
        if let maximumResponseBytes, data.count > maximumResponseBytes {
            throw method == "GET" ? AnyEngineError.readLimit : AnyEngineError.writeUncertain
        }
        do {
            if let nativeBinding, (200..<300).contains(http.statusCode) {
                try nativeBinding.requireResponse(http)
            }
            return AnyHTTPJSONResponse(statusCode: http.statusCode,
                                       body: try Self.decodeResponse(status: http.statusCode, data: data))
        } catch {
            // Dispatch already happened. A malformed successful mutation receipt
            // cannot prove that no write occurred. Keep explicit native
            // rejections typed; callers must reconcile every other uncertain ack.
            if method != "GET", (200..<300).contains(http.statusCode) {
                if let native = error as? AnyEngineError, case .writeRejected = native {
                    throw native
                }
                throw AnyEngineError.writeUncertain
            }
            throw error
        }
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


public struct AnyHTTPFileContentDigest: Codable, Equatable, Sendable {
    public let byteCount: Int64
    public let sha256: String
}

extension AnyHTTPClient {
    /// Read the original native plaintext content in bounded HTTP ranges.
    /// A digest proves these bytes; it does not assert cloud custody.
    public func readFileContentDigest(
        spaceID: String, fileID: String, size: Int64, mime: String,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyHTTPFileContentDigest {
        try await readFileContent(spaceID: spaceID, fileID: fileID, size: size,
                                  mime: mime, output: nil, authorize: authorize)
    }

    /// Write only a newly created file in an existing private app directory.
    /// No runtime URL or bearer capability is returned or stored. A supplied
    /// plaintext digest must match before the output is committed.
    public func downloadFileContent(
        spaceID: String, fileID: String, size: Int64, mime: String, to destination: URL,
        expectedSHA256: String? = nil,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> String {
        if let expectedSHA256 {
            guard expectedSHA256.utf8.count == 64,
                  expectedSHA256.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
                throw AnyEngineError.invalidOperation("file content digest")
            }
        }
        try await checkAccount(); try await authorize(); try Task.checkCancellation()
        let output = try AnyHTTPPrivateDownload(destination)
        defer { output.finish() }
        let result = try await readFileContent(spaceID: spaceID, fileID: fileID, size: size,
                                              mime: mime, output: output.handle, authorize: authorize)
        guard expectedSHA256.map({ $0 == result.sha256 }) ?? true else {
            throw AnyEngineError.invalidOperation("file content digest differs")
        }
        try output.commit()
        return result.sha256
    }

    private func readFileContent(
        spaceID: String, fileID: String, size: Int64, mime: String, output: FileHandle?,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyHTTPFileContentDigest {
        guard (0...Int64(512 << 20)).contains(size), !spaceID.isEmpty, !fileID.isEmpty,
              mime.utf8.count <= 1024, !mime.contains("\r"), !mime.contains("\n") else {
            throw AnyEngineError.invalidOperation("file content bounds")
        }
        let contentType = mime.isEmpty ? "application/octet-stream" : mime
        var offset: Int64 = 0
        var hash = SHA256()
        repeat {
            try await checkAccount(); try await authorize(); try Task.checkCancellation()
            let length = min(Int64(1 << 20), size - offset)
            var request = try makeRequest(method: "GET",
                path: ["v1", "spaces", spaceID, "files", fileID, "content"], body: nil)
            request.setValue(contentType, forHTTPHeaderField: "Accept")
            request.setValue("identity", forHTTPHeaderField: "Accept-Encoding")
            if size > 0 {
                request.setValue("bytes=\(offset)-\(offset + length - 1)", forHTTPHeaderField: "Range")
            }
            let read = AnyHTTPBoundedFileRead(maximumBytes: max(Int(length), 65_536))
            let (data, response) = try await read.read(request)
            try await checkAccount(); try await authorize(); try Task.checkCancellation()
            guard let http = response as? HTTPURLResponse else {
                throw AnyEngineError.malformedResponse("file content HTTP response")
            }
            guard (200..<300).contains(http.statusCode) else {
                _ = try Self.decodeResponse(status: http.statusCode, data: data)
                throw AnyEngineError.malformedResponse("file content status")
            }
            guard http.url == request.url, Int64(data.count) == length,
                  http.value(forHTTPHeaderField: "Content-Type") == contentType,
                  http.value(forHTTPHeaderField: "Content-Encoding").map({ $0 == "identity" }) ?? true,
                  http.statusCode == (size == 0 ? 200 : 206),
                  size == 0 || http.value(forHTTPHeaderField: "Content-Range") ==
                    "bytes \(offset)-\(offset + length - 1)/\(size)" else {
                throw AnyEngineError.malformedResponse("file content range, size, MIME or identity")
            }
            hash.update(data: data)
            try output?.write(contentsOf: data)
            offset += length
        } while offset < size
        try await checkAccount(); try await authorize(); try Task.checkCancellation()
        return .init(byteCount: offset, sha256: hash.finalize().map { String(format: "%02x", $0) }.joined())
    }
}

/// This object has one lexical owner, held until the async read has finished.
/// Its open directory descriptor fixes cleanup to the same directory even if
/// the caller renames the directory while the read is suspended.
private final class AnyHTTPPrivateDownload {
    let handle: FileHandle
    private let directory: Int32
    private let name: String
    private var committed = false
    private var finished = false

    init(_ destination: URL) throws {
        guard destination.isFileURL, destination.lastPathComponent != ".",
              destination.lastPathComponent != "..", !destination.lastPathComponent.isEmpty else {
            throw AnyEngineError.invalidOperation("private file destination")
        }
        let parent = destination.deletingLastPathComponent()
        let directory = open(parent.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard directory >= 0 else { throw AnyEngineError.invalidOperation("private file directory") }
        var attributes = stat()
        guard fstat(directory, &attributes) == 0,
              attributes.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              attributes.st_mode & mode_t(0o077) == 0, attributes.st_uid == geteuid() else {
            close(directory)
            throw AnyEngineError.invalidOperation("private file directory permissions")
        }
        let name = destination.lastPathComponent
        let descriptor = openat(directory, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, mode_t(0o600))
        guard descriptor >= 0 else {
            close(directory)
            throw AnyEngineError.invalidOperation("private file destination already exists or is unavailable")
        }
        self.directory = directory; self.name = name
        handle = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true)
    }

    func commit() throws {
        try handle.synchronize()
        try handle.close()
        committed = true
    }

    func finish() {
        guard !finished else { return }
        finished = true
        try? handle.close()
        if !committed { _ = unlinkat(directory, name, 0) }
        _ = close(directory)
    }
}


/// One request owns one serial data delegate. The lock also covers task
/// cancellation, which can arrive off the delegate queue. Response bytes are
/// refused before append once the fixed range/error-envelope ceiling is met.
private final class AnyHTTPBoundedFileRead: NSObject, URLSessionDataDelegate, @unchecked Sendable {
    private let maximumBytes: Int
    private let lock = NSLock()
    private var continuation: CheckedContinuation<(Data, URLResponse), any Error>?
    private var currentSession: URLSession?
    private var currentTask: URLSessionDataTask?
    private var response: URLResponse?
    private var bytes = Data()
    private var finished = false

    init(maximumBytes: Int) { self.maximumBytes = maximumBytes }

    func read(_ request: URLRequest) async throws -> (Data, URLResponse) {
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            return try await withCheckedThrowingContinuation { continuation in
                let configuration = URLSessionConfiguration.ephemeral
                configuration.httpShouldSetCookies = false
                configuration.urlCache = nil
                configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
                let queue = OperationQueue()
                queue.maxConcurrentOperationCount = 1
                let session = URLSession(configuration: configuration, delegate: self, delegateQueue: queue)
                let task = session.dataTask(with: request)
                lock.lock()
                guard !finished else {
                    lock.unlock()
                    session.invalidateAndCancel()
                    continuation.resume(throwing: CancellationError())
                    return
                }
                self.continuation = continuation
                currentSession = session; currentTask = task
                lock.unlock()
                task.resume()
            }
        } onCancel: {
            self.finish(.failure(CancellationError()))
        }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest,
                    completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        completionHandler(nil)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse,
                    completionHandler: @escaping @Sendable (URLSession.ResponseDisposition) -> Void) {
        guard response.expectedContentLength <= Int64(maximumBytes) else {
            completionHandler(.cancel)
            finish(.failure(AnyEngineError.readLimit))
            return
        }
        lock.lock()
        let active = !finished
        if active { self.response = response }
        lock.unlock()
        completionHandler(active ? .allow : .cancel)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        guard data.count <= maximumBytes - bytes.count else {
            lock.unlock(); finish(.failure(AnyEngineError.readLimit)); return
        }
        bytes.append(data)
        lock.unlock()
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: (any Error)?) {
        lock.lock()
        let result: Result<(Data, URLResponse), any Error>
        if let error { result = .failure(error) }
        else if let response { result = .success((bytes, response)) }
        else { result = .failure(AnyEngineError.malformedResponse("file content HTTP response")) }
        lock.unlock()
        finish(result)
    }

    private func finish(_ result: Result<(Data, URLResponse), any Error>) {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        finished = true
        let continuation = continuation, task = currentTask, session = currentSession
        self.continuation = nil; currentTask = nil; currentSession = nil
        bytes = Data()
        lock.unlock()
        task?.cancel()
        session?.invalidateAndCancel()
        continuation?.resume(with: result)
    }
}
