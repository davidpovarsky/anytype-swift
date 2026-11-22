#if DEBUG && targetEnvironment(simulator)
import Foundation
import Darwin
import CryptoKit
import Security
@_spi(OriginalEditorQualification) import SecureService
@_spi(OriginalEditorQualification) import Services
import AnytypeCore
import ProtobufMessages
import SwiftProtobuf

internal enum OriginalEditorQualificationRuntimeError: Error, Sendable {
    case unqualifiedProcess, alreadyClaimed, existingAccount, existingRepository
    case configuredInvocation, missingAccountLifetime, invalidNativeAccount
    case unavailableRuntime, overlappingOperation, wrongSpace, invalidNativeSpace
    case permissionReadinessTimeout, invalidSpaceRole, fileSystemFailure(Int32)
    case invalidResumeCheckpoint, invalidResumeCredential, resumeCredentialCleanupFailed, resumeNotRequested
}

internal struct OriginalEditorQualificationBootstrapFailure: Error {
    let retainedRepositoryDirectory: URL?
    let underlyingError: any Error
    let credentialCleanupError: (any Error)?

    init(retainedRepositoryDirectory: URL?, underlyingError: any Error,
         credentialCleanupError: (any Error)? = nil) {
        self.retainedRepositoryDirectory = retainedRepositoryDirectory
        self.underlyingError = underlyingError
        self.credentialCleanupError = credentialCleanupError
    }
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

