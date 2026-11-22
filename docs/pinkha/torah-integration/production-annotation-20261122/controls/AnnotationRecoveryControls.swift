import Foundation

// These controls execute the real new pure assessment sources.
// Fixtures are explicit policy observations, not fake engine/native evidence.
enum RecoveryControlFailure: Error { case failed(String) }

private enum Fixture {
    static let annotationUUID = UUID(uuidString: "11111111-1111-1111-1111-111111111111")!
    static let messageID = UUID(uuidString: "22222222-2222-2222-2222-222222222222")!
    static let mutationID = UUID(uuidString: "33333333-3333-3333-3333-333333333333")!
    static let attemptID = UUID(uuidString: "44444444-4444-4444-4444-444444444444")!
    static let anotherID = UUID(uuidString: "55555555-5555-5555-5555-555555555555")!
    static let payload = String(repeating: "a", count: 64)
    static let source = String(repeating: "b", count: 64)
    static let snapshot = String(repeating: "c", count: 64)

    static func scope(account: String = "account-A", space: String = "space-A",
                      namespace: String = "existing.namespace") throws -> TorahAnnotationNativeScope {
        try .init(destination: "AnyTapy", account: account, space: space,
                  namespace: namespace, annotationUUID: annotationUUID)
    }

    static func commitment(
        scope: TorahAnnotationNativeScope? = nil,
        messageID: UUID = Fixture.messageID, mutationID: UUID = Fixture.mutationID,
        revision: Int64 = 5, sourceDigest: String = Fixture.source,
        payloadDigest: String = Fixture.payload
    ) throws -> TorahAnnotationNativeCommitment {
        try .init(scope: scope ?? Fixture.scope(), messageID: messageID,
                  mutationID: mutationID, revision: revision,
                  sourceDigest: sourceDigest, payloadDigest: payloadDigest)
    }

    static func identity(scope: TorahAnnotationNativeScope? = nil,
                         objectID: String = "actual-native-object-A") throws -> TorahAnnotationNativeIdentity {
        try .init(scope: scope ?? Fixture.scope(), objectID: objectID)
    }

    static func attempt(
        commitment: TorahAnnotationNativeCommitment? = nil,
        state: TorahAnnotationCreateDispatchState = .mayHaveDispatched
    ) throws -> TorahAnnotationNativeCreateAttempt {
        try .init(attemptID: attemptID, commitment: commitment ?? Fixture.commitment(), dispatchState: state)
    }

    static func candidate(
        identity: TorahAnnotationNativeIdentity? = nil,
        nativeTypeID: String = "actual-annotation-type",
        state: TorahAnnotationNativeObjectState = .present,
        classification: TorahAnnotationNativeClassification = .annotation,
        attemptID: UUID = Fixture.attemptID,
        creation: TorahAnnotationNativeCommitment? = nil,
        applied: TorahAnnotationNativeCommitment? = nil,
        snapshot: String? = nil
    ) throws -> TorahAnnotationNativeCandidate {
        try .init(identity: identity ?? Fixture.identity(), nativeTypeID: nativeTypeID,
                  objectState: state, classification: classification,
                  creationAttemptID: attemptID,
                  creationCommitment: creation ?? Fixture.commitment(),
                  appliedCommitment: applied, nativeSnapshotDigest: snapshot)
    }
}

