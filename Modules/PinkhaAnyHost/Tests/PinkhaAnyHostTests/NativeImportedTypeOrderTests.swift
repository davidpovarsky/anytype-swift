import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativeImportedTypeOrderTests: XCTestCase {
    private func owner(_ id: String, scope: String = String(repeating: "a", count: 64),
                       order: String? = nil, builtIn: Bool = false, marked: Bool = true,
                       eligible: Bool = true,
                       change: (inout [String: AnyJSON]) -> Void = { _ in }) throws -> AnyNativePropertyOwner {
        var metadata: [String: AnyJSON] = [
            "heartTypeOrderContract": .string(AnyNativeImportedTypeOrder.contract),
            "heartTypeOrderScopeSHA256": .string(scope),
            "heartSourceObjectID": .string("source-" + id),
            "heartTypeKey": .string("kind" + id),
            "heartUniqueKey": .string("ot-kind" + id),
            "heartSnapshotSHA256": .string(String(repeating: "b", count: 64)),
            "heartJSONViewSHA256": .string(String(repeating: "c", count: 64)),
        ]
        if let order { metadata["heartTypeOrderValue"] = .string(order) }
        change(&metadata)
        var raw: [String: AnyJSON] = [
            "id": .string(id), "name": .string("Original " + id),
            "builtIn": .bool(builtIn), "unrelated": .string("retained"),
        ]
        if marked { raw["meta"] = .object(metadata) }
        return try AnyNativePropertyOwner(raw: .object(raw), documentEligible: eligible)
    }

    func testSourceGroupsSortOnlyTheirSlotsAndPreserveOwnersAndStableTies() throws {
        let input = try [
            owner("a", order: "z"), owner("page", builtIn: true, marked: false),
            owner("b", scope: String(repeating: "d", count: 64), order: "z"),
            owner("c", order: "a"), owner("ordinary", marked: false),
            owner("d", scope: String(repeating: "d", count: 64), order: "a"),
            owner("tie", order: "a"),
        ]
        let output = try AnyNativeImportedTypeOrder.arranged(input)
        XCTAssertEqual(output.map(\.id), ["c", "page", "d", "tie", "ordinary", "b", "a"])
        XCTAssertEqual(Dictionary(uniqueKeysWithValues: output.map { ($0.id, $0.raw) }),
                       Dictionary(uniqueKeysWithValues: input.map { ($0.id, $0.raw) }))
        XCTAssertEqual(try AnyNativeImportedTypeOrder.arranged(output).map(\.id), output.map(\.id))
    }

    func testAbsentAndEmptyRanksStayDistinctAndBothSortAfterExplicitRanks() throws {
        let input = try [owner("absent"), owner("empty", order: ""), owner("rank", order: "A"),
                         owner("utf8", order: "a\u{301}"), owner("composed", order: "\u{e1}")]
        let absent = try XCTUnwrap(AnyNativeImportedTypeOrder(owner: input[0]))
        let empty = try XCTUnwrap(AnyNativeImportedTypeOrder(owner: input[1]))
        XCTAssertNil(absent.orderID)
        XCTAssertEqual(empty.orderID, "")
        XCTAssertNil(input[0].raw["meta"]?["heartTypeOrderValue"])
        XCTAssertEqual(input[1].raw["meta"]?["heartTypeOrderValue"], .string(""))
        XCTAssertEqual(try AnyNativeImportedTypeOrder.arranged(input).map(\.id),
                       ["rank", "utf8", "composed", "absent", "empty"])
    }

    func testMalformedClaimsAndBuiltinOrDuplicateSourceOwnershipAreRefused() throws {
        let changes: [(inout [String: AnyJSON]) -> Void] = [
            { $0["heartTypeOrderContract"] = .string("future") },
            { $0.removeValue(forKey: "heartTypeOrderContract") },
            { $0["heartTypeOrderScopeSHA256"] = .string("foreign-unbound-scope") },
            { $0["heartTypeOrderValue"] = .null },
            { $0["heartTypeOrderValue"] = .integer(1) },
            { $0["heartTypeOrderValue"] = .string(String(repeating: "x", count: 65_537)) },
            { $0["heartTypeOrderFutureRule"] = .bool(true) },
            { $0["heartUniqueKey"] = .string("ot-wrong") },
            { $0["heartSnapshotSHA256"] = .string("unknown") },
        ]
        for change in changes {
            XCTAssertThrowsError(try AnyNativeImportedTypeOrder.arranged([owner("x", change: change)]))
        }
        XCTAssertThrowsError(try AnyNativeImportedTypeOrder.arranged([owner("page", builtIn: true)]))
        let duplicate = try owner("second") { $0["heartSourceObjectID"] = .string("source-first") }
        XCTAssertThrowsError(try AnyNativeImportedTypeOrder.arranged([owner("first"), duplicate]))
        let legacy = try owner("legacy", marked: false)
        XCTAssertEqual(try AnyNativeImportedTypeOrder.arranged([legacy]), [legacy])
    }

    func testCatalogOrderingDoesNotGrantDocumentEligibilityOrReorderCollections() throws {
        let first = try owner("first", order: "z")
        let blocked = try owner("blocked", order: "a", eligible: false)
        let collection = try owner("collection", marked: false)
        let catalog = try AnyNativePropertyCatalog(
            workspace: .init(accountID: "account", spaceID: "space"),
            generation: UUID(), engineStartedAt: "original-start",
            types: [first, blocked], collections: [collection])
        XCTAssertEqual(catalog.types.map(\.id), ["blocked", "first"])
        XCTAssertEqual(catalog.selectableDocumentTypes.map(\.id), ["first"])
        XCTAssertEqual(catalog.collections, [collection])
        XCTAssertFalse(catalog.types[0].documentEligible)
    }
}
