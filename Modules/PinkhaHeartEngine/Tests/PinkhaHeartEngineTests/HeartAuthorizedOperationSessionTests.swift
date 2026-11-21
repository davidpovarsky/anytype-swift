import Foundation
import PinkhaKit
import XCTest
@testable import PinkhaHeartEngine

@MainActor
final class HeartAuthorizedOperationSessionTests: XCTestCase {
    func testSameOwnerReadsAndPublishesCompleteNativeResult() async throws {
        let transport = HeartReadControlledTransport()
        let session = try HeartAuthorizedOperationSession(accountID: "account", spaceID: "space", transport: transport)
        let reader = HeartAuthorizedOperationReader(session: session)
        let task = Task { try await reader.readOperation(operationID: HeartReadFixture.operationID) }
        await transport.waitForRequest()
        await transport.succeed(try HeartReadFixture.response().serializedData())
        let result = try await task.value
        XCTAssertEqual(result.scope, session.scope)
        var published: TorahAuthorizedOperationSnapshot?
        XCTAssertTrue(session.publishIfCurrent(result) { published = $0 })
        XCTAssertEqual(published, result)
        let count = await transport.callCount
        XCTAssertEqual(count, 1)
    }

    func testInvalidationWhileNativeCallSuspendsDropsWholeSnapshot() async throws {
        let transport = HeartReadControlledTransport()
        let session = try HeartAuthorizedOperationSession(accountID: "account", spaceID: "space", transport: transport)
        let reader = HeartAuthorizedOperationReader(session: session)
        let task = Task { try await reader.readOperation(operationID: HeartReadFixture.operationID) }
        await transport.waitForRequest()
        session.invalidate()
        await transport.succeed(try HeartReadFixture.response().serializedData())
        do { _ = try await task.value; XCTFail("Invalidated owner released a snapshot") }
        catch { XCTAssertEqual(error as? TorahOperationReadError, .accountChanged) }
    }

    func testCancellationWhileNativeCallSuspendsDropsWholeSnapshot() async throws {
        let transport = HeartReadControlledTransport()
        let session = try HeartAuthorizedOperationSession(accountID: "account", spaceID: "space", transport: transport)
        let task = Task { try await HeartAuthorizedOperationReader(session: session).readOperation(operationID: HeartReadFixture.operationID) }
        await transport.waitForRequest()
        task.cancel()
        await transport.succeed(try HeartReadFixture.response().serializedData())
        do { _ = try await task.value; XCTFail("Cancelled call released a snapshot") }
        catch { XCTAssertTrue(error is CancellationError) }
    }

    func testReopeningIdenticalPublicIDsCannotPublishOldLifetime() throws {
        let transport = HeartReadControlledTransport()
        let old = try HeartAuthorizedOperationSession(accountID: "account", spaceID: "space", transport: transport)
        let snapshot = try HeartReadFixture.decode(HeartReadFixture.response(), scope: old.scope)
        old.invalidate()
        let reopened = try HeartAuthorizedOperationSession(accountID: "account", spaceID: "space", transport: transport)
        XCTAssertNotEqual(old.scope.sessionGeneration, reopened.scope.sessionGeneration)
        var publications = 0
        XCTAssertFalse(old.publishIfCurrent(snapshot) { _ in publications += 1 })
        XCTAssertFalse(reopened.publishIfCurrent(snapshot) { _ in publications += 1 })
        XCTAssertEqual(publications, 0)
    }

    func testInvalidatedSessionNeverCallsNativeTransport() async throws {
        let transport = HeartReadControlledTransport()
        let session = try HeartAuthorizedOperationSession(accountID: "account", spaceID: "space", transport: transport)
        session.invalidate()
        do {
            _ = try await HeartAuthorizedOperationReader(session: session).readOperation(operationID: HeartReadFixture.operationID)
            XCTFail("Invalidated owner started native work")
        } catch { XCTAssertEqual(error as? TorahOperationReadError, .accountChanged) }
        let count = await transport.callCount
        XCTAssertEqual(count, 0)
    }
}

private actor HeartReadControlledTransport: HeartAuthorizedOperationTransport {
    private(set) var callCount = 0
    private var waiting: [CheckedContinuation<Void, Never>] = []
    private var response: CheckedContinuation<Data, Never>?

    func readAuthorizedOperation(request: Data) async throws -> Data {
        callCount += 1
        return await withCheckedContinuation { continuation in
            response = continuation
            for waiter in waiting { waiter.resume() }
            waiting.removeAll()
        }
    }

    func waitForRequest() async {
        if response != nil { return }
        await withCheckedContinuation { waiting.append($0) }
    }

    func succeed(_ bytes: Data) {
        let pending = response
        response = nil
        pending?.resume(returning: bytes)
    }
}
