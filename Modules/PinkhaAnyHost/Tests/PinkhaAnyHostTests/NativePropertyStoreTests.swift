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
            "_applySeq": .integer(17),
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

// These are typed Host receipt fixtures, not native transport or mounted UI proof.
extension NativePropertyStoreTests {
    private func unicodePropertySnapshot(key: AnyNativePropertyKey, kind: String,
                                         value: AnyJSON?, sequence: Int64) throws -> AnyNativePropertySnapshot {
        let original = try snapshot()
        var raw = try XCTUnwrap(original.raw.object)
        var namespace = try XCTUnwrap(raw[key.ownerID]?.object)
        namespace[key.propertyID] = value
        raw[key.ownerID] = .object(namespace)
        raw["_applySeq"] = .integer(sequence)
        var definitions = original.rows.map(\.definition).filter { $0.key != key }
        definitions.append(try definition(key.ownerID, key.propertyID, kind: kind))
        return try AnyNativePropertyStore.materialize(raw: .object(raw), objectID: original.objectID,
            catalog: original.catalog, definitions: definitions, policy: policy(), canWrite: true)
    }

    private func unicodePropertyReceipt(key: AnyNativePropertyKey, kind: String,
                                        before: AnyJSON, requested: AnyJSON,
                                        actual: AnyJSON?) throws -> (AnyPreparedPropertyEdit, AnyPropertyEditReceipt) {
        let subject = try store()
        let initial = try unicodePropertySnapshot(key: key, kind: kind, value: before, sequence: 17)
        let edit = try subject.prepareSetValue(initial, key: key, value: requested)
        let accepted = try AnyNativePropertyStore.acceptedFence(.object([
            "engineStartedAt": .string(initial.engineStartedAt),
            "propertiesVersion": initial.nativeVersion, "applySeq": .integer(18)
        ]), original: edit.fence)
        let readback = try unicodePropertySnapshot(key: key, kind: kind, value: actual, sequence: 18)
        XCTAssertEqual(readback.fence, accepted)
        XCTAssertEqual(try AnyHostCanonical.bytes(try XCTUnwrap(edit.patch[key.propertyID])),
                       try AnyHostCanonical.bytes(requested))
        return (edit, subject.receipt(for: edit, accepted: accepted, readback: readback))
    }

    private func requireUnverifiedUnicodeReceipt(_ receipt: AnyPropertyEditReceipt,
                                                 file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertEqual(receipt.readback, .nativeAcceptedButCurrentStateUnverified, file: file, line: line)
        XCTAssertNil(receipt.snapshot, file: file, line: line)
        XCTAssertNil(receipt.undo, file: file, line: line)
    }

    private func requireVerifiedUnicodeReceipt(_ receipt: AnyPropertyEditReceipt,
                                               key: AnyNativePropertyKey, before: AnyJSON,
                                               actual: AnyJSON?, file: StaticString = #filePath,
                                               line: UInt = #line) throws {
        XCTAssertEqual(receipt.readback, .verifiedCurrent, file: file, line: line)
        let current = try XCTUnwrap(receipt.snapshot, file: file, line: line)
        if let actual {
            XCTAssertEqual(try AnyHostCanonical.bytes(try XCTUnwrap(current.raw[key.ownerID]?[key.propertyID])),
                           try AnyHostCanonical.bytes(actual), file: file, line: line)
        } else {
            XCTAssertNil(current.raw[key.ownerID]?[key.propertyID], file: file, line: line)
        }
        let inverse = try XCTUnwrap(receipt.undo, file: file, line: line)
        XCTAssertEqual(inverse.fence, current.fence, file: file, line: line)
        XCTAssertEqual(try AnyHostCanonical.bytes(try XCTUnwrap(inverse.patch[key.propertyID])),
                       try AnyHostCanonical.bytes(before), file: file, line: line)
    }

