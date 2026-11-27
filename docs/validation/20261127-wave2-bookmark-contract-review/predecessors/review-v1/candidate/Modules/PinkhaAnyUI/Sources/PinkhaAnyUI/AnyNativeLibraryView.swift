#if canImport(UIKit) && canImport(SwiftUI)
import Foundation
import SwiftUI
import UniformTypeIdentifiers
import DesignKit
import AnytypeCore
import Loc
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

private struct AnyNativeNameRequest: Identifiable {
    let id = UUID()
    let item: AnyHierarchyItem?
    let kind: PinkhaHierarchyNodeKind
    let parentID: String?
    let isNote: Bool
}

private struct AnyNativeBookmarkSubmission {
    let typeID: String
    let sourceURL: String
}

private struct AnyNativeNameSubmission {
    let item: AnyHierarchyItem?
    let kind: PinkhaHierarchyNodeKind
    let parentID: String?
    let isNote: Bool
    let title: String
    var bookmark: AnyNativeBookmarkSubmission? = nil
}

/// One coherent native Space. Its account/session/creators are supplied by the
/// native application owner; this entry point has no Heart object-ID fallback.
public struct AnyNativeLibraryView: View {
    @State private var model: AnyLibraryPresentation
    @State private var path: [AnyNativeLibraryDestination] = []
    @State private var nameRequest: AnyNativeNameRequest?
    @State private var pendingNameSubmission: AnyNativeNameSubmission?
    @State private var editMode: EditMode = .inactive
    @State private var moveItem: AnyHierarchyItem?
    @State private var removeItem: AnyHierarchyItem?
    private let onRequestClose: @MainActor () async -> Void
    private let lifetime: AnyUIPresentationLifetime
    private let onManageMembers: (@MainActor () -> Void)?

    public init(client: AnyHTTPClient, session: AnyApplicationSession,
                objects: AnyNativeObjectCreator, blocks: AnyNativeBlockCreator,
                capabilities: AnyUIFoundationCapabilities,
                onRequestClose: @escaping @MainActor () async -> Void,
                lifetime: AnyUIPresentationLifetime, recovery: AnyNativeLibraryRecovery,
                onManageMembers: (@MainActor () -> Void)? = nil) {
        _model = State(initialValue: AnyLibraryPresentation(client: client, session: session,
            objects: objects, blocks: blocks, capabilities: capabilities, lifetime: lifetime, recovery: recovery))
        _path = State(initialValue: recovery.workspace == session.workspace ? recovery.navigation : [])
        self.onRequestClose = onRequestClose; self.lifetime = lifetime
        self.onManageMembers = onManageMembers
    }

