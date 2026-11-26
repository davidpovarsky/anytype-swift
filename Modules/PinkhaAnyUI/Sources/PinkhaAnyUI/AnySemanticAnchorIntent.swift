#if canImport(SwiftUI)
import Foundation
import PinkhaKit
import PinkhaAnyHost

/// One read-only preview, owned by the mounted document that prepared it.
/// The identity is consumed before a native write and can never be retried.
@MainActor
public final class AnySemanticAnchorIntent {
    public let anchor: PinkhaSemanticTextAnchor
    public let blockID: String
    public let selectedText: String
    let owner: UUID
    let capture: AnySemanticAnchorCapture
    var consumed = false

    init(owner: UUID, capture: AnySemanticAnchorCapture, selectedText: String) {
        self.owner = owner
        self.capture = capture
        self.anchor = capture.anchor
        self.blockID = capture.blockID
        self.selectedText = selectedText
    }
}
#endif
