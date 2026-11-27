import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
@testable import PinkhaAnyUI

@Suite("Native attachment caller recovery", .timeLimit(.minutes(1)))
struct AnyNativeAttachmentIntentStoreTests {
    @Test
    func originalIntentSurvivesNewStoreWithoutASelectedURLOrNativeReceipt() async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let intent = try fixture.intent()
        let original = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let first = try await original.claim(objectID: intent.objectID)
        try await original.save(intent, claim: first)
        await original.release(first)

        let restarted = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let second = try await restarted.claim(objectID: intent.objectID)
        do {
            let loaded = try await restarted.pending(second)
            let actual = try #require(loaded)
            #expect(actual == intent)
            #expect(actual.mutationID == intent.mutationID)
            #expect(actual.fingerprint == intent.fingerprint)
            let raw = try Data(contentsOf: fixture.recordURL(objectID: intent.objectID))
            let value = try #require(JSONSerialization.jsonObject(with: raw) as? [String: Any])
            #expect(Set(value.keys) == ["format", "intent"])
            let storedIntent = try #require(value["intent"] as? [String: Any])
            #expect(Set(storedIntent.keys) == ["workspace", "mutationID", "objectID", "name", "mime", "byteCount", "contentSHA256", "fingerprint"])
            #expect(storedIntent["name"] as? String == intent.name)
            #expect(storedIntent["contentSHA256"] as? String == intent.contentSHA256)
            // Store removal is tested as caller-state CAS only. No native
            // receipt or UI reconciliation is invented by this component.
            try await restarted.remove(intent, claim: second)
            let removed = try await restarted.pending(second)
            #expect(removed == nil)
            await restarted.release(second)
        } catch { await restarted.release(second); throw error }
    }

    @Test
    func replacementStoreCannotAcquireOrOverwriteTheOriginalPendingIntent() async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let intent = try fixture.intent()
        let first = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let replacement = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let held = try await first.claim(objectID: intent.objectID)
        do {
            try await first.save(intent, claim: held)
            do {
                let forbidden = try await replacement.claim(objectID: intent.objectID)
                await replacement.release(forbidden)
                Issue.record("A replacement owner acquired a still-owned caller snapshot")
            } catch let error as AnyNativeAttachmentRecoveryError {
                #expect(error == .operationInProgress)
            }
            await first.release(held)
        } catch { await first.release(held); throw error }

        let current = try await replacement.claim(objectID: intent.objectID)
        do {
            let different = try fixture.intent(mutationID: String(repeating: "b", count: 32), name: "different.txt")
            do {
                try await replacement.save(different, claim: current)
                Issue.record("A different user selection replaced an unresolved original intent")
            } catch let error as AnyNativeAttachmentRecoveryError {
                #expect(error == .conflictingIntent)
            }
            let retained = try await replacement.pending(current)
            #expect(retained == intent)
            await first.release(held)
            do {
                let forbidden = try await first.claim(objectID: intent.objectID)
                await first.release(forbidden)
                Issue.record("A stale release unlocked the replacement owner's claim")
            } catch let error as AnyNativeAttachmentRecoveryError {
                #expect(error == .operationInProgress)
            }
            await replacement.release(current)
        } catch { await replacement.release(current); throw error }
    }

    @Test(arguments: [false, true])
    func malformedOrForeignSnapshotCannotBecomeARecoveryIntent(foreignWorkspace: Bool) async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let intent = try fixture.intent()
        let first = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let held = try await first.claim(objectID: intent.objectID)
        try await first.save(intent, claim: held)
        await first.release(held)
        let path = try fixture.recordURL(objectID: intent.objectID)
        let damaged: Data
        if foreignWorkspace {
            let workspace = try AnyTorahWorkspace(accountID: "other-account", spaceID: fixture.workspace.spaceID)
            let other = try AnyNativeFileAttachmentIntent(workspace: workspace, mutationID: intent.mutationID,
                objectID: intent.objectID, name: intent.name, mime: intent.mime,
                byteCount: intent.byteCount, contentSHA256: intent.contentSHA256)
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
            let encoded = try encoder.encode(other)
            let object = try JSONSerialization.jsonObject(with: encoded)
            damaged = try JSONSerialization.data(withJSONObject: ["format": 1, "intent": object],
                options: [.sortedKeys, .withoutEscapingSlashes])
        } else { damaged = Data("{incomplete".utf8) }
        // Preserve the real original inode, mode and Apple protection so the
        // intended schema/scope boundary, rather than a permission error, fires.
        let output = try FileHandle(forWritingTo: path)
        do {
            try output.truncate(atOffset: 0)
            try output.write(contentsOf: damaged)
            try output.synchronize()
            try output.close()
        } catch { try? output.close(); throw error }
        #expect(try Data(contentsOf: path) == damaged)
        let reopened = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let claim = try await reopened.claim(objectID: intent.objectID)
        do {
            do {
                _ = try await reopened.pending(claim)
                Issue.record("An invalid caller snapshot supplied a recovery intent")
            } catch let error as AnyNativeAttachmentRecoveryError {
                #expect(foreignWorkspace && error == .invalidRecord)
            } catch is DecodingError {
                #expect(!foreignWorkspace)
            }
            await reopened.release(claim)
        } catch { await reopened.release(claim); throw error }
    }
}

