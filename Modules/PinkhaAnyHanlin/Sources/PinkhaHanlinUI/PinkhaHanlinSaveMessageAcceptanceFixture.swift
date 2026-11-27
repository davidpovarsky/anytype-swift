#if DEBUG && targetEnvironment(simulator) && canImport(UIKit)
import Foundation
import Darwin
import HanlinHostContracts
import PinkhaHanlinCore

/// A fresh custody envelope supplied by the native acceptance controller after
/// inspecting the actual retained account. This file does not create an account,
/// discover credentials, grant tool permission, or prove a native route exists.
public struct PinkhaHanlinSaveMessageAcceptanceFixture: Codable, Sendable {
    public enum Engine: String, Codable, Sendable { case heart, any }
    public struct AnyRuntime: Codable, Sendable {
        public let generation: UUID
        public let engineStartedAt: String
    }

    public let version: Int
    public let fixtureID: UUID
    public let createdAt: Date
    public let sourceSHA: String
    public let runID: String
    public let runAttempt: String
    public let engine: Engine
    public let accountID: String
    public let spaceID: String
    public let sourceObjectID: String
    public let sourceRevisionSHA256: String
    public let custodyReceiptSHA256: String
    public let nativeManifestSHA256: String
    public let nativeBinarySHA256: String
    public let preparationReceiptSHA256: String
    public let processID: Int32
    public let anyRuntime: AnyRuntime?

    public static var isRequested: Bool {
        ProcessInfo.processInfo.environment["PINKHA_HANLIN_SAVE_NATIVE_UI"] == "1"
    }

    public var markdown: String {
        "# Hanlin " + fixtureID.uuidString + "\n\nשלום **bold** and *italic* with `code`.\n\n- first\n- second"
    }
    public func prompt(_ ordinal: Int) -> String {
        "Prepare Hanlin save " + (ordinal == 0 ? "cancel " : "allow ") + fixtureID.uuidString
    }
    public var hostApp: String {
        engine == .any ? PinkhaHanlinEngineNamespace.any : PinkhaHanlinEngineNamespace.heart
    }

    public static func loadIfRequested(engine: Engine) throws -> Self? {
        guard isRequested else { return nil }
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1",
              let rawID = environment["PINKHA_HANLIN_SAVE_FIXTURE_ID"],
              let id = UUID(uuidString: rawID), rawID == id.uuidString else {
            throw HanlinHostError.invalidContext
        }
        let root = try supportDirectory()
        let url = root.appendingPathComponent("pinkha-hanlin-save-fixture-" + id.uuidString + ".json")
        let bytes = try readRegularFile(url, maximumBytes: 16_384)
        let fixture = try JSONDecoder().decode(Self.self, from: bytes)
        try fixture.validate(environment: environment)
        guard fixture.engine == engine, fixture.fixtureID == id,
              !FileManager.default.fileExists(atPath: fixture.resultDirectory(in: root).path) else {
            throw HanlinHostError.invalidContext
        }
        return fixture
    }

