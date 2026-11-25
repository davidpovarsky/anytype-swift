#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Narrow actual-native persistence for the added default/description adapter.
/// The source is explicitly synthetic component input, never live Heart authority.
final class AnyDestinationNativeDefaultTests: XCTestCase, @unchecked Sendable {
    func testActualNativeDefaultMetadataAndDescriptionColdReopen() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["execute", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the explicit retained real-native controller and phase.")
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
        let journal = work.appendingPathComponent("journal", isDirectory: true)
        let authorization: AnyDestinationAuthorization = {
            let member = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "members", "me"])
            guard member["identity"]?.string == account, member["status"] == .string("active"),
                  ["owner", "writer"].contains(member["permission"]?.string ?? "") else {
                throw DefaultNativeControlFailure.unauthorized
            }
        }
        let capabilities = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace,
                                                                               authorize: authorization)
        let defaultValue = "definition e\u{301} — ברירת מחדל"
        let definition = try Self.componentDefinition(defaultValue: defaultValue)
        let canonical = try Self.componentDescription()
        let nativeCatalog = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", space, "types", "any", "properties"], authorize: authorization)
        try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(nativeCatalog, bindings: [canonical])
        let field = try XCTUnwrap(definition.property(sourceKey: "componentDefault"))
        let ownerKey = try XCTUnwrap(definition.catalogSourceKey)
        let plan: AnyDestinationMigrationPlan
        if phase == "execute", !FileManager.default.fileExists(atPath: planURL.path) {
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
            var items = definition.schemaItems
            for (key, value, description) in [
                ("absent", Optional<AnyJSON>.none, Optional<AnyJSON>.none),
                ("empty", .some(.string("")), .some(.string(""))),
                ("explicit", .some(.string("explicit e\u{301}")), .some(.string("תיאור e\u{301}\nsecond line")))] {
                var any: [AnyDestinationField] = [.init(key: .native("name"), value: .literal(.string(key)))]
                if let description { any.append(.init(key: .native("description"), value: .literal(description))) }
                var groups: [AnyDestinationField] = [.init(key: .native("any"), value: .object(any))]
                if let value {
                    groups.append(.init(key: field.owner, value: .object([.init(key: field.record, value: .literal(value))])))
                }
                items.append(.init(sourceKey: key, sourceObjectID: key,
                    operation: .object(type: .native("page"), collections: [field.owner], initialProperties: .object(groups))))
            }
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let input = try encoder.encode(items)
            try input.write(to: inputURL, options: .withoutOverwriting)
            let digest = AnyContentDigest.sha256(input)
            let sourceIDs = Array(Set(items.map(\.sourceObjectID))).sorted()
            let source = try AnyDestinationSourceBinding(accountID: "explicit-component-default-input",
                spaceID: "explicit-component-default-input", witnessSHA256: digest, captureManifestSHA256: digest,
                semanticPlanSHA256: digest, sourceObjectIDs: sourceIDs)
            plan = try AnyDestinationMigrationPlan(source: source, workspace: workspace,
                storeID: capabilities.capabilities.storeID, planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                coverage: sourceIDs.map { id in
                    .init(sourceObjectID: id, disposition: .mapped(itemSourceKeys: items.filter { $0.sourceObjectID == id }.map(\.sourceKey)))
                }, items: items)
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else { plan = try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL)) }
        let source = plan.source
        let sourceCheck: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { current in
            guard current == source, AnyContentDigest.sha256(try Data(contentsOf: inputURL)) == source.captureManifestSHA256 else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
        let progress = try await AnyDestinationMigrationExecutor(client: client, journalDirectory: journal)
            .execute(plan: plan, payloads: { _ in throw DefaultNativeControlFailure.unexpectedPayload },
                     verifySource: sourceCheck, authorize: authorization)
        XCTAssertTrue(progress.allItemsReconciled); XCTAssertEqual(progress.mappings.count, 5)
        let verified = try await AnyDestinationMigrationVerifier(client: client)
            .verify(plan: plan, progress: progress, verifySource: sourceCheck, authorize: authorization)
        XCTAssertEqual(verified.observations.count, 5)
        let ownerID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == ownerKey }).objectID
        let propertyID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == field.sourceKey }?.recordIDs.first)
        let properties = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", space, "collections", ownerID, "properties"], authorize: authorization)
        let actualProperty = try XCTUnwrap(properties["properties"]?.array?.first { $0["id"]?.string == propertyID })
        let metadata = try XCTUnwrap(AnyNativePropertyDefinition(ownerID: ownerID, raw: actualProperty).importedDefaultMetadata)
        XCTAssertEqual(Data(try XCTUnwrap(metadata.value.string).utf8), Data(defaultValue.utf8))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
        try encoder.encode(verified).write(to: work.appendingPathComponent(phase + "-verification.json"), options: .withoutOverwriting)
        try encoder.encode(actualProperty).write(to: work.appendingPathComponent(phase + "-property.json"), options: .withoutOverwriting)
    }

    private static func componentDefinition(defaultValue: String) throws -> AnyHeartNativeDefinitionPlan {
        let row = try componentRow(id: "component-default", key: "componentDefault", format: 0,
            name: "Component default", description: "Explicit immutable component input",
            defaultValue: .string(defaultValue))
        let digest = AnyContentDigest.sha256(row.jsonViewBytes)
        let catalog = try AnyHeartNativeDefinitionCatalog(sourceAccountID: "explicit-component-input",
            sourceSpaceID: "component-space", captureManifestSHA256: digest,
            sourceWitnessSHA256: digest, snapshots: [row])
        XCTAssertFalse(catalog.permitsDestinationWrites)
        let plan = try AnyHeartNativeDefinitionPlan(catalog: catalog)
        XCTAssertTrue(plan.issues.isEmpty)
        _ = try plan.admittedSchemaItems()
        return plan
    }
    private static func componentDescription() throws -> AnyDestinationCanonicalPropertyBinding {
        try .init(evidence: .init(snapshot: componentRow(id: "component-description", key: "description", format: 0,
            name: "Description", description: "", defaultValue: .null)))
    }
    private static func componentRow(id: String, key: String, format: Int64, name: String,
                                     description: String, defaultValue: AnyJSON) throws -> AnyHeartNativeSnapshotView {
        let marker = Data(("explicit-synthetic-wire-control-not-native-authority:" + id).utf8)
        let details: AnyJSON = .object(["name": .string(name), "description": .string(description),
            "relationKey": .string(key), "relationFormat": .integer(format), "relationDefaultValue": defaultValue,
            "relationMaxCount": .integer(1), "relationReadonlyValue": .bool(false),
            "relationFormatIncludeTime": .bool(false), "relationFormatObjectTypes": .array([])])
        let view: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string("component-space"), "ObjectID": .string(id), "NativeType": .integer(521),
            "UniqueKey": .string("rel-" + key), "SnapshotSHA256": .string(AnyContentDigest.sha256(marker)),
            "SnapshotBytes": .integer(Int64(marker.count)),
            "Snapshot": .object(["blocks": .array([]), "details": details, "objectTypes": .array([]), "relationLinks": .array([])])])
        return try .init(jsonView: JSONEncoder().encode(view), snapshotBytes: marker,
                         sourceSpaceID: "component-space", sourceObjectID: id)
    }
}
private enum DefaultNativeControlFailure: Error { case unauthorized, unexpectedPayload }
#endif
