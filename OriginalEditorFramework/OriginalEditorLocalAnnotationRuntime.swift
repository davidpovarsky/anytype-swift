import Foundation
import CryptoKit
import UIKit
import AnytypeCore
@_spi(OriginalEditorLocalAnnotation) import Services
import ProtobufMessages
import SwiftProtobuf

/// One retained original localOnly account. It never borrows an already running
/// account/handler, installs a replacement engine, or makes a remote Space.
@MainActor
internal final class OriginalEditorLocalAnnotationRuntime {
    private enum Phase { case starting, ready, failed }
    private static var claimed = false
    private static var retained: OriginalEditorLocalAnnotationRuntime?
    private let appGroup: String
    private let journal: OriginalEditorLocalAnnotationJournal
    private let accountManager: any AccountManagerProtocol
    private let userInfo: any BasicUserInfoStorageProtocol
    private let accountLifetime: EditorDocumentWriteLifetime
    private let lifetime = EditorDocumentWriteLifetime()
    private let listener = MiddlewareEventsListener()
    private let handler = InvocationMesagesHandler()
    private var accountCapture: EditorDocumentWriteCapture?
    private var accountReservation: EditorDocumentWriteLifetime.Observation?
    private var runtimeBinding: EditorDocumentWriteSourceBinding?
    private var phase = Phase.starting
    private var opening = false
    private var accountID = ""
    private var currentOwner: OriginalEditorLocalAnnotationDraftOwner?

    private init(appGroup: String, journal: OriginalEditorLocalAnnotationJournal,
                 accountManager: any AccountManagerProtocol,
                 userInfo: any BasicUserInfoStorageProtocol,
                 accountLifetime: EditorDocumentWriteLifetime) {
        self.appGroup = appGroup
        self.journal = journal
        self.accountManager = accountManager
        self.userInfo = userInfo
        self.accountLifetime = accountLifetime
    }

    static func acquire(appGroup: String) async throws -> OriginalEditorLocalAnnotationRuntime {
        if let retained {
            guard retained.appGroup == appGroup else {
                throw AnytypeOriginalEditorLocalAnnotationError.incompatibleDeployment
            }
            try retained.validate()
            return retained
        }
        guard !claimed, InvocationSettings.handler == nil, InvocationDispatchContext.binding == nil else {
            throw AnytypeOriginalEditorLocalAnnotationError.runtimeAlreadyOwned
        }
        _ = try AnytypeOriginalEditorModule.inspectResources()
        #if DEBUG || RELEASE_NIGHTLY
        try OriginalRuntimeEnvironment.configureEmbedded(appGroup: appGroup, expectedTarget: .debug)
        #elseif RELEASE_ANYTYPE
        try OriginalRuntimeEnvironment.configureEmbedded(appGroup: appGroup, expectedTarget: .releaseAnytype)
        #else
        throw AnytypeOriginalEditorLocalAnnotationError.incompatibleDeployment
        #endif
        // Claim before any await. A cancelled bootstrap never opens a second
        // account in this process; the original native call may still be running.
        claimed = true
        let journal = try await Task.detached {
            try OriginalEditorLocalAnnotationJournal.open(appGroup: appGroup)
        }.value
        let manager = Container.shared.accountManager()
        let info = Container.shared.basicUserInfoStorage()
        guard let accountLifetime = manager.editorWriteLifetime else {
            throw AnytypeOriginalEditorLocalAnnotationError.originalServiceUnavailable
        }
        let runtime = OriginalEditorLocalAnnotationRuntime(appGroup: appGroup, journal: journal,
            accountManager: manager, userInfo: info, accountLifetime: accountLifetime)
        retained = runtime
        do {
            try await runtime.bootstrap()
            return runtime
        } catch {
            runtime.failClosed()
            throw error
        }
    }

