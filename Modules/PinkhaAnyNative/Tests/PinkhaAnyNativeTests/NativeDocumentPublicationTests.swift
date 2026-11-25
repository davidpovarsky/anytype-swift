#if os(iOS)
import Foundation
import XCTest
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaAnyRuntime
import PinkhaTorahPresentation
@testable import PinkhaAnyUI
@testable import PinkhaAnyNative

/// Actual AnyLib reads and writes with a bounded delivery gate. The surface is
/// synthetic; these tests certify model publication, not UIKit gestures.
@MainActor
final class NativeDocumentPublicationTests: XCTestCase {
    func testAcknowledgedNativeEditsRetireOlderReadsAndKeepUndo() async throws {
        try await withDocument { fixture in
            let model = fixture.model, blockID = fixture.blockID
            let original = try fixture.block()
            let held = await fixture.gate.arm(.load)
            let oldLoad = fixture.start { await model.load() }
            try await fixture.gate.waitUntilCaptured(held)

            try fixture.type("נשמר כעת")
            await model.flush()
            XCTAssertEqual(model.writeState, .saved)
            let acknowledged = try XCTUnwrap(model.read?.nativeVersion)
            let history = model.textHistoryEpochs
            let stored = try await fixture.read()
            XCTAssertEqual(stored.snapshot.blocks.first { $0.id == blockID }?.text, "נשמר כעת")
            await fixture.gate.release(held)
            await oldLoad.value
            try await fixture.settleDeferredReads()

            XCTAssertEqual(try fixture.block().text, "נשמר כעת")
            XCTAssertEqual(model.read?.nativeVersion, acknowledged)
            XCTAssertEqual(model.textHistoryEpochs, history)
            await model.undoLastNativeEdit()
            try await fixture.settleDeferredReads()
            XCTAssertEqual(try fixture.block().text, original.text,
                           "A late display read must not clear the acknowledged native Undo.")
            let undone = try await fixture.read()
            XCTAssertEqual(undone.snapshot.blocks.first { $0.id == blockID }?.text, original.text)

            let styleBefore = try fixture.block().native["style"]
            let heldStyle = await fixture.gate.arm(.load)
            let oldStyleLoad = fixture.start { await model.load() }
            try await fixture.gate.waitUntilCaptured(heldStyle)
            model.select(blockIDs: [blockID], focusedBlockID: blockID, range: .init(location: 0, length: 0))
            await model.setWritingStyle(direction: .rightToLeft, alignment: .right)
            let styledVersion = try XCTUnwrap(model.read?.nativeVersion)
            XCTAssertEqual(try fixture.block().direction, .rightToLeft)
            XCTAssertEqual(try fixture.block().alignment, .right)
            await fixture.gate.release(heldStyle)
            await oldStyleLoad.value
            try await fixture.settleDeferredReads()
            XCTAssertEqual(model.read?.nativeVersion, styledVersion)
            XCTAssertEqual(try fixture.block().direction, .rightToLeft)
            await model.undoLastNativeEdit()
            try await fixture.settleDeferredReads()
            XCTAssertEqual(try fixture.block().native["style"], styleBefore)

            let heldCreate = await fixture.gate.arm(.load)
            let oldCreateLoad = fixture.start { await model.load() }
            try await fixture.gate.waitUntilCaptured(heldCreate)
            await model.addParagraph()
            let acknowledgedIDs = model.orderedBlocks.map(\.id)
            XCTAssertEqual(acknowledgedIDs.count, 2)
            let insertedID = try XCTUnwrap(model.focusedBlockID)
            XCTAssertNotEqual(insertedID, blockID)
            await fixture.gate.release(heldCreate)
            await oldCreateLoad.value
            try await fixture.settleDeferredReads()
            XCTAssertEqual(model.orderedBlocks.map(\.id), acknowledgedIDs)
            XCTAssertEqual(model.focusedBlockID, insertedID)
            let created = try await fixture.read()
            XCTAssertEqual(created.snapshot.depthFirstIDs, acknowledgedIDs)
        }
    }

