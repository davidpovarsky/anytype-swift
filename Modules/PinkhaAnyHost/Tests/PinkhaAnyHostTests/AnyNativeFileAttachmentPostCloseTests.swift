import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

// Component fixtures only. The backing below models the same original journal
// reservation across closed adapters; it does not qualify protected-file locks,
// an Apple owner transition, or persistence of the volatile acknowledgement.
private actor PostCloseJournalBacking {
    private var identities: [String: AnyNativeCreationIdentity] = [:]
    private var states: [String: AnyNativeCreationState] = [:]

    init(identity: AnyNativeCreationIdentity? = nil, state: AnyNativeCreationState = .reserved) {
        if let identity {
            identities[identity.key] = identity
            states[identity.key] = state
        }
    }

    func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        if let old = identities[identity.key] {
            guard old == identity, let state = states[identity.key] else {
                throw AnyNativeCreationError.contentConflict
            }
            return .init(state: state, ownsDispatch: false)
        }
        identities[identity.key] = identity
        states[identity.key] = .reserved
        return .init(state: .reserved, ownsDispatch: true)
    }

    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        guard identities[identity.key] == identity, let old = states[identity.key] else {
            throw AnyNativeCreationError.contentConflict
        }
        switch (old, state) {
        case (.reserved, .created): break
        case (.created(let before), .verified(let after)) where before == after: break
        case (.verified(let before), .verified(let after)) where before == after: break
        default: throw AnyNativeCreationError.contentConflict
        }
        states[identity.key] = state
    }

    func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        if let old = identities[identity.key], old != identity {
            throw AnyNativeCreationError.contentConflict
        }
        return states[identity.key]
    }
}

private actor PostCloseJournal: AnyNativeCreationJournaling {
    struct Observations: Equatable, Sendable {
        var reserves = 0
        var records = 0
        var lookups = 0
        var closedIOAttempts = 0
        var poisoned = false
        var closed = false
    }

    nonisolated let workspace: AnyTorahWorkspace
    private let backing: PostCloseJournalBacking
    private let poisonCreatedReceipt: Bool
    private var observations = Observations()

    init(_ workspace: AnyTorahWorkspace, backing: PostCloseJournalBacking,
         poisonCreatedReceipt: Bool = false) {
        self.workspace = workspace
        self.backing = backing
        self.poisonCreatedReceipt = poisonCreatedReceipt
    }

    private func admitIO() throws {
        if observations.closed {
            observations.closedIOAttempts += 1
            throw AnyNativeCreationError.journalUnavailable
        }
        guard !observations.poisoned else { throw AnyNativeCreationError.journalUnavailable }
    }

    func reserve(_ identity: AnyNativeCreationIdentity) async throws -> AnyNativeCreationReservation {
        observations.reserves += 1
        try admitIO()
        return try await backing.reserve(identity)
    }

    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) async throws {
        observations.records += 1
        try admitIO()
        if poisonCreatedReceipt, case .created = state {
            observations.poisoned = true
            throw AnyNativeCreationError.journalUnavailable
        }
        try await backing.record(state, identity: identity)
    }

    func lookup(_ identity: AnyNativeCreationIdentity) async throws -> AnyNativeCreationState? {
        observations.lookups += 1
        try admitIO()
        return try await backing.lookup(identity)
    }

    func close() { observations.closed = true }
    func snapshot() -> Observations { observations }
}

private actor PostCloseReadLease {
    enum Boundary: Sendable { case current, retireOnFirstRead, retireOnSecondRead, cancelAfterSecondRead }
    struct Observations: Equatable, Sendable {
        var reads = 0
        var approvals = 0
        var currentGeneration: UInt64
        var cancellationInjected = false
    }

    private let workspace: AnyTorahWorkspace
    private let objectID: String
    private let capturedGeneration: UInt64
    private let boundary: Boundary
    private var observations: Observations

    init(_ intent: AnyNativeFileAttachmentIntent, generation: UInt64,
         boundary: Boundary = .current) {
        workspace = intent.workspace
        objectID = intent.objectID
        capturedGeneration = generation
        self.boundary = boundary
        observations = .init(currentGeneration: generation)
    }

    private func requireCurrent(_ intent: AnyNativeFileAttachmentIntent) throws {
        guard observations.currentGeneration == capturedGeneration,
              workspace.accountID.utf8.elementsEqual(intent.workspace.accountID.utf8),
              workspace.spaceID.utf8.elementsEqual(intent.workspace.spaceID.utf8),
              objectID.utf8.elementsEqual(intent.objectID.utf8) else {
            throw AnyEngineError.accountChanged
        }
    }

    func validate(_ intent: AnyNativeFileAttachmentIntent) throws {
        observations.reads += 1
        switch (boundary, observations.reads) {
        case (.retireOnFirstRead, 1), (.retireOnSecondRead, 2):
            observations.currentGeneration += 1
        default: break
        }
        try requireCurrent(intent)
        if case .cancelAfterSecondRead = boundary, observations.reads == 2 {
            // Deliberately return normally after cancellation, so the production
            // check AFTER the final authorization await must refuse delivery.
            withUnsafeCurrentTask { $0?.cancel() }
            observations.cancellationInjected = Task.isCancelled
        }
    }

    func approve(_ intent: AnyNativeFileAttachmentIntent) throws {
        try requireCurrent(intent)
        observations.approvals += 1
    }

    func retire() { observations.currentGeneration += 1 }
    func snapshot() -> Observations { observations }
}

