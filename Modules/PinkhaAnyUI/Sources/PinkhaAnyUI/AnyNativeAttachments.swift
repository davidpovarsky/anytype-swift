#if canImport(UIKit) && canImport(HanlinMiniAppsBridge)
import Foundation
import Observation
import SwiftUI
import UIKit
import QuickLook
import UniformTypeIdentifiers
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaKit
import HanlinMiniAppsBridge

struct AnyNativeAttachment: Identifiable, Equatable, Sendable {
    let id: String
    let objectID: String
    let name: String
    let mime: String
    let size: Int64
    let rootCID: String?
    let inline: Bool
    let cached: Bool
    let durable: Bool

    init(_ value: AnyJSON, objectID: String) throws {
        let name = value["name"]?.string ?? ""
        let mime = value["mime"]?.string ?? ""
        let rootCID = value["rootCid"]?.string
        guard let id = value["fileId"]?.string, AnyEditorBlock.validID(id),
              value["objectId"]?.string == objectID,
              let size = value["size"]?.integer, (0...AnyPreparedFileIntent.maximumBytes).contains(size),
              let inline = value["inline"]?.bool,
              let cached = value["cached"]?.bool, let durable = value["durable"]?.bool,
              value["name"] == nil || value["name"]?.string != nil,
              name.utf8.count <= 16_384,
              value["mime"] == nil || value["mime"]?.string != nil,
              mime.utf8.count <= 1_024,
              value["rootCid"] == nil || rootCID != nil,
              (inline
                ? (rootCID ?? "").isEmpty && cached && durable
                : !(rootCID ?? "").isEmpty) else {
            throw AnyHostError.invalidDocument("native attachment metadata")
        }
        self.id = id; self.objectID = objectID; self.size = size
        self.name = name; self.mime = mime.isEmpty ? "application/octet-stream" : mime
        self.rootCID = rootCID; self.inline = inline
        self.cached = cached; self.durable = durable
    }

    func sameContent(as other: Self) -> Bool {
        id == other.id && objectID == other.objectID && name == other.name &&
        mime == other.mime && size == other.size && rootCID == other.rootCID && inline == other.inline
    }
}

struct AnyNativeAttachmentPreview: Identifiable {
    let id = UUID()
    let url: URL
}

struct AnyNativeAttachmentPicker: Identifiable {
    let id = UUID()
    let initialDirectory: URL
}

private actor AnyNativeAttachmentUploadApproval {
    private var consumed = false
    func consume() throws {
        guard !consumed else { throw AnyNativeFileAttachmentError.writeUncertain }
        consumed = true
    }
}

private struct AnyNativeAttachmentOperation: Sendable {
    let creator: AnyNativeFileAttachmentCreator
    let lease: AnyHostLease
    let authorizeRead: AnyNativeFileAttachmentCreator.Check
    let authorizeAttachment: AnyNativeFileAttachmentCreator.Check
    let files: @Sendable () async throws -> [AnyNativeAttachment]
}

private enum AnyNativeAttachmentResume: Sendable {
    case verified(AnyNativeFileAttachmentIntent, [AnyNativeAttachment])
    case notRecorded(AnyNativeFileAttachmentIntent, [AnyNativeAttachment])
    case noPending([AnyNativeAttachment])
}

/// A visible Retry action can authorize one scheduling request. A native 204
/// acknowledges that request only; it never supplies a file-status value.
private actor AnyNativeAttachmentRetryApproval {
    private var consumed = false
    private(set) var acknowledged = false

    func consume() throws {
        guard !consumed else {
            throw AnyEngineError.invalidOperation("native file retry approval already used")
        }
        consumed = true
    }

    func acknowledge() { acknowledged = true }
}

@Observable @MainActor
final class AnyNativeAttachmentsPresentation: Identifiable {
    let id = UUID()
    let document: AnyDocumentPresentation
    let owner: UUID
    var files: [AnyNativeAttachment] = []
    var preview: AnyNativeAttachmentPreview?
    var error: String?
    var busy = false
    var pendingMiniAppsInput: MiniAppContent?
    var storageStatuses: [String: AnyNativeFileStatus] = [:]
    var storageNotice: String?
    var filePicker: AnyNativeAttachmentPicker?
    var pendingAttachment: AnyNativeFileAttachmentIntent?
    var uploadNotice: String?
    private var uploadRecoveryReady = false
    private var active = true
    @ObservationIgnored private var task: Task<Void, Never>?
    @ObservationIgnored private var directories: [URL] = []

