import SwiftUI
import TorahInspectorUI

struct TorahEditorHostModifier: ViewModifier {
    let session: TorahEditorSession?

    @ViewBuilder
    func body(content: Content) -> some View {
        if let session {
            @Bindable var session = session

            content
                .overlay(alignment: .topTrailing) {
                    Button {
                        session.presentSearch(targetBlockId: nil)
                    } label: {
                        Label("תורה / מקורות", systemImage: "text.book.closed")
                            .font(.subheadline.weight(.semibold))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(.regularMaterial, in: Capsule())
                    }
                    .buttonStyle(.plain)
                    .padding(.top, 54)
                    .padding(.trailing, 16)
                    .accessibilityIdentifier("torah-sources-entry")
                }
                .popover(isPresented: $session.isSearchPresented, attachmentAnchor: .rect(.bounds)) {
                    TorahSourcesSearchView(session: session)
                        .presentationCompactAdaptation(.sheet)
                }
                .torahInspectorSheet(
                    selection: $session.selection,
                    repository: session.repository,
                    selectedTool: $session.selectedTool,
                    selectedDetent: $session.selectedDetent,
                    actions: session.hostActions
                )
                .alert(
                    "Torah Inspector",
                    isPresented: Binding(
                        get: { session.message != nil },
                        set: { if !$0 { session.message = nil } }
                    )
                ) {
                    Button("אישור") { session.message = nil }
                } message: {
                    Text(session.message ?? "")
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
