import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

private actor ObservationStore: AnyTorahObservableOperationStore {
    nonisolated let workspace: AnyTorahWorkspace
    private let pair = AsyncThrowingStream<AnyTorahLiveSnapshot, Error>.makeStream()
    private var generation: UUID?
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func snapshot() throws -> AnyTorahProjection { try .init(claims: []) }
    func append(_ operation: AnyTorahOperation,
                authorize: @escaping @Sendable () async throws -> Void) async throws {
        throw AnyEngineError.unverifiedWrite
    }
    func watch(session: AnyStreamSession, limit: Int) async throws
        -> AsyncThrowingStream<AnyTorahLiveSnapshot, Error> {
        generation = await session.generation
        return pair.stream
    }
    func emit(_ projection: AnyTorahProjection, initial: Bool, generation other: UUID? = nil) {
        guard let generation = other ?? generation else { return }
        pair.continuation.yield(.init(generation: generation, projection: projection, initial: initial))
    }
}

private actor ObservationAccess: AnyTorahTargetAccess {
    nonisolated let workspace: AnyTorahWorkspace
    private var allowed = true
    private var validations = 0
    private var pausePublication = false
    private let paused = AsyncStream<Void>.makeStream(bufferingPolicy: .bufferingOldest(1))
    private let cancelled = AsyncStream<Void>.makeStream(bufferingPolicy: .bufferingOldest(1))

    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func revoke() { allowed = false }
    func pauseDuringPublication() { pausePublication = true }
    func waitUntilPaused() async { for await _ in paused.stream { return } }
    func waitUntilCancelled() async { for await _ in cancelled.stream { return } }
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) async throws {
        validations += 1
        guard allowed else { throw TorahAssociationRepositoryError.permissionDenied }
        if pausePublication && validations > 1 {
            paused.continuation.yield(())
            do { try await Task.sleep(for: .seconds(30)) }
            catch { cancelled.continuation.yield(()); throw error }
        }
    }
}

@Suite("Generation-fenced canonical association observation")
struct AssociationObservationTests: Sendable {
    private let target = TorahAssociationTarget.object(objectId: "document")
    private func fixture() throws -> (AnyTorahWorkspace, ObservationStore, ObservationAccess, AnyTorahAssociationRepository, AnyStreamSession) {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let store = ObservationStore(workspace)
        let access = ObservationAccess(workspace)
        let repository = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: access)
        return (workspace, store, access, repository, AnyStreamSession())
    }
    private func projection(spaceID: String = "space") throws -> AnyTorahProjection {
        let item = TorahAssociationItem(
            id: "quote-instance", kind: .ref, role: .sourceQuote, providerID: "sefaria",
            externalID: "Genesis.1.1", canonicalKey: "Genesis 1:1", labelHe: "בראשית",
            unknownFields: ["future": .bool(true)])
        let payload = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
            .init(location: .init(spaceId: spaceID, target: target), item: item)
        ]))
        let operation = try AnyTorahOperation(
            operationID: String(repeating: "a", count: 32), spaceID: spaceID,
            authorID: "account", kind: .add, targetObjectID: target.objectId,
            providerID: item.providerID, canonicalRef: item.canonicalKey, payload: payload)
        return try .init(claims: [.init(operation: operation, creator: "account")])
    }

    @Test func atomicInitialSnapshotUsesActualDomainRecordsAndOwnership() async throws {
        let (workspace, store, _, repository, session) = try fixture()
        let stream = try await repository.watch(target: target, spaceID: workspace.spaceID, session: session)
        await store.emit(try projection(), initial: true)
        var iterator = stream.makeAsyncIterator()
        let initial = try #require(try await iterator.next())
        #expect(initial.initial)
        #expect(initial.workspace == workspace)
        #expect(initial.target == target)
        let expectedGeneration = await session.generation
        #expect(initial.generation == expectedGeneration)
        #expect(initial.snapshot.records.first?.item.id == "quote-instance")
        #expect(initial.snapshot.records.first?.item.unknownFields["future"] == .bool(true))
        await session.invalidate()
    }

    @Test func deltaCannotStandInForAtomicInitialSnapshot() async throws {
        let (workspace, store, _, repository, session) = try fixture()
        let stream = try await repository.watch(target: target, spaceID: workspace.spaceID, session: session)
        await store.emit(try projection(), initial: false)
        var iterator = stream.makeAsyncIterator()
        await #expect(throws: AnyLiveQueryError.invalidSequence("missing atomic initial snapshot")) {
            _ = try await iterator.next()
        }
        await session.invalidate()
    }

    @Test func foreignGenerationIsRejectedBeforePublication() async throws {
        let (workspace, store, _, repository, session) = try fixture()
        let stream = try await repository.watch(target: target, spaceID: workspace.spaceID, session: session)
        await store.emit(try projection(), initial: true, generation: UUID())
        var iterator = stream.makeAsyncIterator()
        await #expect(throws: AnyLiveQueryError.staleGeneration) {
            _ = try await iterator.next()
        }
        await session.invalidate()
    }

    @Test func readabilityIsRecheckedForEverySnapshot() async throws {
        let (workspace, store, access, repository, session) = try fixture()
        let stream = try await repository.watch(target: target, spaceID: workspace.spaceID, session: session)
        await store.emit(try projection(), initial: true)
        var iterator = stream.makeAsyncIterator()
        _ = try #require(try await iterator.next())
        await access.revoke()
        await store.emit(try projection(), initial: false)
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            _ = try await iterator.next()
        }
        await session.invalidate()
    }

    @Test func invalidationDuringTargetReadCancelsItWithoutPublishing() async throws {
        let (workspace, store, access, repository, session) = try fixture()
        await access.pauseDuringPublication()
        let stream = try await repository.watch(target: target, spaceID: workspace.spaceID, session: session)
        let consumer = Task {
            var iterator = stream.makeAsyncIterator()
            return try await iterator.next()
        }
        await store.emit(try projection(), initial: true)
        await access.waitUntilPaused()
        await session.invalidate()
        await #expect(throws: AnyLiveQueryError.staleGeneration) {
            _ = try await consumer.value
        }
        await access.waitUntilCancelled()
    }

    @Test func anotherWorkspaceCannotAppearAsAnEmptySnapshot() async throws {
        let (workspace, store, _, repository, session) = try fixture()
        let stream = try await repository.watch(target: target, spaceID: workspace.spaceID, session: session)
        await store.emit(try projection(spaceID: "foreign-space"), initial: true)
        var iterator = stream.makeAsyncIterator()
        await #expect(throws: TorahAssociationRepositoryError.targetOutsideSpace) {
            _ = try await iterator.next()
        }
        await session.invalidate()
    }

    @Test func secondInitialRequiresNewSubscriptionInsteadOfSilentReset() async throws {
        let (workspace, store, _, repository, session) = try fixture()
        let stream = try await repository.watch(target: target, spaceID: workspace.spaceID, session: session)
        await store.emit(try projection(), initial: true)
        var iterator = stream.makeAsyncIterator()
        _ = try #require(try await iterator.next())
        await store.emit(try projection(), initial: true)
        await #expect(throws: AnyLiveQueryError.invalidSequence("repeated initial snapshot")) {
            _ = try await iterator.next()
        }
        await session.invalidate()
    }
}
