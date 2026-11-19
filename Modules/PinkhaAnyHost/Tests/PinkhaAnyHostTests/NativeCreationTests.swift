import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

private actor CreationMemoryJournal: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    var identities: [String: AnyNativeCreationIdentity] = [:]
    var states: [String: AnyNativeCreationState] = [:]
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func reserve(_ id: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        guard id.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        if let old = identities[id.key] {
            guard old == id else { throw AnyNativeCreationError.contentConflict }
            return .init(state: states[id.key]!, ownsDispatch: false)
        }
        identities[id.key] = id; states[id.key] = .reserved
        return .init(state: .reserved, ownsDispatch: true)
    }
    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        guard identities[identity.key] == identity else { throw AnyNativeCreationError.contentConflict }
        states[identity.key] = state
    }
    func lookup(_ id: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        if let old = identities[id.key], old != id { throw AnyNativeCreationError.contentConflict }
        return states[id.key]
    }
}
private actor CreationGate {
    var isOpen = false
    var waiting: [CheckedContinuation<Void, Never>] = []
    func wait() async {
        if isOpen { return }
        await withCheckedContinuation { waiting.append($0) }
    }
    func open() {
        isOpen = true; let calls = waiting; waiting.removeAll()
        for call in calls { call.resume() }
    }
}
private actor CreationNativeFixture {
    var calls = 0
    var failDispatch = false
    var failRead = false
    var record: AnyJSON
    let entered: CreationGate
    let release: CreationGate?
    init(title: String = "original", entered: CreationGate = CreationGate(), release: CreationGate? = nil) {
        record = .object(["id": .string("created-object"), "spaceId": .string("space"),
                          "any": .object(["type": .string("page"), "name": .string(title)])])
        self.entered = entered; self.release = release
    }
    func create(_ intent: AnyNativeObjectCreationIntent,
                authorize: @escaping @Sendable () async throws -> Void) async throws -> String {
        try await authorize()
        calls += 1
        await entered.open()
        if let release { await release.wait() }
        if failDispatch { throw AnyEngineError.writeUncertain }
        return "created-object"
    }
    func read(_ id: String) throws -> AnyJSON {
        if failRead { throw AnyEngineError.http(status: 404, code: "object.not_found") }
        return record
    }
    func setFailure(dispatch: Bool = false, read: Bool = false) {
        failDispatch = dispatch; failRead = read
    }
    func setTitle(_ value: String) {
        record = .object(["id": .string("created-object"), "spaceId": .string("space"),
            "any": .object(["type": .string("page"), "name": .string(value)])])
    }
}
private actor NativeConfirmation {
    var values: [String] = []
    func record(_ id: String) { values.append(id) }
}

