#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// A narrow real-native persistence/readback for the new imported type rank.
/// The original capture's unsupported layouts and complete admission stay refused.
final class AnyDestinationNativeTypeOrderTests: XCTestCase, @unchecked Sendable {
    func testActualSourceTypeRanksPersistThroughPreparedReplayAndColdCatalog() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let originalPath = env["PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["execute", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the exact real-native type-order controller and original source.")
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
                  member["permission"] == .string("owner") else { throw TypeOrderNativeFailure.unauthorized }
        }
        let original = try Self.originalCapture(at: URL(fileURLWithPath: originalPath, isDirectory: true))
        let source = try AnyHeartNativeDefinitionCatalog(bundle: original)
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: source)
        try require(original.objects.count == 156 && source.types.count == 20 && source.relations.count == 126)
        try require(!source.permitsDestinationWrites && !mapper.permitsDestinationWrites)
        XCTAssertThrowsError(try mapper.admittedSchemaItems())
        let basic = source.types.filter { $0.recommendedLayout == 0 }
        try require(basic.count == 3 && basic.filter { $0.orderID != nil }.count == 1)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        var items: [AnyDestinationMigrationItem] = []
        for (index, definition) in basic.enumerated() {
            let selected = try XCTUnwrap(mapper.schemaItems.first {
                $0.sourceObjectID == definition.objectID &&
                    { if case .typeDefinition = $0.operation { return true }; return false }($0)
            })
            guard case .typeDefinition(let draft) = selected.operation,
                  case .literal(let metadata) = draft.meta else { throw TypeOrderNativeFailure.assertion }
            try require(metadata[AnyNativeImportedTypeOrder.valueKey] == definition.orderID.map(AnyJSON.string))
            let key = "type-\(index)"
            // Component scope: exact captured metadata, but only a standalone
            // editor part. The source recommendation graph is NOT admitted here.
            items.append(.init(sourceKey: key, sourceObjectID: definition.objectID,
                operation: .typeDefinition(.init(xKey: draft.xKey, name: draft.name,
                    description: draft.description, iconCID: draft.iconCID,
                    layout: .literal(.object(["type": .string("page")])),
                    hidden: draft.hidden, meta: draft.meta))))
            items.append(.init(sourceKey: "editor-\(index)", sourceObjectID: definition.objectID,
                expectedRecordCount: 2,
                operation: .partDefinition(owner: .mapped(sourceKey: key, slot: .objectID, encoding: .rawID),
                    draft: .literal(.object([
                        "key": .string("content"), "name": .string("Content"), "pos": .string("m"),
                        "ui": .object(["type": .string("document")]),
                        "datasets": .array([.object(["module": .string("editor"), "key": .string("editor_blocks")])]),
                    ])))))
        }
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let inputURL = work.appendingPathComponent("type-order-component-input.json")
        let planURL = work.appendingPathComponent("type-order-plan.json")
        let journal = work.appendingPathComponent("journal", isDirectory: true)
        let definitions = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace, authorize: authorize)
        let expectedInput = try encoder.encode(items)
        let plan: AnyDestinationMigrationPlan
        if phase == "execute" {
            try require(!FileManager.default.fileExists(atPath: planURL.path))
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
            try expectedInput.write(to: inputURL, options: .withoutOverwriting)
            let digest = AnyContentDigest.sha256(expectedInput)
            let component = try AnyDestinationSourceBinding(
                accountID: "explicit-source-type-order-component", spaceID: "explicit-source-type-order-component",
                witnessSHA256: digest, captureManifestSHA256: digest, semanticPlanSHA256: digest,
                sourceObjectIDs: basic.map(\.objectID))
            plan = try .init(source: component, workspace: workspace, storeID: definitions.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                coverage: basic.enumerated().map { index, definition in
                    .init(sourceObjectID: definition.objectID,
                          disposition: .mapped(itemSourceKeys: ["type-\(index)", "editor-\(index)"]))
                }, items: items)
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else {
            try require(expectedInput == Data(contentsOf: inputURL))
            plan = try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL))
        }
        let component = plan.source
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { candidate in
            guard candidate == component,
                  AnyContentDigest.sha256(try Data(contentsOf: inputURL)) == component.captureManifestSHA256 else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
        try require(plan.binding.workspace == workspace && plan.items.count == 6)
        let executor = try AnyDestinationMigrationExecutor(client: client, journalDirectory: journal)
        let progress = try await executor.execute(plan: plan,
            payloads: { _ in throw TypeOrderNativeFailure.unexpectedPayload },
            verifySource: verifySource, authorize: authorize)
        try require(progress.allItemsReconciled && progress.mappings.count == 6)
        let repeated = try await executor.execute(plan: plan,
            payloads: { _ in throw TypeOrderNativeFailure.unexpectedPayload },
            verifySource: verifySource, authorize: authorize)
        try require(encoder.encode(progress.mappings) == encoder.encode(repeated.mappings))
        let verified = try await AnyDestinationMigrationVerifier(client: client)
            .verify(plan: plan, progress: repeated, verifySource: verifySource, authorize: authorize)
        try require(verified.comparedOperationCount == 6 && verified.observations.count == 6)

        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let store = try AnyNativePropertyStore(client: client, workspace: workspace, policy: .init())
        let nativeCatalog: AnyNativePropertyCatalog
        do {
            nativeCatalog = try await session.perform { lease in try await store.catalog(lease: lease) }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
        var targetIDs: [String] = [], exactRows: [AnyJSON] = []
        for (index, definition) in basic.enumerated() {
            let target = try XCTUnwrap(progress.mappings.first { $0.sourceKey == "type-\(index)" }?.objectID)
            targetIDs.append(target)
            let rows = nativeCatalog.types.filter { $0.id == target }
            try require(rows.count == 1)
            let row = try XCTUnwrap(rows.first)
            try require(row.documentEligible && !row.builtIn)
            let item = items[index * 2]
            guard case .typeDefinition(let draft) = item.operation,
                  case .literal(let metadata) = draft.meta else { throw TypeOrderNativeFailure.assertion }
            try require(AnyDestinationDefinitionChecks.bytes(XCTUnwrap(row.raw["meta"])) ==
                        AnyDestinationDefinitionChecks.bytes(metadata))
            let order = try XCTUnwrap(AnyNativeImportedTypeOrder(owner: row))
            try require(order.orderID.map { Data($0.utf8) } == definition.orderID.map { Data($0.utf8) })
            try require(order.scope == Data(source.contentSHA256.utf8))
            try require(nativeCatalog.types.filter { $0.xKey == draft.xKey }.count == 1)
            exactRows.append(.object([
                "sourceObjectID": .string(definition.objectID), "targetTypeID": .string(target),
                "sourceSnapshotSHA256": .string(definition.snapshot.snapshotSHA256),
                "sourceViewSHA256": .string(definition.snapshot.viewSHA256),
                "metadataSHA256": .string(AnyContentDigest.sha256(try AnyDestinationDefinitionChecks.bytes(metadata))),
                "rankPresent": .bool(definition.orderID != nil),
                "editorEligible": .bool(row.documentEligible),
            ]))
        }
        let imported = nativeCatalog.types.filter { targetIDs.contains($0.id) }
        let orderedSource = try XCTUnwrap(basic.firstIndex { $0.orderID != nil })
        try require(imported.count == 3 && imported.first?.id == targetIDs[orderedSource])
        let proof: AnyJSON = .object([
            "contract": .string("pinkha-source-type-order-native-component-v1"),
            "sourceManifestSHA256": .string(original.manifestSHA256),
            "sourceCatalogSHA256": .string(source.contentSHA256),
            "types": .array(exactRows), "sourceAdmissionPromoted": .bool(false),
            "wholeSpaceMigration": .bool(false),
        ])
        let proofBytes = try encoder.encode(proof), verificationBytes = try encoder.encode(verified)
        if phase == "reopen" {
            try require(proofBytes == Data(contentsOf: work.appendingPathComponent("execute-type-order.json")))
            let previous = try JSONDecoder().decode(AnyDestinationContentVerification.self,
                from: Data(contentsOf: work.appendingPathComponent("execute-verification.json")))
            try require(verified.observations == previous.observations)
            try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        }
        try proofBytes.write(to: work.appendingPathComponent(phase + "-type-order.json"), options: .withoutOverwriting)
        try verificationBytes.write(to: work.appendingPathComponent(phase + "-verification.json"), options: .withoutOverwriting)
        try require(Self.originalCapture(at: URL(fileURLWithPath: originalPath, isDirectory: true)).manifestSHA256 == original.manifestSHA256)
        print("NATIVE_TYPE_ORDER_COMPONENT target_types=3 native_editor_parts=3 prepared_operations=6 exact_type_handles=3 source_admission=false whole_space_migration=false phase=" + phase)
    }

    private static func originalCapture(at input: URL) throws -> AnyHeartNativeSpaceBundle {
        let root = input.resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
                  parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw TypeOrderNativeFailure.changedSource
            }
            let file = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
            guard file.path.hasPrefix(directory.path + "/"),
                  try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
                throw TypeOrderNativeFailure.changedSource
            }
            return try Data(contentsOf: file, options: [.mappedIfSafe])
        }
        let contextBytes = try bytes("fixture-context.json", under: root)
        guard AnyContentDigest.sha256(contextBytes) == "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a" else {
            throw TypeOrderNativeFailure.changedSource
        }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        guard context["customSchemaAcceptanceStatus"] == .string("FAIL"),
              context["readOnlyDiagnosticFixture"] == .bool(true), context["sourceAdmissionPromoted"] == .bool(false) else {
            throw TypeOrderNativeFailure.changedSource
        }
        let directory = root.appendingPathComponent("bundle", isDirectory: true)
        let manifest = try bytes("manifest.json", under: directory)
        guard AnyContentDigest.sha256(manifest) == "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4" else {
            throw TypeOrderNativeFailure.changedSource
        }
        return try .init(manifest: manifest,
            sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try bytes($0.path, under: directory) }
    }
    private func require(_ condition: @autoclosure () throws -> Bool) throws {
        guard try condition() else { throw TypeOrderNativeFailure.assertion }
    }
}
private enum TypeOrderNativeFailure: Error { case unauthorized, unexpectedPayload, changedSource, assertion }
#endif
