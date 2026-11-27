#if DEBUG && targetEnvironment(simulator) && canImport(UIKit)
import Foundation
import HanlinHostContracts
import PinkhaHanlinCore

/// The controller supplies retained-account custody, not a guessed new runtime
/// UUID. The mounted original editor supplies the process-owned native facts in
/// a separate read-only preparation, before a save-capable host may be chosen.
public enum PinkhaHanlinSaveMessageAcceptancePreparation {
    public struct Request: Codable, Sendable {
        public let version: Int
        public let fixtureID: UUID
        public let createdAt: Date
        public let sourceSHA: String
        public let runID: String
        public let runAttempt: String
        public let engine: PinkhaHanlinSaveMessageAcceptanceFixture.Engine
        public let accountID: String
        public let spaceID: String
        public let sourceObjectID: String
        public let custodyReceiptSHA256: String
        public let nativeManifestSHA256: String
        public let nativeBinarySHA256: String

        public func validate() throws {
            let environment = ProcessInfo.processInfo.environment
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
                  PinkhaHanlinSaveMessageAcceptanceFixture.hex(sourceSHA, count: 40),
                  [custodyReceiptSHA256, nativeManifestSHA256, nativeBinarySHA256]
                    .allSatisfy({ PinkhaHanlinSaveMessageAcceptanceFixture.hex($0, count: 64) }),
                  UInt64(runID).map({ $0 > 0 }) == true, runID.utf8.count <= 20,
                  UInt64(runAttempt).map({ $0 > 0 }) == true, runAttempt.utf8.count <= 20,
                  [accountID, spaceID, sourceObjectID].allSatisfy(PinkhaHanlinSaveMessageAcceptanceFixture.validReference) else {
                throw HanlinHostError.invalidContext
            }
        }
    }

    public struct Receipt: Codable, Sendable {
        public let request: Request
        public let observedAt: Date
        public let processID: Int32
        public let sourceRevisionSHA256: String
        public let nativeSourceReadbackSHA256: String
        public let nativeSourceVersionSHA256: String?
        public let anyRuntime: PinkhaHanlinSaveMessageAcceptanceFixture.AnyRuntime?
    }

    public static func loadIfRequested(engine: PinkhaHanlinSaveMessageAcceptanceFixture.Engine) throws -> Request? {
        guard PinkhaHanlinSaveMessageAcceptanceFixture.isRequested else { return nil }
        let environment = ProcessInfo.processInfo.environment
        guard let raw = environment["PINKHA_HANLIN_SAVE_FIXTURE_ID"], let id = UUID(uuidString: raw), raw == id.uuidString else {
            throw HanlinHostError.invalidContext
        }
        let root = try PinkhaHanlinSaveMessageAcceptanceFixture.supportDirectory()
        let fixture = root.appendingPathComponent("pinkha-hanlin-save-fixture-" + id.uuidString + ".json")
        if FileManager.default.fileExists(atPath: fixture.path) { return nil }
        guard !FileManager.default.fileExists(atPath: receiptURL(root: root, id: id).path) else {
            // The controller must now bind a fresh fixture to the actual receipt.
            // A second button press cannot replace the preparation evidence.
            throw HanlinHostError.invalidContext
        }
        let url = root.appendingPathComponent("pinkha-hanlin-save-request-" + id.uuidString + ".json")
        let request = try JSONDecoder().decode(Request.self,
            from: PinkhaHanlinSaveMessageAcceptanceFixture.readRegularFile(url, maximumBytes: 16_384))
        try request.validate()
        guard request.engine == engine, request.fixtureID == id else { throw HanlinHostError.invalidContext }
        return request
    }

