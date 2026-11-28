#if PINKHA_DUAL_ENGINE_RUNTIME
import SwiftUI
import PinkhaEngineHost

/// Scene presents this sheet over the retained original Any root. Opening an
/// imported document adds the original editor above it; it does not replace the
/// workspace owner or construct another account session.
@MainActor
struct PinkhaImportedDocumentsView: View {
    @Bindable private var model: PinkhaImportedDocumentsPresentation
    private let onClose: @MainActor () async -> Void
    @State private var closeRequest: Task<Void, Never>?

    init(model: PinkhaImportedDocumentsPresentation,
         onClose: @escaping @MainActor () async -> Void) {
        self.model = model
        self.onClose = onClose
    }

    var body: some View {
        NavigationStack {
            List {
                Section(PinkhaMigrationText.text("Destination")) {
                    if !model.destination.displayName.isEmpty {
                        Text(model.destination.displayName).font(.headline)
                    }
                    identity(PinkhaMigrationText.text("Account ID"), model.destination.accountID)
                    identity(PinkhaMigrationText.text("Space ID"), model.destination.spaceID)
                }
                Section(PinkhaMigrationText.text("Saved imports")) {
                    if model.savedImports.isEmpty, !model.isBusy {
                        Text(PinkhaMigrationText.text("No saved imports for this Space."))
                            .foregroundStyle(.secondary)
                    }
                    ForEach(model.savedImports) { saved in
                        if saved.selection.completed != nil {
                            Button {
                                model.requestDocuments(for: saved)
                            } label: {
                                savedRow(saved, completed: true)
                            }
                            .buttonStyle(.plain)
                            .disabled(model.isBusy || model.isClosed)
                        } else {
                            savedRow(saved, completed: false)
                        }
                    }
                }
                if let selected = model.selectedImport {
                    Section(PinkhaMigrationText.text("Documents")) {
                        identity(PinkhaMigrationText.text("Source account ID"),
                                 selected.selection.sourceAccountID)
                        identity(PinkhaMigrationText.text("Source Space ID"),
                                 selected.selection.sourceSpaceID)
                        if model.documents.isEmpty, !model.isBusy, model.problem == nil {
                            Text(PinkhaMigrationText.text("No documents are available in this import."))
                                .foregroundStyle(.secondary)
                        }
                        ForEach(model.documents) { row in
                            Button {
                                model.requestOpen(row)
                            } label: {
                                VStack(alignment: .leading, spacing: 5) {
                                    Text(row.destinationObjectID)
                                        .font(.body.monospaced())
                                        .foregroundStyle(.primary)
                                    HStack(alignment: .firstTextBaseline) {
                                        Text(PinkhaMigrationText.text("Type ID"))
                                        Text(row.nativeTypeID).font(.caption.monospaced())
                                    }
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.vertical, 4)
                            }
                            .buttonStyle(.plain)
                            .disabled(model.isBusy || model.isClosed)
                        }
                    }
                }
                if model.isBusy {
                    Section { ProgressView(phaseText) }
                }
                if let problem = model.problem {
                    Section {
                        Text(problem)
                            .foregroundStyle(.secondary)
                            .accessibilityIdentifier("pinkha.imported-documents.problem")
                    }
                }
            }
            .navigationTitle(PinkhaMigrationText.text("Imported documents"))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(PinkhaMigrationText.text("Close")) { closeBrowser() }
                        .disabled(closeRequest != nil)
                        .accessibilityIdentifier("pinkha.imported-documents.close")
                }
                ToolbarItem(placement: .primaryAction) {
                    Button(PinkhaMigrationText.text("Reload")) { model.requestReload() }
                        .disabled(model.isBusy || model.isClosed)
                        .accessibilityIdentifier("pinkha.imported-documents.reload")
                }
            }
        }
        .interactiveDismissDisabled(true)
        .sheet(item: Binding(
            get: { model.documentRoute },
            // Only an exact route-scoped close changes this value. An old
            // modal's dismissal cannot close a newer document route.
            set: { _ in }
        )) { route in
            documentSheet(route)
        }
    }

    private var phaseText: String {
        switch model.phase {
        case .idle: PinkhaMigrationText.text("Imported documents")
        case .savedImports: PinkhaMigrationText.text("Loading saved imports…")
        case .documents: PinkhaMigrationText.text("Reading imported documents…")
        case .openingDocument: PinkhaMigrationText.text("Opening document…")
        case .closingDocument: PinkhaMigrationText.text("Closing document…")
        }
    }

    private func identity(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.body.monospaced()).textSelection(.enabled)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func savedRow(
        _ saved: PinkhaImportedDocumentsPresentation.SavedImport,
        completed: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            identity(PinkhaMigrationText.text("Source account ID"),
                     saved.selection.sourceAccountID)
            identity(PinkhaMigrationText.text("Source Space ID"),
                     saved.selection.sourceSpaceID)
            if completed {
                Label(PinkhaMigrationText.text("Completion recorded"), systemImage: "checkmark.circle")
                    .font(.caption)
                Text(PinkhaMigrationText.text("Open documents"))
                    .font(.subheadline).foregroundStyle(.tint)
            } else {
                Label(PinkhaMigrationText.text("No recorded completion"), systemImage: "clock")
                    .font(.caption).foregroundStyle(.secondary)
                Text(PinkhaMigrationText.text("This import is incomplete or uncertain. It cannot be opened here."))
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 5)
    }

    private func documentSheet(
        _ route: PinkhaImportedDocumentsPresentation.DocumentRoute
    ) -> some View {
        NavigationStack {
            Group {
                if let editor = model.editor, !editor.mount.isClosed {
                    PinkhaEmbeddedAnyImportedDocumentView(mount: editor.mount)
                        .id(editor.id)
                } else if model.isBusy {
                    ProgressView(phaseText)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Text(model.problem ?? PinkhaMigrationText.text("This document is no longer open."))
                        .multilineTextAlignment(.center)
                        .padding()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(PinkhaMigrationText.text("Close document")) {
                        model.requestCloseDocument(routeID: route.id)
                    }
                    .accessibilityIdentifier("pinkha.imported-documents.close-document")
                }
            }
        }
        .interactiveDismissDisabled(true)
    }

    private func closeBrowser() {
        guard closeRequest == nil else { return }
        model.requestClose()
        // This UI callback is retained independently from model work. Its
        // closeAndDrain call joins only the model's native-work cleanup task.
        closeRequest = Task { @MainActor in
            await model.closeAndDrain()
            await onClose()
        }
    }
}
#endif
