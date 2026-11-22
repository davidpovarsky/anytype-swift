import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost
@testable import PinkhaAnyUI

/// Actual read-only controller/session with suspended typed transport results.
/// These controls do not certify a native service or a mounted Apple screen.
@MainActor
@Suite("Native history publication boundaries", .timeLimit(.minutes(1)))
struct AnyNativeHistoryPresentationTests {
    @Test
    func supersededVersionCannotReplaceTheCurrentSelection() async throws {
        let fixture = try HistoryPresentationFixture(pages: [historyPage(["a", "b"])])
        await fixture.subject.refresh()
        let old = Task { await fixture.subject.showVersion("a") }
        await fixture.reader.waitForVersion("a")
        let current = Task { await fixture.subject.showVersion("b") }
        await fixture.reader.waitForVersion("b")
        try await fixture.reader.complete("b")
        await current.value
        try await fixture.reader.complete("a")
        await old.value
        #expect(fixture.subject.selected?.version == "b")
        #expect(fixture.subject.selectedVersion == "b")
        #expect(!fixture.subject.isLoadingVersion)
        await fixture.subject.drain()
    }

    @Test
    func pageFailureRetiresAnInFlightVersionEvenWhenItIgnoresCancellation() async throws {
        let fixture = try HistoryPresentationFixture(pages: [historyPage(["a"], cursor: "next"), historyPage(["a"])])
        await fixture.subject.refresh()
        let pending = Task { await fixture.subject.showVersion("a") }
        await fixture.reader.waitForVersion("a")
        await fixture.subject.loadMore()
        #expect(fixture.subject.problem == .paginationChanged)
        #expect(fixture.subject.changes.isEmpty)
        try await fixture.reader.complete("a")
        await pending.value
        #expect(fixture.subject.selected == nil)
        #expect(fixture.subject.selectedVersion == nil)
        #expect(!fixture.subject.isLoadingVersion)
        await fixture.subject.drain()
    }

    @Test
    func refreshCannotBeRepopulatedByThePreviousPreview() async throws {
        let fixture = try HistoryPresentationFixture(pages: [historyPage(["old"]), historyPage(["new"])])
        await fixture.subject.refresh()
        let old = Task { await fixture.subject.showVersion("old") }
        await fixture.reader.waitForVersion("old")
        await fixture.subject.refresh()
        try await fixture.reader.complete("old")
        await old.value
        #expect(fixture.subject.changes.map(\.version) == ["new"])
        #expect(fixture.subject.selected == nil)
        #expect(fixture.subject.problem == nil)
        await fixture.subject.drain()
    }

    @Test
    func MountedOwnerRevocationClearsAllHistoricalData() async throws {
        let fixture = try HistoryPresentationFixture(pages: [historyPage(["private"])])
        await fixture.subject.refresh()
        let pending = Task { await fixture.subject.showVersion("private") }
        await fixture.reader.waitForVersion("private")
        fixture.owner.active = false
        try await fixture.reader.complete("private")
        await pending.value
        #expect(!fixture.subject.isActive)
        #expect(fixture.subject.changes.isEmpty)
        #expect(fixture.subject.selected == nil)
        #expect(fixture.subject.problem == .accessChanged)
        await fixture.subject.drain()
    }

    @Test
    func missingTruncatedAndLargeVersionsNeverBecomeEmptySuccess() async throws {
        let cases: [(AnyNativeHistoryError, AnyNativeHistoryProblem)] = [
            (.versionNotFound, .versionNotFound), (.truncated, .truncated), (.viewTooLarge, .viewTooLarge)
        ]
        for (error, expected) in cases {
            let fixture = try HistoryPresentationFixture(pages: [historyPage(["version"])])
            await fixture.subject.refresh()
            let pending = Task { await fixture.subject.showVersion("version") }
            await fixture.reader.waitForVersion("version")
            try await fixture.reader.complete("version", error: error)
            await pending.value
            #expect(fixture.subject.versionProblem == expected)
            #expect(fixture.subject.selected == nil)
            #expect(fixture.subject.changes.count == 1)
            await fixture.subject.drain()
        }
    }

