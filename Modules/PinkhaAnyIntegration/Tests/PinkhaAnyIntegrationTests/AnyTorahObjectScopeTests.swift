import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

private func objectProof(_ operations: [AnyTorahOperation], objectID: String = "object",
                         reachable: Set<String> = [], limit: Int = 10_000) throws -> AnyGuardedTorahObjectSnapshot {
    let records = operations.map { operation -> AnyJSON in
        var fields = operation.fields.object!
        fields["id"] = .string(operation.recordID)
        fields["creator"] = .string(operation.authorID)
        fields["nativeChangeId"] = .string("change")
        fields["nativeACLHeadId"] = .string("acl")
        return .object(fields)
    }
    return try .init(response: .object([
        "contract": .string("pinkha-torah-native-v1"), "scope": .string("object-logical-closure"),
        "version": .integer(1), "spaceId": .string("space"), "rootObjectId": .string("root"),
        "dataset": .string("pinkha_torah_claims_v1"), "targetObjectId": .string(objectID),
        "complete": .bool(true), "limit": .integer(Int64(limit)), "records": .array(records),
        "reachableClaimBlockIds": .array(reachable.sorted().map(AnyJSON.string)),
        "readiness": .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                              "generation": .string(String(repeating: "a", count: 64))])
    ]), expectedSpaceID: "space", expectedRootObjectID: "root", expectedObjectID: objectID, limit: limit)
}

private actor ObjectStoreFixture: AnyTorahObjectOperationObserving {
    nonisolated let workspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")
    var operations: [AnyTorahOperation]
    var reachable: Set<String>
    var globalReads = 0
    var objectReads = 0
    private var continuation: AsyncThrowingStream<AnyGuardedTorahObjectLiveSnapshot, Error>.Continuation?
    private var waiting: [CheckedContinuation<Void, Never>] = []
    init(_ operations: [AnyTorahOperation], reachable: Set<String> = []) {
        self.operations = operations; self.reachable = reachable
    }
    func snapshot() throws -> AnyTorahProjection {
        globalReads += 1
        // Represents an arbitrarily large unrelated Space. Normal editor reads
        // must not reach this deliberately unavailable workspace-wide window.
        throw AnyEngineError.readLimit
    }
    func objectSnapshot(objectID: String, limit: Int) throws -> AnyGuardedTorahObjectSnapshot {
        objectReads += 1
        return try objectProof(operations, objectID: objectID, reachable: reachable, limit: limit)
    }
    func append(_ operation: AnyTorahOperation, authorize: @escaping @Sendable () async throws -> Void) async throws {
        try await authorize()
        operations.append(operation)
        if !operation.targetBlockID.isEmpty { reachable.insert(operation.targetBlockID) }
    }
    func watchObject(objectID: String, session: AnyStreamSession, limit: Int) async throws
        -> AsyncThrowingStream<AnyGuardedTorahObjectLiveSnapshot, Error> {
        let pair = AsyncThrowingStream<AnyGuardedTorahObjectLiveSnapshot, Error>.makeStream()
        continuation = pair.continuation
        for waiter in waiting { waiter.resume() }
        waiting = []
        return pair.stream
    }
    func waitUntilWatching() async {
        if continuation != nil { return }
        await withCheckedContinuation { waiting.append($0) }
    }
    func emit(generation: UUID, initial: Bool) throws {
        continuation?.yield(.init(generation: generation,
            snapshot: try objectProof(operations, reachable: reachable), initial: initial))
    }
    func counts() -> (Int, Int) { (globalReads, objectReads) }
}

private actor ObjectAccessFixture: AnyTorahTargetAccess {
    nonisolated let workspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")
    var targets: [TorahAssociationTarget] = []
    var allowed = true
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) throws {
        targets.append(target)
        if !allowed { throw TorahAssociationRepositoryError.permissionDenied }
    }
    func deny() { allowed = false }
    func validated() -> [TorahAssociationTarget] { targets }
}