    func testStaleReadFailureAndDeferCannotReplaceNewOwnerState() async throws {
        try await withDocument { fixture in
            let model = fixture.model
            let heldError = await fixture.gate.arm(.load)
            let oldError = fixture.start { await model.load() }
            try await fixture.gate.waitUntilCaptured(heldError)
            try fixture.type("שמירה מאוחרת")
            await model.flush()
            XCTAssertEqual(model.writeState, .saved)
            model.message = "current-publication"
            await fixture.gate.release(heldError, fail: true)
            await oldError.value
            try await fixture.settleDeferredReads()
            XCTAssertEqual(model.message, "current-publication")
            XCTAssertEqual(try fixture.block().text, "שמירה מאוחרת")

            model.unmount()
            let oldOwner = model.mountedOwnerID
            let heldOldOwner = await fixture.gate.arm(.load)
            let oldOwnerLoad = fixture.start { await model.load() }
            try await fixture.gate.waitUntilCaptured(heldOldOwner)
            XCTAssertTrue(model.isLoading)
            // SwiftUI can start a read before UIKit mounts the actual surface.
            model.mount(surface: fixture.surface)
            XCTAssertNotEqual(model.mountedOwnerID, oldOwner)
            let heldNewOwner = await fixture.gate.arm(.load)
            let newOwnerLoad = fixture.start { await model.load() }
            try await fixture.gate.waitUntilCaptured(heldNewOwner)
            XCTAssertTrue(model.isLoading)
            model.message = "new-owner-publication"
            await fixture.gate.release(heldOldOwner, fail: true)
            await oldOwnerLoad.value
            XCTAssertTrue(model.isLoading, "The old defer cannot finish a newer owner's load.")
            XCTAssertEqual(model.message, "new-owner-publication")
            await fixture.gate.release(heldNewOwner)
            await newOwnerLoad.value
            try await fixture.settleDeferredReads()
            XCTAssertFalse(model.isLoading)
            XCTAssertTrue(model.canMutate)
            XCTAssertEqual(try fixture.block().text, "שמירה מאוחרת")
        }
    }

    func testTypingAndCompositionBackToBaseDuringNativeSaveRetainNewRevision() async throws {
        try await withDocument { fixture in
            let model = fixture.model
            let original = try fixture.block().text
            let held = await fixture.gate.arm(.mutationReadback)
            try fixture.type("טיוטה ראשונה")
            // Exercise the real 450ms debounce owner, not a separate manual flush.
            try await fixture.gate.waitUntilCaptured(held)
            let alreadyStored = try await fixture.read()
            XCTAssertEqual(alreadyStored.snapshot.blocks.first { $0.id == fixture.blockID }?.text, "טיוטה ראשונה")
            try fixture.type(original)
            XCTAssertEqual(model.recoveredDrafts.first?.inlineMarkdown, original,
                           "Typing back to the old base is still a newer unsaved intent.")
            await fixture.gate.release(held)
            try await fixture.waitUntilSaved()
            try await fixture.settleDeferredReads()
            XCTAssertEqual(model.writeState, .saved)
            XCTAssertFalse(model.hasPendingEdits)
            XCTAssertEqual(try fixture.block().text, original)
            let restored = try await fixture.read()
            XCTAssertEqual(restored.snapshot.blocks.first { $0.id == fixture.blockID }?.text, original)

            let heldComposition = await fixture.gate.arm(.mutationReadback)
            try fixture.type("טיוטה בזמן הקלדה")
            try await fixture.gate.waitUntilCaptured(heldComposition)
            let rendered = try fixture.block()
            let source = model.source(for: rendered)
            try model.beginTextComposition(renderedBlock: rendered, source: source,
                selection: .init(location: source.utf16.count, length: 0))
            let output = model.finishTextComposition(blockID: fixture.blockID, display: original,
                selection: .init(location: original.utf16.count, length: 0), allowSaving: true)
            XCTAssertEqual(output, original)
            XCTAssertEqual(model.recoveredDrafts.first?.inlineMarkdown, original)
            await fixture.gate.release(heldComposition)
            try await fixture.waitUntilSaved()
            try await fixture.settleDeferredReads()
            XCTAssertEqual(model.writeState, .saved)
            XCTAssertFalse(model.hasPendingEdits)
            XCTAssertEqual(try fixture.block().text, original)
            let final = try await fixture.read()
            XCTAssertEqual(final.snapshot.blocks.first { $0.id == fixture.blockID }?.text, original)
        }
    }