    init(document: AnyDocumentPresentation) throws {
        try document.requireMounted(document.mountedOwnerID)
        self.document = document; owner = document.mountedOwnerID
        document.installPresentationLifecycle(revoke: { [weak self] in
            self?.active = false; self?.task?.cancel(); self?.discardVisibleFiles()
        }, drain: { [weak self] in await self?.close() })
    }

    func load() async {
        guard active, !busy else { return }
        storageStatuses = [:]; storageNotice = nil
        busy = true; defer { busy = false }
        let client = document.client, documents = document.documents, objectID = document.objectID
        let workspace = document.workspace, authorize = authorization()
        do {
            let result = try await document.nativeSession.perform { lease in
                _ = try await documents.read(objectID: objectID, lease: lease)
                let value = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", workspace.spaceID, "files"],
                    query: ["objectId": objectID, "limit": "10001"], maximumResponseBytes: 8 << 20,
                    authorize: authorize)
                guard let rows = value["files"]?.array, rows.count <= 10_000 else {
                    throw AnyHostError.incompleteDocument
                }
                let files = try rows.map { try AnyNativeAttachment($0, objectID: objectID) }
                guard Set(files.map(\.id)).count == files.count else { throw AnyHostError.incompleteDocument }
                try await authorize(); try await lease.validate()
                return files
            }
            try requireActive()
            files = result.sorted { $0.name.localizedStandardCompare($1.name) == .orderedAscending }
            error = nil
        } catch {
            if active {
                discardVisibleFiles()
                self.error = AnyUIErrorText.describe(error)
            }
        }
    }

    func canRetryStorage(_ file: AnyNativeAttachment) -> Bool {
        guard let status = storageStatuses[file.id] else { return false }
        return active && !busy && task == nil && document.canMutate && !document.hasPendingEdits &&
            files.contains(where: { $0.sameContent(as: file) }) && status.state != .durable
    }

    func checkStorageStatus(_ file: AnyNativeAttachment) {
        storageOperation(file, retry: false)
    }

    func retryStorage(_ file: AnyNativeAttachment) {
        guard canRetryStorage(file) else { return }
        storageOperation(file, retry: true)
    }

    /// Status is fetched only for the chosen row, never by polling every file
    /// or by automatically repeating an uncertain scheduling request.
    private func storageOperation(_ file: AnyNativeAttachment, retry: Bool) {
        guard active, !busy, task == nil,
              files.contains(where: { $0.sameContent(as: file) }) else { return }
        storageStatuses[file.id] = nil; storageNotice = nil
        busy = true
        task = Task { [weak self] in
            guard let self else { return }
            defer { task = nil; busy = false }
            let approval = AnyNativeAttachmentRetryApproval()
            do {
                try requireCurrentFile(file)
                let client = document.client, workspace = document.workspace
                let reference = try PinkhaAnyEngine.AnyNativeFileReference(accountID: workspace.accountID,
                    spaceID: workspace.spaceID, objectID: document.objectID, fileID: file.id)
                let storage = AnyNativeFileDurability(client: client)
                let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace,
                    allowedTypeIDs: document.capabilities.allowedTargetTypes,
                    editorDataset: document.documents.dataset,
                    documentTypePolicy: .nativeCanonicalEditorV1)
                let currentFile: @Sendable () async throws -> Void = { [weak self] in
                    guard let self else { throw AnyHostError.sessionClosed }
                    try await self.requireCurrentFile(file)
                }
                let currentRetry: @Sendable () async throws -> Void = { [weak self] in
                    guard let self else { throw AnyHostError.sessionClosed }
                    try await self.requireStorageRetry(file)
                }
                let status = try await document.nativeSession.perform { lease in
                    let authorizeRead: @Sendable () async throws -> Void = {
                        try await lease.validate()
                        try await currentFile()
                        try await access.validate(.object(objectId: reference.objectID), intent: .read)
                        try await currentFile()
                    }
                    let metadata: @Sendable () async throws -> AnyNativeAttachment = {
                        try AnyNativeAttachment(await client.requestJSON(method: "GET",
                            path: ["v1", "spaces", workspace.spaceID, "files", reference.fileID],
                            authorize: authorizeRead), objectID: reference.objectID)
                    }
                    let before = try await metadata()
                    guard before.sameContent(as: file) else { throw AnyHostError.changedDocument }
                    if retry {
                        _ = try await storage.retry(reference, authorizeRead: authorizeRead,
                            authorizeRetry: {
                                try await access.validate(.object(objectId: reference.objectID), intent: .write)
                                try await lease.validate()
                                try await currentRetry()
                                try await approval.consume()
                            })
                        await approval.acknowledge()
                    }
                    // Even after 204, publish only a separately returned native
                    // status. The metadata bracket still binds the chosen file.
                    let status = try await storage.status(reference, authorize: authorizeRead)
                    let after = try await metadata()
                    guard after.sameContent(as: before) else { throw AnyHostError.changedDocument }
                    try await authorizeRead()
                    return status
                }
                try requireCurrentFile(file)
                storageStatuses[file.id] = status
                storageNotice = retry ? Self.retryAcknowledgedMessage : nil
                error = nil
            } catch {
                let acknowledged = await approval.acknowledged
                if active {
                    discardVisibleFiles()
                    storageNotice = acknowledged ? Self.retryAcknowledgedMessage : nil
                    self.error = AnyUIErrorText.describe(error)
                }
            }
        }
    }

    private static var retryAcknowledgedMessage: String {
        AnyUIErrorText.text("בקשת הניסיון החוזר התקבלה. בדוק את מצב השמירה הנוכחי.",
                            "Retry requested. Check the current storage status for progress.")
    }

    private func requireCurrentFile(_ file: AnyNativeAttachment) throws {
        try requireActive()
        guard file.objectID == document.objectID,
              files.contains(where: { $0.sameContent(as: file) }) else {
            throw AnyHostError.changedDocument
        }
    }

    private func requireStorageRetry(_ file: AnyNativeAttachment) throws {
        try requireCurrentFile(file)
        guard document.canMutate, !document.hasPendingEdits else {
            throw AnyHostError.changedDocument
        }
    }

    func open(_ file: AnyNativeAttachment, inMiniApps: Bool = false, completed: @escaping @MainActor () -> Void = {}) {
        guard active, !busy, task == nil,
              files.contains(where: { $0.sameContent(as: file) }) else { return }
        busy = true
        task = Task { [weak self] in
            guard let self else { return }
            defer { task = nil; busy = false }
            do {
                try requireActive()
                let parent = FileManager.default.temporaryDirectory
                    .appendingPathComponent("pinkha-native-file-" + UUID().uuidString, isDirectory: true)
                try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false,
                                                        attributes: [.posixPermissions: 0o700])
                directories.append(parent)
                let ext = (file.name as NSString).pathExtension
                let safeExt = ext.unicodeScalars.allSatisfy { CharacterSet.alphanumerics.contains($0) } && ext.count <= 16 ? ext : ""
                let output = parent.appendingPathComponent("attachment" + (safeExt.isEmpty ? "" : "." + safeExt))
                let client = document.client, workspace = document.workspace
                let authorize = authorization()
                let path = ["v1", "spaces", workspace.spaceID, "files", file.id]
                try await document.nativeSession.perform { lease in
                    let before = try AnyNativeAttachment(
                        await client.requestJSON(method: "GET", path: path, authorize: authorize),
                        objectID: file.objectID)
                    guard before.sameContent(as: file) else { throw AnyHostError.changedDocument }
                    _ = try await client.downloadFileContent(spaceID: workspace.spaceID, fileID: file.id,
                        size: file.size, mime: file.mime, to: output, expectedSHA256: nil, authorize: authorize)
                    let after = try AnyNativeAttachment(
                        await client.requestJSON(method: "GET", path: path, authorize: authorize),
                        objectID: file.objectID)
                    guard after.sameContent(as: before) else { throw AnyHostError.changedDocument }
                    try await authorize(); try await lease.validate()
                }
                try requireActive()
                if inMiniApps {
                    let store = try MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared")
                    pendingMiniAppsInput = try store.importAttachment(at: output, name: file.name,
                        typeIdentifier: UTType(mimeType: file.mime)?.identifier)
                    completed()
                } else { preview = .init(url: output) }
            } catch {
                if active {
                    discardVisibleFiles()
                    self.error = AnyUIErrorText.describe(error)
                }
            }
        }
    }

    func close() async {
        active = false
        discardVisibleFiles()
        let current = task; current?.cancel()
        await current?.value
        task = nil; preview = nil
        let owned = directories; directories = []
        for directory in owned { try? FileManager.default.removeItem(at: directory) }
    }

    private func discardVisibleFiles() {
        files = []
        preview = nil
        storageStatuses = [:]
        storageNotice = nil
        filePicker = nil
        pendingAttachment = nil
        uploadNotice = nil
        uploadRecoveryReady = false
    }

    private func requireActive() throws {
        guard active, !Task.isCancelled else { throw AnyHostError.sessionClosed }
        try document.requireMounted(owner)
    }

    private func authorization() -> @Sendable () async throws -> Void {
        { [weak self] in
            guard let self else { throw AnyHostError.sessionClosed }
            try await self.requireActive()
        }
    }
}

