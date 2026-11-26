import Foundation
import XCTest
@testable import PinkhaKit

final class TorahLegacyAssociationCutoverPlanTests: XCTestCase {
    private let space = "cutover-space-א"
    private let object = "cutover-document"
    private let key = "canonical-property"
    private let codec = TorahAssociationPayloadCodec()

    private func item(_ id: String = "first") -> TorahAssociationItem {
        .init(id: id, kind: .ref, role: .sourceQuote, providerID: "sefaria",
              externalID: "Genesis 1:1", canonicalKey: "Genesis.1.1", labelHe: "בראשית א א",
              labelEn: "Genesis", createdAt: Date(timeIntervalSince1970: 1_795_600_000.125),
              customMetadata: ["unchanged": "exact"],
              unknownFields: ["future": .object(["number": .number(9_007_199_254_740_992),
                                                 "string": .string("preserved / + 😀")])])
    }
    private func location(_ block: String? = nil) -> TorahAssociationLocation {
        .init(spaceId: space, target: block.map { .block(objectId: object, blockId: $0) } ?? .object(objectId: object))
    }
    private func plan(_ raw: Data?) throws -> TorahLegacyAssociationCutoverPlan {
        try .init(spaceID: space, objectID: object, propertyKey: key, propertyValue: raw)
    }
    private func current(_ records: [TorahStoredAssociationRecord], unknown: [String: TorahJSONValue] = [:]) throws -> Data {
        try codec.encodeCanonicalDocument(.init(records: records, unknownFields: unknown))
    }

    func testWholeSourceKeepsEveryUnknownFieldAndExactCanonicalFact() throws {
        let records = [TorahStoredAssociationRecord(location: location(), item: item(),
                                                   unknownFields: ["recordFuture": .bool(true)]),
                       TorahStoredAssociationRecord(location: location("block-b"), item: item("second"))]
        let envelope: [String: TorahJSONValue] = ["envelopeFuture": .array([.null, .number(1.25), .string("exact")])]
        let raw = try current(records, unknown: envelope)
        let value = try plan(raw)
        XCTAssertEqual(value.legacyValue, raw)
        XCTAssertEqual(value.envelopeUnknown, envelope)
        XCTAssertEqual(value.facts.count, records.count)
        for fact in value.facts {
            let payload = try codec.decodeCanonicalDocument(fact.payload, legacyLocation: location())
            XCTAssertEqual(payload.unknownFields, envelope)
            XCTAssertEqual(payload.records.count, 1)
            XCTAssertTrue(records.contains(payload.records[0]))
        }
    }

    func testLegacyV1UsesActualSharedCodecAndRetainsOriginalBytes() throws {
        let raw = try codec.encodeDocument(.init(items: [item()], unknownFields: ["legacyFuture": .string("retained")]))
        let oldRole = Data(String(decoding: raw, as: UTF8.self)
            .replacingOccurrences(of: "\"sourceQuote\"", with: "\"source_quote\"").utf8)
        let value = try plan(oldRole)
        XCTAssertEqual(value.legacyValue, oldRole)
        XCTAssertEqual(value.facts.count, 1)
        let actual = try codec.decodeCanonicalDocument(value.facts[0].payload, legacyLocation: location())
        XCTAssertEqual(actual.records[0].location, location())
        XCTAssertEqual(actual.records[0].item.role, .sourceQuote)
        XCTAssertEqual(actual.unknownFields, ["legacyFuture": .string("retained")])
    }

    func testMissingEmptyAndExplicitEmptyDocumentRemainDistinct() throws {
        let missing = try plan(nil)
        let empty = try plan(Data())
        let json = try plan(current([], unknown: ["futureEmpty": .string("retained")]))
        XCTAssertFalse(missing.valuePresent)
        XCTAssertTrue(empty.valuePresent)
        XCTAssertEqual(missing.facts, [])
        XCTAssertEqual(empty.facts, [])
        XCTAssertEqual(json.facts, [])
        XCTAssertNotEqual(try missing.canonicalBytes(), try empty.canonicalBytes())
        XCTAssertNotEqual(try empty.canonicalBytes(), try json.canonicalBytes())
        XCTAssertEqual(json.envelopeUnknown, ["futureEmpty": .string("retained")])
    }

    func testDuplicateIdentityIsRefusedWithoutDroppingOneRecord() throws {
        var divergent = item()
        divergent.labelHe = "different"
        XCTAssertThrowsError(try plan(current([
            .init(location: location(), item: item()),
            .init(location: location(), item: divergent)
        ])))
    }

    func testForeignOwnersMalformedTargetsAndProviderRefuse() throws {
        let foreign = TorahAssociationLocation(spaceId: "foreign", target: .object(objectId: object))
        XCTAssertThrowsError(try plan(current([.init(location: foreign, item: item())])))
        XCTAssertThrowsError(try plan(current([.init(location: location(""), item: item())])))
        var emptyProvider = item(); emptyProvider.providerID = ""
        XCTAssertThrowsError(try plan(current([.init(location: location(), item: emptyProvider)])))
        var emptyRef = item(); emptyRef.externalID = ""; emptyRef.canonicalKey = ""
        XCTAssertThrowsError(try plan(current([.init(location: location(), item: emptyRef)])))
    }

