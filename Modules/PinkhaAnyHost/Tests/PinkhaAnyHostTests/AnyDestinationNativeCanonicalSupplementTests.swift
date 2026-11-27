#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class AnyDestinationNativeCanonicalSupplementTests: XCTestCase, @unchecked Sendable {
    func testEightOriginalCanonicalDescriptorsAndColdProcessKeepSourceValueMeaningSeparate() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_NATIVE_CANONICAL_FIXTURE"],
              let workPath = env["PINKHA_NATIVE_CANONICAL_WORK"],
              let phase = env["PINKHA_NATIVE_CANONICAL_PHASE"], ["read", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the owned retained-account canonical-definition controller.")
        }
        let runtime = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        try require(runtime["binarySHA256"] == .string("1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"))
        try require(runtime["componentScope"] == .string("retained-original-canonical-definitions-v1"))
        try require(runtime["outboundDeniedByOS"] == .bool(true) && runtime["networkPeerCount"] == .integer(0))
        let fixture = try NativeCanonicalSupplementFixture.load()
        let extra = try fixture.bindings()
        let directory = try AnyNativeImportedDefinitionDirectory(plan: fixture.plan, mappings: fixture.mappings,
            supplementalCanonicalDefinitions: extra)
        try require(directory.entries.count == 21 && directory.unresolvedSourceDefinitionIDs.count == 129)
        try require(!directory.permitsSourceAdmission && directory.supplementalCanonicalDefinitions == extra)
        let account = try XCTUnwrap(runtime["accountID"]?.string)
        let space = try XCTUnwrap(runtime["spaceID"]?.string)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        try require(workspace == fixture.plan.binding.workspace)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(runtime["baseURL"]?.string))),
            expectedAccountID: account)
        let reader = try AnyNativeImportedDefinitionStore(client: client, workspace: workspace)
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let lease: AnyHostLease
        do {
            lease = try await session.perform { lease in
                var rows: [AnyJSON] = []
                for canonical in extra {
                    let snapshot = try await reader.read(sourceObjectID: canonical.evidence.sourceObjectID,
                        directory: directory, lease: lease)
                    try self.require(snapshot.workspace == workspace && snapshot.generation == lease.generation)
                    try self.require(snapshot.engineStartedAt == lease.engineStartedAt && !snapshot.permitsDestinationWrites)
                    try self.require(snapshot.matchesOriginalDescriptor && snapshot.nativeCreationOutcome == nil)
                    try self.require(snapshot.raw == canonical.expectedNativeDescriptor)
                    let entry = snapshot.entry
                    try self.require(entry.sourceSnapshotSHA256 == canonical.evidence.snapshotSHA256)
                    try self.require(entry.sourceJSONViewSHA256 == canonical.evidence.viewSHA256)
                    let meaning = NativeCanonicalSupplementFixture.meaning(canonical.propertyID)
                    try self.require(entry.canonicalValueSemantics == meaning)
                    rows.append(.object(["sourceObjectID": .string(entry.sourceObjectID),
                        "sourceUniqueKey": .string(entry.sourceUniqueKey),
                        "sourceSnapshotSHA256": .string(entry.sourceSnapshotSHA256),
                        "sourceJSONViewSHA256": .string(entry.sourceJSONViewSHA256),
                        "nativeOwnerID": .string("any"), "nativePropertyID": .string(canonical.propertyID),
                        "valueSemantics": .string(meaning.rawValue), "raw": snapshot.raw]))
                }
                let bytes = try AnyDestinationDefinitionChecks.bytes(.array(rows))
                if phase == "reopen" {
                    try self.require(bytes == Data(contentsOf: work.appendingPathComponent("read-canonical.json")))
                }
                try bytes.write(to: work.appendingPathComponent(phase + "-canonical.json"))
                let foreign = try AnyNativeImportedDefinitionStore(client: client,
                    workspace: .init(accountID: account, spaceID: space + "-foreign"))
                do {
                    _ = try await foreign.read(sourceObjectID: extra[0].evidence.sourceObjectID,
                        directory: directory, lease: lease)
                    throw NativeCanonicalSupplementFailure.assertion
                } catch AnyHostError.wrongWorkspace { }
                return lease
            }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
        do {
            _ = try await reader.read(sourceObjectID: extra[0].evidence.sourceObjectID, directory: directory, lease: lease)
            throw NativeCanonicalSupplementFailure.assertion
        } catch AnyHostError.sessionClosed { }
        try fixture.requireRetainedInputsUnchanged()
        try AnyDestinationDefinitionChecks.bytes(.object([
            "phase": .string(phase), "newCanonicalDefinitions": .integer(8),
            "allDirectoryEntries": .integer(21), "unresolvedSourceDefinitions": .integer(129),
            "foreignSpaceRefused": .bool(true), "revokedLeaseRefused": .bool(true),
            "preparedOperations": .integer(0), "domainWrites": .integer(0),
            "originalHistoryValuesRestamped": .bool(false), "literalNativeIdentityEquivalenceClaim": .bool(false),
            "sourceAdmissionPromoted": .bool(false), "wholeSpaceMigration": .bool(false)]))
            .write(to: work.appendingPathComponent(phase + "-result.json"))
        print("PINKHA_NATIVE_CANONICAL_DEFINITION_PHASE_PASS " + phase)
    }

    private func require(_ condition: @autoclosure () throws -> Bool) throws {
        guard try condition() else { throw NativeCanonicalSupplementFailure.assertion }
    }
}
#endif
