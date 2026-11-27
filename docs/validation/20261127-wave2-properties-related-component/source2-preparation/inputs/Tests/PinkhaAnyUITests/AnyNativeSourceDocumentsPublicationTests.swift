import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaAnyUI

/// Actual Properties result-state ownership with noncooperative typed reads.
/// This does not replace or certify the native index, metadata or ACL checks.
@MainActor
@Suite("Native Properties related-document publication", .timeLimit(.minutes(1)))
struct AnyNativeSourceDocumentsPublicationTests {
    @Test
    func queuedOldRequestCannotBorrowReopenedSheetAndCurrentFailureCanRetry() async throws {
        let owner = SourceDocumentsTestOwner()
        owner.open()
        var reservation = AnyNativePropertyChildReservation()
        let firstPresentation = try #require(owner.model.presentationID)
        _ = reservation.reserve(in: firstPresentation)
        var oldReads = 0
        let old = try #require(owner.load("old") {
            oldReads += 1
            return sourceDocumentsResult("old")
        })
        defer { old.cancel(); owner.close() }
        // No suspension before this close/reopen: the old Task is queued, but
        // the synchronous tap has already captured the old presentation ID.
        owner.close()
        owner.open()
        let currentPresentation = try #require(owner.model.presentationID)
        #expect(firstPresentation != currentPresentation)
        // Retain the old View's reservation deliberately, instead of assuming
        // SwiftUI destroyed its State. Reopening still permits a new child.
        #expect(!reservation.isReserved(in: currentPresentation))
        _ = reservation.reserve(in: currentPresentation)
        reservation.release(in: firstPresentation, current: currentPresentation)
        #expect(reservation.isReserved(in: currentPresentation))
        let failed = try #require(owner.load("current-failure") {
            throw SourceDocumentsTestFailure()
        })
        await failed.value
        await old.value
        #expect(oldReads == 0)
        #expect(owner.feedback == ["current-failure:failure"])
        #expect(owner.finished == ["current-failure"])
        #expect(!owner.model.isLoading)
        #expect(owner.model.documents.isEmpty)
        #expect(owner.model.title == nil)
        reservation.release(in: currentPresentation, current: currentPresentation)
        #expect(!reservation.isReserved(in: currentPresentation))

        let retry = try #require(owner.load("retry") { sourceDocumentsResult("current") })
        await retry.value
        #expect(owner.model.documents.map(\.objectID) == ["current"])
        #expect(owner.model.title == "Source current")
        #expect(owner.feedback == ["current-failure:failure", "retry:success"])
        #expect(owner.finished == ["current-failure", "retry"])
        owner.close()
    }

    @Test(arguments: [false, true], [false, true])
    func noncooperativeOldCompletionCannotReplaceReopenedRequest(
        olderFails: Bool, changesDocumentOwner: Bool
    ) async throws {
        let owner = SourceDocumentsTestOwner()
        let stale = SuspendedSourceDocumentsRead()
        let current = SuspendedSourceDocumentsRead()
        owner.open()
        let old = try #require(owner.load("old") { try await stale.read() })
        defer { old.cancel(); stale.cancelOutstanding(); current.cancelOutstanding(); owner.close() }
        try await stale.waitUntilStarted()
        owner.close()
        if changesDocumentOwner { owner.documentOwner = UUID() }
        owner.open()
        let new = try #require(owner.load("new") { try await current.read() })
        defer { new.cancel() }
        try await current.waitUntilStarted()
        #expect(old.isCancelled)
        #expect(owner.model.isLoading)

        if olderFails { try stale.complete(.failure(SourceDocumentsTestFailure())) }
        else { try stale.complete(.success(sourceDocumentsResult("stale"))) }
        await old.value
        // The old success, error and defer must not publish or finish the new
        // owner's still-pending request, even when the document UUID is equal.
        #expect(owner.model.isLoading)
        #expect(owner.model.documents.isEmpty)
        #expect(owner.model.title == nil)
        #expect(owner.feedback.isEmpty)
        #expect(owner.finished.isEmpty)

        try current.complete(.success(sourceDocumentsResult("current")))
        await new.value
        #expect(!owner.model.isLoading)
        #expect(owner.model.documents.map(\.objectID) == ["current"])
        #expect(owner.model.title == "Source current")
        #expect(owner.feedback == ["new:success"])
        #expect(owner.finished == ["new"])
        #expect(stale.invocations == 1 && current.invocations == 1)
    }

    @Test(arguments: [false, true])
    func retirementDiscardsRowsAndRejectsANoncooperativeCompletion(fails: Bool) async throws {
        let owner = SourceDocumentsTestOwner()
        owner.open()
        let published = try #require(owner.load("published") { sourceDocumentsResult("visible") })
        await published.value
        #expect(owner.model.documents.map(\.objectID) == ["visible"])
        // The real results sheet's Done binding clears only its title. The
        // Properties owner still owns the old rows until its own retirement.
        owner.model.title = nil
        let pending = SuspendedSourceDocumentsRead()
        let old = try #require(owner.load("retired") { try await pending.read() })
        defer { old.cancel(); pending.cancelOutstanding(); owner.close() }
        try await pending.waitUntilStarted()
        owner.close()
        #expect(owner.model.documents.isEmpty)
        #expect(owner.model.title == nil)
        #expect(!owner.model.isLoading)

        if fails { try pending.complete(.failure(SourceDocumentsTestFailure())) }
        else { try pending.complete(.success(sourceDocumentsResult("late"))) }
        await old.value
        #expect(owner.model.documents.isEmpty)
        #expect(owner.model.title == nil)
        #expect(!owner.model.isLoading)
        #expect(owner.feedback == ["published:success"])
        #expect(owner.finished == ["published"])
        var closedReads = 0
        if let forbidden = owner.load("closed", read: {
            closedReads += 1
            return sourceDocumentsResult("forbidden")
        }) {
            await forbidden.value
            Issue.record("A retired Properties owner admitted a read")
        }
        #expect(closedReads == 0)
    }

    @Test(arguments: [false, true])
    func asyncWaiterJoinsReadAndForwardsCallerCancellation(cancelCaller: Bool) async throws {
        let owner = SourceDocumentsTestOwner()
        let pending = SuspendedSourceDocumentsRead()
        owner.open()
        let request = try #require(owner.load("request") { try await pending.read() })
        var waiterEntered = false
        var waiterReturned = false
        let waiter = Task { @MainActor in
            waiterEntered = true
            await AnyNativeSourceDocumentsPresentation.waitForCompletion(of: request)
            waiterReturned = true
        }
        defer { waiter.cancel(); request.cancel(); pending.cancelOutstanding(); owner.close() }
        try await pending.waitUntilStarted()
        try await SourceDocumentsTestOwner.waitUntil { waiterEntered }
        #expect(!waiterReturned)
        if cancelCaller {
            waiter.cancel()
            try await SourceDocumentsTestOwner.waitUntil { request.isCancelled }
        }
        // Even the cancelled caller joins the noncooperative read; completion
        // is not reported merely because the child Task has been created.
        #expect(!waiterReturned)
        try pending.complete(.success(sourceDocumentsResult("finished")))
        await waiter.value
        #expect(waiterReturned)
        #expect(!owner.model.isLoading)
        #expect(owner.model.documents.map(\.objectID) == (cancelCaller ? [] : ["finished"]))
        #expect(owner.feedback == (cancelCaller ? [] : ["request:success"]))
        #expect(owner.finished == ["request"])
    }

    @Test(arguments: [false, true])
    func temporarilyInactiveOwnerFinishesItsRequestAndCanRetry(fails: Bool) async throws {
        let owner = SourceDocumentsTestOwner()
        let pending = SuspendedSourceDocumentsRead()
        owner.open()
        let presentation = try #require(owner.model.presentationID)
        let documentOwner = owner.documentOwner
        var reservation = AnyNativePropertyChildReservation()
        _ = reservation.reserve(in: presentation)
        let optionalRequest: Task<Void, Never>? = owner.model.load(documentOwner: documentOwner,
            read: { try await pending.read() },
            isOwnerCurrent: { owner.active && owner.documentOwner == documentOwner },
            canPresent: { true },
            didComplete: { result in
                switch result {
                case .success: owner.feedback.append("inactive:success")
                case .failure: owner.feedback.append("inactive:failure")
                }
            }, didFinish: {
                owner.finished.append("inactive")
                reservation.release(in: presentation, current: owner.model.presentationID)
            })
        let request = try #require(optionalRequest)
        defer { request.cancel(); pending.cancelOutstanding(); owner.close() }
        try await pending.waitUntilStarted()
        // An inactive scene can fail the mounted foreground guard without
        // closing Properties or replacing its document/presentation owner.
        owner.active = false
        if fails { try pending.complete(.failure(SourceDocumentsTestFailure())) }
        else { try pending.complete(.success(sourceDocumentsResult("inactive"))) }
        await request.value
        #expect(owner.model.presentationID == presentation)
        #expect(owner.model.documents.isEmpty)
        #expect(owner.model.title == nil)
        #expect(owner.feedback.isEmpty)
        #expect(!owner.model.isLoading)
        #expect(owner.finished == ["inactive"])
        #expect(!reservation.isReserved(in: presentation))

        owner.active = true
        let retry = try #require(owner.load("retry") { sourceDocumentsResult("current") })
        await retry.value
        #expect(owner.model.presentationID == presentation)
        #expect(owner.model.documents.map(\.objectID) == ["current"])
        #expect(owner.model.title == "Source current")
        #expect(owner.feedback == ["retry:success"])
        #expect(owner.finished == ["inactive", "retry"])
        #expect(!owner.model.isLoading)
    }
}

