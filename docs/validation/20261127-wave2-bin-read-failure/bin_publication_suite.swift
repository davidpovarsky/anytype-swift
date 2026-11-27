
/// Exercises the actual Bin publication state with controlled completed and
/// suspended reads. This does not certify Native ACLs or mounted Restore UI.
@MainActor
@Suite("Native Bin read publication", .timeLimit(.minutes(1)))
struct AnyLibraryBinPublicationTests {
    @Test
    func failedCurrentBinReadRetiresRowsAndAnExplicitRetryCanRecover() async throws {
        let fixture = try LibrarySearchFixture()
        let subject = fixture.subject
        var reads = 0
        await subject.refreshBin {
            reads += 1
            return [.init(id: "archived-document", title: "Archived document", isFolder: false)]
        }
        #expect(subject.binItems.map(\.id) == ["archived-document"])
        #expect(!subject.isLoadingBin)
        #expect(!subject.binReadFailed)

        await subject.refreshBin {
            reads += 1
            throw AnyHostError.changedDocument
        }
        #expect(subject.binItems.isEmpty)
        #expect(!subject.isLoadingBin)
        #expect(subject.binReadFailed)
        let failure = try #require(subject.message)
        #expect(!failure.isEmpty)
        #expect(subject.pendingRestores.isEmpty)

        await subject.refreshBin {
            reads += 1
            #expect(!subject.binReadFailed)
            return [.init(id: "current-folder", title: "Current folder", isFolder: true)]
        }
        #expect(subject.binItems == [.init(id: "current-folder", title: "Current folder", isFolder: true)])
        #expect(!subject.isLoadingBin)
        #expect(!subject.binReadFailed)
        await subject.refreshBin {
            reads += 1
            throw AnyHostError.changedDocument
        }
        #expect(subject.binReadFailed)
        #expect(reads == 4)
        await fixture.lifetime.drain()
        #expect(!subject.binReadFailed)
        #expect(subject.binItems.isEmpty)
    }

    @Test(arguments: [false, true])
    func olderBinCompletionCannotReplaceOrClearANewerRead(olderFails: Bool) async throws {
        let fixture = try LibrarySearchFixture()
        let subject = fixture.subject
        let suspended = SuspendedLibraryBinRead()
        let older = Task {
            await subject.refreshBin { try await suspended.read() }
        }
        defer { older.cancel(); suspended.cancelOutstanding() }
        try await suspended.waitUntilStarted()
        #expect(subject.isLoadingBin)

        let current = AnyLibraryBinItem(id: "current-document", title: "Current", isFolder: false)
        let expectedRows: [AnyLibraryBinItem]
        if olderFails {
            await subject.refreshBin { [current] }
            expectedRows = [current]
        } else {
            await subject.refreshBin { throw AnyHostError.changedDocument }
            expectedRows = []
        }
        let expectedFailure = !olderFails
        let expectedMessage = subject.message
        #expect(subject.binItems == expectedRows)
        #expect(subject.binReadFailed == expectedFailure)
        #expect(!subject.isLoadingBin)
        #expect((expectedMessage != nil) == expectedFailure)

        if olderFails {
            try suspended.complete(.failure(AnyHostError.changedDocument))
        } else {
            try suspended.complete(.success([
                .init(id: "stale-document", title: "Stale", isFolder: false)
            ]))
        }
        await older.value
        #expect(subject.binItems == expectedRows)
        #expect(subject.binReadFailed == expectedFailure)
        #expect(subject.message == expectedMessage)
        #expect(!subject.isLoadingBin)
        #expect(suspended.invocations == 1)
        await fixture.lifetime.drain()
    }
}

@MainActor
private final class SuspendedLibraryBinRead {
    private(set) var invocations = 0
    private var pending: CheckedContinuation<[AnyLibraryBinItem], any Error>?
    private var started: CheckedContinuation<Void, any Error>?

    func read() async throws -> [AnyLibraryBinItem] {
        try Task.checkCancellation()
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
        // A failure deadline only: the test advances at the actual read boundary.
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

    func complete(_ result: Result<[AnyLibraryBinItem], any Error>) throws {
        let continuation = try #require(pending)
        pending = nil
        continuation.resume(with: result)
    }

    func cancelOutstanding() {
        let call = pending, waiter = started
        pending = nil
        started = nil
        call?.resume(throwing: CancellationError())
        waiter?.resume(throwing: CancellationError())
    }
}
