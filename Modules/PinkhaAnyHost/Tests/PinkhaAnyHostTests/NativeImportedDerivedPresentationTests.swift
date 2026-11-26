import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// The migration planner binds historical creator/time definitions to native
/// destination roles. Reading that imported type must keep the destination's
/// signed clocks and identities authoritative, without admitting a write.
final class NativeImportedDerivedPresentationTests: XCTestCase {
    private let roles: [AnyDestinationCanonicalPropertyBinding.DerivedRole] =
        [.author, .createdAt, .modifiedAt, .modifiedBy]

    func testDerivedRecommendationsReadNativeRootValuesAndRemainReadOnly() throws {
        for bookmark in [false, true] {
            let value = try snapshot(bookmark: bookmark)
            let rows = value.rows.filter { $0.id.ownerID == "any" }
            XCTAssertEqual(rows.map(\.id.propertyID), roles.map(\.rawValue))
            XCTAssertEqual(rows.map(\.value), expectedValues)
            XCTAssertTrue(rows.allSatisfy(\.isReadOnly))
            XCTAssertTrue(rows.allSatisfy(\.isVisible))
            XCTAssertEqual(value.rows.count, roles.count + (bookmark ? 1 : 0))
            let store = try makeStore()
            for row in rows {
                XCTAssertThrowsError(try store.prepareSetValue(value, key: row.id,
                    value: .string("forged-source-signer"))) { error in
                    XCTAssertEqual(error as? AnyNativePropertyError, .readOnly)
                }
            }
            if bookmark {
                XCTAssertEqual(value.bookmarkSourceURL?.absoluteString, "https://example.org/source")
                XCTAssertFalse(try XCTUnwrap(value.bookmarkSourceRow).isReadOnly)
            }
            let reader = try snapshot(bookmark: bookmark, canWrite: false)
            XCTAssertTrue(reader.rows.allSatisfy(\.isReadOnly))
            XCTAssertEqual(reader.rows.filter { $0.id.ownerID == "any" }.map(\.value), expectedValues)
        }
    }

    func testDerivedRecommendationsRejectEveryChangedNativeDescriptor() throws {
        let changes: [(inout [String: AnyJSON]) -> Void] = [
            { $0["scope"] = .string("synced") },
            { $0["kind"] = .string("number") },
            { $0["name"] = .string("Source value") },
            { $0["description"] = .string("Unqualified source clock") },
            { $0["xFormat"] = .object(["type": .string("date")]) },
            { $0["additionalAuthority"] = .bool(true) }
        ]
        for role in roles {
            for (index, change) in changes.enumerated() {
                XCTAssertThrowsError(try snapshot(alteredRole: role, change: change),
                    "Changed native descriptor \(role.rawValue), vector \(index)") { error in
                    XCTAssertEqual(error as? AnyNativePropertyError, .invalidCatalog)
                }
            }
        }
    }

    func testDerivedVisibilityDefaultsAndExplicitReopenPreserveNativeAuthority() throws {
        let hidden = try [key("createdAt"), key("modifiedBy")]
        let initial = try snapshot(hidden: hidden)
        XCTAssertEqual(initial.rows.filter { !$0.isVisible }.map(\.id), hidden)
        XCTAssertEqual(initial.rows.map(\.value), expectedValues)
        let reopened = try snapshot(hidden: hidden, storedHidden: [])
        XCTAssertTrue(reopened.rows.allSatisfy(\.isVisible))
        XCTAssertTrue(reopened.rows.allSatisfy(\.isReadOnly))
        XCTAssertEqual(reopened.rows.map(\.value), expectedValues)
        XCTAssertEqual(reopened.raw, try snapshot(hidden: [], storedHidden: []).raw)
    }

