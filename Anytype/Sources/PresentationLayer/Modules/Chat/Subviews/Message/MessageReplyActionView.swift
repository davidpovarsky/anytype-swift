import Foundation
import SwiftUI

struct MessageReplyActionView<Content: View>: View {
    
    // MARK: - Gesture Config
    
    private let minReplyWidth: CGFloat = 50
    private let replyImageWidth: CGFloat = 32
    
    // MARK: - State
    
    @State private var offsetX: CGFloat = 0
    @State private var hasTriggeredFeedback = false
    @Binding private var centerOffsetY: CGFloat
    
    let isEnabled: Bool
    let contentHorizontalPadding: CGFloat
    let content: Content
    let action: () -> Void
    
    init(isEnabled: Bool, contentHorizontalPadding: CGFloat, centerOffsetY: Binding<CGFloat>, @ViewBuilder content: () -> Content, action: @escaping () -> Void) {
        self.isEnabled = isEnabled
        self.contentHorizontalPadding = contentHorizontalPadding
        self._centerOffsetY = centerOffsetY
        self.action = action
        self.content = content()
    }
    
    var body: some View {
        if #available(iOS 18.0, *), isEnabled {
            contentWithReply
        } else {
            content
        }
    }
    
    @available(iOS 18.0, *)
    private var contentWithReply: some View {
        let progress = (abs(offsetX) / minReplyWidth).clamped(to: 0...1)
        return content
            .overlay(alignment: .topTrailing) {
                Image(asset: .X32.reply)
                    .renderingMode(.template)
                    .foregroundStyle(Color.Control.primary)
                    .padding(.trailing, -(contentHorizontalPadding + replyImageWidth))
                    .opacity(progress)
                    .scaleEffect(progress)
                    .offset(y: centerOffsetY - replyImageWidth/2)
            }
            .offset(x: offsetX)
            .animation(.easeOut(duration: 0.15), value: offsetX)
            .gesture(MessageReplyGestureRecognizer(handleAction: { gesture in
                guard let view = gesture.view else { return }
                let translation = gesture.translation(in: gesture.view)
                let directedDistance = view.effectiveUserInterfaceLayoutDirection == .rightToLeft
                    ? translation.x
                    : -translation.x
                switch gesture.state {
                case .changed:
                    guard directedDistance > 0 else { return }
                    
                    offsetX = translation.x
                    
                    if !hasTriggeredFeedback && directedDistance >= minReplyWidth {
                        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
                        hasTriggeredFeedback = true
                    }
                case .ended:
                    if directedDistance > minReplyWidth {
                        action()
                    }
                    withAnimation {
                        offsetX = 0
                    }
                    hasTriggeredFeedback = false
                default:
                    break
                }
            }))
    }
}
