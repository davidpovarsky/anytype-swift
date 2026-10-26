import Testing
import UIKit
import PinkhaKit
import Services
@testable import Anytype

@Suite("Pinkha numbered marker adapter", .serialized)
@MainActor
struct PinkhaTextBlockLeadingMarkerAdapterTests {
    @Test("Wide Pinkha RTL numbers use semantic alignment", arguments: [20, 99, 100])
    func widePinkhaRTLNumber(number: Int) throws {
        let leadingView = TextBlockLeadingView()
        leadingView.semanticContentAttribute = .forceRightToLeft
        leadingView.update(blockId: "pinkha", style: .numbered(number))

        PinkhaTextBlockLeadingMarkerAdapter.applyNumberAlignment(
            context: pinkhaContext,
            content: .empty(contentType: .numbered).updated(number: number),
            to: leadingView
        )

        #expect(try #require(numberLabel(in: leadingView)).textAlignment == .natural)
    }

    @Test("Pinkha LTR keeps the original wide-number alignment exactly", arguments: [20, 99, 100])
    func widePinkhaLTRNumber(number: Int) throws {
        let leadingView = TextBlockLeadingView()
        leadingView.semanticContentAttribute = .forceLeftToRight
        leadingView.update(blockId: "pinkha-ltr", style: .numbered(number))

        PinkhaTextBlockLeadingMarkerAdapter.applyNumberAlignment(
            context: pinkhaContext,
            content: .empty(contentType: .numbered).updated(number: number),
            to: leadingView
        )

        #expect(try #require(numberLabel(in: leadingView)).textAlignment == .left)
    }

    @Test("Ordinary Anytype wide numbers retain the original physical alignment")
    func ordinaryAnytypeWideNumber() throws {
        let leadingView = TextBlockLeadingView()
        leadingView.update(blockId: "anytype", style: .numbered(20))

        PinkhaTextBlockLeadingMarkerAdapter.applyNumberAlignment(
            context: nil,
            content: .empty(contentType: .numbered).updated(number: 20),
            to: leadingView
        )

        #expect(try #require(numberLabel(in: leadingView)).textAlignment == .left)
    }

    @Test("Numbers below the host wide-number threshold remain centered", arguments: [1, 9, 10, 19])
    func narrowPinkhaNumber(number: Int) throws {
        let leadingView = TextBlockLeadingView()
        leadingView.semanticContentAttribute = .forceRightToLeft
        leadingView.update(blockId: "pinkha-narrow", style: .numbered(number))

        PinkhaTextBlockLeadingMarkerAdapter.applyNumberAlignment(
            context: pinkhaContext,
            content: .empty(contentType: .numbered).updated(number: number),
            to: leadingView
        )

        #expect(try #require(numberLabel(in: leadingView)).textAlignment == .center)
    }

    @Test("The complete text row places the marker on the physical right in RTL and left in LTR")
    func physicalMarkerSide() throws {
        let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 390, height: 844))
        let controller = UIViewController()
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer { window.isHidden = true }

        let nestedContainer = UIView(frame: CGRect(x: 0, y: 0, width: 320, height: 52))
        let view = TextBlockContentView()
        view.frame = CGRect(x: 40, y: 0, width: 240, height: 52)
        controller.view.addSubview(nestedContainer)
        nestedContainer.addSubview(view)

        var configuration = TextBlockContentConfiguration.empty
        configuration.blockId = "nested-number-row"
        configuration.content = .plain("טקסט ברשימה מקוננת", contentType: .numbered).updated(number: 100)
        configuration.attributedString = NSAttributedString(string: configuration.content.text)
        configuration.pinkhaWritingContext = pinkhaContext

        view.semanticContentAttribute = .forceRightToLeft
        view.update(with: configuration)
        view.layoutIfNeeded()

        let leadingView = try #require(firstDescendant(of: TextBlockLeadingView.self, in: view))
        // The XCTest host does not propagate -testLanguage into UIKit's effective direction.
        // Force the whole hierarchy to model an app-level language override: the host row's
        // existing leading/trailing constraints must then place the marker on the physical right.
        forceSemanticContentAttribute(.forceRightToLeft, in: window)
        view.update(with: configuration)
        view.layoutIfNeeded()

        var markerFrame = leadingView.convert(leadingView.bounds, to: nestedContainer)
        var textFrame = view.textView.convert(view.textView.bounds, to: nestedContainer)
        #expect(markerFrame.midX > textFrame.midX)
        #expect(try #require(numberLabel(in: leadingView)).textAlignment == .natural)

        // Reuse the same host row while the effective app language changes at runtime.
        forceSemanticContentAttribute(.forceLeftToRight, in: window)
        view.update(with: configuration)
        view.layoutIfNeeded()

        markerFrame = leadingView.convert(leadingView.bounds, to: nestedContainer)
        textFrame = view.textView.convert(view.textView.bounds, to: nestedContainer)
        #expect(markerFrame.midX < textFrame.midX)
        #expect(try #require(numberLabel(in: leadingView)).textAlignment == .left)

        // Reuse it again for an ordinary Anytype row; the original host value remains exact.
        configuration.blockId = "ordinary-reused-number-row"
        configuration.pinkhaWritingContext = nil
        view.update(with: configuration)
        view.layoutIfNeeded()
        let reusedLeadingView = try #require(firstDescendant(of: TextBlockLeadingView.self, in: view))
        #expect(try #require(numberLabel(in: reusedLeadingView)).textAlignment == .left)
    }

    private var pinkhaContext: PinkhaTextBlockWritingContext {
        PinkhaTextBlockWritingContext(
            origin: .newParagraph,
            persistedAlignment: nil,
            alignmentWasExplicit: false
        )
    }

    private func numberLabel(in view: UIView) -> UILabel? {
        if let label = view as? UILabel { return label }
        return view.subviews.lazy.compactMap { numberLabel(in: $0) }.first
    }

    private func firstDescendant<T: UIView>(of type: T.Type, in view: UIView) -> T? {
        if let match = view as? T { return match }
        return view.subviews.lazy.compactMap { firstDescendant(of: type, in: $0) }.first
    }

    private func forceSemanticContentAttribute(
        _ attribute: UISemanticContentAttribute,
        in view: UIView
    ) {
        view.semanticContentAttribute = attribute
        view.subviews.forEach { forceSemanticContentAttribute(attribute, in: $0) }
    }
}