private func sourceDocumentsResult(_ id: String) -> AnyNativeSourceDocumentsRead {
    .init(documents: [.init(id: id, spaceID: "source-space", objectID: id,
                           title: id, sourceReference: "Genesis 1:1")],
          title: "Source " + id, complete: true)
}

@MainActor
private final class SourceDocumentsTestOwner {
    let model = AnyNativeSourceDocumentsPresentation()
    var documentOwner = UUID()
    var active = false
    var feedback: [String] = []
    var finished: [String] = []

    func open() {
        active = true
        model.beginPresentation(documentOwner: documentOwner)
    }

    func close() {
        active = false
        model.retire()
    }

    static func waitUntil(_ condition: @MainActor () -> Bool) async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(10))
        while !condition() {
            try Task.checkCancellation()
            guard ContinuousClock.now < deadline else { throw SourceDocumentsTestFailure() }
            try await Task.sleep(for: .milliseconds(5))
        }
    }

    func load(_ label: String,
              read: @escaping @MainActor () async throws -> AnyNativeSourceDocumentsRead) -> Task<Void, Never>? {
        let expected = documentOwner
        return model.load(documentOwner: expected, read: read,
            isOwnerCurrent: { [self] in active && documentOwner == expected },
            canPresent: { true },
            didComplete: { [self] result in
                switch result {
                case .success: feedback.append(label + ":success")
                case .failure: feedback.append(label + ":failure")
                }
            }, didFinish: { [self] in finished.append(label) })
    }
}

