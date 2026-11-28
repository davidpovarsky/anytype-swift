#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import Observation
import PinkhaEngineHost
import PinkhaAnyHost
import PinkhaAnyIntegration

/// Non-authority saved selections and document rows are displayed only for the
/// explicitly selected destination. Every native open uses the original
/// presentation's context owner, session and current generation checks.
@MainActor
@Observable
final class PinkhaImportedDocumentsPresentation {
    struct SavedImport: Identifiable {
        let selection: PinkhaMigrationSelectionStore.SavedSelection

        var id: Data {
            var bytes = Data()
            for value in [selection.sourceAccountID, selection.sourceSpaceID,
                          selection.captureManifestSHA256] {
                let part = Data(value.utf8)
                bytes.append(contentsOf: String(part.count).utf8)
                bytes.append(58)
                bytes.append(part)
            }
            return bytes
        }
    }

    struct DocumentRoute: Identifiable {
        let id: UUID
    }

    struct Editor: Identifiable {
        let id: UUID
        let mount: PinkhaEmbeddedAnyImportedDocumentMount
    }

    enum Phase {
        case idle, savedImports, documents, openingDocument, closingDocument
    }

    private enum BrowserError: Error {
        case destinationChanged, duplicateDocument, closedMount
    }

    let destination: PinkhaEmbeddedAnyDestinationSelection
    private(set) var savedImports: [SavedImport] = []
    private(set) var selectedImport: SavedImport?
    private(set) var documents: [PinkhaEmbeddedAnyImportedDocument] = []
    private(set) var documentRoute: DocumentRoute?
    private(set) var editor: Editor?
    private(set) var phase: Phase = .idle
    private(set) var problem: String?
    private(set) var isClosed = false
    private(set) var isBusy = false

    private let presentation: PinkhaEmbeddedAnyPresentation
    private let selections: PinkhaMigrationSelectionStore
    @ObservationIgnored private var work: Task<Void, Never>?
    @ObservationIgnored private var workID: UUID?
    @ObservationIgnored private var closeTask: Task<Void, Never>?
    @ObservationIgnored private var retainedMount: PinkhaEmbeddedAnyImportedDocumentMount?
    @ObservationIgnored private var completed: PinkhaMigrationSelectionStore.CompletedSelection?

    init(presentation: PinkhaEmbeddedAnyPresentation,
         destination: PinkhaEmbeddedAnyDestinationSelection,
         selections: PinkhaMigrationSelectionStore) {
        self.presentation = presentation
        self.destination = destination
        self.selections = selections
    }

    /// Scene registers this model before awaiting the actual owned read.
    /// Cancellation joins that read; it does not abandon an in-flight owner.
    func loadSaved() async {
        guard let task = startSavedRead() else { return }
        await withTaskCancellationHandler {
            await task.value
        } onCancel: {
            task.cancel()
        }
    }

    func requestReload() {
        _ = startSavedRead()
    }

    func requestDocuments(for requested: SavedImport) {
        guard canStart, documentRoute == nil,
              let saved = savedImports.first(where: { $0.id == requested.id }),
              let selected = saved.selection.completed else { return }
        selectedImport = saved
        documents = []
        completed = nil
        problem = nil
        installWork(phase: .documents) { [self] ticket in
            await loadDocuments(completed: selected, ticket: ticket)
        }
    }

    func requestOpen(_ requested: PinkhaEmbeddedAnyImportedDocument) {
        guard let row = documents.first(where: {
            same($0.destinationObjectID, requested.destinationObjectID) &&
            same($0.nativeTypeID, requested.nativeTypeID)
        }) else { return }
        startDocument(destinationObjectID: row.destinationObjectID)
    }

    /// Route-scoped dismissal also works while opening. It cancels the actual
    /// worker, retains that handle in a replacement cleanup task, and joins it
    /// before draining any owner that returned late.
    func requestCloseDocument(routeID: UUID) {
        guard !isClosed, documentRoute?.id == routeID else { return }
        documentRoute = nil
        editor = nil
        retainedMount?.onOpenDocument = nil
        retainedMount?.requestClose()
        let previous = work
        previous?.cancel()
        installWork(phase: .closingDocument, joining: previous) { [self] _ in
            await drainRetainedMount()
        }
    }

