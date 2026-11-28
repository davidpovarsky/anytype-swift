import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

/// A source file can already be in private app storage, or can be fetched once
/// through the existing native Files API into an explicitly new private path.
/// No destination import/prepare/commit route is called by either choice.
public enum AnyNativeImportedContextArchiveSource: Sendable {
    case retainedFile(URL)
    case nativeDownload(to: URL)
}

/// The cold-open result keeps historical source data and current native routing
/// separate. A mapped Type ID remains a routing hint: the existing definition
/// and Type-reference stores check its current native state when it is used.
public struct AnyNativeImportedContext: Sendable {
    public let reference: AnyNativeImportedContextReference
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let engineBinding: AnyNativeAccountRunBinding
    public let savedPlan: AnyDestinationMigrationPlan
    public let mappings: [AnyDestinationMigrationMapping]
    public let sourceCatalog: AnyHeartNativeDefinitionCatalog
    public let definitionDirectory: AnyNativeImportedDefinitionDirectory
    public let catalogDirectory: AnyNativeImportedCatalogDirectory
    public let typeReferences: AnyHeartNativeTypeReferencePlan
    public let observedCatalogRecordCount: Int
    /// nil for a preservation-only open. A catalog carrier never fills this.
    public let content: AnyNativeImportedContentContext?
    /// A separate completed supplement, admitted through current native reads.
    public let ordinaryProperties: AnyNativeImportedOrdinaryPropertyContext?
    public var originalHistoryReconstructed: Bool { false }
    public var permitsMigrationReplay: Bool { false }
    public var qualifiesWholeSourceBehavior: Bool { false }
    public var isAtomicWholeSpaceObservation: Bool { false }
}

