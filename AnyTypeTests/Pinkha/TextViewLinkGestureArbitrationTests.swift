import Testing
import UIKit
@testable import Anytype

@Suite("Native link selection gesture ownership", .serialized)
@MainActor
struct TextViewLinkGestureArbitrationTests {
    @Test("The exact input single tap waits for link double-tap selection")
    func sameInputSingleTapDefersToLinkSelection() throws {
        let fixture = try LinkGestureFixture()
        let single = UITapGestureRecognizer()
        fixture.input.addGestureRecognizer(single)
        #expect(fixture.interaction.gestureRecognizer(fixture.selection, shouldBeRequiredToFailBy: single))
        #expect(!fixture.interaction.gestureRecognizer(fixture.selection, shouldRequireFailureOf: single))
        #expect(!fixture.interaction.gestureRecognizer(fixture.selection, shouldRecognizeSimultaneouslyWith: single))
        #expect(fixture.handler.selections == 0)
    }

    @Test("Other inputs, parent scrolling and unrelated gestures keep their own policy")
    func foreignAndUnrelatedGesturesRemainIndependent() throws {
        let fixture = try LinkGestureFixture()
        let parent = UIView()
        parent.addSubview(fixture.input)
        let sibling = UITextView()
        parent.addSubview(sibling)
        let parentTap = UITapGestureRecognizer()
        parent.addGestureRecognizer(parentTap)
        let foreignTap = UITapGestureRecognizer()
        sibling.addGestureRecognizer(foreignTap)
        let pan = UIPanGestureRecognizer()
        let longPress = UILongPressGestureRecognizer()
        let doubleTap = UITapGestureRecognizer()
        doubleTap.numberOfTapsRequired = 2
        let multiTouch = UITapGestureRecognizer()
        multiTouch.numberOfTouchesRequired = 2
        for recognizer in [pan, longPress, doubleTap, multiTouch] as [UIGestureRecognizer] {
            fixture.input.addGestureRecognizer(recognizer)
        }
        for recognizer in [parentTap, foreignTap, pan, longPress, doubleTap, multiTouch, fixture.selection] as [UIGestureRecognizer] {
            #expect(!fixture.interaction.gestureRecognizer(fixture.selection, shouldBeRequiredToFailBy: recognizer))
        }
        #expect(!fixture.interaction.gestureRecognizer(foreignTap, shouldBeRequiredToFailBy: parentTap))
        #expect(fixture.handler.selections == 0)
    }

    @Test("Native text-interaction failure requirements belong only to the same text input")
    func nativeTextInteractionUsesPublicOwnership() throws {
        let fixture = try LinkGestureFixture()
        let native = UITextInteraction(for: .nonEditable)
        native.textInput = fixture.input
        fixture.input.addInteraction(native)
        defer { fixture.input.removeInteraction(native) }
        let nativeGestures = native.gesturesForFailureRequirements.filter {
            guard let view = $0.view else { return false }
            return view === fixture.input || view.isDescendant(of: fixture.input)
        }
        try #require(!nativeGestures.isEmpty)
        for recognizer in nativeGestures {
            #expect(fixture.interaction.gestureRecognizer(fixture.selection, shouldBeRequiredToFailBy: recognizer))
        }
        #expect(fixture.handler.selections == 0)
    }

    @Test("Removing and reattaching the interaction retires its exact old recognizer")
    func removalAndReattachmentRetirePriorRecognizer() throws {
        let fixture = try LinkGestureFixture()
        let single = UITapGestureRecognizer()
        fixture.input.addGestureRecognizer(single)
        fixture.input.removeInteraction(fixture.interaction)
        #expect(fixture.selection.view == nil)
        #expect(fixture.interaction.view == nil)
        #expect(!fixture.interaction.gestureRecognizer(fixture.selection, shouldBeRequiredToFailBy: single))
        fixture.input.addInteraction(fixture.interaction)
        let current = try #require(fixture.input.gestureRecognizers?.filter { $0.delegate === fixture.interaction })
        try #require(current.count == 1)
        #expect(current[0] !== fixture.selection)
        #expect(fixture.interaction.gestureRecognizer(current[0], shouldBeRequiredToFailBy: single))
        #expect(!fixture.interaction.gestureRecognizer(fixture.selection, shouldBeRequiredToFailBy: single))
    }

    @Test("Mention and object single-tap interactions do not acquire link-selection priority")
    func singleTapAttributeHandlersRemainIndependent() throws {
        for key in [NSAttributedString.Key.mention, .linkToObject, .link] {
            let fixture = try LinkGestureFixture(attribute: key, taps: 1)
            let single = UITapGestureRecognizer()
            fixture.input.addGestureRecognizer(single)
            #expect(!fixture.interaction.gestureRecognizer(fixture.selection, shouldBeRequiredToFailBy: single))
            #expect(fixture.handler.selections == 0)
        }
    }
}

@MainActor
private struct LinkGestureFixture {
    let input: UITextView
    let handler: LinkGestureHandler
    let interaction: TextViewAttributeSelectionInteraction
    let selection: UITapGestureRecognizer

    init(attribute: NSAttributedString.Key = .link, taps: Int = 2) throws {
        let input = UITextView(frame: CGRect(x: 0, y: 0, width: 320, height: 80))
        input.attributedText = NSAttributedString(string: "Anchor", attributes: [.link: URL(string: "https://example.com")!])
        let handler = LinkGestureHandler()
        let interaction = TextViewAttributeSelectionInteraction(textView: input, attributeKey: attribute,
            numberOfTapsRequired: taps, tapHandler: handler)
        input.addInteraction(interaction)
        let owned = try #require(input.gestureRecognizers?.filter { $0.delegate === interaction })
        try #require(owned.count == 1)
        self.input = input
        self.handler = handler
        self.interaction = interaction
        selection = try #require(owned[0] as? UITapGestureRecognizer)
    }
}

@MainActor
private final class LinkGestureHandler: TextViewAttributeSelectionHandler {
    var selections = 0
    func didSelect(_ attribute: NSAttributedString.Key, in textView: UITextView, recognizer: UITapGestureRecognizer) {
        selections += 1
    }
}
