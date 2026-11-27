import Foundation
import Observation
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration

public enum AnyNativeRecoveryError: Error, Equatable, Sendable {
    case wrongWorkspace, invalidSnapshot, capacityExceeded
}

/// UI-only destinations contain native IDs; they carry no service or authority.
public enum AnyNativeLibraryDestination: Hashable, Sendable {
    case folder(String)
    case document(String, String?)
    case allDocuments
    case notes
    case bin
}

public struct AnyNativeRecoveredBlockDraft: Sendable, Equatable, Encodable {
    public let baseNative: AnyJSON
    public let inlineMarkdown: String
    public let selectionLocation: Int
    public let selectionLength: Int
    public let revision: UInt64
    public let blockID: String
    public var selection: NSRange { NSRange(location: selectionLocation, length: selectionLength) }

    public init(base: AnyEditorBlock, inlineMarkdown: String, selection: NSRange,
                revision: UInt64) throws {
        let projection = base.type == "code" ? AnyInlineMarkdown(literal: inlineMarkdown) :
                                              AnyInlineMarkdown(inlineMarkdown)
        // Use the same scalar-safe UTF-16 boundary check as live composition.
        // Foundation range conversion alone accepted a split surrogate on Apple.
        guard inlineMarkdown.utf8.count <= 65_536, projection.isEditable,
              selection.location >= 0, selection.length >= 0,
              selection.location <= projection.display.utf16.count,
              selection.length <= projection.display.utf16.count - selection.location,
              (try? AnyInlineMarkdown(literal: projection.display).sourceRange(for: selection)) != nil else {
            throw AnyNativeRecoveryError.invalidSnapshot
        }
        self.baseNative = base.native; self.blockID = base.id; self.inlineMarkdown = inlineMarkdown
        self.selectionLocation = selection.location; self.selectionLength = selection.length
        self.revision = revision
    }
}

/// Visible input that could not be mapped back through known inline markup.
/// It is local copy/review data, never an automatically writable native source.
public struct AnyNativeUnmappedTextDraft: Sendable, Equatable, Encodable {
    public let blockID: String
    public let baseNative: AnyJSON
    public let baselineSource: String
    public let display: String
    public let selectionLocation: Int
    public let selectionLength: Int
    public let reason: String
    public var selection: NSRange { .init(location: selectionLocation, length: selectionLength) }

    public init(base: AnyEditorBlock, baselineSource: String, display: String,
                selection: NSRange, reason: String) throws {
        guard baselineSource.utf8.count <= 65_536, display.utf8.count <= 65_536,
              reason.utf8.count <= 1024 else { throw AnyNativeRecoveryError.invalidSnapshot }
        _ = try AnyInlineMarkdown(literal: display).sourceRange(for: selection)
        self.blockID = base.id; self.baseNative = base.native
        self.baselineSource = baselineSource; self.display = display; self.reason = reason
        self.selectionLocation = selection.location; self.selectionLength = selection.length
    }
}

public struct AnyNativeDocumentRecoverySnapshot: Sendable, Encodable {
    public let workspace: AnyTorahWorkspace
    public let objectID: String
    public let dataset: String
    public let drafts: [AnyNativeRecoveredBlockDraft]
    public let unmappedDrafts: [AnyNativeUnmappedTextDraft]
    public let selectedBlockIDs: [String]
    public let focusedBlockID: String?
    public let selectionLocation: Int
    public let selectionLength: Int
    public var selection: NSRange { .init(location: selectionLocation, length: selectionLength) }

    public init(workspace: AnyTorahWorkspace, objectID: String, dataset: String = "editor_blocks",
                drafts: [AnyNativeRecoveredBlockDraft], selectedBlockIDs: [String],
                focusedBlockID: String?, selection: NSRange,
                unmappedDrafts: [AnyNativeUnmappedTextDraft] = []) throws {
        guard AnyEditorBlock.validID(objectID), dataset == "editor_blocks",
              drafts.count + unmappedDrafts.count <= 1_000,
              Set(drafts.map(\.blockID)).count == drafts.count,
              Set(unmappedDrafts.map(\.blockID)).count == unmappedDrafts.count,
              selectedBlockIDs.count <= 10_000,
              selectedBlockIDs.allSatisfy(AnyEditorBlock.validID),
              Set(selectedBlockIDs).count == selectedBlockIDs.count,
              focusedBlockID.map(AnyEditorBlock.validID) ?? true,
              selection.location >= 0, selection.length >= 0,
              selection.location <= 65_536, selection.length <= 65_536 - selection.location else {
            throw AnyNativeRecoveryError.invalidSnapshot
        }
        self.workspace = workspace; self.objectID = objectID; self.dataset = dataset
        self.drafts = drafts.sorted { $0.blockID < $1.blockID }
        self.unmappedDrafts = unmappedDrafts.sorted { $0.blockID < $1.blockID }
        self.selectedBlockIDs = selectedBlockIDs; self.focusedBlockID = focusedBlockID
        self.selectionLocation = selection.location; self.selectionLength = selection.length
    }
}

