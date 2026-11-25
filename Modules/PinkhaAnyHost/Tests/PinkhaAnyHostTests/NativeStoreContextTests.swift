import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativeStoreContextTests: XCTestCase {
    func testOnlyExactNativeLifecycleAndDerivedEmptyStoreAreClassified() throws {
        for flag in [false, true] {
            let input = try fixture(client: client(flag))
            let context = try parse(input)
            XCTAssertEqual(context.classifiedCollections.map(\.kind), [.clientSpaceLifecycle, .emptyDefaultKeyValue])
            XCTAssertEqual(context.classification(named: "_client")?.sourceSpaceCreated, flag)
            XCTAssertEqual(context.classification(named: "_client")?.sourceRowSHA256, hash(client(flag)))
            XCTAssertTrue(context.unmappedCollectionNames.isEmpty)
            XCTAssertFalse(context.permitsDestinationWrites)
            XCTAssertEqual(context.sourceWitnessSHA256, hash(input.rows))
        }
    }

    func testForeignEmptyAndNonemptyNativeCollectionsStayUnmapped() throws {
        var nonBoolean = Data([7])
        nonBoolean.append(Data("id".utf8)); nonBoolean.append(contentsOf: [0, 3])
        nonBoolean.append(Data("space".utf8)); nonBoolean.append(0)
        nonBoolean.append(Data("created".utf8)); nonBoolean.append(contentsOf: [0, 2])
        nonBoolean.append(Data(repeating: 0, count: 9))
        let inputs: [Input] = [
            try fixture(extra: ["foreign-empty": []]),
            try fixture(keyValueRows: [(Data([3, 107, 0]), Data([7, 0]))]),
            try fixture(client: client(false) + Data([0])),
            try fixture(client: nonBoolean),
        ]
        for input in inputs {
            let context = try parse(input)
            XCTAssertFalse(context.unmappedCollectionNames.isEmpty)
            XCTAssertFalse(context.permitsDestinationWrites)
        }
        let nonempty = try parse(inputs[1])
        XCTAssertEqual(nonempty.classifiedCollections.map(\.kind), [.clientSpaceLifecycle])
        XCTAssertEqual(nonempty.unmappedCollectionNames, [try AnyHeartNativeStoreContext.defaultKeyValueCollectionID(spaceID: space)])
    }

    func testWitnessFramingIdentityCountsAndTrailingBytesCannotBeRelabeled() throws {
        let original = try fixture()
        for bytes in [Data(original.rows.dropLast()), original.rows + Data([0]),
                      Data(repeating: 0xff, count: 8) + original.rows.dropFirst(8)] {
            var input = original; input.rows = bytes
            input.manifest = replacing(input.manifest, ["SourceRows", "SHA256"], .string(hash(bytes)))
            input.manifest = replacing(input.manifest, ["SourceRows", "Bytes"], .integer(Int64(bytes.count)))
            input.manifest = replacing(input.manifest, ["Receipt", "Source", "source", "native", "WitnessSHA256"], .string(hash(bytes)))
            input.manifest = replacing(input.manifest, ["Receipt", "Inventory", "SourceWitnessSHA256"], .string(hash(bytes)))
            XCTAssertThrowsError(try parse(input))
        }
        for path in [
            ["Receipt", "Source", "source", "native", "Generation"],
            ["Receipt", "Source", "source", "native", "Rows"],
            ["Receipt", "Inventory", "OtherCollectionRows"]
        ] {
            var input = original; input.manifest = replacing(input.manifest, path, .integer(99))
            XCTAssertThrowsError(try parse(input))
        }
        var wrongOwner = original
        wrongOwner.manifest = replacing(wrongOwner.manifest,
            ["Receipt", "Source", "source", "native", "OwnerSHA256"], .string(String(repeating: "0", count: 64)))
        XCTAssertThrowsError(try parse(wrongOwner))
        var omitted = original
        omitted.manifest = replacing(omitted.manifest, ["RetainedOtherCollections"], .array([]))
        omitted.manifest = replacing(omitted.manifest, ["Receipt", "Inventory", "OtherCollections"], .integer(0))
        omitted.manifest = replacing(omitted.manifest, ["Receipt", "Inventory", "OtherCollectionRows"], .integer(0))
        XCTAssertThrowsError(try parse(omitted))
        XCTAssertThrowsError(try AnyHeartNativeStoreContext(sourceAccountID: account, sourceSpaceID: "foreign",
            manifest: original.manifest, manifestSHA256: hash(try encoded(original.manifest)), sourceRows: original.rows))
    }

    func testNativeCIDUsesOriginalSpaceBytesAndSupportsNonzeroDataIndices() throws {
        let original = try fixture()
        let id = try AnyHeartNativeStoreContext.defaultKeyValueCollectionID(spaceID: space)
        XCTAssertEqual(id, "bafyreihex6v2k6fbrtqv3nx35okzensur565vccrpvidzeags6zx5g2k2e")
        XCTAssertNotEqual(id, try AnyHeartNativeStoreContext.defaultKeyValueCollectionID(spaceID: space + "x"))
        var sliced = original
        let padded = Data([99]) + original.rows
        sliced.rows = padded.dropFirst()
        XCTAssertEqual(try parse(sliced).sourceWitnessSHA256, hash(original.rows))
    }

    func testOriginalReal156ClassifiesOnlyNativeStoreContextAndRetainsSemanticBlockers() throws {
        let bundle = try originalBundle(environment: "PINKHA_NATIVE_CUSTOM_SOURCE_FIXTURE",
            contextSHA: "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a",
            manifestSHA: "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4")
        XCTAssertEqual(bundle.objects.count, 156)
        let context = try XCTUnwrap(bundle.nativeStoreContext)
        XCTAssertEqual(context.classifiedCollections.map(\.kind), [.clientSpaceLifecycle, .emptyDefaultKeyValue])
        XCTAssertEqual(context.classification(named: "_client")?.sourceSpaceCreated, false)
        XCTAssertEqual(context.classification(named: "_client")?.sourceRowSHA256,
                       "646cfb00a89f7ea887ed855eda75e6c943ffe34647032d3eb4fba2a545727d38")
        XCTAssertTrue(context.unmappedCollectionNames.isEmpty)
        XCTAssertFalse(context.permitsDestinationWrites)
        XCTAssertFalse(bundle.issues.contains { $0.code == "retained-collection-requires-semantic-mapping" })
        XCTAssertTrue(bundle.issues.contains { $0.code == "compiled-definition-descriptors-not-captured" })
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: bundle))
        XCTAssertFalse(definitions.issues.isEmpty)
        XCTAssertThrowsError(try definitions.admittedSchemaItems())
        let pages = bundle.objects.filter { $0.nativeType == 16 }
        let objects = pages.map { AnyHeartNativeDefinitionPlan.ObjectBinding(sourceObjectID: $0.sourceObjectID,
            destinationSourceKey: AnyHeartNativePageComposition.objectSourceKey(spaceID: bundle.sourceSpaceID, objectID: $0.sourceObjectID)) }
        for page in pages {
            let composition = try AnyHeartNativePageComposition(bundle: bundle, sourceObjectID: page.sourceObjectID,
                                                                definitions: definitions, objects: objects)
            XCTAssertFalse(composition.sourceIssues.contains("unmapped-native-collections"))
            XCTAssertTrue(composition.sourceIssues.contains("bundled-definition-fallback"))
            XCTAssertThrowsError(try composition.admittedCurrentItems())
        }
        print("ACTUAL_REAL156_NATIVE_CONTEXT lifecycle_rows=1 original_created=false default_kv_rows=0 full_source_admission=false")
    }

    func testFreshNative5e8CaptureUsesSameClosedContextRules() throws {
        let bundle = try originalBundle(environment: "PINKHA_NATIVE_COMPILED_CAPTURE_FIXTURE",
            contextSHA: "f68679409eaf93676b346eed7e2e9bd31146674956c634081268f36303f527b9",
            manifestSHA: "04b9309e1b96918c47d1b00eed6b1a76b2e13432636a0aba77706f2f69082994")
        XCTAssertEqual(bundle.objects.count, 143)
        let context = try XCTUnwrap(bundle.nativeStoreContext)
        XCTAssertEqual(context.classifiedCollections.map(\.kind), [.clientSpaceLifecycle, .emptyDefaultKeyValue])
        XCTAssertTrue(context.unmappedCollectionNames.isEmpty)
        XCTAssertFalse(context.permitsDestinationWrites)
        XCTAssertEqual(bundle.bundledDefinitions.count, 6)
        XCTAssertFalse(bundle.issues.contains { $0.code == "retained-collection-requires-semantic-mapping" })
        XCTAssertThrowsError(try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: bundle)).admittedSchemaItems())
        print("ACTUAL_NATIVE5E8_CONTEXT snapshots=143 classified_contexts=2 full_source_admission=false")
    }

    private let account = "component-account"
    private let space = "component-source-space"
    private struct Input { var rows: Data; var manifest: AnyJSON }
    private func hash(_ data: Data) -> String { AnyContentDigest.sha256(data) }
    private func encoded(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    private func parse(_ input: Input) throws -> AnyHeartNativeStoreContext {
        try .init(sourceAccountID: account, sourceSpaceID: space, manifest: input.manifest,
                  manifestSHA256: hash(try encoded(input.manifest)), sourceRows: input.rows)
    }
    private func client(_ value: Bool) -> Data {
        Data([7]) + Data("id".utf8) + Data([0, 3]) + Data("space".utf8) + Data([0]) +
            Data("created".utf8) + Data([0, value ? 5 : 4, 0])
    }
    private func fixture(client value: Data? = nil, keyValueRows: [(Data, Data)] = [],
                         extra: [String: [(Data, Data)]] = [:]) throws -> Input {
        let kv = try AnyHeartNativeStoreContext.defaultKeyValueCollectionID(spaceID: space)
        let acl = "component-acl", nonce = Data(repeating: 0xa1, count: 32)
        var collections: [String: [(Data, Data)]] = [
            "_client": [(Data([3]) + Data("space".utf8) + Data([0]), value ?? client(false))],
            kv: keyValueRows, acl: [], "heads": [], "state": [], "changes": []
        ]
        for (key, rows) in extra { collections[key] = rows }
        func number(_ value: Int) -> Data {
            var number = UInt64(value).bigEndian
            return withUnsafeBytes(of: &number) { Data($0) }
        }
        var bytes = Data()
        func frame(_ value: Data) { bytes.append(number(value.count)); bytes.append(value) }
        for value in [Data("pinkha-localstore-witness-v1".utf8),
                      Data("anyenc-v1.0.3-decoded-value-roundtrip-v1".utf8),
                      Data("heart-owned-local-store-v1".utf8), nonce, Data(space.utf8), number(4), number(collections.count)] {
            frame(value)
        }
        var coverage: [AnyJSON] = [], retained: [AnyJSON] = []
        var totalRows = 0, totalBytes = 0, otherRows = 0
        for name in collections.keys.sorted(by: { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }) {
            let rows = collections[name]!.sorted { $0.0.lexicographicallyPrecedes($1.0) }
            frame(Data(name.utf8)); frame(number(rows.count))
            for (id, value) in rows { frame(id); frame(value) }
            let count = rows.reduce(0) { $0 + $1.1.count }
            totalRows += rows.count; totalBytes += count
            coverage.append(.object(["NameSHA256": .string(hash(Data(name.utf8))), "Rows": .integer(Int64(rows.count)),
                "EncodedValueBytes": .integer(Int64(count)), "UnresolvedCollection": .bool(name == kv)]))
            if !["state", "heads", "changes", acl].contains(name) {
                retained.append(.object(["Name": .string(name), "Rows": .integer(Int64(rows.count)), "Bytes": .integer(Int64(count))]))
                otherRows += rows.count
            }
        }
        let native: AnyJSON = .object([
            "Version": .string("native-localstore-witness-v1"), "Encoding": .string("anyenc-v1.0.3-decoded-value-roundtrip-v1"),
            "Authority": .string("heart-owned-local-store-v1"), "SpaceSHA256": .string(hash(Data(space.utf8))),
            "WitnessSHA256": .string(hash(bytes)), "OwnerSHA256": .string(hash(nonce)), "Generation": .integer(4),
            "Collections": .integer(Int64(collections.count)), "Rows": .integer(Int64(totalRows)),
            "EncodedValueBytes": .integer(Int64(totalBytes)), "CollectionCoverage": .array(coverage)])
        let manifest: AnyJSON = .object([
            "Contract": .string("pinkha-native-whole-source-bundle-v1"),
            "SourceRows": .object(["Path": .string("native-source-rows.witness"), "SHA256": .string(hash(bytes)), "Bytes": .integer(Int64(bytes.count))]),
            "RetainedOtherCollections": .array(retained),
            "Receipt": .object([
                "Source": .object(["accountSHA256": .string(hash(Data(account.utf8))),
                    "source": .object(["native": native, "aclIdSHA256": .string(hash(Data(acl.utf8)))])]),
                "Inventory": .object(["SourceWitnessSHA256": .string(hash(bytes)), "Generation": .integer(4),
                    "OtherCollections": .integer(Int64(retained.count)), "OtherCollectionRows": .integer(Int64(otherRows)),
                    "KeyValueStores": .integer(1), "KeyValueRows": .integer(Int64(keyValueRows.count))])
            ])
        ])
        return Input(rows: bytes, manifest: manifest)
    }
    private func replacing(_ value: AnyJSON, _ path: [String], _ replacement: AnyJSON) -> AnyJSON {
        guard let first = path.first else { return replacement }
        var fields = value.object!
        fields[first] = replacing(fields[first]!, Array(path.dropFirst()), replacement)
        return .object(fields)
    }

    private func originalBundle(environment: String, contextSHA: String, manifestSHA: String) throws -> AnyHeartNativeSpaceBundle {
        guard let path = ProcessInfo.processInfo.environment[environment] else {
            throw XCTSkip("Explicit original native capture required.")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
                  parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
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
        guard hash(contextBytes) == contextSHA else { throw AnyHeartNativeSpaceBundleError.invalidManifest }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        let directory = root.appendingPathComponent(context["bundleRelativePath"]?.string ?? "bundle", isDirectory: true)
        let manifest = try bytes("manifest.json", under: directory)
        guard hash(manifest) == manifestSHA else { throw AnyHeartNativeSpaceBundleError.invalidManifest }
        return try .init(manifest: manifest, sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
                         sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try bytes($0.path, under: directory) }
    }
}
