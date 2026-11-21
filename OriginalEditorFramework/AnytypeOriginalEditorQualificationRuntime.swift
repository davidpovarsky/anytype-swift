#if DEBUG && targetEnvironment(simulator)
import Foundation
import Darwin
import CryptoKit
import Services
import AnytypeCore
import ProtobufMessages
import SwiftProtobuf

internal enum OriginalEditorQualificationRuntimeError: Error, Sendable {
    case unqualifiedProcess, alreadyClaimed, existingAccount, existingRepository
    case configuredInvocation, missingAccountLifetime, invalidNativeAccount
    case unavailableRuntime, overlappingOperation, wrongSpace, invalidNativeSpace
    case permissionReadinessTimeout, invalidSpaceRole, fileSystemFailure(Int32)
}

internal struct OriginalEditorQualificationBootstrapFailure: Error {
    let retainedRepositoryDirectory: URL?
    let underlyingError: any Error
}

/// A receipt from the original WorkspaceCreate followed by WorkspaceOpen.
/// It does not contain wallet material or AccountInfo.metadataKey.
private struct OriginalEditorQualificationSpaceReceipt: Sendable {
    let spaceID: String
    let spaceViewID: String
    let createResponseSHA256: String
    let openedInfo: AccountInfo
}

/// This capability is minted only in this file after real native creation in a
/// new local-only acceptance account. It cannot wrap a caller-supplied Space ID.
@MainActor
internal final class OwnedQualificationSpace {
    internal let accountID: String
    internal let spaceID: String
    internal let runtimeNonce: UUID
    internal let creationResponseSHA256: String

    fileprivate enum Role { case fixture, restore }
    private let runtime: OwnedOriginalEditorQualificationRuntime
    private let role: Role
    private var claimed = false

    fileprivate init(runtime: OwnedOriginalEditorQualificationRuntime,
                     receipt: OriginalEditorQualificationSpaceReceipt, role: Role) {
        self.runtime = runtime
        self.role = role
        accountID = runtime.accountID
        spaceID = receipt.spaceID
        runtimeNonce = runtime.runtimeNonce
        creationResponseSHA256 = receipt.createResponseSHA256
    }

    internal func validateCurrentRuntime() throws {
        try runtime.validateCurrentRuntime()
        guard runtime.owns(self) else { throw OriginalEditorQualificationRuntimeError.wrongSpace }
    }

    internal func claimForFixture() throws {
        try claim(expected: .fixture)
    }

    internal func claimForImport() throws {
        try claim(expected: .restore)
    }

    private func claim(expected: Role) throws {
        try validateCurrentRuntime()
        guard role == expected, !claimed else {
            throw OriginalEditorQualificationRuntimeError.invalidSpaceRole
        }
        claimed = true
    }

    internal func performRPCs<Value: Sendable>(
        rpcNames: Set<String>, operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        try validateCurrentRuntime()
        return try await runtime.performRPCs(rpcNames: rpcNames, operation: operation)
    }
}

/// Qualification uses the original services in an exclusively owned fresh app
/// process. It has no logout, reset, account selection or repository deletion API.
/// Any failed operation retains its account, Space, files and process authority
/// until the acceptance runner shuts down its own simulator application.
@MainActor
internal final class OwnedOriginalEditorQualificationRuntime {
    private enum Phase { case starting, ready, failed }
    private static var processClaimed = false
    private static var retainedRuntime: OwnedOriginalEditorQualificationRuntime?

    internal let runtimeNonce = UUID()
    internal private(set) var accountID = ""
    internal private(set) var retainedRepositoryDirectory: URL?

    private let accountManager: any AccountManagerProtocol
    private let userInfo: any BasicUserInfoStorageProtocol
    private let accountLifetime: EditorDocumentWriteLifetime
    private let sourceLifetime = EditorDocumentWriteLifetime()
    private let middlewareListener: MiddlewareEventsListener
    private let invocationHandler: InvocationMesagesHandler
    private let workspaceService: any WorkspaceServiceProtocol
    private let participants: any ParticipantsStorageProtocol
    private let spaces: any SpaceViewsStorageProtocol
    private let objectTypes: any ObjectTypeProviderProtocol
    private let properties: any PropertyDetailsStorageProtocol
    private var sourceBinding: EditorDocumentWriteSourceBinding?
    private var accountCapture: EditorDocumentWriteCapture?
    private var accountReservation: EditorDocumentWriteLifetime.Observation?
    private var phase = Phase.starting
    private var operationInProgress = false
    private var spaceCreationInProgress = false
    private var fixtureRoleClaimed = false
    private var restoreRoleClaimed = false
    private var fixtureSpace: OwnedQualificationSpace?
    private var restoreSpace: OwnedQualificationSpace?

