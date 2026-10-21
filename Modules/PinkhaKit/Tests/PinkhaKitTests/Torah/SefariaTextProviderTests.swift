import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

@Suite("Sefaria text provider")
struct SefariaTextProviderTests {
    @Test("V3 section text preserves segment order, gaps, navigation, version and license")
    func sectionText() async throws {
        let metadata = #"{"is_ref":true,"depth":2,"start_indexes":[1],"start_labels":["1"],"navigation_refs":{"prev_section_ref":"Genesis 0","next_section_ref":"Genesis 2"}}"#
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: metadata),
            textURL: MockHTTPResponse(data: try TorahFixture.data("text-section"))
        ])
        let provider = SefariaTextProvider(client: SefariaClient(transport: transport))

        let document = try await provider.fetchText(reference: "Genesis 1", request: TorahTextRequest())

        #expect(document.canonicalRef == "Genesis 1")
        #expect(document.sectionRef == "Genesis 1")
        #expect(document.segments.map(\.canonicalRef) == ["Genesis 1:1", "Genesis 1:3"])
        #expect(document.segments.map(\.hebrewRef) == ["בראשית א׳:א׳", "בראשית א׳:ג׳"])
        #expect(document.segments.map(\.ordinal) == [1, 3])
        #expect(document.previousSectionRef == "Genesis 0")
        #expect(document.nextSectionRef == "Genesis 2")
        #expect(document.version.versionTitle == "Fixture Hebrew")
        #expect(document.version.license == "CC-BY")
        #expect(document.version.direction == "rtl")
    }

    @Test("Section-derived Hebrew segment labels use correct 15 and 16 numerals")
    func sectionDerivedHebrewFifteenAndSixteen() throws {
        let root: [String: Any] = [
            "ref": "Genesis 1:15-16",
            "heRef": "בראשית א׳:ט״ו-ט״ז",
            "sectionRef": "Genesis 1",
            "heSectionRef": "בראשית א׳",
            "versions": [[
                "language": "he",
                "versionTitle": "Fixture",
                "text": ["חמשה עשר", "ששה עשר"]
            ]]
        ]
        let metadata: [String: Any] = [
            "depth": 2,
            "start_indexes": [1, 15],
            "end_indexes": [1, 16]
        ]

        let document = try SefariaTextProvider.decode(
            requestedReference: "Genesis 1:15-16",
            root: root,
            metadata: metadata
        )

        #expect(document.segments.map(\.hebrewRef) == ["בראשית א׳:ט״ו", "בראשית א׳:ט״ז"])
    }

    @Test("Complex daf sections never fabricate Hebrew segment labels")
    func complexDafDoesNotFabricateHebrewRef() throws {
        #expect(SefariaTextProvider.localizedSegmentReference(
            sectionRef: "Berakhot 2a",
            hebrewSectionRef: "ברכות ב׳ א",
            ordinal: 1,
            depth: 2
        ) == nil)
        #expect(SefariaTextProvider.localizedSegmentReference(
            sectionRef: "Genesis 1-2",
            hebrewSectionRef: "בראשית א׳-ב׳",
            ordinal: 1,
            depth: 2
        ) == nil)
    }

    @Test("Documented one-based Genesis 1:1 indexes remain ordinal one")
    func documentedFirstSegmentOrdinal() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201:1"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201:1?version=hebrew&fill_in_missing_segments=0&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(data: try TorahFixture.data("reference-resolved")),
            textURL: MockHTTPResponse(json: #"{"ref":"Genesis 1:1","heRef":"בראשית א׳:א׳","sectionRef":"Genesis 1","versions":[{"language":"he","versionTitle":"Fixture","text":"בראשית"}]}"#)
        ])

        let document = try await SefariaTextProvider(client: SefariaClient(transport: transport))
            .fetchText(
                reference: "Genesis 1:1",
                request: TorahTextRequest(language: "hebrew", fillInMissingSegments: false)
            )

        #expect(document.canonicalRef == "Genesis 1:1")
        #expect(document.sectionRef == "Genesis 1")
        #expect(document.segments.map(\.canonicalRef) == ["Genesis 1:1"])
        #expect(document.segments.map(\.ordinal) == [1])
    }

    @Test("Exact segment identity is preserved")
    func exactSegment() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201:7"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201:7?version=hebrew&fill_in_missing_segments=0&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true,"depth":2,"start_indexes":[1,7],"start_labels":["1","7"],"end_indexes":[1,7],"end_labels":["1","7"],"navigation_refs":{}}"#),
            textURL: MockHTTPResponse(json: #"{"ref":"Genesis 1:7","heRef":"בראשית א׳:ז׳","sectionRef":"Genesis 1","versions":[{"language":"he","versionTitle":"Fixture","text":"פסוק"}]}"#)
        ])
        let document = try await SefariaTextProvider(client: SefariaClient(transport: transport))
            .fetchText(
                reference: "Genesis 1:7",
                request: TorahTextRequest(language: "hebrew", fillInMissingSegments: false)
            )

        #expect(document.canonicalRef == "Genesis 1:7")
        #expect(document.sectionRef == "Genesis 1")
        #expect(document.segments.count == 1)
        #expect(document.segments[0].canonicalRef == "Genesis 1:7")
        #expect(document.segments[0].ordinal == 7)
    }

    @Test("Same-section ranges start at the documented ordinal and retain gaps")
    func rangedReferenceOrdinal() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201:7-9"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201:7-9?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true,"depth":2,"start_indexes":[1,7],"start_labels":["1","7"],"end_indexes":[1,9],"end_labels":["1","9"],"navigation_refs":{}}"#),
            textURL: MockHTTPResponse(json: #"{"ref":"Genesis 1:7-9","heRef":"בראשית א׳:ז׳-ט׳","sectionRef":"Genesis 1","versions":[{"language":"he","versionTitle":"Fixture","text":["שבע","","תשע"]}]}"#)
        ])

        let document = try await SefariaTextProvider(client: SefariaClient(transport: transport))
            .fetchText(reference: "Genesis 1:7-9")

        #expect(document.canonicalRef == "Genesis 1:7-9")
        #expect(document.sectionRef == "Genesis 1")
        #expect(document.segments.map(\.canonicalRef) == ["Genesis 1:7", "Genesis 1:9"])
        #expect(document.segments.map(\.ordinal) == [7, 9])
    }

    @Test("Cross-section ranges fail instead of fabricating segment identities")
    func crossSectionRangeDoesNotFabricateSegmentRefs() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201:31-2:2"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201:31-2:2?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true,"depth":2,"start_indexes":[1,31],"end_indexes":[2,2],"navigation_refs":{}}"#),
            textURL: MockHTTPResponse(json: #"{"ref":"Genesis 1:31-2:2","sectionRef":"Genesis 1","versions":[{"language":"he","versionTitle":"Fixture","text":["thirty-one","one","two"]}]}"#)
        ])

        await #expect(throws: TorahError.malformedResponse) {
            _ = try await SefariaTextProvider(client: SefariaClient(transport: transport))
                .fetchText(reference: "Genesis 1:31-2:2")
        }
    }

    @Test("Unavailable requested version falls back to source without relabeling language")
    func sourceFallback() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201"
        let requestedURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let sourceURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=source&fill_in_missing_segments=1&return_format=text_only"
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true,"depth":2,"start_indexes":[1],"start_labels":["1"],"navigation_refs":{}}"#),
            requestedURL: MockHTTPResponse(json: #"{"ref":"Genesis 1","sectionRef":"Genesis 1","versions":[]}"#),
            sourceURL: MockHTTPResponse(json: #"{"ref":"Genesis 1","sectionRef":"Genesis 1","versions":[{"language":"en","actualLanguage":"en","versionTitle":"English Source","direction":"ltr","text":["In the beginning"]}]}"#)
        ])

        let document = try await SefariaTextProvider(client: SefariaClient(transport: transport))
            .fetchText(reference: "Genesis 1")

        #expect(document.version.language == "en")
        #expect(document.version.actualLanguage == "en")
        #expect(document.version.versionTitle == "English Source")
        #expect(document.version.direction == "ltr")
        #expect(document.segments[0].text == "In the beginning")
    }

    @Test("No available version is noText rather than a fake empty document")
    func noAvailableVersion() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201"
        let requestedURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let sourceURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=source&fill_in_missing_segments=1&return_format=text_only"
        let empty = #"{"ref":"Genesis 1","sectionRef":"Genesis 1","versions":[]}"#
        let transport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true}"#),
            requestedURL: MockHTTPResponse(json: empty),
            sourceURL: MockHTTPResponse(json: empty)
        ])
        await #expect(throws: TorahError.noText) {
            _ = try await SefariaTextProvider(client: SefariaClient(transport: transport))
                .fetchText(reference: "Genesis 1")
        }
    }

    @Test("Malformed text and failed HTTP are distinct")
    func textErrors() async throws {
        let metadataURL = "https://www.sefaria.org/api/ref/Genesis%201"
        let textURL = "https://www.sefaria.org/api/v3/texts/Genesis%201?version=hebrew&fill_in_missing_segments=1&return_format=text_only"
        let malformedTransport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true}"#),
            textURL: MockHTTPResponse(json: "not-json")
        ])
        await #expect(throws: TorahError.malformedResponse) {
            _ = try await SefariaTextProvider(client: SefariaClient(transport: malformedTransport))
                .fetchText(reference: "Genesis 1")
        }

        let failedTransport = MockTorahHTTPTransport(responses: [
            metadataURL: MockHTTPResponse(json: #"{"is_ref":true}"#),
            textURL: MockHTTPResponse(statusCode: 503, json: #"{"error":"unavailable"}"#)
        ])
        do {
            _ = try await SefariaTextProvider(client: SefariaClient(transport: failedTransport))
                .fetchText(reference: "Genesis 1")
            Issue.record("Expected HTTP failure")
        } catch let error as TorahError {
            guard case .network(let message) = error else {
                Issue.record("Expected network status error, got \(error)")
                return
            }
            #expect(message.contains("503"))
        }
    }

    @Test("Full segment display normalization is faithful, unbounded and keeps raw payload")
    func fullSegmentDisplayNormalization() throws {
        let longTail = String(repeating: "אבגדה ", count: 900)
        let root: [String: Any] = [
            "ref": "Genesis 1",
            "heRef": "בראשית א׳",
            "sectionRef": "Genesis 1",
            "heSectionRef": "בראשית א׳",
            "versions": [[
                "language": "he",
                "versionTitle": "Fixture",
                "direction": "rtl",
                "text": [
                    "בְּרֵאשִׁית&nbsp;<b>בָּרָא</b> &amp; &#1492;&#X5D0;",
                    "&lt;מילולי&gt; <span>מילה</span><span>נוספת</span> <b>מודגש</b><b>צמוד</b><br>שורה<p>פסקה</p>",
                    "סימן & לא־ישות &unknown; &amp;lt;שמור&amp;gt; " + longTail
                ]
            ]]
        ]
        let metadata: [String: Any] = [
            "depth": 2,
            "start_indexes": [1],
            "navigation_refs": [:]
        ]

        let document = try SefariaTextProvider.decode(
            requestedReference: "Genesis 1",
            root: root,
            metadata: metadata
        )

        #expect(document.segments.count == 3)
        #expect(document.segments[0].text == "בְּרֵאשִׁית\u{00A0}בָּרָא & הא")
        #expect(document.segments[1].text == "<מילולי> מילה נוספת מודגש צמוד\nשורה\nפסקה")
        #expect(document.segments[2].text.contains("סימן & לא־ישות &unknown; <שמור>"))
        #expect(document.segments[2].text.count > 4_096)
        #expect(document.segments.map(\.ordinal) == [1, 2, 3])
        #expect(document.segments.map(\.canonicalRef) == ["Genesis 1:1", "Genesis 1:2", "Genesis 1:3"])
        #expect(document.rawProviderPayload == SefariaJSON.payload(root))
    }

    @Test("Already-clean text and invalid entities are left intact")
    func cleanTextIsStable() {
        let clean = "וְהָאָרֶץ הָיְתָה < בין & ובין"
        #expect(SefariaDisplayText.fullSegment(clean) == clean)
        #expect(SefariaDisplayText.fullSegment("&#xD800; &#1114112;") == "&#xD800; &#1114112;")
        #expect(SefariaDisplayText.fullSegment("&#x202E;") == "&#x202E;")
    }

    @Test("Genesis 1:5 spacing and standard typography entities decode at the provider boundary")
    func genesisOneFiveEntityFixture() {
        let providerText = "וַיִּקְרָא אֱלֹהִים לָאוֹר יוֹם&thinsp;&thinsp;&nbsp;וְלַחֹשֶׁךְ קָרָא לָיְלָה&hellip; &ldquo;יוֹם&rdquo; &ndash; &amp;"
        let displayed = SefariaDisplayText.fullSegment(providerText)

        #expect(displayed == "וַיִּקְרָא אֱלֹהִים לָאוֹר יוֹם\u{2009}\u{2009}\u{00A0}וְלַחֹשֶׁךְ קָרָא לָיְלָה… “יוֹם” – &")
        #expect(!displayed.contains("&thinsp;"))
        #expect(!displayed.contains("&nbsp;"))
    }

    @Test("Entity decoding is bounded, case tolerant and preserves unknown names")
    func entityCoverageAndBounds() {
        let encoded = "א&ensp;&emsp;ב&shy;&lrm;&rlm;&mdash;&Prime;&#65;&#x42;&#X43; &unknown; &amp;amp;"
        let decoded = SefariaDisplayText.fullSegment(encoded)

        #expect(decoded == "א\u{2002}\u{2003}ב\u{00AD}\u{200E}\u{200F}—″ABC &unknown; &")
    }
}
