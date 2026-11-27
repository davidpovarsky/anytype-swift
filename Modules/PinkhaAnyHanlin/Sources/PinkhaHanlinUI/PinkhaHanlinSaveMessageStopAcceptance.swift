#if DEBUG && targetEnvironment(simulator) && canImport(UIKit)
import Foundation
import UIKit
import HanlinAgentCore
import HanlinHostContracts
import PinkhaHanlinCore

/// Constructed only from a fresh original engine read, after the original SDK
/// cancellation, consumer and native worker have joined. It is not a save ACK.
public struct PinkhaHanlinStoppedRootReadback: Codable, Sendable {
    public let objectReference: String
    public let rootReadbackSHA256: String
    public let bodyRowCount: Int
    public let nativeVersionSHA256: String?
    public let nativeMarkdownSHA256: String?
    public let nativeMarkdownUTF8Bytes: Int?
    public let nativeGeneration: UUID?
    public let engineStartedAtSHA256: String?

    public init(objectReference: String, rootReadbackSHA256: String, bodyRowCount: Int,
                nativeVersionSHA256: String? = nil, nativeMarkdownSHA256: String? = nil,
                nativeMarkdownUTF8Bytes: Int? = nil, nativeGeneration: UUID? = nil,
                engineStartedAtSHA256: String? = nil) {
        self.objectReference = objectReference; self.rootReadbackSHA256 = rootReadbackSHA256
        self.bodyRowCount = bodyRowCount; self.nativeVersionSHA256 = nativeVersionSHA256
        self.nativeMarkdownSHA256 = nativeMarkdownSHA256; self.nativeMarkdownUTF8Bytes = nativeMarkdownUTF8Bytes
        self.nativeGeneration = nativeGeneration; self.engineStartedAtSHA256 = engineStartedAtSHA256
    }
}

@MainActor
final class PinkhaHanlinSaveMessageStopAcceptance: PinkhaHanlinSaveMessageNativeObserver {
    typealias NativeReadback = @MainActor @Sendable (PinkhaHanlinSaveMessageProgress) async throws -> PinkhaHanlinStoppedRootReadback
    struct PersistedObservation: Codable, Sendable {
        let event: String
        let sequence: Int
        let progressSHA256: String
    }
    struct Receipt: Codable, Sendable {
        var identity: PinkhaHanlinWriteIdentity?
        var workerID: UUID?
        var workerEnteredAt: Date?
        var rootKnownAt: Date?
        var knownRootReference: String?
        var stopRequestedAt: Date?
        var drainRegisteredAt: Date?
        var releaseAt: Date?
        var workerFinishedAt: Date?
        var consumerFinishedAt: Date?
        var sdkAndConsumerJoinedAt: Date?
        var finishedAt: Date?
        var drainWaitersObserved = 0
        var bodyDispatchEventsObserved = 0
        var persisted: [PersistedObservation] = []
        var heldProgress: PinkhaHanlinSaveMessageProgress?
        var closedProgress: PinkhaHanlinSaveMessageProgress?
        var finalProgress: PinkhaHanlinSaveMessageProgress?
        var finalEntry: PinkhaHanlinWriteJournal.Entry?
        var intentStatus: String?
        var nativeReadback: PinkhaHanlinStoppedRootReadback?
        var failure: String?
    }

    private let fixture: PinkhaHanlinSaveMessageAcceptanceFixture
    private weak var presentation: PinkhaHanlinChatPresentation?
    private let journal: PinkhaHanlinWriteJournal
    private let verifyNativeReadback: NativeReadback
    private let update: @MainActor (String, Receipt) throws -> Void
    private let failure: @MainActor (String, Receipt) -> Void
    private let releaseButton: UIButton
    private var intent: PinkhaHanlinMessageSaveIntents.Intent?
    private var receipt = Receipt()
    private var hold: CheckedContinuation<Void, Never>?
    private var watchdog: Task<Void, Never>?
    private var task: Task<Void, Never>?
    private var releasing: Task<Void, Never>?
    private var ended = false

