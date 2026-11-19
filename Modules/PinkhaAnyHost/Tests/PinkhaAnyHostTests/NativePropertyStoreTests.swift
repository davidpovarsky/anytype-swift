import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePropertyStoreTests: XCTestCase, @unchecked Sendable {
    private func workspace(_ space: String = "space") throws -> AnyTorahWorkspace {
        try .init(accountID: "account", spaceID: space)
    }
    private func policy() throws -> AnyNativePropertyPolicy {
        try .init(hiddenPropertyKeys: [.init(ownerID: "wiki", propertyID: "order")],
                  managedPropertyKeys: [.init(ownerID: "wiki", propertyID: "parent")],
                  hiddenCollectionIDs: ["note-marker"])
    }
    private func store() throws -> AnyNativePropertyStore {
        try .init(client: .init(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account"),
                  workspace: workspace(), policy: policy())
    }
    private func owner(_ id: String, eligible: Bool = false, hidden: Bool = false,
                       builtIn: Bool = false) throws -> AnyNativePropertyOwner {
        try .init(raw: .object(["id": .string(id), "name": .string("Label " + id),
                               "hidden": .bool(hidden), "builtIn": .bool(builtIn)]),
                  documentEligible: eligible)
    }
    private func catalog(_ space: String = "space") throws -> AnyNativePropertyCatalog {
        try .init(workspace: workspace(space), generation: UUID(uuidString: "11111111-1111-1111-1111-111111111111")!,
            engineStartedAt: "run",
            types: [owner("page", eligible: true, hidden: true, builtIn: true),
                    owner("custom", eligible: true), owner("opaque"), owner("hidden-custom", eligible: true, hidden: true)],
            collections: [owner("collection-a"), owner("collection-b"), owner("wiki"), owner("note-marker"),
                          owner(AnyNativePropertyStore.presentationCollectionID, hidden: true, builtIn: true)])
    }
    private func definition(_ owner: String, _ id: String, kind: String = "string",
                            scope: String = "synced", name: String? = nil) throws -> AnyNativePropertyDefinition {
        try .init(ownerID: owner, raw: .object([
            "id": .string(id), "name": .string(name ?? id), "kind": .string(kind), "scope": .string(scope)]))
    }
    private func snapshot(attached: Bool = false, hidden: [String] = [],
                          canWrite: Bool = true, space: String = "space") throws -> AnyNativePropertySnapshot {
        var collectionIDs = ["collection-a", "wiki"]
        if attached { collectionIDs.append(AnyNativePropertyStore.presentationCollectionID) }
        let raw: AnyJSON = .object([
            "id": .string("document"), "spaceId": .string(space), "author": .string("native-author"),
            "_ver": .object(["id": .string("v1"), "any": .object(["type": .string("v2"), "name": .string("v3")]),
                "collection-a": .object(["nested": .object(["leaf": .string("v4")])])]),
            "any": .object(["type": .string("page"), "name": .string("שלום"),
                           "collections": .array(collectionIDs.map(AnyJSON.string))]),
            "collection-a": .object(["count": .integer(42), "future": .object(["digits": .string("999999999999999999999")])]),
            "wiki": .object(["parent": .string("parent-id"), "order": .string("PPPP")]),
            "old-orphan-namespace": .object(["business": .object(["unknown": .array([.integer(7), .string("עברית")])])]),
            AnyNativePropertyStore.presentationCollectionID: .object([
                AnyNativePropertyStore.hiddenPropertiesID: .array(hidden.map(AnyJSON.string))])])
        var definitions = try [
            definition("any", "name"), definition("any", "type"),
            definition("any", "collections", kind: "array"), definition("any", "template", kind: "object"),
            definition("any", "author", scope: "derived"),
            definition("collection-a", "count", kind: "number"),
            definition("collection-a", "future", kind: "decimal128"),
            definition("collection-a", "device", scope: "local"),
            definition("collection-a", "account", scope: "account"),
            definition("wiki", "parent"), definition("wiki", "order")]
        if attached {
            definitions.append(try definition(AnyNativePropertyStore.presentationCollectionID,
                AnyNativePropertyStore.hiddenPropertiesID, kind: "array"))
        }
        return try AnyNativePropertyStore.materialize(raw: raw, objectID: "document", catalog: catalog(space),
            definitions: definitions, policy: policy(), canWrite: canWrite)
    }

    func testExactQualifiedKeysCannotCollideAtSeparatorsAndDerivedKeysAreDistinct() throws {
        let first = try AnyNativePropertyKey(ownerID: "a:b", propertyID: "c")
        let second = try AnyNativePropertyKey(ownerID: "a", propertyID: "b:c")
        XCTAssertNotEqual(first.visibilityKey, second.visibilityKey)
        XCTAssertEqual(try AnyNativePropertyKey(ownerID: "any", propertyID: "name").visibilityKey, "property:v1:3:any:4:name")
        XCTAssertEqual(AnyNativePropertyVisibilityKey(derived: .sources).rawValue,
                       "derived:v1:pinkha-torah-native-v1:pinkhaSources")
        XCTAssertThrowsError(try AnyNativePropertyKey(ownerID: "bad\nid", propertyID: "name"))
    }

    func testRawUnknownNamespacesAndNativeDerivedMetadataSurviveProjection() throws {
        let value = try snapshot()
        XCTAssertEqual(value.raw["old-orphan-namespace"]?["business"]?["unknown"],
                       .array([.integer(7), .string("עברית")]))
        let author = try XCTUnwrap(value.rows.first { $0.id.propertyID == "author" })
        XCTAssertEqual(author.value, .string("native-author"))
        XCTAssertTrue(author.isReadOnly)
        let unknown = try XCTUnwrap(value.rows.first { $0.id.propertyID == "future" })
        XCTAssertNil(unknown.definition.kind)
        XCTAssertTrue(unknown.isReadOnly)
        XCTAssertEqual(unknown.value, .object(["digits": .string("999999999999999999999")]))
    }

    func testSingleValuePatchCapturesExactVersionAndInverseWithoutEchoingOtherNamespaces() throws {
        let value = try snapshot()
        let edit = try store().prepareSetValue(value,
            key: .init(ownerID: "collection-a", propertyID: "count"), value: .integer(43))
        XCTAssertEqual(edit.ownerID, "collection-a")
        XCTAssertEqual(edit.patch, ["count": .integer(43)])
        XCTAssertEqual(edit.inversePatch, ["count": .integer(42)])
        XCTAssertEqual(edit.nativeVersion, value.raw["_ver"])
        XCTAssertNil(edit.patch["old-orphan-namespace"])
        XCTAssertEqual(value.raw["collection-a"]?["future"]?["digits"], .string("999999999999999999999"))
    }

    func testGenericSetCannotBypassTypeMembershipHierarchyOrUnsupportedScope() throws {
        let value = try snapshot(), subject = try store()
        for (owner, property) in [("any", "type"), ("any", "collections"), ("any", "template"),
                                  ("wiki", "parent"), ("wiki", "order"), ("collection-a", "future"),
                                  ("collection-a", "device"), ("collection-a", "account")] {
            XCTAssertThrowsError(try subject.prepareSetValue(value,
                key: .init(ownerID: owner, propertyID: property), value: .string("forged"))) {
                XCTAssertEqual($0 as? AnyNativePropertyError, .readOnly)
            }
        }
    }

    func testReaderSnapshotCannotPrepareAnyMutation() throws {
        let value = try snapshot(canWrite: false), subject = try store()
        XCTAssertTrue(value.rows.allSatisfy(\.isReadOnly))
        XCTAssertThrowsError(try subject.prepareSetValue(value, key: .init(ownerID: "any", propertyID: "name"),
                                                         value: .string("changed")))
        XCTAssertThrowsError(try subject.prepareSetType(value, typeID: "custom"))
        XCTAssertThrowsError(try subject.prepareAttachCollection(value, collectionID: "collection-b"))
    }

    func testTypePickerUsesEligibilityAndPreservesOriginalNamespaces() throws {
        let value = try snapshot(), subject = try store()
        XCTAssertEqual(Set(value.catalog.selectableDocumentTypes.map(\.id)), ["page", "custom"])
        let edit = try subject.prepareSetType(value, typeID: "custom")
        XCTAssertEqual(edit.patch, ["type": .string("custom")])
        XCTAssertEqual(edit.typeDestination, "custom")
        XCTAssertEqual(edit.inversePatch, ["type": .string("page")])
        XCTAssertNotNil(value.raw["old-orphan-namespace"])
        for type in ["opaque", "hidden-custom", "missing"] {
            XCTAssertThrowsError(try subject.prepareSetType(value, typeID: type))
        }
    }

    func testCollectionMembershipDoesNotDeleteValuesOrBypassManagedCollections() throws {
        let value = try snapshot(), subject = try store()
        let attach = try subject.prepareAttachCollection(value, collectionID: "collection-b")
        XCTAssertEqual(attach.patch["collections"], .array(["collection-a", "collection-b", "wiki"].map(AnyJSON.string)))
        let detach = try subject.prepareDetachCollection(value, collectionID: "collection-a")
        XCTAssertEqual(detach.patch, ["collections": .array([.string("wiki")])])
        XCTAssertEqual(value.raw["collection-a"]?["count"], .integer(42))
        XCTAssertThrowsError(try subject.prepareDetachCollection(value, collectionID: "wiki"))
        for id in ["bin", "template", "note-marker", "wiki", AnyNativePropertyStore.presentationCollectionID] {
            XCTAssertThrowsError(try subject.prepareAttachCollection(value, collectionID: id))
        }
    }

    func testVisibilityPreservesFutureKeysAndChangesOnlyPreferenceNamespace() throws {
        let key = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "count")
        let future = "future:v9:opaque-setting"
        let value = try snapshot(attached: true, hidden: [future]), subject = try store()
        let edit = try subject.prepareVisibility(value, key: .init(property: key), visible: false)
        XCTAssertEqual(edit.ownerID, AnyNativePropertyStore.presentationCollectionID)
        XCTAssertEqual(Set(edit.patch[AnyNativePropertyStore.hiddenPropertiesID]!.array!.compactMap(\.string)),
                       [future, key.visibilityKey])
        XCTAssertNil(edit.patch["count"])
        XCTAssertEqual(value.raw["collection-a"]?["count"], .integer(42))
        let alreadyHidden = try snapshot(attached: true, hidden: [future, key.visibilityKey])
        let show = try subject.prepareVisibility(alreadyHidden, key: .init(property: key), visible: true)
        XCTAssertEqual(show.patch[AnyNativePropertyStore.hiddenPropertiesID], .array([.string(future)]))
    }

    func testVisibilityAttachmentAndDerivedPanelRemainExplicit() throws {
        let subject = try store()
        XCTAssertThrowsError(try subject.prepareVisibility(snapshot(), key: .init(derived: .sources), visible: false)) {
            XCTAssertEqual($0 as? AnyNativePropertyError, .presentationNotAttached)
        }
        let edit = try subject.prepareVisibility(snapshot(attached: true), key: .init(derived: .topics), visible: false)
        XCTAssertEqual(edit.patch[AnyNativePropertyStore.hiddenPropertiesID],
                       .array([.string("derived:v1:pinkha-torah-native-v1:pinkhaTopics")]))
        XCTAssertEqual(edit.patch.count, 1)
        XCTAssertThrowsError(try subject.prepareVisibility(snapshot(attached: true),
            key: .init(property: .init(ownerID: "wiki", propertyID: "order")), visible: true))
    }

    func testMalformedOrOverflowingVisibilityNeverSilentlyDropsValues() throws {
        XCTAssertThrowsError(try snapshot(attached: true, hidden: ["same", "same"]))
        XCTAssertThrowsError(try snapshot(attached: true, hidden: [String(repeating: "x", count: 4097)]))
        XCTAssertThrowsError(try snapshot(attached: true, hidden: (0...512).map(String.init)))
        XCTAssertThrowsError(try snapshot(attached: true, hidden: [""]))
        XCTAssertThrowsError(try snapshot(attached: true, hidden: ["bad\u{0000}key"]))
        XCTAssertNoThrow(try snapshot(attached: true, hidden: ["unknown-version:still-preserved"]))
    }

    func testCatalogRejectsDuplicatesButAllowsLegitimateCrossCatalogID() throws {
        let common = try owner("collection")
        XCTAssertNoThrow(try AnyNativePropertyCatalog(workspace: workspace(), generation: UUID(),
            engineStartedAt: "run", types: [common], collections: [common]))
        XCTAssertThrowsError(try AnyNativePropertyCatalog(workspace: workspace(), generation: UUID(),
            engineStartedAt: "run", types: [common, common], collections: []))
        XCTAssertThrowsError(try store().prepareSetType(snapshot(space: "foreign"), typeID: "custom"))
    }

    func testNativeProofRequiresExactPolicyWorkspaceReadinessAndCapabilityVersion() throws {
        let proof: AnyJSON = .object(["contract": .string("pinkha-torah-native-v1"), "version": .integer(1),
            "policy": .string("canonical-editor-module-v1"), "spaceId": .string("space"),
            "typeId": .string("page"), "eligible": .bool(true),
            "canonicalEditorDataset": .string("editor_blocks"),
            "readiness": .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                                 "generation": .string(String(repeating: "a", count: 64))])])
        XCTAssertNoThrow(try AnyNativeDocumentTypeProof(response: proof, workspace: workspace(), typeID: "page"))
        for (key, value) in [("spaceId", AnyJSON.string("foreign")), ("version", .integer(2)),
                            ("policy", .string("any-nonempty-type")), ("canonicalEditorDataset", .string("named_editor"))] {
            var invalid = proof.object!; invalid[key] = value
            XCTAssertThrowsError(try AnyNativeDocumentTypeProof(response: .object(invalid), workspace: workspace(), typeID: "page"))
        }
        for value in [AnyJSON.bool(true), .string("1"), .integer(0), .integer(2)] {
            XCTAssertThrowsError(try AnyNativePropertyStore.requireCapability(
                .object(["contract": .string("pinkha-torah-native-v1"), "nativeDocumentMembership": value]),
                "nativeDocumentMembership"))
        }
    }

    func testPropertyKindMismatchCannotBecomeAnUnconditionalOrWholeRecordWrite() throws {
        let subject = try store(), value = try snapshot()
        XCTAssertThrowsError(try subject.prepareSetValue(value,
            key: .init(ownerID: "collection-a", propertyID: "count"), value: .string("not a number")))
        let unset = try subject.prepareSetValue(value,
            key: .init(ownerID: "collection-a", propertyID: "count"), value: .null)
        XCTAssertEqual(unset.patch, ["count": .null])
        XCTAssertEqual(unset.inversePatch, ["count": .integer(42)])
        XCTAssertTrue(AnyNativePropertyStore.nativeValueMatches(.integer(4), requested: .number(4.0)))
        XCTAssertFalse(AnyNativePropertyStore.nativeValueMatches(.integer(9_007_199_254_740_993), requested: .number(9_007_199_254_740_992)))
        XCTAssertTrue(AnyNativePropertyStore.nativeValueMatches(.object(["$date": .string("2026-11-19T10:00:00.123Z")]),
            requested: .object(["$date": .string("2026-11-19T12:00:00.123999+02:00")])))
        XCTAssertThrowsError(try subject.prepareSetValue(value,
            key: .init(ownerID: "old-orphan-namespace", propertyID: "business"), value: .null))
    }
}
