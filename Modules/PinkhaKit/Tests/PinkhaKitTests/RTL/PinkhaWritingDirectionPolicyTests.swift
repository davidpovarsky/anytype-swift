import Testing
@testable import PinkhaKit

@Suite("App-wide writing direction policy")
struct PinkhaWritingDirectionPolicyTests {
    @Test("Empty editing defaults follow the effective application direction", arguments: [
        (PinkhaLayoutDirection.leftToRight, PinkhaParagraphAlignment.left),
        (PinkhaLayoutDirection.rightToLeft, PinkhaParagraphAlignment.right)
    ])
    func emptyDefaultFollowsApplicationDirection(
        direction: PinkhaLayoutDirection,
        alignment: PinkhaParagraphAlignment
    ) {
        let decision = resolve(
            isEmpty: true,
            interfaceDirection: direction
        )

        #expect(decision.baseWritingDirection == direction)
        #expect(decision.alignment == alignment)
    }

    @Test("Content direction is respected without changing the application default alignment")
    func contentDirectionDoesNotOwnDefaultAlignment() {
        let decision = resolve(
            isEmpty: false,
            interfaceDirection: .leftToRight,
            detectedTextDirection: .rightToLeft,
            persistedAlignment: .right
        )

        #expect(decision.baseWritingDirection == .rightToLeft)
        #expect(decision.alignment == .left)
    }

    @Test("Explicit user alignment survives every application direction", arguments: [
        (PinkhaParagraphAlignment.left, PinkhaLayoutDirection.rightToLeft),
        (PinkhaParagraphAlignment.right, PinkhaLayoutDirection.leftToRight),
        (PinkhaParagraphAlignment.center, PinkhaLayoutDirection.rightToLeft),
        (PinkhaParagraphAlignment.justified, PinkhaLayoutDirection.leftToRight)
    ])
    func explicitAlignmentWins(
        alignment: PinkhaParagraphAlignment,
        direction: PinkhaLayoutDirection
    ) {
        let decision = resolve(
            isEmpty: false,
            interfaceDirection: direction,
            detectedTextDirection: direction,
            persistedAlignment: alignment,
            alignmentWasExplicit: true
        )

        #expect(decision.alignment == alignment)
    }

    @Test("Ambiguous old left and right values follow the current app language", arguments: [
        (PinkhaParagraphAlignment.left, PinkhaLayoutDirection.rightToLeft, PinkhaParagraphAlignment.right),
        (PinkhaParagraphAlignment.right, PinkhaLayoutDirection.leftToRight, PinkhaParagraphAlignment.left)
    ])
    func ambiguousLegacyAlignmentIsDisplayOnly(
        stored: PinkhaParagraphAlignment,
        direction: PinkhaLayoutDirection,
        expected: PinkhaParagraphAlignment
    ) {
        let decision = resolve(
            isEmpty: false,
            interfaceDirection: direction,
            detectedTextDirection: direction,
            persistedAlignment: stored
        )

        #expect(decision.alignment == expected)
    }

    @Test("Unmarked center and justified formatting remain visually unchanged")
    func unmarkedNonDefaultAlignmentIsPreserved() {
        for alignment in [PinkhaParagraphAlignment.center, .justified] {
            let decision = resolve(
                isEmpty: false,
                interfaceDirection: .rightToLeft,
                detectedTextDirection: .rightToLeft,
                persistedAlignment: alignment
            )
            #expect(decision.alignment == alignment)
        }
    }

    private func resolve(
        isEmpty: Bool,
        interfaceDirection: PinkhaLayoutDirection,
        detectedTextDirection: PinkhaLayoutDirection? = nil,
        persistedAlignment: PinkhaParagraphAlignment? = nil,
        alignmentWasExplicit: Bool = false
    ) -> PinkhaWritingDirectionDecision {
        PinkhaWritingDirectionPolicy.resolve(
            PinkhaWritingDirectionInput(
                isEmpty: isEmpty,
                interfaceDirection: interfaceDirection,
                detectedTextDirection: detectedTextDirection,
                persistedAlignment: persistedAlignment,
                alignmentWasExplicit: alignmentWasExplicit
            )
        )
    }
}
