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

        TorahSearchViewShell(
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
        TorahSourceSearchResultRow(
            result: result,
            locale: locale,
            onSelect: result.scope == .references ? {
                Task { await presenter.openReference(result) }
            } : nil,
            primaryAccessibilityLabel: result.title(locale: locale),
            primaryAccessibilityHint: result.scope == .references
                ? Loc.Pinkha.Torah.openInspector
                : nil,
            onLink: {
                Task { await presenter.link(result) }
            },
            linkAccessibilityLabel: linkTitle
        )
    }

    private var linkTitle: String {
        TorahSourcesSearchCopy.linkTitle(blockId: presenter.associationTargetBlockID)
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

private struct TorahSearchViewShell<Content: View>: View {
    let title: String?
    let placeholder: String
    @Binding var searchText: String
    let searchFieldAccessibilityIdentifier: String
    private let content: Content
    @State private var searchFieldIsFocused = true

    init(
        title: String?,
        placeholder: String,
        searchText: Binding<String>,
        searchFieldAccessibilityIdentifier: String,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.placeholder = placeholder
        self._searchText = searchText
        self.searchFieldAccessibilityIdentifier = searchFieldAccessibilityIdentifier
        self.content = content()
    }

    var body: some View {
        VStack(spacing: 0) {
            DragIndicator()
            TitleView(title: title)
            SearchBar(
                text: $searchText,
                focused: searchFieldIsFocused,
                placeholder: placeholder
            )
            .accessibilityIdentifier(searchFieldAccessibilityIdentifier)
            content
        }
        .background(Color.Background.secondary)
        .onAppear { searchFieldIsFocused = true }
        .onDisappear { searchFieldIsFocused = false }
    }
}

private struct TorahSourceSearchResultRow: View {
    static let rowHeight: CGFloat = 68
    static let iconSlotSize: CGFloat = 48
    static let iconGlyphSize: CGFloat = 24

    let result: TorahEditorSession.SearchResult
    let locale: Locale
    let onSelect: (() -> Void)?
    let primaryAccessibilityLabel: String
    let primaryAccessibilityHint: String?
    let onLink: () -> Void
    let linkAccessibilityLabel: String

    var body: some View {
        HStack(alignment: .center, spacing: 0) {
            primaryContent
            linkButton
        }
        .frame(height: Self.rowHeight)
        .newDivider()
        .padding(.horizontal, 16)
    }

    @ViewBuilder
    private var primaryContent: some View {
        if let onSelect {
            Button(action: onSelect) {
                rowContent
            }
            .buttonStyle(.plain)
            .accessibilityLabel(primaryAccessibilityLabel)
            .accessibilityHint(primaryAccessibilityHint ?? "")
        } else {
            rowContent
                .accessibilityElement(children: .combine)
                .accessibilityLabel(primaryAccessibilityLabel)
        }
    }

    private var rowContent: some View {
        HStack(alignment: .center, spacing: 12) {
            Image(asset: asset)
                .renderingMode(.template)
                .resizable()
                .scaledToFit()
                .dynamicForegroundStyle(
                    color: Color.Control.secondary,
                    disabledColor: Color.Control.tertiary
                )
                .frame(width: Self.iconGlyphSize, height: Self.iconGlyphSize)
                .frame(width: Self.iconSlotSize, height: Self.iconSlotSize)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 1) {
                AnytypeText(result.title(locale: locale), style: .previewTitle2Medium)
                    .foregroundStyle(Color.Text.primary)
                    .lineLimit(1)
                    .frame(height: 20)

                if let subtitle = result.subtitle(locale: locale) {
                    AnytypeText(subtitle, style: .relation2Regular)
                        .foregroundStyle(Color.Text.secondary)
                        .lineLimit(1)
                }
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
    }

    private var linkButton: some View {
        Button(action: onLink) {
            Image(asset: .X24.linkToExistingObject)
                .renderingMode(.template)
                .frame(width: 20, height: 20)
                .foregroundStyle(Color.Control.secondary)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(linkAccessibilityLabel)
    }

    private var asset: ImageAsset {
        switch result.scope {
        case .references: .CustomIcons.book
        case .topics: .CustomIcons.pricetag
        case .words: .CustomIcons.text
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
