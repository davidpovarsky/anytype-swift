import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePageCompositionTests: XCTestCase {
    func testPageCompositionKeepsOneTitleAndDefersExactReferenceCycles() throws {
        let definitions = try syntheticDefinitions()
        XCTAssertTrue(definitions.issues.isEmpty)
        XCTAssertFalse(try definitions.admittedSchemaItems().isEmpty)
        let pages = try [page("first", other: "second"), page("second", other: "first")]
        let objects = bindings(pages)
        let first = try AnyHeartNativePageComposition(snapshot: pages[0], definitions: definitions, objects: objects)
        let second = try AnyHeartNativePageComposition(snapshot: pages[1], definitions: definitions, objects: objects)
        XCTAssertEqual(pages.map(\.uniqueKey), ["page", "page"])
        XCTAssertNotEqual(first.sourceKey, second.sourceKey)
        XCTAssertEqual(first.items.count, 3)
        XCTAssertEqual(first.body.entries.count, 1)
        XCTAssertEqual(first.body.entries[0].text, "גוף first — a\u{301}")
        XCTAssertEqual(first.presentDetailKeys.count, 5)
        let initial = try first.values.initialProperties.resolved(resolve)
        XCTAssertEqual(initial["any"]?["name"], .string("כותרת first"))
        let owner = try XCTUnwrap(definitions.propertyOwner)
        let namespace = try resolve(owner)
        let done = try XCTUnwrap(definitions.property(sourceKey: "done"))
        let count = try XCTUnwrap(definitions.property(sourceKey: "count"))
        let empty = try XCTUnwrap(definitions.property(sourceKey: "empty"))
        let ref = try XCTUnwrap(definitions.property(sourceKey: "other"))
        XCTAssertEqual(initial[namespace]?[try resolve(done.record)], .bool(false))
        XCTAssertEqual(initial[namespace]?[try resolve(count.record)], .integer(0))
        XCTAssertEqual(initial[namespace]?[try resolve(empty.record)], .string(""))
        XCTAssertNil(initial[namespace]?[try resolve(ref.record)])
        XCTAssertNil(initial[namespace]?["name"])
        XCTAssertEqual(first.values.deferredGroups.count, 1)
        let patch = try first.values.deferredGroups[0].fields.resolved(resolve)
        XCTAssertEqual(patch[try resolve(ref.record)], .array([.string("any://" + second.sourceKey)]))
        let reverse = try second.values.deferredGroups[0].fields.resolved(resolve)
        XCTAssertEqual(reverse[try resolve(ref.record)], .array([.string("any://" + first.sourceKey)]))
        guard case .object(_, let attached, _) = first.items[0].operation else { return XCTFail("Expected creation first") }
        XCTAssertEqual(attached, [owner])
        guard case .propertyUpdate(let object, let groupOwner, _) = first.items.last?.operation else {
            return XCTFail("Reference cycles must use a later owner-group SET")
        }
        XCTAssertEqual(object, .mapped(sourceKey: first.sourceKey, slot: .objectID, encoding: .rawID))
        XCTAssertEqual(groupOwner, owner)
        XCTAssertThrowsError(try first.admittedCurrentItems(), "Detached semantic controls grant no source admission")
        XCTAssertFalse(first.permitsDestinationWrites)
        let repeated = try AnyHeartNativePageComposition(snapshot: pages[0], definitions: definitions, objects: objects)
        XCTAssertEqual(repeated.contentSHA256, first.contentSHA256)
    }

    func testUnaccountedDetailsSourceMetadataAndAmbiguousIdentitiesAreRefused() throws {
        let definitions = try syntheticDefinitions()
        let other = try page("second", other: "first")
        let mutations: [(inout [String: AnyJSON], inout [String: AnyJSON]) -> Void] = [
            { details, _ in details["unknown"] = .array([]) },
            { details, _ in _ = details.removeValue(forKey: "name") },
            { details, _ in details["featuredRelations"] = .array([]) },
            { _, raw in raw["fileInfo"] = .object(["retained": .bool(true)]) },
            { _, raw in raw["originalCreatedTimestamp"] = .string("123") },
            { _, raw in raw["objectTypes"] = .array([.string("ot-owned"), .string("ot-other")]) },
            { _, raw in raw["relationLinks"] = .array([.object(["key": .string("name"), "format": .integer(2)])]) },
            { _, raw in raw["relationLinks"] = .array(Array(repeating: .object(["key": .string("name"), "format": .integer(1)]), count: 2)) }
        ]
        for mutate in mutations {
            let candidate = try page("first", other: "second", mutate: mutate)
            XCTAssertThrowsError(try AnyHeartNativePageComposition(snapshot: candidate, definitions: definitions,
                                                                  objects: bindings([candidate, other])))
        }
        let candidate = try page("first", other: "second")
        var aliases = bindings([candidate, other])
        aliases[1] = .init(sourceObjectID: other.sourceObjectID, destinationSourceKey: aliases[0].destinationSourceKey)
        XCTAssertThrowsError(try AnyHeartNativePageComposition(snapshot: candidate, definitions: definitions, objects: aliases))
        let unsupported = try syntheticDefinitions(layout: 1)
        XCTAssertThrowsError(try unsupported.admittedSchemaItems())
        XCTAssertThrowsError(try AnyHeartNativePageComposition(snapshot: candidate, definitions: unsupported,
                                                              objects: bindings([candidate, other])))
    }

    func testOriginalCapturedPageComposesCurrentStateAndRetainsSourceBlockers() throws {
        let bundle = try fixture("PINKHA_NATIVE_SOURCE_FIXTURE",
            contextSHA: "5357d52f5e76b604a40d7a5f2b1bc002e19bc864c419a45f90128bfa965d5850",
            manifestSHA: "2a1a02987204321aaa1c8cf9f0c7f413f4b50dbce87280d82499c4f9bc7be238")
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: bundle))
        let pages = bundle.objects.filter { $0.nativeType == 16 }
        XCTAssertEqual(pages.count, 1)
        let original = try XCTUnwrap(pages.first)
        let plan = try AnyHeartNativePageComposition(bundle: bundle, sourceObjectID: original.sourceObjectID,
                                                    definitions: definitions, objects: bindings(pages))
        XCTAssertEqual(plan.items.count, 2)
        XCTAssertEqual(plan.presentDetailKeys, ["name"])
        XCTAssertTrue(plan.layout.title == original.details["name"]?.string, "Original title bytes changed")
        XCTAssertEqual(plan.body.entries.count, 1)
        XCTAssertFalse(plan.definitionIssues.isEmpty)
        XCTAssertFalse(plan.sourceIssues.isEmpty)
        XCTAssertThrowsError(try plan.admittedCurrentItems())
        XCTAssertFalse(plan.permitsDestinationWrites)
        XCTAssertThrowsError(try AnyHeartNativePageComposition(bundle: bundle, sourceObjectID: original.sourceObjectID,
                                                              definitions: syntheticDefinitions(), objects: bindings(pages)))
        let unsupported = try XCTUnwrap(bundle.objects.first { $0.nativeType != 16 })
        for id in ["foreign-source-identity", unsupported.sourceObjectID] {
            var invalid = bindings(pages)
            invalid.append(.init(sourceObjectID: id,
                destinationSourceKey: AnyHeartNativePageComposition.objectSourceKey(spaceID: bundle.sourceSpaceID, objectID: id)))
            XCTAssertThrowsError(try AnyHeartNativePageComposition(bundle: bundle, sourceObjectID: original.sourceObjectID,
                                                                  definitions: definitions, objects: invalid))
        }
        print("NATIVE_PAGE_COMPOSITION originalPages=1 objects=144 currentItems=2 originalSchemaAndSourceBlockersRetained=true destinationWrites=false digest=\(plan.contentSHA256)")
    }

    func testOriginalCustomCapturePreservesBothPagesAllValuesAndDistinctIdentities() throws {
        let bundle = try fixture("PINKHA_NATIVE_CUSTOM_SOURCE_FIXTURE",
            contextSHA: "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a",
            manifestSHA: "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4")
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: bundle))
        XCTAssertEqual(bundle.objects.count, 156)
        XCTAssertTrue(bundle.resolverUnmapped.isEmpty)
        let pages = bundle.objects.filter { $0.nativeType == 16 }
        XCTAssertEqual(pages.count, 2)
        XCTAssertEqual(Set(pages.map(\.uniqueKey)), ["page"])
        let objects = bindings(pages)
        var keys = Set<String>()
        for original in pages {
            let plan = try AnyHeartNativePageComposition(bundle: bundle, sourceObjectID: original.sourceObjectID,
                                                        definitions: definitions, objects: objects)
            XCTAssertTrue(keys.insert(plan.sourceKey).inserted)
            XCTAssertEqual(plan.presentDetailKeys.count, 8)
            XCTAssertTrue(Set(plan.presentDetailKeys) == Set(original.details.keys), "Some present detail was not consumed")
            XCTAssertTrue(plan.layout.title == original.details["name"]?.string, "Original custom title changed")
            XCTAssertEqual(plan.body.entries.count, 1)
            XCTAssertEqual(plan.values.initialRelationKeys.count, 7)
            XCTAssertEqual(plan.values.deferredRelationKeys.count, 1)
            XCTAssertEqual(plan.items.count, 3)
            XCTAssertFalse(plan.definitionIssues.isEmpty, "Unimplemented built-in schema must not disappear")
            XCTAssertThrowsError(try plan.admittedCurrentItems())
            XCTAssertFalse(plan.permitsDestinationWrites)
        }
        XCTAssertEqual(keys.count, 2)
        print("NATIVE_CUSTOM_PAGE_COMPOSITION pages=2 details=16 bodyBlocks=2 distinctObjectIdentities=true completeCaptureObjects=156 originalCustomAcceptanceFailureRetained=true destinationWrites=false")
    }

    private func resolve(_ reference: AnyDestinationReference) throws -> String {
        switch reference {
        case .native(let id): return id
        case .mapped(let key, _, let encoding): return encoding == .anyURI ? "any://" + key : key
        }
    }
    private func bindings(_ pages: [AnyHeartNativeSnapshotView]) -> [AnyHeartNativeDefinitionPlan.ObjectBinding] {
        pages.map { .init(sourceObjectID: $0.sourceObjectID,
                         destinationSourceKey: AnyHeartNativePageComposition.objectSourceKey(spaceID: $0.sourceSpaceID, objectID: $0.sourceObjectID)) }
    }
    private func syntheticDefinitions(layout: Int64 = 0) throws -> AnyHeartNativeDefinitionPlan {
        var rows: [AnyHeartNativeSnapshotView] = []
        let relations: [(String, Int64)] = [("name", 1), ("done", 6), ("count", 2), ("empty", 0), ("other", 100)]
        for (key, format) in relations {
            rows.append(try snapshot(id: "relation-" + key, type: 521, key: "rel-" + key,
                raw: .object(["blocks": .array([]), "objectTypes": .array([]), "relationLinks": .array([]),
                    "details": .object(["name": .string(key), "description": .string("captured"),
                        "relationKey": .string(key), "relationFormat": .integer(format),
                        "relationDefaultValue": .null, "relationReadonlyValue": .bool(false),
                        "relationMaxCount": .integer(key == "name" ? 1 : 0),
                        "relationFormatIncludeTime": .bool(key != "name"), "relationFormatObjectTypes": .array([]),
                        "isHidden": .bool(key == "name")])])))
        }
        rows.append(try snapshot(id: "owned-type", type: 528, key: "ot-owned",
            raw: .object(["blocks": .array([]), "objectTypes": .array([]), "relationLinks": .array([]),
                "details": .object(["name": .string("Owned"), "recommendedLayout": .integer(layout),
                    "recommendedRelations": .array([.string("relation-name"), .string("relation-done")]),
                    "recommendedFeaturedRelations": .array([.string("relation-name")]),
                    "recommendedHiddenRelations": .array([]), "recommendedFileRelations": .array([])])])))
        return try .init(catalog: .init(sourceAccountID: "source-account", sourceSpaceID: "source-space",
            captureManifestSHA256: String(repeating: "a", count: 64),
            sourceWitnessSHA256: String(repeating: "b", count: 64), snapshots: rows))
    }

    private func page(_ id: String, other: String,
                      mutate: (inout [String: AnyJSON], inout [String: AnyJSON]) -> Void = { _, _ in }) throws -> AnyHeartNativeSnapshotView {
        func block(_ suffix: String, children: [String] = [], kind: String, value: AnyJSON,
                   restrictions: [String: Bool]? = nil, fields: AnyJSON = .null) -> AnyJSON {
            .object(["id": .string(suffix.isEmpty ? id : id + suffix),
                "childrenIds": .array(children.map { .string(id + $0) }), "fields": fields,
                "backgroundColor": .string(""), "align": .integer(0), "verticalAlign": .integer(0),
                "restrictions": restrictions.map { .object($0.mapValues(AnyJSON.bool)) } ?? .null, kind: value])
        }
        func text(_ value: String, style: Int64 = 0) -> AnyJSON {
            .object(["text": .string(value), "style": .integer(style), "checked": .bool(false),
                "marks": .object(["marks": .array([])]), "color": .string(""), "iconEmoji": .string(""), "iconImage": .string("")])
        }
        let protected = ["drag": true, "dropOn": true, "edit": false, "read": false, "remove": true]
        let blocks = [
            block("", children: ["-header", "-body"], kind: "smartblock", value: .object([:]),
                  restrictions: ["drag": false, "dropOn": false, "edit": false, "read": false, "remove": false]),
            block("-header", children: ["-title", "-featured"], kind: "layout", value: .object(["style": .integer(3)]),
                  restrictions: ["drag": true, "dropOn": true, "edit": true, "read": false, "remove": true]),
            block("-title", kind: "text", value: text("", style: 7), restrictions: protected,
                  fields: .object(["_detailsKey": .array([.string("name"), .string("done")])])),
            block("-featured", kind: "featuredRelations", value: .object([:]), restrictions: protected),
            block("-body", kind: "text", value: text("גוף \(id) — a\u{301}"))
        ]
        var details: [String: AnyJSON] = ["name": .string("כותרת \(id)"), "done": .bool(false),
            "count": .integer(0), "empty": .string(""), "other": .array([.string(other)])]
        var raw: [String: AnyJSON] = ["blocks": .array(blocks), "objectTypes": .array([.string("ot-owned")]),
            "relationLinks": .array([.object(["key": .string("name"), "format": .integer(1)])]),
            "key": .string(""), "originalCreatedTimestamp": .string("0")]
        mutate(&details, &raw); raw["details"] = .object(details)
        return try snapshot(id: id, type: 16, key: "page", raw: .object(raw))
    }
    private func snapshot(id: String, type: Int64, key: String, raw: AnyJSON) throws -> AnyHeartNativeSnapshotView {
        let pb = Data("synthetic-page-composition-control:\(id)".utf8)
        let envelope: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string("source-space"), "ObjectID": .string(id), "NativeType": .integer(type),
            "UniqueKey": .string(key), "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)),
            "SnapshotBytes": .integer(Int64(pb.count)), "Snapshot": raw])
        return try .init(jsonView: JSONEncoder().encode(envelope), snapshotBytes: pb,
                         sourceSpaceID: "source-space", sourceObjectID: id)
    }
    private func fixture(_ environment: String, contextSHA: String, manifestSHA: String) throws -> AnyHeartNativeSpaceBundle {
        guard let path = ProcessInfo.processInfo.environment[environment] else {
            throw XCTSkip("Explicit immutable original capture required")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
                  parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw AnyHeartNativePageCompositionError.sourceBinding
            }
            let file = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
            guard file.path.hasPrefix(directory.path + "/"),
                  try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
                throw AnyHeartNativePageCompositionError.sourceBinding
            }
            return try Data(contentsOf: file, options: [.mappedIfSafe])
        }
        let contextBytes = try bytes("fixture-context.json", under: root)
        guard AnyContentDigest.sha256(contextBytes) == contextSHA else { throw AnyHeartNativePageCompositionError.sourceBinding }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        let directory = root.appendingPathComponent(try XCTUnwrap(context["bundleRelativePath"]?.string), isDirectory: true)
        let manifest = try bytes("manifest.json", under: directory)
        guard AnyContentDigest.sha256(manifest) == manifestSHA else { throw AnyHeartNativePageCompositionError.sourceBinding }
        return try .init(manifest: manifest, sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
                        sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try bytes($0.path, under: directory) }
    }
}
