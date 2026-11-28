import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

/// Private output for the existing native file-intent client. A prior file is
/// reused only after complete byte/identity verification; partials and failures
/// are retained. No captured input, journal or unrelated entry is removed.
enum AnyHeartMigrationPrivatePayload {
    static func requireParent(_ url: URL, excludingCapture capture: String) throws {
        let fd = try openParent(url, excludingCapture: capture)
        defer { _ = close(fd) }
        try requireParentIdentity(fd, url: url)
    }

    static func materialize(_ archive: AnyHeartNativePreservationArchive, under parent: URL,
                            excludingCapture capture: String) throws -> URL {
        try Task.checkCancellation()
        guard archive.bytes.count >= 4096, archive.bytes.count <= AnyHeartNativePreservationArchive.maximumBytes,
              AnyContentDigest.sha256(archive.bytes) == archive.sha256 else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        let parentFD = try openParent(parent, excludingCapture: capture)
        defer { _ = close(parentFD) }
        let name = "captured-source-" + archive.sha256 + ".pinkha-heart-source"
        let url = parent.appendingPathComponent(name, isDirectory: false)
        let output = openat(parentFD, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        if output >= 0 {
            let handle = FileHandle(fileDescriptor: output, closeOnDealloc: true)
            defer { try? handle.close() }
            var initial = stat()
            guard fstat(output, &initial) == 0, regular(initial, mode: 0o600), initial.st_size == 0 else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            try requireNamed(output, parentFD: parentFD, name: name)
            // A failed or cancelled write leaves its owned partial file in place.
            // No automatic retry may replace it or promote it to a valid archive.
            try Task.checkCancellation()
            try handle.write(contentsOf: archive.bytes)
            guard fsync(output) == 0, fchmod(output, mode_t(0o400)) == 0, fsync(output) == 0 else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            var final = stat()
            guard fstat(output, &final) == 0, regular(final, mode: 0o400),
                  final.st_dev == initial.st_dev, final.st_ino == initial.st_ino,
                  final.st_size == Int64(archive.bytes.count) else {
                throw AnyHeartNativeMigrationProducerError.privateStorage
            }
            try requireNamed(output, parentFD: parentFD, name: name)
            try requireParentIdentity(parentFD, url: parent)
            guard fsync(parentFD) == 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
            try handle.close()
        } else {
            guard errno == EEXIST else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        }
        // Fresh and previously completed files receive the same full independent
        // readback. The underlying native file client rechecks the intent hash.
        try verify(parentFD: parentFD, name: name, expected: archive.bytes, expectedSHA256: archive.sha256)
        try requireParentIdentity(parentFD, url: parent)
        try Task.checkCancellation()
        return url
    }

    private static func openParent(_ url: URL, excludingCapture capture: String) throws -> Int32 {
        guard url.isFileURL, url.path.hasPrefix("/"), !url.path.contains("\0"),
              Data(url.standardizedFileURL.path.utf8) == Data(url.path.utf8),
              Data(url.resolvingSymlinksInPath().standardizedFileURL.path.utf8) == Data(url.path.utf8),
              !capture.isEmpty, !capture.contains("\0"),
              Data(url.path.utf8) != Data(capture.utf8),
              !url.path.hasPrefix(capture.hasSuffix("/") ? capture : capture + "/") else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        let fd = open(url.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        do { try requireParentIdentity(fd, url: url) }
        catch { _ = close(fd); throw error }
        return fd
    }

    private static func requireParentIdentity(_ fd: Int32, url: URL) throws {
        var actual = stat(), named = stat()
        guard fstat(fd, &actual) == 0, lstat(url.path, &named) == 0,
              actual.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              actual.st_mode & mode_t(0o7777) == mode_t(0o700), actual.st_uid == geteuid(),
              actual.st_dev == named.st_dev, actual.st_ino == named.st_ino,
              actual.st_mode == named.st_mode, actual.st_uid == named.st_uid, actual.st_gid == named.st_gid else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
    }

    private static func requireNamed(_ fd: Int32, parentFD: Int32, name: String) throws {
        var actual = stat(), named = stat()
        guard fstat(fd, &actual) == 0,
              fstatat(parentFD, name, &named, AT_SYMLINK_NOFOLLOW) == 0, same(actual, named) else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
    }

    private static func verify(parentFD: Int32, name: String, expected: Data, expectedSHA256: String) throws {
        let fd = openat(parentFD, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        guard fd >= 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat(), after = stat()
        guard fstat(fd, &before) == 0, regular(before, mode: 0o400), before.st_size == Int64(expected.count) else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        try requireNamed(fd, parentFD: parentFD, name: name)
        var bytes = Data()
        while bytes.count <= expected.count {
            try Task.checkCancellation()
            let value = try handle.read(upToCount: min(1_048_576, expected.count + 1 - bytes.count)) ?? Data()
            if value.isEmpty { break }
            bytes.append(value)
        }
        guard bytes == expected, AnyContentDigest.sha256(bytes) == expectedSHA256,
              fstat(fd, &after) == 0, same(before, after) else {
            throw AnyHeartNativeMigrationProducerError.privateStorage
        }
        try requireNamed(fd, parentFD: parentFD, name: name)
        try handle.close()
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
