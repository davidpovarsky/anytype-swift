import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaKit
@testable import PinkhaAnyHost

/// Real Host snapshot/conditional edit preparation, with in-memory received
/// fields. No HTTP request or native engine is performed by these controls.
final class AnySemanticAnchorDocumentTests: XCTestCase {
    private let owner = UUID(uuidString: "00112233-4455-6677-8899-aabbccddeeff")!
    private let style: AnyJSON = .object([
        "pinkhaWritingDirection": .string("rightToLeft"),
        "pinkhaTextAlignment": .string("right"),
        "future": .object(["opaque": .array([.integer(4), .string("keep")])])
    ])

    private func anchor(object: String = "document") throws -> PinkhaSemanticTextAnchor {
        try .init(spaceID: "space", objectID: object,
                  id: UUID(uuidString: "11112233-4455-6677-8899-aabbccddeeff")!)
    }

    private func block(_ id: String = "paragraph", text: String = "לפני **שָׁלוֹם 😀** אחרי",
                       type: String = "paragraph", parent: String = "", position: String = "A",
                       style: AnyJSON? = nil, version: String = "text-v1") -> AnyJSON {
        .object(["id": .string(id), "type": .string(type), "text": .string(text),
            "nav": .object(["parentId": .string(parent), "pos": .string(position)]),
            "style": style ?? self.style,
            "_ver": .object(["id": .string("create-" + id), "text": .string(version),
                             "style": .object(["*": .string("style-v1")])])])
    }

    private func read(_ blocks: [AnyJSON], version: String = "document-v1", run: String = "native-run-1",
                      generation: UUID? = nil, space: String = "space", object: String = "document",
                      dataset: String = "editor_blocks") throws -> AnyEditorRead {
        let snapshot = try AnyEditorSnapshot(spaceID: space, objectID: object, title: "כותרת",
            response: .object(["records": .array(blocks), "total": .integer(Int64(blocks.count)), "hasNext": .bool(false)]),
            dataset: dataset)
        return .init(snapshot: snapshot, markdown: "not used as a locator", nativeVersion: version,
                     engineStartedAt: run, generation: generation ?? owner)
    }

    private func store() throws -> AnyEditorDocumentStore {
        // No request is made. The existing Host preparation API requires a
        // client identity even when preparing an edit from an obtained read.
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account")
        return try .init(client: client, workspace: .init(accountID: "account", spaceID: "space"), allowedTypeIDs: ["page"])
    }

    private func capture(_ source: AnyEditorRead, anchor: PinkhaSemanticTextAnchor? = nil) throws -> AnySemanticAnchorCapture {
        let projection = AnyInlineMarkdown(source.snapshot.blocks.first(where: { $0.id == "paragraph" })!.text)
        let range = (projection.display as NSString).range(of: "שָׁלוֹם 😀")
        return try .init(read: source, blockID: "paragraph", range: range, anchor: anchor ?? self.anchor())
    }

    func testCaptureUsesExistingVersionRunCASAndPreservesExactInverseAndOpaqueFields() throws {
        let original = block()
        let source = try read([original])
        let captured = try capture(source)
        let edit = try captured.prepare(current: source, documents: store())
        XCTAssertEqual(edit.expectedVersion, source.nativeVersion)
        XCTAssertEqual(edit.engineStartedAt, source.engineStartedAt)
        XCTAssertEqual(edit.generation, source.generation)
        XCTAssertEqual(edit.blockID, "paragraph")
        XCTAssertEqual(edit.set, ["text": .string(captured.replacement)])
        XCTAssertEqual(edit.inverseSet, ["text": original["text"]!])
        XCTAssertTrue(edit.unset.isEmpty)
        XCTAssertEqual(source.snapshot.blocks[0].native, original)
        XCTAssertEqual(captured.expected.text, AnyInlineMarkdown(source.snapshot.blocks[0].text).display)
        XCTAssertEqual(captured.expected.marks.first?.anchor, captured.anchor)
    }

    func testPrepareRejectsVersionOwnerRunScopeDatasetAndUnknownFieldChanges() throws {
        let source = try read([block()]), captured = try capture(source)
        let changed = [
            try read([block()], version: "document-v2"),
            try read([block()], run: "native-run-2"),
            try read([block()], generation: UUID()),
            try read([block()], space: "other-space"),
            try read([block()], object: "other-document"),
            try read([block()], dataset: "other_editor"),
            try read([block(style: .object(["future": .string("changed without changing visible text")]))]),
            try read([block(parent: "missing")]),
        ]
        for current in changed {
            XCTAssertThrowsError(try captured.prepare(current: current, documents: store())) {
                XCTAssertEqual($0 as? AnyHostError, .changedDocument)
            }
        }
    }

