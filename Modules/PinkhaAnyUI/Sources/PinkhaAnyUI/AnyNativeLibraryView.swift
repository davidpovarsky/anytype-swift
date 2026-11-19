#if canImport(UIKit) && canImport(SwiftUI)
import Foundation
import SwiftUI
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

/// One coherent native Space. Its account/session/creators are supplied by the
/// native application owner; this entry point has no Heart object-ID fallback.
public struct AnyNativeLibraryView: View {
    @State private var model: AnyLibraryPresentation
    @State private var path: [AnyNativeLibraryDestination] = []
    @State private var nameRequest: AnyNativeNameRequest?
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
        .onChange(of: path) { _, current in
            guard lifetime.isActive else { return }
            do { try model.recovery.replaceNavigation(current, workspace: model.session.workspace) }
            catch { model.message = AnyUIErrorText.describe(error) }
        }
        .task {
            model.onOpenDocument = { id, blockID in path.append(.document(id, blockID)) }
            await model.open()
        }
        .sheet(item: $nameRequest) { request in
            AnyNativeNameSheet(title: request.item == nil ?
                AnyUIErrorText.text("יצירה", "Create") : AnyUIErrorText.text("שינוי שם", "Rename"),
                initialValue: request.item?.title ?? "") { title in
                    if let item = request.item { Task { await model.rename(item, title: title) } }
                    else { Task { await model.create(title: title, kind: request.kind,
                                                    parentID: request.parentID, isNote: request.isNote) } }
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
                            ForEach(items, id: \.objectID) { item in hierarchyRow(item) }
                                .onMove { offsets, destination in
                                    guard offsets.count == 1, let offset = offsets.first,
                                          items.indices.contains(offset) else { return }
                                    let item = items[offset]
                                    var reordered = items.map(\.objectID)
                                    reordered.move(fromOffsets: offsets, toOffset: destination)
                                    guard let index = reordered.firstIndex(of: item.objectID) else { return }
                                    let before = index + 1 < reordered.count ? reordered[index + 1] : nil
                                    Task { await model.move(objectID: item.objectID, parentID: parentID,
                                                            beforeSiblingID: before) }
                                }
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
                    Menu {
                        Button(AnyUIErrorText.text("מסמך חדש", "New document"), systemImage: "doc.badge.plus") {
                            nameRequest = .init(item: nil, kind: .writingDocument, parentID: parentID, isNote: false)
                        }.accessibilityIdentifier("any-native-new-document")
                        Button(AnyUIErrorText.text("הערה חדשה", "New Note"), systemImage: "note.text.badge.plus") {
                            nameRequest = .init(item: nil, kind: .writingDocument, parentID: parentID, isNote: true)
                        }.accessibilityIdentifier("any-native-new-note")
                        Button(AnyUIErrorText.text("תיקייה חדשה", "New folder"), systemImage: "folder.badge.plus") {
                            nameRequest = .init(item: nil, kind: .folder, parentID: parentID, isNote: false)
                        }.accessibilityIdentifier("any-native-new-folder")
                    } label: { Image(systemName: "plus") }
                        .disabled(!model.canWrite)
                        .accessibilityIdentifier("any-native-create-menu")
                }
            }
        }
    }

    private func hierarchyRow(_ item: AnyHierarchyPresentationItem) -> some View {
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
        }
        .contextMenu {
            Button(AnyUIErrorText.text("שינוי שם", "Rename"), systemImage: "pencil") {
                nameRequest = .init(item: item.native, kind: item.kind, parentID: item.parentID, isNote: false)
            }.disabled(!model.canWrite)
            Button(AnyUIErrorText.text("העברה", "Move"), systemImage: "folder") { moveItem = item.native }
                .disabled(!model.canWrite)
            Button(AnyUIErrorText.text("העברה לסל המחזור", "Move to Bin"), systemImage: "trash", role: .destructive) {
                removeItem = item.native
            }.disabled(!model.canWrite)
        }
        .draggable("pinkha-any-node|\(model.session.workspace.spaceID)|\(item.objectID)")
        .dropDestination(for: String.self) { payloads, _ in
            guard model.canWrite, payloads.count == 1 else { return false }
            let parts = payloads[0].split(separator: "|", omittingEmptySubsequences: false).map(String.init)
            guard parts.count == 3, parts[0] == "pinkha-any-node",
                  parts[1] == model.session.workspace.spaceID,
                  model.hierarchy?.itemsByID[parts[2]] != nil else { return false }
            Task {
                await model.move(objectID: parts[2], parentID: item.kind == .folder ? item.objectID : item.parentID,
                                 beforeSiblingID: item.kind == .folder ? nil : item.objectID)
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

private struct AnyNativeNameSheet: View {
    let title: String
    let commit: (String) -> Void
    @State private var value: String
    @Environment(\.dismiss) private var dismiss
    @FocusState private var focused: Bool
    init(title: String, initialValue: String, commit: @escaping (String) -> Void) {
        self.title = title; self.commit = commit; _value = State(initialValue: initialValue)
    }
    var body: some View {
        NavigationStack {
            Form {
                TextField(AnyUIErrorText.text("כותרת", "Title"), text: $value, axis: .vertical)
                    .focused($focused)
                    .accessibilityIdentifier("any-native-name-input")
            }
            .navigationTitle(title)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(AnyUIErrorText.text("ביטול", "Cancel")) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(AnyUIErrorText.text("שמירה", "Save")) {
                        commit(value); dismiss()
                    }.disabled(value.utf8.count > 4096 || value.contains("\0"))
                        .accessibilityIdentifier("any-native-name-confirm")
                }
            }
            .task { focused = true }
        }
        .presentationDetents([.medium])
    }
}
#endif