private struct AttachmentIntentStoreFixture {
    let parent: URL
    let workspace: AnyTorahWorkspace

    init() throws {
        workspace = try .init(accountID: "attachment-account", spaceID: "attachment-space")
        parent = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("pinkha-caller-intent-test-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
    }

    func intent(mutationID: String = String(repeating: "a", count: 32), name: String = "original.txt") throws -> AnyNativeFileAttachmentIntent {
        try .init(workspace: workspace, mutationID: mutationID, objectID: "document", name: name,
            mime: "text/plain", byteCount: 7, contentSHA256: AnyContentDigest.sha256(Data("example".utf8)))
    }

    func recordURL(objectID: String) throws -> URL {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let scope = AnyContentDigest.sha256(try encoder.encode(["any", workspace.accountID, workspace.spaceID]))
        return parent.appendingPathComponent("PinkhaAttachmentIntents/any/" + scope, isDirectory: true)
            .appendingPathComponent(AnyContentDigest.sha256(Data(objectID.utf8)) + ".json")
    }

    func removeOwnedDirectory() { try? FileManager.default.removeItem(at: parent) }
}
// This appended suite exercises the real 063d Host receipt API through its
// existing component initializer. It does not construct an opaque token or
// claim Native HTTP, Apple protected-journal, cancellation-close or UI coverage.
@testable import PinkhaAnyHost

@Suite("Live-authorized native attachment receipt carrier", .timeLimit(.minutes(2)))
struct AnyNativeAttachmentReceiptCarrierTests {
    @Test
    func originalOpaqueReceiptSurvivesClaimReopenWithoutEnteringDurableJSON() async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let intent = try fixture.intent()
        let store = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let journal = ReceiptCarrierJournal(fixture.workspace, poisonCreated: true)
        let native = ReceiptCarrierNative()
        let creator = try native.creator(journal)
        let first = try await store.claim(objectID: intent.objectID)
        do {
            do {
                try await store.retainRecoveryReceipt(for: intent, from: creator, authorizeRead: {}, claim: first)
                Issue.record("A claim without its durable pending intent requested a token")
            } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .conflictingIntent) }
            try await store.save(intent, claim: first)
            let originalJSON = try Data(contentsOf: fixture.recordURL(objectID: intent.objectID))
            try await native.leaveHostAcknowledgementFromComponentReply(intent, creator: creator)
            try await store.retainRecoveryReceipt(for: intent, from: creator, authorizeRead: {}, claim: first)
            #expect(try Data(contentsOf: fixture.recordURL(objectID: intent.objectID)) == originalJSON)
            await store.release(first)
            // Export was live-authorized BEFORE closing the original modeled
            // journal. No post-close creator export is exercised or assumed.
            await journal.close()
            let reopenedJournal = try await journal.reopenOriginalEntries()
            let current = try native.creator(reopenedJournal)

            let processRestart = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
            let coldClaim = try await processRestart.claim(objectID: intent.objectID)
            do {
                let missing = try await processRestart.recoveryReceipt(for: intent, claim: coldClaim)
                #expect(missing == nil)
                await processRestart.release(coldClaim)
            } catch { await processRestart.release(coldClaim); throw error }

