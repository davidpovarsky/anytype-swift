import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Caller metadata is a hint to the original native route. That route may
/// infer a MIME type or append a missing filename extension. Neither hint is
/// an assertion about the returned native metadata or network custody.
public struct AnyNativeFileUploadSpecification: Sendable {
    public static let maximumByteCount: Int64 = 512 * 1024 * 1024
    public let accountID: String
    public let spaceID: String
    public let objectID: String
    public let name: String
    public let mime: String
    public let size: Int64
    public let contentSHA256: String

    public init(accountID: String, spaceID: String, objectID: String,
                name: String, mime: String, size: Int64, contentSHA256: String) throws {
        // Reuse the native file namespace's exact scope validation. This
        // placeholder validates scope only; no file ID is allocated here.
        _ = try AnyNativeFileReference(accountID: accountID, spaceID: spaceID,
                                      objectID: objectID, fileID: "scope-validation")
        guard (0...Self.maximumByteCount).contains(size),
              Self.validName(name), Self.validMIMEHint(mime),
              contentSHA256.utf8.count == 64,
              contentSHA256.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            throw AnyNativeFileUploadError.invalidSpecification
        }
        self.accountID = accountID; self.spaceID = spaceID; self.objectID = objectID
        self.name = name; self.mime = mime; self.size = size; self.contentSHA256 = contentSHA256
    }

    static func validName(_ value: String) -> Bool {
        value.utf8.count <= 8_192 && value.utf8.allSatisfy { $0 >= 32 && $0 != 127 }
    }

    static func validResolvedName(_ value: String) -> Bool {
        // Native ensureNameExt can append to an already maximum-length hint.
        value.utf8.count <= 16_384 && value.utf8.allSatisfy { $0 >= 32 && $0 != 127 }
    }

    static func validMIMEHint(_ value: String) -> Bool {
        // Preserve safe header parameters and spelling; the native resolver
        // owns parsing, normalization, sniffing and filename refinement.
        value.utf8.count <= 1_024 && value.utf8.allSatisfy { (32...126).contains($0) }
    }

    static func validResolvedMIME(_ value: String) -> Bool {
        if value.isEmpty { return true }
        guard value.utf8.count <= 1_024 else { return false }
        let parts = value.split(separator: "/", omittingEmptySubsequences: false)
        guard parts.count == 2 else { return false }
        let token = Set("!#$%&'*+-.^_`|~".utf8)
        return parts.allSatisfy { part in
            !part.isEmpty && part.utf8.allSatisfy {
                (48...57).contains($0) || (65...90).contains($0) ||
                    (97...122).contains($0) || token.contains($0)
            }
        }
    }
}

public enum AnyNativeFileUploadError: Error, Equatable, Sendable {
    case invalidSpecification
    case invalidSource
    case sourceChanged
    case contentMismatch
    case stagingUnavailable
    case stagingChanged
    case ioFailure
    case redirectRefused
}

public struct AnyNativeFileSourceFingerprint: Sendable {
    public let byteCount: Int64
    public let sha256: String
}