    public var body: some View {
        NavigationStack(path: $path) {
            library(parentID: nil)
                .navigationDestination(for: AnyNativeLibraryDestination.self) { route in
                    switch route {
                    case .folder(let id): library(parentID: id)
                    case .document(let id, let blockID):
                        AnyNativeDocumentEntry(library: model, objectID: id, blockID: blockID)
                    case .allDocuments: documents(notesOnly: false)
                    case .notes: documents(notesOnly: true)
                    case .bin: bin
                    }
                }
        }
        .environment(\.editMode, $editMode)
        .onChange(of: path) { _, current in
            guard lifetime.isActive else { return }
            do { try model.recovery.replaceNavigation(current, workspace: model.session.workspace) }
            catch { model.message = AnyUIErrorText.describe(error) }
        }
        .task {
            model.onOpenDocument = { id, blockID in path.append(.document(id, blockID)) }
            await model.open()
            routeMiniAppsReturn()
        }
        .task(id: AnyMiniAppsReturnRouter.shared.requestID) { routeMiniAppsReturn() }
        .onChange(of: model.isReady) { _, ready in if ready { routeMiniAppsReturn() } }
        .sheet(item: $nameRequest, onDismiss: submitAfterNameDismissal) { request in
            if let item = request.item {
                AnyNativeNameSheet(title: AnyUIErrorText.text("שינוי שם", "Rename"),
                    initialValue: item.title, commit: { title in
                        finishNaming(request, title: title, kind: request.kind, isNote: request.isNote)
                    }, cancel: { cancelNaming(request) })
            } else {
                AnyNativeCreationSheet(bookmarkTypes: model.bookmarkTypes, commit: { kind, isNote, title in
                    finishNaming(request, title: title, kind: kind, isNote: isNote)
                }, bookmarkCommit: { typeID, sourceURL in
                    finishNaming(request, title: "", kind: .writingDocument, isNote: false,
                        bookmark: .init(typeID: typeID, sourceURL: sourceURL))
                }, cancel: { cancelNaming(request) })
            }
        }
        .sheet(isPresented: Binding(get: { moveItem != nil }, set: { if !$0 { moveItem = nil } })) {
            if let item = moveItem { movePicker(item) }
        }
        .confirmationDialog(AnyUIErrorText.text("העברה לסל המחזור", "Move to Bin"),
            isPresented: Binding(get: { removeItem != nil }, set: { if !$0 { removeItem = nil } }),
            titleVisibility: .visible) {
                if let item = removeItem {
                    Button(item.kind == .folder ?
                        AnyUIErrorText.text("העברת התוכן לתיקיית האב והסרת התיקייה", "Move contents to the parent and remove folder") :
                        AnyUIErrorText.text("העברה לסל המחזור", "Move to Bin"), role: .destructive) {
                            Task { await model.remove(item) }; removeItem = nil
                        }.accessibilityIdentifier("any-native-bin-confirm-remove")
                }
                Button(AnyUIErrorText.text("ביטול", "Cancel"), role: .cancel) { removeItem = nil }
            }
        .alert(AnyUIErrorText.text("הודעה", "Message"),
               isPresented: Binding(get: { model.message != nil }, set: { if !$0 { model.message = nil } })) {
            Button(AnyUIErrorText.text("אישור", "OK"), role: .cancel) { model.message = nil }
        } message: { Text(model.message ?? "") }
    }

    private func beginNaming(_ request: AnyNativeNameRequest) {
        guard lifetime.isActive, model.canWrite,
              nameRequest == nil, pendingNameSubmission == nil else { return }
        nameRequest = request
    }

    private func finishNaming(_ request: AnyNativeNameRequest, title: String,
                              kind: PinkhaHierarchyNodeKind, isNote: Bool,
                              bookmark: AnyNativeBookmarkSubmission? = nil) {
        guard nameRequest?.id == request.id else { return }
        guard lifetime.isActive, model.canWrite else {
            pendingNameSubmission = nil
            nameRequest = nil
            return
        }
        pendingNameSubmission = .init(item: request.item, kind: kind,
            parentID: request.parentID, isNote: isNote, title: title, bookmark: bookmark)
        nameRequest = nil
    }

    private func cancelNaming(_ request: AnyNativeNameRequest) {
        guard nameRequest?.id == request.id else { return }
        pendingNameSubmission = nil
        nameRequest = nil
    }

    private func routeMiniAppsReturn() {
        guard lifetime.isActive, model.isReady,
              let objectID = AnyMiniAppsReturnRouter.shared.pendingObject(
                accountID: model.session.workspace.accountID, spaceID: model.session.workspace.spaceID) else { return }
        if path.last != .document(objectID, nil) { path.append(.document(objectID, nil)) }
        AnyMiniAppsReturnRouter.shared.didRoute(accountID: model.session.workspace.accountID,
            spaceID: model.session.workspace.spaceID, objectID: objectID)
    }

    private func submitAfterNameDismissal() {
        // Consume once only after SwiftUI reports that the owned sheet closed.
        // Merely requesting dismissal does not finish the presentation transition.
        guard let submission = pendingNameSubmission else { return }
        pendingNameSubmission = nil
        guard lifetime.isActive, model.canWrite else { return }
        Task { @MainActor in
            guard lifetime.isActive, model.canWrite else { return }
            if let item = submission.item {
                await model.rename(item, title: submission.title)
            } else if let bookmark = submission.bookmark {
                await model.createBookmark(typeID: bookmark.typeID, sourceURL: bookmark.sourceURL,
                                           parentID: submission.parentID)
            } else {
                await model.create(title: submission.title, kind: submission.kind,
                                   parentID: submission.parentID, isNote: submission.isNote)
            }
        }
    }

