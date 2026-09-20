import Testing
@testable import PinkhaKit

@Suite("PinkhaHierarchyCodecTests")
struct PinkhaHierarchyCodecTests {

    // MARK: - Parent Relation Encoding Tests

    @Test("Object relation parent list encoding: non-empty parent produces single-item array")
    func testParentListEncoding() {
        let result = PinkhaHierarchyCodec.encodeParentRelation(parentId: "parent_folder_123")
        #expect(result == ["parent_folder_123"])
    }

    @Test("Object relation parent list encoding: nil or empty parent produces empty array")
    func testParentListEncodingEmpty() {
        let nilResult = PinkhaHierarchyCodec.encodeParentRelation(parentId: nil)
        #expect(nilResult.isEmpty)

        let emptyResult = PinkhaHierarchyCodec.encodeParentRelation(parentId: "")
        #expect(emptyResult.isEmpty)
    }

    // MARK: - Parent Relation Decoding Tests

    @Test("Parent list decoding: single-element list decodes canonical parentId")
    func testParentListDecodingSingle() {
        let decoded = PinkhaHierarchyCodec.decodeParentId(listValues: ["folder_abc"], scalarValue: nil)
        #expect(decoded == "folder_abc")
    }

    @Test("Parent list decoding: multi-element list decodes first parentId")
    func testParentListDecodingFirst() {
        let decoded = PinkhaHierarchyCodec.decodeParentId(listValues: ["folder_first", "folder_second"], scalarValue: nil)
        #expect(decoded == "folder_first")
    }

    @Test("Parent list decoding: empty list returns nil")
    func testParentListDecodingEmpty() {
        let decoded = PinkhaHierarchyCodec.decodeParentId(listValues: [], scalarValue: nil)
        #expect(decoded == nil)

        let decodedEmptyStr = PinkhaHierarchyCodec.decodeParentId(listValues: [""], scalarValue: nil)
        #expect(decodedEmptyStr == nil)
    }

    // MARK: - Backward-Compatible Scalar Decoding Tests

    @Test("Backward-compatible scalar parent decoding: valid scalar decodes parentId")
    func testBackwardCompatibleScalarDecoding() {
        let decoded = PinkhaHierarchyCodec.decodeParentId(listValues: nil, scalarValue: "legacy_parent_id")
        #expect(decoded == "legacy_parent_id")
    }

    @Test("Backward-compatible scalar parent decoding: empty or nil scalar returns nil")
    func testBackwardCompatibleScalarDecodingEmpty() {
        let decodedEmpty = PinkhaHierarchyCodec.decodeParentId(listValues: nil, scalarValue: "")
        #expect(decodedEmpty == nil)

        let decodedNil = PinkhaHierarchyCodec.decodeParentId(listValues: nil, scalarValue: nil)
        #expect(decodedNil == nil)
    }

    @Test("Parent decoding precedence: listValue takes precedence over legacy scalar string")
    func testParentDecodingPrecedence() {
        let decoded = PinkhaHierarchyCodec.decodeParentId(listValues: ["canonical_id"], scalarValue: "legacy_id")
        #expect(decoded == "canonical_id")
    }

    // MARK: - Hierarchy Key Builder Tests

    @Test("Required hierarchy subscription keys include standard id, type, and name")
    func testRequiredStandardKeys() {
        let standard = PinkhaHierarchyKeyBuilder.requiredStandardKeys
        #expect(standard.contains("id"))
        #expect(standard.contains("type"))
        #expect(standard.contains("name"))
    }

    @Test("Hierarchy key builder combines standard keys with custom parent and order keys, deduplicating safely")
    func testKeyBuilderComposition() {
        let standardKeys = ["id", "spaceId", "type", "name", "isDeleted", "isArchived", "id"]
        let parentKey = "pinkha.parent"
        let orderKey = "pinkha.order"

        let keys = PinkhaHierarchyKeyBuilder.buildKeys(
            standardKeys: standardKeys,
            parentPropertyKey: parentKey,
            orderPropertyKey: orderKey
        )

        // Must contain all standard keys
        #expect(keys.contains("id"))
        #expect(keys.contains("spaceId"))
        #expect(keys.contains("type"))
        #expect(keys.contains("name"))
        #expect(keys.contains("isDeleted"))
        #expect(keys.contains("isArchived"))

        // Must contain custom keys
        #expect(keys.contains(parentKey))
        #expect(keys.contains(orderKey))

        // Must be deduplicated
        #expect(keys.filter { $0 == "id" }.count == 1)

        // Custom keys must not be added if empty
        let keysWithoutCustom = PinkhaHierarchyKeyBuilder.buildKeys(
            standardKeys: ["id", "type"],
            parentPropertyKey: "",
            orderPropertyKey: ""
        )
        #expect(keysWithoutCustom == ["id", "type"])
    }
}
