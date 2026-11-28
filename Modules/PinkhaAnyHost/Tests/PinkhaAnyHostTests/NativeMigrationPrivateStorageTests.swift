import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

/// Private, synthetic filesystem controls only. No native account, original
/// capture, migration executor or existing private journal is opened by these
/// tests. Static bind-mount identity exclusion is a source-review obligation;
/// these unprivileged controls do not claim to create or qualify a mount alias.
final class NativeMigrationPrivateStorageTests: XCTestCase, @unchecked Sendable {
    private let account = "source-account", space = "source-space"
    private func hash(_ text: String) -> String { AnyContentDigest.sha256(Data(text.utf8)) }
    private func encode(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    private func receipt() -> AnyJSON {
        .object([
            "Version": .string("loaded-account-native-space-source-v1"),
            "Source": .object([
                "version": .string("loaded-account-native-witness-v1"),
                "accountAuthority": .string("held-application-account-directory-lease-v1"),
                "sessionAuthority": .string("validated-native-full-unassociated-session-v1"),
                "accountSHA256": .string(hash(account)), "accountDirectorySHA256": .string(hash("unit-directory")),
                "accountSessionAuthorizedAtCapture": .bool(true), "nativeIdentityCensusRequired": .bool(true),
                "source": .object([
                    "version": .string("loaded-native-acl-witness-v1"),
                    "accountSHA256": .string(hash(account)), "spaceSHA256": .string(hash(space)),
                    "alreadyLoaded": .bool(true), "aclReadAuthorizedAtCapture": .bool(true),
                    "aclIdSHA256": .string(hash("acl")), "aclHeadSHA256": .string(hash("head")),
                    "native": .object([
                        "Version": .string("native-localstore-witness-v1"), "SpaceSHA256": .string(hash(space)),
                        "WitnessSHA256": .string(hash("unit-witness")), "LocalDecodedRowsComplete": .bool(true),
                        "Generation": .integer(0)])
                ])
            ]),
            "Inventory": .object(["SpaceSHA256": .string(hash(space)), "SourceWitnessSHA256": .string(hash("unit-witness")),
                "ACLHeadSHA256": .string(hash("head")), "Generation": .integer(0), "Trees": .integer(0),
                "OtherCollections": .integer(0), "OtherCollectionRows": .integer(0)]),
            "AccountSessionAuthorizedAtFinalCapture": .bool(true), "AllNativeHeadRowsAccounted": .bool(true),
            "CapturedSnapshotsBoundToUnchangedCheckpoint": .bool(true), "OriginalNativeHistoryRowsRetained": .bool(true),
            "NativeTrees": .integer(0), "CapturedObjects": .integer(0), "CapturedFiles": .integer(0),
            "FileReferences": .integer(0), "UnresolvedEntries": .integer(0), "ClosedResolverUnmapped": .integer(0),
            "SnapshotBytes": .integer(0), "MetadataBytes": .integer(0), "PlaintextBytes": .integer(0),
            "Tombstones": .integer(0), "SettingsTrees": .integer(0), "UnsupportedTrees": .integer(0),
            "IndexResolverSnapshotBound": .bool(false), "Objects": .array([]),
            "AllCurrentObjectsCaptured": .bool(true), "CurrentFilePayloadCompleteness": .bool(true),
            "PermitsDestinationWrites": .bool(false), "HasNativeSourceAdmission": .bool(false),
            "SemanticCompleteness": .bool(false), "HistorySemanticsValidated": .bool(false)])
    }


    private struct Fixture {
        let root: URL
        let captureParent: URL
        let capture: URL
        let journal: URL
        let payload: URL
        let archive: AnyHeartNativePreservationArchive
        let binding: AnyPreparedMigrationPlanBinding
        var journalRoot: URL { journal.appendingPathComponent("AnyDestinationMigrationV1", isDirectory: true) }
        var journalScope: URL {
            journalRoot.appendingPathComponent(AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
                binding.workspace.accountID, binding.workspace.spaceID, binding.storeID, binding.planID
            ])), isDirectory: true)
        }
    }

    private func directory(_ url: URL) throws {
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true,
            attributes: [.posixPermissions: 0o700])
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: url.path)
    }

    private func withFixture(_ body: (Fixture) throws -> Void) throws {
        let root = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("capture-private-storage-control-" + UUID().uuidString, isDirectory: true)
        try directory(root)
        defer { try? FileManager.default.removeItem(at: root) }
        let captureParent = root.appendingPathComponent("capture", isDirectory: true)
        let capture = captureParent.appendingPathComponent("native-source-control", isDirectory: true)
        let journal = root.appendingPathComponent("journal", isDirectory: true)
        let payload = root.appendingPathComponent("payload", isDirectory: true)
        for path in [captureParent, capture, journal, payload] { try directory(path) }
        // Large enough to exercise the original native-file threshold without
        // turning the synthetic source witness into a native admission.
        let rows = Data(repeating: 65, count: 8192)
        let manifest = try encode(.object([
            "Contract": .string("pinkha-native-whole-source-bundle-v1"), "Receipt": receipt(),
            "SourceRows": .object(["Path": .string("native-source-rows.witness"),
                "SHA256": .string(AnyContentDigest.sha256(rows)), "Bytes": .integer(Int64(rows.count))]),
            "Trees": .array([]), "Objects": .array([]), "Files": .array([]), "FileReferences": .array([]),
            "Gaps": .array([]), "ResolverUnmapped": .array([]), "BundledDefinitionsUsed": .array([]),
            "BundledDefinitions": .null, "RetainedOtherCollections": .array([])
        ]))
        for (name, bytes) in [("manifest.json", manifest), ("native-source-rows.witness", rows)] {
            let url = capture.appendingPathComponent(name)
            try bytes.write(to: url)
            try FileManager.default.setAttributes([.posixPermissions: 0o400], ofItemAtPath: url.path)
        }
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest, sourceAccountID: account,
                                                   sourceSpaceID: space) { member in
            guard member.path == "native-source-rows.witness" else {
                throw AnyHeartNativePreservationError.member
            }
            return rows
        }
        let archive = try AnyHeartNativePreservationArchive(capturedBundle: bundle) { member in
            guard member.path == "native-source-rows.witness" else {
                throw AnyHeartNativePreservationError.member
            }
            return rows
        }
        let binding = try AnyPreparedMigrationPlanBinding(
            workspace: .init(accountID: "destination-account", spaceID: "destination-space"),
            storeID: "fixture-store", planID: String(repeating: "1", count: 64),
            planSHA256: String(repeating: "2", count: 64))
        try body(.init(root: root, captureParent: captureParent, capture: capture,
                       journal: journal, payload: payload, archive: archive, binding: binding))
    }

    private func storage(_ fixture: Fixture, journal: URL? = nil,
                         payload: URL? = nil) throws -> AnyHeartMigrationPrivateStorage {
        try .init(captureParent: fixture.captureParent, captureDirectory: fixture.capture.path,
                  journalParent: journal ?? fixture.journal, payloadParent: payload ?? fixture.payload,
                  planBinding: fixture.binding)
    }

    private func metadata(_ url: URL) throws -> stat {
        var value = stat()
        guard lstat(url.path, &value) == 0 else { throw AnyHeartNativeMigrationProducerError.privateStorage }
        return value
    }

    func testFreshArchiveAndExactReuseKeepOnePrivateVerifiedFile() throws {
        try withFixture { f in
            let scope = try storage(f)
            let output = try scope.materialize(f.archive)
            let before = try metadata(output)
            XCTAssertEqual(before.st_mode & mode_t(S_IFMT), mode_t(S_IFREG))
            XCTAssertEqual(before.st_mode & mode_t(0o7777), mode_t(0o400))
            XCTAssertEqual(before.st_uid, geteuid())
            XCTAssertEqual(before.st_nlink, 1)
            XCTAssertEqual(try Data(contentsOf: output), f.archive.bytes)
            let reused = try scope.materialize(f.archive), after = try metadata(reused)
            XCTAssertEqual(reused, output)
            XCTAssertEqual(before.st_dev, after.st_dev)
            XCTAssertEqual(before.st_ino, after.st_ino)
            XCTAssertEqual(try Data(contentsOf: reused), f.archive.bytes)
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: f.payload.path),
                           [output.lastPathComponent])
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: f.journal.path), [])
            // The unchanged Journal may create its two prospective directories
            // only under the stable private owner. Later scope checks admit
            // those exact normal paths without claiming journal completion.
            try directory(f.journalRoot); try directory(f.journalScope)
            try scope.validate()
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: f.journalScope.path), [])
        }
    }

    func testCaptureAndUnlistedDescendantAreRefusedAsEitherOutputParent() throws {
        try withFixture { f in
            let hidden = f.capture.appendingPathComponent("unlisted-private-child", isDirectory: true)
            try directory(hidden)
            let sentinel = hidden.appendingPathComponent("sentinel")
            let bytes = Data("retain this synthetic capture member".utf8)
            try bytes.write(to: sentinel)
            try FileManager.default.setAttributes([.posixPermissions: 0o400], ofItemAtPath: sentinel.path)
            for forbidden in [f.capture, hidden] {
                XCTAssertThrowsError(try storage(f, journal: forbidden)) {
                    XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .privateStorage)
                }
                XCTAssertThrowsError(try storage(f, payload: forbidden)) {
                    XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .privateStorage)
                }
            }
            let alias = f.root.appendingPathComponent("capture-link", isDirectory: true)
            try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: hidden)
            XCTAssertThrowsError(try storage(f, payload: alias)) {
                XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .privateStorage)
            }
            XCTAssertEqual(try Data(contentsOf: sentinel), bytes)
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: f.payload.path), [])
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: f.journal.path), [])
        }
    }

    func testPartialOrWritableExistingArchiveIsRetainedAndNeverOverwritten() throws {
        for partial in [true, false] {
            try withFixture { f in
                let output = f.payload.appendingPathComponent(
                    "captured-source-" + f.archive.sha256 + ".pinkha-heart-source")
                let previous = partial ? Data("retained partial".utf8) : f.archive.bytes
                try previous.write(to: output)
                try FileManager.default.setAttributes([.posixPermissions: partial ? 0o400 : 0o600],
                                                       ofItemAtPath: output.path)
                let before = try metadata(output)
                let scope = try storage(f)
                XCTAssertThrowsError(try scope.materialize(f.archive)) {
                    XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .privateStorage)
                }
                let after = try metadata(output)
                XCTAssertEqual(try Data(contentsOf: output), previous)
                XCTAssertEqual(before.st_dev, after.st_dev)
                XCTAssertEqual(before.st_ino, after.st_ino)
                XCTAssertEqual(before.st_mode, after.st_mode)
                XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: f.payload.path),
                               [output.lastPathComponent])
            }
        }
    }

    func testReplacedOutputOrExistingJournalScopeRefusesBeforeMaterialization() throws {
        for replaceJournalScope in [false, true] {
            try withFixture { f in
                try directory(f.journalRoot); try directory(f.journalScope)
                let scope = try storage(f)
                let original = replaceJournalScope ? f.journalScope : f.payload
                let retained = original.deletingLastPathComponent().appendingPathComponent(
                    original.lastPathComponent + "-retained", isDirectory: true)
                try FileManager.default.moveItem(at: original, to: retained)
                try directory(original)
                XCTAssertThrowsError(try scope.validate()) {
                    XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .privateStorage)
                }
                XCTAssertThrowsError(try scope.materialize(f.archive)) {
                    XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .privateStorage)
                }
                XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: f.payload.path), [])
                XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: retained.path), [])
            }
        }
    }
}
