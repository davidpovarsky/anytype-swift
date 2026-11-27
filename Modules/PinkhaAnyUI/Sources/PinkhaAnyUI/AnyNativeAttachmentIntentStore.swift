import Foundation
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

enum AnyNativeAttachmentRecoveryError: Error, Equatable, Sendable {
    case operationInProgress, invalidRecord, conflictingIntent, capacityExceeded, unavailable
}

struct AnyNativeAttachmentIntentClaim: Sendable {
    fileprivate let id: UUID
    fileprivate let objectID: String
}

/// Caller state only. The original Host creator remains the sole owner of
/// dispatch reservation and native receipt recording in its existing journal.
/// This file contains no selected URL, file bytes, native metadata or authority.
private struct AnyNativeAttachmentIntentRecord: Codable {
    let format: Int
    let intent: AnyNativeFileAttachmentIntent

    init(intent: AnyNativeFileAttachmentIntent) {
        format = 1
        self.intent = intent
    }
}

/// The existing account/Space recovery owner shares this one store between
/// replacement sheets. A filesystem claim also excludes a second store instance
/// until the actual previous task has drained; cancellation alone releases none.
actor AnyNativeAttachmentIntentStore {
    nonisolated let workspace: AnyTorahWorkspace
    private let parentOverride: URL?
    private var owned: (claim: AnyNativeAttachmentIntentClaim, files: AnyAttachmentIntentFiles)?

    init(workspace: AnyTorahWorkspace, parent: URL? = nil) {
        self.workspace = workspace
        parentOverride = parent
    }

    func claim(objectID: String) throws -> AnyNativeAttachmentIntentClaim {
        guard owned == nil else { throw AnyNativeAttachmentRecoveryError.operationInProgress }
        _ = try PinkhaAnyEngine.AnyNativeFileReference(accountID: workspace.accountID, spaceID: workspace.spaceID,
                                      objectID: objectID, fileID: "caller-intent-scope")
        let parent = try parentOverride ?? FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true)
        let scope = AnyContentDigest.sha256(try Self.encode(["any", workspace.accountID, workspace.spaceID]))
        let files = try AnyAttachmentIntentFiles(parent: parent, scope: scope)
        let claim = AnyNativeAttachmentIntentClaim(id: UUID(), objectID: objectID)
        owned = (claim, files)
        return claim
    }

    func release(_ claim: AnyNativeAttachmentIntentClaim) {
        guard owned?.claim.id == claim.id else { return }
        // The caller awaits every child and native operation before release.
        // Dropping the private descriptors releases only this caller-state lock.
        owned = nil
    }

    func pending(_ claim: AnyNativeAttachmentIntentClaim) throws -> AnyNativeFileAttachmentIntent? {
        let files = try requireClaim(claim)
        guard let bytes = try files.read(name: Self.name(claim.objectID)) else { return nil }
        let record = try JSONDecoder().decode(AnyNativeAttachmentIntentRecord.self, from: bytes)
        guard record.format == 1, try Self.encode(record) == bytes else {
            throw AnyNativeAttachmentRecoveryError.invalidRecord
        }
        try requireIntent(record.intent, claim: claim)
        return record.intent
    }

    /// A pending user action is never overwritten by another selection. The
    /// exclusive filesystem owner serializes the read/create across instances.
    func save(_ intent: AnyNativeFileAttachmentIntent, claim: AnyNativeAttachmentIntentClaim) throws {
        let files = try requireClaim(claim)
        try requireIntent(intent, claim: claim)
        if let existing = try pending(claim) {
            guard try Self.encode(existing) == Self.encode(intent) else {
                throw AnyNativeAttachmentRecoveryError.conflictingIntent
            }
            try files.confirmDurability(name: Self.name(claim.objectID))
            return
        }
        try files.create(name: Self.name(claim.objectID), bytes: Self.encode(AnyNativeAttachmentIntentRecord(intent: intent)))
    }

    /// The presentation invokes this only after verified Host/list reconciliation.
    /// A missing/replaced journal cannot certify non-dispatch. Neither a native
    /// error, no-record result, missing ACK nor a reserved entry is that proof.
    func remove(_ intent: AnyNativeFileAttachmentIntent, claim: AnyNativeAttachmentIntentClaim) throws {
        let files = try requireClaim(claim)
        try requireIntent(intent, claim: claim)
        guard let current = try pending(claim), try Self.encode(current) == Self.encode(intent) else {
            throw AnyNativeAttachmentRecoveryError.conflictingIntent
        }
        try files.remove(name: Self.name(claim.objectID), expected: Self.encode(AnyNativeAttachmentIntentRecord(intent: intent)))
    }

    private func requireClaim(_ claim: AnyNativeAttachmentIntentClaim) throws -> AnyAttachmentIntentFiles {
        guard let owned, owned.claim.id == claim.id,
              owned.claim.objectID.utf8.elementsEqual(claim.objectID.utf8) else {
            throw AnyNativeAttachmentRecoveryError.operationInProgress
        }
        return owned.files
    }

    private func requireIntent(_ intent: AnyNativeFileAttachmentIntent,
                               claim: AnyNativeAttachmentIntentClaim) throws {
        guard intent.workspace.accountID.utf8.elementsEqual(workspace.accountID.utf8),
              intent.workspace.spaceID.utf8.elementsEqual(workspace.spaceID.utf8),
              intent.objectID.utf8.elementsEqual(claim.objectID.utf8) else {
            throw AnyNativeAttachmentRecoveryError.invalidRecord
        }
    }

    private static func name(_ objectID: String) -> String {
        AnyContentDigest.sha256(Data(objectID.utf8)) + ".json"
    }

    private static func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(value)
    }
}

