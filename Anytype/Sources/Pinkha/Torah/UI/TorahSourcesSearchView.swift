import SwiftUI
import UIKit
import PinkhaKit
import TorahInspectorUI

struct TorahSourcesSearchView: View {
    let session: TorahEditorSession
    @State private var presenter: TorahSourcesSearchPresenter

    init(session: TorahEditorSession) {
        self.session = session
        _presenter = State(initialValue: TorahSourcesSearchPresenter(
            session: session,
            context: session.associationContext,
            searchScope: session.searchScope,
            searchQuery: session.searchQuery,
            onOpenSelection: session.openResolvedReferenceFromStandaloneSearch
        ))
    }

    var body: some View {
        @Bindable var presenter = presenter

        SearchViewShell(
            title: TorahSourcesSearchCopy.contextTitle(
                blockId: presenter.associationTargetBlockID
            ),
            placeholder: Loc.Pinkha.Torah.searchPlaceholder,
            searchText: $presenter.searchQuery,
            searchFieldAccessibilityIdentifier: "torah-sources-search-field"
        ) {
            TorahSourcesSearchContentView(
                presenter: presenter,
                showsSearchBar: false,
                accessibilityIdentifier: "torah-sources-search-standalone"
            )
        }
        .accessibilityIdentifier("torah-sources-search-sheet")
    }
}

struct TorahInspectorEmbeddedSearchView: View {
    @State private var presenter: TorahSourcesSearchPresenter

    init(
        session: TorahEditorSession,
        navigation: TorahInspectorSearchNavigation
    ) {
        _presenter = State(initialValue: TorahSourcesSearchPresenter(
            session: session,
            context: session.documentAssociationContext,
            onOpenSelection: navigation.navigateToFullSource
        ))
    }

    var body: some View {
        TorahSourcesSearchContentView(
            presenter: presenter,
            showsSearchBar: true,
            accessibilityIdentifier: "torah-sources-search-embedded"
        )
    }
}

struct TorahSourcesSearchContentView: View {
    @Bindable var presenter: TorahSourcesSearchPresenter
    let showsSearchBar: Bool
    let accessibilityIdentifier: String
    @State private var searchFieldIsFocused = true
    @Environment(\.locale) private var locale

    var body: some View {
        VStack(spacing: 0) {
            if showsSearchBar {
                SearchBar(
                    text: $presenter.searchQuery,
                    focused: searchFieldIsFocused,
                    placeholder: Loc.Pinkha.Torah.searchPlaceholder
                )
                .accessibilityIdentifier("torah-sources-search-field")
            }
            scopePicker
            if TorahAssociationPreviewStrip.shouldShow(
                items: presenter.associations,
                persistenceState: presenter.persistenceState
            ) {
                associationPreview
            }
            results
        }
        .background(Color.Background.secondary)
        .accessibilityIdentifier(accessibilityIdentifier)
        .onChange(of: presenter.persistenceState) { _, state in
            guard state == .saved else { return }
            UIAccessibility.post(
                notification: .announcement,
                argument: Loc.Pinkha.Torah.Persistence.saved
            )
        }
        .task(id: SearchTaskID(scope: presenter.searchScope, query: presenter.searchQuery)) {
            await presenter.performSearch(debounce: .milliseconds(300))
        }
        .task(id: presenter.context.id) { await presenter.refreshAssociations() }
        .onAppear {
            if showsSearchBar { searchFieldIsFocused = true }
        }
        .onDisappear {
            searchFieldIsFocused = false
            presenter.cancelPendingRequests()
        }
    }