@main
struct AnnotationRecoveryControls {
    static func main() throws {
        var results: [String] = []
        func check(_ name: String, _ condition: Bool) throws {
            guard condition else { throw RecoveryControlFailure.failed(name) }
            results.append(name)
        }
        func rejects(_ name: String, _ body: () throws -> Void) throws {
            var rejected = false
            do { try body() } catch is TorahAnnotationNativeContractError { rejected = true }
            try check(name, rejected)
        }

        let commitment = try Fixture.commitment()
        let identity = try Fixture.identity()
        let uncertain = try Fixture.attempt()
        let observed = try Fixture.candidate()
        func creation(
            commitment value: TorahAnnotationNativeCommitment = commitment,
            purpose: TorahAnnotationMaterializationPurpose = .annotation,
            attempt: TorahAnnotationNativeCreateAttempt? = nil,
            mapping: TorahAnnotationNativeIdentity? = nil,
            candidates: [TorahAnnotationNativeCandidate] = [],
            typeID: String = "actual-annotation-type", current: Bool = true
        ) -> TorahAnnotationCreateRecoveryAssessment {
            TorahAnnotationCreateRecovery.assessCreation(
                commitment: value, purpose: purpose, attempt: attempt, mapping: mapping,
                candidates: candidates, annotationTypeID: typeID, ownerIsCurrent: current)
        }
        func identityAssessment(_ candidate: TorahAnnotationNativeCandidate,
                                current: Bool = true) -> TorahAnnotationIdentityAssessment {
            TorahAnnotationCreateRecovery.assessIdentity(
                commitment: commitment, expectedIdentity: identity, candidate: candidate,
                annotationTypeID: "actual-annotation-type", ownerIsCurrent: current)
        }
        func appliedAssessment(_ candidate: TorahAnnotationNativeCandidate,
                               current: Bool = true) -> TorahAnnotationAppliedAssessment {
            TorahAnnotationCreateRecovery.assessApplied(
                commitment: commitment, expectedIdentity: identity, candidate: candidate,
                annotationTypeID: "actual-annotation-type", ownerIsCurrent: current)
        }

        try check("new scope requests preparation only", creation() == .prepareFirstCreate)
        try check("prepared unissued attempt still only requests preparation",
                  creation(attempt: try Fixture.attempt(state: .notDispatched)) == .prepareFirstCreate)
        try check("crash after dispatch with zero index matches remains uncertain",
                  creation(attempt: uncertain) == .creationUncertain)
        try check("repeated recovery cannot turn uncertainty into create",
                  creation(attempt: uncertain) == .creationUncertain)
        try check("different revision cannot reuse uncertain attempt",
                  creation(commitment: try Fixture.commitment(revision: 6), attempt: uncertain)
                    == .conflict(.pendingCommitmentMismatch))
        try check("retired owner cannot prepare or recover",
                  creation(attempt: uncertain, current: false) == .ownerUnavailable)
        try check("highlight-only never materializes a native annotation",
                  creation(purpose: .highlightMetadataOnly) == .notMaterializable)
        try check("tombstone never creates a replacement",
                  creation(purpose: .tombstone, attempt: uncertain) == .notMaterializable)
        try check("known mapping plus empty index requires direct original read",
                  creation(mapping: identity) == .verifyExistingObject(identity))
        try check("known returned ID plus empty index requires direct original read",
                  creation(attempt: try Fixture.attempt(state: .nativeObjectObserved(identity.objectID)))
                    == .verifyExistingObject(identity))
        try check("conflicting returned ID cannot replace mapped ID",
                  creation(attempt: try Fixture.attempt(state: .nativeObjectObserved("other-native-ID")),
                           mapping: identity) == .conflict(.objectIdentityMismatch))
        try check("one exact index candidate requests fresh verification only",
                  creation(attempt: uncertain, candidates: [observed]) == .verifyExistingObject(identity))
        try check("same UUID with wrong attempt is a conflict",
                  creation(attempt: uncertain, candidates: [try Fixture.candidate(attemptID: Fixture.anotherID)])
                    == .conflict(.creationAttemptMismatch))
        try check("candidate from different create commitment is a conflict",
                  creation(candidates: [try Fixture.candidate(creation: try Fixture.commitment(revision: 4))])
                    == .conflict(.pendingCommitmentMismatch))
        let other = try Fixture.candidate(identity: try Fixture.identity(objectID: "actual-native-object-B"))
        try check("two candidate native IDs are ambiguous",
                  creation(attempt: uncertain, candidates: [observed, other]) == .conflict(.ambiguousCandidates))
        try check("duplicate candidate rows are not inferred uniqueness",
                  creation(candidates: [observed, observed]) == .conflict(.ambiguousCandidates))
        let foreignScope = try Fixture.scope(account: "account-B")
        try check("candidate from changed account cannot be recovered",
                  creation(candidates: [try Fixture.candidate(identity: try Fixture.identity(scope: foreignScope))])
                    == .conflict(.scopeMismatch))
        try check("known mapping from changed Space cannot create or recover",
                  creation(mapping: try Fixture.identity(scope: try Fixture.scope(space: "space-B")))
                    == .conflict(.scopeMismatch))
        try check("candidate creation metadata from another scope is a conflict",
                  creation(candidates: [try Fixture.candidate(creation: try Fixture.commitment(scope: foreignScope))])
                    == .conflict(.scopeMismatch))
        for writingType in [TorahAnnotationPromotedWritingType.chiddush, .article, .research] {
            try check("explicitly promoted \(writingType.rawValue) cannot be silently demoted",
                      creation(candidates: [try Fixture.candidate(classification: .promotedDocument(writingType))])
                        == .conflict(.promotionRequiresExplicitResolution))
        }
        try check("ordinary Note type is never annotation fallback",
                  creation(candidates: [try Fixture.candidate(nativeTypeID: "original-note-type")])
                    == .conflict(.annotationTypeMismatch))
        for state in [TorahAnnotationNativeObjectState.archived, .deleted, .unavailable] {
            try check("non-present native state \(state) never causes replacement",
                      creation(mapping: identity, candidates: [try Fixture.candidate(state: state)])
                        == .conflict(.nativeObjectUnavailable))
        }
        try check("unvalidated annotation type cannot prepare create",
                  creation(typeID: "") == .conflict(.invalidAnnotationType))
        try check("mapped identity cannot be overwritten by another candidate",
                  creation(mapping: identity, candidates: [other]) == .conflict(.objectIdentityMismatch))
        try check("identity recovery is possible before body application",
                  identityAssessment(observed) == .identityMatches(identity))
        try check("identity recovery does not prove body application",
                  appliedAssessment(observed) == .bodyApplicationUnproven)
        let applied = try Fixture.candidate(applied: commitment, snapshot: Fixture.snapshot)
        try check("matching explicit applied marker retains separate snapshot commitment",
                  appliedAssessment(applied) == .appliedCommitmentMatches(identity, nativeSnapshotDigest: Fixture.snapshot))
        try check("applied marker without snapshot remains body-unproven",
                  appliedAssessment(try Fixture.candidate(applied: commitment)) == .bodyApplicationUnproven)
        try check("older applied exchange revision is explicit conflict",
                  appliedAssessment(try Fixture.candidate(applied: try Fixture.commitment(revision: 4),
                                                         snapshot: Fixture.snapshot))
                    == .conflict(.staleAppliedExchangeRevision))
        try check("newer applied exchange revision is not an ACK for old delivery",
                  appliedAssessment(try Fixture.candidate(applied: try Fixture.commitment(revision: 6),
                                                         snapshot: Fixture.snapshot))
                    == .conflict(.newerAppliedExchangeRevision))
        try check("same revision with changed payload is conflict",
                  appliedAssessment(try Fixture.candidate(applied: try Fixture.commitment(payloadDigest: Fixture.snapshot),
                                                         snapshot: Fixture.snapshot))
                    == .conflict(.appliedPayloadMismatch))
        try check("same revision with changed source is conflict",
                  appliedAssessment(try Fixture.candidate(applied: try Fixture.commitment(sourceDigest: Fixture.snapshot),
                                                         snapshot: Fixture.snapshot))
                    == .conflict(.appliedSourceMismatch))
        try check("different message cannot acknowledge same body",
                  appliedAssessment(try Fixture.candidate(applied: try Fixture.commitment(messageID: Fixture.anotherID),
                                                         snapshot: Fixture.snapshot))
                    == .conflict(.appliedMessageMismatch))
        try check("different mutation cannot acknowledge same body",
                  appliedAssessment(try Fixture.candidate(applied: try Fixture.commitment(mutationID: Fixture.anotherID),
                                                         snapshot: Fixture.snapshot))
                    == .conflict(.appliedMessageMismatch))
        try check("applied commitment from foreign account is conflict",
                  appliedAssessment(try Fixture.candidate(applied: try Fixture.commitment(scope: foreignScope),
                                                         snapshot: Fixture.snapshot))
                    == .conflict(.scopeMismatch))
        try check("retired owner cannot establish identity",
                  identityAssessment(observed, current: false) == .ownerUnavailable)
        try check("retired owner cannot establish applied assessment",
                  appliedAssessment(applied, current: false) == .ownerUnavailable)
        try check("direct readback of different actual native ID is rejected",
                  identityAssessment(other) == .conflict(.objectIdentityMismatch))
        try check("annotation classification remains non-document",
                  !TorahAnnotationNativeClassification.annotation.isDocument)
        try rejects("empty actual native ID is refused") { _ = try Fixture.identity(objectID: "") }
        try rejects("oversized actual native ID is refused") {
            _ = try Fixture.identity(objectID: String(repeating: "x", count: 513))
        }
        try rejects("NUL native ID is refused") { _ = try Fixture.identity(objectID: "native\u{0}ID") }
        try rejects("unvalidated Space is refused") { _ = try Fixture.scope(space: "wrong space") }
        try rejects("nonpositive exchange revision is refused") { _ = try Fixture.commitment(revision: 0) }
        try rejects("noncanonical source digest is refused") {
            _ = try Fixture.commitment(sourceDigest: String(repeating: "B", count: 64))
        }
        try rejects("short payload digest is refused") { _ = try Fixture.commitment(payloadDigest: "abc") }
        try rejects("invalid observed ID cannot enter durable attempt value") {
            _ = try Fixture.attempt(state: .nativeObjectObserved(""))
        }
        try rejects("invalid snapshot commitment is refused") {
            _ = try Fixture.candidate(applied: commitment, snapshot: "unverified")
        }

        let report: [String: Any] = [
            "scope": "Pure recovery policy over explicit observations; no native engine, RPC, mapping persistence or ACK",
            "tests_run": results.count, "passed": results, "native_tests": 0,
            "status": "PASS_NEW_POLICY_CONTROLS"
        ]
        let bytes = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys, .prettyPrinted])
        print(String(decoding: bytes, as: UTF8.self))
    }
}
