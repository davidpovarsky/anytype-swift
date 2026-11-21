#if PINKHA_NATIVE_DERIVED && targetEnvironment(simulator)
import CryptoKit
import Darwin
import Foundation

/// Read-only acceptance observer. The original native store is checked before
/// AccountSelect can open it; only aggregate hashes and identities leave memory.
enum PinkhaTypePreservationLaunchProof {
    private enum Failure: Error { case invalidInput, changedStore, exceededBound }
    private static let support = "Library/Application Support"
    private static let store = support + "/Anytype/middleware-go"
    private static let baselineName = "pinkha-type-preservation-baseline.json"
    private static let fixtureName = "pinkha-native-derived-ui-fixture.json"
    private static let algorithm = "sha256-length-framed-utf8-v1"

    private struct Binding: Codable, Equatable {
        let sourceSHA, runID, runAttempt, nonce: String
    }
    private struct Directory: Codable, Equatable {
        let path, device, inode: String
        let createdAt: Double
    }
    private struct Inventory: Codable, Equatable {
        let algorithm, sha256: String
        let files, bytes, directories: Int
    }
    private struct Installation: Decodable {
        let schemaVersion: Int
        let status: String
        let binding: Binding
        let baselineSHA256, fixtureSHA256, simulatorUDID: String
        let accountID, spaceID, subjectID: String
        let preparationPID: Int32
        let currentDirectories: [String: Directory]
        let directoryBirthNanoseconds: [String: String]
        let nativeOpenInventory: Inventory
    }
    private struct Proof: Encodable {
        let schemaVersion = 1
        let status = "PASS_BEFORE_ACCOUNT_SELECT"
        let binding: Binding
        let installationSHA256, baselineSHA256, fixtureSHA256: String
        let accountID, spaceID, subjectID: String
        let processID: Int32
        let directories: [String: Directory]
        let directoryBirthNanoseconds: [String: String]
        let nativeOpenInventory: Inventory
    }

