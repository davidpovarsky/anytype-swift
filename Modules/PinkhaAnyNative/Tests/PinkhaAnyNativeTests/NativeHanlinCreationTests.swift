#if os(iOS)
import Foundation
import XCTest
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaAnyRuntime
import PinkhaAnyHanlin
import PinkhaHanlinCore
@testable import PinkhaAnyNative

/// Real linked AnyLib, original protected journals and the original Hanlin
/// catalog/router/approval/runner are exercised here. The presentation owner is
/// explicitly synthetic: this test does not certify a UIKit confirmation sheet.
@MainActor
final class NativeHanlinCreationTests: XCTestCase {
    func testRealProtectedHanlinCreationDenialCommitDuplicateAndRevocation() async throws {
        XCTAssertEqual(AnyEmbeddedBuild.linked, .pinkhaNativeV1,
                       "This test must run against the source-verified native contract.")
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("native-hanlin-proof-" + UUID().uuidString, isDirectory: true)
        let credentialService = "io.pinkha.hanlin.native.tests." + UUID().uuidString
        let application = try AnyNativeApplication(dataDirectory: directory, credentialService: credentialService)
        var accountID: String?
        var ownedSpaceID: String?
        var installedHost: AnyHanlinHost?
        do {
            try await application.start(network: .official)
            let account = try await application.createAccount()
            accountID = account.id
            try await application.acknowledgeRecoveryBackup(accountID: account.id)
            XCTAssertTrue(PinkhaHanlinAccountOwner.shared.isAvailable(account: account.id),
                          "The application, not each chat, must open the shared account owner.")
            let spaceID = try await application.createSpace(name: "Disposable native Hanlin acceptance")
            ownedSpaceID = spaceID
            let workspaceOwner = try await application.connectSpace(id: spaceID)
            let documents = try AnyEditorDocumentStore(
                client: workspaceOwner.client, workspace: workspaceOwner.workspace,
                allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
            let uiOwner = SyntheticHanlinCreationOwner(scope: .init(
                accountID: account.id, spaceID: spaceID, sceneID: UUID(), ownerID: UUID(),
                document: nil, selection: []))
            let creation = try AnyHanlinCreationServices(
                creator: workspaceOwner.objects,
                authority: AnyHanlinCreationAuthority(client: workspaceOwner.client,
                                                       workspace: workspaceOwner.workspace))
            let host = try AnyHanlinHost(native: workspaceOwner.session, documents: documents,
                owner: uiOwner, conversationID: UUID(), locale: Locale(identifier: "he"), creation: creation)
            installedHost = host
            let mounted = SyntheticHanlinOwnedChat(host: host)
            try PinkhaHanlinAccountOwner.shared.register(mounted)
            uiOwner.mounted = mounted
            try host.bindMountedPresentation(mounted)
            XCTAssertTrue(host.missingWriteInstallation.isEmpty)

            let catalog = try await host.catalog(for: host.session.context)
            XCTAssertEqual(catalog.tools.count, 1)
            XCTAssertEqual(catalog.tools.first?.route.alias, PinkhaHanlinCreatePagePlan.alias)
            XCTAssertEqual(catalog.tools.first?.writeGuarantee, .independentObjectCreation)
            XCTAssertEqual(uiOwner.readPromptCount, 0,
                           "Creating a new page must not silently grant source-text access.")
            let initialPages = try await pageIDs(workspaceOwner)
            let journal = try await PinkhaHanlinAccountOwner.shared.journal(
                for: host.session.context.namespace)

            uiOwner.answerMode = .deny
            let denied = try invocation(session: host.session, title: "Denied synthetic page")
            let deniedPlan = try PinkhaHanlinCreatePagePlan(invocation: denied)
            let deniedResult = try await host.execute(denied) { _ in }
            XCTAssertEqual(deniedResult.effectState, .notDispatched)
            let deniedEntry = try await journal.receipt(for: deniedPlan.identity)
            XCTAssertNil(deniedEntry, "Denial must not reserve a native creation attempt.")
            let afterDenied = try await pageIDs(workspaceOwner)
            XCTAssertEqual(afterDenied, initialPages)
            XCTAssertEqual(uiOwner.prompts.count, 1)
            XCTAssertEqual(uiOwner.prompts.first?.spaceID, spaceID)
            XCTAssertEqual(uiOwner.prompts.first?.title, deniedPlan.title)

            let title = "דף בדיקת Hanlin " + UUID().uuidString
            uiOwner.answerMode = .allow
            let approved = try invocation(session: host.session, title: title)
            let approvedPlan = try PinkhaHanlinCreatePagePlan(invocation: approved)
            let committed = try await host.execute(approved) { _ in }
            XCTAssertEqual(committed.effectState, .confirmedCommitted)
            XCTAssertEqual(committed.context, host.session.context)
            XCTAssertEqual(committed.reconciliationReference, approvedPlan.identity.key)
            guard case .completed(let contents) = committed.result.outcome else {
                throw HanlinHostError.resultMismatch
            }
            XCTAssertTrue(contents.isEmpty, "The SDK receives an opaque metadata receipt.")
            let committedEntryValue = try await journal.receipt(for: approvedPlan.identity)
            let committedEntry = try XCTUnwrap(committedEntryValue)
            XCTAssertEqual(committedEntry.effect, .committed)
            XCTAssertEqual(committedEntry.identity.session.context.namespace,
                           host.session.context.namespace)
            let createdID = try XCTUnwrap(committedEntry.createdObjectReference)
            let afterCommitted = try await pageIDs(workspaceOwner)
            XCTAssertEqual(afterCommitted.subtracting(initialPages), [createdID])
            XCTAssertTrue(initialPages.isSubset(of: afterCommitted))
            let created = try await workspaceOwner.session.perform { lease in
                try await documents.read(objectID: createdID, lease: lease)
            }
            XCTAssertEqual(created.snapshot.title, title)
            XCTAssertTrue(created.snapshot.blocks.isEmpty,
                          "The existing Hanlin capability creates only one titled Page, without body edits.")
            XCTAssertEqual(uiOwner.prompts.count, 2)
            XCTAssertEqual(uiOwner.prompts.last?.title, title)
            XCTAssertEqual(uiOwner.prompts.last?.spaceID, spaceID)
            XCTAssertEqual(uiOwner.readPromptCount, 0)

            let encodedReceipt = try JSONEncoder().encode(committedEntry)
            XCTAssertNil(encodedReceipt.range(of: Data(title.utf8)),
                         "Protected Hanlin metadata must not contain the business title.")
            let metadata = try XCTUnwrap(host.metadataReceipt(for: approved.request.id))
            XCTAssertEqual(metadata.effectState, .confirmedCommitted)
            guard case .completed(let metadataContents) = metadata.result.outcome else {
                throw HanlinHostError.resultMismatch
            }
            XCTAssertTrue(metadataContents.isEmpty)

            do {
                _ = try await host.execute(approved) { _ in }
                XCTFail("The same SDK invocation must never create a second page or prompt.")
            } catch let error as HanlinHostError {
                XCTAssertEqual(error, .duplicateInvocation)
            }
            let reminted = try invocation(session: host.session, title: title,
                runID: approved.runID, providerCallID: approved.providerCallID)
            do {
                _ = try await host.execute(reminted) { _ in }
                XCTFail("A reminted invocation cannot reuse an already claimed provider call.")
            } catch let error as HanlinHostError {
                XCTAssertEqual(error, .idempotencyConflict)
            }
            XCTAssertEqual(uiOwner.prompts.count, 2)
            let afterDuplicate = try await pageIDs(workspaceOwner)
            XCTAssertEqual(afterDuplicate, afterCommitted)

            // Delivering a queued Allow after its original source is revoked is
            // a denial, even though the native account still has writer rights.
            uiOwner.answerMode = .revokeBeforeAllow
            let stale = try invocation(session: host.session, title: "Revoked synthetic page")
            let stalePlan = try PinkhaHanlinCreatePagePlan(invocation: stale)
            do {
                let result = try await host.execute(stale) { _ in }
                XCTAssertEqual(result.effectState, .notDispatched)
            } catch let error as HanlinHostError {
                XCTAssertTrue(error == .staleContext || error == .cancelled,
                              "A revoked confirmation must fail at its original lifetime fence.")
            }
            let staleEntry = try await journal.receipt(for: stalePlan.identity)
            XCTAssertNil(staleEntry)
            let afterRevocation = try await pageIDs(workspaceOwner)
            XCTAssertEqual(afterRevocation, afterCommitted)
            XCTAssertEqual(host.metadataReceipt(for: approved.request.id)?.effectState, .confirmedCommitted,
                           "Revocation preserves the original committed metadata receipt.")
            await host.close()
            installedHost = nil
            try await application.signOut()
            XCTAssertFalse(PinkhaHanlinAccountOwner.shared.isAvailable(account: account.id))
            let retainedAfterLogout = try await journal.receipt(for: approvedPlan.identity)
            XCTAssertEqual(retainedAfterLogout, committedEntry,
                           "Ordinary logout must retain original protected Hanlin receipts.")
            let reopenedAccount = try await application.openSavedAccount(id: account.id)
            XCTAssertEqual(reopenedAccount.id, account.id)
            XCTAssertTrue(PinkhaHanlinAccountOwner.shared.isAvailable(account: account.id))
            let reopenedWorkspace = try await application.connectSpace(id: spaceID)
            let reopenedPages = try await pageIDs(reopenedWorkspace)
            XCTAssertEqual(reopenedPages, afterCommitted)
            let reusedJournal = try await PinkhaHanlinAccountOwner.shared.journal(
                for: host.session.context.namespace)
            let retainedAfterReopen = try await reusedJournal.receipt(for: approvedPlan.identity)
            XCTAssertEqual(retainedAfterReopen, committedEntry)
            try await application.deleteSpace(id: spaceID)
            ownedSpaceID = nil
            try await PinkhaHanlinAccountOwner.shared.closeAccount(account.id, removeData: true)
            try await application.signOut()
            try await application.removeSavedAccount(id: account.id)
            await application.stop()
            try await AnyProtectedCreationJournal.removeAccountData(accountID: account.id)
            try FileManager.default.removeItem(at: directory)
        } catch {
            await installedHost?.close()
            if let ownedSpaceID { try? await application.deleteSpace(id: ownedSpaceID) }
            await application.stop()
            if let accountID {
                try? await PinkhaHanlinAccountOwner.shared.closeAccount(accountID, removeData: true)
                try? AnyNativeCredentialVault(service: credentialService).remove(accountID: accountID)
                try? await AnyProtectedCreationJournal.removeAccountData(accountID: accountID)
            }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    private func invocation(
        session: HanlinHostSession, title: String,
        runID: UUID = UUID(), providerCallID: String = UUID().uuidString
    ) throws -> HanlinHostInvocation {
        try .init(request: .init(
            id: .init(validating: UUID().uuidString.lowercased()),
            logicalToolID: .init(providerInstanceID: .init(validating: "anytype.host"),
                                localToolID: .init(validating: "create-page")),
            aliasUsed: PinkhaHanlinCreatePagePlan.alias, descriptorRevision: .init(1),
            routingTableRevision: .init(1), arguments: .object(["title": .string(title)]),
            origin: .assistantModel, deadline: .now.addingTimeInterval(25),
            limits: .init(timeoutMilliseconds: 25_000, maximumOutputBytes: 32_768)),
            session: session, runID: runID, step: 0, providerCallID: providerCallID,
            writeGuarantee: .independentObjectCreation)
    }

    private func pageIDs(_ owner: AnyNativeWorkspaceOwner) async throws -> Set<String> {
        try await owner.session.perform { lease in
            let result = try await owner.client.requestJSON(method: "POST",
                path: ["v1", "spaces", owner.workspace.spaceID, "objects", "query"],
                body: .object([
                    "filter": .object(["any.type": .object(["$eq": .string("page")])]),
                    "limit": .integer(1_000), "includeTotal": .bool(true)
                ]), authorize: { try await lease.validate() })
            guard let records = result["records"]?.array,
                  result["total"]?.integer == Int64(records.count),
                  result["hasNext"]?.bool == false, records.count <= 1_000 else {
                throw HanlinHostError.resultMismatch
            }
            var identifiers = Set<String>()
            for record in records {
                guard let id = record["id"]?.string, !id.isEmpty,
                      record["spaceId"]?.string == owner.workspace.spaceID,
                      record["any"]?["type"]?.string == "page",
                      identifiers.insert(id).inserted else { throw HanlinHostError.resultMismatch }
            }
            try await lease.validate()
            return identifiers
        }
    }
}

@MainActor
private final class SyntheticHanlinOwnedChat: PinkhaHanlinOwnedPresentation {
    let session: HanlinHostSession
    private weak var host: AnyHanlinHost?
    private(set) var invalidated = false
    init(host: AnyHanlinHost) { self.host = host; self.session = host.session }
    func invalidate() { invalidated = true; host?.invalidate() }
}

@MainActor
private final class SyntheticHanlinCreationOwner: AnyHanlinCreationPresentationOwner {
    enum AnswerMode { case deny, allow, revokeBeforeAllow }
    let scope: AnyHanlinPresentationScope
    var answerMode = AnswerMode.deny
    weak var mounted: SyntheticHanlinOwnedChat?
    private(set) var prompts = [AnyHanlinCreatePagePrompt]()
    private(set) var readPromptCount = 0
    private var installedSession: HanlinHostSession?
    private var invalidate: (@Sendable () -> Void)?
    private var revoked = false

    init(scope: AnyHanlinPresentationScope) { self.scope = scope }
    func currentScope() throws -> AnyHanlinPresentationScope {
        guard !revoked else { throw HanlinHostError.staleContext }
        return scope
    }
    func install(session: HanlinHostSession, invalidate: @escaping @Sendable () -> Void) throws {
        guard installedSession == nil else { throw HanlinHostError.staleContext }
        installedSession = session
        self.invalidate = invalidate
    }
    func validateSDKPresentation(for session: HanlinHostSession) throws {
        _ = try currentScope()
        guard installedSession == session, let mounted, mounted.session == session,
              !mounted.invalidated, PinkhaHanlinAccountOwner.shared.owns(mounted) else {
            throw HanlinHostError.staleContext
        }
    }
    func presentCreatePageConfirmation(_ prompt: AnyHanlinCreatePagePrompt,
                                      answer: @escaping @MainActor (Bool) -> Void) throws {
        try validateSDKPresentation(for: prompt.session)
        guard prompt.spaceID == scope.spaceID else { throw HanlinHostError.staleContext }
        prompts.append(prompt)
        switch answerMode {
        case .deny: answer(false)
        case .allow: answer(true)
        case .revokeBeforeAllow:
            revoked = true
            invalidate?()
            answer(true)
        }
    }
    func presentReadConsent(context: HanlinHostContext,
                            answer: @escaping @MainActor (Bool) -> Void) throws {
        readPromptCount += 1
        answer(false)
    }
    func dismissPendingPrompts() {}
    func validateMounted(_ destination: HanlinHostDestination) throws {
        // No UIKit view is mounted by this integration fixture.
        throw HanlinHostError.denied
    }
}
#endif
