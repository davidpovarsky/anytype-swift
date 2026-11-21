#if PINKHA_AUTHORIZED_READ_CANDIDATE
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaKit
import PinkhaAnyRuntime

/// One new real iOS C-library/managed-HTTP/owned-host/shared-reader journey.
/// It does not rerun the accepted runtime lifecycle methods or claim full T2.
@MainActor
final class AnyAuthorizedOperationReadRuntimeTests: XCTestCase {
    func testManagedNativeAuthorizedReadPreservesBytesAcrossBlockDeletionAndColdReopen() async throws {
        XCTAssertEqual(AnyEmbeddedBuild.linked, .pinkhaNativeV1)
        let runtime = AnyEmbeddedRuntime.shared
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(
            "pinkha-authorized-read-" + UUID().uuidString, isDirectory: true)
        var owner: AnyApplicationSession?
        var cleanupClient: AnyHTTPClient?
        var ownedSpaceID: String?
        do {
            let boot = try await runtime.start(dataDirectory: directory, network: .official, build: .linked)
            let auth = try await authenticate(runtime, boot: boot)
            let client = try boot.dataClient(expectedAccountID: auth.accountID)
            cleanupClient = client
            let createdSpace = try await client.requestJSON(method: "POST", path: ["v1", "spaces"],
                body: .object(["name": .string("Disposable authorized operation read")]))
            let spaceID = try XCTUnwrap(createdSpace["id"]?.string)
            ownedSpaceID = spaceID
            let workspace = try AnyTorahWorkspace(accountID: auth.accountID, spaceID: spaceID)
            let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
            owner = session
            let reader = try await AnyHostAuthorizedTorahOperationReader(client: client, session: session)
            XCTAssertEqual(reader.scope.sessionGeneration, session.generation)
            let repository = try AnyGuardedTorahClaimsRepository(client: client, spaceID: spaceID)
            let capabilities = try await repository.verifyCapabilities()
            XCTAssertTrue(capabilities.nativeAuthorizedOperationRead,
                          "This selected method requires the real separately qualified read candidate.")
            let operationID = intentID()

            // Read on a fresh Space must not install its protected history.
            await requireReadError(.historyUnavailable, reader: reader, operationID: operationID)
            do {
                _ = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", spaceID, "bundles", AnyGuardedTorahCapabilities.bundleID])
                XCTFail("A read implicitly installed a private bundle.")
            } catch let error as AnyEngineError {
                XCTAssertEqual(error, .http(status: 404, code: "bundle.not_found"))
            }
            try await session.perform { lease in
                try await repository.install { try await lease.validate() }
            }
            let absent = try await reader.readOperation(operationID: operationID)
            XCTAssertEqual(absent.scope, reader.scope)
            XCTAssertEqual(absent.outcome, .absentInVerifiedLocalSnapshot)
            XCTAssertTrue(absent.variants.isEmpty)

            let page = try await client.requestJSON(method: "POST", path: ["v1", "spaces", spaceID, "objects"],
                body: .object(["type": .string("page"),
                    "initialProperties": .object(["any": .object(["name": .string("מסמך בדיקת קריאה")])])]))
            let objectID = try XCTUnwrap(page["objectId"]?.string)
            let blocks = ["v1", "spaces", spaceID, "objects", objectID, "editor", "editor_blocks", "blocks"]
            let block = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", spaceID, "pinkha", "objects", objectID, "editor", "editor_blocks", "blocks"],
                body: .object(["type": .string("paragraph"), "text": .string("פסקה מקורית")]))
            let blockID = try XCTUnwrap(block["recordIds"]?.array?.first?.string)
            let operation = try AnyTorahOperation(operationID: operationID, spaceID: spaceID,
                authorID: auth.accountID, kind: .add, targetObjectID: objectID, targetBlockID: blockID,
                providerID: "sefaria", canonicalRef: "Genesis.1.1",
                payload: Data([0, 255, 1]) + Data("מקור מקורי\n".utf8), observed: [])
            let append = try await session.perform { lease in
                try await repository.append(operation) { try await lease.validate() }
            }
            XCTAssertTrue(append.created)
            let changeID = try XCTUnwrap(append.changeID)
            let live = try await reader.readOperation(operationID: operationID)
            try requireExact(live, reader: reader, operation: operation,
                             changeID: changeID, state: .liveBlock)

            let deleted = try await client.requestJSON(method: "DELETE", path: blocks + [blockID])
            XCTAssertEqual(deleted["recordIds"]?.array, [.string(blockID)])
            XCTAssertFalse(try XCTUnwrap(deleted["changeId"]?.string).isEmpty)
            let unreachable = try await reader.readOperation(operationID: operationID)
            try requireExact(unreachable, reader: reader, operation: operation,
                             changeID: changeID, state: .unreachableBlock)
            XCTAssertNotEqual(unreachable.nativeSnapshotToken, live.nativeSnapshotToken)

            // The actual application owner drains before the actual C runtime
            // stops. Restore the same disposable account into the original disk.
            await session.revokeAndDrain()
            await runtime.stop(expectedGeneration: boot.generation)
            let reopenedBoot = try await runtime.start(dataDirectory: directory, network: .official, build: .linked)
            let restored = try await authenticate(runtime, boot: reopenedBoot, mnemonic: auth.mnemonic)
            XCTAssertEqual(restored.accountID, auth.accountID)
            let reopenedClient = try reopenedBoot.dataClient(expectedAccountID: auth.accountID)
            cleanupClient = reopenedClient
            let reopenedSession = try await AnyApplicationSession.connect(client: reopenedClient, workspace: workspace)
            owner = reopenedSession
            let reopenedReader = try await AnyHostAuthorizedTorahOperationReader(
                client: reopenedClient, session: reopenedSession)
            XCTAssertNotEqual(reopenedReader.scope.sessionGeneration, reader.scope.sessionGeneration)
            let reopened = try await reopenedReader.readOperation(operationID: operationID)
            try requireExact(reopened, reader: reopenedReader, operation: operation,
                             changeID: changeID, state: .unreachableBlock)
            XCTAssertEqual(reopened.variants, unreachable.variants)
            await requireReadError(.accountChanged, reader: reader, operationID: operationID)
            do {
                _ = try await AnyHostAuthorizedTorahOperationReader(client: client, session: session)
                XCTFail("A closed owner constructed a new private-operation reader.")
            } catch {
                XCTAssertEqual(error as? TorahOperationReadError, .accountChanged)
            }

            _ = try await reopenedClient.requestJSON(method: "DELETE",
                path: ["v1", "spaces", spaceID, "objects", objectID])
            await requireReadError(.targetStateUnavailable, reader: reopenedReader, operationID: operationID)
            await reopenedSession.revokeAndDrain()
            _ = try await reopenedClient.requestJSON(method: "DELETE", path: ["v1", "spaces", spaceID])
            ownedSpaceID = nil
            _ = try await runtime.executeControl(.signOut, expectedGeneration: reopenedBoot.generation)
            await runtime.stop(expectedGeneration: reopenedBoot.generation)
            try FileManager.default.removeItem(at: directory)
        } catch {
            await owner?.revokeAndDrain()
            if let client = cleanupClient, let spaceID = ownedSpaceID {
                _ = try? await client.requestJSON(method: "DELETE", path: ["v1", "spaces", spaceID])
            }
            await runtime.stop()
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    private func authenticate(_ runtime: AnyEmbeddedRuntime, boot: AnyEmbeddedSession,
                              mnemonic: String? = nil) async throws -> (accountID: String, mnemonic: String) {
        var fields: [String: AnyJSON] = [:]
        if let mnemonic { fields = ["mnemonic": .string(mnemonic), "index": .integer(1)] }
        let bytes = try await runtime.executeControl(.authenticate,
            jsonBody: JSONEncoder().encode(AnyJSON.object(fields)), expectedGeneration: boot.generation)
        let auth = try JSONDecoder().decode(AnyJSON.self, from: bytes)
        let accountID = try XCTUnwrap(auth["accountId"]?.string)
        let secret = try XCTUnwrap(mnemonic ?? auth["mnemonic"]?.string)
        XCTAssertFalse(secret.isEmpty)
        // Recovery phrases and managed tokens are never attached or printed.
        return (accountID, secret)
    }

    private func intentID() -> String {
        UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    }

    private func requireExact(_ value: TorahAuthorizedOperationSnapshot,
                              reader: AnyHostAuthorizedTorahOperationReader, operation: AnyTorahOperation,
                              changeID: String, state: TorahOperationTargetReachability) throws {
        XCTAssertEqual(value.scope, reader.scope)
        XCTAssertEqual(value.operationID, operation.operationID)
        XCTAssertEqual(value.outcome, .found)
        XCTAssertFalse(value.conflicted)
        XCTAssertEqual(value.variants.count, 1)
        let variant = try XCTUnwrap(value.variants.first)
        XCTAssertEqual(variant.claimID, operation.claimID)
        XCTAssertEqual(variant.canonicalBytes, operation.canonicalBytes)
        XCTAssertEqual(variant.authorID, operation.authorID)
        XCTAssertEqual(variant.spaceID, operation.spaceID)
        XCTAssertEqual(variant.target.objectId, operation.targetObjectID)
        XCTAssertEqual(variant.target.blockId, operation.targetBlockID)
        XCTAssertEqual(variant.reachability, state)
        XCTAssertEqual(variant.provenance.count, 1)
        let proof = try XCTUnwrap(variant.provenance.first)
        XCTAssertEqual(proof.creator, operation.authorID)
        XCTAssertEqual(proof.nativeChangeID, changeID)
        XCTAssertFalse(proof.nativeACLHeadID.isEmpty)
    }

    private func requireReadError(_ expected: TorahOperationReadError,
                                  reader: AnyHostAuthorizedTorahOperationReader,
                                  operationID: String) async {
        do {
            _ = try await reader.readOperation(operationID: operationID)
            XCTFail("Unavailable or stale authority returned a private operation.")
        } catch {
            XCTAssertEqual(error as? TorahOperationReadError, expected)
        }
    }
}
#endif
