#if canImport(SwiftUI)
import Foundation
import Observation
import SwiftUI
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration

/// One imported context and one original native editor, owned by the current
/// workspace presentation. References locate evidence; native admission remains
/// in openContent/withDocument and the original canonical-editor policy.
@MainActor @Observable
public final class AnyNativeImportedDocumentMount: Sendable {
    public let id = UUID()
    public let destinationObjectID: String
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public private(set) var presentation: AnyDocumentPresentation?
    public private(set) var entry: AnyNativeImportedDocumentEntry?
    public private(set) var isClosed = false
    public var onOpenDocument: ((String, String?) -> Void)?

    @ObservationIgnored private let library: AnyLibraryPresentation
    @ObservationIgnored private let lifetime: AnyUIPresentationLifetime
    @ObservationIgnored private var registration: UUID?
    @ObservationIgnored private var openingTask: Task<AnyNativeImportedContextOwner, Error>?
    @ObservationIgnored private var admissionTask: Task<AnyNativeImportedDocumentEntry, Error>?
    @ObservationIgnored private var contextOwner: AnyNativeImportedContextOwner?
    @ObservationIgnored private var closeTask: Task<Void, Never>?

    private init(library: AnyLibraryPresentation, destinationObjectID: String) throws {
        try Task.checkCancellation()
        try library.lifetime.requireActive()
        guard library.isReady, !destinationObjectID.isEmpty else {
            throw AnyHostError.incompleteDocument
        }
        self.library = library
        self.lifetime = library.lifetime
        self.destinationObjectID = destinationObjectID
        self.workspace = library.session.workspace
        self.generation = library.session.generation
        // The parent lifetime retains the mount until explicit drain removes
        // this registration; a discarded view cannot orphan the opened owner.
        registration = try lifetime.register(
            revoke: { self.requestClose() },
            drain: { await self.closeAndDrain() })
    }

    /// Uses the completed preservation/content pair without adding an ordinary
    /// property claim or treating a catalog address as an editable document.
    public static func open(
        library: AnyLibraryPresentation,
        preservationReference: AnyNativeImportedContextReference,
        preservationJournalDirectory: URL,
        contentReference: AnyNativeImportedContentContextReference,
        archiveSource: AnyNativeImportedContextArchiveSource,
        destinationObjectID: String
    ) async throws -> AnyNativeImportedDocumentMount {
        let client = library.client, session = library.session
        return try await prepare(library: library, destinationObjectID: destinationObjectID) {
            try await AnyNativeImportedContextOwner.openContent(
                client: client, session: session,
                preservationReference: preservationReference,
                preservationJournalDirectory: preservationJournalDirectory,
                contentReference: contentReference, archiveSource: archiveSource)
        }
    }

    /// Consumes only the original typed third reference and its own completed
    /// journal. This overload does not construct or qualify that producer.
    public static func open(
        library: AnyLibraryPresentation,
        preservationReference: AnyNativeImportedContextReference,
        preservationJournalDirectory: URL,
        contentReference: AnyNativeImportedContentContextReference,
        ordinaryPropertyReference: AnyNativeImportedOrdinaryPropertyReference,
        ordinaryPropertyJournalDirectory: URL,
        archiveSource: AnyNativeImportedContextArchiveSource,
        destinationObjectID: String
    ) async throws -> AnyNativeImportedDocumentMount {
        let client = library.client, session = library.session
        return try await prepare(library: library, destinationObjectID: destinationObjectID) {
            try await AnyNativeImportedContextOwner.openContent(
                client: client, session: session,
                preservationReference: preservationReference,
                preservationJournalDirectory: preservationJournalDirectory,
                contentReference: contentReference,
                ordinaryPropertyReference: ordinaryPropertyReference,
                ordinaryPropertyJournalDirectory: ordinaryPropertyJournalDirectory,
                archiveSource: archiveSource)
        }
    }

