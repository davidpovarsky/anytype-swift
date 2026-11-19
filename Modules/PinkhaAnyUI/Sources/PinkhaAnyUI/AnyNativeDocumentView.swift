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
                                    .accessibilityIdentifier("any-native-add-paragraph")
                            }
                        }
                    }
            }
            writeStatus.accessibilityIdentifier("any-native-save-status")
                .accessibilityValue(Text(presentation.writeStatusAccessibilityValue))
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
                    Button(AnyUIErrorText.text("העברת קישורי מקורות", "Transfer source associations"),
                           systemImage: "arrow.up.arrow.down") { presentation.showsArchiveTransfer = true }
                        .accessibilityIdentifier("any-native-canonical-transfer")
                    Button(AnyUIErrorText.text("הוספת פסקה", "Add paragraph"), systemImage: "plus") {
                        Task { await presentation.addParagraph() }
                    }.disabled(!presentation.canMutate)
                    Button(AnyUIErrorText.text("כתיבה מימין לשמאל", "Right to left")) {
                        Task { await presentation.setWritingStyle(direction: .rightToLeft, alignment: .natural) }
                    }.disabled(presentation.selectedBlockIDs.isEmpty || !presentation.canMutate)
                    Button(AnyUIErrorText.text("כתיבה משמאל לימין", "Left to right")) {
                        Task { await presentation.setWritingStyle(direction: .leftToRight, alignment: .natural) }
                    }.disabled(presentation.selectedBlockIDs.isEmpty || !presentation.canMutate)
                    Menu(AnyUIErrorText.text("יישור טקסט", "Text alignment")) {
                        Button(AnyUIErrorText.text("טבעי", "Natural")) {
                            Task { await presentation.setWritingStyle(alignment: .natural) }
                        }
                        Button(AnyUIErrorText.text("לשמאל", "Left")) {
                            Task { await presentation.setWritingStyle(alignment: .left) }
                        }
                        Button(AnyUIErrorText.text("למרכז", "Center")) {
                            Task { await presentation.setWritingStyle(alignment: .center) }
                        }
                        Button(AnyUIErrorText.text("לימין", "Right")) {
                            Task { await presentation.setWritingStyle(alignment: .right) }
                        }
                        Button(AnyUIErrorText.text("לשני הצדדים", "Justified")) {
                            Task { await presentation.setWritingStyle(alignment: .justified) }
                        }
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
                    .disabled(!presentation.isMounted || presentation.read == nil || presentation.hasPendingEdits)
            }
        }
        .modifier(AnyTorahInspectorLayer(session: presentation.torah, host: .editor))
        .sheet(isPresented: $presentation.showsArchiveTransfer) {
            AnyNativeArchiveTransferView(document: presentation)
        }
        .sheet(isPresented: $presentation.showsDraftReview) { draftReview }
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
        .task { await presentation.load() }
        // The UIKit controller/dismantle hook owns actual removal. Owned
        // property/inspector sheets may cover this view without retiring it.
    }

    private var draftReview: some View {
        NavigationStack {
            List {
                Section {
                    Text(AnyUIErrorText.recoveredDrafts)
                        .font(.footnote).foregroundStyle(.secondary)
                }
                ForEach(presentation.recoveredDrafts, id: \.blockID) { draft in
                    Section(AnyUIErrorText.text("שינוי מקומי", "Local edit")) {
                        Text(draft.inlineMarkdown).textSelection(.enabled)
                        if let current = presentation.read?.snapshot.blocks.first(where: { $0.id == draft.blockID }),
                           presentation.read?.snapshot.depthFirstIDs.contains(draft.blockID) == true {
                            Text(AnyUIErrorText.text("הטקסט השמור כעת", "Currently saved text"))
                                .font(.caption).foregroundStyle(.secondary)
                            Text(current.text).textSelection(.enabled).foregroundStyle(.secondary)
                        } else {
                            Text(AnyUIErrorText.text("הבלוק אינו נגיש כעת. הטקסט המקומי נשמר להעתקה.",
                                                    "This block is currently unavailable. Its local text is retained for copying."))
                                .font(.footnote).foregroundStyle(.secondary)
                        }
                    }
                }
                ForEach(presentation.recoveredUnmappedDrafts, id: \.blockID) { draft in
                    Section(AnyUIErrorText.text("טקסט שהוקלד ושמור לבדיקה", "Typed text retained for review")) {
                        Text(draft.display).textSelection(.enabled)
                        Text(AnyUIErrorText.unmappedComposition).font(.footnote).foregroundStyle(.secondary)
                    }
                }
                Button(AnyUIErrorText.text("העתקת הטקסט המקומי", "Copy local text")) {
                    UIPasteboard.general.string = presentation.localDraftTextForCopy
                }
                Button(AnyUIErrorText.text("בדיקה והמשך שמירה", "Review and resume saving")) {
                    Task { await presentation.resumeRecoveredDrafts() }
                }.accessibilityIdentifier("any-native-resume-recovered-drafts")
                    .disabled(!presentation.recoveredUnmappedDrafts.isEmpty || presentation.isComposing)
            }
            .navigationTitle(AnyUIErrorText.text("שינויים ששוחזרו", "Recovered edits"))
            .toolbar { ToolbarItem(placement: .confirmationAction) {
                Button(AnyUIErrorText.text("סיום", "Done")) { presentation.showsDraftReview = false }
            }}
        }
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
                    if presentation.requiresDraftReview {
                        Button(AnyUIErrorText.text("בדיקת השינויים ששוחזרו", "Review recovered edits")) {
                            presentation.showsDraftReview = true
                        }.accessibilityIdentifier("any-native-review-recovered-drafts")
                    } else {
                        Button(AnyUIErrorText.text("ניסיון נוסף", "Retry")) { Task { await presentation.flush() } }
                    }
                    Button(AnyUIErrorText.text("שמירת טקסט מקומי להעתקה", "Copy local text")) {
                        UIPasteboard.general.string = presentation.localDraftTextForCopy
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

struct AnyTorahInspectorLayer: ViewModifier {
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

#endif
