import SwiftUI
import AnytypeCore
import Services

struct SearchCell<SearchData: SearchDataProtocol, TrailingContent: View>: View {
    
    let data: SearchData
    private let onSelect: (() -> Void)?
    private let primaryAccessibilityLabel: String?
    private let primaryAccessibilityHint: String?
    private let trailingContent: TrailingContent

    init(data: SearchData) where TrailingContent == EmptyView {
        self.data = data
        self.onSelect = nil
        self.primaryAccessibilityLabel = nil
        self.primaryAccessibilityHint = nil
        self.trailingContent = EmptyView()
    }

    init(
        data: SearchData,
        onSelect: (() -> Void)?,
        primaryAccessibilityLabel: String? = nil,
        primaryAccessibilityHint: String? = nil,
        @ViewBuilder trailingContent: () -> TrailingContent
    ) {
        self.data = data
        self.onSelect = onSelect
        self.primaryAccessibilityLabel = primaryAccessibilityLabel
        self.primaryAccessibilityHint = primaryAccessibilityHint
        self.trailingContent = trailingContent()
    }

    var body: some View {
        HStack(alignment: .center, spacing: 0) {
            primaryContent
            trailingContent
        }
        .frame(height: data.isMinimal ? 52 : 68)
        .newDivider()
        .padding(.horizontal, 16)
    }

    @ViewBuilder
    private var primaryContent: some View {
        if let onSelect {
            Button(action: onSelect) {
                cellContent
            }
            .buttonStyle(.plain)
            .accessibilityLabel(primaryAccessibilityLabel ?? data.title)
            .accessibilityHint(primaryAccessibilityHint ?? "")
        } else {
            cellContent
        }
    }

    private var cellContent: some View {
        HStack(alignment: .center, spacing: 0) {
            icon
            content
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
    }
    
    @ViewBuilder
    private var icon: some View {
        if let iconImage = data.iconImage {
            if data.isMinimal {
                IconView(icon: iconImage)
                    .frame(width: 24, height: 24)
                    .allowsHitTesting(false)
                Spacer.fixedWidth(10)
            } else {
                IconView(icon: iconImage)
                    .frame(width: 48, height: 48)
                    .allowsHitTesting(false)
                Spacer.fixedWidth( 12)
            }
        }
    }
    
    private var content: some View {
        VStack(alignment: .leading, spacing: 0) {
            Spacer()
            
            AnytypeText(data.title, style: data.isMinimal ? .uxBodyRegular : .previewTitle2Medium)
                .foregroundStyle(Color.Text.primary)
                .lineLimit(1)
                .frame(height: 20)
            
            switch data.mode {
            case .full(let descriptionInfo, let callout):
                if let descriptionInfo {
                    Spacer.fixedHeight(1)
                    AnytypeText(descriptionInfo.description, style: descriptionInfo.descriptionFont)
                        .foregroundStyle(Color(descriptionInfo.descriptionTextColor))
                        .lineLimit(1)
                }
                
                if let callout {
                    Spacer.fixedHeight(2)
                    AnytypeText(callout, style: .relation2Regular)
                    .foregroundStyle(Color.Text.secondary)
                    .lineLimit(1)
                }
            case .minimal:
                EmptyView()
            }
            
            Spacer()
        }
    }
    
}
