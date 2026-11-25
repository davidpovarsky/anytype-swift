import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

public enum AnyHeartNativeCaptureError: Error, Equatable, Sendable {
    case invalidDescriptor, sourceBinding, privateDirectory, privateMember(String), changedMember(String)
}

/// A byte-bound receipt from the real loaded-account native capture bridge.
/// This is captured source evidence, not a current session or migration permit.
/// The caller must supply the expected identities from its current account.
public struct AnyHeartNativeCaptureDescriptor: Sendable {
    public static let contract = "pinkha-native-source-capture-v1"

    public let requestID: String
    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let privateBundleDirectory: String
    public let manifestSHA256: String
    public let sourceRowsSHA256: String
    public let nativeTrees: Int
    public let capturedObjects: Int
    public let capturedFiles: Int
    public let currentFilePayloadCompleteness: Bool
    public let originalDescriptor: Data

    public var permitsDestinationWrites: Bool { false }

    public init(data: Data, expectedAccountID: String, expectedSpaceID: String,
                expectedRequestID: String) throws {
        guard !data.isEmpty, data.count <= 32 * 1024 else {
            throw AnyHeartNativeCaptureError.invalidDescriptor
        }
        let value = try JSONDecoder().decode(AnyJSON.self, from: data)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: data, encoded: encoder.encode(value))
        let fields: Set<String> = ["contract", "requestID", "sourceAccountID", "sourceSpaceID",
            "privateBundleDirectory", "manifestSHA256", "sourceRowsSHA256", "nativeTrees",
            "capturedObjects", "capturedFiles", "accountSessionAuthorizedAtCapture",
            "capturedSnapshotsBoundToCheckpoint", "currentFilePayloadCompleteness",
            "originalNativeHistoryRowsRetained", "permitsDestinationWrites"]
        guard let object = value.object, Set(object.keys) == fields,
              value["contract"]?.string == Self.contract,
              let request = value["requestID"]?.string, Self.validRequest(request),
              Self.exact(request, expectedRequestID),
              let account = value["sourceAccountID"]?.string, Self.validID(account),
              Self.exact(account, expectedAccountID),
              let space = value["sourceSpaceID"]?.string, Self.validID(space),
              Self.exact(space, expectedSpaceID),
              let directory = value["privateBundleDirectory"]?.string, Self.validID(directory),
              directory.hasPrefix("/"),
              let manifest = value["manifestSHA256"]?.string, Self.validSHA(manifest),
              let rows = value["sourceRowsSHA256"]?.string, Self.validSHA(rows),
              let trees = value["nativeTrees"]?.integer, (0...100_000).contains(trees),
              let objects = value["capturedObjects"]?.integer, (0...10_000).contains(objects),
              objects <= trees,
              let files = value["capturedFiles"]?.integer, (0...256).contains(files),
              value["accountSessionAuthorizedAtCapture"]?.bool == true,
              value["capturedSnapshotsBoundToCheckpoint"]?.bool == true,
              value["originalNativeHistoryRowsRetained"]?.bool == true,
              value["permitsDestinationWrites"]?.bool == false,
              let completeFiles = value["currentFilePayloadCompleteness"]?.bool else {
            throw AnyHeartNativeCaptureError.invalidDescriptor
        }
        requestID = request; sourceAccountID = account; sourceSpaceID = space
        privateBundleDirectory = directory; manifestSHA256 = manifest; sourceRowsSHA256 = rows
        nativeTrees = Int(trees); capturedObjects = Int(objects); capturedFiles = Int(files)
        currentFilePayloadCompleteness = completeFiles; originalDescriptor = data
    }

    /// Read only the newly captured child of an explicitly supplied app-private
    /// parent. The directory descriptor pins every member read to that child;
    /// symlinks, changed bytes and writable/exported source files are refused.
    /// Run this bounded, potentially large read off the main actor.
    public func loadBundle(under privateParent: URL) throws -> AnyHeartNativeSpaceBundle {
        try Task.checkCancellation()
        let reader = try AnyNativePrivateBundleReader(parent: privateParent, child: privateBundleDirectory)
        let manifest = try reader.read("manifest.json", expectedBytes: nil, maximum: 16 * 1024 * 1024)
        guard !manifest.isEmpty, AnyContentDigest.sha256(manifest) == manifestSHA256 else {
            throw AnyHeartNativeCaptureError.changedMember("manifest.json")
        }
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: sourceAccountID, sourceSpaceID: sourceSpaceID) { member in
            try Task.checkCancellation()
            return try reader.read(member.path, expectedBytes: member.byteCount, maximum: member.byteCount)
        }
        guard bundle.manifestSHA256 == manifestSHA256, bundle.sourceRows.sha256 == sourceRowsSHA256,
              bundle.trees.count == nativeTrees, bundle.objects.count == capturedObjects,
              bundle.receipt["CapturedFiles"]?.integer == Int64(capturedFiles),
              bundle.receipt["CurrentFilePayloadCompleteness"]?.bool == currentFilePayloadCompleteness,
              bundle.receipt["OriginalNativeHistoryRowsRetained"]?.bool == true,
              bundle.receipt["PermitsDestinationWrites"]?.bool == false else {
            throw AnyHeartNativeCaptureError.sourceBinding
        }
        return bundle
    }

    private static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 && !value.contains("\0")
    }
    private static func validRequest(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 128 && value.utf8.allSatisfy {
            (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || $0 == 45 || $0 == 95
        }
    }
    private static func validSHA(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static func exact(_ first: String, _ second: String) -> Bool {
        Data(first.utf8) == Data(second.utf8)
    }
}

private final class AnyNativePrivateBundleReader {
    private let directory: Int32

    init(parent: URL, child: String) throws {
        guard parent.isFileURL, !child.contains("\0") else { throw AnyHeartNativeCaptureError.privateDirectory }
        let parentPath = parent.path
        let childURL = URL(fileURLWithPath: child, isDirectory: true)
        guard Self.canonical(parentPath), Self.canonical(child),
              Self.exact(childURL.deletingLastPathComponent().path, parentPath),
              childURL.lastPathComponent.hasPrefix("native-source-"),
              childURL.lastPathComponent.utf8.count > "native-source-".utf8.count else {
            throw AnyHeartNativeCaptureError.privateDirectory
        }
        let parentFD = open(parentPath, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard parentFD >= 0 else { throw AnyHeartNativeCaptureError.privateDirectory }
        defer { _ = close(parentFD) }
        do { try Self.checkDirectory(parentFD) } catch { throw AnyHeartNativeCaptureError.privateDirectory }
        let childFD = openat(parentFD, childURL.lastPathComponent, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard childFD >= 0 else { throw AnyHeartNativeCaptureError.privateDirectory }
        do { try Self.checkDirectory(childFD) } catch {
            _ = close(childFD); throw AnyHeartNativeCaptureError.privateDirectory
        }
        directory = childFD
    }

    deinit { _ = close(directory) }

    func read(_ path: String, expectedBytes: Int?, maximum: Int) throws -> Data {
        let parts = path.split(separator: "/", omittingEmptySubsequences: false)
        guard !parts.isEmpty, !path.contains("\0"), !path.contains("\\"),
              parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }), maximum >= 0 else {
            throw AnyHeartNativeCaptureError.privateMember(path)
        }
        var current = directory, ownedDirectories: [Int32] = []
        defer { for fd in ownedDirectories.reversed() { _ = close(fd) } }
        for part in parts.dropLast() {
            let fd = openat(current, String(part), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw AnyHeartNativeCaptureError.privateMember(path) }
            ownedDirectories.append(fd)
            do { try Self.checkDirectory(fd) } catch { throw AnyHeartNativeCaptureError.privateMember(path) }
            current = fd
        }
        let fd = openat(current, String(parts.last!), O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        guard fd >= 0 else { throw AnyHeartNativeCaptureError.privateMember(path) }
        let file = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? file.close() }
        var before = stat()
        guard fstat(fd, &before) == 0, (before.st_mode & mode_t(S_IFMT)) == mode_t(S_IFREG),
              (before.st_mode & 0o7777) == 0o400, before.st_uid == geteuid(),
              before.st_size >= 0, before.st_size <= Int64(maximum),
              expectedBytes == nil || before.st_size == Int64(expectedBytes!) else {
            throw AnyHeartNativeCaptureError.privateMember(path)
        }
        var bytes = Data()
        while bytes.count <= maximum {
            try Task.checkCancellation()
            let remaining = maximum - bytes.count
            let count = min(64 * 1024, remaining + 1)
            guard let part = try file.read(upToCount: count), !part.isEmpty else { break }
            bytes.append(part)
            guard bytes.count <= maximum else { throw AnyHeartNativeCaptureError.changedMember(path) }
        }
        var after = stat()
        guard fstat(fd, &after) == 0, Self.sameFileState(before, after),
              bytes.count == Int(before.st_size) else {
            throw AnyHeartNativeCaptureError.changedMember(path)
        }
        return bytes
    }

    private static func checkDirectory(_ fd: Int32) throws {
        var info = stat()
        guard fstat(fd, &info) == 0, (info.st_mode & mode_t(S_IFMT)) == mode_t(S_IFDIR),
              (info.st_mode & 0o7777) == 0o700, info.st_uid == geteuid() else {
            throw AnyHeartNativeCaptureError.privateDirectory
        }
    }
    private static func canonical(_ path: String) -> Bool {
        let url = URL(fileURLWithPath: path, isDirectory: true)
        return path.hasPrefix("/") && exact(url.standardizedFileURL.path, path)
            && exact(url.resolvingSymlinksInPath().standardizedFileURL.path, path)
    }
    private static func exact(_ first: String, _ second: String) -> Bool { Data(first.utf8) == Data(second.utf8) }
    private static func sameFileState(_ first: stat, _ second: stat) -> Bool {
        guard first.st_dev == second.st_dev, first.st_ino == second.st_ino,
              first.st_size == second.st_size, first.st_mode == second.st_mode,
              first.st_uid == second.st_uid, first.st_gid == second.st_gid else { return false }
        #if canImport(Darwin)
        return first.st_mtimespec.tv_sec == second.st_mtimespec.tv_sec
            && first.st_mtimespec.tv_nsec == second.st_mtimespec.tv_nsec
            && first.st_ctimespec.tv_sec == second.st_ctimespec.tv_sec
            && first.st_ctimespec.tv_nsec == second.st_ctimespec.tv_nsec
        #else
        return first.st_mtim.tv_sec == second.st_mtim.tv_sec && first.st_mtim.tv_nsec == second.st_mtim.tv_nsec
            && first.st_ctim.tv_sec == second.st_ctim.tv_sec && first.st_ctim.tv_nsec == second.st_ctim.tv_nsec
        #endif
    }
}
