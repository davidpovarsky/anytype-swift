import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

private actor AttachmentJournal: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    private var identities: [String: AnyNativeCreationIdentity] = [:]
    private var states: [String: AnyNativeCreationState] = [:]
    private var rejectReceipt = false
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func rejectCreatedReceipt() { rejectReceipt = true }
    func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        if let prior = identities[identity.key] {
            guard prior == identity else { throw AnyNativeCreationError.contentConflict }
            return .init(state: states[identity.key]!, ownsDispatch: false)
        }
        identities[identity.key] = identity; states[identity.key] = .reserved
        return .init(state: .reserved, ownsDispatch: true)
    }
    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        guard identities[identity.key] == identity else { throw AnyNativeCreationError.contentConflict }
        if rejectReceipt { throw AnyNativeCreationError.journalUnavailable }
        guard let old = states[identity.key] else { throw AnyNativeCreationError.corruptJournal }
        switch (old, state) {
        case (.reserved, .created): break
        case (.created(let a), .verified(let b)) where a == b: break
        case (.verified(let a), .verified(let b)) where a == b: break
        default: throw AnyNativeCreationError.contentConflict
        }
        states[identity.key] = state
    }
    func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        if let prior = identities[identity.key], prior != identity { throw AnyNativeCreationError.contentConflict }
        return states[identity.key]
    }
    func encodedIdentity(_ identity: AnyNativeCreationIdentity) throws -> Data {
        try JSONEncoder().encode(identities[identity.key])
    }
}

private actor AttachmentBarrier {
    private var opened = false
    private var waiters: [CheckedContinuation<Void, Never>] = []
    func wait() async {
        if opened { return }
        await withCheckedContinuation { waiters.append($0) }
    }
    func open() {
        opened = true
        let waiting = waiters; waiters.removeAll()
        for waiter in waiting { waiter.resume() }
    }
}

private actor AttachmentAuthority {
    private var active = true
    private var writes = 0
    func validate() throws { if !active { throw AnyEngineError.accountChanged } }
    func approve() throws { try validate(); writes += 1 }
    func setActive(_ value: Bool) { active = value }
    func approvals() -> Int { writes }
}

private actor AttachmentNative {
    enum Failure: Equatable, Sendable { case none, lostAcknowledgement, nativeForbidden, afterReceipt }
    private var mode: Failure = .none
    private var uploads = 0
    private var reads = 0
    private var corruptDigest = false
    private var changedSecondMetadata = false
    private var stableReadName: String?
    let entered = AttachmentBarrier()
    private let release: AttachmentBarrier?
    init(release: AttachmentBarrier? = nil) { self.release = release }
    func configure(_ failure: Failure = .none, badDigest: Bool = false, metadataDrift: Bool = false,
                   stableReadName: String? = nil) {
        mode = failure; corruptDigest = badDigest; changedSecondMetadata = metadataDrift
        self.stableReadName = stableReadName
    }
    func counts() -> (Int, Int) { (uploads, reads) }
    func upload(_ specification: AnyNativeFileUploadSpecification, _ fileURL: URL,
        _ validate: @escaping AnyNativeFileAttachmentCreator.Check,
        _ authorize: @escaping AnyNativeFileAttachmentCreator.Check,
        _ retain: @escaping @Sendable (AnyNativeAttachedFile) async throws -> Void) async throws -> AnyNativeAttachedFile {
        try await validate()
        do { try await authorize() }
        catch { throw AnyNativeFileUploadUncertain(knownReceipt: nil, underlying: error) }
        uploads += 1
        await entered.open()
        if let release { await release.wait() }
        if mode == .lostAcknowledgement {
            throw AnyNativeFileUploadUncertain(knownReceipt: nil, underlying: AnyEngineError.writeUncertain)
        }
        if mode == .nativeForbidden {
            throw AnyNativeFileUploadUncertain(knownReceipt: nil,
                underlying: AnyEngineError.http(status: 403, code: "acl.forbidden"))
        }
        let receipt = try Self.file(specification)
        do {
            try await retain(receipt)
            if mode == .afterReceipt { throw AnyEngineError.accountChanged }
            try await validate()
        } catch {
            throw AnyNativeFileUploadUncertain(knownReceipt: .init(receipt: receipt), underlying: error)
        }
        return receipt
    }
    func inspect(_ specification: AnyNativeFileUploadSpecification, _ fileID: String,
        _ authorize: @escaping AnyNativeFileAttachmentCreator.Check) async throws -> AnyNativeAttachedFile {
        try await authorize(); reads += 1
        return try Self.file(specification, name: stableReadName ?? (changedSecondMetadata && reads.isMultiple(of: 2) ? "changed.txt" : nil))
    }
    func digest(_ file: AnyNativeAttachedFile,
        _ authorize: @escaping AnyNativeFileAttachmentCreator.Check) async throws -> AnyHTTPFileContentDigest {
        try await authorize()
        let sha = corruptDigest ? String(repeating: "0", count: 64) : AnyContentDigest.sha256(Data("data".utf8))
        return try JSONDecoder().decode(AnyHTTPFileContentDigest.self, from: JSONEncoder().encode(
            AnyJSON.object(["byteCount": .integer(4), "sha256": .string(sha)])))
    }
    static func file(_ specification: AnyNativeFileUploadSpecification, name: String? = nil) throws -> AnyNativeAttachedFile {
        try .init(native: .object([
            "fileId": .string("Bst4MGoLyBW"), "objectId": .string(specification.objectID),
            "size": .integer(specification.size), "inline": .bool(true),
            "durable": .bool(true), "cached": .bool(true),
            "name": .string(name ?? specification.name), "mime": .string(specification.mime)
        ]), specification: specification, expectedFileID: "Bst4MGoLyBW")
    }
}