    @ViewBuilder private func library(parentID: String?) -> some View {
        @Bindable var model = model
        Group {
            if model.requiresSetup {
                ContentUnavailableView {
                    Label(AnyUIErrorText.text("הכנת סביבת הכתיבה", "Set up writing workspace"),
                          systemImage: "books.vertical")
                } description: {
                    Text(AnyUIErrorText.text("הגדרת הספרייה, ההערות וקישורי המקורות במרחב הזה.",
                                            "Set up the library, Notes, and source associations in this Space."))
                } actions: {
                    Button(AnyUIErrorText.text("הגדרה", "Set up")) { Task { await model.installWorkspace() } }
                        .disabled(model.isLoading)
                        .accessibilityIdentifier("any-native-workspace-setup")
                }
            } else if model.isLoading && model.hierarchy == nil {
                ProgressView()
            } else {
                List {
                    if !model.searchQuery.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        Section(AnyUIErrorText.text("תוצאות חיפוש", "Search results")) {
                            if model.isSearching { ProgressView() }
                            ForEach(model.searchResults) { item in documentRow(item) }
                            if !model.isSearching && model.searchResults.isEmpty {
                                Text(AnyUIErrorText.text("לא נמצאו תוצאות", "No results")).foregroundStyle(.secondary)
                            }
                        }
                    } else {
                        if parentID == nil {
                            Section {
                                NavigationLink(value: AnyNativeLibraryDestination.allDocuments) {
                                    Label(AnyUIErrorText.text("כל המסמכים", "All documents"), systemImage: "doc.on.doc")
                                }
                                NavigationLink(value: AnyNativeLibraryDestination.notes) {
                                    Label(AnyUIErrorText.text("הערות", "Notes"), systemImage: "note.text")
                                }
                                NavigationLink(value: AnyNativeLibraryDestination.bin) {
                                    Label(AnyUIErrorText.text("סל המחזור", "Bin"), systemImage: "trash")
                                }.accessibilityIdentifier("any-native-open-bin")
                            }
                        }
                        Section {
                            let items = model.hierarchyPresentation.children(of: parentID)
                            ForEach(items, id: \.objectID) { item in
                                hierarchyRow(item)
                                    .moveDisabled(!editMode.isEditing || !model.canWrite)
                            }
                                // Remove List reordering outside Edit mode so folder drops own the interaction.
                                .onMove(perform: editMode.isEditing && model.canWrite ? { offsets, destination in
                                    guard lifetime.isActive, model.canWrite, editMode.isEditing,
                                          offsets.count == 1, let offset = offsets.first,
                                          items.indices.contains(offset) else { return }
                                    let item = items[offset]
                                    var reordered = items.map(\.objectID)
                                    reordered.move(fromOffsets: offsets, toOffset: destination)
                                    guard let index = reordered.firstIndex(of: item.objectID) else { return }
                                    let before = index + 1 < reordered.count ? reordered[index + 1] : nil
                                    Task { await model.move(objectID: item.objectID, parentID: parentID,
                                                            beforeSiblingID: before) }
                                } : nil)
                            ForEach(model.pendingCreations.filter { $0.plan.parentID == parentID }) { pending in
                                HStack {
                                    Label(pending.plan.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : pending.plan.title,
                                          systemImage: pending.bookmark != nil ? "bookmark" : (pending.plan.kind == .folder ? "folder" : "doc"))
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    if pending.error == nil { ProgressView() }
                                    else { Button(AnyUIErrorText.text("ניסיון נוסף", "Retry")) {
                                        Task { await model.retryCreation(pending.id) }
                                    }}
                                }
                                if let error = pending.error { Text(error).font(.caption).foregroundStyle(.secondary) }
                            }
                        } header: { Text(parentID == nil ? AnyUIErrorText.text("ספרייה", "Library") : "") }
                        if let issues = model.hierarchy?.issues, !issues.isEmpty {
                            Section {
                                Text(AnyUIErrorText.text("יש פריטים שמיקום התיקייה שלהם דורש תיקון.",
                                    "Some items have a folder placement that needs repair."))
                                    .font(.footnote).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                .searchable(text: $model.searchQuery, prompt: AnyUIErrorText.text("חיפוש במסמכים", "Search documents"))
                .onChange(of: model.searchQuery) { _, _ in model.searchChanged() }
                .refreshable { await model.refresh() }
                .accessibilityIdentifier("any-native-library")
                .accessibilityValue(Text(model.pendingMoves.isEmpty ? "ready" : "saving"))
            }
        }
        .navigationTitle(parentID.flatMap { model.hierarchyPresentation.itemsByID[$0]?.title } ??
                         AnyUIErrorText.text("ספרייה", "Library"))
        .toolbar {
            if parentID == nil {
                ToolbarItem(placement: .topBarLeading) {
                    Button(AnyUIErrorText.text("מרחבים", "Spaces")) {
                        Task { lifetime.revoke(); await lifetime.drain(); await onRequestClose() }
                    }.accessibilityIdentifier("any-native-close-workspace")
                }
            }
            ToolbarItemGroup(placement: .topBarTrailing) {
                if let onManageMembers {
                    Button(action: onManageMembers) { Image(systemName: "person.2") }
                        .accessibilityLabel(Text(AnyUIErrorText.text("הרשאות והזמנות", "Members and invitations")))
                        .accessibilityIdentifier("any-native-members")
                        .disabled(!lifetime.isActive)
                }
                if model.hierarchy != nil {
                    EditButton().disabled(!model.canWrite)
                    Button {
                        beginNaming(.init(item: nil, kind: .writingDocument,
                                          parentID: parentID, isNote: false))
                    } label: { Image(systemName: "plus") }
                        .disabled(!model.canWrite || nameRequest != nil || pendingNameSubmission != nil)
                        .accessibilityLabel(Text(AnyUIErrorText.text("יצירה", "Create")))
                        .accessibilityIdentifier("any-native-create-menu")
                }
            }
        }
    }

    private func hierarchyRow(_ item: AnyHierarchyPresentationItem) -> some View {
        AnyNativeHierarchyDropRow(session: model.session, canDrop: { sourceID in
            canDropHierarchy(sourceID, onto: item.objectID)
        }, performDrop: { sourceID in
            Task { @MainActor in
                guard canDropHierarchy(sourceID, onto: item.objectID),
                      let destination = model.hierarchy?.itemsByID[item.objectID] else { return }
                await model.move(objectID: sourceID,
                    parentID: destination.kind == .folder ? destination.objectID : destination.parentID,
                    beforeSiblingID: destination.kind == .folder ? nil : destination.objectID)
            }
        }) {
            HStack(spacing: 8) {
                Button {
                    path.append(item.kind == .folder ? .folder(item.objectID) : .document(item.objectID, nil))
                } label: {
                    HStack {
                        Label(item.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : item.title,
                              systemImage: item.kind == .folder ? "folder" : "doc.text")
                            .foregroundStyle(.primary)
                        Spacer()
                        if item.isPending || model.pendingMoves.contains(item.objectID) { ProgressView() }
                        if item.kind == .folder { Image(systemName: "chevron.forward").foregroundStyle(.secondary) }
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("any-native-hierarchy-row-\(item.objectID)")
                .contextMenu { hierarchyActions(item) }

                Menu { hierarchyActions(item) } label: {
                    Image(systemName: "ellipsis")
                        .frame(width: 44, height: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.borderless)
                .accessibilityLabel(AnyUIErrorText.text("פעולות פריט", "Item actions"))
                .accessibilityIdentifier("any-native-hierarchy-actions-\(item.objectID)")

                if model.canWrite && !editMode.isEditing {
                    AnyNativeHierarchyDragHandle(session: model.session, objectID: item.objectID,
                        title: item.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : item.title,
                        canDrag: { lifetime.isActive && model.canWrite && !editMode.isEditing
                            && !model.pendingMoves.contains(item.objectID) })
                        .frame(width: 44, height: 44)
                }
            }
        }
    }

    @ViewBuilder
    private func hierarchyActions(_ item: AnyHierarchyPresentationItem) -> some View {
        Button(AnyUIErrorText.text("שינוי שם", "Rename"), systemImage: "pencil") {
            beginNaming(.init(item: item.native, kind: item.kind, parentID: item.parentID, isNote: false))
        }.disabled(!model.canWrite)
        Button(AnyUIErrorText.text("העברה", "Move"), systemImage: "folder") { moveItem = item.native }
            .disabled(!model.canWrite)
            .accessibilityIdentifier("any-native-hierarchy-move")
        Button(AnyUIErrorText.text("העברה לסל המחזור", "Move to Bin"), systemImage: "trash", role: .destructive) {
            removeItem = item.native
        }.disabled(!model.canWrite)
            .accessibilityIdentifier("any-native-hierarchy-archive")
    }

    private func canDropHierarchy(_ sourceID: String, onto destinationID: String) -> Bool {
        lifetime.isActive && model.canWrite && !editMode.isEditing && sourceID != destinationID
            && !model.pendingMoves.contains(sourceID)
            && model.hierarchy?.itemsByID[sourceID] != nil
            && model.hierarchy?.itemsByID[destinationID] != nil
    }

    private func documents(notesOnly: Bool) -> some View {
        List(model.allDocuments.filter { !notesOnly || $0.isNote }) { item in documentRow(item) }
            .navigationTitle(notesOnly ? AnyUIErrorText.text("הערות", "Notes") :
                                        AnyUIErrorText.text("כל המסמכים", "All documents"))
            .refreshable { await model.refresh() }
    }

    private var bin: some View {
        List {
            if model.isLoadingBin && model.binItems.isEmpty { ProgressView() }
            if model.binReadFailed {
                VStack(alignment: .leading, spacing: 8) {
                    Text(AnyUIErrorText.text("לא ניתן לטעון את סל המחזור.", "Couldn't load the Bin."))
                        .foregroundStyle(.secondary)
                    Button(AnyUIErrorText.text("ניסיון נוסף", "Retry")) {
                        Task { await model.refreshBin() }
                    }
                    .buttonStyle(.borderless)
                    .disabled(!lifetime.isActive || model.isLoadingBin)
                    .accessibilityIdentifier("any-native-bin-retry")
                }
                .accessibilityElement(children: .contain)
                .accessibilityIdentifier("any-native-bin-read-failure")
            }
            ForEach(model.binItems) { item in
                HStack {
                    Label(item.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : item.title,
                          systemImage: item.isFolder ? "folder" : "doc.text")
                    Spacer()
                    if model.pendingRestores.contains(item.id) {
                        ProgressView()
                    } else {
                        Button(AnyUIErrorText.text("שחזור", "Restore")) {
                            Task { await model.restoreFromBin(objectID: item.id) }
                        }
                        .buttonStyle(.borderless)
                        .disabled(!lifetime.isActive || !model.canWrite)
                        .accessibilityIdentifier("any-native-bin-restore-" + item.id)
                    }
                }
                .accessibilityElement(children: .contain)
                .accessibilityIdentifier("any-native-bin-item-" + item.id)
            }
            if !model.isLoadingBin && !model.binReadFailed && model.binItems.isEmpty {
                Text(AnyUIErrorText.text("סל המחזור ריק", "The Bin is empty"))
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("any-native-bin-empty")
            }
        }
        .navigationTitle(AnyUIErrorText.text("סל המחזור", "Bin"))
        .accessibilityIdentifier("any-native-bin")
        .task(id: model.isReady) { if model.isReady { await model.refreshBin() } }
        .refreshable { await model.refreshBin() }
    }

    private func documentRow(_ item: AnyLibraryDocument) -> some View {
        Button { path.append(.document(item.id, nil)) } label: {
            VStack(alignment: .leading, spacing: 4) {
                Label(item.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : item.title,
                      systemImage: item.isNote ? "note.text" : "doc.text").foregroundStyle(.primary)
                if let snippet = item.snippet { Text(snippet).font(.caption).lineLimit(3).foregroundStyle(.secondary) }
            }
        }
    }

    private func movePicker(_ item: AnyHierarchyItem) -> some View {
        NavigationStack {
            List {
                Button(AnyUIErrorText.text("שורש הספרייה", "Library root")) {
                    moveItem = nil
                    Task { await model.move(objectID: item.objectID, parentID: nil) }
                }
                ForEach(model.hierarchy?.items.filter { $0.kind == .folder && $0.objectID != item.objectID } ?? [],
                        id: \.objectID) { folder in
                    Button {
                        moveItem = nil
                        Task { await model.move(objectID: item.objectID, parentID: folder.objectID) }
                    } label: { Label(folder.title, systemImage: "folder") }
                }
            }
            .navigationTitle(AnyUIErrorText.text("העברה לתיקייה", "Move to folder"))
            .toolbar { ToolbarItem(placement: .cancellationAction) {
                Button(AnyUIErrorText.text("ביטול", "Cancel")) { moveItem = nil }
            }}
        }
    }
}

private struct AnyNativeDocumentEntry: View {
    let library: AnyLibraryPresentation
    let objectID: String
    let blockID: String?
    @State private var presentation: AnyDocumentPresentation?
    @State private var error: String?
    @State private var didReveal = false

    var body: some View {
        Group {
            if let presentation {
                AnyNativeDocumentView(presentation: presentation)
                    .onChange(of: presentation.contentRevision) { _, _ in reveal(presentation) }
            } else if let error {
                ContentUnavailableView(AnyUIErrorText.text("לא ניתן לפתוח את המסמך", "Unable to open document"),
                                       systemImage: "doc.badge.ellipsis", description: Text(error))
            } else { ProgressView() }
        }
        .task(id: library.isReady ? objectID : "") {
            guard library.isReady else { return }
            error = nil
            do { presentation = try library.document(objectID) }
            catch { self.error = AnyUIErrorText.describe(error) }
        }
    }

    private func reveal(_ presentation: AnyDocumentPresentation) {
        guard !didReveal, let blockID, let surface = presentation.surface,
              presentation.read?.snapshot.depthFirstIDs.contains(blockID) == true else { return }
        surface.reveal(blockID: blockID, selection: nil)
        didReveal = surface.isBlockVisible(blockID)
    }
}

private enum AnyNativeCreationKind: Hashable {
    case document, note, folder, bookmarkTypes, bookmarkURL(String)
}

private struct AnyNativeCreationSheet: View {
    let bookmarkTypes: [AnyNativePropertyOwner]
    let commit: (PinkhaHierarchyNodeKind, Bool, String) -> Void
    let bookmarkCommit: (String, String) -> Void
    let cancel: () -> Void
    @State private var path: [AnyNativeCreationKind] = []

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Button(AnyUIErrorText.text("מסמך חדש", "New document"), systemImage: "doc.badge.plus") {
                    path.append(.document)
                }.accessibilityIdentifier("any-native-new-document")
                Button(AnyUIErrorText.text("הערה חדשה", "New Note"), systemImage: "note.text.badge.plus") {
                    path.append(.note)
                }.accessibilityIdentifier("any-native-new-note")
                Button(AnyUIErrorText.text("תיקייה חדשה", "New folder"), systemImage: "folder.badge.plus") {
                    path.append(.folder)
                }.accessibilityIdentifier("any-native-new-folder")
                Button(AnyUIErrorText.text("סימנייה חדשה", "New bookmark"), systemImage: "bookmark") {
                    if let only = bookmarkTypes.first, bookmarkTypes.count == 1 {
                        path.append(.bookmarkURL(only.id))
                    } else { path.append(.bookmarkTypes) }
                }
                .disabled(bookmarkTypes.isEmpty)
                .accessibilityIdentifier("any-native-new-bookmark")
                if bookmarkTypes.isEmpty {
                    Text(AnyUIErrorText.text("לא נמצא סוג סימנייה במרחב הזה.", "No bookmark type is available in this Space."))
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            .navigationTitle(AnyUIErrorText.text("יצירה", "Create"))
            .toolbar {
                if path.isEmpty {
                    ToolbarItem(placement: .cancellationAction) {
                        Button(AnyUIErrorText.text("ביטול", "Cancel"), action: cancel)
                    }
                }
            }
            .navigationDestination(for: AnyNativeCreationKind.self) { choice in
                switch choice {
                case .document, .note, .folder:
                    AnyNativeNameForm(title: AnyUIErrorText.text("יצירה", "Create"), initialValue: "",
                        commit: { title in
                            commit(choice == .folder ? .folder : .writingDocument, choice == .note, title)
                        }, cancel: cancel)
                case .bookmarkTypes:
                    List(bookmarkTypes) { type in
                        Button(type.name) { path.append(.bookmarkURL(type.id)) }
                            .accessibilityIdentifier("any-native-bookmark-type-" + type.id)
                    }
                    .navigationTitle(AnyUIErrorText.text("סוג סימנייה", "Bookmark type"))
                case .bookmarkURL(let typeID):
                    AnyNativeBookmarkURLForm(commit: { value in bookmarkCommit(typeID, value) }, cancel: cancel)
                }
            }
        }
        .presentationDetents([.medium])
    }
}

private struct AnyNativeBookmarkURLForm: View {
    let commit: (String) -> Void
    let cancel: () -> Void
    @State private var value = ""
    @State private var submitted = false
    @State private var invalidURL = false
    @FocusState private var focused: Bool

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                AnytypeTextField(placeholder: Loc.Set.Bookmark.Create.placeholder,
                                 font: .uxBodyRegular, text: $value)
                    .foregroundStyle(Color.Text.primary)
                    .keyboardType(.URL)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .submitLabel(.done)
                    .focused($focused)
                    .accessibilityLabel(Loc.Set.Bookmark.Create.placeholder)
                    .accessibilityIdentifier("any-native-bookmark-url-input")
                    .onSubmit(submit)
                Spacer(minLength: 8)
                Button(Loc.create, action: submit)
                    .font(AnytypeFontBuilder.font(anytypeFont: .uxBodyRegular))
                    .foregroundStyle(isDisabled ? Color.Text.tertiary : Color.Control.accent100)
                    .disabled(isDisabled)
                    .accessibilityIdentifier("any-native-bookmark-create")
            }
            .padding(.horizontal, 20)
            .frame(minHeight: 48)
            Spacer().frame(height: 12)
        }
        .background(Color.Background.secondary)
        .navigationTitle(AnyUIErrorText.text("סימנייה חדשה", "New bookmark"))
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(AnyUIErrorText.text("ביטול", "Cancel")) { focused = false; cancel() }
            }
        }
        .alert(Loc.Set.Bookmark.Error.message, isPresented: $invalidURL) {
            Button(AnyUIErrorText.text("אישור", "OK"), role: .cancel) {}
        }
        .task { focused = true }
    }

