#if canImport(SwiftUI)
import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost
@testable import PinkhaAnyUI

/// Drives the actual library publication method with typed suspended reads.
/// No HTTP, native search, or mounted Apple screen is certified by these tests.
@MainActor
@Suite("Native library search publication", .timeLimit(.minutes(1)))
struct AnyLibrarySearchPublicationTests {
    @Test
    func failedReplacementSearchCannotDisplayThePreviousQueryResults() async throws {
        let fixture = try LibrarySearchFixture()
        let subject = fixture.subject
        subject.searchQuery = "first query"
        let first = try #require(subject.searchChanged { query in
            #expect(query == "first query")
            return [.init(id: "first-document", title: "First result", isNote: false, snippet: "first")]
        })
        await first.value
        #expect(subject.searchResults.map(\.id) == ["first-document"])
        #expect(!subject.isSearching)

        subject.searchQuery = "  replacement query  "
        let replacement = try #require(subject.searchChanged { query in
            #expect(query == "replacement query")
            throw AnyHostError.changedDocument
        })
        #expect(subject.isSearching)
        #expect(subject.searchResults.isEmpty)
        await replacement.value
        #expect(subject.searchResults.isEmpty)
        #expect(!subject.isSearching)
        #expect(subject.message != nil)
        await fixture.lifetime.drain()
    }

    @Test
    func cancelledOlderReadCannotRepopulateAFailedReplacement() async throws {
        let fixture = try LibrarySearchFixture()
        let subject = fixture.subject
        let suspended = SuspendedLibrarySearch()
        defer { suspended.cancelOutstanding() }
        subject.searchQuery = "older query"
        let older = try #require(subject.searchChanged { query in
            #expect(query == "older query")
            return try await suspended.read()
        })
        try await suspended.waitUntilStarted()

        subject.searchQuery = "current query"
        let current = try #require(subject.searchChanged { query in
            #expect(query == "current query")
            throw AnyHostError.changedDocument
        })
        #expect(older.isCancelled)
        await current.value
        let failureMessage = try #require(subject.message)
        #expect(subject.searchResults.isEmpty)
        #expect(!subject.isSearching)

        // The old provider deliberately completes successfully after cancellation.
        try suspended.succeed([.init(id: "stale-document", title: "Stale result", isNote: false, snippet: nil)])
        await older.value
        #expect(subject.searchResults.isEmpty)
        #expect(subject.message == failureMessage)
        #expect(!subject.isSearching)
        #expect(suspended.invocations == 1)
        await fixture.lifetime.drain()
    }
}

private struct LibrarySearchDeadline: Error {}

@MainActor
private final class SuspendedLibrarySearch {
    private(set) var invocations = 0
    private var pending: CheckedContinuation<[AnyLibraryDocument], any Error>?
    private var started: CheckedContinuation<Void, any Error>?

    func read() async throws -> [AnyLibraryDocument] {
        invocations += 1
        return try await withCheckedThrowingContinuation { continuation in
            pending = continuation
            let waiter = started
            started = nil
            waiter?.resume(returning: ())
        }
    }

    func waitUntilStarted() async throws {
        if invocations > 0 { return }
        // Only a failure deadline; the test advances at the actual read boundary.
        let deadline = Task { @MainActor [weak self] in
            do { try await Task.sleep(for: .seconds(10)) } catch { return }
            guard let self else { return }
            let waiter = self.started
            self.started = nil
            waiter?.resume(throwing: LibrarySearchDeadline())
        }
        defer { deadline.cancel() }
        try await withCheckedThrowingContinuation { started = $0 }
    }

    func succeed(_ rows: [AnyLibraryDocument]) throws {
        let continuation = try #require(pending)
        pending = nil
        continuation.resume(returning: rows)
    }

    func cancelOutstanding() {
        let call = pending, waiter = started
        pending = nil
        started = nil
        call?.resume(throwing: CancellationError())
        waiter?.resume(throwing: CancellationError())
    }
}

/// Construction uses the production model/session types. The injected read is
/// the only dispatched operation; this journal rejects any accidental mutation.
@MainActor
private struct LibrarySearchFixture {
    let lifetime = AnyUIPresentationLifetime()
    let subject: AnyLibraryPresentation

    init() throws {
        let workspace = try AnyTorahWorkspace(accountID: "search-account", spaceID: "search-space")
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!,
                                       expectedAccountID: workspace.accountID)
        let session = AnyApplicationSession(workspace: workspace, engineStartedAt: "search-run", verifyRun: { "search-run" })
        let journal = LibrarySearchUnusedJournal(workspace: workspace)
        let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
        let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace,
                                               journal: journal, allowedTypeIDs: ["page"])
        subject = AnyLibraryPresentation(client: client, session: session, objects: objects, blocks: blocks,
            capabilities: try Self.capabilities(), lifetime: lifetime, recovery: .init(workspace: workspace))
    }

    private static func capabilities() throws -> AnyUIFoundationCapabilities {
        var value: [String: AnyJSON] = [
            "contract": .string("pinkha-torah-native-v1"),
            "bundleId": .string("pinkha/torah-native/v1"),
            "module": .string("pinkha_torah_native"),
            "dataset": .string("pinkha_torah_claims_v1"),
            "dataVersion": .string("pinkha-torah-native-claims-v1"),
            "nativeSemanticPayload": .string("canonical-associations-v2-single-record"),
            "associationBlockDataset": .string("editor_blocks"),
            "documentTypePolicy": .string("canonical-editor-module-v1"),
            "propertyPresentationCollection": .string("pinkha_presentation_v1"),
            "propertyPresentationHiddenProperty": .string("hiddenProperties"),
            "allowedTargetTypes": .array([.string("page")]),
            "nativeClaimsMaxRecords": .integer(10_000),
            "nativeClaimsMaxBytes": .integer(16_777_216),
            "mobileManagedTokenGateway": .integer(0)]
        for key in ["nativeSignedClaims", "spaceWideOperationConflictDomain", "currentACLCommitFence",
                    "targetTreeCommitFence", "nativeDocumentProperties", "nativeIndexedSourceQuery",
                    "nativeRelatedVersion", "conditionalBlockPatch", "conditionalPropertiesSet",
                    "conditionalPropertiesApplySeq", "conditionalPropertiesNoop", "conditionalBlockCurrentWriterFence",
                    "currentWriterObjectCreate", "currentWriterBlockCreate", "nativeClaimsSnapshot", "nativeClaimsWatch",
                    "nativeObjectClaimsSnapshot", "nativeObjectClaimsWatch", "nativeDocumentTypePolicy",
                    "nativeDocumentMembership", "conditionalMembershipSet", "nativePropertyPresentation"] {
            value[key] = .integer(1)
        }
        return try AnyUIFoundationCapabilities(response: .object(value))
    }
}

private actor LibrarySearchUnusedJournal: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    init(workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        Issue.record("Library search must not reserve a native mutation")
        throw AnyHostError.sessionClosed
    }
    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        Issue.record("Library search must not record a native mutation")
        throw AnyHostError.sessionClosed
    }
    func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        Issue.record("Library search must not inspect a mutation journal")
        throw AnyHostError.sessionClosed
    }
}
#endif