    internal let runtimeNonce: UUID
    internal private(set) var accountID = ""
    internal private(set) var retainedRepositoryDirectory: URL?
    internal private(set) var recoveredCheckpoint: OriginalEditorQualificationResumeCheckpoint?
    internal private(set) var recoveredEvidenceDirectory: URL?
    internal private(set) var processResumeReceipt: AnytypeOriginalEditorProcessResumeReceipt?
    private let preparesProcessResume: Bool
    private let resumeFiles: OriginalEditorQualificationResumeFiles
    private var processResumePrepared = false
    private static var processResumeMode: String? {
        ProcessInfo.processInfo.environment["OTZARIA_ORIGINAL_EDITOR_PROCESS_RESUME"]
    }

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
                 accountLifetime: EditorDocumentWriteLifetime,
                 runtimeNonce: UUID = UUID(), preparesProcessResume: Bool = false,
                 resumeFiles: OriginalEditorQualificationResumeFiles = .init()) {
        self.runtimeNonce = runtimeNonce
        self.preparesProcessResume = preparesProcessResume
        self.resumeFiles = resumeFiles
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
              InvocationDispatchContext.binding == nil,
              processResumeMode == nil || processResumeMode == "prepare-owned-once" else {
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
            accountManager: manager, userInfo: info, accountLifetime: accountLifetime,
            preparesProcessResume: processResumeMode == "prepare-owned-once"
        )
        // Retention is deliberate: a cancelled native call or Go import can
        // outlive its Swift caller. Failure never makes this process reusable.
        retainedRuntime = runtime
        do {
            try await runtime.bootstrap()
            return runtime
        } catch {
            runtime.failClosed()
            var cleanupError: (any Error)?
            if runtime.preparesProcessResume {
                do { try await runtime.resumeFiles.removeOwnedCredential() } catch { cleanupError = error }
            }
            throw OriginalEditorQualificationBootstrapFailure(
                retainedRepositoryDirectory: runtime.retainedRepositoryDirectory,
                underlyingError: error, credentialCleanupError: cleanupError
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
            let mnemonic = try await auth.originalEditorQualificationCreateWallet(rootPath: claim.repository.path)
            if preparesProcessResume {
                try await resumeFiles.storeCredential(mnemonic, nonce: runtimeNonce)
            }
            try Task.checkCancellation()
            return try await auth.originalEditorQualificationCreateAccount(
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
        await transition.finishAndWaitForRelease {
            manager.account.id.utf8.elementsEqual(expected.utf8)
                && info.usersId.utf8.elementsEqual(expected.utf8)
        }
        try Task.checkCancellation()
        guard identityIsCurrent() else { throw OriginalEditorQualificationRuntimeError.invalidNativeAccount }
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



    internal static func cleanupOwnedProcessResumeCredential() async throws -> Bool {
        guard ["org.otzaria.original-editor-qualification", "com.davidpovarsky.chavrusatext"]
                .contains(Bundle.main.bundleIdentifier ?? ""),
              ProcessInfo.processInfo.environment["OTZARIA_ORIGINAL_EDITOR_QUALIFICATION"] == "owned-local-only",
              ["prepare-owned-once", "resume-owned-once"].contains(processResumeMode ?? "") else {
            throw OriginalEditorQualificationRuntimeError.unqualifiedProcess
        }
        guard processClaimed, let runtime = retainedRuntime else { return false }
        return try await runtime.resumeFiles.removeOwnedCredential()
    }

    internal func preservingProcessResumeCleanupFailure(_ originalError: any Error) async -> any Error {
        guard preparesProcessResume || Self.processResumeMode == "resume-owned-once" else {
            return originalError
        }
        failClosed()
        do {
            _ = try await resumeFiles.removeOwnedCredential()
            return originalError
        } catch {
            return OriginalEditorQualificationBootstrapFailure(
                retainedRepositoryDirectory: retainedRepositoryDirectory,
                underlyingError: originalError, credentialCleanupError: error
            )
        }
    }

    internal static func resumeLocalOnlyAcceptance(
        request: OriginalEditorQualificationResumeRequest
    ) async throws -> OwnedOriginalEditorQualificationRuntime {
        guard ["org.otzaria.original-editor-qualification", "com.davidpovarsky.chavrusatext"]
                .contains(Bundle.main.bundleIdentifier ?? ""),
              ProcessInfo.processInfo.environment["OTZARIA_ORIGINAL_EDITOR_QUALIFICATION"] == "owned-local-only",
              processResumeMode == "resume-owned-once",
              InvocationDispatchContext.binding == nil, InvocationSettings.handler == nil else {
            throw OriginalEditorQualificationRuntimeError.unqualifiedProcess
        }
        guard !processClaimed else { throw OriginalEditorQualificationRuntimeError.alreadyClaimed }
        try request.validate()
        let manager = Container.shared.accountManager()
        let info = Container.shared.basicUserInfoStorage()
        guard manager is AccountManager, manager.account.id.isEmpty,
              let accountLifetime = manager.editorWriteLifetime else {
            throw OriginalEditorQualificationRuntimeError.existingAccount
        }
        processClaimed = true
        let files = OriginalEditorQualificationResumeFiles()
        var runtime: OwnedOriginalEditorQualificationRuntime?
        do {
            let original = Container.shared.localRepoService()
            let checkpoint = try await files.claim(request: request, original: original)
            try Task.checkCancellation()
            let groupDefaults = UserDefaults(suiteName: TargetsConstants.appGroup)
            for value in [UserDefaults.standard.object(forKey: "userId"),
                          groupDefaults?.object(forKey: "userId")] {
                guard value == nil || (value as? String)?.utf8.elementsEqual(checkpoint.accountID.utf8) == true else {
                    throw OriginalEditorQualificationRuntimeError.existingAccount
                }
            }
            guard manager.account.id.isEmpty,
                  info.usersId.utf8.elementsEqual(checkpoint.accountID.utf8) else {
                throw OriginalEditorQualificationRuntimeError.existingAccount
            }
            let owned = OwnedOriginalEditorQualificationRuntime(
                accountManager: manager, userInfo: info, accountLifetime: accountLifetime,
                runtimeNonce: checkpoint.runtimeNonce, preparesProcessResume: false, resumeFiles: files
            )
            runtime = owned
            retainedRuntime = owned
            owned.retainedRepositoryDirectory = try await files.parentDirectory(original: original)
            owned.fixtureRoleClaimed = true
            owned.restoreRoleClaimed = true
            try await owned.recover(checkpoint: checkpoint, original: original)
            return owned
        } catch {
            runtime?.failClosed()
            var cleanupError: (any Error)?
            do { try await files.removeOwnedCredential() } catch { cleanupError = error }
            throw OriginalEditorQualificationBootstrapFailure(
                retainedRepositoryDirectory: runtime?.retainedRepositoryDirectory,
                underlyingError: error, credentialCleanupError: cleanupError
            )
        }
    }

    private func recover(checkpoint: OriginalEditorQualificationResumeCheckpoint,
                         original: any LocalRepoServiceProtocol) async throws {
        let transition = EditorAccountWriteTransition(
            lifetime: accountLifetime, rpcNames: ["WalletRecover", "AccountSelect"]
        )
        defer { transition.finish() }
        try Task.checkCancellation()
        try await resumeFiles.validateRepository(checkpoint: checkpoint, original: original)
        let mnemonic = try await resumeFiles.consumeCredential(checkpoint: checkpoint)
        try Task.checkCancellation()
        guard accountManager.account.id.isEmpty,
              userInfo.usersId.utf8.elementsEqual(checkpoint.accountID.utf8) else {
            throw OriginalEditorQualificationRuntimeError.existingAccount
        }
        InvocationSettings.handler = invocationHandler
        let auth = Container.shared.authMiddleService()
        let repository = original.middlewareRepoURL
        let account = try await InvocationDispatchContext.$binding.withValue(transition.binding) {
            try await auth.originalEditorQualificationWalletRecovery(rootPath: repository.path, mnemonic: mnemonic)
            try Task.checkCancellation()
            return try await auth.originalEditorQualificationSelectAccount(
                id: checkpoint.accountID, rootPath: repository.path,
                networkMode: .localOnly, joinStreamUrl: "", configPath: nil,
                preferredSpaceId: checkpoint.spaceID
            )
        }
        try Task.checkCancellation()
        try await resumeFiles.validateRepository(checkpoint: checkpoint, original: original)
        guard account.id.utf8.elementsEqual(checkpoint.accountID.utf8),
              account.status == .active, !account.info.techSpaceId.isEmpty,
              accountManager.account.id.isEmpty,
              userInfo.usersId.utf8.elementsEqual(checkpoint.accountID.utf8) else {
            throw OriginalEditorQualificationRuntimeError.invalidNativeAccount
        }
        accountID = account.id
        accountManager.account = account
        Container.shared.middlewareConfigurationProvider().setupConfiguration(account: account)
        let expected = account.id
        let manager = accountManager
        let info = userInfo
        await transition.finishAndWaitForRelease {
            manager.account.id.utf8.elementsEqual(expected.utf8)
                && info.usersId.utf8.elementsEqual(expected.utf8)
        }
        try Task.checkCancellation()
        guard identityIsCurrent() else { throw OriginalEditorQualificationRuntimeError.invalidNativeAccount }
        let capturedAccount = try EditorDocumentWriteCapture(accountLifetime)
        accountCapture = capturedAccount
        guard let reservation = accountLifetime.admitOperation(capturedAccount.token) else {
            throw OriginalEditorQualificationRuntimeError.unavailableRuntime
        }
        accountReservation = reservation
        sourceBinding = try EditorDocumentWriteSourceBinding(
            lifetime: sourceLifetime, accountLifetime: accountLifetime,
            isCurrent: { [weak self] in self?.identityIsCurrent() == true }
        )
        try await InvocationDispatchContext.$binding.withValue(capturedAccount.accountDispatchBinding()) {
            middlewareListener.startListening()
            await spaces.startSubscription()
            await participants.startSubscription()
            try Task.checkCancellation()
        }
        try sourceBinding?.validate()
        phase = .ready
        try validateCurrentRuntime()
        try await openExistingResumeObject(checkpoint)
    }

    private func openExistingResumeObject(
        _ checkpoint: OriginalEditorQualificationResumeCheckpoint
    ) async throws {
        let service = workspaceService
        let opened = try await performRPCs(rpcNames: ["WorkspaceOpen"]) {
            try await service.workspaceOpenForOriginalSelection(
                spaceId: checkpoint.spaceID, withChat: false
            )
        }
        guard opened.accountSpaceId.utf8.elementsEqual(checkpoint.spaceID.utf8),
              !opened.spaceViewId.isEmpty, let accountCapture else {
            throw OriginalEditorQualificationRuntimeError.invalidNativeSpace
        }
        spaces.addSpaceInfo(spaceId: checkpoint.spaceID, info: opened)
        try await InvocationDispatchContext.$binding.withValue(accountCapture.accountDispatchBinding()) {
            await objectTypes.prepareData(spaceId: checkpoint.spaceID)
            await properties.prepareData(spaceId: checkpoint.spaceID)
            try Task.checkCancellation()
        }
        let page = try objectTypes.objectType(uniqueKey: .page, spaceId: checkpoint.spaceID)
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(15))
        while !participants.canEdit(spaceId: checkpoint.spaceID) {
            try validateCurrentRuntime()
            guard clock.now < deadline else {
                throw OriginalEditorQualificationRuntimeError.permissionReadinessTimeout
            }
            try await clock.sleep(for: .milliseconds(50))
        }
        try validateCurrentRuntime()
        let shown = try await performRPCs(rpcNames: ["ObjectShow"]) {
            try await ClientCommands.objectShow(.with {
                $0.contextID = checkpoint.objectID
                $0.objectID = checkpoint.objectID
                $0.spaceID = checkpoint.spaceID
            }).invoke()
        }
        guard shown.hasObjectView,
              shown.objectView.rootID.utf8.elementsEqual(checkpoint.objectID.utf8) else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
        }
        let roots = shown.objectView.details.filter { $0.id.utf8.elementsEqual(checkpoint.objectID.utf8) }
        guard roots.count == 1, roots[0].hasDetails,
              case .stringValue(let actualID)? = roots[0].details.fields["id"]?.kind,
              case .stringValue(let actualSpace)? = roots[0].details.fields["spaceId"]?.kind,
              case .listValue(let types)? = roots[0].details.fields["type"]?.kind,
              actualID.utf8.elementsEqual(checkpoint.objectID.utf8),
              actualSpace.utf8.elementsEqual(checkpoint.spaceID.utf8),
              types.values.count == 1,
              case .stringValue(let typeID)? = types.values[0].kind,
              typeID.utf8.elementsEqual(page.id.utf8) else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
        }
        for key in ["isDeleted", "isArchived"] {
            if let value = roots[0].details.fields[key] {
                guard case .boolValue(false)? = value.kind else {
                    throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
                }
            }
        }
        let evidence = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        try shown.serializedData().write(
            to: evidence.appendingPathComponent("original-process-resume-object-show.pb"),
            options: .withoutOverwriting
        )
        try Task.checkCancellation()
        try validateCurrentRuntime()
        recoveredCheckpoint = checkpoint
        recoveredEvidenceDirectory = evidence
        processResumeReceipt = checkpoint.receipt(credentialConsumed: true)
    }

    internal func prepareProcessResume(
        request: OriginalEditorQualificationResumeRequest,
        space: OwnedQualificationSpace, objectID: String
    ) async throws -> AnytypeOriginalEditorProcessResumeReceipt {
        try validateCurrentRuntime()
        try space.validateCurrentRuntime()
        guard preparesProcessResume, !processResumePrepared,
              restoreSpace === space, !operationInProgress, !spaceCreationInProgress else {
            throw OriginalEditorQualificationRuntimeError.resumeNotRequested
        }
        processResumePrepared = true
        let checkpoint = try await resumeFiles.seal(
            nonce: runtimeNonce, accountID: accountID, spaceID: space.spaceID,
            objectID: objectID, creationDigest: space.creationResponseSHA256,
            request: request, original: Container.shared.localRepoService()
        )
        try Task.checkCancellation()
        try validateCurrentRuntime()
        let receipt = checkpoint.receipt(credentialConsumed: false)
        processResumeReceipt = receipt
        return receipt
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

internal struct OriginalEditorQualificationResumeRequest: Codable, Sendable, Equatable {
    let workspaceNamespace: UUID
    let hostProfileID: String
    let annotationUUID: UUID
    let legacyAnnotationID: Int64
    let revision: Int64
    let sourceWitnessSHA256: String
    let payloadDigest: String
    let nativeArchiveSHA256: String
    let nativeBodySHA256: String

    init(source: AnytypeOriginalEditorQualificationSource,
         context: AnytypeOriginalEditorProcessResumeContext,
         snapshot: AnytypeOriginalEditorSnapshot) throws {
        workspaceNamespace = context.workspaceNamespace
        hostProfileID = source.hostProfileID
        annotationUUID = source.annotationUUID
        legacyAnnotationID = context.legacyAnnotationID
        revision = source.expectedRevision
        sourceWitnessSHA256 = source.sourceWitnessSHA256
        payloadDigest = context.payloadDigest
        nativeArchiveSHA256 = snapshot.nativeArchiveSHA256
        nativeBodySHA256 = SHA256.hash(data: snapshot.bodyBytes)
            .map { String(format: "%02x", $0) }.joined()
        try validate()
    }

    func validate() throws {
        guard UUID(uuidString: hostProfileID)?.uuidString == hostProfileID,
              legacyAnnotationID > 0, revision > 0,
              [sourceWitnessSHA256, payloadDigest, nativeArchiveSHA256, nativeBodySHA256].allSatisfy({
                  $0.utf8.count == 64
                      && $0.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) })
              }) else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
        }
    }
}

