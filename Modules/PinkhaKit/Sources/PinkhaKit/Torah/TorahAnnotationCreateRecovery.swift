import Foundation

public enum TorahAnnotationRecoveryConflict: Sendable, Equatable {
    case invalidAnnotationType
    case scopeMismatch
    case pendingCommitmentMismatch
    case creationAttemptMismatch
    case ambiguousCandidates
    case objectIdentityMismatch
    case nativeObjectUnavailable
    case annotationTypeMismatch
    case promotionRequiresExplicitResolution
    case staleAppliedExchangeRevision
    case newerAppliedExchangeRevision
    case appliedPayloadMismatch
    case appliedSourceMismatch
    case appliedMessageMismatch
}

/// An assessment chooses the next verification step. It does not authorize a
/// native create, persist a mapping, certify uniqueness or acknowledge delivery.
public enum TorahAnnotationCreateRecoveryAssessment: Sendable, Equatable {
    case prepareFirstCreate
    case verifyExistingObject(TorahAnnotationNativeIdentity)
    case creationUncertain
    case ownerUnavailable
    case notMaterializable
    case conflict(TorahAnnotationRecoveryConflict)
}

/// Identity recovery is deliberately distinct from body application.
public enum TorahAnnotationIdentityAssessment: Sendable, Equatable {
    case identityMatches(TorahAnnotationNativeIdentity)
    case ownerUnavailable
    case conflict(TorahAnnotationRecoveryConflict)
}

/// Even a positive assessment is not an opaque runtime-issued receipt. The
/// legacy positive case remains source-compatible, but assessApplied never
/// emits it from caller-constructible digest data. Only a separately closed
/// actual native comparison can describe body equality, and even a historical
/// export comparison alone is not an atomic native COMMIT or ACK capability.
public enum TorahAnnotationAppliedAssessment: Sendable, Equatable {
    case appliedCommitmentMatches(TorahAnnotationNativeIdentity, nativeSnapshotDigest: String)
    case bodyApplicationUnproven
    case ownerUnavailable
    case conflict(TorahAnnotationRecoveryConflict)
}

/// Pure conservative policy over explicit observations. There is no database,
/// transport, native invocation, account selection, retry loop or hash encoder.
public enum TorahAnnotationCreateRecovery {
    public static func assessCreation(
        commitment: TorahAnnotationNativeCommitment,
        purpose: TorahAnnotationMaterializationPurpose,
        attempt: TorahAnnotationNativeCreateAttempt?,
        mapping: TorahAnnotationNativeIdentity?,
        candidates: [TorahAnnotationNativeCandidate],
        annotationTypeID: String,
        ownerIsCurrent: Bool
    ) -> TorahAnnotationCreateRecoveryAssessment {
        guard ownerIsCurrent else { return .ownerUnavailable }
        guard purpose == .annotation else { return .notMaterializable }
        guard TorahAnnotationNativeValidation.identifier(annotationTypeID) else {
            return .conflict(.invalidAnnotationType)
        }
        if let attempt, attempt.commitment != commitment {
            return .conflict(.pendingCommitmentMismatch)
        }
        if let mapping, mapping.scope != commitment.scope {
            return .conflict(.scopeMismatch)
        }
        for candidate in candidates {
            if let conflict = identityConflict(candidate, scope: commitment.scope,
                                               annotationTypeID: annotationTypeID) {
                return .conflict(conflict)
            }
        }
        // Repeated IDs are also ambiguous input, not evidence of one object.
        guard candidates.count <= 1 else { return .conflict(.ambiguousCandidates) }

        var known = mapping
        if let attempt, case let .nativeObjectObserved(id) = attempt.dispatchState {
            if let known, known.objectID != id { return .conflict(.objectIdentityMismatch) }
            do { known = try TorahAnnotationNativeIdentity(scope: commitment.scope, objectID: id) }
            catch { return .conflict(.objectIdentityMismatch) }
        }
        if let known {
            if let candidate = candidates.first, candidate.identity != known {
                return .conflict(.objectIdentityMismatch)
            }
            // An empty index query cannot erase a known mapping. Read the
            // original object directly; missing/deleted/denied means no replacement.
            return .verifyExistingObject(known)
        }
        if let candidate = candidates.first {
            guard candidate.creationCommitment == commitment else {
                return .conflict(.pendingCommitmentMismatch)
            }
            if let attempt, candidate.creationAttemptID != attempt.attemptID {
                return .conflict(.creationAttemptMismatch)
            }
            return .verifyExistingObject(candidate.identity)
        }
        if let attempt, case .mayHaveDispatched = attempt.dispatchState {
            // Heart can create the native tree even if index publication fails.
            // No query count/timeout makes this a safe second ObjectCreate.
            return .creationUncertain
        }
        // The consumer must durably reserve this exact commitment/attempt and
        // record mayHaveDispatched BEFORE the independently authorized first call.
        return .prepareFirstCreate
    }

