#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import Darwin
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration

enum PinkhaMigrationSelectionError: Error {
    case busy, invalidIdentity, changedStorage, changedSelection
    case retainedOperationRequiresReview, alreadyCompleted, invalidCompletion
}

/// The App's sole owner of migration names. Names and original journals are
/// never moved, replaced or removed. Release is permitted only after the source
/// facade and the complete presentation-owned destination call have drained.
/// These private locators do not authorize a native read, write or replay.
actor PinkhaMigrationSelectionStore {
    struct Operation: Sendable {
        let request: AnyHeartNativeMigrationRequest
        fileprivate let id: UUID
        fileprivate let destinationKey: String
        fileprivate let sourceKey: String
    }

    struct CompletedSelection: Sendable {
        let preservationReference: AnyNativeImportedContextReference
        let contentReference: AnyNativeImportedContentContextReference
        /// Present for a retained Ordinary14 result, including all-present v2,
        /// which uses the original preservation journal and no second journal.
        let ordinaryReference: AnyNativeImportedOrdinaryPropertyReference?
        let journalParent: URL
        let archiveURL: URL
        var grantsNativeAuthority: Bool { false }
    }

    struct SavedSelection: Sendable {
        let sourceAccountID: String
        let sourceSpaceID: String
        let captureManifestSHA256: String
        /// nil preserves an incomplete/uncertain original operation. It must
        /// not be presented as rolled back or replaced by a new migration.
        let completed: CompletedSelection?
    }

    private struct Intent: Codable {
        let contract: String
        let sourceAccountID: String
        let sourceSpaceID: String
        let captureManifestSHA256: String
        let sourceRowsSHA256: String
        let destinationNetworkID: String
        let destinationAccountID: String
        let destinationSpaceID: String
        let storeID: String
        let planID: String
    }

    private struct Completion: Codable {
        let contract: String
        let preservationSHA256: String
        let contentSHA256: String
        let ordinarySHA256: String?
    }

    private struct Held {
        let operation: Operation
        let intent: Intent
        let sourceBundle: AnyHeartNativeSpaceBundle
        let destination: PinnedDirectory
        let directory: PinnedDirectory
        let journals: PinnedDirectory
        let payloads: PinnedDirectory

        func validate(root: PinnedDirectory) throws {
            try root.validate()
            try destination.validate()
            try directory.validate()
            try journals.validate()
            try payloads.validate()
        }
    }

    private let root: PinnedDirectory
    private var active: Held?
    private var retentionTask: Task<Void, Error>?
    private var retentionTicket: UUID?

    init(privateDirectory: URL) throws {
        root = try PinnedDirectory(existing: privateDirectory)
    }

    static func privateDirectory() throws -> URL {
        let support = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: false).resolvingSymlinksInPath()
        // The existing OS application Library is the infrastructure anchor.
        // Every directory created or reused below it gets fresh child+parent
        // durability barriers, including Application Support and Pinkha.
        let library = try PinnedDirectory(existing: support.deletingLastPathComponent(),
            requirePrivatePermissions: false)
        let supportDirectory = try library.child(support.lastPathComponent, create: true,
            requirePrivatePermissions: false)
        let pinkha = try supportDirectory.child("Pinkha", create: true)
        return try pinkha.child("MigrationSelectionsV1", create: true).url
    }

    /// Call only after an explicit source/destination confirmation. Persist the
    /// exact selected scope BEFORE invoking C's original producer. A second
    /// capture for the same pair cannot silently replace an uncertain operation.
    func prepare(review: AnyHeartNativeSourceCaptureReview,
                 networkID: String, workspace: AnyTorahWorkspace) throws -> Operation {
        guard active == nil, retentionTask == nil else { throw PinkhaMigrationSelectionError.busy }
        let descriptor = review.descriptor
        guard descriptor.manifestSHA256 == review.bundle.manifestSHA256,
              descriptor.sourceRowsSHA256 == review.bundle.sourceRows.sha256,
              Self.same(descriptor.sourceAccountID, review.bundle.sourceAccountID),
              Self.same(descriptor.sourceSpaceID, review.bundle.sourceSpaceID) else {
            throw PinkhaMigrationSelectionError.invalidIdentity
        }
        let destinationKey = try Self.key(["destination", networkID, workspace.accountID, workspace.spaceID])
        let sourceKey = try Self.key(["source", descriptor.sourceAccountID, descriptor.sourceSpaceID])
        let storeID = "heart-source-" + sourceKey
        let planID = try Self.key(["plan", destinationKey, sourceKey,
            descriptor.manifestSHA256, descriptor.sourceRowsSHA256])
        let intent = Intent(contract: "pinkha-app-migration-intent-v1",
            sourceAccountID: descriptor.sourceAccountID, sourceSpaceID: descriptor.sourceSpaceID,
            captureManifestSHA256: descriptor.manifestSHA256, sourceRowsSHA256: descriptor.sourceRowsSHA256,
            destinationNetworkID: networkID, destinationAccountID: workspace.accountID,
            destinationSpaceID: workspace.spaceID, storeID: storeID, planID: planID)
        try Self.validate(intent)
        try root.validate()
        let destination = try root.child(destinationKey, create: true)
        let directory = try destination.child(sourceKey, create: true)
        if try directory.read("completed.json", maximum: 4096) != nil {
            throw PinkhaMigrationSelectionError.alreadyCompleted
        }
        let bytes = try Self.encode(intent, maximum: 65_536)
        if let retained = try directory.read("intent.json", maximum: 65_536) {
            _ = try Self.decodeIntent(retained)
            guard retained == bytes else {
                throw PinkhaMigrationSelectionError.retainedOperationRequiresReview
            }
        }
        // Exact prior bytes are freshly read and synchronized by writeOnce too.
        try directory.writeOnce("intent.json", bytes: bytes, maximum: 65_536)
        let journals = try directory.child("journals", create: true)
        let payloads = try directory.child("payloads", create: true)
        let request = try AnyHeartNativeMigrationRequest(networkID: networkID, workspace: workspace,
            storeID: storeID, planID: planID, journalParent: journals.url, payloadParent: payloads.url)
        let operation = Operation(request: request, id: UUID(),
            destinationKey: destinationKey, sourceKey: sourceKey)
        let held = Held(operation: operation, intent: intent, sourceBundle: review.bundle, destination: destination,
            directory: directory, journals: journals, payloads: payloads)
        try held.validate(root: root)
        active = held
        return operation
    }

    /// Invoke inside E's original destination body, immediately after C returns
    /// its genuine completed result and BEFORE the outer delivery fence. There
    /// is deliberately no cancellation check: a known outcome must be retained
    /// in its original scope even if cancellation/account replacement is pending.
    /// This records no invented receipt and performs no native mutation.
    func retain(_ completion: AnyHeartNativeMigrationCompletion, for operation: Operation) async throws {
        _ = try requireHeld(operation)
        guard retentionTask == nil else { throw PinkhaMigrationSelectionError.busy }
        let ticket = UUID()
        // An unstructured task does not inherit caller cancellation. Never
        // cancel this handle: the original checkpoint reader checks cancellation,
        // and the already-known outcome must reach durable original-scope storage.
        let task = Task { try self.retainKnownCompletion(completion, for: operation) }
        retentionTicket = ticket
        retentionTask = task
        defer {
            if retentionTicket == ticket {
                retentionTicket = nil
                retentionTask = nil
            }
        }
        // Await the actual child even when this calling task was cancelled.
        // The enclosing E/C invocation cannot finish its drain before this join.
        try await task.value
    }

    private func retainKnownCompletion(_ completion: AnyHeartNativeMigrationCompletion,
                                       for operation: Operation) throws {
        let held = try requireHeld(operation)
        try held.validate(root: root)
        let preservation = try AnyNativeImportedContextReference.decode(completion.encodedPreservationReference)
        let content = try AnyNativeImportedContentContextReference.decode(completion.encodedContentReference)
        guard try preservation.encoded() == completion.preservationReference.encoded(),
              try content.encoded() == completion.contentReference.encoded() else {
            throw PinkhaMigrationSelectionError.invalidCompletion
        }
        try Self.requireReferences(preservation, content: content, intent: held.intent)
        let checkpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: held.journals.url, binding: preservation.binding)
        guard checkpoint.checkpointSHA256 == preservation.checkpointSHA256,
              checkpoint.checkpointSHA256 == completion.checkpoint.checkpointSHA256,
              checkpoint.plan.canonicalBytes == completion.checkpoint.plan.canonicalBytes,
              Self.same(completion.journalParent.path, held.journals.url.path),
              Self.same(completion.privateArchiveURL.path, Self.archiveURL(
                reference: preservation, payloads: held.payloads.url).path) else {
            throw PinkhaMigrationSelectionError.invalidCompletion
        }
        try held.directory.writeOnce("preservation.json",
            bytes: completion.encodedPreservationReference,
            maximum: AnyNativeImportedContextReference.maximumBytes)
        try held.directory.writeOnce("content.json", bytes: completion.encodedContentReference,
            maximum: AnyNativeImportedContentContextReference.maximumBytes)
        let marker = Completion(contract: "pinkha-app-migration-completion-v1",
            preservationSHA256: AnyContentDigest.sha256(completion.encodedPreservationReference),
            contentSHA256: AnyContentDigest.sha256(completion.encodedContentReference), ordinarySHA256: nil)
        // Commit the pair only after both immutable files and their directory
        // were synchronized. A partial pair remains pending, never successful.
        try held.directory.writeOnce("completed.json", bytes: Self.encode(marker, maximum: 4096),
            maximum: 4096)
        try held.validate(root: root)
    }

    /// Retain C's distinct three-locator result in the same uncancelled owned
    /// task. A failed Ordinary14 stage never calls this method and never commits
    /// a completion marker. Its original intent, payload and journals remain.
    func retainOrdinary(_ completion: AnyHeartNativeOrdinaryMigrationCompletion,
                        for operation: Operation) async throws {
        _ = try requireHeld(operation)
        guard retentionTask == nil else { throw PinkhaMigrationSelectionError.busy }
        let ticket = UUID()
        let task = Task { try self.retainKnownOrdinaryCompletion(completion, for: operation) }
        retentionTicket = ticket
        retentionTask = task
        defer {
            if retentionTicket == ticket {
                retentionTicket = nil
                retentionTask = nil
            }
        }
        try await task.value
    }

    private func retainKnownOrdinaryCompletion(_ completion: AnyHeartNativeOrdinaryMigrationCompletion,
                                               for operation: Operation) throws {
        let held = try requireHeld(operation)
        try held.validate(root: root)
        let original = completion.preservation
        let preservation = try AnyNativeImportedContextReference.decode(original.encodedPreservationReference)
        let content = try AnyNativeImportedContentContextReference.decode(original.encodedContentReference)
        let ordinary = try AnyNativeImportedOrdinaryPropertyReference.decode(completion.encodedOrdinaryReference)
        guard try preservation.encoded() == original.preservationReference.encoded(),
              try content.encoded() == original.contentReference.encoded(),
              try ordinary.encoded() == completion.ordinaryReference.encoded() else {
            throw PinkhaMigrationSelectionError.invalidCompletion
        }
        try Self.requireReferences(preservation, content: content, intent: held.intent)
        let checkpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: held.journals.url, binding: preservation.binding)
        guard checkpoint.checkpointSHA256 == preservation.checkpointSHA256,
              checkpoint.checkpointSHA256 == original.checkpoint.checkpointSHA256,
              checkpoint.plan.canonicalBytes == original.checkpoint.plan.canonicalBytes,
              Self.same(original.journalParent.path, held.journals.url.path),
              Self.same(original.privateArchiveURL.path, Self.archiveURL(
                reference: preservation, payloads: held.payloads.url).path) else {
            throw PinkhaMigrationSelectionError.invalidCompletion
        }
        let supplementalCheckpoint: AnyDestinationSavedCheckpoint?
        if ordinary.hasSupplementalCheckpoint {
            guard let returned = completion.ordinaryCheckpoint,
                  completion.ordinaryVerification != nil else {
                throw PinkhaMigrationSelectionError.invalidCompletion
            }
            let saved = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                journalDirectory: held.journals.url, binding: ordinary.binding(preservation: preservation))
            guard saved.checkpointSHA256 == ordinary.supplementCheckpointSHA256,
                  saved.checkpointSHA256 == returned.checkpointSHA256,
                  saved.plan.canonicalBytes == returned.plan.canonicalBytes else {
                throw PinkhaMigrationSelectionError.invalidCompletion
            }
            supplementalCheckpoint = saved
        } else {
            // All fourteen definitions were already imported by preservation.
            // Bind its actual checkpoint; never create or invent a second one.
            guard completion.ordinaryCheckpoint == nil,
                  completion.ordinaryVerification == nil else {
                throw PinkhaMigrationSelectionError.invalidCompletion
            }
            _ = try ordinary.binding(preservation: preservation)
            supplementalCheckpoint = nil
        }
        // C's original typed constructor verifies the complete partition,
        // original provenance/intents and exact missing-only checkpoint. It
        // delegates all-new input to legacy v1 and retains all-present v2.
        let expected = try AnyNativeImportedOrdinaryPropertyReference(
            preservationReference: preservation, bundle: held.sourceBundle,
            preservationCheckpoint: checkpoint, supplementalCheckpoint: supplementalCheckpoint)
        guard try expected.encoded() == completion.encodedOrdinaryReference else {
            throw PinkhaMigrationSelectionError.invalidCompletion
        }
        try held.directory.writeOnce("preservation.json",
            bytes: original.encodedPreservationReference,
            maximum: AnyNativeImportedContextReference.maximumBytes)
        try held.directory.writeOnce("content.json", bytes: original.encodedContentReference,
            maximum: AnyNativeImportedContentContextReference.maximumBytes)
        try held.directory.writeOnce("ordinary.json", bytes: completion.encodedOrdinaryReference,
            maximum: AnyNativeImportedOrdinaryPropertyReference.maximumBytes)
        let marker = Completion(contract: "pinkha-app-migration-completion-v2",
            preservationSHA256: AnyContentDigest.sha256(original.encodedPreservationReference),
            contentSHA256: AnyContentDigest.sha256(original.encodedContentReference),
            ordinarySHA256: AnyContentDigest.sha256(completion.encodedOrdinaryReference))
        // All three immutable files are durable before the marker. Partial files
        // never imply that either original native stage was rolled back.
        try held.directory.writeOnce("completed.json", bytes: Self.encode(marker, maximum: 4096),
            maximum: 4096)
        try held.validate(root: root)
    }

    /// No native work is cancelled or assumed settled here. The Scene must
    /// first await its source facade / destination operation's complete drain.
    /// All intent, journal, payload, reference and partial files are retained.
    func release(_ operation: Operation) throws {
        _ = try requireHeld(operation)
        guard retentionTask == nil else { throw PinkhaMigrationSelectionError.busy }
        active = nil
    }

    /// Select only the explicitly opened destination, never all accounts or a
    /// last-used/default account. Results remain routing hints. C's original
    /// context owner must perform current native/lease/run admission when opened.
    func savedSelections(networkID: String, workspace: AnyTorahWorkspace) throws -> [SavedSelection] {
        let destinationKey = try Self.key(["destination", networkID, workspace.accountID, workspace.spaceID])
        try root.validate()
        guard let destination = try root.existingChild(destinationKey) else { return [] }
        var result: [SavedSelection] = []
        for name in try destination.childNames(maximum: 256) {
            guard Self.digest(name) else {
                throw PinkhaMigrationSelectionError.changedStorage
            }
            let directory = try destination.child(name, create: false)
            guard let bytes = try directory.read("intent.json", maximum: 65_536) else {
                // A crash before publishing the intent created no native work.
                // Keep that directory; it is neither a completed selection nor
                // permission to infer any account or reconstruct an operation.
                continue
            }
            let intent = try Self.decodeIntent(bytes)
            guard Self.same(intent.destinationNetworkID, networkID),
                  Self.same(intent.destinationAccountID, workspace.accountID),
                  Self.same(intent.destinationSpaceID, workspace.spaceID),
                  try Self.key(["source", intent.sourceAccountID, intent.sourceSpaceID]) == name else {
                throw PinkhaMigrationSelectionError.changedSelection
            }
            let completed: CompletedSelection?
            if let markerBytes = try directory.read("completed.json", maximum: 4096) {
                let marker = try JSONDecoder().decode(Completion.self, from: markerBytes)
                try AnyTorahSourceJSONGuard.validateRoundTrip(original: markerBytes,
                    encoded: Self.encode(marker, maximum: 4096))
                guard marker.contract == "pinkha-app-migration-completion-v1" ||
                        marker.contract == "pinkha-app-migration-completion-v2",
                      let preservationBytes = try directory.read("preservation.json",
                        maximum: AnyNativeImportedContextReference.maximumBytes),
                      let contentBytes = try directory.read("content.json",
                        maximum: AnyNativeImportedContentContextReference.maximumBytes),
                      AnyContentDigest.sha256(preservationBytes) == marker.preservationSHA256,
                      AnyContentDigest.sha256(contentBytes) == marker.contentSHA256 else {
                    throw PinkhaMigrationSelectionError.invalidCompletion
                }
                let preservation = try AnyNativeImportedContextReference.decode(preservationBytes)
                let content = try AnyNativeImportedContentContextReference.decode(contentBytes)
                try Self.requireReferences(preservation, content: content, intent: intent)
                let ordinary: AnyNativeImportedOrdinaryPropertyReference?
                if marker.contract == "pinkha-app-migration-completion-v2" {
                    guard let expected = marker.ordinarySHA256, Self.digest(expected),
                          let bytes = try directory.read("ordinary.json",
                            maximum: AnyNativeImportedOrdinaryPropertyReference.maximumBytes),
                          AnyContentDigest.sha256(bytes) == expected else {
                        throw PinkhaMigrationSelectionError.invalidCompletion
                    }
                    let reference = try AnyNativeImportedOrdinaryPropertyReference.decode(bytes)
                    _ = try reference.binding(preservation: preservation)
                    ordinary = reference
                } else {
                    guard marker.ordinarySHA256 == nil else {
                        throw PinkhaMigrationSelectionError.invalidCompletion
                    }
                    ordinary = nil
                }
                let journals = try directory.child("journals", create: false)
                let payloads = try directory.child("payloads", create: false)
                completed = .init(preservationReference: preservation, contentReference: content,
                    ordinaryReference: ordinary, journalParent: journals.url, archiveURL: Self.archiveURL(
                        reference: preservation, payloads: payloads.url))
            } else { completed = nil }
            try directory.validate()
            result.append(.init(sourceAccountID: intent.sourceAccountID, sourceSpaceID: intent.sourceSpaceID,
                captureManifestSHA256: intent.captureManifestSHA256, completed: completed))
        }
        try destination.validate()
        try root.validate()
        return result
    }

    private func requireHeld(_ operation: Operation) throws -> Held {
        guard let held = active, held.operation.id == operation.id,
              held.operation.destinationKey == operation.destinationKey,
              held.operation.sourceKey == operation.sourceKey else {
            throw PinkhaMigrationSelectionError.changedSelection
        }
        return held
    }

    private static func archiveURL(reference: AnyNativeImportedContextReference, payloads: URL) -> URL {
        payloads.appendingPathComponent("captured-source-" + reference.archiveSHA256 + ".pinkha-heart-source")
    }

    private static func requireReferences(_ reference: AnyNativeImportedContextReference,
        content: AnyNativeImportedContentContextReference, intent: Intent) throws {
        guard Self.same(reference.destinationNetworkID, intent.destinationNetworkID),
              Self.same(reference.destinationAccountID, intent.destinationAccountID),
              Self.same(reference.destinationSpaceID, intent.destinationSpaceID),
              Self.same(reference.sourceAccountID, intent.sourceAccountID),
              Self.same(reference.sourceSpaceID, intent.sourceSpaceID),
              Self.same(reference.storeID, intent.storeID), reference.planID == intent.planID,
              reference.captureManifestSHA256 == intent.captureManifestSHA256 else {
            throw PinkhaMigrationSelectionError.invalidCompletion
        }
        _ = try content.binding(preservation: reference)
    }

    private static func decodeIntent(_ bytes: Data) throws -> Intent {
        let intent = try JSONDecoder().decode(Intent.self, from: bytes)
        try validate(intent)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: encode(intent, maximum: 65_536))
        return intent
    }

    private static func validate(_ intent: Intent) throws {
        guard intent.contract == "pinkha-app-migration-intent-v1",
              [intent.sourceAccountID, intent.sourceSpaceID, intent.destinationNetworkID,
               intent.destinationAccountID, intent.destinationSpaceID, intent.storeID].allSatisfy({
                   Self.validOpaque($0, maximum: 4096)
               }),
              [intent.captureManifestSHA256, intent.sourceRowsSHA256, intent.planID]
                .allSatisfy(Self.digest) else {
            throw PinkhaMigrationSelectionError.invalidIdentity
        }
        let sourceKey = try key(["source", intent.sourceAccountID, intent.sourceSpaceID])
        let destinationKey = try key(["destination", intent.destinationNetworkID,
            intent.destinationAccountID, intent.destinationSpaceID])
        guard intent.storeID == "heart-source-" + sourceKey,
              intent.planID == (try key(["plan", destinationKey, sourceKey,
                intent.captureManifestSHA256, intent.sourceRowsSHA256])) else {
            throw PinkhaMigrationSelectionError.changedSelection
        }
    }

    // Same finite byte/control rules as the original Host validators. These
    // App-private checks only admit locator data; they grant no native authority.
    private static func validOpaque(_ value: String, maximum: Int) -> Bool {
        !value.isEmpty && value.utf8.count <= maximum &&
            value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }

    private static func digest(_ value: String) -> Bool {
        value.utf8.count == 64 &&
            value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }

    private static func key(_ values: [String]) throws -> String {
        var material = Data("pinkha-app-migration-selection-v1\n".utf8)
        for value in values {
            guard Self.validOpaque(value, maximum: 4096) else {
                throw PinkhaMigrationSelectionError.invalidIdentity
            }
            let bytes = Data(value.utf8)
            material.append(contentsOf: String(bytes.count).utf8)
            material.append(58)
            material.append(bytes)
        }
        return AnyContentDigest.sha256(material)
    }

    private static func encode<Value: Encodable>(_ value: Value, maximum: Int) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(value)
        guard !bytes.isEmpty, bytes.count <= maximum else {
            throw PinkhaMigrationSelectionError.invalidIdentity
        }
        return bytes
    }

    private static func same(_ a: String, _ b: String) -> Bool {
        Data(a.utf8) == Data(b.utf8)
    }
}