extension AnyNativeAttachmentsPresentation {
    var canAddAttachment: Bool {
        active && !busy && task == nil && filePicker == nil && uploadRecoveryReady &&
        pendingAttachment == nil && document.canMutate && !document.hasPendingEdits
    }

    var showsAttachmentCheck: Bool { pendingAttachment != nil || !uploadRecoveryReady }

    func chooseAttachment() {
        guard canAddAttachment else { return }
        do {
            try requireUploadWrite()
            let directory = try FileManager.default.url(for: .documentDirectory,
                in: .userDomainMask, appropriateFor: nil, create: true)
            filePicker = .init(initialDirectory: directory)
        } catch { self.error = AnyUIErrorText.describe(error) }
    }

    func selectedAttachment(_ result: Result<URL?, any Error>, pickerID: UUID) {
        guard filePicker?.id == pickerID else { return }
        filePicker = nil
        guard active, !busy, task == nil else { return }
        switch result {
        case .success(nil): break
        case .failure(let error): self.error = AnyUIErrorText.describe(error)
        case .success(let selected?): upload(selected)
        }
    }

    /// Loading the protected original intent does not upload or verify a whole
    /// file automatically. The user's Check action performs read-only recovery.
    func loadUploadRecovery() {
        guard active, !busy, task == nil else { return }
        busy = true
        task = Task { [weak self] in
            guard let self else { return }
            defer { task = nil; busy = false }
            do {
                let pending = try await withUploadClaim { store, claim in
                    try await performAttachment { operation in
                        try await operation.authorizeRead()
                        let pending = try await store.pending(claim)
                        try await operation.authorizeRead()
                        return pending
                    }
                }
                try requireActive()
                pendingAttachment = pending
                uploadRecoveryReady = true
                uploadNotice = pending == nil ? nil : Self.pendingUploadMessage
            } catch { presentUploadFailure(error) }
        }
    }

