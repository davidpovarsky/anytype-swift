import Foundation
import Testing
@testable import PinkhaKit

@Suite("Go and Swift canonical query projection parity")
struct TorahDerivedQueryProjectionTests {
    @Test func sharedGoldenFixtures() throws {
        let url = try #require(Bundle.module.url(forResource: "derived-query-golden", withExtension: "json"))
        let fixtures = try JSONDecoder().decode([Fixture].self, from: Data(contentsOf: url))
        for fixture in fixtures where fixture.error == nil {
            let raw = Data(fixture.raw.utf8)
            let payload = fixture.raw.isEmpty ? TorahCanonicalAssociationsPayload(records: []) : try TorahAssociationPayloadCodec()
                .decodeCanonicalDocument(raw, legacyLocation: TorahAssociationLocation(spaceId: fixture.space, target: .object(objectId: fixture.object)))
            let expected = try #require(fixture.expected)
            let projection = TorahDocumentPropertyProjection(records: payload.records, spaceId: fixture.space, objectId: fixture.object)
            let derived = TorahDerivedQueryProjection(records: payload.records, spaceId: fixture.space, objectId: fixture.object)
            #expect(projection.sources.map(\.id) == expected.sourceIDs, "\(fixture.name)")
            #expect(projection.topics.map(\.id) == expected.topicIDs, "\(fixture.name)")
            #expect(projection.words.map(\.id) == expected.wordIDs, "\(fixture.name)")
            #expect(derived.sources == expected.sources, "\(fixture.name)")
            #expect(derived.topics == expected.topics, "\(fixture.name)")
            #expect(derived.words == expected.words, "\(fixture.name)")
            #expect(Data(fixture.raw.utf8) == raw)
        }
    }

    @Test func errorsDoNotBecomeEmpty() throws {
        let url = try #require(Bundle.module.url(forResource: "derived-query-golden", withExtension: "json"))
        let fixtures = try JSONDecoder().decode([Fixture].self, from: Data(contentsOf: url))
        for fixture in fixtures where fixture.error != nil {
            #expect(throws: (any Error).self, "\(fixture.name)") {
                try TorahAssociationPayloadCodec().decodeCanonicalDocument(
                    fixture.raw,
                    legacyLocation: TorahAssociationLocation(spaceId: fixture.space, target: .object(objectId: fixture.object))
                )
            }
        }
    }
}

private struct Fixture: Decodable {
    let name: String
    let space: String
    let object: String
    let raw: String
    let error: String?
    let expected: Expected?
}

private struct Expected: Decodable {
    let sourceIDs: [String]
    let topicIDs: [String]
    let wordIDs: [String]
    let sources: [String]
    let topics: [String]
    let words: [String]
}