    static func captureBeforeAccountSelect(accountID: String) throws {
        let env = ProcessInfo.processInfo.environment
        guard env["PINKHA_TYPE_PRESERVATION_POSTFLIGHT"] == "1" else { return }
        let disabled = ["PINKHA_NATIVE_DERIVED_ACCEPTANCE", "PINKHA_PREPARE_TYPE_PRESERVATION",
            "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION", "PINKHA_SIMULATOR_UI_DISPOSABLE",
            "PINKHA_HANLIN_NATIVE_PREPARATION", "PINKHA_PREPARE_HANLIN_SELECTION_UI",
            "PINKHA_PROPERTIES_PREPARE", "PINKHA_T5_UI_PREPARATION", "PINKHA_T5_APPLE_PAIR"]
        try require(env["PINKHA_TYPE_PRESERVATION_MODE"] == "SIMULATOR_NORMAL_INSTALL_PREOPEN_PROOF" &&
                    disabled.allSatisfy { env[$0] == "0" })
        let input = env["PINKHA_TYPE_PRESERVATION_INSTALLATION_BASE64"] ?? ""
        try require(!input.isEmpty && input.utf8.count <= 87_384)
        guard let data = Data(base64Encoded: input), data.count <= 65_536 else { throw Failure.invalidInput }
        let checksum = digest(data)
        try require(checksum == env["PINKHA_TYPE_PRESERVATION_INSTALLATION_SHA256"])
        let installation = try JSONDecoder().decode(Installation.self, from: data)
        let binding = installation.binding
        try require(installation.schemaVersion == 2 && installation.status == "PASS_STOPPED_NATIVE_STORE_UNCHANGED" &&
                    binding.sourceSHA == env["PINKHA_TYPE_PRESERVATION_SOURCE_SHA"] &&
                    binding.runID == env["PINKHA_TYPE_PRESERVATION_RUN_ID"] &&
                    binding.runAttempt == env["PINKHA_TYPE_PRESERVATION_RUN_ATTEMPT"] &&
                    binding.nonce == env["PINKHA_TYPE_PRESERVATION_NONCE"] &&
                    binding.nonce.count == 32 && binding.nonce.allSatisfy(\.isHexDigit) &&
                    installation.baselineSHA256 == env["PINKHA_TYPE_PRESERVATION_BASELINE_SHA256"] &&
                    !accountID.isEmpty && accountID == installation.accountID &&
                    installation.preparationPID != ProcessInfo.processInfo.processIdentifier)
        let root = URL(fileURLWithPath: NSHomeDirectory()).standardizedFileURL.resolvingSymlinksInPath()
        try require(UUID(uuidString: installation.simulatorUDID) != nil &&
                    root.pathComponents.map { $0.lowercased() }.contains(installation.simulatorUDID.lowercased()))
        let nativeRoot = root.appendingPathComponent(store)
        let urls = ["container": root, "middleware": nativeRoot]
        var directories: [String: Directory] = [:], births: [String: String] = [:]
        try require(Set(installation.currentDirectories.keys) == Set(urls.keys) &&
                    Set(installation.directoryBirthNanoseconds.keys) == Set(urls.keys))
        for (name, url) in urls {
            let actual = try directory(url)
            guard let original = installation.currentDirectories[name] else { throw Failure.invalidInput }
            let info = try metadata(url)
            let born = String(Int64(info.st_birthtimespec.tv_sec) * 1_000_000_000 + Int64(info.st_birthtimespec.tv_nsec))
            try require(actual.device == original.device && actual.inode == original.inode &&
                        born == installation.directoryBirthNanoseconds[name])
            directories[name] = actual; births[name] = born
        }
        let receiptURL = root.appendingPathComponent(support)
            .appendingPathComponent("pinkha-type-preservation-preopen-" + binding.nonce + ".json")
        // A second account open cannot overwrite or reuse the first observation.
        try require(!FileManager.default.fileExists(atPath: receiptURL.path))
        let inventory = try inventory(nativeRoot, root: root, baselineSHA: installation.baselineSHA256,
                                      fixtureSHA: installation.fixtureSHA256)
        try require(inventory == installation.nativeOpenInventory)
        for (name, url) in urls { try require(try directory(url) == directories[name]) }
        let proof = Proof(binding: binding, installationSHA256: checksum,
            baselineSHA256: installation.baselineSHA256, fixtureSHA256: installation.fixtureSHA256,
            accountID: accountID, spaceID: installation.spaceID, subjectID: installation.subjectID,
            processID: ProcessInfo.processInfo.processIdentifier, directories: directories,
            directoryBirthNanoseconds: births, nativeOpenInventory: inventory)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let encoded = try encoder.encode(proof)
        try require(encoded.count <= 65_536)
        try encoded.write(to: receiptURL, options: .withoutOverwriting)
    }