private struct SourceDocumentsTestFailure: Error {}

@MainActor
private final class SuspendedSourceDocumentsRead {
    private(set) var invocations = 0
    private var pending: CheckedContinuation<AnyNativeSourceDocumentsRead, Error>?
    private var started: CheckedContinuation<Void, Error>?

    func read() async throws -> AnyNativeSourceDocumentsRead {
        try Task.checkCancellation()
        invocations += 1
        // Deliberately no cancellation handler: a late provider must still be
        // unable to publish after the owner has cancelled this consumer.
        return try await withCheckedThrowingContinuation { continuation in
            pending = continuation
            let waiter = started; started = nil
            waiter?.resume(returning: ())
        }
    }

    func waitUntilStarted() async throws {
        if invocations > 0 { return }
        let deadline = Task { @MainActor [weak self] in
            do { try await Task.sleep(for: .seconds(10)) } catch { return }
            guard let self else { return }
            let waiter = started; started = nil
            waiter?.resume(throwing: SourceDocumentsTestFailure())
        }
        defer { deadline.cancel() }
        try await withCheckedThrowingContinuation { started = $0 }
    }

    func complete(_ result: Result<AnyNativeSourceDocumentsRead, Error>) throws {
        let continuation = try #require(pending)
        pending = nil
        continuation.resume(with: result)
    }

    func cancelOutstanding() {
        let call = pending, waiter = started
        pending = nil; started = nil
        call?.resume(throwing: CancellationError())
        waiter?.resume(throwing: CancellationError())
    }
}
