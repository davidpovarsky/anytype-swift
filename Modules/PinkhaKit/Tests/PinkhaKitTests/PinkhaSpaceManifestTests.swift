import Foundation
import Testing
@testable import PinkhaKit

@Suite("PinkhaSpaceManifestTests")
struct PinkhaSpaceManifestTests {

    @Test("Manifest JSON round-trip serialization preserves all mappings")
    func testSerializationRoundTrip() throws {
        let manifest = PinkhaSpaceManifest(
            schemaVersion: 1,
            spaceId: "space_test_123",
            manifestObjectId: "obj_manifest_456",
            parentPropertyId: "rel_parent_001",
            parentPropertyKey: "pinkha_parent",
            orderPropertyId: "rel_order_002",
            orderPropertyKey: "pinkha_order",
            documentAssociationsPropertyId: "rel_assoc_003",
            documentAssociationsPropertyKey: "pinkha_assoc",
            folderTypeId: "type_folder_010",
            bookFolderTypeId: "type_bookfolder_020",
            registeredDocumentTypes: [
                PinkhaSchemaRoles.chiddushKey: "type_chiddush_100",
                PinkhaSchemaRoles.articleKey: "type_article_200",
                PinkhaSchemaRoles.researchKey: "type_research_300"
            ]
        )

        let data = try manifest.toJSONData()
        let decoded = try PinkhaSpaceManifest.fromJSONData(data)

        #expect(decoded == manifest)
        #expect(decoded.schemaVersion == 1)
        #expect(decoded.spaceId == "space_test_123")
        #expect(decoded.manifestObjectId == "obj_manifest_456")
        #expect(decoded.parentPropertyId == "rel_parent_001")
        #expect(decoded.orderPropertyId == "rel_order_002")
        #expect(decoded.documentAssociationsPropertyId == "rel_assoc_003")
        #expect(decoded.folderTypeId == "type_folder_010")
        #expect(decoded.bookFolderTypeId == "type_bookfolder_020")
        #expect(decoded.typeId(for: PinkhaSchemaRoles.chiddushKey) == "type_chiddush_100")
        #expect(decoded.typeId(for: PinkhaSchemaRoles.articleKey) == "type_article_200")
        #expect(decoded.typeId(for: PinkhaSchemaRoles.researchKey) == "type_research_300")
    }

    @Test("Role resolution and type validation helpers")
    func testRoleResolution() {
        let manifest = PinkhaSpaceManifest(
            spaceId: "space_test",
            parentPropertyId: "p_id",
            parentPropertyKey: "p_key",
            orderPropertyId: "o_id",
            orderPropertyKey: "o_key",
            documentAssociationsPropertyId: "a_id",
            documentAssociationsPropertyKey: "a_key",
            folderTypeId: "f_id",
            bookFolderTypeId: "bf_id",
            registeredDocumentTypes: [
                "chiddush": "type_ch",
                "article": "type_art"
            ]
        )

        #expect(manifest.isFolder(typeId: "f_id"))
        #expect(!manifest.isFolder(typeId: "bf_id"))
        #expect(manifest.isBookFolder(typeId: "bf_id"))
        #expect(manifest.isRegisteredDocumentType(typeId: "type_ch"))
        #expect(manifest.isRegisteredDocumentType(typeId: "type_art"))
        #expect(!manifest.isRegisteredDocumentType(typeId: "type_unknown"))
        #expect(manifest.role(forTypeId: "type_ch") == "chiddush")
        #expect(manifest.role(forTypeId: "type_art") == "article")
        #expect(manifest.role(forTypeId: "other") == nil)
        #expect(manifest.isAnyPinkhaType(typeId: "f_id"))
        #expect(manifest.isAnyPinkhaType(typeId: "type_ch"))
        #expect(!manifest.isAnyPinkhaType(typeId: "type_page"))
    }

    @Test("Torah association payload serialization")
    func testTorahAssociationsSerialization() throws {
        let item = TorahAssociationItem(
            id: "test_assoc_1",
            kind: .ref,
            role: .context,
            providerID: "sefaria",
            externalID: "Genesis.1.1",
            canonicalKey: "בראשית א:א",
            labelHe: "בראשית א:א",
            labelEn: "Genesis 1:1"
        )

        let payload = TorahDocumentAssociationsPayload(version: 1, items: [item])
        let data = try JSONEncoder().encode(payload)
        let decoded = try JSONDecoder().decode(TorahDocumentAssociationsPayload.self, from: data)

        #expect(decoded == payload)
        #expect(decoded.items.count == 1)
        #expect(decoded.items[0].canonicalKey == "בראשית א:א")
        #expect(decoded.items[0].kind == .ref)
        #expect(decoded.items[0].role == .context)
    }

    @Test("Torah source quote payload serialization")
    func testSourceQuoteSerialization() throws {
        let quote = TorahSourceQuotePayload(
            version: 1,
            providerID: "sefaria",
            externalID: "Bava_Kamma.2a.1",
            canonicalKey: "בבא קמא ב.",
            labelHe: "בבא קמא דף ב ע\"א",
            labelEn: "Bava Kamma 2a",
            segment: "1",
            snapshotText: "ארבעה אבות נזיקין",
            readOnly: true
        )

        let data = try JSONEncoder().encode(quote)
        let decoded = try JSONDecoder().decode(TorahSourceQuotePayload.self, from: data)

        #expect(decoded == quote)
        #expect(decoded.readOnly == true)
        #expect(decoded.snapshotText == "ארבעה אבות נזיקין")
    }
}
