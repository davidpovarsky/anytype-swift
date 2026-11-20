#if canImport(SwiftUI)
import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost
@testable import PinkhaAnyUI

/// Exercises the real presentation model with suspended typed operation results.
/// These tests prove publication ordering, not native HTTP or mounted UI authority.
@MainActor
@Suite("Native property presentation ordering", .timeLimit(.minutes(1)))
struct AnyNativePropertyPresentationTests {
    @Test
    func delayedReviewCannotRestoreOldTypeOrEraseAcknowledgedUndo() async throws {
        let fixture = try PropertyPresentationFixture()
        defer { fixture.cancelOutstandingCalls() }
        let first = try fixture.snapshot(sequence: 17)
        let changed = try fixture.snapshot(type: "custom", sequence: 18)
        let undone = try fixture.snapshot(sequence: 19)
        let subject = try await fixture.loaded(first)

        let stale = Task { await subject.load(reviewCurrent: true) }
        try await fixture.reads.waitUntilStarted(1)
        let change = Task { await subject.setType("custom") }
        try await fixture.writes.waitUntilStarted(0)
        #expect(!subject.isLoading)
        let inverse = try fixture.store.prepareSetType(changed, typeID: "page")
        try fixture.writes.succeed(0, fixture.receipt(changed, undo: inverse))
        await change.value
        #expect(subject.snapshot?.currentTypeID == "custom")
        #expect(subject.canUndo)

        try fixture.reads.succeed(1, first)
        await stale.value
        #expect(subject.snapshot?.fence == changed.fence)
        #expect(subject.canUndo)
        #expect(!subject.needsReview)

        let undo = Task { await subject.undoLastChange() }
        try await fixture.writes.waitUntilStarted(1)
        let actualUndo = try #require(fixture.edits.last)
        #expect(actualUndo.patch == ["type": .string("page")])
        #expect(actualUndo.fence == changed.fence)
        try fixture.writes.succeed(1, fixture.receipt(undone))
        await undo.value
        #expect(subject.snapshot?.fence == undone.fence)
        #expect(subject.snapshot?.currentTypeID == "page")
        #expect(fixture.documentReloads == 2)
    }

    @Test
    func delayedReadFailureCannotReplaceAcknowledgedWriteFeedbackOrUndo() async throws {
        let fixture = try PropertyPresentationFixture()
        defer { fixture.cancelOutstandingCalls() }
        let first = try fixture.snapshot(sequence: 17)
        let changed = try fixture.snapshot(type: "custom", sequence: 18)
        let subject = try await fixture.loaded(first)
        let stale = Task { await subject.load(reviewCurrent: true) }
        try await fixture.reads.waitUntilStarted(1)
        let change = Task { await subject.setType("custom") }
        try await fixture.writes.waitUntilStarted(0)
        let inverse = try fixture.store.prepareSetType(changed, typeID: "page")
        try fixture.writes.succeed(0, fixture.receipt(changed, undo: inverse))
        await change.value
        subject.message = "Current acknowledged result"

        try fixture.reads.fail(1, AnyHostError.changedDocument)
        await stale.value
        #expect(subject.message == "Current acknowledged result")
        #expect(subject.snapshot?.fence == changed.fence)
        #expect(subject.canUndo)
        #expect(!subject.needsReview)
        #expect(!subject.isLoading)
    }

    @Test
    func delayedRefreshCannotRevealAnAcknowledgedHiddenProperty() async throws {
        let fixture = try PropertyPresentationFixture()
        defer { fixture.cancelOutstandingCalls() }
        let key = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "count")
        let visibility = AnyNativePropertyVisibilityKey(property: key)
        let first = try fixture.snapshot(sequence: 17)
        let hidden = try fixture.snapshot(sequence: 18, hidden: [key.visibilityKey])
        let subject = try await fixture.loaded(first)
        let stale = Task { await subject.load(reviewCurrent: true) }
        try await fixture.reads.waitUntilStarted(1)
        let change = Task { await subject.setVisibility(visibility, visible: false) }
        try await fixture.visibilityWrites.waitUntilStarted(0)
        #expect(!subject.isLoading)
        let inverse = try fixture.store.prepareVisibility(hidden, key: visibility, visible: true)
        try fixture.visibilityWrites.succeed(0, fixture.receipt(hidden, undo: inverse))
        await change.value

