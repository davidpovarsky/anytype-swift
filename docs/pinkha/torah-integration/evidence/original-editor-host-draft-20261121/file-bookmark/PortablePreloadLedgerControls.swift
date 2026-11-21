import Foundation

/// Runs the actual production ledger and document owner. PortableDocument is an
/// explicit disposable protocol probe; no file service, RPC or editor is faked
/// into a Native success by this component executable.
@main
private struct PortablePreloadLedgerControls {
    @MainActor
    private static func makeOwner() throws -> EditorDocumentWriteOwner {
        let document = PortableDocument()
        return try EditorDocumentWriteOwner(
            data: .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode),
            lifetimeDocument: document
        )
    }

    @MainActor
    private static func rejected(_ body: () throws -> Void) throws {
        do {
            try body()
        } catch let error as EditorDocumentWriteError {
            precondition(error == .rejected(.invalidLease))
            return
        }
        throw UnexpectedAcceptance()
    }

    @MainActor
    private static func unknownAndForeignReceipts() throws {
        let owner = try makeOwner(), other = try makeOwner()
        let ledger = DocumentOwnedFilePreloads(owner: owner)
        try rejected { _ = try ledger.claim(fileID: "foreign", spaceID: "owned-space", owner: owner) }
        try rejected { try ledger.remember(fileID: "owned", spaceID: "owned-space", owner: other) }
        try ledger.remember(fileID: "owned", spaceID: "owned-space", owner: owner)
        try rejected { _ = try ledger.claim(fileID: "owned", spaceID: "other-space", owner: owner) }
        try rejected { _ = try ledger.claim(fileID: "owned", spaceID: "owned-space", owner: other) }
        let claim = try ledger.claim(fileID: "owned", spaceID: "owned-space", owner: owner)
        try rejected { try ledger.completed(claim, owner: other) }
        try ledger.completed(claim, owner: owner)
    }

    @MainActor
    private static func unicodeIdentityStaysByteExact() throws {
        let owner = try makeOwner(), ledger = DocumentOwnedFilePreloads(owner: owner)
        let composed = "\u{e9}", decomposed = "e\u{301}"
        precondition(composed == decomposed && Data(composed.utf8) != Data(decomposed.utf8))
        try ledger.remember(fileID: composed, spaceID: composed, owner: owner)
        try rejected { _ = try ledger.claim(fileID: decomposed, spaceID: composed, owner: owner) }
        try rejected { _ = try ledger.claim(fileID: composed, spaceID: decomposed, owner: owner) }
        let claim = try ledger.claim(fileID: composed, spaceID: composed, owner: owner)
        try ledger.completed(claim, owner: owner)
    }

    @MainActor
    private static func uncertainClaimCannotBeRetriedOrReplaced() throws {
        let owner = try makeOwner(), ledger = DocumentOwnedFilePreloads(owner: owner)
        try ledger.remember(fileID: "retained", spaceID: "owned-space", owner: owner)
        _ = try ledger.claim(fileID: "retained", spaceID: "owned-space", owner: owner)
        // No success receipt: an original service error/cancellation cannot
        // authorize a replay, overwrite the claim, or discard the underlying data.
        try rejected { _ = try ledger.claim(fileID: "retained", spaceID: "owned-space", owner: owner) }
        try rejected { try ledger.remember(fileID: "retained", spaceID: "owned-space", owner: owner) }
        owner.retire()
        try rejected { try ledger.remember(fileID: "retained", spaceID: "owned-space", owner: owner) }
    }

    @MainActor
    private static func staleCompletionCannotConsumeNewReceipt() throws {
        let owner = try makeOwner(), ledger = DocumentOwnedFilePreloads(owner: owner)
        try ledger.remember(fileID: "reused-native-id", spaceID: "owned-space", owner: owner)
        let old = try ledger.claim(fileID: "reused-native-id", spaceID: "owned-space", owner: owner)
        try ledger.completed(old, owner: owner)
        try rejected { try ledger.completed(old, owner: owner) }
        // A new actual native preload can return the same content-addressed ID.
        // Its claim has a new generation, which an old completion cannot consume.
        try ledger.remember(fileID: "reused-native-id", spaceID: "owned-space", owner: owner)
        let current = try ledger.claim(fileID: "reused-native-id", spaceID: "owned-space", owner: owner)
        try rejected { try ledger.completed(old, owner: owner) }
        try ledger.completed(current, owner: owner)
    }

    @MainActor
    private static func independentLedgersCannotCompleteEachOther() throws {
        let owner = try makeOwner()
        let first = DocumentOwnedFilePreloads(owner: owner), second = DocumentOwnedFilePreloads(owner: owner)
        try first.remember(fileID: "same-id", spaceID: "owned-space", owner: owner)
        try second.remember(fileID: "same-id", spaceID: "owned-space", owner: owner)
        let a = try first.claim(fileID: "same-id", spaceID: "owned-space", owner: owner)
        let b = try second.claim(fileID: "same-id", spaceID: "owned-space", owner: owner)
        try rejected { try first.completed(b, owner: owner) }
        try rejected { try second.completed(a, owner: owner) }
        try first.completed(a, owner: owner)
        try second.completed(b, owner: owner)
    }

    @MainActor
    private static func lateBookkeepingDoesNotAuthorizeRetiredDispatch() async throws {
        let owner = try makeOwner(), ledger = DocumentOwnedFilePreloads(owner: owner)
        let probe = DispatchProbe()
        owner.retire()
        try ledger.remember(fileID: "late-original-result", spaceID: "owned-space", owner: owner)
        do {
            try await owner.performMutation(contextId: "owned") { await probe.invoke() }
            throw UnexpectedAcceptance()
        } catch let error as EditorDocumentWriteError {
            precondition(error == .rejected(.retired))
        }
        let count = await probe.count
        precondition(count == 0)
    }

    @MainActor
    static func main() async throws {
        try unknownAndForeignReceipts()
        try unicodeIdentityStaysByteExact()
        try uncertainClaimCannotBeRetriedOrReplaced()
        try staleCompletionCannotConsumeNewReceipt()
        try independentLedgersCannotCompleteEachOther()
        try await lateBookkeepingDoesNotAuthorizeRetiredDispatch()
        print("{\"status\":\"PASS_PORTABLE_PRELOAD_LEDGER_6\",\"executed\":6,\"passed\":6,\"file_service_RPC\":\"NOT_RUN\",\"wrapper_Apple_typecheck\":\"NOT_RUN\",\"native_editor\":\"NOT_RUN\"}")
    }
}

private struct UnexpectedAcceptance: Error {}

private actor DispatchProbe {
    private(set) var count = 0
    func invoke() { count += 1 }
}