private actor PostCloseNative {
    enum Acknowledgement: Sendable { case original, missing }
    struct Observations: Equatable, Sendable {
        var uploads = 0
        var metadataReads = 0
        var digestReads = 0
        var activeUploadCalls = 0
        var finishedUploadCalls = 0
        var retiredCallAttempts = 0
        var cancellationObservedAfterDispatch = false
        var acknowledgementDelivered = false
        var retired = false
    }

    private let acknowledgement: Acknowledgement
    private var observations = Observations()

    init(_ acknowledgement: Acknowledgement = .original) { self.acknowledgement = acknowledgement }

    private func requireActive() throws {
        if observations.retired {
            observations.retiredCallAttempts += 1
            throw AnyEngineError.accountChanged
        }
    }

    func upload(_ specification: AnyNativeFileUploadSpecification, _ fileURL: URL,
        _ validate: @escaping AnyNativeFileAttachmentCreator.Check,
        _ authorize: @escaping AnyNativeFileAttachmentCreator.Check,
        _ retain: @escaping @Sendable (AnyNativeAttachedFile) async throws -> Void) async throws -> AnyNativeAttachedFile {
        try requireActive()
        try await validate()
        try await authorize()
        observations.uploads += 1
        observations.activeUploadCalls += 1
        defer {
            observations.activeUploadCalls -= 1
            observations.finishedUploadCalls += 1
        }
        // This is the actual original task, after its one dispatch admission.
        // A late native acknowledgement intentionally ignores its cancellation.
        withUnsafeCurrentTask { $0?.cancel() }
        observations.cancellationObservedAfterDispatch = Task.isCancelled
        if case .missing = acknowledgement {
            throw AnyNativeFileUploadUncertain(knownReceipt: nil, underlying: AnyEngineError.writeUncertain)
        }
        let receipt = try Self.file(specification)
        observations.acknowledgementDelivered = true
        do {
            try await retain(receipt)
            return receipt
        } catch {
            throw AnyNativeFileUploadUncertain(knownReceipt: .init(receipt: receipt), underlying: error)
        }
    }

    func inspect(_ specification: AnyNativeFileUploadSpecification, _ fileID: String,
                 _ authorize: @escaping AnyNativeFileAttachmentCreator.Check) async throws -> AnyNativeAttachedFile {
        try requireActive()
        try await authorize()
        observations.metadataReads += 1
        guard fileID == "Bst4MGoLyBW" else { throw AnyNativeFileAttachmentError.writeUncertain }
        return try Self.file(specification)
    }

    func digest(_ file: AnyNativeAttachedFile,
                _ authorize: @escaping AnyNativeFileAttachmentCreator.Check) async throws -> AnyHTTPFileContentDigest {
        try requireActive()
        try await authorize()
        observations.digestReads += 1
        guard file.reference.fileID == "Bst4MGoLyBW", file.byteCount == 4 else {
            throw AnyNativeFileAttachmentError.writeUncertain
        }
        return try JSONDecoder().decode(AnyHTTPFileContentDigest.self, from: JSONEncoder().encode(
            AnyJSON.object(["byteCount": .integer(4),
                "sha256": .string(AnyContentDigest.sha256(Data("data".utf8)))])))
    }

    private static func file(_ specification: AnyNativeFileUploadSpecification) throws -> AnyNativeAttachedFile {
        try .init(native: .object([
            "fileId": .string("Bst4MGoLyBW"), "objectId": .string(specification.objectID),
            "size": .integer(specification.size), "inline": .bool(true),
            "durable": .bool(true), "cached": .bool(true),
            "name": .string(specification.name), "mime": .string(specification.mime)
        ]), specification: specification, expectedFileID: "Bst4MGoLyBW")
    }

    func retireAfterDrain() throws {
        guard observations.activeUploadCalls == 0, observations.finishedUploadCalls == 1 else {
            throw AnyNativeCreationError.journalUnavailable
        }
        observations.retired = true
    }
    func snapshot() -> Observations { observations }
}

