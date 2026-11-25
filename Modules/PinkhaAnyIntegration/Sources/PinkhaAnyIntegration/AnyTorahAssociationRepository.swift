import Foundation
import PinkhaKit
import PinkhaAnyEngine

public struct AnyTorahAssociationConflict: Sendable {
    public let claimIDs: [String]
    public let reason: String
}

public struct AnyTorahAssociationSnapshot: Sendable {
    public let records: [TorahStoredAssociationRecord]
    public let conflicts: [AnyTorahAssociationConflict]
}

/// Bridges the actual PinkhaKit domain contract to immutable Any records.
/// No Heart fallback, shadow canonical file or best-effort snapshot replacement.
public actor AnyTorahAssociationRepository: TorahAssociationRepository {
    public nonisolated let workspace: AnyTorahWorkspace
    private let store: any AnyTorahOperationStore
    private let access: any AnyTorahTargetAccess
    private let codec = TorahAssociationPayloadCodec()
    private var mutationTail: Task<Void, Never>?

    public init(workspace: AnyTorahWorkspace, store: any AnyTorahOperationStore,
                access: any AnyTorahTargetAccess) throws {
        guard store.workspace == workspace, access.workspace == workspace else {
            throw AnyEngineError.invalidIdentity("mixed engine workspace")
        }
        self.workspace = workspace
        self.store = store
        self.access = access
    }

    public func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        try await list(target: .object(objectId: objectId), spaceID: spaceId)
    }

    public func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        try await list(target: .block(objectId: objectId, blockId: blockId), spaceID: spaceId)
    }

    public func snapshot(target: TorahAssociationTarget, spaceID: String) async throws -> AnyTorahAssociationSnapshot {
        try checkSpace(spaceID)
        if let mutationTail { await mutationTail.value }
        try await access.validate(target, intent: .read)
        let state = try await decoded(target: target)
        return .init(records: state.live.map(\.record), conflicts: state.conflicts)
    }


    /// Observes complete native projections. A terminal error requires a fresh
    /// stream; this API does not invent event replay or compare version cursors.
    /// The UI must requireActive(generation:) again before committing a queued
    /// snapshot to presentation, since invalidation can follow publication.
    public func watch(target: TorahAssociationTarget, spaceID: String,
                      session: AnyStreamSession, limit: Int = 10_000) async throws
        -> AsyncThrowingStream<AnyTorahAssociationLiveSnapshot, Error> {
        try checkSpace(spaceID)
        guard (1...10_000).contains(limit),
              let observable = store as? any AnyTorahObservableOperationStore else {
            throw AnyLiveQueryError.invalidSequence("native observation unavailable")
        }
        let generation = await session.generation
        try await session.requireActive(generation: generation)
        try await access.validate(target, intent: .read)
        try await session.requireActive(generation: generation)
        let upstream = try await observable.watch(session: session, limit: limit)
        let pair = AsyncThrowingStream<AnyTorahAssociationLiveSnapshot, Error>.makeStream(
            bufferingPolicy: .bufferingOldest(2))
        let registration = try await session.register(generation: generation) {
            pair.continuation.finish(throwing: AnyLiveQueryError.staleGeneration)
        }
        let worker = Task { [self] in
            do {
                var receivedInitial = false
                for try await update in upstream {
                    try Task.checkCancellation()
                    try await session.requireActive(generation: update.generation)
                    guard update.generation == generation else { throw AnyLiveQueryError.staleGeneration }
                    guard receivedInitial ? !update.initial : update.initial else {
                        throw AnyLiveQueryError.invalidSequence(
                            receivedInitial ? "repeated initial snapshot" : "missing atomic initial snapshot")
                    }
                    try await access.validate(target, intent: .read)
                    try await session.requireActive(generation: generation)
                    let state = try decoded(projection: update.projection, target: target)
                    let output = AnyTorahAssociationLiveSnapshot(
                        workspace: workspace, target: target, generation: generation, initial: update.initial,
                        snapshot: .init(records: state.live.map(\.record), conflicts: state.conflicts))
                    try Task.checkCancellation()
                    try await session.requireActive(generation: generation)
                    switch pair.continuation.yield(output) {
                    case .enqueued: break
                    case .dropped: throw AnyLiveQueryError.bufferOverflow
                    case .terminated: throw CancellationError()
                    @unknown default: throw AnyLiveQueryError.bufferOverflow
                    }
                    receivedInitial = true
                }
                throw AnyLiveQueryError.disconnected
            } catch {
                pair.continuation.finish(throwing: error)
            }
            await session.unregister(registration)
        }
        pair.continuation.onTermination = { @Sendable _ in worker.cancel() }
        return pair.stream
    }

    /// Decode one target from an already atomic complete canonical projection.
    /// This avoids repeated whole-space reads during related-document paging;
    /// target readability is still checked at the time of use.
    public func snapshot(projection: AnyTorahProjection, target: TorahAssociationTarget,
                         spaceID: String) async throws -> AnyTorahAssociationSnapshot {
        try checkSpace(spaceID)
        try await access.validate(target, intent: .read)
        let state = try decoded(projection: projection, target: target)
        return .init(records: state.live.map(\.record), conflicts: state.conflicts)
    }

    public func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                               spaceId: String) async throws -> TorahAssociationItem {
        try await upsertAssociation(item, target: target, spaceId: spaceId)
    }

    public func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                                  spaceId: String) async throws -> TorahAssociationItem {
        try await apply(item, target: target, spaceId: spaceId, requireExisting: false)
    }

    public func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                                  spaceId: String) async throws -> TorahAssociationItem {
        try await apply(item, target: target, spaceId: spaceId, requireExisting: true)
    }

    /// Item-level convenience mutation. For durable retry across intervening
    /// edits, persist prepareMutation's full value and use commitPrepared.
    public func apply(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                      spaceId: String, requireExisting: Bool = false,
                      operationID: String = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                      authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> TorahAssociationItem {
        try checkSpace(spaceId)
        return try await serial { [self] in
            try await mutate(item, target: target, requireExisting: requireExisting,
                             operationID: operationID, authorize: authorize)
        }
    }

    public func removeAssociation(associationId: String, target: TorahAssociationTarget,
                                  spaceId: String) async throws {
        try await removeAssociation(associationId: associationId, target: target, spaceId: spaceId, authorize: {})
    }

    public func removeAssociation(associationId: String, target: TorahAssociationTarget,
                                  spaceId: String,
                                  authorize: @escaping @Sendable () async throws -> Void) async throws {
        try checkSpace(spaceId)
        try await serial { [self] in
            try Task.checkCancellation()
            try await authorize()
            try await access.validate(target, intent: .write)
            let state = try await decoded(target: target)
            guard let mutation = try TorahImmutableAssociationPolicy.removing(
                associationID: associationId, from: state.policy) else { return }
            let operation = try nativeOperation(mutation,
                operationID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased())
            try await store.append(operation) { [access] in
                try Task.checkCancellation()
                try await authorize()
                try await access.validate(target, intent: .write)
            }
        }
    }

    private func list(target: TorahAssociationTarget, spaceID: String) async throws -> [TorahAssociationItem] {
        let snapshot = try await snapshot(target: target, spaceID: spaceID)
        guard snapshot.conflicts.isEmpty else {
            throw TorahAssociationRepositoryError.writeConflict("Concurrent association variants require explicit resolution")
        }
        return TorahAssociationCollectionPolicy.sorted(snapshot.records.map(\.item))
    }

    private struct State: Sendable {
        let policy: TorahImmutableAssociationState
        var live: [TorahImmutableAssociationEntry] { policy.entries }
        var conflicts: [AnyTorahAssociationConflict] {
            policy.conflicts.map { .init(claimIDs: $0.claimIDs, reason: $0.reason) }
        }
    }


    /// Native object closure avoids the global workspace limit for an editor.
    /// Block eligibility is supplied by the native read transaction; one current
    /// document/member validation fences delivery without N block-tree scans.
    public func objectSnapshot(objectID: String, spaceID: String, limit: Int = 10_000) async throws
        -> AnyTorahObjectAssociationSnapshot {
        try checkSpace(spaceID)
        guard let scoped = store as? any AnyTorahObjectOperationReading else {
            throw AnyEngineError.unsupportedEngine("native object association scope")
        }
        if let mutationTail { await mutationTail.value }
        let native = try await scoped.objectSnapshot(objectID: objectID, limit: limit)
        return try await objectSnapshot(native: native, spaceID: spaceID)
    }

    public func objectSnapshot(native: AnyGuardedTorahObjectSnapshot, spaceID: String) async throws
        -> AnyTorahObjectAssociationSnapshot {
        try checkSpace(spaceID)
        guard native.spaceID == workspace.spaceID else {
            throw TorahAssociationRepositoryError.targetOutsideSpace
        }
        let output = try decodeObject(native)
        try await access.validate(.object(objectId: native.targetObjectID), intent: .read)
        return output
    }

    public func watchObject(objectID: String, spaceID: String, session: AnyStreamSession,
                            limit: Int = 10_000) async throws
        -> AsyncThrowingStream<AnyTorahObjectAssociationLiveSnapshot, Error> {
        try checkSpace(spaceID)
        guard (1...10_000).contains(limit),
              let scoped = store as? any AnyTorahObjectOperationObserving else {
            throw AnyEngineError.unsupportedEngine("native object association observation")
        }
        let generation = await session.generation
        try await session.requireActive(generation: generation)
        try await access.validate(.object(objectId: objectID), intent: .read)
        let upstream = try await scoped.watchObject(objectID: objectID, session: session, limit: limit)
        let pair = AsyncThrowingStream<AnyTorahObjectAssociationLiveSnapshot, Error>.makeStream(
            bufferingPolicy: .bufferingOldest(2))
        let registration = try await session.register(generation: generation) {
            pair.continuation.finish(throwing: AnyLiveQueryError.staleGeneration)
        }
        let worker = Task { [self] in
            do {
                var initial = false
                for try await update in upstream {
                    try Task.checkCancellation()
                    try await session.requireActive(generation: update.generation)
                    guard update.generation == generation else { throw AnyLiveQueryError.staleGeneration }
                    guard initial ? !update.initial : update.initial,
                          update.snapshot.targetObjectID == objectID else {
                        throw AnyLiveQueryError.invalidSequence("native object initial/scope")
                    }
                    let snapshot = try await objectSnapshot(native: update.snapshot, spaceID: spaceID)
                    try await session.requireActive(generation: generation)
                    let value = AnyTorahObjectAssociationLiveSnapshot(generation: generation,
                                                                      initial: update.initial, snapshot: snapshot)
                    switch pair.continuation.yield(value) {
                    case .enqueued: break
                    case .dropped: throw AnyLiveQueryError.bufferOverflow
                    case .terminated: throw CancellationError()
                    @unknown default: throw AnyLiveQueryError.bufferOverflow
                    }
                    initial = true
                }
                throw AnyLiveQueryError.disconnected
            } catch { pair.continuation.finish(throwing: error) }
            await session.unregister(registration)
        }
        pair.continuation.onTermination = { @Sendable _ in worker.cancel() }
        return pair.stream
    }

    private func decodeObject(_ native: AnyGuardedTorahObjectSnapshot) throws -> AnyTorahObjectAssociationSnapshot {
        guard native.spaceID == workspace.spaceID,
              native.projection.all.allSatisfy({ $0.operation.spaceID == workspace.spaceID }) else {
            throw TorahAssociationRepositoryError.targetOutsideSpace
        }
        var records: [TorahStoredAssociationRecord] = []
        var conflicts: [AnyTorahAssociationConflict] = []
        let targets: [TorahAssociationTarget] = [.object(objectId: native.targetObjectID)] +
            native.reachableClaimBlockIDs.sorted().map {
                .block(objectId: native.targetObjectID, blockId: $0)
            }
        for target in targets {
            let state = try decoded(projection: native.projection, target: target)
            records.append(contentsOf: state.live.map(\.record))
            conflicts.append(contentsOf: state.conflicts)
        }
        return .init(workspace: workspace, objectID: native.targetObjectID, records: records,
                     conflicts: conflicts, reachableClaimBlockIDs: native.reachableClaimBlockIDs,
                     nativeGeneration: native.readinessGeneration)
    }

    private func decoded(target: TorahAssociationTarget) async throws -> State {
        if let scoped = store as? any AnyTorahObjectOperationReading {
            let native = try await scoped.objectSnapshot(objectID: target.objectId, limit: 10_000)
            guard native.spaceID == workspace.spaceID, native.targetObjectID == target.objectId else {
                throw TorahAssociationRepositoryError.targetOutsideSpace
            }
            if let blockID = target.blockId,
               native.projection.all.contains(where: {
                   $0.operation.targetObjectID == target.objectId && $0.operation.targetBlockID == blockID
               }), !native.reachableClaimBlockIDs.contains(blockID) {
                throw TorahAssociationRepositoryError.targetNotFound
            }
            return try decoded(projection: native.projection, target: target)
        }
        return try decoded(projection: await store.snapshot(), target: target)
    }

    private func decoded(projection: AnyTorahProjection, target: TorahAssociationTarget) throws -> State {
        guard projection.all.allSatisfy({ $0.operation.spaceID == workspace.spaceID }) else {
            throw TorahAssociationRepositoryError.targetOutsideSpace
        }
        let relevant: (AnyTorahClaim) -> Bool = {
            $0.operation.targetObjectID == target.objectId &&
            $0.operation.targetBlockID == (target.blockId ?? "")
        }
        var conflicts = projection.conflicts.values.filter { $0.contains(where: relevant) }.map {
            AnyTorahAssociationConflict(claimIDs: $0.map(\.id).sorted(),
                                        reason: "same operation ID carries different payloads")
        }
        let unresolved = Set(projection.pendingObserved)
        for claim in projection.all.filter(relevant)
            where projection.conflicts[claim.operation.logicalKey] == nil &&
                  !unresolved.isDisjoint(with: claim.operation.observed) {
            conflicts.append(.init(claimIDs: ([claim.id] + claim.operation.observed.filter { unresolved.contains($0) }).sorted(),
                                   reason: "observed predecessor is not yet resolved"))
        }
        let location = TorahAssociationLocation(spaceId: workspace.spaceID, target: target)
        let live = try projection.live.filter(relevant).map { claim -> TorahImmutableAssociationClaim in
            let op = claim.operation
            guard op.spaceID == workspace.spaceID else {
                throw TorahAssociationRepositoryError.targetOutsideSpace
            }
            let content = try AnyTorahSourceJSONGuard.preservingMigrationErrors {
                try TorahImmutableAssociationContent(payload: op.payload, location: location,
                    providerID: op.providerID, canonicalRef: op.canonicalRef)
            }
            return try .init(claimID: claim.id, content: content)
        }
        // Native collision/tombstone projection remains authoritative. The
        // default shared policy preserves every concurrent Any variant.
        return try .init(policy: TorahImmutableAssociationPolicy.project(
            live, at: location, nativeConflicts: conflicts.map {
                .init(claimIDs: $0.claimIDs, reason: $0.reason)
            }))
    }

    /// Returns nil when the canonical item is already unchanged. This read/plan
    /// never dispatches the proposed operation.
    public func prepareMutation(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                                spaceId: String, requireExisting: Bool = false,
                                operationID: String = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                                authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyTorahPreparedMutation? {
        try checkSpace(spaceId)
        return try await serial { [self] in
            let plan = try await plannedMutation(item, target: target, requireExisting: requireExisting,
                                                 operationID: operationID, authorize: authorize)
            guard let operation = plan.operation else { return nil }
            return try AnyTorahPreparedMutation(workspace: workspace, operation: operation)
        }
    }

    /// Replays exactly the frozen operation even if another edit arrived. Its
    /// original observed predecessors are never silently rebased on new state.
    @discardableResult
    public func commitPrepared(_ prepared: AnyTorahPreparedMutation,
                               authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> TorahAssociationItem? {
        guard prepared.workspace == workspace else { throw AnyEngineError.accountChanged }
        return try await serial { [self] in
            let operation = prepared.operation
            let target: TorahAssociationTarget = operation.targetBlockID.isEmpty
                ? .object(objectId: operation.targetObjectID)
                : .block(objectId: operation.targetObjectID, blockId: operation.targetBlockID)
            try await access.validate(target, intent: .write)
            try await store.append(operation) { [access] in
                try Task.checkCancellation()
                try await authorize()
                try await access.validate(target, intent: .write)
            }
            guard operation.kind != .remove else { return nil }
            return try codec.decodeCanonicalDocument(operation.payload,
                legacyLocation: .init(spaceId: workspace.spaceID, target: target)).records.first?.item
        }
    }

    private func mutate(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                        requireExisting: Bool, operationID: String,
                        authorize: @escaping @Sendable () async throws -> Void) async throws -> TorahAssociationItem {
        let plan = try await plannedMutation(item, target: target, requireExisting: requireExisting,
                                             operationID: operationID, authorize: authorize)
        guard let operation = plan.operation else { return plan.item }
        try await store.append(operation) { [access] in
            try Task.checkCancellation()
            try await authorize()
            try await access.validate(target, intent: .write)
        }
        return plan.item
    }

    private func plannedMutation(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                                 requireExisting: Bool, operationID: String,
                                 authorize: @escaping @Sendable () async throws -> Void) async throws -> (item: TorahAssociationItem, operation: AnyTorahOperation?) {
        try Task.checkCancellation()
        try await authorize()
        try await access.validate(target, intent: .write)
        guard !item.id.isEmpty, !item.providerID.isEmpty,
              !item.canonicalKey.isEmpty || !item.externalID.isEmpty else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        let state = try await decoded(target: target)
        let plan = try TorahImmutableAssociationPolicy.plan(
            item, in: state.policy, requireExisting: requireExisting)
        let operation = try plan.mutation.map { try nativeOperation($0, operationID: operationID) }
        return (plan.item, operation)
    }

    /// The shared planner never manufactures native author/signature authority.
    /// The existing Any constructor freezes the exact native operation contract,
    /// and append still rechecks the current account/ACL at the actual write.
    private nonisolated func nativeOperation(_ mutation: TorahImmutableAssociationMutation,
                                 operationID: String) throws -> AnyTorahOperation {
        guard mutation.location.spaceId == workspace.spaceID else {
            throw TorahAssociationRepositoryError.targetOutsideSpace
        }
        let kind: AnyTorahOperation.Kind = switch mutation.kind {
        case .add: .add
        case .remove: .remove
        case .replace: .replace
        }
        return try AnyTorahOperation(
            operationID: operationID, spaceID: workspace.spaceID, authorID: workspace.accountID,
            kind: kind, targetObjectID: mutation.location.target.objectId,
            targetBlockID: mutation.location.target.blockId ?? "",
            providerID: mutation.providerID, canonicalRef: mutation.canonicalRef,
            payload: mutation.payload, observed: mutation.observed)
    }

    private func checkSpace(_ id: String) throws {
        guard id == workspace.spaceID else { throw TorahAssociationRepositoryError.targetOutsideSpace }
    }

    private func serial<T: Sendable>(_ action: @escaping @Sendable () async throws -> T) async throws -> T {
        let prior = mutationTail
        let task = Task {
            if let prior { await prior.value }
            try Task.checkCancellation()
            return try await action()
        }
        mutationTail = Task { _ = try? await task.value }
        return try await withTaskCancellationHandler {
            try await task.value
        } onCancel: {
            task.cancel()
        }
    }
}
