#if canImport(UIKit) && canImport(SwiftUI)
import Foundation
import SwiftUI
import UIKit
import PinkhaKit
import PinkhaAnyHost
import PinkhaTorahPresentation
import TorahInspectorCore
import TorahInspectorUI
import Loc

public struct AnyNativeDocumentView: View {
    @Bindable private var presentation: AnyDocumentPresentation
    public init(presentation: AnyDocumentPresentation) { self.presentation = presentation }

    public var body: some View {
        VStack(spacing: 0) {
            if presentation.isLoading && presentation.read == nil { ProgressView().padding() }
            if presentation.read != nil {
                AnyNativeEditor(presentation: presentation, revision: presentation.contentRevision)
                    .overlay {
                        if presentation.orderedBlocks.isEmpty {
                            ContentUnavailableView {
                                Label(AnyUIErrorText.text("מסמך ריק", "Empty document"), systemImage: "doc.text")
                            } actions: {
                                Button(AnyUIErrorText.text("הוספת פסקה", "Add paragraph")) {
                                    Task { await presentation.addParagraph() }
                                }.disabled(!presentation.canMutate)
                            }
                        }
                    }
            }
            writeStatus
        }
        .navigationTitle(presentation.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : presentation.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button { presentation.torah.presentSearch(scope: .document) } label: {
                    Image(systemName: "books.vertical")
                }.accessibilityLabel(Loc.Pinkha.Torah.sources)
                    .accessibilityIdentifier("any-native-document-sources")
                Button { presentation.showsProperties = true } label: { Image(systemName: "slider.horizontal.3") }
                    .accessibilityLabel(AnyUIErrorText.text("מאפיינים", "Properties"))
                    .accessibilityIdentifier("any-native-document-properties")
                Menu {
                    Button(AnyUIErrorText.text("הוספת פסקה", "Add paragraph"), systemImage: "plus") {
                        Task { await presentation.addParagraph() }
                    }.disabled(!presentation.canMutate)
                    Button(AnyUIErrorText.text("כתיבה מימין לשמאל", "Right to left")) {
                        Task { await presentation.setWritingStyle(direction: .rightToLeft, alignment: .natural) }
                    }.disabled(presentation.selectedBlockIDs.isEmpty || !presentation.canMutate)
                    Button(AnyUIErrorText.text("כתיבה משמאל לימין", "Left to right")) {
                        Task { await presentation.setWritingStyle(direction: .leftToRight, alignment: .natural) }
                    }.disabled(presentation.selectedBlockIDs.isEmpty || !presentation.canMutate)
                    Button(AnyUIErrorText.text("יישור טבעי", "Natural alignment")) {
                        Task { await presentation.setWritingStyle(direction: .natural, alignment: .natural) }
                    }.disabled(presentation.selectedBlockIDs.isEmpty || !presentation.canMutate)
                    Button(AnyUIErrorText.text("ביטול הפעולה האחרונה", "Undo last saved edit"), systemImage: "arrow.uturn.backward") {
                        Task { await presentation.undoLastNativeEdit() }
                    }.disabled(presentation.hasPendingEdits || !presentation.canMutate)
                    Button(AnyUIErrorText.text("רענון", "Refresh"), systemImage: "arrow.clockwise") {
                        Task { await presentation.retryObservation() }
                    }
                } label: { Image(systemName: "ellipsis.circle") }
                Button { presentation.presentHanlin() } label: { Image(systemName: "bubble.left.and.bubble.right") }
                    .accessibilityLabel("Hanlin")
                    .accessibilityIdentifier("any-native-hanlin")
                    .disabled(!presentation.isMounted || presentation.read == nil)
            }
        }
        .modifier(AnyTorahInspectorLayer(session: presentation.torah, host: .editor))
        .sheet(isPresented: $presentation.showsProperties) {
            AnyNativePropertiesView(presentation: presentation)
        }
        .sheet(isPresented: Binding(get: { presentation.sourceDocumentsTitle != nil },
                                     set: { if !$0 { presentation.sourceDocumentsTitle = nil } })) {
            NavigationStack {
                List(presentation.sourceDocuments) { item in
                    Button {
                        presentation.sourceDocumentsTitle = nil
                        presentation.showsProperties = false
                        presentation.onOpenObject?(item.objectID, item.blockID)
                    } label: {
                        Label(item.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : item.title,
                              systemImage: item.kind == .note ? "note.text" : "doc.text")
                    }
                }
                .navigationTitle(presentation.sourceDocumentsTitle ?? "")
                .toolbar { ToolbarItem(placement: .confirmationAction) {
                    Button(AnyUIErrorText.text("סיום", "Done")) { presentation.sourceDocumentsTitle = nil }
                }}
            }
        }
        .alert(AnyUIErrorText.text("הודעה", "Message"),
               isPresented: Binding(get: { presentation.message != nil || presentation.torah.message != nil },
                                    set: { if !$0 { presentation.message = nil; presentation.torah.message = nil } })) {
            Button(AnyUIErrorText.text("אישור", "OK"), role: .cancel) {
                presentation.message = nil; presentation.torah.message = nil
            }
        } message: { Text(presentation.message ?? presentation.torah.message ?? "") }
        .onDisappear { presentation.unmount() }
    }

    @ViewBuilder private var writeStatus: some View {
        switch presentation.writeState {
        case .clean: EmptyView()
        case .pending:
            Label(AnyUIErrorText.text("שינויים ממתינים", "Unsaved changes"), systemImage: "pencil")
                .font(.caption).foregroundStyle(.secondary).padding(6)
        case .saving: ProgressView(AnyUIErrorText.text("שומר…", "Saving…")).font(.caption).padding(6)
        case .saved:
            Label(AnyUIErrorText.text("נשמר", "Saved"), systemImage: "checkmark")
                .font(.caption).foregroundStyle(.secondary).padding(6)
        case .conflict(let message), .uncertain(let message), .failed(let message):
            VStack(spacing: 8) {
                Text(message).font(.caption)
                HStack {
                    Button(AnyUIErrorText.text("ניסיון נוסף", "Retry")) { Task { await presentation.flush() } }
                    Button(AnyUIErrorText.text("שמירת טקסט מקומי להעתקה", "Copy local text")) {
                        UIPasteboard.general.string = presentation.orderedBlocks.map {
                            presentation.source(for: $0)
                        }.joined(separator: "\n\n")
                    }
                    Button(AnyUIErrorText.text("ביטול השינויים המקומיים", "Discard local edits"), role: .destructive) {
                        presentation.discardLocalDrafts()
                        Task { await presentation.load() }
                    }
                }.font(.caption)
            }.padding().background(.thinMaterial)
        }
    }
}