internal struct OriginalEditorQualificationResumeCheckpoint: Codable, Sendable {
    struct DirectoryIdentity: Codable, Sendable, Equatable {
        let device: Int64
        let inode: UInt64
    }

    let schema: String
    let runtimeNonce: UUID
    let bundleID: String
    let accountID: String
    let spaceID: String
    let objectID: String
    let spaceCreationResponseSHA256: String
    let preparedProcessID: Int32
    let parentIdentity: DirectoryIdentity
    let repositoryIdentity: DirectoryIdentity
    let accountRepositoryIdentity: DirectoryIdentity
    let request: OriginalEditorQualificationResumeRequest

    func validate() throws {
        try request.validate()
        guard schema == "original-editor-owned-process-resume/1",
              ["org.otzaria.original-editor-qualification", "com.davidpovarsky.chavrusatext"].contains(bundleID),
              [accountID, spaceID, objectID].allSatisfy(Self.validNativeComponent),
              preparedProcessID > 0, spaceCreationResponseSHA256.utf8.count == 64,
              spaceCreationResponseSHA256.utf8.allSatisfy({
                  (48...57).contains($0) || (97...102).contains($0)
              }) else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
        }
    }

    static func validNativeComponent(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 512 && value != "." && value != ".."
            && value.utf8.allSatisfy({
                (48...57).contains($0) || (65...90).contains($0)
                    || (97...122).contains($0) || $0 == 45 || $0 == 46 || $0 == 95
            })
    }

    func receipt(credentialConsumed: Bool) -> AnytypeOriginalEditorProcessResumeReceipt {
        .init(runtimeNonce: runtimeNonce, accountID: accountID,
              spaceID: spaceID, objectID: objectID,
              preparedProcessID: preparedProcessID,
              currentProcessID: ProcessInfo.processInfo.processIdentifier,
              credentialConsumed: credentialConsumed)
    }
}