        try fixture.reads.succeed(1, first)
        await stale.value
        #expect(subject.snapshot?.fence == hidden.fence)
        #expect(subject.hiddenRows.contains { $0.id == key })
        #expect(!subject.visibleRows.contains { $0.id == key })
        #expect(subject.canUndo)
        #expect(fixture.visibilityEdits.first?.fence == first.fence)
    }

    @Test
    func refreshDuringWriteDoesNotDispatchOrReportMissingWorkspace() async throws {
        let fixture = try PropertyPresentationFixture()
        defer { fixture.cancelOutstandingCalls() }
        let first = try fixture.snapshot(sequence: 17)
        let changed = try fixture.snapshot(type: "custom", sequence: 18)
        let subject = try await fixture.loaded(first)
        subject.message = "Keep current feedback"
        let change = Task { await subject.setType("custom") }
        try await fixture.writes.waitUntilStarted(0)

        await subject.load()
        await subject.load(reviewCurrent: true)
        #expect(fixture.reads.invocationCount == 1)
        #expect(subject.isSaving)
        #expect(!subject.isLoading)
        #expect(subject.message == "Keep current feedback")
        try fixture.writes.succeed(0, fixture.receipt(changed))
        await change.value
        #expect(!subject.isSaving)
        #expect(subject.snapshot?.fence == changed.fence)
    }

    @Test
    func supersededReadFailureCannotClearNewerReadSpinnerOrFeedback() async throws {
        let fixture = try PropertyPresentationFixture()
        defer { fixture.cancelOutstandingCalls() }
        let first = try fixture.snapshot(sequence: 17)
        let current = try fixture.snapshot(type: "custom", sequence: 20)
        let subject = try await fixture.loaded(first)
        let old = Task { await subject.load() }
        try await fixture.reads.waitUntilStarted(1)
        let new = Task { await subject.load() }
        try await fixture.reads.waitUntilStarted(2)
        subject.message = "New request owns feedback"

        try fixture.reads.fail(1, AnyHostError.changedDocument)
        await old.value
        #expect(subject.isLoading)
        #expect(subject.message == "New request owns feedback")
        try fixture.reads.succeed(2, current)
        await new.value
        #expect(!subject.isLoading)
        #expect(subject.snapshot?.fence == current.fence)
    }

    @Test
    func oldReadCannotPublishOrClearLoadingAfterOwnerReactivation() async throws {
        for failOldRead in [false, true] {
            let fixture = try PropertyPresentationFixture()
            defer { fixture.cancelOutstandingCalls() }
            let first = try fixture.snapshot(sequence: 17)
            let staleValue = try fixture.snapshot(type: "custom-two", sequence: 18)
            let current = try fixture.snapshot(type: "custom", sequence: 19)
            let subject = try await fixture.loaded(first)
            let old = Task { await subject.load(reviewCurrent: true) }
            try await fixture.reads.waitUntilStarted(1)
            subject.deactivate()
            #expect(!subject.isLoading)
            fixture.mountedOwner = UUID()
            subject.activate()
            let new = Task { await subject.load() }
            try await fixture.reads.waitUntilStarted(2)
            subject.message = "New mounted owner"

            if failOldRead { try fixture.reads.fail(1, AnyHostError.changedDocument) }
            else { try fixture.reads.succeed(1, staleValue) }
            await old.value
            #expect(subject.isLoading)
            #expect(subject.snapshot?.fence == first.fence)
            #expect(subject.message == "New mounted owner")
            try fixture.reads.succeed(2, current)
            await new.value
            #expect(!subject.isLoading)
            #expect(subject.snapshot?.fence == current.fence)
        }
    }

    @Test
    func oldWriteCompletionCannotClearNewOwnerSavingStateOrPublishFailure() async throws {
        for failOldWrite in [false, true] {
            let fixture = try PropertyPresentationFixture()
            defer { fixture.cancelOutstandingCalls() }
            let first = try fixture.snapshot(sequence: 17)
            let committedBeforeReview = try fixture.snapshot(type: "custom", sequence: 18)
            let newest = try fixture.snapshot(sequence: 19)
            let subject = try await fixture.loaded(first)
            let old = Task { await subject.setType("custom") }
            try await fixture.writes.waitUntilStarted(0)
            subject.deactivate()
            #expect(!subject.isSaving)
            #expect(subject.needsReview)
            fixture.mountedOwner = UUID()
            subject.activate()
            #expect(!subject.canWrite)

            // The native write committed, but its old presentation has not yet
            // received a receipt. Explicit review acquires the real new state.
            let review = Task { await subject.load(reviewCurrent: true) }
            try await fixture.reads.waitUntilStarted(1)
            try fixture.reads.succeed(1, committedBeforeReview)
            await review.value
            #expect(subject.canWrite)
            let new = Task { await subject.setType("page") }
            try await fixture.writes.waitUntilStarted(1)
            subject.message = "New owner is saving"

            if failOldWrite { try fixture.writes.fail(0, AnyHostError.changedDocument) }
            else { try fixture.writes.succeed(0, fixture.receipt(committedBeforeReview)) }
            await old.value
            #expect(subject.isSaving)
            #expect(!subject.needsReview)
            #expect(subject.message == "New owner is saving")
            #expect(subject.snapshot?.fence == committedBeforeReview.fence)
            let inverse = try fixture.store.prepareSetType(newest, typeID: "custom")
            try fixture.writes.succeed(1, fixture.receipt(newest, undo: inverse))
            await new.value
            #expect(!subject.isSaving)
            #expect(subject.snapshot?.fence == newest.fence)
            #expect(subject.canUndo)
        }
    }
}

