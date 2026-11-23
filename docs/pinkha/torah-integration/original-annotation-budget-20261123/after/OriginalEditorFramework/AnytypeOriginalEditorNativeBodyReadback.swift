import Foundation
import CryptoKit
import PinkhaKit
import ProtobufMessages
import SwiftProtobuf

/// A historical comparison of a real original export obtained while the exact
/// Host/Owner remained admitted. The original exporter visits objects in separate
/// native tasks, and inbound native edits can occur during that visit. This value
/// therefore grants no live-body, whole-graph atomicity, mapping, COMMIT or ACK
/// authority. It has no public initializer, mutable state, Codable or restore path.
internal struct OriginalAnnotationHistoricalBodyComparison: Sendable {
    let identity: TorahAnnotationNativeIdentity
    let observedAppliedCommitment: TorahAnnotationNativeCommitment
    let bodyFormatVersion: Int64
    let historicalCapturedAgainstRevision: Int64
    let intendedBodySHA256: String
    let capturedArchiveSHA256: String
    let capturedNativeArchiveBytes: Data
    let capturedNativeReportBytes: Data
    let capturedObjectIDs: [String]
    let capturedFilePaths: [String]
    let retainedCaptureDirectoryURL: URL

    fileprivate init(identity: TorahAnnotationNativeIdentity,
                     observedAppliedCommitment: TorahAnnotationNativeCommitment,
                     intended: AnytypeOriginalEditorSnapshot, nativeArchive: Data,
                     nativeReport: Data, comparison: OriginalAnnotationNativeArchiveComparison,
                     directory: URL) {
        self.identity = identity
        self.observedAppliedCommitment = observedAppliedCommitment
        bodyFormatVersion = comparison.formatVersion
        historicalCapturedAgainstRevision = intended.provenance.capturedAgainstRevision
        intendedBodySHA256 = Self.digest(intended.bodyBytes)
        capturedArchiveSHA256 = Self.digest(nativeArchive)
        capturedNativeArchiveBytes = nativeArchive
        capturedNativeReportBytes = nativeReport
        capturedObjectIDs = comparison.objectIDs
        capturedFilePaths = comparison.filePaths
        retainedCaptureDirectoryURL = directory
    }