/// Owns presentation work within the *existing* AnyApplicationSession. It does
/// not create a new account/Space session or mint a replacement lease. Closing
/// this context cancels and drains only work registered through withContext.
public actor AnyNativeImportedContextOwner {
    public nonisolated let workspace: AnyTorahWorkspace
    public nonisolated let generation: UUID
    private let session: AnyApplicationSession
    private let client: AnyHTTPClient
    private let context: AnyNativeImportedContext
    private let ordinaryJournalDirectory: URL?
    private var closed = false
    private var calls: [UUID: @Sendable () -> Void] = [:]
    private var drainWaiters: [CheckedContinuation<Void, Never>] = []

    private init(session: AnyApplicationSession, client: AnyHTTPClient,
                 context: AnyNativeImportedContext, ordinaryJournalDirectory: URL? = nil) {
        self.session = session; self.client = client; self.context = context
        self.ordinaryJournalDirectory = ordinaryJournalDirectory
        workspace = context.workspace; generation = context.generation
    }

    /// Restores the exact saved plan/mapping and complete admitted source file.
    /// It checks every original catalog row through the existing signed native
    /// reader, but does not demand that ordinary documents still equal their
    /// initial imported contents. No missing journal/archive is repaired.
    public static func open(
        client: AnyHTTPClient, session: AnyApplicationSession,
        reference: AnyNativeImportedContextReference, journalDirectory: URL,
        archiveSource: AnyNativeImportedContextArchiveSource
    ) async throws -> AnyNativeImportedContextOwner {
        try await open(client: client, session: session, reference: reference,
            journalDirectory: journalDirectory, archiveSource: archiveSource, completedContent: nil)
    }

    /// Opens the real current-content projection of the already completed whole
    /// preservation checkpoint. The separate locator identifies that view; it
    /// never creates a second plan, repeats migration or uses the catalog carrier
    /// as a document. Source keys and native intents retain the original binding.
    public static func openContent(
        client: AnyHTTPClient, session: AnyApplicationSession,
        preservationReference: AnyNativeImportedContextReference,
        preservationJournalDirectory: URL,
        contentReference: AnyNativeImportedContentContextReference,
        archiveSource: AnyNativeImportedContextArchiveSource
    ) async throws -> AnyNativeImportedContextOwner {
        _ = try contentReference.binding(preservation: preservationReference)
        return try await open(client: client, session: session, reference: preservationReference,
            journalDirectory: preservationJournalDirectory, archiveSource: archiveSource,
            completedContent: contentReference)
    }

    /// Explicitly adds the completed Ordinary14 namespace to the existing
    /// content view. It opens no session, replays no migration, and never repairs
    /// a missing journal. Both caller-supplied locators remain non-authoritative.
    public static func openContent(
        client: AnyHTTPClient, session: AnyApplicationSession,
        preservationReference: AnyNativeImportedContextReference,
        preservationJournalDirectory: URL,
        contentReference: AnyNativeImportedContentContextReference,
        ordinaryPropertyReference: AnyNativeImportedOrdinaryPropertyReference,
        ordinaryPropertyJournalDirectory: URL,
        archiveSource: AnyNativeImportedContextArchiveSource
    ) async throws -> AnyNativeImportedContextOwner {
        _ = try contentReference.binding(preservation: preservationReference)
        _ = try ordinaryPropertyReference.binding(preservation: preservationReference)
        return try await open(client: client, session: session, reference: preservationReference,
            journalDirectory: preservationJournalDirectory, archiveSource: archiveSource,
            completedContent: contentReference, completedOrdinary: ordinaryPropertyReference,
            ordinaryJournalDirectory: ordinaryPropertyJournalDirectory)
    }

    private static func open(
        client: AnyHTTPClient, session: AnyApplicationSession,
        reference: AnyNativeImportedContextReference, journalDirectory: URL,
        archiveSource: AnyNativeImportedContextArchiveSource,
        completedContent: AnyNativeImportedContentContextReference?,
        completedOrdinary: AnyNativeImportedOrdinaryPropertyReference? = nil,
        ordinaryJournalDirectory: URL? = nil
    ) async throws -> AnyNativeImportedContextOwner {
        guard (completedOrdinary == nil) == (ordinaryJournalDirectory == nil),
              completedOrdinary == nil || completedContent != nil else {
            throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint
        }
        if let completedOrdinary { _ = try completedOrdinary.binding(preservation: reference) }
        try requireScope(client: client, session: session, reference: reference)
        let context = try await session.perform { lease in
            guard lease.generation == session.generation,
                  AnyImportedContextAdmission.sameWorkspace(lease.workspace, reference.binding.workspace) else {
                throw AnyHostError.wrongWorkspace
            }
            try await lease.validate()
            let run = try await client.nativeAccountRunBinding(expectedNetworkID: reference.destinationNetworkID)
            let admission = AnyImportedContextAdmission(client: client, lease: lease, binding: run)
            try await admission.validate()
            // Private journal content is not read until current authority and
            // the same existing application lease have both been admitted.
            let checkpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                journalDirectory: journalDirectory, binding: reference.binding)
            guard checkpoint.checkpointSHA256 == reference.checkpointSHA256,
                  AnyNativeImportedContextReference.sameBinding(checkpoint.plan.binding, reference.binding) else {
                throw AnyNativeImportedContextError.changedCheckpoint
            }
            let archive = try AnyImportedContextArchiveIntent(checkpoint: checkpoint, reference: reference)
            let before = try await archive.currentReceipt(admission)
            let file: URL
            switch archiveSource {
            case .retainedFile(let path): file = path
            case .nativeDownload(let path):
                _ = try await client.downloadFileContent(
                    spaceID: reference.binding.workspace.spaceID, fileID: archive.fileID,
                    size: archive.intent.size, mime: archive.intent.mime, to: path,
                    expectedSHA256: archive.intent.contentSHA256,
                    authorize: { try await admission.validate() })
                file = path
            }
            try await admission.validate()
            let bytes = try AnyImportedContextPrivateArchive.read(file,
                expectedBytes: reference.archiveBytes, expectedSHA256: reference.archiveSHA256)
            let expected = try reference.expectedArchiveBinding()
            let reopened = try AnyHeartNativePreservationArchive(restoring: bytes, expected: expected)
            let restored = try AnyHeartNativePreservationArchive.restore(bytes, expected: expected)
            let preservation = try AnyHeartNativeSourcePreservation(bundle: restored.bundle,
                definitionEvidence: restored.definitionEvidence, archive: reopened)
            let exactPlan = try preservation.preservationPlan(workspace: reference.binding.workspace,
                storeID: reference.binding.storeID, planID: reference.binding.planID)
            guard exactPlan.canonicalBytes == checkpoint.plan.canonicalBytes,
                  Data(preservation.archiveItemSourceKey.utf8) == Data(reference.archiveSourceKey.utf8) else {
                throw AnyNativeImportedContextError.changedCheckpoint
            }
            var definitions = try AnyNativeImportedDefinitionDirectory(plan: checkpoint.plan,
                mappings: checkpoint.mappings,
                supplementalCanonicalDefinitions: reference.supplementalCanonicalDefinitions)
            let directory = try AnyNativeImportedCatalogDirectory(plan: checkpoint.plan, mappings: checkpoint.mappings)
            let catalog = try restored.definitionEvidence.catalog(bundle: restored.bundle)
            let ordinary: AnyNativeImportedOrdinaryPropertyContext?
            if let completedOrdinary {
                guard let ordinaryJournalDirectory else {
                    throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint
                }
                try await admission.validate()
                let ordinaryBinding = try completedOrdinary.binding(preservation: reference)
                let savedOrdinary = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                    journalDirectory: ordinaryJournalDirectory, binding: ordinaryBinding)
                let value = try AnyNativeImportedOrdinaryPropertyContext(reference: completedOrdinary,
                    preservationReference: reference, bundle: restored.bundle,
                    completedPreservationPlan: checkpoint.plan,
                    completedPreservationMappings: checkpoint.mappings, checkpoint: savedOrdinary)
                definitions = try value.merging(into: definitions)
                try await admission.validateOrdinary(value, definitions: definitions,
                    journalDirectory: ordinaryJournalDirectory)
                ordinary = value
            } else { ordinary = nil }
            let references = try AnyHeartNativeTypeReferencePlan(catalog: catalog, directory: definitions)
            let reader = try AnyNativeImportedCatalogStore(client: client, workspace: reference.binding.workspace)
            for entry in directory.entries {
                try await admission.validate()
                let current = try await reader.read(sourceObjectID: entry.sourceObjectID,
                                                     directory: directory, lease: lease)
                guard current.generation == lease.generation,
                      Data(current.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8),
                      current.entry.evidence == entry.evidence,
                      Data(current.entry.sourceObjectID.utf8) == Data(entry.sourceObjectID.utf8) else {
                    throw AnyNativeImportedContextError.changedArchive
                }
                try await admission.validate()
            }
            let content: AnyNativeImportedContentContext?
            if let completedContent {
                try await admission.validate()
                let contentBinding = try completedContent.binding(preservation: reference)
                guard AnyNativeImportedContextReference.sameBinding(contentBinding, checkpoint.plan.binding) else {
                    throw AnyNativeImportedContentContextError.changedContentCheckpoint
                }
                let value = try AnyNativeImportedContentContext(reference: completedContent,
                    preservationReference: reference, preservation: preservation, checkpoint: checkpoint,
                    catalog: catalog, catalogCarrierObjectIDs: directory.entries.map(\.objectID),
                    ordinaryProperties: ordinary)
                let definitionsReader = try AnyNativeImportedDefinitionStore(client: client,
                    workspace: lease.workspace)
                for entry in value.definitionDirectory.entries {
                    try await admission.validate()
                    let observed = try await definitionsReader.read(sourceObjectID: entry.sourceObjectID,
                        directory: value.definitionDirectory, lease: lease)
                    guard observed.generation == lease.generation,
                          Data(observed.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8) else {
                        throw AnyNativeImportedContentContextError.changedContentCheckpoint
                    }
                    try await admission.validate()
                }
                for entry in value.documents {
                    try await admission.validateDocument(entry, content: value)
                }
                content = value
            } else { content = nil }
            let after = try await archive.currentReceipt(admission)
            guard try AnyHostCanonical.bytes(before, maximumBytes: 65_536) ==
                AnyHostCanonical.bytes(after, maximumBytes: 65_536) else {
                throw AnyNativeImportedContextError.changedArchive
            }
            try await admission.validate()
            return AnyNativeImportedContext(reference: reference, workspace: lease.workspace,
                generation: lease.generation, engineStartedAt: lease.engineStartedAt,
                engineBinding: run, savedPlan: checkpoint.plan, mappings: checkpoint.mappings,
                sourceCatalog: catalog, definitionDirectory: definitions, catalogDirectory: directory,
                typeReferences: references, observedCatalogRecordCount: directory.entries.count,
                content: content, ordinaryProperties: ordinary)
        }
        // The original session performs its last asynchronous run check before
        // this separate delivery observation. The final shared journal read and
        // comparison contain no await inside the active parent actor boundary.
        return try await session.deliverImportedContextObservation {
            let finalCheckpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                journalDirectory: journalDirectory, binding: reference.binding)
            guard finalCheckpoint.checkpointSHA256 == reference.checkpointSHA256,
                  finalCheckpoint.plan.canonicalBytes == context.savedPlan.canonicalBytes else {
                throw AnyNativeImportedContextError.changedCheckpoint
            }
            if let completedContent {
                guard let content = context.content,
                      finalCheckpoint.checkpointSHA256 == completedContent.contentCheckpointSHA256,
                      finalCheckpoint.plan.canonicalBytes == content.savedPlan.canonicalBytes else {
                    throw AnyNativeImportedContentContextError.changedContentCheckpoint
                }
            }
            if let ordinary = context.ordinaryProperties {
                guard let ordinaryJournalDirectory else {
                    throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint
                }
                try ordinary.requirePreservation(reference, checkpoint: finalCheckpoint)
                let finalOrdinary = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                    journalDirectory: ordinaryJournalDirectory, binding: ordinary.savedPlan.binding)
                try ordinary.requireCheckpoint(finalOrdinary)
            }
            // Original content remains the original182 checkpoint. The optional
            // supplement is a distinct checkpoint. These are sequential local
            // delivery observations, not an atomic pair or whole-Space proof.
            return AnyNativeImportedContextOwner(session: session, client: client, context: context,
                ordinaryJournalDirectory: ordinaryJournalDirectory)
        }
    }

    /// A document/property consumer takes this existing lease into the native
    /// stores. No private cached source value is returned from a retired owner.
    public func withContext<Value: Sendable>(
        _ operation: @escaping @Sendable (AnyNativeImportedContext, AnyHostLease) async throws -> Value
    ) async throws -> Value {
        try requireActive()
        let id = UUID(), session = self.session, client = self.client, captured = context
        let ordinaryJournal = ordinaryJournalDirectory
        let task = Task<Value, Error> {
            try await session.perform { lease in
                guard lease.generation == captured.generation,
                      AnyImportedContextAdmission.sameWorkspace(lease.workspace, captured.workspace),
                      Data(lease.engineStartedAt.utf8) == Data(captured.engineStartedAt.utf8) else {
                    throw AnyHostError.wrongWorkspace
                }
                try await self.requireActive()
                let admission = AnyImportedContextAdmission(client: client, lease: lease,
                                                             binding: captured.engineBinding)
                try await admission.validate()
                if let ordinary = captured.ordinaryProperties {
                    guard let ordinaryJournal else {
                        throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint
                    }
                    try await admission.validateOrdinary(ordinary, definitions: captured.definitionDirectory,
                        journalDirectory: ordinaryJournal)
                }
                let value = try await operation(captured, lease)
                if let ordinary = captured.ordinaryProperties {
                    guard let ordinaryJournal else {
                        throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint
                    }
                    try await admission.validateOrdinary(ordinary, definitions: captured.definitionDirectory,
                        journalDirectory: ordinaryJournal)
                }
                try await admission.validate()
                try await self.requireActive()
                return value
            }
        }
        calls[id] = { task.cancel() }
        defer { finish(id) }
        return try await withTaskCancellationHandler {
            let value = try await task.value
            try requireActive()
            let delivered = try await session.deliverImportedContextObservation {
                if let ordinary = captured.ordinaryProperties {
                    guard let ordinaryJournal else {
                        throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint
                    }
                    let finalCheckpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                        journalDirectory: ordinaryJournal, binding: ordinary.savedPlan.binding)
                    try ordinary.requireCheckpoint(finalCheckpoint)
                }
                return value
            }
            try requireActive()
            return delivered
        } onCancel: { task.cancel() }
    }

    /// Resolve an actual editable destination document, preserving its source
    /// identity after ordinary edits. Current native READ, immutable source
    /// facts, original create identity and the selected Type are checked before
    /// and after the consumer. No catalog, xKey or display-name fallback exists.
    public func withDocument<Value: Sendable>(
        destinationObjectID: String,
        _ operation: @escaping @Sendable (
            AnyNativeImportedDocumentEntry, AnyNativeImportedContentContext, AnyHostLease
        ) async throws -> Value
    ) async throws -> Value {
        let client = self.client
        return try await withContext { context, lease in
            guard let content = context.content else {
                throw AnyNativeImportedContentContextError.missingContentCheckpoint
            }
            guard let entry = content.document(destinationObjectID: destinationObjectID) else {
                throw AnyNativeImportedContentContextError.unmappedDocument(destinationObjectID)
            }
            let admission = AnyImportedContextAdmission(client: client, lease: lease,
                binding: context.engineBinding)
            try await admission.validateDocument(entry, content: content)
            let value = try await operation(entry, content, lease)
            try await admission.validateDocument(entry, content: content)
            return value
        }
    }

    public func closeAndDrain() async {
        closed = true
        for cancel in calls.values { cancel() }
        if !calls.isEmpty {
            await withCheckedContinuation { continuation in drainWaiters.append(continuation) }
        }
    }

    public var isActive: Bool {
        get async {
            let parentActive = await session.isActive
            return !closed && parentActive
        }
    }

    private func requireActive() throws {
        guard !closed else { throw AnyNativeImportedContextError.closed }
        try Task.checkCancellation()
    }

    private func finish(_ id: UUID) {
        calls.removeValue(forKey: id)
        if calls.isEmpty {
            let waiting = drainWaiters; drainWaiters.removeAll()
            for continuation in waiting { continuation.resume() }
        }
    }

    private static func requireScope(client: AnyHTTPClient, session: AnyApplicationSession,
                                     reference: AnyNativeImportedContextReference) throws {
        guard Data(client.expectedAccountID.utf8) == Data(reference.destinationAccountID.utf8),
              AnyImportedContextAdmission.sameWorkspace(session.workspace, reference.binding.workspace) else {
            throw AnyHostError.wrongWorkspace
        }
    }
}

