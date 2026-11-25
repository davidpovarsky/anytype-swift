#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Original 156-capture definitions bind this narrow native correspondence.
/// The destination objects are explicit component input. This does not admit
/// the failed original capture, any blocked layout, or a whole-space migration.
final class AnyDestinationNativeIdentityTests: XCTestCase, @unchecked Sendable {
    func testActualCanonicalIdentityDescriptorsAndColdReopen() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let originalPath = env["PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["execute", "reopen"].contains(phase) else {
            throw XCTSkip("Requires exact original source bytes and the retained real-native controller.")
        }
        let fixture = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        try require(fixture["binarySHA256"] == .string("7f9124991e206657f21a9788b58f65de3ec57e019f425772dd4be6b677f803df"))
        try require(fixture["sourceManifestSHA256"] == .string("d33fa2fb166aef89af0047ac23acf5c12fa108baec49566542cccd942a28f460"))
        try require(fixture["phase"] == .string(phase == "execute" ? "execute" : "cold-offline"))
        let account = try XCTUnwrap(fixture["accountID"]?.string)
        let space = try XCTUnwrap(fixture["spaceID"]?.string)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(fixture["baseURL"]?.string))),
                                       expectedAccountID: account)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let authorize: AnyDestinationAuthorization = {
            let member = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "members", "me"])
            guard member["identity"] == .string(account), member["status"] == .string("active"),
                  ["owner", "writer"].contains(member["permission"]?.string ?? "") else {
                throw IdentityNativeControlFailure.unauthorized
            }
        }
        let original = try Self.originalCapture(at: URL(fileURLWithPath: originalPath, isDirectory: true))
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: original)
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog)
        try require(original.objects.count == 156 && catalog.relations.count == 126 &&
                    catalog.types.count == 20 && catalog.options.count == 4)
        try require(!catalog.permitsDestinationWrites && !mapper.permitsDestinationWrites)
        XCTAssertThrowsError(try mapper.admittedSchemaItems())
        let source = try AnyDestinationSourceBinding(bundle: original, semanticPlanSHA256: catalog.contentSHA256,
                                                     sourceObjectIDs: original.objects.map(\.sourceObjectID))
        let roles: [AnyDestinationCanonicalPropertyBinding.IdentityRole] = [.id, .spaceId, .type]
        let bindings = try roles.map { role in
            let property = try XCTUnwrap(mapper.property(sourceKey: role.rawValue))
            let binding = try XCTUnwrap(property.canonicalBinding)
            try require(binding.identityRole == role && property.owner == .native("any") &&
                        property.record == .native(role.rawValue))
            try binding.requireSource(source, objectID: property.relation.objectID)
            return binding
        }
        let originalPages = original.objects.filter { $0.nativeType == 16 }
        try require(originalPages.count == 2)
        // The original source stores these identities in object context, not
        // detail fields. Do not fabricate present id/spaceId/type properties.
        for page in originalPages {
            try require(roles.allSatisfy { page.details[$0.rawValue] == nil })
            try require(page.objectTypes.count == 1 && catalog.type(url: page.objectTypes[0]) != nil)
        }
        let nativeCatalog = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", space, "types", "any", "properties"], authorize: authorize)
        try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(nativeCatalog, bindings: bindings)

        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let planURL = work.appendingPathComponent("plan.json")
        let inputURL = work.appendingPathComponent("component-input.json")
        let journal = work.appendingPathComponent("journal", isDirectory: true)
        let definitions = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace,
                                                                               authorize: authorize)
        let plan: AnyDestinationMigrationPlan
        if phase == "execute" {
            try require(!FileManager.default.fileExists(atPath: planURL.path))
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
            let nonce = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
            let mappedType: AnyDestinationReference = .mapped(sourceKey: "target-type", slot: .objectID, encoding: .rawID)
            let items: [AnyDestinationMigrationItem] = [
                .init(sourceKey: "target-type", sourceObjectID: "component-type",
                      operation: .typeDefinition(.init(xKey: "canonical_identity_" + nonce,
                        name: "Explicit canonical identity component",
                        description: "Original descriptors; independently allocated native target identities",
                        layout: .literal(.object(["type": .string("page")])),
                        meta: .literal(.object(["sourceScope": .string("component-only")]))))),
                .init(sourceKey: "first", sourceObjectID: "component-first",
                      operation: .object(type: mappedType, collections: [],
                        initialProperties: .literal(.object(["any": .object(["name": .string("Identity first — זהות e\u{301}")])])))),
                .init(sourceKey: "second", sourceObjectID: "component-second",
                      operation: .object(type: mappedType, collections: [],
                        initialProperties: .literal(.object(["any": .object(["name": .string("Identity second — זהות")])]))))
            ]
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let input = try encoder.encode(items)
            try input.write(to: inputURL, options: .withoutOverwriting)
            let digest = AnyContentDigest.sha256(input)
            let IDs = items.map(\.sourceObjectID)
            let component = try AnyDestinationSourceBinding(accountID: "explicit-canonical-identity-component",
                spaceID: "explicit-canonical-identity-component", witnessSHA256: digest,
                captureManifestSHA256: digest, semanticPlanSHA256: digest, sourceObjectIDs: IDs)
            plan = try .init(source: component, workspace: workspace, storeID: definitions.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                coverage: items.map { .init(sourceObjectID: $0.sourceObjectID,
                                           disposition: .mapped(itemSourceKeys: [$0.sourceKey])) }, items: items)
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else {
            plan = try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL))
        }
        let componentSource = plan.source
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { candidate in
            guard candidate == componentSource,
                  AnyContentDigest.sha256(try Data(contentsOf: inputURL)) == componentSource.captureManifestSHA256 else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
        try require(plan.binding.workspace == workspace && plan.items.count == 3)
        let progress = try await AnyDestinationMigrationExecutor(client: client, journalDirectory: journal)
            .execute(plan: plan, payloads: { _ in throw IdentityNativeControlFailure.unexpectedPayload },
                     verifySource: verifySource, authorize: authorize)
        try require(progress.allItemsReconciled && progress.mappings.count == 3)
        let verification = try await AnyDestinationMigrationVerifier(client: client)
            .verify(plan: plan, progress: progress, verifySource: verifySource, authorize: authorize)
        try require(verification.comparedOperationCount == 3 && verification.observations.count == 3)
        let type = try XCTUnwrap(progress.mappings.first { $0.sourceKey == "target-type" }?.objectID)
        var identities: [AnyJSON] = []
        for key in ["first", "second"] {
            let object = try XCTUnwrap(progress.mappings.first { $0.sourceKey == key }?.objectID)
            let response = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", space, "objects", object], authorize: authorize)
            let record = try XCTUnwrap(response["record"])
            try require(response["objectId"] == .string(object) && record["id"] == .string(object) &&
                        record["spaceId"] == .string(space) && record["any"]?["type"] == .string(type))
            try require(record["any"]?["id"] == nil && record["any"]?["spaceId"] == nil)
            try require(!originalPages.contains { Data($0.sourceObjectID.utf8) == Data(object.utf8) } &&
                        Data(original.sourceSpaceID.utf8) != Data(space.utf8))
            let name = key == "first" ? "Identity first — זהות e\u{301}" : "Identity second — זהות"
            let query = try await client.requestJSON(method: "POST", path: ["v1", "spaces", space, "objects", "query"],
                body: .object(["filter": .object(["any.name": .string(name)]), "limit": .integer(5),
                               "includeTotal": .bool(true)]), authorize: authorize)
            try require(query["hasNext"] == .bool(false) && query["total"] == .integer(1))
            let rows = try XCTUnwrap(query["records"]?.array)
            try require(rows.count == 1 && rows[0]["id"] == .string(object) && rows[0]["any"]?["type"] == .string(type))
            identities.append(.object(["sourceKey": .string(key), "objectID": .string(object),
                "spaceID": .string(space), "typeID": .string(type), "exactNativeQueryCount": .integer(1)]))
        }
        let descriptorRows = try bindings.map { binding -> AnyJSON in
            .object(["propertyID": .string(binding.propertyID), "nativeContract": .string(binding.nativeContract),
                     "nativeDescriptorSHA256": .string(binding.nativeDescriptorSHA256),
                     "originalSnapshotSHA256": .string(binding.evidence.snapshotSHA256),
                     "originalViewSHA256": .string(binding.evidence.viewSHA256)])
        }
        let proof: AnyJSON = .object([
            "contract": .string("pinkha-native-canonical-identity-component-v1"),
            "originalCaptureManifestSHA256": .string(original.manifestSHA256),
            "originalSourceAdmissionPromoted": .bool(false), "wholeSpaceMigration": .bool(false),
            "sourceIdentityDetailFieldsPresent": .integer(0), "nativeDescriptors": .array(descriptorRows),
            "targetIdentities": .array(identities)
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
        let proofBytes = try encoder.encode(proof), verificationBytes = try encoder.encode(verification)
        if phase == "reopen" {
            try require(proofBytes == Data(contentsOf: work.appendingPathComponent("execute-identities.json")))
            let previous = try JSONDecoder().decode(AnyDestinationContentVerification.self,
                from: Data(contentsOf: work.appendingPathComponent("execute-verification.json")))
            try require(verification.observations == previous.observations)
            try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        }
        try proofBytes.write(to: work.appendingPathComponent(phase + "-identities.json"), options: .withoutOverwriting)
        try verificationBytes.write(to: work.appendingPathComponent(phase + "-verification.json"), options: .withoutOverwriting)
        try require(try Self.originalCapture(at: URL(fileURLWithPath: originalPath, isDirectory: true)).manifestSHA256 == original.manifestSHA256)
        print("NATIVE_IDENTITY_COMPONENT descriptors=3 target_types=1 target_objects=2 exact_query_count=2 source_admission=false whole_space_migration=false phase=" + phase)
    }

    private static func originalCapture(at input: URL) throws -> AnyHeartNativeSpaceBundle {
        let root = input.resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
                  parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw IdentityNativeControlFailure.changedSource
            }
            let file = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
            guard file.path.hasPrefix(directory.path + "/"),
                  try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
                throw IdentityNativeControlFailure.changedSource
            }
            return try Data(contentsOf: file, options: [.mappedIfSafe])
        }
        let contextBytes = try bytes("fixture-context.json", under: root)
        guard AnyContentDigest.sha256(contextBytes) == "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a" else {
            throw IdentityNativeControlFailure.changedSource
        }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        guard context["customSchemaAcceptanceStatus"] == .string("FAIL"),
              context["readOnlyDiagnosticFixture"] == .bool(true), context["sourceAdmissionPromoted"] == .bool(false) else {
            throw IdentityNativeControlFailure.changedSource
        }
        let directory = root.appendingPathComponent("bundle", isDirectory: true)
        let manifest = try bytes("manifest.json", under: directory)
        guard AnyContentDigest.sha256(manifest) == "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4" else {
            throw IdentityNativeControlFailure.changedSource
        }
        return try .init(manifest: manifest,
            sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try bytes($0.path, under: directory) }
    }
    private func require(_ condition: @autoclosure () throws -> Bool) throws {
        guard try condition() else { throw IdentityNativeControlFailure.assertion }
    }
}
private enum IdentityNativeControlFailure: Error { case unauthorized, unexpectedPayload, changedSource, assertion }
#endif
