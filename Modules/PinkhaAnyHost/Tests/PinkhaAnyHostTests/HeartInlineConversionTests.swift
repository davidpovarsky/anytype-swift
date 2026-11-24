import XCTest
import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class HeartInlineConversionTests: XCTestCase {
    private struct Fixture: Decodable {
        let name: String
        let source: String
        let expectedText: String
        let convertible: Bool
        let projection: AnyJSON
    }

    private func fixtures() throws -> [Fixture] {
        var root = URL(fileURLWithPath: #filePath)
        for _ in 0..<5 { root.deleteLastPathComponent() }
        let path = root.appendingPathComponent("Tools/AnyEnginePort/semantic_projection/testdata/inline-v1.json")
        return try JSONDecoder().decode([Fixture].self, from: Data(contentsOf: path))
    }

    private func projection(_ fixture: Fixture) throws -> AnyHeartInlineProjection {
        try .init(source: fixture.source, nativeProjection: JSONEncoder().encode(fixture.projection))
    }

    func testActualNativeCodecFixturesPreserveDestinationSemantics() throws {
        let cases = try fixtures().filter(\.convertible)
        XCTAssertGreaterThanOrEqual(cases.count, 5)
        for fixture in cases {
            let source = try projection(fixture)
            XCTAssertEqual(Data(source.text.utf8), Data(fixture.expectedText.utf8), fixture.name)
            let result = try AnyHeartInlineConversion(source)
            let parsed = source.literal ? AnyInlineMarkdown(literal: result.inlineMarkdown) : AnyInlineMarkdown(result.inlineMarkdown)
            XCTAssertTrue(parsed.isEditable, fixture.name)
            XCTAssertEqual(Data(parsed.display.utf8), Data(fixture.expectedText.utf8), fixture.name)
            XCTAssertEqual(result.sourceSHA256, source.sourceSHA256)
        }
    }

    func testUnsupportedSemanticsRemainExplicit() throws {
        let cases = try fixtures().filter { !$0.convertible }
        XCTAssertGreaterThanOrEqual(cases.count, 3)
        for fixture in cases {
            let source = try projection(fixture)
            XCTAssertEqual(Data(source.text.utf8), Data(fixture.expectedText.utf8), fixture.name)
            XCTAssertThrowsError(try AnyHeartInlineConversion(source), fixture.name)
        }
    }

    func testProjectionRejectsChangedSourceBytes() throws {
        let sample = try XCTUnwrap(fixtures().first)
        let bytes = try JSONEncoder().encode(sample.projection)
        XCTAssertThrowsError(try AnyHeartInlineProjection(source: sample.source + " ", nativeProjection: bytes)) {
            XCTAssertEqual($0 as? AnyHeartInlineProjectionError, .invalidBinding)
        }
    }

    func testProjectionRejectsSurrogateSplittingNativeRange() throws {
        let fixture = try XCTUnwrap(fixtures().first { $0.name == "hebrew-emoji-bold" })
        var value = try XCTUnwrap(fixture.projection.object)
        value["marks"] = .array([.object([
            "kind": .string("bold"), "start": .integer(2), "end": .integer(3), "parameter": .string("")
        ])])
        XCTAssertThrowsError(try AnyHeartInlineProjection(source: fixture.source,
            nativeProjection: JSONEncoder().encode(AnyJSON.object(value)))) {
            XCTAssertEqual($0 as? AnyHeartInlineProjectionError, .invalidRange)
        }
    }

    private func archive(_ blocks: [AnyJSON]) throws -> AnyHeartSpaceArchive {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try .init(sourceSpaceID: "source-space", entries: [
            .init(path: "index.json", bytes: encoder.encode(AnyJSON.object([
                "formatVersion": .string("2.0"), "manifest": .object([:])
            ]))),
            .init(path: "page.json", bytes: encoder.encode(AnyJSON.object([
                "formatVersion": .string("2.0"), "id": .string("page"), "blocks": .array(blocks)
            ])))
        ])
    }

    func testTextBlockPlanRetainsHierarchyAndNativeStyleVocabulary() throws {
        let fixture = try XCTUnwrap(fixtures().first { $0.name == "plain-hebrew" })
        let code = try XCTUnwrap(fixtures().first { $0.name == "literal-code" })
        let types = ["paragraph", "heading_1", "heading_2", "heading_3", "quote", "code",
                     "bulleted_list_item", "numbered_list_item", "checkbox"]
        var blocks: [AnyJSON] = []
        var projections: [AnyHeartTextBlockPlan.Identity: AnyHeartInlineProjection] = [:]
        for (i, type) in types.enumerated() {
            let selected = type == "code" ? code : fixture
            let id = "block-" + String(i)
            var value: [String: AnyJSON] = ["id": .string(id), "type": .string(type),
                "indent": .integer([1, 7, 8].contains(i) ? 1 : 0), "text": .string(selected.source)]
            if type == "code" { value["language"] = .string("swift") }
            if type == "checkbox" { value["checked"] = .bool(true) }
            blocks.append(.object(value))
            projections[.init(kind: .block, sourceSpaceID: "source-space", sourceObjectID: "page", sourceID: id)] = try projection(selected)
        }
        let source = try archive(blocks)
        let plan = try AnyHeartTextBlockPlan(archive: source, sourceObjectID: "page", projections: projections)
        XCTAssertEqual(plan.entries.map(\.type), ["paragraph", "heading", "heading", "heading", "quote", "code", "list_item", "list_item", "check_list_item"])
        XCTAssertEqual(plan.entries[1].parent, plan.entries[0].identity)
        XCTAssertEqual(plan.entries[7].parent, plan.entries[6].identity)
        XCTAssertEqual(plan.entries[8].parent, plan.entries[6].identity)
        XCTAssertEqual(plan.entries[2].style["level"]?.integer, 2)
        XCTAssertEqual(plan.entries[5].style["lang"]?.string, "swift")
        XCTAssertEqual(plan.entries[5].text, code.source)
        XCTAssertEqual(plan.entries[6].style["ordered"]?.bool, false)
        XCTAssertEqual(plan.entries[7].style["ordered"]?.bool, true)
        XCTAssertEqual(plan.entries[7].style["number"]?.integer, 1)
        XCTAssertEqual(plan.entries[8].style["checked"]?.bool, true)
        XCTAssertTrue(plan.entries.allSatisfy { AnyLexicographicPosition.isValid($0.position) })
        XCTAssertLessThan(plan.entries[7].position, plan.entries[8].position)
        XCTAssertEqual(plan.entries.map(\.originalNative), blocks)
        XCTAssertEqual(plan.archiveSHA256, source.contentSHA256)
        XCTAssertFalse(plan.permitsDestinationWrites)
    }

    func testTextBlockPlanRefusesUnknownMetadataAndForeignProjection() throws {
        let fixture = try XCTUnwrap(fixtures().first { $0.name == "plain-hebrew" })
        let native = try projection(fixture)
        let id = AnyHeartTextBlockPlan.Identity(kind: .block, sourceSpaceID: "source-space", sourceObjectID: "page", sourceID: "block")
        var block: [String: AnyJSON] = ["id": .string("block"), "type": .string("paragraph"), "text": .string(fixture.source)]
        block["color"] = .string("red")
        XCTAssertThrowsError(try AnyHeartTextBlockPlan(archive: archive([.object(block)]), sourceObjectID: "page", projections: [id: native])) {
            XCTAssertEqual($0 as? AnyHeartTextBlockPlanError, .unsupportedMetadata("color"))
        }
        block.removeValue(forKey: "color")
        let foreign = AnyHeartTextBlockPlan.Identity(kind: .block, sourceSpaceID: "foreign-space", sourceObjectID: "page", sourceID: "block")
        XCTAssertThrowsError(try AnyHeartTextBlockPlan(archive: archive([.object(block)]), sourceObjectID: "page", projections: [foreign: native])) {
            XCTAssertEqual($0 as? AnyHeartTextBlockPlanError, .unboundProjection)
        }
    }
}