/// A final local observation on the existing parent actor. It performs no
/// native request and does not claim an atomic remote ACL or whole-Space read.
/// Parent retirement cannot interleave with the synchronous callback.
private extension AnyApplicationSession {
    func deliverImportedContextObservation<Value: Sendable>(
        _ operation: @Sendable () throws -> Value
    ) throws -> Value {
        guard isActive else { throw AnyHostError.sessionClosed }
        try Task.checkCancellation()
        let value = try operation()
        try Task.checkCancellation()
        return value
    }
}

private struct AnyImportedContextAdmission: Sendable {
    let client: AnyHTTPClient
    let lease: AnyHostLease
    let binding: AnyNativeAccountRunBinding

    func validate() async throws {
        guard Data(binding.accountID.utf8) == Data(lease.workspace.accountID.utf8),
              Data(client.expectedAccountID.utf8) == Data(lease.workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        try await lease.validate()
        try await client.requireNativeAccountRun(binding)
        let value = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", lease.workspace.spaceID, "members", "me"],
            maximumResponseBytes: 65_536, authorize: { try await lease.validate() })
        guard value["identity"]?.string.map({ Data($0.utf8) }) == Data(lease.workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        // Ordinary account membership owns the private saved checkpoint. A
        // public guest-key identity is not substituted for this account.
        try AnyHTTPTorahTargetAccess.validateMember(value, workspace: lease.workspace, intent: .read)
        try await client.requireNativeAccountRun(binding)
        try await lease.validate()
    }

    func get(_ path: [String]) async throws -> AnyJSON {
        try await validate()
        let value = try await client.requestJSON(method: "GET", path: path,
            maximumResponseBytes: 65_536, authorize: { try await validate() })
        try await validate()
        return value
    }

    func validateOrdinary(_ ordinary: AnyNativeImportedOrdinaryPropertyContext,
                          definitions: AnyNativeImportedDefinitionDirectory,
                          journalDirectory: URL) async throws {
        guard Self.sameWorkspace(ordinary.savedPlan.binding.workspace, lease.workspace),
              AnyNativeImportedContextReference.sameBinding(definitions.binding, ordinary.namespace.binding),
              definitions.supplementalPropertyBindings.count == 1,
              AnyNativeImportedContextReference.sameBinding(
                definitions.supplementalPropertyBindings[0], ordinary.savedPlan.binding) else {
            throw AnyHostError.wrongWorkspace
        }
        try await validate()
        let before = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: journalDirectory, binding: ordinary.savedPlan.binding)
        try ordinary.requireCheckpoint(before)
        let driver = try await AnyDestinationNativeClients.open(client: client, plan: ordinary.savedPlan,
            authorize: { try await validate() })
        let reader = try AnyNativeImportedDefinitionStore(client: client, workspace: lease.workspace)
        try await ordinary.observe(using: driver, authorize: { try await validate() }) { sourceID in
            let observed = try await reader.read(sourceObjectID: sourceID,
                directory: definitions, lease: lease)
            guard Self.sameWorkspace(observed.workspace, lease.workspace),
                  observed.generation == lease.generation,
                  Data(observed.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8),
                  observed.matchesOriginalDescriptor, observed.nativeCreationOutcome == "committed",
                  observed.entry.intent.map({ AnyNativeImportedContextReference.sameBinding(
                    $0.binding, ordinary.savedPlan.binding) }) == true else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition(sourceID)
            }
        }
        let after = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: journalDirectory, binding: ordinary.savedPlan.binding)
        try ordinary.requireCheckpoint(after)
        try await validate()
    }

    func validateDocument(_ entry: AnyNativeImportedDocumentEntry,
                          content: AnyNativeImportedContentContext) async throws {
        guard Self.sameWorkspace(content.savedPlan.binding.workspace, lease.workspace),
              content.document(destinationObjectID: entry.objectID)?.sourceObjectID.utf8
                .elementsEqual(entry.sourceObjectID.utf8) == true else {
            throw AnyHostError.wrongWorkspace
        }
        try await validate()
        let migration = try await AnyNativePreparedMigration.open(client: client, workspace: lease.workspace,
            authorize: { try await validate() })
        guard Data(migration.capabilities.storeID.utf8) == Data(content.savedPlan.binding.storeID.utf8) else {
            throw AnyPreparedMigrationError.changedStore
        }
        let before = try await migration.status(entry.intent, authorize: { try await validate() })
        try entry.requireCurrentReceipt(before)
        let facts = try AnyNativeImportedSourceFactsStore(client: client, workspace: lease.workspace)
        let source = try await facts.read(sourceObjectID: entry.sourceObjectID,
            directory: content.sourceFactsDirectory, lease: lease)
        guard source.generation == lease.generation,
              Data(source.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8),
              Data(source.entry.objectID.utf8) == Data(entry.objectID.utf8),
              source.entry.sourceSnapshotSHA256 == entry.sourceSnapshotSHA256,
              source.entry.sourceJSONViewSHA256 == entry.sourceJSONViewSHA256 else {
            throw AnyNativeImportedContentContextError.changedDocument(entry.objectID)
        }
        try await validate()
        let raw = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", lease.workspace.spaceID, "objects", entry.objectID],
            maximumResponseBytes: 8 * 1024 * 1024, authorize: { try await validate() })
        try entry.requireCurrentObject(raw)
        let after = try await migration.status(entry.intent, authorize: { try await validate() })
        try entry.requireCurrentReceipt(after)
        guard before == after else {
            throw AnyNativeImportedContentContextError.changedDocument(entry.objectID)
        }
        try await validate()
    }

    static func sameWorkspace(_ a: AnyTorahWorkspace, _ b: AnyTorahWorkspace) -> Bool {
        Data(a.accountID.utf8) == Data(b.accountID.utf8) &&
            Data(a.spaceID.utf8) == Data(b.spaceID.utf8)
    }
}

