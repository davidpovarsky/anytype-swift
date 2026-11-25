#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Actual native file-property storage/index/cold-readback. The immutable input
/// is explicitly synthetic component data, never live Heart source authority.
final class AnyDestinationNativeFileReferenceTests: XCTestCase, @unchecked Sendable {
    func testActualNativeFilePropertyLinksAndColdReadback() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["execute", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the explicit retained native controller and phase.")
        }
        let fixture = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        let account = try XCTUnwrap(fixture["accountID"]?.string), space = try XCTUnwrap(fixture["spaceID"]?.string)
        XCTAssertEqual(fixture["binarySHA256"]?.string,
            "bc73441d05a502e3e77df479f54279540489869b00ca1aecf4e1e9f681fa0f49")
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(fixture["baseURL"]?.string))),
                                      expectedAccountID: account)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let planURL = work.appendingPathComponent("plan.json"), inputURL = work.appendingPathComponent("component-input.json")
        let payloadURL = work.appendingPathComponent("full-input"), journal = work.appendingPathComponent("journal")
        let authorization: AnyDestinationAuthorization = {
            let member = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "members", "me"])
            guard member["identity"]?.string == account, member["status"] == .string("active"),
                  ["owner", "writer"].contains(member["permission"]?.string ?? "") else {
                throw NativeFileReferenceControlFailure.unauthorized
            }
        }
        let capability = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace,
                                                                              authorize: authorization)
        let payload = Data((0..<4_097).map { UInt8($0 % 251) })
        let (definition, file, values) = try Self.component(payload: payload)
        let field = try XCTUnwrap(definition.property(sourceKey: "componentFiles"))
        let plan: AnyDestinationMigrationPlan
        if phase == "execute", !FileManager.default.fileExists(atPath: planURL.path) {
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
            try payload.write(to: payloadURL, options: .withoutOverwriting)
            var items = definition.schemaItems
            items.append(.init(sourceKey: "page", sourceObjectID: "component-page",
                operation: .object(type: .native("page"), collections: [field.owner],
                    initialProperties: .literal(.object(["any": .object(["name": .string("Native file property — קובץ")])])))))
            items.append(try file.destinationItem(ownerSourceKey: "page"))
            for group in values.deferredGroups {
                items.append(.init(sourceKey: "file-property-value", sourceObjectID: "component-page",
                    operation: .propertyUpdate(object: .mapped(sourceKey: "page", slot: .objectID, encoding: .rawID),
                        owner: group.owner, patch: group.fields)))
            }
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let input = try encoder.encode(items); try input.write(to: inputURL, options: .withoutOverwriting)
            let digest = AnyContentDigest.sha256(input), sourceIDs = Array(Set(items.map(\.sourceObjectID))).sorted()
            let source = try AnyDestinationSourceBinding(accountID: "explicit-component-file-input",
                spaceID: "explicit-component-file-input", witnessSHA256: digest, captureManifestSHA256: digest,
                semanticPlanSHA256: digest, sourceObjectIDs: sourceIDs)
            plan = try AnyDestinationMigrationPlan(source: source, workspace: workspace,
                storeID: capability.capabilities.storeID, planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                coverage: sourceIDs.map { id in .init(sourceObjectID: id,
                    disposition: .mapped(itemSourceKeys: items.filter { $0.sourceObjectID == id }.map(\.sourceKey))) },
                items: items)
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else { plan = try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL)) }
        let source = plan.source
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { candidate in
            guard candidate == source, AnyContentDigest.sha256(try Data(contentsOf: inputURL)) == source.captureManifestSHA256 else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
        let progress = try await AnyDestinationMigrationExecutor(client: client, journalDirectory: journal)
            .execute(plan: plan, payloads: { key in
                guard phase == "execute", key == file.sourceKey else { throw NativeFileReferenceControlFailure.unexpectedPayload }
                return payloadURL
            }, verifySource: verifySource, authorize: authorization)
        XCTAssertTrue(progress.allItemsReconciled); XCTAssertEqual(progress.mappings.count, 5)
        let verified = try await AnyDestinationMigrationVerifier(client: client)
            .verify(plan: plan, progress: progress, verifySource: verifySource, authorize: authorization)
        XCTAssertEqual(verified.observations.count, 5); XCTAssertEqual(verified.files.count, 1)
        let ownerKey = try XCTUnwrap(definition.catalogSourceKey)
        let owner = try XCTUnwrap(progress.mappings.first { $0.sourceKey == ownerKey }?.objectID)
        let property = try XCTUnwrap(progress.mappings.first { $0.sourceKey == field.sourceKey }?.recordIDs.first)
        let page = try XCTUnwrap(progress.mappings.first { $0.sourceKey == "page" }?.objectID)
        let fileID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == file.sourceKey }?.fileID)
        let expectedURI = "any://f/" + space + "/" + fileID
        let raw = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "objects", page], authorize: authorization)
        let properties = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", space, "collections", owner, "properties"], authorize: authorization)
        let actualProperty = try XCTUnwrap(properties["properties"]?.array?.first { $0["id"]?.string == property })
        let decoded = try AnyNativePropertyDefinition(ownerID: owner, raw: actualProperty)
        let format = try XCTUnwrap(decoded.fileFormat), stored = try XCTUnwrap(raw["record"]?[owner]?[property])
        XCTAssertEqual(stored, .array([.string(expectedURI)]))
        XCTAssertEqual(try format.references(in: stored).map(\.uri), [expectedURI])
        XCTAssertEqual(try format.references(in: stored).first?.spaceID, space)
        XCTAssertEqual(try format.references(in: stored).first?.fileID, fileID)
        let links = try await verifyNativeLinks(client: client, workspace: workspace,
            owner: owner, property: property, page: page, fileID: fileID, uri: expectedURI, authorize: authorization)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
        try encoder.encode(verified).write(to: work.appendingPathComponent(phase + "-verification.json"), options: .withoutOverwriting)
        try encoder.encode(links).write(to: work.appendingPathComponent(phase + "-links.json"), options: .withoutOverwriting)
        try encoder.encode(actualProperty).write(to: work.appendingPathComponent(phase + "-property.json"), options: .withoutOverwriting)
        let mappings = try encoder.encode(progress.mappings)
        if phase == "execute" {
            try mappings.write(to: work.appendingPathComponent("execute-mappings.json"), options: .withoutOverwriting)
        } else {
            XCTAssertEqual(mappings, try Data(contentsOf: work.appendingPathComponent("execute-mappings.json")))
            XCTAssertEqual(try Data(contentsOf: work.appendingPathComponent("execute-verification.json")),
                           try Data(contentsOf: work.appendingPathComponent("reopen-verification.json")))
            XCTAssertEqual(try Data(contentsOf: work.appendingPathComponent("execute-links.json")),
                           try Data(contentsOf: work.appendingPathComponent("reopen-links.json")))
        }
    }

    private func verifyNativeLinks(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
        owner: String, property: String, page: String, fileID: String, uri: String,
        authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        let clock = ContinuousClock(), deadline = ContinuousClock.now + .seconds(30)
        func matches(_ edge: AnyJSON) -> Bool {
            edge["kind"] == .string("relation") && edge["source"]?["spaceId"] == .string(workspace.spaceID) &&
            edge["source"]?["objectId"] == .string(page) && edge["source"]?["dataset"] == .string("prop") &&
            edge["source"]?["typeId"] == .string(owner) && edge["source"]?["recordId"] == .string(property) &&
            edge["target"]?["uri"] == .string(uri) && edge["target"]?["kind"] == .string("f") &&
            edge["target"]?["spaceId"] == .string(workspace.spaceID) && edge["target"]?["fileId"] == .string(fileID) &&
            edge["target"]?["objectId"] == nil
        }
        repeat {
            let forward = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", workspace.spaceID, "objects", page, "links"],
                query: ["kind": "relation", "prop": property, "limit": "2"], authorize: authorize)
            let reverse = try await client.requestJSON(method: "GET", path: ["v1", "backlinks"],
                query: ["target": uri, "kind": "relation", "limit": "2"], authorize: authorize)
            if let edges = forward["links"]?.array, edges.count == 1, matches(edges[0]),
               forward["truncated"]?.bool != true,
               let spaces = reverse["spaces"]?.array, spaces.count == 1,
               spaces[0]["spaceId"] == .string(workspace.spaceID),
               let back = spaces[0]["object"]?.array, back.count == 1, matches(back[0]),
               spaces[0]["parts"]?.array?.isEmpty == true, spaces[0]["truncated"]?.bool != true {
                return .object(["forward": forward, "reverse": reverse])
            }
            try Task.checkCancellation()
            if clock.now < deadline { try await Task.sleep(for: .milliseconds(100)) }
        } while clock.now < deadline
        throw NativeFileReferenceControlFailure.nativeFileIndexMissing
    }

    private static func component(payload: Data) throws ->
        (AnyHeartNativeDefinitionPlan, AnyHeartNativeFileBinding, AnyHeartNativeDefinitionPlan.Values) {
        let details: AnyJSON = .object(["name": .string("Files"), "description": .string("Explicit component input"),
            "relationKey": .string("componentFiles"), "relationFormat": .integer(5),
            "relationDefaultValue": .null, "relationMaxCount": .integer(1),
            "relationReadonlyValue": .bool(false), "relationFormatIncludeTime": .bool(false),
            "relationFormatObjectTypes": .array([])])
        let row = try componentRow(id: "component-file-definition", nativeType: 521, uniqueKey: "rel-componentFiles", details: details)
        let digest = AnyContentDigest.sha256(row.jsonViewBytes)
        let catalog = try AnyHeartNativeDefinitionCatalog(sourceAccountID: "explicit-component-input",
            sourceSpaceID: "component-file-property-source-space-v1", captureManifestSHA256: digest, sourceWitnessSHA256: digest, snapshots: [row])
        let definition = try AnyHeartNativeDefinitionPlan(catalog: catalog)
        XCTAssertTrue(definition.issues.isEmpty); XCTAssertFalse(definition.permitsDestinationWrites)
        _ = try definition.admittedSchemaItems()
        let file = AnyHeartNativeFileBinding(sourceAccountID: catalog.sourceAccountID, sourceSpaceID: catalog.sourceSpaceID,
            captureManifestSHA256: catalog.captureManifestSHA256, sourceWitnessSHA256: catalog.sourceWitnessSHA256,
            fileID: "component-file", variantPath: "original", payloadPath: "full-input",
            payloadSHA256: AnyContentDigest.sha256(payload), size: Int64(payload.count),
            name: "original-file.bin", mimeType: "application/octet-stream")
        let page = try componentRow(id: "component-page", nativeType: 16, uniqueKey: "",
                                    details: .object(["componentFiles": .array([.string(file.fileID)])]))
        let values = try definition.values(snapshot: page, relationKeys: ["componentFiles"], objects: [], files: [file])
        XCTAssertTrue(values.initialGroups.isEmpty); XCTAssertEqual(values.deferredGroups.count, 1)
        return (definition, file, values)
    }
    private static func componentRow(id: String, nativeType: Int64, uniqueKey: String,
                                      details: AnyJSON) throws -> AnyHeartNativeSnapshotView {
        let marker = Data(("explicit-synthetic-wire-control-not-native-authority:" + id).utf8)
        let view: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string("component-file-property-source-space-v1"), "ObjectID": .string(id), "NativeType": .integer(nativeType),
            "UniqueKey": .string(uniqueKey), "SnapshotSHA256": .string(AnyContentDigest.sha256(marker)),
            "SnapshotBytes": .integer(Int64(marker.count)),
            "Snapshot": .object(["blocks": .array([]), "details": details, "objectTypes": .array([]), "relationLinks": .array([])])])
        return try .init(jsonView: JSONEncoder().encode(view), snapshotBytes: marker,
                         sourceSpaceID: "component-file-property-source-space-v1", sourceObjectID: id)
    }
}
private enum NativeFileReferenceControlFailure: Error { case unauthorized, unexpectedPayload, nativeFileIndexMissing }
#endif
