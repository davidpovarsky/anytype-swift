import Foundation
import Darwin
import Security
import SecureService

/// Only this app's original Anytype repository and this additive journal are
/// owned. A foreign/partial account is retained and never reset or adopted.
internal actor OriginalEditorLocalAnnotationJournal {
    struct Account: Codable, Sendable {
        let schema: String
        let owner: UUID
        let bundleID: String
        let appGroup: String
        let repository: String
        var phase: String
        var accountID: String?
        var preferredSpaceID: String?
    }

    /// Historical creation facts only. The runtime never reopens a batch from
    /// this file; a new explicit run obtains a new original private Space.
    struct Batch: Codable, Sendable {
        let schema: String
        let owner: UUID
        let attempt: UUID
        let process: Int32
        let profile: String
        let batchID: UUID
        var phase: String
        var spaceID: String?
        var spaceViewID: String?
    }

    struct Draft: Codable, Sendable {
        let schema: String
        let owner: UUID
        let attempt: UUID
        let process: Int32
        let profile: String
        let annotationUUID: UUID
        let revision: Int64
        let sourceSHA256: String
        let payloadSHA256: String?
        let canonicalSHA256: String
        var phase: String
        var spaceID: String?
        var spaceViewID: String?
        var objectID: String?
        var captureSHA256: String?
        var captureArchiveSHA256: String?
        var batchAttempt: UUID?
    }

    private let root: URL
    private let accountURL: URL
    private let drafts: URL
    private let keychain = KeychainStore()
    private var account: Account
    private var accountBytes: Data
    private var draftBytes: [UUID: Data] = [:]
    private var batchBytes: [UUID: Data] = [:]

    private init(root: URL, account: Account, bytes: Data) {
        self.root = root
        accountURL = root.appendingPathComponent("OriginalEditorLocalAnnotationOwner.json")
        drafts = root.appendingPathComponent("OriginalEditorLocalAnnotationDrafts", isDirectory: true)
        self.account = account
        accountBytes = bytes
    }

    static func open(appGroup: String) throws -> OriginalEditorLocalAnnotationJournal {
        guard let bundle = Bundle.main.bundleIdentifier,
              bundle == "com.davidpovarsky.chavrusatext",
              appGroup == "group.com.davidpovarsky.chavrusatext" else {
            throw AnytypeOriginalEditorLocalAnnotationError.incompatibleDeployment
        }
        let support = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true)
            .resolvingSymlinksInPath().standardizedFileURL
        let root = support.appendingPathComponent("Anytype", isDirectory: true)
        let path = root.appendingPathComponent("OriginalEditorLocalAnnotationOwner.json")
        let repo = root.appendingPathComponent("middleware-go", isDirectory: true)
        var info = stat()
        if Darwin.lstat(root.path, &info) == 0 {
            try requireDirectory(root)
            let bytes = try read(path, maximum: 65_536)
            let value = try JSONDecoder().decode(Account.self, from: bytes)
            guard value.schema == "otzaria.original-local-annotation-account/1",
                  value.bundleID == bundle, value.appGroup == appGroup,
                  value.repository == repo.path,
                  ["claimed", "wallet_may_have_dispatched", "wallet_stored",
                   "account_may_have_dispatched", "account_observed", "ready"].contains(value.phase) else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
            try requireDirectory(root.appendingPathComponent("OriginalEditorLocalAnnotationDrafts"))
            if ["account_observed", "ready"].contains(value.phase) {
                guard let account = value.accountID, !account.isEmpty,
                      !account.utf8.contains(0), account.utf8.count <= 16_384,
                      value.preferredSpaceID.map({ !$0.isEmpty && !$0.utf8.contains(0)
                          && $0.utf8.count <= 16_384 }) ?? true else {
                    throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
                }
                try requireDirectory(repo)
            }
            return .init(root: root, account: value, bytes: bytes)
        }
        guard errno == ENOENT, Darwin.mkdir(root.path, 0o700) == 0 else {
            throw AnytypeOriginalEditorLocalAnnotationError.foreignRepository
        }
        let draftDirectory = root.appendingPathComponent("OriginalEditorLocalAnnotationDrafts")
        guard Darwin.mkdir(draftDirectory.path, 0o700) == 0 else {
            throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno)
        }
        let value = Account(schema: "otzaria.original-local-annotation-account/1", owner: UUID(),
            bundleID: bundle, appGroup: appGroup, repository: repo.path, phase: "claimed")
        let bytes = try encode(value)
        try write(bytes, path: path, replacing: nil)
        return .init(root: root, account: value, bytes: bytes)
    }

    func accountObservation() throws -> Account {
        guard try Self.read(accountURL, maximum: 65_536) == accountBytes else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }
        return account
    }

    func requireRepository(_ original: URL) throws {
        let expected = root.appendingPathComponent("middleware-go", isDirectory: true)
        // Resolve the system-owned Application Support prefix (e.g. /var's
        // Apple alias). The owned repository itself must remain a real directory.
        guard original.resolvingSymlinksInPath().standardizedFileURL.path == expected.path else {
            throw AnytypeOriginalEditorLocalAnnotationError.foreignRepository
        }
        if ["account_observed", "ready"].contains(account.phase) { try Self.requireDirectory(expected) }
    }

    func prepareWallet() throws -> Account {
        _ = try accountObservation()
        guard account.phase == "claimed", account.accountID == nil,
              !keychain.contains(queryable: query()) else {
            throw AnytypeOriginalEditorLocalAnnotationError.uncertainNativeOperation
        }
        var info = stat()
        guard Darwin.lstat(account.repository, &info) != 0, errno == ENOENT else {
            throw AnytypeOriginalEditorLocalAnnotationError.foreignRepository
        }
        try updateAccount(phase: "wallet_may_have_dispatched")
        return account
    }

    func retainCredential(_ mnemonic: String) throws {
        _ = try accountObservation()
        guard account.phase == "wallet_may_have_dispatched", !mnemonic.isEmpty,
              mnemonic.utf8.count <= 4_096 else {
            throw AnytypeOriginalEditorLocalAnnotationError.missingCredential
        }
        // Exclusive add: never replace another keychain item. No credential is
        // serialized into the journal, a callback, a diagnostic or a public API.
        var attributes = query().query
        attributes[String(kSecValueData)] = Data(mnemonic.utf8)
        guard SecItemAdd(attributes as CFDictionary, nil) == errSecSuccess else {
            throw AnytypeOriginalEditorLocalAnnotationError.missingCredential
        }
        guard try keychain.retreiveItem(queryable: query()).utf8.elementsEqual(mnemonic.utf8) else {
            throw AnytypeOriginalEditorLocalAnnotationError.missingCredential
        }
        try updateAccount(phase: "wallet_stored")
    }

    func prepareAccount() throws {
        _ = try accountObservation()
        guard account.phase == "wallet_stored" else {
            throw AnytypeOriginalEditorLocalAnnotationError.uncertainNativeOperation
        }
        _ = try credential()
        try updateAccount(phase: "account_may_have_dispatched")
    }

    /// Retain a genuine successful AccountCreate before any subsequent await
    /// checks current UI ownership. This observation is recovery data only.
    func observeCreatedAccount(accountID: String, preferredSpaceID: String) throws {
        _ = try accountObservation()
        guard account.phase == "account_may_have_dispatched",
              !accountID.isEmpty, accountID.utf8.count <= 16_384,
              preferredSpaceID.utf8.count <= 16_384,
              !accountID.utf8.contains(0), !preferredSpaceID.utf8.contains(0) else {
            throw AnytypeOriginalEditorLocalAnnotationError.unavailableAccount
        }
        var next = account
        next.phase = "account_observed"
        next.accountID = accountID
        next.preferredSpaceID = preferredSpaceID.isEmpty ? nil : preferredSpaceID
        try replaceAccount(next)
    }

    func markAccountReady(accountID: String) throws {
        _ = try accountObservation()
        guard ["account_observed", "ready"].contains(account.phase),
              account.accountID == accountID else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }
        if account.phase != "ready" { try updateAccount(phase: "ready") }
    }

    func credential() throws -> String {
        _ = try accountObservation()
        guard ["wallet_stored", "account_may_have_dispatched", "account_observed", "ready"].contains(account.phase) else {
            throw AnytypeOriginalEditorLocalAnnotationError.missingCredential
        }
        let value = try keychain.retreiveItem(queryable: query())
        guard !value.isEmpty, value.utf8.count <= 4_096 else {
            throw AnytypeOriginalEditorLocalAnnotationError.missingCredential
        }
        // Retained for actual future recovery. Reading does not consume it.
        return value
    }

    func beginBatch(source: AnytypeOriginalEditorLocalAnnotationBatchSource) throws -> Batch {
        _ = try accountObservation()
        guard account.phase == "ready" else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }
        let directory = root.appendingPathComponent("OriginalEditorLocalAnnotationBatches", isDirectory: true)
        var info = stat()
        if Darwin.lstat(directory.path, &info) != 0 {
            guard errno == ENOENT, Darwin.mkdir(directory.path, 0o700) == 0 else {
                throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno)
            }
        }
        try Self.requireDirectory(directory)
        let value = Batch(schema: "otzaria.original-local-annotation-batch/1", owner: account.owner,
            attempt: UUID(), process: ProcessInfo.processInfo.processIdentifier,
            profile: source.hostProfileID, batchID: source.batchID, phase: "prepared")
        let bytes = try Self.encode(value)
        try Self.write(bytes, path: batchURL(value.attempt), replacing: nil)
        batchBytes[value.attempt] = bytes
        return value
    }

    func transitionBatch(_ previous: Batch, to phase: String,
                         spaceID: String? = nil, spaceViewID: String? = nil) throws -> Batch {
        let allowed: [String: Set<String>] = [
            "prepared": ["space_may_have_dispatched"],
            "space_may_have_dispatched": ["space_observed"],
            "space_observed": ["ready"]
        ]
        try requireBatch(previous)
        guard allowed[previous.phase]?.contains(phase) == true else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }
        var value = previous
        value.phase = phase
        if let spaceID { value.spaceID = spaceID }
        if let spaceViewID { value.spaceViewID = spaceViewID }
        if ["space_observed", "ready"].contains(phase) {
            guard let space = value.spaceID, !space.isEmpty, space.utf8.count <= 16_384,
                  !space.utf8.contains(0), let view = value.spaceViewID,
                  !view.isEmpty, view.utf8.count <= 16_384, !view.utf8.contains(0) else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
        }
        let bytes = try Self.encode(value)
        try Self.write(bytes, path: batchURL(value.attempt), replacing: batchBytes[previous.attempt])
        batchBytes[value.attempt] = bytes
        return value
    }

    private func requireBatch(_ value: Batch) throws {
        _ = try accountObservation()
        guard account.phase == "ready", value.owner == account.owner,
              value.process == ProcessInfo.processInfo.processIdentifier,
              let bytes = batchBytes[value.attempt],
              try Self.encode(value) == bytes,
              try Self.read(batchURL(value.attempt), maximum: 32_768) == bytes else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }
    }

    func beginDraft(source: AnytypeOriginalEditorLocalAnnotationSource, canonicalSHA256: String,
                    batch: Batch? = nil) throws -> Draft {
        _ = try accountObservation()
        guard account.phase == "ready", OriginalEditorLocalAnnotationValidation.digest(canonicalSHA256) else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }
        if let batch {
            try requireBatch(batch)
            guard batch.phase == "ready", batch.profile.utf8.elementsEqual(source.hostProfileID.utf8) else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
        }
        let value = Draft(schema: "otzaria.original-local-annotation-draft/1", owner: account.owner,
            attempt: UUID(), process: ProcessInfo.processInfo.processIdentifier,
            profile: source.hostProfileID, annotationUUID: source.annotationUUID,
            revision: source.expectedRevision, sourceSHA256: source.sourceWitnessSHA256,
            payloadSHA256: source.payloadSHA256, canonicalSHA256: canonicalSHA256,
            phase: "prepared", batchAttempt: batch?.attempt)
        let bytes = try Self.encode(value)
        try Self.write(bytes, path: draftURL(value.attempt), replacing: nil)
        draftBytes[value.attempt] = bytes
        return value
    }

    func transition(_ previous: Draft, to phase: String, spaceID: String? = nil,
                    spaceViewID: String? = nil, objectID: String? = nil,
                    captureSHA256: String? = nil, archiveSHA256: String? = nil) throws -> Draft {
        let allowed: [String: Set<String>] = [
            "prepared": ["space_may_have_dispatched", "batch_space_observed"],
            "space_may_have_dispatched": ["space_observed"],
            "space_observed": ["materialization_may_have_dispatched"],
            "batch_space_observed": ["materialization_may_have_dispatched"],
            "materialization_may_have_dispatched": ["object_observed"],
            "object_observed": ["opened"],
            "opened": ["capture_started"],
            "capture_started": ["captured"]
        ]
        guard previous.owner == account.owner, let old = draftBytes[previous.attempt],
              try Self.encode(previous) == old,
              try Self.read(draftURL(previous.attempt), maximum: 32_768) == old,
              allowed[previous.phase]?.contains(phase) == true else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }
        if phase == "batch_space_observed" {
            guard let attempt = previous.batchAttempt, let bytes = batchBytes[attempt] else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
            let batch = try JSONDecoder().decode(Batch.self, from: bytes)
            try requireBatch(batch)
            guard batch.phase == "ready", batch.profile.utf8.elementsEqual(previous.profile.utf8),
                  spaceID == batch.spaceID, spaceViewID == batch.spaceViewID else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
        } else if phase == "space_may_have_dispatched" {
            guard previous.batchAttempt == nil else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
        }
        var value = previous
        value.phase = phase
        if let spaceID { value.spaceID = spaceID }
        if let spaceViewID { value.spaceViewID = spaceViewID }
        if let objectID { value.objectID = objectID }
        if let captureSHA256 { value.captureSHA256 = captureSHA256 }
        if let archiveSHA256 { value.captureArchiveSHA256 = archiveSHA256 }
        let bytes = try Self.encode(value)
        try Self.write(bytes, path: draftURL(value.attempt), replacing: old)
        draftBytes[value.attempt] = bytes
        return value
    }

    private func query() -> GenericPasswordQueryable {
        .init(account: account.owner.uuidString,
              service: "org.otzaria.original-local-annotation.wallet.v1",
              attrAccessible: .afterFirstUnlockThisDeviceOnly)
    }

    private func draftURL(_ id: UUID) -> URL { drafts.appendingPathComponent(id.uuidString + ".json") }
    private func batchURL(_ id: UUID) -> URL {
        root.appendingPathComponent("OriginalEditorLocalAnnotationBatches", isDirectory: true)
            .appendingPathComponent(id.uuidString + ".json")
    }
    private func updateAccount(phase: String) throws {
        var value = account
        value.phase = phase
        try replaceAccount(value)
    }
    private func replaceAccount(_ value: Account) throws {
        let bytes = try Self.encode(value)
        try Self.write(bytes, path: accountURL, replacing: accountBytes)
        account = value
        accountBytes = bytes
    }

    private static func encode<Value: Encodable>(_ value: Value) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(value)
    }

    private static func requireDirectory(_ path: URL) throws {
        var info = stat()
        guard Darwin.lstat(path.path, &info) == 0,
              info.st_mode & S_IFMT == S_IFDIR, info.st_uid == getuid(),
              path.resolvingSymlinksInPath().path == path.path else {
            throw AnytypeOriginalEditorLocalAnnotationError.foreignRepository
        }
    }

    private static func read(_ path: URL, maximum: Int) throws -> Data {
        let fd = Darwin.open(path.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal }
        defer { Darwin.close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_mode & S_IFMT == S_IFREG,
              info.st_uid == getuid(), info.st_size > 0, info.st_size <= maximum else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: false)
        let bytes = try handle.readToEnd() ?? Data()
        guard bytes.count == info.st_size else { throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal }
        return bytes
    }

    private static func write(_ bytes: Data, path: URL, replacing previous: Data?) throws {
        try requireDirectory(path.deletingLastPathComponent())
        if let previous {
            guard try read(path, maximum: 65_536) == previous else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
        } else {
            var info = stat()
            guard lstat(path.path, &info) != 0, errno == ENOENT else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
        }
        let temp = path.deletingLastPathComponent().appendingPathComponent(".local-annotation-" + UUID().uuidString)
        let fd = Darwin.open(temp.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno) }
        var renamed = false
        defer { Darwin.close(fd); if !renamed { Darwin.unlink(temp.path) } }
        try bytes.withUnsafeBytes { raw in
            var sent = 0
            while sent < raw.count {
                let count = Darwin.write(fd, raw.baseAddress!.advanced(by: sent), raw.count - sent)
                guard count > 0 else { throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno) }
                sent += count
            }
        }
        guard fsync(fd) == 0 else { throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno) }
        if let previous {
            guard try read(path, maximum: 65_536) == previous else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
            }
        }
        if previous == nil {
            guard Darwin.link(temp.path, path.path) == 0 else {
                throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno)
            }
            guard Darwin.unlink(temp.path) == 0 else {
                throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno)
            }
        } else {
            guard Darwin.rename(temp.path, path.path) == 0 else {
                throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno)
            }
        }
        renamed = true
        let directory = Darwin.open(path.deletingLastPathComponent().path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directory >= 0 else { throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno) }
        defer { Darwin.close(directory) }
        guard fsync(directory) == 0, try read(path, maximum: 65_536) == bytes else {
            throw AnytypeOriginalEditorLocalAnnotationError.storageFailure(errno)
        }
    }
}
