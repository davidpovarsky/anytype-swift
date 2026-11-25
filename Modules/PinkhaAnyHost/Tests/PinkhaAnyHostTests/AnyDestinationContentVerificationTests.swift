import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class AnyDestinationContentVerificationTests: XCTestCase, @unchecked Sendable {
    func testContentComparisonPreservesExactUnicodeBytes() throws {
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.equal(.string("é"), .string("e\u{301}"), "source", "text"))
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.equal(.string(""), nil, "source", "property presence"))
        XCTAssertNoThrow(try AnyDestinationMigrationVerifier.equal(.array([]), .array([]), "source", "empty value"))
    }

    func testDateWireComparisonUsesExactMillisecondsWithoutChangingOrdinaryJSON() throws {
        let expected = AnyJSON.object(["$date": .integer(1_700_000_000_123)])
        let actual = AnyJSON.object(["$date": .string("2023-11-14T22:13:20.123Z")])
        XCTAssertEqual(try AnyDestinationContentProjection.propertyValue(expected, kind: "datetime"),
                       try AnyDestinationContentProjection.propertyValue(actual, kind: "datetime"))
        let changed = AnyJSON.object(["$date": .string("2023-11-14T22:13:20.124Z")])
        XCTAssertNotEqual(try AnyDestinationContentProjection.propertyValue(expected, kind: "datetime"),
                          try AnyDestinationContentProjection.propertyValue(changed, kind: "datetime"))
        XCTAssertEqual(try AnyDestinationContentProjection.propertyValue(actual, kind: "object"), actual)
        XCTAssertThrowsError(try AnyDestinationContentProjection.propertyValue(
            .object(["$date": .string("2023-11-14T22:13:20.1234Z")]), kind: "datetime"))
    }

    func testUnknownSchemaAndChangedPinnedFieldCannotDisappearInProjection() throws {
        XCTAssertThrowsError(try AnyDestinationContentProjection.root(
            .object(["id": .string("type"), "xKey": .string("type"), "futureBehavior": .bool(true)]), type: true))
        let property = AnyJSON.object(["id": .string("property"), "kind": .string("string"), "scope": .string("synced")])
        let changed = AnyJSON.object(["id": .string("property"), "kind": .string("string"), "scope": .string("local")])
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.equal(
            AnyDestinationContentProjection.property(property), AnyDestinationContentProjection.property(changed),
            "source", "scope"))
        let bad = AnyJSON.object(["id": .string("property"), "kind": .string("string"), "futureConstraint": .string("read-only")])
        XCTAssertThrowsError(try AnyDestinationContentProjection.property(bad))
    }

    func testNativeVariantMetadataCannotBeAcceptedAsAnOriginalFile() throws {
        let original = AnyJSON.object(["fileId": .string("file"), "objectId": .string("owner"),
            "size": .integer(8192), "inline": .bool(false)])
        let variant = AnyJSON.object(["fileId": .string("file"), "objectId": .string("owner"),
            "size": .integer(8192), "inline": .bool(false), "variant": .string("thumbnail"), "variantOf": .string("other")])
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.equal(
            AnyDestinationContentProjection.file(original), AnyDestinationContentProjection.file(variant), "source", "variant"))
    }


    /// Original SDK compile.go sorts same-change declarations by byte key,
    /// while allocated native record identities stay in source declaration order.
    func testNativeCompiledDeclarationOrderPreservesAllocatedRecordIdentities() throws {
        let draft: AnyJSON = .object(["key": .string("main"), "uses": .array([.string("z-use"), .string("a-use")]),
            "datasets": .array([
                .object(["key": .string("notes"), "module": .string("records"),
                    "fields": .array([
                        .object(["key": .string("title"), "kind": .string("string"), "required": .bool(true)]),
                        .object(["key": .string("score"), "kind": .string("number")])]),
                    "indexes": .array([
                        .object(["key": .string("last"), "fields": .array([.string("title")])]),
                        .object(["key": .string("first"), "fields": .array([.string("score")])])])]),
                .object(["module": .string("editor")])])])
        let expected = try AnyDestinationContentProjection.part(draft: draft, owner: "owner",
            recordIDs: ["part", "notes-id", "title-id", "score-id", "last-id", "first-id", "editor-id"])
        var title: [String: AnyJSON] = ["id": .string("title-id"), "key": .string("title"),
            "kind": .string("string"), "scope": .string("synced"), "mutableBy": .string("never"), "required": .bool(true)]
        let score: AnyJSON = .object(["id": .string("score-id"), "key": .string("score"),
            "kind": .string("number"), "scope": .string("synced"), "mutableBy": .string("never")])
        let editor: AnyJSON = .object(["id": .string("editor-id"), "partId": .string("part"),
            "module": .string("editor"), "key": .string("editor_blocks"), "collection": .string("editor_blocks"),
            "idRule": .string("auto"), "deleteBy": .string("anyone")])
        func native(_ title: [String: AnyJSON], reverseFields: Bool = false) throws -> AnyJSON {
            let fields: [AnyJSON] = reverseFields ? [.object(title), score] : [score, .object(title)]
            return try AnyDestinationContentProjection.part(.object(["id": .string("part"), "key": .string("main"),
                "uses": .array([.string("a-use"), .string("z-use")]), "datasets": .array([editor,
                    .object(["id": .string("notes-id"), "partId": .string("part"), "module": .string("records"),
                        "key": .string("notes"), "collection": .string("owner_notes"),
                        "idRule": .string("auto"), "deleteBy": .string("anyone"), "fields": .array(fields),
                        "indexes": .array([
                            .object(["id": .string("first-id"), "key": .string("first"), "fields": .array([.string("score")])]),
                            .object(["id": .string("last-id"), "key": .string("last"), "fields": .array([.string("title")])])])])])]))
        }
        XCTAssertNoThrow(try AnyDestinationMigrationVerifier.equal(expected, native(title), "part", "schema"))
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.equal(expected, native(title, reverseFields: true), "part", "order"))
        title["id"] = .string("score-id")
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.equal(expected, native(title), "part", "record identity"))
        title["id"] = .string("title-id"); title["required"] = .bool(false)
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.equal(expected, native(title), "part", "required"))
    }

    func testWholeSourceBlockerPrecedesAnyNativeReadOrAuthorityCallback() async throws {
        let source = try AnyDestinationSourceBinding(accountID: "component-source", spaceID: "component-space",
            witnessSHA256: String(repeating: "a", count: 64), captureManifestSHA256: String(repeating: "b", count: 64),
            semanticPlanSHA256: String(repeating: "c", count: 64), sourceObjectIDs: ["page", "unsupported-layout"])
        let plan = try AnyDestinationMigrationPlan(source: source, workspace: .init(accountID: "target", spaceID: "space"),
            storeID: "store", planID: AnyContentDigest.sha256(Data("blocked-component-plan".utf8)),
            coverage: [.init(sourceObjectID: "page", disposition: .mapped(itemSourceKeys: ["page"])),
                       .init(sourceObjectID: "unsupported-layout", disposition: .blocked(reasons: ["layout not implemented"]))],
            items: [.init(sourceKey: "page", sourceObjectID: "page",
                          operation: .object(type: .native("page"), collections: [], initialProperties: .literal(.object([:]))))])
        let progress = AnyDestinationMigrationProgress(binding: plan.binding, source: source, mappings: [],
            totalItems: 1, allItemsReconciled: false, verificationIntents: [])
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "target")
        let verifier = AnyDestinationMigrationVerifier(client: client)
        do {
            _ = try await verifier.verify(plan: plan, progress: progress,
                verifySource: { _ in throw VerificationControlFailure.unexpectedAuthorityCall },
                authorize: { throw VerificationControlFailure.unexpectedAuthorityCall })
            XCTFail("Blocked whole-source semantics were admitted")
        } catch {
            XCTAssertEqual(error as? AnyDestinationMigrationError, .incompleteCoverage("layout not implemented"))
        }
    }
}
private enum VerificationControlFailure: Error { case unexpectedAuthorityCall }
