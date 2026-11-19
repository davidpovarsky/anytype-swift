import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
#if canImport(Darwin)
import Darwin
#endif

/// Independent of the SDK database: a rebuild cannot erase an unresolved
/// create and turn it into a duplicate. Files contain only scoped metadata.
public actor AnyProtectedCreationJournal: AnyNativeCreationJournaling {
    public nonisolated let workspace: AnyTorahWorkspace
    private struct Entry: Codable, Equatable {
        let version: Int
        let identity: AnyNativeCreationIdentity
        let state: AnyNativeCreationState
    }
    private let files: AnyCreationMetadataFiles
    private var entries: [String: Entry]
    private var poisoned = false
    private static let maximumEntries = 10_000

    private init(workspace: AnyTorahWorkspace, files: AnyCreationMetadataFiles,
                 entries: [String: Entry]) {
        self.workspace = workspace; self.files = files; self.entries = entries
    }

    public static func open(workspace: AnyTorahWorkspace) async throws -> AnyProtectedCreationJournal {
        #if canImport(Darwin)
        return try await Task.detached {
            let support = try FileManager.default.url(for: .applicationSupportDirectory,
                in: .userDomainMask, appropriateFor: nil, create: true)
            let host = support.appendingPathComponent("Anytype", isDirectory: true)
            try FileManager.default.createDirectory(at: host, withIntermediateDirectories: true)
            return try load(workspace: workspace, parent: host)
        }.value
        #else
        throw AnyNativeCreationError.journalUnavailable
        #endif
    }

    #if DEBUG
    static func openForTesting(workspace: AnyTorahWorkspace, parent: URL) throws -> AnyProtectedCreationJournal {
        try load(workspace: workspace, parent: parent)
    }
    #endif

    private static func load(workspace: AnyTorahWorkspace, parent: URL) throws -> AnyProtectedCreationJournal {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let scopeBytes = try encoder.encode(workspace)
        let scope = AnyContentDigest.sha256(scopeBytes)
        let files = try AnyCreationMetadataFiles(parent: parent, scope: scope)
        let stored = try files.readAll(maximumFiles: maximumEntries * 3 + 1)
        var reservations: [String: Entry] = [:]
        var terminal: [Entry] = []
        var namespacePresent = false
        for (name, data) in stored {
            if name == "workspace.json" {
                guard data == scopeBytes else { throw AnyNativeCreationError.corruptJournal }
                namespacePresent = true
                continue
            }
            let entry = try JSONDecoder().decode(Entry.self, from: data)
            guard entry.version == 1, entry.identity.workspace == workspace,
                  try encoder.encode(entry) == data,
                  name == entry.identity.key + "." + stage(entry.state) + ".json" else {
                throw AnyNativeCreationError.corruptJournal
            }
            try validate(entry)
            if entry.state == .reserved {
                guard reservations.updateValue(entry, forKey: entry.identity.key) == nil else {
                    throw AnyNativeCreationError.corruptJournal
                }
            } else { terminal.append(entry) }
        }
        guard reservations.count <= maximumEntries else { throw AnyNativeCreationError.journalFull }
        for entry in terminal.sorted(by: { stage($0.state) < stage($1.state) }) {
            guard let previous = reservations[entry.identity.key], previous.identity == entry.identity else {
                throw AnyNativeCreationError.corruptJournal
            }
            try transition(from: previous.state, to: entry.state)
            reservations[entry.identity.key] = entry
        }
        if !namespacePresent {
            guard stored.isEmpty else { throw AnyNativeCreationError.corruptJournal }
            try files.append(name: "workspace.json", bytes: scopeBytes)
        }
        return .init(workspace: workspace, files: files, entries: reservations)
    }

    public func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        try requireAvailable(identity)
        if let existing = entries[identity.key] {
            guard existing.identity == identity else { throw AnyNativeCreationError.contentConflict }
            return .init(state: existing.state, ownsDispatch: false)
        }
        guard entries.count < Self.maximumEntries else { throw AnyNativeCreationError.journalFull }
        let entry = Entry(version: 1, identity: identity, state: .reserved)
        try append(entry)
        entries[identity.key] = entry
        return .init(state: .reserved, ownsDispatch: true)
    }

    public func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        try requireAvailable(identity)
        guard state != .reserved, let previous = entries[identity.key],
              previous.identity == identity else { throw AnyNativeCreationError.contentConflict }
        if previous.state == state { return }
        // A confirmed result cannot be downgraded by a delayed callback.
        if case .verified(let oldID) = previous.state, case .created(let id) = state, oldID == id { return }
        try Self.transition(from: previous.state, to: state)
        let entry = Entry(version: 1, identity: identity, state: state)
        try Self.validate(entry)
        try append(entry)
        entries[identity.key] = entry
    }

    public func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        try requireAvailable(identity)
        guard let existing = entries[identity.key] else { return nil }
        guard existing.identity == identity else { throw AnyNativeCreationError.contentConflict }
        return existing.state
    }

    /// Call only after the session has drained. Ordinary logout preserves records.
    public func close() {
        poisoned = true
        files.releaseOwnership()
    }

    public static func removeAccountData(accountID: String) async throws {
        #if canImport(Darwin)
        try await Task.detached {
            let support = try FileManager.default.url(for: .applicationSupportDirectory,
                in: .userDomainMask, appropriateFor: nil, create: false)
            try AnyCreationMetadataFiles.removeAccountData(accountID,
                parent: support.appendingPathComponent("Anytype", isDirectory: true))
        }.value
        #else
        throw AnyNativeCreationError.journalUnavailable
        #endif
    }

    private func requireAvailable(_ identity: AnyNativeCreationIdentity) throws {
        guard !poisoned else { throw AnyNativeCreationError.journalUnavailable }
        guard identity.workspace == workspace else { throw AnyHostError.wrongWorkspace }
    }
    private func append(_ entry: Entry) throws {
        do {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            try files.append(name: entry.identity.key + "." + Self.stage(entry.state) + ".json",
                             bytes: encoder.encode(entry))
        } catch {
            poisoned = true
            throw AnyNativeCreationError.journalUnavailable
        }
    }
    private static func stage(_ state: AnyNativeCreationState) -> String {
        switch state { case .reserved: "reserved"; case .created: "created"; case .verified: "verified" }
    }
    private static func validate(_ entry: Entry) throws {
        if let id = entry.state.objectID {
            guard AnyEditorBlock.validID(id) else { throw AnyNativeCreationError.corruptJournal }
        }
    }
    private static func transition(from: AnyNativeCreationState, to: AnyNativeCreationState) throws {
        switch (from, to) {
        case (.reserved, .created): return
        case (.created(let a), .verified(let b)) where a == b: return
        default: throw AnyNativeCreationError.contentConflict
        }
    }
}