    func testSemanticAnchorCancelCaptureEditsResolveAndUndoUseRealNativeStore() async throws {
        try await withDocument { fixture in
            let model = fixture.model, blockID = fixture.blockID
            let original = try fixture.block()
            let range = NSRange(location: 0, length: 4)
            model.select(blockIDs: [blockID], focusedBlockID: blockID, range: range)
            let cancelled = try await model.prepareSemanticAnchor(
                blockID: blockID, range: range, visibleText: "מקור א")
            let beforeCancel = try await fixture.read()
            model.cancelSemanticAnchor(cancelled)
            let afterCancel = try await fixture.read()
            XCTAssertEqual(afterCancel.nativeVersion, beforeCancel.nativeVersion)
            XCTAssertEqual(afterCancel.snapshot.blocks, beforeCancel.snapshot.blocks,
                           "Preview and Cancel must not write the native document.")

            let intent = try await model.prepareSemanticAnchor(
                blockID: blockID, range: range, visibleText: "מקור א")
            XCTAssertNotEqual(intent.anchor, cancelled.anchor)
            let anchor = try await model.applySemanticAnchor(intent)
            try await fixture.settleDeferredReads()
            XCTAssertEqual(model.writeState, .saved)
            XCTAssertFalse(model.isCreatingTextAnchor)
            XCTAssertTrue(model.canMutate)
            let anchored = try await fixture.read()
            let stored = try XCTUnwrap(anchored.snapshot.blocks.first { $0.id == blockID })
            XCTAssertEqual(stored.native["style"], original.native["style"])
            XCTAssertEqual(stored.native["nav"], original.native["nav"])
            XCTAssertEqual(stored.type, original.type)
            XCTAssertEqual(AnyInlineMarkdown(stored.text).display, "מקור א")
            guard case .resolved(let captured) = try AnySemanticAnchorDocument.resolve(anchor, read: anchored) else {
                return XCTFail("The actual native marker must resolve.")
            }
            XCTAssertEqual(captured.count, 1)
            XCTAssertEqual(captured.first?.range, range)
            XCTAssertEqual(captured.first?.text, "מקור")
            do { _ = try await model.applySemanticAnchor(intent); XCTFail("Consumed intent was replayed.") }
            catch AnyHostError.changedDocument {}
            let afterReplay = try await fixture.read()
            XCTAssertEqual(afterReplay.nativeVersion, anchored.nativeVersion)

            let prefix = "חדש "
            let shifted = try AnyInlineMarkdown(try fixture.block().text)
                .replacing(displayRange: .init(location: 0, length: 0), withLiteral: prefix)
            try model.changeText(blockID: blockID, source: shifted,
                displaySelection: .init(location: prefix.utf16.count, length: 0), renderedBlock: fixture.block())
            await model.flush()
            try await fixture.settleDeferredReads()
            guard case .resolved(let moved) = try await model.revealSemanticAnchor(anchor) else {
                return XCTFail("Native prefix editing must move the marker without an old-offset fallback.")
            }
            XCTAssertEqual(moved.first?.range, NSRange(location: prefix.utf16.count, length: 4))
            XCTAssertEqual(moved.first?.text, "מקור")

            let changed = try AnyInlineMarkdown(try fixture.block().text).replacing(
                displayRange: .init(location: prefix.utf16.count + 1, length: 1), withLiteral: "X")
            try model.changeText(blockID: blockID, source: changed,
                displaySelection: .init(location: prefix.utf16.count + 2, length: 0), renderedBlock: fixture.block())
            await model.flush()
            try await fixture.settleDeferredReads()
            guard case .resolved(let edited) = try await model.revealSemanticAnchor(anchor) else {
                return XCTFail("The same native marker must follow edits inside the selected text.")
            }
            XCTAssertEqual(edited.first?.text, "מXור")
            let currentRange = try XCTUnwrap(edited.first?.range)
            let removed = try AnyInlineMarkdown(try fixture.block().text)
                .replacing(displayRange: currentRange, withLiteral: "")
            try model.changeText(blockID: blockID, source: removed,
                displaySelection: .init(location: currentRange.location, length: 0), renderedBlock: fixture.block())
            await model.flush()
            try await fixture.settleDeferredReads()
            let missing = try await model.revealSemanticAnchor(anchor)
            XCTAssertEqual(missing, .missing)
            await model.undoLastNativeEdit()
            try await fixture.settleDeferredReads()
            guard case .resolved(let restored) = try await model.revealSemanticAnchor(anchor) else {
                return XCTFail("Native Undo must restore the actual marker, not a saved locator.")
            }
            XCTAssertEqual(restored.first?.text, "מXור")
            XCTAssertEqual(try fixture.block().native["style"], original.native["style"])
        }
    }