@MainActor
final class AnyNativeFileAttachmentPostCloseTests: XCTestCase {
    private struct ClosedOriginal {
        let intent: AnyNativeFileAttachmentIntent
        let owner: AnyNativeFileAttachmentCreator
        let backing: PostCloseJournalBacking
        let journal: PostCloseJournal
        let native: PostCloseNative
        let lease: PostCloseReadLease
        let journalAtClose: PostCloseJournal.Observations
        let nativeAtClose: PostCloseNative.Observations
        let leaseAtClose: PostCloseReadLease.Observations
    }

    private let fileURL = URL(fileURLWithPath: "/not-opened-by-post-close-component-fixture")

    private func intent(name: String = "post-close-private.txt", object: String = "original-object",
                        account: String = "original-account", space: String = "original-space") throws -> AnyNativeFileAttachmentIntent {
        try .init(workspace: .init(accountID: account, spaceID: space),
            mutationID: String(repeating: "d", count: 32), objectID: object, name: name,
            mime: "text/plain", byteCount: 4, contentSHA256: AnyContentDigest.sha256(Data("data".utf8)))
    }

    private func creator(_ action: AnyNativeFileAttachmentIntent, journal: PostCloseJournal,
                         native: PostCloseNative) throws -> AnyNativeFileAttachmentCreator {
        try .init(workspace: action.workspace, journal: journal,
            upload: { try await native.upload($0, $1, $2, $3, $4) },
            inspect: { try await native.inspect($0, $1, $2) },
            digest: { try await native.digest($0, $1) })
    }

    private func closedOriginal(_ acknowledgement: PostCloseNative.Acknowledgement = .original) async throws -> ClosedOriginal {
        let action = try intent()
        let backing = PostCloseJournalBacking()
        let journal = PostCloseJournal(action.workspace, backing: backing, poisonCreatedReceipt: true)
        let native = PostCloseNative(acknowledgement)
        let lease = PostCloseReadLease(action, generation: 1)
        let owner = try creator(action, journal: journal, native: native)
        let url = fileURL
        let flight = Task {
            try await owner.attach(action, fileURL: url,
                authorizeRead: { try await lease.validate(action) },
                authorizeAttachment: { try await lease.approve(action) })
        }
        let expected: AnyNativeFileAttachmentError
        switch acknowledgement {
        case .original: expected = .knownFileUnverified("Bst4MGoLyBW")
        case .missing: expected = .writeUncertain
        }
        do {
            _ = try await flight.value
            XCTFail("cancelled original unexpectedly delivered success")
            throw AnyNativeFileAttachmentError.writeUncertain
        } catch let error as AnyNativeFileAttachmentError {
            guard error == expected else { throw error }
        }
        // Awaited completion, including the native defer, precedes both closes.
        let drained = await native.snapshot()
        XCTAssertEqual(drained.uploads, 1)
        XCTAssertEqual(drained.activeUploadCalls, 0)
        XCTAssertEqual(drained.finishedUploadCalls, 1)
        XCTAssertTrue(drained.cancellationObservedAfterDispatch)
        XCTAssertTrue(flight.isCancelled)
        try await native.retireAfterDrain()
        await journal.close()
        await lease.retire()
        let journalAtClose = await journal.snapshot()
        let nativeAtClose = await native.snapshot()
        let leaseAtClose = await lease.snapshot()
        XCTAssertTrue(journalAtClose.closed)
        if case .original = acknowledgement { XCTAssertTrue(journalAtClose.poisoned) }
        XCTAssertEqual(journalAtClose.closedIOAttempts, 0)
        XCTAssertEqual(nativeAtClose.metadataReads, 0)
        XCTAssertEqual(nativeAtClose.digestReads, 0)
        XCTAssertEqual(nativeAtClose.retiredCallAttempts, 0)
        XCTAssertEqual(leaseAtClose.approvals, 1)
        return .init(intent: action, owner: owner, backing: backing, journal: journal,
            native: native, lease: lease, journalAtClose: journalAtClose,
            nativeAtClose: nativeAtClose, leaseAtClose: leaseAtClose)
    }

    private func assertRetiredUntouched(_ original: ClosedOriginal,
        file: StaticString = #filePath, line: UInt = #line) async {
        let journal = await original.journal.snapshot()
        let native = await original.native.snapshot()
        let lease = await original.lease.snapshot()
        XCTAssertEqual(journal, original.journalAtClose, file: file, line: line)
        XCTAssertEqual(native, original.nativeAtClose, file: file, line: line)
        XCTAssertEqual(lease, original.leaseAtClose, file: file, line: line)
    }

