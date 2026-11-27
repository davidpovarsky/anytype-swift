import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeFileAttachmentError: Error, Equatable, Sendable {
    case invalidIntent
    case contentConflict
    /// Dispatch may have created an original native file. It must not be sent again.
    case writeUncertain
    /// Preserve the native response for presentation. The dispatch reservation
    /// remains unresolved; this response does not certify rollback or permit retry.
    case nativeResponse(status: Int, code: String)
    /// The original file ID is known, but complete readback has not been verified.
    case knownFileUnverified(String)
    case noRecordedAttachment
}

/// A user action has one durable identity. Only its hash and scoped mutation ID
/// enter the shared creation journal; no file name, local URL or bytes are stored.
public struct AnyNativeFileAttachmentIntent: Codable, Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let mutationID: String
    public let objectID: String
    public let name: String
    public let mime: String
    public let byteCount: Int64
    public let contentSHA256: String
    public let fingerprint: String

    public var identity: AnyNativeCreationIdentity {
        // Construction and decoding validate all of these fields.
        try! .init(workspace: workspace, mutationID: mutationID,
                   kind: "fileAttachment", fingerprint: fingerprint)
    }

    public init(workspace: AnyTorahWorkspace, mutationID: String, objectID: String,
                name: String, mime: String, byteCount: Int64, contentSHA256: String) throws {
        guard AnyNativeCreationIdentity.isHex(mutationID, count: 32) else {
            throw AnyNativeFileAttachmentError.invalidIntent
        }
        _ = try AnyNativeFileUploadSpecification(accountID: workspace.accountID,
            spaceID: workspace.spaceID, objectID: objectID, name: name, mime: mime,
            size: byteCount, contentSHA256: contentSHA256)
        let canonical: AnyJSON = .object([
            "domain": .string("pinkha-any-file-attachment/v1"),
            "account": .string(workspace.accountID), "space": .string(workspace.spaceID),
            "mutationID": .string(mutationID), "object": .string(objectID),
            "name": .string(name), "mime": .string(mime),
            "bytes": .integer(byteCount), "contentSHA256": .string(contentSHA256)
        ])
        self.workspace = workspace; self.mutationID = mutationID; self.objectID = objectID
        self.name = name; self.mime = mime; self.byteCount = byteCount
        self.contentSHA256 = contentSHA256
        self.fingerprint = AnyContentDigest.sha256(try AnyHostCanonical.bytes(canonical))
    }

    var specification: AnyNativeFileUploadSpecification {
        get throws {
            try .init(accountID: workspace.accountID, spaceID: workspace.spaceID,
                objectID: objectID, name: name, mime: mime, size: byteCount,
                contentSHA256: contentSHA256)
        }
    }

    private enum CodingKeys: String, CodingKey {
        case workspace, mutationID, objectID, name, mime, byteCount, contentSHA256, fingerprint
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(workspace: values.decode(AnyTorahWorkspace.self, forKey: .workspace),
            mutationID: values.decode(String.self, forKey: .mutationID),
            objectID: values.decode(String.self, forKey: .objectID),
            name: values.decode(String.self, forKey: .name),
            mime: values.decode(String.self, forKey: .mime),
            byteCount: values.decode(Int64.self, forKey: .byteCount),
            contentSHA256: values.decode(String.self, forKey: .contentSHA256))
        guard try values.decode(String.self, forKey: .fingerprint).utf8.elementsEqual(fingerprint.utf8) else {
            throw AnyNativeFileAttachmentError.contentConflict
        }
    }
}