    private init(accountManager: any AccountManagerProtocol,
                 userInfo: any BasicUserInfoStorageProtocol,
                 accountLifetime: EditorDocumentWriteLifetime) {
        self.accountManager = accountManager
        self.userInfo = userInfo
        self.accountLifetime = accountLifetime
        middlewareListener = MiddlewareEventsListener()
        invocationHandler = InvocationMesagesHandler()
        workspaceService = Container.shared.workspaceService()
        participants = Container.shared.participantsStorage()
        spaces = Container.shared.spaceViewsStorage()
        objectTypes = Container.shared.objectTypeProvider()
        properties = Container.shared.propertyDetailsStorage()
    }

    /// Internal Debug/Simulator entry used only by the separate native acceptance
    /// consumer. The production SDK factory never creates or selects an account.
    internal static func createLocalOnlyAcceptance() async throws -> OwnedOriginalEditorQualificationRuntime {
        let admittedBundles: Set<String> = [
            "org.otzaria.original-editor-qualification",
            "com.davidpovarsky.chavrusatext",
        ]
        guard Bundle.main.bundleIdentifier.map(admittedBundles.contains) == true,
              ProcessInfo.processInfo.environment["OTZARIA_ORIGINAL_EDITOR_QUALIFICATION"] == "owned-local-only",
              InvocationDispatchContext.binding == nil else {
            throw OriginalEditorQualificationRuntimeError.unqualifiedProcess
        }
        guard !processClaimed else { throw OriginalEditorQualificationRuntimeError.alreadyClaimed }
        guard InvocationSettings.handler == nil else {
            throw OriginalEditorQualificationRuntimeError.configuredInvocation
        }
        // The original app-group getter can migrate an existing standard value.
        // Inspect raw keys before instantiating that original identity storage.
        let groupDefaults = UserDefaults(suiteName: TargetsConstants.appGroup)
        guard ["userId", "analyticsId"].allSatisfy({ key in
            UserDefaults.standard.object(forKey: key) == nil
                && groupDefaults?.object(forKey: key) == nil
        }) else {
            throw OriginalEditorQualificationRuntimeError.existingAccount
        }
        let manager = Container.shared.accountManager()
        let info = Container.shared.basicUserInfoStorage()
        guard manager.account.id.isEmpty, info.usersId.isEmpty else {
            throw OriginalEditorQualificationRuntimeError.existingAccount
        }
        guard let accountLifetime = manager.editorWriteLifetime else {
            throw OriginalEditorQualificationRuntimeError.missingAccountLifetime
        }
        processClaimed = true
        let runtime = OwnedOriginalEditorQualificationRuntime(
            accountManager: manager, userInfo: info, accountLifetime: accountLifetime
        )
        // Retention is deliberate: a cancelled native call or Go import can
        // outlive its Swift caller. Failure never makes this process reusable.
        retainedRuntime = runtime
        do {
            try await runtime.bootstrap()
            return runtime
        } catch {
            runtime.failClosed()
            throw OriginalEditorQualificationBootstrapFailure(
                retainedRepositoryDirectory: runtime.retainedRepositoryDirectory,
                underlyingError: error
            )
        }
    }

