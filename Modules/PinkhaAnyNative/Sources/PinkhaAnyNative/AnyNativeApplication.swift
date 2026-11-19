import Foundation
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaAnyRuntime
import PinkhaAnyUI

public enum AnyNativeApplicationError: Error, Equatable, Sendable {
    case busy
    case closed
    case signedOut
    case recoveryBackupRequired
    case malformedResponse
    case wrongAccount
    case invalidConfiguration
    case secureStorageUnavailable
}

public struct AnyNativeSpace: Identifiable, Sendable, Equatable {
    public let id: String
    public let name: String
    public let status: String
    public let ownRole: String
}

/// One fully scoped native workspace. UI owners must invalidate their mounted
/// state before close; the session then cancels/drains every document operation.
public struct AnyNativeWorkspaceOwner: Sendable {
    public let client: AnyHTTPClient
    public let session: AnyApplicationSession
    public let journal: AnyProtectedCreationJournal
    public let objects: AnyNativeObjectCreator
    public let blocks: AnyNativeBlockCreator
    public let capabilities: AnyUIFoundationCapabilities

    public var workspace: AnyTorahWorkspace { session.workspace }

    func close() async {
        await session.revokeAndDrain()
        await journal.close()
    }
}

/// The exclusive Any application owner. It never constructs a Heart service,
/// reads a Heart wallet, or passes a Heart object identifier into the new SDK.
/// Account transitions are serialized and drained before the C runtime stops.
public actor AnyNativeApplication {
    private let runtime = AnyEmbeddedRuntime.shared
    private let dataDirectory: URL
    private let vault: any AnyNativeCredentialStoring
    private var embedded: AnyEmbeddedSession?
    private var account: AnyNativeAccount?
    private var pendingCredential: AnyNativeCredential?
    private var lastNetwork: AnyEmbeddedNetwork?
    private var workspaceOwner: AnyNativeWorkspaceOwner?
    private var closing = false
    private var shutdown: Task<Void, Never>?
    private var generation = UUID()
    private var calls: [UUID: @Sendable () -> Void] = [:]
    private var drainWaiters: [CheckedContinuation<Void, Never>] = []

    public init(dataDirectory: URL, credentialService: String) throws {
        guard dataDirectory.isFileURL, dataDirectory.path.hasPrefix("/"),
              dataDirectory.path != "/", dataDirectory.lastPathComponent != ".." else {
            throw AnyNativeApplicationError.invalidConfiguration
        }
        self.dataDirectory = dataDirectory
        self.vault = try AnyNativeCredentialVault(service: credentialService)
    }

    #if DEBUG
    /// Fault-injection boundary for real native/Keychain acceptance tests.
    init(dataDirectory: URL, testCredentialStore: any AnyNativeCredentialStoring) throws {
        guard dataDirectory.isFileURL, dataDirectory.path.hasPrefix("/"),
              dataDirectory.path != "/", dataDirectory.lastPathComponent != ".." else {
            throw AnyNativeApplicationError.invalidConfiguration
        }
        self.dataDirectory = dataDirectory
        self.vault = testCredentialStore
    }
    #endif

    public static func defaultDataDirectory() throws -> URL {
        let support = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true)
        return support.appendingPathComponent("PinkhaAnyNativeV1", isDirectory: true)
    }

    public func savedAccounts() throws -> [AnyNativeAccount] { try vault.allMetadata() }
    public func currentAccount() -> AnyNativeAccount? { account }
    public func pendingRecoveryAccount() -> AnyNativeAccount? { pendingCredential?.metadata }
    public func isRunning() -> Bool { embedded != nil }
    public func currentWorkspace() -> AnyNativeWorkspaceOwner? { workspaceOwner }
    public func emergencyStop() -> AnyEmbeddedEmergencyStop? { embedded?.emergencyStop }

    public func start(network: AnyEmbeddedNetwork) async throws {
        try await transition {
            try await self.startOwned(network: network)
        }
    }

    private func startOwned(network: AnyEmbeddedNetwork) async throws {
        guard embedded == nil else { throw AnyNativeApplicationError.busy }
        try Task.checkCancellation()
        try FileManager.default.createDirectory(at: dataDirectory, withIntermediateDirectories: true,
            attributes: [.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication])
        let session = try await runtime.start(dataDirectory: dataDirectory, network: network, build: .pinkhaNativeV1)
        embedded = session
        lastNetwork = network
    }

    /// A generated recovery phrase is saved before any successful account
    /// receipt. The UI must show/acknowledge backup before opening documents.
    public func createAccount() async throws -> AnyNativeAccount {
        try await transition { try await self.authenticate(mnemonic: nil, index: 1, generated: true) }
    }

    public func restoreAccount(mnemonic: String, derivationIndex: UInt32 = 1) async throws -> AnyNativeAccount {
        guard !mnemonic.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              mnemonic.utf8.count <= 4096 else { throw AnyNativeApplicationError.invalidConfiguration }
        return try await transition {
            try await self.authenticate(mnemonic: mnemonic, index: derivationIndex, generated: false)
        }
    }

    public func openSavedAccount(id: String) async throws -> AnyNativeAccount {
        try await transition {
            let credential = try await self.readCredential(id: id)
            return try await self.authenticate(mnemonic: credential.mnemonic,
                index: credential.derivationIndex, generated: false,
                preserveBackupRequirement: credential.needsRecoveryBackup, expectedAccountID: id)
        }
    }

    private func readCredential(id: String) throws -> AnyNativeCredential { try vault.read(accountID: id) }

    private func authenticate(mnemonic: String?, index: UInt32, generated: Bool,
                              preserveBackupRequirement: Bool = false,
                              expectedAccountID: String? = nil) async throws -> AnyNativeAccount {
        guard let embedded else { throw AnyNativeApplicationError.closed }
        guard account == nil else { throw AnyNativeApplicationError.busy }
        guard pendingCredential == nil else { throw AnyNativeApplicationError.recoveryBackupRequired }
        do {
            var body: [String: AnyJSON] = [:]
            if let mnemonic {
                body["mnemonic"] = .string(mnemonic)
                body["index"] = .integer(Int64(index))
            }
            let bytes = try JSONEncoder().encode(AnyJSON.object(body))
            let response = try await runtime.executeControl(.authenticate, jsonBody: bytes,
                                                            expectedGeneration: embedded.generation)
            let value = try JSONDecoder().decode(AnyJSON.self, from: response)
            guard let id = value["accountId"]?.string, id.hasPrefix("A"), id.utf8.count <= 128,
                  let secret = generated ? value["mnemonic"]?.string : mnemonic, !secret.isEmpty else {
                throw AnyNativeApplicationError.malformedResponse
            }
            if let expectedAccountID, id != expectedAccountID { throw AnyNativeApplicationError.wrongAccount }
            // Preserve a confirmed credential before any cancellation boundary.
            // A persistence failure may expose it only through explicit recovery
            // UI; it never enables document access or an automatic new account.
            let credential = AnyNativeCredential(version: 1, accountID: id, derivationIndex: index,
                mnemonic: secret, needsRecoveryBackup: generated || preserveBackupRequirement)
            do { try vault.save(credential) }
            catch {
                pendingCredential = credential
                throw AnyNativeApplicationError.secureStorageUnavailable
            }
            account = credential.metadata
            return credential.metadata
        } catch {
            await failClosedAuthentication(generation: embedded.generation)
            throw error
        }
    }

    private func failClosedAuthentication(generation: UUID) async {
        account = nil
        do {
            _ = try await runtime.executeControl(.signOut, expectedGeneration: generation)
        } catch {
            await runtime.stop(expectedGeneration: generation)
            if embedded?.generation == generation { embedded = nil }
        }
    }

    /// Call only from the explicit recovery/backup UI. No receipt includes it.
    public func recoveryPhrase(accountID: String) throws -> String {
        guard !closing else { throw AnyNativeApplicationError.closed }
        if pendingCredential?.accountID == accountID { return pendingCredential!.mnemonic }
        return try vault.read(accountID: accountID).mnemonic
    }

    public func acknowledgeRecoveryBackup(accountID: String) async throws {
        try await transition { try await self.acknowledgeOwnedBackup(accountID: accountID) }
    }

    private func acknowledgeOwnedBackup(accountID: String) async throws {
        let recovering = pendingCredential?.accountID == accountID
        let old: AnyNativeCredential
        if recovering { old = pendingCredential! }
        else { old = try vault.read(accountID: accountID) }
        let updated = AnyNativeCredential(version: old.version, accountID: old.accountID,
            derivationIndex: old.derivationIndex, mnemonic: old.mnemonic, needsRecoveryBackup: false)
        do { try vault.save(updated) }
        catch { throw AnyNativeApplicationError.secureStorageUnavailable }
        if recovering {
            pendingCredential = nil
            if embedded == nil {
                guard let lastNetwork else { throw AnyNativeApplicationError.closed }
                try await startOwned(network: lastNetwork)
            }
            _ = try await authenticate(mnemonic: updated.mnemonic, index: updated.derivationIndex,
                                       generated: false, expectedAccountID: updated.accountID)
        } else if account?.id == accountID {
            account = updated.metadata
        }
    }

    public func listSpaces() async throws -> [AnyNativeSpace] {
        try await transition {
            let client = try await self.accountClient(requireBackup: true)
            let value = try await client.requestJSON(method: "GET", path: ["v1", "spaces"])
            guard let spaces = value["spaces"]?.array, spaces.count <= 10_000 else {
                throw AnyNativeApplicationError.malformedResponse
            }
            var seen = Set<String>()
            return try spaces.map { raw in
                guard let id = raw["id"]?.string, AnyEditorBlock.validID(id),
                      seen.insert(id).inserted, let status = raw["status"]?.string,
                      let role = raw["ownRole"]?.string else {
                    throw AnyNativeApplicationError.malformedResponse
                }
                return AnyNativeSpace(id: id, name: raw["name"]?.string ?? "",
                                      status: status, ownRole: role)
            }
        }
    }

    public func createSpace(name: String) async throws -> String {
        guard !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              name.utf8.count <= 512 else { throw AnyNativeApplicationError.invalidConfiguration }
        return try await transition {
            let client = try await self.accountClient(requireBackup: true)
            let value = try await client.requestJSON(method: "POST", path: ["v1", "spaces"],
                                                     body: .object(["name": .string(name)]))
            guard let id = value["id"]?.string, AnyEditorBlock.validID(id) else {
                throw AnyNativeApplicationError.malformedResponse
            }
            return id
        }
    }

    /// Explicit user-requested deletion. Native derived spaces remain protected
    /// by the server; no other account or legacy local store is touched.
    public func deleteSpace(id: String) async throws {
        guard AnyEditorBlock.validID(id) else { throw AnyNativeApplicationError.invalidConfiguration }
        try await transition { try await self.deleteOwnedSpace(id: id) }
    }

    private func deleteOwnedSpace(id: String) async throws {
        let client = try accountClient(requireBackup: true)
        if workspaceOwner?.workspace.spaceID == id { await closeOwnedSpace() }
        _ = try await client.requestJSON(method: "DELETE", path: ["v1", "spaces", id])
    }

    public func removeSavedAccount(id: String) throws {
        guard !closing, calls.isEmpty, account?.id != id else { throw AnyNativeApplicationError.busy }
        let credential = try vault.read(accountID: id)
        guard !credential.needsRecoveryBackup else { throw AnyNativeApplicationError.recoveryBackupRequired }
        try vault.remove(accountID: id)
    }

    /// Opening a Space verifies current membership and every native activation
    /// capability. It does not implicitly create or repair the Pinkha schema.
    public func connectSpace(id: String) async throws -> AnyNativeWorkspaceOwner {
        guard AnyEditorBlock.validID(id) else { throw AnyNativeApplicationError.invalidConfiguration }
        return try await transition { try await self.connectOwnedSpace(id: id) }
    }

    private func connectOwnedSpace(id: String) async throws -> AnyNativeWorkspaceOwner {
        let client = try accountClient(requireBackup: true)
        if let current = workspaceOwner, current.workspace.spaceID == id { return current }
        if let previous = workspaceOwner {
            workspaceOwner = nil
            await previous.close()
        }
        let workspace = try AnyTorahWorkspace(accountID: client.expectedAccountID, spaceID: id)
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        var openedJournal: AnyProtectedCreationJournal?
        do {
            let member = try await client.requestJSON(method: "GET", path: ["v1", "spaces", id, "members", "me"])
            try AnyHTTPTorahTargetAccess.validateMember(member, workspace: workspace, intent: .read)
            let capabilities = try await AnyUIFoundationCapabilities.verify(client: client, session: session)
            guard client.hasManagedAuthorization else { throw AnyNativeApplicationError.invalidConfiguration }
            let gateway = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
            guard gateway["mobileManagedTokenGateway"]?.integer == 1 else {
                throw AnyUIActivationError.missingCapability("mobileManagedTokenGateway")
            }
            let journal = try await AnyProtectedCreationJournal.open(workspace: workspace)
            openedJournal = journal
            let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
            let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace, journal: journal,
                                                    allowedTypeIDs: capabilities.allowedTargetTypes)
            try Task.checkCancellation()
            guard !closing else { throw AnyNativeApplicationError.closed }
            let owner = AnyNativeWorkspaceOwner(client: client, session: session, journal: journal,
                objects: objects, blocks: blocks, capabilities: capabilities)
            workspaceOwner = owner
            return owner
        } catch {
            await session.revokeAndDrain()
            await openedJournal?.close()
            throw error
        }
    }

    private func accountClient(requireBackup: Bool) throws -> AnyHTTPClient {
        guard !closing, let embedded, let account else { throw AnyNativeApplicationError.signedOut }
        guard !requireBackup || !account.needsRecoveryBackup else {
            throw AnyNativeApplicationError.recoveryBackupRequired
        }
        return try embedded.dataClient(expectedAccountID: account.id)
    }

    public func closeSpace() async throws {
        try await transition { await self.closeOwnedSpace() }
    }

    private func closeOwnedSpace() async {
        let current = workspaceOwner
        workspaceOwner = nil
        await current?.close()
    }

    public func signOut() async throws {
        try await transition { try await self.signOutOwned() }
    }

    private func signOutOwned() async throws {
        guard let embedded else { throw AnyNativeApplicationError.closed }
        await closeOwnedSpace()
        _ = try await runtime.executeControl(.signOut, expectedGeneration: embedded.generation)
        account = nil
    }

    /// Called only after the native UI has revoked/dismissed its owners.
    /// In-flight effects settle their original-scope receipts before stop.
    public func stop() async {
        if let shutdown {
            await shutdown.value
            return
        }
        closing = true
        generation = UUID()
        for cancel in calls.values { cancel() }
        let task = Task { await self.finishShutdown() }
        shutdown = task
        await task.value
        shutdown = nil
        closing = false
    }

    private func finishShutdown() async {
        if !calls.isEmpty {
            await withCheckedContinuation { drainWaiters.append($0) }
        }
        await closeOwnedSpace()
        if let embedded {
            await runtime.stop(expectedGeneration: embedded.generation)
        }
        embedded = nil
        account = nil
    }

    private func transition<Value: Sendable>(
        _ action: @escaping @Sendable () async throws -> Value
    ) async throws -> Value {
        guard !closing else { throw AnyNativeApplicationError.closed }
        guard calls.isEmpty else { throw AnyNativeApplicationError.busy }
        let ticket = UUID(), current = generation
        let task = Task { try await action() }
        calls[ticket] = { task.cancel() }
        defer {
            calls.removeValue(forKey: ticket)
            if calls.isEmpty {
                let waiters = drainWaiters
                drainWaiters.removeAll()
                for waiter in waiters { waiter.resume() }
            }
        }
        return try await withTaskCancellationHandler {
            let result = try await task.value
            guard !closing, generation == current else { throw AnyNativeApplicationError.closed }
            try Task.checkCancellation()
            return result
        } onCancel: { task.cancel() }
    }
}
