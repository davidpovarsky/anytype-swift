import Foundation
import SwiftUI

extension View {
    func customBackSwipe(_ actionEnded: @escaping () -> Void) -> some View {
        modifier(CustomBackSwipeModifier(actionEnded: actionEnded))
    }
}

private struct CustomBackSwipeModifier: ViewModifier {
    @Environment(\.layoutDirection) private var layoutDirection
    @State private var width: CGFloat = 0

    let actionEnded: () -> Void

    func body(content: Content) -> some View {
        content
            .onGeometryChange(for: CGFloat.self) { proxy in
                proxy.size.width
            } action: { width in
                self.width = width
            }
            .simultaneousGesture(
            DragGesture()
                .onEnded { value in
                    guard isLeadingEdgeSwipe(value) else { return }
                    actionEnded()
                }
        )
    }

    private func isLeadingEdgeSwipe(_ value: DragGesture.Value) -> Bool {
        guard width > 0 else { return false }
        let edgeWidth = min(50, width)
        switch layoutDirection {
        case .leftToRight:
            return value.startLocation.x < edgeWidth
                && value.translation.width > 50
        case .rightToLeft:
            return value.startLocation.x > width - edgeWidth
                && value.translation.width < -50
        @unknown default:
            return false
        }
    }
}
