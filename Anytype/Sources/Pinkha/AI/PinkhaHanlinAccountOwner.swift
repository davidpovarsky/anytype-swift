import Foundation
import HanlinHostContracts

/// The application owns journal opening, presentation revocation and explicit account erasure.
/// Keeping journal actors across ordinary dismissals preserves late original-scope receipts and
/// prevents competing windows from opening separate writers for the same account/Space.
@MainActor
final class PinkhaHanlinAccountOwner {
    static let shared = PinkhaHanlinAccountOwner()

    private struct Presentation {
        weak var value: PinkhaHanlinChatPresentation?
        let account: Data
    }
    private struct Opening {
        let account: Data
        let task: Task<PinkhaHanlinWriteJournal, Error>
    }
    private var presentations: [UUID: Presentation] = [:]
    private var journals: [String: Opening] = [:]
    private var closedAccounts = Set<Data>()
    private var removingAccounts = Set<Data>()

    func isAvailable(account: String) -> Bool {
        !closedAccounts.contains(Data(account.utf8))
    }

    func register(_ presentation: PinkhaHanlinChatPresentation) throws {
        let account = presentation.session.context.namespace.account
        guard isAvailable(account: account) else { throw HanlinHostError.staleContext }
        presentations = presentations.filter { $0.value.value != nil }
        presentations[presentation.session.id] = .init(value: presentation, account: Data(account.utf8))
    }

    func unregister(_ id: UUID) { presentations[id] = nil }

    func owns(_ presentation: PinkhaHanlinChatPresentation) -> Bool {
        presentations[presentation.session.id]?.value === presentation
    }

    func journal(for namespace: HanlinConversationNamespace) async throws -> PinkhaHanlinWriteJournal {
        guard isAvailable(account: namespace.account) else { throw HanlinHostError.staleContext }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let key = PinkhaHanlinCreatePagePlan.digest(try encoder.encode(namespace))
        let opening: Opening
        if let existing = journals[key] {
            opening = existing
        } else {
            let task = Task { try await PinkhaHanlinWriteJournal.open(namespace: namespace) }
            opening = .init(account: Data(namespace.account.utf8), task: task)
            journals[key] = opening
        }
        let journal = try await opening.task.value
        guard isAvailable(account: namespace.account) else { throw HanlinHostError.staleContext }
        return journal
    }

    func accountDidOpen(_ account: String) throws {
        let key = Data(account.utf8)
        guard !removingAccounts.contains(key) else { throw HanlinHostError.staleContext }
        closedAccounts.remove(key)
    }

    /// A native logout/delete operation calls this BEFORE its first suspension. Ordinary logout
    /// preserves metadata; removeData explicitly poisons every opening/loaded writer before erasure.
    func closeAccount(_ account: String, removeData: Bool) async throws {
        guard !account.isEmpty else { return }
        let key = Data(account.utf8)
        closedAccounts.insert(key)
        let owned = presentations.values.filter { $0.account == key }.compactMap(\.value)
        for presentation in owned { presentation.invalidate() }
        guard removeData else { return }
        guard removingAccounts.insert(key).inserted else { throw HanlinHostError.staleContext }
        defer { removingAccounts.remove(key) }
        let openings = journals.filter { $0.value.account == key }
        // Do not cancel opening tasks: a suspended open must finish and be poisoned before unlink.
        for (_, opening) in openings {
            if let journal = try? await opening.task.value { await journal.revokeForDataRemoval() }
        }
        try await PinkhaHanlinWriteJournal.removeAccountData(account)
        for (id, _) in openings { journals[id] = nil }
    }
}