    func testSemanticAnchorStaleIntentAndRetiredReadbackCannotWriteOrPublishAgain() async throws {
        try await withDocument { fixture in
            let model = fixture.model, blockID = fixture.blockID
            let range = NSRange(location: 0, length: 4)
            model.select(blockIDs: [blockID], focusedBlockID: blockID, range: range)
            let stale = try await model.prepareSemanticAnchor(
                blockID: blockID, range: range, visibleText: "מקור א")
            let documents = model.documents, objectID = model.objectID
            let external = try await fixture.owner.session.perform { lease in
                let read = try await documents.read(objectID: objectID, lease: lease)
                let edit = try documents.prepareTextEdit(read, blockID: blockID, inlineMarkdown: "מקור ב")
                let receipt = try await documents.apply(edit, lease: lease)
                guard receipt.readback == .verifiedCurrent else { throw AnyHostError.writeUncertain }
                return try await documents.read(objectID: objectID, lease: lease)
            }
            await model.load()
            do { _ = try await model.applySemanticAnchor(stale); XCTFail("A stale native selection was written.") }
            catch AnyHostError.changedDocument {}
            let afterRefusal = try await fixture.read()
            XCTAssertEqual(afterRefusal.nativeVersion, external.nativeVersion)
            XCTAssertFalse(model.isCreatingTextAnchor)

            await model.load()
            model.select(blockIDs: [blockID], focusedBlockID: blockID, range: range)
            let intent = try await model.prepareSemanticAnchor(
                blockID: blockID, range: range, visibleText: "מקור ב")
            let before = try XCTUnwrap(model.read?.nativeVersion)
            let held = await fixture.gate.arm(.mutationReadback)
            let apply = Task { @MainActor in try await model.applySemanticAnchor(intent) }
            try await fixture.gate.waitUntilCaptured(held)
            XCTAssertTrue(model.isCreatingTextAnchor)
            XCTAssertFalse(model.canMutate)
            XCTAssertThrowsError(try fixture.type("must not replace a pending anchor"))
            model.unmount()
            await fixture.gate.release(held)
            do { _ = try await apply.value; XCTFail("A retired view published the native result.") }
            catch AnyHostError.sessionClosed {}
            XCTAssertEqual(model.read?.nativeVersion, before)
            XCTAssertFalse(model.isCreatingTextAnchor)
            let committed = try await fixture.read()
            guard case .resolved(let fragments) = try AnySemanticAnchorDocument.resolve(intent.anchor, read: committed) else {
                return XCTFail("The already accepted native write must remain recoverable.")
            }
            XCTAssertEqual(fragments.count, 1)
            XCTAssertEqual(fragments.first?.text, "מקור")

            model.mount(surface: fixture.surface)
            await model.load()
            do { _ = try await model.applySemanticAnchor(intent); XCTFail("A retired intent was retried.") }
            catch AnyHostError.sessionClosed {}
            catch AnyHostError.changedDocument {}
            let afterRetiredReplay = try await fixture.read()
            XCTAssertEqual(afterRetiredReplay.nativeVersion, committed.nativeVersion)
        }
    }