    private var scopePicker: some View {
        Picker(Loc.Pinkha.Torah.searchType, selection: $presenter.searchScope) {
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
        TorahAssociationPreviewStrip(
            items: presenter.associations,
            persistenceState: presenter.persistenceState,
            locale: locale,
            canOpen: presenter.canOpenAssociation,
            onOpen: presenter.openAssociation,
            onUnlink: { item in
                Task { await presenter.unlinkAssociation(item) }
            }
        )
        .divider()
    }

    @ViewBuilder
    private var results: some View {
        switch presenter.searchState {
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
                title: presenter.searchScope == .words
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
                    action: { await presenter.performSearch() }
                )
            )
            .accessibilityIdentifier("torah-search-error")
        case .results(let values):
            PlainList {
                ForEach(values) { result in
                    resultRow(result)
                        .id(result.id)
                }
            }
            .scrollIndicators(.never)
            .scrollPosition(id: $presenter.resultListScrollAnchor)
            .id(SearchTaskID(scope: presenter.searchScope, query: presenter.searchQuery))
        }
    }

    private func resultRow(_ result: TorahEditorSession.SearchResult) -> some View {
        SearchCell(
            data: TorahSearchCellData(result: result, locale: locale),
            onSelect: result.scope == .references ? {
                Task { await presenter.openReference(result) }
            } : nil,
            assetGlyphSize: SearchCellIconView.standardAssetGlyphSize,
            primaryAccessibilityLabel: result.title(locale: locale),
            primaryAccessibilityHint: result.scope == .references
                ? Loc.Pinkha.Torah.openInspector
                : nil
        ) {
            Button {
                Task { await presenter.link(result) }
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
        TorahSourcesSearchCopy.linkTitle(blockId: presenter.associationTargetBlockID)
    }
}

struct TorahSearchCellData: SearchDataProtocol {
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

struct TorahAssociationPreviewStrip: View {
    static let height: CGFloat = 48

    let items: [TorahAssociationItem]
    let persistenceState: TorahAssociationPersistenceState?
    let locale: Locale
    let canOpen: (TorahAssociationItem) -> Bool
    let onOpen: (TorahAssociationItem) -> Void
    let onUnlink: (TorahAssociationItem) -> Void

    static func shouldShow(
        items: [TorahAssociationItem],
        persistenceState: TorahAssociationPersistenceState?
    ) -> Bool {
        items.isNotEmpty || visiblePersistenceLabel(persistenceState) != nil
    }

    var body: some View {
        ScrollView(.horizontal) {
            LazyHStack(spacing: 8) {
                if items.isNotEmpty {
                    AnytypeText(Loc.Pinkha.Torah.sources, style: .caption1Regular)
                        .foregroundStyle(Color.Text.secondary)
                        .fixedSize(horizontal: true, vertical: false)
                }

                if let statusLabel = Self.visiblePersistenceLabel(persistenceState) {
                    persistenceStatus(statusLabel)
                }

                ForEach(items) { item in
                    associationCard(item)
                }
            }
            .frame(height: 44)
            .padding(.horizontal, 16)
        }
        .scrollIndicators(.hidden)
        .frame(height: Self.height)
        .accessibilityIdentifier("torah-existing-associations-strip")
    }

    private func persistenceStatus(_ label: String) -> some View {
        HStack(spacing: 6) {
            if persistenceState == .waiting || persistenceState == .saving {
                ProgressView()
                    .controlSize(.small)
                    .accessibilityHidden(true)
            }
            AnytypeText(label, style: .caption1Regular)
                .foregroundStyle(Color.Text.secondary)
                .lineLimit(1)
                .fixedSize(horizontal: true, vertical: false)
        }
        .accessibilityElement(children: .combine)
    }

    private func associationCard(_ item: TorahAssociationItem) -> some View {
        let label = displayLabel(item)
        return HStack(spacing: 4) {
            Button {
                onOpen(item)
            } label: {
                HStack(spacing: 6) {
                    Image(asset: kindAsset(item.kind))
                        .renderingMode(.template)
                        .resizable()
                        .scaledToFit()
                        .frame(width: 18, height: 18)
                        .foregroundStyle(Color.Control.secondary)
                        .accessibilityHidden(true)
                    AnytypeText(label, style: .caption1Medium)
                        .foregroundStyle(Color.Text.primary)
                        .lineLimit(1)
                }
                .padding(.leading, 10)
                .padding(.vertical, 8)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(!canOpen(item))
            .environment(
                \.layoutDirection,
                TorahAssociationDisplayFormatter.containsHebrew(label)
                    ? .rightToLeft
                    : .leftToRight
            )

            Button {
                onUnlink(item)
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
        .frame(height: 44)
        .background(Color.Shape.transparentSecondary)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    static func visiblePersistenceLabel(
        _ state: TorahAssociationPersistenceState?
    ) -> String? {
        guard let state else { return nil }
        switch state {
        case .waiting: return Loc.Pinkha.Torah.Persistence.waiting
        case .saving: return Loc.Pinkha.Torah.Persistence.saving
        case .saved: return nil
        case .conflict(let message):
            return message.isEmpty ? Loc.Pinkha.Torah.Persistence.conflict : message
        case .uncertain(let message):
            return message.isEmpty ? Loc.Pinkha.Torah.Persistence.uncertain : message
        case .error(let message):
            return message.isEmpty ? Loc.Pinkha.Torah.Persistence.error : message
        }
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

enum TorahSourcesSearchCopy {
    static func contextTitle(blockId: String?) -> String {
        blockId == nil ? Loc.Pinkha.Torah.documentLinks : Loc.Pinkha.Torah.blockLinks
    }

    static func linkTitle(blockId: String?) -> String {
        blockId == nil ? Loc.Pinkha.Torah.linkToDocument : Loc.Pinkha.Torah.linkToBlock
    }
}

private struct SearchTaskID: Equatable, Hashable {
    let scope: TorahEditorSession.SearchScope
    let query: String
}
