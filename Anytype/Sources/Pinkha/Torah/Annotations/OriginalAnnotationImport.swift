import Foundation
import CryptoKit
import Security
@_spi(OriginalEditor) import ProtobufMessages

/// Complete copied native history delivered after both original RPC drains.
/// These values do not grant current source/Space permission, a retry, a durable
/// destination mapping, body acceptance, or a Host acknowledgement.
struct OriginalAnnotationImportCallHistory: Sendable {
    let response: Anytype_Rpc.Annotation.Import.Response?
    let responseCopyError: OriginalAnnotationImportHistoryError?
    let cancellationResponse: Anytype_Rpc.Annotation.Import.Cancel.Response?
    let cancellationCopyError: OriginalAnnotationImportHistoryError?
    let cancellationWasScheduled: Bool
    let cancellationAwaitFailed: Bool

    fileprivate init(
        call: OriginalAnnotationImportCall,
        cancellation: OriginalAnnotationImportCancellationCall,
        cancellationWasScheduled: Bool,
        cancellationAwaitFailed: Bool
    ) {
        do {
            response = try call.copyObservedNativeResponse()
            responseCopyError = nil
        } catch {
            response = nil
            responseCopyError = (error as? OriginalAnnotationImportHistoryError) ?? .copyFailed
        }
        do {
            cancellationResponse = try cancellation.copyObservedNativeResponse()
            cancellationCopyError = nil
        } catch {
            cancellationResponse = nil
            cancellationCopyError = (error as? OriginalAnnotationImportHistoryError) ?? .copyFailed
        }
        self.cancellationWasScheduled = cancellationWasScheduled
        self.cancellationAwaitFailed = cancellationAwaitFailed
    }
}

enum OriginalAnnotationImportAttemptError: Error, Sendable, Equatable {
    case invalidInput
    case randomSourceUnavailable
    case alreadyInvoked
    case unqualifiedCancellation
}

/// Local scheduling facts only, deliberately separate from the native Cancel
/// response's NOT_OBSERVED/REQUESTED/DONE_OBSERVED dispositions.
enum OriginalAnnotationImportCancellationScheduling: Sendable {
    case beforeInvocation
    case scheduled
    case alreadyScheduled
    case importDrained
}

/// Marks whether SourceBinding actually entered its supplied operation. This
/// distinguishes a rejection before that closure from a native RPC still
/// running after its Swift waiter was cancelled; a nil response cannot do that.
private final class OriginalAnnotationImportEntry: @unchecked Sendable {
    private let lock = NSLock()
    private var entered = false

    func enter() {
        lock.lock()
        entered = true
        lock.unlock()
    }

    var didEnter: Bool {
        lock.lock()
        defer { lock.unlock() }
        return entered
    }
}

/// A one-use, closed original selected-Space/source operation. Construction does
/// no native work. Its owner must durably mark possible dispatch before invoking
/// this exact handle, retain it through onDrained, and never adopt history as a
/// fresh attempt. No public factory accepts a replacement native executor.
@MainActor
final class OriginalAnnotationImportAttempt {
    private enum Phase { case prepared, invoking, drained }

    private let source: EditorDocumentWriteSourceBinding
    private let call: OriginalAnnotationImportCall
    private let cancellationCall: OriginalAnnotationImportCancellationCall
    private let entry = OriginalAnnotationImportEntry()
    private var onDrained: (@MainActor @Sendable (OriginalAnnotationImportCallHistory) -> Void)?
    private var phase = Phase.prepared
    private var admissions: [EditorDocumentWriteLifetime.Observation] = []
    private var retirements: [EditorDocumentWriteLifetime.Observation] = []
    private var importDrained = false
    private var cancellationScheduled = false
    private var cancellationDrained = false
    private var cancellationAwaitFailed = false
    private var cancellationTask: Task<Void, Never>?
    private(set) var drainedHistory: OriginalAnnotationImportCallHistory?

