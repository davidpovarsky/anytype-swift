import Foundation
import CryptoKit
import HanlinMiniAppsBridge
import Services
import SwiftProtobuf
import UIKit
import UniformTypeIdentifiers
import AnytypeCore

struct PinkhaMiniAppsContext {
    let source: MiniAppSourceContext
    let inputs: [MiniAppContent]

    @MainActor
    static func capture(editor: EditorPageController, store: MiniAppBridgeStore,
                        range: NSRange? = nil) async throws -> Self {
        guard let model = editor.viewModel as? EditorPageViewModel,
              model.document.isOpened else { throw PinkhaMiniAppsError.documentUnavailable }
        let document = model.document
        let accountID = Container.shared.accountManager().account.id
        let objectID = document.objectId
        let spaceID = document.spaceId
        func validateSource() throws {
            guard !accountID.isEmpty, Container.shared.accountManager().account.id == accountID,
                  editor.viewModel.document.objectId == objectID,
                  editor.viewModel.document.spaceId == spaceID, document.isOpened else {
                throw PinkhaMiniAppsError.documentUnavailable
            }
        }
        try validateSource()
        let selectedIDs: [String]
        switch model.blocksStateManager.editingState {
        case .selecting(let blocks, _), .simpleTablesSelection(_, let blocks, _): selectedIDs = blocks
        default: selectedIDs = []
        }
        var textSelection: MiniAppTextSelection?
        var focusID: String?
        if let textView = editor.firstResponderView as? UITextView,
           (textView.isFirstResponder || range != nil),
           let blockID = blockID(containing: textView, editor: editor) {
            focusID = blockID
            let attributed = textView.attributedText ?? NSAttributedString(string: textView.text ?? "")
            let selectedRange = range ?? textView.selectedRange
            if selectedRange.location != NSNotFound,
               selectedRange.location >= 0, selectedRange.length >= 0,
               selectedRange.location <= attributed.length,
               selectedRange.length <= attributed.length - selectedRange.location {
                let before = AttributedTextConverter.asMiddleware(
                    attributedText: attributed.attributedSubstring(from: NSRange(location: 0, length: selectedRange.location)))
                let selected = AttributedTextConverter.asMiddleware(
                    attributedText: attributed.attributedSubstring(from: selectedRange))
                textSelection = MiniAppTextSelection(location: before.text.utf16.count,
                    length: selected.text.utf16.count, text: selected.text, blockIDs: [blockID])
            }
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
                guard let url = ContentUrlBuilder.fileUrl(fileId: file.metadata.targetObjectId) else { continue }
                let (local, response) = try await URLSession.shared.download(from: url)
                defer { try? FileManager.default.removeItem(at: local) }
                try validateSource()
                if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                    throw PinkhaMiniAppsError.attachmentUnavailable
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

    static var sourceAppID: String { Bundle.main.bundleIdentifier ?? "io.anytype.app" }

    static var callbacks: MiniAppCallbacks {
        let entries = Bundle.main.object(forInfoDictionaryKey: "CFBundleURLTypes") as? [[String: Any]]
        let schemes = entries?.flatMap { $0["CFBundleURLSchemes"] as? [String] ?? [] } ?? []
        let scheme = schemes.first(where: { $0 != "anytype" }) ?? "anytype"
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
    static func blockID(containing textView: UITextView, editor: EditorPageController) -> String? {
        var current: UIView? = textView
        while let view = current {
            if let cell = view as? UICollectionViewCell,
               let indexPath = editor.collectionView.indexPath(for: cell) {
                return editor.viewModel?.modelsHolder.blockViewModel(at: indexPath.row)?.blockId
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