    private func upload(_ url: URL) {
        guard canAddAttachment else { return }
        busy = true
        uploadRecoveryReady = false
        uploadNotice = nil
        task = Task { [weak self] in
            guard let self else { return }
            defer { task = nil; busy = false }
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            var mayHaveSavedIntent = true
            do {
                try requireUploadWrite()
                let rows = try await withUploadClaim { store, claim in
                    guard try await store.pending(claim) == nil else {
                        throw AnyNativeAttachmentRecoveryError.conflictingIntent
                    }
                    mayHaveSavedIntent = false
                    let fingerprint = try await Self.fingerprint(url)
                    try requireUploadWrite()
                    let intent = try AnyNativeFileAttachmentIntent(workspace: document.workspace,
                        mutationID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                        objectID: document.objectID, name: url.lastPathComponent,
                        mime: UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream",
                        byteCount: fingerprint.byteCount, contentSHA256: fingerprint.sha256)
                    mayHaveSavedIntent = true
                    let rows = try await performAttachment { operation in
                        try await operation.authorizeRead()
                        // The caller snapshot is durable before the Host can
                        // reserve its one original native POST.
                        try await store.save(intent, claim: claim)
                        try await operation.authorizeRead()
                        // Keep the exact original actor before dispatch, even
                        // if later cancellation prevents a live token export.
                        try await store.retainOriginalCreator(for: intent, from: operation.creator,
                            lease: operation.lease, claim: claim)
                        let file: AnyNativeAttachedFile
                        do {
                            file = try await operation.creator.attach(intent, fileURL: url,
                                authorizeRead: operation.authorizeRead,
                                authorizeAttachment: operation.authorizeAttachment)
                        } catch {
                            await Self.retainLiveAttachmentReceipt(intent, operation: operation,
                                store: store, claim: claim)
                            throw error
                        }
                        // A returned Host result has durably verified its ID.
                        // Keep the caller intent until the separate FilesV2 check.
                        try await store.consumeRecoveryReceipt(for: intent, claim: claim)
                        let rows = try await operation.files()
                        try Self.requireReturnedFile(file, in: rows, intent: intent)
                        return rows
                    }
                    try requireActive()
                    try await store.remove(intent, claim: claim)
                    try requireActive()
                    return rows
                }
                try requireActive()
                publishUploadRows(rows)
                uploadNotice = AnyUIErrorText.text("הקובץ צורף למסמך.", "The file was attached to this document.")
            } catch { presentUploadFailure(error, pendingPossible: mayHaveSavedIntent) }
        }
    }

