import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

@Suite("Sefaria relationship provider")
struct SefariaRelationshipProviderTests {
    @Test("Rich linked-source data maps to updated Core relationship fields")
    func richRelationships() async throws {
        let url = "https://www.sefaria.org/api/links/Genesis%201:1?with_text=1"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(data: try TorahFixture.data("links"))
        ])
        let sources = try await SefariaRelationshipProvider(client: SefariaClient(transport: transport))
            .links(for: "Genesis 1:1")

        #expect(sources.count == 2)
        let commentary = try #require(sources.first)
        #expect(commentary.sourceRef == "Rashi on Genesis 1:1:1")
        #expect(commentary.canonicalBookID == "Rashi on Genesis")
        #expect(commentary.anchorRefs == ["Genesis 1:1"])
        #expect(commentary.relationshipKind == .commentary)
        #expect(commentary.semanticCategory == .commentary)
        #expect(commentary.hebrewCollectiveTitle == "רש״י")
        #expect(commentary.hebrewText == "אָמַר רַבִּי יִצְחָק")
        #expect(commentary.englishText == "Rabbi Isaac said")
        #expect(commentary.versionTitle == "Sefaria Community Translation")
        #expect(commentary.license == "CC-BY-SA")

        let midrash = sources[1]
        #expect(midrash.relationshipKind == .link)
        #expect(midrash.semanticCategory == .midrash)
        #expect(midrash.anchorRefs == ["Genesis 1:1"])
        #expect(midrash.rawProviderPayload.contains("Genesis Rabbah"))
    }

    @Test("Relationship groups are deterministic and remove exact duplicates")
    func relationshipGrouping() async throws {
        let url = "https://www.sefaria.org/api/links/Genesis%201:1?with_text=1"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(data: try TorahFixture.data("links"))
        ])
        let sources = try await SefariaRelationshipProvider(client: SefariaClient(transport: transport))
            .links(for: "Genesis 1:1")
        let groups = TorahRelationshipGroups(sources: sources + sources)

        #expect(groups.commentary.count == 1)
        #expect(groups.linkedSources.count == 1)
        #expect(groups.commentaryGroups.map(\.id) == ["Rashi on Genesis"])
        #expect(groups.linkedSourceGroups.count == 1)
        #expect(groups.commentaryGroups[0].entries.count == 1)
    }

    @Test("Reference topics retain localized titles and deduplicate slugs")
    func linkedTopics() async throws {
        let url = "https://www.sefaria.org/api/ref-topic-links/Genesis%201:1?interface_lang=english"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(data: try TorahFixture.data("topics"))
        ])
        let topics = try await SefariaRelationshipProvider(client: SefariaClient(transport: transport))
            .topics(for: "Genesis 1:1")

        #expect(topics.map(\.slug) == ["creation", "light"])
        #expect(topics[0].titleHe == "בריאה")
        #expect(topics[0].titleEn == "Creation")
    }

    @Test("Malformed relationship payload does not become an empty relationship list")
    func malformedRelationships() async throws {
        let url = "https://www.sefaria.org/api/links/Genesis%201:1?with_text=1"
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(json: #"{"links":[]}"#)
        ])
        await #expect(throws: TorahError.malformedResponse) {
            _ = try await SefariaRelationshipProvider(client: SefariaClient(transport: transport))
                .links(for: "Genesis 1:1")
        }
    }
}
