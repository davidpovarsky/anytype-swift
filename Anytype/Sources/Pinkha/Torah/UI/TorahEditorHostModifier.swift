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
                .overlay(alignment: .topTrailing) {
                    Button {
                        session.presentSearch(scope: .document)
                    } label: {
                        HStack(spacing: 6) {
                            Label(Loc.Pinkha.Torah.title, systemImage: "text.book.closed")
                            if !session.visibleDocumentAssociations.isEmpty {
                                Text(session.visibleDocumentAssociations.count, format: .number)
                                    .font(.caption2.weight(.bold))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(.secondary.opacity(0.14), in: Capsule())
                            }
                        }
                            .font(.subheadline.weight(.semibold))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(.regularMaterial, in: Capsule())
                    }
                    .buttonStyle(.plain)
                    .padding(.top, 54)
                    .padding(.trailing, 16)
                    .accessibilityIdentifier("torah-sources-entry")
                    .accessibilityValue(String(session.visibleDocumentAssociations.count))
                }
                .popover(isPresented: $session.isSearchPresented, attachmentAnchor: .rect(.bounds)) {
                    TorahSourcesSearchView(session: session)
                        .presentationCompactAdaptation(.sheet)
                }
                .torahInspectorSheet(
                    selection: $session.selection,
                    repository: session.repository,
                    entryMode: session.inspectorEntryMode,
                    selectedTool: $session.selectedTool,
                    selectedDetent: $session.selectedDetent,
                    actions: session.hostActions
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
                    session.updateEffectiveLocale(locale)
                    await session.refreshAssociationSnapshot()
                }
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
}

extension View {
    func torahEditorHost(session: TorahEditorSession?) -> some View {
        modifier(TorahEditorHostModifier(session: session))
    }
}
