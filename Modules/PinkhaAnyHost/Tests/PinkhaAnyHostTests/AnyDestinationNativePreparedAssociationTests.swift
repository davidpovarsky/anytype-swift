#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// The source is an exact private copy of the previously qualified Any
/// semantic fixture. A new seed is explicit and never rewrites its old claims.
final class AnyDestinationNativePreparedAssociationTests: XCTestCase, @unchecked Sendable {
    func testPreparedSemanticAssociationKeepsObservedSetConflictAndColdRetry() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let runtimePath = env["PINKHA_NATIVE_PREPARED_ASSOCIATION_FIXTURE"],
              let workPath = env["PINKHA_NATIVE_PREPARED_ASSOCIATION_WORK"],
              let phase = env["PINKHA_NATIVE_PREPARED_ASSOCIATION_PHASE"],
              ["execute", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the isolated retained semantic-account controller.")
        }
        let runtime = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: runtimePath)))
        try require(runtime["componentScope"] == .string("retained-native-prepared-association-v1"))
        try require(runtime["binarySHA256"] == .string("1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"))
        try require(runtime["outboundDeniedByOS"] == .bool(true) && runtime["networkPeerCount"] == .integer(0))
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let originalBytes = try Data(contentsOf: work.appendingPathComponent("semantic-original-fixture.json"))
        try require(AnyContentDigest.sha256(originalBytes) == "2103428a0bac1645b612936bde7b13ba6e707ad9e172059f44a618b941cd3e1f")
        let original = try JSONDecoder().decode(AnyJSON.self, from: originalBytes)
        let account = try XCTUnwrap(runtime["accountID"]?.string), space = try XCTUnwrap(runtime["spaceID"]?.string)
        let object = try XCTUnwrap(original["objectID"]?.string), block = try XCTUnwrap(original["blockID"]?.string)
        try require(Data(account.utf8) == Data(XCTUnwrap(original["creatorAccountID"]?.string).utf8))
        try require(Data(space.utf8) == Data(XCTUnwrap(original["spaceID"]?.string).utf8))
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let location = TorahAssociationLocation(spaceId: space, target: .object(objectId: object))
        let semantic = try JSONDecoder().decode(TorahAssociationItem.self,
            from: AnyDestinationDefinitionChecks.bytes(XCTUnwrap(original["semanticItem"])))
        let unrelated = try JSONDecoder().decode(TorahAssociationItem.self,
            from: AnyDestinationDefinitionChecks.bytes(XCTUnwrap(original["unrelatedItem"])))
        let anchor = try XCTUnwrap(TorahSemanticAnchorAssociation.decoding(semantic, location: location)).anchor
        try require(anchor.id.uuidString.lowercased() == original["anchor"]?["id"]?.string?.lowercased())
        let linkedBytes = try XCTUnwrap(Data(base64Encoded: XCTUnwrap(original["linkedCanonical"]?.string)))
        let linked = try TorahAssociationPayloadCodec().decodeCanonicalDocument(linkedBytes, legacyLocation: location)
        let sourceRecord = try XCTUnwrap(linked.records.first { $0.item.id == semantic.id })
        try require(sourceRecord.item == semantic && !semantic.unknownFields.isEmpty)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(runtime["baseURL"]?.string))), expectedAccountID: account)
        let store = try AnyGuardedTorahOperationStore(client: client, workspace: workspace)
        let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace, allowedTypeIDs: ["page"])
        let repository = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: access)
        let documents = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let ledger = try NativePreparedAssociationLedger(url: work.appendingPathComponent("dispatch-ledger.json"))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let returned: (AnyHostLease, AnyTorahPreparedMutation)
        do {
            returned = try await session.perform { lease in
                let authorize: @Sendable () async throws -> Void = { try await lease.validate() }
                let read = try await documents.read(objectID: object, lease: lease)
                try self.require(read.snapshot.depthFirstIDs == [block])
                try self.require(read.snapshot.blocks[0].text == original["editedBody"]?.string)
                try self.require(read.snapshot.blocks[0].native["style"] == original["style"])
                try self.require(read.snapshot.blocks[0].native["nav"] == original["navigation"])
                guard case .resolved(let fragments) = try AnySemanticAnchorDocument.resolve(anchor, read: read) else {
                    throw NativePreparedAssociationFailure.assertion("original marker is unresolved")
                }
                try self.require(fragments.count == 1 && fragments[0].blockID == block && fragments[0].range.length > 0)
                let body = try encoder.encode(read.snapshot.blocks.map(\.native))
                let initial = try await store.repository.readObjectSnapshot(objectID: object)
                try self.require(initial.projection.conflicts.isEmpty && initial.projection.pendingObserved.isEmpty)
                let preparedA: AnyTorahPreparedMutation
                if phase == "execute" {
                    try self.require(initial.projection.all.count == 3 && initial.projection.live.count == 1)
                    let initialView = try await repository.snapshot(target: location.target, spaceID: space)
                    try self.require(initialView.records.map(\.item) == [unrelated] && initialView.conflicts.isEmpty)
                    let candidates = try initial.projection.all.filter { $0.operation.kind != .remove }.filter { claim in
                        let value = try TorahImmutableAssociationContent(payload: claim.operation.payload,
                            location: location, providerID: claim.operation.providerID, canonicalRef: claim.operation.canonicalRef)
                        return value.record.item.id == semantic.id
                    }
                    try self.require(candidates.count == 1)
                    let removed = candidates[0].operation
                    let content = try TorahImmutableAssociationContent(payload: removed.payload, location: location,
                        providerID: removed.providerID, canonicalRef: removed.canonicalRef)
                    try self.require(content.record == sourceRecord && content.envelopeUnknown == linked.unknownFields)
                    let run = try XCTUnwrap(runtime["runID"]?.string)
                    try self.require(run.utf8.count == 32 && run.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) })
                    func operationID(_ suffix: String) -> String { String(AnyContentDigest.sha256(Data((run + "|" + suffix).utf8)).prefix(32)) }
                    let ids = ["seed", "A", "B"].map(operationID)
                    try self.require(Set(ids).count == 3 && initial.projection.all.allSatisfy { !ids.contains($0.operation.operationID) })
                    let seed = try AnyTorahPreparedMutation(workspace: workspace, operation: .init(
                        operationID: ids[0], spaceID: space, authorID: account, kind: .add,
                        targetObjectID: object, targetBlockID: "", providerID: removed.providerID,
                        canonicalRef: removed.canonicalRef, payload: removed.payload, observed: []))
                    try self.require(seed.operation.operationID != removed.operationID && seed.operation.payload == removed.payload)
                    try Self.durableNew(encoder.encode(seed), at: work.appendingPathComponent("seed-prepared.json"))
                    try Self.durableNew(Self.nativeBytes(initial), at: work.appendingPathComponent("baseline-claims.json"))
                    try Self.durableNew(body, at: work.appendingPathComponent("baseline-body.json"))
                    _ = try await self.commit(seed, name: "explicit-new-seed", expectedCount: 4,
                        repository: repository, store: store, object: object, authorize: authorize, ledger: ledger)
                    var a = semantic; a.labelEn = "Prepared A — exact retained marker"
                    let candidateA = try await repository.prepareMutation(a, target: location.target,
                        spaceId: space, requireExisting: true, operationID: ids[1], authorize: authorize)
                    preparedA = try XCTUnwrap(candidateA)
                    var b = semantic; b.labelEn = "Intervening B — same original association"
                    let candidateB = try await repository.prepareMutation(b, target: location.target,
                        spaceId: space, requireExisting: true, operationID: ids[2], authorize: authorize)
                    let preparedB = try XCTUnwrap(candidateB)
                    try self.require(preparedA.operation.kind == .replace && preparedB.operation.kind == .replace)
                    try self.require(preparedA.operation.observed == [seed.operation.claimID] && preparedB.operation.observed == [seed.operation.claimID])
                    for (prepared, expected, name) in [(preparedA, a, "A"), (preparedB, b, "B")] {
                        let projected = try TorahImmutableAssociationContent(payload: prepared.operation.payload,
                            location: location, providerID: prepared.operation.providerID, canonicalRef: prepared.operation.canonicalRef)
                        var expectedRecord = sourceRecord; expectedRecord.item = expected
                        try self.require(projected.record == expectedRecord && projected.envelopeUnknown == linked.unknownFields)
                        try Self.durableNew(encoder.encode(prepared), at: work.appendingPathComponent(name + "-prepared.json"))
                    }
                    _ = try await self.commit(preparedB, name: "intervening-B", expectedCount: 5,
                        repository: repository, store: store, object: object, authorize: authorize, ledger: ledger)
                    let restoredA = try JSONDecoder().decode(AnyTorahPreparedMutation.self,
                        from: Data(contentsOf: work.appendingPathComponent("A-prepared.json")))
                    try self.require(restoredA.operation == preparedA.operation)
                    _ = try await self.commit(restoredA, name: "frozen-A", expectedCount: 6,
                        repository: repository, store: store, object: object, authorize: authorize, ledger: ledger)
                    _ = try await self.commit(restoredA, name: "exact-A-retry", expectedCount: 6,
                        repository: repository, store: store, object: object, authorize: authorize, ledger: ledger)
                } else {
                    preparedA = try JSONDecoder().decode(AnyTorahPreparedMutation.self,
                        from: Data(contentsOf: work.appendingPathComponent("A-prepared.json")))
                    try self.require(initial.projection.all.count == 6)
                    try self.require(Self.nativeBytes(initial) == Data(contentsOf: work.appendingPathComponent("execute-claims.json")))
                    try self.require(body == Data(contentsOf: work.appendingPathComponent("baseline-body.json")))
                    _ = try await self.commit(preparedA, name: "cold-exact-A-retry", expectedCount: 6,
                        repository: repository, store: store, object: object, authorize: authorize, ledger: ledger)
                }
                let preparedB = try JSONDecoder().decode(AnyTorahPreparedMutation.self,
                    from: Data(contentsOf: work.appendingPathComponent("B-prepared.json")))
                let after = try await store.repository.readObjectSnapshot(objectID: object)
                try self.require(after.projection.all.count == 6 && after.projection.live.count == 3)
                try self.require(after.projection.conflicts.isEmpty && after.projection.pendingObserved.isEmpty)
                let baseline = try JSONDecoder().decode(AnyJSON.self,
                    from: Data(contentsOf: work.appendingPathComponent("baseline-claims.json")))
                let afterJSON = try JSONDecoder().decode(AnyJSON.self, from: Self.nativeBytes(after))
                let baselineRows = try XCTUnwrap(baseline["claims"]?.array), currentRows = try XCTUnwrap(afterJSON["claims"]?.array)
                try self.require(baselineRows.count == 3 && baselineRows.allSatisfy { currentRows.contains($0) })
                let state = try await repository.snapshot(target: location.target, spaceID: space)
                try self.require(state.records.count == 3 && state.conflicts.count == 1)
                try self.require(Set(state.conflicts[0].claimIDs) == Set([preparedA.operation.claimID, preparedB.operation.claimID]))
                try self.require(state.records.filter { $0.item.id == unrelated.id }.map(\.item) == [unrelated])
                let variants = state.records.filter { $0.item.id == semantic.id }
                try self.require(variants.count == 2 && Set(variants.compactMap { $0.item.labelEn }) == ["Prepared A — exact retained marker", "Intervening B — same original association"])
                for variant in variants {
                    var originalItem = variant.item; originalItem.labelEn = semantic.labelEn
                    try self.require(originalItem == semantic && variant.unknownFields == sourceRecord.unknownFields)
                    let resolved = try XCTUnwrap(TorahSemanticAnchorAssociation.decoding(variant.item, location: location))
                    try self.require(resolved.anchor == anchor)
                }
                do {
                    _ = try await repository.listDocumentAssociations(objectId: object, spaceId: space)
                    throw NativePreparedAssociationFailure.assertion("concurrent variants were silently flattened")
                } catch TorahAssociationRepositoryError.writeConflict { }
                let unchangedBody = try await documents.read(objectID: object, lease: lease)
                try self.require(encoder.encode(unchangedBody.snapshot.blocks.map(\.native)) == body)
                let complete = try Self.nativeBytes(after)
                if phase == "reopen" { try self.require(complete == Data(contentsOf: work.appendingPathComponent("execute-claims.json"))) }
                try Self.durableNew(complete, at: work.appendingPathComponent(phase + "-claims.json"))
                try Self.durableNew(body, at: work.appendingPathComponent(phase + "-body.json"))
                return (lease, preparedA)
            }
            await session.revokeAndDrain()
        } catch {
            await session.revokeAndDrain()
            throw error
        }
        try await ledger.begin("retired-lease-" + phase, prepared: returned.1)
        do {
            _ = try await repository.commitPrepared(returned.1, authorize: { try await returned.0.validate() })
            try await ledger.unknown("retired-lease-" + phase)
            throw NativePreparedAssociationFailure.assertion("retired lease admitted an exact retry")
        } catch AnyHostError.sessionClosed {
            let after = try await store.repository.readObjectSnapshot(objectID: object)
            try require(Self.nativeBytes(after) == Data(contentsOf: work.appendingPathComponent(phase + "-claims.json")))
            try await ledger.denied("retired-lease-" + phase)
        }
        try Self.durableNew(AnyDestinationDefinitionChecks.bytes(.object([
            "phase": .string(phase), "baselineNativeClaims": .integer(3), "finalNativeClaims": .integer(6),
            "newDistinctClaims": .integer(3), "historicalClaimsAndProvenanceUnchanged": .bool(true),
            "frozenObservedSetRetained": .bool(true), "interveningVariantRetained": .bool(true),
            "explicitSemanticConflicts": .integer(1), "unrelatedAssociationUnchanged": .bool(true),
            "originalMarkerBlockAndBodyUnchanged": .bool(true), "unknownPayloadFieldsUnchanged": .bool(true),
            "retiredLeaseRefused": .bool(true), "newObjects": .integer(0), "newEditorBlocks": .integer(0),
            "moduleInstalls": .integer(0), "originalSourceAdmissionPromoted": .bool(false),
            "independentClientSignatureVerification": .bool(false)])), at: work.appendingPathComponent(phase + "-result.json"))
        try require(AnyContentDigest.sha256(Data(contentsOf: work.appendingPathComponent("semantic-original-fixture.json"))) == "2103428a0bac1645b612936bde7b13ba6e707ad9e172059f44a618b941cd3e1f")
        print("PINKHA_NATIVE_PREPARED_ASSOCIATION_PHASE_PASS " + phase)
    }

    private func commit(_ prepared: AnyTorahPreparedMutation, name: String, expectedCount: Int,
                        repository: AnyTorahAssociationRepository, store: AnyGuardedTorahOperationStore,
                        object: String, authorize: @escaping @Sendable () async throws -> Void,
                        ledger: NativePreparedAssociationLedger) async throws -> AnyGuardedTorahObjectSnapshot {
        try await ledger.begin(name, prepared: prepared)
        do {
            _ = try await repository.commitPrepared(prepared, authorize: authorize)
            let observed = try await store.repository.readObjectSnapshot(objectID: object)
            try require(observed.projection.all.count == expectedCount)
            let exact = observed.projection.all.filter { $0.id == prepared.operation.claimID }
            try require(exact.count == 1 && exact[0].operation == prepared.operation)
            try await ledger.acknowledged(name, snapshotSHA256: AnyContentDigest.sha256(Self.nativeBytes(observed)))
            return observed
        } catch {
            try await ledger.unknown(name)
            throw error
        }
    }

    private static func nativeBytes(_ snapshot: AnyGuardedTorahObjectSnapshot) throws -> Data {
        let rows = try snapshot.projection.all.sorted { $0.id < $1.id }.map { claim -> AnyJSON in
            let provenance = try XCTUnwrap(snapshot.provenance[claim.id])
            guard provenance.creator == claim.creator, !provenance.changeID.isEmpty, !provenance.aclHeadID.isEmpty else {
                throw NativePreparedAssociationFailure.assertion("native provenance")
            }
            return .object(["claimID": .string(claim.id), "creator": .string(claim.creator),
                "operation": try JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(claim.operation)),
                "nativeChangeID": .string(provenance.changeID), "nativeACLHeadID": .string(provenance.aclHeadID)])
        }
        return try AnyDestinationDefinitionChecks.bytes(.object(["spaceID": .string(snapshot.spaceID),
            "rootObjectID": .string(snapshot.rootObjectID), "targetObjectID": .string(snapshot.targetObjectID),
            "claims": .array(rows)]))
    }

    private static func durableNew(_ data: Data, at url: URL) throws {
        try data.write(to: url, options: .withoutOverwriting)
        let file = try FileHandle(forWritingTo: url)
        defer { try? file.close() }
        try file.synchronize()
    }

    private func require(_ value: @autoclosure () throws -> Bool) throws {
        guard try value() else { throw NativePreparedAssociationFailure.assertion("native acceptance predicate") }
    }
}