private struct AnyImportedContextArchiveIntent: Sendable {
    let intent: AnyPreparedFileIntent
    let mapping: AnyDestinationMigrationMapping
    let fileID: String

    init(checkpoint: AnyDestinationSavedCheckpoint, reference: AnyNativeImportedContextReference) throws {
        let matches = checkpoint.plan.items.indices.filter {
            Data(checkpoint.plan.items[$0].sourceKey.utf8) == Data(reference.archiveSourceKey.utf8)
        }
        guard matches.count == 1, let index = matches.first,
              checkpoint.intents.indices.contains(index), checkpoint.mappings.indices.contains(index),
              case .file(let intent) = checkpoint.intents[index],
              intent.size == reference.archiveBytes, intent.contentSHA256 == reference.archiveSHA256,
              Data(intent.mime.utf8) == Data(AnyHeartNativePreservationArchive.mimeType.utf8),
              AnyNativeImportedContextReference.sameBinding(intent.binding, reference.binding),
              let fileID = checkpoint.mappings[index].fileID else {
            throw AnyNativeImportedContextError.unavailableArchive
        }
        self.intent = intent; mapping = checkpoint.mappings[index]; self.fileID = fileID
    }

    func currentReceipt(_ admission: AnyImportedContextAdmission) async throws -> AnyJSON {
        let binding = intent.binding
        let prefix = ["v1", "spaces", binding.workspace.spaceID, "pinkha", "migration"]
        let rawCapabilities = try await admission.get(prefix + ["file", "capabilities"])
        let capabilities = try AnyPreparedFileCapabilities(rawCapabilities, workspace: binding.workspace)
        guard same(rawCapabilities["accountId"]?.string, binding.workspace.accountID),
              same(rawCapabilities["spaceId"]?.string, binding.workspace.spaceID),
              same(capabilities.storeID, binding.storeID) else { throw AnyPreparedMigrationError.changedStore }
        let raw = try await admission.get(prefix + ["intents", intent.intentID, "file"])
        let receipt = try AnyPreparedFileReceipt(raw, intent: intent)
        guard same(raw["accountId"]?.string, binding.workspace.accountID),
              same(raw["spaceId"]?.string, binding.workspace.spaceID),
              same(raw["storeId"]?.string, binding.storeID),
              same(raw["planId"]?.string, binding.planID),
              same(raw["sourceKey"]?.string, intent.sourceKey),
              same(raw["ownerObjectId"]?.string, intent.ownerObjectID),
              receipt.isCompleteAndCurrent,
              same(receipt.fingerprint, mapping.fingerprint),
              same(receipt.objectID, mapping.objectID), same(receipt.fileID, fileID),
              receipt.recordIDs.map({ Data($0.utf8) }) == mapping.recordIDs.map({ Data($0.utf8) }),
              mapping.signedChangeIDs.contains(where: { same($0, receipt.changeID) }) else {
            throw AnyNativeImportedContextError.changedArchive
        }
        return raw
    }

