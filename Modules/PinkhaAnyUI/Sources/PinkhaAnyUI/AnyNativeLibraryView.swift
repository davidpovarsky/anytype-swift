#if canImport(UIKit) && canImport(SwiftUI)
import Foundation
import SwiftUI
import UniformTypeIdentifiers
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

private struct AnyNativeNameSubmission {
    let item: AnyHierarchyItem?
    let kind: PinkhaHierarchyNodeKind
    let parentID: String?
    let isNote: Bool
    let title: String
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

    public init(client: AnyHTTPClient, session: AnyApplicationSession,
                objects: AnyNativeObjectCreator, blocks: AnyNativeBlockCreator,
                capabilities: AnyUIFoundationCapabilities,
                onRequestClose: @escaping @MainActor () async -> Void,
                lifetime: AnyUIPresentationLifetime, recovery: AnyNativeLibraryRecovery) {
        _model = State(initialValue: AnyLibraryPresentation(client: client, session: session,
            objects: objects, blocks: blocks, capabilities: capabilities, lifetime: lifetime, recovery: recovery))
        _path = State(initialValue: recovery.workspace == session.workspace ? recovery.navigation : [])
        self.onRequestClose = onRequestClose; self.lifetime = lifetime
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
        }
        .sheet(item: $nameRequest, onDismiss: submitAfterNameDismissal) { request in
            if let item = request.item {
                AnyNativeNameSheet(title: AnyUIErrorText.text("שינוי שם", "Rename"),
                    initialValue: item.title, commit: { title in
                        finishNaming(request, title: title, kind: request.kind, isNote: request.isNote)
                    }, cancel: { cancelNaming(request) })
            } else {
                AnyNativeCreationSheet(commit: { kind, isNote, title in
                    finishNaming(request, title: title, kind: kind, isNote: isNote)
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
                        }
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
                              kind: PinkhaHierarchyNodeKind, isNote: Bool) {
        guard nameRequest?.id == request.id else { return }
        guard lifetime.isActive, model.canWrite else {
            pendingNameSubmission = nil
            nameRequest = nil
            return
        }
        pendingNameSubmission = .init(item: request.item, kind: kind,
            parentID: request.parentID, isNote: isNote, title: title)
        nameRequest = nil
    }

    private func cancelNaming(_ request: AnyNativeNameRequest) {
        guard nameRequest?.id == request.id else { return }
        pendingNameSubmission = nil
        nameRequest = nil
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
                                    Label(pending.plan.title, systemImage: pending.plan.kind == .folder ? "folder" : "doc")
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
            .contextMenu {
                Button(AnyUIErrorText.text("שינוי שם", "Rename"), systemImage: "pencil") {
                    beginNaming(.init(item: item.native, kind: item.kind, parentID: item.parentID, isNote: false))
                }.disabled(!model.canWrite)
                Button(AnyUIErrorText.text("העברה", "Move"), systemImage: "folder") { moveItem = item.native }
                    .disabled(!model.canWrite)
                    .accessibilityIdentifier("any-native-hierarchy-move")
                Button(AnyUIErrorText.text("העברה לסל המחזור", "Move to Bin"), systemImage: "trash", role: .destructive) {
                    removeItem = item.native
                }.disabled(!model.canWrite)
            }

            if model.canWrite && !editMode.isEditing {
                Image(systemName: "line.3.horizontal")
                    .foregroundStyle(.secondary)
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel(Text(AnyUIErrorText.text("גרירה של ", "Drag ") +
                        (item.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : item.title)))
                    .accessibilityHint(Text(AnyUIErrorText.text("גרירה לתיקייה כדי להעביר את הפריט.",
                                                              "Drag into a folder to move this item.")))
                    .accessibilityIdentifier("any-native-hierarchy-drag-\(item.objectID)")
                    .draggable("pinkha-any-node|\(model.session.workspace.spaceID)|\(item.objectID)")
            }
        }
        .accessibilityElement(children: .contain)
        // Start loading in the List drop callback while the provider is available.
        // Revalidate the mounted workspace when asynchronous loading completes.
        .onDrop(of: [.utf8PlainText], isTargeted: nil) { providers in
            guard lifetime.isActive, model.canWrite, !editMode.isEditing,
                  providers.count == 1, let provider = providers.first,
                  provider.canLoadObject(ofClass: NSString.self) else { return false }
            _ = provider.loadObject(ofClass: NSString.self) { value, error in
                guard error == nil, let payload = value as? String else { return }
                Task { @MainActor in
                    guard lifetime.isActive, model.canWrite, !editMode.isEditing,
                          payload.utf8.count <= 1024 else { return }
                    let parts = payload.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
                    guard parts.count == 3, parts[0] == "pinkha-any-node",
                          parts[1] == model.session.workspace.spaceID,
                          model.hierarchy?.itemsByID[parts[2]] != nil,
                          let destination = model.hierarchy?.itemsByID[item.objectID] else { return }
                    await model.move(objectID: parts[2],
                                     parentID: destination.kind == .folder ? destination.objectID : destination.parentID,
                                     beforeSiblingID: destination.kind == .folder ? nil : destination.objectID)
                }
            }
            return true
        }
    }

    private func documents(notesOnly: Bool) -> some View {
        List(model.allDocuments.filter { !notesOnly || $0.isNote }) { item in documentRow(item) }
            .navigationTitle(notesOnly ? AnyUIErrorText.text("הערות", "Notes") :
                                        AnyUIErrorText.text("כל המסמכים", "All documents"))
            .refreshable { await model.refresh() }
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
    case document, note, folder
}

private struct AnyNativeCreationSheet: View {
    let commit: (PinkhaHierarchyNodeKind, Bool, String) -> Void
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
                AnyNativeNameForm(title: AnyUIErrorText.text("יצירה", "Create"), initialValue: "",
                    commit: { title in
                        commit(choice == .folder ? .folder : .writingDocument, choice == .note, title)
                    }, cancel: cancel)
            }
        }
        .presentationDetents([.medium])
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