    func testStringReadbackRequiresExactUTF8BeforeCreatingUndo() throws {
        let name = try AnyNativePropertyKey(ownerID: "any", propertyID: "name")
        // The second owner is a typed fixture for a mapped string URL value.
        // This test does not claim native imported-Type mapping or URL-open proof.
        let url = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "mapped-url-fixture")
        let pairs: [(AnyNativePropertyKey, String, String)] = [
            (name, "Caf\u{00E9}", "Cafe\u{0301}"),
            (name, "\u{05E9}\u{05C1}\u{05B0}", "\u{05E9}\u{05B0}\u{05C1}"),
            (url, "https://example.invalid/Caf\u{00E9}", "https://example.invalid/Cafe\u{0301}")
        ]
        for (key, before, requested) in pairs {
            XCTAssertEqual(before, requested) // Establish the old canonical-equality counterexample.
            XCTAssertFalse(before.utf8.elementsEqual(requested.utf8))
            let (edit, wrong) = try unicodePropertyReceipt(key: key, kind: "string",
                before: .string(before), requested: .string(requested), actual: .string(before))
            XCTAssertEqual(try AnyHostCanonical.bytes(try XCTUnwrap(edit.inversePatch[key.propertyID])),
                           try AnyHostCanonical.bytes(.string(before)))
            requireUnverifiedUnicodeReceipt(wrong)
            let (_, exact) = try unicodePropertyReceipt(key: key, kind: "string",
                before: .string(before), requested: .string(requested), actual: .string(requested))
            try requireVerifiedUnicodeReceipt(exact, key: key, before: .string(before), actual: .string(requested))
        }
    }

    func testNestedStringAndKeyReadbackRequiresExactUTF8BeforeCreatingUndo() throws {
        let key = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "unicode-structure-fixture")
        let nfc = "Caf\u{00E9}", nfd = "Cafe\u{0301}"
        let pairs: [(String, AnyJSON, AnyJSON)] = [
            ("array", .array([.object(["text": .string(nfc)])]),
                      .array([.object(["text": .string(nfd)])])),
            ("object", .object(["text": .array([.string(nfc)])]),
                       .object(["text": .array([.string(nfd)])])),
            ("object", .object([nfc: .integer(7)]), .object([nfd: .integer(7)]))
        ]
        for (kind, before, requested) in pairs {
            XCTAssertEqual(before, requested) // Includes canonical equality of dictionary keys.
            XCTAssertNotEqual(try AnyHostCanonical.bytes(before), try AnyHostCanonical.bytes(requested))
            let (_, wrong) = try unicodePropertyReceipt(key: key, kind: kind,
                before: before, requested: requested, actual: before)
            requireUnverifiedUnicodeReceipt(wrong)
            let (_, exact) = try unicodePropertyReceipt(key: key, kind: kind,
                before: before, requested: requested, actual: requested)
            try requireVerifiedUnicodeReceipt(exact, key: key, before: before, actual: requested)
        }
    }

    func testPropertyReceiptRetainsDocumentedNativeNormalizationAndUnsetRules() throws {
        let key = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "native-representation-fixture")
        let dateBefore: AnyJSON = .object(["$date": .string("2026-11-18T10:00:00.000Z")])
        let pairs: [(String, AnyJSON, AnyJSON, AnyJSON?)] = [
            ("number", .integer(3), .number(4.0), .integer(4)),
            ("number", .integer(3), .integer(4), .number(4.0)),
            ("number", .number(1.0), .number(-0.0), .number(0.0)),
            ("datetime", dateBefore,
                .object(["$date": .string("2026-11-19T12:00:00.123999+02:00")]),
                .object(["$date": .string("2026-11-19T10:00:00.123Z")])),
            ("string", .string("original"), .null, nil)
        ]
        for (kind, before, requested, actual) in pairs {
            let (_, receipt) = try unicodePropertyReceipt(key: key, kind: kind,
                before: before, requested: requested, actual: actual)
            try requireVerifiedUnicodeReceipt(receipt, key: key, before: before, actual: actual)
        }
        // An explicit stored null is not the native absent-property result of unset.
        let (_, storedNull) = try unicodePropertyReceipt(key: key, kind: "string",
            before: .string("original"), requested: .null, actual: .null)
        requireUnverifiedUnicodeReceipt(storedNull)
    }

    func testPropertyValueComparisonUsesTheExistingCanonicalDepthLimit() throws {
        func nested(_ depth: Int) -> AnyJSON {
            (0..<depth).reduce(AnyJSON.string("exact")) { value, _ in .array([value]) }
        }
        let atLimit = nested(32), pastLimit = nested(33)
        XCTAssertNoThrow(try AnyHostCanonical.bytes(atLimit))
        XCTAssertTrue(AnyNativePropertyStore.nativeValueMatches(atLimit, requested: atLimit))
        XCTAssertThrowsError(try AnyHostCanonical.bytes(pastLimit))
        XCTAssertFalse(AnyNativePropertyStore.nativeValueMatches(pastLimit, requested: pastLimit))
        let key = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "depth-fixture")
        let captured = try unicodePropertySnapshot(key: key, kind: "array", value: .array([]), sequence: 17)
        XCTAssertThrowsError(try store().prepareSetValue(captured, key: key, value: pastLimit))
        // Raw native records include their namespace containers in the same bound.
        XCTAssertThrowsError(try unicodePropertySnapshot(key: key, kind: "array", value: pastLimit, sequence: 18))
    }
}
