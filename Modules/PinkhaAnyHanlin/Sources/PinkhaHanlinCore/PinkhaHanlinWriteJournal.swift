import Foundation
import HanlinHostContracts
#if os(iOS)
import Darwin
#endif

/// App-owned, append-only metadata. This is NOT a native transaction, CAS or permission service.
/// Reserve is durable before dispatch. A reservation without a terminal receipt is unresolved forever
/// until an explicit original-scope reconciliation owner supplies evidence; never retry or erase it.
public actor PinkhaHanlinWriteJournal {
    public enum Effect: String, Codable, Sendable { case reserved, uncertain, notDispatched, committed }
    public struct Entry: Codable, Equatable, Sendable {
        public let version: Int
        public let identity: PinkhaHanlinWriteIdentity
        public let effect: Effect
        public let createdObjectReference: String?
    }

    private let store: PinkhaHanlinProtectedMetadataFiles
    private let namespace: HanlinConversationNamespace
    private var entries: [String: Entry]
    private var knownObjects: [String: PinkhaHanlinKnownObjectRecovery]
    private var poisoned = false
    private var removed = false
    private static let maximumEntries = 256

    private init(store: PinkhaHanlinProtectedMetadataFiles, namespace: HanlinConversationNamespace,
                 entries: [String: Entry], knownObjects: [String: PinkhaHanlinKnownObjectRecovery]) {
        self.store = store; self.namespace = namespace; self.entries = entries
        self.knownObjects = knownObjects
    }

    /// Uses the real host's Application Support/Anytype ownership pattern, never middleware-go,
    /// an App Group, personal Space path or a caller/model URL. The new child belongs only to this feature.
    public static func open(namespace: HanlinConversationNamespace) async throws -> PinkhaHanlinWriteJournal {
        #if os(iOS)
        try await Task.detached {
            let base = try FileManager.default.url(for: .applicationSupportDirectory,
                in: .userDomainMask, appropriateFor: nil, create: true)
            let host = base.appendingPathComponent("Anytype", isDirectory: true)
            // Do not change attributes of the existing host directory.
            try FileManager.default.createDirectory(at: host, withIntermediateDirectories: true)
            return try load(parent: host, namespace: namespace)
        }.value
        #else
        throw PinkhaHanlinWriteError.unavailable
        #endif
    }

    #if DEBUG
    /// Test-only parent override. Never used by the production factory or a model argument.
    static func openInTestDirectory(_ directory: URL,
                                    namespace: HanlinConversationNamespace) async throws -> PinkhaHanlinWriteJournal {
        try await Task.detached { try load(parent: directory, namespace: namespace) }.value
    }
    #endif

    private static func load(parent: URL, namespace: HanlinConversationNamespace) throws -> PinkhaHanlinWriteJournal {
        guard PinkhaHanlinEngineNamespace.supports(namespace.app) else { throw PinkhaHanlinWriteError.invalidPlan }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let scope = PinkhaHanlinCreatePagePlan.digest(try encoder.encode(namespace))
        let store = try PinkhaHanlinProtectedMetadataFiles(parent: parent, scope: scope)
        let files = try store.readAll(maximumFiles: maximumEntries * 4)
        var reservations: [String: Entry] = [:]
        var outcomes: [String: [Entry]] = [:]
        var knownObjects: [String: PinkhaHanlinKnownObjectRecovery] = [:]
        for (name, bytes) in files {
            if name.hasSuffix(PinkhaHanlinKnownObjectRecovery.suffix) {
                let recovery = try PinkhaHanlinKnownObjectRecovery.decode(
                    bytes, fileName: name, namespace: namespace)
                knownObjects[recovery.identity.key] = recovery
                continue
            }
            let entry = try JSONDecoder().decode(Entry.self, from: bytes)
            try entry.identity.validate()
            // Canonical round-trip rejects unknown fields, duplicate fields and unsupported encodings.
            guard entry.version == 1, entry.identity.session.context.namespace == namespace,
                  try encoder.encode(entry) == bytes,
                  name == entry.identity.key + "." + entry.effect.rawValue else { throw PinkhaHanlinWriteError.corruptJournal }
            try validate(entry)
            if entry.effect == .reserved { reservations[entry.identity.key] = entry }
            else { outcomes[entry.identity.key, default: []].append(entry) }
        }
        guard reservations.count <= maximumEntries, Set(outcomes.keys).isSubset(of: Set(reservations.keys)),
              Set(knownObjects.keys).isSubset(of: Set(reservations.keys)) else {
            throw PinkhaHanlinWriteError.corruptJournal
        }
        var providerCalls = Set<String>()
        for entry in reservations.values {
            let id = entry.identity
            guard providerCalls.insert(id.runID.uuidString + ":" + String(id.step) + ":" + id.providerCallDigest).inserted else {
                throw PinkhaHanlinWriteError.corruptJournal
            }
        }
        for (key, changes) in outcomes {
            guard let reservation = reservations[key], changes.allSatisfy({ $0.identity == reservation.identity }),
                  !(changes.contains { $0.effect == .notDispatched } && changes.count != 1) else {
                throw PinkhaHanlinWriteError.corruptJournal
            }
            reservations[key] = changes.first { $0.effect == .committed }
                ?? changes.first { $0.effect == .notDispatched }
                ?? changes.first { $0.effect == .uncertain }
        }
        for (key, recovery) in knownObjects {
            guard let entry = reservations[key] else { throw PinkhaHanlinWriteError.corruptJournal }
            do { try recovery.validate(against: entry) }
            catch { throw PinkhaHanlinWriteError.corruptJournal }
        }
        try store.recordNamespace(namespace)
        return .init(store: store, namespace: namespace, entries: reservations, knownObjects: knownObjects)
    }

    /// Current actor/owner state only; no permission grant, cleanup, reservation or native I/O.
    public func validateCreationAvailability(namespace expected: HanlinConversationNamespace) throws {
        guard !poisoned else { throw PinkhaHanlinWriteError.unavailable }
        guard expected == namespace else { throw PinkhaHanlinWriteError.invalidPlan }
        guard !entries.values.contains(where: { $0.effect == .reserved || $0.effect == .uncertain }) else {
            throw PinkhaHanlinWriteError.unresolved
        }
        guard entries.count < Self.maximumEntries else { throw PinkhaHanlinWriteError.journalFull }
    }

    public func reserve(_ identity: PinkhaHanlinWriteIdentity) throws {
        guard !poisoned else { throw PinkhaHanlinWriteError.unavailable }
        try identity.validate()
        guard identity.session.context.namespace == namespace else { throw PinkhaHanlinWriteError.invalidPlan }
        if let existing = entries[identity.key] {
            throw existing.identity == identity ? PinkhaHanlinWriteError.duplicate : .conflict
        }
        // A second provider-call identity cannot mint a retry under another invocation ID.
        if entries.values.contains(where: {
            $0.identity.runID == identity.runID && $0.identity.step == identity.step
                && $0.identity.providerCallDigest == identity.providerCallDigest
        }) { throw PinkhaHanlinWriteError.conflict }
        try validateCreationAvailability(namespace: identity.session.context.namespace)
        let entry = Entry(version: 1, identity: identity, effect: .reserved, createdObjectReference: nil)
        try append(entry)
        entries[identity.key] = entry
    }

    /// Late authoritative success may refine uncertain to committed in the ORIGINAL scope.
    /// No error/cancel can downgrade committed, and no retry/retarget is performed here.
    @discardableResult
    public func record(_ effect: Effect, identity: PinkhaHanlinWriteIdentity,
                createdObjectReference: String? = nil) throws -> Entry {
        guard !poisoned, effect != .reserved,
              let previous = entries[identity.key], previous.identity == identity else {
            throw PinkhaHanlinWriteError.unavailable
        }
        if previous.effect == .committed {
            if let createdObjectReference,
               previous.createdObjectReference.map({ Data($0.utf8) }) != Data(createdObjectReference.utf8) {
                throw PinkhaHanlinWriteError.conflict
            }
            return previous
        }
        if let recovery = knownObjects[identity.key] {
            try recovery.validate(against: Entry(version: 1, identity: identity, effect: effect,
                                                 createdObjectReference: createdObjectReference))
        }
        if previous.effect == effect {
            guard previous.createdObjectReference.map({ Data($0.utf8) }) == createdObjectReference.map({ Data($0.utf8) }) else {
                throw PinkhaHanlinWriteError.conflict
            }
            return previous
        }
        guard previous.effect == .reserved || (previous.effect == .uncertain && effect == .committed) else {
            throw PinkhaHanlinWriteError.conflict
        }
        let entry = Entry(version: 1, identity: identity, effect: effect, createdObjectReference: createdObjectReference)
        try Self.validate(entry)
        try append(entry)
        entries[identity.key] = entry
        return entry
    }


    /// A native root ID with unverified/partial bootstrap is recovery metadata,
    /// never a committed receipt or permission to read that object. This sidecar
    /// leaves every existing v1 reservation/outcome byte unchanged.
    public func recordKnownIncompleteObject(_ objectID: String, identity: PinkhaHanlinWriteIdentity) throws {
        guard !poisoned, let previous = entries[identity.key], previous.identity == identity else {
            throw PinkhaHanlinWriteError.unavailable
        }
        let recovery = PinkhaHanlinKnownObjectRecovery(version: 1, identity: identity,
                                                        createdObjectReference: objectID)
        try recovery.validate(against: previous)
        if let existing = knownObjects[identity.key] {
            guard existing == recovery else { throw PinkhaHanlinWriteError.conflict }
            return
        }
        // A confirmed matching receipt is already stronger original-scope evidence.
        if previous.effect == .committed { return }
        do {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            try store.append(name: identity.key + PinkhaHanlinKnownObjectRecovery.suffix,
                             bytes: encoder.encode(recovery))
            knownObjects[identity.key] = recovery
        } catch {
            poisoned = true
            throw PinkhaHanlinWriteError.unavailable
        }
    }

    public func knownCreatedObjectReference(for identity: PinkhaHanlinWriteIdentity) throws -> String? {
        guard !removed else { throw PinkhaHanlinWriteError.unavailable }
        guard identity.session.context.namespace == namespace else { throw PinkhaHanlinWriteError.invalidPlan }
        guard let entry = entries[identity.key] else { return nil }
        guard entry.identity == identity else { throw PinkhaHanlinWriteError.conflict }
        return knownObjects[identity.key]?.createdObjectReference ?? entry.createdObjectReference
    }

    public func receipt(for identity: PinkhaHanlinWriteIdentity) throws -> Entry? {
        guard !removed else { throw PinkhaHanlinWriteError.unavailable }
        guard identity.session.context.namespace == namespace else { throw PinkhaHanlinWriteError.invalidPlan }
        guard let entry = entries[identity.key] else { return nil }
        guard entry.identity == identity else { throw PinkhaHanlinWriteError.conflict }
        return entry // Metadata only; not a permission to read the resulting object.
    }

    /// Only the explicit account remove-data path calls this. Ordinary dismissal/logout retains
    /// reservations so a late native callback can refine the ORIGINAL uncertain outcome.
    public func revokeForDataRemoval() {
        poisoned = true
        removed = true
        entries.removeAll()
        knownObjects.removeAll()
        store.releaseOwnershipForRemoval()
    }

    public static func removeAccountData(_ account: String, app: String = PinkhaHanlinEngineNamespace.heart) async throws {
        guard PinkhaHanlinEngineNamespace.supports(app) else { throw PinkhaHanlinWriteError.invalidPlan }
        #if os(iOS)
        try await Task.detached {
            let base = try FileManager.default.url(for: .applicationSupportDirectory,
                in: .userDomainMask, appropriateFor: nil, create: false)
            try PinkhaHanlinProtectedMetadataFiles.removeAccountData(account,
                parent: base.appendingPathComponent("Anytype", isDirectory: true), app: app)
        }.value
        #else
        throw PinkhaHanlinWriteError.unavailable
        #endif
    }

    #if DEBUG
    static func removeAccountDataInTestDirectory(_ account: String, parent: URL) throws {
        try PinkhaHanlinProtectedMetadataFiles.removeAccountData(account, parent: parent)
    }
    #endif

    private func append(_ entry: Entry) throws {
        do {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            try store.append(name: entry.identity.key + "." + entry.effect.rawValue, bytes: encoder.encode(entry))
        } catch {
            poisoned = true // Preserve every partial/unknown file; don't delete, overwrite, reset or retry.
            throw PinkhaHanlinWriteError.unavailable
        }
    }

    private static func validate(_ entry: Entry) throws {
        if entry.effect == .committed {
            guard let reference = entry.createdObjectReference, !reference.isEmpty, reference.utf8.count <= 256 else {
                throw PinkhaHanlinWriteError.corruptJournal
            }
        } else if entry.createdObjectReference != nil { throw PinkhaHanlinWriteError.corruptJournal }
    }
}

