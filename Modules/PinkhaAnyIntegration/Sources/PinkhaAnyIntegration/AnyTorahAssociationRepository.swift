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
        try checkSpace(spaceId)
        try await serial { [self] in
            try Task.checkCancellation()
            try await access.validate(target, intent: .write)
            let state = try await decoded(target: target)
            try requireNoConflicts(state)
            let matches = state.live.filter { $0.record.item.id == associationId }
            guard !matches.isEmpty else { return }
            let operation = try AnyTorahOperation(
                operationID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                spaceID: workspace.spaceID, authorID: workspace.accountID, kind: .remove,
                targetObjectID: target.objectId, targetBlockID: target.blockId ?? "",
                observed: matches.map { $0.claim.id })
            try await store.append(operation) { [access] in
                try Task.checkCancellation()
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

    private struct Live: Sendable {
        let claim: AnyTorahClaim
        let record: TorahStoredAssociationRecord
        let envelopeUnknown: [String: TorahJSONValue]
    }
    private struct State: Sendable {
        let live: [Live]
        let conflicts: [AnyTorahAssociationConflict]
    }

    private func decoded(target: TorahAssociationTarget) async throws -> State {
        let projection = try await store.snapshot()
        let relevant: (AnyTorahClaim) -> Bool = {
            $0.operation.targetObjectID == target.objectId &&
            $0.operation.targetBlockID == (target.blockId ?? "")
        }
        var conflicts = projection.conflicts.values.filter { $0.contains(where: relevant) }.map {
            AnyTorahAssociationConflict(claimIDs: $0.map(\.id).sorted(),
                                        reason: "same operation ID carries different payloads")
        }
        let location = TorahAssociationLocation(spaceId: workspace.spaceID, target: target)
        let live = try projection.live.filter(relevant).map { claim -> Live in
            let op = claim.operation
            guard op.spaceID == workspace.spaceID else {
                throw TorahAssociationRepositoryError.targetOutsideSpace
            }
            let payload = try codec.decodeCanonicalDocument(op.payload, legacyLocation: location)
            guard payload.records.count == 1, let record = payload.records.first,
                  record.location == location, !record.item.id.isEmpty,
                  record.item.providerID == op.providerID,
                  (record.item.canonicalKey.isEmpty ? record.item.externalID : record.item.canonicalKey) == op.canonicalRef else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            return Live(claim: claim, record: record, envelopeUnknown: payload.unknownFields)
        }
        // Concurrent replacements of one item are retained, never silently LWW'd.
        let semanticGroups = Dictionary(grouping: live) {
            TorahAssociationIdentity(item: $0.record.item, location: location)
        }
        for group in semanticGroups.values where group.count > 1 {
            conflicts.append(.init(claimIDs: group.map { $0.claim.id }.sorted(),
                                   reason: "concurrent live association variants"))
        }
        let idGroups = Dictionary(grouping: live, by: { $0.record.item.id })
        for group in idGroups.values where group.count > 1 &&
            Set(group.map { TorahAssociationIdentity(item: $0.record.item, location: location) }).count > 1 {
            conflicts.append(.init(claimIDs: group.map { $0.claim.id }.sorted(),
                                   reason: "stable association ID changed identity concurrently"))
        }
        return .init(live: live, conflicts: conflicts)
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
        let location = TorahAssociationLocation(spaceId: workspace.spaceID, target: target)
        let state = try await decoded(target: target)
        try requireNoConflicts(state)
        let incomingIdentity = TorahAssociationIdentity(item: item, location: location)
        let matches = state.live.filter {
            $0.record.item.id == item.id ||
            (!requireExisting && TorahAssociationIdentity(item: $0.record.item, location: location) == incomingIdentity)
        }
        guard matches.count <= 1 else {
            throw TorahAssociationRepositoryError.writeConflict("Ambiguous association identity")
        }
        let existing = matches.first
        if requireExisting && existing == nil {
            throw TorahAssociationRepositoryError.associationNotFound(item.id)
        }
        let merged: TorahAssociationItem
        if let existing {
            let prior = [existing.record.item]
            let items = requireExisting
                ? try TorahAssociationCollectionPolicy.updating(item, in: prior)
                : TorahAssociationCollectionPolicy.upserting(item, into: prior, location: location)
            guard let value = items.first else { throw TorahAssociationRepositoryError.malformedCanonicalData }
            merged = value
        } else {
            merged = item
        }
        var record = existing?.record ?? TorahStoredAssociationRecord(location: location, item: merged)
        record.item = merged
        let payload = try codec.encodeCanonicalDocument(.init(
            records: [record], unknownFields: existing?.envelopeUnknown ?? [:]))
        if let existing, payload == existing.claim.operation.payload { return (merged, nil) }
        let operation = try AnyTorahOperation(
            operationID: operationID, spaceID: workspace.spaceID, authorID: workspace.accountID,
            kind: existing == nil ? .add : .replace,
            targetObjectID: target.objectId, targetBlockID: target.blockId ?? "",
            providerID: merged.providerID,
            canonicalRef: merged.canonicalKey.isEmpty ? merged.externalID : merged.canonicalKey,
            payload: payload, observed: existing.map { [$0.claim.id] } ?? [])
        return (merged, operation)
    }

    private func requireNoConflicts(_ state: State) throws {
        guard state.conflicts.isEmpty else {
            throw TorahAssociationRepositoryError.writeConflict("Concurrent association variants require explicit resolution")
        }
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
