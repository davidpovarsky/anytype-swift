import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativeCaptureDescriptorTests: XCTestCase {
    private let account = "source-account", space = "source-space", request = "capture-control-1"
    private func hash(_ text: String) -> String { AnyContentDigest.sha256(Data(text.utf8)) }
    private func encode(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    private func descriptor(_ value: AnyJSON, accountID: String? = nil) throws -> AnyHeartNativeCaptureDescriptor {
        try .init(data: encode(value), expectedAccountID: accountID ?? account,
                  expectedSpaceID: space, expectedRequestID: request)
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

    private func descriptorValue(manifest: Data, directory: URL, accountID: String, spaceID: String) throws -> AnyJSON {
        let root = try JSONDecoder().decode(AnyJSON.self, from: manifest)
        return .object([
            "contract": .string(AnyHeartNativeCaptureDescriptor.contract), "requestID": .string(request),
            "sourceAccountID": .string(accountID), "sourceSpaceID": .string(spaceID),
            "privateBundleDirectory": .string(directory.path), "manifestSHA256": .string(AnyContentDigest.sha256(manifest)),
            "sourceRowsSHA256": try XCTUnwrap(root["SourceRows"]?["SHA256"]),
            "nativeTrees": try XCTUnwrap(root["Receipt"]?["NativeTrees"]),
            "capturedObjects": try XCTUnwrap(root["Receipt"]?["CapturedObjects"]),
            "capturedFiles": try XCTUnwrap(root["Receipt"]?["CapturedFiles"]),
            "accountSessionAuthorizedAtCapture": .bool(true), "capturedSnapshotsBoundToCheckpoint": .bool(true),
            "currentFilePayloadCompleteness": try XCTUnwrap(root["Receipt"]?["CurrentFilePayloadCompleteness"]),
            "originalNativeHistoryRowsRetained": .bool(true), "permitsDestinationWrites": .bool(false)])
    }

    private func withFixture(_ body: (URL, URL, AnyJSON) throws -> Void) throws {
        let root = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("capture-reader-control-" + UUID().uuidString, isDirectory: true)
        let directory = root.appendingPathComponent("native-source-control", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true,
                                                 attributes: [.posixPermissions: 0o700])
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: root.path)
        let rows = Data("synthetic unit control; not a native capture".utf8)
        let manifest = try encode(.object([
            "Contract": .string("pinkha-native-whole-source-bundle-v1"), "Receipt": receipt(),
            "SourceRows": .object(["Path": .string("native-source-rows.witness"),
                "SHA256": .string(AnyContentDigest.sha256(rows)), "Bytes": .integer(Int64(rows.count))]),
            "Trees": .array([]), "Objects": .array([]), "Files": .array([]), "FileReferences": .array([]),
            "Gaps": .array([]), "ResolverUnmapped": .array([]), "BundledDefinitionsUsed": .array([]),
            "RetainedOtherCollections": .array([])]))
        for (name, bytes) in [("manifest.json", manifest), ("native-source-rows.witness", rows)] {
            let url = directory.appendingPathComponent(name)
            try bytes.write(to: url)
            try FileManager.default.setAttributes([.posixPermissions: 0o400], ofItemAtPath: url.path)
        }
        try body(root, directory, descriptorValue(manifest: manifest, directory: directory, accountID: account, spaceID: space))
    }

    func testDescriptorRequiresExactCallerIdentityAndUnambiguousCapturedOnlyContract() throws {
        try withFixture { _, _, original in
            XCTAssertFalse(try descriptor(original).permitsDestinationWrites)
            let mutations: [(String, AnyJSON)] = [
                ("contract", .string("future-capture")), ("requestID", .string("different-request")),
                ("sourceAccountID", .string("another-account")), ("sourceSpaceID", .string("another-space")),
                ("accountSessionAuthorizedAtCapture", .bool(false)), ("capturedSnapshotsBoundToCheckpoint", .bool(false)),
                ("originalNativeHistoryRowsRetained", .bool(false)), ("permitsDestinationWrites", .bool(true)),
                ("capturedObjects", .integer(1)), ("capturedFiles", .integer(257)), ("nativeTrees", .integer(-1)),
                ("manifestSHA256", .string(String(repeating: "F", count: 64))),
                ("unknown", .string("must-not-be-discarded")), ("privateBundleDirectory", .string("relative"))]
            for (key, value) in mutations {
                var row = original.object!; row[key] = value
                XCTAssertThrowsError(try descriptor(.object(row)), key)
            }
            var composed = original.object!; composed["sourceAccountID"] = .string("\u{00E1}")
            XCTAssertThrowsError(try descriptor(.object(composed), accountID: "a\u{0301}"), "Identity is exact UTF-8, not Unicode-equivalent text")
            let encoded = try encode(original)
            let duplicate = Data(("{" + "\"permitsDestinationWrites\":true," + String(decoding: encoded.dropFirst(), as: UTF8.self)).utf8)
            XCTAssertThrowsError(try AnyHeartNativeCaptureDescriptor(data: duplicate, expectedAccountID: account,
                expectedSpaceID: space, expectedRequestID: request))
        }
    }

    func testPrivateBundleReadVerifiesAllBytesWithoutPromotingSourceOrDestinationAuthority() throws {
        try withFixture { root, _, value in
            let capture = try descriptor(value), bundle = try capture.loadBundle(under: root)
            XCTAssertEqual(bundle.sourceAccountID, account)
            XCTAssertEqual(bundle.sourceRows.sha256, capture.sourceRowsSHA256)
            XCTAssertEqual(bundle.verifiedMembers.count, 1)
            XCTAssertFalse(capture.permitsDestinationWrites)
            XCTAssertEqual(bundle.receipt["PermitsDestinationWrites"]?.bool, false)
            XCTAssertEqual(bundle.receipt["HasNativeSourceAdmission"]?.bool, false)
        }
    }

    func testChangedManifestSourceBytesCountsAndFlagsAreRefused() throws {
        for name in ["manifest.json", "native-source-rows.witness"] {
            try withFixture { root, directory, value in
                let file = directory.appendingPathComponent(name)
                var bytes = try Data(contentsOf: file); bytes[bytes.startIndex] ^= 1
                try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
                try bytes.write(to: file)
                try FileManager.default.setAttributes([.posixPermissions: 0o400], ofItemAtPath: file.path)
                XCTAssertThrowsError(try descriptor(value).loadBundle(under: root), name)
            }
        }
        for (key, replacement) in [("nativeTrees", AnyJSON.integer(1)), ("capturedFiles", .integer(1)),
                                    ("currentFilePayloadCompleteness", .bool(false)),
                                    ("sourceRowsSHA256", .string(String(repeating: "f", count: 64)))] {
            try withFixture { root, _, original in
                var value = original.object!; value[key] = replacement
                XCTAssertThrowsError(try descriptor(.object(value)).loadBundle(under: root), key)
            }
        }
    }

    func testParentEscapeSymlinksAndNonPrivatePermissionsAreRefused() throws {
        for mutation in ["wrong-parent", "parent-symlink", "bundle-symlink", "member-symlink",
                         "writable-manifest", "writable-member", "public-parent", "public-bundle"] {
            try withFixture { root, directory, original in
                var parent = root, value = original.object!
                switch mutation {
                case "wrong-parent": parent = root.deletingLastPathComponent()
                case "parent-symlink":
                    let link = root.appendingPathComponent("parent-link")
                    try FileManager.default.createSymbolicLink(at: link, withDestinationURL: root)
                    parent = link
                case "bundle-symlink":
                    let link = root.appendingPathComponent("native-source-link")
                    try FileManager.default.createSymbolicLink(at: link, withDestinationURL: directory)
                    value["privateBundleDirectory"] = .string(link.path)
                case "member-symlink":
                    let file = directory.appendingPathComponent("native-source-rows.witness")
                    let moved = root.appendingPathComponent("retained-control.witness")
                    try FileManager.default.moveItem(at: file, to: moved)
                    try FileManager.default.createSymbolicLink(at: file, withDestinationURL: moved)
                case "writable-manifest", "writable-member":
                    let name = mutation == "writable-manifest" ? "manifest.json" : "native-source-rows.witness"
                    try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: directory.appendingPathComponent(name).path)
                case "public-parent": try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: root.path)
                default: try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: directory.path)
                }
                XCTAssertThrowsError(try descriptor(.object(value)).loadBundle(under: parent), mutation)
            }
        }
    }

    func testOriginalNativeCapturesReadThroughPrivateDescriptorAndKeepTheirSemanticBlockers() throws {
        let fixtures = [
            ("PINKHA_NATIVE_SOURCE_FIXTURE", 144, "5357d52f5e76b604a40d7a5f2b1bc002e19bc864c419a45f90128bfa965d5850",
             "2a1a02987204321aaa1c8cf9f0c7f413f4b50dbce87280d82499c4f9bc7be238"),
            ("PINKHA_NATIVE_CUSTOM_SOURCE_FIXTURE", 156, "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a",
             "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4")]
        for (environment, count, contextHash, manifestHash) in fixtures {
            guard let path = ProcessInfo.processInfo.environment[environment] else {
                throw XCTSkip("Explicit immutable original capture is required")
            }
            let source = URL(fileURLWithPath: path, isDirectory: true)
            let contextData = try Data(contentsOf: source.appendingPathComponent("fixture-context.json"))
            XCTAssertEqual(AnyContentDigest.sha256(contextData), contextHash)
            let context = try JSONDecoder().decode(AnyJSON.self, from: contextData)
            let originalDirectory = source.appendingPathComponent(try XCTUnwrap(context["bundleRelativePath"]?.string))
            let parent = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
                .appendingPathComponent("capture-reader-original-" + UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false,
                                                    attributes: [.posixPermissions: 0o700])
            defer { try? FileManager.default.removeItem(at: parent) }
            let directory = parent.appendingPathComponent("native-source-retained", isDirectory: true)
            try FileManager.default.copyItem(at: originalDirectory, to: directory)
            try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: directory.path)
            let enumerator = try XCTUnwrap(FileManager.default.enumerator(at: directory,
                includingPropertiesForKeys: [.isDirectoryKey, .isSymbolicLinkKey]))
            for case let url as URL in enumerator {
                let attributes = try url.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
                XCTAssertNotEqual(attributes.isSymbolicLink, true)
                try FileManager.default.setAttributes([.posixPermissions: attributes.isDirectory == true ? 0o700 : 0o400],
                                                       ofItemAtPath: url.path)
            }
            let manifest = try Data(contentsOf: directory.appendingPathComponent("manifest.json"))
            XCTAssertEqual(AnyContentDigest.sha256(manifest), manifestHash)
            let accountID = try XCTUnwrap(context["sourceAccountID"]?.string)
            let spaceID = try XCTUnwrap(context["sourceSpaceID"]?.string)
            let value = try descriptorValue(manifest: manifest, directory: directory, accountID: accountID, spaceID: spaceID)
            let capture = try AnyHeartNativeCaptureDescriptor(data: encode(value), expectedAccountID: accountID,
                expectedSpaceID: spaceID, expectedRequestID: request)
            let bundle = try capture.loadBundle(under: parent)
            XCTAssertEqual(bundle.objects.count, count)
            XCTAssertEqual(bundle.manifestSHA256, manifestHash)
            XCTAssertFalse(capture.permitsDestinationWrites)
            XCTAssertEqual(bundle.receipt["PermitsDestinationWrites"]?.bool, false)
            let definitions = try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: bundle))
            XCTAssertFalse(definitions.issues.isEmpty, "Real source semantic gaps must not disappear")
            XCTAssertThrowsError(try definitions.admittedSchemaItems())
            print("PRIVATE_CAPTURE_READER objects=\(count) verifiedMembers=\(bundle.verifiedMembers.count) originalManifest=\(manifestHash) permitsDestinationWrites=false originalSourceIssuesRetained=true")
        }
    }
}