    private func bootstrap() async throws {
        let observation = try await journal.accountObservation()
        let recovering = ["account_observed", "ready"].contains(observation.phase)
        guard accountManager.account.id.isEmpty,
              userInfo.usersId.isEmpty || (recovering
                    && userInfo.usersId == observation.accountID) else {
            throw AnytypeOriginalEditorLocalAnnotationError.runtimeAlreadyOwned
        }
        let originalRepo = Container.shared.localRepoService().middlewareRepoURL
        try await journal.requireRepository(originalRepo)
        guard recovering || observation.phase == "claimed" else {
            // Missing durable identity after a possible AccountCreate is not
            // permission to call it again or to replace the original repository.
            throw AnytypeOriginalEditorLocalAnnotationError.uncertainNativeOperation
        }
        let transition = EditorAccountWriteTransition(lifetime: accountLifetime,
            rpcNames: recovering ? ["WalletRecover", "AccountSelect"] : ["WalletCreate", "AccountCreate"])
        defer { transition.finish() }
        InvocationSettings.handler = handler
        let auth = Container.shared.authMiddleService()
        let account: AccountData
        if recovering {
            guard let id = observation.accountID else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
            let mnemonic = try await journal.credential()
            account = try await InvocationDispatchContext.$binding.withValue(transition.binding) {
                try await auth.originalLocalAnnotationRecoverWallet(rootPath: originalRepo.path, mnemonic: mnemonic)
                try Task.checkCancellation()
                return try await auth.originalLocalAnnotationSelectAccount(
                    id: id, rootPath: originalRepo.path, preferredSpaceID: observation.preferredSpaceID ?? "")
            }
            guard account.id.utf8.elementsEqual(id.utf8) else {
                throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount
            }
        } else {
            _ = try await journal.prepareWallet()
            account = try await InvocationDispatchContext.$binding.withValue(transition.binding) {
                let mnemonic = try await auth.originalLocalAnnotationCreateWallet(rootPath: originalRepo.path)
                try await journal.retainCredential(mnemonic)
                try Task.checkCancellation()
                try await journal.prepareAccount()
                let created = try await auth.originalLocalAnnotationCreateAccount()
                guard !created.id.isEmpty, created.status == .active, !created.info.techSpaceId.isEmpty else {
                    throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount
                }
                // A successful original response is persisted before later UI
                // cancellation/readiness checks. Relaunch selects this account;
                // it never repeats AccountCreate or an uncertain WorkspaceCreate.
                try await journal.observeCreatedAccount(accountID: created.id,
                    preferredSpaceID: created.info.accountSpaceId)
                return created
            }
        }
        guard !account.id.isEmpty, account.status == .active,
              !account.info.techSpaceId.isEmpty,
              accountManager.account.id.isEmpty else {
            throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount
        }
        accountID = account.id
        userInfo.usersId = account.id
        accountManager.account = account
        Container.shared.middlewareConfigurationProvider().setupConfiguration(account: account)
        let expected = accountID, manager = accountManager, info = userInfo
        await transition.finishAndWaitForRelease {
            manager.account.id.utf8.elementsEqual(expected.utf8)
                && info.usersId.utf8.elementsEqual(expected.utf8)
        }
        try Task.checkCancellation()
        let capture = try EditorDocumentWriteCapture(accountLifetime)
        accountCapture = capture
        guard let reservation = accountLifetime.admitOperation(capture.token) else {
            throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount
        }
        accountReservation = reservation
        runtimeBinding = try EditorDocumentWriteSourceBinding(lifetime: lifetime,
            accountLifetime: accountLifetime, isCurrent: { [weak self] in self?.identityIsCurrent() == true })
        let spaces = Container.shared.spaceViewsStorage()
        let participants = Container.shared.participantsStorage()
        try await InvocationDispatchContext.$binding.withValue(capture.accountDispatchBinding()) {
            listener.startListening()
            await spaces.startSubscription()
            await participants.startSubscription()
            try Task.checkCancellation()
        }
        phase = .ready
        try validate()
        try await journal.markAccountReady(accountID: accountID)
        try await journal.requireRepository(originalRepo)
    }

    private func identityIsCurrent() -> Bool {
        phase != .failed && !accountID.isEmpty
            && accountManager.account.id.utf8.elementsEqual(accountID.utf8)
            && userInfo.usersId.utf8.elementsEqual(accountID.utf8)
            && InvocationSettings.handler === handler
    }