    fileprivate init(
        source: EditorDocumentWriteSourceBinding,
        request: Anytype_Rpc.Annotation.Import.Request,
        cancellation: Anytype_Rpc.Annotation.Import.Cancel.Request,
        onDrained: @escaping @MainActor @Sendable (OriginalAnnotationImportCallHistory) -> Void
    ) {
        self.source = source
        call = ClientCommands.annotationImport(request).retainingOriginalAnnotationImportHistory()
        cancellationCall = ClientCommands.annotationImportCancel(cancellation)
            .retainingOriginalAnnotationImportCancellationHistory()
        self.onDrained = onDrained
    }

    /// One actual original typed invocation. A thrown error, including waiter
    /// cancellation, preserves its complete late response through onDrained.
    func invoke() async throws -> Anytype_Rpc.Annotation.Import.Response {
        guard phase == .prepared else {
            throw OriginalAnnotationImportAttemptError.alreadyInvoked
        }
        phase = .invoking
        do {
            try source.validate()
            // These are the same source/account/selection/permission captures,
            // not newly created lifetimes. Keep their original admissions until
            // both original native calls have drained, including after retirement.
            admissions = try EditorDocumentWriteCapture.acquireAll(source.captures)
            retirements = source.captures.map { capture in
                capture.source.observe(capture.token) { [self] in
                    Task { @MainActor in _ = requestCancellation() }
                }
            }
        } catch {
            finishImportDrain()
            throw error
        }

        return try await withTaskCancellationHandler {
            do {
                return try await source.performOperation(
                    rpcNames: ["AnnotationImport"],
                    onDrained: { [self] in finishImportDrain() },
                    operation: { [call, entry] in
                        entry.enter()
                        return try await call.invoke()
                    }
                )
            } catch {
                // performOperation installs its drain before entering this
                // closure. If it never entered, its pre-admission rejection
                // cannot have scheduled this closed native call. Otherwise
                // only that original drain may release the retained admissions.
                if !entry.didEnter { finishImportDrain() }
                throw error
            }
        } onCancel: { [self] in
            Task { @MainActor in _ = requestCancellation() }
        }
    }

    /// Cancellation-only dispatch for this same immutable private request.
    /// It cannot start another import, renew current write permission, or turn
    /// NOT_OBSERVED into drain. There is exactly one control call and no retry.
    @discardableResult
    func requestCancellation() -> OriginalAnnotationImportCancellationScheduling {
        guard phase != .prepared else { return .beforeInvocation }
        if cancellationScheduled { return .alreadyScheduled }
        guard phase == .invoking, !importDrained else { return .importDrained }
        cancellationScheduled = true
        // An unstructured task is owned by this attempt. Cancelling an awaiting
        // UI task does not abandon the actual cancellation call or its drain.
        cancellationTask = Task { @MainActor [self] in
            await runCancellation()
        }
        return .scheduled
    }

    private func runCancellation() async {
        let lease = EditorDocumentWriteOperation { [self] _ in
            Task { @MainActor in finishCancellationDrain() }
        }
        defer {
            if lease.finishOuter() { finishCancellationDrain() }
        }
        // The captured admissions above are already held. Reacquiring a
        // current-source write permit after retirement would reject necessary
        // cleanup. This exact binding admits only the already-created control,
        // whose native endpoint can only cancel a matching registered import.
        let binding = InvocationDispatchBinding { messageName in
            guard messageName == "AnnotationImportCancel" else {
                throw OriginalAnnotationImportAttemptError.unqualifiedCancellation
            }
            return lease.permit { [] }
        }
        do {
            _ = try await InvocationDispatchContext.$binding.withValue(binding) { [cancellationCall] in
                try await cancellationCall.invoke()
            }
        } catch {
            // Native error policy is unchanged inside Invocation. Keep failed
            // or unobserved control history and still wait for actual drain.
            cancellationAwaitFailed = true
        }
    }

    private func finishImportDrain() {
        guard !importDrained else { return }
        importDrained = true
        finishIfDrained()
    }

    private func finishCancellationDrain() {
        guard !cancellationDrained else { return }
        cancellationDrained = true
        finishIfDrained()
    }

