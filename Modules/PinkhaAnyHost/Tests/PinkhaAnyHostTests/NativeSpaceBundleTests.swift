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
        XCTAssertEqual(bundle.issues.map(\.code),
                       ["compiled-definition-descriptors-not-captured", "retained-collection-requires-semantic-mapping"])
        XCTAssertTrue(bundle.bundledDefinitions.isEmpty)
        XCTAssertEqual(bundle.bundledDefinitionsUsed, ["ot-page"])
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

    private func addingCompiledDefinitions(to input: Fixture) throws -> Fixture {
        var result = input
        var entries: [AnyJSON] = []
        for (kind, key, message, definition) in [
            ("property", "componentField", "anytype.model.Relation",
             AnyJSON.object(["id": .string("_brcomponentField"), "key": .string("componentField"),
                             "name": .string("Explicit synthetic descriptor"), "format": .integer(0),
                             "futureSourceField": .object(["preserved": .bool(true)])])),
            ("type", "page", "anytype.model.ObjectType",
             AnyJSON.object(["key": .string("page"), "name": .string("Page"), "layout": .integer(0)]))
        ] {
            // Byte-membership control only. Native protobuf/JSON equivalence is
            // separately exercised against the actual generated Go descriptors.
            let raw = Data(("synthetic-protobuf-component-only:" + kind + ":" + key).utf8)
            let view: AnyJSON = .object(["Contract": .string("pinkha-native-bundled-definition-json-v1"),
                "Kind": .string(kind), "Key": .string(key), "ProtobufMessage": .string(message),
                "ProtobufSHA256": .string(AnyContentDigest.sha256(raw)), "ProtobufBytes": .integer(Int64(raw.count)),
                "Definition": definition])
            let json = try JSONEncoder().encode(view)
            let base = "compiled-definition-" + AnyContentDigest.sha256(Data((kind + ":" + key).utf8))
            func add(_ name: String, _ data: Data) -> AnyJSON {
                result.members[name] = data
                return .object(["Path": .string(name), "Bytes": .integer(Int64(data.count)),
                                "SHA256": .string(AnyContentDigest.sha256(data))])
            }
            entries.append(.object(["Kind": .string(kind), "Key": .string(key), "ProtobufMessage": .string(message),
                "Protobuf": add(base + ".pb", raw), "JSONView": add(base + ".json", json)]))
        }
        result.manifest["BundledDefinitionsUsed"] = .array([.string("property:componentField"), .string("type:page")])
        result.manifest["BundledDefinitions"] = .array(entries)
        return result
    }

    func testCompiledDescriptorsRetainExactMembersWithoutBecomingSourceObjects() throws {
        let f = try addingCompiledDefinitions(to: fixture()), bundle = try f.read()
        XCTAssertEqual(bundle.verifiedMembers.count, 9)
        XCTAssertEqual(Set(bundle.verifiedMembers.map(\.path)), Set(f.members.keys))
        XCTAssertEqual(bundle.objects.map(\.sourceObjectID), ["doc"])
        XCTAssertEqual(bundle.trees.count, 3)
        XCTAssertEqual(bundle.bundledDefinitions.map(\.identity), ["property:componentField", "type:page"])
        XCTAssertEqual(bundle.bundledDefinitions[0].definition["futureSourceField"], .object(["preserved": .bool(true)]))
        for descriptor in bundle.bundledDefinitions {
            XCTAssertEqual(AnyContentDigest.sha256(descriptor.protobufBytes), descriptor.protobufSHA256)
            XCTAssertEqual(AnyContentDigest.sha256(descriptor.jsonViewBytes), descriptor.jsonViewSHA256)
        }
        XCTAssertFalse(bundle.issues.contains { $0.code == "compiled-definition-descriptors-not-captured" })
        XCTAssertEqual(bundle.receipt["HasNativeSourceAdmission"], .bool(false))
        XCTAssertEqual(bundle.receipt["PermitsDestinationWrites"], .bool(false))
    }

    func testCompiledDescriptorMembershipRejectsMissingChangedReorderedAndDuplicateEntries() throws {
        let original = try addingCompiledDefinitions(to: fixture())
        let entries = try XCTUnwrap(original.manifest["BundledDefinitions"]?.array)
        for entry in entries {
            for field in ["Protobuf", "JSONView"] {
                let path = try XCTUnwrap(entry[field]?["Path"]?.string)
                var changed = original; changed.members[path] = nil
                XCTAssertThrowsError(try changed.read())
                changed = original; changed.members[path]! += Data([1])
                XCTAssertThrowsError(try changed.read())
            }
        }
        for replacement in [AnyJSON.null, .array([]), .array(Array(entries.reversed())), .array(entries + [entries[0]])] {
            var changed = original; changed.manifest["BundledDefinitions"] = replacement
            XCTAssertThrowsError(try changed.read())
        }
        for replacement in [AnyJSON.null, .array([.string("type:page")]),
                                     .array([.string("property:componentField"), .string("property:componentField")])] {
            var changed = original; changed.manifest["BundledDefinitionsUsed"] = replacement
            XCTAssertThrowsError(try changed.read())
        }
    }

    func testCompiledDescriptorViewMustMatchProtobufBindingAndExactNativeIdentity() throws {
        let original = try addingCompiledDefinitions(to: fixture())
        let entries = try XCTUnwrap(original.manifest["BundledDefinitions"]?.array)
        let originalEntry = try XCTUnwrap(entries.first?.object)
        let originalMember = try XCTUnwrap(originalEntry["JSONView"]?.object)
        let path = try XCTUnwrap(originalMember["Path"]?.string)
        let raw = try XCTUnwrap(original.members[path])
        let view = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: raw).object)
        for (field, value) in [
            ("Contract", AnyJSON.string("future-unqualified-contract")),
            ("Key", .string("foreign-key")), ("Kind", .string("type")),
            ("ProtobufMessage", .string("anytype.model.ObjectType")),
            ("ProtobufSHA256", .string(String(repeating: "0", count: 64))),
            ("ProtobufBytes", .integer(1)),
            ("Definition", .object(["key": .string("componentField"), "id": .string("_brforeign-key")]))
        ] {
            var changed = original, newView = view; newView[field] = value
            let bytes = try JSONEncoder().encode(AnyJSON.object(newView))
            changed.members[path] = bytes
            var member = originalMember; member["SHA256"] = .string(AnyContentDigest.sha256(bytes))
            member["Bytes"] = .integer(Int64(bytes.count))
            var entry = originalEntry; entry["JSONView"] = .object(member)
            changed.manifest["BundledDefinitions"] = .array([.object(entry), entries[1]])
            XCTAssertThrowsError(try changed.read(), field)
        }
    }

    func testActualNativeCompiledRegistryCaptureRetainsCompleteOriginalMembers() throws {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_NATIVE_COMPILED_CAPTURE_FIXTURE"] else {
            throw XCTSkip("Requires the retained exact native compiled-descriptor capture.")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let pieces = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
                  pieces.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw AnyHeartNativeSpaceBundleError.invalidManifest
            }
            let file = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
            guard file.path.hasPrefix(directory.path + "/"),
                  try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
                throw AnyHeartNativeSpaceBundleError.invalidMember(relative)
            }
            return try Data(contentsOf: file, options: [.mappedIfSafe])
        }
        let contextBytes = try bytes("fixture-context.json", under: root)
        XCTAssertEqual(AnyContentDigest.sha256(contextBytes), "f68679409eaf93676b346eed7e2e9bd31146674956c634081268f36303f527b9")
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        XCTAssertEqual(context["nativeSource"], .string("5e8f9ce4ec789c1cd775b148a6cc49d4a28f56b5"))
        XCTAssertEqual(context["nativeMethodResult"], .string("PASS"))
        XCTAssertEqual(context["sourceAdmissionPromoted"], .bool(false))
        let directory = root.appendingPathComponent("bundle", isDirectory: true)
        let manifest = try bytes("manifest.json", under: directory)
        XCTAssertEqual(AnyContentDigest.sha256(manifest), "04b9309e1b96918c47d1b00eed6b1a76b2e13432636a0aba77706f2f69082994")
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try bytes($0.path, under: directory) }
        XCTAssertEqual(bundle.objects.count, 143)
        XCTAssertEqual(bundle.trees.count, 144)
        XCTAssertEqual(bundle.verifiedMembers.count, 299)
        XCTAssertEqual(bundle.bundledDefinitions.map(\.identity), [
            "property:analyticsSpaceId", "property:apiObjectKey", "property:headerRelationsLayout",
            "property:homepage", "property:migrationObjectContext", "property:relationFormatIncludeTime"
        ])
        XCTAssertEqual(bundle.bundledDefinitionsUsed, bundle.bundledDefinitions.map(\.identity))
        XCTAssertFalse(bundle.issues.contains { $0.code == "compiled-definition-descriptors-not-captured" })
        XCTAssertFalse(bundle.issues.contains { $0.code == "unknown-manifest-field" && $0.field == "BundledDefinitions" })
        for definition in bundle.bundledDefinitions {
            XCTAssertEqual(definition.kind, .property)
            XCTAssertEqual(definition.protobufMessage, "anytype.model.Relation")
            XCTAssertNil(definition.definition["defaultValue"], "Actual native absent Value must remain absent in its JSON view")
            XCTAssertEqual(definition.definition["key"], .string(definition.key))
            XCTAssertEqual(definition.definition["id"], .string("_br" + definition.key))
        }
        XCTAssertEqual(bundle.receipt["HasNativeSourceAdmission"], .bool(false))
        XCTAssertEqual(bundle.receipt["PermitsDestinationWrites"], .bool(false))
        XCTAssertFalse(try AnyHeartNativeDefinitionCatalog(bundle: bundle).permitsDestinationWrites)
        XCTAssertEqual(try bytes("manifest.json", under: directory), manifest)
        print("ACTUAL_NATIVE_COMPILED_CAPTURE snapshots=143 trees=144 descriptors=6 original_members=299 destination_admission=false")
    }
}
