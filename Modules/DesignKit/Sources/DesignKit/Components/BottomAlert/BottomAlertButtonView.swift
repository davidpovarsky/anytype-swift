import Foundation
import SwiftUI
import AnytypeCore

public struct BottomAlertButton {
    
    public enum Style {
        case primary
        case secondary
        case warning
    }
    
    public var text: String
    public var style: Style
    public var disable = false
    public var action: () async throws -> Void
    public var prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?
    
    public init(text: String, style: Style, disable: Bool = false,
                prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? = nil,
                action: @escaping () async throws -> Void) {
        self.text = text
        self.style = style
        self.disable = disable
        self.action = action
        self.prepareAction = prepareAction
    }
    
    fileprivate var standartStyle: StandardButtonStyle {
        switch style {
        case .primary:
            return .primaryLarge
        case .secondary:
            return .secondaryLarge
        case .warning:
            return .warningLarge
        }
    }
}



struct BottomAlertButtonView: View {
    
    let buttons: [BottomAlertButton]
    
    var body: some View {
        AsyncStandardButtonGroup {
            buttonsView
        }
    }
    
    @ViewBuilder
    private var buttonsView: some View {
        BottomAlertButttonStack {
            ForEach(0..<buttons.count, id: \.self) { index in
                let button = buttons[index]
                AsyncStandardButton(
                    button.text,
                    style: button.standartStyle,
                    prepareAction: button.prepareAction,
                    action: button.action
                )
                .disabled(button.disable)
            }
        }
    }
}


extension BottomAlertButtonView {
    init(@ArrayBuilder<BottomAlertButton> buttons: () -> [BottomAlertButton]) {
        self.buttons = buttons()
    }
}