    public func validate(environment: [String: String] = ProcessInfo.processInfo.environment) throws {
        let age = Date().timeIntervalSince(createdAt)
        guard version == 1, age >= 0, age < 3_600,
              Bundle.main.object(forInfoDictionaryKey: "CompilationCondition") as? String == "DEBUG",
              environment["PINKHA_HANLIN_SAVE_NATIVE_UI"] == "1",
              environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1",
              environment["PINKHA_HANLIN_NATIVE_UI"] != "1", environment["PINKHA_HANLIN_SELECTION_UI"] != "1",
              environment["PINKHA_HANLIN_SAVE_FIXTURE_ID"] == fixtureID.uuidString,
              environment["PINKHA_HANLIN_SAVE_SOURCE_SHA"] == sourceSHA,
              environment["PINKHA_HANLIN_SAVE_RUN_ID"] == runID,
              environment["PINKHA_HANLIN_SAVE_RUN_ATTEMPT"] == runAttempt,
              environment["PINKHA_HANLIN_SAVE_CUSTODY_SHA256"] == custodyReceiptSHA256,
              environment["PINKHA_HANLIN_SAVE_NATIVE_MANIFEST_SHA256"] == nativeManifestSHA256,
              environment["PINKHA_HANLIN_SAVE_NATIVE_BINARY_SHA256"] == nativeBinarySHA256,
              Self.hex(sourceSHA, count: 40),
              processID == ProcessInfo.processInfo.processIdentifier,
              [sourceRevisionSHA256, custodyReceiptSHA256, nativeManifestSHA256, nativeBinarySHA256, preparationReceiptSHA256]
                .allSatisfy({ Self.hex($0, count: 64) }),
              UInt64(runID).map({ $0 > 0 }) == true, runID.utf8.count <= 20,
              UInt64(runAttempt).map({ $0 > 0 }) == true, runAttempt.utf8.count <= 20,
              [accountID, spaceID, sourceObjectID].allSatisfy(Self.validReference) else {
            throw HanlinHostError.invalidContext
        }
        switch engine {
        case .any:
            guard let anyRuntime, !anyRuntime.engineStartedAt.isEmpty,
                  anyRuntime.engineStartedAt.utf8.count <= 256,
                  anyRuntime.engineStartedAt.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }) else {
                throw HanlinHostError.invalidContext
            }
        case .heart:
            guard anyRuntime == nil else { throw HanlinHostError.invalidContext }
        }
        try PinkhaHanlinSaveMessageAcceptancePreparation.validateReceipt(for: self)
    }

    public func validate(session: HanlinHostSession) throws {
        try validate()
        let context = session.context, namespace = context.namespace
        guard namespace.app.utf8.elementsEqual(hostApp.utf8),
              namespace.account.utf8.elementsEqual(accountID.utf8),
              namespace.space.utf8.elementsEqual(spaceID.utf8),
              namespace.workspace.utf8.elementsEqual(spaceID.utf8),
              context.objectReference?.utf8.elementsEqual(sourceObjectID.utf8) == true,
              context.selectionReferences.isEmpty,
              let revision = context.sourceRevision,
              PinkhaHanlinCreatePagePlan.digest(Data(revision.utf8)) == sourceRevisionSHA256 else {
            throw HanlinHostError.staleContext
        }
    }

    /// One new directory is the fixture's single-use claim. No old result or
    /// private account file is overwritten or removed by this diagnostic.
    func claimResultDirectory() throws -> URL {
        try validate()
        let directory = resultDirectory(in: try Self.supportDirectory())
        guard Darwin.mkdir(directory.path, mode_t(0o700)) == 0 else { throw HanlinHostError.invalidContext }
        return directory
    }

    private func resultDirectory(in root: URL) -> URL {
        root.appendingPathComponent("pinkha-hanlin-save-result-" + fixtureID.uuidString, isDirectory: true)
    }

    static func supportDirectory() throws -> URL {
        let url = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: false)
        let values = try url.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
        guard values.isDirectory == true, values.isSymbolicLink != true else { throw HanlinHostError.invalidContext }
        return url
    }

    static func readRegularFile(_ url: URL, maximumBytes: Int) throws -> Data {
        let fd = Darwin.open(url.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw HanlinHostError.invalidContext }
        defer { Darwin.close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
              info.st_size > 0, info.st_size <= off_t(maximumBytes) else { throw HanlinHostError.invalidContext }
        var data = Data(count: Int(info.st_size))
        let count = data.withUnsafeMutableBytes { buffer in Darwin.read(fd, buffer.baseAddress, buffer.count) }
        var extra: UInt8 = 0
        guard count == data.count, Darwin.read(fd, &extra, 1) == 0 else { throw HanlinHostError.invalidContext }
        return data
    }

    static func hex(_ value: String, count: Int) -> Bool {
        value.utf8.count == count && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    static func validReference(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 256 &&
            value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
}
#endif