@MainActor
final class AnyNativeFileAttachmentCreatorTests: XCTestCase {
    private let fileURL = URL(fileURLWithPath: "/not-opened-by-injected-component-fixture")
    private func intent(_ mutation: String = String(repeating: "a", count: 32),
                        name: String = "private-original.txt", object: String = "original-object") throws -> AnyNativeFileAttachmentIntent {
        try .init(workspace: .init(accountID: "original-account", spaceID: "original-space"),
            mutationID: mutation, objectID: object, name: name, mime: "text/plain",
            byteCount: 4, contentSHA256: AnyContentDigest.sha256(Data("data".utf8)))
    }
    private func creator(_ intent: AnyNativeFileAttachmentIntent, _ journal: AttachmentJournal,
                         _ native: AttachmentNative) throws -> AnyNativeFileAttachmentCreator {
        try .init(workspace: intent.workspace, journal: journal,
            upload: { try await native.upload($0, $1, $2, $3, $4) },
            inspect: { try await native.inspect($0, $1, $2) },
            digest: { try await native.digest($0, $1) })
    }
    private func error(_ expected: AnyNativeFileAttachmentError,
                       _ body: () async throws -> Void, file: StaticString = #filePath, line: UInt = #line) async {
        do { try await body(); XCTFail("expected \(expected)", file: file, line: line) }
        catch { XCTAssertEqual(error as? AnyNativeFileAttachmentError, expected, file: file, line: line) }
    }

    func testUnknownAcknowledgementSurvivesNewCreatorWithoutSecondDispatch() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        await native.configure(.lostAcknowledgement)
        let first = try creator(action, journal, native)
        await error(.writeUncertain) { _ = try await first.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        let reopened = try creator(action, journal, native)
        await error(.writeUncertain) { _ = try await reopened.resume(action, authorizeRead: {}) }
        await error(.writeUncertain) { _ = try await reopened.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1); XCTAssertEqual(counts.1, 0)
        let state = try await journal.lookup(action.identity); XCTAssertEqual(state, .reserved)
    }