            let second = try await store.claim(objectID: intent.objectID)
            do {
                let retained = try await store.recoveryReceipt(for: intent, claim: second)
                let token = try #require(retained)
                let file = try await current.resume(intent, recoveryReceipt: token, authorizeRead: {})
                #expect(file.reference.fileID == ReceiptCarrierNative.fileID)
                let state = try await reopenedJournal.lookup(intent.identity)
                #expect(state == .verified(ReceiptCarrierNative.fileID))
                try await store.consumeRecoveryReceipt(for: intent, claim: second)
                let consumed = try await store.recoveryReceipt(for: intent, claim: second)
                #expect(consumed == nil)
                // Durable caller removal is still separate and requires the
                // real UI's Host + FilesV2 reconciliation, not this component.
                let pending = try await store.pending(second)
                #expect(pending == intent)
                #expect(try Data(contentsOf: fixture.recordURL(objectID: intent.objectID)) == originalJSON)
                await store.release(second)
            } catch { await store.release(second); throw error }
            let counts = await native.counts()
            #expect(counts.uploads == 1 && counts.metadataReads == 2 && counts.contentReads == 1)
        } catch { await store.release(first); throw error }
    }

    @Test
    func currentClaimExactIntentAndFreshHostAuthorityRemainRequired() async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let intent = try fixture.intent(name: "caf\u{00E9}.txt")
        let store = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let journal = ReceiptCarrierJournal(fixture.workspace)
        let native = ReceiptCarrierNative()
        let creator = try native.creator(journal)
        let authority = ReceiptCarrierAuthority()
        let first = try await store.claim(objectID: intent.objectID)
        do {
            try await store.save(intent, claim: first)
            try await native.leaveHostAcknowledgementFromComponentReply(intent, creator: creator)
            try await store.retainRecoveryReceipt(for: intent, from: creator,
                authorizeRead: { try await authority.check() }, claim: first)
            await store.release(first)
        } catch { await store.release(first); throw error }
        let current = try await store.claim(objectID: intent.objectID)
        do {
            let checksBefore = await authority.count()
            do {
                try await store.retainRecoveryReceipt(for: intent, from: creator,
                    authorizeRead: { try await authority.check() }, claim: first)
                Issue.record("A released claim retained a token")
            } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .operationInProgress) }
            do {
                _ = try await store.recoveryReceipt(for: intent, claim: first)
                Issue.record("A released claim retrieved a token")
            } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .operationInProgress) }
            do {
                try await store.consumeRecoveryReceipt(for: intent, claim: first)
                Issue.record("A released claim consumed the current token")
            } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .operationInProgress) }
            let checksAfter = await authority.count()
            #expect(checksAfter == checksBefore)

            let different = try fixture.intent(name: "cafe\u{0301}.txt")
            #expect(different.name == intent.name)
            #expect(!different.name.utf8.elementsEqual(intent.name.utf8))
            for action in 0..<3 {
                do {
                    if action == 0 {
                        try await store.retainRecoveryReceipt(for: different, from: creator,
                            authorizeRead: { try await authority.check() }, claim: current)
                    } else if action == 1 {
                        _ = try await store.recoveryReceipt(for: different, claim: current)
                    } else {
                        try await store.consumeRecoveryReceipt(for: different, claim: current)
                    }
                    Issue.record("A byte-different pending intent accessed the original token")
                } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .conflictingIntent) }
            }
            for (account, space, object) in [
                ("foreign-account", fixture.workspace.spaceID, intent.objectID),
                (fixture.workspace.accountID, "foreign-space", intent.objectID),
                (fixture.workspace.accountID, fixture.workspace.spaceID, "foreign-object")
            ] {
                let foreign = try AnyNativeFileAttachmentIntent(workspace: .init(accountID: account, spaceID: space),
                    mutationID: intent.mutationID, objectID: object, name: intent.name, mime: intent.mime,
                    byteCount: intent.byteCount, contentSHA256: intent.contentSHA256)
                do {
                    _ = try await store.recoveryReceipt(for: foreign, claim: current)
                    Issue.record("Foreign scope retrieved the original token")
                } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .invalidRecord) }
            }
            let foreignWorkspace = try AnyTorahWorkspace(accountID: "foreign-account", spaceID: fixture.workspace.spaceID)
            let foreignCreator = try native.creator(ReceiptCarrierJournal(foreignWorkspace))
            do {
                try await store.retainRecoveryReceipt(for: intent, from: foreignCreator,
                    authorizeRead: { try await authority.check() }, claim: current)
                Issue.record("A different Host workspace supplied a token")
            } catch let error as AnyHostError { #expect(error == .wrongWorkspace) }

            await authority.deny()
            do {
                try await store.retainRecoveryReceipt(for: intent, from: creator,
                    authorizeRead: { try await authority.check() }, claim: current)
                Issue.record("Revoked read authority exported a Host token")
            } catch let error as AnyEngineError { #expect(error == .accountChanged) }
            let retained = try await store.recoveryReceipt(for: intent, claim: current)
            let token = try #require(retained)
            do {
                _ = try await creator.resume(intent, recoveryReceipt: token,
                    authorizeRead: { try await authority.check() })
                Issue.record("Possession of a token bypassed current Host authority")
            } catch let error as AnyEngineError { #expect(error == .accountChanged) }
            let counts = await native.counts()
            #expect(counts.uploads == 1 && counts.metadataReads == 0 && counts.contentReads == 0)
            await store.release(current)
        } catch { await store.release(current); throw error }
    }

    @Test
    func claimRetirementDuringHostAuthorizationCannotInsertALateToken() async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let intent = try fixture.intent()
        let store = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let native = ReceiptCarrierNative()
        let creator = try native.creator(ReceiptCarrierJournal(fixture.workspace))
        let first = try await store.claim(objectID: intent.objectID)
        var activeClaim = first
        let gate = ReceiptCarrierReadGate()
        var capture: Task<Void, any Error>?
        do {
            try await store.save(intent, claim: first)
            try await native.leaveHostAcknowledgementFromComponentReply(intent, creator: creator)
            let pending = Task {
                try await store.retainRecoveryReceipt(for: intent, from: creator,
                    authorizeRead: { try await gate.check() }, claim: first)
            }
            capture = pending
            try await gate.waitUntilStarted()
            await store.release(first)
            let replacement = try await store.claim(objectID: intent.objectID)
            activeClaim = replacement
            await gate.open()
            do {
                try await pending.value
                Issue.record("A retired claim published a token after its awaited authorization")
            } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .operationInProgress) }
            let missing = try await store.recoveryReceipt(for: intent, claim: replacement)
            #expect(missing == nil)
            try await store.retainRecoveryReceipt(for: intent, from: creator, authorizeRead: {}, claim: replacement)
            let current = try await store.recoveryReceipt(for: intent, claim: replacement)
            #expect(current != nil)
            await store.release(replacement)
        } catch {
            capture?.cancel()
            await gate.open()
            _ = try? await capture?.value
            await store.release(activeClaim)
            throw error
        }
    }

    @Test
    func fullPendingCapacityPreservesAllOpaqueReceiptsWithoutEviction() async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let store = AnyNativeAttachmentIntentStore(workspace: fixture.workspace, parent: fixture.parent)
        let native = ReceiptCarrierNative()
        let journal = ReceiptCarrierJournal(fixture.workspace)
        let creator = try native.creator(journal)
        var intents: [AnyNativeFileAttachmentIntent] = []
        for index in 0..<128 {
            let hex = String(index + 1, radix: 16)
            let intent = try AnyNativeFileAttachmentIntent(workspace: fixture.workspace,
                mutationID: String(repeating: "0", count: 32 - hex.count) + hex,
                objectID: "capacity-document-\(index)", name: "original.txt", mime: "text/plain",
                byteCount: 7, contentSHA256: AnyContentDigest.sha256(Data("example".utf8)))
            let claim = try await store.claim(objectID: intent.objectID)
            do {
                try await store.save(intent, claim: claim)
                try await native.leaveHostAcknowledgementFromComponentReply(intent, creator: creator)
                try await store.retainRecoveryReceipt(for: intent, from: creator, authorizeRead: {}, claim: claim)
                // Host verification can settle before the caller consumes its
                // token (for example, cancellation at delivery). This releases
                // only the Host's own 64-slot memory, never a caller token.
                _ = try await creator.resume(intent, authorizeRead: {})
                await store.release(claim)
                intents.append(intent)
            } catch { await store.release(claim); throw error }
        }
        let overflow = try AnyNativeFileAttachmentIntent(workspace: fixture.workspace,
            mutationID: String(repeating: "f", count: 32), objectID: "capacity-document-overflow",
            name: "overflow.txt", mime: "text/plain", byteCount: 7,
            contentSHA256: AnyContentDigest.sha256(Data("example".utf8)))
        let overflowClaim = try await store.claim(objectID: overflow.objectID)
        do {
            do {
                try await store.save(overflow, claim: overflowClaim)
                Issue.record("The existing pending-record limit admitted a 129th request")
            } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .capacityExceeded) }
            let absent = try await store.pending(overflowClaim)
            #expect(absent == nil)
            await store.release(overflowClaim)
        } catch { await store.release(overflowClaim); throw error }
        for intent in intents {
            let claim = try await store.claim(objectID: intent.objectID)
            do {
                let retained = try await store.recoveryReceipt(for: intent, claim: claim)
                #expect(retained != nil)
                await store.release(claim)
            } catch { await store.release(claim); throw error }
        }
        let first = try #require(intents.first)
        let claim = try await store.claim(objectID: first.objectID)
        do {
            let retained = try await store.recoveryReceipt(for: first, claim: claim)
            let token = try #require(retained)
            _ = try await creator.resume(first, recoveryReceipt: token, authorizeRead: {})
            // This invokes the existing caller-state CAS after real Host
            // verification; it does not stand in for the UI's FilesV2 check.
            try await store.remove(first, claim: claim)
            let next = try AnyNativeFileAttachmentIntent(workspace: fixture.workspace,
                mutationID: overflow.mutationID, objectID: first.objectID, name: overflow.name,
                mime: overflow.mime, byteCount: overflow.byteCount, contentSHA256: overflow.contentSHA256)
            try await store.save(next, claim: claim)
            let oldWasRemoved = try await store.recoveryReceipt(for: next, claim: claim)
            #expect(oldWasRemoved == nil)
            await store.release(claim)
        } catch { await store.release(claim); throw error }
        let counts = await native.counts()
        #expect(counts.uploads == 128 && counts.metadataReads == 258 && counts.contentReads == 129)
    }
}

