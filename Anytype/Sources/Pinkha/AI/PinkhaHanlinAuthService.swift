import Foundation
import Factory
import Services
import HanlinHostContracts

/// Native Auth remains the account owner. These exact attempts only restrict
/// the existing Hanlin shutdown/resume calls and admit original Back cancellation.
actor PinkhaHanlinAuthService: AuthServiceProtocol {
    private let base: any AuthServiceProtocol
    private let accounts = Container.shared.accountManager()
    private var bootstrap: any PinkhaSpaceBootstrapServiceProtocol { Container.shared.pinkhaBootstrapService() }
    private var current: OriginalAuthAttempt?
    private var stopping: OriginalAuthAttempt?
    private var successfulStopRequired = false

    init(base: any AuthServiceProtocol) { self.base = base }

    func createWallet() async throws -> String {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.createWallet() }
        }
    }

    func walletRecovery(mnemonic: String) async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.walletRecovery(mnemonic: mnemonic) }
        }
    }

    func accountRecover() async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.accountRecover() }
        }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        try await base.mnemonicByEntropy(entropy)
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = accounts.account.id
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(previousAccount, removeData: false)
            }
            try await self.stage(attempt) { await bootstrap.quiesceAccountOperations() }
            let account = try await self.stage(attempt) {
                try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                    try await base.createAccount(name: name, iconOption: iconOption, imagePath: imagePath)
                }
            }
            try await self.stage(attempt) { try await bootstrap.resumeAccountOperations() }
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
                }
            }
            return account
        }
    }

    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = accounts.account.id
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(previousAccount, removeData: false)
            }
            try await self.stage(attempt) { await bootstrap.quiesceAccountOperations() }
            let account = try await self.stage(attempt) {
                try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                    try await base.selectAccount(id: id, preferredSpaceId: preferredSpaceId)
                }
            }
            try await self.stage(attempt) { try await bootstrap.resumeAccountOperations() }
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
                }
            }
            return account
        }
    }

    func logout(removeData: Bool) async throws {
        guard stopping == nil else { throw HanlinHostError.staleContext }
        let previous = current
        if let previous {
            // Keep the existing busy rejection for destructive overlap. Only
            // the real Back/logout(false) route supersedes a pending startup.
            guard previous.kind == .startup, !removeData else { throw HanlinHostError.staleContext }
        }
        let stop = try OriginalAuthAttempt(kind: .stop)
        stopping = stop
        previous?.retire() // synchronous, also revokes the child's Auth attempt
        let originalAccount = accounts.account.id
        let bootstrap = bootstrap
        try await withTaskCancellationHandler {
            do {
                // True removal keeps the original journal poison/flush/removal
                // before native erasure. This path never overlaps a startup.
                try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: removeData)
                // Dispatch real original Stop before joining any retired startup
                // or bootstrap stage. It can cancel native AccountSelect/Create.
                try await OriginalAuthRequestContext.$parent.withValue(stop) {
                    try await base.logout(removeData: removeData)
                }
                await previous?.waitForDrain()
                await bootstrap.quiesceAccountOperations()
                // An operation admitted before retirement may drain after Stop
                // began. Reclose its non-destructive presentation state afterwards.
                try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: false)
                let finalAccount = accounts.account.id
                if !finalAccount.utf8.elementsEqual(originalAccount.utf8) {
                    try await PinkhaHanlinAccountOwner.shared.closeAccount(finalAccount, removeData: false)
                }
                successfulStopRequired = false
                stop.finishOuter()
                if stopping === stop { stopping = nil }
            } catch {
                stop.retire()
                await previous?.waitForDrain()
                successfulStopRequired = true
                stop.finishOuter()
                if stopping === stop { stopping = nil }
                throw error
            }
        } onCancel: { stop.retire() }
    }

    func deleteAccount() async throws -> AccountStatus {
        let base = base
        let account = accounts.account.id
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(account, removeData: false)
            }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.deleteAccount() }
        }
    }

    func restoreAccount() async throws -> AccountStatus {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            let status = try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.restoreAccount() }
            let account = self.accounts.account.id
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account)
                }
            }
            return status
        }
    }

    private func stage<Value: Sendable>(
        _ attempt: OriginalAuthAttempt,
        operation: @escaping @Sendable () async throws -> Value
    ) async throws -> Value {
        try requireCurrent(attempt)
        let admissions = try attempt.admitStage()
        defer { for admission in admissions { admission.cancel() } }
        let result = try await operation()
        try requireCurrent(attempt)
        return result
    }

    private func perform<Value: Sendable>(
        kind: OriginalAuthAttempt.Kind,
        operation: @escaping @Sendable (OriginalAuthAttempt) async throws -> Value
    ) async throws -> Value {
        guard current == nil, stopping == nil, !successfulStopRequired else { throw HanlinHostError.staleContext }
        let attempt = try OriginalAuthAttempt(kind: kind)
        current = attempt
        return try await withTaskCancellationHandler {
            do {
                let result = try await operation(attempt)
                try requireCurrent(attempt)
                attempt.finishOuter()
                if current === attempt { current = nil }
                return result
            } catch {
                attempt.retire()
                attempt.finishOuter()
                await attempt.waitForDrain()
                if current === attempt { current = nil }
                throw error
            }
        } onCancel: { attempt.retire() }
    }

    private func requireCurrent(_ attempt: OriginalAuthAttempt) throws {
        guard current === attempt, stopping == nil else { throw HanlinHostError.staleContext }
        try attempt.validate()
    }
}
