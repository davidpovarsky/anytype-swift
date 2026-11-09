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

    @Test func eligibilityUsesUniversalDocumentTypesAndExactSpace() {
        let manifest = manifest()
        for id in ["type-chiddush", "type-article", "type-research", "page", "note", "custom-arbitrary-type"] {
            #expect(TorahDocumentPropertyEligibility.includes(typeId: id, spaceId: "space", manifest: manifest))
        }
        for id in [""] {
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

    @Test func internalPropertyIdentityCoversBothCanonicalAndOrderWhilePreservingParent() {
        let manifest = manifest()
        // Canonical storage matches both isCanonicalProperty and isInternalProperty, but NOT isOrderProperty
        #expect(TorahDocumentPropertyEligibility.isCanonicalProperty(id: "internal-id", key: "other", spaceId: "space", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isOrderProperty(id: "internal-id", key: "internal-key", spaceId: "space", manifest: manifest))
        #expect(TorahDocumentPropertyEligibility.isInternalProperty(id: "internal-id", key: "other", spaceId: "space", manifest: manifest))

        // Order storage (סדר) matches isOrderProperty and isInternalProperty, but NOT isCanonicalProperty
        #expect(TorahDocumentPropertyEligibility.isOrderProperty(id: "order-id", key: "other", spaceId: "space", manifest: manifest))
        #expect(TorahDocumentPropertyEligibility.isOrderProperty(id: "other", key: "order-key", spaceId: "space", manifest: manifest))
        #expect(TorahDocumentPropertyEligibility.isOrderStorage(id: "order-id", key: "order-key", spaceId: "space", manifest: manifest))
        #expect(TorahDocumentPropertyEligibility.isInternalProperty(id: "order-id", key: "other", spaceId: "space", manifest: manifest))
        #expect(TorahDocumentPropertyEligibility.isInternalProperty(id: "other", key: "order-key", spaceId: "space", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isCanonicalProperty(id: "order-id", key: "order-key", spaceId: "space", manifest: manifest))

        // User-visible hierarchy field הורה (parentPropertyId / parentPropertyKey) MUST NOT be treated as internal
        #expect(!TorahDocumentPropertyEligibility.isInternalProperty(id: "parent-id", key: "parent-key", spaceId: "space", manifest: manifest))

        // Cross-Space isolation
        #expect(!TorahDocumentPropertyEligibility.isOrderProperty(id: "order-id", key: "order-key", spaceId: "other-space", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isInternalProperty(id: "order-id", key: "order-key", spaceId: "other-space", manifest: manifest))
    }

    @Test func userPropertyWithSameHebrewDisplayNameIsNotCanonicalOrInternal() {
        // H03: User-made properties with the same Hebrew display names "הקשר תורני" or "סדר" but DIFFERENT IDs/keys
        // must not be falsely hidden or matched as canonical or internal storage.
        let manifest = manifest()
        let userPropertyId = "user-prop-123"
        let userPropertyKey = "customKey456"
        #expect(!TorahDocumentPropertyEligibility.isCanonicalProperty(id: userPropertyId, key: userPropertyKey, spaceId: "space", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isCanonicalStorage(id: userPropertyId, key: userPropertyKey, spaceId: "space", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isOrderProperty(id: userPropertyId, key: userPropertyKey, spaceId: "space", manifest: manifest))
        #expect(!TorahDocumentPropertyEligibility.isInternalProperty(id: userPropertyId, key: userPropertyKey, spaceId: "space", manifest: manifest))
    }

    @Test func ordinaryNoteAndGenericTypesAreEligibleForNativeDerivedProperties() {
        let manifest = manifest()
        for ineligibleType in ["note", "page", "task", "journal", "custom-type"] {
            #expect(TorahDocumentPropertyEligibility.includes(typeId: ineligibleType, spaceId: "space", manifest: manifest))
        }
    }

    @Test func nativeDerivedKeysAreExclusivelyVerified() {
        for definition in TorahNativePropertyDefinition.all {
            #expect(TorahDocumentPropertyEligibility.isNativeDerivedKey(definition.key))
        }
        #expect(!TorahDocumentPropertyEligibility.isNativeDerivedKey("internal-key"))
        #expect(!TorahDocumentPropertyEligibility.isNativeDerivedKey("order-key"))
        #expect(!TorahDocumentPropertyEligibility.isNativeDerivedKey("customKey"))
        #expect(!TorahDocumentPropertyEligibility.isNativeDerivedKey("tag"))
    }

    @Test func normalDocumentClassificationRejectsInfrastructureAndLifecycleStates() {
        let manifest = manifest()
        for layout in [0, 1, 2, 3, 9, 11, 14] {
            #expect(TorahDocumentPropertyEligibility.includesDocument(
                objectId: "document", typeId: "arbitrary-user-type", spaceId: "space", layout: layout,
                isTemplate: false, isDeleted: false, isArchived: false, isInternal: false, manifest: manifest
            ))
        }
        for layout in [nil, 4, 5, 7, 10, 12, 13, 18, 19, 24, 999] as [Int?] {
            #expect(!TorahDocumentPropertyEligibility.includesDocument(
                objectId: "record", typeId: "arbitrary-user-type", spaceId: "space", layout: layout,
                isTemplate: false, isDeleted: false, isArchived: false, isInternal: false, manifest: manifest
            ))
        }
        for flag in 0..<4 {
            #expect(!TorahDocumentPropertyEligibility.includesDocument(
                objectId: "record", typeId: "page", spaceId: "space", layout: 0,
                isTemplate: flag == 0, isDeleted: flag == 1, isArchived: flag == 2, isInternal: flag == 3, manifest: manifest
            ))
        }
        #expect(!manifest.isRegisteredDocumentType(typeId: "page"))
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
            spaceId: "space",
            parentPropertyId: "parent-id",
            parentPropertyKey: "parent-key",
            orderPropertyId: "order-id",
            orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "internal-id",
            documentAssociationsPropertyKey: "internal-key",
            registeredDocumentTypes: ["chiddush": "type-chiddush", "article": "type-article", "research": "type-research"]
        )
    }
}