    private func bootstrap() async throws {
        let transition = EditorAccountWriteTransition(
            lifetime: accountLifetime, rpcNames: ["WalletCreate", "AccountCreate"]
        )
        defer { transition.finish() }
        let localRepo = Container.shared.localRepoService()
        let claim = try await OriginalEditorQualificationRepositoryFiles().claim(
            runtimeNonce: runtimeNonce, original: localRepo
        )
        retainedRepositoryDirectory = claim.parent
        try Task.checkCancellation()
        guard accountManager.account.id.isEmpty, userInfo.usersId.isEmpty else {
            throw OriginalEditorQualificationRuntimeError.existingAccount
        }
        // The same original response-event handler is retained; logging remains
        // disabled so the disposable wallet has no diagnostic credential copy.
        InvocationSettings.handler = invocationHandler
        let auth = Container.shared.authMiddleService()
        let account = try await InvocationDispatchContext.$binding.withValue(transition.binding) {
            _ = try await auth.createWallet(rootPath: claim.repository.path)
            try Task.checkCancellation()
            return try await auth.createAccount(
                name: "Original editor qualification", imagePath: "", iconOption: 0,
                networkMode: .localOnly, joinStreamUrl: "", configPath: nil
            )
        }
        try Task.checkCancellation()
        guard !account.id.isEmpty, !account.id.utf8.contains(0),
              account.status == .active, !account.info.techSpaceId.isEmpty,
              accountManager.account.id.isEmpty, userInfo.usersId.isEmpty else {
            throw OriginalEditorQualificationRuntimeError.invalidNativeAccount
        }
        accountID = account.id
        userInfo.usersId = account.id
        accountManager.account = account
        Container.shared.middlewareConfigurationProvider().setupConfiguration(account: account)
        let expected = account.id
        let manager = accountManager
        let info = userInfo
        transition.finish {
            manager.account.id.utf8.elementsEqual(expected.utf8)
                && info.usersId.utf8.elementsEqual(expected.utf8)
        }
        let capturedAccount = try EditorDocumentWriteCapture(accountLifetime)
        accountCapture = capturedAccount
        // Pin this one native account for the entire owned acceptance process.
        // Even a timeout after ObjectImport's early return cannot let an original
        // AuthService transition overtake its still-running Go import.
        guard let reservation = accountLifetime.admitOperation(capturedAccount.token) else {
            throw OriginalEditorQualificationRuntimeError.unavailableRuntime
        }
        accountReservation = reservation
        sourceBinding = try EditorDocumentWriteSourceBinding(
            lifetime: sourceLifetime, accountLifetime: accountLifetime,
            isCurrent: { [weak self] in self?.identityIsCurrent() == true }
        )
        // Original long-lived subscriptions inherit the frozen account context,
        // not a short opening/import lease. The original Lib listener is additive.
        try await InvocationDispatchContext.$binding.withValue(capturedAccount.accountDispatchBinding()) {
            middlewareListener.startListening()
            await spaces.startSubscription()
            await participants.startSubscription()
            try Task.checkCancellation()
        }
        try sourceBinding?.validate()
        phase = .ready
        try validateCurrentRuntime()
    }

    internal func validateCurrentRuntime() throws {
        guard phase == .ready, identityIsCurrent(), let sourceBinding else {
            throw OriginalEditorQualificationRuntimeError.unavailableRuntime
        }
        try sourceBinding.validate()
    }

    private func identityIsCurrent() -> Bool {
        phase != .failed && !accountID.isEmpty
            && accountManager.account.id.utf8.elementsEqual(accountID.utf8)
            && userInfo.usersId.utf8.elementsEqual(accountID.utf8)
    }

    fileprivate func owns(_ space: OwnedQualificationSpace) -> Bool {
        (fixtureSpace === space || restoreSpace === space)
            && space.runtimeNonce == runtimeNonce
            && space.accountID.utf8.elementsEqual(accountID.utf8)
    }

    internal func makeFixtureSpace() async throws -> OwnedQualificationSpace {
        try validateCurrentRuntime()
        guard !fixtureRoleClaimed else { throw OriginalEditorQualificationRuntimeError.alreadyClaimed }
        guard !spaceCreationInProgress, !operationInProgress else {
            throw OriginalEditorQualificationRuntimeError.overlappingOperation
        }
        fixtureRoleClaimed = true
        let result = try await makeSpace(role: .fixture)
        fixtureSpace = result
        return result
    }

    internal func makeRestoreSpace() async throws -> OwnedQualificationSpace {
        try validateCurrentRuntime()
        guard !restoreRoleClaimed else { throw OriginalEditorQualificationRuntimeError.alreadyClaimed }
        guard !spaceCreationInProgress, !operationInProgress else {
            throw OriginalEditorQualificationRuntimeError.overlappingOperation
        }
        restoreRoleClaimed = true
        let result = try await makeSpace(role: .restore)
        restoreSpace = result
        return result
    }