/// Small private filesystem owner for the App's fixed migration namespace.
/// An independent administrator can still rename ancestors: every use detects
/// identity replacement, but these descriptors do not claim an OS namespace lock.
private final class PinnedDirectory {
    let url: URL
    let fd: Int32
    private let requirePrivatePermissions: Bool

    init(existing url: URL, requirePrivatePermissions: Bool = true) throws {
        guard url.isFileURL, url.path.hasPrefix("/"), !url.path.contains("\0"),
              Data(url.standardizedFileURL.path.utf8) == Data(url.path.utf8),
              Data(url.resolvingSymlinksInPath().path.utf8) == Data(url.path.utf8) else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
        let fd = open(url.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw PinkhaMigrationSelectionError.changedStorage }
        do {
            try Self.validate(fd: fd, url: url, requirePrivatePermissions: requirePrivatePermissions)
        } catch { _ = close(fd); throw error }
        self.url = url
        self.fd = fd
        self.requirePrivatePermissions = requirePrivatePermissions
    }

    private init(admittedURL url: URL, admittedFD fd: Int32, requirePrivatePermissions: Bool) {
        self.url = url
        self.fd = fd
        self.requirePrivatePermissions = requirePrivatePermissions
    }

    deinit { _ = close(fd) }

    func validate() throws {
        try Self.validate(fd: fd, url: url, requirePrivatePermissions: requirePrivatePermissions)
    }