private struct AnyTorahInspectorLayer: ViewModifier {
    @Bindable var session: TorahEditorSession
    let host: TorahEditorSession.PresentationHost
    private var owns: Bool { session.presentationHost == host }
    private var selection: Binding<TorahInspectorSelection?> {
        .init(get: { owns ? session.selection : nil },
              set: { if owns { session.selection = $0 } })
    }
    private var search: Binding<Bool> {
        .init(get: { owns && session.isSearchPresented },
              set: { if owns { session.isSearchPresented = $0 } })
    }
    func body(content: Content) -> some View {
        content
            .sheet(isPresented: search, onDismiss: session.searchDidDismiss) {
                AnyNativeSourceSearchView(session: session)
            }
            .torahInspectorSheet(selection: selection, repository: session.repository,
                entryMode: session.inspectorEntryMode, selectedTool: $session.selectedTool,
                selectedDetent: $session.selectedDetent,
                configuration: .init(availableTools: [.commentaries, .links, .relatedDocuments, .notes],
                                     allowsInlineFullSourceNavigation: true),
                actions: session.hostActions)
    }
}

public struct AnyNativeSourceSearchView: View {
    @State private var presenter: TorahSourcesSearchPresenter
    private let session: TorahEditorSession
    @Environment(\.dismiss) private var dismiss
    @Environment(\.locale) private var locale

    public init(session: TorahEditorSession, fixedScope: Bool = false,
                onSelectValue: ((TorahAssociationItem) -> Void)? = nil) {
        self.session = session
        _presenter = State(initialValue: TorahSourcesSearchPresenter(session: session,
            context: session.associationContext, searchScope: session.searchScope,
            fixedScope: fixedScope, onSelectValue: onSelectValue,
            onOpenSelection: { [weak session] selection in
                session?.openResolvedReferenceFromStandaloneSearch(selection)
            }))
    }

