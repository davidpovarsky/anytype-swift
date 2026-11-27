#if DEBUG && targetEnvironment(simulator)
import Foundation
import UIKit
import Factory
import Services
import ProtobufMessages
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaHanlinUI

/// Owned by one real mounted Heart sheet. Preparation and independent postflight
/// use its original native services; no account is created, switched or logged out.
@MainActor
final class PinkhaHanlinHeartSaveAcceptance {
    private let request: PinkhaHanlinSaveMessageAcceptancePreparation.Request?
    private let fixture: PinkhaHanlinSaveMessageAcceptanceFixture?
    private weak var editor: EditorPageController?
    private var started = false
    private var task: Task<Void, Never>?

    init(request: PinkhaHanlinSaveMessageAcceptancePreparation.Request?,
         fixture: PinkhaHanlinSaveMessageAcceptanceFixture?, presenter: UIViewController) throws {
        guard (request == nil) != (fixture == nil), let editor = presenter as? EditorPageController else {
            throw HanlinHostError.invalidContext
        }
        self.request = request; self.fixture = fixture; self.editor = editor
        if let request { try request.validate() }
        if let fixture { try fixture.validate() }
        try validateNativeAccount()
    }

    func didMount(host: PinkhaHanlinReadWriteHost, presentation: PinkhaHanlinChatPresentation,
                  controller: PinkhaHanlinChatController) {
        // viewDidAppear also runs after an original consent sheet disappears.
        // It cannot claim another fixture or start a second native operation.
        guard !started else { return }
        started = true
        do { try presentation.holdSaveMessageAcceptancePreparation() }
        catch { presentation.invalidate(); return }
        let pending = Task { @MainActor [weak presentation, weak controller] in
            do {
                guard let presentation, let controller else { throw HanlinHostError.staleContext }
                let typeID = try pageTypeID()
                let view = try await read(objectID: sourceObjectID, typeID: typeID, host: host, presentation: presentation)
                guard let revision = host.session.context.sourceRevision else { throw HanlinHostError.staleContext }
                if let request {
                    try PinkhaHanlinSaveMessageAcceptancePreparation.record(request: request,
                        sourceRevision: revision,
                        nativeSourceReadbackSHA256: PinkhaHanlinCreatePagePlan.digest(try view.serializedData()))
                    // This is the ordinary host. No provider or save action is
                    // installed during the read-only preparation. Close it and
                    // bind a fixture to the recorded live process before retrying.
                } else if let fixture {
                    try fixture.validate(session: host.session)
                    PinkhaHanlinSaveMessageAcceptanceDriver.start(fixture: fixture,
                        presentation: presentation, controller: controller) { [self, weak presentation] snapshot in
                        guard let presentation else { throw HanlinHostError.staleContext }
                        return try await verify(snapshot, typeID: typeID, host: host, presentation: presentation)
                    }
                }
            } catch { presentation?.invalidate() }
        }
        task = pending
        do { try presentation.ownSaveMessageAcceptancePreparation(pending) }
        catch { pending.cancel(); presentation.invalidate() }
    }

    func invalidate() { task?.cancel() }

    private var accountID: String { fixture?.accountID ?? request!.accountID }
    private var spaceID: String { fixture?.spaceID ?? request!.spaceID }
    private var sourceObjectID: String { fixture?.sourceObjectID ?? request!.sourceObjectID }

    private func validateNativeAccount() throws {
        try Task.checkCancellation()
        guard Container.shared.serverConfigurationStorage().currentConfiguration() == .localOnly,
              InvocationSettings.handler?.isLogEnabled == false,
              Container.shared.accountManager().account.id.utf8.elementsEqual(accountID.utf8),
              PinkhaHanlinAccountOwner.shared.isAvailable(account: accountID),
              let editor, editor.viewModel?.document.objectId.utf8.elementsEqual(sourceObjectID.utf8) == true,
              editor.viewIfLoaded?.window != nil, !editor.isBeingDismissed, !editor.isMovingFromParent else {
            throw HanlinHostError.staleContext
        }
    }

