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
    private enum Phase { case starting, ready, stopping, stopped, failed, stopFailed }
    private static var claimed = false
    private static var retained: OriginalEditorLocalAnnotationRuntime?
    private let appGroup: String
    private let journal: OriginalEditorLocalAnnotationJournal
    private let accountManager: any AccountManagerProtocol
    private let userInfo: any BasicUserInfoStorageProtocol
    private let authMiddleService: any AuthMiddleServiceProtocol
    private let accountLifetime: EditorDocumentWriteLifetime
    private let lifetime = EditorDocumentWriteLifetime()
    private let process: OriginalEditorEmbeddedAccountProcess
    private let processLease: OriginalEditorLocalAccountLease
    private var stopTask: Task<Void, Error>?
    private var accountCapture: EditorDocumentWriteCapture?
    private var accountReservation: EditorDocumentWriteLifetime.Observation?
    private var runtimeBinding: EditorDocumentWriteSourceBinding?
    private var phase = Phase.starting
    private var opening = false
    private var accountID = ""
    private var currentOwner: OriginalEditorLocalAnnotationDraftOwner?
    private var currentBatch: OriginalEditorLocalAnnotationBatchOwner?

    private init(appGroup: String, journal: OriginalEditorLocalAnnotationJournal,
                 accountManager: any AccountManagerProtocol,
                 userInfo: any BasicUserInfoStorageProtocol,
                 accountLifetime: EditorDocumentWriteLifetime,
                 process: OriginalEditorEmbeddedAccountProcess,
                 processLease: OriginalEditorLocalAccountLease) {
        self.appGroup = appGroup
        self.journal = journal
        self.accountManager = accountManager
        self.userInfo = userInfo
        authMiddleService = Container.shared.authMiddleService()
        self.accountLifetime = accountLifetime
        self.process = process
        self.processLease = processLease
    }

    static func acquire(appGroup: String) async throws -> OriginalEditorLocalAnnotationRuntime {
        if let retained {
            guard retained.appGroup == appGroup else {
                throw AnytypeOriginalEditorLocalAnnotationError.incompatibleDeployment
            }
            try retained.validate()
            return retained
        }
        guard !claimed, InvocationDispatchContext.binding == nil else {
            throw AnytypeOriginalEditorLocalAnnotationError.runtimeAlreadyOwned
        }
        let process = try OriginalEditorEmbeddedAccountProcess.acquire(appGroup: appGroup)
        try await process.initializeMiddleware()
        let lease = try process.claimLocalAccount()
        // Reserve the original process before the first await. The original
        // account presentation and localOnly editor can never overlap.
        claimed = true
        let journal: OriginalEditorLocalAnnotationJournal
        do {
            journal = try await Task.detached {
                try OriginalEditorLocalAnnotationJournal.open(appGroup: appGroup)
            }.value
        } catch {
            // Journal opening dispatched no native account operation. This
            // unused reservation can be released without an AccountStop.
            try process.releaseLocalAccount(lease)
            claimed = false
            throw error
        }
        let manager = Container.shared.accountManager()
        let info = Container.shared.basicUserInfoStorage()
        guard let accountLifetime = manager.editorWriteLifetime else {
            throw AnytypeOriginalEditorLocalAnnotationError.originalServiceUnavailable
        }
        let runtime = OriginalEditorLocalAnnotationRuntime(appGroup: appGroup, journal: journal,
            accountManager: manager, userInfo: info, accountLifetime: accountLifetime,
            process: process, processLease: lease)
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
        let auth = authMiddleService
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
        (phase == .starting || phase == .ready) && !accountID.isEmpty
            && accountManager.account.id.utf8.elementsEqual(accountID.utf8)
            && userInfo.usersId.utf8.elementsEqual(accountID.utf8)
            && (try? process.validateLocalAccount(processLease)) != nil
    }

    internal func validate() throws {
        guard phase == .ready, identityIsCurrent(), let runtimeBinding else {
            throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount
        }
        try runtimeBinding.validate()
    }

    private func failClosed() {
        phase = .failed
        currentBatch?.sourceLifetime.retire()
        lifetime.markUnavailable()
        // Retain handler/account/native admissions and original repository.
        // Retirement is not evidence of rollback or completion of a native call.
    }

    /// A normal account presentation may start only after the private localOnly
    /// editor was explicitly closed and the REAL original account has stopped.
    /// The stop task outlives cancellation of any awaiting sheet or window.
    static func suspend(appGroup: String, retrying: Bool) async throws {
        guard let runtime = retained else {
            guard !claimed else { throw AnytypeOriginalEditorLocalAnnotationError.runtimeAlreadyOwned }
            return
        }
        guard runtime.appGroup.utf8.elementsEqual(appGroup.utf8) else {
            throw AnytypeOriginalEditorLocalAnnotationError.incompatibleDeployment
        }
        try await runtime.stop(retrying: retrying)
    }

    private func stop(retrying: Bool) async throws {
        if let stopTask, phase == .stopping || !retrying {
            try await stopTask.value
            return
        }
        retireExpiredBatchIfNeeded()
        guard !opening, currentOwner?.isCurrent != true, currentBatch?.isCurrent != true else {
            // Do not discard a draft or conversion run held by another owner.
            throw AnytypeOriginalEditorLocalAnnotationError.overlappingSession
        }
        if phase == .stopFailed && !retrying {
            throw AnytypeOriginalEditorLocalAnnotationError.closeRequiresExplicitRetry
        }
        guard phase == .ready || phase == .failed || phase == .stopFailed else {
            throw AnytypeOriginalEditorLocalAnnotationError.runtimeAlreadyOwned
        }
        try process.validateLocalAccount(processLease)
        guard InvocationDispatchContext.binding == nil else {
            throw AnytypeOriginalEditorLocalAnnotationError.runtimeAlreadyOwned
        }
        phase = .stopping
        lifetime.markUnavailable()
        currentOwner?.retire()
        // This reservation protected the selected local account between calls.
        // Retired source operations keep THEIR original admissions until their
        // actual native callbacks drain; AccountStop waits on those admissions.
        accountReservation?.cancel()
        accountReservation = nil
        let task = Task { @MainActor [self] in
            let transition = EditorAccountWriteTransition(
                lifetime: accountLifetime, rpcNames: ["AccountStop"])
            do {
                try await InvocationDispatchContext.$binding.withValue(transition.binding) {
                    try await authMiddleService.logout(removeData: false)
                }
                await transition.finishAndWaitForRelease()
                try await ServiceMessageHandlerAdapter.shared.waitForPendingEventDelivery()
                await Container.shared.spaceViewsStorage().stopSubscription()
                await Container.shared.participantsStorage().stopSubscription()
                await Container.shared.loginStateService().cleanStateAfterLogout()
                try await ServiceMessageHandlerAdapter.shared.waitForPendingEventDelivery()
                accountManager.account = .empty
                // No handler is replaced and no local repository/credential is
                // deleted. A subsequent local session selects the SAME private
                // account with networkMode.localOnly from its original journal.
                try process.releaseLocalAccount(processLease)
                currentOwner = nil
                currentBatch = nil
                accountCapture = nil
                runtimeBinding = nil
                phase = .stopped
                if Self.retained === self {
                    Self.retained = nil
                    Self.claimed = false
                }
            } catch {
                await transition.finishAndWaitForRelease()
                phase = .stopFailed
                // A failed Stop retains the sole owner and exact original
                // repository. Explicit retry is the only in-process release.
                throw error
            }
        }
        stopTask = task
        try await task.value
    }

    private func createPrivateSpace(name: String,
                                    creationBinding: EditorDocumentWriteSourceBinding? = nil) async throws -> AccountInfo {
        try validate()
        guard let runtimeBinding else { throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount }
        let service = Container.shared.workspaceService()
        let operationBinding = creationBinding ?? runtimeBinding
        let opened = try await operationBinding.performOperation(rpcNames: ["WorkspaceCreate", "WorkspaceOpen"]) {
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
        let preparationBinding: InvocationDispatchBinding
        if let creationBinding {
            try creationBinding.validate()
            let captures = creationBinding.captures
            preparationBinding = InvocationDispatchBinding { _ in
                for captured in captures { try captured.validate() }
                return InvocationDispatchPermit {
                    let admissions = try EditorDocumentWriteCapture.acquireAll(captures)
                    return InvocationDispatchCompletion { for admission in admissions { admission.cancel() } }
                }
            }
        } else {
            preparationBinding = capture.accountDispatchBinding()
        }
        try await InvocationDispatchContext.$binding.withValue(preparationBinding) {
            await Container.shared.objectTypeProvider().prepareData(spaceId: opened.accountSpaceId)
            await Container.shared.propertyDetailsStorage().prepareData(spaceId: opened.accountSpaceId)
        }
        try creationBinding?.validate()
        return opened
    }

    internal func openBatch(
        sourceLifetime: AnytypeOriginalEditorLocalAnnotationBatchSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationBatchSource) -> Bool
    ) async throws -> OriginalEditorLocalAnnotationBatchOwner {
        try validate()
        retireExpiredBatchIfNeeded()
        guard !opening, currentOwner?.isCurrent != true, currentBatch?.isCurrent != true else {
            throw AnytypeOriginalEditorLocalAnnotationError.overlappingSession
        }
        opening = true
        defer { opening = false }
        let captured = try EditorDocumentWriteCapture(sourceLifetime.lifetime)
        let check: @MainActor () throws -> Void = { [self] in
            try validate(); try captured.validate()
            guard sourceLifetime.isCurrent, sourceIsCurrent(sourceLifetime.source) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
        }
        try check()
        var record = try await journal.beginBatch(source: sourceLifetime.source)
        do {
            try check()
            guard let runtimeBinding else {
                throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount
            }
            try runtimeBinding.validate()
            let originalCaptures = runtimeBinding.captures + [captured]
            let binding = try EditorDocumentWriteSourceBinding(
                lifetime: sourceLifetime.lifetime, accountLifetime: accountLifetime,
                additionalLifetimes: originalCaptures.map(\.source),
                isCurrent: { sourceLifetime.isCurrent && sourceIsCurrent(sourceLifetime.source) })
            try Self.requireInheritedCaptures(originalCaptures, in: binding)
            record = try await journal.transitionBatch(record, to: "space_may_have_dispatched")
            try check()
            let space = try await createPrivateSpace(name: "Local annotation batch " + record.attempt.uuidString,
                creationBinding: binding)
            record = try await journal.transitionBatch(record, to: "space_observed",
                spaceID: space.accountSpaceId, spaceViewID: space.spaceViewId)
            try check()
            let selected = try await prepareSelectedSpace(space.accountSpaceId,
                retaining: binding.captures)
            try check()
            record = try await journal.transitionBatch(record, to: "ready")
            try check()
            let owner = OriginalEditorLocalAnnotationBatchOwner(
                sourceLifetime: sourceLifetime, runtime: self, journalRecord: record,
                selected: selected.selection, annotationTypeID: selected.typeID,
                capture: captured, sourceIsCurrent: sourceIsCurrent)
            currentBatch = owner
            return owner
        } catch {
            sourceLifetime.retire()
            failClosed()
            throw error
        }
    }

    internal func retireBatch(_ batch: OriginalEditorLocalAnnotationBatchOwner) {
        guard currentBatch === batch else { return }
        // Admission retires first. A running native body still keeps its original
        // leases and must drain through the unchanged real AccountStop path.
        if currentOwner?.batchAttemptID == batch.journalRecord.attempt { currentOwner?.retire() }
    }

    private func retireExpiredBatchIfNeeded() {
        if let batch = currentBatch, !batch.isCurrent { retireBatch(batch) }
    }

    internal func open(sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
                       canonical: OriginalEditorLocalAnnotationCanonical,
                       sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool)
        async throws -> OriginalEditorLocalAnnotationDraftOwner {
        guard currentBatch?.isCurrent != true else {
            throw AnytypeOriginalEditorLocalAnnotationError.overlappingSession
        }
        retireExpiredBatchIfNeeded()
        return try await openDraft(sourceLifetime: sourceLifetime, canonical: canonical,
            batch: nil, sourceIsCurrent: sourceIsCurrent)
    }

    internal func openBatchAnnotation(batch: OriginalEditorLocalAnnotationBatchOwner,
                                     sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
                                     canonical: OriginalEditorLocalAnnotationCanonical,
                                     sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool)
        async throws -> OriginalEditorLocalAnnotationDraftOwner {
        try batch.validate()
        guard currentBatch === batch, case .plainText = canonical.body else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidSource
        }
        return try await openDraft(sourceLifetime: sourceLifetime, canonical: canonical,
            batch: batch, sourceIsCurrent: sourceIsCurrent)
    }

    private func openDraft(sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
                           canonical: OriginalEditorLocalAnnotationCanonical,
                           batch: OriginalEditorLocalAnnotationBatchOwner?,
                           sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool)
        async throws -> OriginalEditorLocalAnnotationDraftOwner {
        try validate()
        guard !opening, currentOwner?.isCurrent != true else {
            throw AnytypeOriginalEditorLocalAnnotationError.overlappingSession
        }
        let source = sourceLifetime.source
        try batch?.reserve(source)
        opening = true
        defer { opening = false }
        let stillCurrent: @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool = { candidate in
            sourceIsCurrent(candidate) && (batch?.isCurrent ?? true)
        }
        let check: @MainActor () throws -> Void = { [self] in
            try validate(); try batch?.validate()
            guard sourceLifetime.isCurrent, stillCurrent(source) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
        }
        try check()
        var draft = try await journal.beginDraft(source: source, canonicalSHA256: canonical.digest,
                                                batch: batch?.journalRecord)
        do {
            let selected: (selection: OriginalActiveSpaceSelection, typeID: String)
            let spaceID: String
            if let batch {
                try batch.validate()
                guard let observedSpace = batch.journalRecord.spaceID,
                      let observedView = batch.journalRecord.spaceViewID else {
                    throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
                }
                spaceID = observedSpace
                draft = try await journal.transition(draft, to: "batch_space_observed",
                    spaceID: observedSpace, spaceViewID: observedView)
                try check()
                // This is the LIVE selection from this run's actual creation and
                // schema readback. No persisted ID can reselect or revive it.
                selected = (batch.selected, batch.annotationTypeID)
            } else {
                draft = try await journal.transition(draft, to: "space_may_have_dispatched")
                try check()
                let space = try await createPrivateSpace(name: "Local annotation " + draft.attempt.uuidString)
                draft = try await journal.transition(draft, to: "space_observed",
                    spaceID: space.accountSpaceId, spaceViewID: space.spaceViewId)
                try check()
                selected = try await prepareSelectedSpace(space.accountSpaceId)
                spaceID = space.accountSpaceId
            }
            try check()
            let prepared = try sourceBinding(sourceLifetime, selection: selected.selection,
                additionalCaptures: batch.map { [$0.capture] } ?? [], sourceIsCurrent: stillCurrent)
            draft = try await journal.transition(draft, to: "materialization_may_have_dispatched")
            try check()
            let materialized = try await OriginalEditorLocalAnnotationMaterialization.materialize(
                canonical: canonical, source: source, draft: draft, accountID: accountID,
                selection: selected.selection, annotationTypeID: selected.typeID,
                binding: prepared, sourceIsCurrent: check)
            // Actual typed drain and fresh ObjectShow precede every observation.
            draft = try await journal.transition(draft, to: "object_observed", objectID: materialized)
            try check()
            let editorBinding = try AnytypeOriginalEditorBinding(accountID: accountID,
                spaceID: spaceID, objectID: materialized, hostProfileID: source.hostProfileID,
                annotationUUID: source.annotationUUID, expectedRevision: source.expectedRevision,
                sourceWitnessSHA256: source.sourceWitnessSHA256)
            let originalSource = AnytypeOriginalEditorSourceLifetime(binding: editorBinding)
            let retirement = sourceLifetime.lifetime.observe(try EditorDocumentWriteCapture(sourceLifetime.lifetime).token) {
                originalSource.retire()
            }
            let host: AnytypeOriginalEditorHost
            if batch != nil {
                // Include the exact run/row/permission generations at the REAL
                // original writer's GCD admission, not only a Swift UI callback.
                try originalSource.claim(for: editorBinding)
                do {
                    let originalCaptures = prepared.captures
                    let hostBinding = try EditorDocumentWriteSourceBinding(
                        lifetime: originalSource.lifetime, accountLifetime: accountLifetime,
                        additionalLifetimes: originalCaptures.map(\.source),
                        isCurrent: {
                            originalSource.isCurrent && sourceLifetime.isCurrent && stillCurrent(source)
                        })
                    try Self.requireInheritedCaptures(originalCaptures, in: hostBinding)
                    host = try await AnytypeOriginalEditorModule.makeHost(binding: editorBinding,
                        sourceLifetime: originalSource, sourceBinding: hostBinding,
                        accountManager: accountManager)
                } catch {
                    originalSource.retire()
                    throw error
                }
            } else {
                host = try await AnytypeOriginalEditorModule.openExistingEditor(
                    binding: editorBinding, sourceLifetime: originalSource
                ) { candidate in
                    candidate == editorBinding && sourceLifetime.isCurrent && stillCurrent(source)
                }
            }
            try check()
            host.snapshotTransportOriginHostProfileID = canonical.transportOriginHostProfileID
            draft = try await journal.transition(draft, to: "opened")
            let owner = OriginalEditorLocalAnnotationDraftOwner(host: host, sourceLifetime: sourceLifetime,
                journal: journal, draft: draft, retirement: retirement,
                sourceIsCurrent: stillCurrent, runtime: self)
            currentOwner = owner
            return owner
        } catch {
            // Unknown effects are retained. No fresh import or duplicate UUID is
            // inferred from failure/cancellation; only real Stop can release us.
            batch?.sourceLifetime.retire()
            failClosed()
            throw error
        }
    }

    private static func requireInheritedCaptures(_ captures: [EditorDocumentWriteCapture],
                                                 in binding: EditorDocumentWriteSourceBinding) throws {
        for capture in captures {
            try capture.validate()
            guard binding.captures.contains(where: { $0.source === capture.source && $0.token == capture.token }) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
        }
        try binding.validate()
    }

    private func prepareSelectedSpace(_ spaceID: String,
                                      retaining captures: [EditorDocumentWriteCapture] = []) async throws
        -> (selection: OriginalActiveSpaceSelection, typeID: String) {
        try validate()
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(20))
        for captured in captures { try captured.validate() }
        while !Container.shared.participantsStorage().canEdit(spaceId: spaceID) {
            try validate()
            for captured in captures { try captured.validate() }
            guard clock.now < deadline else { throw AnytypeOriginalEditorLocalAnnotationError.unavailableSpace }
            try await clock.sleep(for: .milliseconds(50))
        }
        guard let manager = Container.shared.activeSpaceManager() as? ActiveSpaceManager else {
            throw AnytypeOriginalEditorLocalAnnotationError.originalServiceUnavailable
        }
        for captured in captures { try captured.validate() }
        if captures.isEmpty {
            _ = try await manager.setActiveSpace(spaceId: spaceID)
        } else {
            _ = try await manager.setActiveSpaceForLocalAnnotationBatch(spaceId: spaceID, retaining: captures)
        }
        for captured in captures { try captured.validate() }
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
                               additionalCaptures: [EditorDocumentWriteCapture] = [],
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
            try EditorDocumentWriteCapture(lifetime)] + additionalCaptures
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
    var canonicalBodySHA256: String { draft.canonicalSHA256 }
    var batchAttemptID: UUID? { draft.batchAttempt }
    func validateCurrent() throws {
        try runtime.validate()
        guard source.isCurrent, sourceIsCurrent(source.source) else {
            throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
        }
    }

    func validateCapturedSource(_ capture: AnytypeOriginalEditorLocalAnnotationCapture) throws {
        try validateCurrent()
        guard captureAttempted, draft.phase == "captured",
              capture.nativeCapture.snapshot.provenance.matchesCaptureBinding(host.binding),
              draft.captureSHA256 == OriginalEditorLocalAnnotationValidation.sha256(
                capture.nativeCapture.snapshot.bodyBytes),
              draft.captureArchiveSHA256 == capture.nativeCapture.snapshot.nativeArchiveSHA256 else {
            throw AnytypeOriginalEditorLocalAnnotationError.canonicalBodyMismatch
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
        let text = try OriginalEditorLocalAnnotationNativeBody.textProjection(native.snapshot, source: source.source)
        draft = try await journal.transition(draft, to: "captured",
            captureSHA256: OriginalEditorLocalAnnotationValidation.sha256(native.snapshot.bodyBytes),
            archiveSHA256: native.snapshot.nativeArchiveSHA256)
        // Capture terminally retired the separate native editor. The Host source
        // remains current through its original SQLite CAS and is retired by that
        // owner afterwards. This history is neither a saved-row commit nor ACK.
        return .init(nativeCapture: native, textPreview: text.textPreview, fullPlainText: text.fullPlainText)
    }

    func retire() {
        source.retire()
        host.retire()
    }
}