    private func expect<E: Error & Equatable>(_ expected: E,
        _ operation: () async throws -> Void, file: StaticString = #filePath, line: UInt = #line) async {
        do { try await operation(); XCTFail("expected \(expected)", file: file, line: line) }
        catch { XCTAssertEqual(error as? E, expected, file: file, line: line) }
    }

    func testPostCloseMemoryExportRecoversSameReservationThroughNewNativeOwner() async throws {
        let original = try await closedOriginal()
        let action = original.intent
        let reopened = PostCloseJournal(action.workspace, backing: original.backing)
        let freshNative = PostCloseNative()
        let freshOwner = try creator(action, journal: reopened, native: freshNative)
        let authority = PostCloseReadLease(action, generation: 2)
        let witness = try await original.owner.retainedRecoveryReceipt(for: action,
            authorizeRead: { try await authority.validate(action) })
        let exported = await authority.snapshot()
        XCTAssertEqual(exported.reads, 2)
        XCTAssertEqual(exported.approvals, 0)
        XCTAssertFalse(String(describing: witness).contains(action.name))
        XCTAssertFalse(String(reflecting: witness).contains(action.objectID))
        await assertRetiredUntouched(original)

        let before = try await reopened.lookup(action.identity)
        XCTAssertEqual(before, .reserved)
        let result = try await freshOwner.resume(action, recoveryReceipt: witness,
            authorizeRead: { try await authority.validate(action) })
        XCTAssertEqual(result.reference.fileID, "Bst4MGoLyBW")
        let final = try await reopened.lookup(action.identity)
        let calls = await freshNative.snapshot()
        let journalCalls = await reopened.snapshot()
        XCTAssertEqual(final, .verified("Bst4MGoLyBW"))
        XCTAssertEqual(calls.uploads, 0)
        XCTAssertEqual(calls.metadataReads, 2)
        XCTAssertEqual(calls.digestReads, 1)
        XCTAssertEqual(journalCalls.reserves, 0)
        XCTAssertEqual(journalCalls.records, 2)
        await assertRetiredUntouched(original)
    }

    func testPostCloseExportRechecksBothFreshReadsAndFinalCancellationWithoutLosingMemory() async throws {
        let boundaries: [PostCloseReadLease.Boundary] = [.retireOnFirstRead, .retireOnSecondRead, .cancelAfterSecondRead]
        for boundary in boundaries {
            let original = try await closedOriginal()
            let action = original.intent
            let authority = PostCloseReadLease(action, generation: 2, boundary: boundary)
            let export = Task {
                try await original.owner.retainedRecoveryReceipt(for: action,
                    authorizeRead: { try await authority.validate(action) })
            }
            switch boundary {
            case .retireOnFirstRead, .retireOnSecondRead:
                await expect(AnyEngineError.accountChanged) { _ = try await export.value }
            case .cancelAfterSecondRead:
                do { _ = try await export.value; XCTFail("cancelled final authorization delivered a witness") }
                catch { XCTAssertTrue(error is CancellationError) }
                XCTAssertTrue(export.isCancelled)
            case .current: XCTFail("unexpected control")
            }
            let refused = await authority.snapshot()
            if case .retireOnFirstRead = boundary { XCTAssertEqual(refused.reads, 1) }
            else { XCTAssertEqual(refused.reads, 2) }
            if case .cancelAfterSecondRead = boundary { XCTAssertTrue(refused.cancellationInjected) }
            XCTAssertEqual(refused.approvals, 0)
            await assertRetiredUntouched(original)

            // Each failure must leave the original private memory intact. A new
            // current lease succeeds twice, without reopening the old adapter.
            let current = PostCloseReadLease(action, generation: 3)
            _ = try await original.owner.retainedRecoveryReceipt(for: action,
                authorizeRead: { try await current.validate(action) })
            let retried = await current.snapshot()
            XCTAssertEqual(retried.reads, 2)
            XCTAssertEqual(retried.approvals, 0)
            await assertRetiredUntouched(original)
        }
    }