    init(fixture: PinkhaHanlinSaveMessageAcceptanceFixture,
         presentation: PinkhaHanlinChatPresentation, journal: PinkhaHanlinWriteJournal,
         window: UIWindow, verifyNativeReadback: @escaping NativeReadback,
         update: @escaping @MainActor (String, Receipt) throws -> Void,
         failure: @escaping @MainActor (String, Receipt) -> Void) throws {
        try fixture.validate(session: presentation.session)
        guard fixture.scenario == .stopAfterDurableRoot else { throw HanlinHostError.invalidContext }
        self.fixture = fixture; self.presentation = presentation; self.journal = journal
        self.verifyNativeReadback = verifyNativeReadback; self.update = update; self.failure = failure
        releaseButton = UIButton(type: .system)
        releaseButton.frame = CGRect(x: 12, y: window.safeAreaInsets.top + 28,
            width: min(300, window.bounds.width - 24), height: 32)
        releaseButton.setTitle("Release original worker", for: .normal)
        releaseButton.backgroundColor = .systemBackground
        releaseButton.accessibilityIdentifier = "pinkha.hanlin.save-acceptance-release-root"
        releaseButton.isHidden = true; releaseButton.isEnabled = false
        releaseButton.addAction(UIAction { [weak self] _ in self?.releaseFromControl() }, for: .touchUpInside)
        window.addSubview(releaseButton)
    }

    func started(_ value: PinkhaHanlinMessageSaveIntents.Intent) throws {
        guard !ended, intent == nil, value.origin.session == presentation?.session,
              let runID = value.executionRunID else { throw HanlinHostError.resultMismatch }
        try fixture.validate(session: value.origin.session)
        try PinkhaHanlinSaveMessageNativeObservation.install(self, session: value.origin.session,
            runID: runID, requestID: value.requestID)
        intent = value
    }

    func originalSaveWorkerEntered(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID) {
        do {
            guard !ended, let intent, receipt.identity == nil,
                  identity.session == intent.origin.session, identity.runID == intent.executionRunID,
                  identity.step == 0,
                  identity.providerCallDigest == PinkhaHanlinCreatePagePlan.digest(Data(intent.requestID.uuidString.utf8)) else {
                throw HanlinHostError.resultMismatch
            }
            try identity.validate(); try fixture.validate(session: identity.session)
            receipt.identity = identity; receipt.workerID = workerID; receipt.workerEnteredAt = .now
        } catch { abort("original_stop_worker_identity_mismatch") }
    }

