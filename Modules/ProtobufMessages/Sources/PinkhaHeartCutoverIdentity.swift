#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation

// Wire correlation only. These frames follow the original native operation.go
// and torahcutovercontract/contract.go. They do not parse legacy JSON, interpret
// semantic anchors, grant authority, or replace the shared source-plan codec.
// The caller bounds serialized requests before computing these identities.
extension PinkhaHeartCutoverClient {
    static func claimIdentity(_ request: Anytype_PinkhaTorahCutover.OperationRequest,
                              author: String) throws -> String {
        let kind: String
        switch request.kind.rawValue {
        case 1: kind = "add"
        case 2: kind = "remove"
        case 3: kind = "replace"
        default: throw PinkhaHeartCutoverFailure(reason: .invalidRequest)
        }
        var frame = IdentityFrame("pinkha-t2-operation")
        frame.number(1)
        for value in [request.scope.spaceID, request.operationID, author, kind,
                      request.scope.objectID, request.blockID,
                      request.source.providerID, request.source.canonicalRef] { frame.text(value) }
        frame.bytes(request.payload)
        // Only v1 observed IDs are a set that deduplicates. Native v2 ordered
        // vectors reject duplicates and therefore retain their original count.
        let observed = Array(Set(request.observedClaimIds.map { Data($0.utf8) }))
            .sorted { $0.lexicographicallyPrecedes($1) }
        frame.number(UInt32(observed.count))
        for value in observed { frame.bytes(value) }
        return claimKey(metadata: false, spaceID: request.scope.spaceID, id: request.operationID) + "/" + digest(frame.data)
    }

    static func claimIdentity(_ request: Anytype_PinkhaTorahCutover.RecordRequest,
                              author: String) throws -> String {
        let kind: String
        switch request.kind.rawValue {
        case 1: kind = "begin"
        case 2: kind = "import"
        case 3: kind = "seal"
        default: throw PinkhaHeartCutoverFailure(reason: .invalidRequest)
        }
        var frame = IdentityFrame("pinkha-torah-cutover-record-v1")
        frame.number(1)
        for value in [request.scope.spaceID, request.scope.objectID, request.recordID,
                      author, kind, request.planID] { frame.text(value) }
        switch request.kind.rawValue {
        case 1:
            guard request.hasPlan else { throw PinkhaHeartCutoverFailure(reason: .invalidRequest) }
            frame.bytes(planFrame(request.plan))
            frame.strings(request.sourceHeads)
        case 2:
            frame.text(request.factID); frame.text(request.importClaimID)
            let witnesses = request.nativeChanges.sorted {
                Data($0.changeID.utf8).lexicographicallyPrecedes(Data($1.changeID.utf8))
            }
            frame.number(UInt32(witnesses.count))
            for witness in witnesses {
                frame.text(witness.changeID); frame.text(witness.creator); frame.text(witness.aclHeadID)
            }
        case 3:
            let bindings = request.imported.sorted {
                let left = Data($0.factID.utf8), right = Data($1.factID.utf8)
                return left == right
                    ? Data($0.claimID.utf8).lexicographicallyPrecedes(Data($1.claimID.utf8))
                    : left.lexicographicallyPrecedes(right)
            }
            frame.number(UInt32(bindings.count))
            for binding in bindings { frame.text(binding.factID); frame.text(binding.claimID) }
            frame.strings(request.importRecords)
        default: preconditionFailure("kind was validated")
        }
        return claimKey(metadata: true, spaceID: request.scope.spaceID, id: request.recordID) + "/" + digest(frame.data)
    }

    private static func planFrame(_ plan: Anytype_PinkhaTorahCutover.Plan) -> Data {
        var frame = IdentityFrame("pinkha-torah-legacy-cutover-v1")
        frame.number(plan.version)
        for value in [plan.spaceID, plan.objectID, plan.propertyKey] { frame.text(value) }
        frame.data.append(plan.valuePresent ? 1 : 0)
        frame.bytes(plan.legacyValue)
        let facts = plan.facts.map { fact -> Data in
            var result = IdentityFrame("pinkha-torah-cutover-fact-v1")
            for value in [plan.spaceID, plan.objectID, fact.blockID, fact.providerID, fact.canonicalRef] { result.text(value) }
            result.bytes(fact.payload)
            return result.data
        }.sorted { $0.lexicographicallyPrecedes($1) }
        frame.number(UInt32(facts.count))
        for fact in facts { frame.bytes(fact) }
        return frame.data
    }

    private struct IdentityFrame {
        var data: Data
        init(_ domain: String) { data = Data((domain + "\0").utf8) }
        mutating func number(_ value: UInt32) {
            var bigEndian = value.bigEndian
            withUnsafeBytes(of: &bigEndian) { data.append(contentsOf: $0) }
        }
        mutating func bytes(_ value: Data) { number(UInt32(value.count)); data.append(value) }
        mutating func text(_ value: String) { bytes(Data(value.utf8)) }
        mutating func strings(_ values: [String]) {
            let sorted = values.map { Data($0.utf8) }.sorted { $0.lexicographicallyPrecedes($1) }
            number(UInt32(sorted.count))
            for value in sorted { bytes(value) }
        }
    }
}
#endif
