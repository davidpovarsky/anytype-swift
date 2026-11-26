#if canImport(SwiftUI)
import Foundation
import XCTest
import PinkhaKit
import TorahInspectorCore
@testable import PinkhaTorahPresentation

/// Controller boundary tests with explicit in-memory I/O and the unchanged
/// provider JSON fixture. These are not native-engine or live-network evidence.
@MainActor
final class SharedSemanticSourceLinkTests: XCTestCase {
    func testCanonicalSourceRequiresFreshResolutionBeforeAndAfterTheWrite() async throws {
        let fixture = try SemanticSourceFixture()
        let values = try await fixture.session.link(fixture.result, to: fixture.context, rawQuery: "Genesis 1:1")
        XCTAssertEqual(fixture.resolveCount, 2)
        XCTAssertEqual(values.count, 1)
        let item = try XCTUnwrap(values.first)
        XCTAssertEqual(item.canonicalKey, "Genesis 1:1")
        XCTAssertEqual(try TorahSemanticAnchorAssociation.decoding(item, location: fixture.location)?.anchor,
                       fixture.anchor)
        XCTAssertEqual(fixture.session.persistenceState, .saved)
        let writes = await fixture.store.writeCount()
        XCTAssertEqual(writes, 1)
        XCTAssertTrue(fixture.session.cachedAssociations(for: .init(
            spaceId: "space", objectId: "document", scope: .document)).isEmpty)
    }

    func testMissingAmbiguousAndForeignAnchorsCannotWriteOrFallBackToDocumentSources() async throws {
        for variant in ["missing", "ambiguous", "foreign"] {
            let fixture = try SemanticSourceFixture()
            fixture.resolutionMode = variant
            let context: TorahAssociationContext
            if variant == "foreign" {
                context = .init(spaceId: "space", objectId: "document", scope: .semantic(
                    try .init(spaceID: "other-space", objectID: "document", id: fixture.anchor.id)))
            } else { context = fixture.context }
            do {
                _ = try await fixture.session.link(fixture.result, to: context, rawQuery: "Genesis 1:1")
                XCTFail("Unresolved semantic target was accepted: " + variant)
            } catch {
                if variant == "foreign" {
                    XCTAssertEqual(error as? PinkhaSemanticTextAnchorError, .wrongDocument)
                } else {
                    XCTAssertEqual(error as? TorahSemanticAnchorResolutionError,
                                   variant == "missing" ? .missing : .ambiguous)
                }
            }
            let writes = await fixture.store.writeCount()
            XCTAssertEqual(writes, 0)
            XCTAssertNotEqual(fixture.session.persistenceState, .saved)
        }
    }

    func testReplyCannotReplaceCanonicalFieldOrMarkerReadback() async throws {
        for variant in ["changed-field", "missing-metadata", "marker-removed-after-write"] {
            let fixture = try SemanticSourceFixture()
            if variant == "marker-removed-after-write" { fixture.missingAfterWrite = true }
            else { await fixture.store.setReadbackFault(variant) }
            do {
                _ = try await fixture.session.link(fixture.result, to: fixture.context, rawQuery: "Genesis 1:1")
                XCTFail("A transport reply substituted for canonical semantic readback: " + variant)
            } catch {
                XCTAssertEqual(error as? TorahSemanticAnchorResolutionError, .writeUnconfirmed)
            }
            let writes = await fixture.store.writeCount()
            XCTAssertEqual(writes, 1, "A partially confirmed write must never be retried automatically.")
            guard case .uncertain = fixture.session.persistenceState else {
                return XCTFail("A possibly committed source requires an uncertain status.")
            }
        }
    }