    public static func record(request: Request, sourceRevision: String,
        nativeSourceReadbackSHA256: String, nativeSourceVersionSHA256: String? = nil,
        anyRuntime: PinkhaHanlinSaveMessageAcceptanceFixture.AnyRuntime? = nil) throws {
        try request.validate()
        guard !sourceRevision.isEmpty, sourceRevision.utf8.count <= 4_096,
              PinkhaHanlinSaveMessageAcceptanceFixture.hex(nativeSourceReadbackSHA256, count: 64),
              nativeSourceVersionSHA256.map({ PinkhaHanlinSaveMessageAcceptanceFixture.hex($0, count: 64) }) ?? true,
              (request.engine == .any) == (anyRuntime != nil),
              (request.engine == .any) == (nativeSourceVersionSHA256 != nil) else { throw HanlinHostError.invalidContext }
        let receipt = Receipt(request: request, observedAt: .now,
            processID: ProcessInfo.processInfo.processIdentifier,
            sourceRevisionSHA256: PinkhaHanlinCreatePagePlan.digest(Data(sourceRevision.utf8)),
            nativeSourceReadbackSHA256: nativeSourceReadbackSHA256,
            nativeSourceVersionSHA256: nativeSourceVersionSHA256, anyRuntime: anyRuntime)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(receipt)
        guard bytes.count <= 16_384 else { throw HanlinHostError.outputLimitExceeded }
        try bytes.write(to: receiptURL(root: PinkhaHanlinSaveMessageAcceptanceFixture.supportDirectory(), id: request.fixtureID),
                        options: .withoutOverwriting)
    }

    static func validateReceipt(for fixture: PinkhaHanlinSaveMessageAcceptanceFixture) throws {
        let bytes = try PinkhaHanlinSaveMessageAcceptanceFixture.readRegularFile(
            receiptURL(root: PinkhaHanlinSaveMessageAcceptanceFixture.supportDirectory(), id: fixture.fixtureID), maximumBytes: 16_384)
        guard PinkhaHanlinCreatePagePlan.digest(bytes) == fixture.preparationReceiptSHA256 else { throw HanlinHostError.invalidContext }
        let receipt = try JSONDecoder().decode(Receipt.self, from: bytes)
        try receipt.request.validate()
        let r = receipt.request
        guard r.fixtureID == fixture.fixtureID, r.engine == fixture.engine,
              r.createdAt == fixture.createdAt, r.sourceSHA == fixture.sourceSHA,
              r.runID == fixture.runID, r.runAttempt == fixture.runAttempt,
              r.accountID.utf8.elementsEqual(fixture.accountID.utf8),
              r.spaceID.utf8.elementsEqual(fixture.spaceID.utf8),
              r.sourceObjectID.utf8.elementsEqual(fixture.sourceObjectID.utf8),
              r.custodyReceiptSHA256 == fixture.custodyReceiptSHA256,
              r.nativeManifestSHA256 == fixture.nativeManifestSHA256, r.nativeBinarySHA256 == fixture.nativeBinarySHA256,
              receipt.processID == fixture.processID, receipt.observedAt >= r.createdAt,
              receipt.observedAt <= .now, receipt.sourceRevisionSHA256 == fixture.sourceRevisionSHA256,
              PinkhaHanlinSaveMessageAcceptanceFixture.hex(receipt.nativeSourceReadbackSHA256, count: 64),
              (r.engine == .any) == (receipt.nativeSourceVersionSHA256 != nil),
              receipt.nativeSourceVersionSHA256.map({ PinkhaHanlinSaveMessageAcceptanceFixture.hex($0, count: 64) }) ?? true,
              receipt.anyRuntime?.generation == fixture.anyRuntime?.generation,
              receipt.anyRuntime?.engineStartedAt.data(using: .utf8) == fixture.anyRuntime?.engineStartedAt.data(using: .utf8) else {
            throw HanlinHostError.staleContext
        }
    }

    private static func receiptURL(root: URL, id: UUID) -> URL {
        root.appendingPathComponent("pinkha-hanlin-save-preparation-" + id.uuidString + ".json")
    }
}
#endif