/// Bounded protected caller snapshots, under a namespace separate from the
/// creation journal. All operations run on the store actor, away from UIKit.
private final class AnyAttachmentIntentFiles: @unchecked Sendable {
    private static let maximumBytes = 32_768
    private static let maximumRecords = 128
    private let directory: URL
    private let directoryFD: Int32
    private let lockFD: Int32

    init(parent: URL, scope: String) throws {
        guard parent.isFileURL, parent.query == nil, parent.fragment == nil,
              parent.path.hasPrefix("/"), !parent.path.utf8.contains(0) else {
            throw AnyNativeAttachmentRecoveryError.unavailable
        }
        // Application Support can include a system alias (for example /var).
        // Only its resolved physical directory is used for the private children.
        let physical = parent.resolvingSymlinksInPath().standardizedFileURL
        var currentURL = physical
        var currentFD = open(physical.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard currentFD >= 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        var retained = false
        defer { if !retained { _ = close(currentFD) } }
        try Self.requireDirectory(currentFD, privateMode: false)
        for component in ["PinkhaAttachmentIntents", "any", scope] {
            let created = mkdirat(currentFD, component, mode_t(0o700)) == 0
            guard created || errno == EEXIST else { throw AnyNativeAttachmentRecoveryError.unavailable }
            let child = openat(currentFD, component, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard child >= 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
            do {
                try Self.requireDirectory(child, privateMode: true)
                let childURL = currentURL.appendingPathComponent(component, isDirectory: true)
                if created { try Self.protect(childURL) }
                try Self.requireProtection(childURL)
                try Self.requireNamedIdentity(childURL, descriptor: child, directory: true)
                guard fsync(child) == 0, fsync(currentFD) == 0 else {
                    throw AnyNativeAttachmentRecoveryError.unavailable
                }
                _ = close(currentFD)
                currentFD = child
                currentURL = childURL
            } catch { _ = close(child); throw error }
        }
        let lock = openat(currentFD, "owner.lock", O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK, mode_t(0o600))
        guard lock >= 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        do {
            try Self.requireFile(lock, allowEmpty: true)
            guard flock(lock, LOCK_EX | LOCK_NB) == 0 else {
                throw AnyNativeAttachmentRecoveryError.operationInProgress
            }
            try Self.protect(currentURL.appendingPathComponent("owner.lock"))
            try Self.requireNamedIdentity(currentURL.appendingPathComponent("owner.lock"), descriptor: lock, directory: false)
            guard fsync(lock) == 0, fsync(currentFD) == 0 else {
                throw AnyNativeAttachmentRecoveryError.unavailable
            }
        } catch { _ = close(lock); throw error }
        directory = currentURL
        directoryFD = currentFD
        lockFD = lock
        retained = true
    }

    deinit {
        _ = close(lockFD)
        _ = close(directoryFD)
    }

    func read(name: String) throws -> Data? {
        try requireOwner()
        let descriptor = openat(directoryFD, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        if descriptor < 0 {
            if errno == ENOENT { return nil }
            throw AnyNativeAttachmentRecoveryError.invalidRecord
        }
        defer { _ = close(descriptor) }
        let before = try Self.requireFile(descriptor)
        try Self.requireProtection(directory.appendingPathComponent(name))
        var bytes = Data(count: Self.maximumBytes + 1)
        var count = 0
        try bytes.withUnsafeMutableBytes { buffer in
            guard let address = buffer.baseAddress else { throw AnyNativeAttachmentRecoveryError.invalidRecord }
            while count < buffer.count {
                let size = Self.systemRead(descriptor, address.advanced(by: count), buffer.count - count)
                if size < 0 && errno == EINTR { continue }
                guard size >= 0 else { throw AnyNativeAttachmentRecoveryError.invalidRecord }
                if size == 0 { break }
                count += size
            }
        }
        guard count > 0, count <= Self.maximumBytes, count == before.st_size else {
            throw AnyNativeAttachmentRecoveryError.invalidRecord
        }
        let after = try Self.requireFile(descriptor)
        guard Self.sameFile(before, after), before.st_size == after.st_size else {
            throw AnyNativeAttachmentRecoveryError.invalidRecord
        }
        try Self.requireNamedIdentity(directory.appendingPathComponent(name), descriptor: descriptor, directory: false)
        bytes.count = count
        return bytes
    }

    func create(name: String, bytes: Data) throws {
        try requireOwner()
        guard !bytes.isEmpty, bytes.count <= Self.maximumBytes else {
            throw AnyNativeAttachmentRecoveryError.capacityExceeded
        }
        guard try read(name: name) == nil else { throw AnyNativeAttachmentRecoveryError.conflictingIntent }
        guard try recordCount() < Self.maximumRecords else { throw AnyNativeAttachmentRecoveryError.capacityExceeded }
        let temporary = ".pending-" + UUID().uuidString.lowercased() + ".tmp"
        let descriptor = openat(directoryFD, temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard descriptor >= 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        var temporaryRemoved = false
        defer {
            // Only this exclusively created inode belongs to this cleanup.
            if !temporaryRemoved, (try? Self.requireNamedIdentity(directory.appendingPathComponent(temporary),
                descriptor: descriptor, directory: false)) != nil { _ = unlinkat(directoryFD, temporary, 0) }
            _ = close(descriptor)
        }
        try Self.protect(directory.appendingPathComponent(temporary))
        try Self.requireNamedIdentity(directory.appendingPathComponent(temporary), descriptor: descriptor, directory: false)
        try Self.requireFile(descriptor, allowEmpty: true)
        try bytes.withUnsafeBytes { buffer in
            guard let address = buffer.baseAddress else { throw AnyNativeAttachmentRecoveryError.unavailable }
            var count = 0
            while count < buffer.count {
                let size = Self.systemWrite(descriptor, address.advanced(by: count), buffer.count - count)
                if size < 0 && errno == EINTR { continue }
                guard size > 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
                count += size
            }
        }
        try Self.synchronize(descriptor)
        try requireOwner()
        guard try read(name: name) == nil else { throw AnyNativeAttachmentRecoveryError.conflictingIntent }
        // linkat is an atomic create-if-absent even outside the cooperating
        // owner lock. It cannot replace a different pending request.
        guard linkat(directoryFD, temporary, directoryFD, name, 0) == 0 else {
            throw errno == EEXIST ? AnyNativeAttachmentRecoveryError.conflictingIntent : .unavailable
        }
        guard unlinkat(directoryFD, temporary, 0) == 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        temporaryRemoved = true
        guard fsync(directoryFD) == 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        try Self.synchronize(descriptor)
        guard try read(name: name) == bytes else { throw AnyNativeAttachmentRecoveryError.invalidRecord }
    }

    func remove(name: String, expected: Data) throws {
        try requireOwner()
        guard try read(name: name) == expected else { throw AnyNativeAttachmentRecoveryError.conflictingIntent }
        guard unlinkat(directoryFD, name, 0) == 0, fsync(directoryFD) == 0 else {
            throw AnyNativeAttachmentRecoveryError.unavailable
        }
    }

    func confirmDurability(name: String) throws {
        try requireOwner()
        let descriptor = openat(directoryFD, name, O_RDWR | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        guard descriptor >= 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        defer { _ = close(descriptor) }
        try Self.requireFile(descriptor)
        try Self.requireProtection(directory.appendingPathComponent(name))
        try Self.requireNamedIdentity(directory.appendingPathComponent(name), descriptor: descriptor, directory: false)
        try Self.synchronize(descriptor)
        guard fsync(directoryFD) == 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        try Self.synchronize(descriptor)
    }

    private func requireOwner() throws {
        try Self.requireDirectory(directoryFD, privateMode: true)
        try Self.requireNamedIdentity(directory, descriptor: directoryFD, directory: true)
        try Self.requireNamedIdentity(directory.appendingPathComponent("owner.lock"), descriptor: lockFD, directory: false)
    }

    private func recordCount() throws -> Int {
        let duplicate = dup(directoryFD)
        guard duplicate >= 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        guard let stream = fdopendir(duplicate) else {
            _ = close(duplicate)
            throw AnyNativeAttachmentRecoveryError.unavailable
        }
        defer { _ = closedir(stream) }
        rewinddir(stream)
        var count = 0
        while true {
            errno = 0
            guard let entry = readdir(stream) else {
                guard errno == 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
                break
            }
            let name = withUnsafePointer(to: entry.pointee.d_name) { pointer in
                pointer.withMemoryRebound(to: CChar.self, capacity: MemoryLayout.size(ofValue: entry.pointee.d_name)) {
                    String(cString: $0)
                }
            }
            if [".", "..", "owner.lock"].contains(name) { continue }
            // An incomplete caller snapshot is retained for diagnosis. It does
            // not grant permission to discard or replay its original request.
            guard name.utf8.count == 69, name.hasSuffix(".json"),
                  name.dropLast(5).utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
                throw AnyNativeAttachmentRecoveryError.invalidRecord
            }
            count += 1
            guard count <= Self.maximumRecords else { throw AnyNativeAttachmentRecoveryError.capacityExceeded }
        }
        return count
    }

    private static func requireDirectory(_ descriptor: Int32, privateMode: Bool) throws {
        var value = stat()
        guard fstat(descriptor, &value) == 0, value.st_uid == geteuid(),
              value.st_mode & S_IFMT == S_IFDIR,
              !privateMode || value.st_mode & 0o777 == 0o700 else {
            throw AnyNativeAttachmentRecoveryError.unavailable
        }
    }

    @discardableResult
    private static func requireFile(_ descriptor: Int32, allowEmpty: Bool = false) throws -> stat {
        var value = stat()
        guard fstat(descriptor, &value) == 0, value.st_uid == geteuid(), value.st_nlink == 1,
              value.st_mode & S_IFMT == S_IFREG, value.st_mode & 0o777 == 0o600,
              value.st_size >= (allowEmpty ? 0 : 1), value.st_size <= maximumBytes else {
            throw AnyNativeAttachmentRecoveryError.invalidRecord
        }
        return value
    }

    private static func requireNamedIdentity(_ url: URL, descriptor: Int32, directory: Bool) throws {
        var held = stat(), named = stat()
        guard fstat(descriptor, &held) == 0, lstat(url.path, &named) == 0,
              sameFile(held, named), named.st_mode & S_IFMT == (directory ? S_IFDIR : S_IFREG),
              url.standardizedFileURL == url.resolvingSymlinksInPath().standardizedFileURL else {
            throw AnyNativeAttachmentRecoveryError.unavailable
        }
    }

    private static func sameFile(_ left: stat, _ right: stat) -> Bool {
        #if canImport(Darwin)
        let modifiedLeft = left.st_mtimespec, modifiedRight = right.st_mtimespec
        let changedLeft = left.st_ctimespec, changedRight = right.st_ctimespec
        #else
        let modifiedLeft = left.st_mtim, modifiedRight = right.st_mtim
        let changedLeft = left.st_ctim, changedRight = right.st_ctim
        #endif
        return left.st_dev == right.st_dev && left.st_ino == right.st_ino && left.st_uid == right.st_uid &&
            left.st_gid == right.st_gid && left.st_mode == right.st_mode && left.st_nlink == right.st_nlink &&
            left.st_size == right.st_size && modifiedLeft.tv_sec == modifiedRight.tv_sec &&
            modifiedLeft.tv_nsec == modifiedRight.tv_nsec && changedLeft.tv_sec == changedRight.tv_sec &&
            changedLeft.tv_nsec == changedRight.tv_nsec
    }

    private static func protect(_ url: URL) throws {
        #if os(iOS) || os(tvOS) || os(watchOS) || os(visionOS)
        try FileManager.default.setAttributes([.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication], ofItemAtPath: url.path)
        #endif
        #if canImport(Darwin)
        var mutable = url
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try mutable.setResourceValues(values)
        #endif
        try requireProtection(url)
    }

    private static func requireProtection(_ url: URL) throws {
        #if os(iOS) || os(tvOS) || os(watchOS) || os(visionOS)
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        #if targetEnvironment(simulator)
        // The existing protected journal uses this Simulator-only distinction.
        // Physical-device data protection still requires its own actual proof.
        if attributes[.protectionKey] == nil { return }
        #endif
        let raw = (attributes[.protectionKey] as? FileProtectionType)?.rawValue ?? attributes[.protectionKey] as? String
        guard raw == FileProtectionType.completeUntilFirstUserAuthentication.rawValue else {
            throw AnyNativeAttachmentRecoveryError.unavailable
        }
        #endif
    }

    private static func synchronize(_ descriptor: Int32) throws {
        guard fsync(descriptor) == 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        #if canImport(Darwin)
        guard Darwin.fcntl(descriptor, F_FULLFSYNC) == 0 else { throw AnyNativeAttachmentRecoveryError.unavailable }
        #endif
    }

    private static func systemRead(_ descriptor: Int32, _ buffer: UnsafeMutableRawPointer, _ count: Int) -> Int {
        #if canImport(Darwin)
        Darwin.read(descriptor, buffer, count)
        #else
        Glibc.read(descriptor, buffer, count)
        #endif
    }

    private static func systemWrite(_ descriptor: Int32, _ buffer: UnsafeRawPointer, _ count: Int) -> Int {
        #if canImport(Darwin)
        Darwin.write(descriptor, buffer, count)
        #else
        Glibc.write(descriptor, buffer, count)
        #endif
    }
}