    func testPostCloseExportRejectsForeignWorkspaceAndChangedIntentWithoutRetiredIO() async throws {
        let original = try await closedOriginal()
        let action = original.intent
        for foreign in [try intent(account: "other-account"), try intent(space: "other-space")] {
            let authority = PostCloseReadLease(action, generation: 2)
            await expect(AnyHostError.wrongWorkspace) {
                _ = try await original.owner.retainedRecoveryReceipt(for: foreign,
                    authorizeRead: { try await authority.validate(action) })
            }
            let observations = await authority.snapshot()
            XCTAssertEqual(observations.reads, 0)
        }
        for changed in [try intent(name: "changed-intent.txt"), try intent(object: "other-object")] {
            let authority = PostCloseReadLease(action, generation: 2)
            await expect(AnyNativeFileAttachmentError.contentConflict) {
                _ = try await original.owner.retainedRecoveryReceipt(for: changed,
                    authorizeRead: { try await authority.validate(action) })
            }
            let observations = await authority.snapshot()
            XCTAssertEqual(observations.reads, 1)
        }
        let current = PostCloseReadLease(action, generation: 3)
        _ = try await original.owner.retainedRecoveryReceipt(for: action,
            authorizeRead: { try await current.validate(action) })
        let accepted = await current.snapshot()
        XCTAssertEqual(accepted.reads, 2)
        await assertRetiredUntouched(original)
    }

    func testPostCloseUnknownAcknowledgementAndForeignReservationCannotDispatchOrInventRecovery() async throws {
        let unknown = try await closedOriginal(.missing)
        let action = unknown.intent
        let authority = PostCloseReadLease(action, generation: 2)
        await expect(AnyNativeFileAttachmentError.writeUncertain) {
            _ = try await unknown.owner.retainedRecoveryReceipt(for: action,
                authorizeRead: { try await authority.validate(action) })
        }
        let deniedExport = await authority.snapshot()
        XCTAssertEqual(deniedExport.reads, 1)
        let reopened = PostCloseJournal(action.workspace, backing: unknown.backing)
        let freshNative = PostCloseNative()
        let freshOwner = try creator(action, journal: reopened, native: freshNative)
        await expect(AnyNativeFileAttachmentError.writeUncertain) {
            _ = try await freshOwner.resume(action, authorizeRead: { try await authority.validate(action) })
        }
        let unresolved = try await reopened.lookup(action.identity)
        XCTAssertEqual(unresolved, .reserved)
        let noCalls = await freshNative.snapshot()
        XCTAssertEqual(noCalls.uploads, 0)
        XCTAssertEqual(noCalls.metadataReads, 0)
        XCTAssertEqual(noCalls.digestReads, 0)
        XCTAssertFalse(unknown.nativeAtClose.acknowledgementDelivered)
        await assertRetiredUntouched(unknown)

        let known = try await closedOriginal()
        let knownAction = known.intent
        let current = PostCloseReadLease(knownAction, generation: 2)
        let witness = try await known.owner.retainedRecoveryReceipt(for: knownAction,
            authorizeRead: { try await current.validate(knownAction) })
        let invalidNative = PostCloseNative()
        let absent = PostCloseJournal(knownAction.workspace, backing: PostCloseJournalBacking())
        let absentOwner = try creator(knownAction, journal: absent, native: invalidNative)
        await expect(AnyNativeFileAttachmentError.noRecordedAttachment) {
            _ = try await absentOwner.resume(knownAction, recoveryReceipt: witness,
                authorizeRead: { try await current.validate(knownAction) })
        }
        let wrongID = PostCloseJournal(knownAction.workspace,
            backing: PostCloseJournalBacking(identity: knownAction.identity, state: .created("A7cZ9y2KpQ4")))
        let wrongIDOwner = try creator(knownAction, journal: wrongID, native: invalidNative)
        await expect(AnyNativeFileAttachmentError.writeUncertain) {
            _ = try await wrongIDOwner.resume(knownAction, recoveryReceipt: witness,
                authorizeRead: { try await current.validate(knownAction) })
        }
        let changed = try intent(name: "different-original-reservation.txt")
        let mismatch = PostCloseJournal(knownAction.workspace,
            backing: PostCloseJournalBacking(identity: changed.identity))
        let mismatchOwner = try creator(knownAction, journal: mismatch, native: invalidNative)
        await expect(AnyNativeCreationError.contentConflict) {
            _ = try await mismatchOwner.resume(knownAction, recoveryReceipt: witness,
                authorizeRead: { try await current.validate(knownAction) })
        }
        let invalidCalls = await invalidNative.snapshot()
        XCTAssertEqual(invalidCalls.uploads, 0)
        XCTAssertEqual(invalidCalls.metadataReads, 0)
        XCTAssertEqual(invalidCalls.digestReads, 0)
        for journal in [absent, wrongID, mismatch] {
            let observations = await journal.snapshot()
            XCTAssertEqual(observations.reserves, 0)
            XCTAssertEqual(observations.records, 0)
        }
        await assertRetiredUntouched(known)
    }
}