    internal func validate() throws {
        guard phase == .ready, identityIsCurrent(), let runtimeBinding else {
            throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount
        }
        try runtimeBinding.validate()
    }

    private func failClosed() {
        phase = .failed
        lifetime.markUnavailable()
        // Retain handler/account/native admissions and original repository.
        // Retirement is not evidence of rollback or completion of a native call.
    }

    private func createPrivateSpace(name: String) async throws -> AccountInfo {
        try validate()
        guard let runtimeBinding else { throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount }
        let service = Container.shared.workspaceService()
        let opened = try await runtimeBinding.performOperation(rpcNames: ["WorkspaceCreate", "WorkspaceOpen"]) {
            let created = try await service.createSpace(name: name, iconOption: 0, accessType: .private,
                useCase: .none, withChat: false, spaceType: .regular)
            guard !created.spaceID.isEmpty else { throw AnytypeOriginalEditorLocalAnnotationError.unavailableSpace }
            let result = try await service.workspaceOpen(spaceId: created.spaceID, withChat: false)
            guard result.accountSpaceId == created.spaceID, !result.spaceViewId.isEmpty else {
                throw AnytypeOriginalEditorLocalAnnotationError.unavailableSpace
            }
            return result
        }
        try validate()
        Container.shared.spaceViewsStorage().addSpaceInfo(spaceId: opened.accountSpaceId, info: opened)
        guard let capture = accountCapture else { throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount }
        try await InvocationDispatchContext.$binding.withValue(capture.accountDispatchBinding()) {
            await Container.shared.objectTypeProvider().prepareData(spaceId: opened.accountSpaceId)
            await Container.shared.propertyDetailsStorage().prepareData(spaceId: opened.accountSpaceId)
        }
        return opened
    }

    internal func open(sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
                       canonical: OriginalEditorLocalAnnotationCanonical,
                       sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool)
        async throws -> OriginalEditorLocalAnnotationDraftOwner {
        try validate()
        guard !opening, currentOwner?.isCurrent != true else {
            throw AnytypeOriginalEditorLocalAnnotationError.overlappingSession
        }
        opening = true
        defer { opening = false }
        let source = sourceLifetime.source
        let check: @MainActor () throws -> Void = { [self] in
            try validate()
            guard sourceLifetime.isCurrent, sourceIsCurrent(source) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
        }
        try check()
        var draft = try await journal.beginDraft(source: source, canonicalSHA256: canonical.digest)
        do {
            draft = try await journal.transition(draft, to: "space_may_have_dispatched")
            try check()
            let space = try await createPrivateSpace(name: "Local annotation " + draft.attempt.uuidString)
            draft = try await journal.transition(draft, to: "space_observed",
                spaceID: space.accountSpaceId, spaceViewID: space.spaceViewId)
            try check()
            let selected = try await prepareSelectedSpace(space.accountSpaceId)
            try check()
            let prepared = try sourceBinding(sourceLifetime, selection: selected.selection,
                                            sourceIsCurrent: sourceIsCurrent)
            draft = try await journal.transition(draft, to: "materialization_may_have_dispatched")
            try check()
            let materialized = try await OriginalEditorLocalAnnotationMaterialization.materialize(
                canonical: canonical, source: source, draft: draft, accountID: accountID,
                selection: selected.selection, annotationTypeID: selected.typeID,
                binding: prepared, sourceIsCurrent: check)
            // The materializer requires actual typed drain and fresh ObjectShow.
            // Neither ObjectCreate's returned ID nor an empty index is a mapping.
            draft = try await journal.transition(draft, to: "object_observed", objectID: materialized)
            try check()
            let editorBinding = try AnytypeOriginalEditorBinding(accountID: accountID,
                spaceID: space.accountSpaceId, objectID: materialized, hostProfileID: source.hostProfileID,
                annotationUUID: source.annotationUUID, expectedRevision: source.expectedRevision,
                sourceWitnessSHA256: source.sourceWitnessSHA256)
            let originalSource = AnytypeOriginalEditorSourceLifetime(binding: editorBinding)
            let retirement = sourceLifetime.lifetime.observe(try EditorDocumentWriteCapture(sourceLifetime.lifetime).token) {
                originalSource.retire()
            }
            let host = try await AnytypeOriginalEditorModule.openExistingEditor(
                binding: editorBinding, sourceLifetime: originalSource
            ) { candidate in
                candidate == editorBinding && sourceLifetime.isCurrent && sourceIsCurrent(source)
            }
            try check()
            draft = try await journal.transition(draft, to: "opened")
            let owner = OriginalEditorLocalAnnotationDraftOwner(host: host, sourceLifetime: sourceLifetime,
                journal: journal, draft: draft, retirement: retirement,
                sourceIsCurrent: sourceIsCurrent, runtime: self)
            currentOwner = owner
            return owner
        } catch {
            // Unknown native effects are retained. A new process may reconstruct
            // canonical bytes in a fresh private Space; this process never retries
            // or treats the failed attempt as absent/rolled back.
            failClosed()
            throw error
        }
    }