private actor ReceiptCarrierJournal: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    private var entries: [String: (AnyNativeCreationIdentity, AnyNativeCreationState)] = [:]
    private let poisonCreated: Bool
    private var poisoned = false
    private var closed = false
    init(_ workspace: AnyTorahWorkspace, poisonCreated: Bool = false) {
        self.workspace = workspace; self.poisonCreated = poisonCreated
    }
    private init(_ workspace: AnyTorahWorkspace,
                 entries: [String: (AnyNativeCreationIdentity, AnyNativeCreationState)]) {
        self.workspace = workspace; self.entries = entries; poisonCreated = false
    }
    func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        try available()
        if let old = entries[identity.key] {
            guard old.0 == identity else { throw AnyNativeCreationError.contentConflict }
            return .init(state: old.1, ownsDispatch: false)
        }
        entries[identity.key] = (identity, .reserved)
        return .init(state: .reserved, ownsDispatch: true)
    }
    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        try available()
        guard let old = entries[identity.key], old.0 == identity else { throw AnyNativeCreationError.contentConflict }
        if case .created = state, poisonCreated { poisoned = true; throw AnyNativeCreationError.journalUnavailable }
        switch (old.1, state) {
        case (.reserved, .created): break
        case (.created(let left), .verified(let right)) where left == right: break
        case (.verified(let left), .verified(let right)) where left == right: break
        default: throw AnyNativeCreationError.contentConflict
        }
        entries[identity.key] = (identity, state)
    }
    func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        try available()
        guard let old = entries[identity.key] else { return nil }
        guard old.0 == identity else { throw AnyNativeCreationError.contentConflict }
        return old.1
    }
    func close() { closed = true }
    func reopenOriginalEntries() throws -> ReceiptCarrierJournal {
        guard closed else { throw AnyNativeCreationError.journalUnavailable }
        return .init(workspace, entries: entries)
    }
    private func available() throws {
        guard !poisoned, !closed else { throw AnyNativeCreationError.journalUnavailable }
    }
}