    private static func digest(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
}

internal struct OriginalAnnotationHistoricalBodyReadbackFailure: Error {
    let retainedCaptureDirectoryURL: URL
    let underlyingError: any Error
}

internal enum OriginalAnnotationHistoricalBodyReadbackError: Error, Sendable, Equatable {
    case wrongBinding
    case unsupportedBodyFormat
    case wrongProvenance
    case nativeIdentityMismatch
    case appliedCommitmentMismatch
    case metadataChangedDuringRead
    case incompleteNativeExport
}

extension AnytypeOriginalEditorHost {
    /// A downstream production prerequisite, intentionally internal until the
    /// durable delivery/materialization composition supplies its own closed
    /// source/commit boundary. It neither creates nor restores any native object.
    @MainActor
    internal func withHistoricalAnnotationBodyComparison<Value: Sendable>(
        intendedBodyBytes: Data,
        intendedBodyFormat: String,
        intendedBodyFormatVersion: Int64,
        expectedIdentity: TorahAnnotationNativeIdentity,
        commitment: TorahAnnotationNativeCommitment,
        annotationTypeID: String,
        consume: @MainActor @Sendable (OriginalAnnotationHistoricalBodyComparison) throws -> Value
    ) async throws -> OriginalAnnotationHeldReadOutcome<Value> {
        try validateCurrentSource()
        guard expectedIdentity.scope == commitment.scope,
              expectedIdentity.objectID.utf8.elementsEqual(binding.objectID.utf8),
              expectedIdentity.scope.account.utf8.elementsEqual(binding.accountID.utf8),
              expectedIdentity.scope.space.utf8.elementsEqual(binding.spaceID.utf8),
              expectedIdentity.scope.annotationUUID == binding.annotationUUID,
              commitment.sourceDigest.utf8.elementsEqual(binding.sourceWitnessSHA256.utf8) else {
            throw OriginalAnnotationHistoricalBodyReadbackError.wrongBinding
        }
        guard intendedBodyFormat.utf8.elementsEqual(AnytypeOriginalEditorSnapshot.format.utf8),
              intendedBodyFormatVersion == AnytypeOriginalEditorSnapshot.formatVersion else {
            throw OriginalAnnotationHistoricalBodyReadbackError.unsupportedBodyFormat
        }
        let intended = try AnytypeOriginalEditorSnapshot(
            bodyBytes: intendedBodyBytes, maximumBodyBytes: OriginalAnnotationPayloadBudget.maximumBodyBytes
        )
        let provenance = intended.provenance
        guard provenance.accountID.utf8.elementsEqual(binding.accountID.utf8),
              provenance.spaceID.utf8.elementsEqual(binding.spaceID.utf8),
              provenance.objectID.utf8.elementsEqual(binding.objectID.utf8),
              provenance.hostProfileID.utf8.elementsEqual(binding.hostProfileID.utf8),
              provenance.annotationUUID == binding.annotationUUID,
              provenance.sourceWitnessSHA256.utf8.elementsEqual(commitment.sourceDigest.utf8) else {
            throw OriginalAnnotationHistoricalBodyReadbackError.wrongProvenance
        }
        // capturedAgainstRevision is retained historical provenance. It is not
        // reinterpreted as the current exchange revision or current source CAS.
        let expected = try OriginalAnnotationNativeArchiveComparison(
            archiveBytes: intended.nativeArchiveBytes, rootID: binding.objectID,
            spaceID: binding.spaceID, formatVersion: intendedBodyFormatVersion,
            reportedObjectCount: intended.exportedObjectCount
        )
        let adapter = try OriginalAnnotationObjectReadback.bindExistingOriginal(
            session: preparedSession, requestedIdentity: expectedIdentity
        )
        let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        do {
            return try await adapter.withFreshNativeArchiveObservation(
                ownedArchiveDirectory: directory
            ) { [self] observation in
                try validateCurrentSource()
                let exported = observation.exportResponse
                guard exported.hasReport else {
                    throw OriginalAnnotationHistoricalBodyReadbackError.incompleteNativeExport
                }
                let reportBytes = try exported.report.serializedData()
                guard exported.report.status == .success, exported.succeed > 0,
                      exported.report.succeed == exported.succeed,
                      exported.report.objectErrors == 0, exported.report.fileErrors == 0,
                      exported.report.issues.isEmpty else {
                    throw OriginalAnnotationHistoricalBodyReadbackError.incompleteNativeExport
                }
                let archiveBytes = try OriginalEditorArchiveFiles.readArchive(
                    URL(fileURLWithPath: exported.path), in: directory,
                    maximumBytes: OriginalAnnotationPayloadBudget.maximumArchiveBytes
                )
                let actual = try OriginalAnnotationNativeArchiveComparison(
                    archiveBytes: archiveBytes, rootID: binding.objectID, spaceID: binding.spaceID,
                    formatVersion: intendedBodyFormatVersion, reportedObjectCount: exported.succeed
                )
                let native = try OriginalAnnotationNativeMetadata.decode(
                    actual.rootSnapshot.details, rootID: binding.objectID
                )
                let before = try OriginalAnnotationNativeMetadata.decode(
                    observation.before.rootDetails, rootID: binding.objectID
                )
                let after = try OriginalAnnotationNativeMetadata.decode(
                    observation.after.rootDetails, rootID: binding.objectID
                )
                guard before == native, after == native else {
                    throw OriginalAnnotationHistoricalBodyReadbackError.metadataChangedDuringRead
                }
                guard case .identityMatches(let identity) = TorahAnnotationCreateRecovery.assessIdentity(
                    commitment: commitment, expectedIdentity: expectedIdentity, candidate: native,
                    annotationTypeID: annotationTypeID, ownerIsCurrent: true
                ), identity == expectedIdentity else {
                    throw OriginalAnnotationHistoricalBodyReadbackError.nativeIdentityMismatch
                }
                guard let applied = native.appliedCommitment, applied == commitment else {
                    throw OriginalAnnotationHistoricalBodyReadbackError.appliedCommitmentMismatch
                }
                try expected.requireEqual(to: actual)
                try validateCurrentSource()
                let comparison = OriginalAnnotationHistoricalBodyComparison(
                    identity: expectedIdentity, observedAppliedCommitment: applied,
                    intended: intended, nativeArchive: archiveBytes, nativeReport: reportBytes,
                    comparison: actual, directory: directory
                )
                // Synchronous consumption is still inside the same original
                // Owner barrier. The adapter retains post-consumption owner loss
                // in completedWithoutCurrentOwnership instead of hiding a result.
                return try consume(comparison)
            }
        } catch {
            throw OriginalAnnotationHistoricalBodyReadbackFailure(
                retainedCaptureDirectoryURL: directory, underlyingError: error
            )
        }
    }
}