    func testNumericPrecisionAndEscapedDuplicateKeyRefuse() throws {
        let raw = try current([.init(location: location(), item: item())])
        let unsafe = Data(String(decoding: raw, as: UTF8.self)
            .replacingOccurrences(of: "9007199254740992", with: "9007199254740993").utf8)
        XCTAssertThrowsError(try plan(unsafe))
        let duplicate = Data(String(decoding: raw, as: UTF8.self)
            .replacingOccurrences(of: "\"id\":\"first\"", with: "\"id\":\"first\",\"i\\u0064\":\"second\"").utf8)
        XCTAssertThrowsError(try plan(duplicate))
    }

    func testSemanticOwnersAndTwoSameVerseAnchorsStayDistinct() throws {
        var records: [TorahStoredAssociationRecord] = []
        for (id, uuid) in [("one", "11111111-1111-4111-8111-111111111111"),
                           ("two", "22222222-2222-4222-8222-222222222222")] {
            let anchor = try PinkhaSemanticTextAnchor(spaceID: space, objectID: object, id: UUID(uuidString: uuid)!)
            let linked = try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: item(id), location: location())
            records.append(.init(location: location(), item: linked))
        }
        let value = try plan(current(records))
        XCTAssertEqual(value.facts.count, 2)
        XCTAssertNotEqual(value.facts[0].payload, value.facts[1].payload)
        var foreign = records[0]
        foreign.objectId = "foreign-document"
        XCTAssertThrowsError(try plan(current([foreign])))
        var blockOwned = records[0]; blockOwned.blockId = "block"
        XCTAssertThrowsError(try plan(current([blockOwned])))
    }

    func testUnrepresentableLegacyUnknownEnvelopeRefusesEvenWhenEmpty() throws {
        let raw = try codec.encodeDocument(.init(items: [], unknownFields: ["records": .string("must not disappear")]))
        XCTAssertThrowsError(try plan(raw))
    }

    func testOwnedSourceAndCanonicalOrderingAreStable() throws {
        var raw = try current([.init(location: location(), item: item("z")),
                               .init(location: location("block"), item: item("a"))])
        let value = try plan(raw)
        let before = value.legacyValue
        let frame = try value.canonicalBytes()
        raw.removeAll()
        XCTAssertEqual(value.legacyValue, before)
        XCTAssertEqual(try value.canonicalBytes(), frame)
        let wires = try value.facts.map { try $0.canonicalBytes(spaceID: space, objectID: object) }
        XCTAssertEqual(wires, wires.sorted { $0.lexicographicallyPrecedes($1) })
    }

    func testExportActualSharedCodecVectorsForIndependentNativeCoverage() throws {
        guard let output = ProcessInfo.processInfo.environment["PINKHA_CUTOVER_VECTORS"] else {
            XCTFail("explicit owned vector artifact path is required"); return
        }
        let document = try current([.init(location: location(), item: item(),
                                          unknownFields: ["recordFuture": .array([.number(1.25), .bool(false)])])],
                                   unknown: ["outer": .string("exact")])
        let blocks = try current([.init(location: location("first-block"), item: item("first")),
                                   .init(location: location(), item: item("second"))],
                                  unknown: ["future": .object(["count": .number(1_000)])])
        let legacy = try codec.encodeDocument(.init(items: [item()],
                                                    unknownFields: ["old": .string("exact")]))
        let oldRole = Data(String(decoding: legacy, as: UTF8.self)
            .replacingOccurrences(of: "\"sourceQuote\"", with: "\"source_quote\"").utf8)
        let exponent = Data(String(decoding: blocks, as: UTF8.self)
            .replacingOccurrences(of: "\"count\":1000", with: "\"count\":10.000e2").utf8)
        XCTAssertNotEqual(exponent, blocks)
        let utc = ISO8601DateFormatter()
        utc.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        utc.timeZone = TimeZone(secondsFromGMT: 0)
        let offset = ISO8601DateFormatter()
        offset.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        offset.timeZone = TimeZone(secondsFromGMT: 7_200)
        let timestamp = item().createdAt!
        let offsetDate = Data(String(decoding: document, as: UTF8.self)
            .replacingOccurrences(of: utc.string(from: timestamp), with: offset.string(from: timestamp)).utf8)
        XCTAssertNotEqual(offsetDate, document)
        let anchor = try PinkhaSemanticTextAnchor(spaceID: space, objectID: object,
                                                  id: UUID(uuidString: "33333333-3333-4333-8333-333333333333")!)
        let semantic = try current([.init(location: location(), item:
            TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: item("semantic"), location: location()))])
        let inputs: [(String, Data?)] = [
            ("missing", nil), ("present-empty", Data()),
            ("empty-with-unknown", try current([], unknown: ["future": .string("retained")])),
            ("document-unknown", document), ("blocks-order", blocks), ("legacy-role", oldRole),
            ("exact-exponent", exponent), ("known-date", offsetDate), ("semantic-owner", semantic)
        ]
        struct Vector: Encodable { let name: String; let wire: Data; let canonical: Data }
        var vectors: [Vector] = []
        for (name, input) in inputs {
            let value = try plan(input)
            vectors.append(.init(name: name, wire: try value.wireData(), canonical: try value.canonicalBytes()))
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        try encoder.encode(vectors).write(to: URL(fileURLWithPath: output), options: .atomic)
        XCTAssertEqual(vectors.count, 9)
    }
}