    private var isDisabled: Bool { value.isEmpty || submitted }

    private func submit() {
        guard !isDisabled else { return }
        guard let url = AnytypeURL(string: value),
              AnyNativeBookmarkCreationBinding.websiteURL(url.absoluteString) != nil else {
            invalidURL = true; return
        }
        submitted = true; focused = false
        commit(url.absoluteString)
    }
}

private struct AnyNativeNameSheet: View {
    let title: String
    let initialValue: String
    let commit: (String) -> Void
    let cancel: () -> Void

    var body: some View {
        NavigationStack {
            AnyNativeNameForm(title: title, initialValue: initialValue, commit: commit, cancel: cancel)
        }
        .presentationDetents([.medium])
    }
}

private struct AnyNativeNameForm: View {
    let title: String
    let commit: (String) -> Void
    let cancel: () -> Void
    @State private var value: String
    @FocusState private var focused: Bool

    init(title: String, initialValue: String, commit: @escaping (String) -> Void,
         cancel: @escaping () -> Void) {
        self.title = title; self.commit = commit; self.cancel = cancel
        _value = State(initialValue: initialValue)
    }

    var body: some View {
        Form {
            TextField(AnyUIErrorText.text("כותרת", "Title"), text: $value, axis: .vertical)
                .focused($focused)
                .accessibilityIdentifier("any-native-name-input")
        }
        .navigationTitle(title)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(AnyUIErrorText.text("ביטול", "Cancel")) {
                    focused = false
                    cancel()
                }
            }
            ToolbarItem(placement: .confirmationAction) {
                Button(AnyUIErrorText.text("שמירה", "Save")) {
                    focused = false
                    commit(value)
                }.disabled(value.utf8.count > 4096 || value.contains("\0"))
                    .accessibilityIdentifier("any-native-name-confirm")
            }
        }
        .task { focused = true }
    }
}
#endif