    func checkPendingAttachment() {
        guard active, !busy, task == nil else { return }
        busy = true
        task = Task { [weak self] in
            guard let self else { return }
            defer { task = nil; busy = false }
            do {
                let result = try await withUploadClaim { store, claim in
                    let result = try await performAttachment { operation in
                        try await operation.authorizeRead()
                        guard let intent = try await store.pending(claim) else {
                            return AnyNativeAttachmentResume.noPending(try await operation.files())
                        }
                        do {
                            // No selected URL and no new mutation ID exists on
                            // this path. Unknown or reserved outcomes never POST.
                            let retained = try await store.recoveryReceipt(for: intent,
                                currentCreator: operation.creator, lease: operation.lease,
                                authorizeRead: operation.authorizeRead, claim: claim)
                            let file: AnyNativeAttachedFile
                            do {
                                if let retained {
                                    file = try await operation.creator.resume(intent, recoveryReceipt: retained,
                                        authorizeRead: operation.authorizeRead)
                                } else {
                                    file = try await operation.creator.resume(intent, authorizeRead: operation.authorizeRead)
                                }
                            } catch AnyNativeFileAttachmentError.noRecordedAttachment {
                                // An opaque token never substitutes for the
                                // original journal reservation or permits POST.
                                throw AnyNativeFileAttachmentError.noRecordedAttachment
                            } catch {
                                await Self.retainLiveAttachmentReceipt(intent, operation: operation,
                                    store: store, claim: claim)
                                throw error
                            }
                            try await store.consumeRecoveryReceipt(for: intent, claim: claim)
                            let rows = try await operation.files()
                            try Self.requireReturnedFile(file, in: rows, intent: intent)
                            return AnyNativeAttachmentResume.verified(intent, rows)
                        } catch AnyNativeFileAttachmentError.noRecordedAttachment {
                            try await operation.authorizeRead()
                            return AnyNativeAttachmentResume.notRecorded(intent, try await operation.files())
                        }
                    }
                    try requireActive()
                    switch result {
                    case .verified(let intent, _): try await store.remove(intent, claim: claim)
                    case .notRecorded, .noPending: break
                    }
                    try requireActive()
                    return result
                }
                try requireActive()
                switch result {
                case .verified(_, let rows):
                    publishUploadRows(rows)
                    uploadNotice = AnyUIErrorText.text("הקובץ המצורף אומת.", "The original attachment was verified.")
                case .notRecorded(let intent, let rows):
                    publishUploadRows(rows)
                    pendingAttachment = intent
                    // A missing/replaced journal can also return no record.
                    // That does not prove the original native POST never ran.
                    uploadNotice = AnyUIErrorText.text("אין רישום שמאפשר לאמת את בקשת הצירוף. הבקשה המקורית נשמרה ולא תישלח שוב.",
                        "No record is available to verify this attachment request. The original request is retained and will not be sent again.")
                case .noPending(let rows): publishUploadRows(rows)
                }
            } catch { presentUploadFailure(error) }
        }
    }