public enum AnyNativeDraftReconciliation: Sendable, Equatable {
    case alreadyStored, requiresReview, conflict

    public static func evaluate(_ draft: AnyNativeRecoveredBlockDraft,
                                current: AnyEditorBlock?, reachable: Bool) -> Self {
        guard reachable, let current, current.id == draft.blockID,
              current.type == draft.baseNative["type"]?.string else { return .conflict }
        // A late native confirmation may outlive its old mounted UI owner.
        // Matching current text is accepted without issuing another mutation.
        if current.text == draft.inlineMarkdown { return .alreadyStored }
        guard current.text == (draft.baseNative["text"]?.string ?? ""),
              current.native["_ver"] == draft.baseNative["_ver"] else { return .conflict }
        return .requiresReview
    }
}

/// Retained by the account/Space owner across a background runtime restart.
/// This is bounded local recovery state, not a journal or a grant of authority.
/// It deliberately does not promise persistence after process termination.
@MainActor @Observable
public final class AnyNativeLibraryRecovery {
    public let workspace: AnyTorahWorkspace
    public private(set) var navigation: [AnyNativeLibraryDestination] = []
    @ObservationIgnored private var documents: [String: AnyNativeDocumentRecoverySnapshot] = [:]
    @ObservationIgnored private var sizes: [String: Int] = [:]
    @ObservationIgnored private var attachmentIntents: AnyNativeAttachmentIntentStore?
    private static let maximumDocuments = 128
    private static let maximumBytes = 16_777_216

    public init(workspace: AnyTorahWorkspace) { self.workspace = workspace }

    /// Only attachment caller intents use protected process-persistent storage.
    /// The original navigation/text recovery above keeps its existing lifetime.
    func attachmentIntentStore(workspace expected: AnyTorahWorkspace) throws -> AnyNativeAttachmentIntentStore {
        try requireWorkspace(expected)
        guard workspace.accountID.utf8.elementsEqual(expected.accountID.utf8),
              workspace.spaceID.utf8.elementsEqual(expected.spaceID.utf8) else {
            throw AnyNativeRecoveryError.wrongWorkspace
        }
        if let attachmentIntents { return attachmentIntents }
        let store = AnyNativeAttachmentIntentStore(workspace: workspace)
        attachmentIntents = store
        return store
    }

    public func requireWorkspace(_ expected: AnyTorahWorkspace) throws {
        guard workspace == expected else { throw AnyNativeRecoveryError.wrongWorkspace }
    }

    public func replaceNavigation(_ path: [AnyNativeLibraryDestination],
                                  workspace expected: AnyTorahWorkspace) throws {
        try requireWorkspace(expected)
        guard path.count <= 128 else { throw AnyNativeRecoveryError.capacityExceeded }
        for route in path {
            switch route {
            case .document(let id, let block):
                guard AnyEditorBlock.validID(id), block.map(AnyEditorBlock.validID) ?? true else {
                    throw AnyNativeRecoveryError.invalidSnapshot
                }
            case .folder(let id):
                guard AnyEditorBlock.validID(id) else { throw AnyNativeRecoveryError.invalidSnapshot }
            case .allDocuments, .notes, .bin: break
            }
        }
        navigation = path
    }

    public func save(_ snapshot: AnyNativeDocumentRecoverySnapshot) throws {
        try requireWorkspace(snapshot.workspace)
        let bytes = try JSONEncoder().encode(snapshot).count
        let total = sizes.filter { $0.key != snapshot.objectID }.values.reduce(0, +) + bytes
        guard documents[snapshot.objectID] != nil || documents.count < Self.maximumDocuments,
              total <= Self.maximumBytes else { throw AnyNativeRecoveryError.capacityExceeded }
        documents[snapshot.objectID] = snapshot; sizes[snapshot.objectID] = bytes
    }

    public func document(_ objectID: String,
                         workspace expected: AnyTorahWorkspace) throws -> AnyNativeDocumentRecoverySnapshot? {
        try requireWorkspace(expected)
        guard AnyEditorBlock.validID(objectID) else { throw AnyNativeRecoveryError.invalidSnapshot }
        return documents[objectID]
    }

    /// Only an explicit user action clears unsaved content.
    public func discardDocument(_ objectID: String, workspace expected: AnyTorahWorkspace) throws {
        try requireWorkspace(expected)
        documents.removeValue(forKey: objectID); sizes.removeValue(forKey: objectID)
    }
}
