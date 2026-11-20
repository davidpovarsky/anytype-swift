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
    @State private var documentChildReserved = false
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
                Button {
                    guard reserveDocumentChild() else { return }
                    presentation.torah.presentSearch(scope: .document)
                    releaseDocumentChildIfAbsent()
                } label: {
                    Image(systemName: "books.vertical")
                }.accessibilityLabel(Loc.Pinkha.Torah.sources)
                    .accessibilityIdentifier("any-native-document-sources")
                    .disabled(!canPresentDocumentChild)
                Button {
                    guard reserveDocumentChild() else { return }
                    presentation.showsProperties = true
                } label: { Image(systemName: "slider.horizontal.3") }
                    .accessibilityLabel(AnyUIErrorText.text("מאפיינים", "Properties"))
                    .accessibilityIdentifier("any-native-document-properties")
                    .disabled(!canPresentDocumentChild)
                Menu {
                    Button(AnyUIErrorText.text("העברת קישורי מקורות", "Transfer source associations"),
                           systemImage: "arrow.up.arrow.down") {
                        guard reserveDocumentChild() else { return }
                        presentation.showsArchiveTransfer = true
                    }
                        .accessibilityIdentifier("any-native-canonical-transfer")
                        .disabled(!canPresentDocumentChild)
                    Button(AnyUIErrorText.text("הוספת פסקה", "Add paragraph"), systemImage: "plus") {
                        Task { await presentation.addParagraph() }
                    }.disabled(!presentation.canMutate)
                    Button(AnyUIErrorText.text("כתיבה מימין לשמאל", "Right to left")) {
                        Task { await presentation.setWritingStyle(direction: .rightToLeft, alignment: .natural) }
                    }.disabled(presentation.selectedBlockIDs.isEmpty || !presentation.canMutate)
                        .accessibilityIdentifier("any-native-writing-direction-rtl")
                        .accessibilityAddTraits(isSavedDirection(.rightToLeft) ? .isSelected : [])
                    Button(AnyUIErrorText.text("כתיבה משמאל לימין", "Left to right")) {
                        Task { await presentation.setWritingStyle(direction: .leftToRight, alignment: .natural) }
                    }.disabled(presentation.selectedBlockIDs.isEmpty || !presentation.canMutate)
                        .accessibilityIdentifier("any-native-writing-direction-ltr")
                        .accessibilityAddTraits(isSavedDirection(.leftToRight) ? .isSelected : [])
                    Menu(AnyUIErrorText.text("יישור טקסט", "Text alignment")) {
                        Button(AnyUIErrorText.text("טבעי", "Natural")) {
                            Task { await presentation.setWritingStyle(alignment: .natural) }
                        }
                            .accessibilityIdentifier("any-native-text-alignment-natural")
                            .accessibilityAddTraits(isSavedAlignment(.natural) ? .isSelected : [])
                        Button(AnyUIErrorText.text("לשמאל", "Left")) {
                            Task { await presentation.setWritingStyle(alignment: .left) }
                        }
                            .accessibilityIdentifier("any-native-text-alignment-left")
                            .accessibilityAddTraits(isSavedAlignment(.left) ? .isSelected : [])
                        Button(AnyUIErrorText.text("למרכז", "Center")) {
                            Task { await presentation.setWritingStyle(alignment: .center) }
                        }
                            .accessibilityIdentifier("any-native-text-alignment-center")
                            .accessibilityAddTraits(isSavedAlignment(.center) ? .isSelected : [])
                        Button(AnyUIErrorText.text("לימין", "Right")) {
                            Task { await presentation.setWritingStyle(alignment: .right) }
                        }
                            .accessibilityIdentifier("any-native-text-alignment-right")
                            .accessibilityAddTraits(isSavedAlignment(.right) ? .isSelected : [])
                        Button(AnyUIErrorText.text("לשני הצדדים", "Justified")) {
                            Task { await presentation.setWritingStyle(alignment: .justified) }
                        }
                            .accessibilityIdentifier("any-native-text-alignment-justified")
                            .accessibilityAddTraits(isSavedAlignment(.justified) ? .isSelected : [])
                    }.disabled(presentation.selectedBlockIDs.isEmpty || !presentation.canMutate)
                        .accessibilityIdentifier("any-native-text-alignment")
                    Button(AnyUIErrorText.text("ביטול הפעולה האחרונה", "Undo last saved edit"), systemImage: "arrow.uturn.backward") {
                        Task { await presentation.undoLastNativeEdit() }
                    }.disabled(presentation.hasPendingEdits || !presentation.canMutate)
                    Button(AnyUIErrorText.text("רענון", "Refresh"), systemImage: "arrow.clockwise") {
                        Task { await presentation.retryObservation() }
                    }
                } label: { Image(systemName: "ellipsis.circle") }
                    .accessibilityLabel(AnyUIErrorText.text("פעולות מסמך", "Document actions"))
                    .accessibilityIdentifier("any-native-document-options")
                    .accessibilityValue(Text(savedWritingStyleDescription))
                Button {
                    guard canPresentDocumentChild else { return }
                    presentation.presentHanlin()
                } label: { Image(systemName: "bubble.left.and.bubble.right") }
                    .accessibilityLabel("Hanlin")
                    .accessibilityIdentifier("any-native-hanlin")
                    .disabled(!presentation.isMounted || presentation.read == nil || presentation.hasPendingEdits || !canPresentDocumentChild)
            }
        }
        .modifier(AnyTorahInspectorLayer(session: presentation.torah, host: .editor,
            onInspectorDismissed: { [ownerID = presentation.mountedOwnerID] in
                releaseDocumentChildIfAbsent()
                presentation.ownedPresentationDidDismiss(.editorInspector, ownerID: ownerID)
            }, onSearchDismissed: { [ownerID = presentation.mountedOwnerID] in
                releaseDocumentChildIfAbsent()
                presentation.ownedPresentationDidDismiss(.editorSearch, ownerID: ownerID)
            }))
        .sheet(isPresented: $presentation.showsArchiveTransfer,
               onDismiss: { releaseDocumentChildIfAbsent() }) {
            AnyNativeArchiveTransferView(document: presentation)
        }
        .sheet(isPresented: $presentation.showsDraftReview,
               onDismiss: { releaseDocumentChildIfAbsent() }) { draftReview }
        .sheet(isPresented: $presentation.showsProperties,
               onDismiss: { [ownerID = presentation.mountedOwnerID] in
                   releaseDocumentChildIfAbsent()
                   presentation.ownedPresentationDidDismiss(.properties, ownerID: ownerID)
               }) {
            AnyNativePropertiesView(presentation: presentation)
        }
        .alert(AnyUIErrorText.text("הודעה", "Message"),
               isPresented: Binding(get: { presentation.message != nil },
                                    set: { if !$0 { presentation.message = nil } })) {
            Button(AnyUIErrorText.text("אישור", "OK"), role: .cancel) {
                presentation.message = nil
            }
        } message: { Text(presentation.message ?? "") }
        .task { await presentation.load() }
        // Block-source buttons can open the retained Inspector directly. Keep
        // its ownership until onDismiss, including the closing animation.
        .onChange(of: presentation.torah.selection?.id) { _, value in
            if value != nil { documentChildReserved = true }
        }
        .onChange(of: presentation.torah.isSearchPresented) { _, value in
            if value { documentChildReserved = true }
        }
        .disabled(presentation.isNavigating)
        // The UIKit controller/dismantle hook owns actual removal. Owned
        // property/inspector sheets may cover this view without retiring it.
    }

    /// Accessibility reports the last native snapshot, never a submitted menu
    /// value. Pending writes retain the previous value; failures use the normal
    /// visible error path. Mixed or unavailable selections have no selected trait.
    private var selectedNativeBlocks: [AnyEditorBlock] {
        let ids = Set(presentation.selectedBlockIDs)
        guard !ids.isEmpty, let snapshot = presentation.read?.snapshot,
              ids.isSubset(of: Set(snapshot.depthFirstIDs)) else { return [] }
        let blocks = snapshot.blocks.filter { ids.contains($0.id) }
        return blocks.count == ids.count ? blocks : []
    }

    private func isSavedDirection(_ value: AnyWritingDirection) -> Bool {
        let blocks = selectedNativeBlocks
        return !blocks.isEmpty && blocks.allSatisfy { ($0.direction ?? .natural) == value }
    }

    private func isSavedAlignment(_ value: AnyTextAlignment) -> Bool {
        let blocks = selectedNativeBlocks
        return !blocks.isEmpty && blocks.allSatisfy { ($0.alignment ?? .natural) == value }
    }

    private var savedWritingStyleDescription: String {
        let blocks = selectedNativeBlocks
        guard let first = blocks.first else {
            return AnyUIErrorText.text("אין בלוק נבחר", "No block selected")
        }
        let direction = first.direction ?? .natural, alignment = first.alignment ?? .natural
        guard blocks.allSatisfy({ ($0.direction ?? .natural) == direction &&
                                 ($0.alignment ?? .natural) == alignment }) else {
            return AnyUIErrorText.text("עיצוב שמור שונה בבלוקים שנבחרו", "Selected blocks have mixed saved styles")
        }
        let directionTitle: String
        switch direction {
        case .natural: directionTitle = AnyUIErrorText.text("כיוון אוטומטי", "Automatic direction")
        case .leftToRight: directionTitle = AnyUIErrorText.text("כתיבה משמאל לימין", "Left to right")
        case .rightToLeft: directionTitle = AnyUIErrorText.text("כתיבה מימין לשמאל", "Right to left")
        }
        let alignmentTitle: String
        switch alignment {
        case .natural: alignmentTitle = AnyUIErrorText.text("טבעי", "Natural")
        case .left: alignmentTitle = AnyUIErrorText.text("לשמאל", "Left")
        case .center: alignmentTitle = AnyUIErrorText.text("למרכז", "Center")
        case .right: alignmentTitle = AnyUIErrorText.text("לימין", "Right")
        case .justified: alignmentTitle = AnyUIErrorText.text("לשני הצדדים", "Justified")
        }
        return AnyUIErrorText.text("העיצוב השמור: ", "Saved style: ") + directionTitle +
            AnyUIErrorText.text(", יישור ", ", alignment ") + alignmentTitle
    }

    private var canPresentDocumentChild: Bool {
        AnyNativeDocumentNavigation.canBeginOwnedPresentation(
            isReserved: documentChildReserved,
            hasInspector: presentation.torah.selection != nil,
            hasSearch: presentation.torah.isSearchPresented,
            hasNativeChild: presentation.showsProperties || presentation.showsArchiveTransfer || presentation.showsDraftReview,
            isNavigating: presentation.isNavigating)
    }

    private func reserveDocumentChild() -> Bool {
        guard canPresentDocumentChild else { return false }
        documentChildReserved = true
        return true
    }

    private func releaseDocumentChildIfAbsent() {
        guard presentation.torah.selection == nil, !presentation.torah.isSearchPresented,
              !presentation.showsProperties, !presentation.showsArchiveTransfer,
              !presentation.showsDraftReview else { return }
        documentChildReserved = false
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
                            guard reserveDocumentChild() else { return }
                            presentation.showsDraftReview = true
                        }.accessibilityIdentifier("any-native-review-recovered-drafts")
                            .disabled(!canPresentDocumentChild)
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
    var onInspectorDismissed: (() -> Void)?
    var onSearchDismissed: (() -> Void)?
    @Environment(\.locale) private var locale
    private var owns: Bool { session.presentationHost == host }
    private var selection: Binding<TorahInspectorSelection?> {
        .init(get: { owns ? session.selection : nil },
              set: { if owns { session.selection = $0 } })
    }
    private var search: Binding<Bool> {
        .init(get: { owns && session.isSearchPresented },
              set: { if owns { session.isSearchPresented = $0 } })
    }
    private var actions: TorahInspectorHostActions {
        var value = session.hostActions
        let close = value.onClose
        let didDismiss = onInspectorDismissed
        // The pinned Kit calls this only from its real sheet onDismiss. Its
        // close button separately clears the selection binding first.
        value.onClose = { close?(); didDismiss?() }
        value.search = TorahInspectorSearchCapability { navigation in
            AnyNativeSourceSearchView(session: session, navigation: navigation)
        }
        return value
    }
    func body(content: Content) -> some View {
        content
            .sheet(isPresented: search, onDismiss: {
                guard owns else { return }
                session.searchDidDismiss(); onSearchDismissed?()
            }) {
                AnyNativeSourceSearchView(session: session)
            }
            .torahInspectorSheet(selection: selection, repository: session.repository,
                entryMode: session.inspectorEntryMode, selectedTool: $session.selectedTool,
                selectedDetent: $session.selectedDetent,
                configuration: .init(availableTools: [.commentaries, .links, .relatedDocuments, .notes],
                                     allowsInlineFullSourceNavigation: true),
                actions: actions)
            .alert(Loc.Pinkha.Torah.title,
                isPresented: Binding(get: { owns && session.message != nil },
                    set: { if owns && !$0 { session.message = nil } })) {
                Button(Loc.ok) { session.message = nil }
            } message: { Text(session.message ?? "") }
            .task { if owns { session.updateEffectiveLocale(locale) } }
            .onChange(of: locale.identifier) { _, _ in
                if owns { session.updateEffectiveLocale(locale) }
            }
    }
}

