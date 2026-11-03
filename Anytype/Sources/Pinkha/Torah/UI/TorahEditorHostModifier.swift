import SwiftUI
import TorahInspectorUI

struct TorahEditorHostModifier: ViewModifier {
    let session: TorahEditorSession?
    var presentationHost: TorahEditorSession.PresentationHost = .editor
    @Environment(\.locale) private var locale

    @ViewBuilder
    func body(content: Content) -> some View {
        if let session {
            @Bindable var session = session

            content
                .sheet(
                    isPresented: Binding(
                        get: { session.presentationHost == presentationHost && session.isSearchPresented },
                        set: { if session.presentationHost == presentationHost { session.isSearchPresented = $0 } }
                    ),
                    onDismiss: {
                        guard session.presentationHost == presentationHost else { return }
                        session.searchDidDismiss()
                    }
                ) {
                    TorahSourcesSearchView(session: session)
                }
                .torahInspectorSheet(
                    selection: Binding(
                        get: { session.presentationHost == presentationHost ? session.selection : nil },
                        set: { if session.presentationHost == presentationHost { session.selection = $0 } }
                    ),
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
                        get: { session.presentationHost == presentationHost && session.message != nil },
                        set: { if !$0 { session.message = nil } }
                    )
                ) {
                    Button(Loc.ok) { session.message = nil }
                } message: {
                    Text(session.message ?? "")
                }
                .task(id: session.objectId) {
                    guard presentationHost == .editor else { return }
                    session.activateDocument()
                    session.updateEffectiveLocale(locale)
                    await session.refreshAssociationSnapshot()
                }
                .onAppear { if presentationHost == .editor { session.activateDocument() } }
                .onDisappear {
                    if presentationHost == .editor {
                        session.deactivateDocument()
                    }
                }
                .onChange(of: locale.identifier) {
                    session.updateEffectiveLocale(locale)
                }
                .onChange(of: session.selection?.id) { _, selectionID in
                    guard session.presentationHost == presentationHost, selectionID == nil else { return }
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
    func torahEditorHost(
        session: TorahEditorSession?,
        presentationHost: TorahEditorSession.PresentationHost = .editor
    ) -> some View {
        modifier(TorahEditorHostModifier(session: session, presentationHost: presentationHost))
    }
}