private actor OriginalEditorQualificationResumeFiles {
    private let keychain = KeychainStore()
    private var ownedCredentialNonce: UUID?
    private var cleanupRequested = false
    private var cleanupResult: Result<Bool, any Error>?
    private let checkpointName = "OriginalEditorQualificationResume.json"
    private let attemptName = "OriginalEditorQualificationResumeAttempt.json"

    private func query(_ nonce: UUID) -> GenericPasswordQueryable {
        .init(account: nonce.uuidString,
              service: "org.otzaria.original-editor-qualification.wallet.v1",
              attrAccessible: .afterFirstUnlockThisDeviceOnly)
    }

    func storeCredential(_ mnemonic: String, nonce: UUID) throws {
        guard !cleanupRequested, ownedCredentialNonce == nil, !mnemonic.isEmpty,
              mnemonic.utf8.count <= 4_096 else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCredential
        }
        try keychain.addOriginalEditorQualificationItem(item: mnemonic, queryable: query(nonce))
        ownedCredentialNonce = nonce
        let stored = try keychain.retreiveItem(queryable: query(nonce))
        guard stored.utf8.elementsEqual(mnemonic.utf8) else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCredential
        }
    }

    @discardableResult
    func removeOwnedCredential() throws -> Bool {
        cleanupRequested = true
        if let cleanupResult { return try cleanupResult.get() }
        guard let nonce = ownedCredentialNonce else { return false }
        do {
            try keychain.removeItem(queryable: query(nonce))
            do {
                _ = try keychain.retreiveItem(queryable: query(nonce))
                throw OriginalEditorQualificationRuntimeError.resumeCredentialCleanupFailed
            } catch KeychainError.keychainError(let status) where status == errSecItemNotFound {
                cleanupResult = .success(true)
                return true
            }
        } catch {
            cleanupResult = .failure(error)
            throw error
        }
    }

    func consumeCredential(checkpoint: OriginalEditorQualificationResumeCheckpoint) throws -> String {
        guard !cleanupRequested, ownedCredentialNonce == checkpoint.runtimeNonce else {
            throw OriginalEditorQualificationRuntimeError.alreadyClaimed
        }
        let mnemonic = try keychain.retreiveItem(queryable: query(checkpoint.runtimeNonce))
        guard !mnemonic.isEmpty, mnemonic.utf8.count <= 4_096 else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCredential
        }
        try removeOwnedCredential()
        return mnemonic
    }

    func seal(nonce: UUID, accountID: String, spaceID: String, objectID: String,
              creationDigest: String, request: OriginalEditorQualificationResumeRequest,
              original: any LocalRepoServiceProtocol) throws -> OriginalEditorQualificationResumeCheckpoint {
        guard !cleanupRequested, ownedCredentialNonce == nonce,
              [accountID, spaceID, objectID].allSatisfy(OriginalEditorQualificationResumeCheckpoint.validNativeComponent) else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCredential
        }
        let paths = try repositoryPaths(original)
        try validateOriginalClaim(parent: paths.parent, nonce: nonce)
        let account = paths.repository.appendingPathComponent(accountID, isDirectory: true)
        let checkpoint = OriginalEditorQualificationResumeCheckpoint(
            schema: "original-editor-owned-process-resume/1", runtimeNonce: nonce,
            bundleID: Bundle.main.bundleIdentifier ?? "", accountID: accountID,
            spaceID: spaceID, objectID: objectID,
            spaceCreationResponseSHA256: creationDigest,
            preparedProcessID: ProcessInfo.processInfo.processIdentifier,
            parentIdentity: try directoryIdentity(paths.parent),
            repositoryIdentity: try directoryIdentity(paths.repository),
            accountRepositoryIdentity: try directoryIdentity(account), request: request
        )
        try checkpoint.validate()
        let data = try encode(checkpoint)
        guard data.count <= 32_768 else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
        }
        try writeExclusive(data, to: paths.parent.appendingPathComponent(checkpointName))
        return checkpoint
    }

    func claim(request: OriginalEditorQualificationResumeRequest,
               original: any LocalRepoServiceProtocol) throws -> OriginalEditorQualificationResumeCheckpoint {
        guard !cleanupRequested, ownedCredentialNonce == nil else {
            throw OriginalEditorQualificationRuntimeError.alreadyClaimed
        }
        let paths = try repositoryPaths(original)
        let data = try readRegular(paths.parent.appendingPathComponent(checkpointName), maximum: 32_768)
        let checkpoint = try JSONDecoder().decode(OriginalEditorQualificationResumeCheckpoint.self, from: data)
        try checkpoint.validate()
        guard try encode(checkpoint) == data,
              checkpoint.bundleID == Bundle.main.bundleIdentifier,
              checkpoint.request == request,
              checkpoint.preparedProcessID != ProcessInfo.processInfo.processIdentifier else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
        }
        try validateOriginalClaim(parent: paths.parent, nonce: checkpoint.runtimeNonce)
        try validateRepository(checkpoint: checkpoint, original: original)
        let receipt = try JSONSerialization.data(withJSONObject: [
            "schema": "original-editor-owned-process-resume-attempt/1",
            "runtimeNonce": checkpoint.runtimeNonce.uuidString,
            "preparedProcessID": checkpoint.preparedProcessID,
            "resumingProcessID": ProcessInfo.processInfo.processIdentifier
        ], options: [.sortedKeys])
        try writeExclusive(receipt, to: paths.parent.appendingPathComponent(attemptName))
        ownedCredentialNonce = checkpoint.runtimeNonce
        return checkpoint
    }

    func parentDirectory(original: any LocalRepoServiceProtocol) throws -> URL {
        try repositoryPaths(original).parent
    }

    func validateRepository(checkpoint: OriginalEditorQualificationResumeCheckpoint,
                            original: any LocalRepoServiceProtocol) throws {
        let paths = try repositoryPaths(original)
        guard try directoryIdentity(paths.parent) == checkpoint.parentIdentity,
              try directoryIdentity(paths.repository) == checkpoint.repositoryIdentity,
              try directoryIdentity(paths.repository.appendingPathComponent(checkpoint.accountID, isDirectory: true))
                == checkpoint.accountRepositoryIdentity else {
            throw OriginalEditorQualificationRuntimeError.existingRepository
        }
    }

    private func repositoryPaths(_ original: any LocalRepoServiceProtocol) throws -> (parent: URL, repository: URL) {
        let support = try FileManager.default.url(
            for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: false
        ).resolvingSymlinksInPath().standardizedFileURL
        let parent = support.appendingPathComponent("Anytype", isDirectory: true)
        _ = try directoryIdentity(parent)
        let expected = parent.appendingPathComponent("middleware-go", isDirectory: true)
        _ = try directoryIdentity(expected)
        let actual = original.middlewareRepoURL.standardizedFileURL
        guard actual.path.utf8.elementsEqual(expected.path.utf8) else {
            throw OriginalEditorQualificationRuntimeError.existingRepository
        }
        return (parent, actual)
    }

    private func directoryIdentity(_ url: URL) throws -> OriginalEditorQualificationResumeCheckpoint.DirectoryIdentity {
        let exact = url.standardizedFileURL
        guard exact.resolvingSymlinksInPath().path.utf8.elementsEqual(exact.path.utf8) else {
            throw OriginalEditorQualificationRuntimeError.existingRepository
        }
        var info = stat()
        guard Darwin.lstat(exact.path, &info) == 0,
              (info.st_mode & S_IFMT) == S_IFDIR, info.st_uid == getuid() else {
            throw OriginalEditorQualificationRuntimeError.existingRepository
        }
        return .init(device: Int64(info.st_dev), inode: UInt64(info.st_ino))
    }

    private func validateOriginalClaim(parent: URL, nonce: UUID) throws {
        let data = try readRegular(parent.appendingPathComponent("OriginalEditorQualificationClaim.json"), maximum: 4_096)
        guard let value = try JSONSerialization.jsonObject(with: data) as? [String: String],
              Set(value.keys) == ["runtimeNonce", "scope"],
              value["runtimeNonce"] == nonce.uuidString,
              value["scope"] == "fresh local-only original editor acceptance; no account reset or repository reuse" else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
        }
    }

    private func encode(_ checkpoint: OriginalEditorQualificationResumeCheckpoint) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(checkpoint)
    }

    private func readRegular(_ url: URL, maximum: Int) throws -> Data {
        let descriptor = Darwin.open(url.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard descriptor >= 0 else { throw OriginalEditorQualificationRuntimeError.fileSystemFailure(errno) }
        let file = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true)
        defer { try? file.close() }
        var info = stat()
        guard Darwin.fstat(descriptor, &info) == 0,
              (info.st_mode & S_IFMT) == S_IFREG, info.st_nlink == 1,
              info.st_uid == getuid(), info.st_size > 0, info.st_size <= maximum,
              let data = try file.read(upToCount: maximum + 1), data.count == info.st_size else {
            throw OriginalEditorQualificationRuntimeError.invalidResumeCheckpoint
        }
        return data
    }

    private func writeExclusive(_ data: Data, to url: URL) throws {
        let descriptor = Darwin.open(url.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard descriptor >= 0 else { throw OriginalEditorQualificationRuntimeError.fileSystemFailure(errno) }
        let file = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true)
        defer { try? file.close() }
        try file.write(contentsOf: data)
        try file.synchronize()
        try file.close()
    }
}

#endif
