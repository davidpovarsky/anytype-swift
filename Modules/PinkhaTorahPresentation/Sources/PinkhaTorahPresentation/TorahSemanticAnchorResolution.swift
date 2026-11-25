import Foundation
import PinkhaKit

/// Each engine supplies a complete, newly authorized native document read.
/// The shared session never resolves by an old block, quote, or stored offset.
public typealias TorahSemanticAnchorResolutionHandler = @MainActor @Sendable
    (PinkhaSemanticTextAnchor) async throws -> PinkhaSemanticTextAnchorResolver.Resolution

public enum TorahSemanticAnchorResolutionError: Error, LocalizedError, Sendable, Equatable {
    case unavailable
    case missing
    case ambiguous
    case writeUnconfirmed

    public var errorDescription: String? {
        switch self {
        case .unavailable: PinkhaSemanticAnchorUI.text(.unavailable)
        case .missing: PinkhaSemanticAnchorUI.text(.missing)
        case .ambiguous: PinkhaSemanticAnchorUI.text(.ambiguous)
        case .writeUnconfirmed: PinkhaSemanticAnchorUI.text(.sourceLinkUnconfirmed)
        }
    }
}
