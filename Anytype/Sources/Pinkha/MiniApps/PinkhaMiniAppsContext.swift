import Foundation
import CryptoKit
import Darwin
import HanlinMiniAppsBridge
import PinkhaHanlinUI
import Services
import SwiftProtobuf
import UIKit
import UniformTypeIdentifiers
import AnytypeCore

/// Retains the exact menu origin without retaining its editor or reusable text view.
/// A detached/reconfigured origin is unavailable; it must never select another responder.
@MainActor
final class PinkhaMiniAppsTextSelection {
    private weak var textView: UITextView?
    private weak var editor: EditorPageController?
    let blockID: String
    let range: NSRange

    init?(textView: UITextView, range: NSRange, editor: EditorPageController) {
        guard let blockID = PinkhaMiniAppsContext.blockID(containing: textView, editor: editor) else { return nil }
        self.textView = textView
        self.editor = editor
        self.blockID = blockID
        self.range = range
    }

    func resolve(editor: EditorPageController) throws -> UITextView {
        guard self.editor === editor, let textView,
              PinkhaMiniAppsContext.blockID(containing: textView, editor: editor) == blockID else {
            throw PinkhaMiniAppsError.documentUnavailable
        }
        return textView
    }
}

struct PinkhaMiniAppsContext {
    let source: MiniAppSourceContext
    let inputs: [MiniAppContent]

    @MainActor
    static func capture(editor: EditorPageController, store: MiniAppBridgeStore,
                        selection: PinkhaMiniAppsTextSelection? = nil,
                        authorize: @MainActor () throws -> Void = {}) async throws -> Self {
        guard let model = editor.viewModel as? EditorPageViewModel,
              model.document.isOpened else { throw PinkhaMiniAppsError.documentUnavailable }
        let document = model.document
        let accountID = Container.shared.accountManager().account.id
        let objectID = document.objectId
        let spaceID = document.spaceId
        func validateSource() throws {
            try Task.checkCancellation()
            try authorize()
            guard !accountID.isEmpty, Container.shared.accountManager().account.id == accountID,
                  editor.viewModel.document.objectId == objectID,
                  editor.viewModel.document.spaceId == spaceID, document.isOpened else {
                throw PinkhaMiniAppsError.documentUnavailable
            }
        }
        try validateSource()
        var selectedIDs: [String]
        if selection != nil {
            selectedIDs = []
        } else {
            switch model.blocksStateManager.editingState {
            case .selecting(let blocks, _), .simpleTablesSelection(_, let blocks, _): selectedIDs = blocks
            default: selectedIDs = []
            }
        }
        var textSelection: MiniAppTextSelection?
        var focusID: String?
        // Simple-table text handlers do not update EditorPageController's cached responder.
        // Selection menus supply their actual view; the toolbar searches UIKit's live responder.
        let origin = try selection.map { try $0.resolve(editor: editor) }
            ?? (selectedIDs.isEmpty ? focusedTextView(in: editor.viewIfLoaded) : nil)
        if let textView = origin, let blockID = blockID(containing: textView, editor: editor) {
            focusID = blockID
            let attributed = textView.attributedText ?? NSAttributedString(string: textView.text ?? "")
            let selectedRange = selection?.range ?? textView.selectedRange
            guard selectedRange.location != NSNotFound,
                  selectedRange.location >= 0, selectedRange.length >= 0,
                  selectedRange.location <= attributed.length,
                  selectedRange.length <= attributed.length - selectedRange.location else {
                throw PinkhaMiniAppsError.documentUnavailable
            }
            let before = AttributedTextConverter.asMiddleware(
                attributedText: attributed.attributedSubstring(from: NSRange(location: 0, length: selectedRange.location)))
            let selected = AttributedTextConverter.asMiddleware(
                attributedText: attributed.attributedSubstring(from: selectedRange))
            textSelection = MiniAppTextSelection(location: before.text.utf16.count,
                length: selected.text.utf16.count, text: selected.text, blockIDs: [blockID])
            // Flush the visible original edit through the same native text service before leaving.
            if !document.isLocked, document.permissions.canEditBlocks, document.details?.isReadonly == false {
                try validateSource()
                try await model.blockActionService.setText(contextId: document.objectId,
                    blockId: blockID, middlewareString: AttributedTextConverter.asMiddleware(attributedText: attributed))
            }
        }
        try validateSource()
        let blocks = try await nativeBlocks(document: document)
        try validateSource()
        selectedIDs = try expandedSelection(selectedIDs, blocks: blocks)
        let snapshots = try blocks.compactMap { info -> PinkhaMiniAppsBlockSnapshot? in
            guard case .text(let text) = info.content,
                  text.contentType != .title, text.contentType != .description else { return nil }
            return .init(id: info.id, text: text.text, marks: try text.marks.serializedData())
        }
        if textSelection == nil, !selectedIDs.isEmpty {
            let selectedText = snapshots.filter { selectedIDs.contains($0.id) }.map(\.text).joined(separator: "\n")
            textSelection = .init(location: 0, length: selectedText.utf16.count,
                                 text: selectedText, blockIDs: selectedIDs)
        }
        let snapshotData = try JSONEncoder().encode(snapshots)
        let revision = SHA256.hash(data: snapshotData).map { String(format: "%02x", $0) }.joined()
        let documentText = snapshots.map(\.text).joined(separator: "\n")
        var metadata = [
            PinkhaMiniAppsEngineScope.metadataKey: PinkhaMiniAppsEngineScope.heart.rawValue,
            "anytype.accountID": accountID,
            "anytype.spaceID": document.spaceId,
            "anytype.blocks": String(decoding: snapshotData, as: UTF8.self)
        ]
        if let anchor = blocks.last(where: { selectedIDs.contains($0.id) })?.id ?? focusID ?? snapshots.last?.id {
            metadata["anytype.insertionAnchor"] = anchor
        }
        let source = MiniAppSourceContext(appID: sourceAppID, displayName: "Anytype",
            documentID: document.objectId, documentTitle: document.details?.title,
            revision: revision, selection: textSelection, documentText: documentText,
            kind: "editor", locator: document.objectId,
            sceneID: editor.viewIfLoaded?.window?.windowScene?.session.persistentIdentifier,
            metadata: metadata)
        var inputs: [MiniAppContent] = []
        // Empty input at a caret is intentional; full document context is separate.
        let text = textSelection?.text ?? ""
        inputs.append(.init(kind: .text, text: text, typeIdentifier: "public.plain-text"))
        for info in blocks where selectedIDs.contains(info.id) {
            switch info.content {
            case .file(let file):
                let (local, response) = try await downloadNativeFile(file)
                defer { try? FileManager.default.removeItem(at: local) }
                try validateSource()
                let refreshed = try await nativeBlocks(document: document)
                try validateSource()
                guard let current = refreshed.first(where: { $0.id == info.id }),
                      case .file(let currentFile) = current.content, currentFile == file else {
                    throw PinkhaMiniAppsError.sourceChanged
                }
                let mimeType = response.mimeType.flatMap { UTType(mimeType: $0) }
                let fileType = response.suggestedFilename.flatMap { UTType(filenameExtension: ($0 as NSString).pathExtension) }
                let nativeType: UTType = file.contentType == .image ? .image :
                    file.contentType == .audio ? .audio : file.contentType == .video ? .video : .data
                let name = response.suggestedFilename
                let typeIdentifier = (mimeType ?? fileType ?? nativeType).identifier
                let attachment = try await Task.detached(priority: .utility) {
                    try store.importAttachment(at: local, name: name, typeIdentifier: typeIdentifier)
                }.value
                try validateSource()
                inputs.append(attachment)
            case .bookmark(let bookmark):
                if let url = bookmark.source?.url {
                    inputs.append(.init(kind: .url, url: url, typeIdentifier: "public.url"))
                }
            default: break
            }
        }
        try validateSource()
        return .init(source: source, inputs: inputs)
    }


