import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativeBookmarkPresentationTests: XCTestCase {
    private let owner = "mapped-property-owner"
    private let property = "mapped-source-url"

    func testBookmarkPreservesItsNativeTypeURLRoleAndUnrelatedContent() throws {
        let value = try snapshot()
        XCTAssertEqual(value.currentTypeID, "imported-bookmark")
        XCTAssertEqual(value.catalog.types.first?.raw["layout"]?["type"], .string("bookmark"))
        XCTAssertEqual(value.importedPresentation?.sourceURLKey, try key())
        XCTAssertEqual(value.bookmarkSourceURL?.absoluteString, "https://example.org/source?chapter=1#section")
        XCTAssertEqual(value.bookmarkSourceRow?.value, .string("https://example.org/source?chapter=1#section"))
        XCTAssertEqual(value.raw["unrelated"], .object(["body": .string("Original native body")]))
        XCTAssertNil(value.raw["any"]?["source"])
        XCTAssertNil(value.raw["any"]?["url"])
    }

    func testBookmarkRequiresAnExactMappedAndRecommendedSourceRole() throws {
        let changes: [(inout [String: AnyJSON]) -> Void] = [
            { $0["sourceURL"] = .object(["ownerId": .string("foreign"), "propertyId": .string("mapped-source-url")]) },
            { $0["sourceURL"] = .object(["ownerId": .string("any"), "propertyId": .string("name")]) },
            { $0["sourceURL"] = .object(["ownerId": .string("mapped-property-owner"), "propertyId": .string("missing")]) },
            { $0["sourceURL"] = .object(["ownerId": .string("mapped-property-owner"), "propertyId": .string("mapped-source-url"), "fallback": .bool(true)]) },
            { $0.removeValue(forKey: "sourceURL") },
            { $0["featured"] = .array([]); $0["recommended"] = .array([]) },
            { $0["sourceRecommendedLayout"] = .integer(0) },
            { $0["unrecognizedRule"] = .bool(true) },
        ]
        for change in changes { XCTAssertThrowsError(try snapshot(descriptorChange: change)) }
        XCTAssertThrowsError(try snapshot(includeURLDefinition: false))
        XCTAssertThrowsError(try snapshot(layout: "page"))
    }

    func testBookmarkRequiresNativeStringSyncedURLDefinition() throws {
        let changes: [(inout [String: AnyJSON]) -> Void] = [
            { $0["kind"] = .string("number") },
            { $0["scope"] = .string("derived") },
            { $0["scope"] = .string("account") },
            { $0["xFormat"] = .object(["type": .string("text")]) },
            { $0["xFormat"] = .null },
        ]
        for change in changes { XCTAssertThrowsError(try snapshot(definitionChange: change)) }
    }

    func testBookmarkHonorsHiddenDefaultsAndExplicitVisibilityWithoutChangingValue() throws {
        let hidden = try snapshot(descriptorChange: {
            $0["hidden"] = .array([Self.address("mapped-property-owner", "mapped-source-url")])
        })
        XCTAssertNil(hidden.bookmarkSourceRow)
        XCTAssertNil(hidden.bookmarkSourceURL)
        XCTAssertEqual(hidden.raw[owner]?[property], .string("https://example.org/source?chapter=1#section"))
        let shown = try snapshot(storedHidden: [], descriptorChange: {
            $0["hidden"] = .array([Self.address("mapped-property-owner", "mapped-source-url")])
        })
        XCTAssertNotNil(shown.bookmarkSourceURL)
        XCTAssertEqual(shown.raw[owner], hidden.raw[owner])
        let explicitlyHidden = try snapshot(storedHidden: [key().visibilityKey])
        XCTAssertNil(explicitlyHidden.bookmarkSourceRow)
        XCTAssertEqual(explicitlyHidden.raw[owner], hidden.raw[owner])
    }

    func testBookmarkPresentationGrantsNoWritesAndRetainsTheNativeFence() throws {
        let reader = try snapshot(canWrite: false)
        XCTAssertTrue(reader.rows.allSatisfy(\.isReadOnly))
        XCTAssertNotNil(reader.bookmarkSourceURL)
        XCTAssertThrowsError(try store().prepareSetValue(reader, key: key(), value: .string("https://example.net/")))
        let writer = try snapshot()
        let edit = try store().prepareSetValue(writer, key: key(), value: .string("https://example.net/"))
        XCTAssertEqual(edit.ownerID, owner)
        XCTAssertEqual(edit.patch, [property: .string("https://example.net/")])
        XCTAssertEqual(edit.nativeVersion, writer.nativeVersion)
        XCTAssertEqual(edit.applySequence, writer.applySequence)
        XCTAssertEqual(edit.generation, writer.generation)
        XCTAssertEqual(writer.raw[owner]?[property], .string("https://example.org/source?chapter=1#section"))
    }

    func testWebsiteActionUsesOnlyBoundedHTTPOrHTTPSAndPreservesUnsupportedValues() throws {
        for text in ["http://example.org/", "https://example.org/path?q=1", "HTTPS://example.org/"] {
            XCTAssertNotNil(try snapshot(urlValue: .string(text)).bookmarkSourceURL)
        }
        let unsupported: [AnyJSON?] = [
            nil, .null, .string(""), .integer(7), .string("relative/path"),
            .string("file:///private/example"), .string("javascript:alert(1)"),
            .string("https:///path"), .string(" https://example.org/"),
            .string("https://name:password@example.org/"),
            .string("https://example.org/" + String(repeating: "a", count: 8192)),
        ]
        for value in unsupported {
            let result = try snapshot(urlValue: value)
            XCTAssertNil(result.bookmarkSourceURL, String(describing: value))
            XCTAssertEqual(result.raw[owner]?[property], value)
        }
    }

    func testBasicV2AndNativeEligibilityRemainSeparateFromBookmarkPresentation() throws {
        XCTAssertThrowsError(try snapshot(eligible: false))
        XCTAssertThrowsError(try snapshot(builtIn: true))
        XCTAssertThrowsError(try snapshot(layout: "page", descriptorChange: {
            $0["contract"] = .string(AnyNativeImportedTypePresentation.contract)
            $0["sourceRecommendedLayout"] = .integer(0)
        }))
        let basic = try snapshot(layout: "page", descriptorChange: {
            $0["contract"] = .string(AnyNativeImportedTypePresentation.contract)
            $0["sourceRecommendedLayout"] = .integer(0)
            $0.removeValue(forKey: "sourceURL")
        })
        XCTAssertNil(basic.importedPresentation?.sourceURLKey)
        XCTAssertNil(basic.bookmarkSourceRow)
        XCTAssertEqual(basic.raw[owner]?[property], .string("https://example.org/source?chapter=1#section"))
    }

    private func key() throws -> AnyNativePropertyKey {
        try .init(ownerID: owner, propertyID: property)
    }

    private static func address(_ owner: String, _ property: String) -> AnyJSON {
        .object(["ownerId": .string(owner), "propertyId": .string(property)])
    }

    private func store() throws -> AnyNativePropertyStore {
        try .init(client: .init(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account"),
                  workspace: .init(accountID: "account", spaceID: "space"), policy: .init())
    }

    private func snapshot(urlValue: AnyJSON? = .string("https://example.org/source?chapter=1#section"),
                          canWrite: Bool = true, eligible: Bool = true, builtIn: Bool = false,
                          layout: String = "bookmark", includeURLDefinition: Bool = true,
                          storedHidden: [String]? = nil,
                          descriptorChange: (inout [String: AnyJSON]) -> Void = { _ in },
                          definitionChange: (inout [String: AnyJSON]) -> Void = { _ in }) throws -> AnyNativePropertySnapshot {
        var descriptor: [String: AnyJSON] = [
            "contract": .string(AnyNativeImportedTypePresentation.bookmarkContract),
            "sourceRecommendedLayout": .integer(11), "propertyOwnerId": .string(owner),
            "sourceURL": Self.address(owner, property),
            "featured": .array([Self.address(owner, property)]),
            "recommended": .array([Self.address("any", "name")]),
            "hidden": .array([]), "files": .array([]),
        ]
        descriptorChange(&descriptor)
        let type = try AnyNativePropertyOwner(raw: .object([
            "id": .string("imported-bookmark"), "name": .string("Imported Bookmark"), "builtIn": .bool(builtIn),
            "layout": .object(["type": .string(layout), "config": .object(["pinkhaHeart": .object(descriptor)])]),
        ]), documentEligible: eligible)
        let collection = try AnyNativePropertyOwner(raw: .object(["id": .string(owner), "name": .string("Imported properties")]))
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let catalog = try AnyNativePropertyCatalog(workspace: workspace, generation: UUID(), engineStartedAt: "native-run",
                                                   types: [type], collections: [collection])
        var definition: [String: AnyJSON] = [
            "id": .string(property), "name": .string("Source URL"), "kind": .string("string"),
            "scope": .string("synced"), "xFormat": .object(["type": .string("url")]),
        ]
        definitionChange(&definition)
        var definitions = [try AnyNativePropertyDefinition(ownerID: "any", raw: .object([
            "id": .string("name"), "name": .string("Name"), "kind": .string("string"), "scope": .string("synced"),
        ]))]
        if includeURLDefinition { definitions.append(try .init(ownerID: owner, raw: .object(definition))) }
        var properties: [String: AnyJSON] = [:]
        if let urlValue { properties[property] = urlValue }
        var raw: [String: AnyJSON] = [
            "id": .string("bookmark-object"), "spaceId": .string("space"), "_applySeq": .integer(17),
            "_ver": .object(["any": .object(["type": .string("native-version")])]),
            "any": .object(["type": .string("imported-bookmark"), "name": .string("Native bookmark"),
                             "collections": .array([.string(owner)])]),
            owner: .object(properties), "unrelated": .object(["body": .string("Original native body")]),
        ]
        if let storedHidden {
            raw[AnyNativePropertyStore.presentationCollectionID] = .object([
                AnyNativePropertyStore.hiddenPropertiesID: .array(storedHidden.map(AnyJSON.string)),
            ])
        }
        return try AnyNativePropertyStore.materialize(raw: .object(raw), objectID: "bookmark-object",
            catalog: catalog, definitions: definitions, policy: .init(), canWrite: canWrite)
    }
}