    private func makeSpace(role: OwnedQualificationSpace.Role) async throws -> OwnedQualificationSpace {
        // Reserve the entire creation/readiness interval before its first await.
        // A second caller cannot create an abandoned duplicate native Space.
        spaceCreationInProgress = true
        defer { spaceCreationInProgress = false }
        let name = "Original editor " + (role == .fixture ? "source " : "restore ") + runtimeNonce.uuidString
        let service = workspaceService
        let receipt = try await performRPCs(
            rpcNames: ["WorkspaceCreate", "WorkspaceOpen"], duringSpaceCreation: true
        ) {
            let created = try await service.createSpace(
                name: name, iconOption: 0, accessType: .private,
                useCase: .none, withChat: false, spaceType: .regular
            )
            guard !created.spaceID.isEmpty, !created.spaceID.utf8.contains(0) else {
                throw OriginalEditorQualificationRuntimeError.invalidNativeSpace
            }
            let opened = try await service.workspaceOpen(spaceId: created.spaceID, withChat: false)
            guard opened.accountSpaceId.utf8.elementsEqual(created.spaceID.utf8),
                  !opened.spaceViewId.isEmpty else {
                throw OriginalEditorQualificationRuntimeError.invalidNativeSpace
            }
            return OriginalEditorQualificationSpaceReceipt(
                spaceID: created.spaceID, spaceViewID: opened.spaceViewId,
                createResponseSHA256: SHA256.hash(data: try created.serializedData())
                    .map { String(format: "%02x", $0) }.joined(),
                openedInfo: opened
            )
        }
        do {
            try validateCurrentRuntime()
            spaces.addSpaceInfo(spaceId: receipt.spaceID, info: receipt.openedInfo)
            guard let accountCapture else { throw OriginalEditorQualificationRuntimeError.unavailableRuntime }
            try await InvocationDispatchContext.$binding.withValue(accountCapture.accountDispatchBinding()) {
                await objectTypes.prepareData(spaceId: receipt.spaceID)
                await properties.prepareData(spaceId: receipt.spaceID)
                try Task.checkCancellation()
            }
            // Check real native type data instead of installing a substitute.
            _ = try objectTypes.objectType(uniqueKey: .page, spaceId: receipt.spaceID)
            let clock = ContinuousClock()
            let deadline = clock.now.advanced(by: .seconds(15))
            while !participants.canEdit(spaceId: receipt.spaceID) {
                try validateCurrentRuntime()
                guard clock.now < deadline else {
                    throw OriginalEditorQualificationRuntimeError.permissionReadinessTimeout
                }
                try await clock.sleep(for: .milliseconds(50))
            }
            try validateCurrentRuntime()
            return OwnedQualificationSpace(runtime: self, receipt: receipt, role: role)
        } catch {
            failClosed()
            throw error
        }
    }

    fileprivate func performRPCs<Value: Sendable>(
        rpcNames: Set<String>, duringSpaceCreation: Bool = false,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        try validateCurrentRuntime()
        guard !operationInProgress, (!spaceCreationInProgress || duringSpaceCreation),
              let sourceBinding else {
            throw OriginalEditorQualificationRuntimeError.overlappingOperation
        }
        operationInProgress = true
        defer { operationInProgress = false }
        do {
            let value = try await sourceBinding.performOperation(rpcNames: rpcNames, operation: operation)
            try validateCurrentRuntime()
            return value
        } catch {
            failClosed()
            throw error
        }
    }

    private func failClosed() {
        phase = .failed
        sourceLifetime.markUnavailable()
        // Keep accountReservation, native services, files and receipts alive.
        // An error is not evidence that an asynchronous native import stopped.
    }
}

/// Small filesystem preparation runs on its own actor, never on the UI actor.
/// mkdir is exclusive; an existing original repository or parent is preserved.
private actor OriginalEditorQualificationRepositoryFiles {
    struct Claim: Sendable { let parent: URL; let repository: URL }

    func claim(runtimeNonce: UUID, original: any LocalRepoServiceProtocol) throws -> Claim {
        let support = try FileManager.default.url(
            for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: true
        ).resolvingSymlinksInPath().standardizedFileURL
        let parent = support.appendingPathComponent("Anytype", isDirectory: true)
        guard Darwin.mkdir(parent.path, 0o700) == 0 else {
            if errno == EEXIST { throw OriginalEditorQualificationRuntimeError.existingRepository }
            throw OriginalEditorQualificationRuntimeError.fileSystemFailure(errno)
        }
        let expected = parent.appendingPathComponent("middleware-go", isDirectory: true)
        let actual = original.middlewareRepoURL.standardizedFileURL
        guard actual.path.utf8.elementsEqual(expected.path.utf8),
              actual.resolvingSymlinksInPath().path.utf8.elementsEqual(actual.path.utf8) else {
            throw OriginalEditorQualificationRuntimeError.existingRepository
        }
        var info = stat()
        guard Darwin.lstat(actual.path, &info) != 0, errno == ENOENT else {
            throw OriginalEditorQualificationRuntimeError.existingRepository
        }
        let receipt = try JSONSerialization.data(withJSONObject: [
            "runtimeNonce": runtimeNonce.uuidString,
            "scope": "fresh local-only original editor acceptance; no account reset or repository reuse",
        ], options: [.sortedKeys])
        try receipt.write(to: parent.appendingPathComponent("OriginalEditorQualificationClaim.json"),
                          options: .withoutOverwriting)
        return Claim(parent: parent, repository: actual)
    }
}
#endif
