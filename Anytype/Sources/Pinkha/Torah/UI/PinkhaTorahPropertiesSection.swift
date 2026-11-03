import Loc
import PinkhaKit
import SwiftUI

struct PinkhaTorahPropertiesSection: View {
    let model: PinkhaTorahPropertiesModel

    var body: some View {
        if model.isEligible, let session = model.session {
            ForEach(TorahAssociationKind.allCases, id: \.self) { kind in
                PinkhaTorahPropertyRow(
                    kind: kind,
                    items: session.documentPropertyProjection[kind],
                    canEdit: model.canEdit,
                    onEdit: { model.edit(kind) }
                )
                .divider()
            }
        }
    }
}

struct PinkhaTorahPropertiesLoadingState: View {
    let model: PinkhaTorahPropertiesModel

    var body: some View {
        if let message = model.session?.message {
            EmptyStateView(
                title: Loc.Pinkha.Torah.title,
                subtitle: message,
                style: .error,
                buttonData: EmptyStateView.ButtonData(title: Loc.Pinkha.Home.retry) {
                    await model.reloadManifest()
                }
            )
        } else {
            ProgressView()
                .frame(maxWidth: .infinity)
                .padding(.vertical, 24)
        }
    }
}

struct PinkhaTorahPropertyRow: View {
    let kind: TorahAssociationKind
    let items: [TorahAssociationItem]
    let canEdit: Bool
    let onEdit: () -> Void
    @State private var size: CGSize = .zero
    @Environment(\.locale) private var locale

    private let style: PropertyStyle = .regular(allowMultiLine: false)

    private var title: String {
        Loc.Pinkha.Torah.propertyName(for: kind, locale: locale)
    }

    var body: some View {
        Button(action: onEdit) {
            HStack(spacing: 0) {
                AnytypeText(title, style: .relation1Regular)
                    .foregroundStyle(Color.Text.secondary)
                    .lineLimit(1)
                    .frame(width: size.width * 0.4, alignment: .leading)
                Spacer.fixedWidth(8)
                TagPropertyView(
                    tags: items.map { item in
                        Property.Tag.Option(
                            id: item.id,
                            text: TorahAssociationDisplayFormatter.label(for: item, locale: locale),
                            textColor: style.fontColor,
                            backgroundColor: Color.Shape.tertiary
                        )
                    },
                    hint: Loc.add,
                    style: style
                )
                Spacer(minLength: 8)
            }
            .frame(maxWidth: .infinity, minHeight: 48, alignment: .leading)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .readSize { size = $0 }
        .disabled(!canEdit)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(title)
        .accessibilityValue(items.map { TorahAssociationDisplayFormatter.label(for: $0, locale: locale) }.joined(separator: ", "))
        .accessibilityIdentifier("torah-property-\(kind.rawValue)")
    }
}
