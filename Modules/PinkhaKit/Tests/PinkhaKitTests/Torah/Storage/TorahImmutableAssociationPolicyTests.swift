import Foundation
import Testing
@testable import PinkhaKit

struct TorahImmutableAssociationPolicyTests {
    private let location = TorahAssociationLocation(spaceId: "space", target: .object(objectId: "object"))

    private func item(_ id: String = "stable", role: TorahAssociationRole = .context,
                      ref: String = "Genesis.1.1", label: String = "בראשית") -> TorahAssociationItem {
        .init(id: id, kind: .ref, role: role, providerID: "sefaria",
              externalID: ref, canonicalKey: ref, labelHe: label)
    }

    private func payload(_ item: TorahAssociationItem,
                         recordUnknown: [String: TorahJSONValue] = [:],
                         envelopeUnknown: [String: TorahJSONValue] = [:],
                         at target: TorahAssociationLocation? = nil) throws -> Data {
        try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(
            records: [.init(location: target ?? location, item: item, unknownFields: recordUnknown)],
            unknownFields: envelopeUnknown))
    }

    private func claim(_ number: Int, _ bytes: Data) throws -> TorahImmutableAssociationClaim {
        let record = try TorahAssociationPayloadCodec().decodeCanonicalDocument(bytes, legacyLocation: location).records[0]
        let id = String(repeating: "a", count: 64) + "/" +
            String(format: "%064x", number)
        return try .init(claimID: id, content: .init(payload: bytes, location: location,
            providerID: record.item.providerID,
            canonicalRef: record.item.canonicalKey.isEmpty ? record.item.externalID : record.item.canonicalKey))
    }

    @Test func defaultDuplicatePolicyKeepsEveryVariantAndRefusesWrites() throws {
        let bytes = try payload(item())
        let claims = try [claim(1, bytes), claim(2, bytes)]
        let state = try TorahImmutableAssociationPolicy.project(claims, at: location)
        #expect(state.entries.count == 2)
        #expect(state.entries.flatMap(\.observedClaimIDs).sorted() == claims.map(\.claimID).sorted())
        #expect(state.conflicts.count == 1)
        #expect(throws: TorahAssociationRepositoryError.self) {
            try TorahImmutableAssociationPolicy.removing(associationID: "stable", from: state)
        }
    }

    @Test func explicitEqualFactsKeepBothClaimsAndRemoveAllObservedClaims() throws {
        let bytes = try payload(item())
        let pretty = try JSONSerialization.data(withJSONObject: JSONSerialization.jsonObject(with: bytes),
                                                 options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
        #expect(bytes != pretty)
        let claims = try [claim(1, bytes), claim(2, pretty)]
        let state = try TorahImmutableAssociationPolicy.project(claims, at: location,
                                                               duplicates: .coalesceEqualCanonicalFacts)
        #expect(state.entries.count == 1)
        #expect(state.entries[0].claims.map(\.content.originalPayload) == [bytes, pretty])
        #expect(state.conflicts.isEmpty)
        #expect(try TorahImmutableAssociationPolicy.plan(item(), in: state, requireExisting: true).mutation == nil)
        let remove = try #require(try TorahImmutableAssociationPolicy.removing(associationID: "stable", from: state))
        #expect(remove.kind == .remove)
        #expect(remove.observed == claims.map(\.claimID).sorted())
        #expect(remove.payload.isEmpty && remove.providerID.isEmpty && remove.canonicalRef.isEmpty)
    }

    @Test func canonicalEqualityIncludesUnknownEnvelopeRecordAndItemFields() throws {
        let original = try payload(item(), recordUnknown: ["record": .number(7)],
                                   envelopeUnknown: ["envelope": .bool(true)])
        var variant = item(); variant.unknownFields["futureItem"] = .string("retained")
        let variants = try [
            payload(item(), recordUnknown: ["record": .number(8)], envelopeUnknown: ["envelope": .bool(true)]),
            payload(item(), recordUnknown: ["record": .number(7)], envelopeUnknown: ["envelope": .bool(false)]),
            payload(variant, recordUnknown: ["record": .number(7)], envelopeUnknown: ["envelope": .bool(true)])
        ]
        for bytes in variants {
            let state = try TorahImmutableAssociationPolicy.project([claim(1, original), claim(2, bytes)],
                at: location, duplicates: .coalesceEqualCanonicalFacts)
            #expect(state.entries.count == 2 && !state.conflicts.isEmpty)
            #expect(throws: TorahAssociationRepositoryError.self) {
                try TorahImmutableAssociationPolicy.plan(item(), in: state, requireExisting: false)
            }
        }
    }

    @Test func sameStableIDWithChangedSourceRemainsExplicitConflict() throws {
        let state = try TorahImmutableAssociationPolicy.project([
            claim(1, payload(item())), claim(2, payload(item(ref: "Exodus.1.1")))
        ], at: location, duplicates: .coalesceEqualCanonicalFacts)
        #expect(state.entries.count == 2)
        #expect(state.conflicts.contains { $0.reason == "stable association ID changed identity concurrently" })
        #expect(throws: TorahAssociationRepositoryError.self) {
            try TorahImmutableAssociationPolicy.removing(associationID: "stable", from: state)
        }
    }

    @Test func nativeCollisionOrMissingPredecessorNeverDisappearsUnderCoalescing() throws {
        let claims = try [claim(1, payload(item())), claim(2, payload(item()))]
        for reason in ["same operation ID carries different payloads", "observed predecessor is not yet resolved"] {
            let native = TorahImmutableAssociationConflict(claimIDs: claims.map(\.claimID), reason: reason)
            let state = try TorahImmutableAssociationPolicy.project(claims, at: location,
                nativeConflicts: [native], duplicates: .coalesceEqualCanonicalFacts)
            #expect(state.entries.count == 1)
            #expect(state.conflicts == [native])
            #expect(throws: TorahAssociationRepositoryError.self) {
                try TorahImmutableAssociationPolicy.plan(item(), in: state, requireExisting: true)
            }
        }
    }

    @Test func replacementPreservesStableIdentityAndAllUnknownLevels() throws {
        var original = item()
        original.createdAt = Date(timeIntervalSince1970: 1_700_000_000)
        original.rawInput = "original input"
        original.providerPayload = "provider bytes"
        original.customMetadata = ["existing": "value"]
        original.unknownFields = ["old": .number(7)]
        let bytes = try payload(original, recordUnknown: ["record": .bool(true)],
                                envelopeUnknown: ["envelope": .array([.number(3)])])
        let nativeClaim = try claim(1, bytes)
        let state = try TorahImmutableAssociationPolicy.project([nativeClaim], at: location)
        var incoming = item("new-proposed-id", label: "updated")
        incoming.customMetadata = ["added": "value"]
        incoming.unknownFields = ["new": .bool(true)]
        let plan = try TorahImmutableAssociationPolicy.plan(incoming, in: state, requireExisting: false)
        #expect(plan.item.id == "stable")
        #expect(plan.item.createdAt == original.createdAt)
        #expect(plan.item.rawInput == original.rawInput && plan.item.providerPayload == original.providerPayload)
        #expect(plan.item.customMetadata == ["existing": "value", "added": "value"])
        #expect(plan.item.unknownFields == ["old": .number(7), "new": .bool(true)])
        let mutation = try #require(plan.mutation)
        #expect(mutation.kind == .replace && mutation.observed == [nativeClaim.claimID])
        let decoded = try TorahAssociationPayloadCodec().decodeCanonicalDocument(mutation.payload, legacyLocation: location)
        #expect(decoded.unknownFields == ["envelope": .array([.number(3)])])
        #expect(decoded.records[0].unknownFields == ["record": .bool(true)])
        #expect(decoded.records[0].item == plan.item)
    }

    @Test func defaultNoOpComparisonRetainsExistingAnyRawByteBehavior() throws {
        let bytes = try payload(item())
        let pretty = try JSONSerialization.data(withJSONObject: JSONSerialization.jsonObject(with: bytes),
                                                 options: [.prettyPrinted, .sortedKeys])
        let canonical = try TorahImmutableAssociationPolicy.project([claim(1, bytes)], at: location)
        #expect(try TorahImmutableAssociationPolicy.plan(item(), in: canonical, requireExisting: true).mutation == nil)
        let noncanonical = try TorahImmutableAssociationPolicy.project([claim(1, pretty)], at: location)
        let mutation = try #require(TorahImmutableAssociationPolicy.plan(item(), in: noncanonical, requireExisting: true).mutation)
        #expect(mutation.kind == .replace && mutation.payload == bytes)
    }

    @Test func missingUpdateAndMissingRemovalRemainDifferentOutcomes() throws {
        let empty = try TorahImmutableAssociationPolicy.project([], at: location)
        #expect(throws: TorahAssociationRepositoryError.associationNotFound("stable")) {
            try TorahImmutableAssociationPolicy.plan(item(), in: empty, requireExisting: true)
        }
        #expect(try TorahImmutableAssociationPolicy.removing(associationID: "stable", from: empty) == nil)
        let mutation = try #require(TorahImmutableAssociationPolicy.plan(item(), in: empty, requireExisting: false).mutation)
        #expect(mutation.kind == .add && mutation.observed.isEmpty)
        #expect(mutation.location == location)
    }

    @Test func duplicateNativeClaimsAndForeignExactOwnerAreRefused() throws {
        let first = try claim(1, payload(item()))
        #expect(throws: TorahAssociationRepositoryError.malformedCanonicalData) {
            try TorahImmutableAssociationPolicy.project([first, first], at: location)
        }
        let foreign = TorahAssociationLocation(spaceId: "foreign", target: location.target)
        #expect(throws: TorahAssociationRepositoryError.malformedCanonicalData) {
            try TorahImmutableAssociationPolicy.project([first], at: foreign)
        }
        let normalized = TorahAssociationLocation(spaceId: "\u{e9}", target: location.target)
        let decomposed = TorahAssociationLocation(spaceId: "e\u{301}", target: location.target)
        #expect(normalized == decomposed)
        let data = try payload(item(), at: normalized)
        #expect(throws: TorahAssociationRepositoryError.malformedCanonicalData) {
            try TorahImmutableAssociationContent(payload: data, location: decomposed,
                providerID: "sefaria", canonicalRef: "Genesis.1.1")
        }
        #expect(throws: TorahAssociationRepositoryError.malformedCanonicalData) {
            try TorahImmutableAssociationContent(payload: payload(item()), location: location,
                providerID: "other-provider", canonicalRef: "Genesis.1.1")
        }
    }

    @Test func unrepresentableUnknownNumberAndDuplicateJSONAreRefusedBeforePlanning() throws {
        let original = try payload(item())
        let prefix = String(decoding: original, as: UTF8.self).dropLast()
        let numeric = Data((prefix + #","future":9007199254740993}"#).utf8)
        #expect(throws: TorahSourceJSONGuardError.numericPrecisionWouldChange(path: "/future")) {
            try TorahImmutableAssociationContent(payload: numeric, location: location,
                providerID: "sefaria", canonicalRef: "Genesis.1.1")
        }
        let repeated = Data((prefix + #","future":1,"\u0066uture":1}"#).utf8)
        #expect(throws: TorahSourceJSONGuardError.duplicateJSONKey(path: "/future")) {
            try TorahImmutableAssociationContent(payload: repeated, location: location,
                providerID: "sefaria", canonicalRef: "Genesis.1.1")
        }
    }

    @Test func distinctQuotesRemainIndependentAndRemovalIsExactlyScoped() throws {
        let a = try claim(1, payload(item("quote-a", role: .sourceQuote)))
        let b = try claim(2, payload(item("quote-b", role: .sourceQuote)))
        let state = try TorahImmutableAssociationPolicy.project([a, b], at: location,
                                                               duplicates: .coalesceEqualCanonicalFacts)
        #expect(state.entries.count == 2 && state.conflicts.isEmpty)
        let remove = try #require(try TorahImmutableAssociationPolicy.removing(associationID: "quote-a", from: state))
        #expect(remove.observed == [a.claimID])
    }

    @Test func nativeObservedBoundRefusesWithoutDroppingAnyClaim() throws {
        let bytes = try payload(item())
        let claims = try (1...257).map { try claim($0, bytes) }
        let state = try TorahImmutableAssociationPolicy.project(claims, at: location,
                                                               duplicates: .coalesceEqualCanonicalFacts)
        #expect(state.entries.count == 1 && state.entries[0].claims.count == 257)
        #expect(state.entries[0].observedClaimIDs == claims.map(\.claimID).sorted())
        #expect(throws: TorahAssociationRepositoryError.self) {
            try TorahImmutableAssociationPolicy.removing(associationID: "stable", from: state)
        }
        #expect(throws: TorahAssociationRepositoryError.self) {
            try TorahImmutableAssociationPolicy.plan(item(label: "updated"), in: state, requireExisting: true)
        }
    }
}
