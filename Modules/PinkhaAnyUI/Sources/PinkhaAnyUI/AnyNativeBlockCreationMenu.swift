#if canImport(UIKit) && canImport(SwiftUI)
import SwiftUI
import UIKit

/// One catalog for the existing document and per-block native menu surfaces.
@MainActor
struct AnyNativeBlockCreationMenu: View {
    let presentation: AnyDocumentPresentation

    var body: some View {
        Menu {
            ForEach(AnyNativeTextBlockKind.allCases, id: \.self) { kind in
                Button(kind.title, systemImage: kind.systemImage) {
                    Task { await presentation.addTextBlock(kind) }
                }
                .accessibilityIdentifier("any-native-add-block-" + kind.rawValue)
            }
        } label: {
            Label(AnyUIErrorText.text("הוספת בלוק", "Add block"), systemImage: "plus")
        }
        .accessibilityIdentifier("any-native-add-block-menu")
        .disabled(!presentation.canMutate)
    }

    static func before(_ blockID: String, presentation: AnyDocumentPresentation) -> UIMenu {
        UIMenu(title: AnyUIErrorText.text("הוספת בלוק לפני", "Add block before"),
               image: UIImage(systemName: "plus"),
               identifier: UIMenu.Identifier("any-native-add-block-before-" + blockID),
               children: AnyNativeTextBlockKind.allCases.map { kind in
            UIAction(title: kind.title, image: UIImage(systemName: kind.systemImage),
                     identifier: UIAction.Identifier("any-native-add-block-" + kind.rawValue),
                     attributes: presentation.canMutate ? [] : [.disabled]) { [weak presentation] _ in
                Task { await presentation?.addTextBlock(kind, before: blockID) }
            }
        })
    }
}

@MainActor
private extension AnyNativeTextBlockKind {
    var title: String {
        switch self {
        case .paragraph: return AnyUIErrorText.text("טקסט", "Text")
        case .heading1: return AnyUIErrorText.text("כותרת 1", "Heading 1")
        case .heading2: return AnyUIErrorText.text("כותרת 2", "Heading 2")
        case .heading3: return AnyUIErrorText.text("כותרת 3", "Heading 3")
        case .bulletedList: return AnyUIErrorText.text("רשימה עם תבליטים", "Bulleted list")
        case .numberedList: return AnyUIErrorText.text("רשימה ממוספרת", "Numbered list")
        case .checklist: return AnyUIErrorText.text("רשימת משימות", "Checklist")
        case .quote: return AnyUIErrorText.text("ציטוט", "Quote")
        case .code: return AnyUIErrorText.text("קוד", "Code")
        }
    }

    var systemImage: String {
        switch self {
        case .paragraph: return "text.alignleading"
        case .heading1, .heading2, .heading3: return "textformat.size"
        case .bulletedList: return "list.bullet"
        case .numberedList: return "list.number"
        case .checklist: return "checklist"
        case .quote: return "text.quote"
        case .code: return "chevron.left.forwardslash.chevron.right"
        }
    }
}
#endif
