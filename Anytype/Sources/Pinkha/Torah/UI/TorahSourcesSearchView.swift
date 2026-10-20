import SwiftUI
import PinkhaKit

struct TorahSourcesSearchView: View {
    @Bindable var session: TorahEditorSession
    @Environment(\.locale) private var locale

    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                associationPreview

                Picker(Loc.Pinkha.Torah.searchType, selection: $session.searchScope) {
                    ForEach(TorahEditorSession.SearchScope.allCases) { scope in
                        Text(scope.title).tag(scope)
                    }
                }
                .pickerStyle(.segmented)

                TextField(Loc.Pinkha.Torah.searchPlaceholder, text: $session.searchQuery)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("torah-sources-search-field")

                results
            }
            .padding(16)
            .navigationTitle(contextTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(Loc.close) { session.isSearchPresented = false }
                }
            }
        }
        .frame(idealWidth: 460, idealHeight: 640)
        .task(id: SearchTaskID(scope: session.searchScope, query: session.searchQuery)) {
            do {
                try await Task.sleep(for: .milliseconds(300))
                await session.performSearch()
            } catch {
            }
        }
        .task(id: session.associationContext.id) { await session.refreshAssociations() }
    }

    private var associationPreview: some View {
        GroupBox {
            if session.currentAssociations.isEmpty {
                Text(session.associationTargetBlockId == nil
                     ? Loc.Pinkha.Torah.noDocumentLinks
                     : Loc.Pinkha.Torah.noBlockLinks)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                ScrollView(.horizontal) {
                    HStack {
                        ForEach(session.currentAssociations) { item in
                            HStack(spacing: 6) {
                                Image(systemName: kindSymbol(item.kind))
                                    .foregroundStyle(.secondary)
                                    .accessibilityHidden(true)
                                Button(displayLabel(item)) {
                                    session.openAssociation(item)
                                }
                                .buttonStyle(.plain)
                                .lineLimit(1)
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
                                    Image(systemName: "xmark.circle.fill")
                                }
                                .buttonStyle(.plain)
                                .accessibilityLabel(Loc.Pinkha.Torah.removeLink)
                            }
                            .font(.caption)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(.secondary.opacity(0.12), in: Capsule())
                        }
                    }
                }
            }

            if let persistenceState = session.persistenceState {
                Text(persistenceLabel(persistenceState))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        } label: {
            Label(
                contextTitle,
                systemImage: "link"
            )
        }
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
        if session.isSearching {
            ProgressView(Loc.Pinkha.Torah.searching)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if session.searchResults.isEmpty {
            ContentUnavailableView(
                Loc.Pinkha.Torah.searchPrompt,
                systemImage: "text.book.closed",
                description: Text(Loc.Pinkha.Torah.searchDescription)
            )
        } else {
            List(session.searchResults) { result in
                VStack(alignment: .leading, spacing: 6) {
                    Text(result.title(locale: locale))
                        .font(.body.weight(.medium))
                    if let subtitle = result.subtitle(locale: locale), !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    HStack {
                        if result.scope == .references {
                            Button(Loc.Pinkha.Torah.openInspector) {
                                Task { await session.openReference(result) }
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        Button(session.associationTargetBlockId == nil
                               ? Loc.Pinkha.Torah.linkToDocument
                               : Loc.Pinkha.Torah.linkToBlock) {
                            Task { await session.link(result) }
                        }
                        .buttonStyle(.bordered)
                    }
                    .controlSize(.small)
                }
                .padding(.vertical, 4)
            }
            .listStyle(.plain)
        }
    }

    private var contextTitle: String {
        session.associationTargetBlockId == nil
            ? Loc.Pinkha.Torah.documentLinks
            : Loc.Pinkha.Torah.blockLinks
    }

    private func displayLabel(_ item: TorahAssociationItem) -> String {
        TorahAssociationDisplayFormatter.label(for: item, locale: locale)
    }

    private func kindSymbol(_ kind: TorahAssociationKind) -> String {
        switch kind {
        case .ref: "book.pages"
        case .topic: "tag"
        case .word: "textformat"
        }
    }
}

private struct SearchTaskID: Equatable {
    let scope: TorahEditorSession.SearchScope
    let query: String
}
