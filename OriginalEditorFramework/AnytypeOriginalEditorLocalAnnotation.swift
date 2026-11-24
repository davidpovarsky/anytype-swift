import Foundation
import UIKit
import CryptoKit

/// The captured canonical Otzaria row. These values are data, not permission to
/// select an account, create a remote object, or acknowledge an exchange.
public struct AnytypeOriginalEditorLocalAnnotationSource: Sendable, Equatable {
    public let hostProfileID: String
    public let annotationUUID: UUID
    public let expectedRevision: Int64
    public let sourceWitnessSHA256: String
    public let payloadSHA256: String?

    public init(hostProfileID: String, annotationUUID: UUID, expectedRevision: Int64,
                sourceWitnessSHA256: String, payloadSHA256: String?) throws {
        guard !hostProfileID.isEmpty, hostProfileID.utf8.count <= 512,
              !hostProfileID.utf8.contains(0), expectedRevision >= 0,
              OriginalEditorLocalAnnotationValidation.digest(sourceWitnessSHA256),
              payloadSHA256.map(OriginalEditorLocalAnnotationValidation.digest) ?? true else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidSource
        }
        self.hostProfileID = hostProfileID
        self.annotationUUID = annotationUUID
        self.expectedRevision = expectedRevision
        self.sourceWitnessSHA256 = sourceWitnessSHA256
        self.payloadSHA256 = payloadSHA256
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.hostProfileID.utf8.elementsEqual(rhs.hostProfileID.utf8)
            && lhs.annotationUUID == rhs.annotationUUID
            && lhs.expectedRevision == rhs.expectedRevision
            && lhs.sourceWitnessSHA256.utf8.elementsEqual(rhs.sourceWitnessSHA256.utf8)
            && lhs.payloadSHA256 == rhs.payloadSHA256
    }
}

/// A plain saved note is seeded through original native block commands. A rich
/// body is the original opaque snapshot decoded from the canonical SQLite row.
/// This local lifecycle supports a body's original Host profile and increasing
/// local row revisions. Cross-profile/device transport with rebased revisions
/// requires a separate canonical transport admission and is rejected here;
/// historical native provenance and creation markers are never relabelled.
public enum AnytypeOriginalEditorLocalAnnotationBody: Sendable {
    case plainText(String)
    case nativeSnapshot(AnytypeOriginalEditorSnapshot)
}

public enum AnytypeOriginalEditorLocalAnnotationError: Error, Sendable, Equatable {
    case invalidSource, retiredSource, sourceAlreadyUsed, canonicalBodyMismatch
    case unsupportedBody, runtimeAlreadyOwned, originalServiceUnavailable
    case incompatibleDeployment, foreignRepository, invalidJournal
    case missingCredential, uncertainNativeOperation, unavailableAccount
    case unavailableSpace, unobservedSchema, wrongNativeIdentity
    case invalidNativeImport, overlappingSession, alreadyMounted, captureAlreadyAttempted
    case invalidPreview, storageFailure(Int32)
}

/// Bind this one-use token to the original Host DB/session/presentation lifetimes
/// before the factory await. Retirement is safe while the Host mutex is held.
@MainActor
public final class AnytypeOriginalEditorLocalAnnotationSourceLifetime {
    public nonisolated let source: AnytypeOriginalEditorLocalAnnotationSource
    internal nonisolated let lifetime = EditorDocumentWriteLifetime()
    private var claimed = false

    public init(source: AnytypeOriginalEditorLocalAnnotationSource) { self.source = source }
    public nonisolated var isCurrent: Bool { lifetime.token() != nil }

    public nonisolated func retire() {
        guard let deliver = lifetime.markUnavailableDeferringObservers() else { return }
        // No callback, I/O or native operation runs on the retiring Host stack.
        Task { @MainActor in deliver() }
    }

    internal func claim() throws {
        guard isCurrent else { throw AnytypeOriginalEditorLocalAnnotationError.retiredSource }
        guard !claimed else { throw AnytypeOriginalEditorLocalAnnotationError.sourceAlreadyUsed }
        claimed = true
    }

    deinit { retire() }
}

/// A secondary preview from the SAME flushed original primary-object export.
/// Only nativeCapture.snapshot.bodyBytes is the complete canonical rich body.
public struct AnytypeOriginalEditorLocalAnnotationCapture: Sendable {
    public let nativeCapture: AnytypeOriginalEditorSnapshotCapture
    public let textPreview: String

