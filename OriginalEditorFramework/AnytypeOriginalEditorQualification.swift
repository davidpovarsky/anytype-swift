#if DEBUG && targetEnvironment(simulator)
import Foundation
import CryptoKit
import Services
import ProtobufMessages
import SwiftProtobuf

/// The real persistence owner supplies these fields from its current snapshot.
/// This descriptor cannot select an account, Space or native object.
@_spi(OriginalEditorQualification)
public struct AnytypeOriginalEditorQualificationSource: Sendable, Equatable {
    public let hostProfileID: String
    public let annotationUUID: UUID
    public let expectedRevision: Int64
    public let sourceWitnessSHA256: String

    public init(hostProfileID: String, annotationUUID: UUID, expectedRevision: Int64,
                sourceWitnessSHA256: String) throws {
        guard !hostProfileID.isEmpty, !hostProfileID.utf8.contains(0), expectedRevision >= 0,
              sourceWitnessSHA256.utf8.count == 64,
              sourceWitnessSHA256.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            throw AnytypeOriginalEditorHostError.invalidBinding
        }
        self.hostProfileID = hostProfileID
        self.annotationUUID = annotationUUID
        self.expectedRevision = expectedRevision
        self.sourceWitnessSHA256 = sourceWitnessSHA256
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.hostProfileID.utf8.elementsEqual(rhs.hostProfileID.utf8)
            && lhs.annotationUUID == rhs.annotationUUID
            && lhs.expectedRevision == rhs.expectedRevision
            && lhs.sourceWitnessSHA256 == rhs.sourceWitnessSHA256
    }

    fileprivate func binding(accountID: String, spaceID: String, objectID: String) throws -> AnytypeOriginalEditorBinding {
        try AnytypeOriginalEditorBinding(
            accountID: accountID, spaceID: spaceID, objectID: objectID,
            hostProfileID: hostProfileID, annotationUUID: annotationUUID,
            expectedRevision: expectedRevision, sourceWitnessSHA256: sourceWitnessSHA256
        )
    }
}


@_spi(OriginalEditorQualification)
public struct AnytypeOriginalEditorProcessResumeContext: Sendable, Equatable {
    public let workspaceNamespace: UUID
    public let legacyAnnotationID: Int64
    public let payloadDigest: String

    public init(workspaceNamespace: UUID, legacyAnnotationID: Int64,
                payloadDigest: String) throws {
        guard legacyAnnotationID > 0, payloadDigest.utf8.count == 64,
              payloadDigest.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            throw AnytypeOriginalEditorHostError.invalidBinding
        }
        self.workspaceNamespace = workspaceNamespace
        self.legacyAnnotationID = legacyAnnotationID
        self.payloadDigest = payloadDigest
    }
}

@_spi(OriginalEditorQualification)
public struct AnytypeOriginalEditorProcessResumeReceipt: Sendable {
    public let runtimeNonce: UUID
    public let accountID: String
    public let spaceID: String
    public let objectID: String
    public let preparedProcessID: Int32
    public let currentProcessID: Int32
    public let credentialConsumed: Bool
}

@_spi(OriginalEditorQualification)
public enum AnytypeOriginalEditorQualificationError: Error, Sendable {
    case sourceChanged, wrongSnapshot, alreadyRestored, nativeIdentityMissing
    case fidelityFixtureNotSelected, restoreNotPrepared
}

/// Retains actual original runtime/Space authority. No public initializer can
/// turn an arbitrary account or Space string into a qualification capability.
@_spi(OriginalEditorQualification)
@MainActor
public final class AnytypeOriginalEditorQualificationSession {
    public let binding: AnytypeOriginalEditorBinding
    public let retainedSourceEvidenceDirectory: URL
    public private(set) var retainedImportEvidenceDirectory: URL?
    public private(set) var processResumeReceipt: AnytypeOriginalEditorProcessResumeReceipt?

    private let runtime: OwnedOriginalEditorQualificationRuntime
    private let initialSource: AnytypeOriginalEditorQualificationSource
    private let fidelityFixture: AnytypeOriginalEditorNativeFixture?
    private var restoreConsumed = false
    private var restoreSpace: OwnedQualificationSpace?
    private var importedCandidate: AnytypeOriginalEditorImportedCandidate?
    private var currentImportedSource: AnytypeOriginalEditorQualificationSource?
    private var currentImportedBodySHA256: String?