private actor ReceiptCarrierNative {
    static let fileID = "Bst4MGoLyBW"
    private var uploads = 0
    private var metadataReads = 0
    private var contentReads = 0
    nonisolated func creator(_ journal: ReceiptCarrierJournal) throws -> AnyNativeFileAttachmentCreator {
        try .init(workspace: journal.workspace, journal: journal,
            upload: { try await self.upload($0, $1, $2, $3, $4) },
            inspect: { try await self.inspect($0, $1, $2) },
            digest: { try await self.digest($0, $1) })
    }
    func leaveHostAcknowledgementFromComponentReply(_ intent: AnyNativeFileAttachmentIntent,
                                    creator: AnyNativeFileAttachmentCreator) async throws {
        do {
            _ = try await creator.attach(intent,
                fileURL: URL(fileURLWithPath: "/not-opened-by-this-Host-component"),
                authorizeRead: {}, authorizeAttachment: {})
            Issue.record("The controlled original acknowledgement unexpectedly completed verification")
        } catch let error as AnyNativeFileAttachmentError {
            #expect(error == .knownFileUnverified(Self.fileID))
        }
    }
    func counts() -> (uploads: Int, metadataReads: Int, contentReads: Int) {
        (uploads, metadataReads, contentReads)
    }
    private func upload(_ specification: AnyNativeFileUploadSpecification, _ unusedURL: URL,
        _ authorizeRead: @escaping AnyNativeFileAttachmentCreator.Check,
        _ authorizeWrite: @escaping AnyNativeFileAttachmentCreator.Check,
        _ receipt: @escaping @Sendable (AnyNativeAttachedFile) async throws -> Void) async throws -> AnyNativeAttachedFile {
        try await authorizeRead()
        try await authorizeWrite()
        uploads += 1
        let actual = try Self.file(specification)
        do { try await receipt(actual) }
        catch { throw AnyNativeFileUploadUncertain(knownReceipt: .init(receipt: actual), underlying: error) }
        // A controlled post-ACK failure leaves the real Host's private receipt
        // populated without calling its verify path. No HTTP/native claim.
        throw AnyNativeFileUploadUncertain(knownReceipt: .init(receipt: actual), underlying: ReceiptCarrierFixtureError.afterAcknowledgement)
    }
    private func inspect(_ specification: AnyNativeFileUploadSpecification, _ fileID: String,
                         _ authorizeRead: @escaping AnyNativeFileAttachmentCreator.Check) async throws -> AnyNativeAttachedFile {
        try await authorizeRead()
        guard fileID.utf8.elementsEqual(Self.fileID.utf8) else { throw AnyNativeFileAttachmentError.writeUncertain }
        metadataReads += 1
        return try Self.file(specification)
    }
    private func digest(_ file: AnyNativeAttachedFile,
                        _ authorizeRead: @escaping AnyNativeFileAttachmentCreator.Check) async throws -> AnyHTTPFileContentDigest {
        try await authorizeRead()
        contentReads += 1
        return try JSONDecoder().decode(AnyHTTPFileContentDigest.self, from: JSONEncoder().encode(
            AnyJSON.object(["byteCount": .integer(7), "sha256": .string(AnyContentDigest.sha256(Data("example".utf8)))])))
    }
    private static func file(_ specification: AnyNativeFileUploadSpecification) throws -> AnyNativeAttachedFile {
        try .init(native: .object(["fileId": .string(fileID), "objectId": .string(specification.objectID),
            "name": .string(specification.name), "mime": .string(specification.mime),
            "size": .integer(specification.size), "inline": .bool(true), "cached": .bool(true), "durable": .bool(true)]),
            specification: specification, expectedFileID: fileID)
    }
}

