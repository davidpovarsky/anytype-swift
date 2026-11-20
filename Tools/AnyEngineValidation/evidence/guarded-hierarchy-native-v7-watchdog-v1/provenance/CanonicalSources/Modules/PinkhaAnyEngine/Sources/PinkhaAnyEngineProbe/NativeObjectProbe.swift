import Foundation
import PinkhaAnyEngine

enum NativeObjectProbe {
    static func run(client: AnyHTTPClient, spaceID: String, mode: String, args: [String]) async throws {
        func argument(_ key: String) throws -> String {
            guard let index = args.firstIndex(of: key), index + 1 < args.count else {
                throw AnyEngineError.invalidIdentity(key)
            }
            return args[index + 1]
        }
        let target = try argument("--target-id")
        let repository = try AnyGuardedTorahClaimsRepository(client: client, spaceID: spaceID)
        if mode == "object-snapshot" {
            let snapshot = try await repository.readObjectSnapshot(objectID: target)
            try emit(snapshot, status: "PASS_REAL_NATIVE_ANY_OBJECT_SNAPSHOT", initialCount: 1, updates: 1)
            return
        }
        guard let expected = Int(try argument("--updates")), (1...100).contains(expected),
              let timeout = Double(try argument("--timeout-seconds")), (1...300).contains(timeout) else {
            throw AnyEngineError.invalidOperation("object watch bounds")
        }
        let session = AnyStreamSession()
        do {
            let final = try await withThrowingTaskGroup(of: Outcome.self) { group in
                group.addTask {
                    let stream = try await repository.watchObject(objectID: target, session: session)
                    var count = 0, initialCount = 0
                    for try await update in stream {
                        try await session.requireActive(generation: update.generation)
                        count += 1
                        if update.initial {
                            initialCount += 1
                            FileHandle.standardOutput.write(Data(
                                "{\"status\":\"READY_REAL_NATIVE_ANY_OBJECT_SNAPSHOT\"}\n".utf8))
                        }
                        guard initialCount == 1 else { throw AnyEngineError.unverifiedWrite }
                        if count == expected {
                            return Outcome(snapshot: update.snapshot, initialCount: initialCount, updates: count)
                        }
                    }
                    throw AnyLiveQueryError.disconnected
                }
                group.addTask {
                    try await Task.sleep(for: .seconds(timeout))
                    throw AnyEngineError.malformedResponse("object watch timeout")
                }
                guard let outcome = try await group.next() else { throw AnyEngineError.unverifiedWrite }
                group.cancelAll()
                return outcome
            }
            await session.invalidate()
            try emit(final.snapshot, status: "PASS_REAL_NATIVE_ANY_OBJECT_WATCH",
                     initialCount: final.initialCount, updates: final.updates)
        } catch {
            await session.invalidate()
            throw error
        }
    }

    private struct Outcome: Sendable {
        let snapshot: AnyGuardedTorahObjectSnapshot
        let initialCount: Int
        let updates: Int
    }
    private static func emit(_ snapshot: AnyGuardedTorahObjectSnapshot, status: String,
                             initialCount: Int, updates: Int) throws {
        let value: AnyJSON = .object([
            "status": .string(status), "targetObjectId": .string(snapshot.targetObjectID),
            "readinessGeneration": .string(snapshot.readinessGeneration),
            "allClaimIds": .array(snapshot.projection.all.map { .string($0.id) }),
            "liveClaimIds": .array(snapshot.projection.live.map { .string($0.id) }),
            "conflictKeys": .array(snapshot.projection.conflicts.keys.sorted().map(AnyJSON.string)),
            "reachableClaimBlockIds": .array(snapshot.reachableClaimBlockIDs.sorted().map(AnyJSON.string)),
            "initialSnapshotCount": .integer(Int64(initialCount)), "updateCount": .integer(Int64(updates))
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        FileHandle.standardOutput.write(try encoder.encode(value))
        FileHandle.standardOutput.write(Data([10]))
    }
}
