import SwiftUI
import PinkhaKit

struct TorahSourcesSearchView: View {
    @Bindable var session: TorahEditorSession
    @Environment(\.locale) private var locale

    var body: some View {
        SearchViewShell(
            title: contextTitle,
            placeholder: Loc.Pinkha.Torah.searchPlaceholder,
            searchText: $session.searchQuery,
            searchFieldAccessibilityIdentifier: "torah-sources-search-field"
        ) {
            scopePicker
            if !session.currentAssociations.isEmpty || session.persistenceState != nil {
                associationPreview
            }
            results
        }
        .accessibilityIdentifier("torah-sources-search-sheet")
        .task(id: SearchTaskID(scope: session.searchScope, query: session.searchQuery)) {
            await session.performSearch(debounce: .milliseconds(300))
        }
        .task(id: session.associationContext.id) { await session.refreshAssociations() }
    }

    private var scopePicker: some View {
        Picker(Loc.Pinkha.Torah.searchType, selection: $session.searchScope) {
            ForEach(TorahEditorSession.SearchScope.allCases) { scope in
                Text(scope.title).tag(scope)
            }
        }
        .pickerStyle(.segmented)
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .divider()
    }

    private var associationPreview: some View {
        VStack(alignment: .leading, spacing: 8) {
            ListSectionHeaderView(
                title: Loc.Pinkha.Torah.sources,
                increasedTopPadding: false,
                bottomPadding: 4
            )

            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(spacing: 8) {
                    ForEach(session.currentAssociations) { item in
                        associationCard(item)
                    }
                }
            }

            if let persistenceState = session.persistenceState {
                AnytypeText(persistenceLabel(persistenceState), style: .caption1Regular)
                    .foregroundStyle(Color.Text.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 8)
        .divider()
    }

    private func associationCard(_ item: TorahAssociationItem) -> some View {
        HStack(spacing: 4) {
            Button {
                session.openAssociation(item)
            } label: {
                HStack(spacing: 6) {
                    Image(asset: kindAsset(item.kind))
                        .resizable()
                        .renderingMode(.template)
                        .frame(width: 18, height: 18)
                        .foregroundStyle(Color.Control.secondary)
                        .accessibilityHidden(true)
                    AnytypeText(displayLabel(item), style: .caption1Medium)
                        .foregroundStyle(Color.Text.primary)
                        .lineLimit(1)
                }
                .padding(.leading, 10)
                .padding(.vertical, 8)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(!session.canOpenAssociation(item))
            .environment(
                \.layoutDirection,
                TorahAssociationDisplayFormatter.containsHebrew(displayLabel(item))
                    ? .rightToLeft
                    : .leftToRight
            )

            Button {
                Task { await session.unlinkAssociation(item) }
            } label: {
                Image(asset: .multiplyCircleFill)
                    .renderingMode(.template)
                    .foregroundStyle(Color.Control.secondary)
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(Loc.Pinkha.Torah.removeLink)
        }
        .background(Color.Shape.transparentSecondary)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    private func persistenceLabel(_ state: TorahAssociationPersistenceState) -> String {
        switch state {
        case .waiting: Loc.Pinkha.Torah.Persistence.waiting
        case .saving: Loc.Pinkha.Torah.Persistence.saving
        case .saved: Loc.Pinkha.Torah.Persistence.saved
        case .conflict: Loc.Pinkha.Torah.Persistence.conflict
        case .uncertain: Loc.Pinkha.Torah.Persistence.uncertain
        case .error: Loc.Pinkha.Torah.Persistence.error
        }
    }

    @ViewBuilder
    private var results: some View {
        switch session.searchState {
        case .idle:
            EmptyStateView(
                title: Loc.Pinkha.Torah.searchPrompt,
                subtitle: Loc.Pinkha.Torah.searchDescription,
                style: .plain
            )
        case .loading:
            ProgressView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .accessibilityLabel(Loc.Pinkha.Torah.searching)
        case .empty:
            EmptyStateView(
                title: session.searchScope == .words
                    ? Loc.Pinkha.Torah.Error.noResolvedWord
                    : Loc.Pinkha.Torah.searchDescription,
                style: .plain
            )
            .accessibilityIdentifier("torah-search-empty")
        case .error(let message):
            EmptyStateView(
                title: Loc.Pinkha.Torah.title,
                subtitle: message,
                style: .error,
                buttonData: EmptyStateView.ButtonData(
                    title: Loc.Pinkha.Home.retry,
                    action: { await session.performSearch() }
                )
            )
            .accessibilityIdentifier("torah-search-error")
        case .results(let values):
            PlainList {
                ForEach(values) { result in
                    resultRow(result)
                }
            }
            .scrollIndicators(.never)
            .id(SearchTaskID(scope: session.searchScope, query: session.searchQuery))
        }
    }

    private func resultRow(_ result: TorahEditorSession.SearchResult) -> some View {
        SearchCell(
            data: TorahSearchCellData(result: result, locale: locale),
            onSelect: result.scope == .references ? {
                Task { await session.openReference(result) }
            } : nil,
            primaryAccessibilityLabel: result.title(locale: locale),
            primaryAccessibilityHint: result.scope == .references
                ? Loc.Pinkha.Torah.openInspector
                : nil
        ) {
            Button {
                Task { await session.link(result) }
            } label: {
                Image(asset: .X24.linkToExistingObject)
                    .renderingMode(.template)
                    .frame(width: 20, height: 20)
                .foregroundStyle(Color.Control.secondary)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(linkTitle)
        }
    }

    private var linkTitle: String {
        session.associationTargetBlockId == nil
            ? Loc.Pinkha.Torah.linkToDocument
            : Loc.Pinkha.Torah.linkToBlock
    }

    private var contextTitle: String {
        session.associationTargetBlockId == nil
            ? Loc.Pinkha.Torah.documentLinks
            : Loc.Pinkha.Torah.blockLinks
    }

    private func displayLabel(_ item: TorahAssociationItem) -> String {
        TorahAssociationDisplayFormatter.label(for: item, locale: locale)
    }

    private func kindAsset(_ kind: TorahAssociationKind) -> ImageAsset {
        switch kind {
        case .ref: .CustomIcons.book
        case .topic: .CustomIcons.pricetag
        case .word: .CustomIcons.text
        }
    }
}

private struct TorahSearchCellData: SearchDataProtocol {
    let id: String
    let iconImage: Icon?
    let title: String
    let mode: SerchDataPresentationMode

    init(result: TorahEditorSession.SearchResult, locale: Locale) {
        self.id = result.id
        self.iconImage = .asset(Self.asset(for: result.scope))
        self.title = result.title(locale: locale)
        self.mode = .full(
            descriptionInfo: result.subtitle(locale: locale).map {
                SearchDataDescriptionInfo(
                    description: $0,
                    descriptionTextColor: Color.Text.secondary,
                    descriptionFont: .relation2Regular
                )
            },
            callout: nil
        )
    }

    private static func asset(for scope: TorahEditorSession.SearchScope) -> ImageAsset {
        switch scope {
        case .references: .CustomIcons.book
        case .topics: .CustomIcons.pricetag
        case .words: .CustomIcons.text
        }
    }
}

private struct SearchTaskID: Equatable, Hashable {
    let scope: TorahEditorSession.SearchScope
    let query: String
}
