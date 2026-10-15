import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

@Suite("Torah association payload codec")
struct TorahAssociationPayloadCodecTests {
    private let codec = TorahAssociationPayloadCodec()

    @Test("Legacy and current source-quote roles decode and encode canonically")
    func roleCompatibility() throws {
        let legacy = Data(#"{"version":1,"items":[{"id":"a","kind":"ref","role":"source_quote","providerID":"sefaria","externalID":"Genesis.1.1","canonicalKey":"Genesis 1:1","labelHe":"בראשית א:א"}]}"#.utf8)
        let current = Data(#"{"version":1,"items":[{"id":"a","kind":"ref","role":"sourceQuote","providerID":"sefaria","externalID":"Genesis.1.1","canonicalKey":"Genesis 1:1","labelHe":"בראשית א:א"}]}"#.utf8)

        let legacyPayload = try codec.decodeDocument(legacy)
        let currentPayload = try codec.decodeDocument(current)

        #expect(legacyPayload.items[0].role == .sourceQuote)
        #expect(currentPayload.items[0].role == .sourceQuote)
        let encoded = String(decoding: try codec.encodeDocument(legacyPayload), as: UTF8.self)
        #expect(encoded.contains(#""role":"sourceQuote""#))
        #expect(!encoded.contains("source_quote"))
    }

    @Test("Document v1 retains stable IDs, optional provenance, and unknown metadata")
    func documentRoundTripIsLossless() throws {
        let input = Data(#"{"futureEnvelope":{"nested":[1,true,null]},"items":[{"canonicalKey":"Genesis 1:1","createdAt":"2026-01-02T03:04:05.678Z","customMetadata":{"legacy":"yes"},"externalID":"Genesis.1.1","id":"stable-id","kind":"ref","labelHe":"בראשית א:א","providerID":"sefaria","providerPayload":"{\"raw\":true}","rawInput":"Gen. 1:1","role":"context","unknownLegacy":{"value":7}}],"version":1}"#.utf8)

        let decoded = try codec.decodeDocument(input)
        let encoded = try codec.encodeDocument(decoded)
        let reopened = try codec.decodeDocument(encoded)

        #expect(reopened == decoded)
        #expect(reopened.items[0].id == "stable-id")
        #expect(reopened.items[0].labelEn == nil)
        #expect(reopened.items[0].rawInput == "Gen. 1:1")
        #expect(reopened.items[0].providerPayload == #"{"raw":true}"#)
        #expect(reopened.items[0].unknownFields["unknownLegacy"] == .object(["value": .number(7)]))
        #expect(reopened.unknownFields["futureEnvelope"] != nil)
    }

    @Test("Legacy source quote v1 decodes unchanged")
    func legacySourceQuote() throws {
        let input = Data(#"{"canonicalKey":"Bava Kamma 2a","externalID":"Bava_Kamma.2a.1","labelEn":"Bava Kamma 2a","labelHe":"בבא קמא ב.","legacyFlag":"kept","providerID":"sefaria","readOnly":true,"segment":"1","snapshotText":"ארבעה אבות נזיקין","version":1}"#.utf8)
        let decoded = try codec.decodeSourceQuote(input)
        let firstCanonical = try codec.encodeSourceQuote(decoded)
        let reopened = try codec.decodeSourceQuote(firstCanonical)
        let secondCanonical = try codec.encodeSourceQuote(reopened)

        #expect(reopened == decoded)
        #expect(firstCanonical == secondCanonical)
        #expect(reopened.version == 1)
        #expect(reopened.snapshotText == "ארבעה אבות נזיקין")
        #expect(reopened.provenance == nil)
        #expect(reopened.unknownFields["legacyFlag"] == .string("kept"))
    }

    @Test("Rich v2 provenance retains raw source, provider response, version, license, timestamp, and excerpt")
    func richProvenanceRoundTrip() throws {
        let timestamp = Date(timeIntervalSince1970: 1_767_326_645.678)
        let document = TorahTextDocument(
            providerID: "sefaria",
            requestedRef: "Gen. 1:1",
            canonicalRef: "Genesis 1:1",
            hebrewRef: "בראשית א:א",
            sectionRef: "Genesis 1",
            hebrewSectionRef: "בראשית א",
            segments: [TorahTextSegment(canonicalRef: "Genesis 1:1", hebrewRef: "בראשית א:א", text: "בְּרֵאשִׁית", ordinal: 1)],
            previousSectionRef: nil,
            nextSectionRef: "Genesis 2",
            version: TorahTextVersionMetadata(
                language: "he",
                actualLanguage: "he",
                languageFamilyName: "hebrew",
                versionTitle: "Tanach with Ta'amei Hamikra",
                versionTitleInHebrew: "תנ״ך",
                license: "CC-BY",
                direction: "rtl"
            ),
            rawProviderPayload: #"{"text":["בְּרֵאשִׁית"],"raw":true}"#
        )
        let provenance = TorahSourceQuoteProvenance(
            retrievedAt: timestamp,
            canonicalRef: "Genesis 1:1",
            providerID: "sefaria",
            referenceProviderPayload: #"{"ref":"Genesis 1:1"}"#,
            document: document,
            excerpt: TorahSourceQuoteExcerpt(
                selectedText: "רֵאשִׁית",
                segmentReference: "Genesis 1:1",
                segmentIndex: 0,
                utf16Offset: 2,
                utf16Length: 8
            )
        )
        let payload = TorahSourceQuotePayload(
            providerID: "sefaria",
            externalID: "Genesis.1.1",
            canonicalKey: "Genesis 1:1",
            labelHe: "בראשית א:א",
            labelEn: "Genesis 1:1",
            snapshotText: document.segments[0].text,
            provenance: provenance
        )

        let first = try codec.encodeSourceQuote(payload)
        let second = try codec.encodeSourceQuote(payload)
        let reopened = try codec.decodeSourceQuote(first)

        #expect(first == second)
        #expect(reopened == payload)
        #expect(reopened.provenance?.document.rawProviderPayload == document.rawProviderPayload)
        #expect(reopened.provenance?.document.version.license == "CC-BY")
        #expect(reopened.provenance?.excerpt.utf16Offset == 2)
        #expect(reopened.provenance?.excerpt.utf16Length == 8)
        #expect(reopened.provenance?.retrievedAt == timestamp)
    }

    @Test("Future and malformed payloads fail without yielding writable data")
    func safeFailures() throws {
        do {
            _ = try codec.decodeDocument(Data(#"{"version":99,"items":[]}"#.utf8))
            Issue.record("Future version unexpectedly decoded")
        } catch let error as TorahAssociationPayloadCodecError {
            #expect(error == .unsupportedVersion(99))
        }

        do {
            _ = try codec.decodeDocument(Data("not-json".utf8))
            Issue.record("Malformed JSON unexpectedly decoded")
        } catch let error as TorahAssociationPayloadCodecError {
            #expect(error == .malformedJSON)
        }
    }
}
