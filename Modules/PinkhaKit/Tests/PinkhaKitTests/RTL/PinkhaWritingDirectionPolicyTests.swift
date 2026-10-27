import Testing
@testable import PinkhaKit

@Suite("Pinkha writing direction policy")
struct PinkhaWritingDirectionPolicyTests {
    @Test("A new empty Hebrew paragraph starts RTL and right aligned")
    func newEmptyHebrewParagraph() {
        let decision = PinkhaWritingDirectionPolicy.resolve(input(
            origin: .newParagraph,
            isEmpty: true,
            interfaceDirection: .rightToLeft
        ))

        #expect(decision == PinkhaWritingDirectionDecision(
            baseWritingDirection: .rightToLeft,
            alignment: .right,
            mutation: .initializeNewParagraph
        ))
    }

    @Test("A new empty English paragraph remains LTR and left aligned")
    func newEmptyEnglishParagraph() {
        let decision = PinkhaWritingDirectionPolicy.resolve(input(
            origin: .newParagraph,
            isEmpty: true,
            interfaceDirection: .leftToRight
        ))

        #expect(decision == PinkhaWritingDirectionDecision(
            baseWritingDirection: .leftToRight,
            alignment: .left,
            mutation: .initializeNewParagraph
        ))
    }

    @Test("Platform-detected text direction wins for mixed non-empty text", arguments: [
        PinkhaLayoutDirection.leftToRight,
        PinkhaLayoutDirection.rightToLeft
    ])
    func detectedDirectionWins(detectedDirection: PinkhaLayoutDirection) {
        let decision = PinkhaWritingDirectionPolicy.resolve(input(
            origin: .newParagraph,
            isEmpty: false,
            interfaceDirection: .rightToLeft,
            detectedTextDirection: detectedDirection
        ))

        #expect(decision?.baseWritingDirection == detectedDirection)
        #expect(decision?.alignment == (detectedDirection == .rightToLeft ? .right : .left))
    }

    @Test("Explicit alignment survives in either writing direction", arguments: [
        (PinkhaParagraphAlignment.left, PinkhaLayoutDirection.rightToLeft),
        (PinkhaParagraphAlignment.right, PinkhaLayoutDirection.leftToRight),
        (PinkhaParagraphAlignment.center, PinkhaLayoutDirection.rightToLeft)
    ])
    func explicitAlignmentWins(
        alignment: PinkhaParagraphAlignment,
        direction: PinkhaLayoutDirection
    ) {
        let decision = PinkhaWritingDirectionPolicy.resolve(input(
            origin: .existingParagraph,
            isEmpty: false,
            interfaceDirection: .rightToLeft,
            detectedTextDirection: direction,
            persistedAlignment: alignment,
            alignmentWasExplicit: true
        ))

        #expect(decision?.alignment == alignment)
        #expect(decision?.baseWritingDirection == direction)
        #expect(decision?.mutation == PinkhaWritingMutation.none)
    }

    @Test("Ambiguous markerless Hebrew uses a reversible display-only right alignment")
    func ambiguousLegacyParagraph() {
        let decision = PinkhaWritingDirectionPolicy.resolve(input(
            origin: .ambiguousLegacyParagraph,
            isEmpty: false,
            interfaceDirection: .rightToLeft,
            detectedTextDirection: .rightToLeft,
            persistedAlignment: .left,
            alignmentWasExplicit: false
        ))

        #expect(decision?.alignment == .right)
        #expect(decision?.mutation == .displayOnlyLegacyFallback)
    }

    @Test("A persisted automatic marker restores direction before live detection is available")
    func persistedAutomaticDirectionRestoresOnReopen() {
        let decision = PinkhaWritingDirectionPolicy.resolve(input(
            origin: .existingParagraph,
            isEmpty: true,
            interfaceDirection: .leftToRight,
            persistedAutomaticDirection: .rightToLeft,
            persistedAlignment: .right
        ))

        #expect(decision?.baseWritingDirection == .rightToLeft)
        #expect(decision?.alignment == .right)
        #expect(decision?.mutation == PinkhaWritingMutation.none)
    }

    @Test("Legacy center and justified choices stay visually unchanged")
    func legacyNonDefaultAlignmentIsPreserved() {
        for alignment in [PinkhaParagraphAlignment.center, .justified] {
            let decision = PinkhaWritingDirectionPolicy.resolve(input(
                origin: .ambiguousLegacyParagraph,
                isEmpty: false,
                interfaceDirection: .rightToLeft,
                detectedTextDirection: .rightToLeft,
                persistedAlignment: alignment
            ))
            #expect(decision?.alignment == alignment)
            #expect(decision?.mutation == .displayOnlyLegacyFallback)
        }
    }

    @Test("Standard Anytype documents are outside Pinkha policy")
    func standardAnytypeIsUntouched() {
        let decision = PinkhaWritingDirectionPolicy.resolve(input(
            context: .standardAnytype,
            origin: .newParagraph,
            isEmpty: true,
            interfaceDirection: .rightToLeft
        ))

        #expect(decision == nil)
    }

    private func input(
        context: PinkhaWritingContext = .pinkhaWritingDocument,
        origin: PinkhaParagraphOrigin,
        isEmpty: Bool,
        interfaceDirection: PinkhaLayoutDirection,
        detectedTextDirection: PinkhaLayoutDirection? = nil,
        persistedAutomaticDirection: PinkhaLayoutDirection? = nil,
        persistedAlignment: PinkhaParagraphAlignment? = nil,
        alignmentWasExplicit: Bool = false
    ) -> PinkhaWritingDirectionInput {
        PinkhaWritingDirectionInput(
            context: context,
            origin: origin,
            isEmpty: isEmpty,
            interfaceDirection: interfaceDirection,
            detectedTextDirection: detectedTextDirection,
            persistedAutomaticDirection: persistedAutomaticDirection,
            persistedAlignment: persistedAlignment,
            alignmentWasExplicit: alignmentWasExplicit
        )
    }
}