    func originalSavePersisted(_ event: PinkhaHanlinSaveMessageProgress.Event,
                               progress: PinkhaHanlinSaveMessageProgress) async {
        do {
            guard !ended, let identity = receipt.identity, progress.manifest.identity == identity,
                  let intent, progress.manifest.titleSHA256 == intent.titleSHA256,
                  progress.manifest.markdownSHA256 == intent.markdownSHA256,
                  receipt.persisted.count < 8,
                  receipt.persisted.last.map({ $0.sequence < progress.sequence }) ?? true else {
                throw HanlinHostError.resultMismatch
            }
            try progress.validate(identity: identity)
            let name: String
            switch event {
            case .rootDispatched: name = "rootDispatched"
            case .rootKnown: name = "rootKnown"
            case .rootVerified: name = "rootVerified"
            case .rootUncertain: name = "rootUncertain"
            case .blockDispatched, .atomicBodyDispatched:
                receipt.bodyDispatchEventsObserved += 1
                throw HanlinHostError.resultMismatch
            default: throw HanlinHostError.resultMismatch
            }
            receipt.persisted.append(.init(event: name, sequence: progress.sequence,
                progressSHA256: PinkhaHanlinCreatePagePlan.digest(try progress.canonicalBytes())))
            guard Self.hasNoBodyDispatch(progress) else { throw HanlinHostError.resultMismatch }
            guard case .rootKnown(let reference) = event else { return }
            // Confirm the bytes through the exact protected actor retained at
            // fixture preparation too; a returned protocol value is insufficient.
            let durable = try await journal.saveMessageProgress(for: identity)
            let entry = try await journal.receipt(for: identity)
            guard !ended, let durable, try durable.canonicalBytes() == progress.canonicalBytes(),
                  entry?.identity == identity, entry?.effect == .reserved,
                  receipt.rootKnownAt == nil, hold == nil, !progress.dispatchClosed,
                  progress.root.reference?.utf8.elementsEqual(reference.utf8) == true,
                  !reference.utf8.elementsEqual(fixture.sourceObjectID.utf8),
                  let presentation, !presentation.isStopping else { throw HanlinHostError.resultMismatch }
            try fixture.validate(session: identity.session)
            try presentation.validateInstallation(for: identity.session)
            // Keep enough original authority lifetime for a real UI Stop. A slow
            // native create cannot silently turn this into timeout acceptance.
            let seconds = min(20, identity.deadline.timeIntervalSinceNow - 1)
            guard seconds >= 5 else { throw HanlinHostError.deadlineExceeded }
            receipt.rootKnownAt = .now; receipt.knownRootReference = reference; receipt.heldProgress = progress
            await withTaskCancellationHandler {
                await withCheckedContinuation { continuation in
                    hold = continuation
                    do { try update("NATIVE_ROOT_DURABLE_AWAIT_STOP", receipt) }
                    catch { abort("stop_root_observation_write_failed"); return }
                    watchdog = Task { @MainActor [weak self] in
                        do {
                            try await Task.sleep(for: .seconds(seconds))
                            self?.abort("stop_root_hold_timed_out")
                        } catch {}
                    }
                }
            } onCancel: {
                Task { @MainActor [weak self] in self?.abort("stop_root_observer_cancelled") }
            }
        } catch { abort("original_durable_root_observation_failed") }
    }

    func stopRequested(messageID: UUID?) {
        guard !ended else { return }
        do {
            guard messageID == intent?.origin.messageID, hold != nil,
                  receipt.rootKnownAt != nil, receipt.stopRequestedAt == nil,
                  let identity = receipt.identity, identity.deadline > .now,
                  presentation?.isStopping == true else { throw HanlinHostError.resultMismatch }
            receipt.stopRequestedAt = .now
            try update("ORIGINAL_STOP_REQUESTED_ROOT_HELD", receipt)
        } catch { abort("original_stop_request_mismatch") }
    }

    func originalSaveDrainRegistered(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID) {
        guard !ended else { return }
        do {
            guard identity == receipt.identity, workerID == receipt.workerID, hold != nil,
                  receipt.stopRequestedAt != nil, receipt.workerFinishedAt == nil,
                  receipt.drainWaitersObserved < 4 else { throw HanlinHostError.resultMismatch }
            receipt.drainWaitersObserved += 1
            guard receipt.drainRegisteredAt == nil else { return }
            receipt.drainRegisteredAt = .now
            task = Task { @MainActor [weak self] in
                guard let self else { return }
                await self.verifyHeldDrain()
            }
        } catch { abort("original_native_drain_waiter_mismatch") }
    }

    private func verifyHeldDrain() async {
        do {
            guard let identity = receipt.identity, let presentation else { throw HanlinHostError.staleContext }
            let entry = try await journal.receipt(for: identity)
            let progress = try await journal.saveMessageProgress(for: identity)
            try Task.checkCancellation()
            guard !ended, hold != nil, receipt.workerFinishedAt == nil, presentation.isStopping,
                  entry?.effect == .uncertain, entry?.identity == identity,
                  let progress, progress.dispatchClosed, Self.hasNoBodyDispatch(progress),
                  progress.root.reference?.data(using: .utf8) == receipt.heldProgress?.root.reference?.data(using: .utf8) else {
                throw HanlinHostError.resultMismatch
            }
            try progress.validate(identity: identity)
            receipt.closedProgress = progress
            try update("ORIGINAL_DRAIN_WAITING_ROOT_HELD", receipt)
            releaseButton.isHidden = false; releaseButton.isEnabled = true
        } catch { abort("original_closed_journal_or_drain_observation_failed") }
    }

