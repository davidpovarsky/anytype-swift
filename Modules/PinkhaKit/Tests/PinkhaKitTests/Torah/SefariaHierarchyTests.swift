import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

@Suite("Sefaria source hierarchy")
struct SefariaHierarchyTests {
    @Test("TOC category tree preserves canonical books and uses bounded cache")
    func tocAndCache() async throws {
        let url = "https://www.sefaria.org/api/index"
        let cache = InMemoryTorahHierarchyCache()
        let date = Date(timeIntervalSince1970: 10_000)
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(data: try TorahFixture.data("toc"))
        ])
        let provider = SefariaHierarchyProvider(
            client: SefariaClient(transport: transport),
            cache: cache,
            ttl: 60,
            now: { date }
        )

        let first = try await provider.fetchHierarchy()
        let second = try await provider.fetchHierarchy()

        #expect(first.providerID == "sefaria")
        #expect(first.roots.map(\.labelEn) == ["Tanakh", "Talmud"])
        #expect(first.roots[0].children[0].children.map(\.canonicalKey) == ["Genesis", "Exodus"])
        #expect(second.roots.count == first.roots.count)
        #expect(await transport.urls() == [url])
    }

    @Test("Path compression keeps canonical tree while projecting single-child chains")
    func compression() {
        let genesis = TorahSourceNode(
            id: "Genesis",
            labelHe: "בראשית",
            labelEn: "Genesis",
            canonicalKey: "Genesis"
        )
        let torah = TorahSourceNode(id: "Torah", labelHe: "תורה", children: [genesis])
        let tanakh = TorahSourceNode(id: "Tanakh", labelHe: "תנ״ך", children: [torah])

        #expect(tanakh.children[0].id == "Torah")
        #expect(tanakh.compressedTarget.id == "Genesis")
        #expect(tanakh.compressedPath().breadcrumbs == ["תנ״ך", "תורה", "בראשית"])
    }

    @Test("Filtering creates passage nodes and avoids leading-title false matches")
    func exactBookFiltering() throws {
        let roots = try SefariaHierarchyProvider.decodeTOC(TorahFixture.data("toc"))
        let hierarchy = TorahSourceHierarchy(roots: roots, providerID: "sefaria")
        let groups = [
            (canonicalKey: "Genesis Rabbah 1:1", labelHe: "בראשית רבה א׳:א׳", leafCount: 2)
        ]
        let filtered = hierarchy.filtered(
            byAssociatedKeys: Set(groups.map(\.canonicalKey)),
            associationGroups: groups
        )

        let allBooks = flattenedCanonicalKeys(filtered.roots)
        #expect(allBooks.contains("Genesis Rabbah"))
        #expect(allBooks.contains("Genesis Rabbah 1:1"))
        #expect(!allBooks.contains("Genesis"))
        #expect(filtered.roots[0].descendantLeafCount == 2)
    }

    @Test("Filtering supports Genesis chapters and Rosh Hashanah daf references")
    func passageFiltering() throws {
        let roots = try SefariaHierarchyProvider.decodeTOC(TorahFixture.data("toc"))
        let hierarchy = TorahSourceHierarchy(roots: roots, providerID: "sefaria")
        let groups = [
            (canonicalKey: "Genesis 1:1", labelHe: "בראשית א׳:א׳", leafCount: 3),
            (canonicalKey: "Rosh Hashanah 16b", labelHe: "ראש השנה ט״ז ב׳", leafCount: 1)
        ]
        let filtered = hierarchy.filtered(
            byAssociatedKeys: Set(groups.map(\.canonicalKey)),
            associationGroups: groups
        )
        let keys = flattenedCanonicalKeys(filtered.roots)

        #expect(keys.contains("Genesis"))
        #expect(keys.contains("Genesis 1:1"))
        #expect(keys.contains("Rosh Hashanah"))
        #expect(keys.contains("Rosh Hashanah 16b"))
    }

    @Test("Book fallback recognizes numeric and Roman title prefixes")
    func numberedBookTitles() {
        #expect(TorahReferenceUtil.bookTitle(from: "1 Samuel 3:4") == "1 Samuel")
        #expect(TorahReferenceUtil.bookTitle(from: "2 Kings 4:1") == "2 Kings")
        #expect(TorahReferenceUtil.bookTitle(from: "4 Maccabees 2:3") == "4 Maccabees")
        #expect(TorahReferenceUtil.bookTitle(from: "II Kings 3:4") == "II Kings")
        #expect(TorahReferenceUtil.bookTitle(from: "Genesis 1:1") == "Genesis")
        #expect(TorahReferenceUtil.bookTitle(from: "Rosh Hashanah 16b") == "Rosh Hashanah")
    }

    @Test("Hierarchy filtering keeps numbered books exact without cross-matching")
    func numberedBookFiltering() throws {
        let roots = try SefariaHierarchyProvider.decodeTOC(TorahFixture.data("toc"))
        let hierarchy = TorahSourceHierarchy(roots: roots, providerID: "sefaria")
        let groups = [
            (canonicalKey: "1 Samuel 3:4", labelHe: "שמואל א׳ ג׳:ד׳", leafCount: 1),
            (canonicalKey: "2 Kings 4:1", labelHe: "מלכים ב׳ ד׳:א׳", leafCount: 2),
            (canonicalKey: "4 Maccabees 2:3", labelHe: "מקבים ד׳ ב׳:ג׳", leafCount: 1)
        ]
        let filtered = hierarchy.filtered(
            byAssociatedKeys: Set(groups.map(\.canonicalKey)),
            associationGroups: groups
        )
        let keys = flattenedCanonicalKeys(filtered.roots)

        #expect(keys.contains("1 Samuel"))
        #expect(keys.contains("1 Samuel 3:4"))
        #expect(keys.contains("2 Kings"))
        #expect(keys.contains("2 Kings 4:1"))
        #expect(keys.contains("4 Maccabees"))
        #expect(keys.contains("4 Maccabees 2:3"))
        #expect(!keys.contains("II Kings"))
        #expect(!keys.contains("Genesis"))
        #expect(!keys.contains("Genesis Rabbah"))
    }

    @Test("Malformed TOC is reported")
    func malformedTOC() {
        #expect(throws: TorahError.malformedResponse) {
            _ = try SefariaHierarchyProvider.decodeTOC(Data(#"{"contents":[]}"#.utf8))
        }
    }

    private func flattenedCanonicalKeys(_ nodes: [TorahSourceNode]) -> Set<String> {
        var result = Set<String>()
        for node in nodes {
            if let key = node.canonicalKey { result.insert(key) }
            result.formUnion(flattenedCanonicalKeys(node.children))
        }
        return result
    }
}