    private func pageTypeID() throws -> String {
        try validateNativeAccount()
        let types = Container.shared.objectTypeProvider().objectTypes(spaceId: spaceID).filter { $0.uniqueKey == .page }
        guard types.count == 1, let type = types.first, !type.id.isEmpty,
              type.spaceId.utf8.elementsEqual(spaceID.utf8), !type.hidden, !type.readonly,
              !type.isArchived, !type.isDeleted, type.recommendedLayout == .basic else { throw HanlinHostError.denied }
        return type.id
    }

    private func validate(host: PinkhaHanlinReadWriteHost, presentation: PinkhaHanlinChatPresentation,
                          typeID: String) async throws {
        try validateNativeAccount()
        try presentation.validateInstallation(for: host.session)
        let context = try await host.context(for: host.session)
        try validateNativeAccount()
        try presentation.validateInstallation(for: host.session)
        guard context == host.session.context, context.namespace.app == PinkhaHanlinEngineNamespace.heart,
              context.namespace.account.utf8.elementsEqual(accountID.utf8),
              context.namespace.space.utf8.elementsEqual(spaceID.utf8),
              context.namespace.workspace.utf8.elementsEqual(spaceID.utf8),
              context.objectReference?.utf8.elementsEqual(sourceObjectID.utf8) == true,
              context.selectionReferences.isEmpty,
              try pageTypeID().utf8.elementsEqual(typeID.utf8) else { throw HanlinHostError.staleContext }
    }

    private func read(objectID: String, typeID: String, host: PinkhaHanlinReadWriteHost,
                      presentation: PinkhaHanlinChatPresentation) async throws -> Anytype_Model_ObjectView {
        try await validate(host: host, presentation: presentation, typeID: typeID)
        let original = Container.shared.objectLifecycleService()
        let view = try await original.openForPreview(contextId: objectID, spaceId: spaceID)
        try await validate(host: host, presentation: presentation, typeID: typeID)
        _ = try PinkhaHanlinHeartSaveReadback(view: view, objectID: objectID, spaceID: spaceID, typeID: typeID)
        return view
    }

    private func verify(_ snapshot: PinkhaHanlinWriteJournal.SaveMessageAcceptanceSnapshot,
        typeID: String, host: PinkhaHanlinReadWriteHost,
        presentation: PinkhaHanlinChatPresentation) async throws -> PinkhaHanlinSaveMessageBodyReadback {
        guard let fixture, snapshot.entry.identity.session == host.session,
              snapshot.entry.effect == .committed, let progress = snapshot.progress,
              progress.manifest.bodyMode == nil, progress.isReadyForCommit,
              let objectID = snapshot.entry.createdObjectReference,
              !objectID.utf8.elementsEqual(sourceObjectID.utf8) else { throw HanlinHostError.resultMismatch }
        try fixture.validate(session: host.session)
        try progress.validate()
        let view = try await read(objectID: objectID, typeID: typeID, host: host, presentation: presentation)
        let actual = try PinkhaHanlinHeartSaveReadback(view: view, objectID: objectID, spaceID: spaceID, typeID: typeID)
        guard actual.body.count == progress.manifest.blockSHA256.count else { throw HanlinHostError.resultMismatch }
        var number = 0
        let blocks = try actual.body.enumerated().map { index, raw in
            number = raw.text.style == .numbered ? number + 1 : 0
            return try PinkhaHanlinHeartSaveBody.decode(raw, ordinal: number == 0 ? nil : number,
                expectedMarker: PinkhaHanlinHeartSaveBody.marker(progress.manifest, index: index))
        }
        let document = try PinkhaHanlinSaveMessageDocument(title: actual.title, blocks: blocks)
        return try document.verifiedReadback(manifest: progress.manifest, objectReference: objectID,
            blockReferences: actual.body.map(\.id))
    }
}
#endif