    private func releaseFromControl() {
        do {
            guard !ended, hold != nil, receipt.closedProgress?.dispatchClosed == true,
                  receipt.drainRegisteredAt != nil, receipt.workerFinishedAt == nil,
                  receipt.releaseAt == nil, presentation?.isStopping == true else { throw HanlinHostError.resultMismatch }
            receipt.releaseAt = .now
            try update("ORIGINAL_WORKER_RELEASED_DRAIN_PENDING", receipt)
            releaseHold()
        } catch { abort("original_root_release_mismatch") }
    }

    func originalSaveWorkerFinished(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID) {
        guard !ended else { return }
        guard identity == receipt.identity, workerID == receipt.workerID, hold == nil,
              receipt.releaseAt != nil, receipt.workerFinishedAt == nil else {
            abort("original_worker_finished_before_held_drain"); return
        }
        receipt.workerFinishedAt = .now
    }

    func consumerFinished(_ value: PinkhaHanlinMessageSaveIntents.Intent) {
        guard !ended else { return }
        guard value.requestID == intent?.requestID, value.origin == intent?.origin,
              value.executionRunID == intent?.executionRunID,
              value.status == .uncertain || value.status == .unconfirmed,
              receipt.consumerFinishedAt == nil else { abort("original_stop_consumer_mismatch"); return }
        receipt.consumerFinishedAt = .now; receipt.intentStatus = value.status.rawValue
    }

    func joined(messageID: UUID?, cancellation: HanlinAgentRunCancellation?) {
        guard !ended else { return }
        do {
            guard messageID == intent?.origin.messageID,
                  let cancellation, cancellation.session == receipt.identity?.session,
                  cancellation.runID == receipt.identity?.runID, cancellation.requiresReconciliation,
                  receipt.workerFinishedAt != nil, receipt.consumerFinishedAt != nil,
                  receipt.releaseAt != nil, receipt.sdkAndConsumerJoinedAt == nil else { throw HanlinHostError.resultMismatch }
            receipt.sdkAndConsumerJoinedAt = .now
            task = Task { @MainActor [weak self] in
                guard let self else { return }
                await self.finish()
            }
        } catch { abort("original_sdk_stop_did_not_join") }
    }