@MainActor
final class NativeCreationTests: XCTestCase {
    private func workspace(_ account: String = "account") throws -> AnyTorahWorkspace {
        try .init(accountID: account, spaceID: "space")
    }
    private func intent(title: String = "original", id: String = String(repeating: "a", count: 32)) throws -> AnyNativeObjectCreationIntent {
        try .init(workspace: workspace(), mutationID: id, typeID: "page",
                  initialProperties: .object(["any": .object(["name": .string(title)])]))
    }
    private func creator(_ journal: CreationMemoryJournal, _ native: CreationNativeFixture) throws -> AnyNativeObjectCreator {
        .init(workspace: try workspace(), journal: journal,
            dispatch: { intent, authorize in try await native.create(intent, authorize: authorize) },
            inspect: { try await native.read($0) })
    }
    func testOptionalEmptyCollectionsAreNativeValid() async throws {
        let journal = CreationMemoryJournal(try workspace()), native = CreationNativeFixture()
        let creator = try creator(journal, native), plan = try intent()
        let id = try await creator.ensureObject(plan, authorize: {})
        XCTAssertEqual(id, "created-object")
        let state = try await journal.lookup(plan.identity)
        XCTAssertEqual(state, .verified(id))
    }
    func testVerifiedRetryReadsSameIDWithoutOverwritingUserRename() async throws {
        let journal = CreationMemoryJournal(try workspace()), native = CreationNativeFixture()
        let creator = try creator(journal, native), plan = try intent()
        _ = try await creator.ensureObject(plan, authorize: {})
        await native.setTitle("user rename")
        let id = try await creator.ensureObject(plan, authorize: {})
        let count = await native.calls
        XCTAssertEqual(id, "created-object"); XCTAssertEqual(count, 1)
    }
    func testLostReplyNeverCreatesFreshObjectOnRetryOrNewOwner() async throws {
        let journal = CreationMemoryJournal(try workspace()), native = CreationNativeFixture()
        await native.setFailure(dispatch: true)
        let creator = try creator(journal, native), plan = try intent()
        do { _ = try await creator.ensureObject(plan, authorize: {}); XCTFail() } catch {}
        let reopened = try self.creator(journal, native)
        do { _ = try await reopened.ensureObject(plan, authorize: {}); XCTFail() }
        catch { XCTAssertEqual(error as? AnyNativeCreationError, .writeUncertain) }
        let count = await native.calls
        XCTAssertEqual(count, 1)
    }
    func testAcceptedIDPersistsBeforeFailedReadbackAndCanBeVerifiedLater() async throws {
        let journal = CreationMemoryJournal(try workspace()), native = CreationNativeFixture()
        await native.setFailure(read: true)
        let creator = try creator(journal, native), plan = try intent()
        do { _ = try await creator.ensureObject(plan, authorize: {}); XCTFail() } catch {}
        let saved = try await creator.recordedObjectID(for: plan)
        XCTAssertEqual(saved, "created-object")
        await native.setFailure()
        _ = try await creator.ensureObject(plan, authorize: {})
        let count = await native.calls
        XCTAssertEqual(count, 1)
    }
    func testIncompleteCreationRetainsIDAndDoesNotClaimVerification() async throws {
        let journal = CreationMemoryJournal(try workspace()), native = CreationNativeFixture(title: "wrong")
        let creator = try creator(journal, native), plan = try intent()
        do { _ = try await creator.ensureObject(plan, authorize: {}); XCTFail() }
        catch { XCTAssertEqual(error as? AnyNativeCreationError, .createdObjectIncomplete("created-object")) }
        let state = try await journal.lookup(plan.identity)
        XCTAssertEqual(state, .created("created-object"))
    }
    func testSameMutationWithDifferentBodyIsConflictBeforeNativeDispatch() async throws {
        let journal = CreationMemoryJournal(try workspace()), native = CreationNativeFixture()
        let creator = try creator(journal, native)
        _ = try await creator.ensureObject(intent(), authorize: {})
        do { _ = try await creator.ensureObject(intent(title: "other"), authorize: {}); XCTFail() }
        catch { XCTAssertEqual(error as? AnyNativeCreationError, .contentConflict) }
        let count = await native.calls
        XCTAssertEqual(count, 1)
    }
    func testConcurrentSameIntentCannotDispatchTwice() async throws {
        let journal = CreationMemoryJournal(try workspace()), release = CreationGate(), entered = CreationGate()
        let native = CreationNativeFixture(entered: entered, release: release)
        let creator = try creator(journal, native), plan = try intent()
        let first = Task { try await creator.ensureObject(plan, authorize: {}) }
        await entered.wait()
        do { _ = try await creator.ensureObject(plan, authorize: {}); XCTFail() }
        catch { XCTAssertEqual(error as? AnyNativeCreationError, .writeUncertain) }
        await release.open()
        _ = try await first.value
        let count = await native.calls
        XCTAssertEqual(count, 1)
    }
    func testForegroundCancellationSettlesOriginalReceiptBeforeLeaseDrain() async throws {
        let journal = CreationMemoryJournal(try workspace()), release = CreationGate(), entered = CreationGate()
        let native = CreationNativeFixture(entered: entered, release: release)
        let creator = try creator(journal, native), plan = try intent(), confirmation = NativeConfirmation()
        let owner = AnyApplicationSession(workspace: try workspace(), engineStartedAt: "run", verifyRun: { "run" })
        let pending = Task {
            try await owner.perform { lease in
                try await creator.ensureObject(plan, authorize: { try await lease.validate() },
                    onNativeConfirmed: { await confirmation.record($0) })
            }
        }
        await entered.wait()
        pending.cancel()
        let drain = Task { await owner.revokeAndDrain() }
        await release.open()
        do { _ = try await pending.value; XCTFail("cancelled delivery") } catch {}
        await drain.value
        let state = try await journal.lookup(plan.identity), confirmed = await confirmation.values
        XCTAssertEqual(state, .verified("created-object"))
        XCTAssertEqual(confirmed, ["created-object"])
    }
    func testDeniedAuthorizationDoesNotReserveOrDispatch() async throws {
        let journal = CreationMemoryJournal(try workspace()), native = CreationNativeFixture()
        let creator = try creator(journal, native), plan = try intent()
        do { _ = try await creator.ensureObject(plan, authorize: { throw AnyHostError.sessionClosed }); XCTFail() } catch {}
        let state = try await journal.lookup(plan.identity), calls = await native.calls
        XCTAssertNil(state); XCTAssertEqual(calls, 0)
    }
    func testAnotherWorkspaceCannotUseThisCreator() async throws {
        let journal = CreationMemoryJournal(try workspace()), native = CreationNativeFixture()
        let creator = try creator(journal, native)
        let foreign = try AnyNativeObjectCreationIntent(workspace: workspace("other"), mutationID: String(repeating: "a", count: 32),
            typeID: "page", initialProperties: .object(["any": .object(["name": .string("original")])]))
        do { _ = try await creator.ensureObject(foreign, authorize: {}); XCTFail() }
        catch { XCTAssertEqual(error as? AnyHostError, .wrongWorkspace) }
        let count = await native.calls
        XCTAssertEqual(count, 0)
    }
    func testIntentFingerprintCannotBeTamperedDuringDecode() throws {
        let encoded = try JSONEncoder().encode(intent())
        var object = try JSONSerialization.jsonObject(with: encoded) as! [String: Any]
        object["fingerprint"] = String(repeating: "f", count: 64)
        XCTAssertThrowsError(try JSONDecoder().decode(AnyNativeObjectCreationIntent.self,
            from: JSONSerialization.data(withJSONObject: object)))
    }
    func testCanonicalValuesSeparateTypesAndIgnoreDictionaryInsertionOrder() throws {
        XCTAssertNotEqual(try AnyHostCanonical.bytes(.integer(1)), try AnyHostCanonical.bytes(.string("1")))
        XCTAssertNotEqual(try AnyHostCanonical.bytes(.array([.string("a"), .string("bc")])),
                          try AnyHostCanonical.bytes(.array([.string("ab"), .string("c")])))
        XCTAssertEqual(try AnyHostCanonical.bytes(.object(["b": .integer(2), "a": .integer(1)])),
                       try AnyHostCanonical.bytes(.object(["a": .integer(1), "b": .integer(2)])))
    }
    #if canImport(Darwin)
    private func journalJSONFiles(in parent: URL) -> [URL] {
        let enumerator = FileManager.default.enumerator(at: parent, includingPropertiesForKeys: [.isRegularFileKey])!
        return enumerator.compactMap { $0 as? URL }.filter { $0.pathExtension == "json" }
    }

