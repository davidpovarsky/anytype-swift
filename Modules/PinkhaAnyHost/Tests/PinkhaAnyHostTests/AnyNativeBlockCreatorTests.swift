
import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

@Suite("Native block intent and shared creation journal")
struct AnyNativeBlockCreatorTests {
    private let workspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")
    private func intent(_ suffix: String = "1", text: String = "שלום **מקור**") throws -> AnyNativeBlockCreationIntent {
        try .init(workspace: workspace, mutationID: String(repeating: suffix, count: 32),
                  objectID: "document", type: "quote", text: text,
                  style: .object(["pinkhaWritingDirection": .string("rightToLeft"),
                                  "futureStyle": .object(["nested": .bool(true)])]),
                  parentID: "parent", position: "PPPP")
    }

    @Test func validatedIntentPreservesTextUnknownStyleAndNativeLocationAcrossEncoding() throws {
        let value = try intent()
        let decoded = try JSONDecoder().decode(AnyNativeBlockCreationIntent.self, from: JSONEncoder().encode(value))
        #expect(decoded == value)
        #expect(decoded.identity.kind == "editorBlock")
        #expect(decoded.body["nav"]?["parentId"]?.string == "parent")
        #expect(decoded.body["style"]?["futureStyle"]?["nested"]?.bool == true)
        var object = try #require(JSONSerialization.jsonObject(with: JSONEncoder().encode(value)) as? [String: Any])
        object["position"] = ""
        #expect(throws: Error.self) {
            try JSONDecoder().decode(AnyNativeBlockCreationIntent.self, from: JSONSerialization.data(withJSONObject: object))
        }
    }

    @Test func changedIntentCannotReuseTheSameJournalIdentity() async throws {
        let value = try intent(), changed = try intent(text: "different source")
        let journal = BlockJournalFixture(workspace: workspace)
        _ = try await journal.reserve(value.identity)
        await #expect(throws: AnyNativeCreationError.contentConflict) {
            try await journal.reserve(changed.identity)
        }
    }

    @Test func exactRetryUsesKnownNativeIDAndPreservesLaterUserEdits() async throws {
        let value = try intent()
        let journal = BlockJournalFixture(workspace: workspace), effects = BlockEffectsFixture()
        let creator = make(journal: journal, effects: effects)
        let id = try await creator.ensureBlock(value, authorize: {})
        await effects.changeText("later edit")
        #expect(try await creator.ensureBlock(value, authorize: {}) == id)
        #expect(await effects.count == 1)
        #expect(await effects.row["text"]?.string == "later edit")
        #expect(try await journal.lookup(value.identity) == .verified(id))
    }

    @Test func lostAutoIDReplyStaysUncertainAndNeverCreatesAnotherBlock() async throws {
        let value = try intent()
        let journal = BlockJournalFixture(workspace: workspace), effects = BlockEffectsFixture()
        let creator = make(journal: journal, effects: effects, loseReply: true)
        await #expect(throws: AnyNativeCreationError.writeUncertain) {
            try await creator.ensureBlock(value, authorize: {})
        }
        await #expect(throws: AnyNativeCreationError.writeUncertain) {
            try await creator.ensureBlock(value, authorize: {})
        }
        #expect(await effects.count == 1)
        #expect(try await journal.lookup(value.identity) == .reserved)
    }

    @Test func mismatchedReadbackRetainsCreatedIDWithoutReportingVerified() async throws {
        let value = try intent()
        let journal = BlockJournalFixture(workspace: workspace), effects = BlockEffectsFixture()
        let creator = make(journal: journal, effects: effects, mismatch: true)
        await #expect(throws: AnyNativeCreationError.createdObjectIncomplete("native-block")) {
            try await creator.ensureBlock(value, authorize: {})
        }
        #expect(try await creator.recordedBlockID(for: value) == "native-block")
        #expect(try await journal.lookup(value.identity) == .created("native-block"))
        #expect(await effects.count == 1)
    }

    @Test func cancellationAfterDispatchSettlesNativeReceiptBeforeReturning() async throws {
        let value = try intent(), gate = BlockGateFixture()
        let journal = BlockJournalFixture(workspace: workspace), effects = BlockEffectsFixture()
        let creator = make(journal: journal, effects: effects, gate: gate)
        let request = Task { try await creator.ensureBlock(value, authorize: {}) }
        await gate.waitUntilHeld()
        request.cancel()
        await gate.release()
        do { _ = try await request.value; Issue.record("Cancelled caller must not receive successful UI delivery") }
        catch { #expect(error is CancellationError) }
        #expect(try await journal.lookup(value.identity) == .verified("native-block"))
        #expect(await effects.count == 1)
    }

    @Test func revocationBeforeDispatchCannotCreateNativeContent() async throws {
        let value = try intent()
        let journal = BlockJournalFixture(workspace: workspace), effects = BlockEffectsFixture()
        let creator = make(journal: journal, effects: effects)
        await #expect(throws: AnyHostError.sessionClosed) {
            try await creator.ensureBlock(value, authorize: { throw AnyHostError.sessionClosed })
        }
        #expect(await effects.count == 0)
        #expect(try await journal.lookup(value.identity) == nil)
    }

    @Test func unsupportedNativeContractDoesNotReserveOrDispatch() async throws {
        let value = try intent()
        let journal = BlockJournalFixture(workspace: workspace), effects = BlockEffectsFixture()
        let creator = make(journal: journal, effects: effects, validateCreation: { _ in
            throw AnyEngineError.incompatibleSchema("block creation unavailable")
        })
        await #expect(throws: AnyEngineError.incompatibleSchema("block creation unavailable")) {
            try await creator.ensureBlock(value, authorize: {})
        }
        #expect(await effects.count == 0)
        #expect(try await journal.lookup(value.identity) == nil)
    }

    @Test func contractRevokedAtDispatchCannotCreateAndRetainsOriginalIntent() async throws {
        let value = try intent()
        let journal = BlockJournalFixture(workspace: workspace), effects = BlockEffectsFixture()
        let contract = BlockContractFixture()
        let creator = make(journal: journal, effects: effects,
                           validateCreation: { _ in try await contract.validate() })
        await #expect(throws: AnyNativeCreationError.writeUncertain) {
            try await creator.ensureBlock(value, authorize: {})
        }
        #expect(await contract.count == 2)
        #expect(await effects.count == 0)
        #expect(try await journal.lookup(value.identity) == .reserved)
    }

    private func make(journal: BlockJournalFixture, effects: BlockEffectsFixture,
                      loseReply: Bool = false, mismatch: Bool = false,
                      gate: BlockGateFixture? = nil,
                      validateCreation: @escaping @Sendable (AnyNativeBlockCreationIntent) async throws -> Void = { _ in }) -> AnyNativeBlockCreator {
        AnyNativeBlockCreator(workspace: workspace, journal: journal,
            dispatch: { intent, authorize in
                try await authorize()
                await effects.create(intent)
                if let gate { await gate.hold() }
                if loseReply { throw URLError(.timedOut) }
                return "native-block"
            }, inspect: { _, _ in
                if mismatch { await effects.changeText("wrong response") }
                return await effects.row
            }, validateCreation: validateCreation)
    }

}

