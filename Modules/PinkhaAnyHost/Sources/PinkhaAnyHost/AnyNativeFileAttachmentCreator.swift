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
    /// The current owner already holds its bounded set of unresolved receipts.
    /// This error never authorizes resending an existing reserved operation.
    case recoveryCapacityReached
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

/// A process-local original native acknowledgement, minted only by this module.
/// It is deliberately not Codable and exposes no mutable or public initializer.
/// A caller may retain it while draining/closing a failed journal owner, then
/// present it to a new owner of the SAME original durable journal reservation.
/// This is not proof that the acknowledgement itself reached durable storage.
public struct AnyNativeFileAttachmentRecoveryReceipt: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    fileprivate let identity: AnyNativeCreationIdentity
    fileprivate let receipt: AnyNativeAttachedFile
    fileprivate init(identity: AnyNativeCreationIdentity, receipt: AnyNativeAttachedFile) {
        self.identity = identity; self.receipt = receipt
    }
    public var description: String { "AnyNativeFileAttachmentRecoveryReceipt(original acknowledgement, private context redacted)" }
    public var debugDescription: String { description }
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
    private let receipts = ReceiptMemory()

    /// Volatile original acknowledgements belong only to this creator's owner.
    /// There is no public import-by-ID API. Reserve capacity before dispatch so
    /// a valid native acknowledgement never needs to evict another action.
    private actor ReceiptMemory {
        struct Entry: Sendable {
            let identity: AnyNativeCreationIdentity
            var receipt: AnyNativeAttachedFile?
        }
        private var entries: [String: Entry] = [:]

        func reserve(_ identity: AnyNativeCreationIdentity) throws {
            if let old = entries[identity.key] {
                guard old.identity == identity else { throw AnyNativeFileAttachmentError.contentConflict }
                return
            }
            guard entries.count < 64 else { throw AnyNativeFileAttachmentError.recoveryCapacityReached }
            entries[identity.key] = Entry(identity: identity)
        }

        func remember(_ receipt: AnyNativeAttachedFile, for identity: AnyNativeCreationIdentity) throws {
            guard var entry = entries[identity.key], entry.identity == identity else {
                throw AnyNativeFileAttachmentError.contentConflict
            }
            if let original = entry.receipt {
                guard AnyNativeFileAttachmentCreator.same(original.reference.fileID, receipt.reference.fileID),
                      AnyNativeFileAttachmentCreator.sameMetadata(original, receipt),
                      original.byteCount == receipt.byteCount else {
                    throw AnyNativeFileAttachmentError.contentConflict
                }
            }
            entry.receipt = receipt
            entries[identity.key] = entry
        }

        func receipt(for identity: AnyNativeCreationIdentity) throws -> AnyNativeAttachedFile? {
            guard let entry = entries[identity.key] else { return nil }
            guard entry.identity == identity else { throw AnyNativeFileAttachmentError.contentConflict }
            return entry.receipt
        }

        func complete(_ identity: AnyNativeCreationIdentity, fileID: String) throws {
            guard let entry = entries[identity.key] else { return }
            guard entry.identity == identity,
                  entry.receipt.map({ AnyNativeFileAttachmentCreator.same($0.reference.fileID, fileID) }) ?? true else {
                throw AnyNativeFileAttachmentError.contentConflict
            }
            entries.removeValue(forKey: identity.key)
        }
    }

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

    /// Obtain the actual remembered acknowledgement before retiring this owner.
    /// A poisoned journal is intentionally not queried or unpoisoned here.
    /// The caller must still hold the original account/Space read authority.
    public func retainedRecoveryReceipt(for intent: AnyNativeFileAttachmentIntent,
                                        authorizeRead: @escaping Check) async throws -> AnyNativeFileAttachmentRecoveryReceipt {
        try requireScope(intent)
        try Task.checkCancellation()
        try await authorizeRead()
        guard let receipt = try await receipts.receipt(for: intent.identity) else {
            throw AnyNativeFileAttachmentError.writeUncertain
        }
        try Self.requireReceipt(receipt, specification: intent.specification)
        try Task.checkCancellation()
        try await authorizeRead()
        try Task.checkCancellation()
        return .init(identity: intent.identity, receipt: receipt)
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
            return try await reconcile(intent, state: state, authorizeRead: authorizeRead)
        }
        let journal = journal
        let receipts = receipts
        let specification = try intent.specification
        do {
            let receipt = try await upload(specification, fileURL, authorizeRead, {
                try Task.checkCancellation()
                try await authorizeRead()
                try await receipts.reserve(intent.identity)
                // Persist before dispatch. If authorization or dispatch then
                // fails, keep the reservation rather than guessing no write.
                let reservation = try await journal.reserve(intent.identity)
                guard reservation.ownsDispatch else { throw AnyNativeFileAttachmentError.writeUncertain }
                try await authorizeAttachment()
                try Task.checkCancellation()
            }, { receipt in
                try Self.requireReceipt(receipt, specification: specification)
                // This bounded private carrier is populated only by the real
                // native acknowledgement. Keep it even if durable recording
                // fails; it never becomes a substitute durability claim.
                try await receipts.remember(receipt, for: intent.identity)
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
            if uncertain.underlying as? AnyNativeFileAttachmentError == .recoveryCapacityReached {
                throw AnyNativeFileAttachmentError.recoveryCapacityReached
            }
            throw AnyNativeFileAttachmentError.writeUncertain
        }
    }

    /// Safe after cancellation or a lost UI response when this original owner
    /// retains the real acknowledgement. A temporary journal failure may be
    /// repaired from that private witness before readback. After process restart,
    /// the original ID must already be durable. This never calls native Attach.
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
        return try await reconcile(intent, state: state, authorizeRead: authorizeRead)
    }

    /// A failed protected journal remains poisoned. Its owning session must be
    /// drained and closed, and the original journal must reopen successfully
    /// through its own unchanged storage/ownership checks before calling here.
    /// This overload requires that exact original reservation; it never creates
    /// a new one and never accepts an arbitrary file ID or serialized witness.
    public func resume(_ intent: AnyNativeFileAttachmentIntent,
                       recoveryReceipt: AnyNativeFileAttachmentRecoveryReceipt,
                       authorizeRead: @escaping Check) async throws -> AnyNativeAttachedFile {
        try requireScope(intent)
        guard recoveryReceipt.identity == intent.identity else {
            throw AnyNativeFileAttachmentError.contentConflict
        }
        try Self.requireReceipt(recoveryReceipt.receipt, specification: intent.specification)
        try Task.checkCancellation()
        try await authorizeRead()
        guard let state = try await journal.lookup(intent.identity) else {
            throw AnyNativeFileAttachmentError.noRecordedAttachment
        }
        if let fileID = state.objectID {
            try Self.requireReceipt(recoveryReceipt.receipt, specification: intent.specification, fileID: fileID)
        }
        try await receipts.reserve(intent.identity)
        try await receipts.remember(recoveryReceipt.receipt, for: intent.identity)
        return try await reconcile(intent, state: state, authorizeRead: authorizeRead)
    }

    private func reconcile(_ intent: AnyNativeFileAttachmentIntent, state: AnyNativeCreationState,
                           authorizeRead: @escaping Check) async throws -> AnyNativeAttachedFile {
        let original = try await receipts.receipt(for: intent.identity)
        if let fileID = state.objectID {
            if let original {
                try Self.requireReceipt(original, specification: intent.specification, fileID: fileID)
            }
            return try await verify(intent, fileID: fileID, expectedReceipt: original, authorizeRead: authorizeRead)
        }
        guard let original else { throw AnyNativeFileAttachmentError.writeUncertain }
        let fileID = original.reference.fileID
        do {
            try Self.requireReceipt(original, specification: intent.specification)
            try Task.checkCancellation()
            try await authorizeRead()
            // Preserve the SAME journal reservation and original file identity.
            // A new creator without this actual witness cannot execute this path.
            try await journal.record(.created(fileID), identity: intent.identity)
        } catch {
            throw AnyNativeFileAttachmentError.knownFileUnverified(fileID)
        }
        return try await verify(intent, fileID: fileID, expectedReceipt: original, authorizeRead: authorizeRead)
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
            // The durable verified record now owns recovery. Release the
            // volatile slot before the final delivery fence: no actor hop may
            // follow the current authority and original-task cancellation checks.
            try await receipts.complete(intent.identity, fileID: fileID)
            try Task.checkCancellation()
            try await authorizeRead()
            try Task.checkCancellation()
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