    /// Best-effort retention happens inside the original awaited operation and
    /// claim. The real Host rechecks current scope/read authority before minting
    /// its opaque token. A cancelled or revoked owner cannot be rescued here;
    /// retain the original failure and unresolved intent in that case.
    nonisolated private static func retainLiveAttachmentReceipt(
        _ intent: AnyNativeFileAttachmentIntent, operation: AnyNativeAttachmentOperation,
        store: AnyNativeAttachmentIntentStore, claim: AnyNativeAttachmentIntentClaim
    ) async {
        guard !Task.isCancelled else { return }
        _ = try? await store.recoveryReceipt(for: intent, currentCreator: operation.creator,
            lease: operation.lease, authorizeRead: operation.authorizeRead, claim: claim)
    }

    private func withUploadClaim<Value: Sendable>(
        _ operation: @MainActor (AnyNativeAttachmentIntentStore, AnyNativeAttachmentIntentClaim) async throws -> Value
    ) async throws -> Value {
        try requireActive()
        let store = try document.attachmentIntentStore(for: owner)
        let claim = try await store.claim(objectID: document.objectID)
        do {
            try requireActive()
            let result = try await operation(store, claim)
            await store.release(claim)
            return result
        } catch {
            // Every nested fingerprint/native operation is awaited, including
            // cancellation, before a replacement sheet may acquire this claim.
            await store.release(claim)
            throw error
        }
    }

    private func performAttachment<Value: Sendable>(
        _ operation: @escaping @Sendable (AnyNativeAttachmentOperation) async throws -> Value
    ) async throws -> Value {
        try requireActive()
        let client = document.client, documents = document.documents, objects = document.objects
        let workspace = document.workspace, objectID = document.objectID
        let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace,
            allowedTypeIDs: document.capabilities.allowedTargetTypes,
            editorDataset: documents.dataset, documentTypePolicy: .nativeCanonicalEditorV1)
        let approval = AnyNativeAttachmentUploadApproval()
        let current = authorization()
        let writable: AnyNativeFileAttachmentCreator.Check = { [weak self] in
            guard let self else { throw AnyHostError.sessionClosed }
            try await self.requireUploadWrite()
        }
        return try await document.nativeSession.perform { lease in
            let authorizeRead: AnyNativeFileAttachmentCreator.Check = {
                try await lease.validate()
                try await current()
                try await access.validate(.object(objectId: objectID), intent: .read)
                try await current()
                try await lease.validate()
            }
            let authorizeAttachment: AnyNativeFileAttachmentCreator.Check = {
                try await approval.consume()
                try await access.validate(.object(objectId: objectID), intent: .write)
                try await lease.validate()
                try await writable()
            }
            let readFiles: @Sendable () async throws -> [AnyNativeAttachment] = {
                _ = try await documents.read(objectID: objectID, lease: lease)
                let value = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", workspace.spaceID, "files"],
                    query: ["objectId": objectID, "limit": "10001"], maximumResponseBytes: 8 << 20,
                    authorize: authorizeRead)
                guard let rows = value["files"]?.array, rows.count <= 10_000 else {
                    throw AnyHostError.incompleteDocument
                }
                let files = try rows.map { try AnyNativeAttachment($0, objectID: objectID) }
                guard Set(files.map(\.id)).count == files.count else { throw AnyHostError.incompleteDocument }
                try await authorizeRead()
                return files
            }
            try await authorizeRead()
            let creator = try await objects.makeFileAttachmentCreator()
            let result = try await operation(.init(creator: creator, lease: lease, authorizeRead: authorizeRead,
                authorizeAttachment: authorizeAttachment, files: readFiles))
            try await authorizeRead()
            return result
        }
    }

    private func requireUploadWrite() throws {
        try requireActive()
        guard document.canMutate, !document.hasPendingEdits else { throw AnyHostError.changedDocument }
    }

    private func publishUploadRows(_ rows: [AnyNativeAttachment]) {
        files = rows.sorted { $0.name.localizedStandardCompare($1.name) == .orderedAscending }
        pendingAttachment = nil
        uploadRecoveryReady = true
        storageStatuses = [:]
        storageNotice = nil
        uploadNotice = nil
        error = nil
    }

    private func presentUploadFailure(_ failure: any Error, pendingPossible: Bool = true) {
        guard active else { return }
        discardVisibleFiles()
        guard (try? requireActive()) != nil else { return }
        // No original hint or resolved native metadata is republished after a
        // failed authority/readback. Check starts with fresh current authority.
        uploadNotice = pendingPossible ? Self.pendingUploadMessage : nil
        uploadRecoveryReady = !pendingPossible
        switch failure {
        case AnyNativeFileAttachmentError.writeUncertain,
             AnyNativeFileAttachmentError.knownFileUnverified(_):
            error = AnyUIErrorText.text("תוצאת הצירוף עדיין לא אומתה. בדוק את הבקשה המקורית; הקובץ לא יישלח שוב.",
                "The attachment result is not yet verified. Check the original request; the file will not be sent again.")
        case AnyNativeAttachmentRecoveryError.operationInProgress:
            error = AnyUIErrorText.text("פעולת צירוף קודמת עדיין מסתיימת. נסה לבדוק שוב לאחר שתסתיים.",
                "An earlier attachment operation is still finishing. Check again after it finishes.")
        default: error = AnyUIErrorText.describe(failure)
        }
    }

    private static var pendingUploadMessage: String {
        AnyUIErrorText.text("אפשר לבדוק את בקשת הצירוף השמורה ללא שליחה נוספת.",
            "You can check the saved attachment request without sending it again.")
    }

    nonisolated private static func requireReturnedFile(_ file: AnyNativeAttachedFile,
        in rows: [AnyNativeAttachment], intent: AnyNativeFileAttachmentIntent) throws {
        let reference = file.reference
        guard reference.accountID.utf8.elementsEqual(intent.workspace.accountID.utf8),
              reference.spaceID.utf8.elementsEqual(intent.workspace.spaceID.utf8),
              reference.objectID.utf8.elementsEqual(intent.objectID.utf8),
              file.byteCount == intent.byteCount,
              let row = rows.first(where: { $0.id.utf8.elementsEqual(reference.fileID.utf8) }),
              row.objectID.utf8.elementsEqual(intent.objectID.utf8), row.size == file.byteCount,
              row.inline == file.inline,
              row.name.utf8.elementsEqual(file.name.utf8),
              row.mime.utf8.elementsEqual((file.mime.isEmpty ? "application/octet-stream" : file.mime).utf8),
              (row.rootCID ?? "").utf8.elementsEqual((file.rootCID ?? "").utf8) else {
            throw AnyHostError.changedDocument
        }
    }

    nonisolated private static func fingerprint(_ url: URL) async throws -> AnyNativeFileSourceFingerprint {
        let child = Task.detached(priority: .utility) { try await AnyNativeFileUploader.fingerprint(fileURL: url) }
        return try await withTaskCancellationHandler {
            try await child.value
        } onCancel: { child.cancel() }
    }
}