    func testProtectedJournalReopensReceiptsWithoutBusinessPayload() async throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let plan = try intent(title: "private business title")
        let journal = try AnyProtectedCreationJournal.openForTesting(workspace: workspace(), parent: parent)
        _ = try await journal.reserve(plan.identity)
        try await journal.record(.created("created-object"), identity: plan.identity)
        try await journal.record(.verified("created-object"), identity: plan.identity)
        await journal.close()
        let next = try AnyProtectedCreationJournal.openForTesting(workspace: workspace(), parent: parent)
        let result = try await next.reserve(plan.identity)
        XCTAssertFalse(result.ownsDispatch); XCTAssertEqual(result.state, .verified("created-object"))
        for file in journalJSONFiles(in: parent) {
            XCTAssertFalse(String(decoding: try Data(contentsOf: file), as: UTF8.self).contains(plan.initialProperties["any"]!["name"]!.string!))
        }
        await next.close()
    }
    func testProtectedJournalExclusiveOwnerAndUnresolvedReopen() async throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let journal = try AnyProtectedCreationJournal.openForTesting(workspace: workspace(), parent: parent)
        _ = try await journal.reserve(intent().identity)
        XCTAssertThrowsError(try AnyProtectedCreationJournal.openForTesting(workspace: workspace(), parent: parent))
        await journal.close()
        let reopened = try AnyProtectedCreationJournal.openForTesting(workspace: workspace(), parent: parent)
        let record = try await reopened.reserve(intent().identity)
        XCTAssertEqual(record.state, .reserved); XCTAssertFalse(record.ownsDispatch)
        await reopened.close()
    }
    func testProtectedJournalRejectsSymlinkDirectory() throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let target = parent.appendingPathComponent("other")
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: false)
        try FileManager.default.createSymbolicLink(at: parent.appendingPathComponent("AnyNativeCreationMetadataV1"),
                                                  withDestinationURL: target)
        XCTAssertThrowsError(try AnyProtectedCreationJournal.openForTesting(workspace: workspace(), parent: parent))
    }
    #endif
}