private struct PropertyPresentationRendezvousDeadline: Error {}

@MainActor
private final class SuspendedPropertyCalls<Value: Sendable> {
    private(set) var invocationCount = 0
    private var pending: [Int: CheckedContinuation<Value, any Error>] = [:]
    private var startedWaiters: [Int: CheckedContinuation<Void, any Error>] = [:]

    func invoke() async throws -> Value {
        let id = invocationCount
        invocationCount += 1
        return try await withTaskCancellationHandler {
            try Task.checkCancellation()
            return try await withCheckedThrowingContinuation { continuation in
                pending[id] = continuation
                startedWaiters.removeValue(forKey: id)?.resume(returning: ())
            }
        } onCancel: {
            Task { @MainActor [weak self] in self?.cancelPending(id) }
        }
    }

    func waitUntilStarted(_ id: Int) async throws {
        try Task.checkCancellation()
        guard invocationCount <= id else { return }
        // A missing dispatch fails the test instead of leaking a continuation.
        // The timer is only a failure deadline; normal scheduling uses the
        // exact invocation rendezvous and never sleeps to guess completion.
        let deadline = Task { @MainActor [weak self] in
            do { try await Task.sleep(for: .seconds(10)) }
            catch { return }
            self?.failWaiter(id, PropertyPresentationRendezvousDeadline())
        }
        defer { deadline.cancel() }
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            try await withCheckedThrowingContinuation { continuation in
                startedWaiters[id] = continuation
            }
        } onCancel: {
            Task { @MainActor [weak self] in self?.failWaiter(id, CancellationError()) }
        }
    }

    func succeed(_ id: Int, _ value: Value) throws {
        let continuation = try #require(pending.removeValue(forKey: id))
        continuation.resume(returning: value)
    }

    func fail(_ id: Int, _ error: any Error) throws {
        let continuation = try #require(pending.removeValue(forKey: id))
        continuation.resume(throwing: error)
    }

    func cancelAll() {
        let calls = Array(pending.values), waiters = Array(startedWaiters.values)
        pending.removeAll(); startedWaiters.removeAll()
        for call in calls { call.resume(throwing: CancellationError()) }
        for waiter in waiters { waiter.resume(throwing: CancellationError()) }
    }

    private func cancelPending(_ id: Int) {
        pending.removeValue(forKey: id)?.resume(throwing: CancellationError())
    }

    private func failWaiter(_ id: Int, _ error: any Error) {
        startedWaiters.removeValue(forKey: id)?.resume(throwing: error)
    }
}

@MainActor
private final class PropertyPresentationFixture {
    let store: AnyNativePropertyStore
    let workspace: AnyTorahWorkspace
    let generation = UUID()
    let reads = SuspendedPropertyCalls<AnyNativePropertySnapshot>()
    let writes = SuspendedPropertyCalls<AnyPropertyEditReceipt>()
    let visibilityWrites = SuspendedPropertyCalls<AnyPropertyEditReceipt>()
    var mountedOwner = UUID()
    var documentReloads = 0
    var edits: [AnyPreparedPropertyEdit] = []
    var visibilityEdits: [AnyPreparedPropertyEdit] = []