    private func prepareSelectedSpace(_ spaceID: String) async throws
        -> (selection: OriginalActiveSpaceSelection, typeID: String) {
        try validate()
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(20))
        while !Container.shared.participantsStorage().canEdit(spaceId: spaceID) {
            try validate()
            guard clock.now < deadline else { throw AnytypeOriginalEditorLocalAnnotationError.unavailableSpace }
            try await clock.sleep(for: .milliseconds(50))
        }
        guard let manager = Container.shared.activeSpaceManager() as? ActiveSpaceManager else {
            throw AnytypeOriginalEditorLocalAnnotationError.originalServiceUnavailable
        }
        _ = try await manager.setActiveSpace(spaceId: spaceID)
        let selection = try manager.currentOriginalActiveSpaceSelection()
        try selection.validate()
        guard selection.accountID == accountID, selection.accountInfo.accountSpaceId == spaceID else {
            throw AnytypeOriginalEditorLocalAnnotationError.unavailableSpace
        }
        let observed = OriginalEditorLocalSchemaHistory()
        let response = try await selection.registerOriginalAnnotationSchema { observed.record($0) }
        try selection.validate()
        guard observed.count == 1, let history = observed.history, history.copyError == nil,
              history.response == response, response.error.code == .null,
              response.hasRegistration, response.registration.appAdmitted,
              response.registration.schemaProtocol == OriginalAnnotationNativeMetadata.protocolValue,
              response.registration.hasObservation,
              response.registration.observation.disposition == "MATCHING_SCHEMA_OBSERVED",
              response.registration.observation.accountIdentity == accountID,
              response.registration.observation.spaceID == spaceID,
              response.registration.observation.hasTypeLayout,
              response.registration.observation.typeLayout.disposition == "MATCHING_SCHEMA_OBSERVED" else {
            throw AnytypeOriginalEditorLocalAnnotationError.unobservedSchema
        }
        let types = response.registration.observation.definitions.filter {
            $0.hasNative && $0.native.nativeKey == OriginalAnnotationNativeMetadata.originalTypeUniqueKey
        }
        guard types.count == 1, let type = types.first?.native, !type.objectID.isEmpty,
              type.accountIdentity == accountID, type.spaceID == spaceID, type.hasDetails,
              OriginalEditorLocalAnnotationNativeBody.string(type.details, "id") == type.objectID,
              OriginalEditorLocalAnnotationNativeBody.string(type.details, "uniqueKey")
                == OriginalAnnotationNativeMetadata.originalTypeUniqueKey else {
            throw AnytypeOriginalEditorLocalAnnotationError.unobservedSchema
        }
        return (selection, type.objectID)
    }

    private func sourceBinding(_ source: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
                               selection: OriginalActiveSpaceSelection,
                               sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool)
        throws -> EditorDocumentWriteSourceBinding {
        try validate()
        guard let accountCapture,
              let participants = Container.shared.participantsStorage() as? ParticipantsStorage,
              let spaces = Container.shared.spaceViewsStorage() as? SpaceViewsStorage else {
            throw AnytypeOriginalEditorLocalAnnotationError.originalServiceUnavailable
        }
        let spaceID = selection.accountInfo.accountSpaceId
        let participant = try participants.currentParticipantEditPermission(spaceId: spaceID)
        let space = try spaces.currentOriginalSpaceViewPermission(spaceId: spaceID)
        let captures = [accountCapture,
            try selection.capture(matching: accountCapture, spaceId: spaceID),
            try participant.capture(matching: accountCapture, spaceId: spaceID),
            try space.capture(matching: accountCapture, spaceId: spaceID),
            try EditorDocumentWriteCapture(lifetime)]
        let binding = try EditorDocumentWriteSourceBinding(lifetime: source.lifetime,
            accountLifetime: accountLifetime, additionalLifetimes: captures.map(\.source), isCurrent: { [weak self] in
                self?.identityIsCurrent() == true && source.isCurrent && sourceIsCurrent(source.source)
            })
        for capture in captures {
            try capture.validate()
            guard binding.captures.contains(where: { $0.source === capture.source && $0.token == capture.token }) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
        }
        return try binding.requiringSpaceEditPermission(participant: participant, spaceView: space, spaceId: spaceID)
    }
}

