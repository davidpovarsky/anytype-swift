import Foundation
import PinkhaAnyEngine

@main
struct PinkhaAnyEngineProbe {
    static func main() async throws {
        let args = CommandLine.arguments
        func argument(_ key: String) throws -> String {
            guard let index = args.firstIndex(of: key), index + 1 < args.count else {
                throw AnyEngineError.invalidIdentity(key)
            }
            return args[index + 1]
        }
        guard let endpoint = URL(string: try argument("--endpoint")) else {
            throw AnyEngineError.invalidEndpoint
        }
        let account = try argument("--account-id")
        let space = try argument("--space-id")
        let client = try AnyHTTPClient(baseURL: endpoint, expectedAccountID: account)
        let repository = AnyTorahClaimsRepository(client: client, spaceID: space)
        let mode = args.contains("--mode") ? try argument("--mode") : "exercise"
        if mode == "check-redirect" {
            do {
                _ = try await client.requestJSON(method: "GET", path: ["v1", "probe-redirect"])
                throw AnyEngineError.unverifiedWrite
            } catch AnyEngineError.http(let status, _) {
                guard status == 307 else { throw AnyEngineError.unverifiedWrite }
            }
            FileHandle.standardOutput.write(Data("{\"status\":\"PASS_REDIRECT_REFUSED\"}\n".utf8))
            return
        }
        if mode == "check-sse" {
            try await checkSSETransport(client: client, space: space, scenario: argument("--scenario"))
            return
        }
        if mode == "watch" {
            guard let expectedUpdates = Int(try argument("--updates")), (1...100).contains(expectedUpdates),
                  let timeout = Double(try argument("--timeout-seconds")), timeout >= 1, timeout <= 300 else {
                throw AnyEngineError.invalidOperation("watch bounds")
            }
            let streamSession = AnyStreamSession()
            let outcome: WatchOutcome
            do {
                outcome = try await withThrowingTaskGroup(of: WatchOutcome.self) { group in
                    group.addTask {
                        let stream = try await repository.watch(session: streamSession)
                        var count = 0
                        var initialCount = 0
                        for try await value in stream {
                            try await streamSession.requireActive(generation: value.generation)
                            count += 1
                            if value.initial {
                                initialCount += 1
                                FileHandle.standardOutput.write(
                                    Data("{\"status\":\"READY_REAL_ANY_SSE_SNAPSHOT\"}\n".utf8))
                            }
                            guard initialCount == 1 else { throw AnyEngineError.unverifiedWrite }
                            if count == expectedUpdates {
                                return WatchOutcome(projection: value.projection,
                                                    initialCount: initialCount, updates: count)
                            }
                        }
                        throw AnyEngineError.unverifiedWrite
                    }
                    group.addTask {
                        try await Task.sleep(for: .seconds(timeout))
                        throw AnyEngineError.malformedResponse("live query timeout")
                    }
                    guard let value = try await group.next() else { throw AnyEngineError.unverifiedWrite }
                    group.cancelAll()
                    return value
                }
            } catch {
                await streamSession.invalidate()
                throw error
            }
            await streamSession.invalidate()
            let result: AnyJSON = .object([
                "status": .string("PASS_REAL_ANY_SSE_CLIENT"),
                "initialSnapshotCount": .integer(Int64(outcome.initialCount)),
                "updateCount": .integer(Int64(outcome.updates)),
                "allClaimIds": .array(outcome.projection.all.map { .string($0.id) }),
                "liveClaimIds": .array(outcome.projection.live.map { .string($0.id) }),
                "conflictKeys": .array(outcome.projection.conflicts.keys.sorted().map(AnyJSON.string))
            ])
            FileHandle.standardOutput.write(try JSONEncoder().encode(result))
            FileHandle.standardOutput.write(Data([10]))
            return
        }
        if mode == "verify" {
            let snapshot = try await repository.snapshot()
            let expected = Set(try argument("--expected-claims").split(separator: ",").map(String.init))
            guard expected.isSubset(of: Set(snapshot.all.map(\.id))) else { throw AnyEngineError.unverifiedWrite }
            let result: AnyJSON = .object([
                "status": .string("PASS_REAL_ANY_HTTP_READ"),
                "allClaimIds": .array(snapshot.all.map { .string($0.id) }),
                "liveClaimIds": .array(snapshot.live.map { .string($0.id) }),
                "conflictKeys": .array(snapshot.conflicts.keys.sorted().map(AnyJSON.string))
            ])
            FileHandle.standardOutput.write(try JSONEncoder().encode(result))
            FileHandle.standardOutput.write(Data([10]))
            return
        }
        if mode == "append" {
            guard args.contains("--allow-disposable-writes"),
                  let kind = AnyTorahOperation.Kind(rawValue: try argument("--kind")) else {
                throw AnyEngineError.invalidOperation("append mode")
            }
            let observed = args.contains("--observed")
                ? try argument("--observed").split(separator: ",").map(String.init) : []
            let payload: Data
            if kind == .remove { payload = Data() }
            else {
                guard let value = Data(base64Encoded: try argument("--payload-base64")) else {
                    throw AnyEngineError.invalidOperation("payload base64")
                }
                payload = value
            }
            let op = try AnyTorahOperation(
                operationID: argument("--operation-id"), spaceID: space, authorID: account, kind: kind,
                targetObjectID: argument("--target-id"),
                targetBlockID: args.contains("--target-block-id") ? argument("--target-block-id") : "",
                providerID: kind == .remove ? "" : argument("--provider-id"),
                canonicalRef: kind == .remove ? "" : argument("--source-ref"),
                payload: payload, observed: observed)
            try await repository.install()
            do {
                let result = try await repository.append(op)
                if args.contains("--expect-collision") { throw AnyEngineError.unverifiedWrite }
                let proof: AnyJSON = .object([
                    "status": .string("PASS_REAL_ANY_APPEND"), "claimId": .string(result.claim.id),
                    "logicalKey": .string(op.logicalKey), "created": .bool(result.created),
                    "conflicted": .bool(result.conflicted),
                    "acknowledgment": .string(result.acknowledgment.rawValue),
                    "targetObjectId": .string(op.targetObjectID)
                ])
                FileHandle.standardOutput.write(try JSONEncoder().encode(proof))
                FileHandle.standardOutput.write(Data([10]))
            } catch AnyEngineError.collision {
                guard args.contains("--expect-collision") else { throw AnyEngineError.collision(op.logicalKey) }
                FileHandle.standardOutput.write(Data("{\"status\":\"PASS_ORDERED_COLLISION_REFUSED\"}\n".utf8))
            }
            return
        }
        guard mode == "exercise", args.contains("--allow-disposable-writes") else {
            throw AnyEngineError.invalidOperation("disposable writes must be explicit")
        }
        try await repository.install()
        let base = ["v1", "spaces", space]
        let created = try await client.requestJSON(method: "POST", path: base + ["objects"], body: .object([
            "type": .string("page"),
            "initialProperties": .object(["any": .object(["name": .string("Pinkha Any disposable acceptance")])])
        ]))
        let target = try created.requireString("objectId")
        func id() -> String { UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased() }
        let add = try AnyTorahOperation(operationID: id(), spaceID: space, authorID: account, kind: .add,
            targetObjectID: target, providerID: "sefaria", canonicalRef: "Genesis.1.1",
            payload: Data("{\"text\":\"בראשית\",\"unknownFutureField\":{\"kept\":true}}".utf8))
        let first = try await repository.append(add)
        guard first.created, first.claim.operation.payload == add.payload else {
            throw AnyEngineError.unverifiedWrite
        }
        let retry = try await repository.append(add)
        guard !retry.created, retry.claim.id == first.claim.id else { throw AnyEngineError.unverifiedWrite }
        let second = try AnyTorahOperation(operationID: id(), spaceID: space, authorID: account, kind: .add,
            targetObjectID: target, providerID: "sefaria", canonicalRef: "Genesis.1.2", payload: Data("עוד".utf8))
        _ = try await repository.append(second)
        let remove = try AnyTorahOperation(operationID: id(), spaceID: space, authorID: account, kind: .remove,
            targetObjectID: target, observed: [add.claimID])
        _ = try await repository.append(remove)
        let snapshot = try await repository.snapshot()
        guard !snapshot.live.contains(where: { $0.id == add.claimID }),
              snapshot.live.contains(where: { $0.id == second.claimID }) else {
            throw AnyEngineError.unverifiedWrite
        }
        let reopened = AnyTorahClaimsRepository(client: client, spaceID: space)
        guard try await reopened.snapshot() == snapshot else { throw AnyEngineError.unverifiedWrite }
        let storage = try await repository.storageLocation()
        // Exercise the actual engine's immutable-field enforcement, not a fake server.
        var changed = try requireValue(add.fields.object)
        changed["payload"] = .string(Data("overwrite".utf8).base64EncodedString())
        do {
            _ = try await client.requestJSON(method: "POST", path: base + ["upsert"], body: .object([
                "objectId": .string(storage.root), "dataset": .string(storage.collection),
                "records": .array([.object(["id": .string(add.recordID), "fields": .object(changed)])])
            ]))
            throw AnyEngineError.unverifiedWrite
        } catch AnyEngineError.writeRejected(let codes) {
            guard codes.contains("upsert.immutable_field") else { throw AnyEngineError.unverifiedWrite }
        }
        let proof: AnyJSON = .object([
            "status": .string("PASS_REAL_ANY_HTTP_COMPONENT"),
            "scope": .string("single process, disposable space, new repository reopen; not two-device or iOS UI parity"),
            "accountId": .string(account), "spaceId": .string(space), "targetObjectId": .string(target),
            "rootObjectId": .string(storage.root), "collection": .string(storage.collection),
            "allClaimIds": .array(snapshot.all.map { .string($0.id) }),
            "liveClaimIds": .array(snapshot.live.map { .string($0.id) }),
            "conflictKeys": .array(snapshot.conflicts.keys.sorted().map(AnyJSON.string)),
            "checks": .array(["bundle schema", "native creator", "immutable write/readback", "exact retry",
                              "observed remove", "unseen add survives", "repository reopen",
                              "engine immutable rejection"].map(AnyJSON.string))
        ])
        let data = try JSONEncoder().encode(proof)
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data([10]))
    }

    private static func checkSSETransport(client: AnyHTTPClient, space: String, scenario: String) async throws {
        let expectedError: AnyLiveQueryError?
        switch scenario {
        case "normal", "generation": expectedError = nil
        case "utf8": expectedError = .invalidUTF8
        case "frame": expectedError = .frameTooLarge
        case "window": expectedError = .windowTooLarge
        case "eof": expectedError = .disconnected
        case "redirect": expectedError = .http(307)
        default: throw AnyEngineError.invalidOperation("SSE fixture scenario")
        }
        let session = AnyStreamSession()
        var invalidated = false
        do {
            let updates = try await client.subscribeQuery(
                spaceID: space, query: .object(["includeTotal": .bool(true), "limit": .integer(4)]),
                streamSession: session, maximumRecords: 4, requireComplete: true, maximumFrameBytes: 1024)
            var count = 0
            for try await update in updates {
                try await session.requireActive(generation: update.generation)
                count += 1
                if scenario == "generation" && update.initial {
                    invalidated = true
                    await session.invalidate()
                    do {
                        try await session.requireActive(generation: update.generation)
                        throw AnyEngineError.unverifiedWrite
                    } catch AnyLiveQueryError.staleGeneration {
                        // Await the stream failure too, proving cancellation before process exit.
                        continue
                    }
                }
                if scenario == "normal" && count == 2 {
                    guard update.records.count == 1, update.records[0]["value"]?.string == "תורה" else {
                        throw AnyEngineError.unverifiedWrite
                    }
                    await session.invalidate()
                    FileHandle.standardOutput.write(Data("{\"status\":\"PASS_SSE_FULL_DOCUMENT\"}\n".utf8))
                    return
                }
            }
            throw AnyEngineError.unverifiedWrite
        } catch {
            await session.invalidate()
            if scenario == "generation" && invalidated &&
                (error is CancellationError || (error as? AnyLiveQueryError) == .staleGeneration) {
                FileHandle.standardOutput.write(Data("{\"status\":\"PASS_SSE_GENERATION_CANCEL\"}\n".utf8))
                return
            }
            guard let expectedError, (error as? AnyLiveQueryError) == expectedError else { throw error }
            FileHandle.standardOutput.write(Data("{\"status\":\"PASS_SSE_NEGATIVE_BOUNDARY\"}\n".utf8))
        }
    }

    private struct WatchOutcome: Sendable {
        let projection: AnyTorahProjection
        let initialCount: Int
        let updates: Int
    }

    private static func requireValue<T>(_ value: T?) throws -> T {
        guard let value else { throw AnyEngineError.malformedResponse("expected object") }
        return value
    }
}
