import Foundation
import Testing
@testable import PinkhaKit

@Suite("Semantic association target persistence and legacy identity")
struct TorahSemanticAnchorAssociationTests {
    private let location = TorahAssociationLocation(spaceId: "space", target: .object(objectId: "object"))
    private func item(id: String = "association-1") -> TorahAssociationItem {
        .init(id: id, kind: .ref, role: .context, providerID: "sefaria",
              externalID: "Genesis 1:1", canonicalKey: "Genesis 1:1", labelHe: "בראשית א:א",
              customMetadata: ["future": "preserve"], unknownFields: ["future": .bool(true)])
    }

    @Test func nativePayloadRoundtripRetainsStableAssociationAndAnchorIDsWithoutOffsets() throws {
        let anchor = try PinkhaSemanticTextAnchor(spaceID: "space", objectID: "object")
        let binding = TorahSemanticAnchorAssociation(anchor: anchor)
        let saved = try binding.attaching(to: item(), location: location)
        let reopened = try JSONDecoder().decode(TorahAssociationItem.self, from: JSONEncoder().encode(saved))
        #expect(try TorahSemanticAnchorAssociation.decoding(reopened, location: location) == binding)
        #expect(reopened.id == "association-1")
        #expect(reopened.customMetadata?["future"] == "preserve")
        #expect(reopened.unknownFields == ["future": .bool(true)])
        let payload = try #require(reopened.customMetadata?[TorahSemanticAnchorAssociation.metadataKey])
        let json = try #require(JSONSerialization.jsonObject(with: Data(payload.utf8)) as? [String: Any])
        #expect(Set(json.keys) == ["version", "marker"])
    }

    @Test func differentPhrasesAndWholeDocumentRemainDifferentWhileSameMarkerRetriesDeduplicate() throws {
        let one = try TorahSemanticAnchorAssociation(anchor: .init(spaceID: "space", objectID: "object"))
            .attaching(to: item(), location: location)
        let two = try TorahSemanticAnchorAssociation(anchor: .init(spaceID: "space", objectID: "object"))
            .attaching(to: item(id: "association-2"), location: location)
        let whole = item(id: "whole-document")
        let items = TorahAssociationCollectionPolicy.adding(two, to: [one, whole], location: location)
        #expect(items.count == 3)
        var retry = one
        retry.id = "retry-id"
        #expect(TorahAssociationCollectionPolicy.adding(retry, to: items, location: location).count == 3)
        #expect(TorahAssociationCollectionPolicy.adding(retry, to: items, location: location).contains { $0.id == one.id })
    }

    @Test func legacyStorageKeyIsByteForByteUnchangedAndUnknownTargetsNeverMasqueradeAsLegacy() throws {
        let legacy = item()
        #expect(TorahAssociationIdentity(item: legacy, location: location).storageKey ==
            "5:space|6:object|0:|3:ref|7:context|7:sefaria|11:Genesis 1:1|0:")
        var unknown = legacy
        unknown.id = "unknown"
        unknown.customMetadata?[TorahSemanticAnchorAssociation.metadataKey] = "{\"version\":99,\"marker\":\"future\"}"
        #expect(TorahSemanticAnchorAssociation.hasReservedMetadata(unknown))
        #expect(throws: (any Error).self) { try TorahSemanticAnchorAssociation.decoding(unknown, location: location) }
        #expect(TorahAssociationCollectionPolicy.adding(unknown, to: [legacy], location: location).count == 2)
    }

    @Test func scopeAndStorageOwnershipMustMatchBeforeReadingOrWritingSemanticMetadata() throws {
        let binding = TorahSemanticAnchorAssociation(anchor: try .init(spaceID: "space", objectID: "object"))
        let saved = try binding.attaching(to: item(), location: location)
        let invalidLocations: [TorahAssociationLocation] = [
            .init(spaceId: "other-space", target: .object(objectId: "object")),
            .init(spaceId: "space", target: .object(objectId: "other-object")),
            .init(spaceId: "space", target: .block(objectId: "object", blockId: "old-block"))
        ]
        for location in invalidLocations {
            #expect(throws: (any Error).self) { try TorahSemanticAnchorAssociation.decoding(saved, location: location) }
            #expect(throws: (any Error).self) { try binding.attaching(to: item(), location: location) }
        }
    }
}