    fileprivate init(runtime: OwnedOriginalEditorQualificationRuntime,
                     source: AnytypeOriginalEditorQualificationSource,
                     binding: AnytypeOriginalEditorBinding,
                     evidence: URL,
                     fidelityFixture: AnytypeOriginalEditorNativeFixture?,
                     processResumeReceipt: AnytypeOriginalEditorProcessResumeReceipt? = nil) {
        self.runtime = runtime
        initialSource = source
        self.binding = binding
        retainedSourceEvidenceDirectory = evidence
        self.fidelityFixture = fidelityFixture
        self.processResumeReceipt = processResumeReceipt
        restoreConsumed = processResumeReceipt != nil
    }

    /// The caller first reads its CURRENT durable row. The snapshot's capture
    /// revision is retained as history; it is never adopted as current authority.
    /// The returned object ID is proven by the original completed native import.
    public func prepareReopen(
        snapshot: AnytypeOriginalEditorSnapshot,
        currentSource: AnytypeOriginalEditorQualificationSource,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorQualificationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorBinding {
        try runtime.validateCurrentRuntime()
        try Task.checkCancellation()
        guard currentSource.hostProfileID.utf8.elementsEqual(initialSource.hostProfileID.utf8),
              currentSource.annotationUUID == initialSource.annotationUUID,
              currentSource.expectedRevision >= initialSource.expectedRevision,
              snapshot.provenance.matchesCaptureBinding(binding) else {
            throw AnytypeOriginalEditorQualificationError.wrongSnapshot
        }
        // A real annotation CAS changes row fields included in its source
        // witness. Historical capture provenance still matches the original
        // binding above; only the freshly read row and callback authorize the
        // returned binding's current revision and source witness.
        guard sourceIsCurrent(currentSource) else {
            throw AnytypeOriginalEditorQualificationError.sourceChanged
        }
        guard !restoreConsumed else { throw AnytypeOriginalEditorQualificationError.alreadyRestored }
        restoreConsumed = true
        let target = try await runtime.makeRestoreSpace()
        restoreSpace = target
        guard sourceIsCurrent(currentSource) else {
            throw AnytypeOriginalEditorQualificationError.sourceChanged
        }
        let candidate = try await AnytypeOriginalEditorRestoreQualification.importCandidate(
            snapshot: snapshot, into: target
        )
        importedCandidate = candidate
        retainedImportEvidenceDirectory = candidate.retainedEvidenceDirectory
        try Task.checkCancellation()
        try runtime.validateCurrentRuntime()
        guard sourceIsCurrent(currentSource) else {
            throw AnytypeOriginalEditorQualificationError.sourceChanged
        }
        let result = try currentSource.binding(
            accountID: candidate.accountID, spaceID: candidate.spaceID, objectID: candidate.objectID
        )
        currentImportedSource = currentSource
        currentImportedBodySHA256 = SHA256.hash(data: snapshot.bodyBytes)
            .map { String(format: "%02x", $0) }.joined()
        return result
    }


    public func prepareProcessResume(
        host: AnytypeOriginalEditorHost,
        snapshot: AnytypeOriginalEditorSnapshot,
        currentSource: AnytypeOriginalEditorQualificationSource,
        context: AnytypeOriginalEditorProcessResumeContext,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorQualificationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorProcessResumeReceipt {
        var beganCapture = false
        do {
            guard let importedCandidate else {
                throw AnytypeOriginalEditorQualificationError.wrongSnapshot
            }
            let expected = try currentSource.binding(
                accountID: importedCandidate.accountID, spaceID: importedCandidate.spaceID,
                objectID: importedCandidate.objectID
            )
            guard host.binding == expected else {
                throw AnytypeOriginalEditorQualificationError.wrongSnapshot
            }
            try host.validateCurrentSource()
            try host.beginSnapshotCapture()
            beganCapture = true
            let receipt = try await host.preparedSession.owner.withExclusiveRead(
                contextId: expected.objectID, spaceId: expected.spaceID,
                rpcNames: [], retireOnSuccess: true
            ) {
                try await self.sealProcessResume(
                    snapshot: snapshot, currentSource: currentSource,
                    context: context, sourceIsCurrent: sourceIsCurrent
                )
            }
            host.completeSnapshotCapture()
            return receipt
        } catch {
            if beganCapture { host.failSnapshotCapture() }
            let failure = await runtime.preservingProcessResumeCleanupFailure(error)
            throw failure
        }
    }

    private func sealProcessResume(
        snapshot: AnytypeOriginalEditorSnapshot,
        currentSource: AnytypeOriginalEditorQualificationSource,
        context: AnytypeOriginalEditorProcessResumeContext,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorQualificationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorProcessResumeReceipt {
        try runtime.validateCurrentRuntime()
        try Task.checkCancellation()
        guard let currentImportedSource, currentImportedSource == currentSource,
              let currentImportedBodySHA256,
              currentImportedBodySHA256 == SHA256.hash(data: snapshot.bodyBytes)
                .map({ String(format: "%02x", $0) }).joined(),
              let importedCandidate, let restoreSpace,
              importedCandidate.accountID.utf8.elementsEqual(runtime.accountID.utf8),
              importedCandidate.spaceID.utf8.elementsEqual(restoreSpace.spaceID.utf8),
              sourceIsCurrent(currentSource) else {
            throw AnytypeOriginalEditorQualificationError.wrongSnapshot
        }
        let request = try OriginalEditorQualificationResumeRequest(
            source: currentSource, context: context, snapshot: snapshot
        )
        let receipt = try await runtime.prepareProcessResume(
            request: request, space: restoreSpace, objectID: importedCandidate.objectID
        )
        guard sourceIsCurrent(currentSource) else {
            throw AnytypeOriginalEditorQualificationError.sourceChanged
        }
        processResumeReceipt = receipt
        return receipt
    }

    /// Independent rich-engine fidelity evidence only. The caller must have
    /// reopened/mounted the returned Host; UI typing and persistence CAS have
    /// their own acceptance witnesses and are not inferred from this fixture.
    public func verifyFidelityAfterReopen(host: AnytypeOriginalEditorHost) async throws -> URL {
        guard let fidelityFixture else {
            throw AnytypeOriginalEditorQualificationError.fidelityFixtureNotSelected
        }
        guard let importedCandidate, let restoreSpace else {
            throw AnytypeOriginalEditorQualificationError.restoreNotPrepared
        }
        return try await AnytypeOriginalEditorNativeFixtureBuilder.verifyAfterReopen(
            candidate: importedCandidate, fixture: fidelityFixture, host: host, in: restoreSpace
        )
    }
}

extension AnytypeOriginalEditorModule {

    @_spi(OriginalEditorQualification)
    @MainActor
    public static func cleanupOwnedProcessResumeCredential() async throws -> Bool {
        try await OwnedOriginalEditorQualificationRuntime.cleanupOwnedProcessResumeCredential()
    }


    @_spi(OriginalEditorQualification)
    @MainActor
    public static func resumeEditableAcceptance(
        source: AnytypeOriginalEditorQualificationSource,
        snapshot: AnytypeOriginalEditorSnapshot,
        context: AnytypeOriginalEditorProcessResumeContext,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorQualificationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorQualificationSession {
        try Task.checkCancellation()
        guard sourceIsCurrent(source) else {
            throw AnytypeOriginalEditorQualificationError.sourceChanged
        }
        let request = try OriginalEditorQualificationResumeRequest(
            source: source, context: context, snapshot: snapshot
        )
        let runtime = try await OwnedOriginalEditorQualificationRuntime.resumeLocalOnlyAcceptance(request: request)
        do {
            try Task.checkCancellation()
            try runtime.validateCurrentRuntime()
            guard sourceIsCurrent(source),
                  let checkpoint = runtime.recoveredCheckpoint,
                  checkpoint.request == request,
                  let evidence = runtime.recoveredEvidenceDirectory,
                  let receipt = runtime.processResumeReceipt, receipt.credentialConsumed else {
                throw AnytypeOriginalEditorQualificationError.sourceChanged
            }
            let binding = try source.binding(
                accountID: runtime.accountID, spaceID: checkpoint.spaceID, objectID: checkpoint.objectID
            )
            let session = AnytypeOriginalEditorQualificationSession(
                runtime: runtime, source: source, binding: binding, evidence: evidence,
                fidelityFixture: nil, processResumeReceipt: receipt
            )
            return session
        } catch {
            let failure = await runtime.preservingProcessResumeCleanupFailure(error)
            throw failure
        }
    }

    /// A fresh real page with no seeded editor text. Native acceptance must type
    /// and commit its two blocks through the actual original editor UI.
    @_spi(OriginalEditorQualification)
    @MainActor
    public static func beginEditableAcceptance(
        source: AnytypeOriginalEditorQualificationSource,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorQualificationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorQualificationSession {
        try await beginOriginalAcceptance(source: source, richFixture: false, sourceIsCurrent: sourceIsCurrent)
    }

    /// A separate original-engine fixture for exact marks/links/file fidelity.
    /// Its seeded native writes are never evidence of UI typing.
    @_spi(OriginalEditorQualification)
    @MainActor
    public static func beginFidelityAcceptance(
        source: AnytypeOriginalEditorQualificationSource,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorQualificationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorQualificationSession {
        try await beginOriginalAcceptance(source: source, richFixture: true, sourceIsCurrent: sourceIsCurrent)
    }

    @MainActor
    private static func beginOriginalAcceptance(
        source: AnytypeOriginalEditorQualificationSource,
        richFixture: Bool,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorQualificationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorQualificationSession {
        try Task.checkCancellation()
        guard sourceIsCurrent(source) else { throw AnytypeOriginalEditorQualificationError.sourceChanged }
        let runtime = try await OwnedOriginalEditorQualificationRuntime.createLocalOnlyAcceptance()
        do {
            guard sourceIsCurrent(source) else { throw AnytypeOriginalEditorQualificationError.sourceChanged }
            let space = try await runtime.makeFixtureSpace()
            guard sourceIsCurrent(source) else { throw AnytypeOriginalEditorQualificationError.sourceChanged }
            let objectID: String
            let evidence: URL
            let fixture: AnytypeOriginalEditorNativeFixture?
            if richFixture {
                let created = try await AnytypeOriginalEditorNativeFixtureBuilder.create(in: space)
                objectID = created.objectID
                evidence = created.retainedEvidenceDirectory
                fixture = created
            } else {
                try space.claimForFixture()
                let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
                let spaceID = space.spaceID
                objectID = try await space.performRPCs(rpcNames: ["ObjectCreate", "ObjectShow"]) {
                    let created = try await ClientCommands.objectCreate(.with {
                        $0.spaceID = spaceID
                        $0.objectTypeUniqueKey = ObjectTypeUniqueKey.page.value
                        $0.details = .with { $0.fields["name"] = .with { $0.stringValue = "" } }
                        // No delete-empty, select-type or select-template flags.
                    }).invoke()
                    try created.serializedData().write(
                        to: directory.appendingPathComponent("original-empty-page-create.pb"),
                        options: .withoutOverwriting
                    )
                    guard !created.objectID.isEmpty, created.hasDetails,
                          created.details.fields["id"]?.stringValue.utf8.elementsEqual(created.objectID.utf8) == true,
                          created.details.fields["spaceId"]?.stringValue.utf8.elementsEqual(spaceID.utf8) == true else {
                        throw AnytypeOriginalEditorQualificationError.nativeIdentityMissing
                    }
                    let shown = try await ClientCommands.objectShow(.with {
                        $0.contextID = created.objectID
                        $0.objectID = created.objectID
                        $0.spaceID = spaceID
                    }).invoke()
                    try shown.serializedData().write(
                        to: directory.appendingPathComponent("original-empty-page-show.pb"),
                        options: .withoutOverwriting
                    )
                    guard shown.hasObjectView,
                          shown.objectView.rootID.utf8.elementsEqual(created.objectID.utf8) else {
                        throw AnytypeOriginalEditorQualificationError.nativeIdentityMissing
                    }
                    let rootDetails = shown.objectView.details.filter {
                        $0.id.utf8.elementsEqual(created.objectID.utf8)
                    }
                    guard rootDetails.count == 1, rootDetails[0].hasDetails,
                          rootDetails[0].details.fields["id"]?.stringValue.utf8.elementsEqual(created.objectID.utf8) == true,
                          rootDetails[0].details.fields["spaceId"]?.stringValue.utf8.elementsEqual(spaceID.utf8) == true else {
                        throw AnytypeOriginalEditorQualificationError.nativeIdentityMissing
                    }
                    return created.objectID
                }
                evidence = directory
                fixture = nil
            }
            try Task.checkCancellation()
            try runtime.validateCurrentRuntime()
            guard sourceIsCurrent(source) else { throw AnytypeOriginalEditorQualificationError.sourceChanged }
            let binding = try source.binding(accountID: runtime.accountID, spaceID: space.spaceID, objectID: objectID)
            return AnytypeOriginalEditorQualificationSession(
                runtime: runtime, source: source, binding: binding, evidence: evidence, fidelityFixture: fixture
            )
        } catch {
            let failure = await runtime.preservingProcessResumeCleanupFailure(error)
            throw failure
        }
    }
}
#endif
