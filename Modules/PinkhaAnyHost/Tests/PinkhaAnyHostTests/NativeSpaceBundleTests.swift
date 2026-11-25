import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Synthetic membership controls; no native capture or source authority claim.
final class NativeSpaceBundleTests: XCTestCase {
    private struct Fixture {
        var manifest: [String: AnyJSON]
        var members: [String: Data]
        func read(accountID: String = "source-account") throws -> AnyHeartNativeSpaceBundle {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            return try AnyHeartNativeSpaceBundle(manifest: encoder.encode(AnyJSON.object(manifest)),
                sourceAccountID: accountID, sourceSpaceID: "source-space") {
                guard let bytes = members[$0.path] else { throw AnyHeartNativeSpaceBundleError.invalidMember($0.path) }
                return bytes
            }
        }
    }
    private func fixture() throws -> Fixture {
        func hash(_ value: String) -> String { AnyContentDigest.sha256(Data(value.utf8)) }
        var members: [String: Data] = [:]
        func member(_ name: String, _ bytes: Data) -> AnyJSON {
            members[name] = bytes
            return .object(["Path": .string(name), "Bytes": .integer(Int64(bytes.count)),
                            "SHA256": .string(AnyContentDigest.sha256(bytes))])
        }
        let pb = Data([0x0a, 0x00])
        let snapshot: AnyJSON = .object(["blocks": .array([]), "details": .object(["name": .string("מקור")]),
                                        "objectTypes": .array([]), "relationLinks": .array([])])
        let envelope: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string("source-space"), "ObjectID": .string("doc"), "NativeType": .integer(16),
            "UniqueKey": .string(""), "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)),
            "SnapshotBytes": .integer(Int64(pb.count)), "Snapshot": snapshot])
        let json = try JSONEncoder().encode(envelope)
        let source = member("native-source-rows.witness", Data("synthetic opaque native rows".utf8))
        let object: AnyJSON = .object(["ObjectID": .string("doc"), "UniqueKey": .string(""), "NativeType": .integer(16),
            "Snapshot": member("snapshot-" + hash("doc") + ".pb", pb),
            "NativeJSONView": member("snapshot-" + hash("doc") + ".json", json)])
        let metadata = Data([0x0a, 0x01, 0x61]), payload = Data([0, 1, 2, 255])
        let variantHash = hash("file-id\0original")
        let variant: AnyJSON = .object(["Path": .string("original"), "ContentID": .string("native-content-cid"),
            "MetadataID": .string("native-metadata-cid"), "Name": .string("מקור.bin"), "MIME": .string("application/octet-stream"),
            "NativeOriginalPath": .bool(true), "UploadChecksumMatches": .bool(true),
            "NativeChecksum": .string("native-format"), "SourceChecksum": .string("native-format"),
            "Metadata": member("metadata-" + variantHash + ".pb", metadata),
            "Payload": member(hash("file-id") + "/" + variantHash + ".payload", payload)])
        let nativeReceipt: AnyJSON = .object(["Version": .string("native-raw-object-snapshot-v1"),
            "ObjectSHA256": .string(hash("doc")), "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)),
            "SmartBlockType": .integer(16), "SnapshotBytes": .integer(Int64(pb.count)),
            "NativeIdentityBoundUnderTreeLock": .bool(true)])
        let receipt: AnyJSON = .object([
            "Version": .string("loaded-account-native-space-source-v1"),
            "Source": .object([
                "version": .string("loaded-account-native-witness-v1"),
                "accountAuthority": .string("held-application-account-directory-lease-v1"),
                "sessionAuthority": .string("validated-native-full-unassociated-session-v1"),
                "accountSHA256": .string(hash("source-account")),
                "accountDirectorySHA256": .string(hash("synthetic-account-directory")),
                "accountSessionAuthorizedAtCapture": .bool(true), "nativeIdentityCensusRequired": .bool(true),
                "source": .object([
                    "version": .string("loaded-native-acl-witness-v1"),
                    "accountSHA256": .string(hash("source-account")), "spaceSHA256": .string(hash("source-space")),
                    "aclIdSHA256": .string(hash("acl-id")), "aclHeadSHA256": .string(hash("acl-head")),
                    "alreadyLoaded": .bool(true), "aclReadAuthorizedAtCapture": .bool(true),
                    "accountSessionAuthorized": .bool(false), "remoteFreshnessEstablished": .bool(false),
                    "native": .object([
                        "Version": .string("native-localstore-witness-v1"), "SpaceSHA256": .string(hash("source-space")),
                        "WitnessSHA256": .string(hash("native-source-witness")), "Generation": .integer(7),
                        "LocalDecodedRowsComplete": .bool(true)
                    ])
                ])
            ]),
            "Inventory": .object(["SpaceSHA256": .string(hash("source-space")),
                "SourceWitnessSHA256": .string(hash("native-source-witness")), "Trees": .integer(3),
                "ACLHeadSHA256": .string(hash("acl-head")), "Generation": .integer(7),
                "OtherCollections": .integer(1), "OtherCollectionRows": .integer(1),
                "KeyValueStores": .integer(1), "KeyValueRows": .integer(1)]),
            "NativeTrees": .integer(3), "CapturedObjects": .integer(1), "CapturedFiles": .integer(1),
            "Tombstones": .integer(1), "SettingsTrees": .integer(1), "UnsupportedTrees": .integer(0),
            "FileReferences": .integer(0), "UnresolvedEntries": .integer(0), "ClosedResolverUnmapped": .integer(0),
            "SnapshotBytes": .integer(Int64(pb.count)), "MetadataBytes": .integer(Int64(metadata.count)),
            "PlaintextBytes": .integer(Int64(payload.count)), "Objects": .array([nativeReceipt]),
            "AccountSessionAuthorizedAtFinalCapture": .bool(true), "AllNativeHeadRowsAccounted": .bool(true),
            "CapturedSnapshotsBoundToUnchangedCheckpoint": .bool(true), "IndexResolverSnapshotBound": .bool(true),
            "OriginalNativeHistoryRowsRetained": .bool(true), "HistorySemanticsValidated": .bool(false),
            "AllCurrentObjectsCaptured": .bool(true), "CurrentFilePayloadCompleteness": .bool(true),
            "SemanticCompleteness": .bool(false), "HasNativeSourceAdmission": .bool(false), "PermitsDestinationWrites": .bool(false)
        ])
        func tree(_ id: String, _ type: Int64, _ status: String) -> AnyJSON {
            .object(["ObjectID": .string(id), "NativeType": .integer(type), "Status": .string(status)])
        }
        let manifest: [String: AnyJSON] = ["Contract": .string("pinkha-native-whole-source-bundle-v1"),
            "Receipt": receipt, "SourceRows": source,
            "Trees": .array([tree("doc", 16, "captured-current-snapshot"), tree("settings", -1, "space-settings-retained"),
                             tree("deleted", -1, "native-tombstone-retained")]), "Objects": .array([object]),
            "Files": .array([.object(["FileID": .string("file-id"), "Variants": .array([variant])])]),
            "FileReferences": .null, "Gaps": .null, "ResolverUnmapped": .null, "BundledDefinitionsUsed": .array([.string("ot-page")]),
            "RetainedOtherCollections": .array([.object(["Name": .string("native-key-value"), "Rows": .integer(1), "Bytes": .integer(42)])])]
        return .init(manifest: manifest, members: members)
    }

    func testEveryDeclaredMemberAndNativeTreeIsRetainedWithoutPromotingSemantics() throws {
        let f = try fixture(), bundle = try f.read()
        XCTAssertEqual(bundle.verifiedMembers.count, 5)
        XCTAssertEqual(Set(bundle.verifiedMembers.map(\.path)), Set(f.members.keys))
        XCTAssertEqual(bundle.trees.map(\.status), ["captured-current-snapshot", "space-settings-retained", "native-tombstone-retained"])
        XCTAssertEqual(bundle.objects.map(\.sourceObjectID), ["doc"])
        XCTAssertEqual(bundle.fileVariants[0].payload.byteCount, 4)
        XCTAssertEqual(bundle.fileVariants[0].name, "מקור.bin")
        XCTAssertEqual(bundle.issues.map(\.code), ["retained-collection-requires-semantic-mapping"])
        XCTAssertEqual(bundle.receipt["HasNativeSourceAdmission"]?.bool, false)
        XCTAssertEqual(bundle.receipt["HistorySemanticsValidated"]?.bool, false)
        XCTAssertEqual(bundle.rawManifest["RetainedOtherCollections"], f.manifest["RetainedOtherCollections"])
    }

    func testChangedOrMissingOpaqueRowsAndFileBytesAreRejected() throws {
        let original = try fixture()
        for path in original.members.keys {
            var changed = original; changed.members[path]! += Data([1])
            XCTAssertThrowsError(try changed.read(), path)
            changed = original; changed.members[path] = nil
            XCTAssertThrowsError(try changed.read(), path)
        }
    }

    func testNativeUnknownTypeSentinelIsLimitedToExplicitRetainedTreeStates() throws {
        let original = try fixture(), bundle = try original.read()
        XCTAssertEqual(bundle.trees.map(\.nativeType), [16, -1, -1])
        for (index, type, status) in [(0, -1, "captured-current-snapshot"),
                                      (1, -2, "space-settings-retained"),
                                      (2, -2, "native-tombstone-retained"),
                                      (1, -1, "future-retained-state")] {
            var changed = original, rows = changed.manifest["Trees"]!.array!
            var row = rows[index].object!
            row["NativeType"] = .integer(Int64(type)); row["Status"] = .string(status)
            rows[index] = .object(row); changed.manifest["Trees"] = .array(rows)
            XCTAssertThrowsError(try changed.read(), "An undecoded native type must not become a current object")
        }
        var unsupported = original, rows = unsupported.manifest["Trees"]!.array!
        var retained = rows[1].object!
        retained["Status"] = .string("unsupported-native-object-retained")
        rows[1] = .object(retained); unsupported.manifest["Trees"] = .array(rows)
        unsupported.manifest["Gaps"] = .array([.object(["ObjectID": .string("settings"),
            "Field": .string("nativeRoot"), "Reason": .string("unsupported-native-object-header-or-store-owned-details")])])
        var receipt = unsupported.manifest["Receipt"]!.object!
        receipt["SettingsTrees"] = .integer(0); receipt["UnsupportedTrees"] = .integer(1)
        receipt["UnresolvedEntries"] = .integer(1)
        receipt["AllCurrentObjectsCaptured"] = .bool(false)
        receipt["CurrentFilePayloadCompleteness"] = .bool(false)
        unsupported.manifest["Receipt"] = .object(receipt)
        let accepted = try unsupported.read()
        XCTAssertEqual(accepted.trees[1].nativeType, -1)
        XCTAssertTrue(accepted.issues.contains { $0.code == "native-tree-semantic-gap" })
        XCTAssertTrue(accepted.issues.contains { $0.code == "native-source-gap" })
        XCTAssertEqual(accepted.receipt["HasNativeSourceAdmission"]?.bool, false)
        XCTAssertEqual(accepted.receipt["PermitsDestinationWrites"]?.bool, false)
    }

    func testInventoriesCannotOmitDuplicateOrReclassifyCapturedObjects() throws {
        var f = try fixture(); f.manifest["Objects"] = .array([])
        XCTAssertThrowsError(try f.read())
        f = try fixture(); let objects = f.manifest["Objects"]!.array!
        f.manifest["Objects"] = .array(objects + objects)
        XCTAssertThrowsError(try f.read())
        f = try fixture(); var receipt = f.manifest["Receipt"]!.object!
        receipt["CapturedObjects"] = .integer(0); f.manifest["Receipt"] = .object(receipt)
        XCTAssertThrowsError(try f.read())
        f = try fixture(); var trees = f.manifest["Trees"]!.array!, first = trees[0].object!
        first["Status"] = .string("space-settings-retained"); trees[0] = .object(first); f.manifest["Trees"] = .array(trees)
        XCTAssertThrowsError(try f.read())
    }

    func testPathsAndSpaceBindingsCannotEscapeAndFutureFieldsStayExplicit() throws {
        var f = try fixture(); var rows = f.manifest["SourceRows"]!.object!
        rows["Path"] = .string("../foreign-source"); f.manifest["SourceRows"] = .object(rows)
        XCTAssertThrowsError(try f.read())
        f = try fixture(); var receipt = f.manifest["Receipt"]!.object!, inventory = receipt["Inventory"]!.object!
        inventory["SpaceSHA256"] = .string(AnyContentDigest.sha256(Data("other-space".utf8)))
        receipt["Inventory"] = .object(inventory); f.manifest["Receipt"] = .object(receipt)
        XCTAssertThrowsError(try f.read())
        f = try fixture(); f.manifest["FutureNativeState"] = .object(["mustRetain": .bool(true)])
        let bundle = try f.read()
        XCTAssertTrue(bundle.issues.contains { $0.code == "unknown-manifest-field" && $0.field == "FutureNativeState" })
        XCTAssertEqual(bundle.rawManifest["FutureNativeState"], f.manifest["FutureNativeState"])
    }

    func testCapturedAccountSpaceACLAndCheckpointMustAgreeWithoutPromotingTheLowerWitness() throws {
        let original = try fixture(), accepted = try original.read()
        XCTAssertEqual(accepted.sourceAccountID, "source-account")
        XCTAssertEqual(accepted.receipt["Source"]?["source"]?["accountSessionAuthorized"]?.bool, false)
        XCTAssertThrowsError(try original.read(accountID: "another-account"))
        func changed(_ value: AnyJSON, path: ArraySlice<String>, to replacement: AnyJSON) -> AnyJSON {
            guard let key = path.first else { return replacement }
            var object = value.object!
            object[key] = changed(object[key]!, path: path.dropFirst(), to: replacement)
            return .object(object)
        }
        let differentHash = AnyJSON.string(String(repeating: "f", count: 64))
        let mutations: [([String], AnyJSON)] = [
            (["Source", "accountSHA256"], differentHash),
            (["Source", "source", "accountSHA256"], differentHash),
            (["Source", "source", "spaceSHA256"], differentHash),
            (["Source", "source", "aclHeadSHA256"], differentHash),
            (["Source", "source", "native", "SpaceSHA256"], differentHash),
            (["Source", "source", "native", "WitnessSHA256"], differentHash),
            (["Source", "source", "native", "Generation"], .integer(8)),
            (["Source", "accountSessionAuthorizedAtCapture"], .bool(false)),
            (["Source", "source", "aclReadAuthorizedAtCapture"], .bool(false)),
            (["Source", "source", "native", "LocalDecodedRowsComplete"], .bool(false)),
            (["Source", "sessionAuthority"], .string("app-associated-session"))
        ]
        for (path, value) in mutations {
            var f = original
            f.manifest["Receipt"] = changed(f.manifest["Receipt"]!, path: path[...], to: value)
            XCTAssertThrowsError(try f.read(), path.joined(separator: "."))
        }
    }
}