    public var body: some View {
        @Bindable var presenter = presenter
        NavigationStack {
            List {
                if !presenter.fixedScope {
                    Picker(Loc.Pinkha.Torah.sources, selection: $presenter.searchScope) {
                        ForEach(TorahEditorSession.SearchScope.allCases) { scope in Text(scope.title).tag(scope) }
                    }.pickerStyle(.segmented)
                }
                if !presenter.visibleAssociations.isEmpty {
                    Section(AnyUIErrorText.text("מקושרים", "Linked")) {
                        ForEach(presenter.visibleAssociations) { item in
                            HStack {
                                Button(TorahAssociationDisplayFormatter.label(for: item, locale: locale)) {
                                    presenter.openAssociation(item)
                                }.disabled(!presenter.canOpenAssociation(item))
                                Spacer()
                                Button(role: .destructive) { Task { await presenter.unlinkAssociation(item) } }
                                    label: { Image(systemName: "link.badge.minus") }
                                    .disabled(!presenter.canEditAssociations)
                            }
                        }
                    }
                }
                Section {
                    switch presenter.searchState {
                    case .idle: Text(AnyUIErrorText.text("חפש מקור, נושא או מילה.", "Search for a source, topic, or word.")).foregroundStyle(.secondary)
                    case .loading: ProgressView()
                    case .empty: Text(AnyUIErrorText.text("לא נמצאו תוצאות", "No results"))
                    case .error(let message): Text(message).foregroundStyle(.red)
                    case .results(let results):
                        ForEach(results) { result in
                            HStack(alignment: .top) {
                                Button {
                                    Task { await presenter.openReference(result) }
                                } label: {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(result.title(locale: locale))
                                        if let subtitle = result.subtitle(locale: locale) {
                                            Text(subtitle).font(.caption).foregroundStyle(.secondary)
                                        }
                                    }
                                }.disabled(result.scope != .references || presenter.isSelectionOnly)
                                Spacer()
                                Button {
                                    Task { await presenter.link(result) }
                                } label: { Image(systemName: presenter.isSelectionOnly ? "checkmark.circle" : "plus.circle") }
                                    .disabled(!presenter.canEditAssociations)
                            }
                        }
                    }
                }
            }
            .searchable(text: $presenter.searchQuery)
            .navigationTitle(presenter.fixedScope ? presenter.searchScope.title : Loc.Pinkha.Torah.sources)
            .toolbar { ToolbarItem(placement: .confirmationAction) {
                Button(AnyUIErrorText.text("סיום", "Done")) { dismiss() }
            }}
            .onChange(of: presenter.searchScope) { _, _ in presenter.categoryDidChange() }
            .onChange(of: presenter.searchQuery) { _, _ in
                Task { await presenter.performSearch(debounce: .milliseconds(300)) }
            }
            .task { session.updateEffectiveLocale(locale); await presenter.refreshAssociations() }
            .onDisappear { presenter.cancelPendingRequests() }
        }
    }
}

public struct AnyNativePropertiesView: View {
    @Bindable var presentation: AnyDocumentPresentation
    @Environment(\.dismiss) private var dismiss
    @Environment(\.locale) private var locale

    public init(presentation: AnyDocumentPresentation) { self.presentation = presentation }

    public var body: some View {
        NavigationStack {
            List {
                propertySection(.references, items: presentation.torah.documentPropertyProjection.sources)
                propertySection(.topics, items: presentation.torah.documentPropertyProjection.topics)
                propertySection(.words, items: presentation.torah.documentPropertyProjection.words)
                if let native = presentation.nativeProperties, !native.readiness.complete {
                    Section { Text(AnyUIErrorText.incompleteIndex).font(.footnote).foregroundStyle(.secondary) }
                }
            }
            .navigationTitle(AnyUIErrorText.text("מאפיינים", "Properties"))
            .toolbar { ToolbarItem(placement: .confirmationAction) {
                Button(AnyUIErrorText.text("סיום", "Done")) { dismiss() }
            }}
            .modifier(AnyTorahInspectorLayer(session: presentation.torah, host: .properties))
            .onAppear { presentation.torah.activatePresentationHost(.properties) }
            .onDisappear { presentation.torah.dismissPropertiesPresentation() }
        }
    }

    @ViewBuilder private func propertySection(_ scope: TorahEditorSession.SearchScope,
                                              items: [TorahAssociationItem]) -> some View {
        Section(scope.title) {
            ForEach(items) { item in
                HStack {
                    Text(TorahAssociationDisplayFormatter.label(for: item, locale: locale))
                    Spacer()
                    Menu {
                        if presentation.torah.canOpenAssociation(item) {
                            Button(AnyUIErrorText.text("פתיחת מקור", "Open source")) {
                                presentation.torah.openDocumentAssociation(item)
                            }
                        }
                        Button(AnyUIErrorText.text("מסמכים מקושרים", "Related documents")) {
                            Task { await presentation.showDocuments(with: item) }
                        }
                        Button(AnyUIErrorText.text("הסרת קישור", "Unlink"), role: .destructive) {
                            Task { await presentation.torah.unlinkAssociation(item, from: presentation.torah.documentAssociationContext) }
                        }.disabled(!presentation.canMutate)
                    } label: { Image(systemName: "ellipsis.circle") }
                }
            }
            Button {
                presentation.torah.presentSearch(scope: .document, initialCategory: scope, host: .properties)
            } label: { Label(AnyUIErrorText.text("הוספה", "Add"), systemImage: "plus") }
                .disabled(!presentation.canMutate)
        }
    }
}
#endif