    /// This model is single-use after closure. No cleanup task waits for a
    /// public method that is itself awaiting that same cleanup.
    func requestClose() {
        guard !isClosed else { return }
        isClosed = true
        let pending = work
        pending?.cancel()
        documentRoute = nil
        editor = nil
        retainedMount?.onOpenDocument = nil
        retainedMount?.requestClose()
        savedImports = []
        selectedImport = nil
        documents = []
        completed = nil
        isBusy = true
        phase = .closingDocument
        closeTask = Task { @MainActor [self] in
            await pending?.value
            // The worker stores a returned mount before any later suspension,
            // even if it was cancelled while the original native open finished.
            await drainRetainedMount()
            work = nil
            workID = nil
            isBusy = false
            phase = .idle
        }
    }

    func closeAndDrain() async {
        requestClose()
        await closeTask?.value
    }

    private var canStart: Bool { !isClosed && work == nil }

    private func startSavedRead() -> Task<Void, Never>? {
        guard canStart, documentRoute == nil else { return nil }
        savedImports = []
        selectedImport = nil
        documents = []
        completed = nil
        problem = nil
        return installWork(phase: .savedImports) { [self] ticket in
            do {
                try await requireDestination(ticket: ticket)
                let workspace = try AnyTorahWorkspace(accountID: destination.accountID,
                    spaceID: destination.spaceID)
                let saved = try await selections.savedSelections(
                    networkID: destination.networkID, workspace: workspace)
                try await requireDestination(ticket: ticket)
                savedImports = saved.map(SavedImport.init(selection:))
            } catch {
                report(error, ticket: ticket,
                    message: PinkhaMigrationText.text("Unable to read saved imports for this destination."))
            }
        }
    }

    /// The only creation point for work tasks registers each handle before the
    /// MainActor can suspend. A replacement is used only for close, and retains
    /// the previous actual handle until its terminal result has been joined.
    @discardableResult
    private func installWork(
        phase newPhase: Phase,
        joining previous: Task<Void, Never>? = nil,
        _ body: @escaping @MainActor (UUID) async -> Void
    ) -> Task<Void, Never> {
        let ticket = UUID()
        workID = ticket
        isBusy = true
        phase = newPhase
        let task = Task { @MainActor [self] in
            defer {
                if workID == ticket {
                    workID = nil
                    work = nil
                    if !isClosed {
                        isBusy = false
                        phase = .idle
                    }
                }
            }
            await previous?.value
            guard !isClosed, workID == ticket else { return }
            await body(ticket)
        }
        work = task
        return task
    }

    private func loadDocuments(
        completed selected: PinkhaMigrationSelectionStore.CompletedSelection,
        ticket: UUID
    ) async {
        do {
            try await requireDestination(ticket: ticket)
            let rows: [PinkhaEmbeddedAnyImportedDocument]
            if let ordinary = selected.ordinaryReference {
                rows = try await presentation.listImportedContent(
                    expectedAccountID: destination.accountID,
                    expectedSpaceID: destination.spaceID,
                    preservationReference: selected.preservationReference,
                    preservationJournalDirectory: selected.journalParent,
                    contentReference: selected.contentReference,
                    ordinaryPropertyReference: ordinary,
                    ordinaryPropertyJournalDirectory: selected.journalParent,
                    archiveSource: .retainedFile(selected.archiveURL))
            } else {
                rows = try await presentation.listImportedContent(
                    expectedAccountID: destination.accountID,
                    expectedSpaceID: destination.spaceID,
                    preservationReference: selected.preservationReference,
                    preservationJournalDirectory: selected.journalParent,
                    contentReference: selected.contentReference,
                    archiveSource: .retainedFile(selected.archiveURL))
            }
            try await requireDestination(ticket: ticket)
            guard Set(rows.map(\.id)).count == rows.count else {
                throw BrowserError.duplicateDocument
            }
            completed = selected
            documents = rows
        } catch {
            report(error, ticket: ticket,
                message: PinkhaMigrationText.text("The saved import could not be opened."))
        }
    }