    func testSuspendedSourceDispatchRechecksPermissionCancellationAndDocumentLifetime() async throws {
        for variant in ["permission", "cancelled", "reopened"] {
            let fixture = try SemanticSourceFixture()
            let gate = SemanticSourceGate()
            await fixture.store.holdNextWrite(gate)
            let task = Task { @MainActor in
                try await fixture.session.link(fixture.result, to: fixture.context, rawQuery: "Genesis 1:1")
            }
            do { try await gate.waitUntilHeld() }
            catch { task.cancel(); await gate.release(); _ = try? await task.value; throw error }
            if variant == "permission" { fixture.canEdit = false }
            else if variant == "cancelled" { task.cancel() }
            else {
                fixture.session.deactivateDocument()
                fixture.session.activateDocument()
                fixture.session.message = "New document lifetime"
                fixture.session.persistenceState = .saved
            }
            await gate.release()
            do { _ = try await task.value; XCTFail("A retired source dispatch wrote: " + variant) }
            catch {
                if variant == "permission" {
                    XCTAssertEqual(error as? TorahAssociationRepositoryError, .permissionDenied)
                } else { XCTAssertTrue(error is CancellationError) }
            }
            let writes = await fixture.store.writeCount()
            XCTAssertEqual(writes, 0)
            if variant == "reopened" {
                XCTAssertEqual(fixture.session.message, "New document lifetime")
                XCTAssertEqual(fixture.session.persistenceState, .saved)
            }
        }
    }

    func testUnlinkRechecksFinalAuthorityAndRequiresCanonicalAbsence() async throws {
        for variant in ["permission", "reopened", "retained-record"] {
            let fixture = try SemanticSourceFixture()
            let values = try await fixture.session.link(fixture.result, to: fixture.context, rawQuery: "Genesis 1:1")
            let item = try XCTUnwrap(values.first)
            let gate = SemanticSourceGate()
            if variant == "retained-record" { await fixture.store.setKeepRemovedRecord() }
            else { await fixture.store.holdNextWrite(gate) }
            let task = Task { @MainActor in
                try await fixture.session.unlinkAssociation(item, from: fixture.context)
            }
            if variant != "retained-record" {
                do { try await gate.waitUntilHeld() }
                catch { task.cancel(); await gate.release(); _ = try? await task.value; throw error }
                if variant == "permission" { fixture.canEdit = false }
                else {
                    fixture.session.deactivateDocument()
                    fixture.session.activateDocument()
                    fixture.session.message = "Reopened source panel"
                    fixture.session.persistenceState = .saved
                }
                await gate.release()
            }
            do { _ = try await task.value; XCTFail("An unconfirmed unlink was accepted: " + variant) }
            catch {
                if variant == "permission" {
                    XCTAssertEqual(error as? TorahAssociationRepositoryError, .permissionDenied)
                } else if variant == "reopened" { XCTAssertTrue(error is CancellationError) }
                else {
                    guard let failure = error as? TorahAssociationRepositoryError, case .writeUncertain = failure else {
                        return XCTFail("A retained canonical record was not reported uncertain.")
                    }
                }
            }
            let remaining = try await fixture.store.listAssociationRecords(objectId: "document", spaceId: "space")
            XCTAssertEqual(remaining.count, 1)
            if variant == "reopened" {
                XCTAssertEqual(fixture.session.message, "Reopened source panel")
                XCTAssertEqual(fixture.session.persistenceState, .saved)
            }
        }
    }
}

@MainActor
private final class SemanticSourceFixture {
    let anchor: PinkhaSemanticTextAnchor
    let session: TorahEditorSession
    let store = SemanticSourceRepository()
    var canEdit = true
    var resolutionMode = "resolved"
    var missingAfterWrite = false
    var resolveCount = 0
    var location: TorahAssociationLocation { .init(spaceId: "space", target: .object(objectId: "document")) }
    var context: TorahAssociationContext { .init(spaceId: "space", objectId: "document", scope: .semantic(anchor)) }
    let result = TorahEditorSession.SearchResult(id: "test-provider-ref", scope: .references,
        providerValue: "Genesis 1:1", labelHe: nil, labelEn: nil,
        fallbackTitle: "Genesis 1:1", fallbackSubtitle: nil)

    init() throws {
        anchor = try .init(spaceID: "space", objectID: "document")
        let fixture = try XCTUnwrap(Bundle.module.url(forResource: "reference-resolved", withExtension: "json"))
        let transport = SemanticSourceTransport(bytes: try Data(contentsOf: fixture))
        session = TorahEditorSession(spaceId: "space", objectId: "document",
            workspace: try .sefaria(transport: transport), associations: store, notesService: SemanticSourceNoNotes())
        session.installAssociationEditingPolicy { [weak self] in self?.canEdit == true }
        session.installSemanticAnchorResolver { [weak self] anchor in
            guard let self else { throw CancellationError() }
            resolveCount += 1
            let marked = try PinkhaSemanticText(text: "text", marks: [.init(anchor: self.anchor,
                                                                           range: .init(location: 0, length: 4))])
            let blocks: [PinkhaSemanticTextAnchorResolver.Block]
            if resolutionMode == "missing" || (missingAfterWrite && resolveCount > 1) {
                blocks = [.init(id: "plain", content: try .init(text: "text"))]
            } else if resolutionMode == "ambiguous" {
                blocks = [.init(id: "first", content: marked), .init(id: "gap", content: try .init(text: "gap")),
                          .init(id: "copy", content: marked)]
            } else { blocks = [.init(id: "first", content: marked)] }
            return try PinkhaSemanticTextAnchorResolver.resolve(anchor, spaceID: "space",
                                                                 objectID: "document", blocks: blocks)
        }
    }
}