private actor BlockJournalFixture: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    var values: [String: (AnyNativeCreationIdentity, AnyNativeCreationState)] = [:]
    init(workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        if let old = values[identity.key] {
            guard old.0 == identity else { throw AnyNativeCreationError.contentConflict }
            return .init(state: old.1, ownsDispatch: false)
        }
        values[identity.key] = (identity, .reserved)
        return .init(state: .reserved, ownsDispatch: true)
    }
    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        guard values[identity.key]?.0 == identity else { throw AnyNativeCreationError.contentConflict }
        values[identity.key] = (identity, state)
    }
    func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        guard let value = values[identity.key] else { return nil }
        guard value.0 == identity else { throw AnyNativeCreationError.contentConflict }
        return value.1
    }
}

private actor BlockEffectsFixture {
    var row: AnyJSON = .object([:])
    var count = 0
    func create(_ intent: AnyNativeBlockCreationIntent) {
        count += 1
        var fields = intent.body.object!
        fields["id"] = .string("native-block")
        row = .object(fields)
    }
    func changeText(_ text: String) {
        var fields = row.object!
        fields["text"] = .string(text); row = .object(fields)
    }
}

private actor BlockGateFixture {
    var held = false
    var waiter: CheckedContinuation<Void, Never>?
    var pending: CheckedContinuation<Void, Never>?
    func hold() async {
        await withCheckedContinuation {
            pending = $0; held = true; waiter?.resume(); waiter = nil
        }
    }
    func waitUntilHeld() async {
        if held { return }
        await withCheckedContinuation { waiter = $0 }
    }
    func release() { pending?.resume(); pending = nil }
}

private actor BlockContractFixture {
    var count = 0
    func validate() throws {
        count += 1
        if count > 1 { throw AnyEngineError.incompatibleSchema("block creation revoked") }
    }
}
