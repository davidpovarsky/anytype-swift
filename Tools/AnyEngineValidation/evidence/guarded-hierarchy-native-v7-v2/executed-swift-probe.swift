import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Actual guarded Wiki operations on a caller-owned disposable Space. No
/// generic-store fallback, mocked transport, or cross-object atomicity claim.
@MainActor
enum GuardedHierarchyProbe {
    private enum Failure: Error { case assertion(String) }

    static func run(url: URL, accountID: String, spaceID: String) async throws {
        let workspace = try AnyTorahWorkspace(accountID: accountID, spaceID: spaceID)
        let client = try AnyHTTPClient(baseURL: url, expectedAccountID: accountID)
        let base = ["v1", "spaces", spaceID]
        let session = AnyStreamSession()
        var checks: [String: Bool] = [:]
        var objectIDs: [String] = []
        var blockID: String?

        func check(_ id: String, _ value: Bool) throws {
            guard value else { throw Failure.assertion(id) }
            checks[id] = true
            FileHandle.standardError.write(Data(("PASS " + id + "\n").utf8))
        }
        func emit(status: String, error: Error? = nil) throws {
            var errorCode: String?
            if let error {
                if let failure = error as? Failure, case .assertion(let code) = failure { errorCode = code }
                else { errorCode = String(reflecting: type(of: error)) }
            }
            struct Report: Codable {
                let status: String
                let scope: String
                let accountID: String
                let spaceID: String
                let objectIDs: [String]
                let blockID: String?
                let checks: [String: Bool]
                let errorCode: String?
                let crossObjectAtomicity: Bool
                let retainedDisposableFixture: Bool
            }
            let result = Report(status: status, scope: "real_native_v7_guarded_wiki_hierarchy",
                                accountID: accountID, spaceID: spaceID, objectIDs: objectIDs,
                                blockID: blockID, checks: checks, errorCode: errorCode,
                                crossObjectAtomicity: false, retainedDisposableFixture: true)
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
            FileHandle.standardOutput.write(try encoder.encode(result))
            FileHandle.standardOutput.write(Data([0x0a]))
        }

        do {
            try await client.checkAccount()
            let health = try await client.requestJSON(method: "GET", path: ["v1", "health"])
            let run = try health.requireString("startedAt")
            let caps = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
            try check("current_guarded_capabilities_and_account",
                      health["account"]?.string == accountID &&
                      caps["contract"]?.string == "pinkha-torah-native-v1" &&
                      caps["conditionalPropertiesSet"]?.integer == 1 &&
                      caps["conditionalMembershipSet"]?.integer == 1 &&
                      caps["nativeDocumentTypePolicy"]?.integer == 1)

            let suffix = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
            let schema = try await AnyHTTPHierarchyRecordStore.installWiki(client: client, workspace: workspace)
            let store = try AnyGuardedHTTPHierarchyRecordStore(
                client: client, workspace: workspace, schema: schema, engineStartedAt: run)
            try await store.verifyCapabilities()
            let typeReply = try await client.requestJSON(method: "POST", path: base + ["types"],
                body: .object(["name": .string("Guarded hierarchy custom document"),
                               "xKey": .string("guarded_hierarchy_type_" + suffix)]))
            let customTypeID = try typeReply.requireString("typeId")
            _ = try await client.requestJSON(method: "POST", path: base + ["types", customTypeID, "parts"],
                body: .object(["key": .string("body"), "datasets": .array([
                    .object(["module": .string("editor")])])]))
            let typeProof = try await client.requestJSON(method: "GET", path: base + ["pinkha", "document-types", customTypeID])
            let ownerReply = try await client.requestJSON(method: "POST", path: base + ["collections"],
                body: .object(["name": .string("Guarded hierarchy preserved fields"),
                               "xKey": .string("guarded_hierarchy_fields_" + suffix)]))
            let extraOwner = try ownerReply.requireString("collectionId")
            let propertyReply = try await client.requestJSON(method: "POST", path: base + ["collections", extraOwner, "properties"],
                body: .object(["name": .string("Preserved metadata"), "xKey": .string("sentinel"),
                               "kind": .string("string"), "scope": .string("synced")]))
            let extraProperty = try propertyReply.requireString("propId")
            let opaqueValue = "retained-metadata-" + suffix
            try check("custom_document_and_preserved_property_definitions",
                      typeProof["eligible"]?.bool == true &&
                      typeProof["canonicalEditorDataset"]?.string == "editor_blocks")

            let allowedTypes: Set<String> = ["page", customTypeID]
            let hierarchy = try AnyHierarchyRepository(workspace: workspace, store: store, allowedTypeIDs: allowedTypes)
            func create(_ plan: AnyHierarchyCreationPlan) async throws -> String {
                guard case .object(var initial) = plan.initialProperties else { throw Failure.assertion("creation_properties_shape") }
                initial[extraOwner] = .object([extraProperty: .string(opaqueValue)])
                let reply = try await client.requestJSON(method: "POST", path: base + ["pinkha", "objects"],
                    body: .object(["type": .string(plan.typeID),
                                   "collections": .array((plan.collections + [extraOwner]).map(AnyJSON.string)),
                                   "initialProperties": .object(initial)]))
                let id = try reply.requireString("objectId")
                objectIDs.append(id)
                return id
            }
            let folderTitle = "Guarded folder " + suffix
            let folderID = try await create(hierarchy.prepareCreation(typeID: "page", title: folderTitle, kind: .folder))
            let firstID = try await create(hierarchy.prepareCreation(typeID: customTypeID,
                title: "Custom child " + suffix, kind: .writingDocument, parentID: folderID))
            let secondID = try await create(hierarchy.prepareCreation(typeID: "page",
                title: "Page child " + suffix, kind: .writingDocument, parentID: folderID))
            let blockReply = try await client.requestJSON(method: "POST",
                path: base + ["pinkha", "objects", folderID, "editor", "editor_blocks", "blocks"],
                body: .object(["type": .string("paragraph"), "text": .string("גוף שנשמר"),
                               "style": .object(["futureStyle": .string("retained")])]))
            guard let createdBlock = blockReply["recordIds"]?.array?.first?.string else {
                throw Failure.assertion("native_body_identity_missing")
            }
            blockID = createdBlock
            let original = try await hierarchy.snapshot()
            try check("guarded_wiki_tree_with_page_and_custom_document",
                      original.tree.children(of: folderID).map(\.objectId) == [firstID, secondID] &&
                      original.itemsByID[firstID]?.typeID == customTypeID)

            let stream = try await hierarchy.watch(session: session)
            var observer = stream.makeAsyncIterator()
            guard let initial = try await observer.next() else { throw Failure.assertion("missing_hierarchy_snapshot") }
            try check("guarded_hierarchy_atomic_initial", initial.initial && initial.snapshot.itemsByID[folderID] != nil)
            let renamed = "Renamed guarded folder " + suffix
            _ = try await hierarchy.rename(objectID: folderID, expectedTitle: folderTitle, newTitle: renamed)
            var sawRename = false
            for _ in 0..<32 {
                guard let update = try await observer.next() else { break }
                try await session.requireActive(generation: update.generation)
                if update.snapshot.itemsByID[folderID]?.title == renamed {
                    sawRename = !update.initial
                    break
                }
            }
            try check("guarded_rename_and_live_native_query", sawRename)
            await session.invalidate()
            do {
                try await session.requireActive(generation: initial.generation)
                throw Failure.assertion("retired_hierarchy_stream_accepted")
            } catch AnyLiveQueryError.staleGeneration {
                try check("retired_hierarchy_generation_rejected", true)
            }

            let stalePlan = try await hierarchy.prepareMove(objectID: secondID, parentID: folderID, beforeSiblingID: firstID)
            let beforeABA = try await store.readObject(objectID: secondID)
            guard let oldName = beforeABA["any"]?["name"]?.string,
                  let beforeVersion = beforeABA["_ver"] else { throw Failure.assertion("missing_native_version") }
            try await store.patch(objectID: secondID, ownerID: "any", values: ["name": .string("Temporary ABA " + suffix)],
                                  expectedVersion: beforeVersion, authorize: {})
            let midABA = try await store.readObject(objectID: secondID)
            guard let midVersion = midABA["_ver"] else { throw Failure.assertion("missing_native_mid_version") }
            try await store.patch(objectID: secondID, ownerID: "any", values: ["name": .string(oldName)],
                                  expectedVersion: midVersion, authorize: {})
            let afterABA = try await store.readObject(objectID: secondID)
            guard afterABA["_ver"] != beforeVersion, afterABA["any"]?["name"]?.string == oldName else {
                throw Failure.assertion("actual_aba_not_established")
            }
            do {
                _ = try await hierarchy.commitPlacement(stalePlan)
                throw Failure.assertion("prepared_aba_plan_accepted")
            } catch AnyHierarchyError.stalePlan {
                try check("prepared_placement_rejects_actual_native_aba", true)
            }
            do {
                try await store.patch(objectID: secondID, ownerID: "any", values: ["name": .string("Rejected stale title")],
                                      expectedVersion: beforeVersion, authorize: {})
                throw Failure.assertion("native_stale_version_accepted")
            } catch AnyEngineError.http(status: 409, code: "pinkha.properties.conflict") {
                try check("native_full_version_refuses_stale_direct_write",
                          try await store.readObject(objectID: secondID)["_ver"] == afterABA["_ver"])
            }

            let racing = try await store.readObject(objectID: firstID)
            guard let racingVersion = racing["_ver"] else { throw Failure.assertion("missing_racing_version") }
            let winnerIndexes = try await withThrowingTaskGroup(of: Int.self) { group in
                for index in 0..<4 {
                    group.addTask {
                        do {
                            try await store.patch(objectID: firstID, ownerID: "any",
                                values: ["name": .string("Concurrent title " + String(index) + " " + suffix)],
                                expectedVersion: racingVersion, authorize: {})
                            return index
                        } catch AnyEngineError.http(status: 409, code: "pinkha.properties.conflict") { return -1 }
                    }
                }
                var result: [Int] = []
                for try await winner in group { result.append(winner) }
                return result
            }
            try check("four_native_conditional_writers_have_one_winner",
                      winnerIndexes.filter { $0 >= 0 }.count == 1 && winnerIndexes.filter { $0 == -1 }.count == 3)

            let move = try await hierarchy.prepareMove(objectID: secondID, parentID: folderID, beforeSiblingID: firstID)
            _ = try await hierarchy.commitPlacement(move)
            let afterMove = try await store.readObject(objectID: secondID)
            _ = try await hierarchy.commitPlacement(move)
            let reorderedTree = try await hierarchy.snapshot()
            let afterRetry = try await store.readObject(objectID: secondID)
            try check("guarded_reorder_and_exact_retry_preserve_native_version",
                      reorderedTree.tree.children(of: folderID).map(\.objectId) == [secondID, firstID] &&
                      afterRetry["_ver"] == afterMove["_ver"])
            do {
                _ = try await hierarchy.prepareMove(objectID: folderID, parentID: firstID)
                throw Failure.assertion("cycle_accepted")
            } catch PinkhaHierarchyError.cycleDetected { try check("guarded_hierarchy_cycle_refused", true) }

            let beforeArchive = try await store.readObject(objectID: folderID)
            let archiveRace = HierarchyArchiveABARace(store: store, objectID: folderID)
            do {
                try await store.setArchived(objectID: folderID, archived: true, authorize: { try await archiveRace.authorize() })
                throw Failure.assertion("archive_dispatch_aba_accepted")
            } catch AnyEngineError.http(status: 409, code: "pinkha.properties.conflict") {
                let unchanged = try await store.readObject(objectID: folderID)
                try check("archive_dispatch_aba_refused_without_membership_loss",
                          await archiveRace.didApplyABA && unchanged["any"]?["collections"] == beforeArchive["any"]?["collections"] &&
                          unchanged[extraOwner]?[extraProperty]?.string == opaqueValue)
            }
            try await store.setArchived(objectID: folderID, archived: true, authorize: {})
            let archived = try await store.readObject(objectID: folderID)
            guard let originalValues = beforeArchive["any"]?["collections"]?.array,
                  let archivedValues = archived["any"]?["collections"]?.array else {
                throw Failure.assertion("archive_membership_metadata_missing")
            }
            let originalMemberships = Set(originalValues.compactMap(\.string))
            let archivedMemberships = Set(archivedValues.compactMap(\.string))
            try check("guarded_bin_preserves_other_memberships_and_property_value",
                      archivedMemberships == originalMemberships.union(["bin"]) &&
                      archived[extraOwner]?[extraProperty]?.string == opaqueValue && archived[schema.collectionID] == beforeArchive[schema.collectionID])
            try await store.setArchived(objectID: folderID, archived: true, authorize: {})
            try check("guarded_bin_exact_retry_preserves_native_version",
                      try await store.readObject(objectID: folderID)["_ver"] == archived["_ver"])
            try await store.setArchived(objectID: folderID, archived: false, authorize: {})
            let restored = try await store.readObject(objectID: folderID)
            let body = try await client.requestJSON(method: "POST", path: base + ["query"],
                body: .object(["objectId": .string(folderID), "dataset": .string("editor_blocks"), "limit": .integer(100)]))
            guard let restoredValues = restored["any"]?["collections"]?.array else {
                throw Failure.assertion("restored_membership_metadata_missing")
            }
            try check("guarded_restore_preserves_memberships_values_and_original_block",
                      Set(restoredValues.compactMap(\.string)) == originalMemberships &&
                      restored[extraOwner]?[extraProperty]?.string == opaqueValue &&
                      body["records"]?.array?.count == 1 && body["records"]?.array?.first?["id"]?.string == createdBlock &&
                      body["records"]?.array?.first?["style"]?["futureStyle"]?.string == "retained")

            let wrongRun = try AnyGuardedHTTPHierarchyRecordStore(client: client, workspace: workspace,
                schema: schema, engineStartedAt: run + "-stale")
            do {
                try await wrongRun.setArchived(objectID: folderID, archived: true, authorize: {})
                throw Failure.assertion("wrong_engine_run_accepted")
            } catch AnyEngineError.incompatibleSchema {
                try check("stale_engine_run_cannot_archive",
                          try await store.readObject(objectID: folderID)["_ver"] == restored["_ver"])
            }
            do {
                try await store.patch(objectID: folderID, ownerID: "any", values: ["name": .string("unguarded")], authorize: {})
                throw Failure.assertion("unguarded_patch_fallback_accepted")
            } catch AnyEngineError.incompatibleSchema { try check("unguarded_patch_entry_refuses_fallback", true) }

            let removal = try await hierarchy.removeFolderSafely(objectID: folderID)
            let final = try await hierarchy.snapshot()
            try check("guarded_folder_removal_reparents_before_binning",
                      removal.complete && removal.folderArchived == true && !removal.atomicAcrossObjects &&
                      Set(removal.reparentedIDs) == [firstID, secondID] && final.itemsByID[folderID] == nil &&
                      final.itemsByID[firstID]?.parentID == nil && final.itemsByID[secondID]?.parentID == nil &&
                      final.itemsByID[firstID]?.typeID == customTypeID)
            let reopened = try AnyHierarchyRepository(workspace: workspace,
                store: AnyGuardedHTTPHierarchyRecordStore(client: client, workspace: workspace,
                    schema: schema, engineStartedAt: run), allowedTypeIDs: allowedTypes)
            try check("fresh_guarded_reader_preserves_final_hierarchy",
                      try await reopened.snapshot().itemsByID == final.itemsByID)
            do {
                _ = try await client.requestJSON(method: "GET", path: base + ["pinkha", "claims"])
                throw Failure.assertion("hierarchy_implicitly_installed_claims")
            } catch AnyEngineError.http(status: 404, code: _) { try check("wiki_does_not_implicitly_install_claims", true) }
            await session.invalidate()
            try emit(status: "PASS")
        } catch {
            await session.invalidate()
            try emit(status: "FAIL", error: error)
            throw Failure.assertion("guarded_hierarchy_probe_failed")
        }
    }
}

/// A real intervening A→B→A property write in the dispatch authorization hook.
/// It never replaces a transport response or the native CAS implementation.
private actor HierarchyArchiveABARace {
    let store: AnyGuardedHTTPHierarchyRecordStore
    let objectID: String
    private var calls = 0
    private(set) var didApplyABA = false
    init(store: AnyGuardedHTTPHierarchyRecordStore, objectID: String) {
        self.store = store; self.objectID = objectID
    }
    func authorize() async throws {
        calls += 1
        guard calls == 2 else { return }
        let original = try await store.readObject(objectID: objectID)
        guard let name = original["any"]?["name"]?.string, let version = original["_ver"] else {
            throw ProbeFailure.assertion("archive_race_missing_version")
        }
        try await store.patch(objectID: objectID, ownerID: "any", values: ["name": .string(name + " temporary")],
                              expectedVersion: version, authorize: {})
        let intermediate = try await store.readObject(objectID: objectID)
        guard let intermediateVersion = intermediate["_ver"] else { throw ProbeFailure.assertion("archive_race_missing_mid_version") }
        try await store.patch(objectID: objectID, ownerID: "any", values: ["name": .string(name)],
                              expectedVersion: intermediateVersion, authorize: {})
        didApplyABA = true
    }
}