private actor ReceiptCarrierAuthority {
    private var active = true
    private var checks = 0
    func check() throws {
        checks += 1
        guard active else { throw AnyEngineError.accountChanged }
    }
    func count() -> Int { checks }
    func deny() { active = false }
}

private enum ReceiptCarrierFixtureError: Error { case afterAcknowledgement, waitExpired }

private actor ReceiptCarrierReadGate {
    private var started = false
    private var opened = false
    private var waiting: CheckedContinuation<Void, Never>?
    func check() async throws {
        started = true
        if !opened { await withCheckedContinuation { waiting = $0 } }
        try Task.checkCancellation()
    }
    func waitUntilStarted() async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(5))
        while !started {
            guard ContinuousClock.now < deadline else { throw ReceiptCarrierFixtureError.waitExpired }
            try await Task.sleep(for: .milliseconds(10))
        }
    }
    func open() {
        opened = true
        let continuation = waiting; waiting = nil
        continuation?.resume()
    }
}

// Consumer/lease coverage for the W1 post-close memory-export contract. These
// tests use the real session, Host and caller store, with the preceding modeled
// journal/native callbacks. They do not prove a mounted or protected-journal
// failure on Apple, real HTTP, Native engine, or process-death recovery.
@Suite("Original attachment creator caller ownership", .timeLimit(.minutes(2)))
struct AnyNativeAttachmentOriginalCreatorTests {
    @Test
    func registeredOriginalCreatorSurvivesDrainedOwnerAndClaimReopen() async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let workspace = fixture.workspace
        let intent = try fixture.intent()
        let store = AnyNativeAttachmentIntentStore(workspace: workspace, parent: fixture.parent)
        let oldSession = Self.session(workspace)
        let oldJournal = ReceiptCarrierJournal(workspace, poisonCreated: true)
        let native = ReceiptCarrierNative()
        let original = try native.creator(oldJournal)
        let first = try await store.claim(objectID: intent.objectID)
        var activeClaim = first
        var replacementSession: AnyApplicationSession?
        var replacementJournal: ReceiptCarrierJournal?
        do {
            try await store.save(intent, claim: first)
            let originalJSON = try Data(contentsOf: fixture.recordURL(objectID: intent.objectID))
            try await oldSession.perform { lease in
                try await store.retainOriginalCreator(for: intent, from: original, lease: lease, claim: first)
                try await Self.leaveAcknowledgement(intent, creator: original, lease: lease)
            }
            // No live token export occurred. The consumer retained the exact
            // creator BEFORE the genuine Host callback populated its memory.
            let notExported = try await store.recoveryReceipt(for: intent, claim: first)
            #expect(notExported == nil)
            await store.release(first)
            await oldSession.revokeAndDrain()
            await oldJournal.close()
            let journal = try await oldJournal.reopenOriginalEntries()
            replacementJournal = journal
            let current = try native.creator(journal)
            let session = Self.session(workspace)
            replacementSession = session
            #expect(session.generation != oldSession.generation)
            let second = try await store.claim(objectID: intent.objectID)
            activeClaim = second
            let verified = try await session.perform { lease in
                let retained = try await store.recoveryReceipt(for: intent, currentCreator: current,
                    lease: lease, authorizeRead: { try await lease.validate() }, claim: second)
                let token = try #require(retained)
                return try await current.resume(intent, recoveryReceipt: token,
                    authorizeRead: { try await lease.validate() })
            }
            #expect(verified.reference.fileID == ReceiptCarrierNative.fileID)
            #expect(verified.byteCount == intent.byteCount)
            let state = try await journal.lookup(intent.identity)
            #expect(state == .verified(ReceiptCarrierNative.fileID))
            let counts = await native.counts()
            #expect(counts.uploads == 1 && counts.metadataReads == 2 && counts.contentReads == 1)
            try await store.consumeRecoveryReceipt(for: intent, claim: second)
            let consumed = try await store.recoveryReceipt(for: intent, claim: second)
            let pending = try await store.pending(second)
            #expect(consumed == nil && pending == intent)
            #expect(try Data(contentsOf: fixture.recordURL(objectID: intent.objectID)) == originalJSON)
            // Only the actual UI's later FilesV2/final-authority reconciliation
            // may remove this pending file. This component leaves it intact.
            await store.release(second)
            await session.revokeAndDrain()
            await journal.close()
        } catch {
            await store.release(activeClaim)
            await replacementSession?.revokeAndDrain()
            await replacementJournal?.close()
            await oldSession.revokeAndDrain()
            await oldJournal.close()
            throw error
        }
    }

    @Test
    func originalPairCannotBeReplacedAndAuthorityErrorsAreNotMissingACK() async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let workspace = fixture.workspace
        let intent = try fixture.intent()
        let store = AnyNativeAttachmentIntentStore(workspace: workspace, parent: fixture.parent)
        let oldSession = Self.session(workspace)
        let oldJournal = ReceiptCarrierJournal(workspace)
        let native = ReceiptCarrierNative()
        let original = try native.creator(oldJournal)
        let wrongSameOwnerCreator = try native.creator(oldJournal)
        let first = try await store.claim(objectID: intent.objectID)
        var activeClaim = first
        var replacementSession: AnyApplicationSession?
        var replacementJournal: ReceiptCarrierJournal?
        do {
            try await store.save(intent, claim: first)
            try await oldSession.perform { lease in
                try await store.retainOriginalCreator(for: intent, from: original, lease: lease, claim: first)
                do {
                    _ = try await store.recoveryReceipt(for: intent, currentCreator: wrongSameOwnerCreator,
                        lease: lease, authorizeRead: {}, claim: first)
                    Issue.record("The same generation accepted a different creator")
                } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .conflictingIntent) }
                do {
                    try await store.retainOriginalCreator(for: intent, from: wrongSameOwnerCreator,
                        lease: lease, claim: first)
                    Issue.record("A second creator replaced the original before dispatch")
                } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .conflictingIntent) }
            }
            await store.release(first)
            await oldSession.revokeAndDrain()
            await oldJournal.close()
            let journal = try await oldJournal.reopenOriginalEntries()
            replacementJournal = journal
            let current = try native.creator(journal)
            let session = Self.session(workspace)
            replacementSession = session
            let second = try await store.claim(objectID: intent.objectID)
            activeClaim = second
            try await session.perform { lease in
                do {
                    _ = try await store.recoveryReceipt(for: intent, currentCreator: original,
                        lease: lease, authorizeRead: {}, claim: second)
                    Issue.record("A replacement generation presented the retired creator as current")
                } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .conflictingIntent) }
                do {
                    try await store.retainOriginalCreator(for: intent, from: current, lease: lease, claim: second)
                    Issue.record("A new current creator replaced the original unresolved actor")
                } catch let error as AnyNativeAttachmentRecoveryError { #expect(error == .conflictingIntent) }
                do {
                    _ = try await store.recoveryReceipt(for: intent, currentCreator: current,
                        lease: lease, authorizeRead: { throw AnyNativeFileAttachmentError.writeUncertain }, claim: second)
                    Issue.record("An authority failure with the missing-ACK error type fell through")
                } catch let error as AnyNativeFileAttachmentError { #expect(error == .writeUncertain) }
                // The original actor has no ACK because no attach was called.
                // Only that precise private-memory absence returns nil.
                let missing = try await store.recoveryReceipt(for: intent, currentCreator: current,
                    lease: lease, authorizeRead: { try await lease.validate() }, claim: second)
                #expect(missing == nil)
                do {
                    _ = try await current.resume(intent, authorizeRead: { try await lease.validate() })
                    Issue.record("A missing original reservation became a verified result")
                } catch let error as AnyNativeFileAttachmentError { #expect(error == .noRecordedAttachment) }
            }
            let counts = await native.counts()
            #expect(counts.uploads == 0 && counts.metadataReads == 0 && counts.contentReads == 0)
            let pending = try await store.pending(second)
            #expect(pending == intent)
            await store.release(second)
            await session.revokeAndDrain()
            await journal.close()
        } catch {
            await store.release(activeClaim)
            await replacementSession?.revokeAndDrain()
            await replacementJournal?.close()
            await oldSession.revokeAndDrain()
            await oldJournal.close()
            throw error
        }
    }

    @Test(arguments: [true, false])
    func retiredClaimOrCurrentLeaseCannotPublishLateOriginalExport(retireClaim: Bool) async throws {
        let fixture = try AttachmentIntentStoreFixture()
        defer { fixture.removeOwnedDirectory() }
        let workspace = fixture.workspace
        let intent = try fixture.intent()
        let store = AnyNativeAttachmentIntentStore(workspace: workspace, parent: fixture.parent)
        let oldSession = Self.session(workspace)
        let oldJournal = ReceiptCarrierJournal(workspace, poisonCreated: true)
        let native = ReceiptCarrierNative()
        let original = try native.creator(oldJournal)
        let first = try await store.claim(objectID: intent.objectID)
        var activeClaim = first
        var replacementSession: AnyApplicationSession?
        var replacementJournal: ReceiptCarrierJournal?
        var capture: Task<AnyNativeFileAttachmentRecoveryReceipt?, any Error>?
        var shutdown: Task<Void, Never>?
        let gate = ReceiptCarrierReadGate()
        do {
            try await store.save(intent, claim: first)
            try await oldSession.perform { lease in
                try await store.retainOriginalCreator(for: intent, from: original, lease: lease, claim: first)
                try await Self.leaveAcknowledgement(intent, creator: original, lease: lease)
            }
            await store.release(first)
            await oldSession.revokeAndDrain()
            await oldJournal.close()
            let journal = try await oldJournal.reopenOriginalEntries()
            replacementJournal = journal
            let current = try native.creator(journal)
            let session = Self.session(workspace)
            replacementSession = session
            let second = try await store.claim(objectID: intent.objectID)
            activeClaim = second
            let pending: Task<AnyNativeFileAttachmentRecoveryReceipt?, any Error> = Task {
                try await session.perform { lease in
                    try await store.recoveryReceipt(for: intent, currentCreator: current,
                        lease: lease, authorizeRead: { try await gate.check() }, claim: second)
                }
            }
            capture = pending
            try await gate.waitUntilStarted()
            if retireClaim {
                await store.release(second)
                activeClaim = try await store.claim(objectID: intent.objectID)
            } else {
                shutdown = Task { await session.revokeAndDrain() }
                let deadline = ContinuousClock.now.advanced(by: .seconds(5))
                while await session.isActive {
                    guard ContinuousClock.now < deadline else { throw ReceiptCarrierFixtureError.waitExpired }
                    try await Task.sleep(for: .milliseconds(10))
                }
            }
            await gate.open()
            do {
                _ = try await pending.value
                Issue.record("Retired current ownership published an original token")
            } catch let error as AnyNativeAttachmentRecoveryError {
                #expect(retireClaim && error == .operationInProgress)
            } catch is CancellationError {
                #expect(!retireClaim)
            } catch let error as AnyHostError {
                #expect(!retireClaim && error == .sessionClosed)
            }
            await shutdown?.value
            let cached = try await store.recoveryReceipt(for: intent, claim: activeClaim)
            let stillPending = try await store.pending(activeClaim)
            #expect(cached == nil && stillPending == intent)
            let counts = await native.counts()
            #expect(counts.uploads == 1 && counts.metadataReads == 0 && counts.contentReads == 0)
            await store.release(activeClaim)
            await session.revokeAndDrain()
            await journal.close()
        } catch {
            capture?.cancel()
            await gate.open()
            _ = try? await capture?.value
            await shutdown?.value
            await store.release(activeClaim)
            await replacementSession?.revokeAndDrain()
            await replacementJournal?.close()
            await oldSession.revokeAndDrain()
            await oldJournal.close()
            throw error
        }
    }

    private static func session(_ workspace: AnyTorahWorkspace) -> AnyApplicationSession {
        .init(workspace: workspace, engineStartedAt: "receipt-caller-component-run",
              verifyRun: { "receipt-caller-component-run" })
    }

    private static func leaveAcknowledgement(_ intent: AnyNativeFileAttachmentIntent,
                                            creator: AnyNativeFileAttachmentCreator,
                                            lease: AnyHostLease) async throws {
        do {
            _ = try await creator.attach(intent,
                fileURL: URL(fileURLWithPath: "/not-opened-by-this-Host-component"),
                authorizeRead: { try await lease.validate() },
                authorizeAttachment: { try await lease.validate() })
            Issue.record("The controlled ACK unexpectedly completed durable verification")
        } catch let error as AnyNativeFileAttachmentError {
            #expect(error == .knownFileUnverified(ReceiptCarrierNative.fileID))
        }
    }
}
