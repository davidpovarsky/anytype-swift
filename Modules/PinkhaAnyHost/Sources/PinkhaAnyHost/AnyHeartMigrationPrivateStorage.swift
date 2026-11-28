import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

/// Retains this operation's capture and output directory descriptors together.
/// The private App namespace owner must serialize moves, mounts and removal of
/// these directories until producer invalidation has drained. Identity checks
/// detect replacement; they are not an atomic namespace lock against an
/// independent administrator. Existing journal internals remain unchanged.
final class AnyHeartMigrationPrivateStorage: @unchecked Sendable {
    private let captureParent: URL
    private let captureURL: URL
    private let journalParent: URL
    private let payloadParent: URL
    private let captureParentFD: Int32
    private let captureFD: Int32
    private let journalFD: Int32
    private let payloadFD: Int32
    private let capturedDirectories: Set<String>
    private let journalScope: String
    private let admittedJournalDirectories: [(URL, Int32)]

    init(captureParent: URL, captureDirectory: String, journalParent: URL, payloadParent: URL,
         planBinding: AnyPreparedMigrationPlanBinding) throws {
        let captureURL = URL(fileURLWithPath: captureDirectory, isDirectory: true)
        guard Self.canonical(captureParent), Self.canonical(captureURL),
              Data(captureURL.deletingLastPathComponent().path.utf8) == Data(captureParent.path.utf8),
              captureURL.lastPathComponent.hasPrefix("native-source-"),
              captureURL.lastPathComponent.utf8.count > "native-source-".utf8.count,
              Self.canonical(journalParent), Self.canonical(payloadParent) else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        var opened: [Int32] = []
        defer { for fd in opened.reversed() { _ = close(fd) } }
        let sourceParent = try Self.openPrivate(captureParent); opened.append(sourceParent)
        let source = openat(sourceParent, captureURL.lastPathComponent, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard source >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        opened.append(source)
        try Self.directoryIdentity(source, url: captureURL)
        let journal = try Self.openPrivate(journalParent); opened.append(journal)
        let payload = try Self.openPrivate(payloadParent); opened.append(payload)
        let directories = try Self.captureDirectoryIdentities(source)
        try Self.excludeCapture(journal, identities: directories)
        try Self.excludeCapture(payload, identities: directories)
        // EXACT unchanged Journal scope derivation. Existing root/scope
        // directories can themselves be mount aliases even when parent is not.
        let scope = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            planBinding.workspace.accountID, planBinding.workspace.spaceID,
            planBinding.storeID, planBinding.planID
        ]))
        let journalChildren = try Self.openJournalDirectories(journal, parent: journalParent,
            scope: scope, captured: directories)
        opened.append(contentsOf: journalChildren.map { $0.1 })
        try Self.directoryIdentity(sourceParent, url: captureParent)
        try Self.directoryIdentity(source, url: captureURL)
        try Self.directoryIdentity(journal, url: journalParent)
        try Self.directoryIdentity(payload, url: payloadParent)
        self.captureParent = captureParent; self.captureURL = captureURL
        self.journalParent = journalParent; self.payloadParent = payloadParent
        captureParentFD = sourceParent; captureFD = source; journalFD = journal; payloadFD = payload
        capturedDirectories = directories
        journalScope = scope; admittedJournalDirectories = journalChildren
        opened.removeAll() // ownership transfers only after complete admission
    }

    deinit {
        for (_, fd) in admittedJournalDirectories.reversed() { _ = close(fd) }
        _ = close(payloadFD); _ = close(journalFD); _ = close(captureFD); _ = close(captureParentFD)
    }

    func validate() throws {
        try Task.checkCancellation()
        try Self.directoryIdentity(captureParentFD, url: captureParent)
        try Self.directoryIdentity(captureFD, url: captureURL)
        try Self.directoryIdentity(journalFD, url: journalParent)
        try Self.directoryIdentity(payloadFD, url: payloadParent)
        try Self.excludeCapture(journalFD, identities: capturedDirectories)
        try Self.excludeCapture(payloadFD, identities: capturedDirectories)
        for (url, fd) in admittedJournalDirectories {
            try Self.directoryIdentity(fd, url: url)
        }
        // Previously absent children remain prospective only under the stated
        // stable namespace owner. Reopen/admit them once the Journal creates
        // them; never infer their identity from the parent alone.
        let current = try Self.openJournalDirectories(journalFD, parent: journalParent,
            scope: journalScope, captured: capturedDirectories)
        defer { for (_, fd) in current.reversed() { _ = close(fd) } }
    }

    /// Private output for the original native file-intent client. Exact existing
    /// bytes may be reused only after fresh identity AND durability barriers.
    /// Partials, failures and original capture inputs are never removed.
    func materialize(_ archive: AnyHeartNativePreservationArchive) throws -> URL {
        try validate()
        guard archive.bytes.count >= 4096, archive.bytes.count <= AnyHeartNativePreservationArchive.maximumBytes,
              AnyContentDigest.sha256(archive.bytes) == archive.sha256 else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        let name = "captured-source-" + archive.sha256 + ".pinkha-heart-source"
        let url = payloadParent.appendingPathComponent(name, isDirectory: false)
        let output = openat(payloadFD, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        if output >= 0 {
            let handle = FileHandle(fileDescriptor: output, closeOnDealloc: true)
            defer { try? handle.close() }
            var initial = stat()
            guard fstat(output, &initial) == 0, Self.regular(initial, mode: 0o600), initial.st_size == 0 else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            try Self.requireNamed(output, parentFD: payloadFD, name: name)
            try validate()
            try handle.write(contentsOf: archive.bytes)
            guard fsync(output) == 0, fchmod(output, mode_t(0o400)) == 0, fsync(output) == 0 else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            var final = stat()
            guard fstat(output, &final) == 0, Self.regular(final, mode: 0o400),
                  final.st_dev == initial.st_dev, final.st_ino == initial.st_ino,
                  final.st_size == Int64(archive.bytes.count) else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            try Self.requireNamed(output, parentFD: payloadFD, name: name)
            try validate()
            guard fsync(payloadFD) == 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
            try handle.close()
        } else {
            guard errno == EEXIST else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        }
        // Both branches perform full readback plus checked fsync on that same
        // verified file FD and the retained output parent. A prior fsync failure
        // cannot be converted into successful reuse merely by matching bytes.
        try verifyAndSynchronize(name: name, expected: archive.bytes, expectedSHA256: archive.sha256)
        try validate()
        return url
    }

    private func verifyAndSynchronize(name: String, expected: Data, expectedSHA256: String) throws {
        let fd = openat(payloadFD, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        guard fd >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat(), after = stat()
        guard fstat(fd, &before) == 0, Self.regular(before, mode: 0o400),
              before.st_size == Int64(expected.count) else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        try Self.requireNamed(fd, parentFD: payloadFD, name: name)
        var bytes = Data()
        while bytes.count <= expected.count {
            try Task.checkCancellation()
            let value = try handle.read(upToCount: min(1_048_576, expected.count + 1 - bytes.count)) ?? Data()
            if value.isEmpty { break }
            bytes.append(value)
        }
        guard bytes == expected, AnyContentDigest.sha256(bytes) == expectedSHA256,
              fstat(fd, &after) == 0, Self.same(before, after) else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        try Self.requireNamed(fd, parentFD: payloadFD, name: name)
        try validate()
        guard fsync(fd) == 0, fsync(payloadFD) == 0 else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        guard fstat(fd, &after) == 0, Self.same(before, after) else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        try Self.requireNamed(fd, parentFD: payloadFD, name: name)
        try validate()
        try handle.close()
    }

    private static func canonical(_ url: URL) -> Bool {
        url.isFileURL && url.path.hasPrefix("/") && !url.path.contains("\0") &&
            Data(url.standardizedFileURL.path.utf8) == Data(url.path.utf8) &&
            Data(url.resolvingSymlinksInPath().standardizedFileURL.path.utf8) == Data(url.path.utf8)
    }

    private static func openPrivate(_ url: URL) throws -> Int32 {
        let fd = open(url.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        do { try directoryIdentity(fd, url: url) } catch { _ = close(fd); throw error }
        return fd
    }

    private static func directoryIdentity(_ fd: Int32, url: URL) throws {
        var actual = stat(), named = stat()
        guard fstat(fd, &actual) == 0, lstat(url.path, &named) == 0,
              actual.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              actual.st_mode & mode_t(0o7777) == mode_t(0o700), actual.st_uid == geteuid(),
              actual.st_dev == named.st_dev, actual.st_ino == named.st_ino,
              actual.st_mode == named.st_mode, actual.st_uid == named.st_uid, actual.st_gid == named.st_gid else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
    }

    private static func identity(_ value: stat) -> String { "\(value.st_dev):\(value.st_ino)" }

    /// Metadata only, through pinned directory descriptors: no file content,
    /// symlink traversal or account/database scan. The finite capture namespace
    /// includes unlisted subdirectories so a static mount alias into one cannot
    /// masquerade as an unrelated output parent.
    private static func captureDirectoryIdentities(_ root: Int32) throws -> Set<String> {
        var identities = Set<String>(), entries = 0
        func visit(_ fd: Int32, depth: Int) throws {
            try Task.checkCancellation()
            var before = stat()
            guard depth <= 32, fstat(fd, &before) == 0,
                  before.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
                  before.st_mode & mode_t(0o7777) == mode_t(0o700), before.st_uid == geteuid(),
                  identities.count < 10_000, identities.insert(identity(before)).inserted else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            let copied = fcntl(fd, F_DUPFD_CLOEXEC, 0)
            guard copied >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
            guard let stream = fdopendir(copied) else {
                _ = close(copied); throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            defer { _ = closedir(stream) }
            while true {
                try Task.checkCancellation()
                errno = 0
                guard let entry = readdir(stream) else {
                    guard errno == 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
                    break
                }
                var rawName = entry.pointee.d_name
                let name = withUnsafeBytes(of: &rawName) { raw -> String? in
                    let bytes = raw.bindMemory(to: CChar.self)
                    guard let first = bytes.baseAddress else { return nil }
                    return String(validatingCString: first)
                }
                guard let name, !name.isEmpty, !name.contains("/") else {
                    throw AnyHeartNativeMigrationProducerError.privateStorage
                }
                if name == "." || name == ".." { continue }
                entries += 1
                guard entries <= 100_000 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
                var row = stat()
                guard fstatat(fd, name, &row, AT_SYMLINK_NOFOLLOW) == 0 else {
                    throw AnyHeartNativeMigrationProducerError.privateStorage
                }
                if row.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR) {
                    let child = openat(fd, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                    guard child >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
                    defer { _ = close(child) }
                    var opened = stat(), final = stat()
                    guard fstat(child, &opened) == 0, same(row, opened) else {
                        throw AnyHeartNativeMigrationProducerError.privateStorage
                    }
                    try visit(child, depth: depth + 1)
                    guard fstatat(fd, name, &final, AT_SYMLINK_NOFOLLOW) == 0, same(row, final) else {
                        throw AnyHeartNativeMigrationProducerError.privateStorage
                    }
                } else if row.st_mode & mode_t(S_IFMT) != mode_t(S_IFREG) {
                    throw AnyHeartNativeMigrationProducerError.privateStorage
                }
            }
            var after = stat()
            guard fstat(fd, &after) == 0, same(before, after) else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
        }
        try visit(root, depth: 0)
        return identities
    }

    /// Compare the output parent and every real parent inode, not path text.
    /// Opening ".." follows the kernel's namespace; captured descendant inode
    /// census additionally rejects a mount alias rooted inside the capture.
    private static func excludeCapture(_ start: Int32, identities: Set<String>) throws {
        var fd = fcntl(start, F_DUPFD_CLOEXEC, 0)
        guard fd >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        defer { _ = close(fd) }
        for _ in 0..<256 {
            try Task.checkCancellation()
            var here = stat()
            guard fstat(fd, &here) == 0, !identities.contains(identity(here)) else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            let parent = openat(fd, "..", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard parent >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
            var above = stat()
            guard fstat(parent, &above) == 0 else {
                _ = close(parent); throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            if identity(here) == identity(above) { _ = close(parent); return }
            _ = close(fd); fd = parent
        }
        throw AnyHeartNativeMigrationProducerError.privateStorage
    }

    /// Opens only the two exact directories that the unchanged Journal will
    /// use. No file is opened or created. An absent descendant is prospective;
    /// any other failure, non-directory, alias or captured inode is refused.
    private static func openJournalDirectories(_ parentFD: Int32, parent: URL,
                                               scope: String, captured: Set<String>) throws -> [(URL, Int32)] {
        var result: [(URL, Int32)] = [], transfer = false
        defer { if !transfer { for (_, fd) in result.reversed() { _ = close(fd) } } }
        var anchor = parentFD, url = parent
        for name in ["AnyDestinationMigrationV1", scope] {
            url = url.appendingPathComponent(name, isDirectory: true)
            let fd = openat(anchor, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            if fd < 0 {
                guard errno == ENOENT else { throw AnyHeartNativeMigrationProducerError.privateStorage }
                break
            }
            result.append((url, fd))
            try directoryIdentity(fd, url: url)
            try excludeCapture(fd, identities: captured)
            anchor = fd
        }
        transfer = true
        return result
    }

    private static func requireNamed(_ fd: Int32, parentFD: Int32, name: String) throws {
        var actual = stat(), named = stat()
        guard fstat(fd, &actual) == 0,
              fstatat(parentFD, name, &named, AT_SYMLINK_NOFOLLOW) == 0, same(actual, named) else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
    }
    private static func regular(_ value: stat, mode: mode_t) -> Bool {
        value.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG) &&
            value.st_mode & mode_t(0o7777) == mode && value.st_uid == geteuid() && value.st_nlink == 1
    }
    private static func same(_ a: stat, _ b: stat) -> Bool {
        guard a.st_dev == b.st_dev, a.st_ino == b.st_ino, a.st_mode == b.st_mode,
              a.st_uid == b.st_uid, a.st_gid == b.st_gid, a.st_nlink == b.st_nlink,
              a.st_size == b.st_size else { return false }
        #if canImport(Darwin)
        return a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
            a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
        #else
        return a.st_mtim.tv_sec == b.st_mtim.tv_sec && a.st_mtim.tv_nsec == b.st_mtim.tv_nsec &&
            a.st_ctim.tv_sec == b.st_ctim.tv_sec && a.st_ctim.tv_nsec == b.st_ctim.tv_nsec
        #endif
    }
}