    private static func prepare(
        library: AnyLibraryPresentation, destinationObjectID: String,
        open: @escaping @Sendable () async throws -> AnyNativeImportedContextOwner
    ) async throws -> AnyNativeImportedDocumentMount {
        let mount = try AnyNativeImportedDocumentMount(
            library: library, destinationObjectID: destinationObjectID)
        let opening = Task { try await open() }
        mount.openingTask = opening
        do {
            let owner = try await withTaskCancellationHandler(operation: {
                try await opening.value
            }, onCancel: { opening.cancel() })
            // Retain a late success before checking cancellation/lifetime, so
            // cleanup can always close that actual owner.
            if mount.isClosed {
                await owner.closeAndDrain()
                throw AnyHostError.sessionClosed
            }
            mount.contextOwner = owner
            try mount.requireCurrent()
            guard sameWorkspace(owner.workspace, library.session.workspace),
                  owner.generation == library.session.generation else {
                throw AnyHostError.wrongWorkspace
            }
            let client = library.client, session = library.session
            let expectedGeneration = session.generation
            let expectedStartedAt = session.engineStartedAt
            let admission = Task {
                try await owner.withDocument(destinationObjectID: destinationObjectID) { entry, _, lease in
                    guard same(entry.objectID, destinationObjectID),
                          sameWorkspace(lease.workspace, session.workspace),
                          lease.generation == expectedGeneration,
                          same(lease.engineStartedAt, expectedStartedAt) else {
                        throw AnyHostError.wrongWorkspace
                    }
                    // A mapped custom Type is not an allowlist exemption.
                    // Require the existing native editor policy and actual Type.
                    let proof = try await AnyNativeDocumentPolicyClient(
                        client: client, workspace: lease.workspace).target(entry.objectID)
                    guard same(proof.typeID, entry.nativeTypeID) else {
                        throw AnyNativeImportedContentContextError.changedDocument(entry.objectID)
                    }
                    try await lease.validate()
                    return entry
                }
            }
            mount.admissionTask = admission
            let entry = try await withTaskCancellationHandler(operation: {
                try await admission.value
            }, onCancel: { admission.cancel() })
            try mount.requireCurrent()
            let editor = try library.makeImportedDocument(destinationObjectID)
            mount.presentation = editor
            guard editor.nativeSession === session, editor.lifetime === library.lifetime,
                  sameWorkspace(editor.workspace, session.workspace),
                  same(editor.objectID, entry.objectID) else {
                throw AnyHostError.wrongWorkspace
            }
            try editor.installImportedMount(readOperation: { _, documents, objectID, outerLease in
                try await outerLease.validate()
                guard same(objectID, destinationObjectID),
                      sameWorkspace(outerLease.workspace, session.workspace),
                      outerLease.generation == expectedGeneration,
                      same(outerLease.engineStartedAt, expectedStartedAt) else {
                    throw AnyHostError.wrongWorkspace
                }
                return try await owner.withDocument(destinationObjectID: destinationObjectID) { entry, _, lease in
                    guard same(entry.objectID, objectID),
                          sameWorkspace(lease.workspace, outerLease.workspace),
                          lease.generation == outerLease.generation,
                          same(lease.engineStartedAt, outerLease.engineStartedAt) else {
                        throw AnyHostError.wrongWorkspace
                    }
                    let read = try await documents.read(objectID: entry.objectID, lease: lease)
                    try await outerLease.validate()
                    return read
                }
            }, revoke: { [weak mount] in mount?.requestClose() })
            editor.onOpenObject = { [weak mount] objectID, blockID in
                guard let mount, !mount.isClosed, mount.lifetime.isActive else { return }
                // The Scene owns replacement; it must drain this mount before
                // opening another exact ID through the next original owner.
                mount.onOpenDocument?(objectID, blockID)
            }
            mount.entry = entry
            try mount.requireCurrent()
            return mount
        } catch {
            await mount.closeAndDrain()
            throw error
        }
    }

    /// Observations keep the original current native/account/run and private
    /// journal checks. A result cannot be delivered after this UI owner closes.
    public func withContext<Value: Sendable>(
        _ operation: @escaping @Sendable (AnyNativeImportedContext, AnyHostLease) async throws -> Value
    ) async throws -> Value {
        try requireCurrent()
        guard let contextOwner else { throw AnyHostError.sessionClosed }
        let value = try await contextOwner.withContext(operation)
        try requireCurrent()
        return value
    }

    public func withDocument<Value: Sendable>(
        _ operation: @escaping @Sendable (
            AnyNativeImportedDocumentEntry, AnyNativeImportedContentContext, AnyHostLease
        ) async throws -> Value
    ) async throws -> Value {
        try requireCurrent()
        guard let contextOwner else { throw AnyHostError.sessionClosed }
        let value = try await contextOwner.withDocument(
            destinationObjectID: destinationObjectID, operation)
        try requireCurrent()
        return value
    }

    /// Revocation is synchronous. The retained cleanup task is also joined by
    /// the parent lifetime and by an explicit Scene replacement.
    public func requestClose() {
        guard !isClosed else { return }
        isClosed = true
        openingTask?.cancel()
        admissionTask?.cancel()
        let opening = openingTask, admission = admissionTask
        let retainedOwner = contextOwner
        let editor = presentation
        presentation = nil
        entry = nil
        editor?.revoke()
        closeTask = Task { @MainActor in
            var opened: AnyNativeImportedContextOwner?
            if let opening {
                switch await opening.result {
                case .success(let owner): opened = owner
                case .failure: break // The opening caller retains its original error.
                }
            }
            // Await the raw opening task even after cancellation. Never discard
            // an original owner that completed before noticing the cancellation.
            if let opened { await opened.closeAndDrain() }
            if let retainedOwner, opened !== retainedOwner {
                await retainedOwner.closeAndDrain()
            }
            if let admission { _ = await admission.result }
            await editor?.drain()
            if let registration = self.registration {
                self.lifetime.unregister(registration)
                self.registration = nil
            }
            self.contextOwner = nil
            self.openingTask = nil
            self.admissionTask = nil
            self.onOpenDocument = nil
        }
    }

    public func closeAndDrain() async {
        requestClose()
        await closeTask?.value
    }

    private func requireCurrent() throws {
        try Task.checkCancellation()
        try lifetime.requireActive()
        guard !isClosed, library.lifetime === lifetime,
              library.session.generation == generation,
              Self.sameWorkspace(library.session.workspace, workspace) else {
            throw AnyHostError.sessionClosed
        }
    }

    nonisolated private static func same(_ a: String, _ b: String) -> Bool {
        Data(a.utf8) == Data(b.utf8)
    }

    nonisolated private static func sameWorkspace(_ a: AnyTorahWorkspace, _ b: AnyTorahWorkspace) -> Bool {
        same(a.accountID, b.accountID) && same(a.spaceID, b.spaceID)
    }
}

#if canImport(UIKit)
/// Uses the existing native editor, toolbar, property UI and child consumers.
public struct AnyNativeImportedDocumentView: View {
    @Bindable private var mount: AnyNativeImportedDocumentMount

    public init(mount: AnyNativeImportedDocumentMount) { self.mount = mount }

    public var body: some View {
        Group {
            if let presentation = mount.presentation, !mount.isClosed {
                AnyNativeDocumentView(presentation: presentation)
            }
        }
        .id(mount.id)
    }
}
#endif
#endif
