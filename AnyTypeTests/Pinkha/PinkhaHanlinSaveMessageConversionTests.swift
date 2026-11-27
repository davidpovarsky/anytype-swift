#if os(iOS)
import Foundation
import XCTest
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
import PinkhaAnyHanlin
import PinkhaHanlinUI
import PinkhaAnyEngine
import PinkhaAnyHost

/// Runs the ORIGINAL Hanlin parser and production conversion/readback helpers.
/// Pure fixtures prove no native write, UI consent, journal durability or Apple QA.
@MainActor
final class PinkhaHanlinSaveMessageConversionTests: XCTestCase {
    func testOriginalParserPreservesHebrewFormattingUnicodeAndOrdinaryLink() async throws {
        let conversion = try await convert("# כותרת\n\n**שלום** _עולם_ ~~ישן~~ `a_b` [קישור](https://example.test/path?q=1) 👩🏽‍💻 e\u{301}\n")
        XCTAssertEqual(conversion.blocks.count, 2)
        XCTAssertEqual(conversion.document.blocks[0].kind, .heading)
        XCTAssertEqual(conversion.document.blocks[0].headingLevel, 1)
        let body = conversion.document.blocks[1].text
        XCTAssertEqual(Data(body.text.utf8), Data("שלום עולם ישן a_b קישור 👩🏽‍💻 e\u{301}".utf8))
        XCTAssertTrue(body.runs.contains { $0.traits == .bold })
        XCTAssertTrue(body.runs.contains { $0.traits == .italic })
        XCTAssertTrue(body.runs.contains { $0.traits == .strike })
        XCTAssertTrue(body.runs.contains { $0.traits == .code })
        XCTAssertTrue(body.runs.contains { $0.link == "https://example.test/path?q=1" })
        let read = try readback(conversion)
        XCTAssertEqual(try read.verifiedBody(manifest: conversion.manifest).nativeReadbackSHA256,
                       conversion.manifest.expectedBodyReadbackSHA256)
    }

    func testNativeRowsRoundTripAllSupportedBlockKindsAndCodeLanguage() async throws {
        let conversion = try await convert("# H1\n\n## H2\n\n### H3\n\n> Quote\n\n- one\n- two\n\n1. first\n2. second\n\n- [x] done\n- [ ] todo\n\n```swift\nlet x = \"**literal**\"\n```\n")
        XCTAssertEqual(conversion.document.blocks.map(\.kind),
                       [.heading, .heading, .heading, .quote, .bulleted, .bulleted, .numbered, .numbered, .checkbox, .checkbox, .code])
        XCTAssertEqual(conversion.document.blocks[6].number, 1)
        XCTAssertEqual(conversion.document.blocks[7].number, 2)
        XCTAssertEqual(conversion.document.blocks[8].checked, true)
        XCTAssertEqual(conversion.document.blocks[9].checked, false)
        XCTAssertEqual(conversion.document.blocks.last?.language, "swift")
        XCTAssertEqual(conversion.document.blocks.last?.text.text, "let x = \"**literal**\"\n")
        XCTAssertEqual(try readback(conversion).verifiedBody(manifest: conversion.manifest).blockReferences.count, 11)
    }

    func testOriginalSoftAndHardBreakPresentationIsOneNewlineEach() async throws {
        let conversion = try await convert("one\ntwo  \nthree\n")
        XCTAssertEqual(conversion.blocks.count, 1)
        XCTAssertEqual(conversion.document.blocks[0].text.text, "one\ntwo\nthree")
        _ = try readback(conversion).verifiedBody(manifest: conversion.manifest)
    }

    func testLiteralEscapesDoNotBecomeFormattingOrHTML() async throws {
        let conversion = try await convert("\\*literal\\* &amp; 2 &lt; 3\n")
        XCTAssertEqual(conversion.document.blocks[0].text.text, "*literal* & 2 < 3")
        XCTAssertTrue(conversion.document.blocks[0].text.runs.allSatisfy { $0.traits.isEmpty && $0.link == nil })
        _ = try readback(conversion).verifiedBody(manifest: conversion.manifest)
    }

    func testUnsupportedStructuresFailBeforeAnyNativePlanCanEscape() async throws {
        for markdown in [
            "#### unsupported heading", "---", "<div>HTML</div>", "![image](https://example.test/a.png)",
            "| A | B |\n|---|---|\n| x | y |", "- outer\n  - nested", "> first\n>\n> second",
            "7. nondefault start", "[label](https://example.test/ \"title\")", "[label](relative)",
            "[email](mailto:a@example.test)", "``code ` inside``", "[x](https://example.test/a(b))"
        ] { try await requireUnsupported(markdown) }
    }

