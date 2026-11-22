import Foundation
import Testing
@testable import PinkhaKit

@Suite("Durable semantic marker identity and transient editor transforms")
struct PinkhaSemanticTextAnchorTests {
    private func anchor() throws -> PinkhaSemanticTextAnchor {
        try .init(spaceID: "space-one", objectID: "document-one",
                  id: UUID(uuidString: "C441BAF4-26F3-4E4F-88C0-C3DD485E93FC")!)
    }

    private func marked(_ text: String, phrase: String) throws -> PinkhaSemanticText {
        try PinkhaSemanticText(text: text).capturing(anchor(), range: (text as NSString).range(of: phrase)).after
    }

    @Test func markerRoundtripBindsExactScopeAndContainsNoOffsets() throws {
        let value = try PinkhaSemanticTextAnchor(spaceID: "מרחב /+", objectID: "document#?%",
                                               id: anchor().id)
        #expect(try PinkhaSemanticTextAnchor(markerURL: value.markerURL()) == value)
        let encoded = try JSONEncoder().encode(value)
        #expect(try JSONDecoder().decode(PinkhaSemanticTextAnchor.self, from: encoded) == value)
        let json = try #require(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        #expect(Set(json.keys) == ["version", "spaceID", "objectID", "id"])
        #expect(!value.belongsTo(spaceID: "other-space", objectID: value.objectID))
        // Identifier ownership uses exact bytes, not canonical String equality.
        let decomposed = try PinkhaSemanticTextAnchor(spaceID: "e\u{301}", objectID: "doc", id: value.id)
        let composed = try PinkhaSemanticTextAnchor(spaceID: "é", objectID: "doc", id: value.id)
        #expect(decomposed != composed)
        #expect(Set([decomposed, composed]).count == 2)
    }

