import Foundation
private enum EditorDocumentWriteError: Error { case rejected(Reason); enum Reason { case retired } }
private struct TypecheckAdmission: Sendable { func cancel() {} }
private final class TypecheckAttempt: Sendable {
    func waitForDrain() async {}
    func admitStage() throws -> [TypecheckAdmission] { [] }
}
private final class TypecheckTasks: Sendable {
    func drain() async {}
    func installMembership(_ task: Task<Void, Error>) {}
}
private struct OriginalAuthStartupSource: Sendable { let binding = TypecheckBinding() }
private struct TypecheckBinding: Sendable {}
private enum InvocationDispatchContext { @TaskLocal static var binding: TypecheckBinding? }
@MainActor private protocol MembershipStatusStorageProtocol: Sendable { func startSubscription() async }
private actor LoginStateIsolationProbe {
    private final class Startup: Sendable {
        let attempt = TypecheckAttempt()
        let tasks = TypecheckTasks()
        func retire() {}
    }
    private var startup: Startup?
    private var accountSource: OriginalAuthStartupSource?
    private var stopping: Stopping?
    private var primaryRunning = false
    private let membershipStatusStorage: any MembershipStatusStorageProtocol
    init(membershipStatusStorage: any MembershipStatusStorageProtocol) { self.membershipStatusStorage = membershipStatusStorage }
    private func validate(_ owner: Startup, source: OriginalAuthStartupSource) throws {}
    private func stopSubscriptions() async {}
    private func clearOriginalStateAfterLogout() async {}
private final class Stopping: @unchecked Sendable {
        var clearAccountData: Bool
        var task: Task<Void, Never>?
        init(clearAccountData: Bool) { self.clearAccountData = clearAccountData }
    }
private func stopOwnedSubscriptions(clearAccountData: Bool) async {
        if let stop = stopping {
            if clearAccountData { stop.clearAccountData = true }
            await stop.task?.value
            return
        }
        let owner = startup
        owner?.retire()
        let stop = Stopping(clearAccountData: clearAccountData)
        stopping = stop
        let task = Task { [weak self] in
            guard let self else { return }
            await self.completeOwnedStop(owner: owner, stop: stop)
        }
        stop.task = task
        await task.value
    }
private func completeOwnedStop(owner: Startup?, stop: Stopping) async {
        await owner?.tasks.drain()
        // Auth's outer startup lease is finished before its error cleanup
        // requests this drain; native Stop is dispatched before logout joins.
        await owner?.attempt.waitForDrain()
        await stopSubscriptions()
        if stop.clearAccountData {
            await clearOriginalStateAfterLogout()
        }
        if startup === owner {
            startup = nil
            accountSource = nil
            primaryRunning = false
        }
        if stopping === stop { stopping = nil }
    }
    private func membershipTypecheck(_ owner: Startup, source: OriginalAuthStartupSource) async throws {
        let task = Task { [weak self] in
            guard let self else { throw EditorDocumentWriteError.rejected(.retired) }
            let admissions = try owner.attempt.admitStage()
            defer { for admission in admissions { admission.cancel() } }
            try await InvocationDispatchContext.$binding.withValue(source.binding) {
                try await self.validate(owner, source: source)
                await self.membershipStatusStorage.startSubscription()
                try await self.validate(owner, source: source)
            }
        }
        owner.tasks.installMembership(task)
    }
}