    private var expectedValues: [AnyJSON?] {
        [.string("destination-signed-author"), .object(["$date": .integer(1_800_000_000_000)]),
         .object(["$date": .integer(1_800_000_012_345)]), .string("destination-latest-signer")]
    }
    private func key(_ id: String) throws -> AnyNativePropertyKey { try .init(ownerID: "any", propertyID: id) }
    private func address(_ key: AnyNativePropertyKey) -> AnyJSON {
        .object(["ownerId": .string(key.ownerID), "propertyId": .string(key.propertyID)])
    }
    private func makeStore() throws -> AnyNativePropertyStore {
        try .init(client: .init(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account"),
            workspace: .init(accountID: "account", spaceID: "space"), policy: .init())
    }
    private func snapshot(bookmark: Bool = false, canWrite: Bool = true,
                          hidden: [AnyNativePropertyKey] = [], storedHidden: [String]? = nil,
                          alteredRole: AnyDestinationCanonicalPropertyBinding.DerivedRole? = nil,
                          change: (inout [String: AnyJSON]) -> Void = { _ in }) throws -> AnyNativePropertySnapshot {
        var descriptor: [String: AnyJSON] = [
            "contract": .string(bookmark ? AnyNativeImportedTypePresentation.bookmarkContract : AnyNativeImportedTypePresentation.contract),
            "sourceRecommendedLayout": .integer(bookmark ? 11 : 0),
            "featured": .array(try roles.map { address(try key($0.rawValue)) }),
            "recommended": .array([]), "hidden": .array([]), "files": .array([]),
            "definitionHidden": .array(hidden.map(address))
        ]
        var collections: [AnyNativePropertyOwner] = []
        var membership: [String] = []
        var definitions = try roles.map { role in
            var fields = try XCTUnwrap(AnyDestinationCanonicalPropertyBinding.nativeDerivedDescriptor(role).object)
            if role == alteredRole { change(&fields) }
            return try AnyNativePropertyDefinition(ownerID: "any", raw: .object(fields))
        }
        if bookmark {
            let urlKey = try AnyNativePropertyKey(ownerID: "imported-properties", propertyID: "source-url")
            descriptor["propertyOwnerId"] = .string(urlKey.ownerID)
            descriptor["recommended"] = .array([address(urlKey)])
            descriptor["sourceURL"] = address(urlKey)
            collections.append(try .init(raw: .object(["id": .string(urlKey.ownerID)])))
            membership.append(urlKey.ownerID)
            definitions.append(try .init(ownerID: urlKey.ownerID, raw: .object([
                "id": .string(urlKey.propertyID), "kind": .string("string"), "scope": .string("synced"),
                "xFormat": .object(["type": .string("url")])
            ])))
        }
        let type = try AnyNativePropertyOwner(raw: .object([
            "id": .string("imported-type"), "name": .string("Migrated native type"),
            "layout": .object(["type": .string(bookmark ? "bookmark" : "page"),
                "config": .object(["pinkhaHeart": .object(descriptor)])])
        ]), documentEligible: true)
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let catalog = try AnyNativePropertyCatalog(workspace: workspace, generation: UUID(),
            engineStartedAt: "native-run", types: [type], collections: collections)
        var raw: [String: AnyJSON] = [
            "id": .string("native-object"), "spaceId": .string("space"), "_applySeq": .integer(7),
            "_ver": .object(["any": .object(["type": .string("signed-native-version")])]),
            "author": expectedValues[0]!, "createdAt": expectedValues[1]!,
            "modifiedAt": expectedValues[2]!, "modifiedBy": expectedValues[3]!,
            // A same-named property payload must never replace native metadata.
            "any": .object(["type": .string(type.id), "collections": .array(membership.map(AnyJSON.string)),
                "author": .string("forged-shadow-author"), "createdAt": .integer(0),
                "modifiedAt": .integer(0), "modifiedBy": .string("forged-shadow-modifier")])
        ]
        if bookmark { raw["imported-properties"] = .object(["source-url": .string("https://example.org/source")]) }
        if let storedHidden {
            raw[AnyNativePropertyStore.presentationCollectionID] = .object([
                AnyNativePropertyStore.hiddenPropertiesID: .array(storedHidden.map(AnyJSON.string))])
        }
        return try AnyNativePropertyStore.materialize(raw: .object(raw), objectID: "native-object", catalog: catalog,
            definitions: definitions, policy: .init(), canWrite: canWrite)
    }
}
