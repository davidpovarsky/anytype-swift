#if canImport(UIKit) && canImport(HanlinMiniAppsBridge)
import Foundation
import UIKit
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaHanlinUI
import HanlinMiniAppsBridge

struct AnyMiniAppsBlockMetadata: Codable, Equatable, Sendable {
    let type: String
    let inlineMarkdown: String
    let style: AnyJSON

    init(_ block: AnyEditorBlock) {
        type = block.type; inlineMarkdown = block.text
        style = block.native["style"] ?? .object([:])
    }

    var projection: AnyInlineMarkdown {
        type == "code" ? .init(literal: inlineMarkdown) : .init(inlineMarkdown)
    }

    func replacing(_ mutation: PinkhaMiniAppsEditPlan.Mutation) throws -> Self {
        let value = try projection.replacing(
            displayRange: .init(location: mutation.location, length: mutation.length),
            withLiteral: mutation.replacement)
        return .init(type: type, inlineMarkdown: value, style: style)
    }

    private init(type: String, inlineMarkdown: String, style: AnyJSON) {
        self.type = type; self.inlineMarkdown = inlineMarkdown; self.style = style
    }

    func snapshot(id: String) throws -> PinkhaMiniAppsBlockSnapshot {
        .init(id: id, text: projection.display, marks: try AnyMiniAppsCodec.encode(self))
    }
}

enum AnyMiniAppsCodec {
    static func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    static func digest<T: Encodable>(_ value: T) throws -> String {
        AnyContentDigest.sha256(try encode(value))
    }
    static var sourceAppID: String? { Bundle.main.bundleIdentifier }
    static var callbacks: MiniAppCallbacks {
        let types = Bundle.main.object(forInfoDictionaryKey: "CFBundleURLTypes") as? [[String: Any]] ?? []
        guard let scheme = types.compactMap({ $0["CFBundleURLSchemes"] as? [String] }).flatMap({ $0 }).first,
              let url = URL(string: scheme + "://miniapps/return") else { return .init() }
        return .init(success: url, error: url, cancel: url)
    }

    @MainActor
    static func matches(_ request: MiniAppInvocation, document: AnyDocumentPresentation) -> Bool {
        request.source.appID == sourceAppID && PinkhaMiniAppsEngineScope.any.matches(request.source) &&
        request.source.metadata["anytype.accountID"]?.utf8.elementsEqual(document.workspace.accountID.utf8) == true &&
        request.source.metadata["anytype.spaceID"]?.utf8.elementsEqual(document.workspace.spaceID.utf8) == true &&
        request.source.documentID?.utf8.elementsEqual(document.objectID.utf8) == true
    }
}

struct AnyMiniAppsCapturedContext: Sendable {
    let source: MiniAppSourceContext
    let inputs: [MiniAppContent]

    @MainActor
    static func capture(document: AnyDocumentPresentation, editor: AnyNativeEditorController,
                        additionalInputs: [MiniAppContent] = []) async throws -> Self {
        let owner = document.mountedOwnerID
        let selected = document.selectedBlockIDs
        let selectionRange = document.selectedTextRange
        await document.flush()
        try document.requireMounted(owner)
        guard !document.hasPendingEdits, !document.isLoading,
              document.selectedBlockIDs == selected, document.selectedTextRange == selectionRange,
              let visible = document.read, let appID = AnyMiniAppsCodec.sourceAppID,
              AnyMiniAppsCodec.callbacks.success != nil else { throw AnyHostError.changedDocument }
        let store = document.documents, objectID = document.objectID
        let current = try await document.nativeSession.perform {
            try await store.read(objectID: objectID, lease: $0)
        }
        try document.requireMounted(owner)
        guard current.snapshot == visible.snapshot, current.nativeVersion == visible.nativeVersion,
              document.read?.snapshot == visible.snapshot, !document.hasPendingEdits,
              document.selectedBlockIDs == selected, document.selectedTextRange == selectionRange
        else { throw AnyHostError.changedDocument }

        let blocks = Dictionary(uniqueKeysWithValues: current.snapshot.blocks.map { ($0.id, $0) })
        let textTypes = Set(["paragraph", "heading", "quote", "code", "list_item", "check_list_item"])
        let snapshots = try current.snapshot.depthFirstIDs.compactMap { id -> PinkhaMiniAppsBlockSnapshot? in
            guard let block = blocks[id], textTypes.contains(block.type) else { return nil }
            return try AnyMiniAppsBlockMetadata(block).snapshot(id: id)
        }
        let selection: MiniAppTextSelection?
        if selected.count == 1, let id = selected.first, let block = snapshots.first(where: { $0.id == id }) {
            guard let range = PinkhaMiniAppsEditPlanner.range(location: selectionRange.location,
                    length: selectionRange.length, in: block.text) else { throw AnyHostError.invalidSelection }
            selection = .init(location: selectionRange.location, length: selectionRange.length,
                              text: String(block.text[range]), blockIDs: [id])
        } else if !selected.isEmpty {
            guard Set(selected).isSubset(of: Set(current.snapshot.depthFirstIDs)) else { throw AnyHostError.invalidSelection }
            let picked = snapshots.filter { selected.contains($0.id) }
            let text = picked.map(\.text).joined(separator: "\n")
            selection = .init(location: 0, length: text.utf16.count, text: text, blockIDs: picked.map(\.id))
        } else { selection = nil }

        let encoded = try AnyMiniAppsCodec.encode(snapshots)
        guard let encodedString = String(data: encoded, encoding: .utf8) else { throw AnyHostError.invalidSelection }
        let metadata = [
            PinkhaMiniAppsEngineScope.metadataKey: PinkhaMiniAppsEngineScope.any.rawValue,
            "anytype.accountID": document.workspace.accountID,
            "anytype.spaceID": document.workspace.spaceID,
            "anytype.blocks": encodedString,
            "anytype.nativeVersion": current.nativeVersion,
            "anytype.insertionAnchor": selected.last ?? document.focusedBlockID ?? current.snapshot.depthFirstIDs.last ?? ""
        ]
        let source = MiniAppSourceContext(appID: appID, displayName: "Pinkha",
            documentID: document.objectID, documentTitle: current.snapshot.title,
            revision: current.snapshot.revision, selection: selection,
            documentText: snapshots.map(\.text).joined(separator: "\n"),
            kind: "editor", locator: document.objectID,
            sceneID: editor.viewIfLoaded?.window?.windowScene?.session.persistentIdentifier,
            metadata: metadata)
        var inputs: [MiniAppContent] = [.init(kind: .text, text: selection?.text ?? "",
                                            typeIdentifier: "public.utf8-plain-text")]
        inputs.append(contentsOf: additionalInputs)
        return .init(source: source, inputs: inputs)
    }
}
#endif