    @Test func malformedFutureAndRedirectedMarkersAreRejected() throws {
        let original = try anchor().markerString
        for text in [original + "?offset=1", original + "#range", original + "/extra",
                     original.replacingOccurrences(of: "://v1/", with: "://v2/"),
                     original.replacingOccurrences(of: "://v1/", with: "://user@v1/"),
                     original.replacingOccurrences(of: "://v1/", with: "://v1:80/"),
                     original.replacingOccurrences(of: "c441baf4", with: "C441BAF4")] {
            let url = try #require(URL(string: text))
            #expect(PinkhaSemanticTextAnchor.isReservedMarkerURL(url))
            #expect(throws: PinkhaSemanticTextAnchorError.self) {
                try PinkhaSemanticTextAnchor(markerURL: url)
            }
        }
        let data = Data("{\"version\":2,\"spaceID\":\"s\",\"objectID\":\"o\",\"id\":\"c441baf4-26f3-4e4f-88c0-c3dd485e93fc\"}".utf8)
        #expect(throws: PinkhaSemanticTextAnchorError.unsupportedVersion) {
            try JSONDecoder().decode(PinkhaSemanticTextAnchor.self, from: data)
        }
    }

    @Test func beforeInsideAndAfterEditsKeepNativeMarkerIdentity() throws {
        let original = try marked("לפני 👩🏽‍💻 דבר־תורה אַב אחרי", phrase: "דבר־תורה אַב")
        let id = try anchor()
        let before = try original.replacing(.init(location: 0, length: 0), with: "ABC ").after
        #expect(before.marks[0].anchor == id)
        #expect(before.marks[0].range.location == original.marks[0].range.location + 4)
        let inside = try before.replacing(.init(location: before.marks[0].range.location + 3, length: 0), with: "😀").after
        #expect(inside.marks[0].range.length == before.marks[0].range.length + 2)
        let after = try inside.replacing(.init(location: inside.text.utf16.count, length: 0), with: " suffix").after
        #expect(after.marks == inside.marks)
        let result = try PinkhaSemanticTextAnchorResolver.resolve(id, spaceID: id.spaceID, objectID: id.objectID,
            blocks: [.init(id: "native-block", content: after)])
        guard case .resolved(let fragments) = result else { Issue.record("Native mark was not resolved"); return }
        #expect(fragments.count == 1)
        #expect(fragments[0].blockID == "native-block")
        #expect(fragments[0].text.utf8.elementsEqual("דבר😀־תורה אַב".utf8))
    }

    @Test func boundaryTypingDoesNotCaptureAdjacentText() throws {
        let original = try marked("before phrase after", phrase: "phrase")
        let start = original.marks[0].range.location
        let before = try original.replacing(.init(location: start, length: 0), with: "X").after
        #expect(before.marks[0].range == .init(location: start + 1, length: 6))
        let end = NSMaxRange(before.marks[0].range)
        let after = try before.replacing(.init(location: end, length: 0), with: "Y").after
        #expect(after.marks == before.marks)
        #expect((after.text as NSString).substring(with: after.marks[0].range) == "phrase")
    }

    @Test func replacementDeletionAndUndoHaveExplicitSemantics() throws {
        let original = try marked("one phrase two", phrase: "phrase")
        let replacement = try original.replacing(original.marks[0].range, with: "different label")
        #expect(replacement.after.marks[0].anchor == original.marks[0].anchor)
        #expect((replacement.after.text as NSString).substring(with: replacement.after.marks[0].range) == "different label")
        #expect(try replacement.inverse(current: replacement.after).after == original)
        let deleted = try original.replacing(original.marks[0].range, with: "")
        #expect(deleted.after.marks.isEmpty)
        let id = try anchor()
        #expect(try PinkhaSemanticTextAnchorResolver.resolve(id, spaceID: id.spaceID, objectID: id.objectID,
            blocks: [.init(id: "native-block", content: deleted.after)]) == .missing)
        #expect(try deleted.inverse(current: deleted.after).after == original)
        let changed = try deleted.after.replacing(.init(location: 0, length: 0), with: "new writer ").after
        #expect(throws: PinkhaSemanticTextAnchorError.changedText) { try deleted.inverse(current: changed) }
    }

    @Test func splitMergeRetainsIdentityAndResolvesCurrentNativeBlockIDs() throws {
        let original = try marked("ab שלום😀 xyz", phrase: "שלום😀")
        let parts = try original.split(at: 5)
        #expect(parts.before.marks[0].anchor == parts.after.marks[0].anchor)
        let id = try anchor()
        let resolution = try PinkhaSemanticTextAnchorResolver.resolve(id, spaceID: id.spaceID, objectID: id.objectID,
            blocks: [.init(id: "left-native-id", content: parts.before), .init(id: "new-native-id", content: parts.after)])
        guard case .resolved(let fragments) = resolution else { Issue.record("Split fragments were not resolved"); return }
        #expect(fragments.map(\.blockID) == ["left-native-id", "new-native-id"])
        #expect(fragments.map(\.text).joined() == "שלום😀")
        #expect(try parts.before.merging(parts.after) == original)
        let withSeparator = try parts.before.merging(parts.after, separator: " ")
        #expect(withSeparator.marks.count == 1)
        #expect((withSeparator.text as NSString).substring(with: withSeparator.marks[0].range) == "של ום😀")
    }

    @Test func clipboardNeverClonesInternalIdentityAndCutUndoRestoresIt() throws {
        let original = try marked("prefix phrase", phrase: "phrase")
        let range = original.marks[0].range
        let clipboard = try original.clipboardText(in: range)
        #expect(clipboard == "phrase")
        #expect(!clipboard.contains(PinkhaSemanticTextAnchor.markerScheme))
        let pasted = try original.replacing(.init(location: original.text.utf16.count, length: 0), with: " " + clipboard).after
        #expect(pasted.marks == original.marks)
        let cut = try original.replacing(range, with: "")
        #expect(cut.after.marks.isEmpty)
        #expect(try cut.inverse(current: cut.after).after == original)
        #expect(try PinkhaSemanticText(text: "").replacing(.init(location: 0, length: 0), with: clipboard).after.marks.isEmpty)
    }

    @Test func ambiguousForeignAndMissingMarksNeverFallBackToTextOrOldOffsets() throws {
        let id = try anchor()
        let repeated = try PinkhaSemanticText(text: "same same", marks: [
            .init(anchor: id, range: .init(location: 0, length: 4)),
            .init(anchor: id, range: .init(location: 5, length: 4))])
        #expect(try PinkhaSemanticTextAnchorResolver.resolve(id, spaceID: id.spaceID, objectID: id.objectID,
            blocks: [.init(id: "native", content: repeated)]) == .ambiguous)
        let single = try marked("same", phrase: "same")
        #expect(try PinkhaSemanticTextAnchorResolver.resolve(id, spaceID: id.spaceID, objectID: id.objectID,
            blocks: [.init(id: "first", content: single), .init(id: "gap", content: .init(text: "unrelated")),
                     .init(id: "copy", content: single)]) == .ambiguous)
        #expect(throws: PinkhaSemanticTextAnchorError.wrongDocument) {
            try PinkhaSemanticTextAnchorResolver.resolve(id, spaceID: "another-space", objectID: id.objectID,
                blocks: [.init(id: "native", content: single)])
        }
        #expect(try PinkhaSemanticTextAnchorResolver.resolve(id, spaceID: id.spaceID, objectID: id.objectID,
            blocks: [.init(id: "native", content: .init(text: "same"))]) == .missing)
    }

    @Test func emojiNiqqudBoundsAndExistingLinksAreProtected() throws {
        let text = "א\u{05B7} 👩🏽‍💻 שלום"
        let original = try PinkhaSemanticText(text: text)
        let emoji = (text as NSString).range(of: "👩🏽‍💻")
        let id = try anchor()
        for range in [NSRange(location: 0, length: 1), .init(location: emoji.location + 1, length: 1),
                      .init(location: NSNotFound, length: 1), .init(location: 0, length: Int.max),
                      .init(location: 0, length: 0)] {
            #expect(throws: PinkhaSemanticTextAnchorError.invalidRange) { try original.capturing(id, range: range) }
        }
        #expect(throws: PinkhaSemanticTextAnchorError.invalidRange) { try original.split(at: emoji.location + 2) }
        #expect(throws: PinkhaSemanticTextAnchorError.selectionAlreadyLinked) {
            try original.capturing(id, range: emoji, occupiedLinkRanges: [emoji])
        }
        let captured = try original.capturing(id, range: emoji).after
        #expect(captured.text.utf8.elementsEqual(text.utf8))
        #expect((captured.text as NSString).substring(with: captured.marks[0].range) == "👩🏽‍💻")
    }

    @Test func normalizedStringEqualityCannotAuthorizeAnUndoOrSourceReplacement() throws {
        let original = try PinkhaSemanticText(text: "e\u{301}")
        let edited = try original.replacing(.init(location: 0, length: 0), with: "!")
        let foreign = try PinkhaSemanticText(text: "!é")
        #expect(edited.after.text == foreign.text)
        #expect(edited.after != foreign)
        #expect(throws: PinkhaSemanticTextAnchorError.changedText) { try edited.inverse(current: foreign) }
    }
}