    func testOriginalMathAndCitationAreRefusedRatherThanFlattened() async throws {
        try await requireUnsupported("The value is $x^2$.")
        try await requireUnsupported("$$\nx^2\n$$")
        try await requireUnsupported("[9F742443](https://example.test/?citationMarker=9F742443&citationTitle=Title&citationA11yValue=Title)")
        // Math-like bytes inside original code stay literal, as the original
        // preprocessor masks code before recognizing math.
        let code = try await convert("`$x^2$`")
        XCTAssertEqual(code.document.blocks[0].text.text, "$x^2$")
        XCTAssertEqual(code.document.blocks[0].text.runs.first?.traits, .code)
    }

    func testExactOriginalPlanProducesSameManifestAndMutationIDsTwice() async throws {
        let plan = try plan("**body**\n\nbody")
        let first = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(plan)
        let second = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(plan)
        XCTAssertEqual(try first.manifest.canonicalSHA256(), try second.manifest.canonicalSHA256())
        XCTAssertEqual(first.manifest.rootMutationID, second.manifest.rootMutationID)
        XCTAssertEqual(try first.manifest.blockMutationID(at: 0), try second.manifest.blockMutationID(at: 0))
        XCTAssertNotEqual(try first.manifest.blockMutationID(at: 0), try first.manifest.blockMutationID(at: 1))
    }

    func testBlockCountRefusesWholeDocumentInsteadOfTruncating() async throws {
        let maximum = try await convert((0..<64).map { "paragraph \($0)" }.joined(separator: "\n\n"))
        XCTAssertEqual(maximum.blocks.count, 64)
        try await requireUnsupported((0..<65).map { "paragraph \($0)" }.joined(separator: "\n\n"))
    }

    func testLongPlainSourceCoalescesRealNativeCharacterRunsWithoutLosingBytes() async throws {
        let source = String(repeating: "a", count: 65_536)
        let conversion = try await convert(source)
        XCTAssertEqual(Data(conversion.document.blocks[0].text.text.utf8), Data(source.utf8))
        XCTAssertEqual(conversion.document.blocks[0].text.runs.count, 1)
        XCTAssertEqual(conversion.document.blocks[0].text.runs[0].length, 65_536)
        _ = try readback(conversion).verifiedBody(manifest: conversion.manifest)
    }

    func testWrongBodySameVisibleTextAndChangedStyleCannotVerify() async throws {
        let conversion = try await convert("**body**")
        let plain = try readback(conversion, mutate: { rows in rows[0]["text"] = .string("body") })
        XCTAssertEqual(plain.blocks[0].text.text, conversion.document.blocks[0].text.text)
        XCTAssertThrowsError(try plain.verifiedBody(manifest: conversion.manifest))
        let changed = try readback(conversion, mutate: { rows in rows[0]["text"] = .string("**different**") })
        XCTAssertThrowsError(try changed.verifiedBody(manifest: conversion.manifest))
    }

    func testWrongTitleOrderAndExtraNativeBlockCannotVerify() async throws {
        let conversion = try await convert("first\n\nsecond")
        XCTAssertThrowsError(try readback(conversion, title: "different").verifiedBody(manifest: conversion.manifest))
        let reordered = try readback(conversion, mutate: { rows in
            let first = rows[0]["nav"]; rows[0]["nav"] = rows[1]["nav"]; rows[1]["nav"] = first
        })
        XCTAssertThrowsError(try reordered.verifiedBody(manifest: conversion.manifest))
        let extra = try readback(conversion, mutate: { rows in
            var copy = rows[1]; copy["id"] = .string("extra"); rows.append(copy)
        })
        XCTAssertThrowsError(try extra.verifiedBody(manifest: conversion.manifest))
    }

    func testNativeHierarchyUnknownMetadataAndWrongSpaceAreNotFlattened() async throws {
        let conversion = try await convert("body")
        XCTAssertThrowsError(try readback(conversion, mutate: { rows in
            rows[0]["nav"] = .object(["parentId": .string("missing-parent"), "pos": .string("a")])
        }))
        XCTAssertThrowsError(try readback(conversion, mutate: { rows in
            rows[0]["style"] = .object(["unknown": .bool(true)])
        }))
        XCTAssertThrowsError(try readback(conversion, rootSpace: "different-space"))
        XCTAssertThrowsError(try readback(conversion, rootType: "note"))
    }

    func testExactUTF8SemanticDigestRejectsCanonicallyEquivalentChangedBody() async throws {
        let conversion = try await convert("é")
        let changed = try readback(conversion, mutate: { rows in rows[0]["text"] = .string("e\u{301}") })
        XCTAssertEqual(changed.blocks[0].text.text, conversion.document.blocks[0].text.text)
        XCTAssertNotEqual(Data(changed.blocks[0].text.text.utf8), Data(conversion.document.blocks[0].text.text.utf8))
        XCTAssertThrowsError(try changed.verifiedBody(manifest: conversion.manifest))
    }

