#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class AnyDestinationNativeSourceFactsTests: XCTestCase, @unchecked Sendable {
    func testOriginalSourceFactsReadSignedNativeRowsAndColdReopenWithoutRestamping() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_NATIVE_SOURCE_FACTS_FIXTURE"],
              let workPath = env["PINKHA_NATIVE_SOURCE_FACTS_WORK"],
              let phase = env["PINKHA_NATIVE_SOURCE_FACTS_PHASE"], ["read", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the owned retained-account source-facts controller.")
        }
        let runtime = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        try require(runtime["binarySHA256"] == .string("1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"))
        try require(runtime["componentScope"] == .string("retained-original-source-facts-v1"))
        try require(runtime["outboundDeniedByOS"] == .bool(true) && runtime["networkPeerCount"] == .integer(0))
        let fixture = try NativeCanonicalSupplementFixture.load()
        let directory = try AnyNativeImportedSourceFactsDirectory(plan: fixture.plan, mappings: fixture.mappings)
        try require(directory.entries.count == 2 && !directory.permitsSourceAdmission)
        let account = try XCTUnwrap(runtime["accountID"]?.string), space = try XCTUnwrap(runtime["spaceID"]?.string)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        try require(workspace == fixture.plan.binding.workspace)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(runtime["baseURL"]?.string))),
            expectedAccountID: account)
        let reader = try AnyNativeImportedSourceFactsStore(client: client, workspace: workspace)
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let lease: AnyHostLease
        do {
            lease = try await session.perform { lease in
                var rows: [AnyJSON] = [], totalBlocks = 0, totalHistoricalValues = 0
                for entry in directory.entries {
                    let snapshot = try await reader.read(sourceObjectID: entry.sourceObjectID,
                        directory: directory, lease: lease)
                    try self.require(snapshot.workspace == workspace && snapshot.generation == lease.generation)
                    try self.require(snapshot.engineStartedAt == lease.engineStartedAt)
                    try self.require(!snapshot.permitsDestinationWrites && !snapshot.originalHistoryReconstructed)
                    try self.require(!snapshot.original.originalHistoryReconstructed)
                    try self.require(Data(snapshot.sourceAccountID.utf8) == Data(fixture.plan.source.accountID.utf8))
                    try self.require(Data(snapshot.creation.destinationAuthor.utf8) == Data(account.utf8))
                    try self.require(Data(snapshot.sourceAccountID.utf8) != Data(snapshot.creation.destinationAuthor.utf8))
                    try self.require(snapshot.creation.changeID == entry.mapping.signedChangeIDs[0])
                    let original = snapshot.original.snapshot
                    let stem = "snapshot-" + AnyContentDigest.sha256(Data(entry.sourceObjectID.utf8))
                    try self.require(original.protobufBytes == Data(contentsOf: fixture.bundle.appendingPathComponent(stem + ".pb")))
                    try self.require(original.jsonViewBytes == Data(contentsOf: fixture.bundle.appendingPathComponent(stem + ".json")))
                    try self.require(original.snapshotSHA256 == entry.sourceSnapshotSHA256 && original.viewSHA256 == entry.sourceJSONViewSHA256)
                    let historical = snapshot.original.historicalValues.map { value in AnyJSON.object([
                        "sourceRelationKey": .string(value.sourceRelationKey), "nativePropertyID": .string(value.destinationPropertyID),
                        "originalValue": value.originalValue]) }
                    totalBlocks += original.blocks.count; totalHistoricalValues += historical.count
                    rows.append(.object([
                        "sourceObjectID": .string(entry.sourceObjectID), "sourceSnapshotSHA256": .string(original.snapshotSHA256),
                        "sourceJSONViewSHA256": .string(original.viewSHA256), "sourceAccountID": .string(snapshot.sourceAccountID),
                        "sourceSpaceID": .string(original.sourceSpaceID), "sourceWitnessSHA256": .string(snapshot.sourceWitnessSHA256),
                        "sourceManifestSHA256": .string(snapshot.sourceManifestSHA256),
                        "originalSnapshotBase64": .string(original.protobufBytes.base64EncodedString()),
                        "originalJSONBase64": .string(original.jsonViewBytes.base64EncodedString()),
                        "originalDetails": .object(original.details), "originalBlocks": .array(original.blocks.map(\.raw)),
                        "originalDepthFirstIDs": .array(original.depthFirstIDs.map(AnyJSON.string)),
                        "originalHistoricalValues": .array(historical),
                        "destinationObjectID": .string(entry.objectID), "dataset": .string(entry.dataset), "recordID": .string(entry.recordID),
                        "destinationCreation": .object(["changeID": .string(snapshot.creation.changeID),
                            "author": .string(snapshot.creation.destinationAuthor), "authorClockSeconds": .integer(snapshot.creation.destinationAuthorClockSeconds)]),
                        "nativeRecord": snapshot.raw]))
                }
                let bytes = try AnyDestinationDefinitionChecks.bytes(.array(rows))
                if phase == "reopen" { try self.require(bytes == Data(contentsOf: work.appendingPathComponent("read-source-facts.json"))) }
                try bytes.write(to: work.appendingPathComponent(phase + "-source-facts.json"))
                let first = try XCTUnwrap(directory.entries.first)
                var mappings = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(fixture.mappings)).array)
                let index = try XCTUnwrap(mappings.firstIndex { $0["sourceKey"] == .string(first.sourceKey) })
                var changed = try XCTUnwrap(mappings[index].object)
                let forged = String(repeating: "0", count: 64)
                try self.require(first.mapping.fingerprint != forged)
                changed["fingerprint"] = .string(forged); mappings[index] = .object(changed)
                let forgedDirectory = try AnyNativeImportedSourceFactsDirectory(plan: fixture.plan,
                    mappings: JSONDecoder().decode([AnyDestinationMigrationMapping].self,
                        from: AnyDestinationDefinitionChecks.bytes(.array(mappings))))
                do {
                    _ = try await reader.read(sourceObjectID: first.sourceObjectID, directory: forgedDirectory, lease: lease)
                    throw NativeSourceFactsFailure.assertion
                } catch AnyNativeImportedSourceFactsError.changedNativeRecord(let source) {
                    try self.require(Data(source.utf8) == Data(first.sourceObjectID.utf8))
                }
                let foreign = try AnyNativeImportedSourceFactsStore(client: client,
                    workspace: .init(accountID: account, spaceID: space + "-foreign"))
                do {
                    _ = try await foreign.read(sourceObjectID: first.sourceObjectID, directory: directory, lease: lease)
                    throw NativeSourceFactsFailure.assertion
                } catch AnyHostError.wrongWorkspace { }
                try AnyDestinationDefinitionChecks.bytes(.object([
                    "phase": .string(phase), "sourceFactRecords": .integer(2),
                    "originalBlocks": .integer(Int64(totalBlocks)), "originalDerivedValues": .integer(Int64(totalHistoricalValues)),
                    "originalBytesEqual": .bool(true), "currentRowsEqualSignedCreation": .bool(true),
                    "forgedMappingFingerprintRefused": .bool(true), "foreignSpaceRefused": .bool(true),
                    "preparedOperations": .integer(0), "domainWriteOperationsRequested": .integer(0),
                    "historicalAuthorIsDestinationSigner": .bool(false), "originalHistoryReconstructed": .bool(false),
                    "sourceAdmissionPromoted": .bool(false), "wholeSpaceMigration": .bool(false)]))
                    .write(to: work.appendingPathComponent(phase + "-result.json"))
                return lease
            }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
        do {
            _ = try await reader.read(sourceObjectID: directory.entries[0].sourceObjectID, directory: directory, lease: lease)
            throw NativeSourceFactsFailure.assertion
        } catch AnyHostError.sessionClosed { }
        var result = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self,
            from: Data(contentsOf: work.appendingPathComponent(phase + "-result.json"))).object)
        result["revokedLeaseRefused"] = .bool(true)
        try AnyDestinationDefinitionChecks.bytes(.object(result)).write(to: work.appendingPathComponent(phase + "-result.json"))
        try fixture.requireRetainedInputsUnchanged()
        print("PINKHA_NATIVE_SOURCE_FACTS_PHASE_PASS " + phase)
    }

    private func require(_ condition: @autoclosure () throws -> Bool) throws {
        guard try condition() else { throw NativeSourceFactsFailure.assertion }
    }
}

enum NativeSourceFactsFailure: Error { case assertion }
#endif
