import Foundation
import PinkhaKit
import PinkhaHeartNative
import ProtobufMessages
import SwiftProtobuf
import XCTest
@testable import PinkhaHeartEngine

/// One fresh synthetic account, one actual generated append, and the actual
/// Lib→Swift shared reader. No source is replayed and no old suite is selected.
@MainActor
final class HeartAuthorizedOperationLibTests: XCTestCase {
    func testActualLibReadOwnsAccountAndSpaceAcrossNativeReopenAndRetirement() async throws {
        let configuration = try JSONDecoder().decode(Configuration.self,
            from: Data(contentsOf: XCTUnwrap(Bundle.module.url(forResource: "host-config", withExtension: "json"))))
        guard configuration.candidate == "69b6b3fc8616b11230cbc45ced0635f60098950a1e611a089ab73baf70550b67",
              configuration.appSHA.count == 40, !configuration.nonce.isEmpty else { throw Failure.configuration }
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-heart-read-" + configuration.nonce)
        guard !FileManager.default.fileExists(atPath: root.path) else { throw Failure.existingData }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        InvocationSettings.handler = nil
        _ = ServiceMessageHandlerAdapter.shared
        try await ClientCommands.initialSetParameters(.with {
            $0.platform = "ios"; $0.version = "0.51.0"; $0.workdir = root.path
            $0.doNotSendLogs = true; $0.doNotSaveLogs = true; $0.doNotSendTelemetry = true
        }).invoke()
        let version = try await ClientCommands.appGetVersion().invoke().version
        guard version == configuration.runtimeVersion else { throw Failure.nativeIdentity }
        let wallet = try await ClientCommands.walletCreate(.with { $0.rootPath = root.path }).invoke()
        guard !wallet.accountKey.isEmpty, !wallet.mnemonic.isEmpty else { throw Failure.nativeIdentity }
        do {
            let created = try await ClientCommands.accountCreate(.with {
                $0.name = "Synthetic authorized read iOS fixture"; $0.networkMode = .localOnly
                $0.disableLocalNetworkSync = true
            }).invoke()
            guard created.hasAccount, !created.account.id.isEmpty else { throw Failure.nativeIdentity }
            let accountID = created.account.id
            let space = try await ClientCommands.workspaceCreate(.with {
                $0.details.fields["name"] = .with { $0.stringValue = "Synthetic read fixture" }
            }).invoke()
            guard !space.spaceID.isEmpty else { throw Failure.nativeIdentity }
            let spaceID = space.spaceID
            try await ClientCommands.workspaceOpen(.with { $0.spaceID = spaceID }).invoke()
            let session = try HeartLibAuthorizedOperationReader.makeSession(forOpenedSpaceID: spaceID)
            let lease = try PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: spaceID)
            XCTAssertEqual(session.scope.accountID, accountID)
            XCTAssertEqual(session.scope.spaceID, spaceID)
            XCTAssertEqual(session.scope.sessionGeneration, lease.generation)
            try await waitForIndexedPage(spaceID: spaceID)
            let document = try await ClientCommands.objectCreate(.with {
                $0.spaceID = spaceID; $0.objectTypeUniqueKey = "ot-page"
                $0.details.fields["name"] = .with { $0.stringValue = "Synthetic read document" }
            }).invoke()
            guard !document.objectID.isEmpty else { throw Failure.nativeIdentity }
            let objectID = document.objectID
            let block = try await ClientCommands.blockCreate(.with {
                $0.contextID = objectID; $0.targetID = objectID; $0.position = .inner
                $0.block.text.text = "Synthetic visible block"
            }).invoke()
            guard !block.blockID.isEmpty else { throw Failure.nativeIdentity }
            let blockID = block.blockID, operationID = String(repeating: "3", count: 32)
            let reader = HeartAuthorizedOperationReader(session: session)
            do {
                _ = try await reader.readOperation(operationID: operationID)
                XCTFail("A read created private history")
            } catch { XCTAssertEqual(error as? TorahOperationReadError, .historyUnavailable) }

            typealias Operations = Pinkha_Fixture_Rpc.Pinkha.TorahOperations
            let payload = Data("תורה e\u{301}".utf8) + Data([0, 255, 128])
            let append = Operations.Append.Request.with {
                $0.protocolVersion = 1; $0.spaceID = spaceID; $0.operationID = operationID; $0.kind = .add
                $0.target.objectID = objectID; $0.target.blockID = blockID
                $0.source.providerID = "fixture"; $0.source.canonicalRef = "fixture:ios-authorized-read:1"
                $0.payload = payload
            }
            let responseBytes = try await PinkhaAuthorizedReadFixtureByteBridge.append(append.serializedData(), lease: lease)
            let appended = try Operations.Append.Response(serializedBytes: responseBytes)
            guard appended.hasError, appended.error.code == .null, appended.protocolVersion == 1,
                  appended.hasReceipt, appended.receipt.disposition == .created,
                  !appended.receipt.claimID.isEmpty, !appended.receipt.changeID.isEmpty else { throw Failure.nativeAppend }
            let live = try await reader.readOperation(operationID: operationID)
            let variant = try XCTUnwrap(live.variants.only)
            XCTAssertEqual(live.outcome, .found)
            XCTAssertEqual(live.scope, session.scope)
            XCTAssertFalse(live.conflicted)
            XCTAssertEqual(variant.claimID, appended.receipt.claimID)
            XCTAssertEqual(variant.authorID, accountID)
            XCTAssertEqual(variant.target, .block(objectId: objectID, blockId: blockID))
            XCTAssertEqual(variant.reachability, .liveBlock)
            XCTAssertEqual(variant.provenance.only?.creator, accountID)
            XCTAssertEqual(variant.provenance.only?.nativeChangeID, appended.receipt.changeID)
            XCTAssertFalse(try XCTUnwrap(variant.provenance.only).nativeACLHeadID.isEmpty)
            let canonical = expectedCanonical(space: spaceID, operation: operationID, author: accountID,
                                              object: objectID, block: blockID, payload: payload)
            XCTAssertEqual(variant.canonicalBytes, canonical)
            let absent = try await reader.readOperation(operationID: String(repeating: "4", count: 32))
            XCTAssertEqual(absent.outcome, .absentInVerifiedLocalSnapshot)
            XCTAssertTrue(absent.variants.isEmpty)

            try await ClientCommands.blockListDelete(.with { $0.contextID = objectID; $0.blockIds = [blockID] }).invoke()
            let unreachable = try await reader.readOperation(operationID: operationID)
            let orphan = try XCTUnwrap(unreachable.variants.only)
            XCTAssertEqual(orphan.reachability, .unreachableBlock)
            XCTAssertEqual(orphan.canonicalBytes, canonical)
            XCTAssertEqual(orphan.provenance, variant.provenance)
            var nativeStopReturned = false, retiredWhileStopPending = false, publicationDeniedAtRetirement = false
            let retirement = NativeRetirementProbe {
                retiredWhileStopPending = !nativeStopReturned
                publicationDeniedAtRetirement = !session.publishIfCurrent(live) { _ in }
            }
            try lease.observeRetirement(retirement)
            try await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            nativeStopReturned = true
            XCTAssertEqual(retirement.count, 1)
            XCTAssertTrue(retiredWhileStopPending)
            XCTAssertTrue(publicationDeniedAtRetirement)
            XCTAssertThrowsError(try HeartLibAuthorizedOperationReader.makeSession(forOpenedSpaceID: spaceID))
            await requireRetired(reader, operation: operationID)

            // Recreate the real native account app in this same iOS process.
            // Linux already separately proves a fresh-process cold reopen.
            try await ClientCommands.walletRecover(.with { $0.rootPath = root.path; $0.accountKey = wallet.accountKey }).invoke()
            let selection = Anytype_Rpc.Account.Select.Request.with {
                $0.id = accountID; $0.rootPath = root.path; $0.networkMode = .localOnly
                $0.disableLocalNetworkSync = true; $0.preferredSpaceID = spaceID
            }
            let selected: Anytype_Rpc.Account.Select.Response
            do { selected = try await ClientCommands.accountSelect(selection).invoke() }
            catch let error as Anytype_Rpc.Account.Select.Response.Error where error.code == .accountStoreNotMigrated {
                try await ClientCommands.accountMigrate(.with { $0.id = accountID; $0.rootPath = root.path }).invoke()
                selected = try await ClientCommands.accountSelect(selection).invoke()
            }
            XCTAssertEqual(selected.account.id, accountID)
            try await ClientCommands.workspaceOpen(.with { $0.spaceID = spaceID }).invoke()
            let reopened = try HeartLibAuthorizedOperationReader.makeSession(forOpenedSpaceID: spaceID)
            XCTAssertNotEqual(reopened.scope.sessionGeneration, session.scope.sessionGeneration)
            let reopenedResult = try await HeartAuthorizedOperationReader(session: reopened).readOperation(operationID: operationID)
            XCTAssertEqual(reopenedResult.variants.only?.canonicalBytes, canonical)
            XCTAssertEqual(reopenedResult.variants.only?.provenance, variant.provenance)
            XCTAssertEqual(reopenedResult.variants.only?.reachability, .unreachableBlock)
            XCTAssertFalse(session.publishIfCurrent(live) { _ in })
            XCTAssertFalse(reopened.publishIfCurrent(live) { _ in })
            try await ClientCommands.spaceDelete(.with { $0.spaceID = spaceID }).invoke()
            XCTAssertFalse(reopened.publishIfCurrent(reopenedResult) { _ in })
            XCTAssertThrowsError(try HeartLibAuthorizedOperationReader.makeSession(forOpenedSpaceID: spaceID))
            await requireRetired(HeartAuthorizedOperationReader(session: reopened), operation: operationID)
            try await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            try await ClientCommands.appShutdown().invoke()
            let result: [String: Any] = [
                "status": "PASS_ACTUAL_HEART_LIB_SHARED_READ", "run_id": configuration.runID,
                "app_sha": configuration.appSHA, "nonce": configuration.nonce,
                "candidate_sha256": configuration.candidate, "native_version": version,
                "pid": ProcessInfo.processInfo.processIdentifier,
                "account_id_sha256": HeartNativeOperationCanonical.digest(Data(accountID.utf8)),
                "space_id_sha256": HeartNativeOperationCanonical.digest(Data(spaceID.utf8)),
                "canonical_sha256": HeartNativeOperationCanonical.digest(canonical),
                "signed_native_provenance": true, "actual_append_calls": 1,
                "verified_local_absence": true, "block_delete_preserved_history": true,
                "native_account_reopen_preserved_unreachable_history": true,
                "retirement_while_stop_pending": retiredWhileStopPending,
                "publication_denied_at_retirement": publicationDeniedAtRetirement,
                "space_delete_retired_reader": true, "app_capability": "OFF",
                "fresh_ios_process_reopen": "NOT_RUN", "two_app_clients": "NOT_RUN"
            ]
            let encoded = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
            let attachment = XCTAttachment(data: encoded, uniformTypeIdentifier: "public.json")
            attachment.name = "heart-authorized-read-" + configuration.nonce + ".json"
            attachment.lifetime = .keepAlways
            add(attachment)
            print("PINKHA_HEART_READ_IOS_RECEIPT " + encoded.base64EncodedString())
        } catch {
            _ = try? await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            _ = try? await ClientCommands.appShutdown().invoke()
            throw error
        }
    }

    private func waitForIndexedPage(spaceID: String) async throws {
        let deadline = ContinuousClock.now + .seconds(20)
        repeat {
            let found = try await ClientCommands.objectSearch(.with {
                $0.spaceID = spaceID; $0.limit = 2; $0.keys = ["id", "spaceId", "uniqueKey"]
                $0.filters = [.with { $0.relationKey = "uniqueKey"; $0.condition = .equal
                    $0.value = .with { $0.stringValue = "ot-page" } }]
            }).invoke()
            if let record = found.records.only {
                guard record.fields["spaceId"]?.stringValue == spaceID,
                      record.fields["uniqueKey"]?.stringValue == "ot-page",
                      record.fields["id"]?.stringValue.isEmpty == false else { throw Failure.nativeIdentity }
                return
            }
            guard found.records.isEmpty else { throw Failure.nativeIdentity }
            try await Task.sleep(for: .milliseconds(100))
        } while ContinuousClock.now < deadline
        throw Failure.typeReadiness
    }

    private func requireRetired(_ reader: HeartAuthorizedOperationReader, operation: String) async {
        do { _ = try await reader.readOperation(operationID: operation); XCTFail("Retired owner released a snapshot") }
        catch { XCTAssertEqual(error as? TorahOperationReadError, .accountChanged) }
    }

    private func expectedCanonical(space: String, operation: String, author: String, object: String,
                                   block: String, payload: Data) -> Data {
        var bytes = Data("pinkha-t2-operation\0".utf8); bytes.append(contentsOf: [0, 0, 0, 1])
        for value in [space, operation, author, "add", object, block, "fixture", "fixture:ios-authorized-read:1"] {
            HeartNativeOperationCanonical.appendFramed(Data(value.utf8), to: &bytes)
        }
        HeartNativeOperationCanonical.appendFramed(payload, to: &bytes)
        bytes.append(contentsOf: [0, 0, 0, 0])
        return bytes
    }

    private struct Configuration: Decodable {
        let runID, appSHA, nonce, candidate, runtimeVersion: String
    }
    private enum Failure: Error { case configuration, existingData, nativeIdentity, nativeAppend, typeReadiness }
}

@MainActor
private final class NativeRetirementProbe: PinkhaNativeReadLeaseObserver {
    var count = 0
    let retired: @MainActor () -> Void
    init(_ retired: @escaping @MainActor () -> Void) { self.retired = retired }
    func nativeReadLeaseDidRetire() { count += 1; retired() }
}

private extension Array {
    var only: Element? { count == 1 ? first : nil }
}
