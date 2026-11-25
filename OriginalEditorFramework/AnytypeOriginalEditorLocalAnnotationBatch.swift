import Foundation

/// An explicit conversion run for ONE captured Host profile. This is data, not
/// an account, Space selector or permission to publish an annotation.
public struct AnytypeOriginalEditorLocalAnnotationBatchSource: Sendable, Equatable {
    public let hostProfileID: String
    public let batchID: UUID

    public init(hostProfileID: String, batchID: UUID) throws {
        guard !hostProfileID.isEmpty, hostProfileID.utf8.count <= 512,
              !hostProfileID.utf8.contains(0) else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidSource
        }
        self.hostProfileID = hostProfileID
        self.batchID = batchID
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.hostProfileID.utf8.elementsEqual(rhs.hostProfileID.utf8)
            && lhs.batchID == rhs.batchID
    }
}

/// Bind this one-use run owner to the actual captured Host profile/workspace
/// before awaiting the factory. Retirement immediately closes native dispatch
/// admission and never calls back on the Host's retiring mutex stack.
@MainActor
public final class AnytypeOriginalEditorLocalAnnotationBatchSourceLifetime {
    public nonisolated let source: AnytypeOriginalEditorLocalAnnotationBatchSource
    internal nonisolated let lifetime = EditorDocumentWriteLifetime()
    private var claimed = false

    public init(source: AnytypeOriginalEditorLocalAnnotationBatchSource) { self.source = source }
    public nonisolated var isCurrent: Bool { lifetime.token() != nil }

    public nonisolated func retire() {
        guard let deliver = lifetime.markUnavailableDeferringObservers() else { return }
        Task { @MainActor in deliver() }
    }

    internal func claim() throws {
        guard isCurrent else { throw AnytypeOriginalEditorLocalAnnotationError.retiredSource }
        guard !claimed else { throw AnytypeOriginalEditorLocalAnnotationError.sourceAlreadyUsed }
        claimed = true
    }

    deinit { retire() }
}

/// A bounded explicit conversion run in ONE newly created original private
/// localOnly Space. Each UUID is admitted once and gets a fresh native root.
/// There is one active annotation at a time. Neither a persisted batch record
/// nor a Space ID can construct this owner or resume its native authority.
@MainActor
public final class AnytypeOriginalEditorLocalAnnotationBatchSession {
    public static let maximumAnnotations = 5_000
    public nonisolated let source: AnytypeOriginalEditorLocalAnnotationBatchSource
    private let owner: OriginalEditorLocalAnnotationBatchOwner
    private nonisolated let sourceLifetime: AnytypeOriginalEditorLocalAnnotationBatchSourceLifetime

    internal init(owner: OriginalEditorLocalAnnotationBatchOwner) {
        self.owner = owner
        sourceLifetime = owner.sourceLifetime
        source = owner.sourceLifetime.source
    }