    func testCaptureRejectsExistingSameIdentityElsewhereAndUnreachableCopies() throws {
        let anchor = try anchor()
        let marker = "[copy](\(anchor.markerString))"
        for extra in [block("copy", text: marker, position: "B"), block("orphan", text: marker, parent: "gone")] {
            XCTAssertThrowsError(try capture(read([block(), extra]), anchor: anchor)) {
                XCTAssertEqual($0 as? PinkhaSemanticTextAnchorError, .selectionAlreadyLinked)
            }
        }
        let source = try read([block()]), captured = try capture(source, anchor: anchor)
        XCTAssertThrowsError(try captured.prepare(current: read([block(), block("copy", text: marker, position: "B")]), documents: store())) {
            XCTAssertEqual($0 as? AnyHostError, .changedDocument)
        }
    }

    func testReadbackRequiresExactMarkerFieldOneFragmentAndCurrentNativeOwner() throws {
        let source = try read([block()]), captured = try capture(source)
        let correct = try read([block(text: captured.replacement, version: "text-v2")], version: "document-v2")
        XCTAssertNoThrow(try captured.verifyReadback(correct))
        for incorrect in [
            try read([block()], version: "document-v2"),
            try read([block(text: captured.replacement)], run: "native-run-2"),
            try read([block(text: captured.replacement)], generation: UUID()),
            try read([block(text: captured.replacement)], dataset: "other_editor"),
            try read([block(text: captured.replacement), block("copy", text: captured.replacement, position: "B")]),
        ] {
            XCTAssertThrowsError(try captured.verifyReadback(incorrect))
        }
        // Full-block adjacent clones satisfy the shared split-fragment shape;
        // initial capture acknowledgement still requires exactly one fragment.
        let whole = try read([block(text: "שָׁלוֹם 😀")]), wholeCapture = try capture(whole)
        let duplicated = try read([block(text: wholeCapture.replacement), block("copy", text: wholeCapture.replacement, position: "B")])
        XCTAssertThrowsError(try wholeCapture.verifyReadback(duplicated)) {
            XCTAssertEqual($0 as? AnyHostError, .writeUncertain)
        }
    }

    func testResolveUsesCompleteCurrentNativeGraphAndReportsMissingAmbiguousOrForeign() throws {
        let anchor = try anchor(), source = "before [selected](\(anchor.markerString)) after"
        let current = try read([block("current-native-id", text: source)])
        guard case .resolved(let fragments) = try AnySemanticAnchorDocument.resolve(anchor, read: current) else { return XCTFail() }
        XCTAssertEqual(fragments.map(\.blockID), ["current-native-id"])
        XCTAssertEqual(fragments.map(\.text), ["selected"])
        XCTAssertEqual(try AnySemanticAnchorDocument.resolve(anchor, read: read([block(text: "selected")])), .missing)
        XCTAssertEqual(try AnySemanticAnchorDocument.resolve(anchor, read: read([
            block(text: source), block("other", text: "unrelated", position: "B"), block("copy", text: source, position: "C")
        ])), .ambiguous)
        XCTAssertThrowsError(try AnySemanticAnchorDocument.resolve(self.anchor(object: "foreign"), read: current)) {
            XCTAssertEqual($0 as? PinkhaSemanticTextAnchorError, .wrongDocument)
        }
    }

    func testCaptureAndResolveRefuseUnsupportedNativeSyntaxInsteadOfRetargetingOffsets() throws {
        let anchor = try anchor()
        XCTAssertThrowsError(try AnySemanticAnchorCapture(read: read([block(type: "image")]), blockID: "paragraph",
            range: .init(location: 0, length: 2), anchor: anchor))
        XCTAssertThrowsError(try AnySemanticAnchorCapture(read: read([block()]), blockID: "missing",
            range: .init(location: 0, length: 2), anchor: anchor))
        XCTAssertThrowsError(try AnySemanticAnchorDocument.resolve(anchor, read: read([
            block(text: "[unsupported](pinkha-anchor://v99/foreign)")
        ])))
    }
}
