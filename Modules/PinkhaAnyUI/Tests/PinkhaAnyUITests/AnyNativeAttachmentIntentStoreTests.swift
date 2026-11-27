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