    public static func assessIdentity(
        commitment: TorahAnnotationNativeCommitment,
        expectedIdentity: TorahAnnotationNativeIdentity,
        candidate: TorahAnnotationNativeCandidate,
        annotationTypeID: String,
        ownerIsCurrent: Bool
    ) -> TorahAnnotationIdentityAssessment {
        guard ownerIsCurrent else { return .ownerUnavailable }
        guard expectedIdentity.scope == commitment.scope else {
            return .conflict(.scopeMismatch)
        }
        if let conflict = identityConflict(candidate, scope: commitment.scope,
                                           annotationTypeID: annotationTypeID) {
            return .conflict(conflict)
        }
        guard candidate.identity == expectedIdentity else {
            return .conflict(.objectIdentityMismatch)
        }
        return .identityMatches(candidate.identity)
    }

    public static func assessApplied(
        commitment: TorahAnnotationNativeCommitment,
        expectedIdentity: TorahAnnotationNativeIdentity,
        candidate: TorahAnnotationNativeCandidate,
        annotationTypeID: String,
        ownerIsCurrent: Bool
    ) -> TorahAnnotationAppliedAssessment {
        switch assessIdentity(commitment: commitment, expectedIdentity: expectedIdentity,
                              candidate: candidate, annotationTypeID: annotationTypeID,
                              ownerIsCurrent: ownerIsCurrent) {
        case .ownerUnavailable: return .ownerUnavailable
        case let .conflict(reason): return .conflict(reason)
        case .identityMatches: break
        }
        guard let applied = candidate.appliedCommitment else { return .bodyApplicationUnproven }
        guard applied.scope == commitment.scope else { return .conflict(.scopeMismatch) }
        guard applied.revision >= commitment.revision else {
            return .conflict(.staleAppliedExchangeRevision)
        }
        guard applied.revision <= commitment.revision else {
            return .conflict(.newerAppliedExchangeRevision)
        }
        guard applied.payloadDigest == commitment.payloadDigest else {
            return .conflict(.appliedPayloadMismatch)
        }
        guard applied.sourceDigest == commitment.sourceDigest else {
            return .conflict(.appliedSourceMismatch)
        }
        guard applied.messageID == commitment.messageID && applied.mutationID == commitment.mutationID else {
            return .conflict(.appliedMessageMismatch)
        }
        // nativeSnapshotDigest is caller-constructible observation data. Its
        // presence (or equality to another supplied digest) does not compare
        // an authentic complete native body with this intended application.
        return .bodyApplicationUnproven
    }

    private static func identityConflict(
        _ candidate: TorahAnnotationNativeCandidate,
        scope: TorahAnnotationNativeScope,
        annotationTypeID: String
    ) -> TorahAnnotationRecoveryConflict? {
        guard TorahAnnotationNativeValidation.identifier(annotationTypeID) else {
            return .invalidAnnotationType
        }
        guard candidate.identity.scope == scope,
              candidate.creationCommitment.scope == scope else { return .scopeMismatch }
        guard candidate.objectState == .present else { return .nativeObjectUnavailable }
        guard candidate.classification == .annotation else {
            return .promotionRequiresExplicitResolution
        }
        guard candidate.nativeTypeID == annotationTypeID else { return .annotationTypeMismatch }
        return nil
    }
}