    internal init(nativeCapture: AnytypeOriginalEditorSnapshotCapture, textPreview: String) {
        self.nativeCapture = nativeCapture
        self.textPreview = textPreview
    }
}

/// A private localOnly native draft. This is never an AnyTapy destination mapping
/// or a committed document. The Host's original SQLite CAS remains Save.
@MainActor
public final class AnytypeOriginalEditorLocalAnnotationSession {
    public let binding: AnytypeOriginalEditorBinding
    private let owner: OriginalEditorLocalAnnotationDraftOwner
    private nonisolated let sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime

    internal init(owner: OriginalEditorLocalAnnotationDraftOwner) {
        self.owner = owner
        binding = owner.host.binding
        sourceLifetime = owner.sourceLifetime
    }

    public func makeViewController() throws -> UIViewController {
        try owner.validateCurrent()
        return try owner.host.makeViewController()
    }

    public func captureNativeSnapshot(maximumBodyBytes: Int) async throws
        -> AnytypeOriginalEditorLocalAnnotationCapture {
        try await owner.capture(maximumBodyBytes: maximumBodyBytes)
    }

    public func retire() { owner.retire() }
    deinit { sourceLifetime.retire() }
}

extension AnytypeOriginalEditorModule {
    /// Opens only an app-owned localOnly draft, reconstructed from the captured
    /// canonical row. No caller-selected account, Space, object or path is accepted.
    /// This is local editing only: it creates neither a remote destination nor
    /// an exchange acknowledgement. It deliberately rejects transported rich
    /// bodies whose historical profile/revision has no admitted local lineage.
    @MainActor
    public static func openLocalAnnotation(
        appGroup: String,
        sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
        body: AnytypeOriginalEditorLocalAnnotationBody,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorLocalAnnotationSession {
        try sourceLifetime.claim()
        do {
            try Task.checkCancellation()
            guard sourceIsCurrent(sourceLifetime.source) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
            let canonical = try OriginalEditorLocalAnnotationCanonical(
                source: sourceLifetime.source, body: body
            )
            let runtime = try await OriginalEditorLocalAnnotationRuntime.acquire(appGroup: appGroup)
            let owner = try await runtime.open(
                sourceLifetime: sourceLifetime, canonical: canonical,
                sourceIsCurrent: sourceIsCurrent
            )
            return AnytypeOriginalEditorLocalAnnotationSession(owner: owner)
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }
}

internal enum OriginalEditorLocalAnnotationValidation {
    static func digest(_ text: String) -> Bool {
        text.utf8.count == 64 && text.utf8.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
    }

    static func sha256(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
}

internal struct OriginalEditorLocalAnnotationCanonical: Sendable {
    let body: AnytypeOriginalEditorLocalAnnotationBody
    let digest: String

    init(source: AnytypeOriginalEditorLocalAnnotationSource,
         body: AnytypeOriginalEditorLocalAnnotationBody) throws {
        switch body {
        case .plainText(let text):
            // A saved plain note may already have a versioned plain envelope.
            // Its Host payload digest is still part of the current row witness;
            // it does not imply that the envelope contains a rich native body.
            guard !text.utf8.contains(0), text.utf8.count <= 1_048_576 else {
                throw AnytypeOriginalEditorLocalAnnotationError.canonicalBodyMismatch
            }
            digest = OriginalEditorLocalAnnotationValidation.sha256(Data(text.utf8))
        case .nativeSnapshot(let snapshot):
            guard source.payloadSHA256 != nil,
                  snapshot.provenance.annotationUUID == source.annotationUUID,
                  snapshot.provenance.hostProfileID.utf8.elementsEqual(source.hostProfileID.utf8),
                  snapshot.provenance.capturedAgainstRevision < source.expectedRevision else {
                throw AnytypeOriginalEditorLocalAnnotationError.canonicalBodyMismatch
            }
            // Native provenance is historical. The current account/Space is
            // independently acquired below; historical IDs never select it.
            try OriginalEditorLocalAnnotationNativeBody.requireAnnotation(snapshot, source: source)
            digest = OriginalEditorLocalAnnotationValidation.sha256(snapshot.bodyBytes)
        }
        self.body = body
    }
}
