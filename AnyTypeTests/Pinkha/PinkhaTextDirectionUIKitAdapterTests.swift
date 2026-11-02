import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
import UIKit
@testable import Anytype

@Suite("App-wide UIKit text direction adapter", .serialized)
@MainActor
struct PinkhaTextDirectionUIKitAdapterTests {
    @Test("Native presentation alignment preserves serialized text/marks, selection, undo and editing callbacks")
    func languageRenderingIsDisplayOnly() throws {
        let textView = UndoTrackingTextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        let observer = TextMutationObserver()
        textView.delegate = observer
        textView.textStorage.delegate = observer
        textView.semanticContentAttribute = .forceRightToLeft
        let hostParagraphStyle = NSMutableParagraphStyle()
        hostParagraphStyle.alignment = .left
        hostParagraphStyle.lineSpacing = 5
        hostParagraphStyle.paragraphSpacing = 3
        textView.attributedText = NSAttributedString(
            string: "English text",
            attributes: [
                .font: UIFont.boldSystemFont(ofSize: 17),
                .paragraphStyle: hostParagraphStyle
            ]
        )
        textView.selectedRange = NSRange(location: 4, length: 3)
        textView.typingAttributes = [.font: UIFont.systemFont(ofSize: 17)]
        observer.reset()

        let attributedBefore = try #require(textView.attributedText)
        let selectionBefore = textView.selectedRange
        let typingBefore = textView.typingAttributes
        let undoFlag = UndoFlagBox()
        textView.testUndoManager.registerUndo(withTarget: undoFlag) { $0.reached = true }
        let couldUndoBefore = textView.testUndoManager.canUndo

        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)
        textView.layoutManager.ensureLayout(for: textView.textContainer)