private actor NativePreparedAssociationLedger {
    let url: URL
    var rows: [AnyJSON]
    init(url: URL) throws {
        self.url = url
        rows = FileManager.default.fileExists(atPath: url.path)
            ? try JSONDecoder().decode([AnyJSON].self, from: Data(contentsOf: url)) : []
    }
    func begin(_ name: String, prepared: AnyTorahPreparedMutation) throws {
        guard !rows.contains(where: { $0["name"] == .string(name) }) else {
            throw NativePreparedAssociationFailure.assertion("mutation phase repeated")
        }
        rows.append(.object(["name": .string(name), "state": .string("dispatching"),
            "operationID": .string(prepared.operation.operationID), "claimID": .string(prepared.operation.claimID),
            "payloadSHA256": .string(AnyContentDigest.sha256(prepared.operation.payload)),
            "observed": .array(prepared.operation.observed.map(AnyJSON.string))]))
        try save()
    }
    func acknowledged(_ name: String, snapshotSHA256: String) throws { try finish(name, state: "acknowledged-validated", digest: snapshotSHA256) }
    func unknown(_ name: String) throws { try finish(name, state: "unqualified-effects-unknown") }
    func denied(_ name: String) throws { try finish(name, state: "confirmed-retired-lease-refusal") }
    private func finish(_ name: String, state: String, digest: String? = nil) throws {
        guard let index = rows.firstIndex(where: { $0["name"] == .string(name) }),
              var row = rows[index].object, row["state"] == .string("dispatching") else {
            throw NativePreparedAssociationFailure.assertion("missing dispatch ledger")
        }
        row["state"] = .string(state)
        if let digest { row["observedNativeSnapshotSHA256"] = .string(digest) }
        rows[index] = .object(row); try save()
    }
    private func save() throws {
        try AnyDestinationDefinitionChecks.bytes(.array(rows)).write(to: url, options: .atomic)
        let file = try FileHandle(forWritingTo: url)
        defer { try? file.close() }
        try file.synchronize()
    }
}

private enum NativePreparedAssociationFailure: Error { case assertion(String) }
#endif