struct AnyNativeAttachmentsView: View {
    @Bindable var model: AnyNativeAttachmentsPresentation
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        NavigationStack {
            List {
                if let error = model.error { Text(error).foregroundStyle(.red).textSelection(.enabled) }
                if let notice = model.storageNotice {
                    Text(notice).font(.footnote).foregroundStyle(.secondary)
                        .accessibilityIdentifier("any-native-file-retry-notice")
                }
                if model.busy { ProgressView() }
                if let notice = model.uploadNotice {
                    Section {
                        Text(notice).font(.footnote).foregroundStyle(.secondary)
                            .accessibilityIdentifier("any-native-upload-notice")
                        if let pending = model.pendingAttachment {
                            Text(pending.name.isEmpty ? AnyUIErrorText.text("קובץ מצורף", "Attachment") : pending.name)
                                .accessibilityIdentifier("any-native-upload-pending-name")
                        }
                        if model.showsAttachmentCheck {
                            Button(AnyUIErrorText.text("בדיקת בקשת הצירוף", "Check attachment request"),
                                   systemImage: "arrow.clockwise") { model.checkPendingAttachment() }
                                .disabled(model.busy)
                                .accessibilityIdentifier("any-native-upload-check")
                        }
                    }
                }
                if !model.busy && model.files.isEmpty && model.error == nil {
                    Text(AnyUIErrorText.text("אין קבצים מצורפים במסמך.", "This document has no attachments."))
                }
                ForEach(model.files) { file in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Button { model.open(file) } label: {
                                VStack(alignment: .leading) {
                                    Label(file.name.isEmpty ? AnyUIErrorText.text("קובץ מצורף", "Attachment") : file.name, systemImage: "doc")
                                    Text(ByteCountFormatter.string(fromByteCount: file.size, countStyle: .file)).font(.caption)
                                    if !file.durable && model.storageStatuses[file.id] == nil {
                                        Text(AnyUIErrorText.text("השמירה ברשת עדיין לא אומתה", "Network backup is not yet verified"))
                                            .font(.caption).foregroundStyle(.secondary)
                                    }
                                }
                            }.accessibilityIdentifier("any-native-attachment-" + file.id)
                            Spacer()
                            Button("MiniApps", systemImage: "square.grid.2x2") {
                                model.open(file, inMiniApps: true) { dismiss() }
                            }.accessibilityIdentifier("any-native-attachment-miniapps-" + file.id)
                        }
                        if let status = model.storageStatuses[file.id] {
                            Text(storageTitle(status.state)).font(.subheadline)
                                .accessibilityIdentifier("any-native-file-storage-state-" + file.id)
                            Text(status.cached
                                 ? AnyUIErrorText.text("זמין במכשיר זה", "Available on this device")
                                 : AnyUIErrorText.text("לא הורד למכשיר זה", "Not downloaded to this device"))
                                .font(.caption).foregroundStyle(.secondary)
                                .accessibilityIdentifier("any-native-file-local-availability-" + file.id)
                        }
                        Button(AnyUIErrorText.text("בדיקת מצב השמירה", "Check storage status"),
                               systemImage: "icloud") { model.checkStorageStatus(file) }
                            .accessibilityIdentifier("any-native-file-check-status-" + file.id)
                        if let status = model.storageStatuses[file.id], status.state != .durable {
                            Button(AnyUIErrorText.text("ניסיון שמירה חוזר", "Retry storage"),
                                   systemImage: "arrow.clockwise") { model.retryStorage(file) }
                                .disabled(!model.canRetryStorage(file))
                                .accessibilityIdentifier("any-native-file-retry-storage-" + file.id)
                        }
                    }.buttonStyle(.borderless)
                        .disabled(model.busy)
                }
            }
            .navigationTitle(AnyUIErrorText.text("קבצים מצורפים", "Attachments"))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(AnyUIErrorText.text("סגירה", "Close")) { dismiss() }
                }
                ToolbarItem(placement: .primaryAction) {
                    Button(AnyUIErrorText.text("צירוף קובץ", "Add attachment"), systemImage: "plus") {
                        model.chooseAttachment()
                    }.disabled(!model.canAddAttachment).accessibilityIdentifier("any-native-upload-add")
                }
                ToolbarItem(placement: .primaryAction) {
                    Button(AnyUIErrorText.text("רענון", "Refresh"), systemImage: "arrow.clockwise") {
                        Task { await model.load(); model.loadUploadRecovery() }
                    }.disabled(model.busy)
                }
            }
            .task { await model.load(); model.loadUploadRecovery() }
            .sheet(item: $model.preview) { item in AnyNativeFilePreview(url: item.url) }
            .sheet(item: $model.filePicker) { picker in
                PinkhaDocumentTransferPicker(operation: .open([.data]), initialDirectory: picker.initialDirectory) { result in
                    model.selectedAttachment(result, pickerID: picker.id)
                }
            }
        }
    }

    private func storageTitle(_ state: AnyNativeFileStatus.State) -> String {
        switch state {
        case .durable: AnyUIErrorText.text("שמירת הקובץ אומתה", "File storage confirmed")
        case .inFlight: AnyUIErrorText.text("שמירת הקובץ מתבצעת", "File storage is in progress")
        case .limited: AnyUIErrorText.text("מכסת האחסון מלאה", "Storage limit reached")
        }
    }
}

private struct AnyNativeFilePreview: UIViewControllerRepresentable {
    let url: URL
    final class Coordinator: NSObject, QLPreviewControllerDataSource {
        let url: URL
        init(url: URL) { self.url = url }
        func numberOfPreviewItems(in controller: QLPreviewController) -> Int { 1 }
        func previewController(_ controller: QLPreviewController, previewItemAt index: Int) -> any QLPreviewItem { url as NSURL }
    }
    func makeCoordinator() -> Coordinator { Coordinator(url: url) }
    func makeUIViewController(context: Context) -> QLPreviewController {
        let controller = QLPreviewController()
        controller.dataSource = context.coordinator
        return controller
    }
    func updateUIViewController(_ controller: QLPreviewController, context: Context) {}
}
#endif
