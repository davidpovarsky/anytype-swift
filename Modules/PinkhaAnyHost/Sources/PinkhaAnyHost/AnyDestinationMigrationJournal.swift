import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

struct AnyDestinationJournalEntry: Codable, Sendable {
    static let version = "pinkha-destination-intent-checkpoint-v1"
    let version: String
    let index: Int
    let sourceKey: String
    let itemSHA256: String
    let resolvedOperation: Data
    let expectedApplySequence: Int64?
    let inlineContent: Data?
    let intentID: String
    let specBytes: Data
    let specSHA256: String
    var receipts: [AnyJSON]

    init(index: Int, sourceKey: String, itemSHA256: String, resolvedOperation: Data,
         expectedApplySequence: Int64?, inlineContent: Data?, intentID: String,
         specBytes: Data, specSHA256: String) {
        version = Self.version; self.index = index; self.sourceKey = sourceKey
        self.itemSHA256 = itemSHA256; self.resolvedOperation = resolvedOperation
        self.expectedApplySequence = expectedApplySequence; self.inlineContent = inlineContent
        self.intentID = intentID; self.specBytes = specBytes; self.specSHA256 = specSHA256
        receipts = []
    }
}

/// Files contain private migration content. They are never an admission proof
/// for native state: every restored receipt is reconciled with its original
/// native intent before another destination action can proceed.
final class AnyDestinationMigrationJournal: @unchecked Sendable {
    static let maximumEntryBytes = 8 * 1024 * 1024
    private let directory: URL
    private let directoryFD: Int32
    private let lockFD: Int32
    private let plan: AnyDestinationMigrationPlan

    private struct Envelope: Codable {
        let version: String
        let contentSHA256: String
        let content: Data
    }

