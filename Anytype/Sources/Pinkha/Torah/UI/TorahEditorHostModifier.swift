import SwiftUI
import TorahInspectorUI

struct TorahEditorHostModifier: ViewModifier {
    let session: TorahEditorSession?
    @Environment(\.locale) private var locale

    @ViewBuilder
    func body(content: Content) -> some View {
        if let session {
            @Bindable var session = session

            content
                .sheet(
                    isPresented: $session.isSearchPresented,
                    onDismiss: session.searchDidDismiss
                ) {
                    TorahSourcesSearchView(session: session)
                }
                .torahInspectorSheet(
                    selection: $session.selection,
                    repository: session.repository,
                    entryMode: session.inspectorEntryMode,
                    selectedTool: $session.selectedTool,
                    selectedDetent: $session.selectedDetent,
                    configuration: TorahInspectorConfiguration(
                        availableTools: [.commentaries, .links, .relatedDocuments],
                        allowsInlineFullSourceNavigation: true,
                        theme: .anytype
                    ),
                    actions: inspectorActions(for: session)
                )
                .alert(
                    Loc.Pinkha.Torah.title,
                    isPresented: Binding(
                        get: { session.message != nil },
                        set: { if !$0 { session.message = nil } }
                    )
                ) {
                    Button(Loc.ok) { session.message = nil }
                } message: {
                    Text(session.message ?? "")
                }
                .task(id: session.objectId) {
                    session.activateDocument()
                    session.updateEffectiveLocale(locale)
                    await session.refreshAssociationSnapshot()
                }
                .onAppear { session.activateDocument() }
                .onDisappear { session.deactivateDocument() }
                .onChange(of: locale.identifier) {
                    session.updateEffectiveLocale(locale)
                }
                .onChange(of: session.selection?.id) { _, selectionID in
                    guard selectionID == nil else { return }
                    Task { await session.refreshAssociationSnapshot() }
                }
        } else {
            content
        }
    }

    private func inspectorActions(for session: TorahEditorSession) -> TorahInspectorHostActions {
        var actions = session.hostActions
        actions.search = TorahInspectorSearchCapability { navigation in
            TorahInspectorEmbeddedSearchView(
                session: session,
                navigation: navigation
            )
        }
        return actions
    }
}

extension View {
    func torahEditorHost(session: TorahEditorSession?) -> some View {
        modifier(TorahEditorHostModifier(session: session))
    }
}