#if os(iOS)
enum PinkhaHanlinMetadataProtection {
    static func acceptsReadback(_ attributes: [FileAttributeKey: Any]) -> Bool {
        #if targetEnvironment(simulator)
        // The verified iOS 27 UIKit probe returned no protectionKey after a
        // successful protection write, in both supported storage locations.
        // This permits missing Simulator metadata only; it proves no physical
        // data protection. All mode, ownership and durability guards still run.
        if attributes[.protectionKey] == nil { return true }
        #endif
        let raw = (attributes[.protectionKey] as? FileProtectionType)?.rawValue
            ?? (attributes[.protectionKey] as? String)
        return raw == FileProtectionType.completeUntilFirstUserAuthentication.rawValue
    }
}
#endif

/// File ownership is exclusive for this actor's lifetime; advisory lock coordinates this feature's
/// cooperating owners, not arbitrary code in the app. On unsupported platforms it fails closed.
private final class PinkhaHanlinProtectedMetadataFiles: Sendable {
    private let directory: URL
    private let parents: [URL]
    private let lockFD: Int32

    init(parent: URL, scope: String) throws {
        #if os(iOS)
        let parentInfo = try parent.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
        guard parentInfo.isSymbolicLink != true, parentInfo.isDirectory == true else { throw PinkhaHanlinWriteError.unavailable }
        let root = parent.appendingPathComponent("HanlinHostMetadataV1", isDirectory: true)
        let directory = root.appendingPathComponent(scope, isDirectory: true)
        for folder in [root, directory] {
            do {
                try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false,
                    attributes: [.posixPermissions: 0o700, .protectionKey: FileProtectionType.completeUntilFirstUserAuthentication])
            } catch let error as CocoaError where error.code == .fileWriteFileExists {
                // Reopening a scope, or sharing this feature root with another
                // account, must validate the existing entry below. Never repair
                // its permissions or treat a file/symlink as a valid directory.
            }
            let values = try folder.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
            guard values.isSymbolicLink != true, values.isDirectory == true else { throw PinkhaHanlinWriteError.unavailable }
            var url = folder; var backup = URLResourceValues(); backup.isExcludedFromBackup = true
            try url.setResourceValues(backup)
            let attributes = try FileManager.default.attributesOfItem(atPath: folder.path)
            guard PinkhaHanlinMetadataProtection.acceptsReadback(attributes),
                  (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700 else { throw PinkhaHanlinWriteError.unavailable }
        }
        let lockURL = directory.appendingPathComponent("owner.lock")
        let fd = Darwin.open(lockURL.path, O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fd >= 0 else { throw PinkhaHanlinWriteError.unavailable }
        guard flock(fd, LOCK_EX | LOCK_NB) == 0 else { Darwin.close(fd); throw PinkhaHanlinWriteError.unavailable }
        do {
            var info = stat()
            guard fstat(fd, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG else { throw PinkhaHanlinWriteError.unavailable }
            try FileManager.default.setAttributes([.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication,
                .posixPermissions: 0o600], ofItemAtPath: lockURL.path)
        } catch { Darwin.close(fd); throw PinkhaHanlinWriteError.unavailable }
        self.directory = directory; self.parents = [directory, root, parent]; self.lockFD = fd
        #else
        throw PinkhaHanlinWriteError.unavailable
        #endif
    }

    deinit {
        #if os(iOS)
        Darwin.close(lockFD) // Never remove the lock file or the records when releasing ownership.
        #endif
    }

    func readAll(maximumFiles: Int) throws -> [(String, Data)] {
        #if os(iOS)
        let urls = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        guard urls.count <= maximumFiles + 2 else { throw PinkhaHanlinWriteError.corruptJournal }
        return try urls.filter { $0.lastPathComponent != "owner.lock" && $0.lastPathComponent != "namespace.json" }.map { url in
            let fd = Darwin.open(url.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw PinkhaHanlinWriteError.corruptJournal }
            let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
            defer { try? handle.close() }
            var info = stat()
            guard fstat(fd, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
                  info.st_mode & 0o777 == 0o600,
                  info.st_size > 0, info.st_size <= 16_384,
                  let bytes = try handle.read(upToCount: 16_385), bytes.count <= 16_384 else {
                throw PinkhaHanlinWriteError.corruptJournal
            }
            let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
            guard PinkhaHanlinMetadataProtection.acceptsReadback(attributes) else {
                throw PinkhaHanlinWriteError.corruptJournal
            }
            return (url.lastPathComponent, bytes)
        }
        #else
        throw PinkhaHanlinWriteError.unavailable
        #endif
    }

    func recordNamespace(_ namespace: HanlinConversationNamespace) throws {
        #if os(iOS)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(namespace)
        let url = directory.appendingPathComponent("namespace.json")
        if FileManager.default.fileExists(atPath: url.path) {
            guard try Self.readNamespace(url) == namespace else { throw PinkhaHanlinWriteError.corruptJournal }
        } else {
            try append(name: "namespace.json", bytes: bytes)
        }
        #else
        throw PinkhaHanlinWriteError.unavailable
        #endif
    }

    func releaseOwnershipForRemoval() {
        #if os(iOS)
        // The containing journal actor is already poisoned. No operation can append afterward.
        _ = flock(lockFD, LOCK_UN)
        #endif
    }

    static func removeAccountData(_ account: String, parent: URL, app: String = PinkhaHanlinEngineNamespace.heart) throws {
        guard PinkhaHanlinEngineNamespace.supports(app) else { throw PinkhaHanlinWriteError.invalidPlan }
        #if os(iOS)
        let root = parent.appendingPathComponent("HanlinHostMetadataV1", isDirectory: true)
        guard FileManager.default.fileExists(atPath: root.path) else { return }
        let parentInfo = try parent.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
        guard parentInfo.isSymbolicLink != true, parentInfo.isDirectory == true else { throw PinkhaHanlinWriteError.corruptJournal }
        let rootInfo = try root.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
        guard rootInfo.isSymbolicLink != true, rootInfo.isDirectory == true else { throw PinkhaHanlinWriteError.corruptJournal }
        for directory in try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil) {
            let info = try directory.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
            guard info.isSymbolicLink != true, info.isDirectory == true else { throw PinkhaHanlinWriteError.corruptJournal }
            // Missing/corrupt ownership metadata is preserved and reported, never guessed or erased.
            let namespace = try readNamespace(directory.appendingPathComponent("namespace.json"))
            guard PinkhaHanlinEngineNamespace.supports(namespace.app) else { throw PinkhaHanlinWriteError.corruptJournal }
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            guard directory.lastPathComponent == PinkhaHanlinCreatePagePlan.digest(try encoder.encode(namespace)) else {
                throw PinkhaHanlinWriteError.corruptJournal
            }
            guard namespace.app.utf8.elementsEqual(app.utf8),
                  namespace.account.utf8.elementsEqual(account.utf8) else { continue }
            let fd = Darwin.open(directory.appendingPathComponent("owner.lock").path, O_RDWR | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw PinkhaHanlinWriteError.unavailable }
            defer { Darwin.close(fd) }
            guard flock(fd, LOCK_EX | LOCK_NB) == 0 else { throw PinkhaHanlinWriteError.unavailable }
            try FileManager.default.removeItem(at: directory)
        }
        #else
        throw PinkhaHanlinWriteError.unavailable
        #endif
    }

    func append(name: String, bytes: Data) throws {
        #if os(iOS)
        guard bytes.count <= 16_384, !name.contains("/"), !name.contains("\\") else { throw PinkhaHanlinWriteError.unavailable }
        let url = directory.appendingPathComponent(name)
        let fd = Darwin.open(url.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fd >= 0 else { throw PinkhaHanlinWriteError.unavailable }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        try FileManager.default.setAttributes([.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication], ofItemAtPath: url.path)
        try handle.write(contentsOf: bytes)
        try handle.synchronize()
        guard Darwin.fcntl(fd, F_FULLFSYNC) == 0 else { throw PinkhaHanlinWriteError.unavailable }
        for folder in parents {
            let parentFD = Darwin.open(folder.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard parentFD >= 0 else { throw PinkhaHanlinWriteError.unavailable }
            let synchronized = Darwin.fsync(parentFD) == 0
            Darwin.close(parentFD)
            guard synchronized else { throw PinkhaHanlinWriteError.unavailable }
        }
        // Strong flush after the directory update too. Failure leaves an unresolved/partial record.
        guard Darwin.fcntl(fd, F_FULLFSYNC) == 0 else { throw PinkhaHanlinWriteError.unavailable }
        #else
        throw PinkhaHanlinWriteError.unavailable
        #endif
    }

    #if os(iOS)
    private static func readNamespace(_ url: URL) throws -> HanlinConversationNamespace {
        let fd = Darwin.open(url.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw PinkhaHanlinWriteError.corruptJournal }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var info = stat()
        guard fstat(fd, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
              info.st_mode & 0o777 == 0o600,
              info.st_size > 0, info.st_size <= 4_096,
              let bytes = try handle.read(upToCount: 4_097), bytes.count <= 4_096 else {
            throw PinkhaHanlinWriteError.corruptJournal
        }
        guard PinkhaHanlinMetadataProtection.acceptsReadback(try FileManager.default.attributesOfItem(atPath: url.path)) else {
            throw PinkhaHanlinWriteError.corruptJournal
        }
        let namespace = try JSONDecoder().decode(HanlinConversationNamespace.self, from: bytes)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        guard try encoder.encode(namespace) == bytes else { throw PinkhaHanlinWriteError.corruptJournal }
        return namespace
    }

    #endif
}