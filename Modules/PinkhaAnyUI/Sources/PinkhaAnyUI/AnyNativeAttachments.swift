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
import HanlinMiniAppsBridge

struct AnyNativeAttachment: Identifiable, Equatable, Sendable {
    let id: String
    let objectID: String
    let name: String
    let mime: String
    let size: Int64
    let rootCID: String?
    let cached: Bool
    let durable: Bool

    init(_ value: AnyJSON, objectID: String) throws {
        guard let id = value["fileId"]?.string, AnyEditorBlock.validID(id),
              value["objectId"]?.string == objectID,
              let size = value["size"]?.integer, (0...AnyPreparedFileIntent.maximumBytes).contains(size),
              let cached = value["cached"]?.bool, let durable = value["durable"]?.bool,
              let name = value["name"]?.string, name.utf8.count <= 1024,
              let mime = value["mime"]?.string, mime.utf8.count <= 255 else {
            throw AnyHostError.invalidDocument("native attachment metadata")
        }
        self.id = id; self.objectID = objectID; self.size = size
        self.name = name; self.mime = mime.isEmpty ? "application/octet-stream" : mime
        rootCID = value["rootCid"]?.string
        self.cached = cached; self.durable = durable
    }

    func sameContent(as other: Self) -> Bool {
        id == other.id && objectID == other.objectID && name == other.name &&
        mime == other.mime && size == other.size && rootCID == other.rootCID
    }
}

struct AnyNativeAttachmentPreview: Identifiable {
    let id = UUID()
    let url: URL
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
                    Button(AnyUIErrorText.text("רענון", "Refresh"), systemImage: "arrow.clockwise") {
                        Task { await model.load() }
                    }.disabled(model.busy)
                }
            }
            .task { await model.load() }
            .sheet(item: $model.preview) { item in AnyNativeFilePreview(url: item.url) }
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
