import Loc
import PinkhaKit
import SwiftUI

struct PinkhaDocumentSourcesPresentation {
    let visibleAssociations: [TorahAssociationItem]
    let remainingCount: Int

    init(associations: [TorahAssociationItem]) {
        visibleAssociations = Array(associations.prefix(2))
        remainingCount = associations.count - visibleAssociations.count
    }
}

struct PinkhaDocumentSourcesFeaturedContent: View {
    let session: TorahEditorSession
    @Environment(\.locale) private var locale

    private let featuredChipStyle: PropertyStyle = .featuredBlock(
        FeaturedPropertySettings(allowMultiLine: false)
    )

    var body: some View {
        let presentation = PinkhaDocumentSourcesPresentation(
            associations: session.visibleDocumentAssociations
        )

        ForEach(presentation.visibleAssociations) { item in
            HStack(spacing: FeaturedPropertiesConstants.itemSpacing) {
                sourceChip(for: item)
                divider
            }
        }

        if presentation.remainingCount > 0 {
            HStack(spacing: FeaturedPropertiesConstants.itemSpacing) {
                moreSourcesChip(count: presentation.remainingCount)
                divider
            }
        }

        addSourceButton
    }

    private func sourceChip(for item: TorahAssociationItem) -> some View {
        let label = TorahAssociationDisplayFormatter.label(for: item, locale: locale)
        return Button {
            session.openDocumentAssociation(item)
        } label: {
            TagView(
                config: TagView.Config(
                    text: label,
                    textColor: featuredChipStyle.fontColor,
                    backgroundColor: Color.Shape.tertiary,
                    textFont: featuredChipStyle.font,
                    guidlines: featuredChipStyle.tagViewGuidlines
                )
            )
            .frame(minWidth: 44, minHeight: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("torah-document-source-chip-\(item.id)")
        .accessibilityLabel(label)
    }

    private func moreSourcesChip(count: Int) -> some View {
        Button {
            session.presentSearch(scope: .document)
        } label: {
            AnytypeText("+\(count)", style: .relation2Regular)
                .foregroundStyle(Color.Text.secondary)
                .lineLimit(1)
                .frame(width: 24, height: 18)
                .background(Color.Shape.tertiary)
                .clipShape(.rect(cornerRadius: 3))
                .frame(minWidth: 44, minHeight: 44)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("torah-document-sources-more")
        .accessibilityLabel("\(count) " + Loc.Pinkha.Torah.sources)
    }

    private var addSourceButton: some View {
        let title = Loc.Pinkha.Torah.sources + " +"
        return Button {
            session.presentSearch(scope: .document)
        } label: {
            TagView(
                config: TagView.Config(
                    text: title,
                    textColor: featuredChipStyle.fontColor,
                    backgroundColor: Color.Shape.tertiary,
                    textFont: featuredChipStyle.font,
                    guidlines: featuredChipStyle.tagViewGuidlines
                )
            )
            .frame(minWidth: 44, minHeight: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("torah-document-sources-add")
        .accessibilityLabel(Loc.add + " " + Loc.Pinkha.Torah.sources)
    }

    private var divider: some View {
        Circle()
            .fill(Color.Text.secondary)
            .frame(width: 3, height: 3)
    }
}