private actor SemanticSourceGate {
    private var held = false
    private var continuation: CheckedContinuation<Void, Never>?
    func hold() async { await withCheckedContinuation { held = true; continuation = $0 } }
    func release() { continuation?.resume(); continuation = nil }
    func waitUntilHeld() async throws {
        for _ in 0..<1_000 {
            try Task.checkCancellation()
            if held { return }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw CancellationError()
    }
}

private actor SemanticSourceRepository: TorahAssociationSnapshotRepository {
    private var records: [TorahStoredAssociationRecord] = []
    private var writes = 0
    private var gate: SemanticSourceGate?
    private var readbackFault: String?
    private var keepRemovedRecord = false
    func writeCount() -> Int { writes }
    func holdNextWrite(_ value: SemanticSourceGate) { gate = value }
    func setReadbackFault(_ value: String) { readbackFault = value }
    func setKeepRemovedRecord() { keepRemovedRecord = true }

    private func dispatch(_ authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        if let held = gate { gate = nil; await held.hold() }
        try Task.checkCancellation()
        try await authorize()
    }
    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] {
        records.filter { $0.objectId == objectId && $0.spaceId == spaceId }
    }
    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        records.filter { $0.objectId == objectId && $0.spaceId == spaceId && $0.blockId == nil }.map(\.item)
    }
    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        records.filter { $0.objectId == objectId && $0.spaceId == spaceId && $0.blockId == blockId }.map(\.item)
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String,
                        authorize: @escaping TorahAssociationWriteAuthorization) async throws -> TorahAssociationItem {
        try await dispatch(authorize)
        var actual = item
        if readbackFault == "changed-field" { actual.labelHe += " altered in stored snapshot" }
        if readbackFault == "missing-metadata" { actual.customMetadata = nil }
        records.append(.init(location: .init(spaceId: spaceId, target: target), item: actual))
        writes += 1
        return item
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        try await addAssociation(item, target: target, spaceId: spaceId, authorize: {})
    }
    func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        try await addAssociation(item, target: target, spaceId: spaceId)
    }
    func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        try await addAssociation(item, target: target, spaceId: spaceId)
    }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {
        try await removeAssociation(associationId: associationId, target: target, spaceId: spaceId, authorize: {})
    }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String,
                           authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        try await dispatch(authorize)
        if !keepRemovedRecord {
            records.removeAll { $0.item.id == associationId && $0.location == .init(spaceId: spaceId, target: target) }
        }
        writes += 1
    }
}

private struct SemanticSourceTransport: TorahHTTPTransport {
    let bytes: Data
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        try Task.checkCancellation()
        let url = try XCTUnwrap(request.url)
        XCTAssertEqual(url.absoluteString, "https://www.sefaria.org/api/ref/Genesis%201:1")
        let response = try XCTUnwrap(HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1",
                                                    headerFields: ["Content-Type": "application/json"]))
        return (bytes, response)
    }
}

@MainActor
private final class SemanticSourceNoNotes: TorahEditorNotesService {
    func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote] { [] }
    func relatedDocuments(for selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot { .unavailable }
    func createNote(for selection: TorahInspectorSelection, authorize: @escaping TorahAssociationWriteAuthorization) async throws -> T5NoteCreationOutcome { throw CancellationError() }
    func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String? { nil }
    func unlink(noteId: String, for selection: TorahInspectorSelection, authorize: @escaping TorahAssociationWriteAuthorization) async throws { throw CancellationError() }
    func unlink(document: TorahRelatedDocument, for selection: TorahInspectorSelection, authorize: @escaping TorahAssociationWriteAuthorization) async throws { throw CancellationError() }
}
#endif