    @Test
    func paginationStopsAtTwentyPagesAndKeepsNativeOrder() async throws {
        let pages = (0..<21).map { historyPage(["v\($0)"], cursor: "cursor\($0)") }
        let fixture = try HistoryPresentationFixture(pages: pages)
        await fixture.subject.refresh()
        for _ in 0..<25 { await fixture.subject.loadMore() }
        #expect(fixture.subject.changes.map(\.version) == (0..<20).map { "v\($0)" })
        #expect(!fixture.subject.hasMore)
        #expect(fixture.subject.problem == .paginationLimit)
        #expect(await fixture.reader.pageCount == 20)
        await fixture.subject.drain()
    }

    @Test
    func listedTruncationDoesNotDispatchACompleteVersionRead() async throws {
        let fixture = try HistoryPresentationFixture(pages: [historyPage(["cut"], truncated: true)])
        await fixture.subject.refresh()
        await fixture.subject.showVersion("cut")
        #expect(fixture.subject.versionProblem == .truncated)
        #expect(fixture.subject.selected == nil)
        #expect(await fixture.reader.versionCount == 0)
        await fixture.subject.drain()
    }
}

@MainActor
private final class HistoryPresentationOwner { var active = true }

@MainActor
private struct HistoryPresentationFixture {
    let owner: HistoryPresentationOwner
    let reader: HistoryPresentationReader
    let subject: AnyNativeHistoryPresentation
    init(pages: [AnyJSON]) throws {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let owner = HistoryPresentationOwner()
        let reader = HistoryPresentationReader(workspace: workspace, pages: pages)
        let session = AnyApplicationSession(workspace: workspace, engineStartedAt: "run", verifyRun: { "run" })
        self.owner = owner; self.reader = reader
        subject = try .init(reader: reader, session: session, checkOwner: {
            guard owner.active else { throw AnyHostError.sessionClosed }
        })
    }
}

private actor HistoryPresentationReader: AnyNativeHistoryReading {
    nonisolated let workspace: AnyTorahWorkspace
    nonisolated let objectID = "object"
    let pages: [AnyJSON]
    private(set) var pageCount = 0, versionCount = 0
    private var pending: [String: CheckedContinuation<AnyNativeHistoryVersion, Error>] = [:]
    private var waiting: [String: CheckedContinuation<Void, Never>] = [:]
    init(workspace: AnyTorahWorkspace, pages: [AnyJSON]) { self.workspace = workspace; self.pages = pages }
    func page(after: AnyNativeHistoryCursor?, lease: AnyHostLease,
              authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyNativeHistoryPage {
        try await authorize()
        let index = pageCount; pageCount += 1
        guard pages.indices.contains(index) else { throw AnyNativeHistoryError.malformedResponse }
        return try .init(response: pages[index], workspace: workspace, objectID: objectID, lease: lease, previous: after)
    }
    func version(_ id: String, lease: AnyHostLease,
                 authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyNativeHistoryVersion {
        versionCount += 1
        return try await withCheckedThrowingContinuation { continuation in
            pending[id] = continuation
            waiting.removeValue(forKey: id)?.resume()
        }
    }
    func waitForVersion(_ id: String) async {
        if pending[id] != nil { return }
        await withCheckedContinuation { waiting[id] = $0 }
    }
    func complete(_ id: String, error: AnyNativeHistoryError? = nil) throws {
        guard let continuation = pending.removeValue(forKey: id) else { throw AnyNativeHistoryError.malformedResponse }
        if let error { continuation.resume(throwing: error) }
        else {
            continuation.resume(returning: try .init(response: .object(["version": .string(id), "datasets": .array([])]),
                requestedVersion: id, workspace: workspace, objectID: objectID))
        }
    }
}

private func historyPage(_ ids: [String], cursor: String = "", truncated: Bool = false) -> AnyJSON {
    .object(["changes": .array(ids.map { .object([
        "version": .string($0), "author": .string("author"), "timestamp": .integer(1),
        "dataset": .string("editor_blocks"), "groupSize": .integer(1), "truncated": .bool(truncated)
    ]) }), "cursor": .string(cursor)])
}
