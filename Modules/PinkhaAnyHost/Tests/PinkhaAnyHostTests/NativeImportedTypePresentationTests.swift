import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativeImportedTypePresentationTests: XCTestCase {
    func testImportedTypeOrderAndDefaultsPreserveCanonicalTitleAndPresentEmptyValues() throws {
        let value = try snapshot()
        XCTAssertEqual(value.rows.filter(\.isVisible).map { $0.id.propertyID },
            ["beta", "name", "alpha", "count", "empty", "emptyList", "flag"])
        XCTAssertEqual(value.rows.filter { !$0.isVisible && $0.id.ownerID == "imported" }.map { $0.id.propertyID },
                       ["secret", "gamma"])
        XCTAssertEqual(value.rows.filter { $0.id == (try? key("any", "name")) }.count, 1)
        XCTAssertTrue(value.rows.contains { $0.id.propertyID == "flag" && $0.value == .bool(false) && $0.isVisible })
        XCTAssertTrue(value.rows.contains { $0.id.propertyID == "count" && $0.value == .integer(0) && $0.isVisible })
        XCTAssertTrue(value.rows.contains { $0.id.propertyID == "empty" && $0.value == .string("") && $0.isVisible })
        XCTAssertTrue(value.rows.contains { $0.id.propertyID == "emptyList" && $0.value == .array([]) && $0.isVisible })
        XCTAssertEqual(value.raw["unrelated"], .object(["source": .string("retained")]))
        XCTAssertFalse(value.presentationAttached)
        XCTAssertEqual(value.hiddenPropertyKeys, try Set([key("imported", "secret"), key("imported", "gamma")].map(\.visibilityKey)))
    }

    func testFirstVisibilityWriteMaterializesDefaultsAndAnExplicitShowSurvivesReopen() throws {
        let value = try snapshot(attached: true)
        let shown = try key("imported", "gamma")
        let edit = try store().prepareVisibility(value, key: .init(property: shown), visible: true)
        XCTAssertEqual(edit.ownerID, AnyNativePropertyStore.presentationCollectionID)
        XCTAssertEqual(edit.patch, [AnyNativePropertyStore.hiddenPropertiesID: .array([
            .string(try key("imported", "secret").visibilityKey)])])
        XCTAssertEqual(edit.inversePatch, [AnyNativePropertyStore.hiddenPropertiesID: .null])
        XCTAssertEqual(edit.nativeVersion, value.nativeVersion)
        XCTAssertEqual(edit.applySequence, value.applySequence)
        let persisted = try XCTUnwrap(edit.patch[AnyNativePropertyStore.hiddenPropertiesID]?.array?.compactMap(\.string))
        let reopened = try snapshot(attached: true, storedHidden: persisted)
        XCTAssertTrue(try XCTUnwrap(reopened.rows.first { $0.id == shown }).isVisible)
        XCTAssertFalse(try XCTUnwrap(reopened.rows.first { $0.id == (try? key("imported", "secret")) }).isVisible)
        XCTAssertEqual(reopened.hiddenPropertyKeys, Set(persisted))
        XCTAssertEqual(reopened.raw["imported"], value.raw["imported"])
    }

    func testExplicitEmptyPreferencesAndFutureKeysOverrideDefaultsWithoutChangingPolicy() throws {
        let showAll = try snapshot(attached: true, storedHidden: [])
        XCTAssertTrue(showAll.rows.filter { $0.id.ownerID == "imported" }.allSatisfy(\.isVisible))
        XCTAssertTrue(showAll.hiddenPropertyKeys.isEmpty)
        XCTAssertFalse(try XCTUnwrap(showAll.rows.first { $0.id == (try? key("any", "type")) }).isVisible)
        let future = "future:v9:retained"
        let value = try snapshot(attached: true, storedHidden: [future])
        let edit = try store().prepareVisibility(value,
            key: .init(property: key("imported", "alpha")), visible: false)
        XCTAssertEqual(Set(try XCTUnwrap(edit.patch[AnyNativePropertyStore.hiddenPropertiesID]?.array?.compactMap(\.string))),
                       [future, try key("imported", "alpha").visibilityKey])
        XCTAssertEqual(edit.inversePatch[AnyNativePropertyStore.hiddenPropertiesID], .array([.string(future)]))
    }

    func testUnsupportedLayoutsAmbiguousPairsAndForeignOwnersCannotChangePresentation() throws {
        let changes: [(inout [String: AnyJSON]) -> Void] = [
            { $0["contract"] = .string("unrelated-contract") },
            { _ = $0.removeValue(forKey: "contract") },
            { $0["sourceRecommendedLayout"] = .integer(1) },
            { $0["sourceRecommendedLayout"] = .null },
            { $0["propertyOwnerId"] = .string("missing") },
            { $0["featured"] = .array([Self.address("unrelated", "source")]) },
            { $0["featured"] = .array([Self.address("any", "type")]) },
            { $0["featured"] = .array([Self.address("imported", "missing")]) },
            { $0["featured"] = .array([Self.address("imported", "beta"), Self.address("imported", "beta")]) },
            { $0["unknownVisibilityRule"] = .bool(true) }
        ]
        for (index, change) in changes.enumerated() {
            XCTAssertThrowsError(try snapshot(change: change), "Unsupported imported presentation \(index)")
        }
        XCTAssertThrowsError(try snapshot(includeForeignDefinition: true, change: {
            $0["featured"] = .array([Self.address("unrelated", "source")])
        }), "An existing attached foreign property is still outside the imported binding")
        let ordinary = try snapshot(includeImportedMarker: false)
        XCTAssertTrue(ordinary.rows.filter { $0.id.ownerID == "imported" }.allSatisfy(\.isVisible))
    }

    func testDefinitionHiddenPreservesCanonicalTitleAndExplicitPreferencesAcrossReopen() throws {
        let change: (inout [String: AnyJSON]) -> Void = {
            $0["definitionHidden"] = .array([Self.address("any", "name"), Self.address("imported", "flag")])
        }
        let value = try snapshot(attached: true, change: change)
        let name = try key("any", "name"), flag = try key("imported", "flag")
        XCTAssertEqual(value.raw["any"]?["name"], .string("כותרת המקור"))
        XCTAssertNil(value.raw["imported"]?["name"])
        XCTAssertEqual(value.rows.filter { $0.id == name }.count, 1)
        XCTAssertFalse(try XCTUnwrap(value.rows.first { $0.id == name }).isVisible)
        XCTAssertFalse(try XCTUnwrap(value.rows.first { $0.id == flag }).isVisible)
        XCTAssertEqual(try XCTUnwrap(value.rows.first { $0.id == flag }).value, .bool(false))
        let titleEdit = try store().prepareSetValue(value, key: name, value: .string("כותרת חדשה"))
        XCTAssertEqual(titleEdit.ownerID, "any")
        XCTAssertEqual(titleEdit.patch, ["name": .string("כותרת חדשה")])
        let visibility = try store().prepareVisibility(value, key: .init(property: name), visible: true)
        let persisted = try XCTUnwrap(visibility.patch[AnyNativePropertyStore.hiddenPropertiesID]?.array?.compactMap(\.string))
        XCTAssertFalse(persisted.contains(name.visibilityKey))
        XCTAssertTrue(persisted.contains(flag.visibilityKey))
        XCTAssertTrue(persisted.contains(try key("imported", "secret").visibilityKey))
        let reopened = try snapshot(attached: true, storedHidden: persisted, change: change)
        XCTAssertTrue(try XCTUnwrap(reopened.rows.first { $0.id == name }).isVisible)
        XCTAssertFalse(try XCTUnwrap(reopened.rows.first { $0.id == flag }).isVisible)
        XCTAssertEqual(reopened.raw["any"]?["name"], value.raw["any"]?["name"])
        let explicitShowAll = try snapshot(attached: true, storedHidden: [], change: change)
        XCTAssertTrue(try XCTUnwrap(explicitShowAll.rows.first { $0.id == name }).isVisible)
        XCTAssertTrue(try XCTUnwrap(explicitShowAll.rows.first { $0.id == flag }).isVisible)
        for malformed in [
            AnyJSON.null,
            .array([Self.address("any", "type")]),
            .array([Self.address("unrelated", "source")]),
            .array([Self.address("any", "name"), Self.address("any", "name")])
        ] {
            XCTAssertThrowsError(try snapshot(includeForeignDefinition: true, change: {
                $0["definitionHidden"] = malformed
            }))
        }
    }

    func testPresentationDefaultsGrantNoWriteAuthorityAndPreserveTheNativeFence() throws {
        let reader = try snapshot(attached: true, canWrite: false)
        XCTAssertTrue(reader.rows.allSatisfy(\.isReadOnly))
        XCTAssertThrowsError(try store().prepareSetValue(reader, key: key("any", "name"), value: .string("forged")))
        XCTAssertThrowsError(try store().prepareVisibility(reader,
            key: .init(property: key("imported", "gamma")), visible: true))
        let writer = try snapshot(attached: true)
        let edit = try store().prepareSetValue(writer, key: key("any", "name"), value: .string("כותרת חדשה"))
        XCTAssertEqual(edit.ownerID, "any"); XCTAssertEqual(edit.patch, ["name": .string("כותרת חדשה")])
        XCTAssertEqual(edit.nativeVersion, writer.raw["_ver"]); XCTAssertEqual(edit.applySequence, 17)
        XCTAssertNil(edit.patch["imported"])
    }

    private func key(_ owner: String, _ property: String) throws -> AnyNativePropertyKey {
        try .init(ownerID: owner, propertyID: property)
    }
    private static func address(_ owner: String, _ property: String) -> AnyJSON {
        .object(["ownerId": .string(owner), "propertyId": .string(property)])
    }
    private func policy() throws -> AnyNativePropertyPolicy {
        try .init(hiddenPropertyKeys: [key("any", "type"), key("any", "collections")])
    }
    private func store() throws -> AnyNativePropertyStore {
        try .init(client: .init(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account"),
            workspace: .init(accountID: "account", spaceID: "space"), policy: policy())
    }
    private func snapshot(attached: Bool = false, storedHidden: [String]? = nil, canWrite: Bool = true,
                          includeForeignDefinition: Bool = false,
                          includeImportedMarker: Bool = true,
                          change: (inout [String: AnyJSON]) -> Void = { _ in }) throws -> AnyNativePropertySnapshot {
        var descriptor: [String: AnyJSON] = [
            "contract": .string(AnyNativeImportedTypePresentation.contract),
            "sourceRecommendedLayout": .integer(0), "propertyOwnerId": .string("imported"),
            "featured": .array([Self.address("imported", "beta"), Self.address("any", "name")]),
            "recommended": .array([Self.address("imported", "alpha"), Self.address("imported", "beta")]),
            "hidden": .array([Self.address("imported", "secret")]), "files": .array([])
        ]
        change(&descriptor)
        let type = try AnyNativePropertyOwner(raw: .object(["id": .string("imported-type"), "name": .string("Captured page type"),
            "layout": .object(["type": .string("page"),
                "config": .object(includeImportedMarker ? ["pinkhaHeart": .object(descriptor)] : [:])])]),
            documentEligible: true)
        func owner(_ id: String) throws -> AnyNativePropertyOwner { try .init(raw: .object(["id": .string(id)])) }
        let catalog = try AnyNativePropertyCatalog(workspace: .init(accountID: "account", spaceID: "space"),
            generation: UUID(uuidString: "11111111-1111-1111-1111-111111111111")!, engineStartedAt: "run",
            types: [type], collections: [owner("imported"), owner("unrelated"), owner(AnyNativePropertyStore.presentationCollectionID)])
        func definition(_ owner: String, _ id: String, kind: String = "string") throws -> AnyNativePropertyDefinition {
            try .init(ownerID: owner, raw: .object(["id": .string(id), "name": .string(id),
                "kind": .string(kind), "scope": .string("synced")]))
        }
        var definitions = try [definition("any", "name"), definition("any", "type"), definition("any", "collections", kind: "array"),
            definition("imported", "alpha"), definition("imported", "beta"), definition("imported", "gamma"),
            definition("imported", "secret"), definition("imported", "flag", kind: "boolean"),
            definition("imported", "count", kind: "number"), definition("imported", "empty"),
            definition("imported", "emptyList", kind: "array")]
        var collections = ["imported"]
        if includeForeignDefinition {
            collections.append("unrelated")
            definitions.append(try definition("unrelated", "source"))
        }
        if attached {
            collections.append(AnyNativePropertyStore.presentationCollectionID)
            definitions.append(try definition(AnyNativePropertyStore.presentationCollectionID, AnyNativePropertyStore.hiddenPropertiesID, kind: "array"))
        }
        var raw: [String: AnyJSON] = ["id": .string("document"), "spaceId": .string("space"), "_applySeq": .integer(17),
            "_ver": .object(["any": .object(["name": .string("name-v1"), "type": .string("type-v1"), "collections": .string("collections-v1")])]),
            "any": .object(["type": .string("imported-type"), "name": .string("כותרת המקור"),
                "collections": .array(collections.map(AnyJSON.string))]),
            "imported": .object(["secret": .string("kept"), "flag": .bool(false), "count": .integer(0), "empty": .string(""), "emptyList": .array([])]),
            "unrelated": .object(["source": .string("retained")])]
        if let storedHidden {
            raw[AnyNativePropertyStore.presentationCollectionID] = .object([
                AnyNativePropertyStore.hiddenPropertiesID: .array(storedHidden.map(AnyJSON.string))])
        }
        return try AnyNativePropertyStore.materialize(raw: .object(raw), objectID: "document", catalog: catalog,
            definitions: definitions, policy: policy(), canWrite: canWrite)
    }
}
