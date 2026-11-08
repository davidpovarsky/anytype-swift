import Loc
import PinkhaKit
import SwiftUI

struct PinkhaDocumentSourcesPresentation: Equatable {
    static let compactAddVisualSize = CGSize(width: 22, height: 18)
    static let compactAddLayoutSize = CGSize(width: 22, height: 26)
    static let compactAddHitTargetSize = CGSize(width: 44, height: 44)
    static let compactAddHitTestingInsets = EdgeInsets(top: -9, leading: -11, bottom: -9, trailing: -11)

    let visibleAssociations: [TorahAssociationItem]
    let remainingAssociations: [TorahAssociationItem]
    let remainingCount: Int
    let canEdit: Bool

    var showsEmptyPlaceholderAdd: Bool {
        visibleAssociations.isEmpty && canEdit
    }

    var showsCompactAdjacentAdd: Bool {
        !visibleAssociations.isEmpty && canEdit
    }

    var showsOverflowMenu: Bool {
        remainingCount > 0
    }

    var hasAnyAddControl: Bool {
        showsEmptyPlaceholderAdd || showsCompactAdjacentAdd
    }

    init(associations: [TorahAssociationItem], canEdit: Bool = true) {
        visibleAssociations = Array(associations.prefix(2))
        remainingAssociations = Array(associations.dropFirst(2))
        remainingCount = associations.count - visibleAssociations.count
        self.canEdit = canEdit
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
            associations: session.documentPropertyProjection.sources,
            canEdit: session.canEditAssociations
        )

        if presentation.showsEmptyPlaceholderAdd {
            addSourceButton
        } else if !presentation.visibleAssociations.isEmpty {
            ForEach(presentation.visibleAssociations) { item in
                sourceChip(for: item)
            }

            if presentation.showsOverflowMenu {
                moreSourcesMenu(presentation: presentation)
            }

            if presentation.showsCompactAdjacentAdd {
                compactAddSourceButton
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
                    session.presentSearch(scope: .document, initialCategory: .references, host: .inspector)
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

    private var compactAddSourceButton: some View {
        Button {
            session.presentSearch(scope: .document, initialCategory: .references, host: .inspector)
        } label: {
            AnytypeText("+", style: .relation2Regular)
                .foregroundStyle(featuredChipStyle.fontColor)
                .lineLimit(1)
                .frame(
                    width: PinkhaDocumentSourcesPresentation.compactAddVisualSize.width,
                    height: PinkhaDocumentSourcesPresentation.compactAddVisualSize.height
                )
                .background(Color.Shape.tertiary)
                .clipShape(.rect(cornerRadius: 3))
                .padding(.vertical, 4)
                .contentShape(
                    Rectangle().inset(by: -11)
                )
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("torah-document-sources-add")
        .accessibilityLabel(Loc.add + " " + Loc.Pinkha.Torah.sources)
        .accessibilityValue("compact-icon")
        .accessibilityAddTraits(.isButton)
    }

    private var addSourceButton: some View {
        let title = "+ " + Loc.Pinkha.Torah.sources
        return Button {
            session.presentSearch(scope: .document, initialCategory: .references, host: .inspector)
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
        .accessibilityValue("placeholder")
        .accessibilityAddTraits(.isButton)
    }
}
