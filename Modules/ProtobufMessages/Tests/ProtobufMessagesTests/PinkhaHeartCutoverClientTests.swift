#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf
import XCTest
@testable import ProtobufMessages

@MainActor
final class PinkhaHeartCutoverClientTests: XCTestCase {
    private typealias Wire = Anytype_PinkhaTorahCutover
    private typealias V1 = Anytype_Rpc.Pinkha.TorahOperations
    // Canonical CIDv1/dag-cbor/SHA2-256 bytes for a synthetic identity only.
    // Actual immutable native change IDs are checked by the captured-frame test.
    private let changeID = "bafyreiet7c2salb3m5r6fxqf3hahayhso55qa34gpbdqc3t23veqypuxfe"
    private let planID = "492bb9fb2ecb18120fb64b5e77912bcd4e0d6e66efedacfc28406899813108fc"
    private let privateText = "private-resolution-must-not-cross-retired-owner"

    private enum Write: CaseIterable, Equatable {
        case metadata, imported, associated
        var method: PinkhaHeartCutoverMethod {
            switch self {
            case .metadata: .append
            case .imported: .importFact
            case .associated: .associationAppend
            }
        }
    }
    private enum FixtureFailure: Error { case transport, expectedFailure }

    func testAllFiveMethodsDispatchWithTheOwnedFrozenScope() async throws {
        let (owner, lease) = try opened()
        let profile = try profile()
        let scope = scope()
        var calls: [PinkhaHeartCutoverMethod] = []
        let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, bytes in
            calls.append(method)
            switch method {
            case .sourceRead, .read:
                XCTAssertEqual(try Wire.Scope(serializedBytes: bytes), scope)
            case .append:
                XCTAssertEqual(try Wire.RecordRequest(serializedBytes: bytes).scope, scope)
            case .importFact, .associationAppend:
                XCTAssertEqual(try Wire.OperationRequest(serializedBytes: bytes).scope, scope)
            }
            return try self.response(method)
        }), profile: profile)
        let source = try await client.source(scope, lease: lease)
        XCTAssertEqual(source.source.value, Data(privateText.utf8))
        let snapshot = try await client.read(scope, lease: lease)
        XCTAssertTrue(snapshot.completeLocal)
        for write in Write.allCases {
            let result = try await invoke(write, client: client, lease: lease)
            XCTAssertEqual(result.0, claimID(write.method))
            XCTAssertEqual(result.1, changeID)
        }
        XCTAssertEqual(calls, [.sourceRead, .read, .append, .importFact, .associationAppend])
        XCTAssertTrue(try owner.lease(forOpenedSpaceID: "space") === lease)
    }

    func testBothReadsRefuseOwnerRetirementWithoutReleasingPrivateResponse() async throws {
        for method in [PinkhaHeartCutoverMethod.sourceRead, .read] {
            let (owner, lease) = try opened()
            let profile = try profile()
            let gate = CutoverByteGate()
            var calls = 0
            let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { observed, _ in
                XCTAssertEqual(observed, method); calls += 1
                return await gate.suspend()
            }), profile: profile)
            let task = Task { @MainActor in
                if method == .sourceRead { _ = try await client.source(self.scope(), lease: lease) }
                else { _ = try await client.read(self.scope(), lease: lease) }
            }
            await gate.waitForDispatch()
            retire(owner)
            gate.complete(try response(method))
            let failure = try await expect(.retiredOwner) { try await task.value }
            XCTAssertNil(failure.durableReceipt)
            XCTAssertFalse(String(reflecting: failure).contains(privateText))
            XCTAssertEqual(calls, 1)
        }
    }

    func testThreeWritesRetainCommitAndAllNativeIssuesAfterOwnerRetirement() async throws {
        for write in Write.allCases {
            let (owner, lease) = try opened()
            let profile = try profile()
            let gate = CutoverByteGate()
            var calls = 0
            let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, _ in
                XCTAssertEqual(method, write.method); calls += 1
                return await gate.suspend()
            }), profile: profile)
            let task = Task { @MainActor in try await self.invoke(write, client: client, lease: lease) }
            await gate.waitForDispatch()
            retire(owner)
            gate.complete(try response(write.method, nativeFailure: true))
            let failure = try await expect(.retiredOwner) { _ = try await task.value }
            XCTAssertEqual(failure.durableReceipt?.claimID, claimID(write.method))
            XCTAssertEqual(failure.durableReceipt?.changeID, changeID)
            XCTAssertEqual(failure.durableReceipt?.disposition, 1)
            XCTAssertEqual(failure.nativeCode, Wire.Error.Code.accountChanged.rawValue)
            XCTAssertEqual(failure.nativeIssues, joinedIssues.map(\.rawValue))
            XCTAssertFalse(String(reflecting: failure).contains(privateText))
            XCTAssertEqual(calls, 1, "a post-authority failure never grants an automatic retry")
        }
    }

    func testThreeWritesPreserveNativeFailureReceiptsWithoutRetry() async throws {
        for write in Write.allCases {
            let (_, lease) = try opened()
            let profile = try profile()
            var calls = 0
            let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, _ in
                XCTAssertEqual(method, write.method); calls += 1
                return try self.response(method, nativeFailure: true)
            }), profile: profile)
            let failure = try await expect(.nativeRefusal) { _ = try await self.invoke(write, client: client, lease: lease) }
            XCTAssertEqual(failure.durableReceipt?.claimID, claimID(write.method))
            XCTAssertEqual(failure.durableReceipt?.changeID, changeID)
            XCTAssertEqual(failure.nativeIssues, joinedIssues.map(\.rawValue))
            XCTAssertEqual(calls, 1)
            XCTAssertFalse(String(reflecting: failure).contains(privateText))
        }
    }

    func testCancellationAfterDispatchRetainsEachNativeAcknowledgement() async throws {
        for write in Write.allCases {
            for nativeFailure in [false, true] {
                let (_, lease) = try opened()
                let profile = try profile()
                let gate = CutoverByteGate()
                var calls = 0
                let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, _ in
                    XCTAssertEqual(method, write.method); calls += 1
                    return await gate.suspend()
                }), profile: profile)
                let task = Task { @MainActor in try await self.invoke(write, client: client, lease: lease) }
                await gate.waitForDispatch()
                task.cancel()
                gate.complete(try response(write.method, nativeFailure: nativeFailure))
                let failure = try await expect(.callerCancelled) { _ = try await task.value }
                XCTAssertEqual(failure.durableReceipt?.claimID, claimID(write.method))
                XCTAssertEqual(failure.durableReceipt?.changeID, changeID)
                XCTAssertEqual(failure.writeEffect, .nativeReceiptReceived)
                XCTAssertEqual(failure.requestSHA256, PinkhaHeartCutoverClient.digest(try frozenData(write)))
                XCTAssertEqual(failure.nativeCode, nativeFailure ? Wire.Error.Code.accountChanged.rawValue : 0)
                XCTAssertEqual(failure.nativeIssues, nativeFailure ? joinedIssues.map(\.rawValue) : [])
                XCTAssertFalse(String(reflecting: failure).contains(privateText))
                XCTAssertEqual(calls, 1)
            }
        }
    }

    func testCancellationBeforeValidatedHandoffNeverDispatches() async throws {
        for write in Write.allCases {
            let (_, lease) = try opened()
            let profile = try profile()
            var calls = 0
            let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { _, _ in
                calls += 1; throw FixtureFailure.transport
            }), profile: profile)
            let task = Task { @MainActor in try await self.invoke(write, client: client, lease: lease) }
            task.cancel()
            do { _ = try await task.value; XCTFail("cancelled before handoff") }
            catch is CancellationError {}
            catch { XCTFail("unexpected cancellation boundary error: \(type(of: error))"); throw error }
            XCTAssertEqual(calls, 0)
        }
    }

    func testRuntimeChangeAndRetiredLeaseRefuseBeforeNativeDispatch() async throws {
        for mismatch in [false, true] {
            let (owner, lease) = try opened()
            let profile = try profile()
            var calls = 0
            let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: {
                mismatch ? "a different native product" : profile.runtimeVersion
            }, invoke: { _, _ in calls += 1; throw FixtureFailure.transport }), profile: profile)
            if !mismatch { retire(owner) }
            for write in Write.allCases {
                _ = try await expect(mismatch ? .unsupportedRuntime : .retiredOwner) {
                    _ = try await self.invoke(write, client: client, lease: lease)
                }
            }
            _ = try await expect(mismatch ? .unsupportedRuntime : .retiredOwner) {
                _ = try await client.source(self.scope(), lease: lease)
            }
            _ = try await expect(mismatch ? .unsupportedRuntime : .retiredOwner) {
                _ = try await client.read(self.scope(), lease: lease)
            }
            XCTAssertEqual(calls, 0)
        }
        XCTAssertThrowsError(try PinkhaHeartCutoverProfile(sourceManifestSHA256: String(repeating: "a", count: 64),
                                                          runtimeVersion: "ordinary app version"))
    }

    func testTransportFailureIsUncertainAndNeverAutomaticallyRetried() async throws {
        for write in Write.allCases {
            let (_, lease) = try opened()
            let profile = try profile()
            var calls = 0
            let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { _, _ in
                calls += 1; throw FixtureFailure.transport
            }), profile: profile)
            let failure = try await expect(.transportUncertain) {
                _ = try await self.invoke(write, client: client, lease: lease)
            }
            XCTAssertNil(failure.durableReceipt)
            XCTAssertEqual(failure.writeEffect, .uncertainAfterDispatch)
            XCTAssertEqual(failure.requestSHA256, PinkhaHeartCutoverClient.digest(try frozenData(write)))
            XCTAssertEqual(calls, 1)
        }
    }

    func testMalformedOversizedAndVersionlessRepliesNeverInventCommitReceipts() async throws {
        for write in Write.allCases {
            for invalid in 0..<3 {
                let (_, lease) = try opened()
                let profile = try profile()
                var calls = 0
                let raw: Data
                if invalid == 0 { raw = Data([0xff]) }
                else if invalid == 1 { raw = Data(count: 4 * 1_024 * 1_024 + 1) }
                else { raw = try response(write.method, version: 0) }
                let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { _, _ in
                    calls += 1; return raw
                }), profile: profile)
                let failure = try await expect(invalid == 1 ? .responseTooLarge : .invalidResponse) {
                    _ = try await self.invoke(write, client: client, lease: lease)
                }
                XCTAssertNil(failure.durableReceipt)
                XCTAssertEqual(failure.writeEffect, .uncertainAfterDispatch)
                XCTAssertEqual(failure.requestSHA256, PinkhaHeartCutoverClient.digest(try frozenData(write)))
                XCTAssertFalse(String(reflecting: failure).contains(privateText))
                XCTAssertEqual(calls, 1)
            }
        }
    }

    func testForeignOrMismatchedAcknowledgementsNeverBecomeDurableReceipts() async throws {
        for write in Write.allCases {
            for tamper in 0..<7 {
                let (_, lease) = try opened()
                let profile = try profile()
                var bytes = try response(write.method)
                if write == .metadata {
                    var reply = try Wire.AppendResponse(serializedBytes: bytes)
                    switch tamper {
                    case 0: reply.receipt.claimID = String(repeating: "a", count: 64) + "/" + String(repeating: "b", count: 64)
                    case 1: reply.receipt.resolution.recordID = String(repeating: "f", count: 32)
                    case 2: reply.receipt.resolution.claims[0].record.objectID = "foreign-object"
                    case 3: reply.receipt.resolution.claims[0].record.authorID = "foreign-author"
                    case 4: reply.receipt.resolution.claims[0].record.plan.legacyValue = Data("changed source".utf8)
                    case 5: reply.receipt.resolution.claims[0].record.spaceID = "foreign-space"
                    default: reply.receipt.resolution.claims[0].claimID = String(claimID(write.method).prefix(65)) + String(repeating: "c", count: 64)
                    }
                    bytes = try reply.serializedData()
                } else {
                    var reply = try Wire.OperationResponse(serializedBytes: bytes)
                    switch tamper {
                    case 0: reply.receipt.claimID = String(repeating: "a", count: 64) + "/" + String(repeating: "b", count: 64)
                    case 1: reply.receipt.resolution.operationID = String(repeating: "f", count: 32)
                    case 2: reply.receipt.resolution.claims[0].operation.target.objectID = "foreign-object"
                    case 3: reply.receipt.resolution.claims[0].operation.authorID = "foreign-author"
                    case 4: reply.receipt.resolution.claims[0].operation.payload = Data("changed payload".utf8)
                    case 5: reply.receipt.resolution.claims[0].operation.spaceID = "foreign-space"
                    default: reply.receipt.resolution.claims[0].claimID = String(claimID(write.method).prefix(65)) + String(repeating: "c", count: 64)
                    }
                    bytes = try reply.serializedData()
                }
                let replyBytes = bytes
                var calls = 0
                let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, _ in
                    XCTAssertEqual(method, write.method); calls += 1
                    return replyBytes
                }), profile: profile)
                let failure = try await expect(.invalidResponse) { _ = try await self.invoke(write, client: client, lease: lease) }
                XCTAssertNil(failure.durableReceipt)
                XCTAssertEqual(failure.writeEffect, .uncertainAfterDispatch)
                XCTAssertEqual(failure.requestSHA256, PinkhaHeartCutoverClient.digest(try frozenData(write)))
                XCTAssertFalse(String(reflecting: failure).contains(privateText))
                XCTAssertEqual(calls, 1)
            }
        }
    }

    func testPrivateOrMalformedChangeIDsCannotCrossRetirementOrCancellation() async throws {
        for write in Write.allCases {
            for cancelled in [false, true] {
                for badID in invalidChangeIDs {
                    let (owner, lease) = try opened()
                    let profile = try profile()
                    let gate = CutoverByteGate()
                    var calls = 0
                    let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, _ in
                        XCTAssertEqual(method, write.method); calls += 1
                        return await gate.suspend()
                    }), profile: profile)
                    let task = Task { @MainActor in try await self.invoke(write, client: client, lease: lease) }
                    await gate.waitForDispatch()
                    if cancelled { task.cancel() } else { retire(owner) }
                    var raw = try response(write.method, nativeFailure: true)
                    if write == .metadata {
                        var reply = try Wire.AppendResponse(serializedBytes: raw)
                        reply.receipt.changeID = badID
                        raw = try reply.serializedData()
                    } else {
                        var reply = try Wire.OperationResponse(serializedBytes: raw)
                        reply.receipt.changeID = badID
                        raw = try reply.serializedData()
                    }
                    gate.complete(raw)
                    let failure = try await expect(cancelled ? .callerCancelled : .invalidResponse) { _ = try await task.value }
                    XCTAssertNil(failure.durableReceipt)
                    XCTAssertEqual(failure.writeEffect, .uncertainAfterDispatch)
                    XCTAssertEqual(failure.requestSHA256, PinkhaHeartCutoverClient.digest(try frozenData(write)))
                    XCTAssertFalse(String(reflecting: failure).contains(privateText))
                    XCTAssertEqual(calls, 1)
                }
            }
        }
    }

    func testNativeChangeIDGrammarRefusesNoncanonicalRepresentations() {
        XCTAssertTrue(PinkhaHeartCutoverProfile.nativeChangeID(changeID))
        for value in invalidChangeIDs { XCTAssertFalse(PinkhaHeartCutoverProfile.nativeChangeID(value), value) }
    }

    func testBareAcknowledgementsBindFullFrozenAuthorAndPayloadDigest() async throws {
        for write in Write.allCases {
            for foreignAuthor in [false, true] {
                let (owner, lease) = try opened()
                let profile = try profile()
                let gate = CutoverByteGate()
                var calls = 0
                var raw = try response(write.method, nativeFailure: true)
                let foreignClaim: String
                if write == .metadata {
                    var request = record()
                    if !foreignAuthor { request.plan.legacyValue = Data("foreign-private-source".utf8) }
                    foreignClaim = try PinkhaHeartCutoverClient.claimIdentity(request, author: foreignAuthor ? "foreign-author" : "account")
                    var reply = try Wire.AppendResponse(serializedBytes: raw)
                    XCTAssertFalse(reply.receipt.hasResolution)
                    reply.receipt.claimID = foreignClaim
                    raw = try reply.serializedData()
                } else {
                    var request = operation()
                    if !foreignAuthor { request.payload = Data("foreign-private-payload".utf8) }
                    foreignClaim = try PinkhaHeartCutoverClient.claimIdentity(request, author: foreignAuthor ? "foreign-author" : "account")
                    var reply = try Wire.OperationResponse(serializedBytes: raw)
                    XCTAssertFalse(reply.receipt.hasResolution)
                    reply.receipt.claimID = foreignClaim
                    raw = try reply.serializedData()
                }
                XCTAssertEqual(foreignClaim.prefix(64), claimID(write.method).prefix(64))
                XCTAssertNotEqual(foreignClaim.suffix(64), claimID(write.method).suffix(64))
                let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, _ in
                    XCTAssertEqual(method, write.method); calls += 1
                    return await gate.suspend()
                }), profile: profile)
                let task = Task { @MainActor in try await self.invoke(write, client: client, lease: lease) }
                await gate.waitForDispatch()
                retire(owner)
                gate.complete(raw)
                let failure = try await expect(.invalidResponse) { _ = try await task.value }
                XCTAssertNil(failure.durableReceipt)
                XCTAssertEqual(failure.writeEffect, .uncertainAfterDispatch)
                XCTAssertEqual(failure.requestSHA256, PinkhaHeartCutoverClient.digest(try frozenData(write)))
                XCTAssertFalse(String(reflecting: failure).contains(privateText))
                XCTAssertFalse(String(reflecting: failure).contains("foreign-private"))
                XCTAssertEqual(calls, 1)
            }
        }
    }

    func testForeignSpaceAndReplacementCannotReuseOldOwner() async throws {
        let (owner, old) = try opened()
        let profile = try profile()
        var calls = 0
        let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { _, _ in
            calls += 1; throw FixtureFailure.transport
        }), profile: profile)
        var foreign = scope(); foreign.spaceID = "foreign-space"
        _ = try await expect(.retiredOwner) { _ = try await client.source(foreign, lease: old) }
        retire(owner)
        establish(owner, account: "replacement-account", space: "space")
        let current = try owner.lease(forOpenedSpaceID: "space")
        XCTAssertNotEqual(current.generation, old.generation)
        XCTAssertEqual(current.accountID, "replacement-account")
        for write in Write.allCases {
            _ = try await expect(.retiredOwner) { _ = try await self.invoke(write, client: client, lease: old) }
        }
        XCTAssertEqual(calls, 0)
        try current.validate()
    }

    func testOwnedTaskKeepsOriginalRequestBytesWhileCallerValueChanges() async throws {
        let (_, lease) = try opened()
        let profile = try profile()
        let gate = CutoverByteGate()
        var request = record()
        let original = try request.serializedData()
        var captured = Data()
        let client = PinkhaHeartCutoverClient(io: .init(runtimeVersion: { profile.runtimeVersion }, invoke: { method, data in
            XCTAssertEqual(method, .append); captured = data
            return await gate.suspend()
        }), profile: profile)
        let frozen = request
        let task = Task { @MainActor in try await client.append(frozen, lease: lease) }
        await gate.waitForDispatch()
        request.scope.objectID = "later-object"
        request.plan.legacyValue = Data("changed later".utf8)
        gate.complete(try response(.append))
        let receipt = try await task.value
        XCTAssertEqual(captured, original)
        XCTAssertNotEqual(captured, try request.serializedData())
        XCTAssertEqual(receipt.claimID, claimID(.append))
    }

    // Independent standard SHA-256 vectors of the original native length framing.
    // Positive captured native responses independently exercise full identities.
    private func claimID(_ method: PinkhaHeartCutoverMethod) -> String {
        let key = method == .append
            ? "4f322b8f2a435b27473d5286363e0c49611f2abee0c71d2af79aefdd96e8e2b5"
            : "b4c10de230387a108c59ab0cf6f6387e134a9ce663bb958f02c5edbf2a09fcf9"
        let digest = method == .append
            ? "fb5834e0cefd8342842fd514d5f535d97721f907f52c5ac70bfe3197e9bc0198"
            : "4633759320b64c9f56df7da63240b5b19477c609287ae0b2fdb5d451cb9da80a"
        return key + "/" + digest
    }

    private var invalidChangeIDs: [String] {
        ["", privateText, changeID.uppercased(), String(changeID.dropLast()), changeID + "a",
         "bafkrei" + String(changeID.dropFirst(7)), String(changeID.dropLast()) + "f",
         String(repeating: "b", count: 59), String(repeating: "a", count: 64)]
    }

    private func frozenData(_ write: Write) throws -> Data {
        if write == .metadata { return try record().serializedData() }
        var request = operation()
        if write == .associated { request.factID = "" }
        return try request.serializedData()
    }

    private var joinedIssues: [Wire.Error.Code] {
        [.accountChanged, .permissionDenied, .incomplete, .unknownError]
    }

    private func profile() throws -> PinkhaHeartCutoverProfile {
        let hash = String(repeating: "a", count: 64)
        return try .init(sourceManifestSHA256: hash, runtimeVersion: "cutover-boundary-fixture-" + hash)
    }

    private func scope() -> Wire.Scope {
        .with { $0.protocolVersion = 1; $0.spaceID = "space"; $0.objectID = "object"; $0.propertyKey = "property" }
    }

    private func record() -> Wire.RecordRequest {
        .with {
            $0.scope = scope(); $0.recordID = String(repeating: "1", count: 32)
            $0.kind = .begin; $0.planID = planID; $0.sourceHeads = ["source-head"]
            $0.plan = .with {
                $0.version = 1; $0.spaceID = "space"; $0.objectID = "object"; $0.propertyKey = "property"
                $0.valuePresent = true; $0.legacyValue = Data("{\"unknown\":9007199254740993,\"text\":\"אבג 👩🏽‍💻\"}".utf8)
            }
        }
    }

    private func operation() -> Wire.OperationRequest {
        .with {
            $0.scope = scope(); $0.operationID = String(repeating: "3", count: 32)
            $0.planID = planID; $0.factID = String(repeating: "4", count: 64)
            $0.kind = .add; $0.source.providerID = "test"; $0.source.canonicalRef = "Ref 1"
            $0.payload = Data(privateText.utf8)
        }
    }

    private func invoke(_ write: Write, client: PinkhaHeartCutoverClient, lease: PinkhaNativeReadLease) async throws -> (String, String) {
        switch write {
        case .metadata:
            let result = try await client.append(record(), lease: lease); return (result.claimID, result.changeID)
        case .imported:
            let result = try await client.importFact(operation(), lease: lease); return (result.claimID, result.changeID)
        case .associated:
            var request = operation(); request.factID = ""
            let result = try await client.associationAppend(request, lease: lease); return (result.claimID, result.changeID)
        }
    }

    private func response(_ method: PinkhaHeartCutoverMethod, nativeFailure: Bool = false, version: UInt32 = 1) throws -> Data {
        let claimID = self.claimID(method)
        let error = Wire.Error.with {
            if nativeFailure { $0.code = .accountChanged; $0.issues = joinedIssues }
        }
        switch method {
        case .sourceRead:
            return try Wire.SourceReadResponse.with {
                $0.protocolVersion = version; $0.error = error
                $0.snapshot.source = .with { $0.key = "property"; $0.present = true; $0.value = Data(privateText.utf8) }
                $0.snapshot.sourceHeads = ["source-head"]
            }.serializedData()
        case .read:
            return try Wire.ReadResponse.with {
                $0.protocolVersion = version; $0.error = error
                $0.snapshot.completeLocal = true; $0.snapshot.state.status = .legacy
                $0.snapshot.source = .with { $0.key = "property"; $0.present = true; $0.value = Data(privateText.utf8) }
                $0.snapshot.sourceHeads = ["source-head"]; $0.snapshot.metadataHeads = ["metadata-head"]
                $0.snapshot.operationHeads = ["operation-head"]
            }.serializedData()
        case .append:
            return try Wire.AppendResponse.with {
                $0.protocolVersion = version; $0.error = error
                $0.receipt = .with {
                    $0.disposition = .created; $0.claimID = claimID; $0.changeID = changeID
                    $0.resolution.recordID = record().recordID
                    let request = record()
                    $0.resolution.claims = [.with {
                        $0.claimID = claimID; $0.digest = String(claimID.suffix(64))
                        $0.record = .with {
                            $0.version = 1; $0.spaceID = request.scope.spaceID; $0.objectID = request.scope.objectID
                            $0.recordID = request.recordID; $0.authorID = "account"; $0.kind = request.kind
                            $0.planID = request.planID; $0.plan = request.plan; $0.factID = request.factID
                            $0.importClaimID = request.importClaimID; $0.imported = request.imported
                            $0.sourceHeads = request.sourceHeads; $0.nativeChanges = request.nativeChanges
                            $0.importRecords = request.importRecords
                        }
                    }]
                    if nativeFailure { $0.clearResolution() }
                }
            }.serializedData()
        case .importFact, .associationAppend:
            return try Wire.OperationResponse.with {
                $0.protocolVersion = version; $0.error = error
                $0.receipt = .with {
                    $0.disposition = .created; $0.claimID = claimID; $0.changeID = changeID
                    $0.resolution.operationID = operation().operationID
                    let request = operation()
                    $0.resolution.claims = [.with {
                        $0.claimID = claimID; $0.digest = String(claimID.suffix(64))
                        $0.operation = .with {
                            $0.version = 1; $0.spaceID = request.scope.spaceID; $0.operationID = request.operationID
                            $0.authorID = "account"; $0.kind = request.kind
                            $0.target.objectID = request.scope.objectID; $0.target.blockID = request.blockID
                            $0.source = request.source; $0.payload = request.payload
                            $0.observedClaimIds = request.observedClaimIds
                        }
                    }]
                    if nativeFailure { $0.clearResolution() }
                }
            }.serializedData()
        }
    }

    private func opened() throws -> (PinkhaNativeReadLifetime, PinkhaNativeReadLease) {
        let owner = PinkhaNativeReadLifetime()
        establish(owner, account: "account", space: "space")
        return (owner, try owner.lease(forOpenedSpaceID: "space"))
    }

    private func establish(_ owner: PinkhaNativeReadLifetime, account: String, space: String) {
        let selected = owner.beforeInvocation(name: "AccountSelect", request: Anytype_Rpc.Account.Select.Request())
        owner.completedInvocation(selected, response: Anytype_Rpc.Account.Select.Response.with {
            $0.account = .with { $0.id = account; $0.status.statusType = .active }
        })
        let opened = owner.beforeInvocation(name: "WorkspaceOpen",
            request: Anytype_Rpc.Workspace.Open.Request.with { $0.spaceID = space })
        owner.completedInvocation(opened, response: Anytype_Rpc.Workspace.Open.Response.with {
            $0.info.workspaceObjectID = "native-workspace"
        })
    }

    private func retire(_ owner: PinkhaNativeReadLifetime) {
        let stopped = owner.beforeInvocation(name: "AccountStop", request: Anytype_Rpc.Account.Select.Request())
        owner.failedInvocation(stopped)
    }

    private func expect(_ reason: PinkhaHeartCutoverFailure.Reason,
                        _ body: @MainActor () async throws -> Void) async throws -> PinkhaHeartCutoverFailure {
        do { try await body() }
        catch let failure as PinkhaHeartCutoverFailure {
            XCTAssertEqual(failure.reason, reason)
            return failure
        } catch {
            XCTFail("unexpected failure type: \(type(of: error))")
            throw error
        }
        XCTFail("expected a closed boundary")
        throw FixtureFailure.expectedFailure
    }
}

@MainActor
private final class CutoverByteGate {
    private var pending: CheckedContinuation<Data, Never>?
    private var observers: [CheckedContinuation<Void, Never>] = []
    private var dispatched = false

    func suspend() async -> Data {
        precondition(!dispatched)
        return await withCheckedContinuation {
            pending = $0; dispatched = true
            let old = observers; observers.removeAll()
            for observer in old { observer.resume() }
        }
    }

    func waitForDispatch() async {
        if dispatched { return }
        await withCheckedContinuation { observers.append($0) }
    }

    func complete(_ data: Data) {
        precondition(dispatched && pending != nil)
        let continuation = pending; pending = nil
        continuation?.resume(returning: data)
    }
}
#endif
