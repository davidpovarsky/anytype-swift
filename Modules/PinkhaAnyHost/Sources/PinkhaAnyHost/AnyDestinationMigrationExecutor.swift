import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

public struct AnyDestinationMigrationMapping: Codable, Sendable {
    public let sourceKey: String
    public let sourceObjectID: String
    public let kind: String
    public let intentID: String
    public let objectID: String
    public let recordIDs: [String]
    public let fileID: String?
    public let fingerprint: String
    public let signedChangeIDs: [String]
    public let currentReceiptSHA256: String
}

/// This reports individually reconciled native operations. Full-Space semantic
/// acceptance additionally compares the source bundle with destination content
/// and file bytes; it is never inferred from a count of these receipts.
public struct AnyDestinationMigrationProgress: Sendable {
    public let binding: AnyPreparedMigrationPlanBinding
    public let source: AnyDestinationSourceBinding
    public let mappings: [AnyDestinationMigrationMapping]
    public let totalItems: Int
    public let allItemsReconciled: Bool
}

public actor AnyDestinationMigrationExecutor {
    private typealias Factory = @Sendable (AnyDestinationMigrationPlan, @escaping AnyDestinationAuthorization) async throws -> any AnyDestinationNativeDriving
    private let journalDirectory: URL
    private let factory: Factory
    private let checkpointHook: @Sendable (Int) async throws -> Void
    private var executing = false

    /// The journal parent must be a private application-owned existing folder.
    /// `verifySource` below is supplied by the native captured-source adapter;
    /// it must recheck that exact capture's current authorization/checkpoint.
    public init(client: AnyHTTPClient, journalDirectory: URL) {
        self.journalDirectory = journalDirectory
        factory = { plan, authorize in
            try await AnyDestinationNativeClients.open(client: client, plan: plan, authorize: authorize)
        }
        checkpointHook = { _ in }
    }

    /// Internal crash-boundary injection. Production always uses native HTTP.
    init(journalDirectory: URL, driver: any AnyDestinationNativeDriving,
         checkpointHook: @escaping @Sendable (Int) async throws -> Void = { _ in }) {
        self.journalDirectory = journalDirectory; factory = { _, _ in driver }
        self.checkpointHook = checkpointHook
    }

    public func execute(
        plan: AnyDestinationMigrationPlan,
        payloads: @escaping @Sendable (String) async throws -> URL,
        verifySource: @escaping @Sendable (AnyDestinationSourceBinding) async throws -> Void,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyDestinationMigrationProgress {
        guard !executing else { throw AnyDestinationMigrationError.alreadyExecuting }
        executing = true; defer { executing = false }
        try plan.requireExecutable()
        let admit: AnyDestinationAuthorization = {
            try Task.checkCancellation(); try await verifySource(plan.source)
            try await authorize(); try Task.checkCancellation()
        }
        try await admit()
        // Both the OS lock and in-actor guard remain held across suspension.
        // The OS closes the lock on process death; no timestamp lease expires
        // while an older process could still mutate the destination.
        let journal = try AnyDestinationMigrationJournal(parent: journalDirectory, plan: plan)
        let driver = try await factory(plan, admit)
        var mappings: [Data: AnyDestinationMigrationMapping] = [:]
        var ordered: [AnyDestinationMigrationMapping] = []
        var entries: [AnyDestinationJournalEntry] = []
        var propertyGroups = Set<Data>()
        var creationProperties: [Data: AnyJSON] = [:]
        for (index, item) in plan.items.enumerated() {
            try await admit()
            let resolved = try item.operation.resolved { try Self.resolve($0, mappings: mappings) }
            let resolvedBytes = try AnyDestinationMigrationJournal.encoded(resolved)
            if case .propertyUpdate(let object, let owner, let patch) = resolved {
                let group = try AnyDestinationMigrationJournal.encoded([object, owner])
                guard propertyGroups.insert(group).inserted else {
                    throw AnyDestinationMigrationError.invalidPlan("aliased property object/owner group")
                }
                try Self.requireDisjointCreationFields(object: object, owner: owner, patch: patch,
                                                       properties: creationProperties)
            }
            var entry: AnyDestinationJournalEntry
            if let previous = try journal.load(index: index) {
                guard previous.resolvedOperation == resolvedBytes else { throw AnyDestinationMigrationError.changedPlan }
                entry = previous
            } else {
                let sequence: Int64?
                if case .propertyUpdate(.native(let object), _, _) = resolved {
                    sequence = try await driver.applySequence(objectID: object, authorize: admit)
                } else { sequence = nil }
                let content: Data?
                if case .file(_, _, _, let size, let digest) = resolved, size < 4096 {
                    let url = try await payloads(item.sourceKey)
                    content = try Self.inlinePayload(url, size: size, digest: digest, sourceKey: item.sourceKey)
                } else { content = nil }
                let intent = try AnyDestinationNativeIntent.make(resolved, binding: plan.binding,
                    sourceKey: item.sourceKey, sequence: sequence, inlineContent: content)
                entry = .init(index: index, sourceKey: item.sourceKey,
                    itemSHA256: AnyContentDigest.sha256(try AnyDestinationMigrationJournal.encoded(item)),
                    resolvedOperation: resolvedBytes, expectedApplySequence: sequence, inlineContent: content,
                    intentID: intent.identity.id, specBytes: intent.identity.spec, specSHA256: intent.identity.sha)
                // This sync completes BEFORE prepare/sign/append. A later call
                // must not refresh a property sequence or resolve a new body.
                try journal.save(entry)
                try await checkpointHook(index)
            }
            let intent = try Self.intent(entry, plan: plan)
            if let previous = entry.receipts.last { try Self.requireNonterminal(previous, sourceKey: item.sourceKey) }
            let prepared: AnyJSON
            do {
                prepared = try await driver.status(intent, authorize: admit)
            } catch AnyEngineError.http(let status, _) where status == 404 && entry.receipts.isEmpty {
                // Only a native 404 with no prior native receipt permits initial
                // preparation. Network/auth/corruption errors are never absence.
                let payload: URL?
                if case .file = intent { payload = try await payloads(item.sourceKey) } else { payload = nil }
                prepared = try await driver.prepare(intent, payload: payload, authorize: admit)
            }
            try Self.record(prepared, in: &entry, intent: intent, journal: journal)
            try Self.requireNonterminal(prepared, sourceKey: item.sourceKey)
            let completed: AnyJSON
            if Self.isComplete(prepared) {
                completed = prepared
            } else {
                // A lost reply escapes immediately. Resuming reconciles this
                // same intent; there is no uncertain-write loop in this call.
                completed = try await driver.commit(intent, receipt: prepared, authorize: admit)
                try Self.record(completed, in: &entry, intent: intent, journal: journal)
                try Self.requireNonterminal(completed, sourceKey: item.sourceKey)
            }
            guard Self.isComplete(completed) else { throw AnyPreparedMigrationError.incompleteCommit }
            let mapping = try Self.mapping(item, entry: entry)
            mappings[Data(item.sourceKey.utf8)] = mapping; ordered.append(mapping); entries.append(entry)
            if case .object(_, _, .literal(let values)) = resolved {
                creationProperties[Data(mapping.objectID.utf8)] = values
            }
        }
        // Recheck every original identity after all later phases, including
        // property links and file records, and after reopening an old journal.
        // This is a sequence of current native reads, not an atomic Space view.
        for index in entries.indices {
            var entry = entries[index]
            let intent = try Self.intent(entry, plan: plan)
            let current = try await driver.status(intent, authorize: admit)
            try Self.record(current, in: &entry, intent: intent, journal: journal)
            try Self.requireNonterminal(current, sourceKey: entry.sourceKey)
            guard Self.isComplete(current) else { throw AnyPreparedMigrationError.incompleteCommit }
            ordered[index] = try Self.mapping(plan.items[index], entry: entry)
            entries[index] = entry
        }
        try await admit()
        return .init(binding: plan.binding, source: plan.source, mappings: ordered,
                     totalItems: plan.items.count, allItemsReconciled: true)
    }

    private static func intent(_ entry: AnyDestinationJournalEntry,
                               plan: AnyDestinationMigrationPlan) throws -> AnyDestinationNativeIntent {
        let operation = try JSONDecoder().decode(AnyDestinationMigrationOperation.self, from: entry.resolvedOperation)
        let value = try AnyDestinationNativeIntent.make(operation, binding: plan.binding, sourceKey: entry.sourceKey,
            sequence: entry.expectedApplySequence, inlineContent: entry.inlineContent)
        guard value.identity.id == entry.intentID, value.identity.spec == entry.specBytes,
              value.identity.sha == entry.specSHA256 else { throw AnyDestinationMigrationError.journalCorrupt }
        for receipt in entry.receipts { try value.validateReceipt(receipt) }
        return value
    }

    private static func resolve(_ reference: AnyDestinationReference,
                                mappings: [Data: AnyDestinationMigrationMapping]) throws -> String {
        switch reference {
        case .native(let value): return value
        case .mapped(let key, let slot, let encoding):
            guard let mapping = mappings[Data(key.utf8)] else { throw AnyDestinationMigrationError.unknownReference(key) }
            let value: String
            switch slot {
            case .objectID: value = mapping.objectID
            case .record(let index):
                guard mapping.recordIDs.indices.contains(index) else { throw AnyDestinationMigrationError.unknownReference(key) }
                value = mapping.recordIDs[index]
            case .fileID:
                guard let id = mapping.fileID else { throw AnyDestinationMigrationError.unknownReference(key) }; value = id
            }
            return encoding == .anyURI ? "any://" + value : value
        }
    }

    private static func record(_ receipt: AnyJSON, in entry: inout AnyDestinationJournalEntry,
                               intent: AnyDestinationNativeIntent, journal: AnyDestinationMigrationJournal) throws {
        try intent.validateReceipt(receipt)
        if let previous = entry.receipts.last { try compare(previous, receipt, sourceKey: entry.sourceKey) }
        let bytes = try AnyDestinationMigrationJournal.encoded(receipt)
        if let previous = entry.receipts.last, try AnyDestinationMigrationJournal.encoded(previous) == bytes { return }
        guard entry.receipts.count < 32 else { throw AnyDestinationMigrationError.journalCorrupt }
        entry.receipts.append(receipt); try journal.save(entry)
    }

    private static func isComplete(_ value: AnyJSON) -> Bool {
        value["stage"]?.string == "complete" && value["outcome"]?.string == "committed" &&
        (value["kind"]?.string != "file" || value["localFileComplete"]?.bool == true)
    }
    private static func requireNonterminal(_ value: AnyJSON, sourceKey: String) throws {
        guard let outcome = value["outcome"]?.string else { throw AnyDestinationMigrationError.journalCorrupt }
        guard outcome == "prepared" || outcome == "committed" else {
            throw AnyDestinationMigrationError.nativeTerminal(sourceKey, outcome)
        }
    }

    private static func compare(_ old: AnyJSON, _ new: AnyJSON, sourceKey: String) throws {
        func same(_ key: String) -> Bool {
            guard let a = old[key]?.string else { return true }
            return new[key]?.string.map { Data($0.utf8) } == Data(a.utf8)
        }
        guard ["intentId", "fingerprint", "objectId", "fileId", "rootCid", "ownerObjectId", "specSHA256"].allSatisfy(same) else {
            throw AnyDestinationMigrationError.changedIdentity(sourceKey)
        }
        if let previous = old["recordIds"]?.array, !previous.isEmpty {
            guard let current = new["recordIds"]?.array,
                  try AnyDestinationMigrationJournal.encoded(previous) == AnyDestinationMigrationJournal.encoded(current) else {
                throw AnyDestinationMigrationError.changedIdentity(sourceKey)
            }
        }
        let a = old["stage"]?.string ?? "", b = new["stage"]?.string ?? ""
        let rootStages: Set<String> = ["root-prepared", "root-committed", "definition-root-prepared", "definition-root-committed"]
        let bootstrapStages: Set<String> = ["bootstrap-prepared", "definition-bootstrap-prepared", "complete"]
        let permittedNewBootstrap = rootStages.contains(a) && bootstrapStages.contains(b)
        guard permittedNewBootstrap || same("changeId") else { throw AnyDestinationMigrationError.changedIdentity(sourceKey) }
        let order: [String: Int] = ["root-prepared": 0, "root-committed": 1, "bootstrap-prepared": 2,
            "block-prepared": 0, "definition-root-prepared": 0, "definition-root-committed": 1,
            "definition-bootstrap-prepared": 2, "definition-property-prepared": 0, "definition-part-prepared": 0,
            "properties-prepared": 0, "file-prepared": 0, "file-root-committed": 1, "file-row-committed": 2, "complete": 3]
        // Preserve a terminal native outcome even when deletion projects it to
        // a pre-commit stage. It still halts immediately and cannot be revived.
        if new["outcome"]?.string == "prepared" || new["outcome"]?.string == "committed" {
            guard let oldOrder = order[a], let newOrder = order[b], newOrder >= oldOrder else {
                throw AnyDestinationMigrationError.changedIdentity(sourceKey)
            }
        }
        if let outcome = old["outcome"]?.string, outcome != "prepared" && outcome != "committed",
           new["outcome"]?.string != outcome { throw AnyDestinationMigrationError.changedIdentity(sourceKey) }
    }

    private static func mapping(_ item: AnyDestinationMigrationItem, entry: AnyDestinationJournalEntry) throws -> AnyDestinationMigrationMapping {
        guard let value = entry.receipts.last, isComplete(value),
              let id = value["objectId"]?.string, let fingerprint = value["fingerprint"]?.string,
              let records = value["recordIds"]?.array,
              records.count == item.expectedRecordCount else { throw AnyDestinationMigrationError.changedIdentity(item.sourceKey) }
        let recordIDs = try records.map { value -> String in
            guard let id = value.string else { throw AnyDestinationMigrationError.journalCorrupt }; return id
        }
        var changes: [String] = []
        for receipt in entry.receipts {
            if let change = receipt["changeId"]?.string, !changes.contains(where: { Data($0.utf8) == Data(change.utf8) }) {
                changes.append(change)
            }
        }
        return .init(sourceKey: item.sourceKey, sourceObjectID: item.sourceObjectID, kind: item.operation.kind,
            intentID: entry.intentID, objectID: id, recordIDs: recordIDs, fileID: value["fileId"]?.string,
            fingerprint: fingerprint, signedChangeIDs: changes,
            currentReceiptSHA256: AnyContentDigest.sha256(try AnyDestinationMigrationJournal.encoded(value)))
    }

    private static func requireDisjointCreationFields(object: AnyDestinationReference, owner: AnyDestinationReference,
                                                      patch: AnyDestinationValue, properties: [Data: AnyJSON]) throws {
        guard case .native(let objectID) = object, case .native(let ownerID) = owner,
              case .literal(let patchValue) = patch, let patch = patchValue.object else {
            throw AnyDestinationMigrationError.invalidPlan("resolved property group")
        }
        guard let initial = properties[Data(objectID.utf8)] else {
            throw AnyDestinationMigrationError.invalidPlan("property target was not created by this plan")
        }
        if let original = initial[ownerID]?.object, !Set(original.keys).isDisjoint(with: Set(patch.keys)) {
            throw AnyDestinationMigrationError.invalidPlan("property update replaces an immutable creation field")
        }
    }

    private static func inlinePayload(_ url: URL, size: Int64, digest: String, sourceKey: String) throws -> Data {
        guard url.isFileURL, (0...4095).contains(size) else { throw AnyDestinationMigrationError.payloadMismatch(sourceKey) }
        let fd = open(url.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw AnyDestinationMigrationError.payloadMismatch(sourceKey) }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true); defer { try? handle.close() }
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG), info.st_size == size else {
            throw AnyDestinationMigrationError.payloadMismatch(sourceKey)
        }
        var data = Data()
        while data.count <= 4095 {
            let next = try handle.read(upToCount: 4096 - data.count) ?? Data()
            if next.isEmpty { break }; data.append(next)
        }
        guard Int64(data.count) == size, AnyContentDigest.sha256(data) == digest,
              fstat(fd, &info) == 0, info.st_size == size else { throw AnyDestinationMigrationError.payloadMismatch(sourceKey) }
        return data
    }
}
