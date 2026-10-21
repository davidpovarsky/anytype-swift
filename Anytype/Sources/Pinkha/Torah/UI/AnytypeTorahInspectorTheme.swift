import SwiftUI
import TorahInspectorUI

extension TorahInspectorTheme {
    @MainActor
    static let anytype = TorahInspectorTheme(
        primaryText: Color.Text.primary,
        secondaryText: Color.Text.secondary,
        accent: Color.Control.accent100,
        background: Color.Background.primary,
        elevatedSurface: Color.Background.secondary,
        divider: Color.Shape.secondary
    ) { value, role in
        let style: AnytypeFont = switch role {
        case .heading: .uxTitle2Semibold
        case .body: .bodyRegular
        case .sourceBody: .uxBodyRegular
        case .caption: .caption1Regular
        case .button: .bodySemibold
        }
        return AnyView(AnytypeText(value, style: style))
    }
}
