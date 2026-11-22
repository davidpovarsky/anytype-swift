import Foundation
import Testing

@Suite(.serialized)
struct OriginalUndoAlertActorBoundaryControls {
    @Test(.timeLimit(.minutes(1))) @MainActor
    func undoAlertKeepsSynchronousTapReservationAndDeferredOriginalCall() async throws {
        let trace = TraceProbe()
        let owner = EditorDocumentWriteOwner(trace: trace)
        let service = UndoServiceProbe(trace: trace)
        let document = DocumentProbe(objectId: "actual-object-probe")
        let router = RouterProbe()
        let handler = ActionHandlerProbe(owner: owner, contextID: document.objectId)
        let model = EditorPageViewModel(router: router, actionHandler: handler,
                                        objectActionsService: service, document: document)
        model.shakeMotionDidAppear()
        let alert = try #require(router.alert)
        #expect(trace.entries.isEmpty)
        #expect(owner.contexts.isEmpty)
        #expect(service.objectIDs.isEmpty)
        let cancel = try #require(alert.buttons.first)
        cancel.action()
        #expect(trace.entries.isEmpty)
        let undo = try #require(alert.buttons.last)
        undo.action()
        #expect(owner.contexts == [document.objectId])
        #expect(trace.entries == ["attempt:" + document.objectId])
        #expect(service.objectIDs.isEmpty)
        #expect(await service.firstCall() == document.objectId)
        #expect(trace.entries == [
            "attempt:" + document.objectId, "deferred-body", "undo:" + document.objectId
        ])
        #expect(service.objectIDs == [document.objectId])

        let rejectedTrace = TraceProbe()
        let rejectedOwner = EditorDocumentWriteOwner(trace: rejectedTrace, rejects: true)
        let rejectedService = UndoServiceProbe(trace: rejectedTrace)
        let rejectedRouter = RouterProbe()
        let rejected = EditorPageViewModel(router: rejectedRouter,
            actionHandler: ActionHandlerProbe(owner: rejectedOwner, contextID: document.objectId),
            objectActionsService: rejectedService, document: document)
        rejected.shakeMotionDidAppear()
        let rejectedAlert = try #require(rejectedRouter.alert)
        let rejectedUndo = try #require(rejectedAlert.buttons.last)
        rejectedUndo.action()
        #expect(rejectedTrace.entries == ["attempt:" + document.objectId])
        #expect(rejectedOwner.contexts.isEmpty)
        #expect(rejectedService.objectIDs.isEmpty)
        await Task.yield()
        #expect(rejectedTrace.entries == ["attempt:" + document.objectId])
        #expect(rejectedService.objectIDs.isEmpty)
    }

    @Test(.timeLimit(.minutes(1))) @MainActor
    func undoAlertKeepsWeakModelLifetimeAndUnboundLegacyPath() async throws {
        let trace = TraceProbe()
        let owner = EditorDocumentWriteOwner(trace: trace)
        let service = UndoServiceProbe(trace: trace)
        let document = DocumentProbe(objectId: "released-object-probe")
        let router = RouterProbe()
        var model: EditorPageViewModel? = EditorPageViewModel(router: router,
            actionHandler: ActionHandlerProbe(owner: owner, contextID: document.objectId),
            objectActionsService: service, document: document)
        weak var released = model
        model?.shakeMotionDidAppear()
        let alert = try #require(router.alert)
        let undo = try #require(alert.buttons.last)
        model = nil
        #expect(released == nil)
        undo.action()
        #expect(trace.entries.isEmpty)
        #expect(owner.contexts.isEmpty)
        #expect(service.objectIDs.isEmpty)

        let legacyTrace = TraceProbe()
        let legacyService = UndoServiceProbe(trace: legacyTrace)
        let legacyRouter = RouterProbe()
        let legacyDocument = DocumentProbe(objectId: "legacy-object-probe")
        let legacy = EditorPageViewModel(router: legacyRouter,
            actionHandler: ActionHandlerProbe(owner: nil, contextID: legacyDocument.objectId),
            objectActionsService: legacyService, document: legacyDocument)
        legacy.shakeMotionDidAppear()
        let legacyAlert = try #require(legacyRouter.alert)
        let legacyUndo = try #require(legacyAlert.buttons.last)
        #expect(legacyTrace.entries.isEmpty)
        legacyUndo.action()
        #expect(legacyTrace.entries.isEmpty)
        #expect(legacyService.objectIDs.isEmpty)
        #expect(await legacyService.firstCall() == legacyDocument.objectId)
        #expect(legacyTrace.entries == ["undo:" + legacyDocument.objectId])
        #expect(legacyService.objectIDs == [legacyDocument.objectId])
    }
}