    /// Keep original file identity through an asynchronous native download.
    /// The caller rechecks its document/account lease and the exact file block.
    @MainActor
    static func downloadNativeFile(_ file: BlockFile) async throws -> (URL, URLResponse) {
        try Task.checkCancellation()
        guard file.state == .done, !file.metadata.targetObjectId.isEmpty,
              let url = ContentUrlBuilder.fileUrl(fileId: file.metadata.targetObjectId) else {
            throw PinkhaMiniAppsError.attachmentUnavailable
        }
        let (local, response) = try await URLSession.shared.download(from: url)
        do {
            try Task.checkCancellation()
            if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                throw PinkhaMiniAppsError.attachmentUnavailable
            }
            return (local, response)
        } catch {
            try? FileManager.default.removeItem(at: local)
            throw error
        }
    }

    struct FileWitness: Equatable, Sendable {
        let count: Int64
        let sha256: Data
    }

    /// Stream original bytes without introducing a file-size or file-count cap.
    /// A no-follow descriptor and before/after identity reject replacement/growth.
    static func fileWitness(at url: URL) throws -> FileWitness {
        try Task.checkCancellation()
        guard url.isFileURL else { throw PinkhaMiniAppsError.attachmentUnavailable }
        let fd = Darwin.open(url.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw PinkhaMiniAppsError.attachmentUnavailable }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat()
        guard Darwin.fstat(fd, &before) == 0,
              before.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG), before.st_size >= 0 else {
            throw PinkhaMiniAppsError.attachmentUnavailable
        }
        var hash = SHA256(), count: Int64 = 0
        while let bytes = try handle.read(upToCount: 65_536), !bytes.isEmpty {
            try Task.checkCancellation()
            hash.update(data: bytes)
            count += Int64(bytes.count)
        }
        try Task.checkCancellation()
        var after = stat()
        guard Darwin.fstat(fd, &after) == 0,
              before.st_dev == after.st_dev, before.st_ino == after.st_ino,
              before.st_size == after.st_size, count == after.st_size,
              before.st_mtimespec.tv_sec == after.st_mtimespec.tv_sec,
              before.st_mtimespec.tv_nsec == after.st_mtimespec.tv_nsec,
              before.st_ctimespec.tv_sec == after.st_ctimespec.tv_sec,
              before.st_ctimespec.tv_nsec == after.st_ctimespec.tv_nsec else {
            throw PinkhaMiniAppsError.sourceChanged
        }
        return .init(count: count, sha256: Data(hash.finalize()))
    }

    static func fileWitnesses(at urls: [URL]) async throws -> [FileWitness] {
        try Task.checkCancellation()
        let worker = Task.detached(priority: .utility) {
            try urls.map { try fileWitness(at: $0) }
        }
        return try await withTaskCancellationHandler {
            try await worker.value
        } onCancel: {
            worker.cancel()
        }
    }

    static func expandedSelection(_ selected: [String], blocks: [BlockInformation]) throws -> [String] {
        guard Set(blocks.map(\.id)).count == blocks.count else {
            throw PinkhaMiniAppsError.sourceChanged
        }
        let indexed = Dictionary(uniqueKeysWithValues: blocks.map { ($0.id, $0) })
        var pending = selected, included = Set<String>()
        while let id = pending.popLast() {
            guard included.insert(id).inserted else { continue }
            if let block = indexed[id] { pending.append(contentsOf: block.childrenIds) }
        }
        return blocks.filter { included.contains($0.id) }.map(\.id)
    }

    static func topLevelAnchor(_ id: String?, documentID: String,
                               blocks: [BlockInformation]) -> String? {
        guard var candidate = id, candidate != documentID else { return nil }
        var parents: [String: String] = [:]
        for block in blocks {
            for child in block.childrenIds { parents[child] = block.id }
        }
        var seen = Set<String>()
        while seen.insert(candidate).inserted {
            guard let parent = parents[candidate] else { return nil }
            if parent == documentID { return candidate }
            candidate = parent
        }
        return nil
    }

    static var sourceAppID: String { Bundle.main.bundleIdentifier ?? "io.anytype.app" }

    static var callbacks: MiniAppCallbacks {
        let entries = Bundle.main.object(forInfoDictionaryKey: "CFBundleURLTypes") as? [[String: Any]]
        let schemes = entries?.flatMap { $0["CFBundleURLSchemes"] as? [String] ?? [] } ?? []
        let bundleScheme = Bundle.main.bundleIdentifier.flatMap { schemes.contains($0) ? $0 : nil }
        let scheme = (bundleScheme ?? schemes.first(where: { $0 != "anytype" }) ?? "anytype").lowercased()
        let url = URL(string: "\(scheme)://miniapps/return")
        return .init(success: url, error: url, cancel: url)
    }

    @MainActor
    static func nativeBlocks(document: any BaseDocumentProtocol) async throws -> [BlockInformation] {
        let view = try await Container.shared.objectLifecycleService().openForPreview(
            contextId: document.objectId, spaceId: document.spaceId)
        guard view.rootID == document.objectId,
              let details = view.details.first(where: { $0.id == document.objectId }),
              ObjectDetails(id: details.id, values: details.details.fields).spaceId == document.spaceId
        else { throw PinkhaMiniAppsError.documentUnavailable }
        let all = view.blocks.compactMap { BlockInformationConverter.convert(block: $0) }
        let index = Dictionary(uniqueKeysWithValues: all.map { ($0.id, $0) })
        var pending = [document.objectId], seen = Set<String>(), ordered: [BlockInformation] = []
        while let id = pending.popLast() {
            guard seen.insert(id).inserted, let info = index[id] else { continue }
            ordered.append(info)
            pending.append(contentsOf: info.childrenIds.reversed())
        }
        return ordered
    }

    @MainActor
    private static func focusedTextView(in view: UIView?) -> UITextView? {
        guard let view else { return nil }
        if let textView = view as? UITextView, textView.isFirstResponder { return textView }
        return view.subviews.lazy.compactMap { focusedTextView(in: $0) }.first
    }

    @MainActor
    static func blockID(containing textView: UITextView, editor: EditorPageController) -> String? {
        guard let editorView = editor.viewIfLoaded, textView.isDescendant(of: editorView) else { return nil }
        var current: UIView? = textView
        while let view = current, view !== editorView {
            if let content = view as? TextBlockContentView, content.textView.textView === textView {
                return content.pinkhaMiniAppsBlockID
            }
            current = view.superview
        }
        return nil
    }
}

enum PinkhaMiniAppsError: LocalizedError {
    case documentUnavailable, attachmentUnavailable, sourceChanged, unsupportedResult, resultNotSaved, companionMissing
    var errorDescription: String? {
        switch self {
        case .documentUnavailable: PinkhaMiniAppsStrings.documentUnavailable
        case .attachmentUnavailable: PinkhaMiniAppsStrings.attachmentUnavailable
        case .sourceChanged: PinkhaMiniAppsStrings.sourceChanged
        case .unsupportedResult: PinkhaMiniAppsStrings.unsupportedResult
        case .resultNotSaved: PinkhaMiniAppsStrings.resultNotSaved
        case .companionMissing: PinkhaMiniAppsStrings.companionMissing
        }
    }
}