@Suite("Native object closure bridges the original canonical domain")
struct AnyTorahObjectScopeTests {
    private func operation(_ id: String, itemID: String, objectID: String = "object",
                           blockID: String = "", kind: AnyTorahOperation.Kind = .add,
                           observed: [String] = []) throws -> AnyTorahOperation {
        let location = TorahAssociationLocation(spaceId: "space", target: blockID.isEmpty ?
            .object(objectId: objectID) : .block(objectId: objectID, blockId: blockID))
        let item = TorahAssociationItem(id: itemID, kind: .ref,
            role: blockID.isEmpty ? .context : .sourceQuote, providerID: "sefaria",
            externalID: "Genesis.1.1", canonicalKey: "Genesis 1:1", labelHe: "בראשית א:א",
            unknownFields: ["future": .object(["retained": .bool(true)])])
        let payload = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
            .init(location: location, item: item, unknownFields: ["recordFuture": .string("exact")])
        ], unknownFields: ["envelopeFuture": .array([.number(7)])]))
        return try .init(operationID: String(repeating: id, count: 32), spaceID: "space", authorID: "account",
            kind: kind, targetObjectID: objectID, targetBlockID: blockID,
            providerID: "sefaria", canonicalRef: "Genesis 1:1", payload: payload, observed: observed)
    }

    private func repository(_ store: ObjectStoreFixture, _ access: ObjectAccessFixture) throws
        -> AnyTorahAssociationRepository {
        try .init(workspace: store.workspace, store: store, access: access)
    }

    @Test func wholeDocumentUsesOneObjectReadAndNativeReachabilityWithoutPerBlockGraphReads() async throws {
        let values = try [operation("1", itemID: "document"),
                          operation("2", itemID: "quote-visible", blockID: "visible"),
                          operation("3", itemID: "quote-orphan", blockID: "orphan")]
        let store = ObjectStoreFixture(values, reachable: ["visible"]), access = ObjectAccessFixture()
        let result = try await repository(store, access).objectSnapshot(objectID: "object", spaceID: "space")
        #expect(Set(result.records.map(\.item.id)) == ["document", "quote-visible"])
        #expect(result.records.first?.item.unknownFields["future"] != nil)
        #expect(result.reachableClaimBlockIDs == ["visible"])
        #expect(await access.validated() == [.object(objectId: "object")])
        let counts = await store.counts()
        #expect(counts.0 == 0 && counts.1 == 1)
    }

    @Test func ordinaryTargetReadsPreferObjectClosureAndOrphanHistoryIsIneligible() async throws {
        let value = try operation("1", itemID: "orphan", blockID: "orphan")
        let store = ObjectStoreFixture([value]), access = ObjectAccessFixture()
        let repository = try repository(store, access)
        #expect(try await repository.listDocumentAssociations(objectId: "object", spaceId: "space").isEmpty)
        await #expect(throws: TorahAssociationRepositoryError.targetNotFound) {
            try await repository.listBlockAssociations(objectId: "object", blockId: "orphan", spaceId: "space")
        }
        #expect(await store.counts().0 == 0)
    }

    @Test func firstAssociationOnFreshReachableBlockDoesNotRequireHistoryMembership() async throws {
        let store = ObjectStoreFixture([]), access = ObjectAccessFixture()
        let repository = try repository(store, access)
        let item = TorahAssociationItem(id: "first", kind: .ref, role: .sourceQuote, providerID: "sefaria",
            externalID: "Genesis.1.1", canonicalKey: "Genesis 1:1", labelHe: "בראשית א:א")
        let plan = try await repository.prepareMutation(item,
            target: .block(objectId: "object", blockId: "fresh"), spaceId: "space")
        #expect(plan?.operation.targetBlockID == "fresh")
        #expect(plan?.operation.observed.isEmpty == true)
        #expect(await store.counts().0 == 0)
    }

    @Test func foreignCollisionIsQuarantinedBeforePayloadDecodeWithoutLeakingForeignItems() async throws {
        let seed = try operation("1", itemID: "seed")
        let witness = try operation("1", itemID: "foreign", objectID: "foreign")
        let independent = try operation("2", itemID: "quote", blockID: "visible")
        let store = ObjectStoreFixture([seed, witness, independent], reachable: ["visible"])
        let result = try await repository(store, ObjectAccessFixture()).objectSnapshot(objectID: "object", spaceID: "space")
        #expect(result.records.map(\.item.id) == ["quote"])
        #expect(result.conflicts.count == 1)
        #expect(Set(result.conflicts[0].claimIDs) == [seed.claimID, witness.claimID])
    }

    @Test func pendingObservedPredecessorIsExplicitConflictForCanonicalMutation() async throws {
        let missing = try operation("1", itemID: "first")
        let replacement = try operation("2", itemID: "first", kind: .replace, observed: [missing.claimID])
        let repository = try repository(ObjectStoreFixture([replacement]), ObjectAccessFixture())
        let snapshot = try await repository.objectSnapshot(objectID: "object", spaceID: "space")
        #expect(snapshot.conflicts.count == 1)
        await #expect(throws: (any Error).self) {
            try await repository.listDocumentAssociations(objectId: "object", spaceId: "space")
        }
    }

    @Test func liveObjectPublicationRechecksCurrentReadability() async throws {
        let store = ObjectStoreFixture([try operation("1", itemID: "document")])
        let access = ObjectAccessFixture(), session = AnyStreamSession()
        let repository = try repository(store, access)
        let stream = try await repository.watchObject(objectID: "object", spaceID: "space", session: session)
        await store.waitUntilWatching()
        try await store.emit(generation: await session.generation, initial: true)
        var iterator = stream.makeAsyncIterator()
        #expect(try await iterator.next()?.snapshot.records.count == 1)
        await access.deny()
        try await store.emit(generation: await session.generation, initial: false)
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) { try await iterator.next() }
        await session.invalidate()
    }

    @Test func objectStreamRejectsMissingAtomicInitialSnapshot() async throws {
        let store = ObjectStoreFixture([]), session = AnyStreamSession()
        let stream = try await repository(store, ObjectAccessFixture())
            .watchObject(objectID: "object", spaceID: "space", session: session)
        await store.waitUntilWatching()
        try await store.emit(generation: await session.generation, initial: false)
        var iterator = stream.makeAsyncIterator()
        await #expect(throws: (any Error).self) { try await iterator.next() }
        await session.invalidate()
    }
}
