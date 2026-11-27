#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf
import XCTest
@testable import ProtobufMessages

/// These are captured frames from the actual native generated-gRPC acceptance
/// run. Replaying them here qualifies the Swift protobuf/client boundary only;
/// it never substitutes for a live native account or Apple bridge acceptance.
@MainActor
final class PinkhaHeartCutoverInteropTests: XCTestCase {
    private typealias Wire = Anytype_PinkhaTorahCutover

    func testAllFiveSwiftMethodsDecodeExactCapturedNativeFrames() async throws {
        let root = try frameRoot()
        let beginBytes = try Data(contentsOf: root.appendingPathComponent("begin-request.pb"))
        let begin = try Wire.RecordRequest(serializedBytes: beginBytes)
        let importBytes = try Data(contentsOf: root.appendingPathComponent("frozen-import-request.pb"))
        let imported = try Wire.OperationRequest(serializedBytes: importBytes)
        let associationBytes = try Data(contentsOf: root.appendingPathComponent("association-append-request.pb"))
        let association = try Wire.OperationRequest(serializedBytes: associationBytes)
        let source = try Wire.SourceReadResponse(serializedBytes: data(root, "source-read-response.pb"))
        let read = try Wire.ReadResponse(serializedBytes: data(root, "sealed-unlinked-read-response.pb"))
        let appended = try Wire.AppendResponse(serializedBytes: data(root, "begin-response.pb"))
        let importedResponse = try Wire.OperationResponse(serializedBytes: data(root, "frozen-import-response.pb"))
        let associationResponse = try Wire.OperationResponse(serializedBytes: data(root, "association-append-response.pb"))

        XCTAssertEqual(try begin.serializedData(), beginBytes)
        XCTAssertEqual(try imported.serializedData(), importBytes)
        XCTAssertEqual(try association.serializedData(), associationBytes)
        XCTAssertEqual(begin.scope, imported.scope)
        XCTAssertEqual(begin.scope, association.scope)
        XCTAssertEqual(begin.planID, read.snapshot.state.planID)
        XCTAssertEqual(begin.plan, read.snapshot.state.plan)
        XCTAssertEqual(source.snapshot.source.value, begin.plan.legacyValue)
        XCTAssertEqual(source.snapshot.source.value, read.snapshot.source.value)
        XCTAssertEqual(begin.plan.facts.count, 2)
        XCTAssertEqual(read.snapshot.metadataClaims.count, 4)
        XCTAssertEqual(read.snapshot.originalClaims.count, 3)
        XCTAssertEqual(read.snapshot.state.status, .sealed)
        XCTAssertTrue(read.snapshot.completeLocal)
        XCTAssertEqual(importedResponse.receipt.disposition.rawValue, 2)
        XCTAssertTrue(importedResponse.receipt.changeID.isEmpty)
        XCTAssertEqual(associationResponse.receipt.disposition.rawValue, 1)
        XCTAssertFalse(associationResponse.receipt.changeID.isEmpty)

        let account = try XCTUnwrap(appended.receipt.resolution.claims.first).record.authorID
        XCTAssertFalse(account.isEmpty)
        for claim in read.snapshot.metadataClaims {
            XCTAssertEqual(claim.record.authorID, account)
            XCTAssertEqual(claim.record.spaceID, begin.scope.spaceID)
            XCTAssertEqual(claim.record.objectID, begin.scope.objectID)
        }
        for fact in begin.plan.facts {
            let matching = read.snapshot.originalClaims.filter { $0.operation.payload == fact.payload }
            XCTAssertEqual(matching.count, 1, "each original opaque payload remains exact after Seal and unlink")
        }

        let owner = PinkhaNativeReadLifetime()
        let selected = owner.beforeInvocation(name: "AccountSelect", request: Anytype_Rpc.Account.Select.Request())
        owner.completedInvocation(selected, response: Anytype_Rpc.Account.Select.Response.with {
            $0.account = .with { $0.id = account; $0.status.statusType = .active }
        })
        let opened = owner.beforeInvocation(name: "WorkspaceOpen",
            request: Anytype_Rpc.Workspace.Open.Request.with { $0.spaceID = begin.scope.spaceID })
        owner.completedInvocation(opened, response: Anytype_Rpc.Workspace.Open.Response.with {
            $0.info.workspaceObjectID = "captured-frame-boundary-only"
        })
        let lease = try owner.lease(forOpenedSpaceID: begin.scope.spaceID)
        let hash = try XCTUnwrap(ProcessInfo.processInfo.environment["PINKHA_CUTOVER_NATIVE_RPC_MANIFEST"])
        let profile = try PinkhaHeartCutoverProfile(sourceManifestSHA256: hash,
            runtimeVersion: "captured-frames-only:" + hash)
        var calls: [PinkhaHeartCutoverMethod] = []
        let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, bytes in
            calls.append(method)
            switch method {
            case .sourceRead:
                XCTAssertEqual(try Wire.Scope(serializedBytes: bytes), begin.scope)
                return try self.data(root, "source-read-response.pb")
            case .read:
                XCTAssertEqual(try Wire.Scope(serializedBytes: bytes), begin.scope)
                return try self.data(root, "sealed-unlinked-read-response.pb")
            case .append:
                XCTAssertEqual(bytes, beginBytes)
                return try self.data(root, "begin-response.pb")
            case .importFact:
                XCTAssertEqual(bytes, importBytes)
                return try self.data(root, "frozen-import-response.pb")
            case .associationAppend:
                XCTAssertEqual(bytes, associationBytes)
                return try self.data(root, "association-append-response.pb")
            }
        }), profile: profile)
        let actualSource = try await client.source(begin.scope, lease: lease)
        let actualRead = try await client.read(begin.scope, lease: lease)
        let actualAppend = try await client.append(begin, lease: lease)
        let actualImport = try await client.importFact(imported, lease: lease)
        let actualAssociation = try await client.associationAppend(association, lease: lease)
        XCTAssertEqual(actualSource, source.snapshot)
        XCTAssertEqual(actualRead, read.snapshot)
        XCTAssertEqual(actualAppend, appended.receipt)
        XCTAssertEqual(actualImport, importedResponse.receipt)
        XCTAssertEqual(actualAssociation, associationResponse.receipt)
        XCTAssertEqual(calls, [.sourceRead, .read, .append, .importFact, .associationAppend])
    }

    func testCanonicalIdentityMatchesEveryCapturedSignedClaim() throws {
        let root = try frameRoot()
        let begin = try Wire.RecordRequest(serializedBytes: data(root, "begin-request.pb"))
        let snapshot = try Wire.ReadResponse(serializedBytes: data(root, "sealed-unlinked-read-response.pb")).snapshot
        XCTAssertEqual(snapshot.metadataClaims.count, 4)
        XCTAssertEqual(snapshot.originalClaims.count, 3)
        XCTAssertEqual(Set(snapshot.metadataClaims.map { $0.record.kind.rawValue }), [1, 2, 3])
        XCTAssertEqual(Set(snapshot.originalClaims.map { $0.operation.kind.rawValue }), [1, 2])
        for claim in snapshot.metadataClaims {
            let record = claim.record
            var request = Wire.RecordRequest.with {
                $0.scope = begin.scope; $0.scope.spaceID = record.spaceID; $0.scope.objectID = record.objectID
                $0.recordID = record.recordID; $0.kind = record.kind; $0.planID = record.planID
                if record.hasPlan { $0.plan = record.plan }
                $0.factID = record.factID; $0.importClaimID = record.importClaimID
                $0.imported = record.imported; $0.sourceHeads = record.sourceHeads
                $0.nativeChanges = record.nativeChanges; $0.importRecords = record.importRecords
            }
            XCTAssertEqual(try PinkhaHeartCutoverClient.claimIdentity(request, author: record.authorID), claim.claimID)
            XCTAssertEqual(claim.digest, String(claim.claimID.suffix(64)))
            request.imported.reverse(); request.sourceHeads.reverse()
            request.nativeChanges.reverse(); request.importRecords.reverse()
            if request.hasPlan { request.plan.facts.reverse() }
            XCTAssertEqual(try PinkhaHeartCutoverClient.claimIdentity(request, author: record.authorID), claim.claimID)
        }
        for claim in snapshot.originalClaims {
            let operation = claim.operation
            var request = Wire.OperationRequest.with {
                $0.scope = begin.scope; $0.scope.spaceID = operation.spaceID
                $0.scope.objectID = operation.target.objectID
                $0.operationID = operation.operationID; $0.kind = operation.kind
                $0.blockID = operation.target.blockID; $0.source = operation.source
                $0.payload = operation.payload; $0.observedClaimIds = operation.observedClaimIds
            }
            XCTAssertEqual(try PinkhaHeartCutoverClient.claimIdentity(request, author: operation.authorID), claim.claimID)
            XCTAssertEqual(claim.digest, String(claim.claimID.suffix(64)))
            request.observedClaimIds += request.observedClaimIds.reversed()
            XCTAssertEqual(try PinkhaHeartCutoverClient.claimIdentity(request, author: operation.authorID), claim.claimID)
        }
        XCTAssertEqual(snapshot.metadataReceipts.count, 4)
        XCTAssertEqual(snapshot.originalReceipts.count, 3)
        for receipt in snapshot.metadataReceipts + snapshot.originalReceipts {
            XCTAssertTrue(PinkhaHeartCutoverProfile.nativeChangeID(receipt.changeID))
        }
    }

    private func frameRoot() throws -> URL {
        let value = try XCTUnwrap(ProcessInfo.processInfo.environment["PINKHA_CUTOVER_NATIVE_WIRE_ROOT"],
            "the qualification controller must bind a passed native receipt and all exact frame hashes")
        let root = URL(fileURLWithPath: value, isDirectory: true)
        XCTAssertEqual(root.resolvingSymlinksInPath().path, root.path)
        return root
    }

    private func data(_ root: URL, _ name: String) throws -> Data {
        let value = try Data(contentsOf: root.appendingPathComponent(name))
        XCTAssertFalse(value.isEmpty)
        XCTAssertLessThanOrEqual(value.count, 4 * 1_024 * 1_024)
        return value
    }
}
#endif