/// Same restrictive storage policy as the preserved Hanlin journal, with
/// directory-relative descriptors and metadata ownership checks for this scope.
private final class AnyCreationMetadataFiles: Sendable {
    private let directory: URL
    private let directoryFD: Int32
    private let lockFD: Int32

    init(parent: URL, scope: String) throws {
        #if canImport(Darwin)
        try Self.requireDirectory(parent, checkMode: false)
        let root = parent.appendingPathComponent("AnyNativeCreationMetadataV1", isDirectory: true)
        let directory = root.appendingPathComponent(scope, isDirectory: true)
        for url in [root, directory] {
            var attributes: [FileAttributeKey: Any] = [.posixPermissions: 0o700]
            #if os(iOS)
            attributes[.protectionKey] = FileProtectionType.completeUntilFirstUserAuthentication
            #endif
            try FileManager.default.createDirectory(at: url, withIntermediateDirectories: false,
                                                     attributes: attributes)
            try Self.requireDirectory(url, checkMode: true)
            var mutable = url; var values = URLResourceValues(); values.isExcludedFromBackup = true
            try mutable.setResourceValues(values)
            try Self.requireProtection(url)
        }
        let dir = Darwin.open(directory.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard dir >= 0 else { throw AnyNativeCreationError.journalUnavailable }
        let lock = Darwin.openat(dir, "owner.lock", O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard lock >= 0 else { Darwin.close(dir); throw AnyNativeCreationError.journalUnavailable }
        do {
            try Self.requireFile(lock, maximumBytes: 16_384, allowEmpty: true)
            guard flock(lock, LOCK_EX | LOCK_NB) == 0 else { throw AnyNativeCreationError.journalUnavailable }
            try Self.protect(directory.appendingPathComponent("owner.lock"))
            for url in [directory, root, parent] {
                let fd = Darwin.open(url.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                guard fd >= 0 else { throw AnyNativeCreationError.journalUnavailable }
                let ok = fsync(fd) == 0; Darwin.close(fd)
                guard ok else { throw AnyNativeCreationError.journalUnavailable }
            }
        } catch { Darwin.close(lock); Darwin.close(dir); throw error }
        self.directory = directory; self.directoryFD = dir; self.lockFD = lock
        #else
        throw AnyNativeCreationError.journalUnavailable
        #endif
    }
    deinit {
        #if canImport(Darwin)
        Darwin.close(lockFD); Darwin.close(directoryFD)
        #endif
    }
    func releaseOwnership() {
        #if canImport(Darwin)
        _ = flock(lockFD, LOCK_UN)
        #endif
    }
    func readAll(maximumFiles: Int) throws -> [(String, Data)] {
        #if canImport(Darwin)
        let urls = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        guard urls.count <= maximumFiles + 1 else { throw AnyNativeCreationError.journalFull }
        return try urls.filter { $0.lastPathComponent != "owner.lock" }.map { url in
            let name = url.lastPathComponent
            guard !name.contains("/"), !name.contains("\\") else { throw AnyNativeCreationError.corruptJournal }
            let fd = Darwin.openat(directoryFD, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw AnyNativeCreationError.corruptJournal }
            let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
            defer { try? handle.close() }
            try Self.requireFile(fd, maximumBytes: 16_384)
            try Self.requireProtection(url)
            guard let bytes = try handle.read(upToCount: 16_385), bytes.count <= 16_384, !bytes.isEmpty else {
                throw AnyNativeCreationError.corruptJournal
            }
            return (name, bytes)
        }
        #else
        throw AnyNativeCreationError.journalUnavailable
        #endif
    }
    func append(name: String, bytes: Data) throws {
        #if canImport(Darwin)
        guard !name.isEmpty, !name.contains("/"), !name.contains("\\"), !bytes.isEmpty, bytes.count <= 16_384 else {
            throw AnyNativeCreationError.journalUnavailable
        }
        let fd = Darwin.openat(directoryFD, name,
            O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fd >= 0 else { throw AnyNativeCreationError.journalUnavailable }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        try Self.requireFile(fd, maximumBytes: 16_384, allowEmpty: true)
        try Self.protect(directory.appendingPathComponent(name))
        try handle.write(contentsOf: bytes)
        try handle.synchronize()
        guard Darwin.fcntl(fd, F_FULLFSYNC) == 0, fsync(directoryFD) == 0,
              Darwin.fcntl(fd, F_FULLFSYNC) == 0 else { throw AnyNativeCreationError.journalUnavailable }
        #else
        throw AnyNativeCreationError.journalUnavailable
        #endif
    }

    #if canImport(Darwin)
    static func removeAccountData(_ accountID: String, parent: URL) throws {
        let root = parent.appendingPathComponent("AnyNativeCreationMetadataV1", isDirectory: true)
        guard FileManager.default.fileExists(atPath: root.path) else { return }
        try requireDirectory(parent, checkMode: false); try requireDirectory(root, checkMode: true)
        for directory in try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil) {
            try requireDirectory(directory, checkMode: true)
            let scope = directory.lastPathComponent
            guard AnyNativeCreationIdentity.isHex(scope, count: 64) else { throw AnyNativeCreationError.corruptJournal }
            let owner = try AnyCreationMetadataFiles(parent: parent, scope: scope)
            let files = try owner.readAll(maximumFiles: 30_001)
            guard let data = files.first(where: { $0.0 == "workspace.json" })?.1 else {
                throw AnyNativeCreationError.corruptJournal
            }
            let workspace = try JSONDecoder().decode(AnyTorahWorkspace.self, from: data)
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            guard try encoder.encode(workspace) == data, AnyContentDigest.sha256(data) == scope else {
                throw AnyNativeCreationError.corruptJournal
            }
            guard workspace.accountID.utf8.elementsEqual(accountID.utf8) else { continue }
            try FileManager.default.removeItem(at: directory)
        }
    }
    private static func requireDirectory(_ url: URL, checkMode: Bool) throws {
        let values = try url.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
        guard values.isSymbolicLink != true, values.isDirectory == true else {
            throw AnyNativeCreationError.journalUnavailable
        }
        var info = stat()
        guard lstat(url.path, &info) == 0, info.st_uid == geteuid(),
              (info.st_mode & S_IFMT) == S_IFDIR,
              !checkMode || info.st_mode & 0o777 == 0o700 else {
            throw AnyNativeCreationError.journalUnavailable
        }
    }
    private static func requireFile(_ fd: Int32, maximumBytes: Int, allowEmpty: Bool = false) throws {
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_nlink == 1,
              (info.st_mode & S_IFMT) == S_IFREG, info.st_mode & 0o777 == 0o600,
              (allowEmpty || info.st_size > 0), info.st_size <= maximumBytes else {
            throw AnyNativeCreationError.corruptJournal
        }
    }
    private static func protect(_ url: URL) throws {
        #if os(iOS)
        try FileManager.default.setAttributes(
            [.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication], ofItemAtPath: url.path)
        #endif
        try requireProtection(url)
    }
    private static func requireProtection(_ url: URL) throws {
        #if os(iOS)
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        #if targetEnvironment(simulator)
        // Same established Simulator exception as the old host. This does not
        // assert physical-device data protection; that gate remains separate.
        if attributes[.protectionKey] == nil { return }
        #endif
        let raw = (attributes[.protectionKey] as? FileProtectionType)?.rawValue
            ?? attributes[.protectionKey] as? String
        guard raw == FileProtectionType.completeUntilFirstUserAuthentication.rawValue else {
            throw AnyNativeCreationError.journalUnavailable
        }
        #endif
    }
    #endif
}
