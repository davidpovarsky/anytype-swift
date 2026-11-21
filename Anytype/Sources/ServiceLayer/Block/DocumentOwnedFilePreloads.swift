import Foundation

/// Receipts for preloads actually returned to this prepared document session.
/// This is ownership bookkeeping only; the original file service owns the data.
@MainActor
final class DocumentOwnedFilePreloads {
    struct Claim: Sendable {
        fileprivate let fileID: Data
        fileprivate let spaceID: Data
        fileprivate let generation: UUID
    }

    private enum State { case available, claimed }
    private struct Entry {
        let spaceID: Data
        let generation: UUID
        var state: State
    }

    private let owner: EditorDocumentWriteOwner
    private var entries: [Data: Entry] = [:]

    init(owner: EditorDocumentWriteOwner) {
        self.owner = owner
    }

    func requireOwner(_ expected: EditorDocumentWriteOwner) throws {
        guard owner === expected else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
    }

    /// Preserve a returned receipt even if retirement follows the original RPC.
    /// Remembering it does not authorize another RPC or deliver a stale result.
    func remember(fileID: String, spaceID: String, owner expected: EditorDocumentWriteOwner) throws {
        try requireOwner(expected)
        guard !fileID.isEmpty, !fileID.utf8.contains(0) else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        let key = Data(fileID.utf8)
        guard entries[key] == nil else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        entries[key] = Entry(spaceID: Data(spaceID.utf8), generation: UUID(), state: .available)
    }

    /// An upload or discard can claim only this session's returned preload.
    /// A failed or cancelled original call leaves the claim uncertain: neither
    /// automatic retry nor destructive cleanup can infer that it rolled back.
    func claim(fileID: String, spaceID: String, owner expected: EditorDocumentWriteOwner) throws -> Claim {
        try requireOwner(expected)
        let key = Data(fileID.utf8)
        guard var entry = entries[key], entry.spaceID == Data(spaceID.utf8),
              case .available = entry.state else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        entry.state = .claimed
        entries[key] = entry
        return Claim(fileID: key, spaceID: entry.spaceID, generation: entry.generation)
    }

    /// Called only after the underlying original service returns success, not
    /// merely when an outer Task is cancelled or its ownership is retired.
    func completed(_ claim: Claim, owner expected: EditorDocumentWriteOwner) throws {
        try requireOwner(expected)
        guard let entry = entries[claim.fileID], entry.spaceID == claim.spaceID,
              entry.generation == claim.generation,
              case .claimed = entry.state else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        entries.removeValue(forKey: claim.fileID)
    }
}