    private static func require(_ value: Bool) throws {
        guard value else { throw Failure.changedStore }
    }
    private static func digest(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
    private static func metadata(_ url: URL) throws -> stat {
        try require(url.standardizedFileURL.resolvingSymlinksInPath().path == url.path)
        var result = stat()
        guard lstat(url.path, &result) == 0 else { throw Failure.changedStore }
        return result
    }
    private static func directory(_ url: URL) throws -> Directory {
        let info = try metadata(url)
        try require(info.st_mode & S_IFMT == S_IFDIR)
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        guard let born = attributes[.creationDate] as? Date else { throw Failure.changedStore }
        try require(born.timeIntervalSince1970.isFinite && born.timeIntervalSince1970 > 0)
        return .init(path: url.path, device: String(info.st_dev), inode: String(info.st_ino),
                     createdAt: born.timeIntervalSince1970)
    }
    private static func unchanged(_ first: stat, _ second: stat) -> Bool {
        first.st_dev == second.st_dev && first.st_ino == second.st_ino && first.st_size == second.st_size &&
        first.st_mode == second.st_mode && first.st_mtimespec.tv_sec == second.st_mtimespec.tv_sec &&
        first.st_mtimespec.tv_nsec == second.st_mtimespec.tv_nsec &&
        first.st_ctimespec.tv_sec == second.st_ctimespec.tv_sec && first.st_ctimespec.tv_nsec == second.st_ctimespec.tv_nsec
    }
    private static func inventory(_ nativeRoot: URL, root: URL, baselineSHA: String, fixtureSHA: String) throws -> Inventory {
        let clock = ContinuousClock(), deadline = ContinuousClock().now.advanced(by: .seconds(120))
        func budget() throws { guard clock.now < deadline else { throw Failure.exceededBound } }
        var traversalFailed = false
        guard let enumerator = FileManager.default.enumerator(at: nativeRoot, includingPropertiesForKeys: nil,
            errorHandler: { _, _ in traversalFailed = true; return false }) else { throw Failure.changedStore }
        var directories: [String] = [], files: [String: (Int, String)] = [:]
        for case let url as URL in enumerator {
            try budget()
            let info = try metadata(url)
            let relative = String(url.path.dropFirst(nativeRoot.path.count + 1))
            try require(!relative.isEmpty && url.path.hasPrefix(nativeRoot.path + "/"))
            if info.st_mode & S_IFMT == S_IFDIR { directories.append(relative) }
            else {
                try require(info.st_mode & S_IFMT == S_IFREG)
                let descriptor = open(url.path, O_RDONLY | O_NOFOLLOW)
                guard descriptor >= 0 else { throw Failure.changedStore }
                let handle = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true)
                defer { try? handle.close() }
                var before = stat(), after = stat(), hash = SHA256()
                try require(fstat(descriptor, &before) == 0 && unchanged(info, before))
                var readBytes = 0
                while let chunk = try handle.read(upToCount: 1_048_576), !chunk.isEmpty {
                    try budget(); hash.update(data: chunk); readBytes += chunk.count
                }
                try require(fstat(descriptor, &after) == 0 && unchanged(before, after) &&
                            unchanged(after, try metadata(url)) && Int64(readBytes) == before.st_size)
                files[relative] = (readBytes, hash.finalize().map { String(format: "%02x", $0) }.joined())
            }
            try require(files.count + directories.count <= 20_000)
        }
        try require(!traversalFailed && !files.isEmpty && files.values.reduce(0) { $0 + $1.0 } > 0)
        var hash = SHA256(); hash.update(data: Data("pinkha-native-store-inventory-v1\0".utf8))
        func fields(_ values: String...) {
            for value in values {
                let bytes = Data(value.utf8)
                var length = UInt64(bytes.count).bigEndian
                withUnsafeBytes(of: &length) { hash.update(data: Data($0)) }
                hash.update(data: bytes)
            }
        }
        func utf8Order(_ left: String, _ right: String) -> Bool { left.utf8.lexicographicallyPrecedes(right.utf8) }
        for name in directories.sorted(by: utf8Order) { fields("D", name) }
        for name in files.keys.sorted(by: utf8Order) {
            guard let file = files[name] else { throw Failure.changedStore }
            fields("F", name, String(file.0), file.1)
        }
        let identities = [baselineName: baselineSHA, fixtureName: fixtureSHA]
        for name in identities.keys.sorted(by: utf8Order) {
            try budget()
            let path = root.appendingPathComponent(support).appendingPathComponent(name)
            let info = try metadata(path)
            try require(info.st_mode & S_IFMT == S_IFREG && info.st_size > 0 && info.st_size <= 65_536)
            let data = try Data(contentsOf: path), checksum = digest(data)
            try require(unchanged(info, try metadata(path)) && checksum == identities[name])
            fields("I", name, checksum)
        }
        try budget()
        return .init(algorithm: algorithm, sha256: hash.finalize().map { String(format: "%02x", $0) }.joined(),
                     files: files.count, bytes: files.values.reduce(0) { $0 + $1.0 }, directories: directories.count)
    }
}
#endif
