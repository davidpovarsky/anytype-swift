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

    private static func requireValue<T>(_ value: T?) throws -> T {
        guard let value else { throw AnyEngineError.malformedResponse("expected object") }
        return value
    }
}