public struct AnyNativeSourceSearchView: View {
    @State private var presenter: TorahSourcesSearchPresenter
    private let session: TorahEditorSession
    private let isEmbedded: Bool
    @Environment(\.dismiss) private var dismiss
    @Environment(\.locale) private var locale

    public init(session: TorahEditorSession, fixedScope: Bool = false,
                onSelectValue: ((TorahAssociationItem) -> Void)? = nil,
                navigation: TorahInspectorSearchNavigation? = nil) {
        self.session = session
        isEmbedded = navigation != nil
        _presenter = State(initialValue: TorahSourcesSearchPresenter(session: session,
            context: navigation == nil ? session.associationContext : session.documentAssociationContext,
            searchScope: navigation == nil ? session.searchScope : .references,
            fixedScope: fixedScope, onSelectValue: onSelectValue,
            onOpenSelection: { [weak session] selection in
                if let navigation { navigation.navigateToFullSource(selection) }
                else { session?.openResolvedReferenceFromStandaloneSearch(selection) }
            }))
    }

    public var body: some View {
        Group {
            if isEmbedded { searchContent }
            else { NavigationStack { searchContent } }
        }
    }

    @ViewBuilder private var searchContent: some View {
        @Bindable var presenter = presenter
            List {
                if !presenter.fixedScope {
                    Picker(Loc.Pinkha.Torah.sources, selection: $presenter.searchScope) {
                        ForEach(TorahEditorSession.SearchScope.allCases) { scope in Text(scope.title).tag(scope) }
                    }.pickerStyle(.segmented)
                }
                if !presenter.isSelectionOnly, let label = persistenceLabel {
                    Section {
                        HStack {
                            if presenter.persistenceState == .waiting || presenter.persistenceState == .saving {
                                ProgressView().accessibilityHidden(true)
                            }
                            Text(label).font(.caption).foregroundStyle(.secondary)
                        }
                        .accessibilityElement(children: .combine)
                        .accessibilityIdentifier("any-native-source-persistence-status")
                    }
                }
                if !presenter.visibleAssociations.isEmpty {
                    Section(AnyUIErrorText.text("מקושרים", "Linked")) {
                        ForEach(presenter.visibleAssociations) { item in
                            HStack {
                                Button(TorahAssociationDisplayFormatter.label(for: item, locale: locale)) {
                                    presenter.openAssociation(item)
                                }.disabled(!presenter.canOpenAssociation(item))
                                    .buttonStyle(.plain)
                                    .accessibilityIdentifier("any-native-linked-source-\(item.id)")
                                    .accessibilityValue(Text(verbatim: item.canonicalKey))
                                Spacer()
                                Button(role: .destructive) { Task { await presenter.unlinkAssociation(item) } }
                                    label: { Image(systemName: "link.badge.minus") }
                                    .disabled(!presenter.canEditAssociations)
                                    .buttonStyle(.plain)
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
                                    .buttonStyle(.plain)
                                    .accessibilityIdentifier("any-native-source-result-\(result.id)")
                                    .accessibilityValue(Text(verbatim: result.providerValue))
                                Spacer()
                                Button {
                                    Task { await presenter.link(result) }
                                } label: { Image(systemName: presenter.isSelectionOnly ? "checkmark.circle" : "plus.circle") }
                                    .disabled(!presenter.canEditAssociations)
                                    .buttonStyle(.plain)
                                    .accessibilityIdentifier(presenter.isSelectionOnly
                                        ? "any-native-source-select-\(result.id)"
                                        : "any-native-source-link-\(result.id)")
                                    .accessibilityLabel(Text(verbatim: (presenter.isSelectionOnly
                                        ? AnyUIErrorText.text("בחירת ", "Select ")
                                        : AnyUIErrorText.text("קישור ", "Link ")) + result.title(locale: locale)))
                            }
                        }
                    }
                }
            }
            .searchable(text: $presenter.searchQuery)
            .navigationTitle(presenter.fixedScope ? presenter.searchScope.title : Loc.Pinkha.Torah.sources)
            .toolbar {
                if !isEmbedded {
                    ToolbarItem(placement: .confirmationAction) {
                        Button(AnyUIErrorText.text("סיום", "Done")) { dismiss() }
                            .accessibilityIdentifier("any-native-source-search-done")
                    }
                }
            }
            .onChange(of: presenter.searchScope) { _, _ in presenter.categoryDidChange() }
            .onChange(of: presenter.canonicalSnapshot) { _, _ in presenter.synchronizeSnapshot() }
            .onChange(of: presenter.persistenceState) { _, state in
                if state == .saved {
                    UIAccessibility.post(notification: .announcement, argument: Loc.Pinkha.Torah.Persistence.saved)
                }
            }
            .onChange(of: presenter.searchQuery) { _, _ in
                Task { await presenter.performSearch(debounce: .milliseconds(300)) }
            }
            .task { session.updateEffectiveLocale(locale); await presenter.refreshAssociations() }
            .onDisappear { presenter.cancelPendingRequests() }
    }

    private var persistenceLabel: String? {
        switch presenter.persistenceState {
        case .waiting: Loc.Pinkha.Torah.Persistence.waiting
        case .saving: Loc.Pinkha.Torah.Persistence.saving
        case .conflict(let message): message.isEmpty ? Loc.Pinkha.Torah.Persistence.conflict : message
        case .uncertain(let message): message.isEmpty ? Loc.Pinkha.Torah.Persistence.uncertain : message
        case .error(let message): message.isEmpty ? Loc.Pinkha.Torah.Persistence.error : message
        case .saved, nil: nil
        }
    }
}

#endif
