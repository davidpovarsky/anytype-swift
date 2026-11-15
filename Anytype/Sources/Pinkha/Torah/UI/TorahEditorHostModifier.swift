import Foundation
import SwiftUI
import TorahInspectorUI

struct TorahEditorHostModifier: ViewModifier {
    let session: TorahEditorSession?
    var presentationHost: TorahEditorSession.PresentationHost = .editor
    @Environment(\.locale) private var locale
    @State private var routeIsMounted = false

    @ViewBuilder
    func body(content: Content) -> some View {
        if let session {
            @Bindable var session = session

            routeObserved(content, session: session)
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
                .onAppear {
                    if presentationHost == .editor {
                        session.activateDocument()
                        if ProcessInfo.processInfo.environment["PINKHA_UI27_ROUTE_OBSERVATION"] == "1" {
                            routeIsMounted = true
                        }
                    }
                }
                .onDisappear {
                    if presentationHost == .editor {
                        session.deactivateDocument()
                        if ProcessInfo.processInfo.environment["PINKHA_UI27_ROUTE_OBSERVATION"] == "1" {
                            routeIsMounted = false
                        }
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

    /// Observe the mounted session, rather than infer its identity from a requested URL.
    /// The ordinary application accessibility tree is unchanged unless explicitly opted in.
    @ViewBuilder
    private func routeObserved(_ content: Content, session: TorahEditorSession) -> some View {
        if presentationHost == .editor,
           ProcessInfo.processInfo.environment["PINKHA_UI27_ROUTE_OBSERVATION"] == "1" {
            content
                .accessibilityElement(children: .contain)
                .accessibilityIdentifier(routeIsMounted
                    ? "pinkha-ui27-editor:\(session.spaceId):\(session.objectId)"
                    : "pinkha-ui27-editor-unmounted")
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
