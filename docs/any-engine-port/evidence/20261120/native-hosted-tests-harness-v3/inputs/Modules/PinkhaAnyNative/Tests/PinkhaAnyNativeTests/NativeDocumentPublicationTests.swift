#if os(iOS)
import Foundation
import XCTest
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaAnyRuntime
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
            let value = NativePublicationFixture(owner: owner, model: model, gate: gate,
                                                  lifetime: lifetime, blockID: blockID)
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
    let surface = NativePublicationSurface()
    private var tasks: [Task<Void, Never>] = []

    init(owner: AnyNativeWorkspaceOwner, model: AnyDocumentPresentation, gate: NativePublicationReadGate,
         lifetime: AnyUIPresentationLifetime, blockID: String) {
        self.owner = owner; self.model = model; self.gate = gate
        self.lifetime = lifetime; self.blockID = blockID
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