/// Validated native data, not a transferable authorization capability. Its
/// account and Space are the original request scope; FileInfo itself does not
/// advertise them. A successful attachment is not a plaintext readback proof.
public struct AnyNativeAttachedFile: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let reference: AnyNativeFileReference
    public let byteCount: Int64
    public let name: String
    public let mime: String
    public let rootCID: String?
    public let inline: Bool
    public let durable: Bool
    public let cached: Bool

    public init(native: AnyJSON, specification: AnyNativeFileUploadSpecification,
                expectedFileID: String? = nil) throws {
        guard let object = native.object,
              let fileID = object["fileId"]?.string,
              let objectID = object["objectId"]?.string,
              objectID.utf8.elementsEqual(specification.objectID.utf8),
              let byteCount = object["size"]?.integer, byteCount == specification.size,
              let inline = object["inline"]?.bool,
              let durable = object["durable"]?.bool,
              let cached = object["cached"]?.bool else {
            throw AnyEngineError.malformedResponse("file attachment scope or fields")
        }
        if let expectedFileID, !fileID.utf8.elementsEqual(expectedFileID.utf8) {
            throw AnyEngineError.malformedResponse("file attachment identity")
        }
        let reference = try AnyNativeFileReference(accountID: specification.accountID,
            spaceID: specification.spaceID, objectID: objectID, fileID: fileID)
        // These are absent in the original API. An explicitly conflicting
        // extension field must not be silently relabelled into our scope.
        for (key, expected) in [("accountId", specification.accountID), ("spaceId", specification.spaceID)] {
            if let value = object[key] {
                guard let text = value.string, text.utf8.elementsEqual(expected.utf8) else {
                    throw AnyEngineError.malformedResponse("file attachment extended scope")
                }
            }
        }
        let name = try Self.optionalString(object, key: "name")
        let mime = try Self.optionalString(object, key: "mime")
        let root = try Self.optionalString(object, key: "rootCid")
        guard AnyNativeFileUploadSpecification.validResolvedName(name),
              AnyNativeFileUploadSpecification.validResolvedMIME(mime),
              try Self.optionalString(object, key: "variant").isEmpty,
              try Self.optionalString(object, key: "variantOf").isEmpty else {
            throw AnyEngineError.malformedResponse("file attachment original metadata")
        }
        if inline {
            guard root.isEmpty, durable, cached else {
                throw AnyEngineError.malformedResponse("inline file attachment storage")
            }
        } else {
            // Validate this opaque native content address with the same safe
            // component rules. The original SDK, not this wrapper, verifies CID
            // cryptography and encrypted storage contents.
            _ = try AnyNativeFileReference(accountID: specification.accountID,
                spaceID: specification.spaceID, objectID: objectID, fileID: root)
        }
        self.reference = reference; self.byteCount = byteCount
        self.name = name; self.mime = mime; self.rootCID = root.isEmpty ? nil : root
        self.inline = inline; self.durable = durable; self.cached = cached
    }

    private static func optionalString(_ object: [String: AnyJSON], key: String) throws -> String {
        guard let value = object[key] else { return "" }
        guard let text = value.string else {
            throw AnyEngineError.malformedResponse("file attachment optional field")
        }
        return text
    }

    public var description: String {
        "AnyNativeAttachedFile(bytes: \(byteCount), inline: \(inline), durable: \(durable), cached: \(cached), private metadata redacted)"
    }
    public var debugDescription: String { description }
}

/// The one-shot dispatch callback has been entered. Native effects must not be
/// retried automatically. A typed native HTTP/rejection error is retained in
/// `underlying`; even that error is not a rollback receipt. A known native file
/// ID remains available if durable journaling or the postflight lease failed.
/// Resolved private metadata is deliberately absent after a failed lease.
public struct AnyNativeFileUploadAcknowledgement: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let reference: AnyNativeFileReference
    public let byteCount: Int64

    public init(receipt: AnyNativeAttachedFile) {
        reference = receipt.reference; byteCount = receipt.byteCount
    }

    public var description: String { "AnyNativeFileUploadAcknowledgement(identity only, bytes: \(byteCount))" }
    public var debugDescription: String { description }
}

public struct AnyNativeFileUploadUncertain: Error, Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let knownReceipt: AnyNativeFileUploadAcknowledgement?
    public let underlying: any Error

    public init(knownReceipt: AnyNativeFileUploadAcknowledgement?, underlying: any Error) {
        self.knownReceipt = knownReceipt; self.underlying = underlying
    }

    public var description: String {
        "AnyNativeFileUploadUncertain(known receipt: \(knownReceipt != nil), private context redacted)"
    }
    public var debugDescription: String { description }
}

/// Original FilesV2 attachment and metadata routes. One invocation admits at
/// most one POST, with no redirect, hidden retry, deduplication or deletion.
/// The Host's durable intent journal must serialize invocations of one action.
public struct AnyNativeFileUploader: Sendable {
    public typealias Check = @Sendable () async throws -> Void
    private let client: AnyHTTPClient
    public init(client: AnyHTTPClient) { self.client = client }

    /// A bounded local selection-to-intent pass, without an account, staging
    /// copy or network access. The caller keeps security-scoped file access
    /// alive and invokes this work off the main actor. Attachment subsequently
    /// makes a second, independently verified bounded copy of these exact bytes.
    public static func fingerprint(fileURL: URL) async throws -> AnyNativeFileSourceFingerprint {
        try Task.checkCancellation()
        return try AnyNativeFileUploadStaging.fingerprint(source: fileURL)
    }

