import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaHanlinCore
import HanlinHostContracts
@testable import PinkhaAnyRuntime
@testable import PinkhaAnyNative

@MainActor
final class NativeApplicationTests: XCTestCase {
    func testRealAccountWorkspaceJournalEditorAndColdReopen() async throws {
        XCTAssertEqual(AnyEmbeddedBuild.linked, .pinkhaNativeV1,
                       "This lane must link the source-verified patched Any library.")
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("native-app-proof-" + UUID().uuidString, isDirectory: true)
        let service = "io.pinkha.native.tests." + UUID().uuidString
        let application = try AnyNativeApplication(dataDirectory: directory, credentialService: service)
        var accountID: String?
        var ownedSpaceID: String?
        do {
            try await application.start(network: .official)
            let account = try await application.createAccount()
            accountID = account.id
            XCTAssertTrue(account.needsRecoveryBackup)
            XCTAssertTrue(PinkhaHanlinAccountOwner.shared.isAvailable(account: account.id))
            let recovery = try await application.recoveryPhrase(accountID: account.id)
            XCTAssertFalse(recovery.isEmpty)
            do {
                _ = try await application.listSpaces()
                XCTFail("New account cannot bypass recovery acknowledgement.")
            } catch let error as AnyNativeApplicationError {
                XCTAssertEqual(error, .recoveryBackupRequired)
            }
            try await application.acknowledgeRecoveryBackup(accountID: account.id)
            let spaceID = try await application.createSpace(name: "Disposable native iOS acceptance")
            ownedSpaceID = spaceID
            let spaces = try await application.listSpaces()
            XCTAssertTrue(spaces.contains { $0.id == spaceID && $0.ownRole == "owner" })
            let owner = try await application.connectSpace(id: spaceID)
            let intent = try AnyNativeObjectCreationIntent(
                workspace: owner.workspace, mutationID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                typeID: "page", initialProperties: .object(["any": .object(["name": .string("Native iOS Hebrew")])]))
            let pageID = try await owner.session.perform { lease in
                try await owner.objects.ensureObject(intent, authorize: { try await lease.validate() })
            }
            let blockIntent = try AnyNativeBlockCreationIntent(
                workspace: owner.workspace, mutationID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                objectID: pageID, type: "paragraph", text: "\u{05E9}\u{05DC}\u{05D5}\u{05DD} **native**",
                style: .object(["unknownFutureStyle": .string("preserve"),
                                "pinkhaWritingDirection": .string("rightToLeft")]),
                position: AnyLexicographicPosition.middle)
            let blockID = try await owner.session.perform { lease in
                try await owner.blocks.ensureBlock(blockIntent, authorize: { try await lease.validate() })
            }
            let editor = try AnyEditorDocumentStore(client: owner.client, workspace: owner.workspace,
                                                    allowedTypeIDs: owner.capabilities.allowedTargetTypes)
            let read = try await owner.session.perform { try await editor.read(objectID: pageID, lease: $0) }
            XCTAssertEqual(read.snapshot.blocks.first?.id, blockID)
            let prepared = try editor.prepareTextEdit(read, blockID: blockID, inlineMarkdown: "Updated native text")
            let receipt = try await owner.session.perform { try await editor.apply(prepared, lease: $0) }
            XCTAssertEqual(receipt.readback, .verifiedCurrent)
            let undo = try XCTUnwrap(receipt.undo)
            let undoReceipt = try await owner.session.perform { try await editor.apply(undo, lease: $0) }
            XCTAssertEqual(undoReceipt.readback, .verifiedCurrent)
            let restored = try await owner.session.perform { try await editor.read(objectID: pageID, lease: $0) }
            XCTAssertEqual(restored.snapshot.blocks.first?.native["style"]?["unknownFutureStyle"], .string("preserve"))
            let firstGeneration = owner.session.generation
            let hanlinLifetime = try NativeAccountLifetimeWitness(accountID: account.id, spaceID: spaceID)
            try PinkhaHanlinAccountOwner.shared.register(hanlinLifetime)
            defer { PinkhaHanlinAccountOwner.shared.unregister(hanlinLifetime.session.id) }
            await application.stop()
            XCTAssertTrue(hanlinLifetime.invalidated)
            XCTAssertFalse(PinkhaHanlinAccountOwner.shared.isAvailable(account: account.id))
            do {
                _ = try await owner.session.perform { try await editor.read(objectID: pageID, lease: $0) }
                XCTFail("A revoked workspace cannot deliver content after stop.")
            } catch let error as AnyHostError { XCTAssertEqual(error, .sessionClosed) }

            try await application.start(network: .official)
            let reopenedAccount = try await application.openSavedAccount(id: account.id)
            XCTAssertEqual(reopenedAccount.id, account.id)
            XCTAssertTrue(PinkhaHanlinAccountOwner.shared.isAvailable(account: account.id))
            XCTAssertTrue(hanlinLifetime.invalidated, "Reopening cannot rearm a revoked presentation.")
            XCTAssertFalse(reopenedAccount.needsRecoveryBackup)
            let reopened = try await application.connectSpace(id: spaceID)
            XCTAssertNotEqual(reopened.session.generation, firstGeneration)
            let retriedPage = try await reopened.session.perform { lease in
                try await reopened.objects.ensureObject(intent, authorize: { try await lease.validate() })
            }
            let retriedBlock = try await reopened.session.perform { lease in
                try await reopened.blocks.ensureBlock(blockIntent, authorize: { try await lease.validate() })
            }
            XCTAssertEqual(retriedPage, pageID)
            XCTAssertEqual(retriedBlock, blockID)
            let reopenedEditor = try AnyEditorDocumentStore(client: reopened.client, workspace: reopened.workspace,
                                                            allowedTypeIDs: reopened.capabilities.allowedTargetTypes)
            let final = try await reopened.session.perform { try await reopenedEditor.read(objectID: pageID, lease: $0) }
            XCTAssertEqual(final.snapshot.blocks.count, 1)
            XCTAssertEqual(final.snapshot.blocks.first?.id, blockID)
            try await application.deleteSpace(id: spaceID)
            ownedSpaceID = nil
            try await application.signOut()
            XCTAssertFalse(PinkhaHanlinAccountOwner.shared.isAvailable(account: account.id))
            try await application.removeSavedAccount(id: account.id)
            let remembered = try await application.savedAccounts()
            XCTAssertTrue(remembered.isEmpty)
            await application.stop()
            try await AnyProtectedCreationJournal.removeAccountData(accountID: account.id)
            try FileManager.default.removeItem(at: directory)
        } catch {
            if let ownedSpaceID { try? await application.deleteSpace(id: ownedSpaceID) }
            await application.stop()
            if let accountID {
                try? AnyNativeCredentialVault(service: service).remove(accountID: accountID)
                try? await AnyProtectedCreationJournal.removeAccountData(accountID: accountID)
            }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    func testPostAuthKeychainFailureRevokesNativeAuthorityAndRecoversSameAccount() async throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("native-keychain-fault-" + UUID().uuidString, isDirectory: true)
        let vault = try FailFirstSaveCredentialStore(service: "io.pinkha.vault.fault." + UUID().uuidString)
        let controlFault = FailSecondNativeAuthentication()
        let application = try AnyNativeApplication(dataDirectory: directory, testCredentialStore: vault,
            beforeNativeAuthentication: { try await controlFault.beforeRequest() })
        var accountID: String?
        do {
            try await application.start(network: .official)
            do {
                _ = try await application.createAccount()
                XCTFail("A failed secure save cannot report successful onboarding.")
            } catch let error as AnyNativeApplicationError {
                XCTAssertEqual(error, .secureStorageUnavailable)
            }
            let current = await application.currentAccount()
            XCTAssertNil(current)
            let pendingValue = await application.pendingRecoveryAccount()
            let pending = try XCTUnwrap(pendingValue)
            accountID = pending.id
            XCTAssertFalse(PinkhaHanlinAccountOwner.shared.isAvailable(account: pending.id))
            XCTAssertTrue(try vault.allMetadata().isEmpty)
            let secret = try await application.recoveryPhrase(accountID: pending.id)
            XCTAssertFalse(secret.isEmpty)
            let embeddedValue = await AnyEmbeddedRuntime.shared.currentSession()
            let embedded = try XCTUnwrap(embeddedValue)
            let (authBytes, authResponse) = try await URLSession.shared.data(for: embedded.authenticatedRead(path: "auth"))
            XCTAssertEqual((authResponse as? HTTPURLResponse)?.statusCode, 200)
            let nativeAuth = try JSONDecoder().decode(AnyJSON.self, from: authBytes)
            XCTAssertEqual(nativeAuth["authorized"], .bool(false))
            do {
                _ = try await application.listSpaces()
                XCTFail("Unsaved account cannot read or create documents.")
            } catch let error as AnyNativeApplicationError {
                XCTAssertEqual(error, .signedOut)
            }
            do {
                try await application.acknowledgeRecoveryBackup(accountID: pending.id + "-foreign")
                XCTFail("An unrelated backup screen cannot consume the pending credential.")
            } catch let error as AnyNativeApplicationError {
                XCTAssertEqual(error, .wrongAccount)
            }
            do {
                try await application.acknowledgeRecoveryBackup(accountID: pending.id)
                XCTFail("The injected native control failure must be reported after the secure save.")
            } catch let error as URLError {
                XCTAssertEqual(error.code, .networkConnectionLost)
            }
            let afterControlFailure = await application.currentAccount()
            let remainingPending = await application.pendingRecoveryAccount()
            XCTAssertNil(afterControlFailure)
            XCTAssertNil(remainingPending)
            let securelyAcknowledged = try vault.read(accountID: pending.id)
            XCTAssertFalse(securelyAcknowledged.needsRecoveryBackup)
            XCTAssertTrue(securelyAcknowledged.mnemonic.utf8.elementsEqual(secret.utf8))
            XCTAssertFalse(PinkhaHanlinAccountOwner.shared.isAvailable(account: pending.id))
            let afterFailureSession = await AnyEmbeddedRuntime.shared.currentSession()
            XCTAssertEqual(afterFailureSession?.generation, embedded.generation)
            let (failedAuthBytes, failedAuthResponse) = try await URLSession.shared.data(
                for: embedded.authenticatedRead(path: "auth"))
            XCTAssertEqual((failedAuthResponse as? HTTPURLResponse)?.statusCode, 200)
            let failedAuth = try JSONDecoder().decode(AnyJSON.self, from: failedAuthBytes)
            XCTAssertEqual(failedAuth["authorized"], .bool(false))
            // Retry directly from the same backup action, with no stop/restart.
            try await application.acknowledgeRecoveryBackup(accountID: pending.id)
            let attempts = await controlFault.attempts
            XCTAssertEqual(attempts, 3)
            let recovered = await application.currentAccount()
            XCTAssertEqual(recovered?.id, pending.id)
            XCTAssertEqual(recovered?.needsRecoveryBackup, false)
            XCTAssertTrue(PinkhaHanlinAccountOwner.shared.isAvailable(account: pending.id))
            let recoveredEmbedded = await AnyEmbeddedRuntime.shared.currentSession()
            XCTAssertEqual(recoveredEmbedded?.generation, embedded.generation)
            let remaining = await application.pendingRecoveryAccount()
            XCTAssertNil(remaining)
            XCTAssertTrue(try vault.read(accountID: pending.id).mnemonic.utf8.elementsEqual(secret.utf8))
            let client = try embedded.dataClient(expectedAccountID: pending.id)
            let authorized = try await client.requestJSON(method: "GET", path: ["v1", "auth"])
            XCTAssertEqual(authorized["authorized"], .bool(true))
            XCTAssertEqual(authorized["accountId"], .string(pending.id))
            await application.stop()
            try vault.remove(accountID: pending.id)
            try FileManager.default.removeItem(at: directory)
        } catch {
            await application.stop()
            if let accountID { try? vault.remove(accountID: accountID) }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    func testRealKeychainNamespaceAndRecoveryMetadataIsolation() throws {
        let id = "A" + UUID().uuidString.replacingOccurrences(of: "-", with: "")
        let one = try AnyNativeCredentialVault(service: "io.pinkha.vault.test.one." + UUID().uuidString)
        let two = try AnyNativeCredentialVault(service: "io.pinkha.vault.test.two." + UUID().uuidString)
        let credential = AnyNativeCredential(version: 1, accountID: id, derivationIndex: 1,
            mnemonic: "synthetic non-wallet fixture", needsRecoveryBackup: true)
        defer { try? one.remove(accountID: id); try? two.remove(accountID: id) }
        try one.save(credential)
        XCTAssertEqual(try one.allMetadata().map(\.id), [id])
        XCTAssertTrue(try two.allMetadata().isEmpty)
        XCTAssertThrowsError(try two.read(accountID: id))
        XCTAssertTrue(try one.read(accountID: id).needsRecoveryBackup)
        XCTAssertEqual(String(describing: credential), "AnyNativeCredential(redacted)")
        XCTAssertEqual(String(reflecting: credential), "AnyNativeCredential(redacted)")
    }
}

private final class FailFirstSaveCredentialStore: AnyNativeCredentialStoring, @unchecked Sendable {
    private let lock = NSLock()
    private var rejectNextSave = true
    private let actual: AnyNativeCredentialVault
    init(service: String) throws { actual = try .init(service: service) }
    func allMetadata() throws -> [AnyNativeAccount] { try actual.allMetadata() }
    func read(accountID: String) throws -> AnyNativeCredential { try actual.read(accountID: accountID) }
    func remove(accountID: String) throws { try actual.remove(accountID: accountID) }
    func save(_ credential: AnyNativeCredential) throws {
        let refuse = lock.withLock {
            let value = rejectNextSave
            rejectNextSave = false
            return value
        }
        if refuse { throw AnyNativeVaultError.unavailable(-25291) }
        try actual.save(credential)
    }
}

private actor FailSecondNativeAuthentication {
    private(set) var attempts = 0
    func beforeRequest() throws {
        attempts += 1
        if attempts == 2 { throw URLError(.networkConnectionLost) }
    }
}

@MainActor
private final class NativeAccountLifetimeWitness: PinkhaHanlinOwnedPresentation {
    let session: HanlinHostSession
    private(set) var invalidated = false
    init(accountID: String, spaceID: String) throws {
        let namespace = try HanlinConversationNamespace(app: "anytype", account: accountID,
                                                        workspace: spaceID, space: spaceID)
        self.session = .init(conversationID: UUID(), context: .init(namespace: namespace,
            sceneID: UUID(), generation: UUID(), objectReference: nil,
            selectionReferences: [], sourceRevision: nil, localeIdentifier: "en"))
    }
    func invalidate() { invalidated = true }
}