    private static func validate(fd: Int32, url: URL, requirePrivatePermissions: Bool) throws {
        var actual = stat(), named = stat()
        guard fstat(fd, &actual) == 0, lstat(url.path, &named) == 0 else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
        let permissions = actual.st_mode & mode_t(0o7777)
        let admittedPermissions = requirePrivatePermissions
            ? permissions == mode_t(0o700)
            : permissions & mode_t(0o700) == mode_t(0o700) &&
                permissions & mode_t(0o7022) == 0
        guard actual.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              admittedPermissions, actual.st_uid == geteuid(),
              Self.sameIdentity(actual, named) else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
    }

    func existingChild(_ name: String, requirePrivatePermissions: Bool = true) throws -> PinnedDirectory? {
        try validName(name)
        try validate()
        let child = openat(fd, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        if child < 0 {
            guard errno == ENOENT else { throw PinkhaMigrationSelectionError.changedStorage }
            return nil
        }
        let childURL = url.appendingPathComponent(name, isDirectory: true)
        do {
            try Self.validate(fd: child, url: childURL, requirePrivatePermissions: requirePrivatePermissions)
            try validate()
        } catch { _ = close(child); throw error }
        return PinnedDirectory(admittedURL: childURL, admittedFD: child,
            requirePrivatePermissions: requirePrivatePermissions)
    }

    func child(_ name: String, create: Bool,
               requirePrivatePermissions: Bool = true) throws -> PinnedDirectory {
        let value: PinnedDirectory
        if let existing = try existingChild(name, requirePrivatePermissions: requirePrivatePermissions) {
            value = existing
        } else {
            guard create, mkdirat(fd, name, mode_t(0o700)) == 0 || errno == EEXIST,
                  let created = try existingChild(name, requirePrivatePermissions: requirePrivatePermissions) else {
                throw PinkhaMigrationSelectionError.changedStorage
            }
            value = created
        }
        // Reuse must retry a previously failed directory-publication barrier.
        // The existence of the name alone never upgrades that failure to success.
        guard fsync(value.fd) == 0, fsync(fd) == 0 else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
        try value.validate()
        try validate()
        return value
    }

    func read(_ name: String, maximum: Int, synchronize: Bool = false) throws -> Data? {
        try validName(name)
        try validate()
        let file = openat(fd, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        if file < 0 {
            guard errno == ENOENT else { throw PinkhaMigrationSelectionError.changedStorage }
            return nil
        }
        let handle = FileHandle(fileDescriptor: file, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat(), after = stat(), named = stat()
        guard fstat(file, &before) == 0, Self.privateFile(before),
              before.st_size > 0, before.st_size <= Int64(maximum),
              fstatat(fd, name, &named, AT_SYMLINK_NOFOLLOW) == 0,
              Self.sameIdentity(before, named) else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
        var bytes = Data()
        while bytes.count <= maximum {
            let part = try handle.read(upToCount: min(1_048_576, maximum + 1 - bytes.count)) ?? Data()
            if part.isEmpty { break }
            bytes.append(part)
        }
        guard bytes.count == Int(before.st_size), bytes.count <= maximum,
              fstat(file, &after) == 0, Self.sameFile(before, after),
              fstatat(fd, name, &named, AT_SYMLINK_NOFOLLOW) == 0,
              Self.sameFile(after, named) else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
        if synchronize {
            guard fsync(file) == 0, fsync(fd) == 0,
                  fstat(file, &after) == 0, Self.sameFile(before, after),
                  fstatat(fd, name, &named, AT_SYMLINK_NOFOLLOW) == 0,
                  Self.sameFile(after, named) else {
                throw PinkhaMigrationSelectionError.changedStorage
            }
        }
        try validate()
        return bytes
    }

    /// Publish one complete immutable file with exclusive rename. A failed
    /// attempt leaves its uniquely named private staging file for diagnosis.
    /// No existing final file is overwritten, even under a competing writer.
    func writeOnce(_ name: String, bytes: Data, maximum: Int) throws {
        try validName(name)
        guard !bytes.isEmpty, bytes.count <= maximum else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
        if let existing = try read(name, maximum: maximum, synchronize: true) {
            guard existing == bytes else { throw PinkhaMigrationSelectionError.changedSelection }
            return
        }
        let staging = ".pending-" + UUID().uuidString
        let file = openat(fd, staging, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard file >= 0 else { throw PinkhaMigrationSelectionError.changedStorage }
        let handle = FileHandle(fileDescriptor: file, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat(), named = stat()
        guard fstat(file, &before) == 0,
              before.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG),
              before.st_mode & mode_t(0o7777) == mode_t(0o600),
              before.st_uid == geteuid(), before.st_nlink == 1, before.st_size == 0 else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
        try handle.write(contentsOf: bytes)
        guard fsync(file) == 0, fchmod(file, mode_t(0o400)) == 0, fsync(file) == 0,
              fstat(file, &before) == 0, Self.privateFile(before),
              before.st_size == Int64(bytes.count),
              fstatat(fd, staging, &named, AT_SYMLINK_NOFOLLOW) == 0,
              Self.sameFile(before, named) else {
            throw PinkhaMigrationSelectionError.changedStorage
        }
        try validate()
        let result = renameatx_np(fd, staging, fd, name, UInt32(RENAME_EXCL))
        if result != 0, errno != EEXIST { throw PinkhaMigrationSelectionError.changedStorage }
        guard try read(name, maximum: maximum, synchronize: true) == bytes else {
            throw PinkhaMigrationSelectionError.changedSelection
        }
        try validate()
    }

    func childNames(maximum: Int) throws -> [String] {
        try validate()
        let copied = openat(fd, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard copied >= 0 else { throw PinkhaMigrationSelectionError.changedStorage }
        do {
            try Self.validate(fd: copied, url: url, requirePrivatePermissions: requirePrivatePermissions)
        } catch { _ = close(copied); throw error }
        guard let stream = fdopendir(copied) else {
            _ = close(copied)
            throw PinkhaMigrationSelectionError.changedStorage
        }
        defer { _ = closedir(stream) }
        var names: [String] = []
        while true {
            errno = 0
            guard let entry = readdir(stream) else {
                guard errno == 0 else { throw PinkhaMigrationSelectionError.changedStorage }
                break
            }
            var raw = entry.pointee.d_name
            guard let name = withUnsafeBytes(of: &raw, { value -> String? in
                guard let first = value.bindMemory(to: CChar.self).baseAddress else { return nil }
                return String(validatingCString: first)
            }) else { throw PinkhaMigrationSelectionError.changedStorage }
            if name == "." || name == ".." { continue }
            guard names.count < maximum else { throw PinkhaMigrationSelectionError.changedStorage }
            names.append(name)
        }
        try validate()
        return names.sorted()
    }

    private func validName(_ name: String) throws {
        guard !name.isEmpty, name != ".", name != "..", !name.contains("/"), !name.contains("\0"),
              name.utf8.count <= 255 else { throw PinkhaMigrationSelectionError.changedStorage }
    }

    private static func privateFile(_ value: stat) -> Bool {
        value.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG)
            && value.st_mode & mode_t(0o7777) == mode_t(0o400)
            && value.st_uid == geteuid() && value.st_nlink == 1
    }

    private static func sameIdentity(_ a: stat, _ b: stat) -> Bool {
        a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_mode == b.st_mode
            && a.st_uid == b.st_uid && a.st_gid == b.st_gid
    }

    private static func sameFile(_ a: stat, _ b: stat) -> Bool {
        sameIdentity(a, b) && a.st_nlink == b.st_nlink && a.st_size == b.st_size
            && a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec
            && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec
            && a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec
            && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
    }
}
#endif
