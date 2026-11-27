#if DEBUG && targetEnvironment(simulator)
import Foundation
import HanlinHostContracts

/// Diagnostic observation only. The original worker and protected store create
/// every identity/value below. No observer can return a native result, approve
/// an effect, alter a receipt, or replace the journal. The one permitted await
/// occurs AFTER the real store has returned, outside its actor/file lock.
@MainActor
public protocol PinkhaHanlinSaveMessageNativeObserver: AnyObject {
    func originalSaveWorkerEntered(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID)
    func originalSavePersisted(_ event: PinkhaHanlinSaveMessageProgress.Event,
                               progress: PinkhaHanlinSaveMessageProgress) async
    func originalSaveDrainRegistered(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID)
    func originalSaveWorkerFinished(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID)
}

@MainActor
public enum PinkhaHanlinSaveMessageNativeObservation {
    nonisolated static var isRequested: Bool {
        let environment = ProcessInfo.processInfo.environment
        return environment["PINKHA_HANLIN_SAVE_NATIVE_UI"] == "1"
            && environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1"
            && environment["PINKHA_HANLIN_SAVE_SCENARIO"] == "stopAfterDurableRoot"
    }
    private struct Binding {
        let session: HanlinHostSession
        let runID: UUID
        let providerCallDigest: String
    }
    private static weak var observer: (any PinkhaHanlinSaveMessageNativeObserver)?
    private static var binding: Binding?

    /// Called only by the already validated, single-use native fixture after
    /// the ORIGINAL AgentSession has issued its presentation-tool start event.
    /// A process owns at most one observer; another fixture cannot replace it.
    public static func install(_ value: any PinkhaHanlinSaveMessageNativeObserver,
                               session: HanlinHostSession, runID: UUID, requestID: UUID) throws {
        guard observer == nil, isRequested else {
            throw HanlinHostError.invalidContext
        }
        binding = .init(session: session, runID: runID,
            providerCallDigest: PinkhaHanlinCreatePagePlan.digest(Data(requestID.uuidString.utf8)))
        observer = value
    }

    public static func uninstall(_ value: any PinkhaHanlinSaveMessageNativeObserver) {
        guard observer === value else { return }
        observer = nil; binding = nil
    }

    static func workerEntered(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID) {
        guard matches(identity), let observer else { return }
        observer.originalSaveWorkerEntered(identity, workerID: workerID)
    }

    static func persisted(_ event: PinkhaHanlinSaveMessageProgress.Event,
                          progress: PinkhaHanlinSaveMessageProgress) async {
        guard matches(progress.manifest.identity), let observer else { return }
        await observer.originalSavePersisted(event, progress: progress)
    }

    static func drainRegistered(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID) {
        guard matches(identity), let observer else { return }
        observer.originalSaveDrainRegistered(identity, workerID: workerID)
    }

    static func workerFinished(_ identity: PinkhaHanlinWriteIdentity, workerID: UUID) {
        guard matches(identity), let observer else { return }
        observer.originalSaveWorkerFinished(identity, workerID: workerID)
    }

    private static func matches(_ identity: PinkhaHanlinWriteIdentity) -> Bool {
        guard let binding else { return false }
        return identity.session == binding.session && identity.runID == binding.runID && identity.step == 0
            && identity.providerCallDigest == binding.providerCallDigest
    }
}
#endif