    init(parent: URL, plan: AnyDestinationMigrationPlan) throws {
        guard parent.isFileURL else { throw AnyDestinationMigrationError.journalUnavailable }
        try Self.requireDirectory(parent, privateMode: false)
        let root = parent.appendingPathComponent("AnyDestinationMigrationV1", isDirectory: true)
        let scope = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            plan.binding.workspace.accountID, plan.binding.workspace.spaceID,
            plan.binding.storeID, plan.binding.planID
        ]))
        let directory = root.appendingPathComponent(scope, isDirectory: true)
        for path in [root, directory] {
            var attributes: [FileAttributeKey: Any] = [.posixPermissions: 0o700]
            #if os(iOS)
            attributes[.protectionKey] = FileProtectionType.completeUntilFirstUserAuthentication
            #endif
            if mkdir(path.path, mode_t(0o700)) != 0 && errno != EEXIST {
                throw AnyDestinationMigrationError.journalUnavailable
            }
            try Self.requireDirectory(path, privateMode: true)
            #if os(iOS)
            try FileManager.default.setAttributes(attributes, ofItemAtPath: path.path)
            #endif
            #if canImport(Darwin)
            var mutable = path; var values = URLResourceValues(); values.isExcludedFromBackup = true
            try mutable.setResourceValues(values)
            #endif
        }
        let directoryFD = open(directory.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directoryFD >= 0 else { throw AnyDestinationMigrationError.journalUnavailable }
        let lockFD = openat(directoryFD, "owner.lock", O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard lockFD >= 0 else { close(directoryFD); throw AnyDestinationMigrationError.journalUnavailable }
        do {
            try Self.requireDirectoryIdentity(directoryFD, path: directory)
            try Self.requireFile(lockFD, maximum: 0)
            guard flock(lockFD, LOCK_EX | LOCK_NB) == 0 else { throw AnyDestinationMigrationError.alreadyExecuting }
            for path in [directory, root, parent] {
                let fd = open(path.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                guard fd >= 0 else { throw AnyDestinationMigrationError.journalUnavailable }
                let status = fsync(fd); close(fd)
                guard status == 0 else { throw AnyDestinationMigrationError.journalUnavailable }
            }
        } catch { close(lockFD); close(directoryFD); throw error }
        self.directory = directory; self.directoryFD = directoryFD; self.lockFD = lockFD; self.plan = plan
        do {
            try validateNames()
            if let previous = try read(name: "plan.json", maximum: AnyDestinationMigrationPlan.maximumPlanBytes) {
                guard previous == plan.canonicalBytes else { throw AnyDestinationMigrationError.changedPlan }
            } else {
                let names = try FileManager.default.contentsOfDirectory(atPath: directory.path)
                guard !names.contains(where: { $0.hasPrefix("entry-") }) else {
                    throw AnyDestinationMigrationError.journalCorrupt
                }
                try write(name: "plan.json", bytes: plan.canonicalBytes,
                          maximum: AnyDestinationMigrationPlan.maximumPlanBytes)
            }
        } catch { throw error }
    }

    deinit { _ = flock(lockFD, LOCK_UN); close(lockFD); close(directoryFD) }

    func load(index: Int) throws -> AnyDestinationJournalEntry? {
        let item = plan.items[index]
        guard let data = try read(name: name(index: index), maximum: Self.maximumEntryBytes) else { return nil }
        let envelope = try JSONDecoder().decode(Envelope.self, from: data)
        guard envelope.version == AnyDestinationJournalEntry.version,
              envelope.contentSHA256 == AnyContentDigest.sha256(envelope.content) else {
            throw AnyDestinationMigrationError.journalCorrupt
        }
        let entry = try JSONDecoder().decode(AnyDestinationJournalEntry.self, from: envelope.content)
        guard entry.version == AnyDestinationJournalEntry.version, entry.index == index,
              Data(entry.sourceKey.utf8) == Data(item.sourceKey.utf8),
              entry.itemSHA256 == AnyContentDigest.sha256(try Self.encoded(item)),
              AnyDestinationPlanChecks.digest(entry.intentID), AnyDestinationPlanChecks.digest(entry.specSHA256),
              entry.specSHA256 == AnyContentDigest.sha256(entry.specBytes), !entry.specBytes.isEmpty,
              entry.specBytes.count <= 1_048_576, entry.resolvedOperation.count <= 2_097_152,
              entry.receipts.count <= 32, (entry.inlineContent?.count ?? 0) <= 4095,
              entry.expectedApplySequence.map({ $0 > 0 }) ?? true,
              try Self.encoded(entry) == envelope.content else {
            throw AnyDestinationMigrationError.journalCorrupt
        }
        return entry
    }

    func save(_ entry: AnyDestinationJournalEntry) throws {
        guard entry.index >= 0, entry.index < plan.items.count,
              Data(entry.sourceKey.utf8) == Data(plan.items[entry.index].sourceKey.utf8) else {
            throw AnyDestinationMigrationError.journalCorrupt
        }
        let content = try Self.encoded(entry)
        let envelope = Envelope(version: AnyDestinationJournalEntry.version,
                                contentSHA256: AnyContentDigest.sha256(content), content: content)
        try write(name: name(index: entry.index), bytes: Self.encoded(envelope), maximum: Self.maximumEntryBytes)
    }

    static func encoded<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }

    private func name(index: Int) -> String {
        "entry-\(index)-\(AnyContentDigest.sha256(Data(plan.items[index].sourceKey.utf8))).json"
    }

    private func validateNames() throws {
        try Self.requireDirectoryIdentity(directoryFD, path: directory)
        let names = try FileManager.default.contentsOfDirectory(atPath: directory.path)
        guard names.count <= plan.items.count + 128 else { throw AnyDestinationMigrationError.journalCorrupt }
        let expected = Set(plan.items.indices.map { name(index: $0) })
        for name in names {
            if name == "owner.lock" || name == "plan.json" || expected.contains(name) { continue }
            // A process killed before atomic rename may leave an owned staging
            // file. It is retained, never interpreted as a completed checkpoint.
            guard name.hasPrefix(".pending-"), UUID(uuidString: String(name.dropFirst(9))) != nil else {
                throw AnyDestinationMigrationError.journalCorrupt
            }
            _ = try read(name: name, maximum: max(Self.maximumEntryBytes, AnyDestinationMigrationPlan.maximumPlanBytes))
        }
        try Self.requireDirectoryIdentity(directoryFD, path: directory)
    }

    private func read(name: String, maximum: Int) throws -> Data? {
        try Self.requireDirectoryIdentity(directoryFD, path: directory)
        let fd = openat(directoryFD, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        if fd < 0 {
            if errno == ENOENT { return nil }
            throw AnyDestinationMigrationError.journalCorrupt
        }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        let expected = try Self.requireFile(fd, maximum: maximum)
        var data = Data()
        while data.count <= maximum {
            let part = try handle.read(upToCount: min(1_048_576, maximum + 1 - data.count)) ?? Data()
            if part.isEmpty { break }
            data.append(part)
        }
        guard data.count == expected, data.count <= maximum,
              try Self.requireFile(fd, maximum: maximum) == expected else {
            throw AnyDestinationMigrationError.journalCorrupt
        }
        return data
    }

    private func write(name: String, bytes: Data, maximum: Int) throws {
        try Self.requireDirectoryIdentity(directoryFD, path: directory)
        guard !bytes.isEmpty, bytes.count <= maximum, !name.contains("/"), !name.contains("\\") else {
            throw AnyDestinationMigrationError.journalUnavailable
        }
        // Existing files must also be owned regular files, not an alternate
        // path or hard link. renameat replaces only this owned directory entry.
        _ = try read(name: name, maximum: maximum)
        let temporary = ".pending-" + UUID().uuidString
        let fd = openat(directoryFD, temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fd >= 0 else { throw AnyDestinationMigrationError.journalUnavailable }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        _ = try Self.requireFile(fd, maximum: maximum)
        #if os(iOS)
        try FileManager.default.setAttributes([.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication],
                                              ofItemAtPath: directory.appendingPathComponent(temporary).path)
        #endif
        try handle.write(contentsOf: bytes); try handle.synchronize()
        #if canImport(Darwin)
        guard fcntl(fd, F_FULLFSYNC) == 0 else { throw AnyDestinationMigrationError.journalUnavailable }
        #endif
        guard try Self.requireFile(fd, maximum: maximum) == bytes.count,
              renameat(directoryFD, temporary, directoryFD, name) == 0,
              fsync(directoryFD) == 0 else { throw AnyDestinationMigrationError.journalUnavailable }
        #if canImport(Darwin)
        guard fcntl(fd, F_FULLFSYNC) == 0 else { throw AnyDestinationMigrationError.journalUnavailable }
        #endif
    }

    private static func requireDirectory(_ url: URL, privateMode: Bool) throws {
        var info = stat()
        guard lstat(url.path, &info) == 0, (info.st_mode & mode_t(S_IFMT)) == mode_t(S_IFDIR),
              info.st_uid == geteuid(), info.st_mode & mode_t(0o022) == 0,
              !privateMode || info.st_mode & mode_t(0o777) == mode_t(0o700) else {
            throw AnyDestinationMigrationError.journalUnavailable
        }
    }

    private static func requireDirectoryIdentity(_ fd: Int32, path: URL) throws {
        try requireDirectory(path, privateMode: true)
        var descriptor = stat(), current = stat()
        guard fstat(fd, &descriptor) == 0, lstat(path.path, &current) == 0,
              descriptor.st_dev == current.st_dev, descriptor.st_ino == current.st_ino,
              descriptor.st_uid == geteuid(), descriptor.st_mode & mode_t(0o777) == mode_t(0o700),
              descriptor.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR) else {
            throw AnyDestinationMigrationError.journalUnavailable
        }
    }

    @discardableResult
    private static func requireFile(_ fd: Int32, maximum: Int) throws -> Int {
        var info = stat()
        guard fstat(fd, &info) == 0, (info.st_mode & mode_t(S_IFMT)) == mode_t(S_IFREG),
              info.st_uid == geteuid(), info.st_nlink == 1,
              info.st_mode & mode_t(0o777) == mode_t(0o600),
              info.st_size >= 0, info.st_size <= maximum else {
            throw AnyDestinationMigrationError.journalCorrupt
        }
        return Int(info.st_size)
    }
}
