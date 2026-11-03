import Foundation
import Testing
@testable import PinkhaKit

@Suite("Canonical Torah property projections")
struct TorahDocumentPropertyProjectionTests {
    @Test(arguments: [0, 1, 2, 12])
    func countsAndOrdering(count: Int) {
        let records = (0..<count).flatMap { index in
            TorahAssociationKind.allCases.map { record(id: "\($0.rawValue)-\(index)", kind: $0) }
        }
        let projection = project(records)
        for kind in TorahAssociationKind.allCases {
            #expect(projection[kind].map(\.id) == (0..<count).map { "\(kind.rawValue)-\($0)" })
        }
    }

    @Test func excludesOtherTargetsRolesAndNotes() {
        let source = record(id: "source")
        var block = record(id: "block")
        block.blockId = "block"
        var otherSpace = record(id: "other-space")
        otherSpace.spaceId = "another-space"
        var otherObject = record(id: "other-object")
        otherObject.objectId = "another-object"
        var quote = record(id: "quote")
        quote.item.role = .sourceQuote
        var note = record(id: "note")
        note.item.canonicalKey = "anytype-note:note"
        #expect(project([block, source, otherSpace, otherObject, quote, note]).sources == [source.item])
    }

    @Test func deduplicatesWithoutChangingStableIdentityOrInput() throws {
        let first = record(id: "stable")
        var semanticDuplicate = first
        semanticDuplicate.item.id = "retry"
        var sameID = first
        sameID.item.canonicalKey = "different-reference"
        var topic = first
        topic.item.id = "topic"
        topic.item.kind = .topic
        let payload = TorahCanonicalAssociationsPayload(
            records: [first, semanticDuplicate, sameID, topic],
            unknownFields: ["future": .object(["preserved": .bool(true)])]
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(payload)
        let projection = project(payload.records)
        #expect(projection.sources == [first.item])
        #expect(projection.topics == [topic.item])
        #expect(try encoder.encode(payload) == bytes)
        #expect(projection.sources.first?.unknownFields == ["futureItem": .number(7)])
        #expect(projection.sources.first?.labelHe == "ברכות כג ב")
        #expect(projection.sources.first?.labelEn == "Berakhot 23b")
        #expect(projection.sources.first?.canonicalKey == "ref-stable")
    }

    @Test func eligibilityUsesAllThreeManifestIDsAndExactSpace() {
        let manifest = manifest()
        for id in ["type-chiddush", "type-article", "type-research"] {
            #expect(TorahDocumentPropertyEligibility.includes(typeId: id, spaceId: "space", manifest: manifest))
        }
        for id in ["page", "note", "חידוש", "folder", ""] {
            #expect(!TorahDocumentPropertyEligibility.includes(typeId: id, spaceId: "space", manifest: manifest))
        }
        #expect(!TorahDocumentPropertyEligibility.includes(typeId: "type-chiddush", spaceId: "other", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.includes(typeId: "type-chiddush", spaceId: "space", manifest: nil))
        var incomplete = manifest
        incomplete.provisioningState = .inProgress
        #expect(!TorahDocumentPropertyEligibility.includes(typeId: "type-chiddush", spaceId: "space", manifest: incomplete))
    }

    @Test func onlyCanonicalPropertyIdentityIsFiltered() {
        let manifest = manifest()
        #expect(TorahDocumentPropertyEligibility.isCanonicalProperty(id: "internal-id", key: "other", spaceId: "space", manifest: manifest))
        #expect(TorahDocumentPropertyEligibility.isCanonicalProperty(id: "other", key: "internal-key", spaceId: "space", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isCanonicalProperty(id: "tag", key: "tag", spaceId: "space", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isCanonicalProperty(id: "internal-id", key: "internal-key", spaceId: "other", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isCanonicalProperty(id: "", key: "", spaceId: "space", manifest: PinkhaSpaceManifest(spaceId: "space")))
    }

    private func project(_ records: [TorahStoredAssociationRecord]) -> TorahDocumentPropertyProjection {
        TorahDocumentPropertyProjection(records: records, spaceId: "space", objectId: "object")
    }

    private func record(id: String, kind: TorahAssociationKind = .ref) -> TorahStoredAssociationRecord {
        TorahStoredAssociationRecord(
            location: TorahAssociationLocation(spaceId: "space", target: .object(objectId: "object")),
            item: TorahAssociationItem(
                id: id, kind: kind, role: .context, providerID: "sefaria", externalID: "ref-\(id)",
                canonicalKey: "ref-\(id)", labelHe: "ברכות כג ב", labelEn: "Berakhot 23b",
                unknownFields: ["futureItem": .number(7)]
            )
        )
    }

    private func manifest() -> PinkhaSpaceManifest {
        PinkhaSpaceManifest(
            spaceId: "space", documentAssociationsPropertyId: "internal-id", documentAssociationsPropertyKey: "internal-key",
            registeredDocumentTypes: ["chiddush": "type-chiddush", "article": "type-article", "research": "type-research"]
        )
    }
}