    /// Real AnyLib persistence and the production Sefaria resolver. This is a
    /// mounted-model test; the separate UIKit test owns physical selection and
    /// cold-process reopening.
    func testSemanticSourceLinksPersistCanonicalIdentityAndRejectMissingOrForeignTargets() async throws {
        try await withDocument { fixture in
            let model = fixture.model, blockID = fixture.blockID
            let firstRange = NSRange(location: 0, length: 4)
            model.select(blockIDs: [blockID], focusedBlockID: blockID, range: firstRange)
            let firstIntent = try await model.prepareSemanticAnchor(
                blockID: blockID, range: firstRange, visibleText: "מקור א")
            let first = try await model.applySemanticAnchor(firstIntent)
            try await fixture.settleDeferredReads()
            let initial = try await fixture.read()
            try await model.torah.presentSemanticAnchorSources(first)
            let opened = try await fixture.read()
            XCTAssertEqual(initial.nativeVersion, opened.nativeVersion,
                           "Opening anchored sources is read-only.")
            let firstContext = TorahAssociationContext(spaceId: model.workspace.spaceID,
                objectId: model.objectID, scope: .semantic(first))
            XCTAssertEqual(model.torah.associationContext, firstContext)

            let result = TorahEditorSession.SearchResult(id: "semantic-native-source",
                scope: .references, providerValue: "Genesis 1:1", labelHe: nil, labelEn: nil,
                fallbackTitle: "Genesis 1:1", fallbackSubtitle: nil)
            let values = try await model.torah.link(result, to: firstContext, rawQuery: "Genesis 1:1")
            XCTAssertEqual(model.torah.persistenceState, .saved)
            XCTAssertEqual(values.count, 1)
            let storedFirst = try XCTUnwrap(values.first)
            XCTAssertEqual(storedFirst.canonicalKey, "Genesis 1:1")
            XCTAssertEqual(storedFirst.providerID, "sefaria")
            let location = TorahAssociationLocation(spaceId: model.workspace.spaceID,
                                                     target: .object(objectId: model.objectID))
            XCTAssertEqual(try TorahSemanticAnchorAssociation.decoding(storedFirst,
                location: location)?.anchor, first)
            let canonical = TorahAssociationPayloadCodec()
            let storedWire = try canonical.encodeDocument(.init(items: [storedFirst]))
            let independentFirst = try await fixture.associationRecords()
            XCTAssertEqual(independentFirst.count, 1)
            XCTAssertNil(independentFirst.first?.blockId)
            XCTAssertEqual(try canonical.encodeDocument(.init(items: independentFirst.map(\.item))), storedWire)

            let repeated = try await model.torah.link(result, to: firstContext, rawQuery: "Genesis 1:1")
            XCTAssertEqual(repeated.count, 1, "A retry of the same canonical source cannot create a second link.")
            XCTAssertEqual(repeated.first?.id, storedFirst.id)
            let ordinaryContext = TorahAssociationContext(spaceId: model.workspace.spaceID,
                                                           objectId: model.objectID, scope: .document)
            XCTAssertTrue(model.torah.cachedAssociations(for: ordinaryContext).isEmpty,
                          "An anchored source is never presented as a whole-document association.")

            await model.load()
            let secondRange = NSRange(location: 5, length: 1)
            model.select(blockIDs: [blockID], focusedBlockID: blockID, range: secondRange)
            let secondIntent = try await model.prepareSemanticAnchor(
                blockID: blockID, range: secondRange, visibleText: "מקור א")
            let second = try await model.applySemanticAnchor(secondIntent)
            try await fixture.settleDeferredReads()
            XCTAssertNotEqual(first, second)
            let secondContext = TorahAssociationContext(spaceId: model.workspace.spaceID,
                objectId: model.objectID, scope: .semantic(second))
            let secondValues = try await model.torah.link(result, to: secondContext, rawQuery: "Genesis 1:1")
            let storedSecond = try XCTUnwrap(secondValues.first)
            XCTAssertEqual(secondValues.count, 1)
            XCTAssertNotEqual(storedFirst.id, storedSecond.id,
                              "The same verse linked to two distinct text anchors has two canonical identities.")
            let independentBoth = try await fixture.associationRecords()
            XCTAssertEqual(independentBoth.count, 2)
            XCTAssertEqual(Set(try independentBoth.compactMap {
                try TorahSemanticAnchorAssociation.decoding($0.item, location: $0.location)?.anchor
            }), Set([first, second]))

            let prefix = "חדש "
            let prefixed = try AnyInlineMarkdown(try fixture.block().text)
                .replacing(displayRange: .init(location: 0, length: 0), withLiteral: prefix)
            try model.changeText(blockID: blockID, source: prefixed,
                displaySelection: .init(location: prefix.utf16.count, length: 0), renderedBlock: fixture.block())
            await model.flush()
            try await fixture.settleDeferredReads()
            guard case .resolved(let moved) = try await model.inspectSemanticAnchor(first) else {
                return XCTFail("The canonical source must remain attached to its actual edited native marker.")
            }
            XCTAssertEqual(moved.first?.range, .init(location: prefix.utf16.count, length: 4))
            XCTAssertEqual(moved.first?.text, "מקור")
            let retainedValues = try await model.torah.associationSnapshot(for: firstContext)
            XCTAssertEqual(retainedValues.count, 1)
            XCTAssertEqual(retainedValues.first?.id, storedFirst.id)

            let foreign = try PinkhaSemanticTextAnchor(spaceID: model.workspace.spaceID,
                objectID: model.objectID + "-foreign", id: first.id)
            do {
                try await model.torah.presentSemanticAnchorSources(foreign)
                XCTFail("A foreign document marker opened this document's source UI.")
            } catch PinkhaSemanticTextAnchorError.wrongDocument {}
            let beforeDenied = try await fixture.associationRecords()
            do {
                _ = try await model.torah.link(result, to: firstContext, rawQuery: "Genesis 1:1",
                                               isCurrentRequest: { false })
                XCTFail("A retired request wrote a source.")
            } catch is CancellationError {}
            let afterDenied = try await fixture.associationRecords()
            XCTAssertEqual(try canonical.encodeDocument(.init(items: beforeDenied.map(\.item))),
                           try canonical.encodeDocument(.init(items: afterDenied.map(\.item))))

            // Remove the actual marker through the ordinary editor write path.
            // Retain its canonical source until the user explicitly unlinks it.
            let removed = try AnyInlineMarkdown(try fixture.block().text)
                .replacing(displayRange: try XCTUnwrap(moved.first?.range), withLiteral: "")
            try model.changeText(blockID: blockID, source: removed,
                displaySelection: .init(location: prefix.utf16.count, length: 0), renderedBlock: fixture.block())
            await model.flush()
            try await fixture.settleDeferredReads()
            let missing = try await model.inspectSemanticAnchor(first)
            XCTAssertEqual(missing, .missing)
            let beforeMissing = try await fixture.associationRecords()
            do {
                _ = try await model.torah.link(result, to: firstContext, rawQuery: "Genesis 1:1")
                XCTFail("A missing anchor was recreated or silently retargeted.")
            } catch TorahSemanticAnchorResolutionError.missing {}
            let afterMissing = try await fixture.associationRecords()
            XCTAssertEqual(try canonical.encodeDocument(.init(items: beforeMissing.map(\.item))),
                           try canonical.encodeDocument(.init(items: afterMissing.map(\.item))))
            let removedLinks = try await model.torah.unlinkAssociation(storedFirst, from: firstContext)
            XCTAssertTrue(removedLinks.isEmpty)
            let finalRecords = try await fixture.associationRecords()
            XCTAssertEqual(finalRecords.map(\.item.id), [storedSecond.id])
            XCTAssertEqual(try TorahSemanticAnchorAssociation.decoding(finalRecords[0].item,
                location: finalRecords[0].location)?.anchor, second)
            XCTAssertEqual(model.torah.persistenceState, .saved)
        }
    }

