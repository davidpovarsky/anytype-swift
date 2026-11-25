import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Reuses immutable original captures. These controls do not mint a native
/// lease, migrate ACL membership, write a destination or prove history replay.
final class NativeHeadCensusTests: XCTestCase {
    func testFreshNative5e8CensusIncludesSettingsACLAndDefaultKV() throws {
        let bundle = try original()
        let census = try XCTUnwrap(bundle.nativeStoreContext?.headCensus)
        XCTAssertEqual(bundle.objects.count, 143)
        XCTAssertEqual(bundle.trees.count, 144)
        XCTAssertEqual(census.sourceHeadIDs.count, 146)
        try requireComplete(bundle, expectedHeadCount: 146)
        XCTAssertEqual(census.capturedACLRowCount, 1)
        XCTAssertFalse(bundle.nativeStoreContext!.permitsDestinationWrites)
        print("ORIGINAL_5E8_SOURCE_CENSUS snapshots=143 trees=144 heads=146 settings=1 acl=1 default_kv=1 semantic_admission=false")
    }

    func testReal156CensusIncludesEveryOriginalNativeHead() throws {
        let bundle = try original(environment: "PINKHA_NATIVE_CUSTOM_SOURCE_FIXTURE",
            contextSHA: "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a",
            manifestSHA: "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4")
        XCTAssertEqual(bundle.objects.count, 156)
        XCTAssertEqual(bundle.trees.count, 157)
        try requireComplete(bundle, expectedHeadCount: 159)
        XCTAssertThrowsError(try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: bundle)).admittedSchemaItems())
        print("ORIGINAL_REAL156_SOURCE_CENSUS snapshots=156 trees=157 heads=159 settings=1 acl=1 default_kv=1 semantic_admission=false")
    }

    func testOriginalWitnessRefusesOmittedRetainedTreeOrRelabeledACLAndKV() throws {
        let bundle = try original()
        let rows = try originalRows()
        let original = bundle.rawManifest
        var omittedTrees = try XCTUnwrap(original["Trees"]?.array)
        let settings = try XCTUnwrap(omittedTrees.firstIndex { $0["Status"] == .string("space-settings-retained") })
        omittedTrees.remove(at: settings)
        var omitted = replacing(original, ["Trees"], .array(omittedTrees))
        omitted = replacing(omitted, ["Receipt", "Inventory", "Trees"], .integer(Int64(omittedTrees.count)))
        let mutations = [
            omitted,
            replacing(original, ["Receipt", "Inventory", "KeyValueStores"], .integer(0)),
            replacing(original, ["Receipt", "Source", "source", "aclIdSHA256"], .string(hash(Data("another-acl".utf8)))),
            replacing(original, ["Receipt", "Inventory", "AllHeadRowsAccounted"], .bool(false))
        ]
        for manifest in mutations {
            XCTAssertThrowsError(try AnyHeartNativeStoreContext(sourceAccountID: bundle.sourceAccountID,
                sourceSpaceID: bundle.sourceSpaceID, manifest: manifest,
                manifestSHA256: hash(try encoded(manifest)), sourceRows: rows))
        }
    }

    func testRetainedSystemCoverageRequiresOriginalNativeKindIdentityAndRows() throws {
        let bundle = try original()
        let census = try XCTUnwrap(bundle.nativeStoreContext?.headCensus)
        let source = try AnyDestinationSourceBinding(bundle: bundle, semanticPlanSHA256: hash(Data("semantic-control".utf8)))
        let kv = try XCTUnwrap(census.defaultKeyValueID)
        let ordinary = try XCTUnwrap(bundle.objects.first?.sourceObjectID)
        XCTAssertNoThrow(try AnyDestinationSystemCoverageChecks.require(source: source,
            sourceID: census.nativeACLID, kind: .nativeACL, capturedRowCount: census.capturedACLRowCount))
        XCTAssertNoThrow(try AnyDestinationSystemCoverageChecks.require(source: source,
            sourceID: kv, kind: .emptyNativeKeyValue, capturedRowCount: 0))
        for (id, kind, count) in [
            (ordinary, AnyDestinationCoverage.SystemKind.nativeACL, census.capturedACLRowCount),
            (ordinary, .emptyNativeKeyValue, 0),
            (census.nativeACLID, .emptyNativeKeyValue, 0),
            (kv, .nativeACL, 1),
            (census.nativeACLID, .nativeACL, census.capturedACLRowCount + 1),
            (kv, .emptyNativeKeyValue, 1)
        ] {
            XCTAssertThrowsError(try AnyDestinationSystemCoverageChecks.require(source: source,
                sourceID: id, kind: kind, capturedRowCount: count))
        }
        let detached = try AnyDestinationSourceBinding(accountID: source.accountID, spaceID: source.spaceID,
            witnessSHA256: source.witnessSHA256, captureManifestSHA256: source.captureManifestSHA256,
            semanticPlanSHA256: source.semanticPlanSHA256, sourceObjectIDs: source.sourceObjectIDs)
        XCTAssertThrowsError(try AnyDestinationSystemCoverageChecks.require(source: detached,
            sourceID: census.nativeACLID, kind: .nativeACL, capturedRowCount: census.capturedACLRowCount))
    }

    func testPlanConstructionAndDecodingCannotRetainOrdinarySnapshotAsNativeACL() throws {
        let bundle = try original()
        let census = try XCTUnwrap(bundle.nativeStoreContext?.headCensus)
        let page = try XCTUnwrap(bundle.objects.first { $0.nativeType == 16 }?.sourceObjectID)
        let ordinary = try XCTUnwrap(bundle.objects.first { $0.sourceObjectID != page }?.sourceObjectID)
        func plan(_ second: String, count: Int, witness: String) throws -> AnyDestinationMigrationPlan {
            let source = try AnyDestinationSourceBinding(bundle: bundle,
                semanticPlanSHA256: hash(Data("system-coverage-component".utf8)), sourceObjectIDs: [page, second])
            return try .init(source: source, workspace: .init(accountID: "component-destination", spaceID: "component-target"),
                storeID: "component-store", planID: hash(Data("system-coverage-component-plan".utf8)),
                coverage: [
                    .init(sourceObjectID: page, disposition: .mapped(itemSourceKeys: ["page"])),
                    .init(sourceObjectID: second, disposition: .retainedSystem(kind: .nativeACL,
                        capturedRowCount: count, witnessSHA256: witness))
                ], items: [.init(sourceKey: "page", sourceObjectID: page,
                    operation: .object(type: .native("page"), collections: [], initialProperties: .literal(.object([:]))))])
        }
        let original = try plan(census.nativeACLID, count: census.capturedACLRowCount, witness: bundle.sourceWitnessSHA256)
        let bytes = try JSONEncoder().encode(original)
        XCTAssertEqual(try AnyDestinationMigrationPlan.decode(bytes).canonicalBytes, original.canonicalBytes)
        XCTAssertThrowsError(try plan(ordinary, count: census.capturedACLRowCount, witness: bundle.sourceWitnessSHA256))
        XCTAssertThrowsError(try plan(census.nativeACLID, count: census.capturedACLRowCount + 1, witness: bundle.sourceWitnessSHA256))
        XCTAssertThrowsError(try plan(census.nativeACLID, count: census.capturedACLRowCount, witness: hash(Data("foreign".utf8))))
        // The complete source binding still includes the unqualified settings
        // tree. This deliberately scoped component is not a whole-space plan.
        XCTAssertLessThan(original.source.sourceObjectIDs.count, census.sourceHeadIDs.count)
    }

    private func requireComplete(_ bundle: AnyHeartNativeSpaceBundle, expectedHeadCount: Int) throws {
        let census = try XCTUnwrap(bundle.nativeStoreContext?.headCensus)
        var expected = Set(bundle.trees.map { Data($0.objectID.utf8) })
        XCTAssertTrue(expected.insert(Data(census.nativeACLID.utf8)).inserted)
        XCTAssertTrue(expected.insert(Data(try XCTUnwrap(census.defaultKeyValueID).utf8)).inserted)
        XCTAssertEqual(Set(census.sourceHeadIDs.map { Data($0.utf8) }), expected)
        let binding = try AnyDestinationSourceBinding(bundle: bundle, semanticPlanSHA256: hash(Data("complete-source-control".utf8)))
        XCTAssertEqual(binding.sourceObjectIDs.count, expectedHeadCount)
        XCTAssertEqual(Set(binding.sourceObjectIDs.map { Data($0.utf8) }), expected)
        XCTAssertEqual(binding.definitionManifestBytes, bundle.manifestBytes)
        let restored = try JSONDecoder().decode(AnyDestinationSourceBinding.self, from: JSONEncoder().encode(binding))
        XCTAssertEqual(restored, binding)
        for tree in bundle.trees where tree.status == "space-settings-retained" {
            XCTAssertTrue(binding.sourceObjectIDs.contains { Data($0.utf8) == Data(tree.objectID.utf8) })
            XCTAssertFalse(bundle.objects.contains { Data($0.sourceObjectID.utf8) == Data(tree.objectID.utf8) })
        }
    }

    private func original(environment: String = "PINKHA_NATIVE_COMPILED_CAPTURE_FIXTURE",
                          contextSHA: String = "f68679409eaf93676b346eed7e2e9bd31146674956c634081268f36303f527b9",
                          manifestSHA: String = "04b9309e1b96918c47d1b00eed6b1a76b2e13432636a0aba77706f2f69082994") throws -> AnyHeartNativeSpaceBundle {
        let (root, context) = try originalDirectory(environment: environment, contextSHA: contextSHA)
        let manifest = try member("manifest.json", under: root)
        XCTAssertEqual(hash(manifest), manifestSHA)
        return try .init(manifest: manifest, sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try member($0.path, under: root) }
    }
    private func originalRows() throws -> Data {
        let (root, _) = try originalDirectory(environment: "PINKHA_NATIVE_COMPILED_CAPTURE_FIXTURE",
            contextSHA: "f68679409eaf93676b346eed7e2e9bd31146674956c634081268f36303f527b9")
        return try member("native-source-rows.witness", under: root)
    }
    private func originalDirectory(environment: String, contextSHA: String) throws -> (URL, AnyJSON) {
        guard let path = ProcessInfo.processInfo.environment[environment] else {
            throw XCTSkip("Explicit immutable native source required")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).resolvingSymlinksInPath().standardizedFileURL
        let bytes = try member("fixture-context.json", under: root)
        XCTAssertEqual(hash(bytes), contextSHA)
        let context = try JSONDecoder().decode(AnyJSON.self, from: bytes)
        return (root.appendingPathComponent(context["bundleRelativePath"]?.string ?? "bundle", isDirectory: true), context)
    }
    private func member(_ relative: String, under root: URL) throws -> Data {
        let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
        guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
              parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
            throw AnyHeartNativeSpaceBundleError.invalidManifest
        }
        let file = root.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
        guard file.path.hasPrefix(root.path + "/"), try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
            throw AnyHeartNativeSpaceBundleError.invalidMember(relative)
        }
        return try Data(contentsOf: file, options: [.mappedIfSafe])
    }
    private func hash(_ bytes: Data) -> String { AnyContentDigest.sha256(bytes) }
    private func encoded(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    private func replacing(_ value: AnyJSON, _ path: [String], _ replacement: AnyJSON) -> AnyJSON {
        guard let first = path.first else { return replacement }
        var fields = value.object!
        fields[first] = replacing(fields[first]!, Array(path.dropFirst()), replacement)
        return .object(fields)
    }
}