    public func attach(
        specification: AnyNativeFileUploadSpecification,
        fileURL: URL,
        validateScope: @escaping Check,
        authorizeDispatch: @escaping Check,
        retainReceipt: @escaping @Sendable (AnyNativeAttachedFile) async throws -> Void
    ) async throws -> AnyNativeAttachedFile {
        try requireAccount(specification)
        try Task.checkCancellation()
        try await client.checkAccount()
        try await validateScope()
        try Task.checkCancellation()
        // Opening, copying and hashing the private staging file all finish
        // before the caller can reserve or consume its one-shot dispatch.
        let staged = try AnyNativeFileUploadStaging.copy(source: fileURL, specification: specification)
        defer { staged.finish() }
        var request = try client.makeRequest(method: "POST",
            path: ["v1", "spaces", specification.spaceID, "objects", specification.objectID, "files"],
            body: nil, query: ["name": specification.name])
        request.setValue(specification.mime.isEmpty ? nil : specification.mime, forHTTPHeaderField: "Content-Type")
        request.setValue(String(specification.size), forHTTPHeaderField: "Content-Length")
        request.setValue("identity", forHTTPHeaderField: "Accept-Encoding")
        request.timeoutInterval = 120
        try await client.checkAccount()
        try await validateScope()
        try Task.checkCancellation()
        try staged.requireUnchangedSourceAndCopy()
        var knownReceipt: AnyNativeFileUploadAcknowledgement?
        do {
            // A callback may persist its reservation and then throw. Entering
            // it is therefore the point after which we preserve uncertainty.
            try await authorizeDispatch()
            try Task.checkCancellation()
            try staged.requireUnchangedSourceAndCopy()
            let (data, response) = try await AnyNativeFileUploadResponse().perform(request, fileURL: staged.fileURL)
            let native = try AnyHTTPClient.decodeResponse(status: response.statusCode, data: data)
            guard response.statusCode == 201 else {
                throw AnyEngineError.malformedResponse("file attachment HTTP status")
            }
            let receipt = try AnyNativeAttachedFile(native: native, specification: specification)
            knownReceipt = .init(receipt: receipt)
            // Do not check cancellation/account/consumer lifetime between the
            // validated acknowledgement and this original-scope journal write.
            try await retainReceipt(receipt)
            try await client.checkAccount()
            try await validateScope()
            try Task.checkCancellation()
            try staged.requireUnchangedCopy()
            return receipt
        } catch {
            throw AnyNativeFileUploadUncertain(knownReceipt: knownReceipt, underlying: error)
        }
    }

    /// Read one known original file. MIME and name are the native resolved
    /// metadata, not necessarily the request hints. This does not verify file
    /// bytes; pair it with readFileContentDigest and another info read.
    public func info(
        specification: AnyNativeFileUploadSpecification,
        fileID: String,
        authorize: @escaping Check
    ) async throws -> AnyNativeAttachedFile {
        try requireAccount(specification)
        _ = try AnyNativeFileReference(accountID: specification.accountID,
            spaceID: specification.spaceID, objectID: specification.objectID, fileID: fileID)
        try Task.checkCancellation()
        try await client.checkAccount()
        try await authorize()
        try Task.checkCancellation()
        var request = try client.makeRequest(method: "GET",
            path: ["v1", "spaces", specification.spaceID, "files", fileID], body: nil)
        request.setValue("identity", forHTTPHeaderField: "Accept-Encoding")
        let (data, response) = try await AnyNativeFileUploadResponse().perform(request, fileURL: nil)
        let native = try AnyHTTPClient.decodeResponse(status: response.statusCode, data: data)
        guard response.statusCode == 200 else {
            throw AnyEngineError.malformedResponse("file info HTTP status")
        }
        let result = try AnyNativeAttachedFile(native: native, specification: specification, expectedFileID: fileID)
        try await client.checkAccount()
        try await authorize()
        try Task.checkCancellation()
        return result
    }

    private func requireAccount(_ specification: AnyNativeFileUploadSpecification) throws {
        guard specification.accountID.utf8.elementsEqual(client.expectedAccountID.utf8) else {
            throw AnyEngineError.accountChanged
        }
    }
}