    private func withDocument(_ body: @MainActor (NativePublicationFixture) async throws -> Void) async throws {
        XCTAssertEqual(AnyEmbeddedBuild.linked, .pinkhaNativeV1)
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("native-publication-" + UUID().uuidString, isDirectory: true)
        let credentialService = "io.pinkha.native.publication.tests." + UUID().uuidString
        let application = try AnyNativeApplication(dataDirectory: directory, credentialService: credentialService)
        var accountID: String?
        var spaceID: String?
        var fixture: NativePublicationFixture?
        do {
            try await application.start(network: .official)
            let account = try await application.createAccount()
            accountID = account.id
            try await application.acknowledgeRecoveryBackup(accountID: account.id)
            let space = try await application.createSpace(name: "Disposable editor publication")
            spaceID = space
            let owner = try await application.connectSpace(id: space)
            let operations = try AnyGuardedTorahOperationStore(client: owner.client, workspace: owner.workspace)
            let marker = try await AnyNoteBootstrap.install(client: owner.client, session: owner.session)
            try await owner.session.perform { lease in
                try await operations.repository.install { try await lease.validate() }
            }
            let intent = try AnyNativeObjectCreationIntent(workspace: owner.workspace,
                mutationID: Self.intentID(), typeID: "page",
                initialProperties: .object(["any": .object(["name": .string("בדיקת פרסום עורך")])]))
            let objectID = try await owner.session.perform { lease in
                try await owner.objects.ensureObject(intent) { try await lease.validate() }
            }
            let block = try AnyNativeBlockCreationIntent(workspace: owner.workspace,
                mutationID: Self.intentID(), objectID: objectID, type: "paragraph", text: "מקור א",
                style: .object(["pinkhaWritingDirection": .string("natural"),
                    "pinkhaTextAlignment": .string("natural"), "pinkhaAlignmentWasExplicit": .bool(false),
                    "publicationFixtureUnknown": .string("preserved")]),
                parentID: "", position: AnyLexicographicPosition.middle)
            let blockID = try await owner.session.perform { lease in
                try await owner.blocks.ensureBlock(block) { try await lease.validate() }
            }
            let lifetime = AnyUIPresentationLifetime()
            let model = try AnyDocumentPresentation(client: owner.client, session: owner.session,
                objects: owner.objects, blocks: owner.blocks, capabilities: owner.capabilities,
                operations: operations, noteMarker: marker, objectID: objectID, lifetime: lifetime,
                recovery: AnyNativeLibraryRecovery(workspace: owner.workspace))
            let gate = NativePublicationReadGate()
            model.editorReadOperation = { purpose, documents, objectID, lease in
                try await gate.read(purpose, documents: documents, objectID: objectID, lease: lease)
            }
            let access = try AnyHTTPTorahTargetAccess(client: owner.client, workspace: owner.workspace,
                allowedTypeIDs: owner.capabilities.allowedTargetTypes, documentTypePolicy: .nativeCanonicalEditorV1)
            let canonicalReader = try AnyTorahAssociationRepository(workspace: owner.workspace,
                store: operations, access: access)
            let associationReader = try AnySessionTorahAssociationRepository(session: owner.session,
                repository: canonicalReader, operations: operations)
            let value = NativePublicationFixture(owner: owner, model: model, gate: gate,
                lifetime: lifetime, blockID: blockID, associationReader: associationReader)
            fixture = value
            model.mount(surface: value.surface)
            await model.load()
            XCTAssertTrue(model.canMutate)
            XCTAssertEqual(try value.block().text, "מקור א")
            try await body(value)
            await value.finish()
            let remaining = await gate.pendingCount
            XCTAssertEqual(remaining, 0, "No paused read or continuation survives the fixture drain.")
            try await application.deleteSpace(id: space)
            spaceID = nil
            try await application.signOut()
            try await application.removeSavedAccount(id: account.id)
            await application.stop()
            try await AnyProtectedCreationJournal.removeAccountData(accountID: account.id)
            try FileManager.default.removeItem(at: directory)
        } catch {
            await fixture?.finish()
            if let spaceID { try? await application.deleteSpace(id: spaceID) }
            await application.stop()
            if let accountID {
                try? AnyNativeCredentialVault(service: credentialService).remove(accountID: accountID)
                try? await AnyProtectedCreationJournal.removeAccountData(accountID: accountID)
            }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    private static func intentID() -> String {
        UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    }
}

@MainActor
private final class NativePublicationFixture {
    let owner: AnyNativeWorkspaceOwner
    let model: AnyDocumentPresentation
    let gate: NativePublicationReadGate
    let lifetime: AnyUIPresentationLifetime
    let blockID: String
    private let associationReader: AnySessionTorahAssociationRepository
    let surface = NativePublicationSurface()
    private var tasks: [Task<Void, Never>] = []

    init(owner: AnyNativeWorkspaceOwner, model: AnyDocumentPresentation, gate: NativePublicationReadGate,
         lifetime: AnyUIPresentationLifetime, blockID: String,
         associationReader: AnySessionTorahAssociationRepository) {
        self.owner = owner; self.model = model; self.gate = gate
        self.lifetime = lifetime; self.blockID = blockID; self.associationReader = associationReader
    }

    func associationRecords() async throws -> [TorahStoredAssociationRecord] {
        try await associationReader.listAssociationRecords(objectId: model.objectID, spaceId: owner.workspace.spaceID)
    }

    func block() throws -> AnyEditorBlock {
        try XCTUnwrap(model.read?.snapshot.blocks.first { $0.id == blockID })
    }

    func type(_ text: String) throws {
        try model.changeText(blockID: blockID, source: text,
            displaySelection: .init(location: text.utf16.count, length: 0), renderedBlock: block())
    }

    func read() async throws -> AnyEditorRead {
        let documents = model.documents, objectID = model.objectID
        return try await owner.session.perform { try await documents.read(objectID: objectID, lease: $0) }
    }

    func settleDeferredReads() async throws {
        guard let pending = model.pendingDeferredEditorRead else { return }
        let completion = NativePublicationCompletion()
        let observer = Task {
            await pending.value
            await completion.finish()
        }
        defer { observer.cancel() }
        do {
            for _ in 0..<2_000 {
                try Task.checkCancellation()
                if await completion.finished {
                    await observer.value
                    return
                }
                try await Task.sleep(for: .milliseconds(10))
            }
        } catch {
            pending.cancel()
            await observer.value
            throw error
        }
        // A failed barrier cancels only the owned deferred read before fixture
        // cleanup; it cannot leave an unstructured waiter or a native lease.
        pending.cancel()
        await observer.value
        throw NativePublicationGateError.timeout
    }

    func waitUntilSaved() async throws {
        for _ in 0..<2_000 {
            try Task.checkCancellation()
            if !model.hasPendingEdits, model.writeState == .saved { return }
            switch model.writeState {
            case .conflict, .uncertain, .failed: throw NativePublicationGateError.saveFailed
            default: break
            }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw NativePublicationGateError.timeout
    }

    func start(_ action: @escaping @MainActor @Sendable () async -> Void) -> Task<Void, Never> {
        let task = Task { await action() }
        tasks.append(task)
        return task
    }

    func finish() async {
        await gate.releaseAll()
        for task in tasks { task.cancel() }
        for task in tasks { await task.value }
        tasks.removeAll()
        await lifetime.drain()
    }
}

@MainActor
private final class NativePublicationSurface: AnyEditorMountedSurface {
    let sceneID = UUID()
    var isForegroundMounted = true
    func isBlockVisible(_ id: String) -> Bool { true }
    func reveal(blockID: String, selection: NSRange?) {}
    func dismissKeyboard() {}
}

private actor NativePublicationCompletion {
    private(set) var finished = false
    func finish() { finished = true }
}

private enum NativePublicationGateError: Error { case timeout, unknownRead, injectedDeliveryFailure, saveFailed }

private actor NativePublicationReadGate {
    private struct Hold {
        let purpose: AnyDocumentReadPurpose
        var captured = false
        var outcome: Bool?
    }
    private var holds: [UUID: Hold] = [:]
    private var order: [UUID] = []
    var pendingCount: Int { holds.count }

    func arm(_ purpose: AnyDocumentReadPurpose) -> UUID {
        let id = UUID()
        holds[id] = .init(purpose: purpose); order.append(id)
        return id
    }

    func read(_ purpose: AnyDocumentReadPurpose, documents: AnyEditorDocumentStore,
              objectID: String, lease: AnyHostLease) async throws -> AnyEditorRead {
        let value = try await documents.read(objectID: objectID, lease: lease)
        guard let id = order.first(where: { holds[$0]?.purpose == purpose && holds[$0]?.captured == false }),
              var hold = holds[id] else { return value }
        hold.captured = true; holds[id] = hold
        defer { holds.removeValue(forKey: id); order.removeAll { $0 == id } }
        // Polling has an explicit bound and cancellation; no continuation can
        // outlive fixture cleanup or prevent the real native lease from draining.
        for _ in 0..<3_000 {
            try Task.checkCancellation()
            if let outcome = holds[id]?.outcome {
                if outcome { return value }
                throw NativePublicationGateError.injectedDeliveryFailure
            }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw NativePublicationGateError.timeout
    }

    func waitUntilCaptured(_ id: UUID) async throws {
        for _ in 0..<2_000 {
            try Task.checkCancellation()
            guard let hold = holds[id] else { throw NativePublicationGateError.unknownRead }
            if hold.captured { return }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw NativePublicationGateError.timeout
    }

    func release(_ id: UUID, fail: Bool = false) {
        guard var hold = holds[id] else { return }
        hold.outcome = !fail; holds[id] = hold
    }

    func releaseAll() {
        for id in order {
            guard var hold = holds[id] else { continue }
            hold.outcome = true; holds[id] = hold
        }
    }
}
#endif