    private func same(_ a: String?, _ b: String) -> Bool {
        a.map { Data($0.utf8) == Data(b.utf8) } ?? false
    }
}

private enum AnyImportedContextPrivateArchive {
    static func read(_ url: URL, expectedBytes: Int64, expectedSHA256: String) throws -> Data {
        guard url.isFileURL, (4096...Int64(AnyHeartNativePreservationArchive.maximumBytes)).contains(expectedBytes) else {
            throw AnyNativeImportedContextError.unavailableArchive
        }
        try Task.checkCancellation()
        let fd = open(url.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw AnyNativeImportedContextError.unavailableArchive }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat(), after = stat(), named = stat()
        guard fstat(fd, &before) == 0, lstat(url.path, &named) == 0,
              before.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG),
              before.st_uid == geteuid(), before.st_nlink == 1,
              before.st_mode & mode_t(0o7777) == mode_t(0o400) ||
                  before.st_mode & mode_t(0o7777) == mode_t(0o600),
              before.st_size == expectedBytes, same(before, named) else {
            throw AnyNativeImportedContextError.unavailableArchive
        }
        let maximum = Int(expectedBytes)
        var data = Data()
        while data.count <= maximum {
            try Task.checkCancellation()
            let part = try handle.read(upToCount: min(1_048_576, maximum + 1 - data.count)) ?? Data()
            if part.isEmpty { break }
            data.append(part)
        }
        guard data.count == maximum, AnyContentDigest.sha256(data) == expectedSHA256,
              fstat(fd, &after) == 0, lstat(url.path, &named) == 0,
              same(before, after), same(after, named) else {
            throw AnyNativeImportedContextError.changedArchive
        }
        try Task.checkCancellation()
        return data
    }

    private static func same(_ a: stat, _ b: stat) -> Bool {
        guard a.st_dev == b.st_dev, a.st_ino == b.st_ino, a.st_mode == b.st_mode,
              a.st_nlink == b.st_nlink, a.st_uid == b.st_uid, a.st_gid == b.st_gid,
              a.st_size == b.st_size else { return false }
        #if canImport(Darwin)
        return a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec &&
            a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
            a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec &&
            a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
        #else
        return a.st_mtim.tv_sec == b.st_mtim.tv_sec && a.st_mtim.tv_nsec == b.st_mtim.tv_nsec &&
            a.st_ctim.tv_sec == b.st_ctim.tv_sec && a.st_ctim.tv_nsec == b.st_ctim.tv_nsec
        #endif
    }
}
