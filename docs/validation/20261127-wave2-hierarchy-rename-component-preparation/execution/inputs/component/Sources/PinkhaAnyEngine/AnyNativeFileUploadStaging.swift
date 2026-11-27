import Foundation
import Crypto
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

/// One attachment exclusively owns these descriptors. No descriptor or source
/// path is exposed to callers. The lock only makes cleanup idempotent; copying
/// and validation are performed serially by the attachment operation.
final class AnyNativeFileUploadStaging: @unchecked Sendable {
    static let chunkByteCount = 1_048_576
    let fileURL: URL
    private let sourceURL: URL
    private let sourceFD: Int32
    private let fileFD: Int32
    private let directoryFD: Int32
    private let parentFD: Int32
    private let directoryName: String
    private let sourceStamp: Stamp
    private let directoryStamp: Stamp
    private var copyStamp: Stamp?
    private let lock = NSLock()
    private var finished = false

    private init(sourceURL: URL, sourceFD: Int32, sourceStamp: Stamp,
                 fileURL: URL, fileFD: Int32, directoryFD: Int32,
                 directoryStamp: Stamp, parentFD: Int32, directoryName: String) {
        self.sourceURL = sourceURL; self.sourceFD = sourceFD; self.sourceStamp = sourceStamp
        self.fileURL = fileURL; self.fileFD = fileFD; self.directoryFD = directoryFD
        self.directoryStamp = directoryStamp; self.parentFD = parentFD; self.directoryName = directoryName
    }

    deinit { finish() }

