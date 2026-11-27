#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Explicit component inputs exercise the production Bookmark emitter, native
/// prepared API, property editor and cold reader. They are not historical
/// Bookmark instances and cannot promote whole-source migration admission.
final class AnyDestinationNativeBookmarkTests: XCTestCase, @unchecked Sendable {
    func testActualNativeBookmarkURLAndEditorNotesColdReopen() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["execute", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the explicit native Bookmark controller and phase.")
        }
        let fixture = try JSONDecoder().decode(AnyJSON.self,
            from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        try require(fixture["binarySHA256"] == .string("1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"))
        try require(fixture["componentScope"] == .string("explicit-native-bookmark-v1"))
        let account = try XCTUnwrap(fixture["accountID"]?.string)
        let space = try XCTUnwrap(fixture["spaceID"]?.string)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(fixture["baseURL"]?.string))),
                                       expectedAccountID: account)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let planURL = work.appendingPathComponent("plan.json")
        let inputURL = work.appendingPathComponent("component-input.json")
        let journal = work.appendingPathComponent("journal", isDirectory: true)
        let authorize: AnyDestinationAuthorization = {
            let member = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", space, "members", "me"])
            guard member["identity"]?.string == account, member["status"] == .string("active"),
                  member["permission"] == .string("owner") else { throw BookmarkNativeFailure.unauthorized }
        }
        let capability = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace,
                                                                              authorize: authorize)
        let definition = try Self.componentDefinition()
        try require(!definition.permitsDestinationWrites && definition.issues.isEmpty)
        let sourceProperty = try XCTUnwrap(definition.property(sourceKey: "source"))
        let sourceType = try XCTUnwrap(definition.types.first)
        let ownerKey = try XCTUnwrap(definition.catalogSourceKey)
        try require(definition.types.count == 1 && sourceProperty.relation.maximumCount == 1)
        let urls = ["https://example.org/source?text=e%CC%81#native", ""]
        let notes = ["הערת סימנייה e\u{301} 🧪 — [מקור](https://example.org/source)",
                     "Empty URL still has native editor notes."]
        var items = try definition.admittedSchemaItems()
        try require(items.count == 4)
        for index in 0..<2 {
            let objectKey = "bookmark-\(index)"
            let row = try Self.row(id: objectKey, type: 16, key: "",
                details: ["source": .string(urls[index])], objectTypes: ["component-bookmark-type"])
            let values = try definition.values(snapshot: row, relationKeys: ["source"], objects: [])
            try require(values.initialRelationKeys == ["source"] && values.deferredGroups.isEmpty)
            let initial: AnyDestinationValue = .object([
                .init(key: .native("any"), value: .literal(.object([
                    "name": .string("Native Bookmark \(index)"),
                    "description": .string("Explicit component input; not a captured historical instance")
                ])))
            ] + values.initialGroups.map { .init(key: $0.owner, value: $0.fields) })
            items.append(.init(sourceKey: objectKey, sourceObjectID: objectKey,
                operation: .object(type: sourceType.object, collections: [sourceProperty.owner],
                                   initialProperties: initial)))
        }
        // Preserve the executor contract: all object identities precede content.
        for index in 0..<2 {
            let objectKey = "bookmark-\(index)"
            items.append(.init(sourceKey: "note-\(index)", sourceObjectID: objectKey,
                operation: .editorBlock(owner: .mapped(sourceKey: objectKey, slot: .objectID, encoding: .rawID),
                    dataset: "editor_blocks", type: "paragraph", text: notes[index],
                    style: .literal(.object([:])), parent: nil, position: "a")))
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
        let expectedInput = try encoder.encode(items)
        try expectedInput.write(to: work.appendingPathComponent(phase + "-generated-input.json"), options: .withoutOverwriting)
        let sourceDigest = AnyContentDigest.sha256(expectedInput)
        let plan: AnyDestinationMigrationPlan
        if phase == "execute" {
            try require(!FileManager.default.fileExists(atPath: planURL.path))
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                    attributes: [.posixPermissions: 0o700])
            try expectedInput.write(to: inputURL, options: .withoutOverwriting)
            let sourceIDs = Array(Set(items.map(\.sourceObjectID))).sorted()
            let source = try AnyDestinationSourceBinding(accountID: "explicit-native-bookmark-component",
                spaceID: "explicit-native-bookmark-component", witnessSHA256: sourceDigest,
                captureManifestSHA256: sourceDigest, semanticPlanSHA256: sourceDigest, sourceObjectIDs: sourceIDs)
            plan = try .init(source: source, workspace: workspace, storeID: capability.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                coverage: sourceIDs.map { id in
                    .init(sourceObjectID: id, disposition: .mapped(itemSourceKeys:
                        items.filter { $0.sourceObjectID == id }.map(\.sourceKey)))
                }, items: items)
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else {
            try require(expectedInput == Data(contentsOf: inputURL))
            plan = try .decode(Data(contentsOf: planURL))
            try require(encoder.encode(plan.items) == expectedInput)
        }
        let component = plan.source
        try require(component.captureManifestSHA256 == sourceDigest && component.semanticPlanSHA256 == sourceDigest)
        try require(plan.items.count == 8 && plan.binding.workspace == workspace)
        // The exact authenticated input is held immutable for this phase. Disk
        // bytes are rechecked at both boundaries; every native call still uses
        // current account/Space and lease/ACL authorization.
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { current in
            guard current == component else { throw AnyDestinationMigrationError.changedSource }
        }
        let executor = try AnyDestinationMigrationExecutor(client: client, journalDirectory: journal)
        let progress = try await executor.execute(plan: plan,
            payloads: { _ in throw BookmarkNativeFailure.unexpectedPayload },
            verifySource: verifySource, authorize: authorize)
        try require(progress.allItemsReconciled && progress.mappings.count == 8)
        let repeated = try await executor.execute(plan: plan,
            payloads: { _ in throw BookmarkNativeFailure.unexpectedPayload },
            verifySource: verifySource, authorize: authorize)
        try require(encoder.encode(progress.mappings) == encoder.encode(repeated.mappings))
        let ownerID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == ownerKey }?.objectID)
        let propertyID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == sourceProperty.sourceKey }?.recordIDs.first)
        let typeID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == sourceType.sourceKey }?.objectID)
        let exactKey = try AnyNativePropertyKey(ownerID: ownerID, propertyID: propertyID)
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let store = try AnyNativePropertyStore(client: client, workspace: workspace, policy: .init())
        let proofRows: [AnyJSON]
        do {
            proofRows = try await session.perform { lease in
                let nativeCatalog = try await store.catalog(lease: lease)
                let nativeType = try XCTUnwrap(nativeCatalog.types.first { $0.id == typeID })
                try self.require(nativeType.documentEligible && nativeType.isSelectableDocumentType && !nativeType.builtIn)
                try self.require(nativeType.raw["layout"]?["type"] == .string("bookmark"))
                try self.require(nativeType.raw["layout"]?["config"]?["pinkhaHeart"]?["contract"] ==
                    .string(AnyNativeImportedTypePresentation.bookmarkContract))
                var output: [AnyJSON] = []
                for index in 0..<2 {
                    let id = try XCTUnwrap(progress.mappings.first { $0.sourceKey == "bookmark-\(index)" }?.objectID)
                    let snapshot = try await store.read(objectID: id, lease: lease, catalog: nativeCatalog)
                    try self.require(snapshot.currentTypeID == typeID && snapshot.collectionIDs.contains(ownerID))
                    try self.require(snapshot.importedPresentation?.sourceURLKey == exactKey)
                    let before = try XCTUnwrap(snapshot.bookmarkSourceRow)
                    try self.require(before.value == .string(urls[index]) && before.isVisible && !before.isReadOnly)
                    try self.require(before.definition.kind == .string && before.definition.scope == "synced")
                    try self.require(before.definition.xFormat?["type"] == .string("url"))
                    try self.require(snapshot.bookmarkSourceRow?.value == .string(urls[index]))
                    if index == 0 { try self.require(snapshot.bookmarkSourceURL?.absoluteString == urls[index]) }
                    else { try self.require(snapshot.bookmarkSourceURL == nil && snapshot.bookmarkSourceRow?.value == .string("")) }
                    output.append(.object([
                        "objectID": .string(id), "nativeTypeID": .string(typeID),
                        "propertyOwnerID": .string(ownerID), "propertyID": .string(propertyID),
                        "sourceURL": .string(urls[index]), "hasHTTPOpenAction": .bool(index == 0),
                        "nativeEditorEligible": .bool(true), "visibleWritableURL": .bool(true),
                        "nativeTypeLayout": try XCTUnwrap(nativeType.raw["layout"]),
                        "noteRecordID": .string(try XCTUnwrap(progress.mappings.first { $0.sourceKey == "note-\(index)" }?.recordIDs.first)),
                        "noteTextSHA256": .string(AnyContentDigest.sha256(Data(notes[index].utf8)))
                    ]))
                }
                return output
            }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
        let verified = try await AnyDestinationMigrationVerifier(client: client)
            .verify(plan: plan, progress: repeated, verifySource: verifySource, authorize: authorize)
        try require(verified.comparedOperationCount == 8 && verified.observations.count == 8)
        let proof: AnyJSON = .object([
            "contract": .string("pinkha-native-bookmark-instance-component-v1"),
            "componentInputSHA256": .string(sourceDigest), "instances": .array(proofRows),
            "preparedOperations": .integer(8), "nativeEditorParagraphs": .integer(2),
            "historicalSourceInstanceClaim": .bool(false), "wholeSpaceMigration": .bool(false),
            "appleUIPresentationAccepted": .bool(false)
        ])
        let proofBytes = try encoder.encode(proof)
        if phase == "reopen" {
            try require(proofBytes == Data(contentsOf: work.appendingPathComponent("execute-bookmark.json")))
            let before = try JSONDecoder().decode(AnyDestinationContentVerification.self,
                from: Data(contentsOf: work.appendingPathComponent("execute-verification.json")))
            try require(before.observations == verified.observations)
            try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        }
        try require(Data(contentsOf: inputURL) == expectedInput)
        try require(AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL)).source == component)
        try proofBytes.write(to: work.appendingPathComponent(phase + "-bookmark.json"), options: .withoutOverwriting)
        try encoder.encode(verified).write(to: work.appendingPathComponent(phase + "-verification.json"), options: .withoutOverwriting)
        print("NATIVE_BOOKMARK_COMPONENT prepared_operations=8 native_instances=2 editor_paragraphs=2 exact_url_roles=2 source_admission=false apple_ui=false phase=" + phase)
    }

    func testNativeBookmarkEditUndoAndEditedColdReopen() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["edit", "reopen-edited"].contains(phase) else {
            throw XCTSkip("Requires completed native Bookmark migration and the edit lifecycle controller.")
        }
        let fixture = try JSONDecoder().decode(AnyJSON.self,
            from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        try require(fixture["binarySHA256"] == .string("1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"))
        try require(fixture["componentScope"] == .string("explicit-native-bookmark-v1"))
        try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        let account = try XCTUnwrap(fixture["accountID"]?.string)
        let space = try XCTUnwrap(fixture["spaceID"]?.string)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(fixture["baseURL"]?.string))),
                                       expectedAccountID: account)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let originalInput = try Data(contentsOf: work.appendingPathComponent("component-input.json"))
        let originalPlan = try Data(contentsOf: work.appendingPathComponent("plan.json"))
        let plan = try AnyDestinationMigrationPlan.decode(originalPlan)
        try require(plan.source.captureManifestSHA256 == AnyContentDigest.sha256(originalInput))
        try require(plan.binding.workspace == workspace && plan.items.count == 8)
        let originalProof = try Data(contentsOf: work.appendingPathComponent("execute-bookmark.json"))
        try require(originalProof == Data(contentsOf: work.appendingPathComponent("reopen-bookmark.json")))
        let accepted = try JSONDecoder().decode(AnyJSON.self, from: originalProof)
        let instances = try XCTUnwrap(accepted["instances"]?.array)
        try require(instances.count == 2)
        let authorize: AnyDestinationAuthorization = {
            let member = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", space, "members", "me"])
            guard member["identity"]?.string == account, member["status"] == .string("active"),
                  member["permission"] == .string("owner") else { throw BookmarkNativeFailure.unauthorized }
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let store = try AnyNativePropertyStore(client: client, workspace: workspace, policy: .init())
        let rows: [AnyJSON]
        do {
            rows = try await session.perform { lease in
                let catalog = try await store.catalog(lease: lease)
                var result: [AnyJSON] = []
                for (index, expected) in instances.enumerated() {
                    let objectID = try XCTUnwrap(expected["objectID"]?.string)
                    let typeID = try XCTUnwrap(expected["nativeTypeID"]?.string)
                    let ownerID = try XCTUnwrap(expected["propertyOwnerID"]?.string)
                    let propertyID = try XCTUnwrap(expected["propertyID"]?.string)
                    let expectedURL = try XCTUnwrap(expected["sourceURL"]?.string)
                    let key = try AnyNativePropertyKey(ownerID: ownerID, propertyID: propertyID)
                    var snapshot = try await store.read(objectID: objectID, lease: lease, catalog: catalog)
                    try self.require(snapshot.currentTypeID == typeID && snapshot.collectionIDs.contains(ownerID))
                    try self.require(snapshot.importedPresentation?.sourceURLKey == key)
                    try self.require(snapshot.bookmarkSourceRow?.value == .string(expectedURL))
                    if phase == "edit" && index == 0 {
                        let changed = "https://example.org/updated?from=native#bookmark"
                        let edit = try store.prepareSetValue(snapshot, key: key, value: .string(changed))
                        let updated = try await store.apply(edit, lease: lease, authorize: authorize)
                        try self.require(updated.readback == .verifiedCurrent)
                        try self.require(updated.snapshot?.bookmarkSourceRow?.value == .string(changed))
                        try self.require(updated.snapshot?.bookmarkSourceURL?.absoluteString == changed)
                        let inverse = try XCTUnwrap(updated.undo)
                        let restored = try await store.apply(inverse, lease: lease, authorize: authorize)
                        try self.require(restored.readback == .verifiedCurrent)
                        snapshot = try XCTUnwrap(restored.snapshot)
                        try self.require(snapshot.bookmarkSourceRow?.value == .string(expectedURL))
                        try encoder.encode(AnyJSON.object([
                            "contract": .string("pinkha-native-bookmark-current-lease-edit-undo-v1"),
                            "objectID": .string(objectID), "ownerID": .string(ownerID), "propertyID": .string(propertyID),
                            "actualConditionalWrites": .integer(2), "readbacksVerified": .bool(true),
                            "inputRestored": .bool(true), "migrationVerifiedBeforeEdits": .bool(true)
                        ])).write(to: work.appendingPathComponent("execute-property-edit.json"), options: .withoutOverwriting)
                    }
                    let query = try await client.requestJSON(method: "POST", path: ["v1", "spaces", space, "query"],
                        body: .object(["objectId": .string(objectID), "dataset": .string("editor_blocks"),
                            "sort": .array([.string("id")]), "limit": .integer(2), "includeTotal": .bool(true)]),
                        authorize: authorize)
                    try await lease.validate(); try await authorize()
                    let blocks = try XCTUnwrap(query["records"]?.array)
                    try self.require(query["total"] == .integer(1) && query["hasNext"] == .bool(false) && blocks.count == 1)
                    let block = blocks[0]
                    let text = try XCTUnwrap(block["text"]?.string)
                    try self.require(block["id"] == expected["noteRecordID"] && block["type"] == .string("paragraph"))
                    try self.require(AnyContentDigest.sha256(Data(text.utf8)) == expected["noteTextSHA256"]?.string)
                    try self.require((block["style"] ?? .object([:])) == .object([:]))
                    try self.require((block["nav"]?["parentId"] ?? .string("")) == .string("") && block["nav"]?["pos"] == .string("a"))
                    result.append(.object(["objectID": .string(objectID), "nativeTypeID": .string(typeID),
                        "ownerID": .string(ownerID), "propertyID": .string(propertyID),
                        "sourceURL": try XCTUnwrap(snapshot.bookmarkSourceRow?.value),
                        "noteRecordID": try XCTUnwrap(block["id"]), "noteText": .string(text)]))
                }
                return result
            }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
        // Accepted migrated content is now editable. Undo restores its value,
        // not the original signed migration revision: the strict original plan
        // must continue to reject that modified object, including after reopen.
        let executor = AnyDestinationMigrationExecutor(client: client, journalDirectory: work.appendingPathComponent("journal"))
        let source = plan.source
        do {
            _ = try await executor.execute(plan: plan,
                payloads: { _ in throw BookmarkNativeFailure.unexpectedPayload },
                verifySource: { current in
                    guard current == source else { throw AnyDestinationMigrationError.changedSource }
                }, authorize: authorize)
            throw BookmarkNativeFailure.assertion
        } catch let error as AnyDestinationMigrationError {
            guard case let .nativeTerminal(key, outcome) = error,
                  key == "bookmark-0", outcome == "committed_modified" else { throw error }
        }
        let proof = try encoder.encode(AnyJSON.object([
            "contract": .string("pinkha-native-bookmark-edit-lifecycle-v1"), "instances": .array(rows),
            "originalMigrationReceiptAcceptedAfterEdits": .bool(false),
            "originalReceiptOutcome": .string("committed_modified"),
            "wholeSpaceMigration": .bool(false)
        ]))
        if phase == "reopen-edited" {
            try require(proof == Data(contentsOf: work.appendingPathComponent("edit-lifecycle.json")))
        }
        try require(originalPlan == Data(contentsOf: work.appendingPathComponent("plan.json")))
        try require(originalInput == Data(contentsOf: work.appendingPathComponent("component-input.json")))
        try proof.write(to: work.appendingPathComponent(phase + "-lifecycle.json"), options: .withoutOverwriting)
        print("NATIVE_BOOKMARK_EDIT_LIFECYCLE actual_conditional_writes=2 exact_instances=2 original_migration_receipt=committed_modified phase=" + phase)
    }

    private static func componentDefinition() throws -> AnyHeartNativeDefinitionPlan {
        let relation = try row(id: "component-source-url", type: 521, key: "rel-source", details: [
            "name": .string("Source"), "description": .string("Explicit component URL definition"),
            "relationKey": .string("source"), "relationFormat": .integer(7), "relationDefaultValue": .null,
            "relationMaxCount": .integer(1), "relationReadonlyValue": .bool(false),
            "relationFormatIncludeTime": .bool(false), "relationFormatObjectTypes": .array([])
        ])
        let type = try row(id: "component-bookmark-type", type: 528, key: "ot-bookmark", details: [
            "name": .string("Imported Bookmark component"), "pluralName": .string("Bookmarks"),
            "recommendedLayout": .integer(11), "recommendedRelations": .array([.string("component-source-url")]),
            "recommendedFeaturedRelations": .array([.string("component-source-url")]),
            "recommendedHiddenRelations": .array([]), "recommendedFileRelations": .array([])
        ])
        let bytes = relation.jsonViewBytes + type.jsonViewBytes
        let digest = AnyContentDigest.sha256(bytes)
        let catalog = try AnyHeartNativeDefinitionCatalog(sourceAccountID: "explicit-bookmark-component",
            sourceSpaceID: "component-space", captureManifestSHA256: digest,
            sourceWitnessSHA256: digest, snapshots: [relation, type])
        guard !catalog.permitsDestinationWrites else { throw BookmarkNativeFailure.assertion }
        return try .init(catalog: catalog)
    }
    private static func row(id: String, type: Int64, key: String, details: [String: AnyJSON],
                            objectTypes: [String] = []) throws -> AnyHeartNativeSnapshotView {
        let marker = Data(("explicit-synthetic-bookmark-component-not-native-source-authority:" + id).utf8)
        let view: AnyJSON = .object([
            "Contract": .string("pinkha-native-snapshot-json-v1"), "SpaceID": .string("component-space"),
            "ObjectID": .string(id), "NativeType": .integer(type), "UniqueKey": .string(key),
            "SnapshotSHA256": .string(AnyContentDigest.sha256(marker)), "SnapshotBytes": .integer(Int64(marker.count)),
            "Snapshot": .object(["blocks": .array([]), "details": .object(details),
                "objectTypes": .array(objectTypes.map(AnyJSON.string)), "relationLinks": .array([])])
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try .init(jsonView: encoder.encode(view), snapshotBytes: marker,
                         sourceSpaceID: "component-space", sourceObjectID: id)
    }
    private func require(_ condition: @autoclosure () throws -> Bool,
                         file: StaticString = #filePath, line: UInt = #line) throws {
        guard try condition() else {
            XCTFail("Native Bookmark contract assertion", file: file, line: line)
            throw BookmarkNativeFailure.assertion
        }
    }
}
private enum BookmarkNativeFailure: Error { case unauthorized, unexpectedPayload, assertion }
#endif
