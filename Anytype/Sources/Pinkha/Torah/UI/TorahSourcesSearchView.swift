import SwiftUI
import PinkhaKit

struct TorahSourcesSearchView: View {
    @Bindable var session: TorahEditorSession
    @Environment(\.locale) private var locale

    var body: some View {
        VStack(spacing: 0) {
            DragIndicator()
            TitleView(title: contextTitle) {
                closeButton
            }
            associationPreview
            scopePicker
            SearchBar(
                text: $session.searchQuery,
                focused: true,
                placeholder: Loc.Pinkha.Torah.searchPlaceholder,
                shouldShowDivider: false
            )
            .accessibilityIdentifier("torah-sources-search-field")
            results
        }
        .background(Color.Background.secondary)
        .task(id: SearchTaskID(scope: session.searchScope, query: session.searchQuery)) {
            await session.performSearch(debounce: .milliseconds(300))
        }
        .task(id: session.associationContext.id) { await session.refreshAssociations() }
    }

    private var closeButton: some View {
        Button {
            session.isSearchPresented = false
        } label: {
            Image(asset: .X24.close)
                .foregroundStyle(Color.Control.secondary)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Loc.close)
    }

    private var scopePicker: some View {
        Picker(Loc.Pinkha.Torah.searchType, selection: $session.searchScope) {
            ForEach(TorahEditorSession.SearchScope.allCases) { scope in
                Text(scope.title).tag(scope)
            }
        }
        .pickerStyle(.segmented)
        .padding(.horizontal, 16)
        .padding(.top, 8)
    }

    private var associationPreview: some View {
        VStack(alignment: .leading, spacing: 8) {
            ListSectionHeaderView(
                title: Loc.Pinkha.Torah.sources,
                increasedTopPadding: false,
                bottomPadding: 4
            )

            if session.currentAssociations.isEmpty {
                AnytypeText(
                    session.associationTargetBlockId == nil
                        ? Loc.Pinkha.Torah.noDocumentLinks
                        : Loc.Pinkha.Torah.noBlockLinks,
                    style: .caption1Regular
                )
                .foregroundStyle(Color.Text.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, 6)
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    LazyHStack(spacing: 8) {
                        ForEach(session.currentAssociations) { item in
                            associationCard(item)
                        }
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
        .padding(.bottom, 4)
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
        HStack(spacing: 8) {
            Group {
                if result.scope == .references {
                    Button {
                        Task { await session.openReference(result) }
                    } label: {
                        resultLabel(result)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(result.title(locale: locale))
                    .accessibilityHint(Loc.Pinkha.Torah.openInspector)
                } else {
                    resultLabel(result)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Button {
                Task { await session.link(result) }
            } label: {
                HStack(spacing: 5) {
                    Image(asset: .X24.linkToExistingObject)
                        .renderingMode(.template)
                        .frame(width: 20, height: 20)
                    AnytypeText(linkTitle, style: .caption1Medium)
                }
                .foregroundStyle(Color.Control.secondary)
                .frame(minHeight: 44)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 8)
        .frame(minHeight: 64)
        .divider(spacing: 0)
    }

    private func resultLabel(_ result: TorahEditorSession.SearchResult) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            AnytypeText(result.title(locale: locale), style: .bodySemibold)
                .foregroundStyle(Color.Text.primary)
            if let subtitle = result.subtitle(locale: locale), !subtitle.isEmpty {
                AnytypeText(subtitle, style: .caption1Regular)
                    .foregroundStyle(Color.Text.secondary)
                    .lineLimit(2)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
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

private struct SearchTaskID: Equatable, Hashable {
    let scope: TorahEditorSession.SearchScope
    let query: String
}
