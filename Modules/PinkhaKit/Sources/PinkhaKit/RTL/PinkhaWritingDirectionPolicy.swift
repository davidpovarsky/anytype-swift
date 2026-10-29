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

public enum PinkhaParagraphOrigin: Sendable, Equatable, Hashable {
    case newParagraph
    case existingParagraph
    case ambiguousLegacyParagraph
}

public struct PinkhaWritingDirectionInput: Sendable, Equatable {
    public let isEmpty: Bool
    public let interfaceDirection: PinkhaLayoutDirection
    public let detectedTextDirection: PinkhaLayoutDirection?
    public let persistedAlignment: PinkhaParagraphAlignment?
    public let alignmentWasExplicit: Bool

    public init(
        isEmpty: Bool,
        interfaceDirection: PinkhaLayoutDirection,
        detectedTextDirection: PinkhaLayoutDirection?,
        persistedAlignment: PinkhaParagraphAlignment?,
        alignmentWasExplicit: Bool
    ) {
        self.isEmpty = isEmpty
        self.interfaceDirection = interfaceDirection
        self.detectedTextDirection = detectedTextDirection
        self.persistedAlignment = persistedAlignment
        self.alignmentWasExplicit = alignmentWasExplicit
    }
}

public struct PinkhaWritingDirectionDecision: Sendable, Equatable {
    public let baseWritingDirection: PinkhaLayoutDirection
    public let alignment: PinkhaParagraphAlignment

    public init(
        baseWritingDirection: PinkhaLayoutDirection,
        alignment: PinkhaParagraphAlignment
    ) {
        self.baseWritingDirection = baseWritingDirection
        self.alignment = alignment
    }
}

/// App-wide writing presentation rules.
///
/// The effective application direction owns the default visual alignment for every document.
/// Non-empty content may still establish its natural base writing direction, while an explicit
/// user alignment always wins. Historical marker-less left/right values are ambiguous, so they
/// are treated as old defaults and adapted for display only; center and justified values are
/// unambiguous formatting choices and remain unchanged. This policy never requests persistence.
public enum PinkhaWritingDirectionPolicy {
    public static func resolve(
        _ input: PinkhaWritingDirectionInput
    ) -> PinkhaWritingDirectionDecision {
        let contentDirection = if input.isEmpty {
            input.interfaceDirection
        } else {
            input.detectedTextDirection ?? input.interfaceDirection
        }
        let applicationDefaultAlignment: PinkhaParagraphAlignment =
            input.interfaceDirection == .rightToLeft ? .right : .left

        let alignment: PinkhaParagraphAlignment
        if input.alignmentWasExplicit, let persistedAlignment = input.persistedAlignment {
            alignment = persistedAlignment
        } else {
            switch input.persistedAlignment {
            case .center, .justified:
                alignment = input.persistedAlignment ?? applicationDefaultAlignment
            case .left, .right, .natural, nil:
                alignment = applicationDefaultAlignment
            }
        }

        return PinkhaWritingDirectionDecision(
            baseWritingDirection: contentDirection,
            alignment: alignment
        )
    }
}
