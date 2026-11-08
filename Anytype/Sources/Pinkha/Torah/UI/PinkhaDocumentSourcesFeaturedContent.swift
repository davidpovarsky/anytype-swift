import Loc
import PinkhaKit
import SwiftUI

struct PinkhaDocumentSourcesPresentation {
    let visibleAssociations: [TorahAssociationItem]
    let remainingAssociations: [TorahAssociationItem]
    let remainingCount: Int

    init(associations: [TorahAssociationItem]) {
        visibleAssociations = Array(associations.prefix(2))
        remainingAssociations = Array(associations.dropFirst(2))
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
            associations: session.documentPropertyProjection.sources
        )

        if presentation.visibleAssociations.isEmpty {
            if session.canEditAssociations {
                addSourceButton
            }
        } else {
            ForEach(presentation.visibleAssociations) { item in
                sourceChip(for: item)
            }

            if presentation.remainingCount > 0 {
                moreSourcesMenu(presentation: presentation)
            }
        }
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
            .padding(.vertical, 4)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .contextMenu {
            Button {
                session.openDocumentAssociation(item)
            } label: {
                Label(label, systemImage: "book")
            }
            if session.canEditAssociations {
                Button {
                    session.presentSearch(scope: .document)
                } label: {
                    Label(
                        TorahAssociationDisplayFormatter.prefersHebrew(locale) ? "הוסף מקור" : "Add source",
                        systemImage: "plus"
                    )
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("torah-document-source-chip-\(item.id)")
        .accessibilityLabel(label)
        .accessibilityAddTraits(.isButton)
    }

    private func moreSourcesMenu(presentation: PinkhaDocumentSourcesPresentation) -> some View {
        Menu {
            ForEach(presentation.remainingAssociations) { item in
                Button {
                    session.openDocumentAssociation(item)
                } label: {
                    Text(TorahAssociationDisplayFormatter.label(for: item, locale: locale))
                }
            }
        } label: {
            moreSourcesChip(count: presentation.remainingCount)
                .padding(.vertical, 4)
                .contentShape(Rectangle())
        }
        .accessibilityIdentifier("torah-document-sources-more")
        .accessibilityLabel("\(presentation.remainingCount) " + Loc.Pinkha.Torah.sources)
    }

    private func moreSourcesChip(count: Int) -> some View {
        AnytypeText("+\(count)", style: .relation2Regular)
            .foregroundStyle(Color.Text.secondary)
            .lineLimit(1)
            .frame(width: 24, height: 18)
            .background(Color.Shape.tertiary)
            .clipShape(.rect(cornerRadius: 3))
            .contentShape(Rectangle())
    }

    private var addSourceButton: some View {
        let title = "+ " + Loc.Pinkha.Torah.sources
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
            .padding(.vertical, 4)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("torah-document-sources-add")
        .accessibilityLabel(Loc.add + " " + Loc.Pinkha.Torah.sources)
        .accessibilityAddTraits(.isButton)
    }
}
