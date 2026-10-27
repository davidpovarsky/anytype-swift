import Foundation

public enum PinkhaLayoutDirection: Sendable, Equatable, Hashable {
    case leftToRight
    case rightToLeft
}

public enum PinkhaParagraphAlignment: Sendable, Equatable, Hashable {
    case left
    case center
    case right
    case justified
    case natural
}

public enum PinkhaWritingContext: Sendable, Equatable, Hashable {
    case standardAnytype
    case pinkhaWritingDocument
}

public enum PinkhaParagraphOrigin: Sendable, Equatable, Hashable {
    case newParagraph
    case existingParagraph
    case ambiguousLegacyParagraph
}

public enum PinkhaWritingMutation: Sendable, Equatable, Hashable {
    case none
    case initializeNewParagraph
    case displayOnlyLegacyFallback
}

public struct PinkhaWritingDirectionInput: Sendable, Equatable {
    public let context: PinkhaWritingContext
    public let origin: PinkhaParagraphOrigin
    public let isEmpty: Bool
    public let interfaceDirection: PinkhaLayoutDirection
    public let detectedTextDirection: PinkhaLayoutDirection?
    public let persistedAutomaticDirection: PinkhaLayoutDirection?
    public let persistedAlignment: PinkhaParagraphAlignment?
    public let alignmentWasExplicit: Bool

    public init(
        context: PinkhaWritingContext,
        origin: PinkhaParagraphOrigin,
        isEmpty: Bool,
        interfaceDirection: PinkhaLayoutDirection,
        detectedTextDirection: PinkhaLayoutDirection?,
        persistedAutomaticDirection: PinkhaLayoutDirection? = nil,
        persistedAlignment: PinkhaParagraphAlignment?,
        alignmentWasExplicit: Bool
    ) {
        self.context = context
        self.origin = origin
        self.isEmpty = isEmpty
        self.interfaceDirection = interfaceDirection
        self.detectedTextDirection = detectedTextDirection
        self.persistedAutomaticDirection = persistedAutomaticDirection
        self.persistedAlignment = persistedAlignment
        self.alignmentWasExplicit = alignmentWasExplicit
    }
}

public struct PinkhaWritingDirectionDecision: Sendable, Equatable {
    public let baseWritingDirection: PinkhaLayoutDirection
    public let alignment: PinkhaParagraphAlignment
    public let mutation: PinkhaWritingMutation

    public init(
        baseWritingDirection: PinkhaLayoutDirection,
        alignment: PinkhaParagraphAlignment,
        mutation: PinkhaWritingMutation
    ) {
        self.baseWritingDirection = baseWritingDirection
        self.alignment = alignment
        self.mutation = mutation
    }
}

/// Pure Pinkha writing rules. Platform adapters remain responsible for asking UIKit/AppKit for
/// the detected direction of non-empty text and for mapping the decision to paragraph styles.
/// This type deliberately does not attempt to implement the Unicode Bidirectional Algorithm.
public enum PinkhaWritingDirectionPolicy {
    public static func resolve(
        _ input: PinkhaWritingDirectionInput
    ) -> PinkhaWritingDirectionDecision? {
        guard input.context == .pinkhaWritingDocument else { return nil }

        let direction = resolvedDirection(input)
        let directionalAlignment: PinkhaParagraphAlignment = direction == .rightToLeft
            ? .right
            : .left

        if input.alignmentWasExplicit, let persistedAlignment = input.persistedAlignment {
            return PinkhaWritingDirectionDecision(
                baseWritingDirection: direction,
                alignment: persistedAlignment,
                mutation: input.origin == .newParagraph ? .initializeNewParagraph : .none
            )
        }

        switch input.origin {
        case .newParagraph:
            return PinkhaWritingDirectionDecision(
                baseWritingDirection: direction,
                alignment: directionalAlignment,
                mutation: .initializeNewParagraph
            )
        case .existingParagraph:
            return PinkhaWritingDirectionDecision(
                baseWritingDirection: direction,
                alignment: input.persistedAlignment ?? directionalAlignment,
                mutation: .none
            )
        case .ambiguousLegacyParagraph:
            return PinkhaWritingDirectionDecision(
                baseWritingDirection: direction,
                // A marker-less host `.left`/`.right` value is indistinguishable from the
                // historical default. Show Hebrew on its physical reading side but keep this
                // fallback display-only: no marker or alignment migration is ever written.
                // Center and justified are non-default choices and remain visually intact.
                alignment: legacyDisplayAlignment(
                    stored: input.persistedAlignment,
                    directional: directionalAlignment
                ),
                mutation: .displayOnlyLegacyFallback
            )
        }
    }

    private static func resolvedDirection(
        _ input: PinkhaWritingDirectionInput
    ) -> PinkhaLayoutDirection {
        if !input.isEmpty, let detectedTextDirection = input.detectedTextDirection {
            return detectedTextDirection
        }
        if let persistedAutomaticDirection = input.persistedAutomaticDirection {
            return persistedAutomaticDirection
        }
        return input.interfaceDirection
    }

    private static func legacyDisplayAlignment(
        stored: PinkhaParagraphAlignment?,
        directional: PinkhaParagraphAlignment
    ) -> PinkhaParagraphAlignment {
        switch stored {
        case .center, .justified:
            return stored ?? directional
        case .left, .right, .natural, nil:
            return directional
        }
    }
}