    private static func openSource(_ source: URL) throws -> (descriptor: Int32, stamp: Stamp) {
        guard source.isFileURL, source.user == nil, source.password == nil,
              source.query == nil, source.fragment == nil, source.path.hasPrefix("/"),
              !source.path.utf8.contains(0) else { throw AnyNativeFileUploadError.invalidSource }
        // O_NONBLOCK prevents a substituted FIFO from blocking before fstat.
        // Only the regular-file descriptor, never a later path read, supplies
        // the content that is hashed and uploaded.
        let sourceFD = open(source.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        guard sourceFD >= 0 else { throw AnyNativeFileUploadError.invalidSource }
        do {
            let sourceStamp = try stamp(sourceFD)
            guard sourceStamp.isRegular,
                  (0...AnyNativeFileUploadSpecification.maximumByteCount).contains(sourceStamp.size) else {
                throw AnyNativeFileUploadError.invalidSource
            }
            return (sourceFD, sourceStamp)
        } catch {
            _ = close(sourceFD)
            throw error
        }
    }

    static func fingerprint(source: URL) throws -> AnyNativeFileSourceFingerprint {
        let opened = try openSource(source)
        defer { _ = close(opened.descriptor) }
        let digest = try stream(opened.descriptor, size: opened.stamp.size, consume: { _ in })
        try requireSource(source, descriptor: opened.descriptor, original: opened.stamp)
        try Task.checkCancellation()
        return .init(byteCount: opened.stamp.size, sha256: digest)
    }

    static func copy(source: URL, specification: AnyNativeFileUploadSpecification) throws -> AnyNativeFileUploadStaging {
        let opened = try openSource(source)
        let sourceFD = opened.descriptor, sourceStamp = opened.stamp
        var transferred = false
        defer { if !transferred { _ = close(sourceFD) } }
        guard sourceStamp.size == specification.size else { throw AnyNativeFileUploadError.invalidSource }
        let parent = FileManager.default.temporaryDirectory
        let parentFD = open(parent.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard parentFD >= 0 else { throw AnyNativeFileUploadError.stagingUnavailable }
        defer { if !transferred { _ = close(parentFD) } }
        let directoryName = "pinkha-native-upload-" + UUID().uuidString.lowercased()
        guard mkdirat(parentFD, directoryName, mode_t(0o700)) == 0 else {
            throw AnyNativeFileUploadError.stagingUnavailable
        }
        var directoryFD: Int32 = -1
        var fileFD: Int32 = -1
        defer {
            if !transferred {
                if directoryFD >= 0 {
                    if fileFD >= 0 {
                        let named = openat(directoryFD, "content", O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
                        if named >= 0 {
                            if let original = try? stamp(fileFD), let current = try? stamp(named),
                               current.sameIdentity(as: original) { _ = unlinkat(directoryFD, "content", 0) }
                            _ = close(named)
                        }
                    }
                    let namedDirectory = openat(parentFD, directoryName, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                    if namedDirectory >= 0 {
                        if let original = try? stamp(directoryFD), let current = try? stamp(namedDirectory),
                           current.sameIdentity(as: original) { _ = unlinkat(parentFD, directoryName, AT_REMOVEDIR) }
                        _ = close(namedDirectory)
                    }
                    _ = close(directoryFD)
                }
                if fileFD >= 0 { _ = close(fileFD) }
            }
        }
        directoryFD = openat(parentFD, directoryName, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directoryFD >= 0, fchmod(directoryFD, mode_t(0o700)) == 0 else {
            throw AnyNativeFileUploadError.stagingUnavailable
        }
        let directoryStamp = try stamp(directoryFD)
        guard directoryStamp.isDirectory, directoryStamp.uid == UInt32(geteuid()),
              directoryStamp.mode & 0o777 == 0o700 else {
            throw AnyNativeFileUploadError.stagingUnavailable
        }
        fileFD = openat(directoryFD, "content", O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fileFD >= 0, fchmod(fileFD, mode_t(0o600)) == 0 else {
            throw AnyNativeFileUploadError.stagingUnavailable
        }
        let staged = AnyNativeFileUploadStaging(sourceURL: source, sourceFD: sourceFD,
            sourceStamp: sourceStamp,
            fileURL: parent.appendingPathComponent(directoryName, isDirectory: true).appendingPathComponent("content"),
            fileFD: fileFD, directoryFD: directoryFD, directoryStamp: directoryStamp,
            parentFD: parentFD, directoryName: directoryName)
        transferred = true
        do {
            try staged.configureAppleProtection()
            try staged.copyContent(specification)
            return staged
        } catch {
            staged.finish()
            throw error
        }
    }

    private func configureAppleProtection() throws {
        #if canImport(Darwin)
        // This temporary plaintext is distinct from native encrypted storage.
        // Set protection before the first content byte reaches the staging
        // file; a failure remains a pre-dispatch local error.
        let directoryURL = fileURL.deletingLastPathComponent()
        #if os(iOS) || os(tvOS) || os(watchOS) || os(visionOS)
        for url in [directoryURL, fileURL] {
            try FileManager.default.setAttributes([.protectionKey: FileProtectionType.complete], ofItemAtPath: url.path)
        }
        #endif
        for var url in [directoryURL, fileURL] {
            var values = URLResourceValues()
            values.isExcludedFromBackup = true
            try url.setResourceValues(values)
        }
        #endif
    }

    private func copyContent(_ specification: AnyNativeFileUploadSpecification) throws {
        let actual = try Self.stream(sourceFD, size: specification.size) { chunk in
            try chunk.withUnsafeBytes { buffer in
                guard let address = buffer.baseAddress else { throw AnyNativeFileUploadError.ioFailure }
                var written = 0
                while written < chunk.count {
                    try Task.checkCancellation()
                    let count = Self.systemWrite(fileFD, address.advanced(by: written), chunk.count - written)
                    if count < 0 && errno == EINTR { continue }
                    guard count > 0 else { throw AnyNativeFileUploadError.ioFailure }
                    written += count
                }
            }
        }
        try requireUnchangedSource()
        guard actual.utf8.elementsEqual(specification.contentSHA256.utf8) else {
            throw AnyNativeFileUploadError.contentMismatch
        }
        guard fsync(fileFD) == 0 else { throw AnyNativeFileUploadError.ioFailure }
        let value = try Self.stamp(fileFD)
        guard value.isRegular, value.size == specification.size,
              value.uid == UInt32(geteuid()), value.mode & 0o777 == 0o600,
              value.links == 1 else { throw AnyNativeFileUploadError.stagingChanged }
        copyStamp = value
        try requireUnchangedCopy()
        try Task.checkCancellation()
    }

    private static func stream(_ descriptor: Int32, size: Int64, consume: (Data) throws -> Void) throws -> String {
        var chunk = Data(count: chunkByteCount), digest = SHA256()
        var consumed: Int64 = 0
        while consumed < size {
            try Task.checkCancellation()
            let count = min(chunkByteCount, Int(size - consumed))
            let readCount = try chunk.withUnsafeMutableBytes { buffer -> Int in
                guard let address = buffer.baseAddress else { throw AnyNativeFileUploadError.ioFailure }
                return try readBytes(descriptor, address, count)
            }
            guard readCount > 0 else { throw AnyNativeFileUploadError.sourceChanged }
            let part = chunk.prefix(readCount)
            digest.update(data: part)
            try consume(part)
            consumed += Int64(readCount)
        }
        var extra: UInt8 = 0
        guard consumed == size, try readBytes(descriptor, &extra, 1) == 0 else {
            throw AnyNativeFileUploadError.sourceChanged
        }
        return digest.finalize().map { String(format: "%02x", $0) }.joined()
    }

    func requireUnchangedSourceAndCopy() throws {
        try requireUnchangedSource()
        try requireUnchangedCopy()
    }

    private func requireUnchangedSource() throws {
        try Self.requireSource(sourceURL, descriptor: sourceFD, original: sourceStamp)
    }

    private static func requireSource(_ source: URL, descriptor: Int32, original: Stamp) throws {
        guard try stamp(descriptor) == original else { throw AnyNativeFileUploadError.sourceChanged }
        let current = open(source.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        guard current >= 0 else { throw AnyNativeFileUploadError.sourceChanged }
        defer { _ = close(current) }
        guard try stamp(current) == original else { throw AnyNativeFileUploadError.sourceChanged }
    }

    func requireUnchangedCopy() throws {
        guard let copyStamp, try Self.stamp(fileFD) == copyStamp,
              try Self.stamp(directoryFD).sameIdentity(as: directoryStamp) else {
            throw AnyNativeFileUploadError.stagingChanged
        }
        let directory = openat(parentFD, directoryName, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directory >= 0 else { throw AnyNativeFileUploadError.stagingChanged }
        defer { _ = close(directory) }
        guard try Self.stamp(directory).sameIdentity(as: directoryStamp) else {
            throw AnyNativeFileUploadError.stagingChanged
        }
        let current = openat(directoryFD, "content", O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        guard current >= 0 else { throw AnyNativeFileUploadError.stagingChanged }
        defer { _ = close(current) }
        guard try Self.stamp(current) == copyStamp else { throw AnyNativeFileUploadError.stagingChanged }
    }

    func finish() {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        finished = true
        lock.unlock()
        // Descriptor-relative cleanup cannot follow a substituted directory.
        // A replaced path is never removed; only our exact original inode is.
        let original = try? Self.stamp(fileFD)
        let current = openat(directoryFD, "content", O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        if current >= 0 {
            if let original, let currentStamp = try? Self.stamp(current), currentStamp.sameIdentity(as: original) {
                _ = unlinkat(directoryFD, "content", 0)
            }
            _ = close(current)
        }
        let directory = openat(parentFD, directoryName, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        if directory >= 0 {
            if let currentStamp = try? Self.stamp(directory), currentStamp.sameIdentity(as: directoryStamp) {
                _ = unlinkat(parentFD, directoryName, AT_REMOVEDIR)
            }
            _ = close(directory)
        }
        _ = close(fileFD); _ = close(sourceFD); _ = close(directoryFD); _ = close(parentFD)
    }

    private struct Stamp: Equatable, Sendable {
        let device: UInt64
        let inode: UInt64
        let mode: UInt32
        let uid: UInt32
        let gid: UInt32
        let links: UInt64
        let size: Int64
        let modifiedSeconds: Int64
        let modifiedNanoseconds: Int64
        let changedSeconds: Int64
        let changedNanoseconds: Int64
        var isRegular: Bool { mode & UInt32(S_IFMT) == UInt32(S_IFREG) }
        var isDirectory: Bool { mode & UInt32(S_IFMT) == UInt32(S_IFDIR) }
        func sameIdentity(as other: Stamp) -> Bool {
            device == other.device && inode == other.inode && mode == other.mode && uid == other.uid && gid == other.gid
        }
    }

    private static func stamp(_ descriptor: Int32) throws -> Stamp {
        var value = stat()
        guard fstat(descriptor, &value) == 0 else { throw AnyNativeFileUploadError.ioFailure }
        #if canImport(Darwin)
        let modified = value.st_mtimespec, changed = value.st_ctimespec
        #else
        let modified = value.st_mtim, changed = value.st_ctim
        #endif
        return Stamp(device: UInt64(truncatingIfNeeded: value.st_dev), inode: UInt64(value.st_ino),
            mode: UInt32(value.st_mode), uid: UInt32(value.st_uid), gid: UInt32(value.st_gid),
            links: UInt64(value.st_nlink), size: Int64(value.st_size),
            modifiedSeconds: Int64(modified.tv_sec), modifiedNanoseconds: Int64(modified.tv_nsec),
            changedSeconds: Int64(changed.tv_sec), changedNanoseconds: Int64(changed.tv_nsec))
    }

    private static func readBytes(_ descriptor: Int32, _ buffer: UnsafeMutableRawPointer, _ count: Int) throws -> Int {
        while true {
            try Task.checkCancellation()
            #if canImport(Darwin)
            let value = Darwin.read(descriptor, buffer, count)
            #else
            let value = Glibc.read(descriptor, buffer, count)
            #endif
            if value < 0 && errno == EINTR { continue }
            guard value >= 0 else { throw AnyNativeFileUploadError.ioFailure }
            return value
        }
    }

    private static func systemWrite(_ descriptor: Int32, _ buffer: UnsafeRawPointer, _ count: Int) -> Int {
        #if canImport(Darwin)
        return Darwin.write(descriptor, buffer, count)
        #else
        return Glibc.write(descriptor, buffer, count)
        #endif
    }
}