    func testStyleRunSegmentationCoalescesButGapsAndSurrogateSplitsRefuse() throws {
        let first = try PinkhaHanlinSavedText(text: "abcd", runs: [.init(offset: 0, length: 4, traits: .bold)])
        let second = try PinkhaHanlinSavedText(text: "abcd", runs: [
            .init(offset: 0, length: 1, traits: .bold), .init(offset: 1, length: 3, traits: .bold)])
        XCTAssertEqual(first, second)
        XCTAssertThrowsError(try PinkhaHanlinSavedText(text: "abcd", runs: [.init(offset: 1, length: 3)]))
        XCTAssertThrowsError(try PinkhaHanlinSavedText(text: "😀", runs: [
            .init(offset: 0, length: 1), .init(offset: 1, length: 1)]))
        XCTAssertThrowsError(try PinkhaHanlinSavedText(text: "a", runs: [
            .init(offset: 0, length: 1, traits: .init(rawValue: 128))]))
    }

    func testCompleteNativeReadbackIsStillNotACommittedAggregateWithoutEffects() async throws {
        let conversion = try await convert("body")
        let witness = try readback(conversion).verifiedBody(manifest: conversion.manifest)
        let initial = try PinkhaHanlinSaveMessageProgress(manifest: conversion.manifest)
        XCTAssertThrowsError(try initial.applying(.bodyVerified(witness)))
        let root = try initial.applying(.rootDispatched).applying(.rootVerified(reference: "native-page",
            readbackSHA256: conversion.manifest.expectedRootReadbackSHA256))
        XCTAssertFalse(root.isReadyForCommit)
        XCTAssertThrowsError(try root.applying(.bodyVerified(witness)))
    }

    private func convert(_ markdown: String) async throws -> PinkhaHanlinMarkdownSaveConversion {
        try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(plan(markdown))
    }

    private func requireUnsupported(_ markdown: String, file: StaticString = #filePath, line: UInt = #line) async throws {
        do { _ = try await convert(markdown); XCTFail("Unsupported structure escaped conversion", file: file, line: line) }
        catch { XCTAssertEqual(error as? PinkhaHanlinSaveMessageError, .unsupportedDocument, file: file, line: line) }
    }

    private func plan(_ markdown: String) throws -> PinkhaHanlinSaveMessagePlan {
        let session = HanlinHostSession(conversationID: UUID(), context: .init(
            namespace: try .init(app: PinkhaHanlinEngineNamespace.any, account: "disposable-account",
                                 workspace: "disposable-space", space: "disposable-space"),
            sceneID: UUID(), generation: UUID()))
        return try .init(invocation: .init(request: .init(id: .init(validating: UUID().uuidString.lowercased()),
            logicalToolID: .init(providerInstanceID: .init(validating: "anytype.host"),
                                localToolID: .init(validating: "save-message")),
            aliasUsed: PinkhaHanlinSaveMessagePlan.alias, descriptorRevision: .init(1), routingTableRevision: .init(1),
            arguments: .object(["title": .string("TITLE"), "markdown": .string(markdown)]),
            origin: .assistantModel, deadline: .now.addingTimeInterval(20),
            limits: .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
            session: session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
            writeGuarantee: .independentObjectCreation, expectedRevision: nil))
    }

    private func readback(_ conversion: PinkhaHanlinMarkdownSaveConversion, title: String? = nil,
                          rootSpace: String = "disposable-space", rootType: String = "page",
                          mutate: (inout [[String: AnyJSON]]) -> Void = { _ in }) throws -> AnyHanlinSaveMessageReadback {
        var rows = conversion.blocks.enumerated().map { index, block -> [String: AnyJSON] in [
            "id": .string("block-\(index)"), "type": .string(block.type), "text": .string(block.text),
            "style": block.style, "nav": .object(["parentId": .string(""), "pos": .string(block.position)]),
            "_ver": .object(["text": .string("native-version-\(index)")])
        ] }
        mutate(&rows)
        let title = title ?? conversion.document.title
        let snapshot = try AnyEditorSnapshot(spaceID: "disposable-space", objectID: "native-page", title: title,
            response: .object(["records": .array(rows.map(AnyJSON.object)),
                               "total": .integer(Int64(rows.count)), "hasNext": .bool(false)]))
        return try .init(snapshot: snapshot, rootRecord: .object([
            "id": .string("native-page"), "spaceId": .string(rootSpace),
            "any": .object(["name": .string(title), "type": .string(rootType)])
        ]), workspace: .init(accountID: "disposable-account", spaceID: "disposable-space"))
    }
}
#endif