    init() throws {
        workspace = try .init(accountID: "account", spaceID: "space")
        store = try .init(
            client: .init(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account"),
            workspace: workspace, policy: .init())
    }

    func loaded(_ initial: AnyNativePropertySnapshot) async throws -> AnyNativePropertyPresentation {
        let operations = AnyNativePropertyPresentationOperations(
            canMutate: { [weak self] in self != nil },
            mountedOwnerID: { [weak self] in
                guard let self else { throw AnyHostError.sessionClosed }
                return self.mountedOwner
            },
            requireMounted: { [weak self] expected in
                guard let self, self.mountedOwner == expected else { throw AnyHostError.sessionClosed }
            },
            read: { [weak self] in
                guard let self else { throw AnyHostError.sessionClosed }
                return try await self.reads.invoke()
            },
            apply: { [weak self] edit, authorize in
                guard let self else { throw AnyHostError.sessionClosed }
                try await authorize()
                self.edits.append(edit)
                return try await self.writes.invoke()
            },
            setVisibility: { [weak self] snapshot, key, visible, authorize in
                guard let self else { throw AnyHostError.sessionClosed }
                try await authorize()
                self.visibilityEdits.append(try self.store.prepareVisibility(snapshot, key: key, visible: visible))
                return try await self.visibilityWrites.invoke()
            },
            reloadDocument: { [weak self] in
                guard let self else { throw AnyHostError.sessionClosed }
                self.documentReloads += 1
            })
        let subject = AnyNativePropertyPresentation(store: store, operations: operations)
        subject.activate()
        let initialRead = Task { await subject.load() }
        try await reads.waitUntilStarted(0)
        try reads.succeed(0, initial)
        await initialRead.value
        #expect(subject.canWrite)
        return subject
    }

    func cancelOutstandingCalls() {
        reads.cancelAll(); writes.cancelAll(); visibilityWrites.cancelAll()
    }

    func receipt(_ snapshot: AnyNativePropertySnapshot,
                 undo: AnyPreparedPropertyEdit? = nil) -> AnyPropertyEditReceipt {
        .init(objectID: snapshot.objectID, readback: .verifiedCurrent, snapshot: snapshot, undo: undo)
    }

    func snapshot(type: String = "page", sequence: Int64, hidden: [String] = []) throws -> AnyNativePropertySnapshot {
        func owner(_ id: String, document: Bool = false) throws -> AnyNativePropertyOwner {
            try .init(raw: .object(["id": .string(id), "name": .string(id)]), documentEligible: document)
        }
        let collection = AnyNativePropertyStore.presentationCollectionID
        let hiddenProperty = AnyNativePropertyStore.hiddenPropertiesID
        let catalog = try AnyNativePropertyCatalog(workspace: workspace, generation: generation,
            engineStartedAt: "original-run",
            types: [owner("page", document: true), owner("custom", document: true), owner("custom-two", document: true)],
            collections: [owner("collection-a"), owner(collection)])
        let definitions = try [
            AnyNativePropertyDefinition(ownerID: "any",
                raw: .object(["id": .string("type"), "kind": .string("string"), "scope": .string("synced")])),
            AnyNativePropertyDefinition(ownerID: "collection-a",
                raw: .object(["id": .string("count"), "kind": .string("number"), "scope": .string("synced")])),
            AnyNativePropertyDefinition(ownerID: collection,
                raw: .object(["id": .string(hiddenProperty), "kind": .string("array"), "scope": .string("synced")]))]
        let raw: AnyJSON = .object([
            "id": .string("document"), "spaceId": .string(workspace.spaceID),
            "_applySeq": .integer(sequence),
            "_ver": .object(["id": .string("row-\(sequence)"),
                             "any": .object(["type": .string("type-\(sequence)")])]),
            "any": .object(["type": .string(type),
                            "collections": .array([.string("collection-a"), .string(collection)])]),
            "collection-a": .object(["count": .integer(42)]),
            collection: .object([hiddenProperty: .array(hidden.map(AnyJSON.string))])])
        return try AnyNativePropertyStore.materialize(raw: raw, objectID: "document", catalog: catalog,
            definitions: definitions, policy: store.policy, canWrite: true)
    }
}
#endif