@MainActor
private final class OriginalEditorLocalSchemaHistory {
    private(set) var count = 0
    private(set) var history: OriginalAnnotationSchemaCallHistory?
    func record(_ value: OriginalAnnotationSchemaCallHistory) { count += 1; history = value }
}

@MainActor
internal final class OriginalEditorLocalAnnotationDraftOwner {
    let host: AnytypeOriginalEditorHost
    nonisolated let sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime
    private var source: AnytypeOriginalEditorLocalAnnotationSourceLifetime { sourceLifetime }
    private let journal: OriginalEditorLocalAnnotationJournal
    private var draft: OriginalEditorLocalAnnotationJournal.Draft
    private let retirement: EditorDocumentWriteLifetime.Observation
    private let sourceIsCurrent: @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool
    private let runtime: OriginalEditorLocalAnnotationRuntime
    private var captureAttempted = false

    init(host: AnytypeOriginalEditorHost, sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
         journal: OriginalEditorLocalAnnotationJournal, draft: OriginalEditorLocalAnnotationJournal.Draft,
         retirement: EditorDocumentWriteLifetime.Observation,
         sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool,
         runtime: OriginalEditorLocalAnnotationRuntime) {
        self.host = host; self.sourceLifetime = sourceLifetime; self.journal = journal; self.draft = draft
        self.retirement = retirement; self.sourceIsCurrent = sourceIsCurrent; self.runtime = runtime
    }

    var isCurrent: Bool { source.isCurrent }
    func validateCurrent() throws {
        try runtime.validate()
        guard source.isCurrent, sourceIsCurrent(source.source) else {
            throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
        }
    }

    func capture(maximumBodyBytes: Int) async throws -> AnytypeOriginalEditorLocalAnnotationCapture {
        try validateCurrent()
        guard !captureAttempted else { throw AnytypeOriginalEditorLocalAnnotationError.captureAlreadyAttempted }
        captureAttempted = true
        draft = try await journal.transition(draft, to: "capture_started")
        try validateCurrent()
        let native = try await host.captureNativeSnapshot(maximumBodyBytes: maximumBodyBytes)
        guard native.snapshot.provenance.matchesCaptureBinding(host.binding) else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
        let preview = try OriginalEditorLocalAnnotationNativeBody.preview(native.snapshot, source: source.source)
        draft = try await journal.transition(draft, to: "captured",
            captureSHA256: OriginalEditorLocalAnnotationValidation.sha256(native.snapshot.bodyBytes),
            archiveSHA256: native.snapshot.nativeArchiveSHA256)
        // Capture terminally retired the separate native editor. The Host source
        // remains current through its original SQLite CAS and is retired by that
        // owner afterwards. This history is neither a saved-row commit nor ACK.
        return .init(nativeCapture: native, textPreview: preview)
    }

    func retire() {
        source.retire()
        host.retire()
    }
}