    private func startDocument(destinationObjectID: String) {
        guard canStart, let selected = completed else { return }
        problem = nil
        if documentRoute == nil { documentRoute = .init(id: UUID()) }
        editor = nil
        retainedMount?.onOpenDocument = nil
        retainedMount?.requestClose()
        installWork(phase: .openingDocument) { [self] ticket in
            await drainRetainedMount()
            do {
                try await requireDestination(ticket: ticket)
                let mount: PinkhaEmbeddedAnyImportedDocumentMount
                if let ordinary = selected.ordinaryReference {
                    mount = try await presentation.mountImportedDocument(
                        expectedAccountID: destination.accountID,
                        expectedSpaceID: destination.spaceID,
                        preservationReference: selected.preservationReference,
                        preservationJournalDirectory: selected.journalParent,
                        contentReference: selected.contentReference,
                        ordinaryPropertyReference: ordinary,
                        ordinaryPropertyJournalDirectory: selected.journalParent,
                        archiveSource: .retainedFile(selected.archiveURL),
                        destinationObjectID: destinationObjectID)
                } else {
                    mount = try await presentation.mountImportedDocument(
                        expectedAccountID: destination.accountID,
                        expectedSpaceID: destination.spaceID,
                        preservationReference: selected.preservationReference,
                        preservationJournalDirectory: selected.journalParent,
                        contentReference: selected.contentReference,
                        archiveSource: .retainedFile(selected.archiveURL),
                        destinationObjectID: destinationObjectID)
                }
                // Retain the actual result before checking cancellation or
                // suspending. Both this worker and the final close can drain it.
                retainedMount = mount
                try await requireDestination(ticket: ticket)
                guard !mount.isClosed, documentRoute != nil else {
                    throw BrowserError.closedMount
                }
                let editorID = UUID()
                mount.onOpenDocument = { [weak self, weak mount] objectID, _ in
                    guard let self, let mount, !self.isClosed,
                          self.editor?.id == editorID,
                          self.retainedMount === mount, !mount.isClosed else { return }
                    // A title/link label is never authority. The old mount is
                    // closed first; original withDocument must admit this exact
                    // destination ID in the same selected imported context.
                    self.startDocument(destinationObjectID: objectID)
                }
                editor = .init(id: editorID, mount: mount)
            } catch {
                await drainRetainedMount()
                report(error, ticket: ticket,
                    message: PinkhaMigrationText.text("This document could not be opened in the selected import."))
            }
        }
    }

    private func drainRetainedMount() async {
        guard let mount = retainedMount else { return }
        mount.onOpenDocument = nil
        mount.requestClose()
        await mount.closeAndDrain()
        if retainedMount === mount { retainedMount = nil }
    }

    private func requireDestination(ticket: UUID) async throws {
        try Task.checkCancellation()
        guard !isClosed, workID == ticket else { throw CancellationError() }
        let current = try await presentation.selectedDestination()
        try Task.checkCancellation()
        guard !isClosed, workID == ticket else { throw CancellationError() }
        guard same(current.accountID, destination.accountID),
              same(current.spaceID, destination.spaceID),
              same(current.networkID, destination.networkID) else {
            throw BrowserError.destinationChanged
        }
    }

    private func report(_ error: any Error, ticket: UUID, message: String) {
        guard !isClosed, workID == ticket, !Task.isCancelled else { return }
        if let browserError = error as? BrowserError, case .destinationChanged = browserError {
            problem = PinkhaMigrationText.text("The selected destination has changed. Close this browser and open it again.")
            requestClose()
        } else if !(error is CancellationError) {
            problem = message
        }
    }

    private func same(_ left: String, _ right: String) -> Bool {
        Data(left.utf8) == Data(right.utf8)
    }
}
#endif