    private func finishIfDrained() {
        guard phase == .invoking, importDrained,
              !cancellationScheduled || cancellationDrained else { return }
        phase = .drained
        let history = OriginalAnnotationImportCallHistory(
            call: call, cancellation: cancellationCall,
            cancellationWasScheduled: cancellationScheduled,
            cancellationAwaitFailed: cancellationAwaitFailed
        )
        drainedHistory = history
        let deliver = onDrained
        onDrained = nil
        for observation in retirements { observation.cancel() }
        retirements.removeAll()
        // Release only after both complete response copies have been retained.
        // A history callback has no authority to revive any of these captures.
        for admission in admissions { admission.cancel() }
        admissions.removeAll()
        cancellationTask = nil
        deliver?(history)
    }
}

@MainActor
extension EditorDocumentWriteSourceBinding {
    /// Intersects the existing source with a genuinely selected original Space
    /// and current original subscription permissions. IDs/archive are bounded
    /// input data only; the original account and native application still admit
    /// the real import. Preparation neither dispatches nor claims a saved row.
    func prepareOriginalAnnotationImport(
        selection: OriginalActiveSpaceSelection,
        sourceSpaceID: String,
        sourceRootID: String,
        archive: Data,
        onDrained: @escaping @MainActor @Sendable (OriginalAnnotationImportCallHistory) -> Void
    ) throws -> OriginalAnnotationImportAttempt {
        try validate()
        try selection.validate()
        let targetSpaceID = selection.accountInfo.accountSpaceId
        let identities = [selection.accountID, sourceSpaceID, sourceRootID, targetSpaceID]
        guard identities.allSatisfy({
            !$0.isEmpty && $0.utf8.count <= 16_384 && !$0.utf8.contains(0)
        }), !archive.isEmpty, archive.count <= 1_024 * 1_024 else {
            throw OriginalAnnotationImportAttemptError.invalidInput
        }
        guard let participants = Container.shared.participantsStorage() as? ParticipantsStorage,
              let spaceViews = Container.shared.spaceViewsStorage() as? SpaceViewsStorage else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let participant = try participants.currentParticipantEditPermission(spaceId: targetSpaceID)
        let spaceView = try spaceViews.currentOriginalSpaceViewPermission(spaceId: targetSpaceID)
        guard spaceView.originalSpaceView.id.utf8.elementsEqual(selection.accountInfo.spaceViewId.utf8) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        let qualified = try requiringOriginalSelectedSpace(selection)
            .requiringSpaceEditPermission(
                participant: participant, spaceView: spaceView, spaceId: targetSpaceID
            )

        var secret = Data(count: 32)
        let randomStatus = secret.withUnsafeMutableBytes { buffer in
            SecRandomCopyBytes(kSecRandomDefault, buffer.count, buffer.baseAddress!)
        }
        guard randomStatus == errSecSuccess, secret.contains(where: { $0 != 0 }) else {
            throw OriginalAnnotationImportAttemptError.randomSourceUnavailable
        }
        var request = Anytype_Rpc.Annotation.Import.Request()
        request.importProtocol = "pinkha.annotation.import.v1"
        request.expectedAccountID = selection.accountID
        request.sourceSpaceID = sourceSpaceID
        request.sourceRootID = sourceRootID
        request.targetSpaceID = targetSpaceID
        request.archive = archive
        request.archiveSha256 = Data(SHA256.hash(data: archive))
        request.attemptSecret = secret

        var cancellation = Anytype_Rpc.Annotation.Import.Cancel.Request()
        cancellation.importProtocol = request.importProtocol
        cancellation.expectedAccountID = request.expectedAccountID
        cancellation.sourceSpaceID = request.sourceSpaceID
        cancellation.sourceRootID = request.sourceRootID
        cancellation.targetSpaceID = request.targetSpaceID
        cancellation.archiveSha256 = request.archiveSha256
        cancellation.attemptSecret = request.attemptSecret
        try qualified.validate()
        return OriginalAnnotationImportAttempt(
            source: qualified, request: request, cancellation: cancellation, onDrained: onDrained
        )
    }
}