    /// The ordinary LocalAnnotationSession supplies the actual original editor
    /// and its same flushed native capture. Backfill calls capture without mounting
    /// a view; Save remains the Host's original atomic saved-row transaction.
    public func openPlainAnnotation(
        sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
        text: String,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorLocalAnnotationSession {
        try sourceLifetime.claim()
        do {
            try Task.checkCancellation()
            try owner.validate()
            guard sourceLifetime.source.hostProfileID.utf8.elementsEqual(source.hostProfileID.utf8),
                  sourceLifetime.isCurrent, sourceIsCurrent(sourceLifetime.source) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
            let canonical = try OriginalEditorLocalAnnotationCanonical(
                source: sourceLifetime.source, body: .plainText(text))
            let draft = try await owner.runtime.openBatchAnnotation(
                batch: owner, sourceLifetime: sourceLifetime, canonical: canonical,
                sourceIsCurrent: sourceIsCurrent)
            return AnytypeOriginalEditorLocalAnnotationSession(owner: draft)
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }

    public func retire() { owner.retire() }
    deinit { sourceLifetime.retire() }
}

extension AnytypeOriginalEditorModule {
    /// Creates one NEW private localOnly Space for the explicit run. Ordinary
    /// editor opens retain their existing fresh-Space policy. On pause/relaunch
    /// the Host re-scans its canonical committed rows and starts a new run;
    /// this factory never adopts an uncertain historical batch or native root.
    @MainActor
    public static func openLocalAnnotationBatch(
        appGroup: String,
        sourceLifetime: AnytypeOriginalEditorLocalAnnotationBatchSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationBatchSource) -> Bool
    ) async throws -> AnytypeOriginalEditorLocalAnnotationBatchSession {
        try sourceLifetime.claim()
        do {
            try Task.checkCancellation()
            guard sourceLifetime.isCurrent, sourceIsCurrent(sourceLifetime.source) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
            let runtime = try await OriginalEditorLocalAnnotationRuntime.acquire(appGroup: appGroup)
            let owner = try await runtime.openBatch(sourceLifetime: sourceLifetime,
                sourceIsCurrent: sourceIsCurrent)
            return AnytypeOriginalEditorLocalAnnotationBatchSession(owner: owner)
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }
}

@MainActor
internal final class OriginalEditorLocalAnnotationBatchOwner {
    nonisolated let sourceLifetime: AnytypeOriginalEditorLocalAnnotationBatchSourceLifetime
    let runtime: OriginalEditorLocalAnnotationRuntime
    let journalRecord: OriginalEditorLocalAnnotationJournal.Batch
    let selected: OriginalActiveSpaceSelection
    let annotationTypeID: String
    let capture: EditorDocumentWriteCapture
    private let sourceIsCurrent: @MainActor (AnytypeOriginalEditorLocalAnnotationBatchSource) -> Bool
    private var admittedAnnotations = Set<UUID>()
    private var runRetirement: EditorDocumentWriteLifetime.Observation?

    init(sourceLifetime: AnytypeOriginalEditorLocalAnnotationBatchSourceLifetime,
         runtime: OriginalEditorLocalAnnotationRuntime,
         journalRecord: OriginalEditorLocalAnnotationJournal.Batch,
         selected: OriginalActiveSpaceSelection, annotationTypeID: String,
         capture: EditorDocumentWriteCapture,
         sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationBatchSource) -> Bool) {
        self.sourceLifetime = sourceLifetime; self.runtime = runtime
        self.journalRecord = journalRecord; self.selected = selected
        self.annotationTypeID = annotationTypeID; self.capture = capture
        self.sourceIsCurrent = sourceIsCurrent
        runRetirement = sourceLifetime.lifetime.observe(capture.token) { [weak self] in
            // The token already closes actual GCD admissions immediately.
            // Child/UI cleanup is deliberately delivered off the Host mutex.
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.runtime.retireBatch(self)
            }
        }
    }

    var isCurrent: Bool { sourceLifetime.isCurrent }

    func validate() throws {
        try runtime.validate()
        try capture.validate()
        guard sourceLifetime.isCurrent, sourceIsCurrent(sourceLifetime.source) else {
            sourceLifetime.retire()
            throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
        }
        try selected.validate()
        guard selected.accountInfo.accountSpaceId.utf8.elementsEqual((journalRecord.spaceID ?? "").utf8),
              selected.accountInfo.spaceViewId.utf8.elementsEqual((journalRecord.spaceViewID ?? "").utf8) else {
            sourceLifetime.retire()
            throw AnytypeOriginalEditorLocalAnnotationError.unavailableSpace
        }
    }

    /// Reserve before any journal/native await. A refused or uncertain attempted
    /// UUID is not retried in this Space, even if its ordinary source was retired.
    func reserve(_ source: AnytypeOriginalEditorLocalAnnotationSource) throws {
        try validate()
        guard source.hostProfileID.utf8.elementsEqual(sourceLifetime.source.hostProfileID.utf8),
              admittedAnnotations.count < AnytypeOriginalEditorLocalAnnotationBatchSession.maximumAnnotations,
              admittedAnnotations.insert(source.annotationUUID).inserted else {
            throw AnytypeOriginalEditorLocalAnnotationError.sourceAlreadyUsed
        }
    }

    func retire() {
        sourceLifetime.retire()
        runtime.retireBatch(self)
    }
}
