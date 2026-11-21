#if DEBUG && targetEnvironment(simulator)
import Foundation
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

    private let runtime: OwnedOriginalEditorQualificationRuntime
    private let initialSource: AnytypeOriginalEditorQualificationSource
    private let fidelityFixture: AnytypeOriginalEditorNativeFixture?
    private var restoreConsumed = false
    private var restoreSpace: OwnedQualificationSpace?
    private var importedCandidate: AnytypeOriginalEditorImportedCandidate?

    fileprivate init(runtime: OwnedOriginalEditorQualificationRuntime,
                     source: AnytypeOriginalEditorQualificationSource,
                     binding: AnytypeOriginalEditorBinding,
                     evidence: URL,
                     fidelityFixture: AnytypeOriginalEditorNativeFixture?) {
        self.runtime = runtime
        initialSource = source
        self.binding = binding
        retainedSourceEvidenceDirectory = evidence
        self.fidelityFixture = fidelityFixture
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
        return try currentSource.binding(
            accountID: candidate.accountID, spaceID: candidate.spaceID, objectID: candidate.objectID
        )
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
    }
}
#endif