    func testKnownReceiptPersistsBeforeLifetimeFailureAndResumesWithReads() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        await native.configure(.afterReceipt)
        let first = try creator(action, journal, native)
        await error(.knownFileUnverified("Bst4MGoLyBW")) { _ = try await first.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        let recorded = try await journal.lookup(action.identity); XCTAssertEqual(recorded, .created("Bst4MGoLyBW"))
        let reopened = try creator(action, journal, native)
        let result = try await reopened.resume(action, authorizeRead: {})
        XCTAssertEqual(result.reference.fileID, "Bst4MGoLyBW")
        let state = try await journal.lookup(action.identity); XCTAssertEqual(state, .verified("Bst4MGoLyBW"))
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1); XCTAssertEqual(counts.1, 2)
    }

    func testDigestMismatchRetainsOriginalIDWithoutVerificationOrResend() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        await native.configure(badDigest: true)
        let owner = try creator(action, journal, native)
        await error(.knownFileUnverified("Bst4MGoLyBW")) { _ = try await owner.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        let before = try await journal.lookup(action.identity); XCTAssertEqual(before, .created("Bst4MGoLyBW"))
        await native.configure()
        _ = try await owner.resume(action, authorizeRead: {})
        let after = try await journal.lookup(action.identity); XCTAssertEqual(after, .verified("Bst4MGoLyBW"))
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1)
    }

    func testConcurrentCallsConsumeOneApprovalAndOneNativePOST() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace)
        let release = AttachmentBarrier(); let native = AttachmentNative(release: release); let authority = AttachmentAuthority()
        let owner = try creator(action, journal, native)
        let first = Task { try await owner.attach(action, fileURL: fileURL,
            authorizeRead: { try await authority.validate() }, authorizeAttachment: { try await authority.approve() }) }
        await native.entered.wait()
        await error(.writeUncertain) {
            _ = try await owner.attach(action, fileURL: self.fileURL,
                authorizeRead: { try await authority.validate() }, authorizeAttachment: { try await authority.approve() })
        }
        await release.open(); _ = try await first.value
        let approvals = await authority.approvals(); XCTAssertEqual(approvals, 1)
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1)
    }

    func testRevocationWhileUploadIsInFlightPreservesOriginalReceiptWithoutDelivery() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace)
        let release = AttachmentBarrier(); let native = AttachmentNative(release: release); let authority = AttachmentAuthority()
        let owner = try creator(action, journal, native)
        let flight = Task { try await owner.attach(action, fileURL: fileURL,
            authorizeRead: { try await authority.validate() }, authorizeAttachment: { try await authority.approve() }) }
        await native.entered.wait(); await authority.setActive(false); await release.open()
        await error(.knownFileUnverified("Bst4MGoLyBW")) { _ = try await flight.value }
        let state = try await journal.lookup(action.identity); XCTAssertEqual(state, .created("Bst4MGoLyBW"))
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1); XCTAssertEqual(counts.1, 0)
        await authority.setActive(true)
        _ = try await owner.resume(action, authorizeRead: { try await authority.validate() })
        let finalCounts = await native.counts(); XCTAssertEqual(finalCounts.0, 1)
    }

    func testFailedReceiptJournalReportsKnownIDAndNeverCreatesReplacement() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        await journal.rejectCreatedReceipt(); let owner = try creator(action, journal, native)
        await error(.knownFileUnverified("Bst4MGoLyBW")) { _ = try await owner.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        await error(.writeUncertain) { _ = try await owner.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        let state = try await journal.lookup(action.identity); XCTAssertEqual(state, .reserved)
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1); XCTAssertEqual(counts.1, 0)
    }

    func testCancelledCallerRetainsLateKnownReceiptAndCannotReceiveSuccess() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace)
        let release = AttachmentBarrier(); let native = AttachmentNative(release: release)
        let owner = try creator(action, journal, native)
        let flight = Task { try await owner.attach(action, fileURL: fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        await native.entered.wait()
        flight.cancel()
        // A non-cooperative native response still delivers its original receipt
        // to the journal. Caller cancellation must suppress a successful result.
        await release.open()
        await error(.knownFileUnverified("Bst4MGoLyBW")) { _ = try await flight.value }
        let state = try await journal.lookup(action.identity); XCTAssertEqual(state, .created("Bst4MGoLyBW"))
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1); XCTAssertEqual(counts.1, 0)
        _ = try await owner.resume(action, authorizeRead: {})
        let finalCounts = await native.counts(); XCTAssertEqual(finalCounts.0, 1)
    }

    func testDeniedMutationApprovalSendsNothingAndRetainsConservativeReservation() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        let owner = try creator(action, journal, native)
        do {
            _ = try await owner.attach(action, fileURL: fileURL, authorizeRead: {},
                authorizeAttachment: { throw AnyEngineError.accountChanged })
            XCTFail("denied mutation must not dispatch")
        } catch { XCTAssertEqual(error as? AnyNativeFileAttachmentError, .writeUncertain) }
        let counts = await native.counts(); XCTAssertEqual(counts.0, 0); XCTAssertEqual(counts.1, 0)
        let state = try await journal.lookup(action.identity); XCTAssertEqual(state, .reserved)
        await error(.writeUncertain) { _ = try await owner.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        let finalCounts = await native.counts(); XCTAssertEqual(finalCounts.0, 0)
    }

    func testNativeRejectionIsTypedButDoesNotClearReservation() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        await native.configure(.nativeForbidden); let owner = try creator(action, journal, native)
        await error(.nativeResponse(status: 403, code: "acl.forbidden")) {
            _ = try await owner.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {})
        }
        await error(.writeUncertain) { _ = try await owner.resume(action, authorizeRead: {}) }
        let state = try await journal.lookup(action.identity); XCTAssertEqual(state, .reserved)
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1)
    }

    func testReadbackMetadataDriftDoesNotVerifyEvenWithMatchingContent() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        await native.configure(metadataDrift: true); let owner = try creator(action, journal, native)
        await error(.knownFileUnverified("Bst4MGoLyBW")) { _ = try await owner.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {}) }
        let state = try await journal.lookup(action.identity); XCTAssertEqual(state, .created("Bst4MGoLyBW"))
    }

    func testStableReadbackMetadataMustMatchTheOriginalWarmAcknowledgement() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        await native.configure(stableReadName: "stable-but-different.txt")
        let owner = try creator(action, journal, native)
        await error(.knownFileUnverified("Bst4MGoLyBW")) {
            _ = try await owner.attach(action, fileURL: self.fileURL, authorizeRead: {}, authorizeAttachment: {})
        }
        let state = try await journal.lookup(action.identity)
        XCTAssertEqual(state, .created("Bst4MGoLyBW"))
        let counts = await native.counts()
        XCTAssertEqual(counts.0, 1)
        XCTAssertEqual(counts.1, 1, "The first native read already contradicts the known acknowledgement")
    }

    func testIntentMismatchAndForeignScopeFailBeforeNativeDispatch() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        let owner = try creator(action, journal, native)
        _ = try await owner.attach(action, fileURL: fileURL, authorizeRead: {}, authorizeAttachment: {})
        let changed = try intent(name: "different.txt")
        do { _ = try await owner.attach(changed, fileURL: fileURL, authorizeRead: {}, authorizeAttachment: {}); XCTFail("changed intent must fail") }
        catch { XCTAssertEqual(error as? AnyNativeCreationError, .contentConflict) }
        let foreign = try AnyNativeFileAttachmentIntent(workspace: .init(accountID: "other-account", spaceID: "original-space"),
            mutationID: action.mutationID, objectID: action.objectID, name: action.name, mime: action.mime,
            byteCount: action.byteCount, contentSHA256: action.contentSHA256)
        do { _ = try await owner.attach(foreign, fileURL: fileURL, authorizeRead: {}, authorizeAttachment: {}); XCTFail("foreign scope must fail") }
        catch { XCTAssertEqual(error as? AnyHostError, .wrongWorkspace) }
        let counts = await native.counts(); XCTAssertEqual(counts.0, 1)
    }

    func testJournalIdentityContainsNoNamePayloadOrLocalURLAndRejectsForgedFingerprint() async throws {
        let action = try intent(); let journal = AttachmentJournal(action.workspace); let native = AttachmentNative()
        let owner = try creator(action, journal, native)
        _ = try await owner.attach(action, fileURL: fileURL, authorizeRead: {}, authorizeAttachment: {})
        // The public UI seam reuses the already seeded journal; neither
        // factory construction nor recorded-ID lookup needs an HTTP request.
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!,
                                      expectedAccountID: action.workspace.accountID)
        let objects = try AnyNativeObjectCreator(client: client, workspace: action.workspace, journal: journal)
        let first = try await objects.makeFileAttachmentCreator()
        let second = try await objects.makeFileAttachmentCreator()
        let firstID = try await first.recordedFileID(for: action)
        let secondID = try await second.recordedFileID(for: action)
        XCTAssertEqual(firstID, "Bst4MGoLyBW"); XCTAssertEqual(secondID, firstID)
        let injected = AnyNativeObjectCreator(workspace: action.workspace, journal: journal,
            dispatch: { _, _ in throw AnyEngineError.invalidOperation("unused component dispatch") },
            inspect: { _ in throw AnyEngineError.invalidOperation("unused component inspect") })
        do { _ = try await injected.makeFileAttachmentCreator(); XCTFail("A clientless injection manufactured an uploader") }
        catch { XCTAssertEqual(error as? AnyEngineError, .incompatibleSchema("native file attachment client unavailable")) }
        let bytes = try await journal.encodedIdentity(action.identity)
        let text = String(decoding: bytes, as: UTF8.self)
        XCTAssertFalse(text.contains(action.name)); XCTAssertFalse(text.contains(fileURL.path))
        XCTAssertFalse(text.contains("data")); XCTAssertTrue(text.contains("fileAttachment"))
        let original = try JSONEncoder().encode(action)
        var json = try JSONDecoder().decode(AnyJSON.self, from: original).object!
        json["fingerprint"] = .string(String(repeating: "0", count: 64))
        let forged = try JSONEncoder().encode(AnyJSON.object(json))
        XCTAssertThrowsError(try JSONDecoder().decode(AnyNativeFileAttachmentIntent.self, from: forged))
    }
}
