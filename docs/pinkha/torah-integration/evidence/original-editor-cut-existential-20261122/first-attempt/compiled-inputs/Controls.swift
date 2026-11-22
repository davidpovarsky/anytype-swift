import Foundation
import Testing

@MainActor
private func verifyCutBoundary(_ kind: CutBoundaryKind) async throws {
    let block = BlockInformation(id: "original-block")
    let document = DocumentProbe(objectId: "original-object", spaceId: "original-Space", block: block)
    let range = NSRange(location: 3, length: 7)
    let expected = CutObservation(objectId: document.objectId, blockInfos: [block], blocksIds: [block.id], range: range)

    let lower = PasteboardBlockService()
    let owner = EditorDocumentWriteOwner()
    let action = ActionHandlerProbe(owner: owner, contextID: document.objectId)
    let unbound = PasteboardBlockDocumentService(service: lower)
    let bound = try PasteboardBlockDocumentService.bindOriginal(unbound, owner: owner, staging: DocumentOwnedFileStaging())
    let handler = makeCutBoundary(kind: kind, document: document, info: block, actionHandler: action, service: bound)
    handler.invokeCut(range)
    #expect(owner.registrations == [document.objectId])
    #expect(owner.validations.isEmpty)
    #expect(owner.completion == nil)
    #expect(await lower.values().isEmpty)
    owner.release()
    #expect(await owner.waitForCompletion() == "success")
    #expect(owner.validations == [ObjectIdentifier(document)])
    #expect(await lower.values() == [expected])

    let weakLower = PasteboardBlockService()
    let weakOwner = EditorDocumentWriteOwner()
    let weakAction = ActionHandlerProbe(owner: weakOwner, contextID: document.objectId)
    var weakBound: (any PasteboardBlockDocumentServiceProtocol)? = try PasteboardBlockDocumentService.bindOriginal(
        PasteboardBlockDocumentService(service: weakLower), owner: weakOwner, staging: DocumentOwnedFileStaging()
    )
    weak var releasedService = weakBound
    let weakHandler = makeCutBoundary(kind: kind, document: document, info: block, actionHandler: weakAction, service: weakBound)
    weakHandler.invokeCut(range)
    #expect(weakOwner.registrations == [document.objectId])
    weakBound = nil
    #expect(releasedService == nil)
    weakOwner.release()
    #expect(await weakOwner.waitForCompletion() == "success")
    #expect(weakOwner.validations.isEmpty)
    #expect(await weakLower.values().isEmpty)

    let failedLower = PasteboardBlockService(throwsBackend: true)
    let failedOwner = EditorDocumentWriteOwner()
    let failedBound = try PasteboardBlockDocumentService.bindOriginal(
        PasteboardBlockDocumentService(service: failedLower), owner: failedOwner, staging: DocumentOwnedFileStaging()
    )
    let failedHandler = makeCutBoundary(
        kind: kind, document: document, info: block,
        actionHandler: ActionHandlerProbe(owner: failedOwner, contextID: document.objectId), service: failedBound
    )
    failedHandler.invokeCut(range)
    #expect(failedOwner.registrations == [document.objectId])
    failedOwner.release()
    #expect(await failedOwner.waitForCompletion() == "backend-error")
    #expect(failedOwner.validations == [ObjectIdentifier(document)])
    #expect(await failedLower.values() == [expected])

    let legacyLower = PasteboardBlockService()
    let legacyService = PasteboardBlockDocumentService(service: legacyLower)
    let legacyHandler = makeCutBoundary(
        kind: kind, document: document, info: block,
        actionHandler: ActionHandlerProbe(owner: nil, contextID: document.objectId), service: legacyService
    )
    legacyHandler.invokeCut(range)
    #expect(await legacyLower.firstObservation() == expected)
    #expect(legacyService.hasValidURL == false)
    #expect(bound.hasValidURL == false)
    #expect(failedBound.hasValidURL == false)
}

@Suite(.serialized)
struct OriginalCutVoidBoundaryControls {
    @Test @MainActor
    func textCutRetainsOriginalDeferredGenericServiceBoundaryAndVirtualGuard() async throws {
        try await verifyCutBoundary(.text)
        let block = BlockInformation(id: "virtual-block")
        let document = DocumentProbe(objectId: "virtual-object", spaceId: "original-Space", block: block)
        let lower = PasteboardBlockService()
        let owner = EditorDocumentWriteOwner()
        let service = PasteboardBlockDocumentService(service: lower)
        let handler = makeCutBoundary(
            kind: .text, document: document, info: block,
            actionHandler: ActionHandlerProbe(owner: owner, contextID: document.objectId),
            service: service, virtualSession: VirtualSessionProbe(isMaterialized: false)
        )
        handler.invokeCut(NSRange(location: 1, length: 2))
        #expect(owner.registrations.isEmpty)
        #expect(await lower.values().isEmpty)
        #expect(service.hasValidURL == false)
    }

    @Test @MainActor
    func tableCutRetainsOriginalDeferredGenericServiceBoundary() async throws {
        try await verifyCutBoundary(.table)
    }
}
