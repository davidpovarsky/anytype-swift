import Foundation
import PinkhaKit

/// A migration containing semantic targets must resolve them from the actual
/// destination document. Ordinary object existence does not prove a marker is
/// present, unique or currently owned by that object.
public protocol AnyTorahSemanticTargetAccess: AnyTorahTargetAccess {
    func validateSemanticTarget(_ anchor: PinkhaSemanticTextAnchor) async throws
}
