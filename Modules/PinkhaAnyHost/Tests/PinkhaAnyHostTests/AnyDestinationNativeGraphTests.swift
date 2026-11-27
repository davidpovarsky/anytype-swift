#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// New typed reader over the already accepted original native relation edge.
/// No prepared migration, schema mutation or property write is performed here.
final class AnyDestinationNativeGraphTests: XCTestCase, @unchecked Sendable {
    func testRetainedOriginalGraphReadOnlyAdapterAndColdIdentity() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_NATIVE_GRAPH_FIXTURE"],
              let workPath = env["PINKHA_NATIVE_GRAPH_WORK"],
              let sourcePath = env["PINKHA_NATIVE_ORIGINAL156"],
              let phase = env["PINKHA_NATIVE_GRAPH_PHASE"],
              ["read", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the retained original graph adapter controller and source definitions.")
        }
        let fixture = try json(URL(fileURLWithPath: fixturePath))
        try require(fixture["binarySHA256"] == .string("1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"))
        try require(fixture["componentScope"] == .string("retained-original-native-graph-adapter-v1"))
        try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        let account = try XCTUnwrap(fixture["accountID"]?.string)
        let space = try XCTUnwrap(fixture["spaceID"]?.string)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(fixture["baseURL"]?.string))),
                                       expectedAccountID: account)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let expectedURL = work.appendingPathComponent("accepted-native-graph.json")
        let expectedBytes = try Data(contentsOf: expectedURL)
        let accepted = try JSONDecoder().decode(AnyJSON.self, from: expectedBytes)
        try require(accepted["sourceReceiptSHA256"] == .string("f7f4a5b34465907c3285229a266a488229a92eb1c3a7c04c5b4cdd162ed1b32b"))
        try require(accepted["sourceComparisonSHA256"] == .string("7c39a72aec3e9c87cef67ffabbe982cd76501f195d36aafd354bea13e5a71ac5"))
        try require(accepted["sourceGraphAlreadyAccepted"] == .bool(true))
        let expected = try XCTUnwrap(accepted["actualLinkIndex"]?["forward"]?["links"]?.array)
        let reverse = try XCTUnwrap(accepted["actualLinkIndex"]?["reverse"]?["object"]?.array)
        try require(expected.count == 1 && reverse == expected)
        try require(accepted["actualLinkIndex"]?["reverse"]?["parts"] == .array([]))
        try require(accepted["actualLinkIndex"]?["emptySource"]?["links"] == .array([]))
        let expectedEdge = expected[0]
        let object = try XCTUnwrap(expectedEdge["source"]?["objectId"]?.string)
        let target = try XCTUnwrap(expectedEdge["target"]?["objectId"]?.string)
        let property = try XCTUnwrap(expectedEdge["source"]?["recordId"]?.string)
        try require(expectedEdge["source"]?["spaceId"] == .string(space))
        try require(expectedEdge["target"]?["spaceId"] == .string(space))
        try require(expectedEdge["source"]?["dataset"] == .string("prop"))
        try require(expectedEdge["kind"] == .string("relation") && object != target)
        let outgoingBinding = try sourceBinding(root: sourcePath, role: .outgoingLinks)
        let incomingBinding = try sourceBinding(root: sourcePath, role: .backlinks)
        let reader = try AnyNativeComputedRelationStore(client: client, workspace: workspace)
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
        let result: (AnyJSON, AnyHostLease)
        do {
            result = try await session.perform { lease in
                let read = try await reader.read(outgoingBinding, objectID: object, lease: lease)
                let back = try await reader.read(incomingBinding, objectID: target, lease: lease)
                let empty = try await reader.read(outgoingBinding, objectID: target, lease: lease)
                for snapshot in [read, back, empty] {
                    try self.require(snapshot.workspace == workspace && snapshot.generation == lease.generation)
                    try self.require(snapshot.engineStartedAt == lease.engineStartedAt)
                    try self.require(!snapshot.permitsDestinationWrites)
                }
                guard case .outgoing(let links) = read.value,
                      case .incoming(let backlinks) = back.value,
                      case .outgoing(let emptyLinks) = empty.value else { throw NativeGraphFailure.assertion }
                try self.require(!links.truncated && !backlinks.truncated && !emptyLinks.truncated)
                try self.require(links.links.count == 1 && backlinks.object.count == 1)
                try self.require(backlinks.parts.isEmpty && emptyLinks.links.isEmpty)
                let out = try self.edge(links.links[0], expected: expectedEdge)
                let incoming = try self.edge(backlinks.object[0], expected: expectedEdge)
                // The new typed narrowing API must preserve the native source
                // property, its declaring owner and the exact target URI.
                let narrowed = try await AnyNativeObjectLinks(client: client).links(spaceID: space, objectID: object,
                    selection: .property(property), kind: "relation", limit: 500, requireComplete: true,
                    authorize: { try await lease.validate() })
                try self.require(narrowed.links.count == 1 && !narrowed.truncated)
                let narrow = try self.edge(narrowed.links[0], expected: expectedEdge)
                try self.require(out == incoming && out == narrow)
                let proof: AnyJSON = .object([
                    "contract": .string("pinkha-retained-original-graph-adapter-v1"),
                    "accountID": .string(account), "spaceID": .string(space),
                    "outgoing": out, "incoming": incoming, "narrowedOutgoing": narrow,
                    "emptyTargetOutgoing": .array([]), "newDomainWrites": .integer(0),
                    "retainedNativeGraphProofSHA256": .string("7c39a72aec3e9c87cef67ffabbe982cd76501f195d36aafd354bea13e5a71ac5"),
                    "sourceLinksSHA256": .string(outgoingBinding.evidence.snapshotSHA256),
                    "sourceLinksJSONViewSHA256": .string(outgoingBinding.evidence.viewSHA256),
                    "sourceLinksObjectID": .string(outgoingBinding.evidence.sourceObjectID),
                    "sourceBacklinksSHA256": .string(incomingBinding.evidence.snapshotSHA256),
                    "sourceBacklinksJSONViewSHA256": .string(incomingBinding.evidence.viewSHA256),
                    "sourceBacklinksObjectID": .string(incomingBinding.evidence.sourceObjectID),
                    "indexResponseTruncated": .bool(false), "expectedRelationDelivered": .bool(true),
                    "replicationCompletenessClaim": .bool(false),
                    "sourceAdmissionPromoted": .bool(false), "wholeSpaceMigration": .bool(false)
                ])
                return (proof, lease)
            }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
        do {
            _ = try await reader.read(outgoingBinding, objectID: object, lease: result.1)
            XCTFail("A revoked session delivered computed graph values")
            throw NativeGraphFailure.assertion
        } catch AnyHostError.sessionClosed { }
        try require(Data(contentsOf: expectedURL) == expectedBytes)
        let bytes = try encoder.encode(result.0)
        if phase == "reopen" {
            try require(bytes == Data(contentsOf: work.appendingPathComponent("read-graph.json")))
        }
        try bytes.write(to: work.appendingPathComponent(phase + "-graph.json"), options: .withoutOverwriting)
        print("NATIVE_GRAPH_ADAPTER new_domain_writes=0 retained_outgoing=1 retained_backlinks=1 exact_source_property=true revoked_lease_refused=true source_admission=false phase=" + phase)
    }

    private func edge(_ value: AnyNativeObjectLink, expected: AnyJSON) throws -> AnyJSON {
        try require(value.kind == "relation")
        try require(value.source.spaceID == expected["source"]?["spaceId"]?.string)
        try require(value.source.objectID == expected["source"]?["objectId"]?.string)
        try require(value.source.dataset == "prop" && value.source.recordID == expected["source"]?["recordId"]?.string)
        try require(value.source.typeID == expected["source"]?["typeId"]?.string && value.source.field == nil)
        try require(value.target.kind == .object && value.target.spaceID == expected["target"]?["spaceId"]?.string)
        try require(value.target.objectID == expected["target"]?["objectId"]?.string)
        try require(value.target.uri == expected["target"]?["uri"]?.string)
        try require(value.target.dataset == nil && value.target.recordID == nil && value.target.propID == nil)
        try require(value.target.identity == nil && value.target.fileID == nil)
        return .object([
            "kind": .string(value.kind),
            "source": .object(["spaceId": .string(value.source.spaceID), "objectId": .string(value.source.objectID),
                               "dataset": .string(value.source.dataset), "recordId": .string(value.source.recordID),
                               "typeId": .string(try XCTUnwrap(value.source.typeID))]),
            "target": .object(["uri": .string(value.target.uri), "kind": .string("o"),
                               "spaceId": .string(try XCTUnwrap(value.target.spaceID)),
                               "objectId": .string(try XCTUnwrap(value.target.objectID))])
        ])
    }

    private func sourceBinding(root: String, role: AnyHeartNativeComputedRelationBinding.Role) throws -> AnyHeartNativeComputedRelationBinding {
        let stem = role == .outgoingLinks
            ? "snapshot-499c3540377351bb70bd1c7cd9eaaafc40acc45dffb31820ed89110e0e592fb4"
            : "snapshot-c9c4bed807a227f8ecfe6d68093e99c89b48814361c328f59b5533513e082b86"
        let directory = URL(fileURLWithPath: root, isDirectory: true).appendingPathComponent("bundle")
        let jsonBytes = try Data(contentsOf: directory.appendingPathComponent(stem + ".json"))
        let protobufBytes = try Data(contentsOf: directory.appendingPathComponent(stem + ".pb"))
        let raw = try JSONDecoder().decode(AnyJSON.self, from: jsonBytes)
        let view = try AnyHeartNativeSnapshotView(jsonView: jsonBytes, snapshotBytes: protobufBytes,
            sourceSpaceID: XCTUnwrap(raw["SpaceID"]?.string), sourceObjectID: XCTUnwrap(raw["ObjectID"]?.string))
        let binding = try AnyHeartNativeComputedRelationBinding(evidence: .init(snapshot: view))
        try require(binding.role == role && !binding.permitsDestinationWrites)
        return binding
    }

    private func json(_ path: URL) throws -> AnyJSON {
        try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: path))
    }
    private func require(_ condition: @autoclosure () throws -> Bool,
                         file: StaticString = #filePath, line: UInt = #line) throws {
        guard try condition() else {
            XCTFail("Native graph adapter contract assertion", file: file, line: line)
            throw NativeGraphFailure.assertion
        }
    }
}
private enum NativeGraphFailure: Error { case assertion }
#endif