    private func finish() async {
        do {
            guard !ended, let identity = receipt.identity, let presentation, let intent,
                  !presentation.isStopping, !presentation.isStreaming, presentation.saveMessageAcceptanceRequiresReconciliation,
                  !presentation.canSaveMessage(intent.origin.messageID),
                  !presentation.isMessageSaved(intent.origin.messageID) else { throw HanlinHostError.resultMismatch }
            try fixture.validate(session: identity.session)
            try presentation.validateInstallation(for: identity.session)
            let entry = try await journal.receipt(for: identity)
            let progress = try await journal.saveMessageProgress(for: identity)
            let known = try await journal.knownCreatedObjectReference(for: identity)
            try Task.checkCancellation()
            guard !ended, let entry, entry.identity == identity, entry.effect == .uncertain,
                  let progress, progress.dispatchClosed, Self.hasNoBodyDispatch(progress),
                  let root = progress.root.reference, let heldRoot = receipt.heldProgress?.root.reference,
                  known?.utf8.elementsEqual(root.utf8) == true, root.utf8.elementsEqual(heldRoot.utf8),
                  receipt.bodyDispatchEventsObserved == 0 else { throw HanlinHostError.resultMismatch }
            try progress.validate(identity: identity)
            receipt.finalEntry = entry; receipt.finalProgress = progress
            try update("ORIGINAL_STOP_JOINED_NATIVE_READ_REQUIRED", receipt)
            let actual = try await verifyNativeReadback(progress)
            try Task.checkCancellation()
            try presentation.validateInstallation(for: identity.session)
            guard !ended, actual.objectReference.utf8.elementsEqual(root.utf8), actual.bodyRowCount == 0,
                  actual.rootReadbackSHA256 == progress.manifest.expectedRootReadbackSHA256 else {
                throw HanlinHostError.resultMismatch
            }
            if fixture.engine == .any {
                guard actual.nativeVersionSHA256.map({ PinkhaHanlinWriteIdentity.isDigest($0) }) == true,
                      actual.nativeMarkdownSHA256 == PinkhaHanlinCreatePagePlan.digest(Data()),
                      actual.nativeMarkdownUTF8Bytes == 0,
                      actual.nativeGeneration == fixture.anyRuntime?.generation,
                      actual.engineStartedAtSHA256 == fixture.anyRuntime.map({
                          PinkhaHanlinCreatePagePlan.digest(Data($0.engineStartedAt.utf8))
                      }) else { throw HanlinHostError.resultMismatch }
            } else {
                guard actual.nativeVersionSHA256 == nil, actual.nativeMarkdownSHA256 == nil,
                      actual.nativeMarkdownUTF8Bytes == nil, actual.nativeGeneration == nil,
                      actual.engineStartedAtSHA256 == nil else { throw HanlinHostError.resultMismatch }
            }
            receipt.nativeReadback = actual; receipt.finishedAt = .now
            try update("ORIGINAL_STOP_DRAIN_AND_EMPTY_ROOT_READBACK_PASS", receipt)
            ended = true
            PinkhaHanlinSaveMessageNativeObservation.uninstall(self)
            releaseButton.removeFromSuperview()
        } catch { abort("original_stop_receipt_or_empty_native_readback_failed") }
    }

    func invalidate() {
        task?.cancel(); watchdog?.cancel()
        PinkhaHanlinSaveMessageNativeObservation.uninstall(self)
        releaseButton.removeFromSuperview()
        if !ended {
            ended = true; receipt.failure = "original_stop_presentation_invalidated"; receipt.finishedAt = .now
            failure("original_stop_presentation_invalidated", receipt)
        }
        // The owner calls this before its synchronous host.revokePresentation.
        // Releasing on the next MainActor turn lets THAT original fence close
        // before the suspended worker may attempt another authorization.
        scheduleRelease()
    }

    func drain() async {
        await task?.value
        await releasing?.value
    }

    func evidenceFailed() { abort("original_stop_driver_evidence_failed") }
    func cancellationFailed() { abort("original_sdk_cancellation_failed") }

    private func abort(_ code: String) {
        guard !ended else { return }
        ended = true; receipt.failure = code; receipt.finishedAt = .now
        watchdog?.cancel(); task?.cancel()
        PinkhaHanlinSaveMessageNativeObservation.uninstall(self)
        releaseButton.removeFromSuperview()
        failure(code, receipt)
        // A watchdog or evidence failure must not release a still-authorized
        // body write. Revoke through the original host before resuming the hold.
        presentation?.invalidate()
        scheduleRelease()
    }

    private func scheduleRelease() {
        guard releasing == nil else { return }
        releasing = Task { @MainActor [self] in
            releaseHold()
        }
    }

    private func releaseHold() {
        watchdog?.cancel(); watchdog = nil
        releaseButton.isEnabled = false; releaseButton.isHidden = true
        let continuation = hold; hold = nil; continuation?.resume()
    }

    static func hasNoBodyDispatch(_ progress: PinkhaHanlinSaveMessageProgress) -> Bool {
        progress.bodyReadback == nil && progress.atomicBody == nil && progress.blocks.allSatisfy { $0 == .pending }
    }
}
#endif
