import Foundation
import XCTest
import PinkhaKit
@testable import PinkhaAnyHost

final class AnySemanticTypingContinuationTests: XCTestCase {
    func testActualMarkdownPerKeystrokePreservesMarkerStylesAndUnrelatedBytes() throws {
        let anchor = try PinkhaSemanticTextAnchor(spaceID: "space", objectID: "document")
        let prefix = "[external](https://example.org/a) before "
        let suffix = " after _unchanged_"
        var source = prefix + "[**Anchor**](" + anchor.markerString + ")" + suffix
        let initial = AnyInlineMarkdown(source)
        var range = (initial.display as NSString).range(of: "Anchor")
        let start = range.location
        var continuation: PinkhaSemanticTypingContinuation?
        for key in ["C", "h", "a", "n", "g", "e", "d"] {
            let current = AnyInlineMarkdown(source)
            let semantic = try current.semanticText()
            let replacement = try continuation?.continuing(in: semantic, range: range, with: key)
                ?? .init(range: range, text: key)
            source = try current.replacing(displayRange: replacement.range, withLiteral: replacement.text)
            let after = try AnyInlineMarkdown(source).semanticText()
            continuation = try .init(before: semantic, replacing: replacement.range, with: replacement.text, after: after)
            range = .init(location: range.location + key.utf16.count, length: 0)
        }
        XCTAssertEqual(source, prefix + "[**Changed**](" + anchor.markerString + ")" + suffix)
        XCTAssertEqual(try AnyInlineMarkdown(source).semanticText().marks,
                       [.init(anchor: anchor, range: .init(location: start, length: 7))])
        // After the adapter retires the typing action, a separately placed end
        // caret must again insert outside the anchor, without changing its UUID.
        let independent = try AnyInlineMarkdown(source).replacing(displayRange: range, withLiteral: "!")
        XCTAssertEqual(independent, prefix + "[**Changed**](" + anchor.markerString + ")\\!" + suffix)
        XCTAssertEqual(AnyInlineMarkdown(independent).display, "external before Changed! after unchanged")
        XCTAssertEqual(try AnyInlineMarkdown(independent).semanticText().marks,
                       [.init(anchor: anchor, range: .init(location: start, length: 7))])
    }
}
