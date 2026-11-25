#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Actual native semantic text + canonical association migration and cold read.
/// Immutable component input is explicit; no full Heart source authority is claimed.
final class AnyDestinationNativeTorahSemanticTests: XCTestCase, @unchecked Sendable {
    func testActualNativeSemanticAssociationsRemainBoundAfterColdOfflineReopen() async throws {
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
        let planURL = work.appendingPathComponent("plan.json")
        let inputURL = work.appendingPathComponent("component-items.json")
        let canonicalURL = work.appendingPathComponent("source-canonical.json")
        let journal = work.appendingPathComponent("journal")
        let authorization: AnyDestinationAuthorization = {
            let member = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "members", "me"])
            guard member["identity"]?.string == account, member["status"] == .string("active"),
                  ["owner", "writer"].contains(member["permission"]?.string ?? "") else {
                throw TorahNativeControlFailure.unauthorized
            }
        }
        let capability = try await AnyNativePreparedDefinitionMigration.open(
            client: client, workspace: workspace, authorize: authorization)
        let sourceLocation = TorahAssociationLocation(spaceId: "explicit-semantic-component-source",
            target: .object(objectId: "source-document"))
        let ids = [UUID(uuidString: "cfe050d0-e511-440c-86a5-526bc1234567")!,
                   UUID(uuidString: "27ed89f1-066e-4360-9b5a-c624c2345678")!]
        let anchors = try ids.map { try PinkhaSemanticTextAnchor(
            spaceID: sourceLocation.spaceId, objectID: sourceLocation.target.objectId, id: $0) }
        let sourceText = "[שָׁלוֹם 😀](\(anchors[0].markerString)) then [a\u{301} second](\(anchors[1].markerString))"
        let sourceRecords = try anchors.enumerated().map { index, anchor -> TorahStoredAssociationRecord in
            let item = TorahAssociationItem(id: "source-association-\(index)", kind: .ref, role: .context,
                providerID: "sefaria", externalID: "Genesis 1:1", canonicalKey: "Genesis.1.1",
                labelHe: "בראשית א׳ א׳", labelEn: "Genesis 1:1", rawInput: "original a\u{301}",
                providerPayload: "{\"retained\":[0,false,null]}", createdAt: Date(timeIntervalSince1970: 123),
                customMetadata: ["future": "untouched"], unknownFields: ["opaque": .bool(false)])
            return .init(location: sourceLocation,
                item: try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: item, location: sourceLocation),
                unknownFields: ["recordFuture": .string("retained")])
        }
        let canonical = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(
            records: sourceRecords, unknownFields: ["envelopeFuture": .array([.null, .number(7)])]))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
        let plan: AnyDestinationMigrationPlan
        if phase == "execute", !FileManager.default.fileExists(atPath: planURL.path) {
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
            let items: [AnyDestinationMigrationItem] = [
                .init(sourceKey: "document", sourceObjectID: sourceLocation.target.objectId,
                    operation: .object(type: .native("page"), collections: [],
                        initialProperties: .literal(.object(["any": .object([
                            "name": .string("Native semantic migration — עוגנים")])])))),
                .init(sourceKey: "body", sourceObjectID: sourceLocation.target.objectId,
                    operation: .anchoredEditorBlock(
                        owner: .mapped(sourceKey: "document", slot: .objectID, encoding: .rawID),
                        dataset: "editor_blocks", type: "paragraph",
                        text: try .init(sourceSpaceID: sourceLocation.spaceId,
                                    sourceObjectID: sourceLocation.target.objectId, inlineMarkdown: sourceText),
                        style: .literal(.object([:])), parent: nil, position: "A"))
            ]
            let input = try encoder.encode(items)
            try input.write(to: inputURL, options: .withoutOverwriting)
            try canonical.write(to: canonicalURL, options: .withoutOverwriting)
            let digest = AnyContentDigest.sha256(input + canonical)
            let source = try AnyDestinationSourceBinding(accountID: "explicit-component-source-account",
                spaceID: sourceLocation.spaceId, witnessSHA256: digest, captureManifestSHA256: digest,
                semanticPlanSHA256: digest, sourceObjectIDs: [sourceLocation.target.objectId])
            plan = try .init(source: source, workspace: workspace, storeID: capability.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                coverage: [.init(sourceObjectID: sourceLocation.target.objectId,
                                 disposition: .mapped(itemSourceKeys: items.map(\.sourceKey)))], items: items)
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else { plan = try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL)) }
        XCTAssertEqual(try Data(contentsOf: canonicalURL), canonical)
        let source = plan.source
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { candidate in
            guard candidate == source,
                  AnyContentDigest.sha256(try Data(contentsOf: inputURL) + Data(contentsOf: canonicalURL)) ==
                    source.captureManifestSHA256 else { throw AnyDestinationMigrationError.changedSource }
        }
        let progress = try await AnyDestinationMigrationExecutor(client: client, journalDirectory: journal).execute(
            plan: plan, payloads: { _ in throw TorahNativeControlFailure.unexpectedPayload },
            verifySource: verifySource, authorize: authorization)
        XCTAssertTrue(progress.allItemsReconciled); XCTAssertEqual(progress.mappings.count, 2)
        let verified = try await AnyDestinationMigrationVerifier(client: client).verify(
            plan: plan, progress: progress, verifySource: verifySource, authorize: authorization)
        let document = try XCTUnwrap(progress.mappings.first { $0.sourceKey == "document" }?.objectID)
        let block = try XCTUnwrap(progress.mappings.first { $0.sourceKey == "body" }?.recordIDs.first)
        let location = TorahAssociationLocation(spaceId: space, target: .object(objectId: document))
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        do {
            let documents = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
            let ordinaryAccess = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace, allowedTypeIDs: ["page"])
            let access = try AnyNativeTorahMigrationTargetAccess(access: ordinaryAccess, documents: documents, session: session)
            let store = try AnyGuardedTorahOperationStore(client: client, workspace: workspace)
            if phase == "execute" {
                // Explicit native module provisioning is fixture preparation.
                // Cold reopen only reads the already installed signed module.
                try await store.repository.install(authorize: authorization)
            }
            let migrated = try AnyTorahMigrationPlan(sourceBytes: canonical, sourceSpaceID: sourceLocation.spaceId,
                sourceObjectID: sourceLocation.target.objectId, workspace: workspace, targetObjectID: document,
                blockIDMap: [:], migrationKey: plan.binding.planID)
            let importer = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
            let receipt = try await importer.execute(migrated, authorize: authorization)
            XCTAssertEqual(receipt.status, .complete); XCTAssertTrue(receipt.pendingClaimIDs.isEmpty)
            if phase == "reopen" {
                XCTAssertEqual(receipt.alreadyPresentClaimIDs.count, 2)
                XCTAssertTrue(receipt.acknowledgedClaimIDs.isEmpty)
            }
            let retry = try await importer.execute(migrated, authorize: authorization)
            XCTAssertEqual(retry.status, .complete)
            XCTAssertEqual(retry.alreadyPresentClaimIDs.count, 2); XCTAssertTrue(retry.acknowledgedClaimIDs.isEmpty)
            let read = try await session.perform { lease in try await documents.read(objectID: document, lease: lease) }
            XCTAssertEqual(read.snapshot.depthFirstIDs, [block])
            let expected = try AnyInlineMarkdown(sourceText).remappingSemanticAnchors(
                sourceSpaceID: sourceLocation.spaceId, sourceObjectID: sourceLocation.target.objectId,
                destinationSpaceID: space, destinationObjectID: document)
            XCTAssertEqual(read.snapshot.blocks.first?.text.utf8.map { $0 }, Array(expected.utf8))
            let repository = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: access)
            let actual = try await repository.listDocumentAssociations(objectId: document, spaceId: space)
                .sorted { $0.id < $1.id }
            XCTAssertEqual(actual.count, 2)
            for (index, item) in actual.enumerated() {
                let semantic = try XCTUnwrap(TorahSemanticAnchorAssociation.decoding(item, location: location))
                XCTAssertEqual(semantic.anchor.id, ids[index])
                guard case .resolved(let fragments) = try AnySemanticAnchorDocument.resolve(semantic.anchor, read: read) else {
                    throw TorahNativeControlFailure.unresolvedTarget
                }
                XCTAssertEqual(fragments.count, 1); XCTAssertEqual(fragments[0].blockID, block)
                XCTAssertGreaterThan(fragments[0].range.length, 0)
                var restored = item
                restored.customMetadata?[TorahSemanticAnchorAssociation.metadataKey] =
                    sourceRecords[index].item.customMetadata?[TorahSemanticAnchorAssociation.metadataKey]
                XCTAssertEqual(restored, sourceRecords[index].item)
                XCTAssertThrowsError(try TorahSemanticAnchorAssociation.decoding(item, location: sourceLocation))
            }
            let originalClaims = try await store.snapshot().all.filter { $0.operation.targetObjectID == document }
            XCTAssertEqual(originalClaims.count, 2)
            let missingAnchor = try PinkhaSemanticTextAnchor(spaceID: sourceLocation.spaceId,
                objectID: sourceLocation.target.objectId, id: UUID(uuidString: "3e756d99-e138-4ebf-a749-c771c3456789")!)
            var missing = sourceRecords[0].item
            missing.id = "source-missing"; missing.customMetadata?.removeValue(forKey: TorahSemanticAnchorAssociation.metadataKey)
            missing = try TorahSemanticAnchorAssociation(anchor: missingAnchor).attaching(to: missing, location: sourceLocation)
            let missingBytes = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(
                records: [.init(location: sourceLocation, item: missing)]))
            let missingPlan = try AnyTorahMigrationPlan(sourceBytes: missingBytes, sourceSpaceID: sourceLocation.spaceId,
                sourceObjectID: sourceLocation.target.objectId, workspace: workspace, targetObjectID: document,
                blockIDMap: [:], migrationKey: plan.binding.planID + "-missing")
            do {
                _ = try await importer.execute(missingPlan, authorize: authorization)
                XCTFail("A missing actual native marker cannot create a migrated association")
            } catch AnyHostError.invalidSelection {}
            let afterClaims = try await store.snapshot().all.filter { $0.operation.targetObjectID == document }
            XCTAssertEqual(afterClaims.map(\.id).sorted(), originalClaims.map(\.id).sorted())
            let claims = originalClaims.map(\.operation).sorted { $0.operationID < $1.operationID }
            try encoder.encode(claims).write(to: work.appendingPathComponent(phase + "-claims.json"), options: .withoutOverwriting)
            try encoder.encode(actual).write(to: work.appendingPathComponent(phase + "-associations.json"), options: .withoutOverwriting)
            try encoder.encode(read.snapshot.blocks.map(\.native)).write(
                to: work.appendingPathComponent(phase + "-blocks.json"), options: .withoutOverwriting)
            try encoder.encode(verified).write(to: work.appendingPathComponent(phase + "-verification.json"), options: .withoutOverwriting)
            try encoder.encode(progress.mappings).write(to: work.appendingPathComponent(phase + "-mappings.json"), options: .withoutOverwriting)
            if phase == "reopen" {
                for suffix in ["claims", "associations", "blocks", "verification", "mappings"] {
                    XCTAssertEqual(try Data(contentsOf: work.appendingPathComponent("execute-" + suffix + ".json")),
                                   try Data(contentsOf: work.appendingPathComponent("reopen-" + suffix + ".json")))
                }
            }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
    }
    private enum TorahNativeControlFailure: Error { case unauthorized, unexpectedPayload, unresolvedTarget }
}
#endif
