import Foundation

import PinkhaKit

import PinkhaAnyEngine



public struct AnyHierarchyLiveSnapshot: Sendable {

    public let generation: UUID

    public let initial: Bool

    public let snapshot: AnyHierarchySnapshot

}



/// Native wiki persistence with the original Pinkha tree/validation domain.

/// Mutation preconditions and readback are explicit. The stock HTTP properties

/// API has no compare-and-set across objects; this adapter does not claim one.

public actor AnyHierarchyRepository {

    public nonisolated let workspace: AnyTorahWorkspace

    public nonisolated let schema: AnyHierarchySchema

    private let store: any AnyHierarchyRecordStore

    private let creator: (any AnyHierarchyObjectCreating)?

    private let allowedTypeIDs: Set<String>

    private let excludedObjectIDs: Set<String>

    private let maximumNodes: Int

    private var mutationTail: Task<Void, Never>?



    public init(workspace: AnyTorahWorkspace, store: any AnyHierarchyRecordStore,

                creator: (any AnyHierarchyObjectCreating)? = nil, allowedTypeIDs: Set<String>,

                excludedObjectIDs: Set<String> = [], maximumNodes: Int = 10_000) throws {

        guard store.workspace == workspace, creator.map({ $0.workspace == workspace }) ?? true,

              !allowedTypeIDs.isEmpty, allowedTypeIDs.allSatisfy(AnyHierarchySchema.validID),

              (1...10_000).contains(maximumNodes) else { throw AnyHierarchyError.incompatibleSchema }

        self.workspace = workspace; self.schema = store.schema; self.store = store

        self.creator = creator; self.allowedTypeIDs = allowedTypeIDs

        self.excludedObjectIDs = excludedObjectIDs; self.maximumNodes = maximumNodes

    }



    public func snapshot() async throws -> AnyHierarchySnapshot {

        try decoded(await store.readRows())

    }



    public func prepareCreation(typeID: String, title: String, kind: PinkhaHierarchyNodeKind,

                                parentID: String? = nil,

                                mutationID: String = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased())

        async throws -> AnyHierarchyCreationPlan {

        guard allowedTypeIDs.contains(typeID) else { throw AnyHierarchyError.incompatibleSchema }

        let current = try await snapshot()

        try validateParent(parentID, current: current)

        return try .init(workspace: workspace, mutationID: mutationID, schema: schema,

                         typeID: typeID, title: title, parentID: parentID,

                         position: AnyLexicographicPosition.between(after: current.children(of: parentID).last?.position,

                                                                    before: nil), kind: kind)

    }



    public func create(_ plan: AnyHierarchyCreationPlan,

                       authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyHierarchyItem {

        guard plan.workspace == workspace, plan.schema == schema, allowedTypeIDs.contains(plan.typeID),

              let creator else { throw AnyHierarchyError.incompatibleSchema }

        return try await serial { [self] in

            try await authorize()

            try await store.validateMembership(intent: .write)

            let current = try await snapshot()

            try validateParent(plan.parentID, current: current)

            let objectID = try await creator.ensureHierarchyObject(plan: plan, authorize: authorize)

            try await authorize()

            let item = try item(from: await store.readObject(objectID: objectID))

            guard item.typeID == plan.typeID, item.title == plan.title,

                  item.parentID == plan.parentID, item.position == plan.position, item.kind == plan.kind else {

                throw AnyHierarchyError.incompleteWrite(objectID)

            }

            return item

        }

    }



    /// beforeSiblingID nil appends. The frozen native string position and prior

    /// state are retained for exact retry; a later different move is not rebased.

    public func prepareMove(objectID: String, parentID: String?,

                            beforeSiblingID: String? = nil) async throws -> AnyHierarchyPlacementPlan {

        let current = try await snapshot()

        return try placement(objectID: objectID, parentID: parentID,

                             beforeSiblingID: beforeSiblingID, in: current)

    }



    @discardableResult

    public func commitPlacement(_ plan: AnyHierarchyPlacementPlan,

                                authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyHierarchyItem {

        try await serial { [self] in try await performPlacement(plan, authorize: authorize) }

    }



    /// Rename requires the caller's prior title. Exact already-applied state is

    /// accepted; a different intervening title is reported instead of overwritten.

    @discardableResult

    public func rename(objectID: String, expectedTitle: String, newTitle: String,

                       authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyHierarchyItem {

        guard newTitle.utf8.count <= 4096, !newTitle.utf8.contains(0) else {

            throw AnyEngineError.invalidIdentity("hierarchy title")

        }

        return try await serial { [self] in

            try await authorize()

            try await store.validateMembership(intent: .write)

            let current = try await snapshot()

            guard let existing = current.itemsByID[objectID] else {

                throw PinkhaHierarchyError.nodeNotFound(objectId: objectID)

            }

            if existing.title == newTitle { return existing }

            guard existing.title == expectedTitle else { throw AnyHierarchyError.stalePlan(objectID) }

            guard let row = current.nativeRows[objectID], let expectedVersion = row["_ver"] else {

                throw AnyHierarchyError.incompatibleSchema

            }

            let fence = try capturedFence(record: row)

            do {

                try await patch(objectID: objectID, ownerID: "any", values: ["name": .string(newTitle)],

                                expectedVersion: expectedVersion, fence: fence, authorize: authorize)

            } catch {

                try await authorize()

                let readback = try item(from: await store.readObject(objectID: objectID))

                guard readback.title == newTitle else { throw error }

                return readback

            }

            try await authorize()

            let readback = try item(from: await store.readObject(objectID: objectID))

            guard readback.title == newTitle else { throw AnyHierarchyError.incompleteWrite(objectID) }

            return readback

        }

    }



    /// Reparent every direct child before moving the folder to the native bin.

    /// New children, unsupported child types, lost authority or changed placement

    /// produce a recoverable partial receipt; no child document is deleted.

    /// A final read verifies observed safety, not a cross-object transaction.

    public func removeFolderSafely(objectID: String,

                                   authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyHierarchyRemovalReceipt {

        try await serial { [self] in

            try await authorize()

            try await store.validateMembership(intent: .write)

            let initial = try await snapshot()

            guard let folder = initial.itemsByID[objectID] else {

                throw PinkhaHierarchyError.nodeNotFound(objectId: objectID)

            }

            guard folder.kind == .folder else { throw PinkhaHierarchyError.invalidNodeType(objectId: objectID) }

            try validateParent(folder.parentID, current: initial)

            try requireSupportedChildren(of: objectID, in: initial)

            var moved: [String] = []

            var archived = false

            do {

                for child in initial.children(of: objectID) {

                    try await authorize()

                    let current = try await snapshot()

                    try requireSameFolder(folder, in: current)

                    try requireSupportedChildren(of: objectID, in: current)

                    guard current.itemsByID[child.objectID]?.parentID == objectID else { continue }

                    let plan = try placement(objectID: child.objectID, parentID: folder.parentID,

                                             beforeSiblingID: nil, in: current)

                    _ = try await performPlacement(plan, authorize: authorize)

                    moved.append(child.objectID)

                }

                let beforeArchive = try await snapshot()

                try requireSameFolder(folder, in: beforeArchive)

                guard rawChildren(of: objectID, in: beforeArchive).isEmpty else {

                    throw AnyHierarchyError.stalePlan("folder gained children")

                }

                try await store.setArchived(objectID: objectID, archived: true, authorize: authorize)

                let folderRecord = try await store.readObject(objectID: objectID)

                archived = folderRecord["any"]?["collections"]?.array?.contains(.string("bin")) == true

                guard archived else { throw AnyHierarchyError.incompleteWrite(objectID) }

                let after = try await snapshot()

                guard rawChildren(of: objectID, in: after).isEmpty else {

                    // Restore visibility if a concurrent client added a child in

                    // the unavoidable stock-API gap. Failure remains explicit.

                    try await store.setArchived(objectID: objectID, archived: false, authorize: authorize)

                    let restored = try await store.readObject(objectID: objectID)

                    archived = restored["any"]?["collections"]?.array?.contains(.string("bin")) == true

                    throw AnyHierarchyError.stalePlan("concurrent child requires another removal plan")

                }

                return .init(folderID: objectID, reparentedIDs: moved, folderArchived: archived,

                             complete: true, recoveryError: nil)

            } catch {

                // Readback can prove a bin write even when the reply was lost.

                // If that read fails, report uncertainty rather than asserting a

                // negative or retrying a destructive operation.

                let archiveState: Bool?

                if let row = try? await store.readObject(objectID: objectID),

                   let collections = row["any"]?["collections"]?.array {

                    archiveState = collections.contains(.string("bin"))

                } else { archiveState = nil }

                return .init(folderID: objectID, reparentedIDs: moved, folderArchived: archiveState,

                             complete: false, recoveryError: error)

            }

        }

    }



    public func watch(session: AnyStreamSession) async throws -> AsyncThrowingStream<AnyHierarchyLiveSnapshot, Error> {

        guard let observable = store as? any AnyHierarchyObservableRecordStore else {

            throw AnyLiveQueryError.invalidSequence("native hierarchy observation unavailable")

        }

        let generation = await session.generation

        try await session.requireActive(generation: generation)

        try await store.validateMembership(intent: .read)

        let upstream = try await observable.watch(session: session)

        let pair = AsyncThrowingStream<AnyHierarchyLiveSnapshot, Error>.makeStream(bufferingPolicy: .bufferingOldest(2))

        let registration = try await session.register(generation: generation) {

            pair.continuation.finish(throwing: AnyLiveQueryError.staleGeneration)

        }

        let worker = Task { [self] in

            do {

                var receivedInitial = false

                for try await update in upstream {

                    try Task.checkCancellation()

                    try await session.requireActive(generation: update.generation)

                    guard update.generation == generation,

                          receivedInitial ? !update.initial : update.initial else {

                        throw AnyLiveQueryError.invalidSequence("hierarchy initial snapshot or generation")

                    }

                    try await store.validateMembership(intent: .read)

                    try await session.requireActive(generation: generation)

                    let output = AnyHierarchyLiveSnapshot(generation: generation, initial: update.initial,

                                                          snapshot: try decoded(update.records))

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

            } catch { pair.continuation.finish(throwing: error) }

            await session.unregister(registration)

        }

        pair.continuation.onTermination = { @Sendable _ in worker.cancel() }

        return pair.stream

    }



    private func performPlacement(_ plan: AnyHierarchyPlacementPlan,

                                  authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyHierarchyItem {

        guard plan.workspace == workspace, plan.schema == schema else { throw AnyHierarchyError.incompatibleSchema }

        // Validate persisted native metadata before even accepting an already-

        // applied placement. A legacy plan must not acquire a new run or sequence.

        let fence = try validatedPlanFence(plan)

        try await authorize()

        try await store.validateMembership(intent: .write)

        let current = try await snapshot()

        guard let before = current.itemsByID[plan.objectID] else {

            throw PinkhaHierarchyError.nodeNotFound(objectId: plan.objectID)

        }

        try current.validateMove(objectID: plan.objectID, parentID: plan.parentID)

        if matches(before, plan: plan) { return before }

        guard before.parentID == plan.previousParentID, before.position == plan.previousPosition,

              current.nativeRows[plan.objectID]?["_ver"] == plan.expectedVersion else {

            throw AnyHierarchyError.stalePlan(plan.objectID)

        }

        if let fence {

            guard let row = current.nativeRows[plan.objectID],

                  try capturedFence(record: row) == fence else {

                throw AnyHierarchyError.stalePlan(plan.objectID)

            }

        }

        do {

            try await patch(objectID: plan.objectID, ownerID: schema.collectionID, values: [

                schema.parentPropertyID: .string(plan.parentID ?? ""),

                schema.positionPropertyID: .string(plan.position)

            ], expectedVersion: plan.expectedVersion, fence: fence, authorize: authorize)

        } catch {

            try await authorize()

            let readback = try item(from: await store.readObject(objectID: plan.objectID))

            guard matches(readback, plan: plan) else { throw error }

            return readback

        }

        try await authorize()

        let readback = try item(from: await store.readObject(objectID: plan.objectID))

        guard matches(readback, plan: plan) else { throw AnyHierarchyError.incompleteWrite(plan.objectID) }

        return readback

    }



    private func patch(objectID: String, ownerID: String, values: [String: AnyJSON],

                       expectedVersion: AnyJSON, fence: AnyConditionalPropertyFence?,

                       authorize: @escaping @Sendable () async throws -> Void) async throws {

        if let conditional = store as? any AnyHierarchyConditionalRecordStore {

            guard let fence, fence.nativeVersion == expectedVersion,

                  fence.engineStartedAt == conditional.engineStartedAt else {

                throw AnyHierarchyError.stalePlan(objectID)

            }

            try await conditional.patch(objectID: objectID, ownerID: ownerID, values: values,

                                        fence: fence, authorize: authorize)

        } else {

            guard fence == nil else { throw AnyHierarchyError.incompatibleSchema }

            try await store.patch(objectID: objectID, ownerID: ownerID, values: values, authorize: authorize)

        }

    }



    private nonisolated func capturedFence(record: AnyJSON) throws -> AnyConditionalPropertyFence? {

        guard let conditional = store as? any AnyHierarchyConditionalRecordStore else { return nil }

        return try .init(record: record, engineStartedAt: conditional.engineStartedAt)

    }



    private nonisolated func validatedPlanFence(_ plan: AnyHierarchyPlacementPlan) throws -> AnyConditionalPropertyFence? {

        guard let conditional = store as? any AnyHierarchyConditionalRecordStore else {

            guard plan.propertyFence == nil else { throw AnyHierarchyError.incompatibleSchema }

            return nil

        }

        guard let fence = plan.propertyFence, fence.nativeVersion == plan.expectedVersion,

              fence.engineStartedAt == conditional.engineStartedAt else {

            throw AnyHierarchyError.stalePlan(plan.objectID)

        }

        return fence

    }



    private nonisolated func placement(objectID: String, parentID: String?, beforeSiblingID: String?,

                           in current: AnyHierarchySnapshot) throws -> AnyHierarchyPlacementPlan {

        try current.validateMove(objectID: objectID, parentID: parentID)

        guard let existing = current.itemsByID[objectID] else {

            throw PinkhaHierarchyError.nodeNotFound(objectId: objectID)

        }

        let siblings = current.children(of: parentID).filter { $0.objectID != objectID }

        let position: String

        if let beforeSiblingID {

            guard let offset = siblings.firstIndex(where: { $0.objectID == beforeSiblingID }) else {

                throw PinkhaHierarchyError.nodeNotFound(objectId: beforeSiblingID)

            }

            position = try AnyLexicographicPosition.between(

                after: offset == 0 ? nil : siblings[offset - 1].position, before: siblings[offset].position)

        } else {

            position = try AnyLexicographicPosition.between(after: siblings.last?.position, before: nil)

        }

        guard let row = current.nativeRows[objectID], let version = row["_ver"] else {

            throw AnyHierarchyError.incompatibleSchema

        }

        let fence = try capturedFence(record: row)

        return try .init(workspace: workspace, schema: schema, objectID: objectID,

                         previousParentID: existing.parentID, previousPosition: existing.position, expectedVersion: version,

                         parentID: parentID, position: position, propertyFence: fence)

    }



    private nonisolated func decoded(_ rows: [AnyJSON]) throws -> AnyHierarchySnapshot {

        try .init(workspace: workspace, schema: schema, rows: rows, allowedTypeIDs: allowedTypeIDs,

                  excludedObjectIDs: excludedObjectIDs, maximumNodes: maximumNodes)

    }

    private nonisolated func item(from row: AnyJSON) throws -> AnyHierarchyItem {

        let snapshot = try decoded([row])

        guard let item = snapshot.items.first else {

            throw AnyHierarchyError.malformedRow(row["id"]?.string ?? "")

        }

        return item

    }

    private nonisolated func matches(_ item: AnyHierarchyItem, plan: AnyHierarchyPlacementPlan) -> Bool {

        item.parentID == plan.parentID && item.position == plan.position

    }

    private nonisolated func validateParent(_ parentID: String?, current: AnyHierarchySnapshot) throws {

        guard let parentID else { return }

        guard let item = current.itemsByID[parentID] else {

            throw PinkhaHierarchyError.parentNotFound(parentId: parentID)

        }

        var cursor: String? = item.objectID

        var visited = Set<String>()

        while let id = cursor {

            guard visited.insert(id).inserted else { throw AnyHierarchyError.cyclicParent(id) }

            guard let parent = current.itemsByID[id] else { throw PinkhaHierarchyError.parentNotFound(parentId: id) }

            cursor = parent.parentID

        }

    }

    private nonisolated func rawChildren(of objectID: String, in current: AnyHierarchySnapshot) -> [String] {

        current.nativeRows.compactMap { id, row in

            row[schema.collectionID]?[schema.parentPropertyID]?.string == objectID ? id : nil

        }.sorted()

    }

    private nonisolated func requireSupportedChildren(of objectID: String, in current: AnyHierarchySnapshot) throws {

        for id in rawChildren(of: objectID, in: current) where current.itemsByID[id] == nil {

            throw AnyHierarchyError.unsupportedChild(id)

        }

    }

    private nonisolated func requireSameFolder(_ folder: AnyHierarchyItem, in current: AnyHierarchySnapshot) throws {

        guard let now = current.itemsByID[folder.objectID], now.kind == .folder,

              now.parentID == folder.parentID, now.position == folder.position else {

            throw AnyHierarchyError.stalePlan(folder.objectID)

        }

    }

    private func serial<Value: Sendable>(_ operation: @escaping @Sendable () async throws -> Value) async throws -> Value {

        let previous = mutationTail

        let task = Task {

            if let previous { await previous.value }

            try Task.checkCancellation()

            return try await operation()

        }

        mutationTail = Task { _ = try? await task.value }

        return try await withTaskCancellationHandler { try await task.value } onCancel: { task.cancel() }

    }

}

