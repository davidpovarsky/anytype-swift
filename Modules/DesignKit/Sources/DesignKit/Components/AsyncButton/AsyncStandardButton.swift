import Foundation
import SwiftUI

public struct AsyncStandardButton: View {
    
    let text: String
    let style: StandardButtonStyle
    let action: () async throws -> Void
    let prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?
    
    @State private var inProgress: Bool = false
    @State private var toast: ToastBarData?
    @Environment(\.standardButtonGroupDisable) @Binding private var groupDisable
    
    public init(
        _ text: String,
        style: StandardButtonStyle,
        prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? = nil,
        action: @escaping () async throws -> Void
    ) {
        self.text = text
        self.style = style
        self.prepareAction = prepareAction
        self.action = action
    }
    
    public var body: some View {
        StandardButton(.text(text), inProgress: inProgress, style: style) {
            // Optional original-owner reservation happens at the real tap,
            // before the existing task. The default route remains unchanged.
            if prepareAction != nil, inProgress || groupDisable { return }
            let prepared = prepareAction?()
            // Add delay
            inProgress = true
            groupDisable = true
            Task {
                do {
                    UISelectionFeedbackGenerator().selectionChanged()
                    if let prepared {
                        try await prepared()
                    } else {
                        try await action()
                    }
                } catch {
                    UINotificationFeedbackGenerator().notificationOccurred(.error)
                    toast = ToastBarData(error.localizedDescription, type: .failure)
                }
                inProgress = false
                groupDisable = false
            }
        }
        .disabled(groupDisable && !inProgress)
        .snackbar(toastBarData: $toast)
    }
}