        let glyphRange = textView.layoutManager.glyphRange(for: textView.textContainer)
        #expect(glyphRange.length > 0)
        let fragment = textView.layoutManager.lineFragmentRect(
            forGlyphAt: glyphRange.location,
            effectiveRange: nil
        )
        let used = textView.layoutManager.lineFragmentUsedRect(
            forGlyphAt: glyphRange.location,
            effectiveRange: nil
        )

        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .right)
        #expect(abs(used.maxX - fragment.maxX) < 0.5)
        #expect(fragment.minX + textView.layoutManager.location(forGlyphAt: glyphRange.location).x > textView.bounds.midX,
                "A reported used rect is insufficient: the rendered glyph origin must move")
        expectOnlyPresentationAlignmentChanged(before: attributedBefore, after: textView.attributedText)
        #expect(textView.selectedRange == selectionBefore)
        expectTypingFormattingPreserved(before: typingBefore, after: textView.typingAttributes)
        #expect(observer.textChangeCount == 0)
        #expect(observer.characterEditCount == 0)
        #expect(textView.testUndoManager.canUndo == couldUndoBefore)

        textView.semanticContentAttribute = .forceLeftToRight
        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)
        textView.layoutManager.ensureLayout(for: textView.textContainer)
        let leftUsed = textView.layoutManager.lineFragmentUsedRect(
            forGlyphAt: glyphRange.location,
            effectiveRange: nil
        )
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
        #expect(abs(leftUsed.minX - fragment.minX) < 0.5)
        #expect(fragment.minX + textView.layoutManager.location(forGlyphAt: glyphRange.location).x < textView.bounds.midX)
        #expect(textView.attributedText == attributedBefore)
        #expect(observer.textChangeCount == 0)
        #expect(observer.characterEditCount == 0)

        textView.testUndoManager.undo()
        #expect(undoFlag.reached)
    }

    @Test("Original native layout manager draws and hits the actual glyphs on the default side",
          arguments: [false, true], ["English text", "English\nabc אבג\nHi 👩🏽‍💻"])
    func nativeGlyphRenderingAndHitTesting(hostUsesRight: Bool, text: String) throws {
        let wrapper = CustomTextView()
        wrapper.frame = CGRect(x: 0, y: 0, width: 320, height: 80)
        wrapper.layoutIfNeeded()
        let textView = wrapper.textView
        textView.textContainerInset = .zero
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = hostUsesRight ? .right : .left
        paragraph.baseWritingDirection = .leftToRight
        textView.attributedText = NSAttributedString(string: text, attributes: [
            .font: UIFont.systemFont(ofSize: 17), .foregroundColor: UIColor.black,
            .paragraphStyle: paragraph
        ])
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let window = UIWindow(windowScene: scene)
        window.frame = CGRect(x: 0, y: 0, width: 390, height: 844)
        let controller = UIViewController()
        controller.view.addSubview(wrapper)
        window.rootViewController = controller
        window.makeKeyAndVisible()
        controller.view.layoutIfNeeded()
        try #require(textView.becomeFirstResponder())
        defer { textView.unmarkText(); textView.resignFirstResponder(); window.isHidden = true }
        textView.selectedRange = NSRange(location: 4, length: 3)
        let context = PinkhaTextBlockWritingContext(
            origin: .ambiguousLegacyParagraph,
            persistedAlignment: hostUsesRight ? .right : .left,
            alignmentWasExplicit: false
        )
        for rtl in [false, true] {
            controller.view.semanticContentAttribute = rtl ? .forceRightToLeft : .forceLeftToRight
            textView.semanticContentAttribute = rtl ? .forceRightToLeft : .forceLeftToRight
            let attributedBefore = try #require(textView.attributedText)
            let selectionBefore = textView.selectedRange
            let typingBefore = textView.typingAttributes
            PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textView)
            let manager = textView.layoutManager
            manager.ensureLayout(for: textView.textContainer)
            textView.layoutIfNeeded()
            try #require(textView.isFirstResponder, "Native caret evidence requires an attached, focused view")
            let range = manager.glyphRange(for: textView.textContainer)
            try #require(range.length > 1)
            let fragment = manager.lineFragmentRect(forGlyphAt: range.location, effectiveRange: nil)
            let first = manager.location(forGlyphAt: range.location)
            let next = manager.location(forGlyphAt: range.location + 1)
            let probe = CGPoint(x: fragment.minX + first.x + (next.x - first.x) * 0.25, y: fragment.midY)
            #expect(manager.glyphIndex(for: probe, in: textView.textContainer) == range.location)
            let nativePosition = try #require(textView.closestPosition(to: probe))
            #expect(textView.offset(from: textView.beginningOfDocument, to: nativePosition) == 0)
            let caret = textView.caretRect(for: textView.beginningOfDocument)
            try #require(caret.height > 0, "The native input geometry must be measurable")
            print("PINKHA_NATIVE_INPUT hostRight=\(hostUsesRight) rtl=\(rtl) caretX=\(caret.midX) firstX=\(fragment.minX + first.x) hit=\(textView.offset(from: textView.beginningOfDocument, to: nativePosition)) responder=\(textView.isFirstResponder)")
            #expect(abs(caret.midX - (fragment.minX + first.x)) < 3,
                    "UITextView's caret must follow the same actual glyph location")

            let format = UIGraphicsImageRendererFormat()
            format.scale = 1
            format.opaque = true
            format.preferredRange = .standard
            let image = UIGraphicsImageRenderer(size: wrapper.bounds.size, format: format).image { canvas in
                UIColor.white.setFill()
                canvas.fill(wrapper.bounds)
                manager.drawGlyphs(forGlyphRange: range, at: .zero)
            }
            let ink = try darkPixelBounds(of: #require(image.cgImage))
            print("PINKHA_NATIVE_GLYPHS hostRight=\(hostUsesRight) rtl=\(rtl) ink=\(ink) firstX=\(fragment.minX + first.x)")
            #expect(rtl ? ink.minX > textView.bounds.midX : ink.maxX < textView.bounds.midX)
            #expect(ink.minX >= 0 && ink.maxX <= textView.bounds.width)
            manager.ensureLayout(for: textView.textContainer)
            #expect(manager.location(forGlyphAt: range.location) == first, "A repeated layout query must not accumulate a shift")
            expectOnlyPresentationAlignmentChanged(before: attributedBefore, after: textView.attributedText)
            #expect(textView.selectedRange == selectionBefore)
            expectTypingFormattingPreserved(before: typingBefore, after: textView.typingAttributes)
        }
    }

    /// The earlier cache implementation promised immutable UIKit attributes but failed
    /// actual editable geometry. Native alignment intentionally changes only the display
    /// paragraph alignment; prove that the real Anytype serialization and all other
    /// formatting survive, rather than treating an in-memory display style as document data.
    private func expectOnlyPresentationAlignmentChanged(before: NSAttributedString, after: NSAttributedString) {
        let savedBefore = AttributedTextConverter.asMiddleware(attributedText: before)
        let savedAfter = AttributedTextConverter.asMiddleware(attributedText: after)
        #expect(savedBefore.text == savedAfter.text)
        #expect(savedBefore.marks == savedAfter.marks)
        func ignoringAlignment(_ value: NSAttributedString) -> NSAttributedString {
            let normalized = NSMutableAttributedString(attributedString: value)
            value.enumerateAttribute(.paragraphStyle, in: NSRange(location: 0, length: value.length)) { style, range, _ in
                guard let paragraph = (style as? NSParagraphStyle)?.mutableCopy() as? NSMutableParagraphStyle else { return }
                paragraph.alignment = .natural
                normalized.addAttribute(.paragraphStyle, value: paragraph, range: range)
            }
            return normalized
        }
        #expect(ignoringAlignment(before) == ignoringAlignment(after))
    }

    private func expectTypingFormattingPreserved(before: [NSAttributedString.Key: Any], after: [NSAttributedString.Key: Any]) {
        if let paragraph = before[.paragraphStyle] as? NSParagraphStyle {
            let current = (after[.paragraphStyle] as? NSParagraphStyle)?.mutableCopy() as? NSMutableParagraphStyle
            #expect(current != nil)
            current?.alignment = paragraph.alignment
            #expect(current?.isEqual(paragraph) == true)
        }
        var original = before
        var current = after
        original.removeValue(forKey: .paragraphStyle)
        current.removeValue(forKey: .paragraphStyle)
        #expect(NSDictionary(dictionary: original).isEqual(NSDictionary(dictionary: current)))
    }

    private func darkPixelBounds(of image: CGImage) throws -> CGRect {
        let width = image.width
        let height = image.height
        var pixels = [UInt8](repeating: 255, count: width * height * 4)
        return try pixels.withUnsafeMutableBytes { buffer in
            let context = try #require(CGContext(
                data: buffer.baseAddress, width: width, height: height,
                bitsPerComponent: 8, bytesPerRow: width * 4,
                space: CGColorSpaceCreateDeviceRGB(),
                bitmapInfo: CGBitmapInfo.byteOrder32Big.rawValue | CGImageAlphaInfo.premultipliedLast.rawValue
            ))
            context.draw(image, in: CGRect(x: 0, y: 0, width: CGFloat(width), height: CGFloat(height)))
            let bytes = buffer.bindMemory(to: UInt8.self)
            var minX = width, minY = height, maxX = -1, maxY = -1
            for y in 0..<height {
                for x in 0..<width {
                    let offset = (y * width + x) * 4
                    if bytes[offset] < 100 && bytes[offset + 1] < 100 && bytes[offset + 2] < 100 {
                        minX = min(minX, x); minY = min(minY, y)
                        maxX = max(maxX, x); maxY = max(maxY, y)
                    }
                }
            }
            try #require(maxX >= minX, "The glyph renderer must draw actual ink, never a blank fixture")
            return CGRect(x: CGFloat(minX), y: CGFloat(minY), width: CGFloat(maxX - minX + 1), height: CGFloat(maxY - minY + 1))
        }
    }

    @Test("An already active display layout preserves marked text during relayout")
    func activeDisplayLayoutPreservesComposition() throws {
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let window = UIWindow(windowScene: scene)
        let controller = UIViewController()
        controller.view.semanticContentAttribute = .forceRightToLeft
        let textView = UITextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        textView.text = "abc"
        textView.textAlignment = .left
        controller.view.addSubview(textView)
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer { textView.unmarkText(); textView.resignFirstResponder(); window.isHidden = true }
        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)
        textView.layoutManager.ensureLayout(for: textView.textContainer)
        try #require(textView.becomeFirstResponder())
        textView.selectedRange = NSRange(location: 3, length: 0)
        textView.setMarkedText("אב", selectedRange: NSRange(location: 2, length: 0))
        let marked = try #require(textView.markedTextRange)
        let markedStart = textView.offset(from: textView.beginningOfDocument, to: marked.start)
        let markedEnd = textView.offset(from: textView.beginningOfDocument, to: marked.end)
        let attributedBefore = textView.attributedText
        let selectionBefore = textView.selectedRange
        let typingBefore = textView.typingAttributes
        let observer = TextMutationObserver()
        textView.delegate = observer
        textView.textStorage.delegate = observer
        textView.layoutManager.invalidateLayout(forCharacterRange: NSRange(location: 0, length: textView.textStorage.length), actualCharacterRange: nil)
        textView.layoutManager.ensureLayout(for: textView.textContainer)
        let after = try #require(textView.markedTextRange)
        #expect(textView.offset(from: textView.beginningOfDocument, to: after.start) == markedStart)
        #expect(textView.offset(from: textView.beginningOfDocument, to: after.end) == markedEnd)
        #expect(textView.attributedText == attributedBefore)
        #expect(textView.selectedRange == selectionBefore)
        #expect(NSDictionary(dictionary: textView.typingAttributes).isEqual(NSDictionary(dictionary: typingBefore)))
        #expect(observer.textChangeCount == 0 && observer.storageEditCount == 0)
        #expect(textView.isFirstResponder)
    }

    @Test("An active marked-text composition is left byte-for-byte untouched")
    func activeIMECompositionIsUntouched() throws {
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let window = UIWindow(windowScene: scene)
        window.frame = CGRect(x: 0, y: 0, width: 390, height: 844)
        let controller = UIViewController()
        let textView = UITextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        controller.view.addSubview(textView)
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer { textView.unmarkText(); textView.resignFirstResponder(); window.isHidden = true }
        textView.semanticContentAttribute = .forceRightToLeft
        textView.textAlignment = .center
        textView.text = "abc"
        textView.selectedRange = NSRange(location: 3, length: 0)
        #expect(textView.becomeFirstResponder())
        textView.setMarkedText("אב", selectedRange: NSRange(location: 2, length: 0))
        _ = try #require(textView.markedTextRange)

        let attributedBefore = textView.attributedText
        let selectionBefore = textView.selectedRange
        let alignmentBefore = textView.textAlignment
        let typingBefore = textView.typingAttributes

        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)

        #expect(textView.attributedText == attributedBefore)
        #expect(textView.selectedRange == selectionBefore)
        #expect(textView.textAlignment == alignmentBefore)
        #expect(NSDictionary(dictionary: textView.typingAttributes).isEqual(
            NSDictionary(dictionary: typingBefore)
        ))
    }

    @Test("A reused empty row keeps placeholder and caret alignment synchronized")
    func placeholderAndCaretAlignment() throws {
        let textView = TextViewWithPlaceholder(frame: .zero, textContainer: nil)
        textView.semanticContentAttribute = .forceRightToLeft
        textView.update(placeholder: NSAttributedString(string: "כתוב כאן"))
        let observer = TextMutationObserver()
        textView.delegate = observer
        textView.textStorage.delegate = observer
        observer.reset()

        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)

        let placeholder = try #require(textView.subviews.compactMap { $0 as? UILabel }.first)
        let paragraphStyle = try #require(
            textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        )
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .right)
        #expect(paragraphStyle.alignment == .right)
        #expect(placeholder.textAlignment == .right)
        #expect(textView.selectedRange == NSRange(location: 0, length: 0))
        #expect(textView.attributedText.length == 0)
        #expect(observer.textChangeCount == 0)
        #expect(observer.storageEditCount == 0)

        textView.semanticContentAttribute = .forceLeftToRight
        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)
        let updatedParagraphStyle = try #require(
            textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        )
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
        #expect(updatedParagraphStyle.alignment == .left)
        #expect(placeholder.textAlignment == .left)
        #expect(observer.textChangeCount == 0)
        #expect(observer.storageEditCount == 0)
    }

    @Test("Ordinary Note and Page receive the same application-direction context", arguments: [
        "ordinary-note-type",
        "ordinary-page-type"
    ])
    func ordinaryDocumentsAreNotGated(typeId: String) throws {
        let blockId = "block-\(typeId)"
        let info = makeInfo(blockId: blockId)
        let document = makeDocument(typeId: typeId, blockId: blockId, info: info)

        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: document,
            info: info,
            text: "ordinary text"
        ))

        #expect(context.origin == .ambiguousLegacyParagraph)
        #expect(context.blockId == blockId)
        #expect(!context.alignmentWasExplicit)
    }

    @Test("Content direction stays natural while default alignment follows app language")
    func contentDirectionAndDefaultAlignmentAreIndependent() {
        let textView = UITextView()
        textView.semanticContentAttribute = .forceLeftToRight
        textView.attributedText = NSAttributedString(string: "שלום")

        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)

        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
        #expect(PinkhaTextDirectionUIKitAdapter.detectedDirection(
            for: textView.text,
            fallback: .leftToRight
        ) == .rightToLeft)
    }

    @Test("Explicit alignment remains unchanged when application direction changes")
    func explicitAlignmentWins() {
        let textView = UITextView()
        textView.semanticContentAttribute = .forceRightToLeft
        textView.textAlignment = .left
        let explicitLeft = PinkhaTextBlockWritingContext(
            origin: .existingParagraph,
            persistedAlignment: .left,
            alignmentWasExplicit: true
        )

        PinkhaTextDirectionUIKitAdapter.apply(context: explicitLeft, to: textView)

        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
    }

    @Test("Old automatic markers no longer override the current application language")
    func oldAutomaticMarkerUsesCurrentLanguage() throws {
        let blockId = "automatic-marker"
        var fields = BlockFields()
        fields[PinkhaSchemaRoles.blockTextDirectionField] = Google_Protobuf_Value(
            stringValue: PinkhaTextDirectionMarker.automatic(.rightToLeft).storedValue
        )
        let info = makeInfo(blockId: blockId, alignment: .right, fields: fields)
        let document = makeDocument(typeId: "ordinary-page", blockId: blockId, info: info)
        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: document,
            info: info,
            text: ""
        ))
        let textView = UITextView()
        textView.semanticContentAttribute = .forceLeftToRight

        PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textView)

        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
        #expect(!context.alignmentWasExplicit)
    }

    @Test("Empty block -> typing -> Return -> next block -> focus -> reuse lifecycle")
    func emptyToTypingToReturnToNextBlockLifecycle() throws {
        // 1. Initial empty block configured in Hebrew environment
        let textView1 = UndoTrackingTextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        textView1.semanticContentAttribute = .forceRightToLeft
        let observer1 = TextMutationObserver()
        textView1.delegate = observer1
        textView1.textStorage.delegate = observer1
        observer1.reset()

        let context1 = PinkhaTextBlockWritingContext(
            origin: .newParagraph,
            persistedAlignment: nil,
            alignmentWasExplicit: false,
            blockId: "block-1"
        )
        PinkhaTextDirectionUIKitAdapter.apply(context: context1, to: textView1)

        #expect(textView1.textAlignment == .right)
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView1) == .right)
        let paragraphStyle1 = try #require(
            textView1.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        )
        #expect(paragraphStyle1.alignment == .right)
        #expect(paragraphStyle1.baseWritingDirection == .rightToLeft)
        #expect(observer1.textChangeCount == 0)
        #expect(observer1.storageEditCount == 0)

        // 2. Simulate typing Hebrew text into block 1
        textView1.textStorage.setAttributedString(NSAttributedString(
            string: "שלום עולם",
            attributes: textView1.typingAttributes
        ))
        PinkhaTextDirectionUIKitAdapter.apply(context: context1, to: textView1)
        textView1.layoutManager.ensureLayout(for: textView1.textContainer)
        let glyphRange1 = textView1.layoutManager.glyphRange(for: textView1.textContainer)
        let used1 = textView1.layoutManager.lineFragmentUsedRect(forGlyphAt: glyphRange1.location, effectiveRange: nil)
        let fragment1 = textView1.layoutManager.lineFragmentRect(forGlyphAt: glyphRange1.location, effectiveRange: nil)
        #expect(abs(used1.maxX - fragment1.maxX) < 0.5)

        // 3. User hits Return -> new empty block 2 created
        let textView2 = UndoTrackingTextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        textView2.semanticContentAttribute = .forceRightToLeft
        let observer2 = TextMutationObserver()
        textView2.delegate = observer2
        textView2.textStorage.delegate = observer2
        observer2.reset()

        let context2 = PinkhaTextBlockWritingContext(
            origin: .newParagraph,
            persistedAlignment: nil,
            alignmentWasExplicit: false,
            blockId: "block-2"
        )
        PinkhaTextDirectionUIKitAdapter.apply(context: context2, to: textView2)

        // The newly created block must be right-aligned and ready for RTL input immediately
        #expect(textView2.textAlignment == .right)
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView2) == .right)
        let paragraphStyle2 = try #require(
            textView2.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        )
        #expect(paragraphStyle2.alignment == .right)
        #expect(paragraphStyle2.baseWritingDirection == .rightToLeft)
        #expect(observer2.textChangeCount == 0)
        #expect(observer2.storageEditCount == 0)

        // 4. Focus handoff and cell reuse: re-applying configuration does not displace alignment
        PinkhaTextDirectionUIKitAdapter.apply(context: context2, to: textView2)
        #expect(textView2.textAlignment == .right)
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView2) == .right)
    }

    @Test("App-level Hebrew direction overrides inherited LTR device direction")
    func appLevelHebrewDirectionOverridesDeviceLTR() throws {
        let textView = UITextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        textView.semanticContentAttribute = .forceRightToLeft

        let context = PinkhaTextBlockWritingContext(
            origin: .newParagraph,
            persistedAlignment: nil,
            alignmentWasExplicit: false,
            blockId: "block-he"
        )

        PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textView)

        #expect(textView.textAlignment == .right)
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .right)
        let paragraphStyle = try #require(
            textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        )
        #expect(paragraphStyle.alignment == .right)
        #expect(paragraphStyle.baseWritingDirection == .rightToLeft)
    }

    @Test("Two simultaneous containers with opposite directions isolate text views without cross-window bleed")
    func oppositeDirectionContainersIsolateTextViews() throws {
        let containerRTL = UIView(frame: CGRect(x: 0, y: 0, width: 320, height: 480))
        containerRTL.semanticContentAttribute = .forceRightToLeft

        let containerLTR = UIView(frame: CGRect(x: 0, y: 0, width: 320, height: 480))
        containerLTR.semanticContentAttribute = .forceLeftToRight

        let textViewRTL = UndoTrackingTextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        let textViewLTR = UndoTrackingTextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))

        containerRTL.addSubview(textViewRTL)
        containerLTR.addSubview(textViewLTR)

        let context = PinkhaTextBlockWritingContext(
            origin: .newParagraph,
            persistedAlignment: nil,
            alignmentWasExplicit: false,
            blockId: "isolated-block"
        )

        // Alternating updates in the same process
        PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textViewRTL)
        PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textViewLTR)
        PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textViewRTL)

        #expect(PinkhaTextDirectionUIKitAdapter.effectiveInterfaceDirection(for: textViewRTL) == .rightToLeft)
        #expect(PinkhaTextDirectionUIKitAdapter.effectiveInterfaceDirection(for: textViewLTR) == .leftToRight)
        #expect(textViewRTL.textAlignment == .right)
        #expect(textViewLTR.textAlignment == .left)
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textViewRTL) == .right)
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textViewLTR) == .left)

        let styleRTL = try #require(textViewRTL.typingAttributes[.paragraphStyle] as? NSParagraphStyle)
        let styleLTR = try #require(textViewLTR.typingAttributes[.paragraphStyle] as? NSParagraphStyle)
        #expect(styleRTL.alignment == .right)
        #expect(styleRTL.baseWritingDirection == .rightToLeft)
        #expect(styleLTR.alignment == .left)
        #expect(styleLTR.baseWritingDirection == .leftToRight)

        // Row reuse: moving a text view from LTR container to RTL container
        textViewLTR.removeFromSuperview()
        containerRTL.addSubview(textViewLTR)
        PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textViewLTR)
        #expect(PinkhaTextDirectionUIKitAdapter.effectiveInterfaceDirection(for: textViewLTR) == .rightToLeft)
        #expect(textViewLTR.textAlignment == .right)
    }

    @Test("Editing preparation restores empty-row typing direction after a host style reset")
    func editingPreparationRestoresTypingDefaults() throws {
        let textView = UndoTrackingTextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        textView.semanticContentAttribute = .forceRightToLeft
        let observer = TextMutationObserver()
        textView.delegate = observer
        textView.textStorage.delegate = observer
        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)
        textView.textAlignment = .left
        textView.typingAttributes = [.font: UIFont.systemFont(ofSize: 17)]
        observer.reset()

        PinkhaTextDirectionUIKitAdapter.prepareForEditing(in: textView)

        let style = try #require(textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle)
        #expect(style.alignment == .right)
        #expect(style.baseWritingDirection == .rightToLeft)
        #expect(textView.selectedRange == NSRange(location: 0, length: 0))
        #expect(textView.textStorage.length == 0)
        #expect(observer.storageEditCount == 0)
        #expect(observer.textChangeCount == 0)

        PinkhaTextDirectionUIKitAdapter.apply(context: nil, to: textView)
        textView.typingAttributes = [:]
        PinkhaTextDirectionUIKitAdapter.prepareForEditing(in: textView)
        #expect(textView.typingAttributes[.paragraphStyle] == nil)
    }

    @Test("Native row caret and delegate insertion contract after attachment", arguments: [false, true])
    func nativeRowAttachmentProbe(configureAfterAttachment: Bool) async throws {
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let window = UIWindow(windowScene: scene)
        window.frame = CGRect(x: 0, y: 0, width: 390, height: 844)
        let controller = UIViewController()
        controller.view.semanticContentAttribute = .forceRightToLeft
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer { window.isHidden = true }

        let row = TextBlockContentView(frame: CGRect(x: 20, y: 80, width: 320, height: 160))
        let textView = row.textView.textView
        textView.semanticContentAttribute = .forceLeftToRight
        var acceptedInsertions = 0
        var insertionDirection: NSWritingDirection?
        let defaults = TextBlockContentConfiguration.empty
        let original = defaults.actions
        let actions = TextBlockContentConfiguration.Actions(
            shouldPaste: original.shouldPaste, copy: original.copy, cut: original.cut,
            createEmptyBlock: original.createEmptyBlock, showObject: original.showObject,
            openURL: original.openURL, handleKeyboardAction: original.handleKeyboardAction,
            becomeFirstResponder: original.becomeFirstResponder, resignFirstResponder: original.resignFirstResponder,
            textBlockSetNeedsLayout: original.textBlockSetNeedsLayout,
            textViewDidChangeText: original.textViewDidChangeText,
            textViewWillBeginEditing: original.textViewWillBeginEditing,
            textViewDidBeginEditing: original.textViewDidBeginEditing,
            textViewDidEndEditing: original.textViewDidEndEditing,
            textViewDidChangeCaretPosition: original.textViewDidChangeCaretPosition,
            textViewShouldReplaceText: { view, replacement, range in
                if !replacement.isEmpty, view.textStorage.length == 0, range == NSRange(location: 0, length: 0) {
                    acceptedInsertions += 1
                    insertionDirection = (view.typingAttributes[.paragraphStyle] as? NSParagraphStyle)?.baseWritingDirection
                }
                return true
            },
            toggleCheckBox: original.toggleCheckBox, toggleDropDown: original.toggleDropDown,
            tapOnCalloutIcon: original.tapOnCalloutIcon, escalateToBlockSelection: original.escalateToBlockSelection
        )
        let hostStyle = NSMutableParagraphStyle()
        hostStyle.alignment = .left
        let configuration = TextBlockContentConfiguration(
            blockId: "attachment-probe", content: .empty(contentType: .text),
            attributedString: NSAttributedString(), placeholderAttributes: [:],
            typingAttributes: { _ in [.paragraphStyle: hostStyle, .font: UIFont.systemFont(ofSize: 17)] },
            textContainerInsets: .zero, alignment: .left,
            pinkhaWritingContext: automaticContext,
            isCheckable: false, isToggled: false, isChecked: false, shouldDisplayPlaceholder: false,
            initialBlockFocusPosition: nil, focusPublisher: defaults.focusPublisher,
            resetPublisher: defaults.resetPublisher, actions: actions
        )
        if configureAfterAttachment {
            controller.view.addSubview(row)
        }
        row.update(with: configuration)
        if !configureAfterAttachment { controller.view.addSubview(row) }
        await Task.yield()
        // Other rendering suites can own temporary windows while this task yields.
        // Keep focus, empty-caret measurement and accepted insertion in one MainActor turn.
        window.makeKeyAndVisible()
        controller.view.layoutIfNeeded()
        row.takeFocus(at: .beginning)
        controller.view.layoutIfNeeded()

        try #require(textView.isFirstResponder, "A nonfocused fixture cannot prove native typing/caret behavior")
        #expect(textView.markedTextRange == nil)
        #expect(textView.selectedRange == NSRange(location: 0, length: 0))
        let selected = try #require(textView.selectedTextRange)
        let emptyCaret = textView.caretRect(for: selected.start)
        print("PINKHA_NATIVE_CARET attachedBeforeConfiguration=\(configureAfterAttachment) caretX=\(emptyCaret.midX) midpoint=\(textView.bounds.midX) responder=\(textView.isFirstResponder)")
        #expect(emptyCaret.midX > textView.bounds.midX,
                "Initial empty caret must be physically right before inserting any text")

        // UIKit's programmatic insertText bypasses should-change on the measured SDK.
        // Exercise the real native delegate contract explicitly; real keyboard input is
        // measured separately by Full Acceptance, never inferred from this unit test.
        let accepted = textView.delegate?.textView?(
            textView, shouldChangeTextIn: NSRange(location: 0, length: 0), replacementText: "א"
        ) ?? false
        try #require(accepted)
        print("PINKHA_NATIVE_DELEGATE_CONTRACT accepted=\(acceptedInsertions) direction=\(String(describing: insertionDirection))")
        textView.insertText("א")
        #expect(acceptedInsertions == 1,
                "A missing real delegate callback invalidates the probe; it is not a direction pass")
        #expect(insertionDirection == .rightToLeft)
        #expect(textView.text == "א")
        textView.resignFirstResponder()
    }

    private var automaticContext: PinkhaTextBlockWritingContext {
        PinkhaTextBlockWritingContext(
            origin: .ambiguousLegacyParagraph,
            persistedAlignment: .left,
            alignmentWasExplicit: false
        )
    }

    private func makeDocument(
        typeId: String,
        blockId: String,
        info: BlockInformation
    ) -> MockBaseDocument {
        let details = ObjectDetails(
            id: "document-\(typeId)",
            values: [
                BundledPropertyKey.type.rawValue: Google_Protobuf_Value(stringValue: typeId)
            ]
        )
        let document = MockBaseDocument(objectId: details.id, details: details)
        document.mockSpaceId = "ordinary-space"
        let container = InfoContainerMock()
        container.getReturnInfo[blockId] = info
        document.mockInfoContainer = container
        return document
    }

    private func makeInfo(
        blockId: String,
        alignment: LayoutAlignment = .left,
        fields: BlockFields = [:]
    ) -> BlockInformation {
        BlockInformation(
            id: blockId,
            content: .text(.plain("ordinary text", contentType: .text)),
            backgroundColor: nil,
            horizontalAlignment: alignment,
            childrenIds: [],
            configurationData: BlockInformationMetadata(backgroundColor: .default),
            fields: fields
        )
    }
}

@MainActor
private final class UndoTrackingTextView: UITextView {
    let testUndoManager = UndoManager()
    override var undoManager: UndoManager? { testUndoManager }
}

@MainActor
private final class TextMutationObserver: NSObject, UITextViewDelegate, NSTextStorageDelegate {
    private(set) var textChangeCount = 0
    private(set) var storageEditCount = 0
    private(set) var characterEditCount = 0

    func reset() {
        textChangeCount = 0
        storageEditCount = 0
        characterEditCount = 0
    }

    func textViewDidChange(_ textView: UITextView) {
        textChangeCount += 1
    }

    nonisolated func textStorage(
        _ textStorage: NSTextStorage,
        didProcessEditing editedMask: NSTextStorage.EditActions,
        range editedRange: NSRange,
        changeInLength delta: Int
    ) {
        MainActor.assumeIsolated {
            storageEditCount += 1
            if editedMask.contains(.editedCharacters) { characterEditCount += 1 }
        }
    }
}

private final class UndoFlagBox: NSObject {
    var reached = false
}
