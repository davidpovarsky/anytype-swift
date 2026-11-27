#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Operates only on the controller's owned exact account copy. Original
/// migration operations, source accounts and old receipts are never replayed.
final class AnyDestinationNativeDefinitionDirectoryTests: XCTestCase, @unchecked Sendable {
    private struct ReadSet: Sendable {
        let content: AnyJSON
        let matches: [Data: Bool]
        let outcomes: [Data: String]
    }

    func testOriginalDefinitionIdentitiesEditsParentRefusalAndColdReopen() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_NATIVE_DEFINITION_FIXTURE"],
              let workPath = env["PINKHA_NATIVE_DEFINITION_WORK"],
              let retainedPath = env["PINKHA_NATIVE_DEFINITION_RETAINED"],
              let phase = env["PINKHA_NATIVE_DEFINITION_PHASE"],
              ["edit", "edited-reopen", "restored-reopen"].contains(phase) else {
            throw XCTSkip("Requires the retained-definition controller and an owned exact account copy.")
        }
        let fixture = try json(URL(fileURLWithPath: fixturePath))
        try require(fixture["binarySHA256"] == .string("1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"))
        try require(fixture["componentScope"] == .string("retained-original-native-definition-directory-v1"))
        try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        let account = try XCTUnwrap(fixture["accountID"]?.string)
        let space = try XCTUnwrap(fixture["spaceID"]?.string)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(fixture["baseURL"]?.string))),
                                      expectedAccountID: account)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let retained = URL(fileURLWithPath: retainedPath, isDirectory: true)
        let planURL = retained.appendingPathComponent("source-preservation-plan.json")
        let mappingsURL = retained.appendingPathComponent("execute-mappings.json")
        let planBytes = try Data(contentsOf: planURL), mappingBytes = try Data(contentsOf: mappingsURL)
        try require(AnyContentDigest.sha256(planBytes) == "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930")
        try require(AnyContentDigest.sha256(mappingBytes) == "eabdf2e362189abd5a2e78f7c13f1f1d77d8339c27109d2a6ec19ccdbb2755a3")
        let plan = try AnyDestinationMigrationPlan.decode(planBytes)
        let mappings = try JSONDecoder().decode([AnyDestinationMigrationMapping].self, from: mappingBytes)
        try require(plan.binding.workspace == workspace && mappings.count == 182)
        let directory = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: mappings)
        try require(!directory.permitsSourceAdmission && !directory.unresolvedSourceDefinitionIDs.isEmpty)
        let types = directory.entries.filter { if case .type = $0.address { true } else { false } }
        let options = directory.entries.filter { if case .option = $0.address { true } else { false } }
        let properties = directory.entries.filter { entry in
            guard case .property = entry.address else { return false }
            return entry.intent?.kind == .propertyDefinition
        }
        let canonicalCount = plan.coverage.filter {
            switch $0.disposition {
            case .canonicalProperty, .preservedCanonicalProperty: true
            default: false
            }
        }.count
        try require(types.count == 1 && properties.count == 7 && options.count == 4)
        try require(directory.entries.count == 12 + canonicalCount && canonicalCount > 0)
        let typeEntry = types[0], optionEntry = options[0]
        guard case .type(let typeID) = typeEntry.address,
              case .option(let ownerKind, let propertyKey, let optionID) = optionEntry.address else {
            throw DefinitionDirectoryFailure.assertion
        }
        let propertyEntry = try XCTUnwrap(properties.first {
            $0.address == .property(ownerKind: ownerKind, key: propertyKey)
        })
        let originalTypeName = try XCTUnwrap(typeEntry.originalDescriptor["name"]?.string)
        let originalPropertyName = try XCTUnwrap(propertyEntry.originalDescriptor["name"]?.string)
        let originalOptionName = try XCTUnwrap(optionEntry.originalDescriptor["name"]?.string)
        let originalOptionColor = try XCTUnwrap(optionEntry.originalDescriptor["color"]?.string)
        let originalOptionPosition = try XCTUnwrap(optionEntry.originalDescriptor["pos"]?.string)
        let originalParentID = try XCTUnwrap(propertyEntry.originalDescriptor["xFormat"]?["pinkhaHeart"]?["sourceObjectID"]?.string)
        let changedTypeName = originalTypeName + " — native identity continuation"
        let changedPropertyName = originalPropertyName + " — native identity continuation"
        let changedOptionName = originalOptionName + " — native identity continuation"
        let changedColor = originalOptionColor == "red" ? "blue" : "red"
        let changedPosition = originalOptionPosition + "z"
        let typePath = ["v1", "spaces", space, "types", typeID]
        let propertyPath = ["v1", "spaces", space, ownerKind.rawValue, propertyKey.ownerID, "properties", propertyKey.propertyID]
        let optionPrefix = "xFormat.options." + optionID + "."
        let changedFields: [String: AnyJSON] = [
            "name": .string(changedPropertyName), optionPrefix + "name": .string(changedOptionName),
            optionPrefix + "color": .string(changedColor), optionPrefix + "pos": .string(changedPosition)]
        let restoredFields: [String: AnyJSON] = [
            "name": .string(originalPropertyName), optionPrefix + "name": .string(originalOptionName),
            optionPrefix + "color": .string(originalOptionColor), optionPrefix + "pos": .string(originalOptionPosition)]
        let changedIDs = Set([typeEntry.sourceObjectID, propertyEntry.sourceObjectID, optionEntry.sourceObjectID].map { Data($0.utf8) })
        let reader = try AnyNativeImportedDefinitionStore(client: client, workspace: workspace)
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let lease: AnyHostLease
        do {
            lease = try await session.perform { lease in
                if phase == "edit" {
                    try self.require(!FileManager.default.fileExists(atPath: work.appendingPathComponent("baseline-definitions.json").path))
                    let initial = try await self.readAll(directory, reader: reader, lease: lease)
                    try self.require(initial.matches.values.allSatisfy { $0 })
                    try self.write(initial.content, work.appendingPathComponent("baseline-definitions.json"))
                    try await self.refuseForgedNativeMapping(plan: plan, mappings: mappings, entry: typeEntry,
                        reader: reader, lease: lease)
                    try await self.refuseForgedNativeMapping(plan: plan, mappings: mappings, entry: propertyEntry,
                        reader: reader, lease: lease)
                    let wrongSpace = try AnyTorahWorkspace(accountID: account, spaceID: space + "-foreign")
                    let wrongReader = try AnyNativeImportedDefinitionStore(client: client, workspace: wrongSpace)
                    do {
                        _ = try await wrongReader.read(sourceObjectID: typeEntry.sourceObjectID, directory: directory, lease: lease)
                        throw DefinitionDirectoryFailure.assertion
                    } catch AnyHostError.wrongWorkspace { }
                    try await self.patch(client, path: typePath, body: .object(["name": .string(changedTypeName)]),
                        key: "type-name-edit", work: work, lease: lease)
                    try await self.patch(client, path: propertyPath, body: .object(["set": .object(changedFields)]),
                        key: "property-and-option-edit", work: work, lease: lease)
                    let editedOption = try await reader.read(sourceObjectID: optionID, directory: directory, lease: lease)
                    try self.require(!editedOption.matchesOriginalDescriptor)
                    try self.require(editedOption.raw["name"] == .string(changedOptionName))
                    try self.require(editedOption.raw["color"] == .string(changedColor))
                    try self.require(editedOption.raw["pos"] == .string(changedPosition))
                    try await self.patch(client, path: propertyPath,
                        body: .object(["set": .object(["xFormat.pinkhaHeart.sourceObjectID": .string("explicit-foreign-parent-origin")])]),
                        key: "parent-provenance-negative", work: work, lease: lease)
                    let direct = try await client.requestJSON(method: "GET", path: Array(propertyPath.dropLast()),
                        authorize: { try await lease.validate() })
                    let parent = try XCTUnwrap(direct["properties"]?.array?.first {
                        $0["id"]?.string.map { Data($0.utf8) } == Data(propertyKey.propertyID.utf8)
                    })
                    try self.require(parent["xFormat"]?["pinkhaHeart"]?["sourceObjectID"] == .string("explicit-foreign-parent-origin"))
                    try self.require(parent["xFormat"]?["options"]?[optionID] == editedOption.raw)
                    for entry in [propertyEntry, optionEntry] {
                        do {
                            _ = try await reader.read(sourceObjectID: entry.sourceObjectID, directory: directory, lease: lease)
                            throw DefinitionDirectoryFailure.assertion
                        } catch AnyNativeImportedDefinitionError.changedIdentity(let refused) {
                            try self.require(Data(refused.utf8) == Data(entry.sourceObjectID.utf8))
                        }
                    }
                    try await self.patch(client, path: propertyPath,
                        body: .object(["set": .object(["xFormat.pinkhaHeart.sourceObjectID": .string(originalParentID)])]),
                        key: "parent-provenance-restore", work: work, lease: lease)
                    let edited = try await self.readAll(directory, reader: reader, lease: lease)
                    try self.checkEdited(edited, changedIDs: changedIDs)
                    try self.write(edited.content, work.appendingPathComponent("edited-definitions.json"))
                    try self.write(.object(["forgedTypeMappingRefused": .bool(true), "forgedPropertyMappingRefused": .bool(true),
                        "foreignSpaceRefused": .bool(true), "changedParentProvenanceRefused": .bool(true),
                        "unchangedOptionUnderChangedParentRefused": .bool(true), "parentProvenanceRestored": .bool(true),
                        "unchangedOptionMetadataDuringNegativeCase": .bool(true)]),
                        work.appendingPathComponent("negative-controls.json"))
                } else if phase == "edited-reopen" {
                    let edited = try await self.readAll(directory, reader: reader, lease: lease)
                    try self.checkEdited(edited, changedIDs: changedIDs)
                    let bytes = try self.encoded(edited.content)
                    try self.require(bytes == Data(contentsOf: work.appendingPathComponent("edited-definitions.json")))
                    try self.write(edited.content, work.appendingPathComponent("cold-edited-definitions.json"))
                    try await self.patch(client, path: typePath, body: .object(["name": .string(originalTypeName)]),
                        key: "type-name-restore", work: work, lease: lease)
                    try await self.patch(client, path: propertyPath, body: .object(["set": .object(restoredFields)]),
                        key: "property-and-option-restore", work: work, lease: lease)
                    let restored = try await self.readAll(directory, reader: reader, lease: lease)
                    try self.require(restored.matches.values.allSatisfy { $0 })
                    try self.require(self.encoded(restored.content) == Data(contentsOf: work.appendingPathComponent("baseline-definitions.json")))
                    try self.write(restored.content, work.appendingPathComponent("restored-definitions.json"))
                } else {
                    let restored = try await self.readAll(directory, reader: reader, lease: lease)
                    try self.require(restored.matches.values.allSatisfy { $0 })
                    let baseline = try Data(contentsOf: work.appendingPathComponent("baseline-definitions.json"))
                    try self.require(self.encoded(restored.content) == baseline)
                    try self.require(Data(contentsOf: work.appendingPathComponent("restored-definitions.json")) == baseline)
                    try self.write(restored.content, work.appendingPathComponent("cold-restored-definitions.json"))
                }
                return lease
            }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
        do {
            _ = try await reader.read(sourceObjectID: typeEntry.sourceObjectID, directory: directory, lease: lease)
            throw DefinitionDirectoryFailure.assertion
        } catch AnyHostError.sessionClosed { }
        try require(Data(contentsOf: planURL) == planBytes && Data(contentsOf: mappingsURL) == mappingBytes)
        let ledger = try XCTUnwrap(json(work.appendingPathComponent("write-ledger.json")).array)
        let expected = phase == "edit" ? 4 : 6
        try require(ledger.count == expected && ledger.allSatisfy { $0["stage"] == .string("confirmed") && $0["status"] == .integer(204) })
        try write(.object(["phase": .string(phase), "allEntries": .integer(Int64(directory.entries.count)),
            "typeEntries": .integer(1), "importedPropertyEntries": .integer(7), "embeddedOptions": .integer(4),
            "canonicalProperties": .integer(Int64(canonicalCount)),
            "unresolvedSourceDefinitions": .integer(Int64(directory.unresolvedSourceDefinitionIDs.count)),
            "revokedSessionReadRefused": .bool(true), "observedPatchCount": .integer(Int64(expected)),
            "sourceAdmissionPromoted": .bool(false), "wholeSpaceMigration": .bool(false),
            "conditionalSchemaConcurrencyClaim": .bool(false), "originalAccountModified": .bool(false)]),
            work.appendingPathComponent(phase + "-result.json"))
        print("PINKHA_NATIVE_DEFINITION_DIRECTORY_PHASE_PASS " + phase)
    }

    private func readAll(_ directory: AnyNativeImportedDefinitionDirectory, reader: AnyNativeImportedDefinitionStore,
                         lease: AnyHostLease) async throws -> ReadSet {
        var rows: [AnyJSON] = [], matches: [Data: Bool] = [:], outcomes: [Data: String] = [:]
        for entry in directory.entries {
            let snapshot = try await reader.read(sourceObjectID: entry.sourceObjectID, directory: directory, lease: lease)
            try require(snapshot.workspace == directory.binding.workspace && snapshot.generation == lease.generation)
            try require(snapshot.engineStartedAt == lease.engineStartedAt && !snapshot.permitsDestinationWrites)
            try require(snapshot.entry.address == entry.address)
            matches[Data(entry.sourceObjectID.utf8)] = snapshot.matchesOriginalDescriptor
            if let outcome = snapshot.nativeCreationOutcome { outcomes[Data(entry.sourceObjectID.utf8)] = outcome }
            rows.append(.object(["sourceObjectID": .string(entry.sourceObjectID),
                "sourceUniqueKey": .string(entry.sourceUniqueKey),
                "sourceSnapshotSHA256": .string(entry.sourceSnapshotSHA256),
                "sourceJSONViewSHA256": .string(entry.sourceJSONViewSHA256),
                "address": address(entry.address), "raw": snapshot.raw]))
        }
        return .init(content: .array(rows), matches: matches, outcomes: outcomes)
    }

    private func checkEdited(_ read: ReadSet, changedIDs: Set<Data>) throws {
        try require(Set(read.matches.filter { !$0.value }.map { $0.key }) == changedIDs)
        for id in changedIDs {
            try require(read.outcomes[id] == AnyPreparedMigrationReceipt.Outcome.committedModified.rawValue)
        }
    }

    private func refuseForgedNativeMapping(plan: AnyDestinationMigrationPlan, mappings: [AnyDestinationMigrationMapping],
                                          entry: AnyNativeImportedDefinitionEntry,
                                          reader: AnyNativeImportedDefinitionStore, lease: AnyHostLease) async throws {
        let sourceKey = try XCTUnwrap(entry.intent?.sourceKey)
        let index = try XCTUnwrap(mappings.firstIndex { Data($0.sourceKey.utf8) == Data(sourceKey.utf8) })
        var changed = mappings
        var raw = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(changed[index])).object)
        if case .type = entry.address {
            raw["objectID"] = .string("explicit-foreign-native-object")
            raw["recordIDs"] = .array([.string("explicit-foreign-native-object")])
        } else {
            raw["recordIDs"] = .array([.string("explicit-foreign-native-record")])
        }
        changed[index] = try JSONDecoder().decode(AnyDestinationMigrationMapping.self, from: encoded(.object(raw)))
        let directory = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: changed)
        do {
            _ = try await reader.read(sourceObjectID: entry.sourceObjectID, directory: directory, lease: lease)
            throw DefinitionDirectoryFailure.assertion
        } catch AnyNativeImportedDefinitionError.changedIdentity(let id) {
            try require(Data(id.utf8) == Data(entry.sourceObjectID.utf8))
        }
    }

    private func patch(_ client: AnyHTTPClient, path: [String], body: AnyJSON,
                       key: String, work: URL, lease: AnyHostLease) async throws {
        let url = work.appendingPathComponent("write-ledger.json")
        var rows = FileManager.default.fileExists(atPath: url.path) ? try XCTUnwrap(json(url).array) : []
        try require(!rows.contains { $0["key"] == .string(key) } && rows.count < 6)
        let bodySHA = AnyContentDigest.sha256(try encoded(body))
        rows.append(.object(["key": .string(key), "method": .string("PATCH"),
            "path": .array(path.map(AnyJSON.string)), "bodySHA256": .string(bodySHA), "stage": .string("dispatching")]))
        try write(.array(rows), url)
        do {
            let response = try await client.requestJSONResponse(method: "PATCH", path: path, body: body,
                validateResponse: { try await lease.validate() }, authorize: { try await lease.validate() })
            try require(response.statusCode == 204)
            var row = try XCTUnwrap(rows[rows.count - 1].object)
            row["stage"] = .string("confirmed"); row["status"] = .integer(Int64(response.statusCode))
            rows[rows.count - 1] = .object(row)
            try write(.array(rows), url)
        } catch {
            var row = try XCTUnwrap(rows[rows.count - 1].object)
            row["stage"] = .string("unconfirmed"); row["errorType"] = .string(String(describing: type(of: error)))
            rows[rows.count - 1] = .object(row)
            try write(.array(rows), url)
            throw error
        }
    }

    private func address(_ value: AnyNativeImportedDefinitionAddress) -> AnyJSON {
        switch value {
        case .type(let id): .object(["kind": .string("type"), "objectID": .string(id)])
        case .property(let ownerKind, let key): .object(["kind": .string("property"),
            "ownerKind": .string(ownerKind.rawValue), "ownerID": .string(key.ownerID), "propertyID": .string(key.propertyID)])
        case .option(let ownerKind, let key, let id): .object(["kind": .string("option"),
            "ownerKind": .string(ownerKind.rawValue), "ownerID": .string(key.ownerID),
            "propertyID": .string(key.propertyID), "optionID": .string(id)])
        }
    }

    private func encoded(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    private func json(_ url: URL) throws -> AnyJSON { try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: url)) }
    private func write(_ value: AnyJSON, _ url: URL) throws { try encoded(value).write(to: url, options: .atomic) }
    private func require(_ value: @autoclosure () throws -> Bool) throws {
        guard try value() else { XCTFail("Native definition directory invariant failed"); throw DefinitionDirectoryFailure.assertion }
    }
    private enum DefinitionDirectoryFailure: Error { case assertion }
}
#endif