/// Uploads through the original native FilesV2 route. Native Attach has no
/// caller idempotency key: the existing durable creation journal owns the one
/// permitted POST, and an unknown result is never changed into another POST.
/// Known IDs recover through metadata and plaintext readback only.
public actor AnyNativeFileAttachmentCreator {
    public nonisolated let workspace: AnyTorahWorkspace
    private let journal: any AnyNativeCreationJournaling
    public typealias Check = @Sendable () async throws -> Void
    typealias Receipt = @Sendable (AnyNativeAttachedFile) async throws -> Void
    typealias Upload = @Sendable (AnyNativeFileUploadSpecification, URL,
        @escaping Check, @escaping Check, @escaping Receipt) async throws -> AnyNativeAttachedFile
    typealias Inspect = @Sendable (AnyNativeFileUploadSpecification, String,
        @escaping Check) async throws -> AnyNativeAttachedFile
    typealias Digest = @Sendable (AnyNativeAttachedFile,
        @escaping Check) async throws -> AnyHTTPFileContentDigest
    private let upload: Upload
    private let inspect: Inspect
    private let digest: Digest

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                journal: any AnyNativeCreationJournaling) throws {
        guard Self.same(client.expectedAccountID, workspace.accountID),
              Self.sameWorkspace(journal.workspace, workspace) else { throw AnyHostError.wrongWorkspace }
        self.workspace = workspace; self.journal = journal
        let uploader = AnyNativeFileUploader(client: client)
        self.upload = { specification, fileURL, validate, authorize, retain in
            try await uploader.attach(specification: specification, fileURL: fileURL,
                validateScope: validate, authorizeDispatch: authorize, retainReceipt: retain)
        }
        self.inspect = { specification, fileID, authorize in
            try await uploader.info(specification: specification, fileID: fileID, authorize: authorize)
        }
        self.digest = { file, authorize in
            try await client.readFileContentDigest(spaceID: file.reference.spaceID,
                fileID: file.reference.fileID, size: file.byteCount, mime: file.mime,
                authorize: authorize)
        }
    }

    /// Component injection exercises the same journal, cancellation and readback
    /// state machine; production construction always uses original native HTTP.
    init(workspace: AnyTorahWorkspace, journal: any AnyNativeCreationJournaling,
         upload: @escaping Upload, inspect: @escaping Inspect, digest: @escaping Digest) throws {
        guard Self.sameWorkspace(journal.workspace, workspace) else { throw AnyHostError.wrongWorkspace }
        self.workspace = workspace; self.journal = journal
        self.upload = upload; self.inspect = inspect; self.digest = digest
    }

    public func recordedFileID(for intent: AnyNativeFileAttachmentIntent) async throws -> String? {
        try requireScope(intent)
        return try await journal.lookup(intent.identity)?.objectID
    }

    /// `authorizeRead` checks the live account, Space and consumer lifetime without
    /// consuming consent. `authorizeAttachment` admits the single user mutation.
    /// A concurrent call may stage a private copy but cannot acquire a second
    /// journal dispatch reservation or send another POST for this intent.
    public func attach(_ intent: AnyNativeFileAttachmentIntent, fileURL: URL,
                       authorizeRead: @escaping Check,
                       authorizeAttachment: @escaping Check) async throws -> AnyNativeAttachedFile {
        try requireScope(intent)
        try Task.checkCancellation()
        try await authorizeRead()
        if let state = try await journal.lookup(intent.identity) {
            guard let fileID = state.objectID else { throw AnyNativeFileAttachmentError.writeUncertain }
            return try await verify(intent, fileID: fileID, authorizeRead: authorizeRead)
        }
        let journal = journal
        let specification = try intent.specification
        do {
            let receipt = try await upload(specification, fileURL, authorizeRead, {
                try Task.checkCancellation()
                try await authorizeRead()
                // Persist before dispatch. If authorization or dispatch then
                // fails, keep the reservation rather than guessing no write.
                let reservation = try await journal.reserve(intent.identity)
                guard reservation.ownsDispatch else { throw AnyNativeFileAttachmentError.writeUncertain }
                try await authorizeAttachment()
                try Task.checkCancellation()
            }, { receipt in
                try Self.requireReceipt(receipt, specification: specification)
                // This callback precedes the HTTP client's postflight account
                // and consumer checks. Never journal into the newly active scope.
                try await journal.record(.created(receipt.reference.fileID), identity: intent.identity)
            })
            try Self.requireReceipt(receipt, specification: specification)
            return try await verify(intent, fileID: receipt.reference.fileID,
                expectedReceipt: receipt, authorizeRead: authorizeRead)
        } catch let uncertain as AnyNativeFileUploadUncertain {
            if let receipt = uncertain.knownReceipt,
               (try? Self.requireAcknowledgement(receipt, specification: specification)) != nil {
                throw AnyNativeFileAttachmentError.knownFileUnverified(receipt.reference.fileID)
            }
            if let native = uncertain.underlying as? AnyEngineError,
               case .http(let status, let code) = native {
                throw AnyNativeFileAttachmentError.nativeResponse(status: status, code: code)
            }
            throw AnyNativeFileAttachmentError.writeUncertain
        }
    }

    /// Safe after cancellation, process restart, or a lost UI response when the
    /// original file ID was retained. It never calls the native attachment route.
    /// An unresolved reservation with no ID stays unresolved; matching filenames
    /// or content among concurrent uploads cannot prove which one this call made.
    /// The metadata journal retains the original ID and input fingerprint, not
    /// the native-normalized 201 metadata. A resumed result proves current stable
    /// metadata and the original content digest; it does not assert that metadata
    /// has never changed since the original acknowledgement.
    public func resume(_ intent: AnyNativeFileAttachmentIntent,
                       authorizeRead: @escaping Check) async throws -> AnyNativeAttachedFile {
        try requireScope(intent)
        try Task.checkCancellation()
        try await authorizeRead()
        guard let state = try await journal.lookup(intent.identity) else {
            throw AnyNativeFileAttachmentError.noRecordedAttachment
        }
        guard let fileID = state.objectID else { throw AnyNativeFileAttachmentError.writeUncertain }
        return try await verify(intent, fileID: fileID, authorizeRead: authorizeRead)
    }

    private func verify(_ intent: AnyNativeFileAttachmentIntent, fileID: String,
                        expectedReceipt: AnyNativeAttachedFile? = nil,
                        authorizeRead: @escaping Check) async throws -> AnyNativeAttachedFile {
        let specification = try intent.specification
        do {
            try Task.checkCancellation()
            try await authorizeRead()
            let before = try await inspect(specification, fileID, authorizeRead)
            try Self.requireReceipt(before, specification: specification, fileID: fileID)
            if let expectedReceipt {
                guard Self.sameMetadata(expectedReceipt, before) else {
                    throw AnyNativeFileAttachmentError.knownFileUnverified(fileID)
                }
            }
            let content = try await digest(before, authorizeRead)
            guard content.byteCount == intent.byteCount,
                  Self.same(content.sha256, intent.contentSHA256) else {
                throw AnyNativeFileAttachmentError.knownFileUnverified(fileID)
            }
            let after = try await inspect(specification, fileID, authorizeRead)
            try Self.requireReceipt(after, specification: specification, fileID: fileID)
            guard Self.sameMetadata(before, after) else {
                throw AnyNativeFileAttachmentError.knownFileUnverified(fileID)
            }
            // Cached/durable may legitimately advance during the content read.
            // The returned status is the actual final native observation.
            try await journal.record(.verified(fileID), identity: intent.identity)
            try Task.checkCancellation()
            try await authorizeRead()
            return after
        } catch {
            throw AnyNativeFileAttachmentError.knownFileUnverified(fileID)
        }
    }

    private func requireScope(_ intent: AnyNativeFileAttachmentIntent) throws {
        guard Self.sameWorkspace(intent.workspace, workspace) else { throw AnyHostError.wrongWorkspace }
    }

    private static func requireReceipt(_ receipt: AnyNativeAttachedFile,
        specification: AnyNativeFileUploadSpecification, fileID: String? = nil) throws {
        try requireAcknowledgement(.init(receipt: receipt), specification: specification, fileID: fileID)
    }

    private static func requireAcknowledgement(_ receipt: AnyNativeFileUploadAcknowledgement,
        specification: AnyNativeFileUploadSpecification, fileID: String? = nil) throws {
        let reference = receipt.reference
        guard same(reference.accountID, specification.accountID),
              same(reference.spaceID, specification.spaceID),
              same(reference.objectID, specification.objectID),
              fileID.map({ same($0, reference.fileID) }) ?? true,
              receipt.byteCount == specification.size else {
            throw AnyNativeFileAttachmentError.writeUncertain
        }
    }

    private static func same(_ a: String, _ b: String) -> Bool { a.utf8.elementsEqual(b.utf8) }
    private static func sameMetadata(_ a: AnyNativeAttachedFile, _ b: AnyNativeAttachedFile) -> Bool {
        let sameRoot: Bool
        switch (a.rootCID, b.rootCID) {
        case (nil, nil): sameRoot = true
        case (.some(let left), .some(let right)): sameRoot = same(left, right)
        default: sameRoot = false
        }
        return same(a.name, b.name) && same(a.mime, b.mime) && sameRoot && a.inline == b.inline
    }
    private static func sameWorkspace(_ a: AnyTorahWorkspace, _ b: AnyTorahWorkspace) -> Bool {
        same(a.accountID, b.accountID) && same(a.spaceID, b.spaceID)
    }
}
