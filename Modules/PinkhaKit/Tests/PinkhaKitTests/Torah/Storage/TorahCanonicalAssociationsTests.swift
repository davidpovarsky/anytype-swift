import Foundation
import Testing
@testable import PinkhaKit

@Suite("Canonical single-writer Torah association payload")
struct TorahCanonicalAssociationsTests {
    private let codec = TorahAssociationPayloadCodec()
    private let document = TorahAssociationLocation(
        spaceId: "space",
        target: .object(objectId: "document")
    )

    @Test("Legacy v1 lifts to an exact document target and preserves unknown fields")
    func legacyLift() throws {
        let data = Data(#"{"futureEnvelope":{"kept":true},"items":[{"id":"legacy","kind":"ref","role":"source_quote","providerID":"sefaria","externalID":"Genesis.1.1","canonicalKey":"Genesis 1:1","labelHe":"בראשית א:א","futureItem":7}],"version":1}"#.utf8)

        let lifted = try codec.decodeCanonicalDocument(data, legacyLocation: document)
        let record = try #require(lifted.records.first)

        #expect(lifted.version == 2)
        #expect(record.location == document)
        #expect(record.item.role == .sourceQuote)
        #expect(record.item.unknownFields["futureItem"] == .number(7))
        #expect(lifted.unknownFields["futureEnvelope"] == .object(["kept": .bool(true)]))
    }

    @Test("V2 round-trip preserves record and envelope extensions")
    func v2RoundTrip() throws {
        let block = TorahAssociationLocation(
            spaceId: "space",
            target: .block(objectId: "document", blockId: "block")
        )
        let payload = TorahCanonicalAssociationsPayload(
            records: [
                TorahStoredAssociationRecord(
                    location: block,
                    item: association(id: "a"),
                    unknownFields: ["recordFuture": .string("kept")]
                )
            ],
            unknownFields: ["envelopeFuture": .array([.number(1), .null])]
        )

        let data = try codec.encodeCanonicalDocument(payload)
        let reopened = try codec.decodeCanonicalDocument(data, legacyLocation: document)

        #expect(reopened == payload)
        #expect(try codec.encodeCanonicalDocument(reopened) == data)
    }

    @Test("Same source stays distinct across block targets and deduplicates within one target")
    func targetScopedIdentity() {
        let blockA = TorahAssociationLocation(
            spaceId: "space",
            target: .block(objectId: "document", blockId: "a")
        )
        let blockB = TorahAssociationLocation(
            spaceId: "space",
            target: .block(objectId: "document", blockId: "b")
        )
        var payload = TorahCanonicalAssociationsPayload(records: [])
        payload = TorahCanonicalAssociationCollectionPolicy.adding(
            association(id: "first"), to: payload, at: blockA
        ).payload
        payload = TorahCanonicalAssociationCollectionPolicy.adding(
            association(id: "second"), to: payload, at: blockB
        ).payload
        let retry = TorahCanonicalAssociationCollectionPolicy.adding(
            association(id: "retry", label: "updated"), to: payload, at: blockA
        )

        #expect(retry.payload.records.count == 2)
        #expect(TorahCanonicalAssociationCollectionPolicy.items(in: retry.payload, at: blockA).map(\.id) == ["first"])
        #expect(TorahCanonicalAssociationCollectionPolicy.items(in: retry.payload, at: blockA).first?.labelEn == "updated")
        #expect(TorahCanonicalAssociationCollectionPolicy.items(in: retry.payload, at: blockB).map(\.id) == ["second"])
    }

    @Test("Future and corrupt canonical payloads fail closed")
    func safeFailures() {
        #expect(throws: TorahAssociationPayloadCodecError.unsupportedVersion(3)) {
            try codec.decodeCanonicalDocument(
                Data(#"{"version":3,"records":[]}"#.utf8),
                legacyLocation: document
            )
        }
        #expect(throws: TorahAssociationPayloadCodecError.malformedJSON) {
            try codec.decodeCanonicalDocument(Data("{".utf8), legacyLocation: document)
        }
    }

    private func association(id: String, label: String = "Genesis 1:1") -> TorahAssociationItem {
        TorahAssociationItem(
            id: id,
            kind: .ref,
            role: .context,
            providerID: "sefaria",
            externalID: "Genesis.1.1",
            canonicalKey: "Genesis 1:1",
            labelHe: "בראשית א:א",
            labelEn: label
        )
    }
}
